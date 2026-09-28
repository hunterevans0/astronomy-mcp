"""Observer locations: geocoding, timezone lookup, and the saved default location.

Geocoding and coordinate-to-timezone lookups use Open-Meteo (no key). The
default location is stored as JSON in ~/.astronomy-mcp/config.json (override
the directory with the ASTRONOMY_MCP_HOME environment variable).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from astronomy_mcp.http import get_json

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass
class Location:
    latitude: float
    longitude: float
    elevation_m: float = 0.0
    timezone: str = "UTC"
    name: str | None = None
    bortle: int | None = None  # user-supplied sky darkness (1 = pristine, 9 = inner city)

    @property
    def tz(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            return ZoneInfo("UTC")

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def data_dir() -> Path:
    return Path(os.environ.get("ASTRONOMY_MCP_HOME") or Path.home() / ".astronomy-mcp")


def _config_path() -> Path:
    return data_dir() / "config.json"


def load_default() -> Location | None:
    try:
        raw = json.loads(_config_path().read_text(encoding="utf-8"))
        return Location(**raw["default_location"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save_default(loc: Location) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        config = {}
    config["default_location"] = loc.to_dict()
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _describe(result: dict[str, Any]) -> str:
    parts = [result.get("name"), result.get("admin1"), result.get("country")]
    return ", ".join(p for p in parts if p)


async def geocode(query: str, count: int = 5) -> list[dict[str, Any]]:
    """Place name to candidate locations. 'Moab, Utah' searches 'Moab' and ranks Utah first."""
    name, _, qualifier = query.partition(",")
    payload = await get_json(
        GEOCODE_URL,
        {"name": name.strip(), "count": max(count, 10) if qualifier else count, "language": "en"},
        source="Open-Meteo geocoding",
        ttl=86400,
    )
    results = payload.get("results") or []
    qualifier = qualifier.strip().lower()
    if qualifier:
        def matches(r: dict[str, Any]) -> bool:
            fields = (r.get("admin1"), r.get("admin2"), r.get("country"), r.get("country_code"))
            return any(f and qualifier in f.lower() for f in fields)
        results = sorted(results, key=lambda r: not matches(r))
    return [
        {
            "name": _describe(r),
            "latitude": r["latitude"],
            "longitude": r["longitude"],
            "elevation_m": r.get("elevation", 0.0),
            "timezone": r.get("timezone", "UTC"),
            "population": r.get("population"),
        }
        for r in results[:count]
    ]


async def lookup_timezone(latitude: float, longitude: float) -> tuple[str, float]:
    """Timezone name and terrain elevation for a coordinate."""
    payload = await get_json(
        FORECAST_URL,
        {"latitude": round(latitude, 3), "longitude": round(longitude, 3), "timezone": "auto", "forecast_days": 1},
        source="Open-Meteo",
        ttl=86400,
    )
    return payload.get("timezone", "UTC"), payload.get("elevation", 0.0)


async def resolve(
    latitude: float | None = None,
    longitude: float | None = None,
    place: str | None = None,
) -> Location:
    """Pick the observer location: explicit coordinates, then a place name, then the saved default."""
    if (latitude is None) != (longitude is None):
        raise ValueError("Provide both latitude and longitude, or neither.")
    if latitude is not None and longitude is not None:
        default = load_default()
        if default and abs(default.latitude - latitude) < 1e-4 and abs(default.longitude - longitude) < 1e-4:
            return default
        tz, elevation = await lookup_timezone(latitude, longitude)
        return Location(latitude, longitude, elevation, tz, name=f"{latitude:.4f}, {longitude:.4f}")
    if place:
        hits = await geocode(place, count=1)
        if not hits:
            raise ValueError(f"Could not find a place called '{place}'.")
        hit = hits[0]
        return Location(hit["latitude"], hit["longitude"], hit["elevation_m"], hit["timezone"], name=hit["name"])
    default = load_default()
    if default is None:
        raise ValueError(
            "No location given and no default location saved. Pass latitude/longitude or place, "
            "or call set_default_location first."
        )
    return default
