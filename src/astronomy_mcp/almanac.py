"""Planetary events over a date range: conjunctions, oppositions and elongations (offline).

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
INNER_PLANETS = ("mercury", "venus")
PLANET_STEP = timedelta(days=1)
MOON_STEP = timedelta(hours=4)  # the Moon covers about 2° in this time
GOLDEN = (math.sqrt(5) - 1) / 2

# Bright stars and clusters the planets and Moon pass: J2000 RA, Dec (degrees) and V magnitude.
# All lie within about 10° of the ecliptic; proper motion is negligible here.
STARS: dict[str, tuple[float, float, float]] = {
    "Pleiades": (56.75, 24.12, 1.6),
    "Aldebaran": (68.980, 16.509, 0.85),
    "Elnath": (81.573, 28.608, 1.65),
    "Castor": (113.650, 31.888, 1.58),
    "Pollux": (116.329, 28.026, 1.14),
    "Beehive Cluster": (130.10, 19.67, 3.7),
    "Regulus": (152.093, 11.967, 1.40),
    "Spica": (201.298, -11.161, 0.97),
    "Zubenelgenubi": (222.720, -16.042, 2.75),
    "Antares": (247.352, -26.432, 1.06),
    "Nunki": (283.816, -26.297, 2.05),
}


def _star_vector(ra: float, dec: float) -> Vec:
    r, d = math.radians(ra), math.radians(dec)
    return math.cos(d) * math.cos(r), math.cos(d) * math.sin(r), math.sin(d)


_STAR_VECTORS = {name: _star_vector(ra, dec) for name, (ra, dec, _) in STARS.items()}


def _direction(name: str, when: datetime) -> Vec:
    if name in _STAR_VECTORS:
        return _STAR_VECTORS[name]
    return sky.unit(sky.vec(ae.GeoVector(sky.BODIES[name], sky.to_time(when), True)))


def _title(name: str) -> str:
    return name if name in STARS else name.title()


def _magnitude(name: str, when: datetime) -> float:
    if name in STARS:
        return STARS[name][2]
    return round(ae.Illumination(sky.BODIES[name], sky.to_time(when)).mag, 1)


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
    mover = a if a in sky.BODIES else b  # a solar-system body of the pair
    ra, dec = sky.j2000_position(sky.Target(mover, sky.BODIES[mover]), when)
    planet = next((x for x in (a, b) if x in sky.PLANETS), None)
    if planet:
        side = "evening" if ae.Elongation(sky.BODIES[planet], sky.to_time(when)).visibility == ae.Visibility.Evening else "morning"
    else:  # the Moon and a star: east of the Sun means the evening sky
        side = "evening" if sky.wrap180(math.degrees(math.atan2(da[1], da[0]) - math.atan2(sun[1], sun[0]))) > 0 else "morning"
    out: dict[str, Any] = {
        "time": fmt(when, shown),
        "bodies": [_title(a), _title(b)],
        "separation_deg": round(separation, 2),
        "summary": f"{_title(north)} passes {separation:.1f}° north of {_title(south)}",
        "constellation": sky.constellation(ra, dec)["name"],
        "elongation_from_sun_deg": round(min(_angle(da, sun), _angle(db, sun)), 1),
        "sky": side,
        "magnitudes": {_title(x): _magnitude(x, when) for x in (a, b)},
    }
    if "moon" in (a, b):
        out["moon_illuminated_percent"] = sky.moon_phase(when)["illuminated_percent"]
        star = next((x for x in (a, b) if x in STARS), None)
        if star and separation < 1.5:
            out["occultation_possible"] = (f"Parallax shifts the Moon by up to 1°, so it may pass in front of {star} "
                                           "as seen from part of the Earth.")
    if loc:
        alt = sky.horizontal(sky.Target(mover, sky.BODIES[mover]), when, loc)["altitude_deg"]
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
    include_stars: bool = False,
) -> dict[str, Any]:
    """Closest approaches between planets (optionally the Moon, and bright stars near the ecliptic)
    within `max_separation_deg`. Stars are paired with the planets and Moon, not with each other."""
    names = [*(["moon"] if include_moon else []), *sky.PLANETS]
    pairs = list(combinations(names, 2)) + ([(n, star) for n in names for star in STARS] if include_stars else [])
    pairs = [p for p in pairs if body is None or body in p]
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


def greatest_elongations(start: datetime, days: int, loc: Location | None = None,
                         planets: list[str] | None = None) -> dict[str, Any]:
    """Greatest elongations of Mercury and Venus, with how high each stands at twilight."""
    shown = loc or Location(0.0, 0.0)
    end = start + timedelta(days=days)
    found = []
    for name in planets or INNER_PLANETS:
        body = sky.BODIES[name]
        t = sky.to_time(start)
        while (event := ae.SearchMaxElongation(body, t)) and (when := sky.to_datetime(event.time)) <= end:
            evening = event.visibility == ae.Visibility.Evening
            details = sky.body_details(name, when, None)
            item: dict[str, Any] = {
                "planet": name.title(),
                "time": fmt(when, shown),
                "sky": "evening" if evening else "morning",
                "elongation_deg": round(event.elongation, 1),
                "magnitude": details["magnitude"],
                "illuminated_percent": details["illuminated_percent"],
                "apparent_diameter_arcsec": details["apparent_diameter_arcsec"],
                "constellation": details["constellation"],
            }
            if loc:
                day = when.astimezone(loc.tz).date()
                n = sky.night(loc, day if evening else day - timedelta(days=1))
                twilight = n.civil[0] if evening else n.civil[1]
                if twilight:
                    h = sky.horizontal(sky.Target(name, body), twilight, loc)
                    item["at_civil_twilight"] = {"time": fmt(twilight, loc), "altitude_deg": round(h["altitude_deg"], 1),
                                                 "direction": sky.compass(h["azimuth_deg"])}
            found.append((when, item))
            t = event.time.AddDays(10)
    found.sort(key=lambda x: x[0])
    return {
        "from": fmt(start, shown),
        "to": fmt(end, shown),
        "count": len(found),
        "elongations": [item for _, item in found],
        "note": "Greatest elongation is the widest angle from the Sun. How high the planet stands at dusk or dawn "
                "also depends on how steeply the ecliptic meets the horizon, so the same elongation can make an easy "
                "or a hard apparition. Mercury is usually best for about a week either side.",
    }
