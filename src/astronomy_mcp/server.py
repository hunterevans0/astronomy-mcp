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

from astronomy_mcp import catalog, conditions, location, planner, simbad, sky, space, vsx
from astronomy_mcp.http import UpstreamError
from astronomy_mcp.location import Location

mcp = MCPServer(
    name="astronomy",
    title="Astronomy Data",
    version="0.2.0",
    log_level="WARNING",
    instructions=(
        "Astronomy tools. Location-aware tools accept latitude/longitude or a place name; with neither "
        "they use the saved default, so call set_default_location once when the user tells you where "
        "they observe from (include their Bortle class if known). For 'what should I look at tonight' "
        "use whats_up_tonight; for one object use is_visible_tonight; for weather use get_sky_forecast. "
        "describe_object merges SIMBAD, OpenNGC and AAVSO VSX. Targets can be planets, the Moon, "
        "catalog names (M31, NGC 7000, Caldwell 14), common names (Orion Nebula) or any SIMBAD "
        "identifier. Times are returned in the observer's local time with a UTC offset. Coordinates "
        "are ICRS/J2000 decimal degrees. Limiting magnitudes and sky brightness are model estimates."
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
BORTLE = Annotated[int | None, Field(ge=1, le=9, description="Bortle class of the sky (1 pristine to 9 inner city). Overrides the saved location's value.")]
MIN_ALT = Annotated[float, Field(ge=0, le=80, description="Minimum useful altitude in degrees")]


async def _location_or_none(latitude: float | None, longitude: float | None, place: str | None) -> Location | None:
    if latitude is None and longitude is None and not place:
        return location.load_default()
    return await location.resolve(latitude, longitude, place)


def _sky_brightness(loc: Location, bortle: int | None = None, sqm: float | None = None) -> tuple[float, str]:
    """(zenith sky brightness in mag/arcsec^2, where that number came from)."""
    if sqm is not None:
        return sqm, "measured SQM supplied by user"
    if bortle is not None:
        return conditions.sqm_from_bortle(bortle), f"Bortle {bortle} supplied by user"
    if loc.bortle is not None:
        return conditions.sqm_from_bortle(loc.bortle), f"Bortle {loc.bortle} from saved location"
    return conditions.sqm_from_bortle(5), "assumed Bortle 5 (suburban); pass bortle or save it with set_default_location"


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
    """Turn a place name into coordinates, elevation and timezone (Open-Meteo geocoder)."""
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
    """Save the observer's default location (and optionally sky darkness) so other tools stop asking.

    Stored in ~/.astronomy-mcp/config.json and reused across sessions.
    """
    if latitude is None and longitude is None and not place:
        raise ValueError("Give a place name or latitude/longitude.")
    loc = await location.resolve(latitude, longitude, place)
    if name:
        loc.name = name
    if bortle is not None:
        loc.bortle = bortle
    location.save_default(loc)
    return {"saved": True, "default_location": loc.to_dict()}


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
    """Find SIMBAD objects within a radius of a sky position, sorted nearest first."""
    results = await simbad.cone_search(ra_deg, dec_deg, radius_arcmin, limit, object_type, max_v_mag)
    return {"count": len(results), "objects": results}


@tool(annotations=READ_ONLY)
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
    """One merged profile of any object: SIMBAD facts, OpenNGC deep-sky data (size, surface
    brightness, common names), AAVSO VSX variability, and constellation. Planets get their current
    apparent details instead."""
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
    """Search the OpenNGC catalog (NGC, IC, Messier, plus Caldwell extras), brightest first."""
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
    """Which IAU constellation a position or object lies in (official 1930 Delporte boundaries)."""
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
    """Where an object is in the sky at a moment: altitude, azimuth, compass direction, airmass,
    RA/Dec (J2000 and of date) and constellation. Includes atmospheric refraction."""
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
    """Rise, transit (highest point) and set times for an object, searched forward from local noon
    of the date. Reports circumpolar / never-rises cases."""
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
    """Sunset, civil/nautical/astronomical twilight, sunrise, the dark window, and how much of the
    dark window is free of moonlight."""
    loc = await location.resolve(latitude, longitude, place)
    day = sky.observing_date(date, loc)
    n = sky.night(loc, day)
    out: dict[str, Any] = {"location": loc.name, **n.to_dict(loc)}
    if n.darkest != "none":
        moon_rst = sky.rise_set_transit(planner.MOON, loc, day)
        track = sky.altitude_track(planner.MOON, n.window[0], n.window[1], loc, step_min=10)
        out["moon"] = {
            **sky.moon_phase(n.window[0] + (n.window[1] - n.window[0]) / 2),
            "rise": moon_rst.get("rise"),
            "set": moon_rst.get("set"),
            "moon_free_dark_hours": round(sum(1 for row in track if row[1] < 0) * 10 / 60, 1),
        }
    return out


@tool(annotations=READ_ONLY)
async def get_moon_phases(
    start_date: Annotated[str | None, Field(description="First day (YYYY-MM-DD); omit for today")] = None,
    days: Annotated[int, Field(ge=1, le=400, description="How many days of primary phases to list")] = 45,
) -> dict[str, Any]:
    """Current Moon phase and illumination, plus exact times of upcoming new, first quarter, full and
    last quarter Moons. Times use the saved default location's timezone, else UTC."""
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
    """Sun, Moon and planets at a moment: magnitude, phase, apparent size, distance, elongation,
    constellation, morning/evening sky, and (with a location) altitude, direction and rise/transit/set
    for the night. Saturn includes ring tilt."""
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
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Ranked list of what is worth observing tonight: planets, the Moon, and deep-sky objects that are
    high enough during darkness and bright enough for the equipment, sky darkness and moonlight.
    Each entry has best time, altitude, compass direction and visibility window."""
    loc = await location.resolve(latitude, longitude, place)
    n = sky.night(loc, sky.observing_date(date, loc))
    sqm, sqm_source = _sky_brightness(loc, bortle)
    cat = await _catalog_or_none() if include != "planets" else None
    result = planner.whats_up(loc, n, cat, sqm, equipment, aperture_mm, min_altitude, include,
                              set(object_types) if object_types else None, max_results)
    result["location"] = loc.name
    if "assumptions" in result:
        result["assumptions"]["sky_brightness_source"] = sqm_source
    if include != "planets" and cat is None:
        result["warning"] = "Deep-sky catalog (OpenNGC) could not be downloaded; only planets are listed."
    return result


@tool(annotations=READ_ONLY)
async def is_visible_tonight(
    target: TARGET,
    date: DATE = None,
    equipment: EQUIPMENT = "telescope",
    aperture_mm: APERTURE = None,
    bortle: BORTLE = None,
    min_altitude: MIN_ALT = 20.0,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Yes/no for one object tonight, with the reasons if not (too low, too faint, midnight sun),
    the best time and direction, the window above min_altitude, and any Moon interference."""
    loc = await location.resolve(latitude, longitude, place)
    t = await planner.resolve_target(target)
    day = sky.observing_date(date, loc)
    n = sky.night(loc, day)
    sqm, sqm_source = _sky_brightness(loc, bortle)
    report = planner.visibility_report(t, loc, n, sqm, equipment, aperture_mm, min_altitude)
    report["limiting_magnitude_assumed"]["sky_brightness_source"] = sqm_source
    return {"date": day.isoformat(), "location": loc.name, "resolved_by": t.source,
            "dark_window": n.to_dict(loc)["dark_window"], **report}


# ================================================================ conditions

@tool(annotations=READ_ONLY)
async def get_sky_forecast(
    date: DATE = None,
    units: Annotated[Literal["metric", "imperial"], Field(description="Units for temperature and wind")] = "metric",
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Hour-by-hour observing forecast from sunset to sunrise: cloud cover by layer, humidity, dew
    point, wind, precipitation chance, plus seeing and transparency (7Timer, ~3 days out). Summarises
    a 0-100 weather score, clear hours, the longest clear stretch and dew risk. Up to ~16 days ahead."""
    loc = await location.resolve(latitude, longitude, place)
    day = sky.observing_date(date, loc)
    n = sky.night(loc, day)
    fc = await conditions.forecast_night(loc, n, units)
    moon = sky.moon_phase(n.window[0] + (n.window[1] - n.window[0]) / 2)
    return {"date": day.isoformat(), "location": loc.name, "night": n.to_dict(loc),
            "moon": {"phase": moon["phase"], "illuminated_percent": moon["illuminated_percent"]}, **fc}


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
    """Estimate the faintest stars and deep-sky objects visible, from sky darkness (Bortle or SQM),
    equipment aperture and moonlight. A model estimate, not a measurement."""
    loc = await _location_or_none(latitude, longitude, place)
    if loc is None:
        loc = Location(0.0, 0.0, name="unspecified")
        include_moon = False
    base_sqm, source = _sky_brightness(loc, bortle, sqm)
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


# ================================================================ events

@tool(annotations=READ_ONLY)
async def get_eclipses(
    years: Annotated[float, Field(gt=0, le=30, description="How many years ahead to search for local solar eclipses")] = 10,
    lunar_count: Annotated[int, Field(ge=1, le=30, description="How many upcoming lunar eclipses to list")] = 6,
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Upcoming lunar eclipses (with whether the Moon is up at mid-eclipse for the observer) and solar
    eclipses actually visible from the observer's location, with contact times and obscuration."""
    loc = await _location_or_none(latitude, longitude, place)
    now = datetime.now(UTC)
    out: dict[str, Any] = {"location": loc.name if loc else None,
                           "lunar_eclipses": sky.lunar_eclipses(now, lunar_count, loc)}
    if loc:
        out["solar_eclipses_visible_here"] = sky.local_solar_eclipses(now, years, loc)
    else:
        out["note"] = "Give a location (or save a default) to find solar eclipses visible from it."
    return out


# ================================================================ space weather and spaceflight

@tool(annotations=READ_ONLY)
async def get_space_weather(
    latitude: LAT = None,
    longitude: LON = None,
    place: PLACE = None,
) -> dict[str, Any]:
    """Geomagnetic activity and aurora outlook from NOAA SWPC: latest Kp, 3-day Kp forecast with
    storm levels, and (with a location) the OVATION aurora probability overhead and poleward."""
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
    """Upcoming orbital launches worldwide (Launch Library 2): time, window, status, rocket, mission,
    orbit, pad, weather probability, webcasts, and distance from the observer when a location is known."""
    loc = await _location_or_none(latitude, longitude, place)
    if max_distance_km and loc is None:
        raise ValueError("max_distance_km needs a location.")
    launches = await space.upcoming_launches(limit, search, loc, max_distance_km)
    return {"count": len(launches), "launches": launches, "source": "The Space Devs Launch Library 2 (cached 15 min)"}


def main() -> None:
    mcp.run()  # stdio transport
