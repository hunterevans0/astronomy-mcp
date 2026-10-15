"""Gravitational-wave events: confirmed catalog events (GWOSC) and public alerts (GraceDB).

GWOSC's GWTC listing carries the parameter estimates (masses, distance) of confirmed events.
GraceDB holds the low-latency public alerts; each significant superevent has a small
classification file (probability of binary black hole, neutron-star merger, or noise) from
the pipeline that found it.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from astronomy_mcp.http import UpstreamError, get_json, get_json_file
from astronomy_mcp.location import data_dir

GWOSC_CATALOG = "https://gwosc.org/eventapi/json/GWTC/"
GRACEDB = "https://gracedb.ligo.org/api"
GPS_EPOCH = datetime(1980, 1, 6, tzinfo=UTC)
# GPS - UTC leap seconds, from the start of each step (GPS seconds).
LEAP_SECONDS = ((1167264017, 18), (1119744016, 17), (1025136015, 16), (0, 15))
# CBC alerts are public when the false-alarm rate is below about one per month.
SIGNIFICANT_FAR_HZ = 1 / (30 * 86400)
SOLAR_MASS_LIMIT_FOR_NS = 3.0
SECONDS_PER_YEAR = 365.25 * 86400
SORTS = ("date", "distance", "mass", "snr")
CLASS_NAMES = {"BBH": "binary black hole", "BNS": "binary neutron star", "NSBH": "neutron star + black hole",
               "Terrestrial": "noise (terrestrial)"}


def gps_to_utc(gps: float) -> datetime:
    leap = next(offset for start, offset in LEAP_SECONDS if gps >= start)
    return GPS_EPOCH + timedelta(seconds=gps - leap)


def far_text(far_hz: float | None) -> str | None:
    """A false-alarm rate as 'one per N years'."""
    if not far_hz:
        return None
    years = 1 / (far_hz * SECONDS_PER_YEAR)
    if years >= 1e6:
        return f"one per {years:.1e} years"
    if years >= 1:
        return f"one per {years:,.0f} years"
    return f"one per {years * 365.25:,.0f} days"


# ---------------------------------------------------------------- confirmed events (GWOSC)

def _value(event: dict[str, Any], key: str, digits: int = 1) -> dict[str, Any] | float | None:
    value = event.get(key)
    if value is None:
        return None
    lower, upper = event.get(f"{key}_lower"), event.get(f"{key}_upper")
    if lower is None or upper is None:
        return round(value, digits)
    return {"value": round(value, digits), "minus": round(abs(lower), digits), "plus": round(upper, digits)}


def _number(v: Any) -> float | None:
    return v["value"] if isinstance(v, dict) else v


def shape_event(name: str, e: dict[str, Any]) -> dict[str, Any]:
    m1, m2 = _value(e, "mass_1_source"), _value(e, "mass_2_source")
    lighter = _number(m2)
    if lighter is None:
        kind = None
    elif lighter < SOLAR_MASS_LIMIT_FOR_NS and (_number(m1) or 0) < SOLAR_MASS_LIMIT_FOR_NS:
        kind = "binary neutron star"
    elif lighter < SOLAR_MASS_LIMIT_FOR_NS:
        kind = "neutron star + black hole (or a light compact object)"
    else:
        kind = "binary black hole"
    distance = _value(e, "luminosity_distance", 0)
    out = {
        "name": e.get("commonName") or name,
        "time_utc": gps_to_utc(e["GPS"]).isoformat(timespec="seconds") if e.get("GPS") else None,
        "catalog": e.get("catalog.shortName"),
        "likely_source": kind,
        "mass_1_solar": m1,
        "mass_2_solar": m2,
        "final_mass_solar": _value(e, "final_mass_source"),
        "chirp_mass_solar": _value(e, "chirp_mass_source", 2),
        "distance_mpc": distance,
        "distance_million_ly": round(_number(distance) * 3.2616) if _number(distance) else None,
        "redshift": _value(e, "redshift", 3),
        "network_snr": _value(e, "network_matched_filter_snr"),
        "probability_astrophysical": round(e["p_astro"], 3) if e.get("p_astro") is not None else None,
        "false_alarm_rate": far_text(e.get("far")),
        "url": f"https://gwosc.org/eventapi/html/{e['catalog.shortName']}/{e.get('commonName')}/" if e.get("catalog.shortName") else None,
    }
    return {k: v for k, v in out.items() if v is not None}


async def catalog_events() -> list[dict[str, Any]]:
    payload = await get_json_file(GWOSC_CATALOG, None, data_dir() / "gw" / "gwtc.json", source="GWOSC", max_age=86400,
                                  timeout=120)
    # The listing has one entry per event version; keep the newest version of each event.
    newest: dict[str, tuple[int, str, dict[str, Any]]] = {}
    for key, event in (payload.get("events") or {}).items():
        name = event.get("commonName") or key
        version = event.get("version") or 0
        if name not in newest or version > newest[name][0]:
            newest[name] = (version, key, event)
    return [shape_event(key, event) for _, key, event in newest.values()]


async def confirmed(event: str | None, sort_by: str, limit: int, min_probability: float) -> dict[str, Any]:
    events = await catalog_events()
    if event:
        wanted = event.strip().upper()
        matches = [e for e in events if e["name"].upper() == wanted or e["name"].upper().startswith(wanted)]
        if not matches:
            raise ValueError(f"GWOSC's catalog has no event named '{event}'. Names look like GW150914 or GW190521_030229.")
        return {"count": len(matches), "events": matches[:limit], "source": "GWOSC event catalog (GWTC)"}
    events = [e for e in events if e.get("probability_astrophysical", 1) >= min_probability]
    keys = {
        "date": lambda e: e.get("time_utc", ""),
        "distance": lambda e: -(_number(e.get("distance_mpc")) or 1e9),
        "mass": lambda e: _number(e.get("final_mass_solar")) or (_number(e.get("mass_1_solar")) or 0) + (_number(e.get("mass_2_solar")) or 0),
        "snr": lambda e: _number(e.get("network_snr")) or 0,
    }
    events.sort(key=keys[sort_by], reverse=True)
    return {
        "total": len(events),
        "count": min(limit, len(events)),
        "sorted_by": sort_by,
        "events": events[:limit],
        "source": "GWOSC event catalog (GWTC)",
        "note": "Masses are in the source frame, in solar masses, with 90% credible ranges where given. The source "
                "type is inferred from the masses (under 3 solar masses taken as a neutron star).",
    }


# ---------------------------------------------------------------- public alerts (GraceDB)

async def _classification(superevent: dict[str, Any]) -> dict[str, Any]:
    sid = superevent["superevent_id"]
    pipeline = (superevent.get("preferred_event_data") or {}).get("pipeline", "")

    async def file(name: str) -> dict[str, Any] | None:
        try:
            return await get_json(f"{GRACEDB}/superevents/{sid}/files/{name}", source="GraceDB", ttl=86400)
        except UpstreamError:
            return None

    p_astro, em_bright = await asyncio.gather(file(f"{pipeline}.p_astro.json"), file("em_bright.json"))
    out: dict[str, Any] = {}
    if isinstance(p_astro, dict) and p_astro:
        ranked = sorted(p_astro.items(), key=lambda kv: -kv[1])
        out["classification"] = {CLASS_NAMES.get(k, k): round(v, 3) for k, v in ranked if v >= 0.001}
        out["most_likely"] = CLASS_NAMES.get(ranked[0][0], ranked[0][0])
    if isinstance(em_bright, dict) and em_bright:
        out["probability_has_neutron_star"] = round(em_bright.get("HasNS", 0), 3)
        out["probability_has_remnant"] = round(em_bright.get("HasRemnant", 0), 3)
    return out


async def recent_alerts(limit: int, include_retracted: bool) -> dict[str, Any]:
    payload = await get_json(
        f"{GRACEDB}/superevents/",
        {"query": f"category: Production far < {SIGNIFICANT_FAR_HZ:.3e}", "orderby": "-t_0", "count": limit * 2,
         "format": "json"},
        source="GraceDB", ttl=600, timeout=60,
    )
    superevents = payload.get("superevents") or []
    chosen = []
    for s in superevents:
        retracted = "ADVNO" in (s.get("labels") or [])
        if retracted and not include_retracted:
            continue
        chosen.append((s, retracted))
        if len(chosen) >= limit:
            break
    gate = asyncio.Semaphore(4)

    async def classify(s: dict[str, Any]) -> dict[str, Any]:
        async with gate:
            return await _classification(s)

    classes = await asyncio.gather(*(classify(s) for s, _ in chosen))
    alerts = []
    for (s, retracted), cls in zip(chosen, classes):
        pref = s.get("preferred_event_data") or {}
        alerts.append({k: v for k, v in {
            "id": s["superevent_id"],
            "time_utc": gps_to_utc(s["t_0"]).isoformat(timespec="seconds") if s.get("t_0") else None,
            "retracted": retracted or None,
            "false_alarm_rate": far_text(s.get("far")),
            "detectors": pref.get("instruments"),
            "search": " ".join(x for x in (pref.get("group"), pref.get("search")) if x) or None,
            **cls,
            "url": f"https://gracedb.ligo.org/superevents/{s['superevent_id']}/view/",
        }.items() if v is not None})
    out: dict[str, Any] = {"count": len(alerts), "alerts": alerts, "source": "GraceDB public superevents (LIGO-Virgo-KAGRA)"}
    if alerts and alerts[0].get("time_utc"):
        latest = datetime.fromisoformat(alerts[0]["time_utc"])
        quiet_days = (datetime.now(UTC) - latest).days
        if quiet_days > 30:
            out["note"] = (f"No significant public alert in the last {quiet_days} days (latest {latest.date()}); the "
                           "detectors issue alerts only during observing runs.")
    out.setdefault("note", "Low-latency alerts: classifications can change, and some alerts are later retracted.")
    return out


async def alert(superevent_id: str) -> dict[str, Any]:
    """One public alert by its GraceDB id (e.g. S251117dq)."""
    sid = superevent_id.strip()
    try:
        s = await get_json(f"{GRACEDB}/superevents/{sid}/", {"format": "json"}, source="GraceDB", ttl=600)
    except UpstreamError as exc:
        if "404" in str(exc):
            raise ValueError(f"GraceDB has no public superevent '{sid}'.") from exc
        raise
    pref = s.get("preferred_event_data") or {}
    out = {
        "id": s["superevent_id"],
        "time_utc": gps_to_utc(s["t_0"]).isoformat(timespec="seconds") if s.get("t_0") else None,
        "retracted": "ADVNO" in (s.get("labels") or []) or None,
        "significant": (s.get("far") or 1) < SIGNIFICANT_FAR_HZ,
        "false_alarm_rate": far_text(s.get("far")),
        "detectors": pref.get("instruments"),
        "search": " ".join(x for x in (pref.get("group"), pref.get("search")) if x) or None,
        "confirmed_as": s.get("gw_id"),
        **await _classification(s),
        "url": f"https://gracedb.ligo.org/superevents/{s['superevent_id']}/view/",
    }
    return {k: v for k, v in out.items() if v is not None}
