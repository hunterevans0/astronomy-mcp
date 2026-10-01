"""Observing-night planning: resolve targets, judge visibility, rank what's up tonight,
and compare nights (best night for a target, dark-moon weekends)."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import astronomy as ae

from astronomy_mcp import catalog, simbad, sky, visibility
from astronomy_mcp.conditions import limiting_magnitude, sqm_with_moon
from astronomy_mcp.horizon import Horizon
from astronomy_mcp.http import UpstreamError
from astronomy_mcp.location import Location
from astronomy_mcp.sky import Night, Target, fmt

MOON = Target("Moon", ae.Body.Moon)
SKIP_GROUPS = {"star", "other", "dark_nebula"}  # rarely what "worth looking at" means

NIGHT_STEP_MIN = 20  # sampling when comparing many nights
MOON_WASHOUT_MAG = 3.0  # sky brightening at which moonlight zeroes a night's score
FULL_CREDIT_HOURS = 2.0  # usable time beyond this no longer improves a night's score
NEW_MOON_REACH_DAYS = 9  # weekends further than this from new moon are never dark
MAX_ILLUMINATION_PCT = 25.0  # dark-moon limit when there is no location to compute moonrise from


async def resolve_target(name: str) -> Target:
    """Planet/Sun/Moon by name, then OpenNGC (M/NGC/IC/common names), then SIMBAD."""
    key = name.strip().lower()
    if key in sky.BODIES:
        return Target(name.strip().title(), sky.BODIES[key])
    try:
        cat = await catalog.get_catalog()
        if obj := cat.lookup(name):
            return Target(obj["name"], None, obj["ra_deg"], obj["dec_deg"], "OpenNGC", obj)
    except UpstreamError:
        pass  # catalog not downloadable right now; SIMBAD still works
    obj = await simbad.lookup(name, max_aliases=0)
    if obj is None:
        raise ValueError(f"Could not resolve '{name}' as a planet, catalog object or SIMBAD identifier.")
    info = {
        "type": obj.get("object_type_description"),
        "magnitude": (obj.get("magnitudes") or {}).get("V"),
        "spectral_type": obj.get("spectral_type"),
    }
    return Target(obj["main_id"], None, obj["ra_deg"], obj["dec_deg"], "SIMBAD", {k: v for k, v in info.items() if v is not None})


def display_names(obj: dict[str, Any]) -> tuple[str, list[str]]:
    """Friendliest name first: Messier number, then NGC/IC/Caldwell, else the common name
    (so 'Large Magellanic Cloud' rather than 'ESO 56-115')."""
    common = obj.get("common_names", [])
    if "messier" in obj:
        return obj["messier"], [obj["name"], *common[:2]]
    if obj["name"].startswith(("NGC", "IC", "Caldwell")) or not common:
        return obj["name"], common[:2]
    return common[0], [obj["name"], *common[1:2]]


def target_magnitude(target: Target, when: datetime) -> float | None:
    if target.body is not None:
        return ae.Illumination(target.body, sky.to_time(when)).mag
    return target.info.get("magnitude")


def _samples(start: datetime, end: datetime, step_min: int) -> list[datetime]:
    out, t = [], start
    while t <= end:
        out.append(t)
        t += timedelta(minutes=step_min)
    return out


def _planet_window(n: Night) -> tuple[datetime, datetime]:
    """Planets and the Moon are fine in twilight: civil dusk to civil dawn."""
    dusk, dawn = n.civil
    if dusk and dawn:
        return dusk, dawn
    return n.window


def difficulty(margin_mag: float) -> str:
    if margin_mag >= 3:
        return "easy"
    if margin_mag >= 1.5:
        return "moderate"
    if margin_mag >= 0.5:
        return "challenging"
    if margin_mag >= 0:
        return "at the limit (averted vision, patience)"
    return "not visible"


def _floor(min_altitude: float, horizon: Horizon | None, azimuth_deg: float) -> float:
    """Lowest useful altitude in a direction: the user's minimum or the terrain, whichever is higher."""
    return max(min_altitude, horizon.altitude_at(azimuth_deg)) if horizon else min_altitude


def _detect(target_info: dict[str, Any], mag: float, sky_sqm: float, equipment: str,
            aperture_mm: float | None, altitude_deg: float) -> visibility.Detection:
    return visibility.detect(
        mag, sky_sqm, equipment, aperture_mm,
        target_info.get("major_axis_arcmin"), target_info.get("minor_axis_arcmin"), target_info.get("group"),
        altitude_deg,
    )


def visibility_report(
    target: Target,
    loc: Location,
    n: Night,
    sqm: float,
    equipment: str,
    aperture_mm: float | None,
    min_altitude: float,
    horizon: Horizon | None = None,
) -> dict[str, Any]:
    """Can this target be seen tonight, when, and if not, why not."""
    is_solar_system = target.body is not None
    start, end = _planet_window(n) if is_solar_system else n.window
    if n.darkest == "none":
        start, end = n.window[0], n.window[0] + timedelta(days=1)
    track = sky.altitude_track(target, start, end, loc, step_min=10)
    moon_track = sky.altitude_track(MOON, start, end, loc, step_min=10)
    moon_mag = ae.Illumination(ae.Body.Moon, sky.to_time(start + (end - start) / 2)).mag

    up = [i for i, (_, alt, az) in enumerate(track) if alt >= _floor(min_altitude, horizon, az)]
    above_min = [i for i, (_, alt, _) in enumerate(track) if alt >= min_altitude]
    best_i = max(up or range(len(track)), key=lambda i: track[i][1])
    best_t, best_alt, best_az = track[best_i]
    reasons: list[str] = []
    mag = target_magnitude(target, best_t)

    if n.darkest == "none" and not is_solar_system:
        reasons.append("The sky never gets dark on this date at this latitude (midnight sun).")
    if not above_min:
        reasons.append(
            f"It never climbs above {min_altitude:.0f}° during the "
            f"{'twilight-to-dawn' if is_solar_system else 'dark'} window (peak {best_alt:.0f}°)."
        )
    elif not up:
        reasons.append("Terrain blocks it: whenever it is high enough, it is behind the local horizon.")

    moon_sep = None
    if moon_track[best_i][1] > 0 and target.name != "Moon":
        moon_sep = sky.separation_deg(*sky.j2000_position(target, best_t), *sky.j2000_position(MOON, best_t))
    sky_here = sqm_with_moon(sqm, moon_mag, moon_track[best_i][1], moon_sep if moon_sep is not None else 90.0)
    detection = None
    if mag is not None and target.name not in ("Moon", "Sun") and up:
        detection = _detect(target.info if not is_solar_system else {}, mag, sky_here, equipment, aperture_mm, best_alt)
        if not detection.visible:
            reasons.append(
                f"Too faint for {equipment.replace('_', ' ')} under this sky: it misses the detection "
                f"threshold by {-detection.margin_mag:.1f} mag at its best."
            )
    moon_note = None
    if moon_sep is not None and moon_sep < 25 and sky.moon_phase(best_t)["illuminated_percent"] > 25:
        moon_note = f"The Moon is only {moon_sep:.0f}° away at the best time, brightening the sky around it."
    if target.name == "Sun":
        reasons = ["The Sun is never a night-time target. Solar observing needs a certified solar filter."]

    report: dict[str, Any] = {
        "target": target.name,
        "visible": not reasons,
        "reasons_not_visible": reasons or None,
        "best_time": fmt(best_t, loc),
        "altitude_at_best_deg": round(best_alt, 1),
        "direction_at_best": f"{sky.compass(best_az)} (az {best_az:.0f}°)",
        "local_horizon_at_best_deg": round(horizon.altitude_at(best_az), 1) if horizon else None,
        "observable_window": (
            {"from": fmt(track[up[0]][0], loc), "until": fmt(track[up[-1]][0], loc),
             "hours": round(len(up) * 10 / 60, 1)} if up else None
        ),
        "magnitude": round(mag, 2) if mag is not None else None,
        "difficulty": difficulty(detection.margin_mag) if detection else None,
        "detection_margin_mag": detection.margin_mag if detection else None,
        "suggested_magnification": (
            f"about {detection.magnification:.0f}x" if detection and equipment == "telescope" else None
        ),
        "moon_warning": moon_note,
        "sky_assumed": limiting_magnitude(sky_here, equipment, aperture_mm),
    }
    return {k: v for k, v in report.items() if v is not None}


def whats_up(
    loc: Location,
    n: Night,
    cat: catalog.Catalog | None,
    sqm: float,
    equipment: str,
    aperture_mm: float | None,
    min_altitude: float,
    include: str,
    groups: set[str] | None,
    max_results: int,
    horizon: Horizon | None = None,
) -> dict[str, Any]:
    if n.darkest == "none":
        return {"message": "The Sun does not set on this date at this latitude; there is no night.", "targets": []}

    entries: list[dict[str, Any]] = []
    dark_times = _samples(n.window[0], n.window[1], 15)
    moon_alts = [sky.horizontal(MOON, t, loc)["altitude_deg"] for t in dark_times]
    moon_mag = ae.Illumination(ae.Body.Moon, sky.to_time(dark_times[len(dark_times) // 2])).mag
    darkest_limit = limiting_magnitude(sqm, equipment, aperture_mm)

    # --- planets and the Moon (full-precision positions, twilight allowed)
    if include in ("all", "planets"):
        p_start, p_end = _planet_window(n)
        p_times = _samples(p_start, p_end, 15)
        for name in ("moon", *sky.PLANETS):
            target = Target(name.title(), sky.BODIES[name])
            track = []
            for t in p_times:
                h = sky.horizontal(target, t, loc)
                track.append((t, h["altitude_deg"], h["azimuth_deg"]))
            up = [row for row in track if row[1] >= _floor(min(min_altitude, 10), horizon, row[2])]
            if not up:
                continue
            best_t, best_alt, best_az = max(up, key=lambda r: r[1])
            mag = target_magnitude(target, best_t)
            if name != "moon" and not _detect({}, mag, sqm, equipment, aperture_mm, best_alt).visible:
                continue
            entry = {
                "name": target.name,
                "type": "Moon" if name == "moon" else "Planet",
                "magnitude": round(mag, 1),
                "best_time": fmt(best_t, loc),
                "altitude_at_best_deg": round(best_alt),
                "direction_at_best": sky.compass(best_az),
                "visible_from": fmt(up[0][0], loc),
                "visible_until": fmt(up[-1][0], loc),
                "score": round(100 * (
                    0.45
                    + 0.25 * math.sin(math.radians(best_alt))
                    + 0.15 * len(up) / len(track)
                    + 0.15 * min(1.0, (darkest_limit["stellar_limit"] - mag) / 6)
                )),
            }
            if name == "moon":
                entry["phase"] = sky.moon_phase(best_t)["phase"]
            if name in ("uranus", "neptune") and equipment == "naked_eye":
                entry["note"] = "At the edge of naked-eye visibility; binoculars help."
            entries.append(entry)

    # --- deep sky from OpenNGC (fast vectorised altitudes, then the detection model)
    hidden_faint = hidden_terrain = 0
    if include in ("all", "deep_sky") and cat is not None and dark_times:
        prefilter_limit = darkest_limit["stellar_limit"]
        candidates = []
        for obj in cat.objects:
            showpiece = "messier" in obj or obj.get("name", "").startswith("Caldwell")
            if groups and obj["group"] not in groups:
                continue
            if obj["group"] in SKIP_GROUPS and not showpiece:
                continue
            mag = obj.get("magnitude")
            if mag is None and (not showpiece or equipment != "telescope"):
                continue
            if mag is not None and mag > prefilter_limit:
                continue
            if 90 - abs(loc.latitude - obj["dec_deg"]) < min_altitude:
                continue
            candidates.append(obj)
        tracks = sky.fast_tracks([(o["ra_deg"], o["dec_deg"]) for o in candidates], dark_times, loc)
        moon_radec = [sky.j2000_position(MOON, t) for t in dark_times]
        for obj, track in zip(candidates, tracks):
            high_enough = [i for i, (alt, _) in enumerate(track) if alt >= min_altitude]
            if not high_enough:
                continue
            up = [i for i in high_enough if track[i][0] >= _floor(min_altitude, horizon, track[i][1])]
            if not up:
                hidden_terrain += 1
                continue
            best_i = max(up, key=lambda i: track[i][0])
            best_alt, best_az = track[best_i]
            sep = None
            if moon_alts[best_i] > 0:
                sep = sky.separation_deg(obj["ra_deg"], obj["dec_deg"], *moon_radec[best_i])
            sky_here = sqm_with_moon(sqm, moon_mag, moon_alts[best_i], sep if sep is not None else 90.0)
            mag = obj.get("magnitude")
            if mag is None:
                margin, magnification = 1.0, None
            else:
                det = _detect(obj, mag, sky_here, equipment, aperture_mm, best_alt)
                margin, magnification = det.margin_mag, det.magnification
            if margin < 0:
                hidden_faint += 1
                continue
            showpiece = "messier" in obj or "common_names" in obj
            score = 100 * (
                0.35 * min(margin, 4) / 4
                + 0.30 * math.sin(math.radians(best_alt))
                + 0.15 * len(up) / len(track)
                + 0.20 * showpiece
            )
            name, aliases = display_names(obj)
            entry = {
                "name": name,
                "also_known_as": ", ".join(aliases) or None,
                "type": obj["type"],
                "constellation": obj.get("constellation"),
                "magnitude": mag,
                "size_arcmin": obj.get("major_axis_arcmin"),
                "difficulty": difficulty(margin),
                "suggested_magnification": (
                    f"about {magnification:.0f}x" if magnification and equipment == "telescope" else None
                ),
                "best_time": fmt(dark_times[best_i], loc),
                "altitude_at_best_deg": round(best_alt),
                "direction_at_best": sky.compass(best_az),
                "visible_from": fmt(dark_times[up[0]], loc),
                "visible_until": fmt(dark_times[up[-1]], loc),
                "score": round(score),
                "note": f"Moon {sep:.0f}° away" if sep is not None and sep < 25 else None,
            }
            entries.append({k: v for k, v in entry.items() if v is not None})

    entries.sort(key=lambda e: e["score"], reverse=True)
    moon_up = sum(1 for alt in moon_alts if alt > 0)
    return {
        "night": n.to_dict(loc),
        "moon": {
            **sky.moon_phase(dark_times[len(dark_times) // 2]),
            "up_during_dark_window_pct": round(100 * moon_up / len(moon_alts)) if moon_alts else 0,
        },
        "assumptions": {
            **darkest_limit,
            "min_altitude_deg": min_altitude,
            "terrain_horizon": "applied" if horizon else "not applied",
            "note": "Visibility comes from a detection model calibrated to Bortle's scale descriptions; "
                    "treat it as an estimate.",
        },
        "count": min(len(entries), max_results),
        "targets": entries[:max_results],
        "too_faint_for_conditions": hidden_faint or None,
        "hidden_by_terrain": hidden_terrain or None,
    }


# ---------------------------------------------------------------- comparing nights

def moon_free_hours(loc: Location, n: Night, step_min: int = 10) -> float:
    """Hours of the night's dark window with the Moon below the horizon."""
    if n.darkest == "none":
        return 0.0
    track = sky.altitude_track(MOON, n.window[0], n.window[1], loc, step_min)
    hours = (n.window[1] - n.window[0]).total_seconds() / 3600
    return round(hours * sum(1 for row in track if row[1] < 0) / len(track), 1)


def _forecast_hour(t: datetime) -> datetime:
    return (t.astimezone(UTC) + timedelta(minutes=30)).replace(minute=0, second=0, microsecond=0)


def score_night(
    target: Target | None,
    loc: Location,
    n: Night,
    sqm: float,
    min_altitude: float,
    clouds: dict[datetime, float] | None,
) -> dict[str, Any]:
    """Score one night 0-100 as usable time x target altitude x moonlight x clear sky.

    Cloud cover is left out (and `cloud_pct` omitted) when the forecast doesn't reach the night.
    """
    row: dict[str, Any] = {"date": n.date.isoformat(), "weekday": n.date.strftime("%a")}
    if n.darkest == "none":
        return {**row, "score": 0, "reason": "no darkness (midnight sun)"}
    is_body = target is not None and target.body is not None
    start, end = _planet_window(n) if is_body else n.window
    times = _samples(start, end, NIGHT_STEP_MIN)
    mid = times[len(times) // 2]
    phase = sky.moon_phase(mid)
    row["moon_illuminated_percent"] = phase["illuminated_percent"]

    if target is None:
        usable = list(range(len(times)))
    else:
        if is_body:
            alts = [sky.horizontal(target, t, loc)["altitude_deg"] for t in times]
        else:
            alts = [alt for alt, _ in sky.fast_tracks([(target.ra_deg, target.dec_deg)], times, loc)[0]]
        usable = [i for i, alt in enumerate(alts) if alt >= min_altitude]
        if not usable:
            return {**row, "score": 0,
                    "reason": f"never above {min_altitude:.0f}° while it is dark (peak {max(alts):.0f}°)"}
        best_i = max(usable, key=lambda i: alts[i])
    hours = (end - start).total_seconds() / 3600 * len(usable) / len(times)
    score = min(1.0, hours / FULL_CREDIT_HOURS)
    if target is None:
        row["dark_hours"] = round(hours, 1)
    else:
        score *= math.sin(math.radians(alts[best_i]))
        row |= {"hours_above_min_altitude": round(hours, 1), "peak_altitude_deg": round(alts[best_i]),
                "best_time": fmt(times[best_i], loc)}

    if not is_body:  # moonlight doesn't hurt the Moon and planets
        sep = 90.0
        if target is not None:
            sep = sky.separation_deg(target.ra_deg, target.dec_deg, *sky.j2000_position(MOON, mid))
            row["moon_separation_deg"] = round(sep)
        brightening = sum(
            sqm - sqm_with_moon(sqm, phase["magnitude"], sky.horizontal(MOON, times[i], loc)["altitude_deg"], sep)
            for i in usable
        ) / len(usable)
        row["moon_sky_brightening_mag"] = round(brightening, 2)
        score *= 1 - min(1.0, brightening / MOON_WASHOUT_MAG)

    if clouds:
        seen = [clouds.get(_forecast_hour(times[i])) for i in usable]
        if None not in seen:
            cloud = sum(seen) / len(seen)
            row["cloud_pct"] = round(cloud)
            score *= 1 - cloud / 100
    return {**row, "score": round(100 * score)}


def best_nights(
    target: Target | None,
    loc: Location,
    first: date,
    days: int,
    sqm: float,
    min_altitude: float,
    clouds: dict[datetime, float] | None,
    top: int = 5,
) -> dict[str, Any]:
    """Score every night in a span; rank those the cloud forecast reaches apart from those it doesn't."""
    rows = [score_night(target, loc, sky.night(loc, first + timedelta(days=i)), sqm, min_altitude, clouds)
            for i in range(days)]

    def ranked(want_forecast: bool) -> list[dict[str, Any]]:
        pool = [r for r in rows if r["score"] > 0 and ("cloud_pct" in r) == want_forecast]
        return sorted(pool, key=lambda r: r["score"], reverse=True)[:top]

    forecast_dates = [r["date"] for r in rows if "cloud_pct" in r]
    factors = ["usable time"]
    if target is not None:
        factors.append("target altitude")
    if target is None or target.is_fixed:
        factors.append("moonlight")
    out = {
        "period": {"from": rows[0]["date"], "to": rows[-1]["date"]},
        "cloud_forecast_through": forecast_dates[-1] if forecast_dates else None,
        "best_nights_with_forecast": ranked(True),
        "best_nights_beyond_forecast": ranked(False),
        "nights": rows,
        "scoring": f"score = {' x '.join(factors)} x clear sky, 0-100. Nights beyond the cloud forecast are "
                   "scored without weather, so compare them only with each other. Cloud forecasts more than "
                   "about 5 days out are low confidence.",
    }
    if not any(r["score"] for r in rows):
        reason = rows[0].get("reason", "the forecast is fully overcast or the Moon washes out every night")
        out["message"] = f"No night in this period scores above zero: {reason}."
    return {k: v for k, v in out.items() if v is not None}


def dark_moon_weekends(
    loc: Location | None, first: date, days: int, min_moon_free_pct: float = 70.0
) -> dict[str, Any]:
    """Friday and Saturday nights that are mostly free of moonlight.

    With a location, a weekend qualifies when the Moon is below the horizon for at least
    `min_moon_free_pct` of the two nights' dark hours. Without one, moonrise is unknown, so
    both nights must have the Moon under MAX_ILLUMINATION_PCT lit.
    """
    tz = loc.tz if loc else UTC
    shown = loc or Location(0.0, 0.0)
    last = first + timedelta(days=days - 1)
    span_start = datetime.combine(first, time(12), tzinfo=tz)
    reach = timedelta(days=30)
    new_moons = [t for name, t in sky.moon_quarters(span_start - reach, span_start + timedelta(days=days) + reach)
                 if name == "New Moon"]
    until_friday = (4 - first.weekday()) % 7
    friday = first + timedelta(days=-1 if until_friday == 6 else until_friday)  # on a Saturday, keep this weekend

    weekends, no_darkness = [], 0
    while friday <= last:
        days_of = (friday, friday + timedelta(days=1))
        friday += timedelta(weeks=1)
        midnights = [datetime.combine(d + timedelta(days=1), time(0), tzinfo=tz) for d in days_of]
        new_moon = min(new_moons, key=lambda t: abs(t - midnights[1]))
        from_new = (midnights[1] - new_moon).total_seconds() / 86400
        if abs(from_new) > NEW_MOON_REACH_DAYS:
            continue
        nights, dark, moon_free = [], 0.0, 0.0
        for day, midnight in zip(days_of, midnights):
            phase = sky.moon_phase(midnight)
            row = {"date": day.isoformat(), "phase": phase["phase"], "illuminated_percent": phase["illuminated_percent"]}
            if loc:
                n = sky.night(loc, day)
                hours = (n.window[1] - n.window[0]).total_seconds() / 3600 if n.darkest != "none" else 0.0
                free = moon_free_hours(loc, n)
                row |= {"dark_hours": round(hours, 1), "moon_free_dark_hours": free}
                dark, moon_free = dark + hours, moon_free + free
            nights.append(row)
        brightest = max(r["illuminated_percent"] for r in nights)
        if loc:
            if not dark:
                no_darkness += 1
                continue
            pct = min(100.0, 100 * moon_free / dark)
            qualifies, excellent = pct >= min_moon_free_pct, pct >= 90
        else:
            pct = None
            qualifies, excellent = brightest <= MAX_ILLUMINATION_PCT, brightest <= 10
        if not qualifies:
            continue
        weekend = {
            "friday": days_of[0].isoformat(),
            "saturday": days_of[1].isoformat(),
            "rating": "excellent" if excellent else "good",
            "moon_free_dark_pct": round(pct) if pct is not None else None,
            "new_moon": fmt(new_moon, shown),
            "days_from_new_moon": round(from_new, 1),
            "nights": nights,
        }
        weekends.append({k: v for k, v in weekend.items() if v is not None})

    out = {
        "period": {"from": first.isoformat(), "to": last.isoformat()},
        "criterion": (
            f"Moon below the horizon for at least {min_moon_free_pct:.0f}% of the Friday and Saturday nights' "
            "dark hours" if loc else
            f"Moon no more than {MAX_ILLUMINATION_PCT:.0f}% lit on both nights (no location given, so moonrise "
            "and moonset are not considered; dates are UTC)"
        ),
        "count": len(weekends),
        "weekends": weekends,
        "weekends_without_darkness": no_darkness or None,
    }
    return {k: v for k, v in out.items() if v is not None}
