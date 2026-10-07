"""Variable stars right now: AAVSO observations (through the VSX API) on top of the VSX catalog entry.

The AAVSO International Database is served by VSX as delimited text
(view=api.delim). Rows flagged discrepant by AAVSO's validators are dropped, and
"fainter than" estimates are kept apart from measurements.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import median
from typing import Any

from astronomy_mcp import vsx
from astronomy_mcp.http import get_text
from astronomy_mcp.location import Location
from astronomy_mcp.sky import fmt

JD_UNIX_EPOCH = 2440587.5
VISUAL_LIKE = ("Vis.", "V", "CV", "TG")  # bands close enough to visual to compare
MAX_LIGHT_CURVE_DAYS = 730
DISCREPANT = "T"


def julian(dt: datetime) -> float:
    return dt.timestamp() / 86400 + JD_UNIX_EPOCH


def from_julian(jd: float) -> datetime:
    return datetime.fromtimestamp((jd - JD_UNIX_EPOCH) * 86400, UTC)


@dataclass
class Observation:
    jd: float
    mag: float
    band: str
    fainter_than: bool
    kind: str  # Visual, CCD, DSLR, PEP...

    @property
    def when(self) -> datetime:
        return from_julian(self.jd)


def parse_observations(text: str) -> list[Observation]:
    lines = text.strip().splitlines()
    if not lines:
        return []
    header = lines[0].split("|")
    col = {name: i for i, name in enumerate(header)}
    needed = ("JD", "mag", "band")
    if not all(n in col for n in needed):
        return []
    out = []
    for line in lines[1:]:
        f = line.split("|")
        if len(f) < len(header):
            continue
        if col.get("val") is not None and f[col["val"]] == DISCREPANT:
            continue
        try:
            jd, mag = float(f[col["JD"]]), float(f[col["mag"]].lstrip("<"))
        except ValueError:
            continue
        fainter = f[col["fainterThan"]] == "1" if "fainterThan" in col else f[col["mag"]].startswith("<")
        out.append(Observation(jd, mag, f[col["band"]], fainter, f[col["obsType"]] if "obsType" in col else ""))
    out.sort(key=lambda o: o.jd)
    return out


async def observations(name: str, days: float, end: datetime | None = None) -> list[Observation]:
    end = end or datetime.now(UTC)
    text = await get_text(vsx.API_URL, {"view": "api.delim", "ident": name.strip(), "fromjd": f"{julian(end) - days:.4f}",
                                        "tojd": f"{julian(end):.4f}", "delimiter": "|"},
                          source="AAVSO (VSX)", ttl=1800, timeout=120)
    return parse_observations(text)


def _slope(points: list[tuple[float, float]]) -> float | None:
    """Least-squares magnitude change per day."""
    if len(points) < 4 or points[-1][0] - points[0][0] < 1:
        return None
    mx = sum(x for x, _ in points) / len(points)
    my = sum(y for _, y in points) / len(points)
    den = sum((x - mx) ** 2 for x, _ in points)
    return sum((x - mx) * (y - my) for x, y in points) / den if den else None


def band_summary(obs: list[Observation], since_jd: float) -> list[dict[str, Any]]:
    by_band: dict[str, list[float]] = {}
    for o in obs:
        if o.jd >= since_jd and not o.fainter_than:
            by_band.setdefault(o.band, []).append(o.mag)
    rows = [{"band": b, "median": round(median(m), 2), "brightest": round(min(m), 2), "faintest": round(max(m), 2),
             "count": len(m)}
            for b, m in by_band.items()]
    return sorted(rows, key=lambda r: -r["count"])


def _eclipsing(star: dict[str, Any]) -> bool:
    return (star.get("variability_type") or "").upper().startswith("E")


def predictions(star: dict[str, Any], now: datetime, loc: Location | None) -> dict[str, Any] | None:
    """Next maximum (pulsating stars) or primary eclipse (eclipsing binaries) from VSX's period and epoch."""
    period, epoch = star.get("period_days"), star.get("epoch_hjd")
    if not isinstance(period, float) or not isinstance(epoch, float) or period <= 0:
        return None
    eclipsing = _eclipsing(star)
    jd_now = julian(now)
    cycles = math.floor((jd_now - epoch) / period)
    last, nxt = epoch + cycles * period, epoch + (cycles + 1) * period
    shown = loc or Location(0.0, 0.0)
    label = "primary_eclipse" if eclipsing else "maximum"
    out: dict[str, Any] = {
        "period_days": period,
        "phase_now": round((jd_now - epoch) / period % 1, 3),
        f"previous_{label}": fmt(from_julian(last), shown),
        f"next_{label}": fmt(from_julian(nxt), shown),
    }
    if eclipsing and period < 30:
        out["upcoming_eclipses"] = [fmt(from_julian(nxt + k * period), shown) for k in range(1, 4)]
    if not eclipsing and period > 50:
        out["note"] = "Long-period variables drift from their predicted dates by days to weeks; observations rule."
    return out


async def status(name: str, days: int, loc: Location | None) -> dict[str, Any]:
    star = await vsx.lookup(name)
    if star is None:
        raise ValueError(f"VSX has no variable star named '{name}'.")
    now = datetime.now(UTC)
    obs = await observations(star.get("name", name), days, now)
    measured = [o for o in obs if not o.fainter_than]
    shown = loc or Location(0.0, 0.0)
    out: dict[str, Any] = {
        "star": {k: star.get(k) for k in ("name", "variability_type", "period_days", "max_mag", "min_mag",
                                          "spectral_type", "constellation", "ra_deg", "dec_deg", "vsx_url") if star.get(k) is not None},
        "observations_last_days": days,
        "count": len(obs),
    }
    if not measured:
        out["message"] = (f"No AAVSO observations of {star.get('name', name)} in the last {days} days"
                          + (" (only 'fainter than' estimates)." if obs else "."))
        if obs:
            faint = obs[-1]
            out["latest_fainter_than"] = {"time": fmt(faint.when, shown), "fainter_than_mag": faint.mag, "band": faint.band}
    else:
        latest = measured[-1]
        out["latest"] = {"time": fmt(latest.when, shown), "magnitude": latest.mag, "band": latest.band, "method": latest.kind}
        out["last_7_days_by_band"] = band_summary(obs, julian(now) - 7) or None
        recent = [(o.jd, o.mag) for o in measured if o.band in VISUAL_LIKE and o.jd >= julian(now) - min(days, 14)]
        slope = _slope(recent)
        if slope is not None and not _eclipsing(star):  # an eclipse lasts hours; a 14-day trend means nothing
            trend = "brightening" if slope < -0.02 else "fading" if slope > 0.02 else "steady"
            out["trend_last_14_days"] = {"direction": trend, "mag_per_day": round(slope, 3)}
        bright, faint = (star.get("max_mag") or {}).get("value"), (star.get("min_mag") or {}).get("value")
        # Where it sits now: the last two days of visual-like estimates, since outbursts rise within a day.
        current = [m for jd, m in recent if jd >= latest.jd - 2]
        typical = median(current) if current else latest.mag
        if isinstance(bright, float) and isinstance(faint, float) and faint > bright and not (star.get("min_mag") or {}).get("is_amplitude"):
            position = (typical - bright) / (faint - bright)
            out["within_range"] = {
                "fraction_from_max": round(min(max(position, 0.0), 1.0), 2),
                "description": "near maximum" if position < 0.25 else "near minimum" if position > 0.75 else "between maximum and minimum",
                "outburst": True if (star.get("variability_type") or "").upper().startswith(("UG", "NL", "ZAND", "N")) and position < 0.5 else None,
            }
            out["within_range"] = {k: v for k, v in out["within_range"].items() if v is not None}
    pred = predictions(star, now, loc)
    if pred:
        out["predicted"] = pred
    out["source"] = "AAVSO International Database via VSX; star data from VSX"
    return {k: v for k, v in out.items() if v is not None}


async def light_curve(name: str, days: int, bands: list[str] | None, bin_days: float | None,
                      loc: Location | None) -> dict[str, Any]:
    star = await vsx.lookup(name)
    if star is None:
        raise ValueError(f"VSX has no variable star named '{name}'.")
    if days > MAX_LIGHT_CURVE_DAYS:
        raise ValueError(f"Light curves are limited to {MAX_LIGHT_CURVE_DAYS} days; busy stars have tens of "
                         "thousands of observations a year.")
    now = datetime.now(UTC)
    obs = await observations(star.get("name", name), days, now)
    wanted = {b.lower() for b in bands} if bands else None
    obs = [o for o in obs if wanted is None or o.band.lower() in wanted]
    width = bin_days or max(1.0, round(days / 150, 1))
    shown = loc or Location(0.0, 0.0)
    series: dict[str, list[dict[str, Any]]] = {}
    groups: dict[tuple[str, int], list[Observation]] = {}
    start = julian(now) - days
    for o in obs:
        groups.setdefault((o.band, int((o.jd - start) // width)), []).append(o)
    for (band, k), members in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        measured = [m.mag for m in members if not m.fainter_than]
        point: dict[str, Any] = {"date": fmt(from_julian(start + (k + 0.5) * width), shown)[:10]}
        if measured:
            point |= {"mag": round(median(measured), 2), "n": len(measured)}
            if len(measured) > 2:
                point["spread"] = round(max(measured) - min(measured), 2)
        else:
            point |= {"fainter_than": min(m.mag for m in members), "n": len(members)}
        series.setdefault(band, []).append(point)
    counts = {band: sum(p["n"] for p in pts) for band, pts in series.items()}
    return {
        "star": {k: star.get(k) for k in ("name", "variability_type", "period_days", "max_mag", "min_mag", "vsx_url") if star.get(k) is not None},
        "from": fmt(from_julian(start), shown)[:10],
        "to": fmt(now, shown)[:10],
        "bin_days": width,
        "observations": len(obs),
        "observations_by_band": dict(sorted(counts.items(), key=lambda kv: -kv[1])) or None,
        "light_curve": dict(sorted(series.items(), key=lambda kv: -counts[kv[0]])),
        "note": "Each point is the median of the observations in a bin. Bands: Vis. (visual estimates), V/B/R/I "
                "(filtered CCD), CV (unfiltered, V zero point), TG (DSLR green). Visual and CCD magnitudes can differ "
                "by a few tenths; 'fainter_than' bins had only negative observations. Smaller magnitudes are brighter.",
        "source": "AAVSO International Database via VSX",
    }
