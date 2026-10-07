"""NASA Deep Space Network status from DSN Now (eyes.nasa.gov/dsn).

dsn.xml is refreshed every few seconds and lists each antenna's pointing, activity,
targets and up/down signals; config.xml maps station and spacecraft codes to names.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import Any

from astronomy_mcp.http import UpstreamError, get_text, get_text_file
from astronomy_mcp.location import data_dir

STATUS_URL = "https://eyes.nasa.gov/dsn/data/dsn.xml"
CONFIG_URL = "https://eyes.nasa.gov/dsn/config.xml"
LIGHT_KM_PER_S = 299_792.458
AU_KM = 149_597_870.7
DISH_TYPES = {"70M": "70 m", "34M": "34 m", "34MHEF": "34 m (high efficiency)", "34MBWG": "34 m (beam waveguide)"}
PLACEHOLDER_TARGETS = {"DSN", "DSS", "TEST", "SIM"}


def _float(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def parse_config(text: str) -> tuple[dict[str, str], dict[str, str]]:
    """({spacecraft code: name}, {dish code: size}) from config.xml."""
    root = ET.fromstring(text)
    craft = {s.get("name", "").lower(): s.get("friendlyName", "") for s in root.iter("spacecraft")}
    dishes = {d.get("name", ""): DISH_TYPES.get(d.get("type", ""), d.get("type", "")) for d in root.iter("dish")}
    return craft, dishes


def _distance(km: float | None) -> dict[str, Any] | None:
    if km is None or km <= 0:
        return None
    out: dict[str, Any] = {"km": round(km)}
    if km > 0.01 * AU_KM:
        out["au"] = round(km / AU_KM, 3)
    seconds = km / LIGHT_KM_PER_S
    out["one_way_light_time"] = f"{seconds / 3600:.1f} h" if seconds > 3600 else f"{seconds / 60:.1f} min" if seconds > 60 else f"{seconds:.2f} s"
    return out


def _signal(el: ET.Element) -> dict[str, Any] | None:
    if el.get("active") != "true":
        return None
    rate = _float(el.get("dataRate"))
    out = {
        "band": el.get("band"),
        "type": el.get("signalType"),
        "data_rate_bps": round(rate) if rate else None,
        "power": (f"{el.get('power')} kW" if el.tag == "upSignal" else f"{el.get('power')} dBm") if el.get("power") else None,
    }
    return {k: v for k, v in out.items() if v not in (None, "", "none")}


def parse_status(text: str, craft: dict[str, str], dishes: dict[str, str]) -> dict[str, Any]:
    """Stations with their antennas, and a list of the spacecraft being contacted."""
    root = ET.fromstring(text)
    stations: list[dict[str, Any]] = []
    contacts: dict[str, dict[str, Any]] = {}
    updated = None
    for el in root:
        if el.tag == "station":
            stamp = _float(el.get("timeUTC"))
            if stamp:
                updated = datetime.fromtimestamp(stamp / 1000, UTC)
            stations.append({"station": el.get("friendlyName") or el.get("name"), "antennas": []})
            continue
        if el.tag != "dish" or not stations:
            continue
        targets = []
        for t in el.findall("target"):
            code = t.get("name", "")
            if code.upper() in PLACEHOLDER_TARGETS or code == "":
                continue
            down = _float(t.get("downlegRange"))
            up = _float(t.get("uplegRange"))
            targets.append({"code": code, "name": craft.get(code.lower(), code), "distance": _distance(down if down and down > 0 else up)})
        up_signals = [s for s in (_signal(x) for x in el.findall("upSignal")) if s]
        down_signals = [s for s in (_signal(x) for x in el.findall("downSignal")) if s]
        dish = {
            "antenna": el.get("name"),
            "size": dishes.get(el.get("name", "")),
            "activity": el.get("activity"),
            "pointing": {"azimuth_deg": _float(el.get("azimuthAngle")), "elevation_deg": _float(el.get("elevationAngle"))},
            "targets": [t["name"] for t in targets] or None,
            "uplink": up_signals or None,
            "downlink": down_signals or None,
            "arrayed": el.get("isArray") == "true" or None,
        }
        stations[-1]["antennas"].append({k: v for k, v in dish.items() if v is not None})
        for t in targets:
            entry = contacts.setdefault(t["name"], {"spacecraft": t["name"], "code": t["code"], "antennas": [],
                                                    "distance": t["distance"], "receiving_data": False, "sending_commands": False})
            entry["antennas"].append(f"{el.get('name')} ({stations[-1]['station']})")
            entry["receiving_data"] |= any(s.get("type") == "data" for s in down_signals)
            entry["sending_commands"] |= any(s.get("type") == "data" for s in up_signals)
            if entry["distance"] is None:
                entry["distance"] = t["distance"]
    spacecraft = sorted(contacts.values(), key=lambda c: -(c["distance"] or {}).get("km", 0))
    for c in spacecraft:
        if c["distance"] is None:
            del c["distance"]
    return {"updated_utc": updated.isoformat(timespec="seconds") if updated else None,
            "spacecraft": spacecraft, "stations": stations}


async def status(spacecraft: str | None = None, include_antennas: bool = True) -> dict[str, Any]:
    config_text = await get_text_file(CONFIG_URL, data_dir() / "dsn" / "config.xml", source="DSN Now", max_age=86400)
    try:
        craft, dishes = parse_config(config_text)
    except ET.ParseError:
        craft, dishes = {}, {}
    text = await get_text(STATUS_URL, source="DSN Now", ttl=5)
    try:
        report = parse_status(text, craft, dishes)
    except ET.ParseError as exc:
        raise UpstreamError(f"DSN Now returned unreadable XML: {exc}") from exc
    if spacecraft:
        wanted = spacecraft.strip().lower()
        report["spacecraft"] = [c for c in report["spacecraft"]
                                if wanted in c["spacecraft"].lower() or wanted == c["code"].lower()]
        report["stations"] = [
            {**s, "antennas": [a for a in s["antennas"] if any(c["spacecraft"] in (a.get("targets") or []) for c in report["spacecraft"])]}
            for s in report["stations"]
        ]
        report["stations"] = [s for s in report["stations"] if s["antennas"]]
        if not report["spacecraft"]:
            report["message"] = f"No antenna is talking to anything matching '{spacecraft}' right now."
    if not include_antennas:
        report.pop("stations")
    report["count"] = len(report["spacecraft"])
    report["note"] = ("Live from DSN Now. Distances come from the antenna's range measurement when one is "
                      "reported; up- and down-link data rates are in bits per second. Contacts change every few hours.")
    return {k: v for k, v in report.items() if v is not None}
