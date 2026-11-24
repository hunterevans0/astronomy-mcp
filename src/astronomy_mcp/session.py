"""Observing sessions: put a list of targets in order for one night, with a start time for each,
so every target is observed while it is high enough (above the terrain too) and the sky is dark,
then export the plan as a SkySafari observing list or CSV.

Scheduling is earliest-deadline-first on a 5-minute grid: of the targets that can start soon,
the one whose observable window closes first goes next, which observes the western sky before
it sets. A few lookahead settings are tried and the plan that fits the most targets wins.
Targets that don't fit get a reason.
"""

from __future__ import annotations

import csv
import io
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

import astronomy as ae

from astronomy_mcp import planner, sky
from astronomy_mcp.conditions import sqm_with_moon
from astronomy_mcp.horizon import Horizon
from astronomy_mcp.location import Location, data_dir
from astronomy_mcp.sky import Night, Target, fmt

STEP_MIN = 5
LOOKAHEADS_MIN = (0, 30, 60, 120)  # how far ahead to look for a target with an earlier deadline


@dataclass
class Request:
    target: Target
    label: str  # name shown in the plan
    minutes: int
    catalog_ids: list[str] = field(default_factory=list)  # NGC/IC/Messier names, for SkySafari
    kind: str = "deep_sky"  # deep_sky | star | solar_system


@dataclass
class _Prepared:
    req: Request
    alts: list[float]
    azs: list[float]
    dark: list[bool]
    allowed: list[bool]
    steps: int
    reason: str | None = None
    detection: Any = None
    best_i: int | None = None


def clock_time(value: str | None, n: Night, loc: Location) -> datetime | None:
    """'21:30' or '01:00' on this night (times before noon are after midnight), or a full ISO time."""
    if not value:
        return None
    value = value.strip()
    if re.fullmatch(r"\d{1,2}:\d{2}", value):
        hour, minute = map(int, value.split(":"))
        day = n.date + timedelta(days=1) if hour < 12 else n.date
        return datetime.combine(day, time(hour, minute), tzinfo=loc.tz)
    return sky.parse_time(value, loc)


def night_grid(n: Night) -> list[datetime]:
    """5-minute samples from civil dusk to civil dawn (the planets' window), else the darkest window."""
    start = n.civil[0] or n.window[0]
    end = n.civil[1] or n.window[1]
    out, t = [], start
    while t <= end:
        out.append(t)
        t += timedelta(minutes=STEP_MIN)
    return out


def _tracks(requests: list[Request], times: list[datetime], loc: Location) -> list[tuple[list[float], list[float]]]:
    fixed = [r for r in requests if r.target.is_fixed]
    fast = iter(sky.fast_tracks([(r.target.ra_deg, r.target.dec_deg) for r in fixed], times, loc) if fixed else [])
    out = []
    for r in requests:
        if r.target.is_fixed:
            track = next(fast)
            out.append(([a for a, _ in track], [z for _, z in track]))
        else:
            rows = [sky.horizontal(r.target, t, loc) for t in times]
            out.append(([h["altitude_deg"] for h in rows], [h["azimuth_deg"] for h in rows]))
    return out


def _runs(flags: list[bool]) -> list[tuple[int, int]]:
    """(first, last) index of each run of True."""
    runs, start = [], None
    for i, ok in enumerate([*flags, False]):
        if ok and start is None:
            start = i
        elif not ok and start is not None:
            runs.append((start, i - 1))
            start = None
    return runs


def _feasible_starts(p: _Prepared) -> list[tuple[int, int]]:
    """(earliest, latest) start index of each stretch where the whole block fits."""
    return [(a, b - p.steps) for a, b in _runs(p.allowed) if b - a >= p.steps]


def _schedule(prepared: list[_Prepared], first: int, gap_steps: int, lookahead: int) -> list[tuple[_Prepared, int]]:
    pending = [p for p in prepared if p.reason is None]
    placed: list[tuple[_Prepared, int]] = []
    cur = first
    while pending:
        options = []
        for p in pending:
            for lo, hi in _feasible_starts(p):
                if hi >= cur:
                    options.append((max(lo, cur), hi, p))
                    break
        if not options:
            break
        soonest = min(s for s, _, _ in options)
        start, _, choice = min((o for o in options if o[0] <= soonest + lookahead), key=lambda o: (o[1], o[0]))
        placed.append((choice, start))
        pending.remove(choice)
        cur = start + choice.steps + gap_steps
    return placed


def plan(
    requests: list[Request],
    loc: Location,
    n: Night,
    sqm: float,
    equipment: str,
    aperture_mm: float | None,
    min_altitude: float,
    horizon: Horizon | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    gap_minutes: int = 5,
) -> dict[str, Any]:
    if n.darkest == "none":
        raise ValueError("The Sun doesn't set on this date at this latitude, so there is no night to plan.")
    times = night_grid(n)
    if start and end and end <= start:
        raise ValueError("The session's end time is before its start.")
    planet_start, planet_end = planner._planet_window(n)
    moon_alts = [sky.horizontal(planner.MOON, t, loc)["altitude_deg"] for t in times]
    moon_mag = ae.Illumination(ae.Body.Moon, sky.to_time(times[len(times) // 2])).mag

    prepared: list[_Prepared] = []
    for r, (alts, azs) in zip(requests, _tracks(requests, times, loc)):
        lo, hi = (planet_start, planet_end) if r.kind == "solar_system" else n.window
        dark = [lo <= t <= hi for t in times]
        in_session = [(start is None or t >= start) and (end is None or t <= end) for t in times]
        floor = [planner._floor(min_altitude, horizon, az) for az in azs]
        allowed = [d and s and a >= f for d, s, a, f in zip(dark, in_session, alts, floor)]
        p = _Prepared(r, alts, azs, dark, allowed, max(1, math.ceil(r.minutes / STEP_MIN)))
        p.reason = _blocker(p, times, min_altitude, floor, in_session, loc)
        if p.reason is None:
            p.best_i = max((i for i, ok in enumerate(allowed) if ok), key=lambda i: alts[i])
            p.detection = _detection(p, times, sqm, equipment, aperture_mm, moon_alts, moon_mag, loc)
            if p.detection is not None and not p.detection.visible:
                p.reason = (f"Too faint for {equipment.replace('_', ' ')} under this sky: it misses the detection "
                            f"threshold by {-p.detection.margin_mag:.1f} mag even at its highest.")
        prepared.append(p)

    first = next((i for i, t in enumerate(times) if start is None or t >= start), len(times))
    gap_steps = math.ceil(gap_minutes / STEP_MIN)
    best: list[tuple[_Prepared, int]] = []
    for minutes in LOOKAHEADS_MIN:
        trial = _schedule(prepared, first, gap_steps, minutes // STEP_MIN)
        if len(trial) > len(best):
            best = trial

    placed = {id(p): s for p, s in best}
    schedule = [_entry(i + 1, p, s, times, moon_alts, loc, equipment, n) for i, (p, s) in enumerate(best)]
    unscheduled = []
    for p in prepared:
        if id(p) in placed:
            continue
        reason = p.reason or _conflict(p, best, times, loc)
        unscheduled.append({"target": p.req.label, "reason": reason})

    out: dict[str, Any] = {
        "date": n.date.isoformat(),
        "dark_window": {"start": fmt(n.window[0], loc), "end": fmt(n.window[1], loc), "darkest_sky": n.darkest},
        "session": {
            "start": fmt(times[best[0][1]], loc) if best else None,
            "end": fmt(times[best[-1][1]] + timedelta(minutes=best[-1][0].req.minutes), loc) if best else None,
            "requested_start": fmt(start, loc) if start else None,
            "requested_end": fmt(end, loc) if end else None,
        },
        "scheduled_count": len(schedule),
        "schedule": schedule,
        "unscheduled": unscheduled or None,
        "moon": sky.moon_phase(n.window[0] + (n.window[1] - n.window[0]) / 2),
        "rules": (f"Each target starts and ends above {min_altitude:g}°"
                  + (" and above the terrain horizon" if horizon else "")
                  + ", deep-sky objects and stars inside the darkest window (astronomical darkness where it exists), "
                    f"planets and the Moon from civil dusk to civil dawn. {gap_minutes} min between targets for "
                    "slewing and finding. Targets whose window closes first go first."),
    }
    out["session"] = {k: v for k, v in out["session"].items() if v is not None}
    return {k: v for k, v in out.items() if v is not None}


def _blocker(p: _Prepared, times: list[datetime], min_altitude: float, floor: list[float],
             in_session: list[bool], loc: Location) -> str | None:
    """Why a target can't go anywhere in the night, or None if it has a slot somewhere."""
    if p.req.target.name == "Sun":
        return "The Sun is not a night-time target."
    high = [i for i, (d, a) in enumerate(zip(p.dark, p.alts)) if d and a >= min_altitude]
    if not high:
        dark_alts = [a for d, a in zip(p.dark, p.alts) if d] or p.alts
        return f"Never above {min_altitude:g}° while the sky is dark (it peaks at {max(dark_alts):.0f}°)."
    clear = [i for i in high if p.alts[i] >= floor[i]]
    if not clear:
        return "Terrain blocks it: whenever it is high enough in the dark, it is behind the local horizon."
    if not any(in_session[i] for i in clear):
        return (f"Only observable from {fmt(times[clear[0]], loc)} to {fmt(times[clear[-1]], loc)}, "
                "outside the session hours.")
    if not _feasible_starts(p):
        longest = max(b - a for a, b in _runs(p.allowed)) * STEP_MIN if any(p.allowed) else 0
        return (f"Only well placed for {longest} min in a row during the session, less than the "
                f"{p.req.minutes} min planned for it; plan a shorter look.")
    return None


def _detection(p: _Prepared, times: list[datetime], sqm: float, equipment: str, aperture_mm: float | None,
               moon_alts: list[float], moon_mag: float, loc: Location) -> Any:
    t = p.req.target
    if t.name in ("Moon", "Sun"):
        return None
    when = times[p.best_i]
    mag = planner.target_magnitude(t, when)
    if mag is None:
        return None
    sep = 90.0
    if moon_alts[p.best_i] > 0:
        sep = sky.separation_deg(*sky.j2000_position(t, when), *sky.j2000_position(planner.MOON, when))
    sky_here = sqm_with_moon(sqm, moon_mag, moon_alts[p.best_i], sep)
    return planner._detect(t.info if t.is_fixed else {}, mag, sky_here, equipment, aperture_mm, p.alts[p.best_i])


def _entry(order: int, p: _Prepared, s: int, times: list[datetime], moon_alts: list[float], loc: Location,
           equipment: str, n: Night) -> dict[str, Any]:
    e = s + p.steps
    begin = times[s]
    finish = begin + timedelta(minutes=p.req.minutes)
    mid = s + p.steps // 2
    window_end = next(b for a, b in _runs(p.allowed) if a <= s <= b)
    moon_sep = None
    if moon_alts[mid] > 0 and p.req.target.name != "Moon":
        moon_sep = sky.separation_deg(*sky.j2000_position(p.req.target, times[mid]),
                                      *sky.j2000_position(planner.MOON, times[mid]))
    det = p.detection
    row = {
        "order": order,
        "target": p.req.label,
        "start": fmt(begin, loc),
        "end": fmt(finish, loc),
        "minutes": p.req.minutes,
        "altitude_deg": {"start": round(p.alts[s]), "end": round(p.alts[min(e, len(times) - 1)])},
        "direction": f"{sky.compass(p.azs[mid])} (az {p.azs[mid]:.0f}°)",
        "observable_until": fmt(times[window_end], loc),
        "difficulty": planner.difficulty(det.margin_mag) if det else None,
        "suggested_magnification": f"about {det.magnification:.0f}x" if det and equipment == "telescope" else None,
        "moon_separation_deg": round(moon_sep) if moon_sep is not None else None,
        "note": ("in twilight" if p.req.kind == "solar_system" and begin < n.window[0] else None),
    }
    return {k: v for k, v in row.items() if v is not None}


def _conflict(p: _Prepared, best: list[tuple[_Prepared, int]], times: list[datetime], loc: Location) -> str:
    lo, hi = _feasible_starts(p)[0][0], _feasible_starts(p)[-1][1] + p.steps
    busy = [q.req.label for q, s in best if s <= hi and s + q.steps >= lo]
    return (f"No free slot: it is well placed from {fmt(times[lo], loc)} to {fmt(times[hi], loc)}, but that time "
            f"went to {', '.join(busy) or 'other targets'}. Shorten some looks or drop a target to fit it.")


# ---------------------------------------------------------------- export

def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:60] or "session"


def skysafari(entries: list[tuple[Request, dict[str, Any]]]) -> str:
    """A SkySafari observing list (.skylist). SkySafari matches objects by catalog number, NGC/IC
    first, and drops entries it can't find in its own database."""
    object_types = {"solar_system": 1, "star": 2, "deep_sky": 4}
    lines = ["SkySafariObservingListVersion=3.0"]
    for req, _ in entries:
        lines += ["SkyObject=BeginObject", f"\tObjectID={object_types[req.kind]},-1,-1"]
        names = list(dict.fromkeys([*req.catalog_ids, req.label]))
        lines += [f"\tCatalogNumber={name}" for name in names]
        lines.append("EndObject=SkyObject")
    return "\n".join(lines) + "\n"


def csv_text(entries: list[tuple[Request, dict[str, Any]]], when: datetime) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["order", "name", "ra_deg", "dec_deg", "start", "end", "minutes"])
    for req, row in entries:
        ra, dec = sky.j2000_position(req.target, when)
        writer.writerow([row.get("order", ""), req.label, f"{ra:.5f}", f"{dec:.5f}", row.get("start", ""),
                         row.get("end", ""), req.minutes])
    return buf.getvalue()


def save_export(text: str, stem: str, extension: str) -> Path:
    folder = data_dir() / "lists"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{slug(stem)}.{extension}"
    path.write_text(text, encoding="utf-8")
    return path
