"""Offline tests for the light-pollution atlas reader, dark-site picking and terrain horizons."""

import io
import json

import pytest
from PIL import Image

from astronomy_mcp import darksites, horizon
from astronomy_mcp import lightpollution as lp
from astronomy_mcp.location import Location


# ------------------------------------------------------------------ atlas zones

def test_zone_table_is_consistent():
    assert len(lp.ZONES) == 15
    assert len(lp.ZONE_COLOURS) == 15  # every colour distinct
    for (_, _, _, high), (_, _, low, _) in zip(lp.ZONES, lp.ZONES[1:]):
        assert high == low  # bands are contiguous


def test_lpi_to_sky_brightness_matches_atlas_key():
    # The atlas key: LPI 1.00 <-> 21.25, LPI 3.00 <-> 20.49, LPI 46.77 <-> 17.80 mag/arcsec^2
    assert lp.sqm_for_lpi(1.0) == pytest.approx(21.25, abs=0.01)
    assert lp.sqm_for_lpi(3.0) == pytest.approx(20.49, abs=0.01)
    assert lp.sqm_for_lpi(46.77) == pytest.approx(17.80, abs=0.01)


def test_describe_zone():
    dark = lp.describe_zone(0)
    city = lp.describe_zone(14)
    assert dark["zone"] == "0" and dark["bortle_estimate"] == 1
    assert city["zone"] == "7b" and city["bortle_estimate"] == 9
    assert dark["sky_brightness_mag_arcsec2"] > city["sky_brightness_mag_arcsec2"]
    mid = lp.describe_zone(lp.ZONE_NAMES.index("4a"))
    assert 20.91 <= mid["sky_brightness_mag_arcsec2"] <= 21.25


def test_zone_of_exact_and_nearest_colour():
    assert lp._zone_of((31, 161, 42)) == lp.ZONE_NAMES.index("3b")
    assert lp._zone_of((30, 160, 40)) == lp.ZONE_NAMES.index("3b")  # anti-aliased pixel


def test_tile_coordinates():
    # Moab, Utah sits in zoom-6 tile (12, 24); verified against the live atlas.
    tx, ty, px, py = lp._tile_coords(38.5733, -109.5498)
    assert (tx, ty) == (12, 24)
    assert 0 <= px < 1024 and 0 <= py < 1024


async def test_zone_at_reads_cached_tile(isolated_home):
    tx, ty, px, py = lp._tile_coords(38.5733, -109.5498)
    img = Image.new("RGB", (1024, 1024), (0, 0, 0))
    img.putpixel((px, py), (191, 100, 30))  # zone 5a
    folder = isolated_home / "lightpollution" / str(lp.ATLAS_YEAR)
    folder.mkdir(parents=True)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    (folder / f"tile_{lp.ZOOM}_{tx}_{ty}.png").write_bytes(buf.getvalue())
    lp._images.clear()
    try:
        result = await lp.sky_brightness(38.5733, -109.5498)
        assert result["zone"] == "5a"
        assert await lp.zone_at(38.5733 + 0.05, -109.5498) == 0
    finally:
        lp._images.clear()


# ------------------------------------------------------------------ geometry and site picking

def test_destination_and_distance_round_trip():
    lat, lon = lp.destination(38.5, -109.5, 90, 50)
    assert lp.distance_km(38.5, -109.5, lat, lon) == pytest.approx(50, abs=0.01)
    assert lat == pytest.approx(38.5, abs=0.05) and lon > -109.5


def test_pick_sites_prefers_dark_then_near_and_spreads_out():
    cells = [
        lp.Cell(0.0, 0.00, 3, 5), lp.Cell(0.0, 0.50, 1, 60), lp.Cell(0.0, 0.52, 1, 62),
        lp.Cell(0.0, 1.00, 1, 110), lp.Cell(0.0, 0.10, 2, 12),
    ]
    picked = lp.pick_sites(cells, 3, min_separation_km=10)
    assert [(c.zone, c.distance_km) for c in picked] == [(1, 60), (1, 110), (2, 12)]


def test_access_points_named_first_and_within_radius():
    elements = [
        {"lat": 37.61, "lon": -110.01, "tags": {"tourism": "viewpoint", "name": "Sipapu Bridge View"}},
        {"lat": 37.60, "lon": -110.00, "tags": {"amenity": "parking", "name": "Trailhead Lot"}},
        {"center": {"lat": 37.605, "lon": -110.012}, "tags": {"tourism": "camp_site"}},
        {"lat": 38.5, "lon": -110.0, "tags": {"tourism": "viewpoint", "name": "Too Far"}},
        {"lat": 37.60, "lon": -110.01, "tags": {"shop": "gift"}},
    ]
    found = darksites._access_points(elements, 37.60, -110.01)
    names = [a["name"] for a in found]
    assert "Too Far" not in names
    assert names[-1] == "campground"  # unnamed sorted last
    assert {"Sipapu Bridge View", "Trailhead Lot"} <= set(names)


def test_overpass_query_is_point_features_only():
    q = darksites._query([(37.6, -110.0)])
    assert "around:8000,37.6000,-110.0000" in q
    assert "protected_area" not in q and "out center tags" in q


# ------------------------------------------------------------------ horizon

def test_apparent_angle_curvature():
    assert horizon.apparent_angle(1000, 2000, 10_000) == pytest.approx(5.7, abs=0.1)
    # A peak level with the eye 100 km away sits below the horizontal because of curvature
    assert horizon.apparent_angle(1000, 1000, 100_000) < -0.3


def test_horizon_interpolation_and_summary():
    hz = horizon.Horizon([float(a) for a in range(0, 360, 10)], [0.0] * 18 + [20.0] + [0.0] * 17, 1500)
    assert hz.altitude_at(180) == 20.0
    assert hz.altitude_at(175) == pytest.approx(10.0)
    assert hz.altitude_at(355) == pytest.approx(0.0)  # wraps past 360
    summary = hz.summary()
    assert summary["highest_obstruction"]["direction"] == "S"
    assert summary["max_obstruction_by_direction_deg"]["S"] == 20.0


async def test_get_horizon_computes_and_caches(isolated_home, monkeypatch):
    calls = []

    async def fake_elevations(points):
        calls.append(len(points))
        # Observer at 1000 m; a 2000 m ridge 10 km due east (azimuth 90), flat elsewhere.
        out = [1000.0]
        for az in range(0, 360, horizon.AZIMUTH_STEP_DEG):
            out += [2000.0 if az == 90 and d == 9 else 1000.0 for d in horizon.DISTANCES_KM]
        return out

    monkeypatch.setattr(horizon, "_elevations", fake_elevations)
    loc = Location(38.0, -109.0, 1000.0, "America/Denver")
    hz = await horizon.get_horizon(loc)
    assert hz.altitude_at(90) == pytest.approx(horizon.apparent_angle(1001.7, 2000, 9000), abs=0.01)
    assert hz.altitude_at(270) < 0
    assert calls == [1 + 36 * len(horizon.DISTANCES_KM)] and calls[0] < 600  # under Open-Meteo's per-minute cap
    await horizon.get_horizon(loc)
    assert len(calls) == 1  # second call served from disk
    cached = json.loads((isolated_home / "horizons" / "38.0000_-109.0000.json").read_text())
    assert len(cached["altitudes"]) == 36
