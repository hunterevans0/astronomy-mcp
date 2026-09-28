# astronomy-mcp

An [MCP](https://modelcontextprotocol.io) server that gives AI assistants a working knowledge of the sky: what an object is, where it is, whether you can see it tonight, whether the weather will cooperate, and what's happening in space.

No API keys are required. Every source is free and public:

| Source | Used for |
| --- | --- |
| [SIMBAD](https://simbad.cds.unistra.fr/) (CDS) | Identifiers, coordinates, types and magnitudes for millions of objects |
| [AAVSO VSX](https://vsx.aavso.org/) | Variable stars: type, period, magnitude range |
| [OpenNGC](https://github.com/mattiaverga/OpenNGC) (CC-BY-SA 4.0) | NGC/IC/Messier/Caldwell deep-sky catalog, downloaded once and cached |
| [Astronomy Engine](https://github.com/cosinekitty/astronomy) | Offline ephemerides: planets, Moon, rise/set, twilight, phases, eclipses, constellations |
| [Open-Meteo](https://open-meteo.com/) | Geocoding, timezones, hourly cloud cover by layer, humidity, dew point, wind |
| [7Timer! ASTRO](https://www.7timer.info/) | Astronomical seeing and transparency |
| [NOAA SWPC](https://www.swpc.noaa.gov/) | Kp index, geomagnetic storm forecast, OVATION aurora nowcast |
| [Launch Library 2](https://thespacedevs.com/llapi) | Upcoming rocket launches (15 requests/hour, so cached 15 min) |

## Tools

Most tools take `latitude`/`longitude` or a `place` name. With neither, they use the saved default location.

**Location**

| Tool | What it does |
| --- | --- |
| `set_default_location` | Save where you observe from (and your Bortle class) to `~/.astronomy-mcp/config.json` |
| `get_default_location` | Show the saved location |
| `geocode_location` | Place name to coordinates, elevation and timezone |

**Planning tonight**

| Tool | What it does |
| --- | --- |
| `whats_up_tonight` | Ranked targets (planets, Moon, deep sky) for your equipment, sky darkness and moonlight |
| `is_visible_tonight` | Yes/no for one object, with reasons, best time, direction and Moon warnings |
| `get_sky_forecast` | Hour-by-hour cloud layers, dew risk, wind, seeing and transparency, plus a 0-100 score |
| `get_twilight_times` | Sunset, civil/nautical/astronomical twilight, dark window, moon-free dark hours |
| `get_limiting_magnitude` | Faintest stars and deep-sky objects reachable, from Bortle/SQM, aperture and moonlight |

**Where things are**

| Tool | What it does |
| --- | --- |
| `get_position` | Altitude, azimuth, compass direction, airmass, RA/Dec and constellation at any time |
| `get_rise_set_transit` | Rise, transit and set, including circumpolar and never-rises cases |
| `get_planet_positions` | Sun, Moon and planets: magnitude, phase, size, elongation, rise/set, Saturn ring tilt |
| `get_moon_phases` | Current phase and exact times of upcoming quarters and new moons |
| `get_eclipses` | Upcoming lunar eclipses, and solar eclipses visible from your location |
| `identify_constellation` | Which constellation an object or RA/Dec lies in |

**Catalogs**

| Tool | What it does |
| --- | --- |
| `describe_object` | Merged profile from SIMBAD, OpenNGC and VSX |
| `search_deep_sky` | Filter NGC/IC/Messier by type, constellation, magnitude, size, and optionally tonight's visibility |
| `simbad_lookup`, `simbad_cone_search` | Raw SIMBAD lookup by name, and search around an RA/Dec |
| `vsx_lookup`, `vsx_cone_search`, `variable_stars_near` | Variable stars by name, by position, or around a named target |

**Space**

| Tool | What it does |
| --- | --- |
| `get_space_weather` | Kp now and 3-day forecast, storm level, aurora probability at your location |
| `get_upcoming_launches` | Upcoming launches with windows, rockets, missions, pads and distance from you |

Targets can be planets, `Moon`, catalog names (`M31`, `NGC 7000`, `Caldwell 14`), common names (`Ring Nebula`) or anything SIMBAD resolves. Times come back in the observer's local time with a UTC offset. Coordinates are ICRS/J2000 decimal degrees.

Sky brightness, limiting magnitudes and visibility verdicts are model estimates. The Bortle class is supplied by the user because there is no light-pollution lookup yet. Without one, the tools assume Bortle 5 and say so in their output.

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```sh
pip install uv          # if you don't have it
uv sync                 # create .venv and install dependencies
```

## Using it

**Claude Code:** the repo includes a project-scoped [.mcp.json](.mcp.json). Open Claude Code in this folder, approve the `astronomy` server when prompted (or via `/mcp`), and then ask things like *"I'm in Moab with an 8-inch Dobsonian. What's worth looking at tonight, and will it be clear?"*

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
uv run pytest -m live                # tests that hit the real services
uv run python scripts/smoke_test.py  # launch over stdio and call every tool
```

Layout of `src/astronomy_mcp/`:

- `server.py`: MCP tool definitions. Its `@tool()` decorator turns expected failures (bad input, a service being down) into messages the model can read. Anything else is reported as a generic crash.
- `sky.py`: offline positional astronomy on Astronomy Engine (twilight, rise/set, fast bulk altitudes, eclipses).
- `planner.py`: target resolution (planet, then OpenNGC, then SIMBAD), visibility verdicts, and the `whats_up_tonight` ranking.
- `conditions.py`: sky-brightness model, limiting magnitude, weather forecast.
- `catalog.py`, `simbad.py`, `vsx.py`, `location.py`, `space.py`: one module per data source.
- `http.py`: shared HTTP client with an in-memory TTL cache.

To add a data source, write a client module and register tools in `server.py` with `@tool()`. [ROADMAP.md](ROADMAP.md) lists candidates.

Set `ASTRONOMY_MCP_HOME` to keep the config and catalog cache somewhere other than `~/.astronomy-mcp`.

Note: `www.aavso.org` is behind a Cloudflare bot challenge, so the VSX client calls `vsx.aavso.org` directly.
