"""Space weather (NOAA SWPC) and rocket launches (The Space Devs Launch Library 2)."""

from __future__ import annotations

import math
from typing import Any

from astronomy_mcp.http import get_json
from astronomy_mcp.location import Location
from astronomy_mcp.sky import fmt, parse_time

SWPC = "https://services.swpc.noaa.gov"
LL2_UPCOMING = "https://ll.thespacedevs.com/2.3.0/launches/upcoming/"

KP_LEVELS = (
    (0, "quiet"), (3, "unsettled"), (4, "active"), (5, "G1 minor storm"), (6, "G2 moderate storm"),
    (7, "G3 strong storm"), (8, "G4 severe storm"), (9, "G5 extreme storm"),
)
# Rough equatorward edge of visible aurora (geomagnetic latitude) for a given Kp.
KP_VIEW_LATITUDE = {0: 66, 1: 64, 2: 62, 3: 60, 4: 58, 5: 56, 6: 54, 7: 52, 8: 50, 9: 48}


def kp_level(kp: float) -> str:
    label = KP_LEVELS[0][1]
    for threshold, name in KP_LEVELS:
        if kp >= threshold:
            label = name
    return label


def aurora_at(coordinates: list[list[float]], latitude: float, longitude: float) -> dict[str, int]:
    """OVATION probability at the nearest grid cell, and the max within 10° poleward
    (aurora is often visible low on the horizon from outside the oval)."""
    lon = round(longitude) % 360
    lat = round(latitude)
    grid = {(int(c[0]), int(c[1])): int(c[2]) for c in coordinates}
    sign = 1 if latitude >= 0 else -1
    poleward = [
        grid.get(((lon + dl) % 360, lat + sign * d), 0)
        for d in range(0, 11)
        for dl in (-2, -1, 0, 1, 2)
        if abs(lat + sign * d) <= 90
    ]
    return {"overhead_probability_pct": grid.get((lon, lat), 0), "max_within_10deg_poleward_pct": max(poleward, default=0)}


async def space_weather(loc: Location | None) -> dict[str, Any]:
    observed = await get_json(f"{SWPC}/products/noaa-planetary-k-index.json", source="NOAA SWPC", ttl=600)
    forecast = await get_json(f"{SWPC}/products/noaa-planetary-k-index-forecast.json", source="NOAA SWPC", ttl=600)
    latest = observed[-1]
    kp_now = float(latest["Kp"])
    predicted = [row for row in forecast if row.get("observed") == "predicted"]
    peak = max(predicted, key=lambda r: float(r["kp"]), default=None)

    def when(stamp: str) -> str:
        return fmt(parse_time(stamp + "Z", loc), loc) if loc else stamp + "Z"

    out: dict[str, Any] = {
        "kp_latest": {"value": kp_now, "level": kp_level(kp_now), "time": when(latest["time_tag"])},
        "kp_last_24h_max": max(float(r["Kp"]) for r in observed[-8:]),
        "kp_forecast_peak": (
            {"value": float(peak["kp"]), "level": kp_level(float(peak["kp"])), "time": when(peak["time_tag"]),
             "noaa_scale": peak.get("noaa_scale")} if peak else None
        ),
        "kp_forecast": [
            {"time": when(r["time_tag"]), "kp": float(r["kp"])} for r in predicted
        ],
        "aurora_rule_of_thumb": (
            f"At the forecast peak (Kp {float(peak['kp']):.0f}) aurora may reach roughly "
            f"{KP_VIEW_LATITUDE[min(9, round(float(peak['kp'])))]}° geomagnetic latitude."
            if peak else None
        ),
    }
    if loc:
        ovation = await get_json(f"{SWPC}/json/ovation_aurora_latest.json", source="NOAA SWPC OVATION", ttl=600)
        out["aurora_at_location"] = {
            **aurora_at(ovation["coordinates"], loc.latitude, loc.longitude),
            "forecast_time": when(ovation["Forecast Time"].rstrip("Z")),
            "note": "OVATION 30-90 minute nowcast. A few percent overhead plus a higher value poleward can still mean a low glow on the horizon.",
        }
    return {k: v for k, v in out.items() if v is not None}


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def _shape_launch(r: dict[str, Any], loc: Location | None) -> dict[str, Any]:
    mission = r.get("mission") or {}
    pad = r.get("pad") or {}
    desc = mission.get("description") or ""
    out: dict[str, Any] = {
        "name": r["name"],
        "status": (r.get("status") or {}).get("name"),
        "net_utc": r.get("net"),
        "net_local": fmt(parse_time(r["net"], loc), loc) if loc and r.get("net") else None,
        "net_precision": (r.get("net_precision") or {}).get("name"),
        "window_utc": {"start": r.get("window_start"), "end": r.get("window_end")},
        "provider": (r.get("launch_service_provider") or {}).get("name"),
        "rocket": ((r.get("rocket") or {}).get("configuration") or {}).get("full_name"),
        "mission": mission.get("name"),
        "mission_type": mission.get("type"),
        "orbit": (mission.get("orbit") or {}).get("name"),
        "description": desc[:300] + ("..." if len(desc) > 300 else "") or None,
        "pad": pad.get("name"),
        "location": (pad.get("location") or {}).get("name"),
        "weather_go_probability_pct": r.get("probability"),
        "webcast_live": r.get("webcast_live") or None,
        "webcasts": [v["url"] for v in mission.get("vid_urls") or [] if v.get("url")][:2] or None,
    }
    if loc and pad.get("latitude") is not None:
        out["distance_from_you_km"] = round(
            _distance_km(loc.latitude, loc.longitude, float(pad["latitude"]), float(pad["longitude"]))
        )
    return {k: v for k, v in out.items() if v not in (None, "", [])}


async def upcoming_launches(limit: int, search: str | None, loc: Location | None, max_distance_km: float | None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": 50 if max_distance_km else limit, "mode": "normal", "hide_recent_previous": "true"}
    if search:
        params["search"] = search
    # LL2 allows 15 requests/hour without a key, so cache for 15 minutes.
    payload = await get_json(LL2_UPCOMING, params, source="Launch Library 2", ttl=900)
    launches = [_shape_launch(r, loc) for r in payload.get("results", [])]
    if max_distance_km is not None:
        launches = [l for l in launches if l.get("distance_from_you_km", math.inf) <= max_distance_km]
    return launches[:limit]
