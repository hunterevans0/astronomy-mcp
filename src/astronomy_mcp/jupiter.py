"""Jupiter's Galilean moons and Great Red Spot (offline).

Moon positions come from Astronomy Engine's Jupiter-moon theory, backdated for light
travel time. Each moon is placed in two frames centred on Jupiter: one looking from
Earth (is it in front of or behind the disk?) and one looking from the Sun (is its
shadow on the disk, or is it inside Jupiter's shadow?). Moons are treated as points
and the shadow as a cylinder, so event times are good to a few minutes.

The Great Red Spot drifts in System II longitude. GRS_LONGITUDE is the value Sky &
Telescope's predictions assume (from JUPOS measurements). Tools also fetch Project Pluto's
table of JUPOS measurements weekly and use it once it has a newer measurement than the
built-in one, so the constant only matters until that table is updated; tools take an
override too.

Mutual events (one moon occulting or eclipsing another) treat the moons as disks of their
real size and the Sun as a disk for the eclipse penumbra; they agree with IMCCE predictions
to about two minutes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import astronomy as ae

from astronomy_mcp import sky
from astronomy_mcp.http import UpstreamError, get_text_file
from astronomy_mcp.location import Location, data_dir
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
GRS_URL = "https://www.projectpluto.com/grs_lon.txt"

# In front of and behind the disk as seen from Earth, then the same two as seen from the Sun.
KINDS = ("transit", "occultation", "shadow transit", "eclipse")
SCAN_STEP = timedelta(minutes=2)
MIN_ALTITUDE_DEG = 10.0  # Jupiter this high, and the Sun below civil twilight, to call an event observable
MAX_SUN_ALTITUDE_DEG = -6.0


@dataclass(frozen=True)
class GrsModel:
    """The Red Spot's System II longitude as a measured value plus a steady drift."""

    epoch: date
    longitude: float
    drift_deg_per_day: float
    source: str

    def at(self, when: datetime) -> float:
        return (self.longitude + self.drift_deg_per_day * (when.date() - self.epoch).days) % 360

    def describe(self) -> dict[str, Any]:
        return {"measured": self.epoch.isoformat(), "longitude_then_deg": round(self.longitude % 360, 1),
                "drift_deg_per_month": round(self.drift_deg_per_day * 30.44, 2), "source": self.source}


BUILT_IN_GRS = GrsModel(GRS_EPOCH, GRS_LONGITUDE, GRS_DRIFT_DEG_PER_DAY, "Sky & Telescope from JUPOS (built in)")


def grs_longitude(when: datetime, model: GrsModel = BUILT_IN_GRS) -> float:
    return model.at(when)


def parse_grs_table(text: str, today: date) -> GrsModel | None:
    """Latest measurement in Project Pluto's grs_lon.txt, with the drift over the 2 years before it.

    Lines are 'YYYY MM DD lon comment' with longitudes unwrapped (439 means 79°). Rows
    in the future are the file's own long-range extrapolation and are skipped.
    """
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4 or not all(p.isdigit() for p in parts[:4]):
            continue
        try:
            day = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            continue
        if day <= today:
            rows.append((day, float(parts[3])))
    if len(rows) < 2:
        return None
    rows.sort()
    last_day, last_lon = rows[-1]
    window = [(d, lon) for d, lon in rows if (last_day - d).days <= 730]
    if len(window) < 2:
        window = rows[-2:]
    # Least-squares slope over the window.
    xs = [(d - last_day).days for d, _ in window]
    ys = [lon for _, lon in window]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return GrsModel(last_day, last_lon, slope, "JUPOS measurements via Project Pluto grs_lon.txt")


async def current_grs_model() -> GrsModel:
    """The newer of the built-in value and Project Pluto's table (fetched weekly, cached on disk)."""
    try:
        text = await get_text_file(GRS_URL, data_dir() / "jupiter" / "grs_lon.txt", source="Project Pluto", max_age=7 * 86400)
    except UpstreamError:
        return BUILT_IN_GRS
    fetched = parse_grs_table(text, date.today())
    return fetched if fetched and fetched.epoch > BUILT_IN_GRS.epoch else BUILT_IN_GRS


@dataclass
class MoonState:
    name: str
    west: float  # offsets from Jupiter's centre in equatorial radii, as seen from Earth
    north: float
    behind: float  # positive when farther than Jupiter
    flags: tuple[bool, bool, bool, bool]  # in the order of KINDS
    sun_west: float = 0.0  # the same offsets as seen from the Sun
    sun_north: float = 0.0
    sun_behind: float = 0.0

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
        moons.append(MoonState(name, west, north, behind, flags, sun_west, sun_north, sun_behind))
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


def moons_now(when: datetime, loc: Location | None, grs: float | None = None,
              model: GrsModel = BUILT_IN_GRS) -> dict[str, Any]:
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
    spot = grs if grs is not None else model.at(when)
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
            "longitude_basis": "given by user" if grs is not None else model.describe(),
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


def find_events(start: datetime, end: datetime, grs: float | None = None,
                model: GrsModel = BUILT_IN_GRS) -> tuple[list[dict[str, Any]], list[str]]:
    """(events between start and end in time order, phenomena already under way at start)."""
    def spot_offset(t: datetime, snap: Snapshot) -> float:
        return sky.wrap180(snap.cm_system_ii - (grs if grs is not None else model.at(t)))

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
    start: datetime, hours: float, loc: Location | None, grs: float | None = None, observable_only: bool = False,
    model: GrsModel = BUILT_IN_GRS, mutual: bool = True,
) -> dict[str, Any]:
    shown = loc or Location(0.0, 0.0)
    end = start + timedelta(hours=hours)
    found, under_way = find_events(start, end, grs, model)
    if mutual:
        found = sorted(found + find_mutual_events(start, end), key=lambda e: e["time"])
    rows = []
    for event in found:
        row = {**event, **{k: fmt(event[k], shown) for k in ("time", "begins", "ends") if k in event}}
        if loc:
            row |= _observing(event["time"], loc)
            if observable_only and (not row["observable_here"] or "note" in row):
                continue
        rows.append(row)
    spot = grs if grs is not None else model.at(start)
    out = {
        "from": fmt(start, shown),
        "to": fmt(start + timedelta(hours=hours), shown),
        "under_way_at_start": under_way or None,
        "count": len(rows),
        "events": rows,
        "great_red_spot_longitude_assumed_deg": round(spot, 1),
        "great_red_spot_longitude_basis": "given by user" if grs is not None else model.describe(),
        "note": "Times are when the moon's centre crosses Jupiter's limb or shadow edge, good to a few minutes; "
                "the moons take several minutes to fade or cross. The Red Spot is well placed for about 50 "
                "minutes either side of its transit, and its longitude drifts (a 1° error shifts the time by 1.7 min)."
                + (" Mutual events (one moon occulting or eclipsing another) give the time of greatest overlap; they "
                   "agree with IMCCE predictions to about 2 minutes and happen only in seasons around Jupiter's "
                   "equinoxes (next: December 2026)." if mutual else "")
                + ("" if loc else " No location given: times are UTC and nothing is checked against your sky."),
    }
    return {k: v for k, v in out.items() if v is not None}



# ---------------------------------------------------------------- mutual events

MOON_RADIUS_KM = {"Io": 1821.6, "Europa": 1560.8, "Ganymede": 2631.2, "Callisto": 2410.3}
SUN_RADIUS_KM = 695_700.0
JUPITER_RADIUS_KM = ae.JUPITER_EQUATORIAL_RADIUS_KM
MUTUAL_STEP = timedelta(minutes=2)


def circle_overlap(r1: float, r2: float, d: float) -> float:
    """Area shared by two circles of radii r1, r2 whose centres are d apart."""
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2
    a1 = r1 * r1 * math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1))
    a2 = r2 * r2 * math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
    return a1 + a2 - 0.5 * math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))


@dataclass
class MutualGeometry:
    separation_km: float  # centre to centre, in the plane of the hidden moon
    reach_km: float  # radius of the occulting disk, or of the penumbra
    umbra_km: float  # radius of the occulting disk, or of the umbra (negative: antumbra)
    target_radius_km: float

    @property
    def ratio(self) -> float:
        """Below 1 while the two touch."""
        return self.separation_km / (self.reach_km + self.target_radius_km)


def mutual_geometry(a: MoonState, b: MoonState, kind: str, sun_distance_km: float) -> MutualGeometry | None:
    """How moon `a` covers moon `b`: 'occultation' as seen from Earth, 'eclipse' as seen from the Sun.
    None when `a` is the farther of the two."""
    rb = MOON_RADIUS_KM[b.name]
    ra = MOON_RADIUS_KM[a.name]
    if kind == "occultation":
        if a.behind >= b.behind:
            return None
        sep = math.hypot(a.west - b.west, a.north - b.north) * JUPITER_RADIUS_KM
        return MutualGeometry(sep, ra, ra, rb)
    if a.sun_behind >= b.sun_behind:
        return None
    sep = math.hypot(a.sun_west - b.sun_west, a.sun_north - b.sun_north) * JUPITER_RADIUS_KM
    spread = (b.sun_behind - a.sun_behind) * JUPITER_RADIUS_KM * SUN_RADIUS_KM / sun_distance_km
    return MutualGeometry(sep, ra + spread, ra - spread, rb)


def _sun_distance_km(when: datetime) -> float:
    return ae.HelioVector(ae.Body.Jupiter, sky.to_time(when)).Length() * ae.KM_PER_AU


def _pair_geometry(when: datetime, i: int, j: int, kind: str) -> MutualGeometry | None:
    snap = snapshot(when)
    return mutual_geometry(snap.moons[i], snap.moons[j], kind, _sun_distance_km(when))


def _ratio(when: datetime, i: int, j: int, kind: str) -> float:
    g = _pair_geometry(when, i, j, kind)
    return g.ratio if g else math.inf


def _golden_min(f: Any, lo: datetime, hi: datetime) -> datetime:
    golden = (math.sqrt(5) - 1) / 2
    a, b = hi - (hi - lo) * golden, lo + (hi - lo) * golden
    fa, fb = f(a), f(b)
    while hi - lo > timedelta(seconds=2):
        if fa < fb:
            hi, b, fb = b, a, fa
            a = hi - (hi - lo) * golden
            fa = f(a)
        else:
            lo, a, fa = a, b, fb
            b = lo + (hi - lo) * golden
            fb = f(b)
    return lo + (hi - lo) / 2


def describe_mutual(kind: str, a: str, b: str, g: MutualGeometry) -> dict[str, Any]:
    area = math.pi * g.target_radius_km**2
    if kind == "occultation":
        covered = circle_overlap(g.reach_km, g.target_radius_km, g.separation_km) / area
        sort = "total" if covered > 0.999 else "annular" if g.separation_km + g.reach_km <= g.target_radius_km else "partial"
        return {"type": sort, "fraction_of_disk_covered": round(covered, 2)}
    umbra = circle_overlap(abs(g.umbra_km), g.target_radius_km, g.separation_km) / area if g.umbra_km > 0 else 0.0
    penumbra = circle_overlap(g.reach_km, g.target_radius_km, g.separation_km) / area
    if g.umbra_km > 0 and umbra > 0.999:
        sort = "total"
    elif umbra > 0:
        sort = "partial"
    elif g.umbra_km <= 0 and g.separation_km + abs(g.umbra_km) < g.target_radius_km:
        sort = "annular"
    else:
        sort = "penumbral"
    # Rough light loss: full in the umbra, about half across the penumbra.
    return {"type": sort, "estimated_light_loss": round(umbra + 0.5 * (penumbra - umbra), 2)}


def find_mutual_events(start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Moons occulting or eclipsing one another between start and end.

    These happen only in seasons around Jupiter's equinoxes (every ~6 years, e.g. 2026-27)
    when the moons' orbits are edge-on to the Sun and Earth.
    """
    pairs = [(i, j, kind) for kind in ("occultation", "eclipse") for i in range(4) for j in range(4) if i != j]
    times = []
    t = start - MUTUAL_STEP
    while t <= end + MUTUAL_STEP:
        times.append(t)
        t += MUTUAL_STEP
    sun_km = _sun_distance_km(start + (end - start) / 2)
    snaps = [snapshot(t) for t in times]
    found = []
    for i, j, kind in pairs:
        ratios = []
        for snap in snaps:
            g = mutual_geometry(snap.moons[i], snap.moons[j], kind, sun_km)
            ratios.append(g.ratio if g else math.inf)
        for k in range(1, len(times) - 1):
            if not (ratios[k] <= ratios[k - 1] and ratios[k] < ratios[k + 1]) or ratios[k] > 3:
                continue
            peak = _golden_min(lambda x: _ratio(x, i, j, kind), times[k - 1], times[k + 1])
            g = _pair_geometry(peak, i, j, kind)
            if g is None or g.ratio >= 1 or not start <= peak <= end:
                continue
            begin = _bisect(peak - timedelta(hours=1), peak, lambda x: _ratio(x, i, j, kind) < 1)
            finish = _bisect(peak, peak + timedelta(hours=1), lambda x: _ratio(x, i, j, kind) >= 1)
            depth = describe_mutual(kind, MOONS[i], MOONS[j], g)
            if depth.get("fraction_of_disk_covered", depth.get("estimated_light_loss", 0)) < 0.03:
                continue  # a graze with no visible dimming
            snap = snapshot(peak)
            hidden = [m.name for m in (snap.moons[i], snap.moons[j]) if m.hidden]
            event: dict[str, Any] = {
                "time": peak,
                "event": f"{MOONS[i]} {'occults' if kind == 'occultation' else 'eclipses'} {MOONS[j]}",
                "mutual": True,
                "begins": begin,
                "ends": finish,
                "duration_min": round((finish - begin).total_seconds() / 60, 1),
                **depth,
            }
            if hidden:
                event["note"] = "not observable: " + " and ".join(hidden) + " hidden by Jupiter or its shadow"
            found.append(event)
    found.sort(key=lambda e: e["time"])
    return found
