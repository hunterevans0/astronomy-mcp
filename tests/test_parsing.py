"""Offline tests for response parsing and input validation."""

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


async def test_vsx_cone_rejects_bad_radius():
    with pytest.raises(ValueError):
        await vsx.cone_search(10, 10, 50)
