"""Offline tests for observing-session planning, its exports, and meteor showers."""

import csv
import io
from datetime import UTC, date, datetime, timedelta

import pytest
from mcp import Client

from astronomy_mcp import catalog, conditions, mcp, meteors, session, sky
from astronomy_mcp.sky import Target
from conftest import MOAB
from test_sky import ADDENDUM_CSV, NGC_CSV

NIGHT = date(2026, 10, 10)  # new Moon at Moab
DARK = conditions.sqm_from_bortle(2)


def req(name, ra, dec, minutes=15, kind="deep_sky", ids=None, info=None):
    return session.Request(Target(name, None, ra, dec, "test", info or {}), name, minutes, ids or [name], kind)


def planet(name, minutes=15):
    return session.Request(Target(name, sky.BODIES[name.lower()]), name, minutes, [name], "solar_system")


def plan(requests, **kw):
    n = sky.night(MOAB, NIGHT)
    return session.plan(requests, MOAB, n, DARK, "telescope", 200, kw.pop("min_altitude", 25), None, **kw)


@pytest.fixture
def small_catalog(monkeypatch):
    monkeypatch.setattr(catalog, "_catalog", catalog.Catalog.from_csv_texts(NGC_CSV, ADDENDUM_CSV))


# ------------------------------------------------------------------ scheduling

def test_targets_setting_first_go_first_and_stay_high():
    # A low western target, one high overhead and one rising in the east, given in the wrong order.
    east, overhead, west = req("East", 30, 20), req("Overhead", 330, 40), req("West", 270, 10)
    out = plan([east, overhead, west])
    order = [row["target"] for row in out["schedule"]]
    assert order[0] == "West" and set(order) == {"East", "Overhead", "West"}
    n = sky.night(MOAB, NIGHT)
    for row in out["schedule"]:
        start, end = datetime.fromisoformat(row["start"]), datetime.fromisoformat(row["end"])
        assert n.window[0] <= start and end <= n.window[1] + timedelta(minutes=5)
        assert row["altitude_deg"]["start"] >= 25 and row["altitude_deg"]["end"] >= 25
    starts = [datetime.fromisoformat(row["start"]) for row in out["schedule"]]
    gaps = [(b - a).total_seconds() / 60 for a, b in zip(starts, starts[1:])]
    assert all(g >= 15 + 5 for g in gaps)  # 15-minute looks with 5 minutes to move


def test_planets_may_start_in_twilight_but_deep_sky_waits_for_dark():
    out = plan([planet("Saturn"), req("Globular", 250, 36)], start=None)
    rows = {row["target"]: row for row in out["schedule"]}
    n = sky.night(MOAB, NIGHT)
    assert datetime.fromisoformat(rows["Globular"]["start"]) >= n.window[0]
    assert "Saturn" in rows


def test_reasons_for_targets_that_do_not_fit():
    n = sky.night(MOAB, NIGHT)
    late = n.window[0] + timedelta(hours=2)
    out = plan([
        req("Southern", 180, -70),  # never rises at 38.6° N
        req("Morning", 85, -5),  # Orion: only up before dawn
        req("Long", 250, 36, minutes=600),  # longer than it is up
    ], end=late)
    reasons = {row["target"]: row["reason"] for row in out["unscheduled"]}
    assert reasons["Southern"].startswith("Never above 25°")
    assert "outside the session hours" in reasons["Morning"]
    assert "plan a shorter look" in reasons["Long"]
    assert out["scheduled_count"] == 0 and "schedule" in out


def test_a_full_session_explains_the_crowded_out_target():
    n = sky.night(MOAB, NIGHT)
    targets = [req(f"T{i}", 300 + i, 30, minutes=60) for i in range(8)]
    out = plan(targets, start=n.window[0], end=n.window[0] + timedelta(hours=3))
    assert out["scheduled_count"] < 8
    assert any(row["reason"].startswith("No free slot") for row in out["unscheduled"])


def test_too_faint_targets_are_left_out():
    faint = req("Faint galaxy", 330, 40, info={"magnitude": 15.5, "major_axis_arcmin": 3, "group": "galaxy"})
    out = plan([faint])
    assert out["scheduled_count"] == 0 and out["unscheduled"][0]["reason"].startswith("Too faint")


def test_clock_times_belong_to_the_night():
    n = sky.night(MOAB, NIGHT)
    assert session.clock_time("21:30", n, MOAB).isoformat() == "2026-10-10T21:30:00-06:00"
    assert session.clock_time("01:15", n, MOAB).isoformat() == "2026-10-11T01:15:00-06:00"
    assert session.clock_time(None, n, MOAB) is None


def test_exports():
    m13 = req("M 13", 250.42, 36.46, ids=["NGC 6205", "M 13"])
    sat = planet("Saturn")
    rows = [{"order": 1, "start": "a", "end": "b"}, {"order": 2, "start": "c", "end": "d"}]
    text = session.skysafari(list(zip([m13, sat], rows)))
    assert text.splitlines() == [
        "SkySafariObservingListVersion=3.0",
        "SkyObject=BeginObject", "\tObjectID=4,-1,-1", "\tCatalogNumber=NGC 6205", "\tCatalogNumber=M 13",
        "EndObject=SkyObject",
        "SkyObject=BeginObject", "\tObjectID=1,-1,-1", "\tCatalogNumber=Saturn", "EndObject=SkyObject",
    ]
    table = list(csv.DictReader(io.StringIO(session.csv_text(list(zip([m13, sat], rows)), datetime(2026, 10, 11, 3, tzinfo=UTC)))))
    assert table[0]["name"] == "M 13" and float(table[0]["ra_deg"]) == pytest.approx(250.42)
    assert table[1]["name"] == "Saturn" and table[1]["start"] == "c"


async def test_plan_tool_resolves_names_and_exports(moab, small_catalog, isolated_home):
    async with Client(mcp) as client:
        result = await client.call_tool("plan_observing_session", {
            "targets": ["M13", "Ring Nebula", "Saturn", "M31", "M13"], "date": "2026-10-10", "terrain": False,
            "minutes": {"M31": 30}, "start_time": "19:30", "end_time": "23:00", "export": "skysafari"})
    out = result.structured_content
    rows = {row["target"]: row for row in out["schedule"]}
    assert set(rows) == {"M 13", "M 57", "Saturn", "M 31"}  # the duplicate is dropped
    assert rows["M 31"]["minutes"] == 30
    assert out["equipment_used"].startswith("telescope, 150 mm")
    path = isolated_home / "lists" / "session_2026_10_10_Moab.skylist"
    assert out["export"]["saved_to"] == str(path)
    assert "CatalogNumber=NGC 6720" in path.read_text(encoding="utf-8")


# ------------------------------------------------------------------ meteor showers

@pytest.mark.parametrize("code, imo_peak_utc", [
    # 2026 maxima stated in the IMO calendar's text
    ("LYR", "2026-04-22T19:40"), ("PER", "2026-08-13T02:00"), ("LEO", "2026-11-17T23:45"),
    ("URS", "2026-12-22T22:00"),
])
def test_peak_times_match_the_imo_calendar(code, imo_peak_utc):
    peak = meteors.peak_time(meteors.find(code), datetime(2026, 1, 1, tzinfo=UTC))
    expected = datetime.fromisoformat(imo_peak_utc).replace(tzinfo=UTC)
    assert abs((peak - expected).total_seconds()) < 20 * 60


def test_geminid_range_from_the_calendar():
    # 'maxima within λ = 261.5 to 262.4, that is 2026 December 13, 21h to December 14, 18h UT'
    gem = meteors.find("Geminids")
    peak = meteors.peak_time(gem, datetime(2026, 12, 1, tzinfo=UTC))
    assert datetime(2026, 12, 13, 21, tzinfo=UTC) < peak < datetime(2026, 12, 14, 18, tzinfo=UTC)


@pytest.mark.parametrize("name, code", [("Perseids", "PER"), ("gem", "GEM"), ("eta Aquariids", "ETA"),
                                        ("4", "GEM"), ("Quadrantid", "QUA"), ("Leonids", "LEO")])
def test_find_showers(name, code):
    assert meteors.find(name).code == code


def test_find_unknown_or_ambiguous_shower():
    with pytest.raises(ValueError, match="No meteor shower"):
        meteors.find("Bananids")
    with pytest.raises(ValueError, match="several"):
        meteors.find("Taurids")


def test_activity_period_wraps_the_new_year():
    qua = meteors.find("QUA")
    assert meteors.is_active(qua, date(2026, 12, 30)) and meteors.is_active(qua, date(2027, 1, 5))
    assert not meteors.is_active(qua, date(2026, 6, 1))


def test_hourly_rate_formula():
    assert meteors.hourly_rate(100, 90, 6.5, 2.2) == pytest.approx(100)
    assert meteors.hourly_rate(100, 30, 6.5, 2.2) == pytest.approx(50)
    assert meteors.hourly_rate(100, 90, 5.5, 2.0) == pytest.approx(50)
    assert meteors.hourly_rate(100, -5, 6.5, 2.2) == 0


def test_zhr_falls_away_from_the_peak():
    qua, peak = meteors.find("QUA"), datetime(2026, 1, 3, 21, tzinfo=UTC)
    assert meteors.zhr_at(qua, peak, peak) == 80
    assert meteors.zhr_at(qua, peak + timedelta(hours=4), peak) == pytest.approx(40, rel=0.02)  # 8 h wide at half
    assert meteors.zhr_at(meteors.find("JBO"), peak, peak) is None


def test_peak_nights_rated_for_moonlight_and_radiant():
    gem = meteors.find("GEM")
    peak = meteors.peak_time(gem, datetime(2026, 12, 1, tzinfo=UTC))
    night = meteors.rate_night(gem, peak, MOAB, meteors.peak_night(MOAB, peak), DARK)
    assert night["night"] == "2026-12-13" and night["rating"] == "excellent"
    assert 60 < night["expected_meteors_per_hour"] < 150

    urs = meteors.find("URS")  # 2026: two days before full Moon
    peak = meteors.peak_time(urs, datetime(2026, 12, 1, tzinfo=UTC))
    night = meteors.rate_night(urs, peak, MOAB, meteors.peak_night(MOAB, peak), DARK)
    assert night["rating"] == "poor" and night["limiting_magnitude_at_best"] < 5

    pup = meteors.find("PUP")  # radiant at -45°: barely rises at Moab
    peak = meteors.peak_time(pup, datetime(2026, 12, 1, tzinfo=UTC))
    night = meteors.rate_night(pup, peak, MOAB, meteors.peak_night(MOAB, peak), DARK)
    assert night["radiant_peak_altitude_deg"] < 10 and night["rating"] == "poor"


def test_upcoming_skips_minor_showers_by_default():
    start = datetime(2026, 11, 23, tzinfo=UTC)
    major = [s.code for s, _ in meteors.upcoming(start, 60, include_minor=False)]
    assert major == ["PUP", "HYD", "GEM", "URS", "QUA"]
    everything = [s.code for s, _ in meteors.upcoming(start, 60, include_minor=True)]
    assert {"PHO", "MON", "COM"} <= set(everything) and len(everything) > len(major)


async def test_meteor_tool(moab):
    async with Client(mcp) as client:
        listing = (await client.call_tool("get_meteor_showers", {"start_date": "2026-11-23", "days": 30})).structured_content
        one = (await client.call_tool("get_meteor_showers", {"shower": "Perseids", "start_date": "2026-07-01"})).structured_content
        nowhere = await client.call_tool("get_meteor_showers", {"shower": "Bananids"})
    gem = next(s for s in listing["showers"] if s["code"] == "004 GEM")
    assert gem["peak_night"]["rating"] == "excellent" and gem["zhr"] == 150
    assert listing["active_now"] == ["Northern Taurids", "Leonids"]
    assert listing["sky_brightness_source"] == "Bortle 2 from saved location"
    assert one["shower"]["peak_utc"].startswith("2026-08-13T0")
    assert [n["night"] for n in one["nights"]] == ["2026-08-11", "2026-08-12", "2026-08-13"]
    assert nowhere.is_error
