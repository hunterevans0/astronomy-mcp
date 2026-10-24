"""Milky Way core photography: when the galactic centre is up in a dark, moonless sky, where to
point, and how the band is tilted against the horizon (offline).

The core is taken as the galactic centre (l = 0, b = 0) in Sagittarius. The band's tilt comes
from two points on the galactic equator either side of it: 0° lies along the horizon (the arch),
90° stands upright.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import astronomy as ae

from astronomy_mcp import sky
from astronomy_mcp.horizon import Horizon
from astronomy_mcp.location import Location
from astronomy_mcp.sky import Night, Target, compass, fmt

# ICRS -> galactic rotation (Hipparcos catalogue, ESA 1997, vol. 1 sec. 1.5.3).
EQ_TO_GAL = (
    (-0.0548755604, -0.8734370902, -0.4838350155),
    (0.4941094279, -0.4448296300, 0.7469822445),
    (-0.8676661490, -0.1980763734, 0.4559837762),
)
BAND_HALF_SPAN_DEG = 8.0  # galactic longitude either side of the core used to measure the band's tilt
THIN_MOON_PCT = 10.0  # a Moon this thin barely brightens the sky, so it doesn't close the window
MIN_WINDOW_HOURS = 0.5  # shorter windows aren't worth a trip
MOON = Target("Moon", ae.Body.Moon)


def galactic_to_equatorial(l_deg: float, b_deg: float) -> tuple[float, float]:
    """Galactic longitude/latitude to J2000 RA/Dec in degrees."""
    l, b = math.radians(l_deg), math.radians(b_deg)
    g = (math.cos(b) * math.cos(l), math.cos(b) * math.sin(l), math.sin(b))
    x, y, z = (sum(EQ_TO_GAL[j][i] * g[j] for j in range(3)) for i in range(3))
    return math.degrees(math.atan2(y, x)) % 360, math.degrees(math.asin(max(-1.0, min(1.0, z))))


CORE = galactic_to_equatorial(0.0, 0.0)
_BAND_POINTS = [CORE, galactic_to_equatorial(-BAND_HALF_SPAN_DEG, 0.0), galactic_to_equatorial(BAND_HALF_SPAN_DEG, 0.0)]


def band_tilt(alt1: float, az1: float, alt2: float, az2: float) -> float:
    """Angle between the horizon and the line joining two nearby sky positions, 0-90°."""
    across = sky.wrap180(az2 - az1) * math.cos(math.radians((alt1 + alt2) / 2))
    return math.degrees(math.atan2(abs(alt2 - alt1), abs(across)))


def composition(tilt_deg: float, altitude_deg: float) -> str:
    if tilt_deg >= 60:
        shape = "The band stands nearly upright: a vertical (portrait) frame or a vertical panorama suits it."
    elif tilt_deg >= 30:
        shape = "The band climbs diagonally from the horizon: a landscape frame with the core off-centre works."
    else:
        shape = "The band lies low along the horizon: the arch, best as a wide horizontal panorama."
    if altitude_deg < 15:
        shape += " The core is low, so haze and light domes on that horizon matter most."
    return shape


@dataclass
class Sample:
    time: datetime
    altitude: float
    azimuth: float
    tilt: float
    floor: float  # minimum altitude at this azimuth: the requested minimum or the terrain, whichever is higher
    moon_altitude: float | None = None

    @property
    def core_up(self) -> bool:
        return self.altitude >= self.floor

    def position(self, loc: Location) -> dict[str, Any]:
        return {"time": fmt(self.time, loc), "altitude_deg": round(self.altitude, 1), "azimuth_deg": round(self.azimuth),
                "direction": compass(self.azimuth), "band_tilt_deg": round(self.tilt)}


def _times(start: datetime, end: datetime, step_min: int) -> list[datetime]:
    count = max(1, int((end - start).total_seconds() // (step_min * 60)))
    return [start + (end - start) * i / count for i in range(count + 1)]


def core_track(loc: Location, start: datetime, end: datetime, min_altitude: float, horizon: Horizon | None,
               step_min: int) -> list[Sample]:
    times = _times(start, end, step_min)
    core, before, after = sky.fast_tracks(_BAND_POINTS, times, loc)
    samples = []
    for t, (alt, az), (alt1, az1), (alt2, az2) in zip(times, core, before, after):
        floor = max(min_altitude, horizon.altitude_at(az)) if horizon else min_altitude
        samples.append(Sample(t, alt, az, band_tilt(alt1, az1, alt2, az2), floor))
    return samples


def _runs(flags: list[bool]) -> list[tuple[int, int]]:
    """(first, last) index of each run of True."""
    runs, start = [], None
    for i, flag in enumerate([*flags, False]):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            runs.append((start, i - 1))
            start = None
    return runs


def plan_night(loc: Location, n: Night, min_altitude: float, horizon: Horizon | None, step_min: int = 5) -> dict[str, Any]:
    """The shooting window on one night: core above the minimum (and the terrain), sky dark, Moon down or thin."""
    row: dict[str, Any] = {"date": n.date.isoformat()}
    if n.darkest in ("none", "bright_twilight", "civil"):
        return {**row, "reason": "no real darkness: the Sun stays less than 12° below the horizon all night"}
    samples = core_track(loc, n.window[0], n.window[1], min_altitude, horizon, step_min)
    for s in samples:
        s.moon_altitude = sky.horizontal(MOON, s.time, loc)["altitude_deg"]
    phase = sky.moon_phase(samples[len(samples) // 2].time)
    thin = phase["illuminated_percent"] <= THIN_MOON_PCT
    moon_up = [(samples[a].time, samples[b].time) for a, b in _runs([s.moon_altitude > 0 for s in samples])]
    row |= {
        "darkness": n.darkest,
        "dark_window": {"start": fmt(n.window[0], loc), "end": fmt(n.window[1], loc)},
        "moon": {
            "phase": phase["phase"],
            "illuminated_percent": phase["illuminated_percent"],
            "up_during_darkness": [{"from": fmt(a, loc), "to": fmt(b, loc)} for a, b in moon_up] or "no",
        },
    }
    if n.darkest == "nautical":
        row["note"] = "The sky never gets fully dark (nautical twilight all night), so the Milky Way will be washed out."

    peak = max(samples, key=lambda s: s.altitude)
    if not any(s.core_up for s in samples):
        if peak.altitude < 0:
            reason = "the core is below the horizon throughout the dark hours"
        elif peak.floor > min_altitude:
            reason = (f"the core peaks at {peak.altitude:.0f}° toward {compass(peak.azimuth)} in darkness, behind terrain "
                      f"that rises to {peak.floor:.0f}° there")
        else:
            reason = f"the core peaks at {peak.altitude:.1f}° in darkness, below the {min_altitude:.0f}° minimum"
        return {**row, "reason": reason}

    good = [s.core_up and (thin or s.moon_altitude <= 0) for s in samples]
    if not any(good):
        return {**row, "reason": f"the Moon ({phase['illuminated_percent']:.0f}% lit) is up whenever the core is"}
    first, last = max(_runs(good), key=lambda r: r[1] - r[0])
    window = samples[first:last + 1]
    best = max(window, key=lambda s: s.altitude)
    hours = (window[-1].time - window[0].time).total_seconds() / 3600
    row |= {
        "shooting_window": {"start": fmt(window[0].time, loc), "end": fmt(window[-1].time, loc), "hours": round(hours, 1)},
        "start": window[0].position(loc),
        "best": best.position(loc),
        "end": window[-1].position(loc),
        "composition": composition(best.tilt, best.altitude),
    }
    if thin and moon_up:
        row["moon"]["note"] = "A thin crescent; it brightens the sky only slightly."
    return row


def compact(row: dict[str, Any]) -> dict[str, Any]:
    """One night in a multi-night list."""
    out = {"date": row["date"], "moon_illuminated_percent": row.get("moon", {}).get("illuminated_percent")}
    if "shooting_window" in row:
        best = row["best"]
        out |= {"shooting_window": row["shooting_window"],
                "best": {k: best[k] for k in ("time", "altitude_deg", "direction", "band_tilt_deg")}}
    else:
        out["reason"] = row["reason"]
    return {k: v for k, v in out.items() if v is not None}


def season(loc: Location, first: date, min_altitude: float, horizon: Horizon | None) -> dict[str, Any]:
    """Hours the core spends above the minimum in darkness, mid-month for the next 12 months (Moon ignored)."""
    hours: dict[str, float] = {}
    for k in range(12):
        month = (first.month - 1 + k) % 12 + 1
        day = date(first.year + (first.month - 1 + k) // 12, month, 15)
        n = sky.night(loc, day)
        h = 0.0
        if n.darkest in ("astronomical", "nautical", "polar_night"):
            samples = core_track(loc, n.window[0], n.window[1], min_altitude, horizon, 15)
            span = (n.window[1] - n.window[0]).total_seconds() / 3600
            h = span * sum(s.core_up for s in samples) / len(samples)
        hours[day.strftime("%Y-%m")] = round(h, 1)
    months = list(hours)
    runs = _runs([hours[m] >= MIN_WINDOW_HOURS for m in months])
    if not runs:
        summary = f"From here the core never clears {min_altitude:.0f}° while the sky is dark."
    else:
        def name(m: str) -> str:
            return datetime.strptime(m, "%Y-%m").strftime("%b %Y")
        spans = "; ".join(name(months[a]) if a == b else f"{name(months[a])} to {name(months[b])}" for a, b in runs)
        longest = max(hours, key=hours.get)
        summary = (f"Core above {min_altitude:.0f}° in darkness in {sum(b - a + 1 for a, b in runs)} of the next 12 "
                   f"months ({spans}); longest around {datetime.strptime(longest, '%Y-%m'):%B %Y} "
                   f"({hours[longest]} h a night, before the Moon is considered).")
    return {"summary": summary, "hours_per_night_by_month": hours}


def next_window(loc: Location, start: date, min_altitude: float, horizon: Horizon | None,
                max_days: int = 400) -> dict[str, Any] | None:
    """The first night from `start` with a shooting window of at least MIN_WINDOW_HOURS."""
    for i in range(max_days):
        n = sky.night(loc, start + timedelta(days=i))
        if n.darkest not in ("astronomical", "nautical", "polar_night"):
            continue
        # Cheap check first: skip nights when the core never clears the minimum in darkness.
        if not any(s.core_up for s in core_track(loc, n.window[0], n.window[1], min_altitude, horizon, 20)):
            continue
        row = plan_night(loc, n, min_altitude, horizon, 10)
        if row.get("shooting_window", {}).get("hours", 0) >= MIN_WINDOW_HOURS:
            return compact(row)
    return None


def plan(loc: Location, first: date, days: int, min_altitude: float, horizon: Horizon | None) -> dict[str, Any]:
    ra, dec = CORE
    out: dict[str, Any] = {
        "core": {"name": "Galactic centre (Sagittarius)", "ra_deg": round(ra, 4), "dec_deg": round(dec, 4),
                 "highest_possible_altitude_deg": round(90 - abs(loc.latitude - dec), 1),
                 **sky.rise_set_transit(Target("Galactic centre", None, ra, dec), loc, first)},
    }
    nights = [plan_night(loc, sky.night(loc, first + timedelta(days=i)), min_altitude, horizon, 5 if days == 1 else 10)
              for i in range(days)]
    if days == 1:
        out["night"] = nights[0]
    else:
        usable = [r for r in nights if r.get("shooting_window", {}).get("hours", 0) >= MIN_WINDOW_HOURS]
        ranked = sorted(usable, key=lambda r: (r["shooting_window"]["hours"], r["best"]["altitude_deg"]), reverse=True)
        out["best_nights"] = [compact(r) for r in ranked[:5]]
        out["nights"] = [compact(r) for r in nights]
    if not any(r.get("shooting_window", {}).get("hours", 0) >= MIN_WINDOW_HOURS for r in nights):
        out["next_good_night"] = next_window(loc, first + timedelta(days=days), min_altitude, horizon) or \
            "none within a year from here"
    out["season"] = season(loc, first, min_altitude, horizon)
    out["criteria"] = (f"Shooting window: Sun at least 18° down (or the darkest twilight the night gets), the core at "
                       f"least {min_altitude:.0f}° up and above the terrain, and the Moon below the horizon or under "
                       f"{THIN_MOON_PCT:.0f}% lit. Weather is not considered; check get_sky_forecast.")
    return out
