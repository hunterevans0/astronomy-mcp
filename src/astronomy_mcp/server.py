"""MCP server exposing SIMBAD and AAVSO VSX astronomy data as tools."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from astronomy_mcp import simbad, vsx

mcp = MCPServer(
    name="astronomy",
    title="Astronomy Data",
    version="0.1.0",
    log_level="WARNING",
    instructions=(
        "Tools for querying astronomical catalogs. Use simbad_lookup to identify any "
        "celestial object and get its coordinates, type, magnitudes and aliases. Use "
        "simbad_cone_search to find what is near a sky position. Use the vsx_* tools for "
        "variable stars (periods, amplitudes, variability types) from AAVSO's VSX. "
        "Coordinates are ICRS/J2000 in decimal degrees."
    ),
)

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=True, idempotent_hint=True)

RA = Annotated[float, Field(ge=0, lt=360, description="Right ascension, decimal degrees (ICRS/J2000)")]
DEC = Annotated[float, Field(ge=-90, le=90, description="Declination, decimal degrees (ICRS/J2000)")]


@mcp.tool(annotations=READ_ONLY)
async def simbad_lookup(
    identifier: Annotated[
        str,
        Field(description="Any SIMBAD identifier or common name, e.g. 'M31', 'Betelgeuse', 'HD 39801', 'NGC 1976'"),
    ],
) -> dict[str, Any]:
    """Look up a celestial object in SIMBAD by name or catalog identifier.

    Returns coordinates, object type, spectral/morphological type, parallax (and derived
    distance), proper motion, radial velocity, redshift, multi-band magnitudes and aliases.
    """
    obj = await simbad.lookup(identifier)
    if obj is None:
        return {"found": False, "message": f"SIMBAD has no object matching '{identifier}'."}
    return {"found": True, **obj}


@mcp.tool(annotations=READ_ONLY)
async def simbad_cone_search(
    ra_deg: RA,
    dec_deg: DEC,
    radius_arcmin: Annotated[float, Field(gt=0, le=60, description="Search radius in arcminutes (max 60)")] = 5.0,
    object_type: Annotated[
        str | None,
        Field(description="Optional SIMBAD object-type code to filter on, e.g. '*' (star), 'G' (galaxy), 'QSO', 'PN', 'OpC', 'V*' (variable star), 'EB*'"),
    ] = None,
    max_v_mag: Annotated[float | None, Field(description="Only return objects with V magnitude at or brighter than this")] = None,
    limit: Annotated[int, Field(ge=1, le=200, description="Maximum number of results")] = 20,
) -> dict[str, Any]:
    """Find SIMBAD objects within a radius of a sky position, sorted nearest first."""
    results = await simbad.cone_search(ra_deg, dec_deg, radius_arcmin, limit, object_type, max_v_mag)
    return {"count": len(results), "objects": results}


@mcp.tool(annotations=READ_ONLY)
async def vsx_lookup(
    name: Annotated[str, Field(description="Variable star name, e.g. 'R Leo', 'Mira', 'SS Cyg', 'delta Cep'")],
) -> dict[str, Any]:
    """Look up a variable star in the AAVSO International Variable Star Index (VSX).

    Returns variability type, period, epoch, magnitude range, spectral type, discoverer,
    constellation and a link to the VSX detail page.
    """
    obj = await vsx.lookup(name)
    if obj is None:
        return {"found": False, "message": f"VSX has no variable star named '{name}'."}
    return {"found": True, **obj}


@mcp.tool(annotations=READ_ONLY)
async def vsx_cone_search(
    ra_deg: RA,
    dec_deg: DEC,
    radius_deg: Annotated[float, Field(gt=0, le=5, description="Search radius in degrees (max 5)")] = 0.5,
    max_mag: Annotated[float | None, Field(description="Only return stars reaching this magnitude or brighter at maximum")] = None,
    limit: Annotated[int, Field(ge=1, le=500, description="Maximum number of results")] = 25,
) -> dict[str, Any]:
    """Find known variable stars in VSX within a radius of a sky position, nearest first."""
    results = await vsx.cone_search(ra_deg, dec_deg, radius_deg, max_mag, limit)
    return {"count": len(results), "variable_stars": results}


@mcp.tool(annotations=READ_ONLY)
async def variable_stars_near(
    target: Annotated[str, Field(description="Name of any object SIMBAD can resolve, e.g. 'M13', 'Vega', 'Pleiades'")],
    radius_deg: Annotated[float, Field(gt=0, le=5, description="Search radius in degrees (max 5)")] = 0.5,
    max_mag: Annotated[float | None, Field(description="Only return stars reaching this magnitude or brighter at maximum")] = None,
    limit: Annotated[int, Field(ge=1, le=500, description="Maximum number of results")] = 25,
) -> dict[str, Any]:
    """Resolve a target name with SIMBAD, then list VSX variable stars around it."""
    obj = await simbad.lookup(target, max_aliases=0)
    if obj is None:
        return {"found": False, "message": f"SIMBAD could not resolve '{target}'."}
    results = await vsx.cone_search(obj["ra_deg"], obj["dec_deg"], radius_deg, max_mag, limit)
    return {
        "found": True,
        "target": {k: obj.get(k) for k in ("main_id", "object_type_description", "ra_deg", "dec_deg")},
        "count": len(results),
        "variable_stars": results,
    }


def main() -> None:
    mcp.run()  # stdio transport
