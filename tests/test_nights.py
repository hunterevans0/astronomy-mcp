"""Offline tests for comparing nights, dark-moon weekends and aerosol transparency."""

from datetime import UTC, date, datetime, timedelta

import pytest

from astronomy_mcp import airquality, conditions, planner, sky
from astronomy_mcp.location import Location
from astronomy_mcp.sky import Target

from conftest import MOAB

M31 = Target("M31", ra_deg=10.6848, dec_deg=41.2691)
SATURN = Target("Saturn", sky.BODIES["saturn"])
NEW_MOON_NIGHT = date(2026, 10, 10)  # new moon 2026-10-10 15:50 UTC
FULL_MOON_NIGHT = date(2026, 10, 25)  # full moon 2026-10-26 04:12 UTC


def _all_hours(first: date, days: int, cloud: float) -> dict[datetime, float]:
    start = datetime(first.year, first.month, first.day, tzinfo=UTC)
    return {start + timedelta(hours=h): cloud for h in range(24 * days)}


# ------------------------------------------------------------------ scoring nights

def test_moon_free_hours():
    new = sky.night(MOAB, NEW_MOON_NIGHT)
    full = sky.night(MOAB, FULL_MOON_NIGHT)
    assert planner.moon_free_hours(MOAB, new) == pytest.approx(new.to_dict(MOAB)["dark_window"]["hours"], abs=0.1)
    assert planner.moon_free_hours(MOAB, full) < 1


def test_moonlight_lowers_a_deep_sky_night_but_not_a_planet():
    dark = planner.score_night(M31, MOAB, sky.night(MOAB, NEW_MOON_NIGHT), 21.6, 25, None)
    bright = planner.score_night(M31, MOAB, sky.night(MOAB, FULL_MOON_NIGHT), 21.6, 25, None)
    assert dark["score"] > 95 and dark["moon_sky_brightening_mag"] == 0
    assert bright["score"] < 25 and bright["moon_sky_brightening_mag"] > 2
    assert dark["peak_altitude_deg"] == pytest.approx(90 - (41.27 - MOAB.latitude), abs=1)
    assert "cloud_pct" not in dark  # no forecast given

    saturn_dark = planner.score_night(SATURN, MOAB, sky.night(MOAB, NEW_MOON_NIGHT), 21.6, 25, None)
    saturn_bright = planner.score_night(SATURN, MOAB, sky.night(MOAB, FULL_MOON_NIGHT), 21.6, 25, None)
    assert "moon_sky_brightening_mag" not in saturn_bright
    assert saturn_bright["score"] == pytest.approx(saturn_dark["score"], abs=3)


def test_moonlight_matters_less_under_a_bright_sky():
    n = sky.night(MOAB, FULL_MOON_NIGHT)
    assert planner.score_night(None, MOAB, n, 18.0, 25, None)["score"] > planner.score_night(None, MOAB, n, 21.6, 25, None)["score"]


def test_clouds_scale_the_score_and_missing_forecast_is_flagged():
    n = sky.night(MOAB, NEW_MOON_NIGHT)
    clear = planner.score_night(None, MOAB, n, 21.6, 25, _all_hours(NEW_MOON_NIGHT, 2, 0))
    half = planner.score_night(None, MOAB, n, 21.6, 25, _all_hours(NEW_MOON_NIGHT, 2, 50))
    assert clear["cloud_pct"] == 0 and half["cloud_pct"] == 50
    assert half["score"] == pytest.approx(clear["score"] / 2, abs=1)
    # A forecast that stops partway through the night doesn't count
    partial = planner.score_night(None, MOAB, n, 21.6, 25, _all_hours(NEW_MOON_NIGHT, 1, 100))
    assert "cloud_pct" not in partial and partial["score"] == clear["score"]


def test_target_that_never_rises_and_midnight_sun():
    omega_cen = Target("Omega Centauri", ra_deg=201.697, dec_deg=-47.479)
    row = planner.score_night(omega_cen, MOAB, sky.night(MOAB, NEW_MOON_NIGHT), 21.6, 25, None)
    assert row["score"] == 0 and "never above 25°" in row["reason"]
    tromso = Location(69.65, 18.96, 0, "Europe/Oslo")
    assert planner.score_night(None, tromso, sky.night(tromso, date(2026, 6, 21)), 21.6, 25, None)["reason"].startswith("no darkness")


def test_best_nights_ranks_forecast_and_later_nights_separately():
    first = date(2026, 10, 8)
    # The forecast covers three nights; the night of the 10th (the 11th in UTC) is overcast
    clouds = _all_hours(first, 4, 0) | _all_hours(date(2026, 10, 11), 1, 100)
    result = planner.best_nights(M31, MOAB, first, 20, 21.6, 25, clouds)
    assert result["period"] == {"from": "2026-10-08", "to": "2026-10-27"}
    assert result["cloud_forecast_through"] == "2026-10-10"
    assert sorted(r["date"] for r in result["best_nights_with_forecast"]) == ["2026-10-08", "2026-10-09"]
    later = result["best_nights_beyond_forecast"]
    assert len(later) == 5 and all("cloud_pct" not in r for r in later)
    assert [r["score"] for r in later] == sorted((r["score"] for r in later), reverse=True)
    assert FULL_MOON_NIGHT.isoformat() not in [r["date"] for r in later]
    assert len(result["nights"]) == 20 and "moonlight" in result["scoring"]


def test_best_nights_explains_an_impossible_target():
    result = planner.best_nights(Target("x", ra_deg=200.0, dec_deg=-80.0), MOAB, NEW_MOON_NIGHT, 3, 21.6, 25, None)
    assert result["best_nights_with_forecast"] == [] and "never above" in result["message"]


# ------------------------------------------------------------------ dark-moon weekends

def test_dark_moon_weekends_bracket_each_new_moon():
    result = planner.dark_moon_weekends(MOAB, date(2026, 10, 1), 91, min_moon_free_pct=90)
    assert [w["friday"] for w in result["weekends"]] == ["2026-10-09", "2026-11-06", "2026-12-04"]
    first = result["weekends"][0]
    assert first["saturday"] == "2026-10-10" and first["rating"] == "excellent"
    assert first["new_moon"].startswith("2026-10-10T09:50-06:00")
    assert abs(first["days_from_new_moon"]) < 1
    assert first["nights"][0]["moon_free_dark_hours"] == first["nights"][0]["dark_hours"]
    # A looser threshold also admits the first-quarter weekends, when the Moon sets around midnight
    loose = planner.dark_moon_weekends(MOAB, date(2026, 10, 1), 91, min_moon_free_pct=70)
    assert {w["friday"] for w in result["weekends"]} < {w["friday"] for w in loose["weekends"]}
    assert all(date.fromisoformat(w["friday"]).weekday() == 4 for w in loose["weekends"])


def test_dark_moon_weekends_start_day_handling():
    # Starting on a Saturday keeps that weekend; starting on a Sunday moves to the next one
    saturday = planner.dark_moon_weekends(MOAB, date(2026, 10, 10), 6)
    assert [w["friday"] for w in saturday["weekends"]] == ["2026-10-09"]
    assert planner.dark_moon_weekends(MOAB, date(2026, 10, 11), 5)["weekends"] == []


def test_dark_moon_weekends_without_location_use_illumination():
    result = planner.dark_moon_weekends(None, date(2026, 10, 1), 91)
    assert "2026-10-09" in [w["friday"] for w in result["weekends"]]
    assert "no location" in result["criterion"]
    for w in result["weekends"]:
        assert "moon_free_dark_pct" not in w
        assert all(n["illuminated_percent"] <= planner.MAX_ILLUMINATION_PCT for n in w["nights"])


def test_dark_moon_weekends_skip_midnight_sun():
    tromso = Location(69.65, 18.96, 0, "Europe/Oslo")
    result = planner.dark_moon_weekends(tromso, date(2026, 6, 1), 30)
    assert result["weekends"] == [] and result["weekends_without_darkness"] >= 1


# ------------------------------------------------------------------ transparency

@pytest.mark.parametrize(
    "aod, label",
    [(0.03, "excellent"), (0.1, "good"), (0.2, "average"), (0.4, "poor"), (1.5, "very poor")],
)
def test_transparency_rating(aod, label):
    assert airquality.rate(aod) == label


def test_main_driver():
    assert airquality.main_driver(0.05, 50, 50, 80) == "none"  # clean column: nothing to blame
    assert airquality.main_driver(0.6, 80, 15, 110) == "dust"
    assert airquality.main_driver(0.6, 2, 60, 70).startswith("smoke")
    assert airquality.main_driver(0.6, 1, 4, 6) == "aerosols aloft"
    assert airquality.main_driver(0.6, None, None, None) == "aerosols aloft"
    assert set(airquality.DRIVER_NOTES) == {"none", "dust", "smoke or fine-particle pollution", "aerosols aloft"}


async def test_transparency_night_summarises_dark_hours(monkeypatch):
    n = sky.night(MOAB, NEW_MOON_NIGHT)
    start = datetime(2026, 10, 10, tzinfo=UTC)
    stamps = [start + timedelta(hours=h) for h in range(48)]

    async def fake_get_json(url, params, **kwargs):
        assert params["start_date"] == "2026-10-11" and params["end_date"] == "2026-10-11"  # the night in UTC
        return {"hourly": {
            "time": [t.strftime("%Y-%m-%dT%H:%M") for t in stamps],
            # smoky all night, with the last hours missing as the forecast runs out
            "aerosol_optical_depth": [0.5 if t < n.window[1] - timedelta(hours=2) else None for t in stamps],
            "dust": [1.0] * 48, "pm2_5": [45.0] * 48, "pm10": [50.0] * 48,
        }}

    monkeypatch.setattr(airquality, "get_json", fake_get_json)
    result = await airquality.transparency_night(MOAB, n)
    summary = result["summary"]
    assert summary["transparency"] == "very poor" and summary["main_driver"].startswith("smoke")
    assert summary["aerosol_extinction_zenith_mag"] == pytest.approx(0.54, abs=0.01)
    assert summary["pm2_5_ug_m3"] == 45.0
    assert result["hourly"][0]["time"].startswith("2026-10-10T18:00-06:00")
    assert not result["hourly"][0]["in_dark_window"] and result["hourly"][-1]["in_dark_window"]
    assert all(h["aerosol_optical_depth"] is not None for h in result["hourly"])


async def test_transparency_night_beyond_forecast(monkeypatch):
    async def no_data(url, params, **kwargs):
        raise airquality.UpstreamError("Open-Meteo Air Quality returned HTTP 400: out of allowed range")

    monkeypatch.setattr(airquality, "get_json", no_data)
    with pytest.raises(ValueError, match="5 days"):
        await airquality.transparency_night(MOAB, sky.night(MOAB, NEW_MOON_NIGHT))


async def test_cloud_cover_by_hour_drops_missing_hours(monkeypatch):
    async def fake_get_json(url, params, **kwargs):
        assert params["forecast_days"] == 16
        return {"hourly": {"time": ["2026-10-10T00:00", "2026-10-10T01:00"], "cloud_cover": [40, None]}}

    monkeypatch.setattr(conditions, "get_json", fake_get_json)
    assert await conditions.cloud_cover_by_hour(MOAB) == {datetime(2026, 10, 10, tzinfo=UTC): 40}
