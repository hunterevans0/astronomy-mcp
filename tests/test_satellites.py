"""Offline tests for satellite propagation, passes and Starlink trains.

Reference values come from Skyfield 1.49 for the same element set.
"""

import math
from datetime import UTC, datetime

import astronomy as ae
import pytest
from mcp import Client

from astronomy_mcp import mcp, satellites, sky
from astronomy_mcp.location import Location

from conftest import MOAB

ISS = {
    "OBJECT_NAME": "ISS (ZARYA)", "OBJECT_ID": "1998-067A", "EPOCH": "2026-10-05T11:57:27.650880",
    "MEAN_MOTION": 15.48742155, "ECCENTRICITY": 0.00068774, "INCLINATION": 51.6314, "RA_OF_ASC_NODE": 114.1795,
    "ARG_OF_PERICENTER": 225.7345, "MEAN_ANOMALY": 134.3079, "EPHEMERIS_TYPE": 0, "CLASSIFICATION_TYPE": "U",
    "NORAD_CAT_ID": 25544, "ELEMENT_SET_NO": 999, "REV_AT_EPOCH": 58885, "BSTAR": 0.00010195541,
    "MEAN_MOTION_DOT": 5.123e-5, "MEAN_MOTION_DDOT": 0,
}


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


@pytest.fixture
def iss():
    return satellites.satellite_from_omm(ISS)


def test_satellite_from_omm(iss):
    assert iss.norad_id == 25544 and iss.standard_magnitude == -1.8
    assert 400 < iss.altitude_km < 430
    assert iss.period_min == pytest.approx(92.98, abs=0.05)


def test_look_matches_skyfield(iss):
    # Skyfield at 16:50:37 UTC (near culmination): altitude 54.9645°, azimuth 324.3354°, range 514.07 km;
    # at 16:52:00: 30.2237°, 28.6011°, 782.96 km
    obs = satellites.Observer(MOAB)
    look = obs.look(iss, utc(2026, 10, 5, 16, 50, 37))
    assert look.altitude == pytest.approx(54.9645, abs=0.02)
    assert look.azimuth == pytest.approx(324.3354, abs=0.03)
    assert look.range_km == pytest.approx(514.07, abs=0.5)
    assert look.sunlit and look.sun_altitude > 0 and not look.visible  # mid-morning in Moab
    later = obs.look(iss, utc(2026, 10, 5, 16, 52))
    assert (later.altitude, later.azimuth) == (pytest.approx(30.2237, abs=0.02), pytest.approx(28.6011, abs=0.03))


def test_rise_times_match_skyfield(iss):
    skyfield_rises = [utc(2026, 10, 5, 15, 12, 9), utc(2026, 10, 5, 16, 47, 17), utc(2026, 10, 5, 18, 26, 15),
                      utc(2026, 10, 5, 21, 41, 34), utc(2026, 10, 5, 23, 17, 49)]
    found = satellites.passes(iss, MOAB, utc(2026, 10, 5, 12), 0.5, 10, include_daylight=True)
    rises = [datetime.fromisoformat(p["rise"]["time"]) for p in found]
    assert len(rises) == len(skyfield_rises)
    for mine, ref in zip(rises, skyfield_rises):
        assert abs((mine - ref).total_seconds()) < 3
    assert all(p["visible"] is False and p["reason"] == "daylight or twilight" for p in found)
    high = found[1]
    assert high["max_altitude_deg"] == 55 and high["highest"]["direction"] == "NW"


def test_visible_passes_need_a_dark_sky(iss):
    found = satellites.passes(iss, MOAB, utc(2026, 10, 5, 12), 10, 10, include_daylight=False)
    assert len(found) >= 2  # morning passes from 12 October
    for p in found:
        start = datetime.fromisoformat(p["visible_from"]["time"])
        assert geometric_sun_altitude(start) < -5.95
        assert p["visible_minutes"] > 0 and p["brightest_magnitude"] < 1


def test_dark_windows_are_after_civil_dusk():
    # 12:00 UTC is 06:00 in Moab, before dawn, so the first window is the end of the night.
    windows = satellites.dark_windows(MOAB, utc(2026, 10, 5, 12), utc(2026, 10, 8, 12))
    assert len(windows) == 4 and windows[0][0] == utc(2026, 10, 5, 12) and windows[-1][1] == utc(2026, 10, 8, 12)
    for a, b in windows[1:]:
        assert sky.sun_altitude(a + (b - a) / 2, MOAB) < -30
        assert geometric_sun_altitude(a) == pytest.approx(-6, abs=0.05)


def geometric_sun_altitude(when: datetime) -> float:
    t, obs = sky.to_time(when), sky.observer(MOAB)
    eq = ae.Equator(ae.Body.Sun, t, obs, True, True)
    return ae.Horizon(t, obs, eq.ra, eq.dec, ae.Refraction.Airless).altitude


def test_magnitude_convention():
    assert satellites.magnitude(-1.8, 1000, 90) == pytest.approx(-1.8)
    assert satellites.magnitude(-1.8, 400, 90) == pytest.approx(-1.8 + 5 * math.log10(0.4))
    assert satellites.magnitude(-1.8, 1000, 30) < satellites.magnitude(-1.8, 1000, 120)
    assert satellites.magnitude(None, 1000, 90) is None


def test_earth_shadow():
    sun = (1.0, 0.0, 0.0)
    assert satellites.in_sunlight((7000.0, 0.0, 0.0), sun)
    assert not satellites.in_sunlight((-7000.0, 0.0, 0.0), sun)  # directly behind Earth
    assert satellites.in_sunlight((-7000.0, 6500.0, 0.0), sun)  # behind, but outside the shadow cylinder


def test_satellite_straight_overhead(iss):
    when = utc(2026, 10, 5, 13)
    jd, fr = satellites._julian(when)
    _, r, _ = iss.rec.sgp4(jd, fr)
    x, y, z = satellites._rotate_z(r, satellites.gstime(jd + fr))
    lat = math.degrees(math.atan2(z, math.hypot(x, y) * (1 - satellites.WGS84_E2)))
    below = Location(lat, math.degrees(math.atan2(y, x)), 0.0)
    assert satellites.Observer(below).altitude(iss, when) > 89.5


def test_overhead_lists_only_satellites_above_the_limit(iss):
    when = utc(2026, 10, 5, 16, 50, 37)
    found = satellites.overhead([iss], MOAB, when, 10, visible_only=False)
    assert found[0]["name"] == "ISS (ZARYA)" and found[0]["altitude_deg"] == 55
    assert found[0]["leaves_view"] == "sets" and found[0]["heading_toward"] in ("NE", "ENE")
    assert satellites.overhead([iss], MOAB, when, 60, visible_only=False) == []
    assert satellites.overhead([iss], MOAB, when, 10, visible_only=True) == []  # daytime


def test_train_spread_and_launch_date():
    batch = []
    for k, anomaly in enumerate((136.3079, 134.3079, 132.3079)):
        batch.append(satellites.satellite_from_omm(
            {**ISS, "NORAD_CAT_ID": 90000 + k, "OBJECT_NAME": f"STARLINK-{k}", "MEAN_ANOMALY": anomaly, "REV_AT_EPOCH": 31 + k}))
    rep, lead, trail = satellites.train_spread(batch, utc(2026, 10, 5, 13))
    assert rep.name == "STARLINK-1"
    assert lead == pytest.approx(2.0, abs=0.1) and trail == pytest.approx(-2.0, abs=0.1)
    assert satellites.launch_date(batch).date().isoformat() == "2026-10-03"
    assert batch[0].standard_magnitude == satellites.STARLINK_STANDARD_MAGNITUDE


async def test_find_satellite_resolves_aliases_and_ambiguity(monkeypatch):
    calls = []

    async def fake(params, cache_name):
        calls.append(params)
        if params.get("CATNR") == "25544":
            return [ISS]
        if params.get("NAME") == "NOAA":
            return [{**ISS, "OBJECT_NAME": "NOAA 15", "NORAD_CAT_ID": 25338},
                    {**ISS, "OBJECT_NAME": "NOAA 19", "NORAD_CAT_ID": 33591}]
        return []

    monkeypatch.setattr(satellites, "_celestrak", fake)
    assert (await satellites.find_satellite("ISS")).norad_id == 25544
    assert (await satellites.find_satellite(" 25544 ")).norad_id == 25544
    with pytest.raises(ValueError, match="NOAA 19 \\(33591\\)"):
        await satellites.find_satellite("NOAA")
    with pytest.raises(ValueError, match="no satellite named"):
        await satellites.find_satellite("nothing like this")
    async with Client(mcp) as client:
        result = await client.call_tool("get_satellite_passes", {"satellite": "NOAA", "latitude": 38.5733, "longitude": -109.5498})
    assert result.is_error and "Pass the NORAD number" in result.content[0].text


def test_rough_magnitudes_from_radar_cross_section():
    # ISS (399 m²) is about -1.8 and Hubble (28 m²) about +2; the estimate is good to ~1.5 mag.
    assert satellites.magnitude_from_rcs(399.05) == pytest.approx(-1.8, abs=1.0)
    assert satellites.magnitude_from_rcs(28.08) == pytest.approx(2.0, abs=1.5)
    debris = {**ISS, "NORAD_CAT_ID": 12345, "OBJECT_NAME": "SL-16 R/B"}
    sat = satellites.satellite_from_omm(debris, rcs={12345: 11.34})
    assert sat.standard_magnitude == pytest.approx(2.36, abs=0.01) and sat.magnitude_basis.startswith("rough")
    assert satellites.satellite_from_omm(debris).standard_magnitude is None
    assert satellites.satellite_from_omm(ISS, rcs={25544: 1.0}).magnitude_basis.startswith("built-in")
    assert satellites.satellite_from_omm(ISS, 0.5).magnitude_basis == "given by user"


async def test_unnamed_starlink_batches_are_matched_to_launches(monkeypatch):
    unnamed = [{**ISS, "OBJECT_NAME": f"2026-230{c}", "OBJECT_ID": f"2026-230{c}", "NORAD_CAT_ID": 99000 + k,
                "MEAN_ANOMALY": 134.3 + k * 0.2} for k, c in enumerate("ABCD")]
    other = [{**ISS, "OBJECT_NAME": "QIANFAN-1", "OBJECT_ID": f"2026-231{c}", "NORAD_CAT_ID": 99100 + k}
             for k, c in enumerate("ABCD")]

    async def fake_celestrak(params, cache_name):
        return unnamed + other

    async def fake_launches():
        return {"2026-230": ("Falcon 9 Block 5 | Starlink Group 10-9", utc(2026, 10, 4, 12, 30))}, None

    monkeypatch.setattr(satellites, "_celestrak", fake_celestrak)
    monkeypatch.setattr(satellites, "starlink_launches", fake_launches)
    monkeypatch.setattr(satellites, "datetime", type("FrozenDatetime", (datetime,), {"now": staticmethod(lambda tz=None: utc(2026, 10, 5, 13))}))
    report = await satellites.starlink_trains(MOAB, utc(2026, 10, 5, 13), 1, 21, 10)
    assert report["count"] == 1
    train = report["trains"][0]
    assert train["launch"] == "2026-230" and train["mission"].endswith("Group 10-9")
    assert train["launched"] == "2026-10-04T12:30+00:00" and train["unnamed_in_catalog"] == 4
    assert train["satellites"] == 4 and train["state"] == "tight train"


def test_centerline_point_geometry():
    # Satellite 400 km straight above a point on the x axis, body far beyond it on the same line.
    sat = (6771.0, 0.0, 0.0)
    assert satellites.centerline_point(sat, (1e9, 0.0, 0.0), 6371.0) == pytest.approx((6371.0, 0.0, 0.0))
    # Body behind the Earth from the satellite: no point sees it in front.
    assert satellites.centerline_point(sat, (-1e9, 0.0, 0.0), 6371.0) is None


def test_transit_centerline_is_where_the_transit_is_seen(iss):
    found = satellites.find_transits(iss, MOAB, utc(2026, 10, 6, 15), 0.25, 200, ("Moon",), 10)
    assert len(found) == 1
    event = found[0]
    assert event["time"].startswith("2026-10-06T10:03:06")
    line = event["centerline_nearest_you"]
    assert 100 < line["distance_km"] < 130 and line["direction"] == "NW"
    assert event["from_your_location"]["transits"] is False and event["crossing_seconds_on_centerline"] > 0.3
    # Standing on the centerline, the same pass crosses the Moon.
    there = Location(line["latitude"], line["longitude"], MOAB.elevation_m, MOAB.timezone)
    again = satellites.find_transits(iss, there, utc(2026, 10, 6, 15), 0.25, 20, ("Moon",), 10)
    assert again[0]["centerline_nearest_you"]["distance_km"] < 1
    here = again[0]["from_your_location"]
    assert here["transits"] is True and here["closest_approach_arcmin"] < 2 and 0.3 < here["crossing_seconds"] < 1.5
    assert 3 < again[0]["path_width_km"] < 8
