"""Saved equipment: telescopes (and binoculars), eyepieces and cameras.

Kept under "equipment" in ~/.astronomy-mcp/config.json, next to the default location, so tools
can use them when a question names no equipment. One telescope and one camera are the defaults:
the first one saved, or whichever was last saved with default=True.
"""

from __future__ import annotations

from typing import Any

from astronomy_mcp import imaging
from astronomy_mcp.location import read_config, write_config_key

KINDS = ("telescope", "eyepiece", "camera")
_LISTS = {"telescope": "telescopes", "eyepiece": "eyepieces", "camera": "cameras"}
HAS_DEFAULT = ("telescope", "camera")
DEFAULT_AFOV_DEG = 52.0  # a Plössl, when the apparent field isn't known


def load() -> dict[str, list[dict[str, Any]]]:
    saved = read_config().get("equipment") or {}
    return {key: [i for i in saved.get(key, []) if isinstance(i, dict) and i.get("name")] for key in _LISTS.values()}


def _write(data: dict[str, list[dict[str, Any]]]) -> None:
    write_config_key("equipment", data)


def _key(name: str) -> str:
    return " ".join(name.lower().split())


def find(kind: str, name: str) -> dict[str, Any] | None:
    items = load()[_LISTS[kind]]
    key = _key(name)
    exact = [i for i in items if _key(i["name"]) == key]
    if exact:
        return exact[0]
    partial = [i for i in items if key in _key(i["name"])]
    return partial[0] if len(partial) == 1 else None


def default(kind: str) -> dict[str, Any] | None:
    items = load()[_LISTS[kind]]
    return next((i for i in items if i.get("default")), items[0] if items else None)


def validate(kind: str, item: dict[str, Any]) -> dict[str, Any]:
    """Check one item has what its kind needs, and drop empty fields."""
    item = {k: v for k, v in item.items() if v is not None and v != ""}
    name = item.get("name", "").strip()
    if not name:
        raise ValueError("Give the equipment a name, e.g. '8-inch Dob' or 'ASI2600MC'.")
    item["name"] = name
    if kind == "telescope":
        if not item.get("aperture_mm"):
            raise ValueError("A telescope or binoculars needs aperture_mm.")
        if item.get("type") == "binoculars":
            item.pop("focal_length_mm", None)
        elif not item.get("focal_length_mm"):
            raise ValueError("A telescope needs focal_length_mm (aperture x focal ratio), for magnification and fields.")
        allowed = {"name", "type", "aperture_mm", "focal_length_mm", "magnification", "default"}
    elif kind == "eyepiece":
        if not item.get("focal_length_mm"):
            raise ValueError("An eyepiece needs focal_length_mm.")
        allowed = {"name", "focal_length_mm", "afov_deg"}
    else:
        if item.get("sensor"):
            imaging.camera(item["sensor"], None, None, None)  # raises for an unknown preset
        elif not (item.get("width_mm") and item.get("height_mm")):
            raise ValueError("A camera needs a sensor preset, or the sensor's width_mm and height_mm.")
        allowed = {"name", "sensor", "width_mm", "height_mm", "pixel_um", "default"}
    unused = set(item) - allowed
    if unused:
        raise ValueError(f"{', '.join(sorted(unused))} doesn't apply to a {kind}.")
    return item


def save(kind: str, item: dict[str, Any], make_default: bool = False) -> tuple[dict[str, Any], bool]:
    """Add an item, or replace the one with the same name. Returns (saved item, replaced?)."""
    item = validate(kind, item)
    data = load()
    items = data[_LISTS[kind]]
    key = _key(item["name"])
    replaced = any(_key(i["name"]) == key for i in items)
    was_default = any(_key(i["name"]) == key and i.get("default") for i in items)
    items[:] = [i for i in items if _key(i["name"]) != key]
    if kind in HAS_DEFAULT:
        if make_default or was_default or not any(i.get("default") for i in items):
            for i in items:
                i.pop("default", None)
            item["default"] = True
        else:
            item.pop("default", None)
    items.append(item)
    _write(data)
    return item, replaced


def remove(kind: str, name: str) -> dict[str, Any]:
    target = find(kind, name)
    if target is None:
        raise ValueError(f"No saved {kind} called '{name}'. Saved: {', '.join(i['name'] for i in load()[_LISTS[kind]]) or 'none'}.")
    data = load()
    items = data[_LISTS[kind]]
    items[:] = [i for i in items if i["name"] != target["name"]]
    if kind in HAS_DEFAULT and target.get("default") and items:
        items[0]["default"] = True
    _write(data)
    return target


# ---------------------------------------------------------------- using what's saved

def telescope(name: str | None = None, kind: str | None = None) -> dict[str, Any] | None:
    """A saved telescope by name; else the default, preferring one of the requested kind
    ('telescope' or 'binoculars'). None when nothing suitable is saved."""
    if name:
        found = find("telescope", name)
        if found is None:
            saved = [i["name"] for i in load()["telescopes"]]
            raise ValueError(f"No saved telescope called '{name}'. Saved: {', '.join(saved) or 'none'}.")
        return found
    scopes = load()["telescopes"]
    if kind:
        scopes = [s for s in scopes if (s.get("type") == "binoculars") == (kind == "binoculars")]
    return next((s for s in scopes if s.get("default")), scopes[0] if scopes else None)


def equipment_kind(scope: dict[str, Any]) -> str:
    """The visibility model's equipment class for a saved telescope."""
    return "binoculars" if scope.get("type") == "binoculars" else "telescope"


def describe(scope: dict[str, Any]) -> str:
    if scope.get("type") == "binoculars":
        size = (f"{scope['magnification']:g}x{scope['aperture_mm']:g}" if scope.get("magnification")
                else f"{scope['aperture_mm']:g} mm")
        return f"saved binoculars '{scope['name']}' ({size})"
    return f"saved telescope '{scope['name']}' ({scope['aperture_mm']:g} mm, {scope['focal_length_mm']:g} mm focal length)"


def camera(name: str | None = None) -> tuple[imaging.Camera, dict[str, Any]] | None:
    """(Camera, saved item) by name, or the default camera; None if none is saved or the name isn't one."""
    item = find("camera", name) if name else default("camera")
    if item is None:
        return None
    cam = imaging.camera(item.get("sensor"), item.get("width_mm"), item.get("height_mm"), item.get("pixel_um"))
    cam.label = f"{item['name']} ({cam.label})" if item.get("sensor") else item["name"]
    return cam, item


def eyepiece_views(focal_mm: float, aperture_mm: float | None) -> list[dict[str, Any]]:
    """Magnification, true field and exit pupil for every saved eyepiece on a telescope, low power first."""
    rows = []
    for e in sorted(load()["eyepieces"], key=lambda e: -e["focal_length_mm"]):
        mag = focal_mm / e["focal_length_mm"]
        afov = e.get("afov_deg") or DEFAULT_AFOV_DEG
        row = {"eyepiece": e["name"], "magnification": round(mag), "true_field_arcmin": round(afov / mag * 60)}
        if aperture_mm:
            row["exit_pupil_mm"] = round(aperture_mm / mag, 1)
            if mag > 2 * aperture_mm:
                row["note"] = "above the useful maximum magnification"
        if not e.get("afov_deg"):
            row["apparent_field_assumed_deg"] = DEFAULT_AFOV_DEG
        rows.append(row)
    return rows


def nearest_eyepiece(focal_mm: float | None, magnification: float | None) -> str | None:
    """The saved eyepiece giving the magnification closest to the suggested one, as 'name (NNx)'."""
    eyepieces = load()["eyepieces"]
    if not (focal_mm and magnification and eyepieces):
        return None
    best = min(eyepieces, key=lambda e: abs(focal_mm / e["focal_length_mm"] - magnification) / magnification)
    return f"{best['name']} ({focal_mm / best['focal_length_mm']:.0f}x)"
