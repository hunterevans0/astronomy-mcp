"""Positional astronomy on top of Astronomy Engine (pure Python, ~1 arcminute accuracy).

Everything here is offline math. Times cross this module's boundary as aware
`datetime`s; astronomy-engine's own `Time` type stays internal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import astronomy as ae

from astronomy_mcp.location import Location

BODIES: dict[str, ae.Body] = {
    "sun": ae.Body.Sun,
    "moon": ae.Body.Moon,
    "mercury": ae.Body.Mercury,
    "venus": ae.Body.Venus,
    "mars": ae.Body.Mars,
    "jupiter": ae.Body.Jupiter,
    "saturn": ae.Body.Saturn,
    "uranus": ae.Body.Uranus,
    "neptune": ae.Body.Neptune,
    "pluto": ae.Body.Pluto,
}
PLANETS = ("mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune")

# Equatorial radii (km), for apparent angular diameter.
RADIUS_KM = {
    "sun": 695700, "moon": 1737.4, "mercury": 2439.7, "venus": 6051.8, "mars": 3396.2,
    "jupiter": 71492, "saturn": 60268, "uranus": 25559, "neptune": 24764, "pluto": 1188.3,
}
AU_KM = 149_597_870.7

MOON_PHASES = (
    "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
    "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent",
)
QUARTER_NAMES = ("New Moon", "First Quarter", "Full Moon", "Last Quarter")
SYNODIC_MONTH_DAYS = 29.530588


@dataclass
class Target:
    """Something to point at: a solar-system body, or a fixed J2000 position."""

    name: str
    body: ae.Body | None = None
    ra_deg: float | None = None
    dec_deg: float | None = None
    source: str = "astronomy-engine"
    info: dict[str, Any] = field(default_factory=dict)

    @property
    def is_fixed(self) -> bool:
        return self.body is None


# ---------------------------------------------------------------- time helpers

def to_time(dt: datetime) -> ae.Time:
    dt = dt.astimezone(UTC)
    return ae.Time.Make(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)


def to_datetime(t: ae.Time) -> datetime:
    return t.Utc().replace(tzinfo=UTC)


def fmt(value: ae.Time | datetime | None, loc: Location) -> str | None:
    """Local ISO 8601 time with UTC offset, minute precision."""
    if value is None:
        return None
    dt = to_datetime(value) if isinstance(value, ae.Time) else value
    return dt.astimezone(loc.tz).isoformat(timespec="minutes")


def parse_time(value: str | None, loc: Location) -> datetime:
    """ISO 8601 string (naive = observer's local time) or None for now."""
    if not value:
        return datetime.now(UTC)
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=loc.tz)


def local_noon(loc: Location, day: date) -> datetime:
    return datetime.combine(day, time(12), tzinfo=loc.tz)


def observing_date(value: str | None, loc: Location) -> date:
    """The local date whose evening starts 'tonight'. Before noon with the Sun down, that's yesterday."""
    if value:
        return date.fromisoformat(value.strip())
    now = datetime.now(loc.tz)
    if now.hour < 12 and sun_altitude(now, loc) < 0:
        return now.date() - timedelta(days=1)
    return now.date()


# ---------------------------------------------------------------- geometry helpers

def observer(loc: Location) -> ae.Observer:
    return ae.Observer(loc.latitude, loc.longitude, loc.elevation_m)


def compass(azimuth_deg: float) -> str:
    points = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
    return points[round(azimuth_deg / 22.5) % 16]


def separation_deg(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    ra1, dec1, ra2, dec2 = map(math.radians, (ra1, dec1, ra2, dec2))
    h = math.sin((dec2 - dec1) / 2) ** 2 + math.cos(dec1) * math.cos(dec2) * math.sin((ra2 - ra1) / 2) ** 2
    return math.degrees(2 * math.asin(min(1.0, math.sqrt(h))))


Vec = tuple[float, float, float]


def vec(v: Any) -> Vec:
    """astronomy-engine vector or state vector as a plain tuple (AU, J2000 equatorial)."""
    return v.x, v.y, v.z


def dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec, b: Vec) -> Vec:
    return a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]


def unit(a: Vec) -> Vec:
    n = math.sqrt(dot(a, a))
    return a[0] / n, a[1] / n, a[2] / n


def wrap180(angle_deg: float) -> float:
    return (angle_deg + 180) % 360 - 180


def body_lon_lat(north: Vec, spin_deg: float, direction: Vec) -> tuple[float, float]:
    """East longitude and latitude on a rotating body of the point facing `direction`.

    `north` is the body's pole and `spin_deg` the IAU prime-meridian angle W, measured along
    the body's equator from its ascending node on the J2000 equator.
    """
    node = unit(cross((0.0, 0.0, 1.0), north))
    quarter = cross(north, node)
    w = math.radians(spin_deg % 360)
    prime = tuple(node[i] * math.cos(w) + quarter[i] * math.sin(w) for i in range(3))
    d = unit(direction)
    lon = math.degrees(math.atan2(dot(d, cross(north, prime)), dot(d, prime)))
    return lon, math.degrees(math.asin(max(-1.0, min(1.0, dot(d, north)))))


def airmass(altitude_deg: float) -> float | None:
    """Kasten & Young (1989) airmass; None below the horizon."""
    if altitude_deg <= 0:
        return None
    return 1.0 / (math.sin(math.radians(altitude_deg)) + 0.50572 * (altitude_deg + 6.07995) ** -1.6364)


def constellation(ra_deg: float, dec_deg: float) -> dict[str, str]:
    c = ae.Constellation(ra_deg / 15.0, dec_deg)
    name = "Antlia" if c.symbol == "Ant" else c.name
    return {"abbreviation": c.symbol, "name": name}


def _body(target: Target) -> ae.Body:
    """astronomy-engine body for a target. Fixed targets use the Star1 slot, so call this
    immediately before the computation that uses it (no awaits in between)."""
    if target.body is not None:
        return target.body
    ae.DefineStar(ae.Body.Star1, target.ra_deg / 15.0, target.dec_deg, 1000.0)
    return ae.Body.Star1


def horizontal(target: Target, when: datetime, loc: Location) -> dict[str, float]:
    """Topocentric apparent position with standard refraction."""
    t, obs = to_time(when), observer(loc)
    eq = ae.Equator(_body(target), t, obs, True, True)
    hor = ae.Horizon(t, obs, eq.ra, eq.dec, ae.Refraction.Normal)
    return {"altitude_deg": hor.altitude, "azimuth_deg": hor.azimuth, "ra_of_date_deg": eq.ra * 15, "dec_of_date_deg": eq.dec}


def sun_altitude(when: datetime, loc: Location) -> float:
    return horizontal(Target("Sun", ae.Body.Sun), when, loc)["altitude_deg"]


def j2000_position(target: Target, when: datetime) -> tuple[float, float]:
    """Geocentric astrometric J2000 RA/Dec in degrees."""
    if target.is_fixed:
        return target.ra_deg, target.dec_deg
    vec = ae.GeoVector(target.body, to_time(when), True)
    eq = ae.EquatorFromVector(vec)
    return eq.ra * 15, eq.dec


def altitude_track(target: Target, start: datetime, end: datetime, loc: Location, step_min: int = 10) -> list[tuple[datetime, float, float]]:
    """(time, altitude, azimuth) samples from start to end inclusive."""
    samples = []
    t = start
    while t <= end:
        h = horizontal(target, t, loc)
        samples.append((t, h["altitude_deg"], h["azimuth_deg"]))
        t += timedelta(minutes=step_min)
    return samples


def fast_tracks(
    coords: list[tuple[float, float]], times: list[datetime], loc: Location
) -> list[list[tuple[float, float]]]:
    """(altitude, azimuth) for many fixed J2000 positions at many times, without refraction.

    Precesses each position to the equinox of date once (at the middle time), then
    uses local sidereal time. Accurate to well under a degree, which is plenty for
    ranking targets over a night.
    """
    mid = to_time(times[len(times) // 2])
    rot = ae.Rotation_EQJ_EQD(mid)
    lat = math.radians(loc.latitude)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    precessed = []
    for ra, dec in coords:
        vec = ae.RotateVector(rot, ae.VectorFromSphere(ae.Spherical(dec, ra, 1.0), mid))
        sph = ae.SphereFromVector(vec)
        precessed.append((math.radians(sph.lon), math.radians(sph.lat)))
    lsts = [math.radians((ae.SiderealTime(to_time(t)) * 15 + loc.longitude) % 360) for t in times]
    tracks = []
    for ra, dec in precessed:
        sin_dec, cos_dec = math.sin(dec), math.cos(dec)
        track = []
        for lst in lsts:
            ha = lst - ra
            sin_alt = sin_lat * sin_dec + cos_lat * cos_dec * math.cos(ha)
            az = math.atan2(-math.sin(ha) * cos_dec, sin_dec * cos_lat - cos_dec * math.cos(ha) * sin_lat)
            track.append((math.degrees(math.asin(max(-1.0, min(1.0, sin_alt)))), math.degrees(az) % 360))
        tracks.append(track)
    return tracks


# ---------------------------------------------------------------- night and events

@dataclass
class Night:
    date: date
    sunset: datetime | None
    sunrise: datetime | None
    civil: tuple[datetime | None, datetime | None]
    nautical: tuple[datetime | None, datetime | None]
    astronomical: tuple[datetime | None, datetime | None]
    darkest: str  # astronomical | nautical | civil | bright_twilight | none (midnight sun) | polar_night
    window: tuple[datetime, datetime]  # darkest available window

    def to_dict(self, loc: Location) -> dict[str, Any]:
        def pair(p: tuple[datetime | None, datetime | None]) -> dict[str, str | None]:
            return {"dusk": fmt(p[0], loc), "dawn": fmt(p[1], loc)}
        hours = (self.window[1] - self.window[0]).total_seconds() / 3600 if self.darkest != "none" else 0.0
        return {
            "date": self.date.isoformat(),
            "sunset": fmt(self.sunset, loc),
            "sunrise": fmt(self.sunrise, loc),
            "civil_twilight": pair(self.civil),
            "nautical_twilight": pair(self.nautical),
            "astronomical_twilight": pair(self.astronomical),
            "darkest_sky": self.darkest,
            "dark_window": {"start": fmt(self.window[0], loc), "end": fmt(self.window[1], loc), "hours": round(hours, 2)},
        }


def night(loc: Location, day: date) -> Night:
    """Sunset, twilight boundaries and sunrise for the night beginning on `day` (local)."""
    noon = local_noon(loc, day)
    t0, obs = to_time(noon), observer(loc)

    def search(direction: ae.Direction, alt: float | None = None) -> datetime | None:
        if alt is None:  # sunrise/sunset proper, with refraction and the Sun's semidiameter
            ev = ae.SearchRiseSet(ae.Body.Sun, obs, direction, t0, 1.0)
        else:
            ev = ae.SearchAltitude(ae.Body.Sun, obs, direction, t0, 1.0, alt)
        return to_datetime(ev) if ev else None

    sunset, sunrise = search(ae.Direction.Set), search(ae.Direction.Rise)
    bands = {name: (search(ae.Direction.Set, alt), search(ae.Direction.Rise, alt)) for name, alt in
             (("civil", -6.0), ("nautical", -12.0), ("astronomical", -18.0))}

    next_noon = noon + timedelta(days=1)
    darkest, window = "none", (noon, noon)
    for name in ("astronomical", "nautical", "civil"):
        dusk, dawn = bands[name]
        if dusk and dawn:
            darkest, window = name, (dusk, dawn)
            break
    else:
        if sun_altitude(noon, loc) < -18:
            darkest, window = "polar_night", (noon, next_noon)
        elif sunset and sunrise:
            darkest, window = "bright_twilight", (sunset, sunrise)
    return Night(day, sunset, sunrise, bands["civil"], bands["nautical"], bands["astronomical"], darkest, window)


def rise_set_transit(target: Target, loc: Location, day: date) -> dict[str, Any]:
    """Next rise, upper transit and set after local noon of `day`."""
    t0, obs = to_time(local_noon(loc, day)), observer(loc)
    body = _body(target)
    rise = ae.SearchRiseSet(body, obs, ae.Direction.Rise, t0, 1.0)
    set_ = ae.SearchRiseSet(body, obs, ae.Direction.Set, t0, 1.0)
    upper = ae.SearchHourAngle(body, obs, 0.0, t0, +1)
    lower = ae.SearchHourAngle(body, obs, 12.0, t0, +1)
    out: dict[str, Any] = {
        "rise": fmt(rise, loc),
        "rise_azimuth_deg": None,
        "transit": fmt(upper.time, loc),
        "transit_altitude_deg": round(upper.hor.altitude, 2),
        "set": fmt(set_, loc),
        "set_azimuth_deg": None,
    }
    if rise:
        az = horizontal(target, to_datetime(rise), loc)["azimuth_deg"]
        out["rise_azimuth_deg"] = f"{az:.0f} ({compass(az)})"
    if set_:
        az = horizontal(target, to_datetime(set_), loc)["azimuth_deg"]
        out["set_azimuth_deg"] = f"{az:.0f} ({compass(az)})"
    if rise is None and set_ is None:
        out["status"] = "circumpolar (never sets)" if lower.hor.altitude > 0 else "never rises"
    return {k: v for k, v in out.items() if v is not None}


def moon_phase(when: datetime) -> dict[str, Any]:
    t = to_time(when)
    angle = ae.MoonPhase(t)
    illum = ae.Illumination(ae.Body.Moon, t)
    return {
        "phase": MOON_PHASES[int(((angle + 22.5) % 360) // 45)],
        "illuminated_percent": round(illum.phase_fraction * 100, 1),
        "age_days": round(angle / 360 * SYNODIC_MONTH_DAYS, 1),
        "phase_angle_deg": round(angle, 1),
        "magnitude": round(illum.mag, 2),
    }


def moon_quarters(start: datetime, end: datetime) -> list[tuple[str, datetime]]:
    out = []
    mq = ae.SearchMoonQuarter(to_time(start))
    while (dt := to_datetime(mq.time)) <= end:
        out.append((QUARTER_NAMES[mq.quarter], dt))
        mq = ae.NextMoonQuarter(mq)
    return out


def body_details(name: str, when: datetime, loc: Location | None) -> dict[str, Any]:
    """Physical/apparent details for a solar-system body at a moment."""
    body = BODIES[name]
    t = to_time(when)
    target = Target(name.title(), body)
    ra, dec = j2000_position(target, when)
    out: dict[str, Any] = {
        "name": name.title(),
        "ra_deg": round(ra, 4),
        "dec_deg": round(dec, 4),
        "constellation": constellation(ra, dec)["name"],
    }
    illum = ae.Illumination(body, t)
    dist_au = illum.geo_dist
    out["magnitude"] = round(illum.mag, 2)
    out["distance_au"] = round(dist_au, 5)
    out["apparent_diameter_arcsec"] = round(2 * math.degrees(math.atan(RADIUS_KM[name] / (dist_au * AU_KM))) * 3600, 2)
    if name not in ("sun",):
        out["illuminated_percent"] = round(illum.phase_fraction * 100, 1)
    if name not in ("sun", "moon"):
        el = ae.Elongation(body, t)
        out["elongation_deg"] = round(el.elongation, 1)
        out["sky"] = "evening" if el.visibility == ae.Visibility.Evening else "morning"
    if name == "saturn":
        out["ring_tilt_deg"] = round(illum.ring_tilt, 2)
    if loc:
        h = horizontal(target, when, loc)
        out["altitude_deg"] = round(h["altitude_deg"], 2)
        out["azimuth_deg"] = round(h["azimuth_deg"], 2)
        out["direction"] = compass(h["azimuth_deg"])
    return out


def lunar_eclipses(start: datetime, count: int, loc: Location | None) -> list[dict[str, Any]]:
    out = []
    ecl = ae.SearchLunarEclipse(to_time(start))
    for _ in range(count):
        peak = to_datetime(ecl.peak)
        item: dict[str, Any] = {
            "kind": ecl.kind.name.lower(),
            "peak_utc": peak.isoformat(timespec="minutes"),
            "obscuration_percent": round(ecl.obscuration * 100, 1),
            "penumbral_duration_min": round(2 * ecl.sd_penum),
            "partial_duration_min": round(2 * ecl.sd_partial) or None,
            "total_duration_min": round(2 * ecl.sd_total) or None,
        }
        if loc:
            item["peak_local"] = fmt(peak, loc)
            alt = horizontal(Target("Moon", ae.Body.Moon), peak, loc)["altitude_deg"]
            item["moon_altitude_at_peak_deg"] = round(alt, 1)
            item["visible_at_peak"] = alt > 0
        out.append({k: v for k, v in item.items() if v is not None})
        ecl = ae.NextLunarEclipse(ecl.peak)
    return out


def local_solar_eclipses(start: datetime, years: float, loc: Location) -> list[dict[str, Any]]:
    """Solar eclipses visible (Sun above horizon at peak) from the location."""
    out = []
    end = start + timedelta(days=365.25 * years)
    obs = observer(loc)
    ecl = ae.SearchLocalSolarEclipse(to_time(start), obs)
    while to_datetime(ecl.peak.time) <= end:
        if ecl.peak.altitude > 0:
            item = {
                "kind": ecl.kind.name.lower(),
                "partial_begins": fmt(ecl.partial_begin.time, loc),
                "total_begins": fmt(ecl.total_begin.time, loc) if ecl.total_begin else None,
                "peak": fmt(ecl.peak.time, loc),
                "total_ends": fmt(ecl.total_end.time, loc) if ecl.total_end else None,
                "partial_ends": fmt(ecl.partial_end.time, loc),
                "sun_altitude_at_peak_deg": round(ecl.peak.altitude, 1),
                "obscuration_percent": round(ecl.obscuration * 100, 1),
            }
            out.append({k: v for k, v in item.items() if v is not None})
        ecl = ae.NextLocalSolarEclipse(ecl.peak.time, obs)
    return out
