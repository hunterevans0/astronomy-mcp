"""The Moon's face: libration, the terminator, and named features.

Orientation uses the IAU rotation model in Astronomy Engine: the selenographic
point under the observer (libration) and under the Sun (which sets the terminator)
are read straight off the Moon's body-fixed frame, so libration is topocentric
when a location is given. Lunar longitudes run east toward Mare Crisium, which is
the celestial-west limb in the sky.

Named features come from the IAU/USGS Gazetteer of Planetary Nomenclature
(https://planetarynames.wr.usgs.gov), downloaded once and cached as a trimmed
JSON under ~/.astronomy-mcp/moon/. Lettered satellite craters are left out.
"""

from __future__ import annotations

import asyncio
import io
import json
import math
import struct
import zipfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import astronomy as ae

from astronomy_mcp import sky
from astronomy_mcp.http import UpstreamError, get_bytes
from astronomy_mcp.location import Location, data_dir

NOMENCLATURE_URL = "https://asc-planetarynames-data.s3.us-west-2.amazonaws.com/MOON_nomenclature_center_pts.zip"
KM_PER_DEGREE = 2 * math.pi * 1737.4 / 360
FEATURE_TYPES = (
    "crater", "mare", "mons", "rima", "vallis", "rupes", "dorsum", "catena", "lacus", "sinus", "palus",
    "promontorium", "oceanus",
)

# Features near the mean limb that libration brings into (or takes out of) view:
# (name, kind, latitude, east longitude, diameter km), from the USGS gazetteer.
LIMB_FEATURES = (
    ("Mare Orientale", "mare", -19.9, -94.7, 294), ("Montes Cordillera", "mons", -19.4, -94.9, 964),
    ("Lacus Veris", "lacus", -16.5, -85.9, 383), ("Lacus Autumni", "lacus", -11.8, -83.2, 196),
    ("Vallis Bouvard", "vallis", -38.4, -82.3, 288), ("Einstein", "crater", 16.6, -88.7, 181),
    ("Bohr", "crater", 12.7, -86.5, 70), ("Vasco da Gama", "crater", 13.8, -83.9, 94),
    ("Hedin", "crater", 2.9, -76.6, 157), ("Struve", "crater", 23.4, -76.7, 164),
    ("Lavoisier", "crater", 38.2, -81.3, 71), ("Repsold", "crater", 51.3, -78.4, 109),
    ("Volta", "crater", 53.9, -84.8, 117), ("Xenophanes", "crater", 57.5, -82.0, 118),
    ("Pythagoras", "crater", 63.7, -63.0, 145), ("Pascal", "crater", 74.4, -70.6, 108),
    ("Hermite", "crater", 86.2, -93.3, 109), ("Byrd", "crater", 85.4, 10.1, 97),
    ("Peary", "crater", 88.6, 24.4, 79), ("Nansen", "crater", 81.2, 95.4, 117),
    ("Petermann", "crater", 74.3, 67.9, 77), ("Mare Humboldtianum", "mare", 56.9, 81.5, 231),
    ("Gauss", "crater", 36.0, 79.1, 171), ("Joliot", "crater", 25.8, 93.4, 173),
    ("Hubble", "crater", 22.3, 86.9, 82), ("Goddard", "crater", 15.2, 89.1, 93),
    ("Mare Marginis", "mare", 12.7, 86.5, 358), ("Neper", "crater", 8.8, 84.6, 144),
    ("Mare Smythii", "mare", -1.7, 87.0, 374), ("Kästner", "crater", -6.9, 78.9, 116),
    ("Hecataeus", "crater", -22.1, 79.7, 134), ("Humboldt", "crater", -27.0, 81.0, 199),
    ("Mare Australe", "mare", -47.8, 92.0, 997), ("Lyot", "crater", -50.5, 84.8, 151),
    ("Boussingault", "crater", -70.2, 53.7, 128), ("Demonax", "crater", -78.1, 59.4, 122),
    ("Scott", "crater", -82.4, 48.5, 108), ("Amundsen", "crater", -84.4, 83.1, 103),
    ("Malapert", "crater", -85.0, 11.4, 72), ("Cabeus", "crater", -85.3, -42.1, 101),
    ("Drygalski", "crater", -79.6, -87.2, 162), ("Le Gentil", "crater", -74.3, -76.0, 125),
    ("Bailly", "crater", -66.8, -68.9, 301), ("Hausen", "crater", -65.1, -88.5, 163),
    ("Pingré", "crater", -58.6, -74.0, 88),
)
FAVOURABLE_GAIN_DEG = 2.0  # tipped at least this far toward us beyond the mean
LIMB_DIRECTIONS = ("north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest")


# ---------------------------------------------------------------- orientation

@dataclass
class Orientation:
    sub_earth_lon: float  # libration in longitude
    sub_earth_lat: float  # libration in latitude
    sub_solar_lon: float
    sub_solar_lat: float

    @property
    def colongitude(self) -> float:
        """Longitude of the sunrise terminator, measured west: 0 at first quarter, 180 at last."""
        return (90 - self.sub_solar_lon) % 360

    def sun_altitude(self, lat: float, lon: float) -> float:
        return elevation(lat, lon, self.sub_solar_lat, self.sub_solar_lon)

    def earth_altitude(self, lat: float, lon: float) -> float:
        """How far inside the limb a spot is: 90 at the centre of the disk, negative on the far side."""
        return elevation(lat, lon, self.sub_earth_lat, self.sub_earth_lon)


def elevation(lat: float, lon: float, sub_lat: float, sub_lon: float) -> float:
    """Altitude at (lat, lon) of a distant body that is overhead at (sub_lat, sub_lon)."""
    lat, sub_lat, dlon = math.radians(lat), math.radians(sub_lat), math.radians(lon - sub_lon)
    s = math.sin(sub_lat) * math.sin(lat) + math.cos(sub_lat) * math.cos(lat) * math.cos(dlon)
    return math.degrees(math.asin(max(-1.0, min(1.0, s))))


def orientation(when: datetime, loc: Location | None = None) -> Orientation:
    t = sky.to_time(when)
    moon = sky.vec(ae.GeoMoon(t))
    sun = sky.vec(ae.GeoVector(ae.Body.Sun, t, False))
    eye = sky.vec(ae.ObserverVector(t, sky.observer(loc), False)) if loc else (0.0, 0.0, 0.0)
    axis = ae.RotationAxis(ae.Body.Moon, t)
    north = sky.vec(axis.north)
    earth_lon, earth_lat = sky.body_lon_lat(north, axis.spin, tuple(e - m for e, m in zip(eye, moon)))
    sun_lon, sun_lat = sky.body_lon_lat(north, axis.spin, tuple(s - m for s, m in zip(sun, moon)))
    return Orientation(earth_lon, earth_lat, sun_lon, sun_lat)


def _moon_summary(when: datetime, loc: Location | None, o: Orientation) -> dict[str, Any]:
    phase = sky.moon_phase(when)
    out = {
        "phase": phase["phase"],
        "illuminated_percent": phase["illuminated_percent"],
        "age_days": phase["age_days"],
        "sun_colongitude_deg": round(o.colongitude, 1),
    }
    if loc:
        h = sky.horizontal(sky.Target("Moon", ae.Body.Moon), when, loc)
        out |= {"altitude_deg": round(h["altitude_deg"], 1), "direction": sky.compass(h["azimuth_deg"]),
                "above_horizon": h["altitude_deg"] > 0}
    return out


# ---------------------------------------------------------------- libration

def libration(when: datetime, loc: Location | None) -> dict[str, Any]:
    """Libration angles, which limb is tipped toward the observer, and how the limb features fare."""
    o = orientation(when, loc)
    shown = loc or Location(0.0, 0.0)
    total = 90 - elevation(0.0, 0.0, o.sub_earth_lat, o.sub_earth_lon)
    bearing = math.degrees(math.atan2(o.sub_earth_lon, o.sub_earth_lat)) % 360
    limb = LIMB_DIRECTIONS[round(bearing / 45) % 8]
    features = []
    for name, kind, lat, lon, diameter in LIMB_FEATURES:
        inside = o.earth_altitude(lat, lon)
        gain = inside - elevation(lat, lon, 0.0, 0.0)
        sun = o.sun_altitude(lat, lon)
        features.append({
            "name": name,
            "type": kind,
            "latitude": lat,
            "longitude": lon,
            "diameter_km": diameter,
            "degrees_inside_limb": round(inside, 1),
            "libration_gain_deg": round(gain, 1),
            "sunlit": sun > 0,
            "view": (
                "beyond the limb" if inside <= 0
                else "in darkness" if sun <= 0
                else "favourable" if gain >= FAVOURABLE_GAIN_DEG
                else "unfavourable" if gain <= -FAVOURABLE_GAIN_DEG
                else "average"
            ),
        })
    features.sort(key=lambda f: f["libration_gain_deg"], reverse=True)
    return {
        "time": sky.fmt(when, shown),
        "libration_longitude_deg": round(o.sub_earth_lon, 2),
        "libration_latitude_deg": round(o.sub_earth_lat, 2),
        "total_libration_deg": round(total, 2),
        "favoured_limb": limb if total >= 1 else "none (nearly face-on)",
        "viewpoint": "topocentric" if loc else "geocentric (a location shifts this by up to 1°)",
        "moon": _moon_summary(when, loc, o),
        "well_placed_now": [f["name"] for f in features if f["view"] == "favourable"],
        "limb_features": features,
        "note": "Limb directions are lunar: east is the Mare Crisium side (celestial west in the sky), north "
                "is the Plato side. Positive longitude libration exposes the east limb, positive latitude the "
                "north. A feature needs to be both tipped toward us and sunlit.",
    }


# ---------------------------------------------------------------- named features

def parse_dbf(data: bytes) -> list[dict[str, str]]:
    """Rows of a dBASE table (the attribute file of a shapefile) as dicts of stripped strings."""
    count, header_len, record_len = struct.unpack("<IHH", data[4:12])
    fields, offset = [], 32
    while data[offset] != 0x0D:
        fields.append((data[offset:offset + 11].split(b"\0")[0].decode("ascii"), data[offset + 16]))
        offset += 32
    rows = []
    for i in range(count):
        record = data[header_len + i * record_len: header_len + (i + 1) * record_len]
        if record[:1] == b"*":  # deleted
            continue
        row, pos = {}, 1
        for name, length in fields:
            row[name] = record[pos:pos + length].decode("utf-8", "replace").strip()
            pos += length
        rows.append(row)
    return rows


def shape_features(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Gazetteer rows -> compact features with east longitude in -180..180; satellite craters dropped."""
    features = []
    for row in rows:
        kind = row["type"].split(",")[0].strip().lower()
        if kind not in FEATURE_TYPES:
            continue
        features.append({
            "name": row["name"],
            "type": kind,
            "latitude": round(float(row["center_lat"]), 2),
            "longitude": round(sky.wrap180(float(row["center_lon"])), 2),
            "diameter_km": round(float(row["diameter"]), 1),
        })
    return features


_features: list[dict[str, Any]] | None = None
_lock = asyncio.Lock()


async def get_features() -> list[dict[str, Any]]:
    """Named lunar features, from memory, the on-disk cache, or a one-time 24 MB download."""
    global _features
    async with _lock:
        if _features is None:
            path = data_dir() / "moon" / "features.json"
            try:
                _features = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                raw = await get_bytes(NOMENCLATURE_URL, source="USGS planetary nomenclature", timeout=180)
                try:
                    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                        table = next(n for n in archive.namelist() if n.lower().endswith(".dbf"))
                        _features = shape_features(parse_dbf(archive.read(table)))
                except (zipfile.BadZipFile, StopIteration, KeyError, struct.error) as exc:
                    raise UpstreamError(f"USGS planetary nomenclature download was not the expected shapefile: {exc}") from exc
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(_features, ensure_ascii=False), encoding="utf-8")
        return _features


# ---------------------------------------------------------------- terminator

def terminator_features(
    features: list[dict[str, Any]],
    o: Orientation,
    min_diameter_km: float,
    max_sun_altitude_deg: float,
    types: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Features in low sunlight on the Earth-facing side, largest first.

    A feature counts from the moment the Sun reaches its near rim (centre still in the dark by
    the feature's angular radius) until the Sun is `max_sun_altitude_deg` up at its centre.
    """
    found = []
    for f in features:
        if f["diameter_km"] < min_diameter_km or (types and f["type"] not in types):
            continue
        inside = o.earth_altitude(f["latitude"], f["longitude"])
        if inside <= 0:
            continue
        sun = o.sun_altitude(f["latitude"], f["longitude"])
        if not -f["diameter_km"] / 2 / KM_PER_DEGREE <= sun <= max_sun_altitude_deg:
            continue
        found.append({
            **f,
            "sun_altitude_deg": round(sun, 1) + 0.0,  # no "-0.0"
            "lighting": "sunrise" if sky.wrap180(f["longitude"] - o.sub_solar_lon) < 0 else "sunset",
            "near_limb": inside < 15 or None,
        })
    found.sort(key=lambda f: f["diameter_km"], reverse=True)
    return [{k: v for k, v in f.items() if v is not None} for f in found]


def terminator(
    features: list[dict[str, Any]],
    when: datetime,
    loc: Location | None,
    min_diameter_km: float = 20.0,
    max_sun_altitude_deg: float = 8.0,
    types: set[str] | None = None,
    limit: int = 30,
) -> dict[str, Any]:
    o = orientation(when, loc)
    shown = loc or Location(0.0, 0.0)
    found = terminator_features(features, o, min_diameter_km, max_sun_altitude_deg, types)
    sunrise_lon = sky.wrap180(-o.colongitude)
    edges = {"sunrise": sunrise_lon, "sunset": sky.wrap180(sunrise_lon + 180)}
    facing = {name: lon for name, lon in edges.items() if o.earth_altitude(0.0, lon) > 0}
    out = {
        "time": sky.fmt(when, shown),
        "moon": _moon_summary(when, loc, o),
        "terminator": {
            "facing_earth": " and ".join(facing) or None,
            **{f"{name}_longitude_deg": round(lon, 1) for name, lon in facing.items()},
        },
        "total_matches": len(found),
        "count": min(len(found), limit),
        "features": found[:limit],
        "note": "Longitudes are lunar: positive east, toward Mare Crisium. Low Sun throws long shadows, so these "
                "features show the most relief; the terminator moves about 0.5° of longitude per hour.",
        "source": "IAU/USGS Gazetteer of Planetary Nomenclature",
    }
    out["terminator"] = {k: v for k, v in out["terminator"].items() if v is not None}
    return out
