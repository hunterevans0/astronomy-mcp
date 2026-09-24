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
