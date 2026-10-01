"""What is dimming the sky: smoke, dust and other aerosols over a night.

From Open-Meteo's air-quality API (CAMS global model, roughly 40 km grid, about
5 days ahead). Aerosol optical depth is a column value and maps directly onto
extinction; the particle concentrations are near the ground and only hint at
which kind of aerosol is responsible, so the named driver is a heuristic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from astronomy_mcp.http import UpstreamError, get_json
from astronomy_mcp.location import Location
from astronomy_mcp.sky import Night, fmt

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Aerosol optical depth at 550 nm below which the night earns each rating.
RATINGS = ((0.08, "excellent"), (0.15, "good"), (0.30, "average"), (0.50, "poor"))
MAG_PER_AOD = 1.086  # extinction in magnitudes per unit optical depth (2.5 / ln 10)
CLEAN_AOD = 0.15  # below this nothing is worth blaming
DUSTY_UG_M3 = 20.0
SMOKY_PM2_5_UG_M3 = 20.0

DRIVER_NOTES = {
    "none": "Aerosols are low; they are not limiting transparency.",
    "dust": "Mineral dust near the ground accounts for most of the coarse particles.",
    "smoke or fine-particle pollution": "Fine particles (PM2.5) are elevated near the ground: wildfire smoke or urban haze. "
                                        "The model cannot tell the two apart.",
    "aerosols aloft": "The column is hazy but surface air is clean, so the layer is overhead: often smoke or dust "
                      "carried in from far away.",
}


def rate(aod: float) -> str:
    return next((label for limit, label in RATINGS if aod < limit), "very poor")


def main_driver(aod: float, dust: float | None, pm2_5: float | None, pm10: float | None) -> str:
    if aod < CLEAN_AOD:
        return "none"
    if dust is not None and dust >= DUSTY_UG_M3 and dust >= 0.5 * (pm10 or dust):
        return "dust"
    if pm2_5 is not None and pm2_5 >= SMOKY_PM2_5_UG_M3:
        return "smoke or fine-particle pollution"
    return "aerosols aloft"


def _mean(values: list[float | None]) -> float | None:
    known = [v for v in values if v is not None]
    return sum(known) / len(known) if known else None


async def transparency_night(loc: Location, n: Night) -> dict[str, Any]:
    start = (n.sunset or n.window[0]).astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    end = (n.sunrise or n.window[1]).astimezone(UTC)
    params = {
        "latitude": round(loc.latitude, 3),
        "longitude": round(loc.longitude, 3),
        "hourly": "aerosol_optical_depth,dust,pm2_5,pm10",
        "timezone": "UTC",
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
    }
    too_far = "Aerosol forecasts only reach about 5 days ahead; pick a nearer date."
    try:
        payload = await get_json(AIR_QUALITY_URL, params, source="Open-Meteo Air Quality", ttl=3600)
    except UpstreamError as exc:
        if "400" in str(exc):
            raise ValueError(too_far) from exc
        raise

    hourly = payload["hourly"]
    hours = []
    for i, stamp in enumerate(hourly["time"]):
        t = datetime.fromisoformat(stamp).replace(tzinfo=UTC)
        if not start <= t <= end or hourly["aerosol_optical_depth"][i] is None:
            continue
        hours.append({
            "time": fmt(t, loc),
            "in_dark_window": n.window[0] - timedelta(minutes=30) <= t <= n.window[1],
            "aerosol_optical_depth": hourly["aerosol_optical_depth"][i],
            "dust_ug_m3": hourly["dust"][i],
            "pm2_5_ug_m3": hourly["pm2_5"][i],
            "pm10_ug_m3": hourly["pm10"][i],
        })
    if not hours:
        raise ValueError(too_far)

    dark = [h for h in hours if h["in_dark_window"]] or hours
    aod = _mean([h["aerosol_optical_depth"] for h in dark])
    dust, pm2_5, pm10 = (_mean([h[k] for h in dark]) for k in ("dust_ug_m3", "pm2_5_ug_m3", "pm10_ug_m3"))
    driver = main_driver(aod, dust, pm2_5, pm10)
    summary = {
        "transparency": rate(aod),
        "main_driver": driver,
        "explanation": DRIVER_NOTES[driver],
        "aerosol_optical_depth_mean": round(aod, 2),
        "aerosol_optical_depth_peak": max(h["aerosol_optical_depth"] for h in dark),
        "aerosol_extinction_zenith_mag": round(MAG_PER_AOD * aod, 2),
        "aerosol_extinction_at_30deg_altitude_mag": round(2 * MAG_PER_AOD * aod, 2),
        "dust_ug_m3": round(dust, 1) if dust is not None else None,
        "pm2_5_ug_m3": round(pm2_5, 1) if pm2_5 is not None else None,
        "pm10_ug_m3": round(pm10, 1) if pm10 is not None else None,
    }
    return {
        "summary": {k: v for k, v in summary.items() if v is not None},
        "hourly": hours,
        "note": "Modelled aerosols on a ~40 km grid. Extinction is the aerosol part only, on top of about "
                "0.13 mag per airmass from clean air; clouds and humidity are in get_sky_forecast.",
        "source": "Open-Meteo Air Quality (CAMS global)",
    }
