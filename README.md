# astronomy-mcp

An [MCP](https://modelcontextprotocol.io) server that gives AI assistants a working knowledge of the sky: what an object is, where it is, whether you can see it tonight from where you are, whether the weather and the local light pollution will cooperate, where to drive for a darker sky, and what's happening in space.

No API keys are required. Every source is free and public:

| Source | Used for |
| --- | --- |
| [SIMBAD](https://simbad.cds.unistra.fr/) (CDS) | Identifiers, coordinates, types and magnitudes for millions of objects |
| [AAVSO VSX](https://vsx.aavso.org/) | Variable stars: type, period, magnitude range |
| [OpenNGC](https://github.com/mattiaverga/OpenNGC) (CC-BY-SA 4.0) | NGC/IC/Messier/Caldwell deep-sky catalog, downloaded once and cached |
| [Astronomy Engine](https://github.com/cosinekitty/astronomy) | Offline ephemerides: planets, Moon, rise/set, twilight, phases, eclipses, constellations, Jupiter's moons, lunar libration |
| [Gazetteer of Planetary Nomenclature](https://planetarynames.wr.usgs.gov/) (IAU/USGS) | Named lunar features with positions and sizes, downloaded once and cached |
| [Open-Meteo](https://open-meteo.com/) | Geocoding, timezones, hourly cloud cover by layer, humidity, dew point, wind, terrain elevation (Copernicus DEM), aerosols and dust (CAMS) |
| [Light Pollution Atlas 2025](https://djlorenz.github.io/astronomy/lp/) (D. Lorenz, VIIRS data) | Artificial sky brightness anywhere, read from the atlas's map tiles and cached |
| [OpenStreetMap](https://www.openstreetmap.org/) via Overpass (ODbL) | Campgrounds, viewpoints and trailheads near candidate dark sites |
| [OpenTopoData](https://www.opentopodata.org/) | Fallback terrain elevation (SRTM 90 m) when Open-Meteo is rate-limited |
| [7Timer! ASTRO](https://www.7timer.info/) | Astronomical seeing and transparency |
| [NOAA SWPC](https://www.swpc.noaa.gov/) | Kp index, geomagnetic storm forecast, OVATION aurora nowcast |
| [Launch Library 2](https://thespacedevs.com/llapi) | Upcoming rocket launches (15 requests/hour, so cached 15 min) |
| [JPL Solar System Dynamics](https://ssd-api.jpl.nasa.gov/) | Comet and asteroid orbits and physical data (SBDB), ephemerides (Horizons), Earth close approaches (CAD) |
| [CNEOS fireballs](https://cneos.jpl.nasa.gov/fireballs/) | Bolides detected by US government sensors |
| [COBS](https://cobs.si/) | Observed comet brightness: light-curve fits and individual observers' reports |
| [Project Pluto](https://www.projectpluto.com/grs_lon.txt) | JUPOS measurements of the Great Red Spot's longitude (fetched weekly) |
| [Washington Double Star catalog](https://www.astro.gsu.edu/wds/) via [VizieR](https://vizier.cds.unistra.fr/) | Double and multiple stars: separations, position angles, magnitudes |
| [AAVSO International Database](https://www.aavso.org/) (via VSX) | Recent variable-star observations and light curves |
| [Latest Supernovae](https://www.rochesterastronomy.org/supernova.html) (D. Bishop) | Active supernovae brighter than magnitude 17, and novae in other galaxies (cached 6 hours) |
| [Recent Galactic novae](https://asd.gsfc.nasa.gov/Koji.Mukai/novae/novae.html) (K. Mukai, NASA GSFC) | Novae in our Galaxy with discovery dates and peak magnitudes |
| [ALeRCE](https://alerce.science/) | Machine-classified supernova candidates from ZTF alerts |
| [DSN Now](https://eyes.nasa.gov/dsn/dsn.html) | Live Deep Space Network antenna activity |
| [CelesTrak](https://celestrak.org/) | Satellite orbital elements, propagated with [SGP4](https://pypi.org/project/sgp4/) (cached 2 hours, as CelesTrak asks), and the satellite catalog's radar sizes for rough brightness |

## Tools

Most tools take `latitude`/`longitude` or a `place` name. With neither, they use the saved default location.

**Location**

| Tool | What it does |
| --- | --- |
| `set_default_location` | Save where you observe from to `~/.astronomy-mcp/config.json`; reports the site's light pollution |
| `get_default_location` | Show the saved location |
| `geocode_location` | Place name to coordinates, elevation and timezone |

**Planning tonight**

| Tool | What it does |
| --- | --- |
| `whats_up_tonight` | Ranked targets (planets, Moon, deep sky) with difficulty, for your equipment, sky darkness, moonlight and terrain |
| `is_visible_tonight` | Yes/no for one object, with reasons (too low, behind terrain, too faint), best time, direction, suggested magnification |
| `get_sky_forecast` | Hour-by-hour cloud layers, dew risk, wind, seeing and transparency, plus a 0-100 score |
| `get_twilight_times` | Sunset, civil/nautical/astronomical twilight, dark window, moon-free dark hours |
| `get_transparency_drivers` | Smoke, dust and aerosols through the night: transparency rating, likely cause, extra extinction |
| `get_limiting_magnitude` | Faintest stars reachable, from sky darkness, aperture and moonlight |

**Planning ahead**

| Tool | What it does |
| --- | --- |
| `best_night_this_month` | Scores upcoming nights for a target (or for dark-sky observing) on altitude, moonlight and cloud forecast |
| `find_dark_moon_weekends` | Weekends with the Moon down for most of the dark hours, up to two years out |

**Sites**

| Tool | What it does |
| --- | --- |
| `get_light_pollution` | Atlas zone, sky brightness (mag/arcsec²), estimated Bortle class and naked-eye limit anywhere |
| `find_dark_sites` | Darker spots within a radius, darkest then nearest, each with nearby campgrounds, viewpoints or trailheads |
| `get_horizon_profile` | How high the terrain rises in each direction, from a 90 m elevation model out to 35 km |

**Where things are**

| Tool | What it does |
| --- | --- |
| `get_position` | Altitude, azimuth, compass direction, airmass, RA/Dec and constellation at any time |
| `get_rise_set_transit` | Rise, transit and set, including circumpolar and never-rises cases |
| `get_planet_positions` | Sun, Moon and planets: magnitude, phase, size, elongation, rise/set, Saturn ring tilt |
| `get_moon_phases` | Current phase and exact times of upcoming quarters and new moons |
| `get_eclipses` | Upcoming lunar eclipses, and solar eclipses visible from your location |
| `identify_constellation` | Which constellation an object or RA/Dec lies in |
| `find_conjunctions` | Close pairings of planets, optionally with the Moon and bright stars (Regulus, Spica, the Pleiades...), with separation and morning/evening sky |
| `find_oppositions` | Oppositions of Mars through Neptune: date, brightness, apparent size, closest approach to Earth |
| `find_greatest_elongations` | Mercury's and Venus's best evening and morning showings, with altitude at twilight |

**Jupiter and the Moon up close**

| Tool | What it does |
| --- | --- |
| `get_jupiter_moons` | Where the four Galilean moons are, which are hidden or in transit, central meridian and Great Red Spot position |
| `get_jupiter_events` | Upcoming moon transits, shadow transits, occultations, eclipses, Red Spot transits and (in season) moons occulting and eclipsing each other, flagged for your sky |
| `get_lunar_terminator` | Named craters, mountains and rilles in low sunlight on the terminator, with the Sun's height at each |
| `get_moon_libration` | Libration angles, the favoured limb, and which limb features (Mare Orientale, Bailly, polar craters) are well placed |

**Comets, asteroids and fireballs**

| Tool | What it does |
| --- | --- |
| `get_comet_visibility` | Comets bright enough to see now, with where and when tonight; or one comet's view tonight, its brightness trend and the latest observers' reports |
| `find_bright_asteroids` | Asteroids bright enough for binoculars or a small telescope, with where and when tonight |
| `get_asteroid_ephemeris` | Position, brightness, motion and altitude over time for any asteroid or comet, plus its size and orbit class |
| `find_close_approaches` | Asteroids and comets passing near Earth: time, distance in lunar distances, speed, size |
| `get_fireball_reports` | Recent large bolides: time, place, energy, and whether one was above your horizon |

**Satellites**

| Tool | What it does |
| --- | --- |
| `get_iss_passes` | Visible ISS passes: where it appears, peaks and vanishes, to the second, with brightness |
| `get_satellite_passes` | The same for any satellite by name or NORAD number, optionally including passes you can't see |
| `find_satellites_overhead` | What's up right now, where each satellite is heading, and when it leaves view |
| `get_starlink_trains` | Recent Starlink batches (including ones not yet named in the catalog), how stretched out each train is, and when it passes over |
| `predict_iss_transit` | The ISS crossing the Sun or Moon: the nearest point on the centerline, path width, time to the millisecond |

**Double stars, variable stars and transients**

| Tool | What it does |
| --- | --- |
| `get_double_star` | Every pair in a double or multiple star, and whether your telescope can split each and at what power |
| `find_splittable_doubles` | Doubles your aperture and seeing can split, brightest first, optionally just those up tonight |
| `get_variable_star_status` | Latest AAVSO brightness, trend, place in its range (outburst?), next maximum or eclipse |
| `get_light_curve` | Binned AAVSO light curve by band, up to two years |
| `get_recent_supernovae` | Supernovae bright enough for amateurs, with host, type, magnitudes and tonight's visibility; optional ALeRCE candidates |
| `get_novae` | Recent Galactic novae with peak and current brightness; optionally novae in M31 and other galaxies |

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
| `get_dsn_status` | Which spacecraft the Deep Space Network is talking to now, how far away, and whether data is flowing |

Targets can be planets, `Moon`, catalog names (`M31`, `NGC 7000`, `Caldwell 14`), common names (`Ring Nebula`) or anything SIMBAD resolves. Times come back in the observer's local time with a UTC offset. Coordinates are ICRS/J2000 decimal degrees.

### How visibility is judged

- **Sky brightness** comes from, in order: an SQM reading or Bortle class the user gives, a Bortle class saved with the location, then the light-pollution atlas. Output always says which one was used.
- **Moonlight** brightens the sky by the Moon's phase and altitude, and more strongly close to the Moon (Krisciunas & Schaefer 1991).
- **Detectability** uses a threshold model at the eyepiece. The telescope darkens the sky and magnifies the object; the eye's threshold depends on the background brightness and the object's apparent size; the model tries several magnifications and keeps the best one. Galaxies and globular clusters are treated as their brighter cores.
- **Calibration:** the model's two free constants are tuned against 53 benchmark cases in [tests/test_visibility.py](tests/test_visibility.py). The cases come from Bortle's published class descriptions, the hardest Messier objects in a 100 mm scope, city-sky observing, and 10x50 binocular targets. It passes all 53. Borderline cases (M33 at Bortle 4, M31 at Bortle 7) land near zero margin by design.
- **Terrain:** targets behind hills are excluded using a cached horizon profile. Trees and buildings aren't in the elevation model.

- **Comparing nights:** `best_night_this_month` multiplies four factors, each 0 to 1: time the target spends above the minimum altitude in darkness (full credit at 2 hours), the sine of its peak altitude, moonlight (how much the Moon brightens the sky at the target's distance from it; 3 mag or more scores zero), and the clear fraction of the cloud forecast. Planets and the Moon skip the moonlight factor. Nights past the forecast are ranked in their own list.

These are estimates. Observer experience, transparency and eyesight shift real results by half a magnitude or more.

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```sh
pip install uv          # if you don't have it
uv sync                 # create .venv and install dependencies
```

## Using it

**Claude Code:** the repo includes a project-scoped [.mcp.json](.mcp.json). Open Claude Code in this folder, approve the `astronomy` server when prompted (or via `/mcp`), and then ask things like *"I'm in Moab with an 8-inch Dobsonian. What's worth looking at tonight, and will it be clear?"*

**Claude Desktop:**

1. Run `uv sync` in this folder so `.venv` has every dependency.
2. Open the Desktop config file. The quickest way is **Settings → Developer → Edit Config**. On disk it is at:
   - Windows, Microsoft Store install: `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json`
   - Windows, direct download: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
3. Add the server under `mcpServers`, pointing at the project's own `.venv` Python so it doesn't depend on which `python` is on your PATH:

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

4. Quit Claude Desktop completely (right-click the tray icon → Quit; closing the window isn't enough) and start it again. Desktop only reads the config and starts servers at launch, so do this after every code change too.
5. Check **Settings → Developer**: `astronomy` should show as running. If it failed, the log is `mcp-server-astronomy.log` in the `logs` folder next to the config file.

The first deep-sky question downloads the OpenNGC catalog (about 4 MB), and the first lunar-terminator question downloads the USGS lunar gazetteer (about 24 MB, kept as a 200 KB extract). Light-pollution tiles and horizon profiles download as needed. Everything is cached in `~/.astronomy-mcp`.

**Other MCP hosts:** use the same command and arguments as for Claude Desktop.

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
- `planner.py`: target resolution (planet, then OpenNGC, then SIMBAD), visibility verdicts, the `whats_up_tonight` ranking, night-by-night scoring and dark-moon weekends.
- `visibility.py`: the detection-threshold model (calibrated in `tests/test_visibility.py`).
- `conditions.py`: sky-brightness and moonlight model, limiting magnitude, weather forecast.
- `airquality.py`: aerosol optical depth, dust and fine particles, and what they do to transparency.
- `jupiter.py`: Galilean moon geometry seen from Earth and from the Sun, event search, central meridian, Great Red Spot (built-in value plus Project Pluto's JUPOS table) and mutual events.
- `lunar.py`: the Moon's orientation (libration, subsolar point), the terminator, and the USGS feature gazetteer.
- `almanac.py`: conjunctions and oppositions.
- `smallbodies.py`: two-body comet orbits, the bright-comet list (COBS brightness, Horizons positions), Horizons ephemerides, close approaches and fireballs.
- `satellites.py`: CelesTrak elements, SGP4 to topocentric, Earth's shadow, brightness, pass search, satellites overhead and Starlink trains.
- `lightpollution.py`, `darksites.py`, `horizon.py`: atlas lookup, dark-site search, terrain horizon.
- `doubles.py`: WDS queries and the rule of thumb for splitting a pair (Dawes limit, seeing, brightness difference).
- `variables.py`: AAVSO observations, trends, range position, predicted maxima and eclipses, light curves.
- `transients.py`: the Latest Supernovae and Galactic novae pages, and ALeRCE candidates.
- `catalog.py`, `simbad.py`, `vsx.py`, `location.py`, `space.py`, `dsn.py`: one module per data source.
- `http.py`: shared HTTP client with an in-memory TTL cache.

To add a data source, write a client module and register tools in `server.py` with `@tool()`. [ROADMAP.md](ROADMAP.md) lists candidates.

Set `ASTRONOMY_MCP_HOME` to keep the config and caches (catalog, atlas tiles, horizon profiles) somewhere other than `~/.astronomy-mcp`.

The server's `instructions` and each tool's description tell the model when a tool is the right source: questions that depend on date, time or location, or that need sourced catalog numbers. They also say general astronomy questions don't need the tools. Keep that balance when adding tools: say when to use the tool, and avoid wording that pushes every astronomy question through it.

Service notes:

- `www.aavso.org` is behind a Cloudflare bot challenge, so the VSX client calls `vsx.aavso.org` directly.
- Open-Meteo counts every coordinate against a 600-per-minute limit, so horizon profiles use 433 points and fall back to OpenTopoData.
- CelesTrak blocks clients that download the same file more than once every two hours, so satellite elements are cached on disk for two hours, and a stale copy is used if a refresh fails.
- Horizons accepts `DES=<SPK-ID>;` for both comets and asteroids, but a bare SPK-ID fails for most asteroids, so names are resolved with SBDB first. Comets add `CAP;NOFRAG` to get the current apparition.
- SBDB's elements for a periodic comet can be from an earlier apparition (10P's are from 2015), so two-body positions can be degrees off. The bright-comet list uses them only to pick candidates.
- JUPOS itself only publishes the Red Spot's longitude as a chart image, so the measurements come from Project Pluto's `grs_lon.txt`. The newer of that table's last point and the built-in value wins.
- Sources looked at and not used: the American Meteor Society's fireball data (the public viewer's data files are deliberately obfuscated, and the keyed API was down); Mini-MegaTORTORA's satellite magnitudes (its `robots.txt` disallows automated access); TNS, which asks scripted clients to register bot credentials; ASAS-SN Sky Patrol, whose API server did not answer; and the Fink broker, which was unreachable.
- AAVSO observations come from `vsx.aavso.org` (`view=api.delim`) with `|` as delimiter, since some fields contain commas. Busy stars have tens of thousands of observations a year, so light curves stop at two years.
- The Latest Supernovae page is about 3.5 MB and asks crawlers to wait 10 s between requests; it is cached for 6 hours.
- Public Overpass servers are often overloaded. `find_dark_sites` asks several mirrors at once and still returns sites, flagged as unchecked for access, if none answer.
