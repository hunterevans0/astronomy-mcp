"""Offline tests for response parsing and input validation."""

import httpx
import pytest

from astronomy_mcp import simbad, vsx


def test_adql_str_escapes_quotes():
    assert simbad._adql_str("Barnard's Star") == "'Barnard''s Star'"


def test_simbad_rows_and_shape():
    payload = {
        "metadata": [{"name": n} for n in ("main_id", "ra", "dec", "otype", "plx_value", "V", "ids")],
        "data": [["M  31  ", 10.68, 41.27, "AGN", 4.0, 3.44, "M  31|NGC   224|NAME Andromeda"]],
    }
    rows = simbad._rows(payload)
    assert rows[0]["main_id"] == "M 31"
    shaped = simbad._shape_object(rows[0], max_aliases=2)
    assert shaped["aliases"] == ["M 31", "NGC 224"]
    assert shaped["alias_count"] == 3
    assert shaped["magnitudes"] == {"V": 3.44}
    assert shaped["distance_pc_from_parallax"] == 250.0
    assert "spectral_type" not in shaped  # None values are dropped


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("4.4 V", {"raw": "4.4 V", "band": "V", "value": 4.4}),
        ("(0.30) CV", {"raw": "(0.30) CV", "band": "CV", "value": 0.30, "is_amplitude": True}),
        ("<15.2 B", {"raw": "<15.2 B", "band": "B", "value": 15.2, "limit": "<"}),
        ("12.1: V", {"raw": "12.1: V", "band": "V", "value": 12.1}),
        (None, None),
    ],
)
def test_vsx_parse_mag(raw, expected):
    assert vsx._parse_mag(raw) == expected


def test_vsx_shape():
    shaped = vsx._shape({"Name": "R Leo", "OID": "17032", "Period": "312.2", "RA2000": "146.88954", "MaxMag": "4.4 V"})
    assert shaped["period_days"] == 312.2
    assert shaped["ra_deg"] == 146.88954
    assert shaped["max_mag"]["value"] == 4.4
    assert shaped["vsx_url"].endswith("oid=17032")


def test_angular_separation():
    assert vsx._angular_sep_arcmin(10, 20, 10, 21) == pytest.approx(60, abs=1e-6)
    # Wraps correctly across RA = 0
    assert vsx._angular_sep_arcmin(359.5, 0, 0.5, 0) == pytest.approx(60, abs=1e-6)


async def test_simbad_cone_rejects_bad_otype():
    with pytest.raises(ValueError):
        await simbad.cone_search(10, 10, 1, object_type="G' OR 1=1 --")


TAP_ROWS = {"metadata": [{"name": "main_id"}], "data": [["M  57"]]}


def _tap_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_simbad_fails_over_to_mirror_and_remembers_it(monkeypatch):
    monkeypatch.setattr(simbad, "_preferred", 0)
    hosts = []

    def handler(request):
        hosts.append(request.url.host)
        if request.url.host == "simbad.cds.unistra.fr":  # the outage: an HTML 404 page
            return httpx.Response(404, html="<!doctype html><title>Page unavailable</title>")
        return httpx.Response(200, json=TAP_ROWS)

    async with _tap_client(handler) as client:
        assert await simbad.run_adql("SELECT", client) == [{"main_id": "M 57"}]
        assert await simbad.run_adql("SELECT", client) == [{"main_id": "M 57"}]
    assert hosts == ["simbad.cds.unistra.fr", "simbad.cfa.harvard.edu", "simbad.cfa.harvard.edu"]


async def test_simbad_reports_every_endpoint_when_all_fail(monkeypatch):
    monkeypatch.setattr(simbad, "_preferred", 0)

    def handler(request):
        if request.url.host == "simbad.idia.ac.za":
            raise httpx.ConnectTimeout("timed out")
        return httpx.Response(503, html="<html>down</html>")

    async with _tap_client(handler) as client:
        with pytest.raises(simbad.SimbadError) as err:
            await simbad.run_adql("SELECT", client)
    message = str(err.value)
    assert all(host in message for host in ("simbad.cds.unistra.fr", "simbad.cfa.harvard.edu", "simbad.idia.ac.za"))
    assert "<html" not in message


async def test_simbad_bad_query_is_not_retried_on_mirrors(monkeypatch):
    monkeypatch.setattr(simbad, "_preferred", 0)
    hosts = []

    def handler(request):
        hosts.append(request.url.host)
        return httpx.Response(400, text="Incorrect ADQL query")

    async with _tap_client(handler) as client:
        with pytest.raises(simbad.SimbadError, match="rejected the query"):
            await simbad.run_adql("SELEKT", client)
    assert hosts == ["simbad.cds.unistra.fr"]


async def test_vsx_cone_rejects_bad_radius():
    with pytest.raises(ValueError):
        await vsx.cone_search(10, 10, 50)
