"""Exoplanets from the NASA Exoplanet Archive (TAP, Planetary Systems Composite table), and
transits an amateur can catch tonight.

Transit ephemerides are BJD_TDB: times at the solar-system barycentre. Converting to the
moment the transit is seen from Earth removes the light travel time across Earth's orbit
(up to 8.3 minutes, depending on where the star is) and TDB-UTC (69 s). Uncertainties in
the period accumulate with every orbit, so the predicted time comes with a timing error.
"""

from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime, timedelta
from typing import Any

import astronomy as ae

from astronomy_mcp import sky
from astronomy_mcp.http import UpstreamError, get_json, get_json_file
from astronomy_mcp.location import Location, data_dir

TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
JD_UNIX_EPOCH = 2440587.5
TDB_MINUS_UTC_DAYS = 69.184 / 86400
LIGHT_DAYS_PER_AU = 1 / 173.1446327
SUN_RADIUS_IN_EARTH_RADII = 109.076

DETAIL_FIELDS = (
    "pl_name", "hostname", "sy_snum", "sy_pnum", "discoverymethod", "disc_year", "disc_facility",
    "pl_orbper", "pl_orbsmax", "pl_orbeccen", "pl_rade", "pl_radj", "pl_bmasse", "pl_bmassj", "pl_eqt", "pl_insol",
    "pl_trandep", "pl_trandur", "pl_tranmid", "pl_tranmiderr1", "pl_orbpererr1", "pl_ratror", "tran_flag",
    "st_spectype", "st_teff", "st_rad", "st_mass", "sy_dist", "sy_vmag", "ra", "dec",
)
TRANSIT_FIELDS = ("pl_name", "hostname", "ra", "dec", "sy_vmag", "pl_orbper", "pl_orbpererr1", "pl_tranmid",
                  "pl_tranmiderr1", "pl_trandur", "pl_trandep", "pl_ratror", "pl_rade", "st_rad")
SORTS = {
    "distance": "sy_dist asc", "radius": "pl_rade asc", "mass": "pl_bmasse asc", "newest": "disc_year desc",
    "host_brightness": "sy_vmag asc", "period": "pl_orbper asc",
}


def julian(dt: datetime) -> float:
    return dt.timestamp() / 86400 + JD_UNIX_EPOCH


def from_julian(jd: float) -> datetime:
    return datetime.fromtimestamp((jd - JD_UNIX_EPOCH) * 86400, UTC)


def _quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


async def run_query(adql: str, ttl: float = 3600) -> list[dict[str, Any]]:
    params = {"query": adql, "format": "json"}
    try:
        data = await get_json(TAP, params, source="NASA Exoplanet Archive", ttl=ttl, timeout=90)
    except UpstreamError as exc:
        if "Could not reach" not in str(exc):
            raise
        await asyncio.sleep(2)  # the archive occasionally drops a connection; one retry
        data = await get_json(TAP, params, source="NASA Exoplanet Archive", ttl=ttl, timeout=90)
    return data if isinstance(data, list) else []


def depth_percent(row: dict[str, Any]) -> float | None:
    """Transit depth in percent: as listed, or from the planet-to-star radius ratio."""
    if row.get("pl_trandep"):
        return row["pl_trandep"]
    if row.get("pl_ratror"):
        return 100 * row["pl_ratror"] ** 2
    if row.get("pl_rade") and row.get("st_rad"):
        return 100 * (row["pl_rade"] / (row["st_rad"] * SUN_RADIUS_IN_EARTH_RADII)) ** 2
    return None


def shape_planet(row: dict[str, Any]) -> dict[str, Any]:
    def r(key: str, digits: int) -> float | None:
        value = row.get(key)
        return round(value, digits) if isinstance(value, (int, float)) else None

    out: dict[str, Any] = {
        "name": row.get("pl_name"),
        "host_star": row.get("hostname"),
        "discovered": row.get("disc_year"),
        "method": row.get("discoverymethod"),
        "facility": row.get("disc_facility"),
        "orbital_period_days": r("pl_orbper", 5),
        "semi_major_axis_au": r("pl_orbsmax", 4),
        "eccentricity": r("pl_orbeccen", 3),
        "radius_earth": r("pl_rade", 2),
        "radius_jupiter": r("pl_radj", 3),
        "mass_earth": r("pl_bmasse", 2),
        "mass_jupiter": r("pl_bmassj", 4),
        "equilibrium_temperature_k": r("pl_eqt", 0),
        "insolation_earth": r("pl_insol", 2),
        "transits": bool(row.get("tran_flag")) if row.get("tran_flag") is not None else None,
        "transit_depth_percent": round(d, 3) if (d := depth_percent(row)) and row.get("tran_flag") else None,
        "transit_duration_hours": r("pl_trandur", 2),
        "star": {k: v for k, v in {
            "spectral_type": row.get("st_spectype"), "temperature_k": r("st_teff", 0), "radius_sun": r("st_rad", 2),
            "mass_sun": r("st_mass", 2), "v_magnitude": r("sy_vmag", 2), "stars_in_system": row.get("sy_snum"),
            "planets_in_system": row.get("sy_pnum"),
        }.items() if v is not None},
        "distance_pc": r("sy_dist", 2),
        "distance_ly": round(row["sy_dist"] * 3.26156, 1) if row.get("sy_dist") else None,
        "ra_deg": r("ra", 5),
        "dec_deg": r("dec", 5),
    }
    if row.get("ra") is not None:
        out["constellation"] = sky.constellation(row["ra"], row["dec"])["name"]
    return {k: v for k, v in out.items() if v not in (None, {})}


# ---------------------------------------------------------------- transit timing

def star_vector(ra: float, dec: float) -> tuple[float, float, float]:
    r, d = math.radians(ra), math.radians(dec)
    return math.cos(d) * math.cos(r), math.cos(d) * math.sin(r), math.sin(d)


def bjd_to_utc(bjd_tdb: float, ra: float, dec: float) -> datetime:
    """When light timed at the barycentre reaches Earth: earlier when Earth is on the star's side."""
    guess = from_julian(bjd_tdb)
    earth = ae.HelioVector(ae.Body.Earth, sky.to_time(guess))  # heliocentre is within 0.01 au of the barycentre
    n = star_vector(ra, dec)
    toward = earth.x * n[0] + earth.y * n[1] + earth.z * n[2]
    return from_julian(bjd_tdb - toward * LIGHT_DAYS_PER_AU - TDB_MINUS_UTC_DAYS)


def transits_between(row: dict[str, Any], start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Predicted mid-transit times (UTC) between start and end, with the timing uncertainty."""
    period, t0 = row.get("pl_orbper"), row.get("pl_tranmid")
    if not period or not t0:
        return []
    first = math.ceil((julian(start) - t0) / period - 0.1)
    last = math.floor((julian(end) - t0) / period + 0.1)
    out = []
    for epoch in range(first, last + 1):
        mid = bjd_to_utc(t0 + epoch * period, row["ra"], row["dec"])
        if not start <= mid <= end:
            continue
        sigma_days = math.hypot(row.get("pl_tranmiderr1") or 0, epoch * (row.get("pl_orbpererr1") or 0))
        out.append({"mid": mid, "uncertainty_min": sigma_days * 1440})
    return out


async def transiting_planets(max_vmag: float) -> list[dict[str, Any]]:
    """Transiting planets with an ephemeris around stars brighter than V 13 (cached a day)."""
    data = await get_json_file(
        TAP,
        {"query": f"select {','.join(TRANSIT_FIELDS)} from pscomppars where tran_flag = 1 and sy_vmag <= 13 "
                  "and pl_tranmid is not null and pl_orbper is not null and pl_trandur is not null", "format": "json"},
        data_dir() / "exoplanets" / "transiting.json", source="NASA Exoplanet Archive", max_age=86400, timeout=120,
    )
    return [r for r in (data if isinstance(data, list) else []) if (r.get("sy_vmag") or 99) <= max_vmag]


def transits_tonight(rows: list[dict[str, Any]], loc: Location, n: sky.Night, min_depth: float,
                     min_altitude: float, full_only: bool, max_uncertainty_min: float) -> list[dict[str, Any]]:
    start, end = n.window
    found = []
    for row in rows:
        depth = depth_percent(row)
        if depth is None or depth < min_depth:
            continue
        half = timedelta(hours=row["pl_trandur"] / 2)
        for t in transits_between(row, start - half, end + half):
            ingress, egress = t["mid"] - half, t["mid"] + half
            complete = start <= ingress and egress <= end
            if full_only and not complete:
                continue
            if t["uncertainty_min"] > max_uncertainty_min:
                continue
            times = [max(ingress, start), t["mid"], min(egress, end)]
            track = sky.fast_tracks([(row["ra"], row["dec"])], times, loc)[0]
            if min(a for a, _ in track) < min_altitude:
                continue
            found.append({
                "planet": row["pl_name"],
                "host_v_magnitude": round(row["sy_vmag"], 2),
                "depth_percent": round(depth, 2),
                "depth_mmag": round(-2500 * math.log10(1 - depth / 100), 1),
                "duration_hours": round(row["pl_trandur"], 2),
                "ingress": sky.fmt(ingress, loc),
                "mid_transit": sky.fmt(t["mid"], loc),
                "egress": sky.fmt(egress, loc),
                "timing_uncertainty_min": round(t["uncertainty_min"], 1),
                "whole_transit_in_dark": complete,
                "altitude_deg": {"ingress": round(track[0][0]), "mid": round(track[1][0]), "egress": round(track[2][0])},
                "direction_at_mid": sky.compass(track[1][1]),
                "constellation": sky.constellation(row["ra"], row["dec"])["name"],
                "ra_deg": round(row["ra"], 5),
                "dec_deg": round(row["dec"], 5),
            })
    found.sort(key=lambda f: f["mid_transit"])  # an observing night is planned in time order
    return found


# ---------------------------------------------------------------- lookups

async def lookup(name: str, loc: Location | None, transit_count: int = 3) -> dict[str, Any]:
    fields = ",".join(DETAIL_FIELDS)
    rows = await run_query(f"select {fields} from pscomppars where upper(pl_name) = upper({_quote(name.strip())})")
    system = False
    if not rows:  # a host star name lists its planets
        rows = await run_query(f"select {fields} from pscomppars where upper(hostname) = upper({_quote(name.strip())}) "
                               "order by pl_orbper")
        system = bool(rows)
    if not rows:
        like = await run_query(f"select top 10 pl_name from pscomppars where upper(pl_name) like upper({_quote('%' + name.strip() + '%')})")
        hint = (" Close matches: " + ", ".join(r["pl_name"] for r in like)) if like else ""
        raise ValueError(f"The NASA Exoplanet Archive has no planet or host star called '{name}'.{hint}")
    planets = []
    now = datetime.now(UTC)
    for row in rows:
        planet = shape_planet(row)
        if row.get("tran_flag") and row.get("pl_tranmid") and row.get("pl_orbper"):
            upcoming = transits_between(row, now, now + timedelta(days=max(row["pl_orbper"] * transit_count, 1)))[:transit_count]
            shown = loc or Location(0.0, 0.0)
            planet["next_transits"] = [{"mid_transit": sky.fmt(t["mid"], shown),
                                        "timing_uncertainty_min": round(t["uncertainty_min"], 1)} for t in upcoming]
        planets.append(planet)
    out: dict[str, Any] = {"planets": planets} if system else planets[0]
    out["source"] = "NASA Exoplanet Archive, Planetary Systems Composite Parameters"
    return out


async def search(method: str | None, min_radius: float | None, max_radius: float | None, max_distance_pc: float | None,
                 min_insolation: float | None, max_insolation: float | None, max_host_vmag: float | None,
                 transiting_only: bool, discovered_since: int | None, sort_by: str, limit: int) -> dict[str, Any]:
    where = []
    if method:
        where.append(f"upper(discoverymethod) like upper({_quote('%' + method + '%')})")
    for column, low, high in (("pl_rade", min_radius, max_radius), ("pl_insol", min_insolation, max_insolation)):
        if low is not None:
            where.append(f"{column} >= {float(low)}")
        if high is not None:
            where.append(f"{column} <= {float(high)}")
    if max_distance_pc is not None:
        where.append(f"sy_dist <= {float(max_distance_pc)}")
    if max_host_vmag is not None:
        where.append(f"sy_vmag <= {float(max_host_vmag)}")
    if transiting_only:
        where.append("tran_flag = 1")
    if discovered_since is not None:
        where.append(f"disc_year >= {int(discovered_since)}")
    clause = (" where " + " and ".join(where)) if where else ""
    order = SORTS[sort_by]
    clause += (" and " if clause else " where ") + f"{order.split()[0]} is not null"  # unknowns can't be ranked
    total = (await run_query(f"select count(*) as n from pscomppars{clause}"))[0]["n"]
    rows = await run_query(f"select top {int(limit)} {','.join(DETAIL_FIELDS)} from pscomppars{clause} order by {order}")
    keep = ("name", "host_star", "discovered", "method", "orbital_period_days", "radius_earth", "mass_earth",
            "equilibrium_temperature_k", "insolation_earth", "distance_ly", "constellation", "transit_depth_percent")
    planets = []
    for row in rows:
        full = shape_planet(row)
        planet = {k: full[k] for k in keep if k in full}
        if "v_magnitude" in full.get("star", {}):
            planet["host_v_magnitude"] = full["star"]["v_magnitude"]
        planets.append(planet)
    return {"total_matches": total, "count": len(planets), "sorted_by": sort_by, "planets": planets,
            "note": "Radii and masses are in Earth units; insolation is relative to what Earth receives (Earth = 1). "
                    "Values are the archive's composite best estimates.",
            "source": "NASA Exoplanet Archive, Planetary Systems Composite Parameters"}
