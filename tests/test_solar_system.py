"""Offline tests for Jupiter's moons, the Moon's libration and terminator, conjunctions and oppositions."""

import math
import struct
from datetime import UTC, datetime, timedelta

import astronomy as ae
import pytest

from astronomy_mcp import almanac, jupiter, lunar, sky

from conftest import MOAB


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


# ------------------------------------------------------------------ Jupiter

def test_central_meridians_match_meeus():
    # Astronomical Algorithms example 43.a: 1992 Dec 16 0h UT, System I 268.06°, System II 72.74°
    snap = jupiter.snapshot(utc(1992, 12, 16))
    assert snap.cm_system_i == pytest.approx(268.06, abs=1.0)
    assert snap.cm_system_ii == pytest.approx(72.74, abs=1.0)


def test_triple_shadow_transit_of_january_2015():
    # Published times (UT, 24 Jan 2015): Callisto's shadow on at 3:11, Io's at 4:35, Europa's at 6:27;
    # Io's off at 6:52, leaving three shadows on the disk for 25 minutes.
    events, under_way = jupiter.find_events(utc(2015, 1, 24, 3), utc(2015, 1, 24, 7))
    assert under_way == []
    times = {(e["moon"], e["event"]): e["time"] for e in events if "moon" in e}
    for key, expected in {
        ("Callisto", "shadow transit begins"): utc(2015, 1, 24, 3, 11),
        ("Io", "shadow transit begins"): utc(2015, 1, 24, 4, 35),
        ("Europa", "shadow transit begins"): utc(2015, 1, 24, 6, 27),
        ("Io", "shadow transit ends"): utc(2015, 1, 24, 6, 52),
    }.items():
        assert abs(times[key] - expected) < timedelta(minutes=3), key
    assert [e["time"] for e in events] == sorted(e["time"] for e in events)
    during = jupiter.snapshot(utc(2015, 1, 24, 6, 40))
    assert sorted(m.name for m in during.moons if m.flags[2]) == ["Callisto", "Europa", "Io"]
    assert "Io shadow transit" in jupiter.find_events(utc(2015, 1, 24, 5), utc(2015, 1, 24, 5, 10))[1]


def test_moon_sides_agree_with_right_ascension():
    when = utc(2026, 10, 3, 11)
    t = sky.to_time(when)
    planet = ae.GeoVector(ae.Body.Jupiter, t, True)
    back = t.AddDays(-planet.Length() / ae.C_AUDAY)
    theory = ae.JupiterMoons(back)
    result = jupiter.moons_now(when, None)
    for row in result["moons"]:
        m = getattr(theory, row["name"].lower())
        moon_ra = ae.EquatorFromVector(ae.Vector(planet.x + m.x, planet.y + m.y, planet.z + m.z, t)).ra
        assert row["side"] == ("east" if moon_ra > ae.EquatorFromVector(planet).ra else "west")
    names = result["east_to_west"].split("  ")
    assert "[Jupiter]" in names and len(names) == 5 - len(result.get("hidden", []))
    assert "observing" not in result and result["jupiter"]["constellation"] == "Leo"


def test_hidden_moon_is_left_out_of_the_lineup():
    # Io is occulted at this moment (it disappears behind Jupiter around 18:39 MDT on 2 Oct 2026)
    result = jupiter.moons_now(utc(2026, 10, 3, 1, 30), MOAB)
    io = next(m for m in result["moons"] if m["name"] == "Io")
    assert io["status"].startswith(("occulted", "eclipsed")) and "Io" in result["hidden"]
    assert "Io" not in result["east_to_west"]
    assert result["observing"]["observable_here"] is False


def test_red_spot_transits_follow_the_rotation_and_the_assumed_longitude():
    start = utc(2026, 10, 3)
    spots = [e["time"] for e in jupiter.find_events(start, start + timedelta(hours=30), grs=98.0)[0] if "moon" not in e]
    assert len(spots) == 3
    for a, b in zip(spots, spots[1:]):
        assert b - a == pytest.approx(timedelta(hours=9, minutes=55, seconds=40), abs=timedelta(seconds=60))
    later = [e["time"] for e in jupiter.find_events(start, start + timedelta(hours=30), grs=99.0)[0] if "moon" not in e]
    assert later[0] - spots[0] == pytest.approx(timedelta(minutes=1.65), abs=timedelta(seconds=20))
    snap = jupiter.snapshot(spots[0])
    assert snap.cm_system_ii == pytest.approx(98.0, abs=0.1)


def test_red_spot_longitude_drifts():
    assert jupiter.grs_longitude(utc(2026, 6, 1)) == 91.0
    assert jupiter.grs_longitude(utc(2027, 6, 1)) == pytest.approx(91.0 + 21.0, abs=0.1)


def test_events_report_filters_to_what_the_site_can_see():
    start = utc(2026, 10, 2, 20)
    everything = jupiter.events(start, 72, MOAB)
    seen = jupiter.events(start, 72, MOAB, observable_only=True)
    assert 0 < seen["count"] < everything["count"]
    assert all(e["observable_here"] and "note" not in e for e in seen["events"])
    assert everything["events"][0]["time"].endswith("-06:00")
    hidden = [e for e in everything["events"] if "note" in e and not e.get("mutual")]
    assert hidden and all(e["event"].startswith(("eclipse", "occultation")) for e in hidden)
    assert "No location" in jupiter.events(start, 2, None)["note"]


# ------------------------------------------------------------------ the Moon's orientation

def test_orientation_matches_meeus():
    # Astronomical Algorithms example 53.a, 1992 April 12 0h TD: l = -1.23, b = +4.20,
    # subsolar point l0 = 67.89, b0 = +1.46, colongitude 22.11
    o = lunar.orientation(utc(1992, 4, 12) - timedelta(seconds=59))
    assert o.sub_earth_lon == pytest.approx(-1.23, abs=0.05)
    assert o.sub_earth_lat == pytest.approx(4.20, abs=0.05)
    assert o.sub_solar_lon == pytest.approx(67.89, abs=0.05)
    assert o.sub_solar_lat == pytest.approx(1.46, abs=0.05)
    assert o.colongitude == pytest.approx(22.11, abs=0.05)


def test_orientation_agrees_with_astronomy_engine_and_shifts_with_the_observer():
    when = utc(2026, 10, 10)
    geo, topo = lunar.orientation(when), lunar.orientation(when, MOAB)
    lib = ae.Libration(sky.to_time(when))
    assert geo.sub_earth_lon == pytest.approx(lib.elon, abs=0.05)
    assert geo.sub_earth_lat == pytest.approx(lib.elat, abs=0.05)
    shift = abs(topo.sub_earth_lon - geo.sub_earth_lon) + abs(topo.sub_earth_lat - geo.sub_earth_lat)
    assert 0.05 < shift < 2.2
    assert topo.sub_solar_lon == pytest.approx(geo.sub_solar_lon, abs=1e-6)


def test_elevation():
    assert lunar.elevation(0, 0, 0, 0) == pytest.approx(90)
    assert lunar.elevation(0, 90, 0, 0) == pytest.approx(0, abs=1e-9)
    assert lunar.elevation(60, 0, 0, 0) == pytest.approx(30)
    assert lunar.elevation(0, 180, 0, 0) == pytest.approx(-90)


def test_libration_report():
    result = lunar.libration(utc(2026, 10, 2, 19, 34), MOAB)
    assert result["libration_latitude_deg"] < -4 and result["favoured_limb"] == "south"
    assert result["viewpoint"] == "topocentric"
    gains = [f["libration_gain_deg"] for f in result["limb_features"]]
    assert gains == sorted(gains, reverse=True) and len(gains) == len(lunar.LIMB_FEATURES) == 45
    views = {f["name"]: f for f in result["limb_features"]}
    assert views["Bailly"]["view"] == "favourable" and "Bailly" in result["well_placed_now"]
    assert views["Byrd"]["view"] in ("unfavourable", "beyond the limb", "in darkness")
    assert views["Scott"]["view"] == "in darkness" and not views["Scott"]["sunlit"]
    for f in result["limb_features"]:
        assert (f["name"] in result["well_placed_now"]) == (f["view"] == "favourable")
    assert lunar.libration(utc(2026, 10, 2, 19, 34), None)["viewpoint"].startswith("geocentric")


# ------------------------------------------------------------------ lunar features

def _dbf(fields: list[tuple[str, int]], rows: list[tuple[str, ...]]) -> bytes:
    record_len = 1 + sum(length for _, length in fields)
    header_len = 32 + 32 * len(fields) + 1
    out = bytearray(32)
    out[4:12] = struct.pack("<IHH", len(rows), header_len, record_len)
    for name, length in fields:
        descriptor = bytearray(32)
        descriptor[:len(name)] = name.encode()
        descriptor[11], descriptor[16] = ord("C"), length
        out += descriptor
    out += b"\r"
    for row in rows:
        out += b" " + b"".join(value.encode("utf-8").ljust(length) for value, (_, length) in zip(row, fields))
    return bytes(out)


def test_parse_dbf_and_shape_features():
    fields = [("name", 20), ("diameter", 12), ("center_lon", 12), ("center_lat", 12), ("type", 24)]
    data = _dbf(fields, [
        ("Copernicus", "96.069916", "339.9214", "9.6209", "Crater, craters"),
        ("Copernicus A", "3.219167", "341.0997", "9.5224", "Satellite Feature"),
        ("Lacus Veris", "382.9", "274.1", "-16.5", "Lacus, lacūs"),
        ("Statio Tranquillitatis", "0.0", "23.47", "0.67", "Statio"),
    ])
    rows = lunar.parse_dbf(data)
    assert len(rows) == 4 and rows[2]["type"] == "Lacus, lacūs"
    assert lunar.shape_features(rows) == [
        {"name": "Copernicus", "type": "crater", "latitude": 9.62, "longitude": -20.08, "diameter_km": 96.1},
        {"name": "Lacus Veris", "type": "lacus", "latitude": -16.5, "longitude": -85.9, "diameter_km": 382.9},
    ]


FEATURES = [
    {"name": "On sunrise line", "type": "crater", "latitude": 0.0, "longitude": -8.0, "diameter_km": 90.0},
    {"name": "Rim just lit", "type": "crater", "latitude": 0.0, "longitude": -11.0, "diameter_km": 240.0},
    {"name": "Still dark", "type": "crater", "latitude": 0.0, "longitude": -11.0, "diameter_km": 60.0},
    {"name": "High sun", "type": "crater", "latitude": 0.0, "longitude": 40.0, "diameter_km": 100.0},
    {"name": "Too small", "type": "crater", "latitude": 10.0, "longitude": -5.0, "diameter_km": 5.0},
    {"name": "Ridge", "type": "mons", "latitude": 60.0, "longitude": -2.0, "diameter_km": 50.0},
    {"name": "Far side sunset", "type": "crater", "latitude": 0.0, "longitude": 172.0, "diameter_km": 300.0},
    {"name": "Limb sunset", "type": "crater", "latitude": 0.0, "longitude": 166.0, "diameter_km": 50.0},
]


def test_terminator_features():
    # Just after first quarter: Sun over 82°E, sunrise terminator at 8°W
    o = lunar.Orientation(0.0, 0.0, 82.0, 0.0)
    found = lunar.terminator_features(FEATURES, o, 20, 8)
    assert [f["name"] for f in found] == ["Rim just lit", "On sunrise line", "Ridge"]
    assert found[1]["sun_altitude_deg"] == 0.0 and found[1]["lighting"] == "sunrise"
    assert found[0]["sun_altitude_deg"] == -3.0
    assert [f["name"] for f in lunar.terminator_features(FEATURES, o, 20, 8, {"mons"})] == ["Ridge"]
    assert "Too small" in [f["name"] for f in lunar.terminator_features(FEATURES, o, 0, 8)]
    # Libration of 80° is unphysical but shows that far-side features appear only once tipped into view
    tipped = lunar.terminator_features(FEATURES, lunar.Orientation(80.0, 0.0, 82.0, 0.0), 20, 8)
    limb = next(f for f in tipped if f["name"] == "Limb sunset")
    assert limb["lighting"] == "sunset" and limb["near_limb"] is True


def test_terminator_report():
    result = lunar.terminator(FEATURES, utc(2026, 10, 19, 3), MOAB, limit=1)  # 21:00 MDT, a day past first quarter
    assert result["moon"]["phase"] == "First Quarter" and result["moon"]["above_horizon"]
    assert result["terminator"]["facing_earth"] == "sunrise"
    assert result["terminator"]["sunrise_longitude_deg"] == pytest.approx(-8.3, abs=0.3)
    assert result["count"] == 1 and result["total_matches"] >= 2
    assert "altitude_deg" not in lunar.terminator(FEATURES, utc(2026, 10, 19, 3), None)["moon"]


# ------------------------------------------------------------------ conjunctions and oppositions

def test_great_conjunction_of_2020():
    result = almanac.conjunctions(utc(2020, 12, 1), 40)
    pair = next(c for c in result["conjunctions"] if c["bodies"] == ["Jupiter", "Saturn"])
    assert pair["time"].startswith("2020-12-21T18:") and pair["separation_deg"] == pytest.approx(0.10, abs=0.01)
    assert pair["summary"] == "Saturn passes 0.1° north of Jupiter" and pair["sky"] == "evening"
    assert pair["elongation_from_sun_deg"] == pytest.approx(30, abs=1)
    assert "at_closest_from_here" not in pair


def test_conjunction_filters():
    start = utc(2026, 10, 2, 20)
    year = almanac.conjunctions(start, 365, MOAB)
    first = year["conjunctions"][0]
    assert first["bodies"] == ["Mars", "Jupiter"] and first["time"].startswith("2026-11-15")
    assert first["separation_deg"] == pytest.approx(1.2, abs=0.1) and first["constellation"] == "Leo"
    assert first["at_closest_from_here"]["visible"] is False  # below the horizon from Moab at that moment
    assert all(c["separation_deg"] <= 5 and c["elongation_from_sun_deg"] >= 12 for c in year["conjunctions"])
    assert [c["time"] for c in year["conjunctions"]] == sorted(c["time"] for c in year["conjunctions"])
    everything = almanac.conjunctions(start, 365, MOAB, min_elongation_deg=0)
    assert everything["count"] == year["count"] + year["lost_in_sun_glare"]
    only_mars = almanac.conjunctions(start, 365, MOAB, body="mars")
    assert only_mars["count"] and all("Mars" in c["bodies"] for c in only_mars["conjunctions"])
    assert almanac.conjunctions(start, 365, MOAB, max_separation_deg=0.5)["count"] < year["count"]


def test_moon_conjunctions():
    result = almanac.conjunctions(utc(2026, 10, 2, 20), 30, include_moon=True, body="moon")
    jupiter_pass = next(c for c in result["conjunctions"] if c["bodies"] == ["Moon", "Jupiter"])
    assert jupiter_pass["time"].startswith("2026-10-06T10:") and jupiter_pass["separation_deg"] < 0.5
    assert jupiter_pass["moon_illuminated_percent"] == pytest.approx(20, abs=2)
    assert all(c["bodies"][0] == "Moon" for c in result["conjunctions"])
    assert "parallax" in result["note"]


def test_oppositions():
    result = almanac.oppositions(utc(2026, 10, 2), 365, MOAB)
    found = {o["planet"]: o for o in result["oppositions"]}
    assert set(found) == {"Saturn", "Uranus", "Jupiter", "Mars", "Neptune"}
    assert found["Saturn"]["opposition"].startswith("2026-10-04") and "ring_tilt_deg" in found["Saturn"]
    assert found["Mars"]["opposition"].startswith("2027-02-19")
    assert found["Mars"]["highest_altitude_from_here_deg"] == pytest.approx(90 - (MOAB.latitude - found["Mars"]["dec_deg"]), abs=0.1)
    assert [o["opposition"] for o in result["oppositions"]] == sorted(o["opposition"] for o in result["oppositions"])
    assert almanac.oppositions(utc(2026, 10, 2), 500, None, ["saturn"])["count"] == 2


def test_mars_closest_approach_of_2003():
    mars = almanac.oppositions(utc(2003, 6, 1), 200, None, ["mars"])["oppositions"][0]
    assert mars["opposition"].startswith("2003-08-28")
    assert mars["closest_to_earth"] == {"date": "2003-08-27", "distance_au": pytest.approx(0.37272, abs=2e-5)}
    assert mars["apparent_diameter_arcsec"] == pytest.approx(25.1, abs=0.1)
    assert "highest_altitude_from_here_deg" not in mars


# ------------------------------------------------------------------ geometry helper

def test_body_lon_lat():
    north = sky.unit((0.0, 0.1, 1.0))
    node = sky.unit(sky.cross((0.0, 0.0, 1.0), north))
    assert sky.body_lon_lat(north, 0.0, node) == pytest.approx((0.0, 0.0), abs=1e-9)
    assert sky.body_lon_lat(north, 30.0, node)[0] == pytest.approx(-30.0)  # the body turned east under the node
    assert sky.body_lon_lat(north, 0.0, north)[1] == pytest.approx(90.0)
    assert sky.wrap180(190) == -170 and sky.wrap180(-180) == -180


# ------------------------------------------------------------------ mutual events and the Red Spot table

def test_mutual_events_match_imcce_predictions():
    # IMCCE via the BAA: Io occults Europa 2026 Sep 23 04:29 UT lasting 3.6 min;
    # Io eclipses Ganymede 2027 Jan 18 04:55.7 UT.
    occultation = [e for e in jupiter.find_mutual_events(utc(2026, 9, 23, 3, 45), utc(2026, 9, 23, 5))
                   if e["event"] == "Io occults Europa"]
    assert len(occultation) == 1
    assert abs((occultation[0]["time"] - utc(2026, 9, 23, 4, 29)).total_seconds()) < 180
    assert occultation[0]["duration_min"] == pytest.approx(3.6, abs=0.5)
    eclipse = [e for e in jupiter.find_mutual_events(utc(2027, 1, 18, 4), utc(2027, 1, 18, 6))
               if e["event"] == "Io eclipses Ganymede"]
    assert len(eclipse) == 1
    assert abs((eclipse[0]["time"] - utc(2027, 1, 18, 4, 55, 42)).total_seconds()) < 90
    assert eclipse[0]["type"] in ("partial", "total") and 0.2 < eclipse[0]["estimated_light_loss"] < 0.8


def test_no_mutual_events_far_from_jupiters_equinox():
    assert jupiter.find_mutual_events(utc(2024, 1, 1), utc(2024, 1, 4)) == []


def test_circle_overlap():
    assert jupiter.circle_overlap(1, 1, 3) == 0
    assert jupiter.circle_overlap(1, 2, 0.5) == pytest.approx(math.pi)
    assert jupiter.circle_overlap(1, 1, 1) == pytest.approx(2 * math.pi / 3 - math.sqrt(3) / 2)


def test_mutual_events_are_listed_with_formatted_contacts():
    report = jupiter.events(utc(2026, 10, 6), 24, MOAB)
    mutual = [e for e in report["events"] if e.get("mutual")]
    assert mutual and all(e["begins"].endswith("-06:00") and e["begins"] < e["ends"] for e in mutual)
    assert not [e for e in jupiter.events(utc(2026, 10, 6), 24, MOAB, mutual=False)["events"] if e.get("mutual")]


GRS_TABLE = """# See end of file for documentation
YYYY MM DD Lon  Source/comments
3025 12  1 16439 (extrapolation)
2025 12  1 439   (2010-present from JUPOS)
2024 10  1 421
2024 01  1 410
2022 11  1 386
"""


def test_red_spot_table_uses_latest_measurement_and_recent_drift():
    model = jupiter.parse_grs_table(GRS_TABLE, datetime(2026, 10, 6).date())
    assert model.epoch.isoformat() == "2025-12-01" and model.longitude == 439
    assert model.drift_deg_per_day * 365.25 == pytest.approx(15.5, abs=1.5)  # about 16°/year lately
    assert model.at(utc(2025, 12, 1)) == pytest.approx(79)
    assert jupiter.parse_grs_table("nothing useful", datetime(2026, 1, 1).date()) is None


# ------------------------------------------------------------------ stars and elongations

def test_venus_passes_the_pleiades_in_april_2020():
    found = almanac.conjunctions(utc(2020, 3, 25), 15, None, 2.0, body="venus", include_stars=True)
    pleiades = [c for c in found["conjunctions"] if "Pleiades" in c["bodies"]]
    assert len(pleiades) == 1 and pleiades[0]["time"].startswith("2020-04-03")
    assert pleiades[0]["separation_deg"] < 0.5 and pleiades[0]["magnitudes"]["Pleiades"] == 1.6
    assert pleiades[0]["sky"] == "evening"


def test_moon_star_pairings_flag_possible_occultations():
    found = almanac.conjunctions(utc(2026, 10, 1), 30, None, 1.5, include_moon=True, include_stars=True)
    antares = [c for c in found["conjunctions"] if set(c["bodies"]) == {"Moon", "Antares"}]
    assert antares and "occultation_possible" in antares[0]


def test_greatest_elongations_of_2026():
    found = almanac.greatest_elongations(utc(2026, 1, 1), 365, MOAB)["elongations"]
    venus = [e for e in found if e["planet"] == "Venus"]
    assert len(venus) == 1 and venus[0]["time"].startswith("2026-08-1") and venus[0]["sky"] == "evening"
    assert venus[0]["elongation_deg"] == pytest.approx(45.9, abs=0.2)
    february = next(e for e in found if e["planet"] == "Mercury" and e["time"].startswith("2026-02"))
    assert february["elongation_deg"] == pytest.approx(18.1, abs=0.2)
    assert february["at_civil_twilight"]["altitude_deg"] > 5
    assert [e["time"] for e in found] == sorted(e["time"] for e in found)
