"""Offline tests for comet orbits, Horizons parsing, close approaches and fireballs."""

import math
from datetime import UTC, datetime

import pytest

from astronomy_mcp import sky, smallbodies
from astronomy_mcp.http import UpstreamError

from conftest import MOAB

# SBDB elements for C/2025 R2 (SWAN), orbit 28
SWAN = smallbodies.Orbit(
    name="C/2025 R2 (SWAN)", key="C/2025 R2", spkid="1004092", e=0.9941957162943971, q=0.5040845283669433,
    tp=2460931.345960075687, node=335.3260081502438, peri=308.3586347168473, incl=4.472974916612676, m1=13.9, k1=9.5,
)

HORIZONS_RESULT = """\
*******************************************************************************
 Date__(UT)__HR:MN, , , R.A._(ICRF), DEC_(ICRF), dRA*cosD,d(DEC)/dt, Azi_(a-app), Elev_(a-app),    APmag,  S-brt,                r,       rdot,             delta,     deldot,     S-O-T,/r,  Cnst,
*******************************************************************************
$$SOE
 2026-Oct-05 00:00,*, ,   108.28587,   23.27484,  30.12, -2.5,  335.280046,   -24.053272,    8.624,  6.890,   2.670357196991, -1.3334093,  2.57098136357249,-24.0037061,   84.6447,/L,   Gem,
 2026-Oct-05 12:00,A,m,   108.42614,   23.28353,  30.10, -2.4,  119.607574,    64.324561,     n.a.,  6.890,   2.669972263123, -1.3323588,  2.56395191247011,-24.2928832,   85.0137,/T,   Gem,
$$EOE
*******************************************************************************
"""


def test_two_body_orbit_matches_horizons_for_a_long_period_comet():
    # JPL Horizons, geocentric astrometric, 2026-10-05 06:00 UT: RA 76.8887°, Dec +27.813°
    geo, r, delta = smallbodies.geocentric(SWAN, datetime(2026, 10, 5, 6, tzinfo=UTC))
    ra, dec = smallbodies._radec(geo)
    assert sky.separation_deg(ra, dec, 76.8887, 27.813) * 60 < 1.0
    assert r == pytest.approx(5.3473, abs=0.002)


@pytest.mark.parametrize("e", [0.3, 0.9, 0.9999, 1.0, 1.0001, 2.5])
def test_orbit_solutions_keep_perihelion_and_angular_momentum(e):
    q = 1.2
    x0, y0 = smallbodies.orbital_plane_position(e, q, 0.0)
    assert (x0, y0) == (pytest.approx(q), pytest.approx(0.0, abs=1e-12))
    # Kepler's second law: r^2 dnu/dt is constant, sqrt(mu q (1 + e)) with mu = k^2
    h = 1e-3
    for days in (5.0, 40.0, 300.0):
        x1, y1 = smallbodies.orbital_plane_position(e, q, days - h)
        x2, y2 = smallbodies.orbital_plane_position(e, q, days + h)
        nu1, nu2 = math.atan2(y1, x1), math.atan2(y2, x2)
        r2 = ((x1 + x2) / 2) ** 2 + ((y1 + y2) / 2) ** 2
        assert r2 * (nu2 - nu1) / (2 * h) == pytest.approx(smallbodies.GAUSS_K * math.sqrt(q * (1 + e)), rel=1e-4)


def test_near_parabolic_orbits_are_continuous():
    positions = [smallbodies.orbital_plane_position(e, 0.5, 60.0) for e in (0.99999, 1.0, 1.00001)]
    for x, y in positions[1:]:
        assert math.hypot(x - positions[0][0], y - positions[0][1]) < 1e-3


def test_orbit_keys_match_cobs_names():
    assert smallbodies._orbit_key("P", "12P") == "12P"
    assert smallbodies._orbit_key("C", "2025 R2") == "C/2025 R2"
    assert smallbodies._orbit_key("P", "2016 BA14") == "P/2016 BA14"
    assert smallbodies._orbit_key("P", "73P-B") == "73P-B"


def test_cobs_current_magnitude_is_ignored_long_after_perihelion():
    now = datetime(2026, 10, 5, tzinfo=UTC)
    entry = {"id": 53, "current_mag": "10.3", "peak_mag": "7.6", "peak_mag_date": "2026-08-03", "perihelion_date": "2026-08-02 02:47"}
    assert smallbodies.cobs_summary(entry, now)["current_magnitude"] == 10.3
    stale = {**entry, "perihelion_date": "2021-06-17 07:43"}
    assert "current_magnitude" not in smallbodies.cobs_summary(stale, now)
    assert smallbodies.cobs_summary(None, now) is None


def test_nearest_perihelion_rolls_old_elements_forward():
    tp_2015 = smallbodies.julian(datetime(2015, 11, 14, tzinfo=UTC))
    assert smallbodies.nearest_perihelion(tp_2015, 5.36 * 365.25, datetime(2026, 10, 5, tzinfo=UTC))[:7] == "2026-08"
    assert smallbodies.nearest_perihelion(tp_2015, None, datetime(2026, 10, 5, tzinfo=UTC)) == "2015-11-14"


def test_parse_horizons_table():
    rows = smallbodies.parse_horizons(HORIZONS_RESULT)
    assert len(rows) == 2 and rows[0]["APmag"] == "8.624" and rows[1]["/r"] == "/T"
    shaped = smallbodies.shape_row(rows[0], MOAB)
    assert shaped["time"] == "2026-10-04T18:00-06:00"
    assert shaped["magnitude"] == 8.6 and shaped["constellation"] == "Gemini"
    assert shaped["sky"] == "morning" and shaped["direction"] == "NNW" and shaped["altitude_deg"] == -24.1
    assert shaped["motion_arcsec_per_min"] == pytest.approx(math.hypot(30.12, 2.5) / 60, abs=0.01)
    assert "magnitude" not in smallbodies.shape_row(rows[1], None)  # n.a. is dropped


def test_parse_horizons_reports_errors():
    with pytest.raises(UpstreamError, match="No matches found"):
        smallbodies.parse_horizons("Matching small-bodies:\n No matches found.\n")


def test_best_view_prefers_dark_sky_then_twilight():
    times = [datetime(2026, 10, 6, h, tzinfo=UTC) for h in range(1, 6)]
    track = [(30, 250), (40, 260), (20, 270), (5, 280), (-5, 290)]
    dark = smallbodies.best_view(track, times, [-8, -12, -20, -25, -30], MOAB)
    assert dark["sky_at_best"] == "dark sky" and dark["altitude_deg"] == 20
    dusk = smallbodies.best_view(track, times, [-8, -12, -5, -5, -5], MOAB)
    assert dusk["sky_at_best"] == "twilight" and dusk["altitude_deg"] == 40
    assert smallbodies.best_view(track, times, [5] * 5, MOAB)["visible"] is False


def test_close_approach_shaping():
    row = {"des": "2026 TC2", "cd": "2026-Oct-07 06:07", "dist": "0.00707", "v_rel": "21.63", "h": "25.884",
           "diameter": None, "fullname": "       (2026 TC2)", "t_sigma_f": "< 00:01"}
    shaped = smallbodies.shape_approach(row, MOAB)
    assert shaped["name"] == "2026 TC2" and shaped["time_local"] == "2026-10-07T00:07-06:00"
    assert shaped["distance_lunar"] == pytest.approx(2.75, abs=0.01) and shaped["estimated_diameter_m"] == "18-40"
    lo, hi = smallbodies.diameter_range_m(22.0)
    assert 100 < lo < 120 and 230 < hi < 250


def test_fireball_signs_and_sightline():
    row = {"date": "2026-08-14 07:48:36", "energy": "3.8", "impact-e": "0.13", "lat": "47.7", "lat-dir": "N",
           "lon": "119.4", "lon-dir": "W", "alt": "30.0", "vel": "12.2"}
    shaped = smallbodies.shape_fireball(row, MOAB)
    assert shaped["latitude"] == 47.7 and shaped["longitude"] == -119.4
    assert shaped["radiated_energy_joules"] == 3.8e10
    assert shaped["distance_from_you_km"] == pytest.approx(1290, abs=10) and shaped["above_your_horizon"] is False
    assert smallbodies.elevation_seen_from(0.001, 30) == pytest.approx(90, abs=0.1)
    assert smallbodies.elevation_seen_from(300, 30) > 0 > smallbodies.elevation_seen_from(700, 30)


# ------------------------------------------------------------------ bright asteroids and COBS observations

CERES_ROW = dict(zip(
    ["full_name", "pdes", "spkid", "e", "a", "i", "om", "w", "ma", "epoch", "H", "G"],
    ["     1 Ceres (A801 AA)", "1", 20000001, ".07969229514816586", "2.765552595034094", "10.58802780183462",
     "80.24862682043221", "73.29421453021587", "274.4193463761342", "2461200.5", "3.34", "0.12"],
))


def test_asteroid_elements_and_magnitude_match_horizons():
    # JPL Horizons, 2026-10-05 00:00 UT: RA 108.28587°, Dec +23.27484°, r 2.67036, delta 2.57098, APmag 8.624
    ceres = smallbodies._asteroid_from_row(CERES_ROW)
    assert ceres.h == 3.34 and ceres.g == 0.12 and ceres.name == "1 Ceres (A801 AA)"
    when = datetime(2026, 10, 5, tzinfo=UTC)
    geo, r, delta = smallbodies.geocentric(ceres, when)
    ra, dec = smallbodies._radec(geo)
    assert sky.separation_deg(ra, dec, 108.28587, 23.27484) * 3600 < 30
    assert (r, delta) == (pytest.approx(2.67036, abs=1e-4), pytest.approx(2.57098, abs=1e-4))
    earth = smallbodies.earth_heliocentric(when)
    helio = tuple(geo[k] + earth[k] for k in range(3))
    assert ceres.predicted_magnitude(r, delta, smallbodies.phase_angle(helio, geo)) == pytest.approx(8.62, abs=0.05)


def test_hg_magnitude_phase_behaviour():
    at_opposition = smallbodies.hg_magnitude(5.0, 0.15, 2.0, 1.0, 0.0)
    assert at_opposition == pytest.approx(5.0 + 5 * math.log10(2.0))
    assert smallbodies.hg_magnitude(5.0, 0.15, 2.0, 1.0, 20.0) > at_opposition + 0.5


async def test_recent_cobs_observations(monkeypatch):
    seen = {}

    async def fake_get_json(url, params=None, **kwargs):
        seen.update(params)
        today = datetime.now(UTC)
        return {"info": {"recordsTotal": 3}, "objects": [
            {"obs_date": f"{today:%Y-%m-%d} 03:55:00", "magnitude": "10.1", "obs_method": {"name": "Visual"},
             "observer": {"first_name": "Mary", "last_name": "Olason", "country": "United States"},
             "instrument_aperture": "9.1", "coma_diameter": "7.00", "tail_length": None},
            {"obs_date": f"{today:%Y-%m-%d} 01:00:00", "magnitude": "10.5", "observer": {}},
            {"obs_date": "2001-01-01 00:00:00", "magnitude": "9.0"},
        ]}

    monkeypatch.setattr(smallbodies, "get_json", fake_get_json)
    recent = await smallbodies.recent_observations("10P", count=2)
    assert seen["des"] == "10P" and seen["format"] == "json"
    assert recent["count_last_30_days"] == 3 and recent["median_magnitude_last_7_days"] == 10.3
    assert recent["latest"][0] == {"date_utc": recent["latest"][0]["date_utc"], "magnitude": 10.1, "method": "Visual",
                                   "aperture_cm": 9.1, "coma_arcmin": 7.0, "observer": "M. Olason (United States)"}
    assert len(recent["latest"]) == 2
