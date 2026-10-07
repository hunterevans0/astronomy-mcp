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

import csv
import io
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
from astronomy_mcp.http import UpstreamError, get_json, get_json_file, get_text_file
from astronomy_mcp.location import Location, data_dir
from astronomy_mcp.sky import Vec

CELESTRAK = "https://celestrak.org/NORAD/elements/gp.php"
SATCAT_CSV = "https://celestrak.org/pub/satcat.csv"
LL2_PREVIOUS = "https://ll.thespacedevs.com/2.3.0/launches/previous/"
RCS_MAGNITUDE_ZERO_POINT = 5.0
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
    magnitude_basis: str | None = None

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
            "standard_magnitude": round(self.standard_magnitude, 1) if self.standard_magnitude is not None else None,
            "standard_magnitude_basis": self.magnitude_basis,
        }


def default_standard_magnitude(norad_id: int, name: str) -> tuple[float | None, str | None]:
    if norad_id in STANDARD_MAGNITUDE:
        return STANDARD_MAGNITUDE[norad_id], "built-in estimate (±1)"
    if name.upper().startswith("STARLINK"):
        return STARLINK_STANDARD_MAGNITUDE, "built-in Starlink estimate (±1)"
    return None, None


def magnitude_from_rcs(rcs_m2: float) -> float:
    """Very rough standard magnitude from radar cross-section. Radar and optical size differ, so
    expect ±1.5 magnitudes; calibrated so the ISS, Hubble and SL-16 rocket bodies come out near
    their observed brightness."""
    return RCS_MAGNITUDE_ZERO_POINT - 2.5 * math.log10(rcs_m2)


def satellite_from_omm(fields: dict[str, Any], standard_magnitude: float | None = None,
                       rcs: dict[int, float] | None = None) -> Satellite:
    rec = Satrec()
    omm.initialize(rec, fields)
    norad, name = int(fields["NORAD_CAT_ID"]), fields.get("OBJECT_NAME", "").strip()
    if standard_magnitude is not None:
        mag, basis = standard_magnitude, "given by user"
    else:
        mag, basis = default_standard_magnitude(norad, name)
        if mag is None and rcs and rcs.get(norad):
            mag, basis = magnitude_from_rcs(rcs[norad]), "rough estimate from radar cross-section (±1.5)"
    return Satellite(
        name=name, norad_id=norad, intl_designator=fields.get("OBJECT_ID", ""), rec=rec,
        epoch=datetime.fromisoformat(fields["EPOCH"]).replace(tzinfo=UTC),
        mean_motion=float(fields["MEAN_MOTION"]), revolutions_at_epoch=int(fields.get("REV_AT_EPOCH") or 0),
        standard_magnitude=mag, magnitude_basis=basis,
    )


_rcs: dict[int, float] | None = None


async def rcs_table() -> dict[int, float]:
    """NORAD id to radar cross-section (m²) from CelesTrak's SATCAT, refreshed weekly. Empty if unavailable."""
    global _rcs
    if _rcs is None:
        try:
            text = await get_text_file(SATCAT_CSV, data_dir() / "celestrak" / "satcat.csv", source="CelesTrak SATCAT",
                                       max_age=7 * 86400)
        except UpstreamError:
            return {}
        table = {}
        for row in csv.DictReader(io.StringIO(text)):
            try:
                value = float(row.get("RCS") or 0)
                if value > 0:
                    table[int(row["NORAD_CAT_ID"])] = value
            except (TypeError, ValueError, KeyError):
                continue
        _rcs = table
    return _rcs


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
    records = await _celestrak({"GROUP": name}, f"group-{name}")
    rcs = await rcs_table()
    return [satellite_from_omm(r, rcs=rcs) for r in records]


async def find_satellite(query: str, standard_magnitude: float | None = None) -> Satellite:
    """A satellite by NORAD number, common name (ISS, Tiangong, Hubble) or CelesTrak name."""
    text = query.strip()
    norad = int(text) if text.isdigit() else ALIASES.get(text.lower())
    if norad is not None:
        records = await _celestrak({"CATNR": str(norad)}, f"catnr-{norad}")
        if not records:
            raise ValueError(f"CelesTrak has no current orbit for NORAD {norad} (it may have decayed).")
        return satellite_from_omm(records[0], standard_magnitude, await rcs_table())
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    records = await _celestrak({"NAME": text}, f"name-{slug}")
    if not records:
        raise ValueError(f"CelesTrak has no satellite named like '{query}'. Try its NORAD catalog number.")
    exact = [r for r in records if r.get("OBJECT_NAME", "").strip().lower() == text.lower()]
    if len(exact) == 1 or len(records) == 1:
        return satellite_from_omm((exact or records)[0], standard_magnitude, await rcs_table())
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
            "magnitude_rough": True if lk.magnitude is not None and (sat.magnitude_basis or "").startswith("rough") else None,
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
    launches, ll2_error = await starlink_launches()
    recent = [r for r in await _celestrak({"GROUP": "last-30-days"}, "group-last-30-days")
              if r.get("OBJECT_NAME", "").upper().startswith("STARLINK") or r.get("OBJECT_ID", "")[:8] in launches]
    batches: dict[str, list[Satellite]] = {}
    for r in recent:
        batches.setdefault(r.get("OBJECT_ID", "")[:8], []).append(
            satellite_from_omm(r, STARLINK_STANDARD_MAGNITUDE))
    now = datetime.now(UTC)
    trains = []
    for launch_id, sats in sorted(batches.items()):
        if len(sats) < 3:
            continue
        mission, net = launches.get(launch_id, (None, None))
        launched = net or launch_date(sats)
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
            "mission": mission,
            "launched": launched.isoformat(timespec="minutes") if net else None,
            "launched_about": None if net else launched.date().isoformat(),
            "unnamed_in_catalog": sum(1 for s in sats if not s.name.upper().startswith("STARLINK")) or None,
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
        trains.append({k: v for k, v in train.items() if v is not None})
    out = {
        "location": loc.name,
        "from": sky.fmt(start, loc),
        "days": days,
        "count": len(trains),
        "trains": trains,
        "note": "Trains are brightest and tightest in the first days after launch, below about 350 km, and "
                "spread out and fade as they climb to their working orbit. Pass times are for the middle "
                "satellite; train_first_at and train_last_at bracket the line. Brightness varies with each "
                "satellite's attitude. Batches are found by name and by matching Launch Library's Starlink "
                "launches, so ones CelesTrak hasn't named yet are included; a launch only appears once "
                "CelesTrak has orbits for it, usually within a day.",
        "launch_library_unavailable": ll2_error,
    }
    return {k: v for k, v in out.items() if v is not None}


async def starlink_launches() -> tuple[dict[str, tuple[str, datetime]], str | None]:
    """Recent Starlink launches from Launch Library 2: {COSPAR launch id: (mission name, launch time)}."""
    try:
        payload = await get_json(LL2_PREVIOUS, {"search": "Starlink", "limit": 20, "mode": "normal"},
                                 source="Launch Library 2", ttl=3600)
    except UpstreamError as exc:
        return {}, str(exc)
    out = {}
    for r in payload.get("results", []):
        designator = r.get("launch_designator")
        if designator and r.get("net") and (r.get("status") or {}).get("abbrev") == "Success":
            out[designator] = (r.get("name", ""), datetime.fromisoformat(r["net"].replace("Z", "+00:00")))
    return out, None


# ---------------------------------------------------------------- transits of the Sun and Moon

BODY_RADIUS_KM = {"Sun": 695_700.0, "Moon": 1737.4}
SATELLITE_SPAN_M = {25544: 109.0, 48274: 55.0}  # longest dimension, for the apparent size


def body_vector_teme(body: str, when: datetime) -> Vec:
    """Geocentric position of the Sun or Moon in km, equator and equinox of date."""
    t = sky.to_time(when)
    v = ae.GeoMoon(t) if body == "Moon" else ae.GeoVector(ae.Body.Sun, t, True)
    v = ae.RotateVector(ae.Rotation_EQJ_EQD(t), v)
    return v.x * sky.AU_KM, v.y * sky.AU_KM, v.z * sky.AU_KM


def _sub(a: Vec, b: Vec) -> Vec:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def _angle_deg(a: Vec, b: Vec) -> float:
    c = sky.cross(a, b)
    return math.degrees(math.atan2(math.sqrt(sky.dot(c, c)), sky.dot(a, b)))


def centerline_point(sat: Vec, body: Vec, radius_km: float) -> Vec | None:
    """Where the line from the body's centre through the satellite meets a sphere of `radius_km`:
    the spot on the ground that sees the satellite exactly in front of the body's centre."""
    w = sky.unit(_sub(sat, body))
    sw = sky.dot(sat, w)
    disc = sw * sw - (sky.dot(sat, sat) - radius_km**2)
    if disc < 0:
        return None
    t = -sw - math.sqrt(disc)
    if t <= 0:
        return None
    return sat[0] + t * w[0], sat[1] + t * w[1], sat[2] + t * w[2]


def _geodetic(p: Vec) -> tuple[float, float]:
    lat = math.degrees(math.atan2(p[2], math.hypot(p[0], p[1]) * (1 - WGS84_E2)))
    return lat, math.degrees(math.atan2(p[1], p[0]))


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.atan2(y, x)) % 360


class TransitGeometry:
    """Satellite and Sun/Moon positions over one pass, Earth-fixed, with the body interpolated."""

    def __init__(self, sat: Satellite, body: str, start: datetime, end: datetime):
        self.sat, self.body, self.start, self.span = sat, body, start, (end - start).total_seconds()
        self.b0, self.b1 = body_vector_teme(body, start), body_vector_teme(body, end)

    def at(self, when: datetime) -> tuple[Vec, Vec] | None:
        """(satellite, body) in km, Earth-fixed."""
        jd, fr = _julian(when)
        err, r, _ = self.sat.rec.sgp4(jd, fr)
        if err:
            return None
        f = (when - self.start).total_seconds() / self.span if self.span else 0.0
        b = tuple(self.b0[k] + (self.b1[k] - self.b0[k]) * f for k in range(3))
        g = gstime(jd + fr)
        return _rotate_z(r, g), _rotate_z(b, g)  # type: ignore[arg-type]

    def separation(self, when: datetime, site: Vec) -> tuple[float, float]:
        """(angle between satellite and body centre, body's angular radius), degrees, seen from `site`."""
        got = self.at(when)
        if got is None:
            return 180.0, 0.0
        s, b = got
        to_body = _sub(b, site)
        radius = math.degrees(math.asin(BODY_RADIUS_KM[self.body] / math.sqrt(sky.dot(to_body, to_body))))
        return _angle_deg(_sub(s, site), to_body), radius


def _minimise_time(f: Any, lo: datetime, hi: datetime, tolerance_s: float = 0.002) -> datetime:
    golden = (math.sqrt(5) - 1) / 2
    a, b = hi - (hi - lo) * golden, lo + (hi - lo) * golden
    fa, fb = f(a), f(b)
    while (hi - lo).total_seconds() > tolerance_s:
        if fa < fb:
            hi, b, fb = b, a, fa
            a = hi - (hi - lo) * golden
            fa = f(a)
        else:
            lo, a, fa = a, b, fb
            b = lo + (hi - lo) * golden
            fb = f(b)
    return lo + (hi - lo) / 2


def _crossing_seconds(geo: TransitGeometry, site: Vec, peak: datetime) -> float:
    """How long the satellite is in front of the disk as seen from `site` (0 if it misses)."""
    def inside(t: datetime) -> bool:
        sep, radius = geo.separation(t, site)
        return sep < radius

    if not inside(peak):
        return 0.0
    edges = []
    for direction in (-1, 1):
        lo, hi = peak, peak + timedelta(seconds=direction * 10)
        for _ in range(40):
            mid = lo + (hi - lo) / 2
            lo, hi = (mid, hi) if inside(mid) else (lo, mid)
        edges.append(lo)
    return abs((edges[1] - edges[0]).total_seconds())


def find_transits(sat: Satellite, loc: Location, start: datetime, days: float, max_distance_km: float,
                  bodies: tuple[str, ...], min_body_altitude: float) -> list[dict[str, Any]]:
    """Passes in which the satellite crosses the Sun or Moon as seen from within `max_distance_km`."""
    obs = Observer(loc)
    # Project onto a sphere through the observer: at the observer's own height, since a 1 km height
    # difference moves the line by 1 km / tan(altitude) toward the body.
    radius = math.sqrt(sky.dot(obs.pos, obs.pos))
    found = []
    for rise, set_ in _horizon_passes(obs, sat, start, start + timedelta(days=days), max(0.0, min_body_altitude - 5)):
        for body in bodies:
            mid = rise + (set_ - rise) / 2
            body_alt = sky.horizontal(sky.Target(body, ae.Body.Sun if body == "Sun" else ae.Body.Moon), mid, loc)["altitude_deg"]
            if body_alt < min_body_altitude - 2:
                continue
            geo = TransitGeometry(sat, body, rise, set_)

            def ground_distance(t: datetime) -> float:
                got = geo.at(t)
                p = centerline_point(*got, radius) if got else None
                return math.radians(_angle_deg(p, obs.pos)) * radius if p else math.inf

            steps = int((set_ - rise).total_seconds())
            samples = [(ground_distance(rise + timedelta(seconds=k)), k) for k in range(steps + 1)]
            best, k = min(samples)
            if best > max_distance_km * 3:
                continue
            peak = _minimise_time(ground_distance, rise + timedelta(seconds=max(0, k - 1)), rise + timedelta(seconds=min(steps, k + 1)))
            distance = ground_distance(peak)
            if distance > max_distance_km:
                continue
            event = describe_transit(geo, obs, radius, peak, distance, loc)
            if event["body_altitude_deg"] >= min_body_altitude:
                found.append(event)
    found.sort(key=lambda e: e["time"])
    return found


def describe_transit(geo: TransitGeometry, obs: Observer, radius: float, peak: datetime, distance: float,
                     loc: Location) -> dict[str, Any]:
    s, b = geo.at(peak)  # type: ignore[misc]
    p = centerline_point(s, b, radius)
    lat, lon = _geodetic(p)  # type: ignore[arg-type]
    here_peak = _minimise_time(lambda t: geo.separation(t, obs.pos)[0], peak - timedelta(seconds=60), peak + timedelta(seconds=60))
    sep_here, body_radius = geo.separation(here_peak, obs.pos)
    on_line = _crossing_seconds(geo, p, peak)  # type: ignore[arg-type]
    here = _crossing_seconds(geo, obs.pos, here_peak)

    # Path width: how far off the centreline the satellite still touches the disk, by sampling a point 2 km off it.
    ahead, behind = geo.at(peak + timedelta(seconds=0.5)), geo.at(peak - timedelta(seconds=0.5))
    width = None
    if ahead and behind:
        along = _sub(centerline_point(*ahead, radius), centerline_point(*behind, radius))  # type: ignore[arg-type]
        across = sky.unit(sky.cross(sky.unit(p), along))  # type: ignore[arg-type]
        q = sky.unit(tuple(p[k] + 2.0 * across[k] for k in range(3)))  # type: ignore[index]
        q = (q[0] * radius, q[1] * radius, q[2] * radius)
        miss = min(geo.separation(peak + timedelta(seconds=dt / 10), q)[0] for dt in range(-30, 31))
        if miss > 0:
            width = 2 * 2.0 * body_radius / miss

    look = Observer(loc).look(geo.sat, peak)
    body_target = sky.Target(geo.body, ae.Body.Sun if geo.body == "Sun" else ae.Body.Moon)
    h = sky.horizontal(body_target, peak, loc)
    span = SATELLITE_SPAN_M.get(geo.sat.norad_id)
    out: dict[str, Any] = {
        "body": geo.body,
        "time": peak.astimezone(loc.tz).isoformat(timespec="milliseconds"),
        "body_altitude_deg": round(h["altitude_deg"], 1),
        "body_direction": sky.compass(h["azimuth_deg"]),
        "body_diameter_arcmin": round(2 * body_radius * 60, 1),
        "satellite_range_km": round(look.range_km) if look else None,
        "satellite_size_arcsec": round(span / (look.range_km * 1000) * 206265, 1) if span and look else None,
        "crossing_seconds_on_centerline": round(on_line, 2),
        "path_width_km": round(width, 1) if width else None,
        "centerline_nearest_you": {
            "distance_km": round(distance, 1),
            "direction": sky.compass(_bearing(loc.latitude, loc.longitude, lat, lon)) if distance > 0.05 else "here",
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
        },
        "from_your_location": {
            "transits": here > 0,
            "closest_approach_arcmin": round(sep_here * 60, 2),
            "disk_radius_arcmin": round(body_radius * 60, 2),
            "crossing_seconds": round(here, 2) if here else None,
            "time": here_peak.astimezone(loc.tz).isoformat(timespec="milliseconds"),
        },
    }
    if geo.body == "Moon":
        out["moon_illuminated_percent"] = sky.moon_phase(peak)["illuminated_percent"]
        sun_alt = sky.sun_altitude(peak, loc)
        out["sun_altitude_deg"] = round(sun_alt, 1)
        if sun_alt > -6:
            out["note"] = "Daytime or twilight Moon: the satellite is a dark silhouette on a faint Moon, hard to record."
    else:
        out["safety"] = "Solar transit: use a certified solar filter on the telescope and camera."
    out["from_your_location"] = {k: v for k, v in out["from_your_location"].items() if v is not None}
    return {k: v for k, v in out.items() if v is not None}
