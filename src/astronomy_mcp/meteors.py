"""Meteor showers: the IMO Working List of Visual Meteor Showers, peak times from solar
longitude, and how good each peak night is from a given site.

The table is Table 5 of the International Meteor Organization's 2026 Meteor Shower Calendar
(working list as of June 2025). The calendar is published once a year as a PDF; the values
change little from year to year, and peak times for any year come from the solar longitude of
maximum, so the table is built in rather than downloaded.

Rates follow the standard visual formula: HR = ZHR x sin(radiant altitude) / r^(6.5 - LM),
where LM is the naked-eye limiting magnitude from the site's sky brightness plus moonlight.
Away from the maximum, ZHR falls off as 10^(-B |dλ|), with B set by the peak's width.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import astronomy as ae

from astronomy_mcp import planner, sky
from astronomy_mcp.conditions import nelm_from_sqm, sqm_with_moon
from astronomy_mcp.location import Location
from astronomy_mcp.sky import Night, fmt

SOURCE = "IMO 2026 Meteor Shower Calendar, Table 5 (Working List of Visual Meteor Showers, June 2025)"
CALENDAR_URL = "https://www.imo.net/resources/calendar/"
PRECESSION_DEG_PER_CENTURY = 1.3970  # general precession in longitude: λ(J2000) to λ(of date)
SUN_DEG_PER_DAY = 360 / 365.2422
DEFAULT_FWHM_HOURS = 72.0  # most showers have broad maxima lasting days
STEP_MIN = 10
REFERENCE_LM = 6.5


@dataclass(frozen=True)
class Shower:
    code: str
    iau: int
    name: str
    active: tuple[tuple[int, int], tuple[int, int]]  # (month, day) start and end
    sol_lon: float  # λ⊙ of maximum, J2000
    ra: float
    dec: float
    velocity: int  # km/s
    r: float  # population index
    zhr: int | None  # None = variable
    fwhm_hours: float = DEFAULT_FWHM_HOURS  # width of the peak at half the maximum ZHR
    daytime: bool = False
    note: str | None = None


SHOWERS: tuple[Shower, ...] = (
    Shower("QUA", 10, "Quadrantids", ((12, 28), (1, 12)), 283.15, 230, 49, 41, 2.1, 80, fwhm_hours=8,
           note="Sharp peak: rates near the listed ZHR last only a few hours around the maximum."),
    Shower("GUM", 404, "gamma-Ursae Minorids", ((1, 10), (1, 22)), 298, 228, 67, 31, 3.0, 3),
    Shower("ACE", 102, "alpha-Centaurids", ((1, 31), (2, 20)), 319.4, 211, -58, 58, 2.0, 6,
           note="ZHR variable, usually about 6; short outbursts of 20-30 have been seen."),
    Shower("LYR", 6, "April Lyrids", ((4, 14), (4, 30)), 32.32, 271, 34, 49, 2.1, 18, fwhm_hours=32,
           note="Peak timing varies by several hours; occasional short bursts up to ZHR 90."),
    Shower("PPU", 137, "pi-Puppids", ((4, 15), (4, 28)), 33.5, 110, -45, 18, 2.0, None),
    Shower("ETA", 31, "eta-Aquariids", ((4, 19), (5, 28)), 45.5, 338, -1, 66, 2.4, 50,
           note="Best from the southern hemisphere and the tropics; the radiant rises only before dawn."),
    Shower("ELY", 145, "eta-Lyrids", ((5, 3), (5, 14)), 50.0, 291, 43, 43, 3.0, 3),
    Shower("ARI", 171, "Daytime Arietids", ((5, 14), (6, 24)), 76.7, 43, 24, 38, 2.8, 30, daytime=True),
    Shower("JBO", 170, "June Bootids", ((6, 22), (7, 2)), 90.3, 221, 48, 18, 2.2, None),
    Shower("JPE", 175, "July Pegasids", ((7, 1), (7, 20)), 108.0, 347, 11, 63, 3.0, 3),
    Shower("GDR", 184, "July gamma-Draconids", ((7, 25), (7, 31)), 125.13, 280, 51, 27, 3.0, 5),
    Shower("SDA", 5, "Southern delta-Aquariids", ((7, 12), (8, 23)), 128, 340, -16, 41, 2.5, 25),
    Shower("CAP", 1, "alpha-Capricornids", ((7, 3), (8, 15)), 128, 307, -10, 23, 2.5, 5,
           note="Low rates, but slow and often bright meteors and fireballs."),
    Shower("ERI", 191, "eta-Eridanids", ((7, 31), (8, 19)), 135, 41, -11, 64, 3.0, 3),
    Shower("PER", 7, "Perseids", ((7, 17), (8, 24)), 140.0, 48, 58, 59, 2.2, 100, fwhm_hours=48),
    Shower("KCG", 12, "kappa-Cygnids", ((8, 3), (8, 28)), 144, 286, 59, 23, 3.0, 3),
    Shower("AUR", 206, "Aurigids", ((8, 28), (9, 5)), 158.6, 91, 39, 66, 2.5, 6),
    Shower("SPE", 208, "September epsilon-Perseids", ((9, 5), (9, 21)), 166.7, 48, 40, 64, 2.5, 8),
    Shower("SLY", 81, "September Lyncids", ((9, 10), (10, 8)), 170, 113, 56, 60, 3.0, 3),
    Shower("DSX", 221, "Daytime Sextantids", ((9, 20), (10, 6)), 188, 156, -2, 32, 2.5, 5, daytime=True),
    Shower("OCT", 281, "October Camelopardalids", ((10, 5), (10, 6)), 192.58, 164, 79, 47, 2.5, 5, fwhm_hours=6),
    Shower("DRA", 9, "Draconids", ((10, 6), (10, 10)), 195.4, 262, 54, 20, 2.6, 5, fwhm_hours=12,
           note="Usually weak, but has produced outbursts of hundreds an hour (2011, 2018). Very slow meteors."),
    Shower("EGE", 23, "epsilon-Geminids", ((10, 14), (10, 27)), 205, 102, 27, 70, 3.0, 3),
    Shower("ORI", 8, "Orionids", ((10, 2), (11, 7)), 208, 95, 16, 66, 2.5, 20,
           note="Broad maximum; ZHRs of 40-70 were seen in 2006-2009."),
    Shower("LMI", 22, "Leonis Minorids", ((10, 19), (10, 27)), 211, 162, 37, 62, 3.0, 2),
    Shower("STA", 2, "Southern Taurids", ((9, 20), (11, 20)), 223, 52, 15, 27, 2.3, 7,
           note="Low rates of slow meteors, with a share of fireballs."),
    Shower("NTA", 17, "Northern Taurids", ((10, 20), (12, 10)), 230, 58, 22, 29, 2.3, 5,
           note="Low rates of slow meteors, with a share of fireballs."),
    Shower("LEO", 13, "Leonids", ((11, 6), (11, 30)), 235.27, 152, 22, 71, 2.5, 15, fwhm_hours=24,
           note="Famous for storms around 1999-2002; no storm is expected for years."),
    Shower("AMO", 246, "alpha-Monocerotids", ((11, 15), (11, 25)), 239.32, 117, 1, 65, 2.4, None, fwhm_hours=2),
    Shower("NOO", 250, "November Orionids", ((11, 13), (12, 6)), 246, 91, 16, 44, 3.0, 3),
    Shower("PHO", 254, "Phoenicids", ((12, 1), (12, 5)), 249.5, 8, -27, 15, 2.8, None),
    Shower("PUP", 301, "Puppid-Velids", ((12, 1), (12, 15)), 255, 123, -45, 44, 2.9, 10,
           note="A complex of weak radiants; the date is a reference for the radiant, not a true maximum."),
    Shower("MON", 19, "Monocerotids", ((12, 1), (12, 19)), 257, 100, 8, 41, 3.0, 3),
    Shower("HYD", 16, "sigma-Hydrids", ((12, 3), (12, 20)), 257, 125, 2, 58, 3.0, 7),
    Shower("GEM", 4, "Geminids", ((12, 4), (12, 20)), 262.2, 112, 33, 35, 2.6, 150, fwhm_hours=20,
           note="The year's richest shower; the radiant is up from mid-evening, so rates are good before midnight too."),
    Shower("COM", 20, "Comae Berenicids", ((12, 4), (1, 30)), 271, 164, 29, 65, 3.0, 3),
    Shower("URS", 15, "Ursids", ((12, 17), (12, 26)), 270.7, 217, 76, 33, 2.8, 10, fwhm_hours=12),
)
MAJOR_MIN_ZHR = 5  # default listing: night-time showers at least this strong


def find(name: str) -> Shower:
    key = name.strip().lower().replace("-", " ").replace("ε", "epsilon").replace("η", "eta")
    for s in SHOWERS:
        if key in (s.code.lower(), s.name.lower().replace("-", " ")) or key == str(s.iau):
            return s
    hits = [s for s in SHOWERS if key in s.name.lower().replace("-", " ")]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        known = ", ".join(s.name for s in SHOWERS if s.zhr is None or s.zhr >= 10)
        raise ValueError(f"No meteor shower called '{name}'. Major ones: {known}. IMO codes (PER, GEM...) work too.")
    raise ValueError(f"'{name}' matches several showers: {', '.join(s.name for s in hits)}.")


def peak_time(shower: Shower, after: datetime) -> datetime:
    """First time after `after` when the Sun reaches the shower's solar longitude of maximum."""
    t = sky.to_time(after)
    of_date = (shower.sol_lon + PRECESSION_DEG_PER_CENTURY * t.ut / 36525) % 360
    found = ae.SearchSunLongitude(of_date, t, 370)
    return sky.to_datetime(found)


def active_label(shower: Shower) -> str:
    (m1, d1), (m2, d2) = shower.active
    return f"{date(2001, m1, d1):%b} {d1} - {date(2001, m2, d2):%b} {d2}"


def is_active(shower: Shower, day: date) -> bool:
    (m1, d1), (m2, d2) = shower.active
    start, end, today = (m1, d1), (m2, d2), (day.month, day.day)
    return start <= today <= end if start <= end else today >= start or today <= end


def zhr_at(shower: Shower, when: datetime, peak: datetime) -> float | None:
    if shower.zhr is None:
        return None
    width_deg = shower.fwhm_hours / 24 * SUN_DEG_PER_DAY
    b = math.log10(2) / (width_deg / 2)
    offset_deg = abs((when - peak).total_seconds()) / 86400 * SUN_DEG_PER_DAY
    return shower.zhr * 10 ** (-b * offset_deg)


def hourly_rate(zhr: float, radiant_alt_deg: float, limiting_mag: float, r: float) -> float:
    """Meteors an observer sees per hour (clear sky, unobstructed view)."""
    if radiant_alt_deg <= 0:
        return 0.0
    return zhr * math.sin(math.radians(radiant_alt_deg)) / r ** (REFERENCE_LM - limiting_mag)


def rating(best_rate: float | None) -> str:
    if best_rate is None:
        return "unpredictable (variable shower)"
    if best_rate >= 40:
        return "excellent"
    if best_rate >= 15:
        return "good"
    if best_rate >= 5:
        return "fair"
    return "poor"


def peak_night(loc: Location, peak: datetime) -> Night:
    """The night whose dark hours contain the peak, or come closest to it."""
    local_day = peak.astimezone(loc.tz).date()
    nights = [sky.night(loc, local_day + timedelta(days=k)) for k in (-1, 0)]

    def distance(n: Night) -> float:
        if n.window[0] <= peak <= n.window[1]:
            return 0.0
        return min(abs((peak - edge).total_seconds()) for edge in n.window)
    return min(nights, key=distance)


def rate_night(shower: Shower, peak: datetime, loc: Location, n: Night, sqm: float) -> dict[str, Any]:
    """Hour-by-hour rates over one night's dark window, summarised."""
    row: dict[str, Any] = {"night": n.date.isoformat()}
    if n.darkest == "none":
        return {**row, "rating": "poor", "reason": "no darkness (midnight sun)", "expected_meteors_per_hour": 0}
    times, t = [], n.window[0]
    while t <= n.window[1]:
        times.append(t)
        t += timedelta(minutes=STEP_MIN)
    radiant = [alt for alt, _ in sky.fast_tracks([(shower.ra, shower.dec)], times, loc)[0]]
    moon_alts = [sky.horizontal(planner.MOON, t, loc)["altitude_deg"] for t in times]
    phase = sky.moon_phase(times[len(times) // 2])
    rows = []
    for t, h, moon_alt in zip(times, radiant, moon_alts):
        lm = nelm_from_sqm(sqm_with_moon(sqm, phase["magnitude"], moon_alt))  # looking away from the Moon
        zhr = zhr_at(shower, t, peak)
        rows.append((t, h, lm, None if zhr is None else hourly_rate(zhr, h, lm, shower.r)))
    best = max(rows, key=lambda r: (r[3] or 0, r[1]))
    up_hours = sum(1 for _, h, _, _ in rows if h >= 20) * STEP_MIN / 60
    row |= {
        "dark_window": {"start": fmt(n.window[0], loc), "end": fmt(n.window[1], loc), "darkest_sky": n.darkest},
        "moon": {"illuminated_percent": phase["illuminated_percent"],
                 "up_during_dark_pct": round(100 * sum(1 for a in moon_alts if a > 0) / len(moon_alts))},
        "radiant_peak_altitude_deg": round(max(radiant)),
        "hours_radiant_above_20deg": round(up_hours, 1),
        "best_time": fmt(best[0], loc),
        "radiant_altitude_at_best_deg": round(best[1]),
        "limiting_magnitude_at_best": round(best[2], 1),
    }
    if shower.zhr is not None:
        row["expected_meteors_per_hour"] = round(best[3])
        row["expected_meteors_all_night"] = round(sum(r[3] for r in rows) * STEP_MIN / 60)
    row["rating"] = rating(best[3]) if max(radiant) > 0 else "poor"
    if max(radiant) <= 0:
        row["reason"] = "The radiant stays below the horizon during the dark hours at this latitude."
    elif shower.zhr is not None and best[3] < 5 and phase["illuminated_percent"] > 50 and any(a > 0 for a in moon_alts):
        row["reason"] = "Moonlight drowns out the fainter meteors."
    return row


def describe(shower: Shower, peak: datetime, loc: Location | None) -> dict[str, Any]:
    ra, dec = shower.ra, shower.dec
    out: dict[str, Any] = {
        "name": shower.name,
        "code": f"{shower.iau:03d} {shower.code}",
        "active": active_label(shower),
        "peak": fmt(peak, loc) if loc else peak.isoformat(timespec="minutes"),
        "peak_utc": peak.astimezone(UTC).isoformat(timespec="minutes"),
        "solar_longitude_deg": shower.sol_lon,
        "zhr": shower.zhr if shower.zhr is not None else "variable",
        "population_index_r": shower.r,
        "velocity_km_s": shower.velocity,
        "radiant": {"ra_deg": ra, "dec_deg": dec, "constellation": sky.constellation(ra, dec)["name"]},
        "daytime_shower": shower.daytime or None,
        "note": shower.note,
    }
    if shower.daytime:
        out["note"] = "Daytime shower: the radiant is close to the Sun, so it is followed by radio; visual rates are tiny."
    return {k: v for k, v in out.items() if v is not None}


def upcoming(start: datetime, days: int, include_minor: bool) -> list[tuple[Shower, datetime]]:
    """Showers whose maximum falls in [start, start + days], in date order."""
    end = start + timedelta(days=days)
    found = []
    for s in SHOWERS:
        if not include_minor and (s.daytime or (s.zhr is not None and s.zhr < MAJOR_MIN_ZHR) or s.zhr is None):
            continue
        t = peak_time(s, start)
        while t <= end:
            found.append((s, t))
            t = peak_time(s, t + timedelta(days=300))
    return sorted(found, key=lambda pair: pair[1])
