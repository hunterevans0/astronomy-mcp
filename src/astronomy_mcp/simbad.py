"""Async client for the SIMBAD astronomical database (CDS, Strasbourg).

Uses SIMBAD's TAP service, which accepts ADQL (an SQL dialect with
spatial functions). Schema reference:
https://simbad.cds.unistra.fr/simbad/tap/tapsearch.html
"""

from __future__ import annotations

import re
from typing import Any

import httpx

TAP_URL = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
USER_AGENT = "astronomy-mcp/0.1"

# Photometric bands available in SIMBAD's `allfluxes` table.
BANDS = ("U", "B", "V", "R", "I", "J", "H", "K", "G")

# SIMBAD object-type codes look like "*", "G", "s*r", "Mi*", "V*?", "EB*", "QSO".
_OTYPE_RE = re.compile(r"^[A-Za-z0-9*?!:.+\-]{1,12}$")


class SimbadError(RuntimeError):
    pass


def _adql_str(value: str) -> str:
    """Quote a value as an ADQL string literal."""
    return "'" + value.replace("'", "''") + "'"


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a TAP JSON response (metadata + data arrays) into dicts."""
    names = [col["name"] for col in payload.get("metadata", [])]
    rows = []
    for raw in payload.get("data", []):
        row = {}
        for name, value in zip(names, raw):
            if isinstance(value, str):
                value = value.strip()
                if name != "ids":
                    value = " ".join(value.split())
            row[name] = value
        rows.append(row)
    return rows


async def run_adql(query: str, client: httpx.AsyncClient | None = None) -> list[dict[str, Any]]:
    """Execute an ADQL query against SIMBAD TAP and return rows as dicts."""
    data = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": query}
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=30, headers={"User-Agent": USER_AGENT})
    try:
        resp = await client.post(TAP_URL, data=data)
    except httpx.HTTPError as exc:
        raise SimbadError(f"Could not reach SIMBAD: {exc}") from exc
    finally:
        if owns_client:
            await client.aclose()
    if resp.status_code != 200:
        raise SimbadError(f"SIMBAD returned HTTP {resp.status_code}: {resp.text[:500]}")
    try:
        return _rows(resp.json())
    except ValueError as exc:
        raise SimbadError(f"SIMBAD returned a non-JSON response: {resp.text[:500]}") from exc


def _shape_object(row: dict[str, Any], max_aliases: int) -> dict[str, Any]:
    """Reshape a flat SIMBAD row into a nested, readable record."""
    mags = {band: row[band] for band in BANDS if row.get(band) is not None}
    # SIMBAD pads identifiers with runs of spaces ("HD  39801"); collapse them.
    aliases = [" ".join(a.split()) for a in (row.get("ids") or "").split("|") if a.strip()]
    result: dict[str, Any] = {
        "main_id": row["main_id"],
        "object_type": row.get("otype"),
        "object_type_description": row.get("otype_desc"),
        "ra_deg": row.get("ra"),
        "dec_deg": row.get("dec"),
        "spectral_type": row.get("sp_type"),
        "morphological_type": row.get("morph_type"),
        "parallax_mas": row.get("plx_value"),
        "proper_motion_mas_per_yr": (
            {"pmra": row["pmra"], "pmdec": row["pmdec"]} if row.get("pmra") is not None else None
        ),
        "radial_velocity_km_s": row.get("rvz_radvel"),
        "redshift": row.get("rvz_redshift"),
        "magnitudes": mags or None,
        "reference_count": row.get("nbref"),
        "aliases": aliases[:max_aliases],
        "alias_count": len(aliases),
    }
    if row.get("plx_value") and row["plx_value"] > 0:
        result["distance_pc_from_parallax"] = round(1000.0 / row["plx_value"], 2)
    return {k: v for k, v in result.items() if v is not None}


_DETAIL_COLUMNS = (
    "b.main_id, b.ra, b.dec, b.otype, t.description AS otype_desc, b.sp_type, "
    "b.morph_type, b.plx_value, b.rvz_redshift, b.rvz_radvel, b.pmra, b.pmdec, b.nbref, "
    + ", ".join(f"f.{band}" for band in BANDS)
)


async def lookup(identifier: str, max_aliases: int = 25) -> dict[str, Any] | None:
    """Look up one object by any identifier SIMBAD knows (e.g. 'M31', 'Betelgeuse')."""
    query = f"""
        SELECT TOP 1 {_DETAIL_COLUMNS}, s.ids
        FROM basic AS b
        JOIN ident AS i ON b.oid = i.oidref
        LEFT JOIN allfluxes AS f ON b.oid = f.oidref
        LEFT JOIN otypedef AS t ON b.otype = t.otype
        LEFT JOIN ids AS s ON b.oid = s.oidref
        WHERE i.id = {_adql_str(identifier.strip())}
    """
    rows = await run_adql(query)
    return _shape_object(rows[0], max_aliases) if rows else None


async def cone_search(
    ra_deg: float,
    dec_deg: float,
    radius_arcmin: float,
    limit: int = 20,
    object_type: str | None = None,
    max_v_mag: float | None = None,
) -> list[dict[str, Any]]:
    """Find objects within a radius of a sky position, nearest first."""
    if not 0 <= ra_deg < 360:
        raise ValueError("ra_deg must be in [0, 360)")
    if not -90 <= dec_deg <= 90:
        raise ValueError("dec_deg must be in [-90, 90]")
    if not 0 < radius_arcmin <= 60:
        raise ValueError("radius_arcmin must be in (0, 60]")
    limit = max(1, min(limit, 200))

    point = f"POINT('ICRS', {ra_deg:.8f}, {dec_deg:.8f})"
    where = [f"CONTAINS(POINT('ICRS', b.ra, b.dec), CIRCLE('ICRS', {ra_deg:.8f}, {dec_deg:.8f}, {radius_arcmin / 60:.8f})) = 1"]
    if object_type:
        if not _OTYPE_RE.match(object_type):
            raise ValueError(f"Invalid SIMBAD object type code: {object_type!r}")
        where.append(f"b.otype = {_adql_str(object_type)}")
    if max_v_mag is not None:
        where.append(f"f.V <= {float(max_v_mag)}")

    query = f"""
        SELECT TOP {limit} {_DETAIL_COLUMNS},
               DISTANCE(POINT('ICRS', b.ra, b.dec), {point}) * 60 AS sep_arcmin
        FROM basic AS b
        LEFT JOIN allfluxes AS f ON b.oid = f.oidref
        LEFT JOIN otypedef AS t ON b.otype = t.otype
        WHERE {' AND '.join(where)}
        ORDER BY sep_arcmin
    """
    results = []
    for row in await run_adql(query):
        shaped = _shape_object(row, max_aliases=0)
        shaped.pop("aliases", None)
        shaped.pop("alias_count", None)
        shaped["separation_arcmin"] = round(row["sep_arcmin"], 4)
        results.append(shaped)
    return results
