"""Launch the server over stdio (as an MCP host would) and exercise every tool.

Usage:  uv run python scripts/smoke_test.py
"""

import asyncio
import json
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters

CALLS = [
    ("simbad_lookup", {"identifier": "Betelgeuse"}),
    ("simbad_lookup", {"identifier": "definitely not a star"}),
    ("simbad_cone_search", {"ra_deg": 83.633, "dec_deg": 22.0145, "radius_arcmin": 3, "limit": 3}),
    ("vsx_lookup", {"name": "R Leo"}),
    ("vsx_cone_search", {"ra_deg": 146.89, "dec_deg": 11.43, "radius_deg": 0.5, "max_mag": 12}),
    ("variable_stars_near", {"target": "M13", "radius_deg": 0.1, "limit": 3}),
    ("geocode_location", {"query": "Moab, Utah", "count": 1}),
    ("describe_object", {"name": "Ring Nebula"}),
    ("search_deep_sky", {"object_type": "globular_cluster", "max_magnitude": 6, "limit": 3}),
    ("identify_constellation", {"target": "Vega"}),
    ("get_position", {"target": "Jupiter", "place": "Moab, Utah"}),
    ("get_rise_set_transit", {"target": "M42", "place": "Moab, Utah"}),
    ("get_twilight_times", {"place": "Moab, Utah"}),
    ("get_moon_phases", {"days": 30}),
    ("get_planet_positions", {"place": "Moab, Utah"}),
    ("whats_up_tonight", {"place": "Moab, Utah", "bortle": 2, "max_results": 5}),
    ("is_visible_tonight", {"target": "Andromeda Galaxy", "place": "Moab, Utah"}),
    ("get_sky_forecast", {"place": "Moab, Utah"}),
    ("get_transparency_drivers", {"place": "Moab, Utah"}),
    ("best_night_this_month", {"target": "M31", "place": "Moab, Utah", "days": 20}),
    ("find_dark_moon_weekends", {"place": "Moab, Utah", "months": 2}),
    ("get_limiting_magnitude", {"equipment": "telescope", "aperture_mm": 200, "bortle": 4, "place": "Moab, Utah"}),
    ("get_light_pollution", {"place": "Moab, Utah"}),
    ("get_horizon_profile", {"place": "Moab, Utah"}),
    ("find_dark_sites", {"place": "Moab, Utah", "radius_km": 60, "max_results": 2}),
    ("get_eclipses", {"place": "Moab, Utah", "lunar_count": 2}),
    ("find_conjunctions", {"place": "Moab, Utah", "days": 120}),
    ("find_oppositions", {"years": 1}),
    ("get_jupiter_moons", {"place": "Moab, Utah"}),
    ("get_jupiter_events", {"place": "Moab, Utah", "hours": 24}),
    ("get_lunar_terminator", {"place": "Moab, Utah", "limit": 5}),
    ("get_moon_libration", {"place": "Moab, Utah"}),
    ("get_comet_visibility", {"place": "Moab, Utah", "limit": 3}),
    ("get_comet_visibility", {"comet": "12P", "place": "Moab, Utah", "days": 5}),
    ("get_asteroid_ephemeris", {"target": "Vesta", "place": "Moab, Utah", "days": 2}),
    ("find_close_approaches", {"days": 30, "limit": 3}),
    ("get_fireball_reports", {"limit": 3, "place": "Moab, Utah"}),
    ("get_iss_passes", {"place": "Moab, Utah"}),
    ("get_satellite_passes", {"satellite": "Hubble", "place": "Moab, Utah", "days": 3}),
    ("find_satellites_overhead", {"place": "Moab, Utah", "visible_only": False, "limit": 3}),
    ("get_starlink_trains", {"place": "Moab, Utah"}),
    ("get_space_weather", {"place": "Fairbanks, Alaska"}),
    ("get_upcoming_launches", {"limit": 2}),
]


async def main() -> int:
    params = StdioServerParameters(command=sys.executable, args=["-m", "astronomy_mcp"])
    failures = 0
    async with Client(params) as client:
        tools = await client.list_tools()
        print("Tools:", ", ".join(t.name for t in tools.tools))
        for name, args in CALLS:
            result = await client.call_tool(name, args)
            status = "ERROR" if result.is_error else "ok"
            failures += result.is_error
            payload = result.structured_content or [c.text for c in result.content]
            print(f"\n== {name}({args}) -> {status}")
            print(json.dumps(payload, indent=2)[:1200])
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
