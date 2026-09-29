"""Offline tests for ephemeris wrappers, the deep-sky catalog, conditions and space-weather parsing."""

from datetime import UTC, date, datetime, timedelta

import pytest

from astronomy_mcp import catalog, conditions, location, sky, space
from astronomy_mcp.location import Location
from astronomy_mcp.sky import Target

from conftest import MOAB

NGC_CSV = """Name;Type;RA;Dec;Const;MajAx;MinAx;PosAng;B-Mag;V-Mag;J-Mag;H-Mag;K-Mag;SurfBr;Hubble;Pax;Pm-RA;Pm-Dec;RadVel;Redshift;Cstar U-Mag;Cstar B-Mag;Cstar V-Mag;M;NGC;IC;Cstar Names;Identifiers;Common names;NED notes;OpenNGC notes;Sources
IC0011;Dup;00:52:59.35;+56:37:18.8;Cas;;;;;;;;;;;;;;;;;;;;0281;;;;;;;
NGC0224;G;00:42:44.35;+41:16:08.6;And;177.83;69.66;35;4.29;3.44;2.09;1.28;0.98;23.63;Sb;6.0000;;;-300;-0.001000;;;;031;;;;2MASX J00424433+4116074,PGC 002557;Andromeda Galaxy;;;
NGC0281;HII;00:52:59.35;+56:37:18.8;Cas;35.00;30.00;;;7.40;;;;;;;;;;;;;;;;;;LBN 616;Pacman Nebula;;;
NGC6205;GCl;16:41:41.63;+36:27:40.7;Her;16.50;;;;5.80;4.45;3.94;3.85;;;0.0813;-3.180;-2.560;-244;-0.000815;;;;013;;;;MWSC 2445;Hercules Globular Cluster;;;
NGC6720;PN;18:53:35.08;+33:01:45.0;Lyr;1.40;;;;8.80;;;;;;;;;;;;;;057;;;;;Ring Nebula;;;
NGC9999;NonEx;00:00:00;+00:00:00;And;;;;;;;;;;;;;;;;;;;;;;;;;;;
"""
ADDENDUM_CSV = """Name;Type;RA;Dec;Const;MajAx;MinAx;PosAng;B-Mag;V-Mag;J-Mag;H-Mag;K-Mag;SurfBr;Hubble;Pax;Pm-RA;Pm-Dec;RadVel;Redshift;Cstar U-Mag;Cstar B-Mag;Cstar V-Mag;M;NGC;IC;Cstar Names;Identifiers;Common names;NED notes;OpenNGC notes;Sources
C041;OCl;04:26:54.0;+15:52:00;Tau;329.00;;;;;;;;;;;104.920;-28.000;40;0.000133;;;;;;;;Cl 050,Mel 025;Hyades;;;
Mel022;OCl;03:47:24.0;+24:07:00;Tau;120.00;;;;1.20;;;;;;;;;;;;;;045;;;;;Pleiades;;;
"""


@pytest.fixture
def cat():
    return catalog.Catalog.from_csv_texts(NGC_CSV, ADDENDUM_CSV)


# ------------------------------------------------------------------ catalog

@pytest.mark.parametrize(
    "raw, key",
    [("NGC 0224", "ngc224"), ("ngc224", "ngc224"), ("M 31", "m31"), ("Messier 31", "m31"),
     ("Caldwell 41", "c41"), ("The Ring Nebula", "ring nebula"), ("PGC 002557", "pgc2557")],
)
def test_normalize(raw, key):
    assert catalog.normalize(raw) == key


@pytest.mark.parametrize("name", ["M31", "M 31", "NGC 224", "Andromeda Galaxy", "andromeda galaxy", "PGC 2557"])
def test_catalog_lookup_aliases(cat, name):
    assert cat.lookup(name)["name"] == "NGC 224"


def test_catalog_shapes_rows(cat):
    m31 = cat.lookup("M31")
    assert m31["messier"] == "M 31"
    assert m31["ra_deg"] == pytest.approx(10.6848, abs=1e-3)
    assert m31["dec_deg"] == pytest.approx(41.2691, abs=1e-3)
    assert m31["magnitude"] == 3.44 and m31["group"] == "galaxy"
    assert cat.lookup("Caldwell 41")["name"] == "Caldwell 41"
    assert cat.lookup("M45")["name"] == "Melotte 22"


def test_catalog_follows_duplicates_and_drops_nonexistent(cat):
    assert cat.lookup("IC 11")["name"] == "NGC 281"
    assert cat.lookup("NGC 9999") is None


def test_catalog_search(cat):
    assert [o["name"] for o in cat.search(messier_only=True)] == ["Melotte 22", "NGC 224", "NGC 6205", "NGC 6720"]
    assert [o["name"] for o in cat.search(group="planetary_nebula")] == ["NGC 6720"]
    assert [o["name"] for o in cat.search(constellation="Tau", max_magnitude=5)] == ["Melotte 22"]
    assert [o["name"] for o in cat.search(name_contains="ring")] == ["NGC 6720"]


def test_constellation_abbrev():
    assert catalog.constellation_abbrev("sagittarius") == "Sgr"
    assert catalog.constellation_abbrev("CVN") == "CVn"
    assert catalog.constellation_abbrev("Narnia") is None
    assert len(catalog.CONSTELLATION_NAMES) == 88


# ------------------------------------------------------------------ sky

def test_night_ordering_and_plausible_times():
    n = sky.night(MOAB, date(2026, 9, 28))
    assert n.darkest == "astronomical"
    events = [n.sunset, n.civil[0], n.nautical[0], n.astronomical[0], n.astronomical[1], n.nautical[1], n.civil[1], n.sunrise]
    assert events == sorted(events)
    local_sunset = n.sunset.astimezone(MOAB.tz)
    assert (local_sunset.hour, local_sunset.minute) >= (18, 55) and local_sunset.hour < 20


def test_midnight_sun_has_no_night():
    tromso = Location(69.65, 18.96, 0, "Europe/Oslo")
    assert sky.night(tromso, date(2026, 6, 21)).darkest == "none"


def test_transit_altitude_matches_geometry():
    t = Target("test", ra_deg=250.0, dec_deg=36.0)
    rst = sky.rise_set_transit(t, MOAB, date(2026, 6, 1))
    assert rst["transit_altitude_deg"] == pytest.approx(90 - abs(MOAB.latitude - 36.0), abs=0.6)
    assert "rise" in rst and "set" in rst


@pytest.mark.parametrize("dec, status", [(88.0, "circumpolar (never sets)"), (-80.0, "never rises")])
def test_circumpolar_and_never_rises(dec, status):
    assert sky.rise_set_transit(Target("x", ra_deg=10.0, dec_deg=dec), MOAB, date(2026, 6, 1))["status"] == status


def test_fast_tracks_agree_with_full_model():
    when = datetime(2026, 10, 10, 6, 0, tzinfo=UTC)
    times = [when + timedelta(hours=h) for h in range(3)]
    ra, dec = 10.6848, 41.2691
    fast = sky.fast_tracks([(ra, dec)], times, MOAB)[0]
    for t, (alt, az) in zip(times, fast):
        full = sky.horizontal(Target("M31", ra_deg=ra, dec_deg=dec), t, MOAB)
        if full["altitude_deg"] > 10:
            assert alt == pytest.approx(full["altitude_deg"], abs=0.3)
            assert az == pytest.approx(full["azimuth_deg"], abs=0.5)


def test_moon_phase_and_quarters():
    start = datetime(2026, 10, 1, tzinfo=UTC)
    quarters = sky.moon_quarters(start, start + timedelta(days=30))
    assert [q for q, _ in quarters] == ["Last Quarter", "New Moon", "First Quarter", "Full Moon"]
    full = dict(quarters)["Full Moon"]
    phase = sky.moon_phase(full)
    assert phase["phase"] == "Full Moon" and phase["illuminated_percent"] > 99


def test_constellation_and_compass():
    assert sky.constellation(83.82, -5.39)["name"] == "Orion"
    assert sky.constellation(150.0, -30.0)["abbreviation"] == "Ant"
    assert sky.compass(0) == "N" and sky.compass(95) == "E" and sky.compass(350) == "N"


def test_airmass():
    assert sky.airmass(90) == pytest.approx(1.0, abs=0.01)
    assert sky.airmass(30) == pytest.approx(2.0, abs=0.05)
    assert sky.airmass(-1) is None


def test_local_solar_eclipse_2029_visible_from_moab():
    found = sky.local_solar_eclipses(datetime(2028, 6, 1, tzinfo=UTC), 1, MOAB)
    assert found and found[0]["peak"].startswith("2029-01-14") and found[0]["kind"] == "partial"


def test_observing_date_explicit():
    assert sky.observing_date("2026-10-10", MOAB) == date(2026, 10, 10)


# ------------------------------------------------------------------ conditions

def test_nelm_and_moonlight():
    assert conditions.nelm_from_sqm(21.9) > conditions.nelm_from_sqm(18.0)
    assert 6.3 < conditions.nelm_from_sqm(21.9) < 6.8
    assert conditions.sqm_with_moon(21.5, -12.7, -5) == 21.5
    bright = conditions.sqm_with_moon(21.5, -12.7, 60)
    assert 17.5 < bright < 18.5
    assert conditions.sqm_with_moon(21.5, -9.0, 60) > bright  # a crescent brightens the sky less
    # Krisciunas & Schaefer: the sky is much brighter close to the Moon
    near = conditions.sqm_with_moon(21.5, -12.7, 60, separation_deg=10)
    assert near < conditions.sqm_with_moon(21.5, -12.7, 60, separation_deg=40) < bright + 0.3
    assert bright - near > 1.0


def test_limiting_magnitude_scales_with_aperture():
    eye = conditions.limiting_magnitude(21.0, "naked_eye")
    scope = conditions.limiting_magnitude(21.0, "telescope", 200)
    assert "aperture_mm" not in eye and "stellar_limit_magnification" not in eye
    assert eye["stellar_limit"] == eye["naked_eye_limit"] + 0.5  # experienced-observer allowance
    # Aperture gain (5 log D/7 = 7.3 mag) plus the darker background at high power
    assert 7.3 < scope["stellar_limit"] - eye["stellar_limit"] < 9.0
    assert scope["stellar_limit_magnification"] >= 100


def test_bortle_round_trip():
    for b in range(1, 10):
        assert conditions.bortle_from_sqm(conditions.sqm_from_bortle(b)) == b


def test_decode_7timer():
    decoded = conditions._decode_7timer(
        {"init": "2026092818", "dataseries": [{"timepoint": 3, "seeing": 2, "transparency": 7}, {"timepoint": 6, "seeing": -9999, "transparency": 3}]}
    )
    first = decoded[datetime(2026, 9, 28, 21, tzinfo=UTC)]
    assert first["seeing"] == '0.5-0.75"' and first["transparency_code"] == 7
    assert decoded[datetime(2026, 9, 29, 0, tzinfo=UTC)]["seeing"] is None


def test_longest_run():
    assert conditions._longest_run([False, True, True, False, True, True, True]) == (4, 3)
    assert conditions._longest_run([False, False]) == (0, 0)


# ------------------------------------------------------------------ location

def test_default_location_round_trip():
    assert location.load_default() is None
    location.save_default(MOAB)
    assert location.load_default() == MOAB


async def test_resolve_without_anything_explains_itself():
    with pytest.raises(ValueError, match="set_default_location"):
        await location.resolve()


async def test_resolve_uses_default(moab):
    assert await location.resolve() == moab
    assert await location.resolve(moab.latitude, moab.longitude) == moab  # no network needed


# ------------------------------------------------------------------ space

def test_kp_level():
    assert space.kp_level(1.3) == "quiet"
    assert space.kp_level(5.0) == "G1 minor storm"
    assert space.kp_level(9.0) == "G5 extreme storm"


def test_aurora_at_grid_lookup():
    coords = [[250, 39, 2], [250, 45, 30], [251, 47, 60], [0, 0, 99]]
    result = space.aurora_at(coords, 38.6, -109.5)
    assert result == {"overhead_probability_pct": 2, "max_within_10deg_poleward_pct": 60}


def test_shape_launch_distance():
    raw = {
        "name": "Falcon 9 | Test", "net": "2026-10-01T15:10:06Z",
        "status": {"name": "Go for Launch"}, "pad": {"name": "SLC-4E", "latitude": "34.632", "longitude": "-120.611",
                                                    "location": {"name": "Vandenberg SFB, CA, USA"}},
        "mission": {"name": "Test", "description": "", "vid_urls": []},
    }
    shaped = space._shape_launch(raw, MOAB)
    assert shaped["location"] == "Vandenberg SFB, CA, USA"
    assert 1000 < shaped["distance_from_you_km"] < 1150
    assert "description" not in shaped and "webcasts" not in shaped
