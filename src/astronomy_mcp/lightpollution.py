"""Artificial sky brightness from David Lorenz's Light Pollution Atlas (2025, VIIRS-based).

https://djlorenz.github.io/astronomy/lp/ publishes the atlas as colour-coded
1024 px web-mercator tiles. Each of its 15 colours is one light-pollution zone,
a band of the Light Pollution Index (artificial / natural brightness, natural =
22.0 mag/arcsec^2). We fetch tiles at zoom 6 (~0.0055 deg per pixel, finer than
the atlas's 1/120 deg data), cache them on disk, and read single pixels.

Values are modelled zenith brightness for a clear, moonless sky, not measurements.
"""

from __future__ import annotations

import asyncio
import io
import math
from dataclasses import dataclass
from typing import Any

from PIL import Image

from astronomy_mcp.conditions import bortle_from_sqm, nelm_from_sqm
from astronomy_mcp.http import UpstreamError, get_bytes
from astronomy_mcp.location import data_dir

ATLAS_YEAR = 2025
TILE_URL = "https://djlorenz.github.io/astronomy/image_tiles/tiles{year}/tile_{z}_{x}_{y}.png"
ZOOM = 6
TILE_PX = 1024
NATURAL_SQM = 22.0
MAX_LATITUDE = 84.0

# zone, RGB on the atlas, Light Pollution Index range (artificial / natural)
ZONES: tuple[tuple[str, tuple[int, int, int], float, float], ...] = (
    ("0", (0, 0, 0), 0.0, 0.01),
    ("1a", (34, 34, 34), 0.01, 0.06),
    ("1b", (66, 66, 66), 0.06, 0.11),
    ("2a", (20, 47, 114), 0.11, 0.19),
    ("2b", (33, 84, 216), 0.19, 0.33),
    ("3a", (15, 87, 20), 0.33, 0.58),
    ("3b", (31, 161, 42), 0.58, 1.00),
    ("4a", (110, 100, 30), 1.00, 1.73),
    ("4b", (184, 166, 37), 1.73, 3.00),
    ("5a", (191, 100, 30), 3.00, 5.20),
    ("5b", (253, 150, 80), 5.20, 9.00),
    ("6a", (251, 90, 73), 9.00, 15.59),
    ("6b", (251, 153, 138), 15.59, 27.00),
    ("7a", (160, 160, 160), 27.00, 46.77),
    ("7b", (242, 242, 242), 46.77, 150.0),
)
ZONE_COLOURS = {rgb: i for i, (_, rgb, _, _) in enumerate(ZONES)}
ZONE_NAMES = [z[0] for z in ZONES]
ZONE_DESCRIPTIONS = {
    "0": "pristine", "1": "excellent dark site", "2": "dark rural", "3": "rural",
    "4": "rural/suburban transition", "5": "suburban", "6": "bright suburban", "7": "city",
}


def sqm_for_lpi(lpi: float) -> float:
    return NATURAL_SQM - 2.5 * math.log10(1 + lpi)


def zone_lpi(index: int) -> float:
    """Representative LPI for a zone: the geometric middle of its band."""
    _, _, low, high = ZONES[index]
    return math.sqrt(max(low, 0.002) * high)


def describe_zone(index: int) -> dict[str, Any]:
    name, _, low, high = ZONES[index]
    lpi = zone_lpi(index)
    sqm = sqm_for_lpi(lpi)
    return {
        "zone": name,
        "zone_description": ZONE_DESCRIPTIONS[name[0]],
        "light_pollution_index": round(lpi, 3),
        "light_pollution_index_range": [low, high if index < len(ZONES) - 1 else None],
        "artificial_vs_natural": f"artificial light is {lpi:.2g}x the natural sky brightness",
        "sky_brightness_mag_arcsec2": round(sqm, 2),
        "sky_brightness_range": [round(sqm_for_lpi(high), 2), round(sqm_for_lpi(low), 2)],
        "bortle_estimate": bortle_from_sqm(sqm),
        "naked_eye_limit": round(nelm_from_sqm(sqm), 1),
    }


# ---------------------------------------------------------------- tiles

def _tile_coords(lat: float, lon: float) -> tuple[int, int, int, int]:
    """(tile x, tile y, pixel x, pixel y) at ZOOM for a coordinate."""
    n = 2**ZOOM
    lat = max(-MAX_LATITUDE, min(MAX_LATITUDE, lat))
    fx = (lon + 180.0) / 360.0 * n
    phi = math.radians(lat)
    fy = (1 - math.log(math.tan(phi) + 1 / math.cos(phi)) / math.pi) / 2 * n
    tx, ty = int(fx) % n, int(fy)
    return tx, ty, min(int((fx % 1) * TILE_PX), TILE_PX - 1), min(int((fy % 1) * TILE_PX), TILE_PX - 1)


_images: dict[tuple[int, int], Image.Image | None] = {}
_locks: dict[tuple[int, int], asyncio.Lock] = {}


async def _tile(tx: int, ty: int) -> Image.Image | None:
    """Decoded tile, from memory, disk, or the atlas site. None where the atlas has no data."""
    key = (tx, ty)
    if key in _images:
        return _images[key]
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        if key in _images:
            return _images[key]
        path = data_dir() / "lightpollution" / str(ATLAS_YEAR) / f"tile_{ZOOM}_{tx}_{ty}.png"
        missing = path.with_suffix(".missing")
        if missing.exists():
            image = None
        else:
            if not path.exists():
                try:
                    content = await get_bytes(
                        TILE_URL.format(year=ATLAS_YEAR, z=ZOOM, x=tx, y=ty), source="Light Pollution Atlas"
                    )
                except UpstreamError as exc:
                    if "HTTP 404" in str(exc):  # ocean or outside coverage
                        missing.parent.mkdir(parents=True, exist_ok=True)
                        missing.touch()
                        _images[key] = None
                        return None
                    raise
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            image = Image.open(io.BytesIO(path.read_bytes())).convert("RGB")
        if len(_images) > 32:
            _images.pop(next(iter(_images)))
        _images[key] = image
        return image


def _zone_of(rgb: tuple[int, int, int]) -> int:
    if rgb in ZONE_COLOURS:
        return ZONE_COLOURS[rgb]
    # Anti-aliased or unexpected pixel: nearest palette colour.
    return min(ZONE_COLOURS.items(), key=lambda kv: sum((a - b) ** 2 for a, b in zip(kv[0], rgb)))[1]


async def zone_at(lat: float, lon: float) -> int | None:
    if abs(lat) > MAX_LATITUDE:
        return None
    tx, ty, px, py = _tile_coords(lat, lon)
    image = await _tile(tx, ty)
    if image is None:
        return 0
    return _zone_of(image.getpixel((px, py)))


async def sky_brightness(lat: float, lon: float) -> dict[str, Any]:
    zone = await zone_at(lat, lon)
    if zone is None:
        raise ValueError("The light pollution atlas does not cover latitudes beyond ±84°.")
    return {**describe_zone(zone), "source": f"Light Pollution Atlas {ATLAS_YEAR} (D. Lorenz, VIIRS data)"}


# ---------------------------------------------------------------- dark-site search

@dataclass
class Cell:
    lat: float
    lon: float
    zone: int
    distance_km: float


def destination(lat: float, lon: float, bearing_deg: float, distance_km: float) -> tuple[float, float]:
    """Point reached travelling a great-circle distance along a bearing."""
    r = 6371.0
    d = distance_km / r
    p1, l1, b = math.radians(lat), math.radians(lon), math.radians(bearing_deg)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), (math.degrees(l2) + 540) % 360 - 180


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


async def scan(lat: float, lon: float, radius_km: float, step_km: float) -> list[Cell]:
    """Sample the atlas on a square grid clipped to a circle around a point."""
    cells_per_side = int(radius_km // step_km)
    points = []
    dlat = step_km / 111.2
    for i in range(-cells_per_side, cells_per_side + 1):
        plat = lat + i * dlat
        if abs(plat) > MAX_LATITUDE:
            continue
        dlon = step_km / (111.2 * max(math.cos(math.radians(plat)), 0.05))
        for j in range(-cells_per_side, cells_per_side + 1):
            plon = (lon + j * dlon + 540) % 360 - 180
            d = distance_km(lat, lon, plat, plon)
            if d <= radius_km:
                points.append((plat, plon, d))
    tiles = {_tile_coords(p[0], p[1])[:2] for p in points}
    await asyncio.gather(*(_tile(tx, ty) for tx, ty in tiles))
    cells = []
    for plat, plon, d in points:
        zone = await zone_at(plat, plon)
        if zone is not None:
            cells.append(Cell(plat, plon, zone, d))
    return cells


def pick_sites(cells: list[Cell], count: int, min_separation_km: float) -> list[Cell]:
    """Darkest cells first, nearest first within a zone, spread at least min_separation_km apart."""
    picked: list[Cell] = []
    for cell in sorted(cells, key=lambda c: (c.zone, c.distance_km)):
        if all(distance_km(cell.lat, cell.lon, p.lat, p.lon) >= min_separation_km for p in picked):
            picked.append(cell)
            if len(picked) == count:
                break
    return picked
