"""Offline tests for double stars, variable stars, supernovae, novae and the Deep Space Network."""

from datetime import UTC, date, datetime, timedelta

import pytest
from mcp import Client

from astronomy_mcp import catalog, doubles, dsn, mcp, transients, variables

from conftest import MOAB


# ------------------------------------------------------------------ names

@pytest.mark.parametrize("name, expected", [
    ("epsilon Lyrae", "eps Lyr"), ("Alpha Centauri", "alf Cen"), ("61 Cygni", "61 Cyg"),
    ("theta1 Orionis", "tet1 Ori"), ("zeta Ursae Majoris", "zet UMa"), ("gamma Leo", "gam Leo"),
    ("Mizar", None), ("M 31", None),
])
def test_bayer_to_simbad(name, expected):
    assert catalog.bayer_to_simbad(name) == expected


# ------------------------------------------------------------------ double stars

def test_discoverer_codes_match_the_wds_field():
    assert doubles.discoverer_code("STF 2382") == "STF2382"
    assert doubles.discoverer_code("stfa 37") == "STFA 37"
    assert doubles.discoverer_code("BU 1") == "BU    1"
    assert doubles.discoverer_code("Albireo") is None


def test_split_rule():
    # Equal pair at the Dawes limit of 100 mm in excellent seeing: just splittable.
    assert doubles.required_separation(100, 1.0, 0) == pytest.approx(1.16)
    # Poor seeing dominates a big aperture.
    assert doubles.required_separation(300, 3.0, 0) == pytest.approx(1.8)
    # Brightness differences make it harder, and much harder past 5 magnitudes.
    assert doubles.required_separation(100, 1.0, 4) == pytest.approx(1.16 * 2.2)
    assert doubles.required_separation(100, 1.0, 10) > 8
    rigel = doubles.assess(9.4, 0.3, 6.8, 100, 1.0)
    assert rigel["splittable"] and rigel["difficulty"] == "moderate" and rigel["suggested_magnification"] >= 50
    assert doubles.assess(2.1, 5.15, 6.1, 60, 1.0)["splittable"] is False
    assert "too faint" in doubles.assess(20, 5, 13.5, 60, 2)["reason"]
    assert doubles.assess(None, 5, 6, 100, 2)["splittable"] is None


def test_shape_pair_cleans_wds_placeholders():
    row = {"WDS": "19307+2758", "Disc": "STFA 43", "Comp": "AB", "Obs1": 1755, "Obs2": 2025, "Nobs": 300, "pa2": 54,
           "sep2": 34.3, "mag1": 3.19, "mag2": 4.68, "SpType": "K3II+B9.5V", "Notes": "  ", "RAJ2000": 292.68033,
           "DEJ2000": 27.95969}
    pair = doubles.shape_pair(row, 80, 2.0)
    assert pair["discoverer"] == "STFA 43" and pair["magnitudes"] == [3.19, 4.68] and "notes" not in pair
    assert pair["with_your_telescope"]["difficulty"] == "easy"
    unknown = doubles.shape_pair({**row, "sep2": -1, "pa2": -1, "Obs2": -1, "Comp": ""}, None, 2.0)
    assert "separation_arcsec" not in unknown and unknown["components"] == "AB" and "with_your_telescope" not in unknown


async def test_double_star_lookup_by_name(monkeypatch):
    queries = []

    async def fake_simbad(ident, max_aliases=25):
        return {"main_id": "* eps01 Lyr", "ra_deg": 281.0846, "dec_deg": 39.6703} if ident == "eps1 Lyr" else None

    async def fake_query(adql):
        queries.append(adql)
        base = {"WDS": "18443+3940", "Obs2": 2021, "RAJ2000": 281.0846, "DEJ2000": 39.6703}
        return [{**base, "Disc": "STFA 37", "Comp": "AB,CD", "sep2": 209.4, "mag1": 4.67, "mag2": 4.56},
                {**base, "Disc": "STF2382", "Comp": "AB", "sep2": 2.1, "mag1": 5.15, "mag2": 6.1},
                {**base, "Disc": "STF2383", "Comp": "CD", "sep2": 2.4, "mag1": 5.25, "mag2": 5.38}]

    monkeypatch.setattr(doubles.simbad, "lookup", fake_simbad)
    monkeypatch.setattr(doubles, "run_query", fake_query)
    result = await doubles.lookup("epsilon Lyrae", 150, 1.5)
    assert result["wds"] == "18443+3940" and result["constellation"] == "Lyra"
    assert [p["discoverer"] for p in result["pairs"]] == ["STF2382", "STF2383", "STFA 37"]  # close pairs first
    assert result["pairs"][0]["with_your_telescope"]["splittable"] is True
    assert "CONTAINS" in queries[0]


# ------------------------------------------------------------------ variable stars

OBS_TEXT = """JD|mag|uncert|band|by|comCode|compStar1|compStar2|charts|comment|transformed|airmass|val|cmag|kmag|starName|obsAffil|mtype|adsRef|digitizer|credit|obsID|fainterThan|obsType|software|obsName|obsCountry
{jd0}|9.1||Vis.|ABC||1|2|X||0||Z|||SS Cyg|||||| 1|0|Visual|VObs, version 2.2.0|Doe, Jane|US
{jd1}|9.4|0.01|V|DEF||1|2|X||1|1.1|V|||SS Cyg||||||2|0|CCD|||DE
{jd2}|<12.0||Vis.|GHI||1|2|X||0||Z|||SS Cyg||||||3|1|Visual|||FR
{jd3}|5.0||Vis.|XYZ||1|2|X||0||T|||SS Cyg||||||4|0|Visual|||FR
"""


def test_parse_observations_keeps_measurements_and_limits_apart():
    now = variables.julian(datetime.now(UTC))
    obs = variables.parse_observations(OBS_TEXT.format(jd0=now - 2, jd1=now - 1, jd2=now - 0.5, jd3=now - 0.2))
    assert [o.mag for o in obs] == [9.1, 9.4, 12.0]  # the discrepant (val T) row is dropped
    assert obs[2].fainter_than and not obs[0].fainter_than and obs[1].band == "V" and obs[0].kind == "Visual"
    assert variables.parse_observations("") == []


def test_predictions_for_eclipses_and_maxima():
    now = datetime(2026, 10, 7, tzinfo=UTC)
    algol = {"variability_type": "EA/SD", "period_days": 2.867343, "epoch_hjd": 2460000.0}
    pred = variables.predictions(algol, now, MOAB)
    nxt = datetime.fromisoformat(pred["next_primary_eclipse"])
    assert timedelta(0) < nxt - now <= timedelta(days=2.868) and len(pred["upcoming_eclipses"]) == 3
    mira = {"variability_type": "M", "period_days": 331.96, "epoch_hjd": 2460000.0}
    assert "next_maximum" in variables.predictions(mira, now, None)
    assert variables.predictions({"variability_type": "UGSS"}, now, None) is None


async def test_variable_status_summarises_recent_observations(monkeypatch):
    now = variables.julian(datetime.now(UTC))

    async def fake_lookup(name):
        return {"name": "SS Cyg", "variability_type": "UGSS", "max_mag": {"value": 7.7}, "min_mag": {"value": 12.4}}

    async def fake_observations(name, days, end=None):
        rows = [variables.Observation(now - 10 + k, 12.0 - 0.3 * k, "Vis.", False, "Visual") for k in range(10)]
        return rows + [variables.Observation(now - 0.1, 13.5, "Vis.", True, "Visual")]

    monkeypatch.setattr(variables.vsx, "lookup", fake_lookup)
    monkeypatch.setattr(variables, "observations", fake_observations)
    status = await variables.status("SS Cyg", 30, MOAB)
    assert status["latest"]["magnitude"] == pytest.approx(9.3)
    assert status["trend_last_14_days"]["direction"] == "brightening"
    assert status["within_range"]["outburst"] is True
    curve = await variables.light_curve("SS Cyg", 30, ["vis."], 5, None)
    points = curve["light_curve"]["Vis."]
    assert curve["bin_days"] == 5 and sum(p["n"] for p in points) == 11 and "fainter_than" in points[-1] or points[-1]["mag"]
    with pytest.raises(ValueError, match="limited"):
        await variables.light_curve("SS Cyg", 5000, None, None, None)


# ------------------------------------------------------------------ supernovae and novae

ROCHESTER = """<b>All active supernova over mag 17.0</b>
<table>
<tr><th>Name</th><th>Mag</th><th>Type</th><th>Host</th></tr>
<tr><td><a href="#2026sqf" target="_self">2026sqf</a></td><td>12.5</td><td>Ia-CSM</td><td><a href="x">NGC 3310</a></td></tr>
<tr><td><a href="novae.html#2026aaom" target="_self">AT2026aaom</a></td><td>15.3</td><td>EGN</td><td><a href="x">M31</a></td></tr>
<tr><td><a href="#2026zsr" target="_self">AT2026zsr</a></td><td>16.2*</td><td>unk</td><td><a href="x">LEDA 4105377</a></td></tr>
</table>
<a id="2026sqf">2026sqf</a>
(= ZTF26abfmmvq) (= AT2026uxt),
<a href="https://www.wis-tns.org/object/2026sqf">TNS</a>
discovered 2026/07/08.251 by
<a href="https://en.wikipedia.org/wiki/Patrick_Wiggins_(astronomer)">Patrick Wiggins</a>
<br />Found in <a href="https://ned.ipac.caltech.edu/byname?objname=NGC+3310">NGC 3310</a>
at <a href="http://www.wikisky.org/?ra=10.646656&de=53.509472"
>R.A. = 10h38m47s.961, Decl. = +53&deg;30'34".10</a>
<br />Mag 12.5:10/1 (11.2:7/28), Type Ia-CSM (z=0.003310)
<a id="2026zsr">AT2026zsr</a>
discovered 2026/09/20.5 by ATLAS
<br />at R.A. = 12h34m17s.316, Decl. = -36&deg;30'41".04
<br />Mag 16.2*:9/30, Type unk
"""


def test_parse_supernova_page():
    found = transients.parse_supernova_page(ROCHESTER, date(2026, 10, 7))
    sn = found[0]
    assert sn["name"] == "2026sqf" and sn["also_known_as"] == ["ZTF26abfmmvq", "AT2026uxt"]
    assert sn["discovered"] == "2026-07-08" and sn["discovered_by"] == "Patrick Wiggins" and sn["host"] == "NGC 3310"
    assert sn["ra_deg"] == pytest.approx(159.69984, abs=1e-4) and sn["dec_deg"] == pytest.approx(53.50947, abs=1e-4)
    assert (sn["magnitude"], sn["magnitude_date"], sn["peak_magnitude"], sn["peak_date"]) == (12.5, "2026-10-01", 11.2, "2026-07-28")
    assert sn["type"] == "Ia-CSM" and sn["redshift"] == 0.00331
    assert found[1]["type"] == "EGN" and "ra_deg" not in found[1]  # detail lives on the novae page
    assert found[2]["magnitude"] == 16.2 and found[2]["dec_deg"] < 0 and "magnitude_note" in found[2]
    with pytest.raises(transients.UpstreamError):
        transients.parse_supernova_page("<html>redesigned</html>", date(2026, 10, 7))


def test_month_day_stays_in_the_past():
    assert transients._month_day("12", "30", date(2027, 1, 3)) == "2026-12-30"
    assert transients._month_day("1", "2", date(2027, 1, 3)) == "2027-01-02"


MUKAI = """<H2>Galactic Novae in 2026 (2 so far)</H2>
<TABLE BORDER=1>
<TR><TH>Name(s)</TH><TH>Position</TH><TH>Discovery</TH><TH>Peak</TH><TH>Disc. Ref</TH><TH>Notes</TH></TR>
<TR><TD><A HREF="https://vsx.aavso.org/x"><FONT COLOR=RED>V488 Sge</FONT></A><BR>Nova Sagittae 2026</BR>PNV J19450648+1822422</TD>
    <TD>19 45 06.49<BR>+18 22 42.1</TD><TD>2026-08-25</TD><TD>7.1</TD>
    <TD>CBET 5729</TD><TD><A HREF="x">ARAS</A></TD></TR>
<TR><TD>PRIME26ahygn<BR>Nova in Ophiuchus</TD>
    <TD>17 42 10.63<BR>-25 24 57..9</TD><TD>2026-03-28</TD><TD>H=11.1</TD>
    <TD>ATel 17945</TD><TD>First detection after a seasonal data gap</TD></TR>
</TABLE>"""


def test_parse_mukai_table():
    rows = transients.parse_mukai_table(MUKAI, 2026)
    assert [r["name"] for r in rows] == ["V488 Sge", "PRIME26ahygn"]
    assert rows[0]["also_known_as"] == ["Nova Sagittae 2026", "PNV J19450648+1822422"] and "notes" not in rows[0]
    assert rows[0]["ra_deg"] == pytest.approx(296.27704, abs=1e-4) and rows[0]["peak_magnitude"] == 7.1
    assert rows[1]["dec_deg"] == pytest.approx(-25.41608, abs=1e-4) and rows[1]["peak_band"] == "H"
    assert transients.parse_mukai_table(MUKAI, 2019) == []


# ------------------------------------------------------------------ Deep Space Network

DSN_CONFIG = """<config><sites><site name="gdscc" friendlyName="Goldstone"><dish name="DSS26" type="34MBWG"></dish></site></sites>
<spacecraftMap><spacecraft name="lucy" friendlyName="Lucy"></spacecraft><spacecraft name="mms4" friendlyName="MMS 4"></spacecraft></spacecraftMap></config>"""
DSN_STATUS = """<dsn>
<station name="gdscc" friendlyName="Goldstone" timeUTC="1791399564000" timeZoneOffset="-25200000.0"/>
<dish name="DSS14" azimuthAngle="0" elevationAngle="90" activity="Engineering Upgrades"><target name="DSN" id="99" uplegRange="-1" downlegRange="-1" rtlt="-1"/></dish>
<dish name="DSS26" azimuthAngle="144" elevationAngle="30" isArray="false" activity="Spacecraft Telemetry, Tracking, and Command">
  <upSignal active="true" signalType="data" dataRate="0" band="X" power="18" spacecraft="LUCY"/>
  <downSignal active="true" signalType="data" dataRate="20000" band="X" power="-140" spacecraft="LUCY"/>
  <target name="LUCY" id="49" uplegRange="896000000" downlegRange="896000000" rtlt="-1"/>
</dish>
<dish name="DSS24" azimuthAngle="10" elevationAngle="40" activity="Tracking">
  <downSignal active="false" signalType="none" dataRate="0" band="S" power="0" spacecraft="MMS4"/>
  <target name="MMS4" id="113" uplegRange="149000" downlegRange="-1" rtlt="-1"/>
</dish>
</dsn>"""


def test_dsn_parsing():
    craft, dishes = dsn.parse_config(DSN_CONFIG)
    assert craft["lucy"] == "Lucy" and dishes["DSS26"] == "34 m (beam waveguide)"
    report = dsn.parse_status(DSN_STATUS, craft, dishes)
    assert report["updated_utc"].startswith("2026-10-07")
    lucy, mms = report["spacecraft"]
    assert lucy["spacecraft"] == "Lucy" and lucy["antennas"] == ["DSS26 (Goldstone)"]
    assert lucy["distance"]["au"] == pytest.approx(5.989, abs=0.001) and lucy["distance"]["one_way_light_time"] == "49.8 min"
    assert lucy["receiving_data"] and lucy["sending_commands"]
    assert mms["distance"]["km"] == 149000 and not mms["receiving_data"]
    antennas = report["stations"][0]["antennas"]
    assert "targets" not in antennas[0]  # DSN placeholder target is hidden
    assert antennas[1]["downlink"][0]["data_rate_bps"] == 20000


async def test_dsn_tool_filters_by_spacecraft(monkeypatch):
    async def fake_text_file(url, path, **kwargs):
        return DSN_CONFIG

    async def fake_text(url, params=None, **kwargs):
        return DSN_STATUS

    monkeypatch.setattr(dsn, "get_text_file", fake_text_file)
    monkeypatch.setattr(dsn, "get_text", fake_text)
    async with Client(mcp) as client:
        data = (await client.call_tool("get_dsn_status", {"spacecraft": "lucy"})).structured_content
        none = (await client.call_tool("get_dsn_status", {"spacecraft": "Voyager"})).structured_content
    assert data["count"] == 1 and data["spacecraft"][0]["spacecraft"] == "Lucy" and "stations" not in data
    assert none["count"] == 0 and "Voyager" in none["message"]
