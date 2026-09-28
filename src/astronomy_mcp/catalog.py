"""OpenNGC deep-sky catalog: NGC, IC, Messier, and notable extras (Caldwell, Pleiades, ...).

OpenNGC (https://github.com/mattiaverga/OpenNGC, CC-BY-SA 4.0) is downloaded
once on first use and cached under ~/.astronomy-mcp/openngc/.
"""

from __future__ import annotations

import asyncio
import csv
import io
import re
from typing import Any

from astronomy_mcp.http import get_bytes
from astronomy_mcp.location import data_dir

BASE_URL = "https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/database_files/"
FILES = ("NGC.csv", "addendum.csv")

# OpenNGC type code -> (description, search group)
TYPES: dict[str, tuple[str, str]] = {
    "*": ("Star", "star"),
    "**": ("Double star", "double_star"),
    "*Ass": ("Stellar association / asterism", "asterism"),
    "OCl": ("Open cluster", "open_cluster"),
    "GCl": ("Globular cluster", "globular_cluster"),
    "Cl+N": ("Star cluster with nebulosity", "nebula"),
    "G": ("Galaxy", "galaxy"),
    "GPair": ("Galaxy pair", "galaxy"),
    "GTrpl": ("Galaxy triplet", "galaxy"),
    "GGroup": ("Group of galaxies", "galaxy"),
    "PN": ("Planetary nebula", "planetary_nebula"),
    "HII": ("HII region", "nebula"),
    "EmN": ("Emission nebula", "nebula"),
    "RfN": ("Reflection nebula", "nebula"),
    "Neb": ("Nebula", "nebula"),
    "DrkN": ("Dark nebula", "dark_nebula"),
    "SNR": ("Supernova remnant", "supernova_remnant"),
    "Nova": ("Nova", "star"),
    "Other": ("Other", "other"),
}
GROUPS = sorted({group for _, group in TYPES.values()})

_CONSTELLATIONS = (
    "And Andromeda|Ant Antlia|Aps Apus|Aqr Aquarius|Aql Aquila|Ara Ara|Ari Aries|Aur Auriga|"
    "Boo Bootes|Cae Caelum|Cam Camelopardalis|Cnc Cancer|CVn Canes Venatici|CMa Canis Major|"
    "CMi Canis Minor|Cap Capricornus|Car Carina|Cas Cassiopeia|Cen Centaurus|Cep Cepheus|Cet Cetus|"
    "Cha Chamaeleon|Cir Circinus|Col Columba|Com Coma Berenices|CrA Corona Australis|"
    "CrB Corona Borealis|Crv Corvus|Crt Crater|Cru Crux|Cyg Cygnus|Del Delphinus|Dor Dorado|"
    "Dra Draco|Equ Equuleus|Eri Eridanus|For Fornax|Gem Gemini|Gru Grus|Her Hercules|"
    "Hor Horologium|Hya Hydra|Hyi Hydrus|Ind Indus|Lac Lacerta|Leo Leo|LMi Leo Minor|Lep Lepus|"
    "Lib Libra|Lup Lupus|Lyn Lynx|Lyr Lyra|Men Mensa|Mic Microscopium|Mon Monoceros|Mus Musca|"
    "Nor Norma|Oct Octans|Oph Ophiuchus|Ori Orion|Pav Pavo|Peg Pegasus|Per Perseus|Phe Phoenix|"
    "Pic Pictor|Psc Pisces|PsA Piscis Austrinus|Pup Puppis|Pyx Pyxis|Ret Reticulum|Sge Sagitta|"
    "Sgr Sagittarius|Sco Scorpius|Scl Sculptor|Sct Scutum|Ser Serpens|Sex Sextans|Tau Taurus|"
    "Tel Telescopium|Tri Triangulum|TrA Triangulum Australe|Tuc Tucana|UMa Ursa Major|"
    "UMi Ursa Minor|Vel Vela|Vir Virgo|Vol Volans|Vul Vulpecula"
)
CONSTELLATION_NAMES: dict[str, str] = dict(entry.split(" ", 1) for entry in _CONSTELLATIONS.split("|"))


def constellation_abbrev(value: str) -> str | None:
    """'Sagittarius', 'sgr' or 'SGR' -> 'Sgr'. OpenNGC uses 'Se1'/'Se2' for the two halves of Serpens."""
    v = value.strip().lower()
    for abbr, name in CONSTELLATION_NAMES.items():
        if v in (abbr.lower(), name.lower()):
            return abbr
    return None


_KEY_RE = re.compile(r"^([a-z][a-z\-]*?)0*(\d.*)$")


def normalize(name: str) -> str:
    """Canonical lookup key: 'NGC 0224' -> 'ngc224', 'Messier 31' -> 'm31', 'Caldwell 41' -> 'c41'."""
    s = name.strip().lower()
    s = re.sub(r"^messier\b", "m", s)
    s = re.sub(r"^caldwell\b", "c", s)
    s = re.sub(r"^the\s+", "", s)
    s = re.sub(r"\s+", "", s) if re.match(r"^[a-z\-]+\s*\d", s) else " ".join(s.split())
    m = _KEY_RE.match(s)
    return f"{m.group(1)}{m.group(2)}" if m else s


def _sexagesimal(value: str, scale: float) -> float | None:
    if not value:
        return None
    sign = -1.0 if value.startswith("-") else 1.0
    parts = [float(p) for p in value.lstrip("+-").split(":")]
    while len(parts) < 3:
        parts.append(0.0)
    return sign * scale * (parts[0] + parts[1] / 60 + parts[2] / 3600)


def _float(value: str) -> float | None:
    try:
        return float(value) if value else None
    except ValueError:
        return None


def _display_name(raw: str) -> str:
    """'NGC0224' -> 'NGC 224', 'C041' -> 'Caldwell 41', 'Mel022' -> 'Melotte 22', 'ESO056-115' -> 'ESO 56-115'."""
    m = re.match(r"^([A-Za-z]+)0*(\d.*)$", raw)
    if not m:
        return raw
    prefix = {"C": "Caldwell", "Mel": "Melotte", "B": "Barnard"}.get(m.group(1), m.group(1))
    return f"{prefix} {m.group(2)}"


def _shape(row: dict[str, str]) -> dict[str, Any]:
    desc, group = TYPES.get(row["Type"], (row["Type"], "other"))
    v_mag, b_mag = _float(row["V-Mag"]), _float(row["B-Mag"])
    obj: dict[str, Any] = {
        "name": _display_name(row["Name"]),
        "messier": f"M {int(row['M'])}" if row["M"] else None,
        "common_names": [n.strip() for n in row["Common names"].split(",") if n.strip()] or None,
        "type": desc,
        "group": group,
        "ra_deg": _sexagesimal(row["RA"], 15.0),
        "dec_deg": _sexagesimal(row["Dec"], 1.0),
        "constellation": row["Const"],
        "magnitude": v_mag if v_mag is not None else b_mag,
        "magnitude_band": "V" if v_mag is not None else ("B" if b_mag is not None else None),
        "surface_brightness": _float(row["SurfBr"]),
        "major_axis_arcmin": _float(row["MajAx"]),
        "minor_axis_arcmin": _float(row["MinAx"]),
        "hubble_type": row["Hubble"] or None,
        "redshift": _float(row["Redshift"]),
        "other_ids": [i.strip() for i in row["Identifiers"].split(",") if i.strip()] or None,
    }
    return {k: v for k, v in obj.items() if v is not None}


class Catalog:
    def __init__(self, objects: list[dict[str, Any]], index: dict[str, dict[str, Any]]):
        self.objects = objects
        self._index = index

    @classmethod
    def from_csv_texts(cls, *texts: str) -> Catalog:
        objects: list[dict[str, Any]] = []
        index: dict[str, dict[str, Any]] = {}
        dups: list[dict[str, str]] = []
        for text in texts:
            for row in csv.DictReader(io.StringIO(text), delimiter=";"):
                if row["Type"] == "Dup":
                    dups.append(row)
                    continue
                if row["Type"] == "NonEx" or row["RA"] == "":
                    continue
                obj = _shape(row)
                objects.append(obj)
                keys = [row["Name"]]
                keys += [f"M{row['M']}"] if row["M"] else []
                keys += [f"NGC{row['NGC']}"] if row["NGC"] else []
                keys += [f"IC{row['IC']}"] if row["IC"] else []
                keys += obj.get("common_names", []) + obj.get("other_ids", [])
                for key in keys:
                    index.setdefault(normalize(key), obj)
        for row in dups:
            target = (
                f"NGC{row['NGC']}" if row["NGC"] else f"IC{row['IC']}" if row["IC"] else f"M{row['M']}" if row["M"] else None
            )
            if target and (obj := index.get(normalize(target))):
                index.setdefault(normalize(row["Name"]), obj)
        return cls(objects, index)

    def lookup(self, name: str) -> dict[str, Any] | None:
        return self._index.get(normalize(name))

    def search(
        self,
        group: str | None = None,
        constellation: str | None = None,
        max_magnitude: float | None = None,
        min_size_arcmin: float | None = None,
        messier_only: bool = False,
        name_contains: str | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        needle = name_contains.lower() if name_contains else None
        allowed = {"Ser", "Se1", "Se2"} if constellation == "Ser" else {constellation}
        for obj in self.objects:
            if group and obj["group"] != group:
                continue
            if constellation and obj.get("constellation") not in allowed:
                continue
            if messier_only and "messier" not in obj:
                continue
            if max_magnitude is not None and (obj.get("magnitude") is None or obj["magnitude"] > max_magnitude):
                continue
            if min_size_arcmin is not None and obj.get("major_axis_arcmin", 0) < min_size_arcmin:
                continue
            if needle and not any(needle in n.lower() for n in [obj["name"], *obj.get("common_names", [])]):
                continue
            results.append(obj)
        results.sort(key=lambda o: o.get("magnitude", 99))
        return results


_catalog: Catalog | None = None
_lock = asyncio.Lock()


async def get_catalog() -> Catalog:
    """Load OpenNGC, downloading it on first use."""
    global _catalog
    if _catalog is not None:
        return _catalog
    async with _lock:
        if _catalog is None:
            folder = data_dir() / "openngc"
            texts = []
            for filename in FILES:
                path = folder / filename
                if not path.exists():
                    content = await get_bytes(BASE_URL + filename, source="OpenNGC (GitHub)")
                    folder.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
                texts.append(path.read_text(encoding="utf-8"))
            _catalog = Catalog.from_csv_texts(*texts)
    return _catalog
