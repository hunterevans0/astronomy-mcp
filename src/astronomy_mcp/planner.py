"""Observing-night planning: resolve targets, judge visibility, rank what's up tonight."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

import astronomy as ae

from astronomy_mcp import catalog, simbad, sky
from astronomy_mcp.conditions import limiting_magnitude, sqm_with_moon
from astronomy_mcp.http import UpstreamError
from astronomy_mcp.location import Location
from astronomy_mcp.sky import Night, Target, fmt

MOON = Target("Moon", ae.Body.Moon)
SKIP_GROUPS = {"star", "other", "dark_nebula"}  # rarely what "worth looking at" means


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


def estimated_surface_brightness(obj: dict[str, Any]) -> float | None:
    """Mean surface brightness (mag/arcsec^2) from magnitude and elliptical size."""
    mag, a = obj.get("magnitude"), obj.get("major_axis_arcmin")
    if mag is None or not a:
        return None
    b = obj.get("minor_axis_arcmin") or a
    return mag + 2.5 * math.log10(math.pi / 4 * a * b * 3600)


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


def visibility_report(
    target: Target,
    loc: Location,
    n: Night,
    sqm: float,
    equipment: str,
    aperture_mm: float | None,
    min_altitude: float,
) -> dict[str, Any]:
    """Can this target be seen tonight, when, and if not, why not."""
    is_solar_system = target.body is not None
    start, end = _planet_window(n) if is_solar_system else n.window
    if n.darkest == "none":
        start, end = n.window[0], n.window[0] + timedelta(days=1)
    track = sky.altitude_track(target, start, end, loc, step_min=10)
    moon_track = sky.altitude_track(MOON, start, end, loc, step_min=10)
    mid = start + (end - start) / 2
    moon_mag = ae.Illumination(ae.Body.Moon, sky.to_time(mid)).mag

    up = [i for i, (_, alt, _) in enumerate(track) if alt >= min_altitude]
    best_i = max(range(len(track)), key=lambda i: track[i][1])
    best_t, best_alt, best_az = track[best_i]
    reasons: list[str] = []
    mag = target_magnitude(target, best_t)

    if n.darkest == "none" and not is_solar_system:
        reasons.append("The sky never gets dark on this date at this latitude (midnight sun).")
    if not up:
        reasons.append(
            f"It never climbs above {min_altitude:.0f}° during the "
            f"{'twilight-to-dawn' if is_solar_system else 'dark'} window (peak {best_alt:.0f}°)."
        )
    limit = limiting_magnitude(sqm_with_moon(sqm, moon_mag, moon_track[best_i][1]), equipment, aperture_mm)
    if mag is not None and target.name != "Moon":
        point_like = is_solar_system or target.source == "SIMBAD" or target.info.get("group") in ("star", "double_star")
        threshold = limit["stellar_limit"] if point_like else limit["extended_object_limit"]
        if mag > threshold:
            reasons.append(f"At magnitude {mag:.1f} it is fainter than the ~{threshold:.1f} you can reach with {equipment.replace('_', ' ')} under this sky.")
    moon_note = None
    if target.name != "Moon" and moon_track[best_i][1] > 0:
        ra, dec = sky.j2000_position(target, best_t)
        mra, mdec = sky.j2000_position(MOON, best_t)
        sep = sky.separation_deg(ra, dec, mra, mdec)
        illum = sky.moon_phase(best_t)["illuminated_percent"]
        if sep < 15 and illum > 25:
            moon_note = f"The {illum:.0f}%-lit Moon is only {sep:.0f}° away at the best time."
    if target.name == "Sun":
        reasons = ["The Sun is never a night-time target. Solar observing needs a certified solar filter."]

    report: dict[str, Any] = {
        "target": target.name,
        "visible": not reasons,
        "reasons_not_visible": reasons or None,
        "best_time": fmt(best_t, loc),
        "altitude_at_best_deg": round(best_alt, 1),
        "direction_at_best": f"{sky.compass(best_az)} (az {best_az:.0f}°)",
        "above_min_altitude": (
            {"from": fmt(track[up[0]][0], loc), "until": fmt(track[up[-1]][0], loc),
             "hours": round(len(up) * 10 / 60, 1)} if up else None
        ),
        "magnitude": round(mag, 2) if mag is not None else None,
        "moon_warning": moon_note,
        "limiting_magnitude_assumed": limit,
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
            up =[row for row in track if row[1] >= min(min_altitude, 10)]
            if not up:
                continue
            best_t, best_alt, best_az = max(up, key=lambda r: r[1])
            mag = target_magnitude(target, best_t)
            if name != "moon" and mag > darkest_limit["stellar_limit"]:
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

    # --- deep sky from OpenNGC (fast vectorised altitudes)
    hidden_faint = 0
    if include in ("all", "deep_sky") and cat is not None and dark_times:
        prefilter_limit = darkest_limit["extended_object_limit"] + 0.5
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
        sky_by_sample = [sqm_with_moon(sqm, moon_mag, alt) for alt in moon_alts]
        moon_radec = [sky.j2000_position(MOON, t) for t in dark_times]
        for obj, track in zip(candidates, tracks):
            up = [i for i, (alt, _) in enumerate(track) if alt >= min_altitude]
            if not up:
                continue
            best_i = max(up, key=lambda i: track[i][0])
            best_alt, best_az = track[best_i]
            limit = limiting_magnitude(sky_by_sample[best_i], equipment, aperture_mm)["extended_object_limit"]
            mag = obj.get("magnitude")
            margin = (limit - mag) if mag is not None else 1.0
            sb = obj.get("surface_brightness") or estimated_surface_brightness(obj)
            if sb is not None:
                margin -= max(0.0, sb - (sky_by_sample[best_i] + 2.5)) * 0.5
            note = None
            if moon_alts[best_i] > 0:
                sep = sky.separation_deg(obj["ra_deg"], obj["dec_deg"], *moon_radec[best_i])
                if sep < 20:
                    margin -= 1.0
                    note = f"Moon {sep:.0f}° away"
            if margin < 0:
                hidden_faint += 1
                continue
            showpiece = "messier" in obj or "common_names" in obj
            score = 100 * (
                0.35 * min(margin, 5) / 5
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
                "best_time": fmt(dark_times[best_i], loc),
                "altitude_at_best_deg": round(best_alt),
                "direction_at_best": sky.compass(best_az),
                "visible_from": fmt(dark_times[up[0]], loc),
                "visible_until": fmt(dark_times[up[-1]], loc),
                "score": round(score),
                "note": note,
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
            "note": "Limiting magnitudes are estimates from a sky-brightness model, not measurements.",
        },
        "count": min(len(entries), max_results),
        "targets": entries[:max_results],
        "too_faint_for_conditions": hidden_faint or None,
    }
