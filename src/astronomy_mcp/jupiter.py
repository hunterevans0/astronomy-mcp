"""Jupiter's Galilean moons and Great Red Spot (offline).

Moon positions come from Astronomy Engine's Jupiter-moon theory, backdated for light
travel time. Each moon is placed in two frames centred on Jupiter: one looking from
Earth (is it in front of or behind the disk?) and one looking from the Sun (is its
shadow on the disk, or is it inside Jupiter's shadow?). Moons are treated as points
and the shadow as a cylinder, so event times are good to a few minutes.

The Great Red Spot drifts in System II longitude. GRS_LONGITUDE is the value Sky &
Telescope's predictions assume (from JUPOS measurements) and needs updating about
once a year; tools take an override.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import astronomy as ae

from astronomy_mcp import sky
from astronomy_mcp.location import Location
from astronomy_mcp.sky import Vec, fmt

MOONS = ("Io", "Europa", "Ganymede", "Callisto")
RADIUS_AU = ae.JUPITER_EQUATORIAL_RADIUS_KM / ae.KM_PER_AU
OBLATENESS = ae.JUPITER_EQUATORIAL_RADIUS_KM / ae.JUPITER_POLAR_RADIUS_KM

# IAU prime-meridian angles at J2000 and rotation rates (deg/day) for the cloud-top systems.
SYSTEM_I = (67.1, 877.900)  # equatorial zone
SYSTEM_II = (43.3, 870.270)  # everything else, including the Great Red Spot

GRS_EPOCH = date(2026, 6, 1)
GRS_LONGITUDE = 91.0  # System II, at GRS_EPOCH
GRS_DRIFT_DEG_PER_DAY = 1.75 / 30.44
GRS_VISIBLE_WITHIN_DEG = 50.0  # of the central meridian; beyond that it is lost near the limb

# In front of and behind the disk as seen from Earth, then the same two as seen from the Sun.
KINDS = ("transit", "occultation", "shadow transit", "eclipse")
SCAN_STEP = timedelta(minutes=2)
MIN_ALTITUDE_DEG = 10.0  # Jupiter this high, and the Sun below civil twilight, to call an event observable
MAX_SUN_ALTITUDE_DEG = -6.0


def grs_longitude(when: datetime) -> float:
    return (GRS_LONGITUDE + GRS_DRIFT_DEG_PER_DAY * (when.date() - GRS_EPOCH).days) % 360


@dataclass
class MoonState:
    name: str
    west: float  # offsets from Jupiter's centre in equatorial radii, as seen from Earth
    north: float
    behind: float  # positive when farther than Jupiter
    flags: tuple[bool, bool, bool, bool]  # in the order of KINDS

    @property
    def hidden(self) -> bool:
        return self.flags[1] or self.flags[3]

    @property
    def status(self) -> str:
        if self.flags[1]:
            return "occulted (behind Jupiter)"
        if self.flags[3]:
            return "eclipsed (in Jupiter's shadow)"
        return "in transit across the disk" if self.flags[0] else "visible"


@dataclass
class Snapshot:
    moons: list[MoonState]
    distance_au: float
    cm_system_i: float
    cm_system_ii: float
    cm_system_iii: float


def _disk_coords(moon: Vec, toward: Vec, pole: Vec) -> tuple[float, float, float]:
    """(west, north, behind) of a moon in Jupiter radii for a viewer looking along `toward`."""
    line = sky.unit(toward)
    along = sky.dot(pole, line)
    north = sky.unit((pole[0] - along * line[0], pole[1] - along * line[1], pole[2] - along * line[2]))
    west = sky.cross(line, north)
    return sky.dot(moon, west) / RADIUS_AU, sky.dot(moon, north) / RADIUS_AU, sky.dot(moon, line) / RADIUS_AU


def _over_disk(west: float, north: float) -> bool:
    return west * west + (north * OBLATENESS) ** 2 < 1.0


def snapshot(when: datetime) -> Snapshot:
    t = sky.to_time(when)
    from_earth = ae.GeoVector(ae.Body.Jupiter, t, True)
    distance = from_earth.Length()
    emitted = t.AddDays(-distance / ae.C_AUDAY)  # when the light we see left Jupiter
    from_sun = sky.vec(ae.HelioVector(ae.Body.Jupiter, emitted))
    axis = ae.RotationAxis(ae.Body.Jupiter, emitted)
    pole = sky.vec(axis.north)
    theory = ae.JupiterMoons(emitted)
    moons = []
    for name in MOONS:
        position = sky.vec(getattr(theory, name.lower()))
        west, north, behind = _disk_coords(position, sky.vec(from_earth), pole)
        sun_west, sun_north, sun_behind = _disk_coords(position, from_sun, pole)
        earth_disk, sun_disk = _over_disk(west, north), _over_disk(sun_west, sun_north)
        flags = (earth_disk and behind < 0, earth_disk and behind > 0, sun_disk and sun_behind < 0, sun_disk and sun_behind > 0)
        moons.append(MoonState(name, west, north, behind, flags))
    to_earth = (-from_earth.x, -from_earth.y, -from_earth.z)

    def central_meridian(spin_deg: float) -> float:
        return -sky.body_lon_lat(pole, spin_deg, to_earth)[0] % 360  # Jupiter longitudes run west

    cms = [central_meridian(w0 + rate * emitted.tt) for w0, rate in (SYSTEM_I, SYSTEM_II)]
    return Snapshot(moons, distance, cms[0], cms[1], central_meridian(axis.spin))


def _observing(when: datetime, loc: Location) -> dict[str, Any]:
    alt = sky.horizontal(sky.Target("Jupiter", ae.Body.Jupiter), when, loc)["altitude_deg"]
    sun = sky.sun_altitude(when, loc)
    return {"jupiter_altitude_deg": round(alt), "sun_altitude_deg": round(sun),
            "observable_here": alt >= MIN_ALTITUDE_DEG and sun <= MAX_SUN_ALTITUDE_DEG}


def moons_now(when: datetime, loc: Location | None, grs: float | None = None) -> dict[str, Any]:
    """Where the four moons sit relative to Jupiter, plus the central meridian and Red Spot."""
    shown = loc or Location(0.0, 0.0)
    snap = snapshot(when)
    arcsec_per_radius = math.degrees(math.atan(RADIUS_AU / snap.distance_au)) * 3600
    moons = []
    for m in snap.moons:
        row = {
            "name": m.name,
            "status": m.status,
            "side": "west" if m.west > 0 else "east",
            "offset_east_west_jupiter_radii": round(abs(m.west), 2),
            "offset_north_jupiter_radii": round(m.north, 2),
            "separation_arcsec": round(math.hypot(m.west, m.north) * arcsec_per_radius),
            "shadow_on_jupiter": m.flags[2] or None,
        }
        moons.append({k: v for k, v in row.items() if v is not None})
    order = sorted([(m.west, m.name) for m in snap.moons if not m.hidden] + [(0.0, "[Jupiter]")])
    spot = grs if grs is not None else grs_longitude(when)
    past = sky.wrap180(snap.cm_system_ii - spot)
    minutes = abs(past) / SYSTEM_II[1] * 1440
    out: dict[str, Any] = {
        "time": fmt(when, shown),
        "jupiter": sky.body_details("jupiter", when, loc),
        "moons": moons,
        "east_to_west": "  ".join(name for _, name in order),
        "hidden": [m.name for m in snap.moons if m.hidden] or None,
        "central_meridian_deg": {"system_i": round(snap.cm_system_i, 1), "system_ii": round(snap.cm_system_ii, 1),
                                 "system_iii": round(snap.cm_system_iii, 1)},
        "great_red_spot": {
            "assumed_system_ii_longitude_deg": round(spot, 1),
            "on_visible_disk": abs(past) <= GRS_VISIBLE_WITHIN_DEG,
            "position": f"{minutes:.0f} min {'past' if past >= 0 else 'before'} the central meridian",
        },
        "note": "East and west are sky directions (west is where Jupiter sets); telescopes may mirror or invert "
                "the view. The Red Spot's longitude drifts, so its timing can be off by several minutes.",
    }
    if loc:
        out["observing"] = _observing(when, loc)
    return {k: v for k, v in out.items() if v is not None}


def _bisect(lo: datetime, hi: datetime, holds: Any) -> datetime:
    """Earliest time in (lo, hi], to a few seconds, at which holds(t) is true (false at lo, true at hi)."""
    while hi - lo > timedelta(seconds=5):
        mid = lo + (hi - lo) / 2
        if holds(mid):
            hi = mid
        else:
            lo = mid
    return hi


def find_events(start: datetime, end: datetime, grs: float | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """(events between start and end in time order, phenomena already under way at start)."""
    def spot_offset(t: datetime, snap: Snapshot) -> float:
        return sky.wrap180(snap.cm_system_ii - (grs if grs is not None else grs_longitude(t)))

    events: list[dict[str, Any]] = []
    t, prev = start, snapshot(start)
    under_way = [f"{m.name} {kind}" for m in prev.moons for kind, on in zip(KINDS, m.flags) if on]
    while t < end:
        nxt = min(t + SCAN_STEP, end)
        cur = snapshot(nxt)
        for i, (before, after) in enumerate(zip(prev.moons, cur.moons)):
            for k, kind in enumerate(KINDS):
                if before.flags[k] == after.flags[k]:
                    continue
                begins = after.flags[k]
                when = _bisect(t, nxt, lambda x, i=i, k=k, begins=begins: snapshot(x).moons[i].flags[k] == begins)
                event = {"time": when, "moon": after.name, "event": f"{kind} {'begins' if begins else 'ends'}"}
                # An eclipse behind the disk, or an occultation of a moon already in shadow, shows nothing.
                other = {1: 3, 3: 1}.get(k)
                if other is not None and snapshot(when).moons[i].flags[other]:
                    event["note"] = "not observable: the moon is " + ("already in shadow" if k == 1 else "behind Jupiter")
                events.append(event)
        if spot_offset(t, prev) < 0 <= spot_offset(nxt, cur) < 90:
            when = _bisect(t, nxt, lambda x: 0 <= spot_offset(x, snapshot(x)) < 90)
            events.append({"time": when, "event": "Great Red Spot crosses the central meridian"})
        t, prev = nxt, cur
    events.sort(key=lambda e: e["time"])
    return events, under_way


def events(
    start: datetime, hours: float, loc: Location | None, grs: float | None = None, observable_only: bool = False
) -> dict[str, Any]:
    shown = loc or Location(0.0, 0.0)
    found, under_way = find_events(start, start + timedelta(hours=hours), grs)
    rows = []
    for event in found:
        row = {**event, "time": fmt(event["time"], shown)}
        if loc:
            row |= _observing(event["time"], loc)
            if observable_only and (not row["observable_here"] or "note" in row):
                continue
        rows.append(row)
    spot = grs if grs is not None else grs_longitude(start)
    out = {
        "from": fmt(start, shown),
        "to": fmt(start + timedelta(hours=hours), shown),
        "under_way_at_start": under_way or None,
        "count": len(rows),
        "events": rows,
        "great_red_spot_longitude_assumed_deg": round(spot, 1),
        "note": "Times are when the moon's centre crosses Jupiter's limb or shadow edge, good to a few minutes; "
                "the moons take several minutes to fade or cross. The Red Spot is well placed for about 50 "
                "minutes either side of its transit, and its longitude drifts (a 1° error shifts the time by 1.7 min)."
                + ("" if loc else " No location given: times are UTC and nothing is checked against your sky."),
    }
    return {k: v for k, v in out.items() if v is not None}

