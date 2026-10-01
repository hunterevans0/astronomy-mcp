"""Observing conditions: sky brightness, limiting magnitude, and the night's weather.

Weather comes from Open-Meteo (hourly cloud layers, humidity, dew point, wind;
16 days ahead) and 7Timer! ASTRO (seeing and transparency; about 3 days ahead).
Sky-brightness numbers are models, not measurements, and are labelled as estimates.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

from astronomy_mcp import visibility
from astronomy_mcp.http import UpstreamError, get_json
from astronomy_mcp.location import Location
from astronomy_mcp.sky import Night, fmt

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
SEVEN_TIMER_URL = "https://www.7timer.info/bin/astro.php"

# Typical zenith sky brightness (mag/arcsec^2, V) for each Bortle class.
BORTLE_SQM = {1: 21.9, 2: 21.6, 3: 21.4, 4: 20.8, 5: 20.1, 6: 19.4, 7: 18.8, 8: 18.3, 9: 17.8}
BORTLE_LABELS = {
    1: "excellent dark site", 2: "typical truly dark site", 3: "rural sky", 4: "rural/suburban transition",
    5: "suburban sky", 6: "bright suburban sky", 7: "suburban/urban transition", 8: "city sky", 9: "inner-city sky",
}
DEFAULT_APERTURE_MM = {"naked_eye": 7.0, "binoculars": 50.0, "telescope": 150.0}

# 7Timer! code tables (http://www.7timer.info/doc.php#astro)
SEEING_ARCSEC = {1: "<0.5\"", 2: "0.5-0.75\"", 3: "0.75-1\"", 4: "1-1.25\"", 5: "1.25-1.5\"", 6: "1.5-2\"", 7: "2-2.5\"", 8: ">2.5\""}
TRANSPARENCY_MAG = {1: "<0.3", 2: "0.3-0.4", 3: "0.4-0.5", 4: "0.5-0.6", 5: "0.6-0.7", 6: "0.7-0.85", 7: "0.85-1", 8: ">1"}


# ---------------------------------------------------------------- sky brightness

def sqm_from_bortle(bortle: int) -> float:
    return BORTLE_SQM[max(1, min(9, bortle))]


def bortle_from_sqm(sqm: float) -> int:
    return min(BORTLE_SQM, key=lambda b: abs(BORTLE_SQM[b] - sqm))


def nelm_from_sqm(sqm: float) -> float:
    """Naked-eye limiting magnitude from sky brightness (Schaefer-style fit)."""
    return visibility.eye_threshold(sqm)


def _moon_scattering(separation_deg: float) -> float:
    """Krisciunas & Schaefer (1991) scattering function f(rho), Rayleigh + Mie terms."""
    rho = max(separation_deg, 5.0)
    return 10**5.36 * (1.06 + math.cos(math.radians(rho)) ** 2) + 10 ** (6.15 - rho / 40)


def sqm_with_moon(
    sqm: float, moon_magnitude: float, moon_altitude_deg: float, separation_deg: float = 90.0
) -> float:
    """Add scattered moonlight to a dark-sky brightness.

    Anchored so a high full Moon (mag -12.7) adds about 18 mag/arcsec^2 at 90°
    from the Moon, scaled by the Moon's actual brightness, damped near the horizon,
    and brightened close to the Moon with the Krisciunas & Schaefer angular profile.
    """
    if moon_altitude_deg <= 0:
        return sqm
    k = 10 ** (-0.4 * (moon_magnitude + 12.7)) * math.sqrt(math.sin(math.radians(moon_altitude_deg)))
    k *= _moon_scattering(separation_deg) / _moon_scattering(90.0)
    return -2.5 * math.log10(10 ** (-0.4 * sqm) + k * 10 ** (-0.4 * 18.0))


def limiting_magnitude(sqm: float, equipment: str, aperture_mm: float | None = None) -> dict[str, Any]:
    aperture = aperture_mm or DEFAULT_APERTURE_MM[equipment]
    best = visibility.detect(0.0, sqm, equipment, aperture)
    out = {
        "sky_brightness_mag_arcsec2": round(sqm, 2),
        "bortle_equivalent": bortle_from_sqm(sqm),
        "naked_eye_limit": round(nelm_from_sqm(sqm), 1),
        "equipment": equipment,
        "aperture_mm": aperture if equipment != "naked_eye" else None,
        "stellar_limit": round(best.margin_mag, 1),
        "stellar_limit_magnification": best.magnification if equipment == "telescope" else None,
    }
    return {k: v for k, v in out.items() if v is not None}


# ---------------------------------------------------------------- forecast

def _decode_7timer(payload: dict[str, Any]) -> dict[datetime, dict[str, Any]]:
    init = datetime.strptime(payload["init"], "%Y%m%d%H").replace(tzinfo=UTC)
    out = {}
    for row in payload.get("dataseries", []):
        seeing, transp = row.get("seeing"), row.get("transparency")
        out[init + timedelta(hours=row["timepoint"])] = {
            "seeing_code": seeing if seeing in SEEING_ARCSEC else None,
            "seeing": SEEING_ARCSEC.get(seeing),
            "transparency_code": transp if transp in TRANSPARENCY_MAG else None,
            "transparency_extinction_mag": TRANSPARENCY_MAG.get(transp),
        }
    return out


async def _seven_timer(loc: Location) -> dict[datetime, dict[str, Any]]:
    payload = await get_json(
        SEVEN_TIMER_URL,
        {"lon": round(loc.longitude, 2), "lat": round(loc.latitude, 2), "ac": 0, "unit": "metric", "output": "json", "tzshift": 0},
        source="7Timer!",
        ttl=3 * 3600,
        timeout=20,
    )
    return _decode_7timer(payload)


def _longest_run(flags: list[bool]) -> tuple[int, int]:
    """(start index, length) of the longest run of True values."""
    best, run_start = (0, 0), None
    for i, flag in enumerate([*flags, False]):
        if flag and run_start is None:
            run_start = i
        elif not flag and run_start is not None:
            if i - run_start > best[1]:
                best = (run_start, i - run_start)
            run_start = None
    return best


async def cloud_cover_by_hour(loc: Location) -> dict[datetime, float]:
    """Total cloud cover (%) for every hour Open-Meteo forecasts, about 16 days ahead."""
    payload = await get_json(
        OPEN_METEO_URL,
        {"latitude": round(loc.latitude, 3), "longitude": round(loc.longitude, 3), "hourly": "cloud_cover",
         "timezone": "UTC", "forecast_days": 16},
        source="Open-Meteo",
        ttl=1800,
    )
    hourly = payload["hourly"]
    return {
        datetime.fromisoformat(stamp).replace(tzinfo=UTC): cloud
        for stamp, cloud in zip(hourly["time"], hourly["cloud_cover"])
        if cloud is not None
    }


async def forecast_night(loc: Location, n: Night, units: str = "metric") -> dict[str, Any]:
    start = (n.sunset or n.window[0]).astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    end = (n.sunrise or n.window[1]).astimezone(UTC)
    params: dict[str, Any] = {
        "latitude": round(loc.latitude, 3),
        "longitude": round(loc.longitude, 3),
        "hourly": "cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,relative_humidity_2m,"
                  "dew_point_2m,temperature_2m,wind_speed_10m,wind_gusts_10m,precipitation_probability,visibility",
        "timezone": "UTC",
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
    }
    if units == "imperial":
        params |= {"temperature_unit": "fahrenheit", "wind_speed_unit": "mph"}
    try:
        payload = await get_json(OPEN_METEO_URL, params, source="Open-Meteo", ttl=1800)
    except UpstreamError as exc:
        if "400" in str(exc):
            raise ValueError("Open-Meteo forecasts only reach about 16 days ahead; pick a nearer date.") from exc
        raise

    try:
        seeing = await _seven_timer(loc)
    except UpstreamError:
        seeing = {}

    hourly = payload["hourly"]
    temp_unit = payload.get("hourly_units", {}).get("temperature_2m", "°C")
    wind_unit = payload.get("hourly_units", {}).get("wind_speed_10m", "km/h")
    dew_margin_warn = 3.6 if units == "imperial" else 2.0
    hours = []
    for i, stamp in enumerate(hourly["time"]):
        t = datetime.fromisoformat(stamp).replace(tzinfo=UTC)
        if not start <= t <= end:
            continue
        row: dict[str, Any] = {
            "time": fmt(t, loc),
            "in_dark_window": n.window[0] - timedelta(minutes=30) <= t <= n.window[1],
            "cloud_total_pct": hourly["cloud_cover"][i],
            "cloud_low_pct": hourly["cloud_cover_low"][i],
            "cloud_mid_pct": hourly["cloud_cover_mid"][i],
            "cloud_high_pct": hourly["cloud_cover_high"][i],
            "humidity_pct": hourly["relative_humidity_2m"][i],
            "temperature": hourly["temperature_2m"][i],
            "dew_point": hourly["dew_point_2m"][i],
            "wind": hourly["wind_speed_10m"][i],
            "gusts": hourly["wind_gusts_10m"][i],
            "precip_probability_pct": hourly["precipitation_probability"][i],
        }
        if seeing:
            nearest = min(seeing, key=lambda s: abs((s - t).total_seconds()))
            if abs((nearest - t).total_seconds()) <= 1.5 * 3600:
                row.update({k: v for k, v in seeing[nearest].items() if v is not None})
        hours.append(row)
    if not hours:
        raise ValueError("No forecast hours overlap that night; it may be too far in the future or past.")

    dark = [h for h in hours if h["in_dark_window"]] or hours
    clouds = [h["cloud_total_pct"] for h in dark if h["cloud_total_pct"] is not None]
    avg_cloud = sum(clouds) / len(clouds) if clouds else None
    run_start, run_len = _longest_run([(h["cloud_total_pct"] or 0) <= 25 for h in dark])
    dew_margins = [h["temperature"] - h["dew_point"] for h in dark if h["temperature"] is not None and h["dew_point"] is not None]
    min_margin = min(dew_margins) if dew_margins else None
    seeing_codes = [h["seeing_code"] for h in dark if h.get("seeing_code")]
    transp_codes = [h["transparency_code"] for h in dark if h.get("transparency_code")]

    # Weather-only score: clear fraction caps it; 7Timer seeing/transparency refine it when available.
    quality = 100.0
    if seeing_codes and transp_codes:
        s = 1 - (sum(seeing_codes) / len(seeing_codes) - 1) / 7
        tr = 1 - (sum(transp_codes) / len(transp_codes) - 1) / 7
        quality = 40 + 30 * s + 30 * tr
    score = round((1 - (avg_cloud or 0) / 100) * quality)
    rating = "excellent" if score >= 80 else "good" if score >= 60 else "fair" if score >= 40 else "poor" if score >= 20 else "clouded out"

    summary: dict[str, Any] = {
        "weather_score": score,
        "rating": rating,
        "average_cloud_pct_dark_hours": round(avg_cloud) if avg_cloud is not None else None,
        "clear_hours_dark_window": sum(1 for c in clouds if c <= 25),
        "longest_clear_stretch": (
            {"start": dark[run_start]["time"], "hours": run_len} if run_len else None
        ),
        "dew_risk": (
            None if min_margin is None
            else "high: plan on a dew heater" if min_margin <= dew_margin_warn
            else "moderate" if min_margin <= 2 * dew_margin_warn else "low"
        ),
        "seeing_note": None if seeing else "Seeing/transparency (7Timer) only cover about 3 days ahead or were unavailable.",
    }
    return {
        "summary": {k: v for k, v in summary.items() if v is not None},
        "units": {"temperature": temp_unit, "wind": wind_unit},
        "hourly": hours,
        "sources": ["Open-Meteo"] + (["7Timer! ASTRO"] if seeing else []),
    }
