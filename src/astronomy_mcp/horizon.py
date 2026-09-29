"""Terrain horizon profiles from a digital elevation model.

Samples terrain along rays every 10° of azimuth out to ~35 km using the Open-Meteo
elevation API (Copernicus DEM, 90 m; falls back to OpenTopoData SRTM 90 m when
rate-limited), then takes the highest apparent angle along each ray, allowing for
Earth's curvature and standard refraction. Ridges are broad, so the profile is
interpolated between rays.
Trees and buildings are not in the DEM, so a local horizon can still be higher.
Profiles are cached on disk per location.
"""

from __future__ import annotations

import asyncio
import json
import math
from dataclasses import dataclass
from typing import Any

from astronomy_mcp.http import UpstreamError, get_json
from astronomy_mcp.lightpollution import destination
from astronomy_mcp.location import Location, data_dir
from astronomy_mcp.sky import compass

ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
OPENTOPODATA_URL = "https://api.opentopodata.org/v1/srtm90m"
EARTH_RADIUS_M = 6_371_000.0
REFRACTION_K = 0.13  # standard terrestrial refraction coefficient
EYE_HEIGHT_M = 1.7
# Open-Meteo counts every coordinate against a 600-per-minute limit, so keep a profile
# (36 rays x 12 distances + the observer = 433 points) well under it.
AZIMUTH_STEP_DEG = 10
DISTANCES_KM = (0.3, 0.6, 1, 1.5, 2.5, 4, 6, 9, 13, 18, 25, 35)
BATCH = 100


@dataclass
class Horizon:
    """Obstruction altitude (degrees) at each sampled azimuth."""

    azimuths: list[float]
    altitudes: list[float]
    observer_elevation_m: float

    def altitude_at(self, azimuth_deg: float) -> float:
        step = self.azimuths[1] - self.azimuths[0]
        pos = (azimuth_deg % 360) / step
        i = int(pos) % len(self.azimuths)
        j = (i + 1) % len(self.azimuths)
        frac = pos - int(pos)
        return self.altitudes[i] * (1 - frac) + self.altitudes[j] * frac

    def summary(self) -> dict[str, Any]:
        highest = max(range(len(self.altitudes)), key=lambda i: self.altitudes[i])
        sectors = {}
        for name, center in (("N", 0), ("NE", 45), ("E", 90), ("SE", 135), ("S", 180), ("SW", 225), ("W", 270), ("NW", 315)):
            vals = [self.altitude_at(center + d) for d in range(-20, 21, 5)]
            sectors[name] = round(max(vals), 1)
        return {
            "observer_ground_elevation_m": round(self.observer_elevation_m),
            "highest_obstruction": {
                "altitude_deg": round(self.altitudes[highest], 1),
                "azimuth_deg": self.azimuths[highest],
                "direction": compass(self.azimuths[highest]),
            },
            "average_horizon_deg": round(sum(max(a, 0) for a in self.altitudes) / len(self.altitudes), 1),
            "max_obstruction_by_direction_deg": sectors,
            "profile": [{"azimuth_deg": az, "altitude_deg": round(alt, 1)} for az, alt in zip(self.azimuths, self.altitudes)],
        }


def apparent_angle(observer_m: float, target_m: float, distance_m: float) -> float:
    """Elevation angle of a terrain point, including curvature and refraction."""
    drop = distance_m**2 / (2 * EARTH_RADIUS_M) * (1 - REFRACTION_K)
    return math.degrees(math.atan2(target_m - drop - observer_m, distance_m))


def _cache_path(lat: float, lon: float):
    return data_dir() / "horizons" / f"{lat:.4f}_{lon:.4f}.json"


async def _open_meteo(chunk: list[tuple[float, float]]) -> list[float]:
    payload = await get_json(
        ELEVATION_URL,
        {"latitude": ",".join(f"{p[0]:.5f}" for p in chunk), "longitude": ",".join(f"{p[1]:.5f}" for p in chunk)},
        source="Open-Meteo elevation",
        timeout=30,
    )
    return [float(e) if e is not None else 0.0 for e in payload["elevation"]]


async def _opentopodata(chunk: list[tuple[float, float]]) -> list[float]:
    payload = await get_json(
        OPENTOPODATA_URL,
        {"locations": "|".join(f"{p[0]:.5f},{p[1]:.5f}" for p in chunk)},
        source="OpenTopoData",
        timeout=30,
    )
    return [float(r["elevation"]) if r.get("elevation") is not None else 0.0 for r in payload["results"]]


async def _elevations(points: list[tuple[float, float]]) -> list[float]:
    chunks = [points[i:i + BATCH] for i in range(0, len(points), BATCH)]
    try:
        results = await asyncio.gather(*(_open_meteo(c) for c in chunks))
        return [e for r in results for e in r]
    except UpstreamError:
        pass
    # OpenTopoData's public API allows one request per second.
    out: list[float] = []
    for i, chunk in enumerate(chunks):
        if i:
            await asyncio.sleep(1.1)
        out += await _opentopodata(chunk)
    return out


async def get_horizon(loc: Location) -> Horizon:
    path = _cache_path(loc.latitude, loc.longitude)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return Horizon(raw["azimuths"], raw["altitudes"], raw["observer_elevation_m"])
    except (OSError, ValueError, KeyError):
        pass
    azimuths = list(range(0, 360, AZIMUTH_STEP_DEG))
    points = [(loc.latitude, loc.longitude)]
    for az in azimuths:
        points += [destination(loc.latitude, loc.longitude, az, d) for d in DISTANCES_KM]
    elevations = await _elevations(points)
    ground = elevations[0]
    eye = ground + EYE_HEIGHT_M
    altitudes = []
    for i, _ in enumerate(azimuths):
        ray = elevations[1 + i * len(DISTANCES_KM): 1 + (i + 1) * len(DISTANCES_KM)]
        altitudes.append(round(max(apparent_angle(eye, h, d * 1000) for h, d in zip(ray, DISTANCES_KM)), 2))
    horizon = Horizon([float(a) for a in azimuths], altitudes, ground)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"azimuths": horizon.azimuths, "altitudes": altitudes, "observer_elevation_m": ground}),
                    encoding="utf-8")
    return horizon
