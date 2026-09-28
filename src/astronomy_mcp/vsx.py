"""Async client for the AAVSO International Variable Star Index (VSX).

API docs: https://www.aavso.org/direct-web-query-vsxvsp
Note: www.aavso.org sits behind a Cloudflare bot challenge, so we call the
vsx.aavso.org host directly with a descriptive User-Agent.
"""

from __future__ import annotations

import math
from typing import Any

import httpx

from astronomy_mcp.http import USER_AGENT

API_URL = "https://vsx.aavso.org/index.php"

_FLOAT_FIELDS = {
    "RA2000": "ra_deg",
    "Declination2000": "dec_deg",
    "ProperMotionRA": "pmra_mas_per_yr",
    "ProperMotionDec": "pmdec_mas_per_yr",
    "Period": "period_days",
    "Epoch": "epoch_hjd",
    "RiseDuration": "rise_duration_pct",
}
_STR_FIELDS = {
    "Name": "name",
    "AUID": "auid",
    "OID": "vsx_oid",
    "VariabilityType": "variability_type",
    "Category": "category",
    "SpectralType": "spectral_type",
    "Discoverer": "discoverer",
    "Constellation": "constellation",
}


class VSXError(RuntimeError):
    pass


def _parse_mag(value: str | None) -> dict[str, Any] | None:
    """Parse VSX magnitude strings like '4.4 V', '<15.2 CV' or '(0.30) G'.

    A value in parentheses is an amplitude rather than an absolute magnitude.
    """
    if not value:
        return None
    text, _, band = value.strip().partition(" ")
    out: dict[str, Any] = {"raw": value.strip()}
    if band:
        out["band"] = band.strip()
    if text.startswith("(") and text.endswith(")"):
        out["is_amplitude"] = True
        text = text[1:-1]
    if text[:1] in "<>":
        out["limit"] = text[0]
        text = text[1:]
    try:
        out["value"] = float(text.rstrip(":"))
    except ValueError:
        pass
    return out


def _shape(obj: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for src, dst in _STR_FIELDS.items():
        if obj.get(src):
            out[dst] = obj[src].strip()
    for src, dst in _FLOAT_FIELDS.items():
        if obj.get(src):
            try:
                out[dst] = float(obj[src])
            except ValueError:
                out[dst] = obj[src]
    for src, dst in (("MaxMag", "max_mag"), ("MinMag", "min_mag")):
        parsed = _parse_mag(obj.get(src))
        if parsed:
            out[dst] = parsed
    if "vsx_oid" in out:
        out["vsx_url"] = f"https://vsx.aavso.org/index.php?view=detail.top&oid={out['vsx_oid']}"
    return out


def _angular_sep_arcmin(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Great-circle separation (haversine), inputs in degrees."""
    ra1, dec1, ra2, dec2 = map(math.radians, (ra1, dec1, ra2, dec2))
    h = math.sin((dec2 - dec1) / 2) ** 2 + math.cos(dec1) * math.cos(dec2) * math.sin((ra2 - ra1) / 2) ** 2
    return math.degrees(2 * math.asin(min(1.0, math.sqrt(h)))) * 60


async def _get(params: dict[str, Any]) -> dict[str, Any]:
    params = {**params, "format": "json"}
    async with httpx.AsyncClient(
        timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    ) as client:
        try:
            resp = await client.get(API_URL, params=params)
        except httpx.HTTPError as exc:
            raise VSXError(f"Could not reach AAVSO VSX: {exc}") from exc
    if resp.status_code != 200:
        raise VSXError(f"VSX returned HTTP {resp.status_code}")
    try:
        return resp.json()
    except ValueError as exc:
        raise VSXError(
            "VSX returned a non-JSON response (possibly a bot challenge page): "
            + resp.text[:200]
        ) from exc


async def lookup(name: str) -> dict[str, Any] | None:
    """Look up a variable star by name (e.g. 'R Leo', 'Mira', 'SS Cyg')."""
    payload = await _get({"view": "api.object", "ident": name.strip()})
    obj = payload.get("VSXObject")
    if not obj or not isinstance(obj, dict):
        return None
    return _shape(obj)


async def cone_search(
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    max_mag: float | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Find variable stars within a radius of a sky position, nearest first."""
    if not 0 <= ra_deg < 360:
        raise ValueError("ra_deg must be in [0, 360)")
    if not -90 <= dec_deg <= 90:
        raise ValueError("dec_deg must be in [-90, 90]")
    if not 0 < radius_deg <= 5:
        raise ValueError("radius_deg must be in (0, 5]")
    limit = max(1, min(limit, 500))

    params: dict[str, Any] = {"view": "api.list", "ra": ra_deg, "dec": dec_deg, "radius": radius_deg}
    if max_mag is not None:
        params["tomag"] = max_mag
    payload = await _get(params)

    container = payload.get("VSXObjects") or {}
    objs = container.get("VSXObject", []) if isinstance(container, dict) else []
    if isinstance(objs, dict):  # a single match comes back as an object, not a list
        objs = [objs]

    results = []
    for obj in objs:
        shaped = _shape(obj)
        if isinstance(shaped.get("ra_deg"), float) and isinstance(shaped.get("dec_deg"), float):
            shaped["separation_arcmin"] = round(
                _angular_sep_arcmin(ra_deg, dec_deg, shaped["ra_deg"], shaped["dec_deg"]), 4
            )
        results.append(shaped)
    results.sort(key=lambda r: r.get("separation_arcmin", math.inf))
    return results[:limit]
