"""Double stars from the Washington Double Star catalog (WDS, via VizieR TAP), and whether a
given telescope can split them.

Splitting is judged with a rule of thumb, not a physical model: an equal pair needs a
separation of at least the larger of the Dawes limit (116"/aperture in mm) and about 0.6x
the seeing; each magnitude of difference between the stars raises that by 30%, and faster
beyond 5 magnitudes, since the faint companion hides in the bright star's glare. The companion must also be
bright enough for the aperture.
"""

from __future__ import annotations

import asyncio
import math
import re
from typing import Any

from astronomy_mcp import catalog, simbad, sky
from astronomy_mcp.http import UpstreamError, get_json
from astronomy_mcp.location import Location

VIZIER_TAP = "https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync"
WDS_TABLE = '"B/wds/wds"'
COLUMNS = "WDS, Disc, Comp, Obs1, Obs2, Nobs, pa2, sep2, mag1, mag2, SpType, Notes, RAJ2000, DEJ2000"
WDS_ID = re.compile(r"^\d{5}[+-]\d{4}$")
DISCOVERER = re.compile(r"^([A-Za-z]{1,4})\s*(\d{1,5})$")


def _clean(value: Any) -> Any:
    """WDS writes -1 (or blanks) for unknown values."""
    if value is None or value == -1 or (isinstance(value, str) and not value.strip()):
        return None
    return value.strip() if isinstance(value, str) else value


async def run_query(adql: str) -> list[dict[str, Any]]:
    payload = await get_json(VIZIER_TAP, {"request": "doQuery", "lang": "ADQL", "format": "json", "query": adql},
                             source="VizieR (WDS)", ttl=86400, timeout=90)
    names = [m["name"] for m in payload.get("metadata", [])]
    return [dict(zip(names, row)) for row in payload.get("data", [])]


def discoverer_code(text: str) -> str | None:
    """'STF 2382' -> 'STF2382', 'Stfa 37' -> 'STFA 37': WDS's fixed 7-character discoverer field."""
    m = DISCOVERER.match(text.strip())
    if not m:
        return None
    code, number = m.group(1).upper(), m.group(2)
    return code + number.rjust(7 - len(code))


def limiting_magnitude(aperture_mm: float) -> float:
    """Faintest star a telescope shows under a reasonably dark sky (classic 2.1 + 5 log D)."""
    return 2.1 + 5 * math.log10(aperture_mm)


def required_separation(aperture_mm: float, seeing_arcsec: float, delta_mag: float) -> float:
    dawes = 116.0 / aperture_mm
    d = max(0.0, delta_mag)
    # 30% per magnitude, steepening past 5 magnitudes where glare swamps the companion
    # (tuned so Antares is borderline in 100 mm, Rigel moderate and Sirius B challenging).
    return max(dawes, 0.6 * seeing_arcsec) * (1 + 0.3 * d + 0.15 * max(0.0, d - 5) ** 2)


def assess(sep: float | None, mag1: float | None, mag2: float | None, aperture_mm: float,
           seeing_arcsec: float) -> dict[str, Any]:
    """Can this aperture split the pair in this seeing, and at what magnification?"""
    if sep is None or sep <= 0:
        return {"splittable": None, "reason": "no recent separation measured"}
    delta = (mag2 - mag1) if mag1 is not None and mag2 is not None else 0.0
    need = required_separation(aperture_mm, seeing_arcsec, abs(delta))
    out: dict[str, Any] = {"required_separation_arcsec": round(need, 2), "dawes_limit_arcsec": round(116.0 / aperture_mm, 2)}
    faint = max(m for m in (mag1, mag2) if m is not None) if mag1 is not None or mag2 is not None else None
    if faint is not None and faint > limiting_magnitude(aperture_mm) - 0.5:
        return {**out, "splittable": False, "reason": f"companion (mag {faint}) too faint for {aperture_mm:.0f} mm"}
    ratio = sep / need
    if ratio < 1:
        limit = "the seeing" if 0.6 * seeing_arcsec > 116.0 / aperture_mm else "the aperture"
        return {**out, "splittable": False, "reason": f"too close for {limit}"}
    # The eye separates two points about 2-4 arcminutes apart; aim for ~240" at the eyepiece, and more
    # for unequal pairs, where extra power spreads the glare away from the companion.
    wanted = 240 / sep * (1 + 0.3 * abs(delta))
    magnification = min(max(25, math.ceil(wanted / 5) * 5), max(50, round(2 * aperture_mm)))
    difficulty = "challenging" if ratio < 1.5 else "moderate" if ratio < 3 else "easy"
    return {**out, "splittable": True, "difficulty": difficulty, "suggested_magnification": magnification}


def shape_pair(row: dict[str, Any], aperture_mm: float | None, seeing_arcsec: float) -> dict[str, Any]:
    mag1, mag2 = _clean(row.get("mag1")), _clean(row.get("mag2"))
    sep = _clean(row.get("sep2"))
    out: dict[str, Any] = {
        "wds": row["WDS"],
        "discoverer": " ".join((row.get("Disc") or "").split()),
        "components": _clean(row.get("Comp")) or "AB",
        "separation_arcsec": sep,
        "position_angle_deg": _clean(row.get("pa2")),
        "measured": _clean(row.get("Obs2")),
        "magnitudes": [m for m in (mag1, mag2) if m is not None] or None,
        "spectral_types": _clean(row.get("SpType")),
        "observations": _clean(row.get("Nobs")),
        "notes": _clean(row.get("Notes")),
    }
    if row.get("RAJ2000") is not None:
        out["ra_deg"] = round(row["RAJ2000"], 5)
        out["dec_deg"] = round(row["DEJ2000"], 5)
    if aperture_mm:
        out["with_your_telescope"] = assess(sep, mag1, mag2, aperture_mm, seeing_arcsec)
    return {k: v for k, v in out.items() if v is not None}


# ---------------------------------------------------------------- one system

async def lookup(name: str, aperture_mm: float | None, seeing_arcsec: float) -> dict[str, Any]:
    """All WDS pairs of one system, by WDS id, discoverer designation or any star name SIMBAD knows."""
    text = name.strip()
    resolved = None
    if WDS_ID.match(text):
        where = f"WDS = '{text}'"
    elif (code := discoverer_code(text)) is not None and not text.upper().startswith(("HD", "HR", "HIP", "SAO", "TYC", "M ")):
        rows = await run_query(f"SELECT {COLUMNS} FROM {WDS_TABLE} WHERE Disc = '{code}'")
        if not rows:
            raise ValueError(f"WDS has no pair with discoverer designation '{text}'.")
        where = f"WDS = '{rows[0]['WDS']}'"
    else:
        bayer = catalog.bayer_to_simbad(text)
        # SIMBAD names the members of a multiple star 'eps01 Lyr', 'eps02 Lyr'; the first is enough
        # to find the WDS system, which covers all of them.
        tries = [bayer, re.sub(r"^([a-z.]+) ", r"\g<1>1 ", bayer)] if bayer else []
        obj = None
        try:
            for ident in [*tries, text]:
                if obj := await simbad.lookup(ident, max_aliases=0):
                    break
        except simbad.SimbadError as exc:
            raise UpstreamError(str(exc)) from exc
        if obj is None:
            raise ValueError(f"Neither WDS nor SIMBAD knows '{name}'.")
        resolved = {k: obj.get(k) for k in ("main_id", "ra_deg", "dec_deg") if obj.get(k) is not None}
        ra, dec = obj["ra_deg"], obj["dec_deg"]
        near = await run_query(
            f"SELECT {COLUMNS} FROM {WDS_TABLE} WHERE 1 = CONTAINS(POINT('ICRS', RAJ2000, DEJ2000), "
            f"CIRCLE('ICRS', {ra}, {dec}, {30 / 3600}))")
        if not near:
            return {"found": False, "resolved_by_simbad": resolved,
                    "message": f"{obj.get('main_id', name)} is not in the Washington Double Star catalog."}
        nearest = min(near, key=lambda r: sky.separation_deg(ra, dec, r["RAJ2000"], r["DEJ2000"]))
        where = f"WDS = '{nearest['WDS']}'"
    rows = await run_query(f"SELECT {COLUMNS} FROM {WDS_TABLE} WHERE {where}")
    # Visual pairs with reasonably bright companions first, closest first (epsilon Lyrae's two close pairs
    # before their wide combinations); then faint companions; sub-half-arcsecond pairs found by speckle or
    # interferometry, and unmeasured ones, last.
    def order(r: dict[str, Any]) -> tuple[bool, bool, float]:
        sep = _clean(r.get("sep2")) or 0
        return sep < 0.5, (_clean(r.get("mag2")) or 99) > 10, sep

    rows.sort(key=order)
    if not rows:
        raise ValueError(f"WDS has no system '{text}'.")
    pairs = [shape_pair(r, aperture_mm, seeing_arcsec) for r in rows]
    first = rows[0]
    out: dict[str, Any] = {
        "found": True,
        "wds": first["WDS"],
        "resolved_by_simbad": resolved,
        "constellation": sky.constellation(first["RAJ2000"], first["DEJ2000"])["name"] if first.get("RAJ2000") is not None else None,
        "pairs": pairs,
        "note": "Separations and position angles are the latest WDS measurements (year in 'measured'); orbiting "
                "pairs change over years. Splitting assessments are a rule of thumb."
                if aperture_mm else
                "Separations and position angles are the latest WDS measurements. Give aperture_mm to judge "
                "whether your telescope can split each pair.",
    }
    return {k: v for k, v in out.items() if v is not None}


# ---------------------------------------------------------------- finding pairs to split

async def _names(pairs: list[dict[str, Any]]) -> None:
    """Add the primary's SIMBAD name (common name or Bayer/Flamsteed) to each pair."""
    gate = asyncio.Semaphore(4)

    async def one(pair: dict[str, Any]) -> None:
        async with gate:
            try:
                rows = await simbad.cone_search(pair["ra_deg"], pair["dec_deg"], 0.2, limit=1,
                                                max_v_mag=pair["magnitudes"][0] + 1.5)
            except (simbad.SimbadError, ValueError):
                return
        if rows:
            pair["star"] = rows[0].get("main_id")

    await asyncio.gather(*(one(p) for p in pairs))


async def splittable(
    aperture_mm: float,
    seeing_arcsec: float,
    max_primary_mag: float,
    max_separation_arcsec: float,
    constellation: str | None,
    challenging_only: bool,
    loc: Location | None,
    night_times: list[Any] | None,
    min_altitude: float,
    limit: int,
) -> dict[str, Any]:
    floor = max(116.0 / aperture_mm, 0.6 * seeing_arcsec)
    faint_limit = limiting_magnitude(aperture_mm) - 0.5
    rows = await run_query(
        f"SELECT TOP 8000 {COLUMNS} FROM {WDS_TABLE} WHERE mag1 <= {max_primary_mag} AND mag2 <= {faint_limit:.1f} "
        f"AND mag2 >= mag1 - 0.5 AND sep2 >= {floor:.2f} AND sep2 <= {max_separation_arcsec} AND Obs2 >= 1990 "
        f"ORDER BY mag1")
    found = []
    for row in rows:
        pair = shape_pair(row, aperture_mm, seeing_arcsec)
        verdict = pair["with_your_telescope"]
        if not verdict.get("splittable") or "ra_deg" not in pair:
            continue
        if challenging_only and verdict["difficulty"] != "challenging":
            continue
        pair["constellation"] = sky.constellation(pair["ra_deg"], pair["dec_deg"])["name"]
        if constellation and constellation.lower() not in (pair["constellation"].lower(),
                                                           sky.constellation(pair["ra_deg"], pair["dec_deg"])["abbreviation"].lower()):
            continue
        found.append(pair)
    if loc and night_times:
        tracks = sky.fast_tracks([(p["ra_deg"], p["dec_deg"]) for p in found], night_times, loc)
        visible = []
        for pair, track in zip(found, tracks):
            best = max(range(len(track)), key=lambda k: track[k][0])
            if track[best][0] >= min_altitude:
                pair["best_time"] = sky.fmt(night_times[best], loc)
                pair["altitude_at_best_deg"] = round(track[best][0])
                visible.append(pair)
        found = visible
    # Showpieces first: bright primaries, then pairs comfortably above the limit.
    found.sort(key=lambda p: (p["magnitudes"][0], -p["separation_arcsec"] if challenging_only else 0))
    shown = found[:limit]
    await _names(shown)
    return {
        "aperture_mm": aperture_mm,
        "seeing_arcsec": seeing_arcsec,
        "dawes_limit_arcsec": round(116.0 / aperture_mm, 2),
        "faintest_companion_mag": round(faint_limit, 1),
        "total_matches": len(found),
        "count": len(shown),
        "pairs": shown,
        "note": "From the Washington Double Star catalog (pairs measured since 1990). 'Splittable' is a rule of "
                "thumb from the Dawes limit, seeing and the brightness difference; steady nights beat it, poor "
                "ones fall short. Many entries are optical pairs rather than true binaries.",
    }
