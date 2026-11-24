"""Offline tests for saved equipment, the observing log and catalogue progress."""

import pytest
from mcp import Client

from astronomy_mcp import catalog, equipment, mcp, obslog
from test_sky import ADDENDUM_CSV, NGC_CSV


@pytest.fixture
def small_catalog(monkeypatch):
    """The test_sky extract (M31, M13, M57, the Pleiades, Caldwell 41) in place of the OpenNGC download."""
    cat = catalog.Catalog.from_csv_texts(NGC_CSV, ADDENDUM_CSV)
    monkeypatch.setattr(catalog, "_catalog", cat)
    return cat


async def call(name, args):
    async with Client(mcp) as client:
        result = await client.call_tool(name, args)
    return result


@pytest.fixture
def dob():
    equipment.save("telescope", {"name": "8-inch Dob", "type": "telescope", "aperture_mm": 203, "focal_length_mm": 1200})
    equipment.save("eyepiece", {"name": "25 mm", "focal_length_mm": 25})
    equipment.save("eyepiece", {"name": "8 mm", "focal_length_mm": 8, "afov_deg": 82})
    equipment.save("camera", {"name": "ASI533MC", "sensor": "asi533"})


# ------------------------------------------------------------------ equipment store

def test_first_saved_is_default_and_make_default_moves_it():
    equipment.save("telescope", {"name": "Dob", "type": "telescope", "aperture_mm": 203, "focal_length_mm": 1200})
    equipment.save("telescope", {"name": "Refractor", "type": "telescope", "aperture_mm": 80, "focal_length_mm": 480})
    assert equipment.telescope()["name"] == "Dob"
    equipment.save("telescope", {"name": "Refractor", "type": "telescope", "aperture_mm": 80, "focal_length_mm": 480},
                   make_default=True)
    assert equipment.telescope()["name"] == "Refractor"
    assert sum(bool(s.get("default")) for s in equipment.load()["telescopes"]) == 1
    equipment.remove("telescope", "refractor")
    assert equipment.telescope()["name"] == "Dob"  # the default passes to what's left


def test_saving_same_name_replaces_and_keeps_default():
    equipment.save("camera", {"name": "Main", "sensor": "asi2600"})
    item, replaced = equipment.save("camera", {"name": "main", "sensor": "asi533"})
    assert replaced and item["default"]
    assert [c["sensor"] for c in equipment.load()["cameras"]] == ["asi533"]


def test_binoculars_and_telescopes_are_told_apart():
    equipment.save("telescope", {"name": "10x50", "type": "binoculars", "aperture_mm": 50, "magnification": 10})
    equipment.save("telescope", {"name": "Dob", "type": "telescope", "aperture_mm": 203, "focal_length_mm": 1200})
    assert equipment.telescope(kind="telescope")["name"] == "Dob"
    assert equipment.telescope(kind="binoculars")["name"] == "10x50"
    assert equipment.describe(equipment.telescope("10x50")) == "saved binoculars '10x50' (10x50)"


@pytest.mark.parametrize("kind, item, message", [
    ("telescope", {"name": "Dob", "type": "telescope", "aperture_mm": 203}, "focal_length_mm"),
    ("telescope", {"name": "Dob", "type": "telescope", "focal_length_mm": 1200}, "aperture_mm"),
    ("eyepiece", {"name": "Plossl"}, "focal_length_mm"),
    ("camera", {"name": "Cam"}, "sensor"),
    ("camera", {"name": "Cam", "sensor": "nonsense"}, "Unknown sensor"),
    ("eyepiece", {"name": "", "focal_length_mm": 10}, "name"),
])
def test_invalid_equipment_is_rejected(kind, item, message):
    with pytest.raises(ValueError, match=message):
        equipment.save(kind, item)


def test_nearest_eyepiece_and_views(dob):
    assert equipment.nearest_eyepiece(1200, 140) == "8 mm (150x)"
    assert equipment.nearest_eyepiece(1200, 40) == "25 mm (48x)"
    views = equipment.eyepiece_views(1200, 203)
    assert [v["magnification"] for v in views] == [48, 150]  # low power first
    assert views[1]["true_field_arcmin"] == round(82 / 150 * 60)


def test_unknown_saved_telescope_name_lists_what_is_saved(dob):
    with pytest.raises(ValueError, match="8-inch Dob"):
        equipment.telescope("C11")


# ------------------------------------------------------------------ tools that use saved equipment

async def test_save_equipment_tool_works_out_focal_length():
    out = (await call("save_equipment", {"kind": "telescope", "name": "Dob", "aperture_mm": 200, "focal_ratio": 6})).structured_content
    assert out["saved"]["focal_length_mm"] == 1200
    assert out["now_saved"]["telescopes"] == ["Dob (default)"]
    eyepiece = (await call("save_equipment", {"kind": "eyepiece", "name": "10 mm", "focal_length_mm": 10})).structured_content
    assert eyepiece["on_default_telescope"]["magnification"] == 120
    removed = (await call("save_equipment", {"kind": "eyepiece", "name": "10 mm", "remove": True})).structured_content
    assert removed["now_saved"]["eyepieces"] == []


async def test_field_of_view_with_nothing_named_uses_saved_setup(dob):
    out = (await call("calculate_field_of_view", {})).structured_content
    assert out["focal_length_mm"] == 1200
    assert out["camera"]["sensor"].startswith("ASI533MC")
    assert [e["eyepiece"] for e in out["saved_eyepieces"]] == ["25 mm", "8 mm"]
    assert "8-inch Dob" in out["telescope_used"]


async def test_field_of_view_without_saved_equipment_still_asks():
    result = await call("calculate_field_of_view", {"sensor": "asi533"})
    assert result.is_error and "focal_length_mm" in result.content[0].text


async def test_saved_camera_name_works_as_sensor(dob):
    out = (await call("frame_target", {"target": "Moon", "focal_length_mm": 400, "sensor": "asi533mc"})).structured_content
    assert out["sensor"].startswith("ASI533MC") and out["focal_length_mm"] == 400


async def test_visibility_uses_saved_telescope_and_suggests_an_eyepiece(moab, dob):
    out = (await call("is_visible_tonight", {"target": "Saturn", "date": "2026-10-10", "terrain": False})).structured_content
    assert out["sky_assumed"]["aperture_mm"] == 203
    assert out["equipment_used"].startswith("saved telescope '8-inch Dob'")
    assert out["suggested_eyepiece"] in ("8 mm (150x)", "25 mm (48x)")
    eye = (await call("is_visible_tonight", {"target": "Saturn", "date": "2026-10-10", "terrain": False,
                                             "equipment": "naked_eye"})).structured_content
    assert eye["equipment_used"] == "naked eye" and "suggested_eyepiece" not in eye


async def test_visibility_without_saved_equipment_says_it_assumed(moab):
    out = (await call("is_visible_tonight", {"target": "Saturn", "date": "2026-10-10", "terrain": False})).structured_content
    assert out["equipment_used"].startswith("telescope, 150 mm (assumed")


# ------------------------------------------------------------------ observing log

def test_catalog_numbers_prefers_what_the_user_typed(small_catalog):
    m31 = small_catalog.lookup("M31")
    assert obslog.catalog_numbers("Andromeda Galaxy", m31) == {"messier": 31}
    assert obslog.catalog_numbers("M102", m31) == {"messier": 102}  # OpenNGC files M102 under M101
    assert obslog.catalog_numbers("Caldwell 41", small_catalog.lookup("Hyades")) == {"caldwell": 41}
    assert obslog.catalog_numbers("x", {"name": "IC 342", "other_ids": ["2MASX J0346", "C 005"]}) == {"caldwell": 5}


def test_progress_counts_only_sightings():
    for n, seen in ((13, True), (13, True), (74, False), (57, True)):
        obslog.add({"target": f"M{n}", "time": "2026-10-10T22:00-06:00", "seen": seen, "messier": n})
    first, missing = obslog.progress(obslog.load(), "messier")
    assert sorted(first) == [13, 57]
    assert len(missing) == 108 and 74 in missing


async def test_log_history_and_delete(moab, dob, small_catalog):
    logged = (await call("log_observation", {"target": "M13", "time": "2026-07-15T23:10", "eyepiece": "8 mm",
                                             "notes": "resolved"})).structured_content
    entry = logged["logged"]
    assert entry["messier"] == 13 and entry["name"] == "M 13"
    assert entry["instrument"] == "8-inch Dob" and entry["magnification"] == 150
    assert entry["night"] == "2026-07-15" and entry["altitude_deg"] > 70
    assert logged["catalog_progress"] == {"messier": "1 of 110 seen"}

    missed = (await call("log_observation", {"target": "Ring Nebula", "time": "2026-07-16T01:30", "seen": False,
                                             "equipment": "binoculars"})).structured_content["logged"]
    assert missed["night"] == "2026-07-15" and missed["instrument"] == "binoculars"

    history = (await call("get_observing_history", {"target": "Hercules Globular Cluster"})).structured_content
    assert history["count"] == 1 and history["summary"]["first_seen"] == "2026-07-15T23:10-06:00"
    both = (await call("get_observing_history", {"since": "2026-07-15"})).structured_content
    assert both["summary"] == {"observations": 2, "distinct_objects_seen": 1, "nights": 1, "not_found": 1,
                               "first": "2026-07-15T23:10-06:00", "latest": "2026-07-16T01:30-06:00"}

    await call("delete_observation", {"observation_id": entry["id"]})
    assert [e["id"] for e in obslog.load()] == [missed["id"]]
    assert (await call("delete_observation", {"observation_id": 99})).is_error


async def test_log_rejects_future_and_keeps_unknown_targets(moab, small_catalog, monkeypatch):
    assert (await call("log_observation", {"target": "Saturn", "time": "2099-01-01T21:00"})).is_error

    async def nothing(*_args, **_kwargs):
        return None
    monkeypatch.setattr("astronomy_mcp.simbad.lookup", nothing)
    out = (await call("log_observation", {"target": "Aurora borealis", "time": "2026-10-10T23:00"})).structured_content
    assert out["logged"]["target"] == "Aurora borealis" and "name" not in out["logged"]
    assert "Not matched" in out["warning"]


async def test_catalog_progress_suggests_unseen_objects_up_tonight(moab, small_catalog):
    obslog.add({"target": "M13", "time": "2026-07-15T23:10-06:00", "seen": True, "messier": 13})
    out = (await call("get_catalog_progress", {"date": "2026-10-10", "terrain": False})).structured_content
    assert out["seen"] == 1 and out["total"] == 110
    assert out["seen_list"] == [{"number": "M 13", "first_seen": "2026-07-15T23:10-06:00"}]
    assert out["not_seen"][0] == {"number": "M 1"}  # not in the test extract, so no details
    tonight = {row["number"] for row in out["up_tonight_not_seen"]}
    assert {"M 31", "M 45"} <= tonight and "M 13" not in tonight
    caldwell = (await call("get_catalog_progress", {"catalog_name": "caldwell", "suggest_tonight": False})).structured_content
    assert caldwell["seen"] == 0 and caldwell["total"] == 109 and "up_tonight_not_seen" not in caldwell
