"""The observing log: what the user has observed, when, where and with what, and progress
through the Messier and Caldwell catalogues.

Stored as JSON in ~/.astronomy-mcp/observations.json. Each entry keeps the target as the user
gave it, the resolved catalogue name and numbers, and the conditions computed at the time
(altitude, Moon), so the log can later be compared with the visibility model's predictions.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from astronomy_mcp import catalog
from astronomy_mcp.location import data_dir

CATALOGS = {"messier": 110, "caldwell": 109}
_NUMBERED = {"messier": re.compile(r"^m(\d{1,3})$"), "caldwell": re.compile(r"^c(\d{1,3})$")}
_CALDWELL_ID = re.compile(r"^C\s*0*(\d{1,3})$")
_CALDWELL_NAME = re.compile(r"^Caldwell\s+(\d{1,3})$")


def _path() -> Path:
    return data_dir() / "observations.json"


def load() -> list[dict[str, Any]]:
    try:
        raw = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entries = raw.get("observations") if isinstance(raw, dict) else None
    return [e for e in entries or [] if isinstance(e, dict) and "id" in e]


def _write(entries: list[dict[str, Any]]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": 1, "observations": entries}, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def catalog_numbers(target_text: str, obj: dict[str, Any] | None) -> dict[str, int]:
    """Messier and Caldwell numbers of an object. A number the user typed ('M102', 'Caldwell 9')
    wins, since OpenNGC files a few disputed entries under another object."""
    out: dict[str, int] = {}
    key = catalog.normalize(target_text)
    for name, pattern in _NUMBERED.items():
        if (m := pattern.match(key)) and 1 <= int(m.group(1)) <= CATALOGS[name]:
            out[name] = int(m.group(1))
    if obj is None:
        return out
    if "messier" not in out and (messier := obj.get("messier")):
        out["messier"] = int(messier.split()[-1])
    if "caldwell" not in out:
        for ident in [obj.get("name", ""), *obj.get("other_ids", [])]:
            if m := (_CALDWELL_ID.match(ident) or _CALDWELL_NAME.match(ident)):
                out["caldwell"] = int(m.group(1))
                break
    return out


def add(entry: dict[str, Any]) -> dict[str, Any]:
    entries = load()
    entry = {"id": max((e["id"] for e in entries), default=0) + 1, **{k: v for k, v in entry.items() if v is not None}}
    entries.append(entry)
    _write(entries)
    return entry


def delete(entry_id: int) -> dict[str, Any]:
    entries = load()
    found = next((e for e in entries if e["id"] == entry_id), None)
    if found is None:
        raise ValueError(f"No logged observation has id {entry_id}. get_observing_history lists the ids.")
    _write([e for e in entries if e["id"] != entry_id])
    return found


def _when(entry: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(entry["time"])


def _names(entry: dict[str, Any]) -> set[str]:
    names = {entry.get("target", ""), entry.get("name", ""), *entry.get("also_known_as", [])}
    names |= {f"M{n}" for n in [entry.get("messier")] if n} | {f"C{n}" for n in [entry.get("caldwell")] if n}
    return {catalog.normalize(n) for n in names if n}


def matches(entry: dict[str, Any], target: str) -> bool:
    key = catalog.normalize(target)
    names = _names(entry)
    return key in names or any(key in n for n in names if len(key) >= 4)


def history(
    entries: list[dict[str, Any]],
    target: str | None = None,
    catalog_name: str | None = None,
    since: date | None = None,
    until: date | None = None,
    seen: bool | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Filtered log, newest first, with a short summary."""
    rows = [e for e in entries
            if (target is None or matches(e, target))
            and (catalog_name is None or e.get(catalog_name))
            and (since is None or _when(e).date() >= since)
            and (until is None or _when(e).date() <= until)
            and (seen is None or e.get("seen", True) == seen)]
    rows.sort(key=_when, reverse=True)
    seen_rows = [e for e in rows if e.get("seen", True)]
    summary: dict[str, Any] = {
        "observations": len(rows),
        "distinct_objects_seen": len({e.get("name") or e.get("target") for e in seen_rows}),
        "nights": len({e["night"] for e in rows if e.get("night")}),
        "not_found": sum(1 for e in rows if not e.get("seen", True)) or None,
    }
    if rows:
        summary["first"] = min(rows, key=_when)["time"]
        summary["latest"] = rows[0]["time"]
    if target and seen_rows:
        summary["first_seen"] = min(seen_rows, key=_when)["time"]
    return {"summary": {k: v for k, v in summary.items() if v is not None},
            "count": min(len(rows), limit), "entries": rows[:limit]}


def members(cat: catalog.Catalog | None, catalog_name: str) -> dict[int, dict[str, Any]]:
    """Catalogue number -> OpenNGC object, for naming the objects not yet seen."""
    out: dict[int, dict[str, Any]] = {}
    for obj in cat.objects if cat else []:
        if (n := catalog_numbers("", obj).get(catalog_name)) and n not in out:
            out[n] = obj
    return out


def progress(entries: list[dict[str, Any]], catalog_name: str) -> tuple[dict[int, dict[str, Any]], list[int]]:
    """(number -> first logged sighting, numbers never seen)."""
    first: dict[int, dict[str, Any]] = {}
    for e in sorted(entries, key=_when):
        n = e.get(catalog_name)
        if n and e.get("seen", True) and n not in first:
            first[n] = e
    return first, [n for n in range(1, CATALOGS[catalog_name] + 1) if n not in first]
