"""Comets, asteroids, close approaches and fireballs (JPL Solar System Dynamics, CNEOS, COBS).

- Which comets are bright: COBS (Comet Observation database) fits each comet's light curve
  to observers' reports, so its current magnitude is the observed one. JPL's total-magnitude
  parameters (M1, K1) give a prediction for comets COBS doesn't cover.
- Where the bright comets are: propagated offline from JPL osculating elements as a two-body
  orbit. Planetary perturbations are ignored, which costs a few arcminutes within a year or
  two of perihelion; plenty for finding one in the sky.
- Ephemerides for a single comet or asteroid come from JPL Horizons, topocentric when a
  location is known.
"""

from __future__ import annotations

import asyncio
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import astronomy as ae

from astronomy_mcp import sky
from astronomy_mcp.http import UpstreamError, get_json, get_json_file
from astronomy_mcp.location import Location, data_dir
from astronomy_mcp.sky import Vec, fmt

SBDB = "https://ssd-api.jpl.nasa.gov/sbdb.api"
SBDB_QUERY = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"
HORIZONS = "https://ssd.jpl.nasa.gov/api/horizons.api"
CAD = "https://ssd-api.jpl.nasa.gov/cad.api"
FIREBALL = "https://ssd-api.jpl.nasa.gov/fireball.api"
COBS_LIST = "https://cobs.si/api/comet_list.api"

GAUSS_K = 0.01720209895  # Gaussian gravitational constant, radians per day
OBLIQUITY = math.radians(23.4392911)  # J2000 mean obliquity of the ecliptic
LIGHT_AU_PER_DAY = 173.1446327
LD_KM = 384_399  # one lunar distance
AU_KM = sky.AU_KM
JD_UNIX_EPOCH = 2440587.5
EARTH_RADIUS_KM = 6371.0

# Rough equipment guide for a comet's total magnitude. Comets are diffuse, so they need
# about a magnitude more than a star of the same brightness.
COMET_EQUIPMENT = ((5.0, "naked eye from a dark site"), (8.0, "binoculars"), (11.0, "small telescope"),
                   (13.5, "8-inch or larger telescope"))


def julian(dt: datetime) -> float:
    return dt.timestamp() / 86400 + JD_UNIX_EPOCH


def from_julian(jd: float) -> datetime:
    return datetime.fromtimestamp((jd - JD_UNIX_EPOCH) * 86400, UTC)


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _round(value: float | None, digits: int) -> float | None:
    return None if value is None else round(value, digits)


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- two-body orbits

def orbital_plane_position(e: float, q: float, days_from_perihelion: float) -> tuple[float, float]:
    """Position in the orbital plane (au), x toward perihelion, for any eccentricity."""
    dt = days_from_perihelion
    if abs(e - 1) < 1e-8:  # parabola: Barker's equation
        w = 1.5 * GAUSS_K * dt / math.sqrt(2 * q**3)
        y = math.cbrt(w + math.sqrt(w * w + 1))
        s = y - 1 / y  # tan(true anomaly / 2)
        return q * (1 - s * s), 2 * q * s
    a = q / (1 - e)
    m = GAUSS_K / abs(a) ** 1.5 * dt
    if e < 1:
        m = math.remainder(m, 2 * math.pi)
        ecc = m + 0.85 * e * math.copysign(1.0, math.sin(m))  # Danby's starter converges for all e < 1
        for _ in range(100):
            step = (ecc - e * math.sin(ecc) - m) / (1 - e * math.cos(ecc))
            ecc -= step
            if abs(step) < 1e-13:
                break
        return a * (math.cos(ecc) - e), a * math.sqrt(1 - e * e) * math.sin(ecc)
    h = math.asinh(m / e)
    for _ in range(100):
        step = (e * math.sinh(h) - h - m) / (e * math.cosh(h) - 1)
        h -= step
        if abs(step) < 1e-13:
            break
    return a * (math.cosh(h) - e), -a * math.sqrt(e * e - 1) * math.sinh(h)


@dataclass
class Orbit:
    """Heliocentric osculating elements, ecliptic and equinox J2000 (angles in degrees)."""

    name: str
    key: str  # designation as COBS writes it: '12P', 'C/2025 R1'
    spkid: str
    e: float
    q: float
    tp: float  # time of perihelion, JD (TDB; the ~1 minute offset from UTC doesn't matter here)
    node: float
    peri: float
    incl: float
    m1: float | None = None
    k1: float | None = None

    def heliocentric(self, jd: float) -> Vec:
        """Equatorial J2000 position in au."""
        x, y = orbital_plane_position(self.e, self.q, jd - self.tp)
        o, w, i = math.radians(self.node), math.radians(self.peri), math.radians(self.incl)
        co, so, cw, sw, ci, si = math.cos(o), math.sin(o), math.cos(w), math.sin(w), math.cos(i), math.sin(i)
        xe = (co * cw - so * sw * ci) * x + (-co * sw - so * cw * ci) * y
        ye = (so * cw + co * sw * ci) * x + (-so * sw + co * cw * ci) * y
        ze = sw * si * x + cw * si * y
        ce, se = math.cos(OBLIQUITY), math.sin(OBLIQUITY)
        return xe, ye * ce - ze * se, ye * se + ze * ce

    def predicted_magnitude(self, r: float, delta: float) -> float | None:
        if self.m1 is None or self.k1 is None:
            return None
        return self.m1 + 5 * math.log10(delta) + self.k1 * math.log10(r)


def earth_heliocentric(when: datetime) -> Vec:
    return sky.vec(ae.HelioVector(ae.Body.Earth, sky.to_time(when)))


def geocentric(orbit: Orbit, when: datetime, earth: Vec | None = None) -> tuple[Vec, float, float]:
    """Astrometric geocentric vector (au, light-time corrected), heliocentric and geocentric distance."""
    earth = earth or earth_heliocentric(when)
    jd, tau = julian(when), 0.0
    for _ in range(3):
        helio = orbit.heliocentric(jd - tau)
        d = (helio[0] - earth[0], helio[1] - earth[1], helio[2] - earth[2])
        delta = math.sqrt(sky.dot(d, d))
        tau = delta / LIGHT_AU_PER_DAY
    return d, math.sqrt(sky.dot(helio, helio)), delta


def _radec(v: Vec) -> tuple[float, float]:
    n = math.sqrt(sky.dot(v, v))
    return math.degrees(math.atan2(v[1], v[0])) % 360, math.degrees(math.asin(v[2] / n))


def _angle(a: Vec, b: Vec) -> float:
    return math.degrees(math.atan2(math.sqrt(sky.dot(sky.cross(a, b), sky.cross(a, b))), sky.dot(a, b)))


def _orbit_key(prefix: str | None, pdes: str) -> str:
    if re.fullmatch(r"\d+[PDI](-[A-Z]+)?", pdes):
        return pdes
    return f"{prefix}/{pdes}" if prefix else pdes


def _orbit_from_row(row: dict[str, Any]) -> Orbit | None:
    try:
        return Orbit(
            name=row["full_name"].strip(), key=_orbit_key(row.get("prefix"), row["pdes"]), spkid=str(row["spkid"]),
            e=float(row["e"]), q=float(row["q"]), tp=float(row["tp"]),
            node=float(row["om"]), peri=float(row["w"]), incl=float(row["i"]),
            m1=_float(row.get("M1")), k1=_float(row.get("K1")),
        )
    except (KeyError, TypeError, ValueError):
        return None


# ---------------------------------------------------------------- SBDB lookup and Horizons

async def lookup(name: str) -> dict[str, Any]:
    """Resolve a comet or asteroid name with SBDB. Raises ValueError if unknown or ambiguous."""
    payload = await get_json(SBDB, {"sstr": name.strip(), "phys-par": "true", "full-prec": "true"},
                             source="JPL SBDB", ttl=3600, accept=(200, 300))
    if "list" in payload:
        options = [o.get("name") for o in payload["list"][:12]]
        raise ValueError(f"'{name}' matches several objects; use a fuller designation, e.g. one of: "
                         + "; ".join(o for o in options if o))
    if "object" not in payload:
        raise ValueError(f"JPL's small-body database has no comet or asteroid matching '{name}'.")
    return payload


def _elements(payload: dict[str, Any]) -> dict[str, float | None]:
    return {e["name"]: _float(e.get("value")) for e in (payload.get("orbit") or {}).get("elements", [])}


def _physical(payload: dict[str, Any]) -> dict[str, Any]:
    wanted = {"H": "absolute_magnitude_H", "diameter": "diameter_km", "albedo": "albedo",
              "rot_per": "rotation_period_h", "M1": "comet_total_magnitude_M1", "K1": "comet_magnitude_slope_K1"}
    out = {}
    for p in payload.get("phys_par", []):
        if p.get("name") in wanted and (value := _float(p.get("value"))) is not None:
            out[wanted[p["name"]]] = value
    return out


def nearest_perihelion(tp: float | None, period_days: float | None, now: datetime) -> str | None:
    """Perihelion date closest to now. SBDB's own tp can belong to an earlier apparition."""
    if tp is None:
        return None
    if period_days:
        tp += round((julian(now) - tp) / period_days) * period_days
    return from_julian(tp).date().isoformat()


def describe_body(payload: dict[str, Any]) -> dict[str, Any]:
    obj, el = payload["object"], _elements(payload)
    is_comet = obj.get("kind", "").startswith("c")
    out = {
        "name": obj.get("fullname"),
        "kind": "comet" if is_comet else "asteroid",
        "orbit_class": (obj.get("orbit_class") or {}).get("name"),
        "near_earth_object": obj.get("neo"),
        "potentially_hazardous": obj.get("pha"),
        "perihelion_au": _round(el.get("q"), 4),
        "aphelion_au": _round(el.get("ad"), 4),
        "eccentricity": _round(el.get("e"), 5),
        "inclination_deg": _round(el.get("i"), 2),
        "period_years": round(el["per"] / 365.25, 2) if el.get("per") else None,
        "nearest_perihelion": nearest_perihelion(el.get("tp"), el.get("per"), datetime.now(UTC)),
        **_physical(payload),
        "sbdb_url": f"https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr={obj.get('spkid')}",
    }
    return _drop_none(out)


def horizons_command(payload: dict[str, Any]) -> str:
    obj = payload["object"]
    return comet_command(obj["spkid"]) if obj.get("kind", "").startswith("c") else f"'DES={obj['spkid']};'"


def comet_command(spkid: str) -> str:
    # CAP picks the current apparition's orbit; NOFRAG skips fragments.
    return f"'DES={spkid};CAP;NOFRAG'"


def parse_horizons(result: str) -> list[dict[str, str]]:
    """Rows of a Horizons CSV observer table as {column name: raw value}."""
    if "$$SOE" not in result:
        message = " ".join(line.strip() for line in result.strip().splitlines()[-6:] if line.strip())
        raise UpstreamError(f"JPL Horizons returned no ephemeris: {message[:400]}")
    head, _, rest = result.partition("$$SOE")
    body = rest.partition("$$EOE")[0]
    header_line = next(line for line in reversed(head.splitlines()) if "Date__(UT)" in line)
    columns = [c.strip() for c in header_line.split(",")]
    rows = []
    for line in body.strip().splitlines():
        values = [v.strip() for v in line.split(",")]
        rows.append({c: v for c, v in zip(columns, values) if c})
    return rows


def _horizons_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%b-%d %H:%M").replace(tzinfo=UTC)


async def horizons_ephemeris(command: str, loc: Location | None, start: datetime, stop: datetime,
                             step: str) -> list[dict[str, str]]:
    params = {
        "format": "json", "COMMAND": command, "OBJ_DATA": "NO", "MAKE_EPHEM": "YES", "EPHEM_TYPE": "OBSERVER",
        "START_TIME": f"'{start.astimezone(UTC):%Y-%m-%d %H:%M}'",
        "STOP_TIME": f"'{stop.astimezone(UTC):%Y-%m-%d %H:%M}'",
        "STEP_SIZE": f"'{step}'", "CSV_FORMAT": "YES", "ANG_FORMAT": "DEG",
        "QUANTITIES": "'1,3,4,9,19,20,23,29'" if loc else "'1,3,9,19,20,23,29'",
    }
    if loc:
        params |= {"CENTER": "'coord@399'", "COORD_TYPE": "GEODETIC",
                   "SITE_COORD": f"'{loc.longitude:.5f},{loc.latitude:.5f},{loc.elevation_m / 1000:.3f}'"}
    else:
        params["CENTER"] = "'500@399'"
    payload = await get_json(HORIZONS, params, source="JPL Horizons", ttl=1800, timeout=60)
    if "error" in payload:
        raise UpstreamError(f"JPL Horizons: {payload['error'][:400]}")
    return parse_horizons(payload.get("result", ""))


def shape_row(row: dict[str, str], loc: Location | None) -> dict[str, Any]:
    when = _horizons_time(row["Date__(UT)__HR:MN"])
    mag = _float(row.get("APmag"))
    if mag is None:
        mag = _float(row.get("T-mag"))
    ra, dec = _float(row.get("R.A._(ICRF)")), _float(row.get("DEC_(ICRF)"))
    rate_ra, rate_dec = _float(row.get("dRA*cosD")), _float(row.get("d(DEC)/dt"))
    out: dict[str, Any] = {
        "time": fmt(when, loc or Location(0.0, 0.0)),
        "ra_deg": ra,
        "dec_deg": dec,
        "constellation": sky.constellation(ra, dec)["name"] if ra is not None and dec is not None else None,
        "magnitude": _round(mag, 1),
        "motion_arcsec_per_min": round(math.hypot(rate_ra, rate_dec) / 60, 2) if rate_ra is not None and rate_dec is not None else None,
        "sun_distance_au": _round(_float(row.get("r")), 4),
        "earth_distance_au": _round(_float(row.get("delta")), 5),
        "elongation_deg": _round(_float(row.get("S-O-T")), 1),
        "sky": {"/T": "evening", "/L": "morning"}.get(row.get("/r", "")),
    }
    if loc:
        alt, az = _float(row.get("Elev_(a-app)")), _float(row.get("Azi_(a-app)"))
        if alt is not None and az is not None:
            out |= {"altitude_deg": round(alt, 1), "azimuth_deg": round(az, 1), "direction": sky.compass(az)}
    return _drop_none(out)


async def ephemeris(name: str, loc: Location | None, start: datetime, days: float, step_hours: float) -> dict[str, Any]:
    payload = await lookup(name)
    rows_wanted = days * 24 / step_hours
    if rows_wanted > 500:
        raise ValueError(f"That would be {rows_wanted:.0f} rows; use a longer step or fewer days (500 rows max).")
    step = f"{round(step_hours * 60)}m"
    rows = await horizons_ephemeris(horizons_command(payload), loc, start, start + timedelta(days=days), step)
    return {
        "object": describe_body(payload),
        "location": loc.name if loc else "geocentric (no location given)",
        "count": len(rows),
        "ephemeris": [shape_row(r, loc) for r in rows],
        "source": "JPL Horizons",
        "note": "Magnitudes for comets are JPL's total-magnitude prediction and can be off by 1-2 magnitudes."
                if payload["object"].get("kind", "").startswith("c") else None,
    }


async def comet_detail(name: str, loc: Location | None, day: Any, days: int) -> dict[str, Any]:
    """One comet: tonight's best view, the brightness trend over the coming weeks, and COBS."""
    payload = await lookup(name)
    obj = payload["object"]
    if not obj.get("kind", "").startswith("c"):
        raise ValueError(f"{obj.get('fullname')} is an asteroid; use get_asteroid_ephemeris for it.")
    command = horizons_command(payload)
    if loc:
        n = sky.night(loc, day)
        start, stop = n.sunset or n.window[0], n.sunrise or n.window[1]
        trend_start = n.window[0] + (n.window[1] - n.window[0]) / 2
    else:
        start = trend_start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        stop = start + timedelta(hours=1)

    async def cobs_entry() -> dict[str, Any] | None:
        try:
            comets = await cobs_comets()
        except UpstreamError:
            return None
        return cobs_summary(comets.get(_orbit_key(obj.get("prefix"), obj.get("des", ""))), datetime.now(UTC))

    tonight_rows, trend_rows, cobs = await asyncio.gather(
        horizons_ephemeris(command, loc, start, stop, "15m") if loc else asyncio.sleep(0, []),
        horizons_ephemeris(command, loc, trend_start, trend_start + timedelta(days=days), "1d"),
        cobs_entry(),
    )
    out: dict[str, Any] = {"comet": describe_body(payload), "cobs": cobs}
    if loc and tonight_rows:
        times = [_horizons_time(r["Date__(UT)__HR:MN"]) for r in tonight_rows]
        track = [(_float(r.get("Elev_(a-app)")) or -90.0, _float(r.get("Azi_(a-app)")) or 0.0) for r in tonight_rows]
        sun_alts = [sky.sun_altitude(t, loc) for t in times]
        mid = shape_row(tonight_rows[len(tonight_rows) // 2], loc)
        out["tonight"] = _drop_none({
            "date": n.date.isoformat(),
            "location": loc.name,
            **best_view(track, times, sun_alts, loc),
            "predicted_magnitude_jpl": mid.get("magnitude"),
            "constellation": mid.get("constellation"),
            "elongation_deg": mid.get("elongation_deg"),
        })
    out["trend"] = [
        {k: v for k, v in shape_row(r, loc).items()
         if k in ("time", "magnitude", "constellation", "altitude_deg", "direction", "elongation_deg",
                  "sun_distance_au", "earth_distance_au", "sky")}
        for r in trend_rows
    ]
    out["trend_note"] = ("One row per day at the middle of the night" if loc else "One row per day") + \
        "; magnitudes are JPL's prediction from M1/K1, which COBS observations often correct by 1-2 magnitudes."
    out["source"] = "JPL SBDB and Horizons; COBS for observed brightness"
    return _drop_none(out)


# ---------------------------------------------------------------- bright comets

async def comet_orbits() -> list[Orbit]:
    """Every comet with perihelion inside 8 au (SBDB, about 3,500, cached for a day)."""
    fields = ("full_name", "pdes", "prefix", "spkid", "e", "q", "tp", "om", "w", "i", "M1", "K1")
    payload = await get_json_file(
        SBDB_QUERY,
        {"fields": ",".join(fields), "sb-kind": "c", "full-prec": "true", "sb-cdata": '{"AND":["q|LT|8"]}'},
        data_dir() / "comets" / "sbdb_orbits.json",
        source="JPL SBDB", max_age=86400, timeout=120,
    )
    names = payload.get("fields", fields)
    orbits = [_orbit_from_row(dict(zip(names, row))) for row in payload.get("data", [])]
    return [o for o in orbits if o is not None]


async def cobs_comets() -> dict[str, dict[str, Any]]:
    """COBS light-curve summary for each observed comet, keyed by designation (cached 6 hours)."""
    payload = await get_json_file(
        COBS_LIST, {"is-observed": "true", "is-active": "true"}, data_dir() / "comets" / "cobs_list.json",
        source="COBS", max_age=6 * 3600,
    )
    return {o["name"]: o for o in payload.get("objects", []) if o.get("name")}


def cobs_summary(entry: dict[str, Any] | None, now: datetime) -> dict[str, Any] | None:
    """COBS's fitted magnitudes for a comet. The 'current' value extrapolates the last fit, so it
    is only trusted within two years of the perihelion that fit belongs to."""
    if not entry:
        return None
    out = _drop_none({
        "current_magnitude": _float(entry.get("current_mag")),
        "peak_magnitude": _float(entry.get("peak_mag")),
        "peak_date": entry.get("peak_mag_date"),
        "perihelion_date": (entry.get("perihelion_date") or "")[:10] or None,
        "url": f"https://cobs.si/comet/{entry['id']}/" if entry.get("id") else None,
    })
    try:
        perihelion = datetime.fromisoformat(entry["perihelion_date"]).replace(tzinfo=UTC)
        stale = abs((now - perihelion).days) > 730
    except (KeyError, TypeError, ValueError):
        stale = True
    if stale:
        out.pop("current_magnitude", None)
    return out


def equipment_for(magnitude: float) -> str:
    for limit, label in COMET_EQUIPMENT:
        if magnitude <= limit:
            return label
    return "large telescope or camera"


def night_samples(loc: Location, day: Any) -> tuple[list[datetime], list[float]]:
    """Times every 15 minutes from sunset to sunrise, with the Sun's altitude at each."""
    n = sky.night(loc, day)
    start, end = n.sunset or n.window[0], n.sunrise or n.window[1]
    if end <= start:
        return [], []
    count = max(2, int((end - start) / timedelta(minutes=15)))
    times = [start + (end - start) * k / count for k in range(count + 1)]
    return times, [sky.sun_altitude(t, loc) for t in times]


def best_view(track: list[tuple[float, float]], times: list[datetime], sun_alts: list[float],
              loc: Location, min_altitude: float = 10.0) -> dict[str, Any]:
    """Highest point of an object over a night, preferring astronomical darkness to twilight."""
    for label, sun_limit in (("dark sky", -18.0), ("twilight", -6.0)):
        usable = [k for k in range(len(times)) if sun_alts[k] < sun_limit and track[k][0] >= min_altitude]
        if usable:
            k = max(usable, key=lambda j: track[j][0])
            return {"visible": True, "best_time": fmt(times[k], loc), "altitude_deg": round(track[k][0]),
                    "direction": sky.compass(track[k][1]), "sky_at_best": label}
    highest = max((track[k][0] for k in range(len(times)) if sun_alts[k] < -6), default=-90.0)
    return {"visible": False,
            "reason": "below the horizon all night" if highest < 0 else f"no higher than {round(highest)}° after dusk"}


async def _horizons_position(orbit: Orbit, when: datetime, gate: asyncio.Semaphore) -> dict[str, Any] | None:
    """Horizons' geocentric position for a comet at one moment, or None if Horizons fails."""
    for attempt in range(2):  # Horizons occasionally drops one of a burst of requests
        async with gate:
            try:
                rows = await horizons_ephemeris(comet_command(orbit.spkid), None, when, when + timedelta(minutes=1), "1m")
                return shape_row(rows[0], None) if rows else None
            except (UpstreamError, ValueError):
                if attempt:
                    return None
        await asyncio.sleep(1)
    return None


async def bright_comets(loc: Location | None, day: Any, max_magnitude: float, limit: int) -> dict[str, Any]:
    """Comets brighter than `max_magnitude`, brightest first, with where to find them tonight.

    Two-body propagation of every comet picks the candidates; Horizons then supplies accurate
    positions for the shortlist, since old elements of short-period comets can be degrees off.
    """
    async def cobs_or_error() -> dict[str, dict[str, Any]] | str:
        try:
            return await cobs_comets()
        except UpstreamError as exc:
            return str(exc)

    orbits, cobs = await asyncio.gather(comet_orbits(), cobs_or_error())
    cobs_error = cobs if isinstance(cobs, str) else None
    cobs = cobs if isinstance(cobs, dict) else {}

    now = datetime.now(UTC)
    if loc:
        times, sun_alts = night_samples(loc, day)
        when = times[len(times) // 2] if times else sky.local_noon(loc, day) + timedelta(hours=12)
    else:
        times, sun_alts, when = [], [], now
    earth = earth_heliocentric(when)
    sun_dir = (-earth[0], -earth[1], -earth[2])
    sun_ra, _ = _radec(sun_dir)

    candidates = []
    for orbit in orbits:
        geo, r, delta = geocentric(orbit, when, earth)
        observed = cobs_summary(cobs.get(orbit.key), now)
        current = observed.get("current_magnitude") if observed else None
        estimate = current if current is not None else orbit.predicted_magnitude(r, delta)
        # Leave a margin: two-body distances from old elements shift the prediction.
        if estimate is not None and estimate <= max_magnitude + 1.5:
            candidates.append((estimate, orbit, geo, r, delta, observed))
    candidates.sort(key=lambda c: c[0])
    candidates = candidates[: limit * 2 + 5]

    gate = asyncio.Semaphore(3)  # be gentle with Horizons
    refined = await asyncio.gather(*(_horizons_position(c[1], when, gate) for c in candidates))

    found, in_glare = [], []
    for (_, orbit, geo, r, delta, observed), precise in zip(candidates, refined):
        if precise:
            ra, dec = precise["ra_deg"], precise["dec_deg"]
            r, delta = precise.get("sun_distance_au", r), precise.get("earth_distance_au", delta)
            elongation = precise.get("elongation_deg")
            predicted = precise.get("magnitude")
            sky_side = precise.get("sky")
            rate = precise.get("motion_arcsec_per_min")
            motion = round(rate * 1440 / 3600, 2) if rate is not None else None
        else:
            ra, dec = _radec(geo)
            elongation = _angle(geo, sun_dir)
            predicted = orbit.predicted_magnitude(r, delta)
            sky_side = "evening" if sky.wrap180(ra - sun_ra) > 0 else "morning"
            motion = None
        current = observed.get("current_magnitude") if observed else None
        magnitude = current if current is not None else predicted
        if magnitude is None or magnitude > max_magnitude:
            continue
        if elongation is not None and elongation < 15:
            in_glare.append(orbit.name)
            continue
        found.append(_drop_none({
            "name": orbit.name,
            "magnitude": round(magnitude, 1),
            "magnitude_source": "COBS (fit to observers' reports)" if current is not None else "JPL M1/K1 prediction",
            "predicted_magnitude_jpl": round(predicted, 1) if predicted is not None else None,
            "equipment": equipment_for(magnitude),
            "constellation": sky.constellation(ra, dec)["name"],
            "ra_deg": round(ra, 3),
            "dec_deg": round(dec, 3),
            "motion_deg_per_day": motion,
            "elongation_deg": round(elongation, 1) if elongation is not None else None,
            "sky": sky_side,
            "sun_distance_au": round(r, 3),
            "earth_distance_au": round(delta, 3),
            "position_source": "JPL Horizons" if precise else "two-body estimate (Horizons unavailable)",
            "cobs": observed,
        }))

    found.sort(key=lambda c: c["magnitude"])
    found = found[:limit]
    if loc and times:
        tracks = sky.fast_tracks([(c["ra_deg"], c["dec_deg"]) for c in found], times, loc)
        for comet, track in zip(found, tracks):
            comet["tonight"] = best_view(track, times, sun_alts, loc)
    return _drop_none({
        "time": fmt(when, loc or Location(0.0, 0.0)),
        "location": loc.name if loc else None,
        "max_magnitude": max_magnitude,
        "count": len(found),
        "comets": found,
        "too_close_to_sun": in_glare or None,
        "cobs_unavailable": cobs_error,
        "note": "A comet's magnitude is its total brightness spread over the coma, so it looks fainter than a "
                "star of the same magnitude. JPL predictions are often off by 1-2 magnitudes; COBS values follow "
                "actual observations.",
    })


# ---------------------------------------------------------------- close approaches

def diameter_range_m(h: float) -> tuple[float, float]:
    """Diameter for absolute magnitude H across typical albedos (0.25 bright to 0.05 dark), in metres."""
    return tuple(1329e3 / math.sqrt(p) * 10 ** (-h / 5) for p in (0.25, 0.05))  # type: ignore[return-value]


def shape_approach(row: dict[str, Any], loc: Location | None) -> dict[str, Any]:
    when = datetime.strptime(row["cd"], "%Y-%b-%d %H:%M").replace(tzinfo=UTC)
    dist_au = float(row["dist"])
    h = _float(row.get("h"))
    diameter = _float(row.get("diameter"))
    if diameter is not None:
        size = {"diameter_m": round(diameter * 1000)}
    elif h is not None:
        lo, hi = diameter_range_m(h)
        size = {"estimated_diameter_m": f"{lo:.0f}-{hi:.0f}" if hi < 1000 else f"{lo / 1000:.1f}-{hi / 1000:.1f} km"}
    else:
        size = {}
    out = {
        "name": re.sub(r"^\((.*)\)$", r"\1", (row.get("fullname") or row["des"]).strip()),
        "time_utc": when.isoformat(timespec="minutes"),
        "time_local": fmt(when, loc) if loc else None,
        "time_uncertainty": row.get("t_sigma_f"),
        "distance_lunar": round(dist_au * AU_KM / LD_KM, 2),
        "distance_km": round(dist_au * AU_KM),
        "relative_velocity_km_s": round(float(row["v_rel"]), 1),
        "absolute_magnitude_H": h,
        **size,
    }
    return _drop_none(out)


async def close_approaches(start: datetime, days: int, max_distance_ld: float, max_h: float | None,
                           limit: int, loc: Location | None) -> dict[str, Any]:
    params: dict[str, Any] = {
        "date-min": start.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S"),
        "date-max": (start + timedelta(days=days)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S"),
        "dist-max": f"{max_distance_ld}LD", "sort": "date", "fullname": "true", "diameter": "true",
    }
    if max_h is not None:
        params["h-max"] = max_h
    payload = await get_json(CAD, params, source="JPL SBDB Close Approach Data", ttl=3600)
    names = payload.get("fields", [])
    rows = [dict(zip(names, r)) for r in payload.get("data", [])]
    approaches = [shape_approach(r, loc) for r in rows]
    return {
        "from": start.astimezone(UTC).isoformat(timespec="minutes"),
        "days": days,
        "max_distance_lunar": max_distance_ld,
        "total": len(approaches),
        "count": min(limit, len(approaches)),
        "approaches": approaches[:limit],
        "source": "JPL SBDB Close Approach Data (times TDB, within about a minute of UTC)",
        "note": "Distances are from Earth's centre; one lunar distance is 384,399 km. time_uncertainty is 3-sigma, "
                "written hh:mm or d_hh:mm. Sizes without a measured "
                "diameter are estimated from H for albedos 0.25 to 0.05. Use get_asteroid_ephemeris to see "
                "whether one is bright enough to observe.",
    }


# ---------------------------------------------------------------- fireballs

def _ground_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return math.radians(sky.separation_deg(lon1, lat1, lon2, lat2)) * EARTH_RADIUS_KM


def elevation_seen_from(distance_km: float, height_km: float) -> float:
    """Elevation angle of a point `height_km` up, `distance_km` away along the ground (spherical Earth)."""
    theta = distance_km / EARTH_RADIUS_KM
    ratio = EARTH_RADIUS_KM / (EARTH_RADIUS_KM + height_km)
    return math.degrees(math.atan2(math.cos(theta) - ratio, math.sin(theta)))


def shape_fireball(row: dict[str, Any], loc: Location | None) -> dict[str, Any]:
    when = datetime.strptime(row["date"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    lat, lon = _float(row.get("lat")), _float(row.get("lon"))
    if lat is not None and row.get("lat-dir") == "S":
        lat = -lat
    if lon is not None and row.get("lon-dir") == "W":
        lon = -lon
    alt = _float(row.get("alt"))
    out: dict[str, Any] = {
        "time_utc": when.isoformat(timespec="seconds"),
        "time_local": fmt(when, loc) if loc else None,
        "latitude": lat,
        "longitude": lon,
        "altitude_km": alt,
        "velocity_km_s": _float(row.get("vel")),
        "radiated_energy_joules": float(f"{float(row['energy']) * 1e10:.2g}") if row.get("energy") else None,
        "impact_energy_kt": _float(row.get("impact-e")),
    }
    if loc and lat is not None and lon is not None:
        distance = _ground_distance_km(loc.latitude, loc.longitude, lat, lon)
        out["distance_from_you_km"] = round(distance)
        if alt is not None:
            elevation = elevation_seen_from(distance, alt)
            out["elevation_from_you_deg"] = round(elevation, 1)
            out["above_your_horizon"] = elevation > 0
    return _drop_none(out)


async def fireballs(days: int, limit: int, loc: Location | None, max_distance_km: float | None) -> dict[str, Any]:
    start = datetime.now(UTC) - timedelta(days=days)
    params: dict[str, Any] = {"date-min": start.strftime("%Y-%m-%d"), "sort": "-date"}
    if max_distance_km is not None:
        params["req-loc"] = "true"
    else:
        params["limit"] = limit
    payload = await get_json(FIREBALL, params, source="CNEOS fireball database", ttl=3600)
    names = payload.get("fields", [])
    events = [shape_fireball(dict(zip(names, r)), loc) for r in payload.get("data", [])]
    if max_distance_km is not None:
        events = [e for e in events if e.get("distance_from_you_km", math.inf) <= max_distance_km]
    return {
        "since": start.date().isoformat(),
        "count": min(limit, len(events)),
        "fireballs": events[:limit],
        "source": "CNEOS fireball and bolide reports (US government sensors)",
        "note": "Only large events detected from space are listed: roughly metre-sized objects and up, a few "
                "dozen a year worldwide. Reports appear days to weeks after the event. Ordinary bright meteors "
                "are not included.",
    }
