"""Supernovae and novae bright enough for amateurs, plus fresh broker candidates.

- Supernovae: David Bishop's "Latest Supernovae" (rochesterastronomy.org), the curated list
  amateurs use: every active supernova brighter than magnitude 17 with type, host, position,
  latest and peak magnitude. The page is large, so it is cached on disk for 6 hours.
- Galactic novae: Koji Mukai's list at NASA GSFC, with current brightness from AAVSO.
- Extragalactic novae (M31 and friends): the same Rochester site's novae page.
- New candidates: the ALeRCE broker's machine-learning classes for ZTF alerts. These are
  mostly fainter than 17 and unconfirmed.

TNS, the official IAU list, needs registered bot credentials for scripted access, so it is
not used here.
"""

from __future__ import annotations

import asyncio
import html
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from astronomy_mcp import sky, variables
from astronomy_mcp.http import UpstreamError, get_json, get_text_file
from astronomy_mcp.location import Location, data_dir

ROCHESTER_SN = "https://www.rochesterastronomy.org/supernova.html"
ROCHESTER_NOVAE = "https://www.rochesterastronomy.org/novae.html"
MUKAI_NOVAE = "https://asd.gsfc.nasa.gov/Koji.Mukai/novae/novae.html"
ALERCE = "https://api.alerce.online/ztf/v1"
# (classifier, class, minimum probability). The light-curve classifier is cautious with young objects;
# the stamp classifier judges the first image and is the early-warning one.
ALERCE_QUERIES = (("lc_classifier", "SNIa", 0.4), ("lc_classifier", "SNIbc", 0.4), ("lc_classifier", "SNII", 0.4),
                  ("lc_classifier", "SLSN", 0.4), ("stamp_classifier", "SN", 0.8))
NOVA_TYPES = {"egn", "nova", "feii", "he/n", "recurrent", "unknown"}
MJD_UNIX_EPOCH = 40587.0
CACHE_SECONDS = 6 * 3600

_TAG = re.compile(r"<[^>]+>")
_COORDS = re.compile(
    r"R\.A\. = (\d+)h(\d+)m(\d+)s\.?(\d*), Decl\. = ([+-])(\d+)&deg;(\d+)'(\d+)\"\.?(\d*)")
_MAG = re.compile(r"Mag\s+([\d.]+)(\*?):(\d+)/(\d+)(?:\s*\(([\d.]+):(\d+)/(\d+)\))?")


def _text(fragment: str) -> str:
    return " ".join(html.unescape(_TAG.sub(" ", fragment)).split())


def _month_day(month: str, day: str, today: date) -> str | None:
    """Rochester writes '10/1' for the latest observation; pick the year that keeps it in the past."""
    try:
        d = date(today.year, int(month), int(day))
    except ValueError:
        return None
    if d > today + timedelta(days=1):
        d = d.replace(year=d.year - 1)
    return d.isoformat()


def parse_entry(block: str, today: date) -> dict[str, Any]:
    """One object from a Rochester detail block (starting at its <a id=...> anchor)."""
    out: dict[str, Any] = {}
    name = re.match(r'<a id="[^"]+">([^<]+)</a>', block)
    if name:
        out["name"] = name.group(1).strip()
    aliases = re.findall(r"\(= ([^)]+)\)", block[:600])
    if aliases:
        out["also_known_as"] = [a.strip() for a in aliases]
    disc = re.search(r"discovered (\d{4})/(\d{2})/(\d{2})(?:\.\d+)? by(.*?)<br", block, re.S)
    if disc:
        out["discovered"] = f"{disc.group(1)}-{disc.group(2)}-{disc.group(3)}"
        who = _text(disc.group(4)).rstrip(",")
        if who:
            out["discovered_by"] = who
    host = re.search(r"Found in\s*(?:<a[^>]*>)?([^<]+)", block)
    if host:
        out["host"] = host.group(1).strip()
    c = _COORDS.search(block)
    if c:
        h, m, s, sf, sign, d, dm, ds, dsf = c.groups()
        ra = (int(h) + int(m) / 60 + float(f"{s}.{sf or 0}") / 3600) * 15
        dec = int(d) + int(dm) / 60 + float(f"{ds}.{dsf or 0}") / 3600
        out["ra_deg"] = round(ra, 5)
        out["dec_deg"] = round(-dec if sign == "-" else dec, 5)
    mag = _MAG.search(block)
    if mag:
        out["magnitude"] = float(mag.group(1))
        out["magnitude_date"] = _month_day(mag.group(3), mag.group(4), today)
        if mag.group(5):
            out["peak_magnitude"] = float(mag.group(5))
            out["peak_date"] = _month_day(mag.group(6), mag.group(7), today)
    kind = re.search(r"Type ([^\s(<,]+)", block)
    if kind:
        out["type"] = kind.group(1)
    z = re.search(r"\(z=([\d.]+)\)", block)
    if z:
        out["redshift"] = float(z.group(1))
    return {k: v for k, v in out.items() if v is not None}


def _blocks(page: str) -> dict[str, str]:
    """Detail blocks keyed by anchor id."""
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'<a id="([^"]+)">', page)]
    return {anchor: page[pos:(starts[k + 1][0] if k + 1 < len(starts) else len(page))][:6000]
            for k, (pos, anchor) in enumerate(starts)}


def parse_supernova_page(page: str, today: date) -> list[dict[str, Any]]:
    """The 'All active supernova over mag 17' table, joined to each object's detail block."""
    start = page.find("All active supernova")
    if start < 0:
        raise UpstreamError("The Latest Supernovae page has changed layout; its summary table was not found.")
    table = page[start:page.find("</table>", start)]
    blocks = _blocks(page)
    found = []
    for row in re.finditer(r'<tr><td><a href="([^"#]*)#([^"]+)"[^>]*>([^<]+)</a></td><td>([^<]*)</td><td>([^<]*)</td><td>(.*?)</td></tr>',
                           table):
        page_ref, anchor, name, mag, kind, host = row.groups()
        entry: dict[str, Any] = {"name": name.strip(), "type": kind.strip(), "host": _text(host)}
        try:
            entry["magnitude"] = float(mag.rstrip("*"))
        except ValueError:
            pass
        if mag.endswith("*"):
            entry["magnitude_note"] = "unconfirmed or not recently updated"
        if not page_ref and anchor in blocks:  # novae in other galaxies link to the novae page instead
            entry = {**parse_entry(blocks[anchor], today), **entry}
        found.append(entry)
    return found


async def supernova_page() -> str:
    return await get_text_file(ROCHESTER_SN, data_dir() / "transients" / "supernova.html", source="Latest Supernovae",
                               max_age=CACHE_SECONDS, timeout=120)


def _tonight(items: list[dict[str, Any]], loc: Location | None, night_times: list[datetime] | None,
             min_altitude: float) -> None:
    if not loc or not night_times:
        return
    placed = [i for i in items if "ra_deg" in i]
    for item, track in zip(placed, sky.fast_tracks([(i["ra_deg"], i["dec_deg"]) for i in placed], night_times, loc)):
        best = max(range(len(track)), key=lambda k: track[k][0])
        alt = track[best][0]
        item["tonight"] = ({"best_time": sky.fmt(night_times[best], loc), "altitude_deg": round(alt),
                            "direction": sky.compass(track[best][1])}
                           if alt >= min_altitude else {"visible": False, "highest_deg": round(alt)})


async def recent_supernovae(max_magnitude: float, limit: int, loc: Location | None,
                            night_times: list[datetime] | None, min_altitude: float, include_candidates: bool,
                            candidate_days: int) -> dict[str, Any]:
    today = datetime.now(UTC).date()
    # The summary also lists novae in other galaxies (type EGN); those belong to get_novae.
    found = [s for s in parse_supernova_page(await supernova_page(), today)
             if s.get("magnitude", 99) <= max_magnitude and s.get("type", "").lower() not in ("egn", "nova")]
    found.sort(key=lambda s: s.get("magnitude", 99))
    for s in found:
        if "ra_deg" in s:
            s["constellation"] = sky.constellation(s["ra_deg"], s["dec_deg"])["name"]
    shown = found[:limit]
    _tonight(shown, loc, night_times, min_altitude)
    out: dict[str, Any] = {
        "max_magnitude": max_magnitude,
        "total": len(found),
        "count": len(shown),
        "supernovae": shown,
        "source": "Latest Supernovae, D. Bishop (rochesterastronomy.org), cached 6 hours",
        "note": "Names starting 'AT' are transients not yet confirmed as supernovae. Magnitudes are the latest "
                "reported (date given) and fade by a magnitude or more a month after peak. A supernova at "
                "magnitude 12-13 needs a 150-200 mm telescope; most here need a camera.",
    }
    if include_candidates:
        try:
            out["broker_candidates"] = await alerce_candidates(candidate_days, limit)
        except UpstreamError as exc:
            out["broker_candidates_unavailable"] = str(exc)
    return out


# ---------------------------------------------------------------- ALeRCE

def _mjd_to_date(mjd: float) -> str:
    return datetime.fromtimestamp((mjd - MJD_UNIX_EPOCH) * 86400, UTC).date().isoformat()


async def alerce_candidates(days: int, limit: int) -> dict[str, Any]:
    """Young ZTF transients ALeRCE's light-curve classifier calls supernovae, most probable first."""
    since = datetime.now(UTC).timestamp() / 86400 + MJD_UNIX_EPOCH - days
    async def query(classifier: str, cls: str, probability: float) -> list[dict[str, Any]]:
        params = {"classifier": classifier, "class": cls, "probability": probability, "firstmjd": f"{since:.2f}",
                  "page_size": limit, "order_by": "probability", "order_mode": "DESC"}
        payload = await get_json(f"{ALERCE}/objects/", params, source="ALeRCE", ttl=1800)
        return [{**r, "classifier": classifier} for r in payload.get("items", [])]

    rows: dict[str, dict[str, Any]] = {}
    for batch in await asyncio.gather(*(query(*q) for q in ALERCE_QUERIES)):
        for r in batch:  # an object can appear under both classifiers; keep the light-curve class
            if r["oid"] not in rows or rows[r["oid"]]["classifier"] == "stamp_classifier":
                rows[r["oid"]] = r
    ranked = sorted(rows.values(), key=lambda r: (r["classifier"] != "lc_classifier", -(r.get("probability") or 0)))[:limit]
    gate = asyncio.Semaphore(4)

    async def mags(oid: str) -> list[dict[str, Any]]:
        async with gate:
            try:
                return await get_json(f"{ALERCE}/objects/{oid}/magstats", source="ALeRCE", ttl=1800)
            except UpstreamError:
                return []

    stats = await asyncio.gather(*(mags(r["oid"]) for r in ranked))
    candidates = []
    for r, st in zip(ranked, stats):
        bands = {1: "g", 2: "r", 3: "i"}
        latest = {bands.get(s.get("fid"), str(s.get("fid"))): round(s["maglast"], 2) for s in st if s.get("maglast")}
        brightest = min((s["magmin"] for s in st if s.get("magmin")), default=None)
        candidates.append({k: v for k, v in {
            "ztf_id": r["oid"],
            "class": r.get("class"),
            "probability": round(r.get("probability") or 0, 2),
            "classified_from": "light curve" if r["classifier"] == "lc_classifier" else "first image only",
            "ra_deg": round(r["meanra"], 5),
            "dec_deg": round(r["meandec"], 5),
            "constellation": sky.constellation(r["meanra"], r["meandec"])["name"],
            "first_detected": _mjd_to_date(r["firstmjd"]),
            "last_detected": _mjd_to_date(r["lastmjd"]),
            "detections": r.get("ndet"),
            "latest_magnitudes": latest or None,
            "brightest_magnitude": round(brightest, 2) if brightest else None,
            "url": f"https://alerce.online/object/{r['oid']}",
        }.items() if v is not None})
    return {
        "first_detected_within_days": days,
        "count": len(candidates),
        "candidates": candidates,
        "note": "Machine-learning classifications of ZTF alerts by the ALeRCE broker: unconfirmed, usually "
                "fainter than magnitude 17. Check TNS for a spectroscopic classification.",
    }


# ---------------------------------------------------------------- novae

def parse_mukai_table(page: str, year: int) -> list[dict[str, Any]]:
    """Rows of the 'Galactic Novae in <year>' table."""
    heading = page.find(f"Galactic Novae in {year}")
    if heading < 0:
        return []
    table = page[heading:page.find("</TABLE>", heading)]
    rows = []
    for tr in re.findall(r"<TR>(.*?)</TR>", table, re.S | re.I):
        cells = re.findall(r"<TD[^>]*>(.*?)</TD>", tr, re.S | re.I)
        if len(cells) < 4:
            continue
        names = [n for n in (_text(x) for x in re.split(r"<BR>|</BR>", cells[0], flags=re.I)) if n]
        position = [_text(x) for x in re.split(r"<BR>", cells[1], flags=re.I)]
        item: dict[str, Any] = {"name": names[0] if names else None, "also_known_as": names[1:] or None,
                                "discovered": _text(cells[2]), "peak": _text(cells[3])}
        try:
            ra = [float(x) for x in position[0].split()]
            dec_text = position[1].replace("..", ".")
            sign = -1 if dec_text.strip().startswith("-") else 1
            dec = [abs(float(x)) for x in dec_text.split()]
            item["ra_deg"] = round((ra[0] + ra[1] / 60 + ra[2] / 3600) * 15, 5)
            item["dec_deg"] = round(sign * (dec[0] + dec[1] / 60 + dec[2] / 3600), 5)
        except (IndexError, ValueError):
            pass
        peak = re.match(r"^(?:([A-Za-z]+)=)?([\d.]+)", item["peak"])
        if peak:
            item["peak_magnitude"] = float(peak.group(2))
            if peak.group(1):
                item["peak_band"] = peak.group(1)
        if len(cells) > 5 and (note := _text(cells[5]).removesuffix("ARAS").strip(" ;")):
            item["notes"] = note
        rows.append({k: v for k, v in item.items() if v not in (None, "", [])})
    return rows


async def _current_brightness(nova: dict[str, Any]) -> None:
    """Latest AAVSO magnitude for a nova, trying each of its names."""
    for ident in [nova.get("name"), *(nova.get("also_known_as") or [])]:
        if not ident or ident.lower().startswith("nova "):
            continue
        try:
            obs = await variables.observations(ident, 20)
        except UpstreamError:
            return
        measured = [o for o in obs if not o.fainter_than]
        # Prefer the latest visual-like magnitude over narrow-band (H-alpha) or infrared ones.
        visual = [o for o in measured if o.band in variables.VISUAL_LIKE]
        if measured:
            last = (visual or measured)[-1]
            nova["latest_aavso"] = {"date": last.when.date().isoformat(), "magnitude": round(last.mag, 2), "band": last.band}
            return


async def galactic_novae(days: int, loc: Location | None, night_times: list[datetime] | None,
                         min_altitude: float) -> list[dict[str, Any]]:
    page = await get_text_file(MUKAI_NOVAE, data_dir() / "transients" / "mukai_novae.html", source="Koji Mukai's nova list",
                               max_age=CACHE_SECONDS)
    today = datetime.now(UTC).date()
    rows = parse_mukai_table(page, today.year) + parse_mukai_table(page, today.year - 1)
    recent = []
    for r in rows:
        try:
            if (today - date.fromisoformat(r.get("discovered", ""))).days <= days:
                recent.append(r)
        except ValueError:
            continue
    gate = asyncio.Semaphore(3)

    async def brightness(n: dict[str, Any]) -> None:
        async with gate:
            await _current_brightness(n)

    await asyncio.gather(*(brightness(n) for n in recent))
    for n in recent:
        if "ra_deg" in n:
            n["constellation"] = sky.constellation(n["ra_deg"], n["dec_deg"])["name"]
    _tonight(recent, loc, night_times, min_altitude)
    return recent


async def extragalactic_novae(days: int) -> list[dict[str, Any]]:
    page = await get_text_file(ROCHESTER_NOVAE, data_dir() / "transients" / "novae.html", source="Latest Supernovae (novae)",
                               max_age=CACHE_SECONDS)
    today = datetime.now(UTC).date()
    found = []
    for anchor, block in _blocks(page).items():
        if not re.match(r"\d{4}", anchor):
            continue
        entry = parse_entry(block, today)
        kind = entry.get("type", "").lower()
        if kind not in NOVA_TYPES:  # flares, CVs and the like
            continue
        if kind == "unknown":
            entry["type"] = "unconfirmed nova candidate"
        try:
            if (today - date.fromisoformat(entry.get("discovered", ""))).days > days:
                continue
        except ValueError:
            continue
        found.append(entry)
    return found


async def novae(days: int, include_extragalactic: bool, loc: Location | None, night_times: list[datetime] | None,
                min_altitude: float) -> dict[str, Any]:
    galactic = await galactic_novae(days, loc, night_times, min_altitude)
    out: dict[str, Any] = {
        "discovered_within_days": days,
        "galactic": galactic,
        "source": "Koji Mukai's list of recent Galactic novae (NASA GSFC); current brightness from AAVSO",
        "note": "Peak magnitudes are as listed (some in red or infrared bands, e.g. 'r=', 'H='). Novae fade over "
                "weeks to months; latest_aavso is the newest positive observation in the last 20 days.",
    }
    if include_extragalactic:
        try:
            out["extragalactic"] = await extragalactic_novae(days)
            out["extragalactic_source"] = "Latest Supernovae novae page (rochesterastronomy.org): mostly M31, magnitude 15-19"
        except UpstreamError as exc:
            out["extragalactic_unavailable"] = str(exc)
    return out
