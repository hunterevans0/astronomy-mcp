"""MCP server for astronomy: catalogs, sky positions, observing plans, conditions, and spaceflight."""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from astronomy_mcp import (
    airquality, almanac, catalog, conditions, darksites, horizon, jupiter, lightpollution, location, lunar, planner,
    satellites, simbad, sky, smallbodies, space, vsx,
)
from astronomy_mcp.http import UpstreamError
from astronomy_mcp.location import Location

mcp = MCPServer(
    name="astronomy",
    title="Astronomy Data",
    version="0.3.0",
    log_level="WARNING",
    instructions=(
        "Tools for observational astronomy: what is in the sky from a given place and time, whether "
        "and when something can be seen, observing conditions (clouds, darkness, light pollution, "
        "terrain), sourced catalog facts about celestial objects, comets, asteroids, satellites, "
        "eclipses, space weather and rocket launches.\n\n"
        "When an answer depends on the date, time or the observer's location (what is up tonight, "
        "where a planet is, rise/set or twilight times, Moon phase, whether an object is visible, the "
        "cloud forecast, how dark a site is), prefer calling a tool over answering from memory: these "
        "values change daily and by location, and recalled numbers are often wrong. For catalog facts "
        "such as magnitudes, sizes, distances and variability, the tools return sourced values; use "
        "them when the specific numbers matter.\n\n"
        "Questions about general astronomy knowledge, history, physics, or how to use equipment do "
        "not need these tools; answer those directly.\n\n"
        "Routing: 'what should I look at tonight' -> whats_up_tonight; 'can I see X' -> "
        "is_visible_tonight; 'will it be clear' -> get_sky_forecast; 'is it smoky or hazy' -> "
        "get_transparency_drivers; 'which night is best' -> best_night_this_month; 'when is the next "
        "new-moon weekend' -> find_dark_moon_weekends; 'how dark is it here' -> "
        "get_light_pollution; 'where can I go for darker skies' -> find_dark_sites; 'tell me about X' "
        "-> describe_object; planet positions -> get_planet_positions; Moon phases -> get_moon_phases; "
        "Jupiter's moons or Red Spot -> get_jupiter_moons, get_jupiter_events; what to look at on the "
        "Moon -> get_lunar_terminator, get_moon_libration; planets close together or at their best -> "
        "find_conjunctions, find_oppositions; Mercury or Venus at their best -> "
        "find_greatest_elongations; asteroids to look for -> find_bright_asteroids; ISS crossing the "
        "Sun or Moon -> predict_iss_transit; "
        "comets -> get_comet_visibility; where an asteroid or comet is -> get_asteroid_ephemeris; "
        "asteroids passing Earth -> find_close_approaches; bolides -> get_fireball_reports; ISS "
        "sightings -> get_iss_passes; other satellites -> get_satellite_passes; 'what is that moving "
        "light' -> find_satellites_overhead; Starlink trains -> get_starlink_trains; "
        "aurora -> get_space_weather; launches -> get_upcoming_launches.\n\n"
        "Location: tools take latitude/longitude or a place name, and otherwise use the saved "
        "default. When the user says where they observe from, call set_default_location once. If no "
        "location is known and the question needs one, ask the user.\n\n"
        "If a tool finds no match or a service is unavailable, say so rather than substituting "
        "remembered values. Visibility verdicts, sky brightness and limiting magnitudes are model "
        "estimates; present them that way. Times come back in the observer's local time with a UTC "
        "offset; coordinates are ICRS/J2000 degrees."
    ),
)

# Failures we expect (bad input, an upstream service down) become ToolError so the model sees
# the message; anything else is a crash and the SDK reports it generically.
ANTICIPATED = (ValueError, UpstreamError, simbad.SimbadError, vsx.VSXError)


def tool(**kwargs: Any) -> Callable[[Callable[..., Awaitable[Any]]], Any]:
    def decorate(fn: Callable[..., Awaitable[Any]]) -> Any:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kw: Any) -> Any:
            try:
                return await fn(*args, **kw)
            except ANTICIPATED as exc:
                raise ToolError(str(exc)) from exc

        return mcp.tool(**kwargs)(wrapper)

    return decorate


READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=True, idempotent_hint=True)

RA = Annotated[float, Field(ge=0, lt=360, description="Right ascension, decimal degrees (ICRS/J2000)")]
DEC = Annotated[float, Field(ge=-90, le=90, description="Declination, decimal degrees (ICRS/J2000)")]
LAT = Annotated[float | None, Field(ge=-90, le=90, description="Observer latitude in degrees (north positive). Omit to use place or the saved default.")]
LON = Annotated[float | None, Field(ge=-180, le=180, description="Observer longitude in degrees (east positive). Omit to use place or the saved default.")]
PLACE = Annotated[str | None, Field(description="Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.")]
DATE = Annotated[str | None, Field(description="Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.")]
TIME = Annotated[str | None, Field(description="ISO 8601 time; without an offset it is the observer's local time. Omit for now.")]
TARGET = Annotated[str, Field(description="Planet, 'Moon', catalog name (M42, NGC 7000, Caldwell 14), common name (Ring Nebula) or SIMBAD identifier")]
EQUIPMENT = Annotated[Literal["naked_eye", "binoculars", "telescope"], Field(description="What the observer is using")]
APERTURE = Annotated[float | None, Field(gt=0, le=2000, description="Aperture in mm (defaults: binoculars 50, telescope 150)")]
BORTLE = Annotated[int | None, Field(ge=1, le=9, description="Bortle class of the sky (1 pristine to 9 inner city). Omit to use the saved value or the light-pollution atlas.")]
TERRAIN = Annotated[bool, Field(description="Account for hills and mountains on the local horizon (first use per location takes a few seconds)")]
MIN_ALT = Annotated[float, Field(ge=0, le=80, description="Minimum useful altitude in degrees")]


async def _location_or_none(latitude: float | None, longitude: float | None, place: str | None) -> Location | None:
    if latitude is None and longitude is None and not place:
        return location.load_default()
    return await location.resolve(latitude, longitude, place)


async def _sky_brightness(loc: Location, bortle: int | None = None, sqm: float | None = None) -> tuple[float, str]:
    """(zenith sky brightness in mag/arcsec^2, where that number came from).

    The user's own numbers win; then the light-pollution atlas; then a suburban guess.
    """
    if sqm is not None:
        return sqm, "measured SQM supplied by user"
    if bortle is not None:
        return conditions.sqm_from_bortle(bortle), f"Bortle {bortle} supplied by user"
    if loc.bortle is not None:
        return conditions.sqm_from_bortle(loc.bortle), f"Bortle {loc.bortle} from saved location"
    try:
        lp = await lightpollution.sky_brightness(loc.latitude, loc.longitude)
        return lp["sky_brightness_mag_arcsec2"], f"light pollution atlas (zone {lp['zone']}, about Bortle {lp['bortle_estimate']})"
    except (UpstreamError, ValueError):
        return conditions.sqm_from_bortle(5), "assumed Bortle 5 (atlas unavailable); pass bortle to override"


async def _horizon_or_none(loc: Location, terrain: bool) -> tuple[horizon.Horizon | None, str | None]:
    if not terrain:
        return None, None
    try:
        return await horizon.get_horizon(loc), None
    except (UpstreamError, ValueError, KeyError) as exc:
        return None, f"Terrain horizon unavailable ({exc}); results ignore hills."


async def _catalog_or_none() -> catalog.Catalog | None:
    try:
        return await catalog.get_catalog()
    except UpstreamError:
        return None


# ================================================================ location

@tool(annotations=READ_ONLY)
async def geocode_location(
    query: Annotated[str, Field(description="Place name, optionally qualified: 'Moab, Utah', 'Cherry Springs State Park'")],
    count: Annotated[int, Field(ge=1, le=10, description="Maximum candidates")] = 5,
) -> dict[str, Any]:
    """Turn a place name into coordinates, elevation and timezone (Open-Meteo geocoder).

    Useful when a place is ambiguous and the user should pick; other tools also accept a
    place name directly.
    """
    results = await location.geocode(query, count)
    return {"count": len(results), "results": results}


@tool(
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=True)
)
async def set_default_location(
    place: PLACE = None,
    latitude: LAT = None,
    longitude: LON = None,
    name: Annotated[str | None, Field(description="Friendly name to store, e.g. 'Backyard'")] = None,
    bortle: BORTLE = None,
) -> dict[str, Any]:
    """Save the observer's default location so later questions don't need it repeated.

    Call this when the user tells you where they usually observe from. Only pass bortle if
    the user states it; otherwise sky darkness comes from the light-pollution atlas, which
    this call reports. Stored in ~/.astronomy-mcp/config.json across sessions.
    """
    if latitude is None and longitude is None and not place:
        raise ValueError("Give a place name or latitude/longitude.")
    loc = await location.resolve(latitude, longitude, place)
    if name:
        loc.name = name
    if bortle is not None:
        loc.bortle = bortle
    location.save_default(loc)
    out: dict[str, Any] = {"saved": True, "default_location": loc.to_dict()}
    try:
        out["light_pollution"] = await lightpollution.sky_brightness(loc.latitude, loc.longitude)
    except (UpstreamError, ValueError):
        pass
    return out


@tool(annotations=READ_ONLY)
async def get_default_location() -> dict[str, Any]:
    """Show the saved default observing location, if any."""
    loc = location.load_default()
    if loc is None:
        return {"set": False, "message": "No default location saved. Use set_default_location."}
    return {"set": True, "default_location": loc.to_dict()}


# ================================================================ catalogs


@tool(annotations=READ_ONLY)
async def simbad_lookup(
    identifier: Annotated[
        str,
        Field(description="Any SIMBAD identifier or common name, e.g. 'M31', 'Betelgeuse', 'HD 39801', 'NGC 1976'"),
    ],
) -> dict[str, Any]:
    """Look up a celestial object in SIMBAD by name or catalog identifier.

    Returns coordinates, object type, spectral/morphological type, parallax (and derived
    distance), proper motion, radial velocity, redshift, multi-band magnitudes and aliases.
    describe_object is usually the better first call; use this for raw SIMBAD data.
    """
    obj = await simbad.lookup(identifier)
    if obj is None:
        return {"found": False, "message": f"SIMBAD has no object matching '{identifier}'."}
    return {"found": True, **obj}


@tool(annotations=READ_ONLY)
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
    """Find SIMBAD objects within a radius of a sky position, sorted nearest first.

    For questions like 'what is at these coordinates' or 'what else is near this object'.
    """
    results = await simbad.cone_search(ra_deg, dec_deg, radius_arcmin, limit, object_type, max_v_mag)
    return {"count": len(results), "objects": results}


@tool(annotations=READ_ONLY)
async def vsx_lookup(
    name: Annotated[str, Field(description="Variable star name, e.g. 'R Leo', 'Mira', 'SS Cyg', 'delta Cep'")],
) -> dict[str, Any]:
    """Look up a variable star in the AAVSO International Variable Star Index (VSX).

    Returns variability type, period, epoch, magnitude range, spectral type, discoverer,
    constellation and a link to the VSX detail page. Use for periods and brightness ranges
    of variable stars rather than recalling them.
    """
    obj = await vsx.lookup(name)
    if obj is None:
        return {"found": False, "message": f"VSX has no variable star named '{name}'."}
    return {"found": True, **obj}


@tool(annotations=READ_ONLY)
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


@tool(annotations=READ_ONLY)
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


@tool(annotations=READ_ONLY)
async def describe_object(name: TARGET) -> dict[str, Any]:
    """Sourced profile of a star, galaxy, nebula, cluster or planet: type, coordinates,
    magnitudes, distance, size, common names, variability and constellation.

    A good first call for 'tell me about X' or 'how far/bright/big is X' when specific numbers
    matter. Merges SIMBAD, OpenNGC and AAVSO VSX; planets get their current apparent details.
    """
    key = name.strip().lower()
    if key in sky.BODIES:
        return {"found": True, "solar_system_body": sky.body_details(key, datetime.now(UTC), location.load_default())}

    async def safe(coro):
        try:
            return await coro
        except (UpstreamError, simbad.SimbadError, vsx.VSXError) as exc:
            return exc

    cat, simbad_obj, vsx_obj = await asyncio.gather(safe(catalog.get_catalog()), safe(simbad.lookup(name)), safe(vsx.lookup(name)))
    errors = {src: str(v) for src, v in (("OpenNGC", cat), ("SIMBAD", simbad_obj), ("VSX", vsx_obj)) if isinstance(v, Exception)}
    ngc = cat.lookup(name) if isinstance(cat, catalog.Catalog) else None
    simbad_obj = simbad_obj if isinstance(simbad_obj, dict) else None
    vsx_obj = vsx_obj if isinstance(vsx_obj, dict) else None
    if simbad_obj is None and ngc is not None:
        # Catalog names SIMBAD doesn't know (e.g. 'Caldwell 41') can still be found by another id.
        for alt in [ngc["name"], *ngc.get("other_ids", [])[:3]]:
            try:
                if simbad_obj := await simbad.lookup(alt):
                    break
            except simbad.SimbadError:
                break
    if not (simbad_obj or ngc or vsx_obj):
        return {"found": False, "message": f"No catalog knows '{name}'.", "source_errors": errors or None}

    base = simbad_obj or ngc or vsx_obj
    out: dict[str, Any] = {"found": True, "query": name}
    if base.get("ra_deg") is not None:
        out["constellation"] = sky.constellation(base["ra_deg"], base["dec_deg"])
    if simbad_obj:
        out["simbad"] = simbad_obj
    if ngc:
        out["deep_sky_catalog"] = ngc
    if vsx_obj:
        out["variable_star"] = vsx_obj
    if errors:
        out["source_errors"] = errors
    return out


@tool(annotations=READ_ONLY)
async def search_deep_sky(
    object_type: Annotated[
        Literal[tuple(catalog.GROUPS)] | None,  # type: ignore[valid-type]
        Field(description="Kind of object to return"),
    ] = None,
    constellation: Annotated[str | None, Field(description="IAU constellation name or abbreviation, e.g. 'Sagittarius' or 'Sgr'")] = None,
    max_magnitude: Annotated[float | None, Field(description="Only objects at this magnitude or brighter")] = None,
    min_size_arcmin: Annotated[float | None, Field(ge=0, description="Minimum major-axis size in arcminutes")] = None,
    messier_only: Annotated[bool, Field(description="Only Messier objects")] = False,
    name_contains: Annotated[str | None, Field(description="Substring of a catalog or common name, e.g. 'Veil'")] = None,
    visible_tonight: Annotated[bool, Field(description="Only objects that clear min_altitude during tonight's dark window (needs a location)")] = False,
    min_altitude: MIN_ALT = 25.0,
    date: DATE = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
    limit: Annotated[int, Field(ge=1, le=200, description="Maximum results")] = 25,
) -> dict[str, Any]:
    """Find deep-sky objects by kind, constellation, brightness or size, brightest first.

    For requests like 'bright planetary nebulae', 'Messier objects in Sagittarius' or
    'large galaxies visible tonight'. Covers NGC, IC, Messier and Caldwell extras (OpenNGC).
    For a ranked plan of what to observe tonight, whats_up_tonight is usually better.
    """
    const_abbr = None
    if constellation:
        const_abbr = catalog.constellation_abbrev(constellation)
        if const_abbr is None:
            raise ValueError(f"'{constellation}' is not an IAU constellation name or abbreviation.")
    cat = await catalog.get_catalog()
    results = cat.search(object_type, const_abbr, max_magnitude, min_size_arcmin, messier_only, name_contains)
    extra: dict[str, Any] = {}
    if visible_tonight:
        loc = await location.resolve(latitude, longitude, place)
        n = sky.night(loc, sky.observing_date(date, loc))
        times = [n.window[0] + (n.window[1] - n.window[0]) * i / 24 for i in range(25)]
        tracks = sky.fast_tracks([(o["ra_deg"], o["dec_deg"]) for o in results], times, loc)
        visible = []
        for obj, track in zip(results, tracks):
            best = max(range(len(track)), key=lambda i: track[i][0])
            if track[best][0] >= min_altitude:
                visible.append({**obj, "best_time": sky.fmt(times[best], loc), "altitude_at_best_deg": round(track[best][0])})
        results = visible
        extra = {"night": {"date": n.date.isoformat(), "dark_window": n.to_dict(loc)["dark_window"]}}
    trimmed = [{k: v for k, v in o.items() if k != "other_ids"} for o in results[:limit]]
    return {"total_matches": len(results), "count": len(trimmed), "objects": trimmed, **extra,
            "source": "OpenNGC (CC-BY-SA 4.0)"}


@tool(annotations=READ_ONLY)
async def identify_constellation(
    target: Annotated[str | None, Field(description="Object name to locate; alternatively give ra_deg/dec_deg")] = None,
    ra_deg: Annotated[float | None, Field(ge=0, lt=360, description="Right ascension, decimal degrees (J2000)")] = None,
    dec_deg: Annotated[float | None, Field(ge=-90, le=90, description="Declination, decimal degrees (J2000)")] = None,
) -> dict[str, Any]:
    """Which IAU constellation an object or RA/Dec lies in, using the official boundaries.

    Planets move between constellations, so use this rather than recalling where one is.
    """
    if target:
        t = await planner.resolve_target(target)
        ra, dec = sky.j2000_position(t, datetime.now(UTC))
        name = t.name
    elif ra_deg is not None and dec_deg is not None:
        ra, dec, name = ra_deg, dec_deg, None
    else:
        raise ValueError("Give a target name or both ra_deg and dec_deg.")
    return {"target": name, "ra_deg": round(ra, 5), "dec_deg": round(dec, 5), **sky.constellation(ra, dec)}


# ================================================================ positions and times

@tool(annotations=READ_ONLY)
async def get_position(
    target: TARGET,
    time: TIME = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Where an object is in the sky at a given moment from a given place.

    Returns altitude, azimuth, compass direction, airmass, RA/Dec (J2000 and of date),
    constellation and magnitude. Use for 'where is Jupiter right now', 'which way do I look for
    M31 at 10pm' and similar; positions depend on time and place and should be computed.
    """
    loc = await location.resolve(latitude, longitude, place)
    t = await planner.resolve_target(target)
    when = sky.parse_time(time, loc)
    h = sky.horizontal(t, when, loc)
    ra, dec = sky.j2000_position(t, when)
    mag = planner.target_magnitude(t, when)
    am = sky.airmass(h["altitude_deg"])
    out = {
        "target": t.name,
        "resolved_by": t.source,
        "time": sky.fmt(when, loc),
        "location": loc.name,
        "altitude_deg": round(h["altitude_deg"], 3),
        "azimuth_deg": round(h["azimuth_deg"], 3),
        "direction": sky.compass(h["azimuth_deg"]),
        "above_horizon": h["altitude_deg"] > 0,
        "airmass": round(am, 3) if am else None,
        "ra_j2000_deg": round(ra, 5),
        "dec_j2000_deg": round(dec, 5),
        "ra_of_date_deg": round(h["ra_of_date_deg"], 5),
        "dec_of_date_deg": round(h["dec_of_date_deg"], 5),
        "constellation": sky.constellation(ra, dec)["name"],
        "magnitude": round(mag, 2) if mag is not None else None,
        "sun_altitude_deg": round(sky.sun_altitude(when, loc), 1),
    }
    return {k: v for k, v in out.items() if v is not None}


@tool(annotations=READ_ONLY)
async def get_rise_set_transit(
    target: TARGET,
    date: DATE = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """When an object rises, reaches its highest point, and sets on a given date and place.

    Works for the Moon, planets, stars and deep-sky objects, and reports circumpolar or
    never-rises cases. For the Sun's times and twilight, use get_twilight_times.
    """
    loc = await location.resolve(latitude, longitude, place)
    t = await planner.resolve_target(target)
    day = sky.observing_date(date, loc)
    return {"target": t.name, "date": day.isoformat(), "location": loc.name, **sky.rise_set_transit(t, loc, day)}


@tool(annotations=READ_ONLY)
async def get_twilight_times(
    date: DATE = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Sunset, twilight stages, sunrise, when it gets fully dark, and moonrise/moonset.

    Use for 'when does it get dark', 'when is astronomical twilight' or 'how many hours of
    moonless darkness tonight'.
    """
    loc = await location.resolve(latitude, longitude, place)
    day = sky.observing_date(date, loc)
    n = sky.night(loc, day)
    out: dict[str, Any] = {"location": loc.name, **n.to_dict(loc)}
    if n.darkest != "none":
        moon_rst = sky.rise_set_transit(planner.MOON, loc, day)
        out["moon"] = {
            **sky.moon_phase(n.window[0] + (n.window[1] - n.window[0]) / 2),
            "rise": moon_rst.get("rise"),
            "set": moon_rst.get("set"),
            "moon_free_dark_hours": planner.moon_free_hours(loc, n),
        }
    return out


@tool(annotations=READ_ONLY)
async def get_moon_phases(
    start_date: Annotated[str | None, Field(description="First day (YYYY-MM-DD); omit for today")] = None,
    days: Annotated[int, Field(ge=1, le=400, description="How many days of primary phases to list")] = 45,
) -> dict[str, Any]:
    """Current Moon phase and illumination, plus exact times of upcoming new, first quarter,
    full and last quarter Moons.

    Use for 'when is the next full/new Moon' or planning dark-sky nights. Times use the saved
    default location's timezone, else UTC.
    """
    loc = location.load_default() or Location(0.0, 0.0, name="UTC")
    if start_date:
        start = datetime.combine(sky.observing_date(start_date, loc), datetime.min.time(), tzinfo=loc.tz)
    else:
        start = datetime.now(UTC)
    quarters = sky.moon_quarters(start, start + timedelta(days=days))
    return {
        "at_start": {"time": sky.fmt(start, loc), **sky.moon_phase(start)},
        "phases": [{"phase": name, "time": sky.fmt(t, loc)} for name, t in quarters],
        "new_moons": [sky.fmt(t, loc) for name, t in quarters if name == "New Moon"],
    }


@tool(annotations=READ_ONLY)
async def get_planet_positions(
    time: TIME = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Where the Sun, Moon and planets are now (or at a given time) and how they look.

    Returns magnitude, phase, apparent size, distance, constellation, morning/evening sky, and
    with a location the altitude, direction and rise/transit/set times. Use for 'which planets
    are up', 'where is Mars' or 'is Venus a morning or evening star'.
    """
    loc = await _location_or_none(latitude, longitude, place)
    when = sky.parse_time(time, loc or Location(0.0, 0.0))
    day = sky.observing_date(None, loc) if loc and not time else (when.astimezone(loc.tz).date() if loc else None)
    bodies = []
    for name in ("sun", "moon", *sky.PLANETS):
        d = sky.body_details(name, when, loc)
        if loc and day:
            rst = sky.rise_set_transit(sky.Target(name.title(), sky.BODIES[name]), loc, day)
            d.update({k: rst[k] for k in ("rise", "transit", "set", "status") if k in rst})
        bodies.append(d)
    return {
        "time": sky.fmt(when, loc) if loc else when.astimezone(UTC).isoformat(timespec="minutes"),
        "location": loc.name if loc else "geocentric (no location given)",
        "bodies": bodies,
    }


# ================================================================ planning

@tool(annotations=READ_ONLY)
async def whats_up_tonight(
    date: DATE = None,
    equipment: EQUIPMENT = "telescope",
    aperture_mm: APERTURE = None,
    bortle: BORTLE = None,
    include: Annotated[Literal["all", "planets", "deep_sky"], Field(description="Which kinds of targets")] = "all",
    object_types: Annotated[
        list[Literal[tuple(catalog.GROUPS)]] | None,  # type: ignore[valid-type]
        Field(description="Restrict deep-sky results to these kinds"),
    ] = None,
    min_altitude: MIN_ALT = 25.0,
    max_results: Annotated[int, Field(ge=1, le=100, description="Maximum targets")] = 20,
    terrain: TERRAIN = True,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Ranked list of what is worth observing on a given night from a given place.

    Use for 'what can I see tonight', 'what should I point my telescope at' or 'what's up this
    weekend'. Considers darkness, the Moon, light pollution (atlas or user-supplied Bortle),
    terrain, and the equipment's reach. Each entry has difficulty, best time, altitude, direction
    and viewing window. Does not check clouds; pair with get_sky_forecast for that.
    """
    loc = await location.resolve(latitude, longitude, place)
    n = sky.night(loc, sky.observing_date(date, loc))
    sqm, sqm_source = await _sky_brightness(loc, bortle)
    hz, hz_warning = await _horizon_or_none(loc, terrain)
    cat = await _catalog_or_none() if include != "planets" else None
    result = planner.whats_up(loc, n, cat, sqm, equipment, aperture_mm, min_altitude, include,
                              set(object_types) if object_types else None, max_results, hz)
    result["location"] = loc.name
    if "assumptions" in result:
        result["assumptions"]["sky_brightness_source"] = sqm_source
    warnings = [w for w in (hz_warning,) if w]
    if include != "planets" and cat is None:
        warnings.append("Deep-sky catalog (OpenNGC) could not be downloaded; only planets are listed.")
    if warnings:
        result["warnings"] = warnings
    return result


@tool(annotations=READ_ONLY)
async def is_visible_tonight(
    target: TARGET,
    date: DATE = None,
    equipment: EQUIPMENT = "telescope",
    aperture_mm: APERTURE = None,
    bortle: BORTLE = None,
    min_altitude: MIN_ALT = 20.0,
    terrain: TERRAIN = True,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Whether one specific object can be seen on a given night, and when and where to look.

    Use for 'can I see Saturn tonight', 'is the Andromeda Galaxy visible from here' and similar,
    even when the question sounds casual. Returns yes/no with reasons (too low, behind terrain,
    too faint for the sky and equipment), difficulty, best time, direction and Moon interference.
    Does not check clouds; use get_sky_forecast for that.
    """
    loc = await location.resolve(latitude, longitude, place)
    t = await planner.resolve_target(target)
    day = sky.observing_date(date, loc)
    n = sky.night(loc, day)
    sqm, sqm_source = await _sky_brightness(loc, bortle)
    hz, hz_warning = await _horizon_or_none(loc, terrain)
    report = planner.visibility_report(t, loc, n, sqm, equipment, aperture_mm, min_altitude, hz)
    report["sky_assumed"]["sky_brightness_source"] = sqm_source
    out = {"date": day.isoformat(), "location": loc.name, "resolved_by": t.source,
           "dark_window": n.to_dict(loc)["dark_window"], **report}
    if hz_warning:
        out["warning"] = hz_warning
    return out


@tool(annotations=READ_ONLY)
async def best_night_this_month(
    target: Annotated[str | None, Field(description="Object to plan for: planet, 'Moon', catalog or common name. Omit to rate nights for general dark-sky observing.")] = None,
    start_date: Annotated[str | None, Field(description="First night to consider (YYYY-MM-DD); omit for tonight")] = None,
    days: Annotated[int, Field(ge=2, le=60, description="How many nights to compare")] = 30,
    min_altitude: MIN_ALT = 25.0,
    bortle: BORTLE = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Compare upcoming nights and pick the best ones, for one target or for dark-sky observing.

    Use for 'which night this week is best for the Orion Nebula', 'when should I go out this
    month' or 'best night for Saturn'. Scores each night on how long the target is well placed
    in darkness, how high it gets, how much moonlight brightens the sky near it, and the cloud
    forecast. Clouds are only forecast about 16 days ahead, so later nights are ranked separately
    on Moon and altitude alone. For one night's detail, follow up with is_visible_tonight and
    get_sky_forecast.
    """
    loc = await location.resolve(latitude, longitude, place)
    t = await planner.resolve_target(target) if target else None
    if t is not None and t.name == "Sun":
        raise ValueError("The Sun is not a night-time target.")
    sqm, sqm_source = await _sky_brightness(loc, bortle)
    warning = None
    try:
        clouds = await conditions.cloud_cover_by_hour(loc)
    except UpstreamError as exc:
        clouds, warning = None, f"Cloud forecast unavailable ({exc}); nights are ranked on Moon and altitude only."
    result = planner.best_nights(t, loc, sky.observing_date(start_date, loc), days, sqm, min_altitude, clouds)
    out = {"target": t.name if t else "general dark-sky observing", "location": loc.name, **result,
           "sky_brightness_source": sqm_source, "warning": warning}
    return {k: v for k, v in out.items() if v is not None}


@tool(annotations=READ_ONLY)
async def find_dark_moon_weekends(
    start_date: Annotated[str | None, Field(description="First day to consider (YYYY-MM-DD); omit for today")] = None,
    months: Annotated[int, Field(ge=1, le=24, description="How many months ahead to search")] = 6,
    min_moon_free_pct: Annotated[float, Field(ge=30, le=100, description="Minimum share of the two nights' dark hours with the Moon below the horizon")] = 70.0,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Upcoming weekends (Friday and Saturday nights) with little or no moonlight.

    Use for 'when is the next new-moon weekend', 'which weekends this summer are good for a
    dark-sky trip' or booking a campsite months ahead. With a location, counts the dark hours
    each night with the Moon down; without one, falls back to the Moon's illumination. Computed
    offline; weather is not considered.
    """
    loc = await _location_or_none(latitude, longitude, place)
    first = sky.observing_date(start_date, loc) if loc or start_date else datetime.now(UTC).date()
    result = planner.dark_moon_weekends(loc, first, round(months * 30.44), min_moon_free_pct)
    return {"location": loc.name if loc else None, **result}


# ================================================================ conditions

@tool(annotations=READ_ONLY)
async def get_sky_forecast(
    date: DATE = None,
    units: Annotated[Literal["metric", "imperial"], Field(description="Units for temperature and wind")] = "metric",
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Night-time observing weather: will it be clear, and when.

    Hour-by-hour from sunset to sunrise: cloud cover by layer, humidity, dew point, wind and
    precipitation chance, plus seeing and transparency about 3 days out. Summarises a 0-100
    score, clear hours, the longest clear stretch and dew risk. Up to ~16 days ahead.
    """
    loc = await location.resolve(latitude, longitude, place)
    day = sky.observing_date(date, loc)
    n = sky.night(loc, day)
    fc = await conditions.forecast_night(loc, n, units)
    moon = sky.moon_phase(n.window[0] + (n.window[1] - n.window[0]) / 2)
    return {"date": day.isoformat(), "location": loc.name, "night": n.to_dict(loc),
            "moon": {"phase": moon["phase"], "illuminated_percent": moon["illuminated_percent"]}, **fc}


@tool(annotations=READ_ONLY)
async def get_transparency_drivers(
    date: DATE = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """What is dimming a night's sky besides clouds: wildfire smoke, dust and other aerosols.

    Use for 'is it smoky tonight', 'why is the sky so hazy' or 'will the Milky Way look washed
    out'. Hour-by-hour aerosol optical depth, dust and fine particles from sunset to sunrise,
    with a transparency rating, the likely cause and the extra extinction in magnitudes. About
    5 days ahead. Clouds, humidity and seeing are in get_sky_forecast.
    """
    loc = await location.resolve(latitude, longitude, place)
    day = sky.observing_date(date, loc)
    n = sky.night(loc, day)
    return {"date": day.isoformat(), "location": loc.name, **await airquality.transparency_night(loc, n)}


@tool(annotations=READ_ONLY)
async def get_limiting_magnitude(
    equipment: EQUIPMENT = "naked_eye",
    aperture_mm: APERTURE = None,
    bortle: BORTLE = None,
    sqm: Annotated[float | None, Field(ge=15, le=22.5, description="Measured sky brightness in mag/arcsec^2 (Sky Quality Meter)")] = None,
    time: TIME = None,
    include_moon: Annotated[bool, Field(description="Account for moonlight at the given time (or tonight's mid-darkness)")] = True,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Estimate the faintest stars visible for a sky and piece of equipment, including moonlight.

    Use for 'how faint can my telescope go' or 'how many stars will I see'. Sky darkness comes
    from the user's Bortle/SQM or the light-pollution atlas. A model estimate.
    """
    loc = await _location_or_none(latitude, longitude, place)
    if loc is None:
        if bortle is None and sqm is None:
            raise ValueError("Give a location, a Bortle class, or an SQM reading so the sky brightness is known.")
        loc = Location(0.0, 0.0, name="unspecified")
        include_moon = False
    base_sqm, source = await _sky_brightness(loc, bortle, sqm)
    effective, moon_info = base_sqm, None
    if include_moon:
        if time:
            when = sky.parse_time(time, loc)
        else:
            n = sky.night(loc, sky.observing_date(None, loc))
            when = n.window[0] + (n.window[1] - n.window[0]) / 2
        h = sky.horizontal(planner.MOON, when, loc)
        phase = sky.moon_phase(when)
        effective = conditions.sqm_with_moon(base_sqm, phase["magnitude"], h["altitude_deg"])
        moon_info = {"time": sky.fmt(when, loc), "moon_altitude_deg": round(h["altitude_deg"], 1),
                     "illuminated_percent": phase["illuminated_percent"],
                     "sky_brightening_mag": round(base_sqm - effective, 2)}
    result = conditions.limiting_magnitude(effective, equipment, aperture_mm)
    out = {**result, "dark_sky_brightness": round(base_sqm, 2), "sky_brightness_source": source, "moon": moon_info,
           "note": "Model estimate; observer experience, eyesight and transparency shift real limits by 0.5-1 mag."}
    return {k: v for k, v in out.items() if v is not None}


@tool(annotations=READ_ONLY)
async def get_light_pollution(
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """How light-polluted a location's sky is: atlas zone, sky brightness (mag/arcsec²), an
    estimated Bortle class, and the naked-eye limiting magnitude.

    Use for 'how dark is the sky at X', 'what Bortle class am I' or comparing sites. From the
    2025 Light Pollution Atlas (VIIRS satellite data); a modelled zenith value for a clear,
    moonless night, not a measurement.
    """
    loc = await location.resolve(latitude, longitude, place)
    return {"location": loc.name, "latitude": loc.latitude, "longitude": loc.longitude,
            **await lightpollution.sky_brightness(loc.latitude, loc.longitude)}


@tool(annotations=READ_ONLY)
async def find_dark_sites(
    radius_km: Annotated[float, Field(ge=10, le=300, description="How far to search (straight-line km)")] = 100,
    max_results: Annotated[int, Field(ge=1, le=10, description="How many sites to suggest")] = 5,
    min_separation_km: Annotated[float, Field(ge=2, le=100, description="Minimum spacing between suggestions")] = 15,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Suggest darker observing spots within a radius, each with nearby access points.

    Use for 'where can I go to see the Milky Way', 'darkest place within an hour of me' and
    similar. Ranks by the light-pollution atlas (darkest first, then closest), and keeps only
    spots with a mapped campground, viewpoint, picnic area, trailhead or named parking nearby
    (OpenStreetMap). Distances are straight-line; the user should check roads and access.
    """
    loc = await location.resolve(latitude, longitude, place)
    result = await darksites.find(loc.latitude, loc.longitude, radius_km, max_results, min_separation_km)
    return {"from": loc.name, **result}


@tool(annotations=READ_ONLY)
async def get_horizon_profile(
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """How high the surrounding terrain rises in each direction from an observing site.

    Use for 'will the mountains block my view to the south' or before planning low targets.
    Computed from a 90 m elevation model out to 35 km with Earth curvature and refraction;
    trees and buildings are not included. whats_up_tonight and is_visible_tonight already
    apply this automatically.
    """
    loc = await location.resolve(latitude, longitude, place)
    hz = await horizon.get_horizon(loc)
    return {"location": loc.name, **hz.summary(),
            "note": "Terrain only (Copernicus 90 m DEM); nearby trees and buildings can raise the real horizon."}


# ================================================================ events

@tool(annotations=READ_ONLY)
async def get_eclipses(
    years: Annotated[float, Field(gt=0, le=30, description="How many years ahead to search for local solar eclipses")] = 10,
    lunar_count: Annotated[int, Field(ge=1, le=30, description="How many upcoming lunar eclipses to list")] = 6,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Upcoming lunar eclipses, and solar eclipses visible from the observer's location.

    Includes whether the Moon is up at mid-eclipse, local contact times and how much of the
    Sun is covered. Use rather than recalling eclipse dates.
    """
    loc = await _location_or_none(latitude, longitude, place)
    now = datetime.now(UTC)
    out: dict[str, Any] = {"location": loc.name if loc else None,
                           "lunar_eclipses": sky.lunar_eclipses(now, lunar_count, loc)}
    if loc:
        out["solar_eclipses_visible_here"] = sky.local_solar_eclipses(now, years, loc)
    else:
        out["note"] = "Give a location (or save a default) to find solar eclipses visible from it."
    return out


def _range_start(start_date: str | None, loc: Location | None) -> datetime:
    """Local midnight starting `start_date`, or now."""
    if not start_date:
        return datetime.now(UTC)
    shown = loc or Location(0.0, 0.0)
    return datetime.combine(sky.observing_date(start_date, shown), datetime.min.time(), tzinfo=shown.tz)


@tool(annotations=READ_ONLY)
async def find_conjunctions(
    start_date: Annotated[str | None, Field(description="First day (YYYY-MM-DD); omit for today")] = None,
    days: Annotated[int, Field(ge=1, le=1830, description="How many days ahead to search")] = 365,
    max_separation_deg: Annotated[float, Field(gt=0, le=15, description="Only pairings at least this close")] = 5.0,
    include_moon: Annotated[bool, Field(description="Also list the Moon passing each planet (about one per planet per month; best with a short range)")] = False,
    body: Annotated[
        Literal["moon", *sky.PLANETS] | None,  # type: ignore[valid-type]
        Field(description="Only pairings that involve this body"),
    ] = None,
    min_elongation_deg: Annotated[float, Field(ge=0, le=60, description="Skip pairings closer to the Sun than this; 0 keeps everything")] = 12.0,
    include_stars: Annotated[bool, Field(description="Also pair the planets (and the Moon, if included) with bright stars and clusters near the ecliptic: Regulus, Spica, Antares, Aldebaran, Pollux, the Pleiades, the Beehive and a few more")] = False,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Upcoming close pairings of planets in the sky (optionally with the Moon and bright stars).

    Use for 'when are Venus and Jupiter close together', 'any conjunctions this year', 'when
    is the Moon next to Saturn' or 'when does Mars pass Regulus'. Returns the moment of
    closest approach, the separation, which body is to the north, the constellation, and
    whether it is a morning or evening event. Computed offline for the centre of the Earth; a
    location only adds local times and whether the pair is up at that moment.
    """
    loc = await _location_or_none(latitude, longitude, place)
    return almanac.conjunctions(_range_start(start_date, loc), days, loc, max_separation_deg,
                                include_moon or body == "moon", body, min_elongation_deg, include_stars)


@tool(annotations=READ_ONLY)
async def find_greatest_elongations(
    start_date: Annotated[str | None, Field(description="First day (YYYY-MM-DD); omit for today")] = None,
    days: Annotated[int, Field(ge=1, le=3650, description="How many days ahead to search")] = 365,
    planets: Annotated[
        list[Literal[almanac.INNER_PLANETS]] | None,  # type: ignore[valid-type]
        Field(description="Mercury, Venus or both (default)"),
    ] = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """When Mercury and Venus are farthest from the Sun in the sky: their best evening and morning showings.

    Use for 'when can I see Mercury', 'when is Venus highest in the evening' or 'best Mercury
    apparition this year'. Gives the date, elongation, morning or evening sky, magnitude and
    phase, and with a location how high the planet stands at civil twilight, which is what
    makes an apparition easy or hard. Computed offline.
    """
    loc = await _location_or_none(latitude, longitude, place)
    return almanac.greatest_elongations(_range_start(start_date, loc), days, loc, planets)


@tool(annotations=READ_ONLY)
async def find_oppositions(
    start_date: Annotated[str | None, Field(description="First day (YYYY-MM-DD); omit for today")] = None,
    years: Annotated[float, Field(gt=0, le=30, description="How many years ahead to search (Mars comes to opposition only every 26 months)")] = 3,
    planets: Annotated[
        list[Literal[almanac.OUTER_PLANETS]] | None,  # type: ignore[valid-type]
        Field(description="Restrict to these planets; omit for Mars through Neptune"),
    ] = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Upcoming oppositions of Mars, Jupiter, Saturn, Uranus and Neptune: when each planet is
    opposite the Sun, up all night, and at its biggest and brightest.

    Use for 'when is the next Mars opposition', 'when is Saturn best this year' or 'how close
    does Mars get in 2027'. Gives the date, constellation, magnitude, apparent size, distance,
    the date of closest approach to Earth, and with a location how high the planet climbs.
    Computed offline; use rather than recalling dates.
    """
    loc = await _location_or_none(latitude, longitude, place)
    return almanac.oppositions(_range_start(start_date, loc), round(years * 365.25), loc, planets)


# ================================================================ Jupiter and the Moon up close

GRS = Annotated[float | None, Field(ge=0, lt=360, description="Great Red Spot's System II longitude, if you have a current measurement; omit to use the latest JUPOS value and its drift")]


@tool(annotations=READ_ONLY)
async def get_jupiter_moons(
    time: TIME = None,
    grs_longitude: GRS = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Where Io, Europa, Ganymede and Callisto are relative to Jupiter at a given moment.

    Use for 'which moon is which', 'why can I only see three moons' or 'is the Red Spot facing
    us right now'. Gives each moon's side and distance from the planet, whether it is in
    transit, hidden behind Jupiter or in its shadow, any moon shadow on the disk, the
    east-to-west line-up, the central meridian longitudes and where the Great Red Spot is.
    Computed offline. For upcoming transits and eclipses, use get_jupiter_events.
    """
    loc = await _location_or_none(latitude, longitude, place)
    return jupiter.moons_now(sky.parse_time(time, loc or Location(0.0, 0.0)), loc, grs_longitude,
                             await jupiter.current_grs_model())


@tool(annotations=READ_ONLY)
async def get_jupiter_events(
    time: Annotated[str | None, Field(description="Start of the search, ISO 8601; without an offset it is the observer's local time. Omit for now.")] = None,
    hours: Annotated[float, Field(gt=0, le=240, description="How many hours ahead to search")] = 24,
    observable_only: Annotated[bool, Field(description="Keep only events with Jupiter at least 10° up in a dark sky at the location")] = False,
    include_mutual_events: Annotated[bool, Field(description="Include moons occulting and eclipsing each other (only in seasons around Jupiter's equinoxes, such as late 2026 to mid 2027)")] = True,
    grs_longitude: GRS = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Upcoming events of Jupiter's moons and Great Red Spot, in time order.

    Use for 'when is the next shadow transit', 'when can I see the Great Red Spot tonight' or
    'any Io transits this week' or 'mutual events tonight'. Lists moon transits, shadow
    transits, occultations and eclipses (start and end), Red Spot transits, and in season the
    moons occulting and eclipsing each other, good to a few minutes. With a location, each
    event says whether Jupiter is up in a dark sky. Computed offline; the Red Spot's longitude
    comes from the latest JUPOS measurement available.
    """
    loc = await _location_or_none(latitude, longitude, place)
    if observable_only and loc is None:
        raise ValueError("observable_only needs a location.")
    return jupiter.events(sky.parse_time(time, loc or Location(0.0, 0.0)), hours, loc, grs_longitude, observable_only,
                          await jupiter.current_grs_model(), include_mutual_events)


@tool(annotations=READ_ONLY)
async def get_lunar_terminator(
    time: TIME = None,
    min_diameter_km: Annotated[float, Field(ge=0, le=1000, description="Smallest feature to list")] = 20.0,
    max_sun_altitude_deg: Annotated[float, Field(gt=0, le=30, description="How far from the terminator to look, as the Sun's height above the feature")] = 8.0,
    feature_types: Annotated[
        list[Literal[lunar.FEATURE_TYPES]] | None,  # type: ignore[valid-type]
        Field(description="Restrict to these kinds of feature, e.g. ['crater'] or ['mons', 'rupes', 'vallis']"),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=100, description="Maximum features")] = 30,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Craters, mountains and other named features on the Moon's terminator at a given time.

    Use for 'what should I look at on the Moon tonight' or 'is Copernicus on the terminator'.
    These are the features in low, raking sunlight, where shadows show the most relief. Lists
    them largest first with the Sun's height at each and whether it is lunar sunrise or
    sunset there, plus the Moon's phase and terminator longitude. Feature names come from
    the IAU/USGS gazetteer (downloaded once, about 24 MB).
    """
    loc = await _location_or_none(latitude, longitude, place)
    when = sky.parse_time(time, loc or Location(0.0, 0.0))
    return lunar.terminator(await lunar.get_features(), when, loc, min_diameter_km, max_sun_altitude_deg,
                            set(feature_types) if feature_types else None, limit)


@tool(annotations=READ_ONLY)
async def get_moon_libration(
    time: TIME = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """How the Moon is tipped toward the observer, and which limb features that brings into view.

    Use for 'is Mare Orientale visible tonight', 'what is the libration' or 'which limb is
    favoured'. Gives libration in longitude and latitude, the favoured limb, and for 45 limb
    features (Mare Orientale, Mare Humboldtianum, Bailly, the polar craters and others) how far
    inside the limb each sits, whether it is sunlit and whether the view is favourable.
    Computed offline.
    """
    loc = await _location_or_none(latitude, longitude, place)
    return lunar.libration(sky.parse_time(time, loc or Location(0.0, 0.0)), loc)


# ================================================================ comets, asteroids and fireballs

@tool(annotations=READ_ONLY)
async def get_comet_visibility(
    comet: Annotated[str | None, Field(description="A comet to look at, e.g. '12P', 'C/2025 R2', 'Tempel 2'. Omit to list the bright comets now.")] = None,
    max_magnitude: Annotated[float, Field(ge=0, le=18, description="Without a comet: only list comets at least this bright")] = 12.0,
    limit: Annotated[int, Field(ge=1, le=30, description="Without a comet: maximum comets to list")] = 10,
    days: Annotated[int, Field(ge=1, le=120, description="With a comet: how many days of brightness and position trend")] = 30,
    date: DATE = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Which comets are bright enough to see now, or how one comet will look over the coming weeks.

    Use for 'are there any comets visible', 'can I see comet X tonight' or 'when is comet X at
    its best'. Without a comet: the comets at or brighter than max_magnitude, brightest first,
    with constellation, morning or evening sky, the equipment needed and, with a location, the
    best time and altitude tonight. Brightness is from COBS observer reports where available,
    otherwise JPL's prediction. With a comet: tonight's view plus a day-by-day trend (JPL
    Horizons). Comet brightness is hard to predict; present magnitudes as estimates.
    """
    loc = await _location_or_none(latitude, longitude, place)
    day = sky.observing_date(date, loc) if loc else None
    if comet:
        return await smallbodies.comet_detail(comet, loc, day, days)
    return await smallbodies.bright_comets(loc, day, max_magnitude, limit)


@tool(annotations=READ_ONLY)
async def find_bright_asteroids(
    max_magnitude: Annotated[float, Field(ge=4, le=12, description="Only asteroids at least this bright")] = 10.0,
    limit: Annotated[int, Field(ge=1, le=30, description="Maximum asteroids")] = 10,
    date: DATE = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Asteroids bright enough for binoculars or a small telescope now, brightest first.

    Use for 'which asteroids can I see', 'is Vesta visible' or 'asteroids near opposition'.
    Gives magnitude, constellation, how far from the Sun in the sky (near 180° means up all
    night) and with a location the best time and altitude tonight. Positions and magnitudes
    from JPL Horizons; for a night-by-night table use get_asteroid_ephemeris.
    """
    loc = await _location_or_none(latitude, longitude, place)
    day = sky.observing_date(date, loc) if loc else None
    return await smallbodies.bright_asteroids(loc, day, max_magnitude, limit)


@tool(annotations=READ_ONLY)
async def get_asteroid_ephemeris(
    target: Annotated[str, Field(description="Asteroid or comet name, number or designation, e.g. 'Vesta', '4', 'Apophis', '2024 YR4', '12P'")],
    start: Annotated[str | None, Field(description="First time, ISO 8601; without an offset it is the observer's local time. Omit for now.")] = None,
    days: Annotated[float, Field(gt=0, le=366, description="How many days to cover")] = 7,
    step_hours: Annotated[float, Field(ge=0.25, le=720, description="Hours between rows (24 for daily)")] = 24,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Where an asteroid (or comet) is and how bright, as a table over time, from JPL Horizons.

    Use for 'where is Vesta', 'how bright will Apophis get' or 'finder positions for asteroid X'.
    Rows give RA/Dec, constellation, magnitude, motion across the sky, distances and elongation
    from the Sun; with a location, also altitude and direction. Also returns the object's
    orbit class, size, albedo and whether it is a near-Earth or potentially hazardous object.
    Up to 500 rows.
    """
    loc = await _location_or_none(latitude, longitude, place)
    when = sky.parse_time(start, loc or Location(0.0, 0.0))
    return await smallbodies.ephemeris(target, loc, when, days, step_hours)


@tool(annotations=READ_ONLY)
async def find_close_approaches(
    start_date: Annotated[str | None, Field(description="First day (YYYY-MM-DD), may be in the past; omit for now")] = None,
    days: Annotated[int, Field(ge=1, le=3650, description="How many days to search")] = 60,
    max_distance_lunar: Annotated[float, Field(gt=0, le=200, description="Only approaches closer than this many lunar distances (1 LD = 384,399 km)")] = 10,
    max_absolute_magnitude: Annotated[float | None, Field(ge=5, le=35, description="Only objects with H at or below this (smaller H is bigger: H 22 is roughly 100-250 m)")] = None,
    limit: Annotated[int, Field(ge=1, le=100, description="Maximum approaches")] = 25,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Asteroids and comets passing close to Earth, in time order (JPL Close Approach Data).

    Use for 'any asteroids passing Earth this month', 'how close did X come' or 'next close
    approach of Apophis'. Gives time, distance in lunar distances and km, speed, absolute
    magnitude and size. A location only adds local times. Whether one is observable needs
    get_asteroid_ephemeris.
    """
    loc = await _location_or_none(latitude, longitude, place)
    return await smallbodies.close_approaches(_range_start(start_date, loc), days, max_distance_lunar,
                                              max_absolute_magnitude, limit, loc)


@tool(annotations=READ_ONLY)
async def get_fireball_reports(
    days: Annotated[int, Field(ge=1, le=12000, description="How many days back to look")] = 365,
    limit: Annotated[int, Field(ge=1, le=100, description="Maximum events, newest first")] = 20,
    max_distance_km: Annotated[float | None, Field(gt=0, le=20000, description="Only events within this distance of the observer")] = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Large fireballs (bolides) detected by US government sensors, newest first (CNEOS).

    Use for 'was that huge fireball last night recorded', 'recent bolides near me' or 'how often
    do big fireballs happen'. Gives time, position, altitude, speed and energy; with a location,
    the distance and whether it was above the observer's horizon. Only metre-scale and larger
    impacts are listed, and reports lag by days to weeks; ordinary bright meteors aren't here.
    """
    loc = await _location_or_none(latitude, longitude, place)
    if max_distance_km and loc is None:
        raise ValueError("max_distance_km needs a location.")
    return await smallbodies.fireballs(days, limit, loc, max_distance_km)


# ================================================================ satellites

PASS_DAYS = Annotated[float, Field(gt=0, le=10, description="How many days ahead (predictions drift after a few days)")]
SAT_MIN_ALT = Annotated[float, Field(ge=0, le=80, description="Only count the satellite while at least this high, degrees")]


@tool(annotations=READ_ONLY)
async def get_iss_passes(
    days: PASS_DAYS = 5,
    min_altitude: SAT_MIN_ALT = 10,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """When the International Space Station will be visible from the observer's location.

    Use for 'when can I see the ISS' or 'is the space station going over tonight'. Lists passes
    where the ISS is sunlit against a dark sky: where it appears, its highest point and where it
    vanishes (often fading into Earth's shadow mid-sky), with local times to the second and an
    estimated magnitude. Computed from CelesTrak orbital elements with SGP4.
    """
    loc = await location.resolve(latitude, longitude, place)
    return await _satellite_passes(loc, "25544", days, min_altitude, False, None)


@tool(annotations=READ_ONLY)
async def get_satellite_passes(
    satellite: Annotated[str, Field(description="NORAD catalog number, a common name ('ISS', 'Tiangong', 'Hubble') or a CelesTrak name ('STARLINK-1234', 'NOAA 19')")],
    days: PASS_DAYS = 5,
    min_altitude: SAT_MIN_ALT = 10,
    include_daylight: Annotated[bool, Field(description="Also list passes that can't be seen (daylight or Earth's shadow), e.g. for radio")] = False,
    standard_magnitude: Annotated[float | None, Field(ge=-5, le=15, description="Satellite's magnitude at 1000 km and half phase, if known; enables brightness estimates")] = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Upcoming passes of any Earth satellite over the observer, by name or NORAD number.

    Use for 'when does Hubble pass over', 'Tiangong passes this week' or a specific NORAD id.
    By default only visible passes (satellite sunlit, observer's sky dark), with where it
    appears, peaks and vanishes. Brightness is estimated for the ISS, Tiangong, Hubble and
    Starlink, or any satellite given standard_magnitude. For the ISS, get_iss_passes is simpler.
    """
    loc = await location.resolve(latitude, longitude, place)
    return await _satellite_passes(loc, satellite, days, min_altitude, include_daylight, standard_magnitude)


async def _satellite_passes(loc: Location, satellite: str, days: float, min_altitude: float,
                            include_daylight: bool, standard_magnitude: float | None) -> dict[str, Any]:
    sat = await satellites.find_satellite(satellite, standard_magnitude)
    start = datetime.now(UTC)
    found = satellites.passes(sat, loc, start, days, min_altitude, include_daylight)
    return {
        "satellite": {k: v for k, v in sat.info().items() if v is not None},
        "location": loc.name,
        "from": sky.fmt(start, loc),
        "days": days,
        "count": len(found),
        "passes": found,
        "note": satellites.element_age_note(sat, start, days)
                + (" No brightness estimate: pass standard_magnitude if you know it." if sat.standard_magnitude is None else
                   f" Magnitudes are estimates; standard magnitude basis: {sat.magnitude_basis}.")
                + (" No visible passes in this period. A satellite shows only while sunlit against a dark sky, so "
                   "there are often a week or more without visible passes; try more days."
                   if not found and not include_daylight else ""),
    }


@tool(annotations=READ_ONLY)
async def find_satellites_overhead(
    time: TIME = None,
    group: Annotated[Literal[satellites.GROUPS], Field(description="Which satellites: visual (about 150 of the brightest), stations, starlink, or active (all ~16,000; slower first download)")] = "visual",  # type: ignore[valid-type]
    min_altitude: SAT_MIN_ALT = 10,
    visible_only: Annotated[bool, Field(description="Only satellites that are sunlit while the observer's sky is dark")] = True,
    limit: Annotated[int, Field(ge=1, le=200, description="Maximum satellites")] = 25,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Satellites above the observer right now (or at a given time): where each is and where it's heading.

    Use for 'what is that moving light' or 'what satellites are up now'. Lists each satellite's
    altitude, direction, distance, whether it is lit by the Sun, estimated magnitude where known,
    and where it will leave view (setting or fading into Earth's shadow). Brightest first.
    """
    loc = await location.resolve(latitude, longitude, place)
    when = sky.parse_time(time, loc)
    sats = await satellites.group(group)
    found = satellites.overhead(sats, loc, when, min_altitude, visible_only)
    sun_alt = sky.sun_altitude(when, loc)
    out = {
        "time": when.astimezone(loc.tz).isoformat(timespec="seconds"),
        "location": loc.name,
        "group": group,
        "sun_altitude_deg": round(sun_alt, 1),
        "total": len(found),
        "count": min(limit, len(found)),
        "satellites": found[:limit],
        "note": "Magnitudes for the ISS, Tiangong, Hubble and Starlink are built-in estimates (±1); others marked "
                "magnitude_rough come from radar cross-section and can be 1.5 magnitudes off."
                + (" The Sun is up or the sky is too bright to see satellites." if sun_alt >= satellites.SUN_LIMIT_DEG else ""),
    }
    return out


@tool(annotations=READ_ONLY)
async def predict_iss_transit(
    days: PASS_DAYS = 7,
    max_distance_km: Annotated[float, Field(gt=0, le=300, description="How far you would travel to the centerline")] = 50,
    bodies: Annotated[list[Literal["Sun", "Moon"]] | None, Field(description="Sun, Moon or both (default)")] = None,
    min_altitude: Annotated[float, Field(ge=0, le=80, description="Lowest Sun or Moon altitude worth considering, degrees")] = 10,
    satellite: Annotated[str, Field(description="Satellite to check; the ISS by default, or 'Tiangong', a name or a NORAD number")] = "ISS",
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """When the ISS (or another satellite) crosses the face of the Sun or Moon near the observer.

    Use for 'can I photograph the ISS crossing the Moon' or 'any ISS solar transits near me'.
    A transit is seen only within a few kilometres of a centerline, so each event gives the
    nearest point on that line (distance, direction, coordinates), the path width, the time to
    the millisecond, how long the crossing lasts (about a second), and whether it transits
    from the observer's own spot. Predictions shift by kilometres as orbits change; recheck a
    day before. Solar transits need a proper solar filter.
    """
    loc = await location.resolve(latitude, longitude, place)
    sat = await satellites.find_satellite(satellite)
    start = datetime.now(UTC)
    found = satellites.find_transits(sat, loc, start, days, max_distance_km, tuple(bodies or ("Sun", "Moon")), min_altitude)
    return {
        "satellite": {k: v for k, v in sat.info().items() if v is not None and k != "standard_magnitude_basis"},
        "location": loc.name,
        "from": sky.fmt(start, loc),
        "days": days,
        "max_distance_km": max_distance_km,
        "count": len(found),
        "transits": found,
        "note": satellites.element_age_note(sat, start, days)
                + " An orbit error of a second along the track moves the centerline by kilometres, so recheck with "
                  "fresh elements on the day and set up close to the centerline.",
    }


@tool(annotations=READ_ONLY)
async def get_starlink_trains(
    days: Annotated[float, Field(gt=0, le=7, description="How many days ahead to look for passes")] = 3,
    max_launch_age_days: Annotated[float, Field(gt=0, le=30, description="Only batches launched within this many days")] = 21,
    min_altitude: SAT_MIN_ALT = 10,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Recently launched Starlink batches and when their 'train' of satellites passes over.

    Use for 'I saw a line of lights moving across the sky' or 'when can I see a Starlink
    train'. For each batch launched in the last few weeks: satellite count, altitude, how
    stretched out the line is, and visible passes with times for the first and last satellite.
    Trains are best in the first days after launch and disperse within a few weeks.
    """
    loc = await location.resolve(latitude, longitude, place)
    return await satellites.starlink_trains(loc, datetime.now(UTC), days, max_launch_age_days, min_altitude)


# ================================================================ space weather and spaceflight

@tool(annotations=READ_ONLY)
async def get_space_weather(
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Aurora chances and geomagnetic storm levels, now and for the next 3 days (NOAA SWPC).

    Use for 'will I see the northern lights', 'is there a geomagnetic storm' or 'what's the Kp'.
    With a location, adds the current aurora probability overhead and toward the pole.
    """
    loc = await _location_or_none(latitude, longitude, place)
    return await space.space_weather(loc)


@tool(annotations=READ_ONLY)
async def get_upcoming_launches(
    limit: Annotated[int, Field(ge=1, le=25, description="Maximum launches")] = 10,
    search: Annotated[str | None, Field(description="Filter by rocket, provider or mission text, e.g. 'Starship', 'Rocket Lab'")] = None,
    max_distance_km: Annotated[float | None, Field(gt=0, description="Only launches from pads within this distance of the observer")] = None,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Upcoming rocket launches worldwide with times, rockets, missions, pads and webcasts.

    Use for 'when is the next SpaceX/Starship launch' or 'any launches I could see from here'
    (max_distance_km filters to nearby pads). Schedules change often, so prefer this over memory.
    """
    loc = await _location_or_none(latitude, longitude, place)
    if max_distance_km and loc is None:
        raise ValueError("max_distance_km needs a location.")
    launches = await space.upcoming_launches(limit, search, loc, max_distance_km)
    return {"count": len(launches), "launches": launches, "source": "The Space Devs Launch Library 2 (cached 15 min)"}


def main() -> None:
    mcp.run()  # stdio transport
