"""Planetary events over a date range: conjunctions and oppositions (offline).

A conjunction here is the moment two bodies are closest together in the sky as seen
from the centre of the Earth, which is what an observer notices, rather than the
moment they share a right ascension or ecliptic longitude. The two differ by hours
at most for close pairings.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from itertools import combinations
from typing import Any

import astronomy as ae

from astronomy_mcp import sky
from astronomy_mcp.location import Location
from astronomy_mcp.sky import Vec, fmt

OUTER_PLANETS = ("mars", "jupiter", "saturn", "uranus", "neptune")
PLANET_STEP = timedelta(days=1)
MOON_STEP = timedelta(hours=4)  # the Moon covers about 2° in this time
GOLDEN = (math.sqrt(5) - 1) / 2


def _direction(name: str, when: datetime) -> Vec:
    return sky.unit(sky.vec(ae.GeoVector(sky.BODIES[name], sky.to_time(when), True)))


def _angle(a: Vec, b: Vec) -> float:
    return math.degrees(math.atan2(math.sqrt(sum(c * c for c in sky.cross(a, b))), sky.dot(a, b)))


def _minimise(f: Any, lo: datetime, hi: datetime, tolerance: timedelta = timedelta(seconds=30)) -> datetime:
    """Golden-section search for the minimum of f between two times that bracket it."""
    a, b = lo + (hi - lo) * (1 - GOLDEN), lo + (hi - lo) * GOLDEN
    fa, fb = f(a), f(b)
    while hi - lo > tolerance:
        if fa < fb:
            hi, b, fb = b, a, fa
            a = lo + (hi - lo) * (1 - GOLDEN)
            fa = f(a)
        else:
            lo, a, fa = a, b, fb
            b = lo + (hi - lo) * GOLDEN
            fb = f(b)
    return lo + (hi - lo) / 2


def _describe_conjunction(a: str, b: str, when: datetime, loc: Location | None) -> dict[str, Any]:
    shown = loc or Location(0.0, 0.0)
    da, db, sun = _direction(a, when), _direction(b, when), _direction("sun", when)
    separation = _angle(da, db)
    north, south = (a, b) if da[2] > db[2] else (b, a)
    ra, dec = sky.j2000_position(sky.Target(a, sky.BODIES[a]), when)
    planet = b if a == "moon" else a
    visibility = ae.Elongation(sky.BODIES[planet], sky.to_time(when)).visibility
    out: dict[str, Any] = {
        "time": fmt(when, shown),
        "bodies": [a.title(), b.title()],
        "separation_deg": round(separation, 2),
        "summary": f"{north.title()} passes {separation:.1f}° north of {south.title()}",
        "constellation": sky.constellation(ra, dec)["name"],
        "elongation_from_sun_deg": round(min(_angle(da, sun), _angle(db, sun)), 1),
        "sky": "evening" if visibility == ae.Visibility.Evening else "morning",
        "magnitudes": {x.title(): round(ae.Illumination(sky.BODIES[x], sky.to_time(when)).mag, 1) for x in (a, b)},
    }
    if "moon" in (a, b):
        out["moon_illuminated_percent"] = sky.moon_phase(when)["illuminated_percent"]
    if loc:
        alt = sky.horizontal(sky.Target(planet, sky.BODIES[planet]), when, loc)["altitude_deg"]
        sun_alt = sky.sun_altitude(when, loc)
        out["at_closest_from_here"] = {
            "altitude_deg": round(alt), "sun_altitude_deg": round(sun_alt),
            "visible": alt > 5 and sun_alt < -6,
        }
    return out


def conjunctions(
    start: datetime,
    days: int,
    loc: Location | None = None,
    max_separation_deg: float = 5.0,
    include_moon: bool = False,
    body: str | None = None,
    min_elongation_deg: float = 12.0,
) -> dict[str, Any]:
    """Closest approaches between planets (and optionally the Moon) within `max_separation_deg`."""
    names = [*(["moon"] if include_moon else []), *sky.PLANETS]
    pairs = [p for p in combinations(names, 2) if body is None or body in p]
    step = MOON_STEP if include_moon else PLANET_STEP
    end = start + timedelta(days=days)
    times = [start + step * i for i in range(-1, int((end - start) / step) + 2)]
    wanted = {name for pair in pairs for name in pair}
    tracks = {name: [_direction(name, t) for t in times] for name in wanted}

    found, in_glare = [], 0
    for a, b in pairs:
        seps = [_angle(u, v) for u, v in zip(tracks[a], tracks[b])]
        for i in range(1, len(seps) - 1):
            # Local minimum on the grid; real separations change by under a step's motion in between.
            if not (seps[i] <= seps[i - 1] and seps[i] < seps[i + 1]) or seps[i] > max_separation_deg + 3:
                continue
            when = _minimise(lambda t: _angle(_direction(a, t), _direction(b, t)), times[i - 1], times[i + 1])
            if not start <= when <= end:
                continue
            event = _describe_conjunction(a, b, when, loc)
            if event["separation_deg"] > max_separation_deg:
                continue
            if event["elongation_from_sun_deg"] < min_elongation_deg:
                in_glare += 1
                continue
            found.append((when, event))
    found.sort(key=lambda item: item[0])
    shown = loc or Location(0.0, 0.0)
    out = {
        "from": fmt(start, shown),
        "to": fmt(end, shown),
        "count": len(found),
        "conjunctions": [event for _, event in found],
        "lost_in_sun_glare": in_glare or None,
        "note": "Closest approach as seen from the centre of the Earth. Planet pairs stay close for days, so "
                "look on the nearest clear evening or morning."
                + (" The Moon moves its own width every hour and parallax shifts it by up to 1°, so Moon "
                   "pairings are best on the date given and vary by location." if include_moon else ""),
    }
    return {k: v for k, v in out.items() if v is not None}


def oppositions(start: datetime, days: int, loc: Location | None = None, planets: list[str] | None = None) -> dict[str, Any]:
    """Oppositions of the outer planets, with each one's closest approach to Earth."""
    shown = loc or Location(0.0, 0.0)
    end = start + timedelta(days=days)
    found = []
    for name in planets or OUTER_PLANETS:
        body = sky.BODIES[name]
        search_from = start
        while True:
            when = sky.to_datetime(ae.SearchRelativeLongitude(body, 0.0, sky.to_time(search_from)))
            if when > end:
                break
            closest = _minimise(lambda t: ae.GeoVector(body, sky.to_time(t), True).Length(),
                                when - timedelta(days=30), when + timedelta(days=30), timedelta(minutes=30))
            details = sky.body_details(name, when, None)
            event: dict[str, Any] = {
                "planet": name.title(),
                "opposition": fmt(when, shown),
                **{k: details[k] for k in ("constellation", "magnitude", "distance_au", "apparent_diameter_arcsec", "dec_deg")},
                "ring_tilt_deg": details.get("ring_tilt_deg"),
                "closest_to_earth": {
                    "date": closest.astimezone(shown.tz).date().isoformat(),
                    "distance_au": round(ae.GeoVector(body, sky.to_time(closest), True).Length(), 5),
                },
            }
            if loc:
                event["highest_altitude_from_here_deg"] = round(90 - abs(loc.latitude - details["dec_deg"]), 1)
            found.append((when, {k: v for k, v in event.items() if v is not None}))
            search_from = when + timedelta(days=30)
    found.sort(key=lambda item: item[0])
    return {
        "from": fmt(start, shown),
        "to": fmt(end, shown),
        "count": len(found),
        "oppositions": [event for _, event in found],
        "note": "At opposition a planet rises around sunset, is up all night and is near its brightest and "
                "largest; it stays well placed for weeks either side.",
    }
