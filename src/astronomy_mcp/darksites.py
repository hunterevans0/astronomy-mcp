"""Find dark observing sites: darkest atlas cells near the observer that have a way in.

The atlas is black over oceans and roadless wilderness too, so every candidate
must have an OpenStreetMap access point nearby (campground, RV park, viewpoint,
picnic area, trailhead, rest area or named parking) found through the Overpass API.
Distances are straight-line, not driving.
"""

from __future__ import annotations

import asyncio
import math
from typing import Any

import httpx

from astronomy_mcp import lightpollution as lp
from astronomy_mcp.http import USER_AGENT, UpstreamError
from astronomy_mcp.sky import compass

# Public Overpass instances are often overloaded; try each in turn.
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
ACCESS_RADIUS_M = 8000
OVERPASS_TIMEOUT_S = 25

ACCESS_KINDS = (
    ("tourism", "camp_site", "campground"),
    ("tourism", "caravan_site", "RV park"),
    ("tourism", "viewpoint", "viewpoint"),
    ("tourism", "picnic_site", "picnic area"),
    ("highway", "trailhead", "trailhead"),
    ("highway", "rest_area", "rest area"),
    ("amenity", "parking", "parking"),
)


def _query(points: list[tuple[float, float]]) -> str:
    blocks = []
    # Point features only: big area relations (national forests, parks) make Overpass very slow.
    for lat, lon in points:
        around = f"around:{ACCESS_RADIUS_M},{lat:.4f},{lon:.4f}"
        blocks.append(f'nwr({around})[tourism~"^(camp_site|caravan_site|viewpoint|picnic_site)$"];')
        blocks.append(f'nwr({around})[highway~"^(trailhead|rest_area)$"];')
        blocks.append(f'nwr({around})[amenity=parking][name][access!~"^(private|no)$"];')
    return "[out:json][timeout:25];(" + "".join(blocks) + ");out center tags;"


def _kind(tags: dict[str, str]) -> str | None:
    for key, value, label in ACCESS_KINDS:
        if tags.get(key) == value:
            return label
    return None


async def _overpass(points: list[tuple[float, float]]) -> list[dict[str, Any]]:
    """Ask every mirror at once and take the first good answer (public instances are often busy)."""
    query = _query(points)
    problems: list[str] = []

    async def ask(client: httpx.AsyncClient, url: str) -> list[dict[str, Any]]:
        resp = await client.post(url, data={"data": query})
        if resp.status_code != 200:
            raise UpstreamError(f"HTTP {resp.status_code}")
        return resp.json().get("elements", [])  # ValueError if an HTML error page came back

    async with httpx.AsyncClient(timeout=OVERPASS_TIMEOUT_S, headers={"User-Agent": USER_AGENT}) as client:
        pending = {asyncio.create_task(ask(client, url)) for url in OVERPASS_URLS}
        try:
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        return task.result()
                    except (httpx.HTTPError, UpstreamError, ValueError) as exc:
                        problems.append(str(exc) or type(exc).__name__)
        finally:
            for task in pending:
                task.cancel()
    raise UpstreamError(f"OpenStreetMap Overpass servers are busy ({'; '.join(problems)}); try again later.")


def _access_points(elements: list[dict[str, Any]], lat: float, lon: float, limit: int = 4) -> list[dict[str, Any]]:
    found = []
    seen: set[str] = set()
    for el in elements:
        tags = el.get("tags", {})
        elat = el.get("lat") or (el.get("center") or {}).get("lat")
        elon = el.get("lon") or (el.get("center") or {}).get("lon")
        kind = _kind(tags)
        if elat is None or kind is None:
            continue
        d = lp.distance_km(lat, lon, elat, elon)
        if d * 1000 > ACCESS_RADIUS_M:
            continue
        name = tags.get("name") or kind
        if name in seen:
            continue
        seen.add(name)
        found.append({"name": name, "kind": kind, "latitude": round(elat, 5), "longitude": round(elon, 5),
                      "distance_from_dark_spot_km": round(d, 1)})
    # Named places first, then closest.
    found.sort(key=lambda a: (a["name"] == a["kind"], a["distance_from_dark_spot_km"]))
    return found[:limit]


async def find(lat: float, lon: float, radius_km: float, count: int, min_separation_km: float) -> dict[str, Any]:
    step = max(2.0, radius_km / 40)
    cells = await lp.scan(lat, lon, radius_km, step)
    if not cells:
        raise ValueError("The light pollution atlas has no data around that location.")
    here = await lp.zone_at(lat, lon)
    candidates = lp.pick_sites(cells, count * 2, min_separation_km)
    try:
        elements = await _overpass([(c.lat, c.lon) for c in candidates])
        access_checked = True
    except UpstreamError:
        elements, access_checked = [], False

    sites = []
    for cell in candidates:
        access = _access_points(elements, cell.lat, cell.lon)
        if access_checked and not access:
            continue  # ocean, lake, or no mapped way in
        bearing_deg = _bearing(lat, lon, cell.lat, cell.lon)
        sites.append({
            "latitude": round(cell.lat, 4),
            "longitude": round(cell.lon, 4),
            "straight_line_km": round(cell.distance_km, 1),
            "direction_from_you": f"{compass(bearing_deg)} ({bearing_deg:.0f}°)",
            **{k: v for k, v in lp.describe_zone(cell.zone).items() if k in (
                "zone", "zone_description", "sky_brightness_mag_arcsec2", "bortle_estimate", "naked_eye_limit")},
            "access_points": access or None,
        })
        if len(sites) == count:
            break
    zones = [c.zone for c in cells]
    return {
        "your_sky": lp.describe_zone(here) if here is not None else None,
        "search_radius_km": radius_km,
        "darkest_zone_in_range": lp.ZONE_NAMES[min(zones)],
        "sites": sites,
        "notes": [
            "Distances are straight-line; check roads, land access and closures before driving.",
            "Sky values are atlas estimates for a clear, moonless sky at the zenith.",
        ] + ([] if access_checked else ["OpenStreetMap was unavailable, so sites are not checked for access and may be on water."]),
        "sources": [f"Light Pollution Atlas {lp.ATLAS_YEAR} (D. Lorenz)", "OpenStreetMap (Overpass API)"],
    }


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360
