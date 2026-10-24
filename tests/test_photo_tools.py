"""Offline tests for Milky Way planning, survey cutouts, finder charts and plate solving."""

import io
import json
from datetime import date

import pytest
from mcp import Client
from PIL import Image

from astronomy_mcp import finder, milkyway, mcp, platesolve, sky, surveys
from astronomy_mcp.horizon import Horizon
from astronomy_mcp.http import UpstreamError
from astronomy_mcp.location import Location

from conftest import MOAB

# ------------------------------------------------------------------ Milky Way core


def test_galactic_coordinates():
    assert milkyway.CORE == (pytest.approx(266.405, abs=0.001), pytest.approx(-28.936, abs=0.001))
    assert milkyway.galactic_to_equatorial(0, 90) == (pytest.approx(192.859, abs=0.001), pytest.approx(27.128, abs=0.001))
    assert milkyway.band_tilt(10, 100, 10, 110) == pytest.approx(0)
    assert milkyway.band_tilt(10, 100, 20, 100) == pytest.approx(90)
    assert "panorama" in milkyway.composition(10, 20) and "portrait" in milkyway.composition(80, 20)


def test_new_moon_night_in_june():
    n = sky.night(MOAB, date(2027, 6, 5))
    row = milkyway.plan_night(MOAB, n, 10, None)
    assert row["shooting_window"]["hours"] == pytest.approx(4.9, abs=0.2)
    best = row["best"]
    assert best["altitude_deg"] == pytest.approx(90 - MOAB.latitude + milkyway.CORE[1], abs=0.2)  # at transit
    assert best["direction"] == "S" and 30 <= best["band_tilt_deg"] <= 90
    assert row["moon"]["illuminated_percent"] < 10


def test_moon_and_terrain_close_the_window():
    moonlit = milkyway.plan_night(MOAB, sky.night(MOAB, date(2026, 10, 19)), 10, None)
    assert "Moon" in moonlit["reason"] and moonlit["moon"]["up_during_darkness"] != "no"
    wall = Horizon(list(range(0, 360, 5)), [30.0] * 72, 1200.0)
    blocked = milkyway.plan_night(MOAB, sky.night(MOAB, date(2027, 6, 5)), 10, wall)
    assert "terrain" in blocked["reason"]


def test_multi_night_plan_and_season():
    out = milkyway.plan(MOAB, date(2027, 5, 25), 21, 10, None)
    hours = [r["shooting_window"]["hours"] for r in out["best_nights"]]
    assert hours == sorted(hours, reverse=True) and len(out["nights"]) == 21
    season = out["season"]["hours_per_night_by_month"]
    assert len(season) == 12 and max(season, key=season.get) == "2027-06" and season["2027-12"] == 0
    assert "next_good_night" not in out


def test_out_of_season_points_ahead_and_far_north_never():
    out = milkyway.plan(MOAB, date(2026, 12, 1), 1, 10, None)
    assert "reason" in out["night"] and out["next_good_night"]["date"] > "2027-01-01"
    assert out["season"]["hours_per_night_by_month"]["2026-12"] == 0 and "2027" in out["season"]["summary"]
    tromso = Location(69.65, 18.96, 0, "Europe/Oslo", name="Tromso")
    far = milkyway.plan(tromso, date(2027, 6, 1), 1, 10, None)
    assert far["core"]["highest_possible_altitude_deg"] < 0
    assert "never clears" in far["season"]["summary"] and far["next_good_night"] == "none within a year from here"


async def test_milky_way_tool(moab):
    async with Client(mcp) as client:
        result = await client.call_tool("plan_milky_way_shot", {"date": "2027-06-05", "terrain": False})
    data = result.structured_content
    assert data["location"] == "Moab" and data["night"]["shooting_window"]["hours"] > 4


# ------------------------------------------------------------------ survey cutouts


def jpeg(size=(64, 64), dot=True) -> bytes:
    image = Image.new("RGB", size, (20, 20, 20))
    if dot:
        image.putpixel((size[0] // 2, size[1] // 2), (255, 255, 255))
    out = io.BytesIO()
    image.save(out, "JPEG")
    return out.getvalue()


@pytest.fixture
def fake_surveys(monkeypatch):
    calls = []

    async def fake_get_bytes(url, params=None, **kwargs):
        calls.append((url, params))
        return jpeg((int(params.get("width", 64)), int(params.get("height", 64))) if "width" in params else (64, 64))

    monkeypatch.setattr(surveys, "get_bytes", fake_get_bytes)
    return calls


def test_survey_choice():
    assert surveys.pick_survey("auto", 1) == "dss2_color"
    assert surveys.pick_survey("auto", 1, grayscale=True) == "dss2_red"
    assert surveys.pick_survey("auto", 12) == "mellinger_color"
    assert surveys.pick_survey("panstarrs_g", 1) == "panstarrs_g"
    with pytest.raises(ValueError, match="Unknown survey"):
        surveys.pick_survey("hubble", 1)


async def test_fetch_saves_and_reuses(fake_surveys):
    data, source, path = await surveys.fetch("dss2_color", 202.47, 47.2, 0.3, 64, 48, "jpg", "M51")
    assert path.exists() and path.name.startswith("m51_dss2_color") and "hips2fits" in source
    assert fake_surveys[0][1]["hips"] == "CDS/P/DSS2/color" and fake_surveys[0][1]["fov"] == "0.300000"
    again, source, _ = await surveys.fetch("dss2_color", 202.47, 47.2, 0.3, 64, 48, "jpg", "M51")
    assert again == data and len(fake_surveys) == 1 and "saved copy" in source


async def test_fetch_coverage_blank_and_fallback(monkeypatch):
    with pytest.raises(ValueError, match="north of declination -30"):
        await surveys.fetch("panstarrs_color", 83.8, -69.3, 0.5, 64, 64)

    async def blank(url, params=None, **kwargs):
        return jpeg(dot=False)

    monkeypatch.setattr(surveys, "get_bytes", blank)
    with pytest.raises(ValueError, match="no data"):
        await surveys.fetch("sdss_color", 10.0, -60.0, 0.5, 64, 64)

    async def hips_down(url, params=None, **kwargs):
        if url == surveys.HIPS2FITS_URL:
            raise UpstreamError("Could not reach CDS hips2fits")
        assert params["Survey"] == "DSS2 Red" and params["Size"] == "0.500000,0.250000"
        return jpeg()

    monkeypatch.setattr(surveys, "get_bytes", hips_down)
    _, source, _ = await surveys.fetch("dss2_red", 10.0, 20.0, 0.5, 64, 32)
    assert "SkyView" in source


async def test_cutout_tool_returns_image(fake_surveys):
    async with Client(mcp) as client:
        result = await client.call_tool("get_survey_cutout", {"ra_deg": 10.0, "dec_deg": 20.0, "fov_deg": 0.2, "width_px": 64})
        fits = await client.call_tool("get_survey_cutout", {"ra_deg": 10.0, "dec_deg": 20.0, "image_format": "fits"})
        moon = await client.call_tool("get_survey_cutout", {"target": "Moon"})
    assert [c.type for c in result.content] == ["text", "image"]
    data = result.structured_content
    assert data["arcsec_per_pixel"] == pytest.approx(0.2 * 3600 / 64, abs=0.01) and data["orientation"].startswith("north up")
    assert [c.type for c in fits.content] == ["text"] and fits.structured_content["saved_to"].endswith(".fits")
    assert moon.is_error


# ------------------------------------------------------------------ finder charts


def test_projection_and_orientations():
    assert finder.project(10, 20, 10, 20) == (pytest.approx(0), pytest.approx(0))
    east, north = finder.project(10, 21, 10, 20)
    assert east == pytest.approx(0, abs=1e-9) and north == pytest.approx(1.0, abs=0.001)
    assert finder.project(11, 20, 10, 20)[0] > 0  # higher RA is east
    assert finder.project(190, -20, 10, 20) is None

    def directions(orientation):
        cv = finder._Canvas(100, 0, 1.0, orientation)
        return cv.direction(0, 1), cv.direction(1, 0)  # north, east

    assert directions("north_up") == ((0, -1), (-1, 0))  # north up, east left
    assert directions("mirrored") == ((0, -1), (1, 0))
    assert directions("rotated") == ((0, 1), (1, 0))
    assert finder.angle_label(90) == "1.5°" and finder.angle_label(12) == "12'" and finder.angle_label(0.5) == '30"'


def test_render_draws_overlays():
    spec = finder.ChartSpec(10, 20, 1.0, "Test", "sub", "T", "credit", frame=finder.Frame(30, 20, 45, "cam"),
                            eyepiece_arcmin=20, eyepiece_label="25 mm", telrad=True,
                            objects=[finder.Marker("NGC 1", 10.2, 20.1, 3)])
    chart = finder.render(jpeg((400, 400)), spec, 400)
    header = 400 // 40 + 400 // 60 + 24
    assert chart.size == (400, 400 + header + 400 // 60 + 16)
    red = sum(1 for p in chart.get_flattened_data() if p[0] > 150 and p[1] < 80 and p[2] < 80)
    assert red > 500  # reticle, frame and eyepiece circle
    with pytest.raises(ValueError):
        finder.render(jpeg((400, 400)), finder.ChartSpec(10, 20, 1.0, "", "", "", "", orientation="sideways"), 400)


async def test_finder_chart_tool(fake_surveys):
    async with Client(mcp) as client:
        result = await client.call_tool("generate_finder_chart", {
            "target": "Neptune", "time": "2026-10-19T04:00Z", "focal_length_mm": 1000, "sensor": "asi533",
            "label_objects": False, "orientation": "mirrored", "size_px": 400})
        no_focal = await client.call_tool("generate_finder_chart", {"ra_deg": 10.0, "dec_deg": 20.0, "eyepiece_mm": 25})
    data = result.structured_content
    assert [c.type for c in result.content] == ["text", "image"]
    assert data["camera_frame"]["long_side_position_angle_deg"] == 90 and data["field_deg"] == pytest.approx(1.296, abs=0.002)
    assert "isn't in it" in data["note"] and data["saved_to"].endswith("_mirrored_print.png")
    assert no_focal.is_error and "focal_length_mm" in no_focal.content[0].text


# ------------------------------------------------------------------ plate solving


def card(key: str, value) -> bytes:
    text = f"'{value}'" if isinstance(value, str) else repr(value)
    return f"{key:<8}= {text:>20}".ljust(80).encode()


def wcs_bytes(cd) -> bytes:
    cards = [card("SIMPLE", "T"), card("CTYPE1", "RA---TAN-SIP"), card("IMAGEW", 2000), card("IMAGEH", 1000),
             *(card(k, v) for k, v in zip(("CD1_1", "CD1_2", "CD2_1", "CD2_2"), cd)), b"END".ljust(80)]
    return b"".join(cards).ljust(2880, b" ")


def test_fits_header_and_orientation():
    header = platesolve.fits_header(wcs_bytes((-1e-4, 0.0, 0.0, -1e-4)))
    assert header["CTYPE1"] == "RA---TAN-SIP" and header["IMAGEW"] == 2000 and header["CD1_1"] == -1e-4

    s = 1e-4
    normal = platesolve.orientation((-s, 0, 0, -s), 2000, 1000)  # north up, east left (rows count down)
    assert "top edge" in normal["north"] and "left edge" in normal["east"] and not normal["mirrored"]
    assert normal["image_up_position_angle_deg"] == 0 and normal["long_side_position_angle_deg"] == 90
    mirrored = platesolve.orientation((s, 0, 0, -s), 2000, 1000)
    assert mirrored["mirrored"] and "right edge" in mirrored["east"]
    # A real solve (nova job 14463352): up is west, so north points to the left edge.
    turned = platesolve.orientation((-2.514e-5, 4.985e-4, -5.0e-4, -2.641e-5), 2296, 1896)
    assert "left edge" in turned["north"] and "bottom edge" in turned["east"] and not turned["mirrored"]
    assert turned["image_up_position_angle_deg"] == pytest.approx(273.0, abs=0.2)


def test_prepare_uploads(tmp_path):
    big = tmp_path / "big.jpg"
    Image.new("RGB", (4000, 2000), (10, 10, 10)).save(big)
    up = platesolve.prepare(big)
    assert up.shrink == pytest.approx(4000 / 3000) and (up.width, up.height) == (4000, 2000)
    assert Image.open(io.BytesIO(up.data)).size == (3000, 1500)
    small = tmp_path / "small.png"
    Image.new("L", (800, 600)).save(small)
    assert platesolve.prepare(small).shrink == 1.0
    deep = tmp_path / "deep.tif"
    Image.new("I;16", (3500, 3500)).save(deep)
    assert platesolve.prepare(deep).shrink == 1.0  # 16-bit data isn't squeezed into 8 bits
    fits = tmp_path / "light.fits"
    fits.write_bytes(card("SIMPLE", "T") + card("NAXIS1", 1200) + card("NAXIS2", 800) + b"END".ljust(80))
    assert (platesolve.prepare(fits).width, platesolve.prepare(fits).height) == (1200, 800)
    fake = tmp_path / "notes.fits"
    fake.write_text("hello")
    for bad, match in ((tmp_path / "x.cr2", "can't read"), (fake, "not a FITS"), (tmp_path / "missing.jpg", "No file")):
        if bad.suffix == ".cr2":
            bad.write_bytes(b"raw")
        with pytest.raises(ValueError, match=match):
            platesolve.prepare(bad)


def test_hints():
    assert platesolve.hints(2.0, (1.0, 1.5), (10.0, 20.0), 5) == {
        "scale_units": "arcsecperpix", "scale_type": "ul", "scale_lower": 2.0, "scale_upper": 3.0,
        "center_ra": 10.0, "center_dec": 20.0, "radius": 5}
    assert platesolve.hints(1.0, None, None, 5) == {}


@pytest.fixture
def nova(monkeypatch, tmp_path):
    """A fake nova.astrometry.net: records posts, answers a job as `state`."""
    monkeypatch.setenv(platesolve.KEY_ENV, "test-key")
    monkeypatch.setattr(platesolve, "_sessions", {})
    sent = {"posts": [], "state": "success"}

    async def fake_post(url, data, *, source, files=None, timeout=60):
        payload = json.loads(data["request-json"])
        sent["posts"].append((url.rsplit("/", 1)[1], payload, files))
        return {"status": "success", "session": "sess"} if url.endswith("login") else {"status": "success", "subid": 42}

    async def fake_get_json(url, params=None, **kwargs):
        if url.endswith("/submissions/42"):
            return {"jobs": [None, 7]}
        if url.endswith("/jobs/7"):
            return {"status": sent["state"]}
        if url.endswith("/calibration/"):
            return {"ra": 83.82, "dec": -5.39, "pixscale": 1.5, "width_arcsec": 3000, "height_arcsec": 2000,
                    "orientation": 0.0, "parity": 1.0}
        if url.endswith("/info/"):
            return {"objects_in_field": ["M42", "Orion Nebula"]}
        raise UpstreamError("HTTP 404")

    async def fake_get_bytes(url, params=None, **kwargs):
        return wcs_bytes((-1.5 / 3600, 0, 0, -1.5 / 3600))

    monkeypatch.setattr(platesolve, "post_json", fake_post)
    monkeypatch.setattr(platesolve, "get_json", fake_get_json)
    monkeypatch.setattr(platesolve, "get_bytes", fake_get_bytes)
    image = tmp_path / "orion.jpg"
    Image.new("RGB", (4500, 3000), (5, 5, 5)).save(image)
    sent["image"] = image
    return sent


async def test_plate_solve_flow(nova):
    async with Client(mcp) as client:
        solved = await client.call_tool("plate_solve_image", {
            "image": str(nova["image"]), "focal_length_mm": 400, "sensor": "asi2600", "ra_deg": 83.8, "dec_deg": -5.4})
        nova["state"] = "solving"
        pending = await client.call_tool("plate_solve_image", {"submission_id": 42, "wait_seconds": 0})
        nova["state"] = "failure"
        failed = await client.call_tool("plate_solve_image", {"submission_id": 42, "wait_seconds": 0})
        neither = await client.call_tool("plate_solve_image", {})

    login, upload = nova["posts"][0], nova["posts"][1]
    assert login[0] == "login" and login[1] == {"apikey": "test-key"}
    hints = upload[1]
    assert upload[0] == "upload" and hints["publicly_visible"] == "n" and hints["allow_commercial_use"] == "n"
    assert hints["center_ra"] == 83.8 and hints["radius"] == 10.0
    native = 206.265 * 3.76 / 400  # 1.94"/px; the 4500 px image was shrunk 1.5x, so the hint is per uploaded pixel
    assert hints["scale_lower"] < native * 1.5 < hints["scale_upper"]
    assert upload[2]["file"][0] == "orion.jpg"

    data = solved.structured_content
    assert data["status"] == "solved" and data["center"]["constellation"] == "Orion"
    assert data["arcsec_per_pixel"] == pytest.approx(2.25)  # 1.5 per uploaded pixel x 1.5 shrink
    assert data["orientation"]["mirrored"] is False and "top edge" in data["orientation"]["north"]
    assert data["implied_focal_length_mm"] == round(206.265 * 3.76 / 2.25)
    assert data["objects_in_field"] == ["M42", "Orion Nebula"]
    assert pending.structured_content["status"] == "pending" and "submission_id=42" in pending.structured_content["message"]
    assert failed.structured_content["status"] == "failed" and "without them" in failed.structured_content["message"]
    assert neither.is_error


async def test_plate_solve_needs_a_key(monkeypatch, tmp_path):
    monkeypatch.delenv(platesolve.KEY_ENV, raising=False)
    image = tmp_path / "a.png"
    Image.new("L", (100, 100)).save(image)
    async with Client(mcp) as client:
        result = await client.call_tool("plate_solve_image", {"image": str(image)})
    assert result.is_error and platesolve.KEY_ENV in result.content[0].text
