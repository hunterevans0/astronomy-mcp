"""In-process MCP tests. Tests marked `live` hit the real services; run them with `pytest -m live`."""

import pytest
from mcp import Client

from astronomy_mcp import conditions, lunar, mcp
from astronomy_mcp.http import UpstreamError

EXPECTED_TOOLS = {
    # catalogs
    "simbad_lookup", "simbad_cone_search", "vsx_lookup", "vsx_cone_search", "variable_stars_near",
    "describe_object", "search_deep_sky", "identify_constellation",
    # location
    "geocode_location", "set_default_location", "get_default_location",
    # sky math
    "get_position", "get_rise_set_transit", "get_twilight_times", "get_moon_phases", "get_planet_positions",
    "get_eclipses", "find_conjunctions", "find_oppositions",
    # solar system detail
    "get_jupiter_moons", "get_jupiter_events", "get_lunar_terminator", "get_moon_libration",
    # planning and conditions
    "whats_up_tonight", "is_visible_tonight", "get_sky_forecast", "get_limiting_magnitude",
    "get_light_pollution", "find_dark_sites", "get_horizon_profile",
    "get_transparency_drivers", "best_night_this_month", "find_dark_moon_weekends",
    # comets, asteroids, fireballs
    "get_comet_visibility", "get_asteroid_ephemeris", "find_close_approaches", "get_fireball_reports",
    # satellites
    "get_iss_passes", "get_satellite_passes", "find_satellites_overhead", "get_starlink_trains",
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
        result = await client.call_tool("whats_up_tonight", {"date": "2026-10-10", "include": "planets", "terrain": False})
    data = result.structured_content
    names = [t["name"] for t in data["targets"]]
    assert "Saturn" in names
    assert data["assumptions"]["sky_brightness_source"] == "Bortle 2 from saved location"


async def test_is_visible_for_planet_offline(moab):
    async with Client(mcp) as client:
        data = (await client.call_tool("is_visible_tonight", {"target": "Saturn", "date": "2026-10-10", "terrain": False})).structured_content
    assert data["visible"] is True and data["resolved_by"] == "astronomy-engine"
    assert data["difficulty"] == "easy"


async def test_dark_moon_weekends_offline(moab):
    async with Client(mcp) as client:
        here = (await client.call_tool("find_dark_moon_weekends", {"start_date": "2026-10-01", "months": 1})).structured_content
    assert here["location"] == "Moab"
    assert here["weekends"][0]["friday"] == "2026-10-09" and here["weekends"][0]["moon_free_dark_pct"] == 100


async def test_dark_moon_weekends_work_without_a_location():
    async with Client(mcp) as client:
        result = await client.call_tool("find_dark_moon_weekends", {"start_date": "2026-10-01", "months": 1})
    assert not result.is_error
    assert result.structured_content["weekends"][0]["friday"] == "2026-10-09"


async def test_best_night_survives_a_forecast_outage(moab, monkeypatch):
    async def down(loc):
        raise UpstreamError("Could not reach Open-Meteo")

    monkeypatch.setattr(conditions, "cloud_cover_by_hour", down)
    async with Client(mcp) as client:
        data = (await client.call_tool("best_night_this_month", {"target": "Saturn", "start_date": "2026-10-08", "days": 5})).structured_content
    assert data["target"] == "Saturn" and "Cloud forecast unavailable" in data["warning"]
    assert data["best_nights_with_forecast"] == [] and len(data["best_nights_beyond_forecast"]) == 5
    assert len(data["nights"]) == 5 and "moonlight" not in data["scoring"]


async def test_solar_system_tools_work_offline_without_a_location():
    async with Client(mcp) as client:
        moons = (await client.call_tool("get_jupiter_moons", {"time": "2026-10-03T11:00Z"})).structured_content
        events = (await client.call_tool("get_jupiter_events", {"time": "2026-10-03T00:00Z", "hours": 12})).structured_content
        libration = (await client.call_tool("get_moon_libration", {"time": "2026-10-03T00:00Z"})).structured_content
        pairs = (await client.call_tool("find_conjunctions", {"start_date": "2026-11-01", "days": 30})).structured_content
        best = (await client.call_tool("find_oppositions", {"start_date": "2026-10-01", "years": 1, "planets": ["saturn"]})).structured_content
        needs_site = await client.call_tool("get_jupiter_events", {"observable_only": True})
    assert moons["time"] == "2026-10-03T11:00+00:00" and len(moons["moons"]) == 4
    assert events["count"] == len(events["events"]) > 0 and events["from"] == "2026-10-03T00:00+00:00"
    assert libration["viewpoint"].startswith("geocentric") and len(libration["limb_features"]) == 45
    assert pairs["from"] == "2026-11-01T00:00+00:00" and pairs["conjunctions"][0]["bodies"] == ["Mars", "Jupiter"]
    assert [o["opposition"][:10] for o in best["oppositions"]] == ["2026-10-04"]
    assert needs_site.is_error and "location" in needs_site.content[0].text


async def test_lunar_terminator_uses_the_gazetteer(moab, monkeypatch):
    async def features():
        return [{"name": "Ptolemaeus", "type": "crater", "latitude": -9.16, "longitude": -1.84, "diameter_km": 153.7},
                {"name": "Langrenus", "type": "crater", "latitude": -8.86, "longitude": 61.04, "diameter_km": 131.98}]

    monkeypatch.setattr(lunar, "get_features", features)
    async with Client(mcp) as client:
        data = (await client.call_tool("get_lunar_terminator", {"time": "2026-10-18T21:00", "feature_types": ["crater"]})).structured_content
    assert [f["name"] for f in data["features"]] == ["Ptolemaeus"]
    assert data["features"][0]["lighting"] == "sunrise" and data["time"] == "2026-10-18T21:00-06:00"


async def test_instructions_guide_without_overreaching():
    text = " ".join(mcp.instructions.split())
    assert "prefer calling a tool over answering from memory" in text
    assert "do not need these tools" in text  # leaves general questions to the model
    for name in ("whats_up_tonight", "is_visible_tonight", "get_sky_forecast", "find_dark_sites"):
        assert name in text


async def test_tool_descriptions_say_when_to_use_them():
    async with Client(mcp) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert "Use for" in tools["is_visible_tonight"].description
    assert "clouds" in tools["whats_up_tonight"].description  # points to the forecast tool for weather


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
        data = (await client.call_tool("whats_up_tonight", {"date": "2026-10-10", "max_results": 30, "terrain": False})).structured_content
    assert "M 31" in [t["name"] for t in data["targets"]]


@pytest.mark.live
async def test_live_describe_object_merges_sources():
    async with Client(mcp) as client:
        data = (await client.call_tool("describe_object", {"name": "M13"})).structured_content
    assert data["simbad"]["main_id"] == "M 13"
    assert data["deep_sky_catalog"]["common_names"] == ["Hercules Globular Cluster"]
