# astronomy-mcp

An [MCP](https://modelcontextprotocol.io) server that gives AI assistants access to astronomy catalogs:

- **[SIMBAD](https://simbad.cds.unistra.fr/)** (CDS): identifiers, coordinates, object types, magnitudes, parallax, and so on for millions of objects, queried over its TAP/ADQL service.
- **[AAVSO VSX](https://vsx.aavso.org/)**: the International Variable Star Index (variability type, period, magnitude range).

No API keys are required. Both services are public.

## Tools

| Tool | What it does |
| --- | --- |
| `simbad_lookup` | Look up any object by name or ID (`M31`, `Betelgeuse`, `HD 39801`) |
| `simbad_cone_search` | Objects within N arcmin of an RA/Dec, filterable by object type and V magnitude |
| `vsx_lookup` | Look up a variable star (`R Leo`, `Mira`, `SS Cyg`) |
| `vsx_cone_search` | Variable stars within N degrees of an RA/Dec |
| `variable_stars_near` | Resolve a target name via SIMBAD, then list VSX variables around it |

Coordinates are ICRS/J2000 decimal degrees.

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```sh
pip install uv          # if you don't have it
uv sync                 # create .venv and install dependencies
```

## Using it

**Claude Code:** the repo includes a project-scoped [.mcp.json](.mcp.json). Open Claude Code in this folder, approve the `astronomy` server when prompted (or via `/mcp`), and then ask things like *"What variable stars are near M13?"*

**Claude Desktop / other MCP hosts:** run `uv sync` first, then point the host at the project's own `.venv` Python. That way the server doesn't depend on which `python` is on the host's PATH:

```json
{
  "mcpServers": {
    "astronomy": {
      "command": "C:/Users/moab/GitRepos/astronomy-mcp/.venv/Scripts/python.exe",
      "args": ["-m", "astronomy_mcp"]
    }
  }
}
```

**Interactive inspector** (browser UI to call tools by hand; needs Node):

```sh
uv run mcp dev src/astronomy_mcp/server.py
```

## Development

```sh
uv run pytest                        # offline tests
uv run pytest -m live                # tests that hit SIMBAD/VSX
uv run python scripts/smoke_test.py  # launch over stdio and call every tool
```

Layout: `src/astronomy_mcp/simbad.py` and `vsx.py` are thin async HTTP clients, and `server.py` defines the MCP tools. To add a data source, write a client module and register tools in `server.py` with `@mcp.tool()`.

Note: `www.aavso.org` is behind a Cloudflare bot challenge, so the VSX client calls `vsx.aavso.org` directly.
