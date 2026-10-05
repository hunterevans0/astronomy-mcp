"""Satellite passes from CelesTrak orbital elements, propagated with SGP4.

Elements come from CelesTrak as GP data (OMM JSON) and are cached on disk for two hours,
the most often CelesTrak allows the same file to be fetched. SGP4 gives positions in the
TEME frame, which are turned into the Earth-fixed frame with Greenwich mean sidereal time
(polar motion and the equation of the equinoxes are ignored: a few hundred metres). The
Sun's direction comes from Astronomy Engine. Earth's shadow is a cylinder of equatorial
radius, so the moment a satellite fades can be off by several seconds.

Brightness uses the standard-magnitude convention: a satellite's magnitude at 1000 km
range and 90° phase angle, scaled by distance and a diffuse-sphere phase function. Real
satellites are not spheres, so expect a magnitude or so of scatter, and flares are not
predicted.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

import astronomy as ae
from sgp4 import omm
from sgp4.api import Satrec
from sgp4.propagation import gstime

from astronomy_mcp import sky
from astronomy_mcp.http import UpstreamError, get_json_file
from astronomy_mcp.location import Location, data_dir
from astronomy_mcp.sky import Vec

CELESTRAK = "https://celestrak.org/NORAD/elements/gp.php"
GROUPS = ("visual", "stations", "starlink", "active")
CACHE_SECONDS = 2 * 3600

EARTH_RADIUS_KM = 6378.137
WGS84_E2 = 6.69437999014e-3
MU_KM3_S2 = 398600.4418
JD_UNIX_EPOCH = 2440587.5
SUN_LIMIT_DEG = -6.0  # observer's Sun must be below this (civil twilight) for a visible pass

ALIASES = {
    "iss": 25544, "international space station": 25544, "zarya": 25544,
    "tiangong": 48274, "css": 48274, "chinese space station": 48274, "tianhe": 48274,
    "hubble": 20580, "hst": 20580, "hubble space telescope": 20580,
}
# Approximate standard magnitudes (1000 km, 90° phase). Starlink varies a lot with attitude;
# trains just after launch are often brighter than this.
STANDARD_MAGNITUDE = {25544: -1.8, 48274: -0.8, 20580: 2.0}
STARLINK_STANDARD_MAGNITUDE = 5.0


# ---------------------------------------------------------------- elements

@dataclass
class Satellite:
    name: str
    norad_id: int
    intl_designator: str
    rec: Satrec
    epoch: datetime
    mean_motion: float  # revolutions per day
    revolutions_at_epoch: int
    standard_magnitude: float | None

    @property
    def period_min(self) -> float:
        return 1440 / self.mean_motion

    @property
    def altitude_km(self) -> float:
        n = self.mean_motion * 2 * math.pi / 86400
        return (MU_KM3_S2 / n**2) ** (1 / 3) - EARTH_RADIUS_KM

    def info(self) -> dict[str, Any]:
        return {
            "name": self.name, "norad_id": self.norad_id, "international_designator": self.intl_designator,
            "elements_epoch_utc": self.epoch.isoformat(timespec="minutes"),
            "mean_altitude_km": round(self.altitude_km), "period_min": round(self.period_min, 1),
            "standard_magnitude": self.standard_magnitude,
        }


def default_standard_magnitude(norad_id: int, name: str) -> float | None:
    if norad_id in STANDARD_MAGNITUDE:
        return STANDARD_MAGNITUDE[norad_id]
    if name.upper().startswith("STARLINK"):
        return STARLINK_STANDARD_MAGNITUDE
    return None


def satellite_from_omm(fields: dict[str, Any], standard_magnitude: float | None = None) -> Satellite:
    rec = Satrec()
    omm.initialize(rec, fields)
    norad, name = int(fields["NORAD_CAT_ID"]), fields.get("OBJECT_NAME", "").strip()
    return Satellite(
        name=name, norad_id=norad, intl_designator=fields.get("OBJECT_ID", ""), rec=rec,
        epoch=datetime.fromisoformat(fields["EPOCH"]).replace(tzinfo=UTC),
        mean_motion=float(fields["MEAN_MOTION"]), revolutions_at_epoch=int(fields.get("REV_AT_EPOCH") or 0),
        standard_magnitude=standard_magnitude if standard_magnitude is not None else default_standard_magnitude(norad, name),
    )


async def _celestrak(params: dict[str, str], cache_name: str) -> list[dict[str, Any]]:
    try:
        data = await get_json_file(CELESTRAK, {**params, "FORMAT": "json"}, data_dir() / "celestrak" / f"{cache_name}.json",
                                   source="CelesTrak", max_age=CACHE_SECONDS, timeout=90)
    except UpstreamError as exc:
        if "No GP data found" in str(exc):
            return []
        raise
    return data if isinstance(data, list) else []


async def group(name: str) -> list[Satellite]:
    if name not in GROUPS and name != "last-30-days":
        raise ValueError(f"Unknown satellite group '{name}'; choose from {', '.join(GROUPS)}.")
    return [satellite_from_omm(r) for r in await _celestrak({"GROUP": name}, f"group-{name}")]


async def find_satellite(query: str, standard_magnitude: float | None = None) -> Satellite:
    """A satellite by NORAD number, common name (ISS, Tiangong, Hubble) or CelesTrak name."""
    text = query.strip()
    norad = int(text) if text.isdigit() else ALIASES.get(text.lower())
    if norad is not None:
        records = await _celestrak({"CATNR": str(norad)}, f"catnr-{norad}")
        if not records:
            raise ValueError(f"CelesTrak has no current orbit for NORAD {norad} (it may have decayed).")
        return satellite_from_omm(records[0], standard_magnitude)
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    records = await _celestrak({"NAME": text}, f"name-{slug}")
    if not records:
        raise ValueError(f"CelesTrak has no satellite named like '{query}'. Try its NORAD catalog number.")
    exact = [r for r in records if r.get("OBJECT_NAME", "").strip().lower() == text.lower()]
    if len(exact) == 1 or len(records) == 1:
        return satellite_from_omm((exact or records)[0], standard_magnitude)
    options = "; ".join(f"{r['OBJECT_NAME'].strip()} ({r['NORAD_CAT_ID']})" for r in records[:12])
    raise ValueError(f"Several satellites match '{query}': {options}. Pass the NORAD number.")


# ---------------------------------------------------------------- geometry

def _julian(dt: datetime) -> tuple[float, float]:
    jd = dt.timestamp() / 86400 + JD_UNIX_EPOCH
    whole = math.floor(jd - 0.5) + 0.5
    return whole, jd - whole


def observer_ecef(loc: Location) -> tuple[Vec, Vec, Vec, Vec]:
    """Observer position (km) and local east, north and up unit vectors, Earth-fixed (WGS84)."""
    lat, lon = math.radians(loc.latitude), math.radians(loc.longitude)
    h = loc.elevation_m / 1000
    sl, cl, so, co = math.sin(lat), math.cos(lat), math.sin(lon), math.cos(lon)
    n = EARTH_RADIUS_KM / math.sqrt(1 - WGS84_E2 * sl * sl)
    pos = ((n + h) * cl * co, (n + h) * cl * so, (n * (1 - WGS84_E2) + h) * sl)
    return pos, (-so, co, 0.0), (-sl * co, -sl * so, cl), (cl * co, cl * so, sl)


def _rotate_z(v: Vec, angle: float) -> Vec:
    """Inertial (TEME) to Earth-fixed: rotate by Greenwich sidereal angle."""
    c, s = math.cos(angle), math.sin(angle)
    return c * v[0] + s * v[1], -s * v[0] + c * v[1], v[2]


def sun_direction_teme(when: datetime) -> Vec:
    """Unit vector to the Sun, equator and equinox of date (TEME to within a few arcseconds)."""
    t = sky.to_time(when)
    v = ae.RotateVector(ae.Rotation_EQJ_EQD(t), ae.GeoVector(ae.Body.Sun, t, True))
    return sky.unit(sky.vec(v))


def in_sunlight(r: Vec, sun: Vec) -> bool:
    """Outside Earth's cylindrical shadow."""
    along = sky.dot(r, sun)
    if along > 0:
        return True
    perp = (r[0] - along * sun[0], r[1] - along * sun[1], r[2] - along * sun[2])
    return sky.dot(perp, perp) > EARTH_RADIUS_KM**2


def magnitude(standard: float | None, range_km: float, phase_deg: float) -> float | None:
    if standard is None:
        return None
    phi = math.radians(phase_deg)
    phase = max(1e-4, math.sin(phi) + (math.pi - phi) * math.cos(phi))  # 1 at 90°
    return standard + 5 * math.log10(range_km / 1000) - 2.5 * math.log10(phase)


@dataclass
class Look:
    when: datetime
    altitude: float
    azimuth: float
    range_km: float
    sunlit: bool
    sun_altitude: float
    magnitude: float | None

    @property
    def visible(self) -> bool:
        return self.sunlit and self.sun_altitude < SUN_LIMIT_DEG

    def point(self, loc: Location) -> dict[str, Any]:
        out = {
            "time": self.when.astimezone(loc.tz).isoformat(timespec="seconds"),
            "altitude_deg": round(self.altitude),
            "azimuth_deg": round(self.azimuth),
            "direction": sky.compass(self.azimuth),
        }
        return out


class Observer:
    """Precomputed observer geometry for fast repeated looks."""

    def __init__(self, loc: Location):
        self.loc = loc
        self.pos, self.east, self.north, self.up = observer_ecef(loc)

    def _topocentric(self, sat: Satellite, when: datetime) -> tuple[Vec, Vec, float] | None:
        jd, fr = _julian(when)
        err, r, _ = sat.rec.sgp4(jd, fr)
        if err:
            return None
        g = gstime(jd + fr)
        fixed = _rotate_z(r, g)
        rho = (fixed[0] - self.pos[0], fixed[1] - self.pos[1], fixed[2] - self.pos[2])
        return r, rho, g

    def altitude(self, sat: Satellite, when: datetime) -> float:
        """Altitude in degrees (no refraction); -90 if SGP4 fails, e.g. for a decayed orbit."""
        got = self._topocentric(sat, when)
        if got is None:
            return -90.0
        rho = got[1]
        return math.degrees(math.asin(sky.dot(rho, self.up) / math.sqrt(sky.dot(rho, rho))))

    def look(self, sat: Satellite, when: datetime, sun: Vec | None = None) -> Look | None:
        got = self._topocentric(sat, when)
        if got is None:
            return None
        r, rho, g = got
        sun = sun or sun_direction_teme(when)
        rng = math.sqrt(sky.dot(rho, rho))
        alt = math.degrees(math.asin(sky.dot(rho, self.up) / rng))
        az = math.degrees(math.atan2(sky.dot(rho, self.east), sky.dot(rho, self.north))) % 360
        sun_fixed = _rotate_z(sun, g)
        sun_alt = math.degrees(math.asin(sky.dot(sun_fixed, self.up)))
        to_observer = (-rho[0] / rng, -rho[1] / rng, -rho[2] / rng)
        phase = math.degrees(math.acos(max(-1.0, min(1.0, sky.dot(sun_fixed, to_observer)))))
        lit = in_sunlight(r, sun)
        return Look(when, alt, az, rng, lit, sun_alt, magnitude(sat.standard_magnitude, rng, phase) if lit else None)


# ---------------------------------------------------------------- passes

COARSE_STEP = timedelta(seconds=20)
FINE_STEP = timedelta(seconds=5)


def dark_windows(loc: Location, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """Stretches between start and end with the Sun below civil twilight."""
    windows = []
    day = start.astimezone(loc.tz).date() - timedelta(days=1)
    while day <= end.astimezone(loc.tz).date():
        n = sky.night(loc, day)
        noon = sky.local_noon(loc, day)
        if n.civil[0] and n.civil[1]:
            span = n.civil
        elif sky.sun_altitude(noon, loc) < SUN_LIMIT_DEG:
            span = (noon, noon + timedelta(days=1))
        else:
            span = None
        if span and span[1] > start and span[0] < end:
            windows.append((max(span[0], start), min(span[1], end)))
        day += timedelta(days=1)
    return windows


def _crossing(obs: Observer, sat: Satellite, lo: datetime, hi: datetime, min_alt: float) -> datetime:
    """Bisect for the moment altitude crosses min_alt between lo and hi (to a second)."""
    rising = obs.altitude(sat, lo) < min_alt
    while hi - lo > timedelta(seconds=1):
        mid = lo + (hi - lo) / 2
        if (obs.altitude(sat, mid) < min_alt) == rising:
            lo = mid
        else:
            hi = mid
    return lo + (hi - lo) / 2


def _horizon_passes(obs: Observer, sat: Satellite, start: datetime, end: datetime,
                    min_alt: float) -> list[tuple[datetime, datetime]]:
    """(rise, set) through min_alt for every pass overlapping [start, end]."""
    passes = []
    t, prev = start, obs.altitude(sat, start)
    rise = start if prev >= min_alt else None
    if rise is not None:  # already up: walk back to the real rise
        back = start
        while obs.altitude(sat, back) >= min_alt and start - back < timedelta(minutes=30):
            back -= COARSE_STEP
        rise = _crossing(obs, sat, back, back + COARSE_STEP, min_alt)
    while t < end or rise is not None:
        nxt = t + COARSE_STEP
        alt = obs.altitude(sat, nxt)
        if rise is None and prev < min_alt <= alt:
            rise = _crossing(obs, sat, t, nxt, min_alt)
        elif rise is not None and alt < min_alt <= prev:
            passes.append((rise, _crossing(obs, sat, t, nxt, min_alt)))
            rise = None
        if rise is not None and nxt - rise > timedelta(hours=3):  # geostationary or similar: never sets
            passes.append((rise, nxt))
            rise = None
        t, prev = nxt, alt
    return passes


def describe_pass(obs: Observer, sat: Satellite, rise: datetime, set_: datetime) -> dict[str, Any]:
    loc = obs.loc
    sun = sun_direction_teme(rise + (set_ - rise) / 2)
    count = max(2, int((set_ - rise) / FINE_STEP))
    looks = [lk for k in range(count + 1) if (lk := obs.look(sat, rise + (set_ - rise) * k / count, sun))]
    if not looks:
        return {"visible": False, "reason": "orbit could not be propagated"}
    highest = max(looks, key=lambda lk: lk.altitude)
    seen = [lk for lk in looks if lk.visible]
    out: dict[str, Any] = {
        "rise": looks[0].point(loc), "highest": highest.point(loc), "set": looks[-1].point(loc),
        "max_altitude_deg": round(highest.altitude),
    }
    if not seen:
        out["visible"] = False
        out["reason"] = "daylight or twilight" if highest.sun_altitude >= SUN_LIMIT_DEG else "in Earth's shadow"
        return out
    peak = max(seen, key=lambda lk: lk.altitude)
    mags = [lk.magnitude for lk in seen if lk.magnitude is not None]
    out.update({
        "visible": True,
        "visible_from": seen[0].point(loc),
        "visible_highest": peak.point(loc),
        "visible_until": seen[-1].point(loc),
        "visible_minutes": round((seen[-1].when - seen[0].when).total_seconds() / 60, 1),
        "brightest_magnitude": round(min(mags), 1) if mags else None,
        "appears_from_shadow": not looks[looks.index(seen[0]) - 1].sunlit if seen[0] is not looks[0] else False,
        "fades_into_shadow": not looks[looks.index(seen[-1]) + 1].sunlit if seen[-1] is not looks[-1] else False,
    })
    return {k: v for k, v in out.items() if v is not None}


def passes(sat: Satellite, loc: Location, start: datetime, days: float, min_alt: float,
           include_daylight: bool) -> list[dict[str, Any]]:
    obs = Observer(loc)
    end = start + timedelta(days=days)
    windows = [(start, end)] if include_daylight else dark_windows(loc, start, end)
    seen: set[datetime] = set()
    found = []
    for w0, w1 in windows:
        for rise, set_ in _horizon_passes(obs, sat, w0, w1, min_alt):
            key = rise.replace(microsecond=0)
            if key in seen:
                continue
            seen.add(key)
            info = describe_pass(obs, sat, rise, set_)
            if include_daylight or info.get("visible"):
                found.append(info)
    return found


def element_age_note(sat: Satellite, start: datetime, days: float) -> str:
    age = (start + timedelta(days=days) - sat.epoch).total_seconds() / 86400
    text = f"Orbital elements from {sat.epoch:%Y-%m-%d %H:%M} UTC."
    if age > 3:
        text += (" Predictions several days past the elements drift by up to a minute or more (more for low or "
                 "manoeuvring satellites like the ISS); check again closer to the time.")
    return text


# ---------------------------------------------------------------- what's up now

def overhead(sats: list[Satellite], loc: Location, when: datetime, min_alt: float,
             visible_only: bool) -> list[dict[str, Any]]:
    obs = Observer(loc)
    sun = sun_direction_teme(when)
    found = []
    for sat in sats:
        if abs((when - sat.epoch).total_seconds()) > 30 * 86400:
            continue  # stale elements, probably decayed
        lk = obs.look(sat, when, sun)
        if lk is None or lk.altitude < min_alt or (visible_only and not lk.visible):
            continue
        # Follow it to see where it leaves view (sets, or fades into Earth's shadow).
        t, leave = when, None
        for _ in range(100):
            t += timedelta(seconds=15)
            nxt = obs.look(sat, t, sun)
            if nxt is None or nxt.altitude < min_alt or (lk.sunlit and not nxt.sunlit):
                leave = nxt
                break
        item = {
            "name": sat.name,
            "norad_id": sat.norad_id,
            "altitude_deg": round(lk.altitude),
            "azimuth_deg": round(lk.azimuth),
            "direction": sky.compass(lk.azimuth),
            "range_km": round(lk.range_km),
            "sunlit": lk.sunlit,
            "visible": lk.visible,
            "magnitude": round(lk.magnitude, 1) if lk.magnitude is not None else None,
            "heading_toward": sky.compass(leave.azimuth) if leave else None,
            "leaves_view": ("fades into shadow" if leave and leave.altitude >= min_alt else "sets") if leave else None,
            "minutes_left_in_view": round((leave.when - when).total_seconds() / 60, 1) if leave else None,
        }
        found.append({k: v for k, v in item.items() if v is not None})
    found.sort(key=lambda s: (s.get("magnitude", 99.0), -s["altitude_deg"]))
    return found


# ---------------------------------------------------------------- Starlink trains

def _arg_of_latitude_offset(ref: tuple[Vec, Vec], other: Vec) -> float:
    """How far `other` is ahead of the reference satellite along the reference orbit, degrees."""
    r0, v0 = ref
    h = sky.unit(sky.cross(r0, v0))
    return math.degrees(math.atan2(sky.dot(sky.cross(r0, other), h), sky.dot(r0, other)))


def launch_date(sats: list[Satellite]) -> datetime:
    """Estimated from revolutions completed since launch, good to a day or so."""
    return min(s.epoch - timedelta(days=s.revolutions_at_epoch / s.mean_motion) for s in sats)


def train_spread(sats: list[Satellite], when: datetime) -> tuple[Satellite, float, float] | None:
    """The middle satellite of a batch and how far (degrees) the rest lead and trail it."""
    states = []
    for s in sats:
        jd, fr = _julian(when)
        err, r, v = s.rec.sgp4(jd, fr)
        if not err:
            states.append((s, r, v))
    if len(states) < 2:
        return None
    first = states[0]
    offsets = [_arg_of_latitude_offset((first[1], first[2]), r) for _, r, _ in states]
    mid = states[offsets.index(sorted(offsets)[len(offsets) // 2])]
    rel = [_arg_of_latitude_offset((mid[1], mid[2]), r) for _, r, _ in states]
    return mid[0], max(rel), min(rel)


async def starlink_trains(loc: Location, start: datetime, days: float, max_age_days: float,
                          min_alt: float) -> dict[str, Any]:
    recent = [r for r in await _celestrak({"GROUP": "last-30-days"}, "group-last-30-days")
              if r.get("OBJECT_NAME", "").upper().startswith("STARLINK")]
    batches: dict[str, list[Satellite]] = {}
    for r in recent:
        batches.setdefault(r.get("OBJECT_ID", "")[:8], []).append(satellite_from_omm(r))
    now = datetime.now(UTC)
    trains = []
    for launch_id, sats in sorted(batches.items()):
        if len(sats) < 3:
            continue
        launched = launch_date(sats)
        age = (now - launched).total_seconds() / 86400
        if age > max_age_days:
            continue
        spread = train_spread(sats, start)
        if spread is None:
            continue
        rep, lead_deg, trail_deg = spread
        period = rep.period_min
        spread_min = (lead_deg - trail_deg) / 360 * period
        altitude = median(s.altitude_km for s in sats)
        train: dict[str, Any] = {
            "launch": launch_id,
            "launched_about": launched.date().isoformat(),
            "satellites": len(sats),
            "median_altitude_km": round(altitude),
            "train_length_minutes": round(spread_min, 1),
            "state": ("tight train" if spread_min < 5 else "spreading out" if spread_min < 20 else
                      "dispersed along the orbit; no longer looks like a train"),
            "reference_satellite": f"{rep.name} ({rep.norad_id})",
        }
        if spread_min < 20:
            found = []
            for p in passes(rep, loc, start, days, min_alt, include_daylight=False):
                peak = datetime.fromisoformat(p["visible_highest"]["time"])
                p["train_first_at"] = (peak - timedelta(minutes=lead_deg / 360 * period)).isoformat(timespec="seconds")
                p["train_last_at"] = (peak - timedelta(minutes=trail_deg / 360 * period)).isoformat(timespec="seconds")
                found.append(p)
            train["visible_passes"] = found
        trains.append(train)
    return {
        "location": loc.name,
        "from": sky.fmt(start, loc),
        "days": days,
        "count": len(trains),
        "trains": trains,
        "note": "Trains are brightest and tightest in the first days after launch, below about 350 km, and "
                "spread out and fade as they climb to their working orbit. Pass times are for the middle "
                "satellite; train_first_at and train_last_at bracket the line. Brightness varies with each "
                "satellite's attitude, and newly launched satellites CelesTrak hasn't named yet are missed.",
    }
