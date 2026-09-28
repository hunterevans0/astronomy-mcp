"""In-process MCP tests. Tests marked `live` hit the real services; run them with `pytest -m live`."""

import pytest
from mcp import Client

from astronomy_mcp import mcp

EXPECTED_TOOLS = {
    # catalogs
    "simbad_lookup", "simbad_cone_search", "vsx_lookup", "vsx_cone_search", "variable_stars_near",
    "describe_object", "search_deep_sky", "identify_constellation",
    # location
    "geocode_location", "set_default_location", "get_default_location",
    # sky math
    "get_position", "get_rise_set_transit", "get_twilight_times", "get_moon_phases", "get_planet_positions",
    "get_eclipses",
    # planning and conditions
    "whats_up_tonight", "is_visible_tonight", "get_sky_forecast", "get_limiting_magnitude",
    # space
    "get_space_weather", "get_upcoming_launches",
}


async def test_tools_registered_with_schemas():
    async with Client(mcp) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert set(tools) == EXPECTED_TOOLS
    for name, tool in tools.items():
        assert tool.description
        assert tool.annotations.read_only_hint is (name != "set_default_location")
    assert tools["simbad_lookup"].input_schema["required"] == ["identifier"]
    assert tools["get_position"].input_schema["required"] == ["target"]


async def test_out_of_range_coordinates_are_rejected():
    async with Client(mcp) as client:
        result = await client.call_tool("vsx_cone_search", {"ra_deg": 400, "dec_deg": 0})
    assert result.is_error


async def test_location_tools_explain_missing_location():
    async with Client(mcp) as client:
        result = await client.call_tool("get_twilight_times", {})
    assert result.is_error
    assert "set_default_location" in result.content[0].text


async def test_twilight_and_position_use_saved_default(moab):
    async with Client(mcp) as client:
        twilight = (await client.call_tool("get_twilight_times", {"date": "2026-10-10"})).structured_content
        position = (await client.call_tool("get_position", {"target": "Saturn", "time": "2026-10-10T23:00"})).structured_content
    assert twilight["location"] == "Moab"
    assert twilight["darkest_sky"] == "astronomical"
    assert twilight["dark_window"]["start"].startswith("2026-10-10T20:")
    assert position["time"] == "2026-10-10T23:00-06:00"
    assert position["above_horizon"] is True


async def test_whats_up_planets_offline(moab):
    async with Client(mcp) as client:
        result = await client.call_tool("whats_up_tonight", {"date": "2026-10-10", "include": "planets"})
    data = result.structured_content
    names = [t["name"] for t in data["targets"]]
    assert "Saturn" in names
    assert data["assumptions"]["sky_brightness_source"] == "Bortle 2 from saved location"


async def test_is_visible_for_planet_offline(moab):
    async with Client(mcp) as client:
        data = (await client.call_tool("is_visible_tonight", {"target": "Saturn", "date": "2026-10-10"})).structured_content
    assert data["visible"] is True and data["resolved_by"] == "astronomy-engine"


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


@pytest.mark.live
async def test_live_whats_up_includes_deep_sky(moab):
    async with Client(mcp) as client:
        data = (await client.call_tool("whats_up_tonight", {"date": "2026-10-10", "max_results": 30})).structured_content
    assert "M 31" in [t["name"] for t in data["targets"]]


@pytest.mark.live
async def test_live_describe_object_merges_sources():
    async with Client(mcp) as client:
        data = (await client.call_tool("describe_object", {"name": "M13"})).structured_content
    assert data["simbad"]["main_id"] == "M 13"
    assert data["deep_sky_catalog"]["common_names"] == ["Hercules Globular Cluster"]
