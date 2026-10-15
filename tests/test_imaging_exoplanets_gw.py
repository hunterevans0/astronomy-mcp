"""Offline tests for astrophotography math, exoplanet transits and gravitational-wave events."""

import math
from datetime import UTC, datetime, timedelta

import pytest
from mcp import Client

from astronomy_mcp import exoplanets, gravwaves, imaging, mcp, sky

from conftest import MOAB


# ------------------------------------------------------------------ field of view and image scale

def test_sensor_presets_and_custom_sensors():
    cam = imaging.camera("ASI2600", None, None, None)
    assert (cam.width_mm, cam.height_mm, cam.pixel_um) == (pytest.approx(23.49, abs=0.01), pytest.approx(15.70, abs=0.01), 3.76)
    assert imaging.camera(None, 23.5, 15.6, None, 24).pixel_um == pytest.approx(3.91, abs=0.01)
    assert imaging.camera("full_frame", None, None, None).pixel_um is None
    with pytest.raises(ValueError, match="Unknown sensor"):
        imaging.camera("hubble", None, None, None)
    with pytest.raises(ValueError):
        imaging.camera(None, None, None, None)


def test_field_of_view_and_sampling():
    out = imaging.field_of_view(400, 80, imaging.camera("asi2600", None, None, None), 3.0, 25, 68)
    cam = out["camera"]
    assert cam["field_deg"] == {"width": 3.36, "height": 2.25}
    assert cam["image_scale_arcsec_per_pixel"] == pytest.approx(206.265 * 3.76 / 400, abs=0.01)
    assert out["focal_ratio"] == "f/5.0" and cam["sampling"]["verdict"].startswith("well matched")
    assert out["eyepiece"] == {"magnification": 16, "true_field_deg": 4.25, "true_field_arcmin": 255, "exit_pupil_mm": 5.0}
    assert imaging.sampling(0.3, 2.0)["verdict"].startswith("oversampled")
    too_much = imaging.field_of_view(2000, 100, None, 2, 4, None)["eyepiece"]
    assert "useful maximum" in too_much["warning"] and too_much["apparent_field_assumed_deg"] == 52


def test_framing():
    fits = imaging.frame("M31", 177.8, 69.7, 35.0, 201.8, 134.9, 400)
    assert fits["fits"] and fits["fills_percent_of_long_side"] == 88 and "35°" in fits["orientation"]
    big = imaging.frame("M31", 177.8, 69.7, 35.0, 100.9, 67.4, 800)
    assert not big["fits"] and "plan_mosaic" in big["suggestion"]
    tiny = imaging.frame("Jupiter", 0.75, 0.75, None, 201.8, 134.9, 400)
    assert "Barlow" in tiny["suggestion"] and "orientation" not in tiny


def test_mosaic_grid_and_orientation():
    assert [imaging.panels_needed(s, 201.8, 0.15) for s in (150, 201.8, 202, 400)] == [1, 1, 2, 3]
    plan = imaging.mosaic(83.8, 0.0, 400, 100, 0, 201.8, 134.9, 0.15)  # width axis due north
    assert plan["grid"] == "3 columns x 1 rows"
    decs = [p["dec_deg"] for p in plan["panels"]]
    assert decs == [pytest.approx(-171.53 / 60, abs=0.01), 0.0, pytest.approx(171.53 / 60, abs=0.01)]
    east = imaging.mosaic(83.8, 0.0, 400, 100, 90, 201.8, 134.9, 0.15)  # width axis due east
    assert [p["offset_arcmin"]["east"] for p in east["panels"]] == [-171.5, 0.0, 171.5]
    assert east["panels"][2]["ra_deg"] == pytest.approx(83.8 + 171.53 / 60, abs=0.01)
    assert imaging.hms(83.8) == "05h35m12.0s" and imaging.dms(-5.5) == "-05°30'00.0\""


def test_npf_rule():
    # (35 x 2.8 + 30 x 6.0) / 14 = 19.9 s on the celestial equator
    out = imaging.exposure(14, 2.8, imaging.camera("full_frame", None, None, None, 24), None, None, 0)
    assert out["npf_seconds_celestial_equator"] == pytest.approx(19.9, abs=0.1)
    assert out["rule_of_500_seconds"] == pytest.approx(35.7, abs=0.1) and out["crop_factor"] == 1.0
    north = imaging.exposure(24, 1.4, None, 4.3, 1.5, 60)
    assert north["npf_seconds_at_target"] == pytest.approx(2 * north["npf_seconds_celestial_equator"], abs=0.1)
    with pytest.raises(ValueError, match="pixel size"):
        imaging.exposure(24, 2.8, None, None, None, None)


async def test_astrophotography_tools_offline():
    async with Client(mcp) as client:
        fov = (await client.call_tool("calculate_field_of_view", {"focal_length_mm": 480, "multiplier": 0.8, "sensor": "asi533"})).structured_content
        framed = (await client.call_tool("frame_target", {"target": "Jupiter", "focal_length_mm": 1200, "sensor": "asi462"})).structured_content
        missing = await client.call_tool("calculate_field_of_view", {"focal_length_mm": 480})
    assert fov["focal_length_mm"] == 384 and fov["camera"]["field_arcmin"]["width"] == pytest.approx(101.2, abs=0.2)
    assert framed["target"] == "Jupiter" and framed["fits"]
    assert missing.is_error


# ------------------------------------------------------------------ exoplanet transits

PLANET = {"pl_name": "Test b", "hostname": "Test", "ra": 300.0, "dec": 40.0, "sy_vmag": 9.0, "pl_orbper": 3.0,
          "pl_orbpererr1": 1e-5, "pl_tranmid": 2461000.5, "pl_tranmiderr1": 1e-4, "pl_trandur": 2.0,
          "pl_trandep": None, "pl_ratror": 0.1, "pl_rade": None, "st_rad": None}


def test_depth_from_listed_value_or_radius_ratio():
    assert exoplanets.depth_percent({"pl_trandep": 2.4}) == 2.4
    assert exoplanets.depth_percent({"pl_ratror": 0.1}) == pytest.approx(1.0)
    assert exoplanets.depth_percent({"pl_rade": 11.2, "st_rad": 1.0}) == pytest.approx(1.054, abs=0.01)
    assert exoplanets.depth_percent({}) is None


def test_barycentric_correction_direction():
    # Star in the direction of Earth's position from the Sun: light reaches Earth first.
    when = datetime(2026, 10, 15, tzinfo=UTC)
    earth = sky.unit(sky.vec(exoplanets.ae.HelioVector(exoplanets.ae.Body.Earth, sky.to_time(when))))
    ra = math.degrees(math.atan2(earth[1], earth[0])) % 360
    dec = math.degrees(math.asin(earth[2]))
    bjd = exoplanets.julian(when)
    early = (when - exoplanets.bjd_to_utc(bjd, ra, dec)).total_seconds()
    late = (when - exoplanets.bjd_to_utc(bjd, (ra + 180) % 360, -dec)).total_seconds()
    assert early == pytest.approx(499 * 0.9977 + 69.18, abs=5)  # ~one au of light time, plus TDB-UTC
    assert late == pytest.approx(-499 * 0.9977 + 69.18, abs=5)


def test_transit_times_and_uncertainty():
    start = exoplanets.from_julian(PLANET["pl_tranmid"] + 300 * 3.0 - 0.5)
    found = exoplanets.transits_between(PLANET, start, start + timedelta(days=7))
    assert len(found) == 3
    gaps = [(b["mid"] - a["mid"]).total_seconds() / 86400 for a, b in zip(found, found[1:])]
    # Not exactly 3 days: Earth's motion changes the light-time correction by up to ~9 s a day.
    assert gaps == [pytest.approx(3.0, abs=60 / 86400)] * 2
    assert found[0]["uncertainty_min"] == pytest.approx(math.hypot(1e-4, 300 * 1e-5) * 1440, rel=0.01)


def test_transits_tonight_filters_and_reports():
    n = sky.night(MOAB, sky.observing_date("2026-10-15", MOAB))
    mid = n.window[0] + (n.window[1] - n.window[0]) / 2
    # A planet whose transit is centred on mid-night, around a star near the zenith at that time.
    h = sky.horizontal(sky.Target("x", None, 0.0, 0.0), mid, MOAB)
    ra = (h["ra_of_date_deg"] - 0.0) % 360
    probe = {**PLANET, "ra": ra, "dec": MOAB.latitude}
    shift = (mid - exoplanets.bjd_to_utc(exoplanets.julian(mid), probe["ra"], probe["dec"])).total_seconds() / 86400
    probe["pl_tranmid"] = exoplanets.julian(mid) + shift - 500 * probe["pl_orbper"]  # reference 500 orbits ago
    found = exoplanets.transits_tonight([probe], MOAB, n, 0.5, 30, True, 30)
    assert len(found) == 1
    t = found[0]
    assert abs((datetime.fromisoformat(t["mid_transit"]) - mid).total_seconds()) < 90
    assert t["depth_percent"] == 1.0 and t["depth_mmag"] == pytest.approx(10.9, abs=0.1) and t["whole_transit_in_dark"]
    assert exoplanets.transits_tonight([probe], MOAB, n, 2.0, 30, True, 30) == []  # too shallow
    stale = {**probe, "pl_orbpererr1": 1e-3}  # 500 orbits x 1.4 min = 12 h uncertain
    assert exoplanets.transits_tonight([stale], MOAB, n, 0.5, 30, True, 30) == []


def test_shape_planet():
    row = {"pl_name": "HD 189733 b", "hostname": "HD 189733", "pl_rade": 12.666, "pl_trandep": 2.4, "tran_flag": 1,
           "sy_dist": 19.7638, "sy_vmag": 7.67, "st_spectype": "K2 V", "ra": 300.18212, "dec": 22.70978, "pl_bmasse": None}
    shaped = exoplanets.shape_planet(row)
    assert shaped["radius_earth"] == 12.67 and shaped["distance_ly"] == 64.5 and shaped["constellation"] == "Vulpecula"
    assert shaped["transit_depth_percent"] == 2.4 and shaped["star"] == {"spectral_type": "K2 V", "v_magnitude": 7.67}
    assert "mass_earth" not in shaped


# ------------------------------------------------------------------ gravitational waves

def test_gps_to_utc_and_far():
    assert gravwaves.gps_to_utc(1126259462.4).isoformat() == "2015-09-14T09:50:45.400000+00:00"  # GW150914
    assert gravwaves.gps_to_utc(1187008882.4).isoformat() == "2017-08-17T12:41:04.400000+00:00"  # GW170817
    assert gravwaves.far_text(1 / (100 * gravwaves.SECONDS_PER_YEAR)) == "one per 100 years"
    assert gravwaves.far_text(1 / (10 * 86400)) == "one per 10 days"
    assert gravwaves.far_text(None) is None


def test_shape_catalog_event():
    event = {"commonName": "GW170817", "GPS": 1187008882.4, "catalog.shortName": "GWTC-1-confident",
             "mass_1_source": 1.46, "mass_1_source_lower": -0.1, "mass_1_source_upper": 0.12,
             "mass_2_source": 1.27, "mass_2_source_lower": -0.09, "mass_2_source_upper": 0.09,
             "luminosity_distance": 40, "luminosity_distance_lower": -15, "luminosity_distance_upper": 7, "p_astro": 1}
    shaped = gravwaves.shape_event("GW170817-v3", event)
    assert shaped["likely_source"] == "binary neutron star" and shaped["distance_million_ly"] == 130
    assert shaped["mass_1_solar"] == {"value": 1.5, "minus": 0.1, "plus": 0.1}
    bbh = gravwaves.shape_event("x", {**event, "mass_1_source": 36, "mass_2_source": 29})
    assert bbh["likely_source"] == "binary black hole"


async def test_alerts_and_catalog(monkeypatch):
    superevents = [
        {"superevent_id": "S251117dq", "t_0": 1447450731.1, "far": 5.9e-15, "labels": ["ADVOK"],
         "preferred_event_data": {"pipeline": "gstlal", "instruments": "H1,L1", "group": "CBC", "search": "AllSky"}},
        {"superevent_id": "S251110q", "t_0": 1446700000.0, "far": 3e-7, "labels": ["ADVNO"], "preferred_event_data": {}},
    ]

    async def fake_get_json(url, params=None, **kwargs):
        if url.endswith("/superevents/"):
            return {"superevents": superevents}
        if url.endswith("gstlal.p_astro.json"):
            return {"BBH": 0.97, "Terrestrial": 0.03, "BNS": 0, "NSBH": 0}
        if url.endswith("em_bright.json"):
            return {"HasNS": 0.0, "HasRemnant": 0.0}
        raise gravwaves.UpstreamError("404")

    async def fake_catalog():
        return [gravwaves.shape_event("a", {"commonName": "GW1", "GPS": 1.2e9, "luminosity_distance": 400, "mass_1_source": 30, "mass_2_source": 25, "p_astro": 0.99}),
                gravwaves.shape_event("b", {"commonName": "GW2", "GPS": 1.3e9, "luminosity_distance": 40, "mass_1_source": 1.4, "mass_2_source": 1.3, "p_astro": 1.0}),
                gravwaves.shape_event("c", {"commonName": "GW3", "GPS": 1.4e9, "luminosity_distance": 900, "mass_1_source": 9, "mass_2_source": 8, "p_astro": 0.3})]

    monkeypatch.setattr(gravwaves, "get_json", fake_get_json)
    monkeypatch.setattr(gravwaves, "catalog_events", fake_catalog)
    alerts = await gravwaves.recent_alerts(5, include_retracted=False)
    assert [a["id"] for a in alerts["alerts"]] == ["S251117dq"]
    assert alerts["alerts"][0]["most_likely"] == "binary black hole" and alerts["alerts"][0]["classification"]["binary black hole"] == 0.97
    assert "No significant public alert" in alerts["note"]
    with_retracted = await gravwaves.recent_alerts(5, include_retracted=True)
    assert with_retracted["alerts"][1]["retracted"] is True
    by_distance = await gravwaves.confirmed(None, "distance", 5, 0.5)
    assert [e["name"] for e in by_distance["events"]] == ["GW2", "GW1"]  # GW3 is below the probability cut
    assert (await gravwaves.confirmed("gw2", "date", 5, 0.5))["events"][0]["name"] == "GW2"
    with pytest.raises(ValueError, match="no event"):
        await gravwaves.confirmed("GW999999", "date", 5, 0.5)
