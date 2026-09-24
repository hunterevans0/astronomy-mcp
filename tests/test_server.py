"""In-process MCP tests. Tests marked `live` hit SIMBAD/VSX; run them with `pytest -m live`."""

import pytest
from mcp import Client

from astronomy_mcp import mcp

EXPECTED_TOOLS = {"simbad_lookup", "simbad_cone_search", "vsx_lookup", "vsx_cone_search", "variable_stars_near"}


async def test_tools_registered_with_schemas():
    async with Client(mcp) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert set(tools) == EXPECTED_TOOLS
    for tool in tools.values():
        assert tool.description
        assert tool.annotations.read_only_hint is True
    assert tools["simbad_lookup"].input_schema["required"] == ["identifier"]


async def test_out_of_range_coordinates_are_rejected():
    async with Client(mcp) as client:
        result = await client.call_tool("vsx_cone_search", {"ra_deg": 400, "dec_deg": 0})
    assert result.is_error


@pytest.mark.live
async def test_live_simbad_lookup():
    async with Client(mcp) as client:
        result = await client.call_tool("simbad_lookup", {"identifier": "Vega"})
    data = result.structured_content
    assert data["found"] and data["main_id"] == "* alf Lyr"


@pytest.mark.live
async def test_live_vsx_lookup():
    async with Client(mcp) as client:
        result = await client.call_tool("vsx_lookup", {"name": "Mira"})
    data = result.structured_content
    assert data["found"] and data["variability_type"] == "M"
