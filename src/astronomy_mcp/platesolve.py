"""Plate solving through Astrometry.net's nova API, with a free account key read from the
ASTROMETRY_NET_API_KEY environment variable.

Uploads are marked private (not publicly visible, no commercial use or modification). A solve
usually takes one to several minutes, so callers wait a while and otherwise hand back the
submission id to check later.

Orientation comes from the solution's WCS file, not the API's `orientation` and `parity` fields,
whose convention differs between FITS and other uploads. In the WCS, pixel y counts rows from the
first row of the file: the top of a JPEG, PNG or TIFF as displayed.
"""

from __future__ import annotations

import asyncio
import io
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from astronomy_mcp import sky
from astronomy_mcp.http import UpstreamError, get_bytes, get_json, post_json
from astronomy_mcp.imaging import dms, hms
from astronomy_mcp.location import data_dir

API_URL = "https://nova.astrometry.net/api"
SITE_URL = "https://nova.astrometry.net"
KEY_ENV = "ASTROMETRY_NET_API_KEY"
SOURCE = "Astrometry.net"
FITS_SUFFIXES = {".fits", ".fit", ".fts"}
UNSUPPORTED_SUFFIXES = {".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2", ".dng", ".pef", ".srw", ".xisf", ".fz"}
MAX_UPLOAD_SIDE_PX = 3000  # larger 8-bit images are shrunk first; the solver doesn't need more
POLL_SECONDS = 5
PRIVATE = {"publicly_visible": "n", "allow_modifications": "n", "allow_commercial_use": "n"}

_sessions: dict[str, str] = {}


def api_key() -> str:
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise ValueError(
            f"Plate solving needs a free Astrometry.net API key. Sign in at {SITE_URL}, copy the key from "
            f"your profile page, and set {KEY_ENV} in this server's environment (the \"env\" block of "
            ".mcp.json or claude_desktop_config.json), then restart the server."
        )
    return key


async def _call(endpoint: str, payload: dict[str, Any], files: dict[str, tuple[str, bytes, str]] | None = None) -> dict[str, Any]:
    out = await post_json(f"{API_URL}/{endpoint}", {"request-json": json.dumps(payload)}, source=SOURCE,
                          files=files, timeout=300)
    if out.get("status") == "error":
        raise UpstreamError(f"Astrometry.net: {out.get('errormessage', 'unknown error')}")
    return out


async def _session(key: str, fresh: bool = False) -> str:
    if fresh or key not in _sessions:
        _sessions[key] = (await _call("login", {"apikey": key}))["session"]
    return _sessions[key]


# ---------------------------------------------------------------- the file to upload

@dataclass
class Upload:
    data: bytes
    filename: str
    width: int | None
    height: int | None
    shrink: float = 1.0  # original pixels per uploaded pixel


def fits_header(data: bytes) -> dict[str, Any]:
    """Keyword values from a FITS header (strings unquoted, numbers as floats)."""
    out: dict[str, Any] = {}
    for i in range(0, len(data) - 79, 80):
        card = data[i:i + 80].decode("ascii", "replace")
        key = card[:8].strip()
        if key == "END":
            break
        if card[8:10] != "= ":
            continue
        raw = card[10:]
        if raw.lstrip().startswith("'"):
            out[key] = raw.split("'")[1].strip()
            continue
        raw = raw.split("/")[0].strip()
        try:
            out[key] = float(raw)
        except ValueError:
            out[key] = raw
    return out


def prepare(path: Path) -> Upload:
    """Read an image for upload, shrinking large 8-bit images."""
    if path.suffix.lower() in UNSUPPORTED_SUFFIXES:
        raise ValueError(f"Astrometry.net can't read {path.suffix} files. Export a JPEG, PNG, TIFF or plain FITS "
                         "(a stretched JPEG solves fine).")
    if not path.is_file():
        raise ValueError(f"No file at {path}.")
    data = path.read_bytes()
    if path.suffix.lower() in FITS_SUFFIXES:
        if not data.startswith(b"SIMPLE"):
            raise ValueError(f"{path.name} is not a FITS file.")
        header = fits_header(data[:2880 * 10])
        width, height = header.get("NAXIS1"), header.get("NAXIS2")
        return Upload(data, path.name, int(width) if width else None, int(height) if height else None)
    try:
        image = Image.open(io.BytesIO(data))
    except UnidentifiedImageError as exc:
        raise ValueError(f"{path.name} is not an image Astrometry.net can read (JPEG, PNG, TIFF or FITS).") from exc
    width, height = image.size
    # 16-bit and float images would be clipped by a conversion to 8 bits, so they go up as they are.
    if max(width, height) <= MAX_UPLOAD_SIDE_PX or image.mode not in ("L", "RGB", "RGBA", "P", "LA"):
        return Upload(data, path.name, width, height)
    shrink = max(width, height) / MAX_UPLOAD_SIDE_PX
    small = image.convert("RGB").resize((round(width / shrink), round(height / shrink)), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    small.save(out, "JPEG", quality=92)
    return Upload(out.getvalue(), f"{path.stem}.jpg", width, height, shrink)


def _submissions_path() -> Path:
    return data_dir() / "platesolve" / "submissions.json"


def remember(submission_id: int, upload: Upload | None, hinted: bool) -> None:
    """Keep what a later check on this submission needs: the shrink factor, original size, hints."""
    path = _submissions_path()
    try:
        known = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        known = {}
    known[str(submission_id)] = {"hinted": hinted, **({"filename": upload.filename, "width": upload.width,
                                                       "height": upload.height, "shrink": upload.shrink} if upload else {})}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(known, indent=1), encoding="utf-8")


def recall(submission_id: int) -> tuple[Upload | None, bool]:
    """(the upload's size and shrink factor, whether hints were sent) for a submission made here."""
    try:
        meta = json.loads(_submissions_path().read_text(encoding="utf-8"))[str(submission_id)]
    except (OSError, ValueError, KeyError):
        return None, False
    upload = Upload(b"", meta["filename"], meta["width"], meta["height"], meta["shrink"]) if "filename" in meta else None
    return upload, meta.get("hinted", False)


def hints(shrink: float, scale: tuple[float, float] | None, center: tuple[float, float] | None,
          radius_deg: float) -> dict[str, Any]:
    """Solver hints: a pixel-scale range (arcsec per original pixel) and a search area."""
    out: dict[str, Any] = {}
    if scale:
        out |= {"scale_units": "arcsecperpix", "scale_type": "ul",
                "scale_lower": round(scale[0] * shrink, 4), "scale_upper": round(scale[1] * shrink, 4)}
    if center:
        out |= {"center_ra": round(center[0], 5), "center_dec": round(center[1], 5), "radius": radius_deg}
    return out


# ---------------------------------------------------------------- submitting and waiting

async def submit(source: Upload | str, solver_hints: dict[str, Any]) -> int:
    """Send a local image or a URL; returns the submission id."""
    key = api_key()
    for attempt in range(2):
        payload = {"session": await _session(key, fresh=attempt > 0), **PRIVATE, **solver_hints}
        try:
            if isinstance(source, str):
                out = await _call("url_upload", {**payload, "url": source})
            else:
                out = await _call("upload", payload, {"file": (source.filename, source.data, "application/octet-stream")})
            return int(out["subid"])
        except UpstreamError as exc:
            if attempt or "session" not in str(exc).lower():  # sessions expire; log in again once
                raise
    raise AssertionError("unreachable")


async def wait(submission_id: int, wait_seconds: float) -> tuple[str, int | None]:
    """('success' | 'failure' | 'pending', job id) after waiting up to `wait_seconds`."""
    deadline = time.monotonic() + wait_seconds
    job_id = None
    while True:
        try:
            sub = await get_json(f"{API_URL}/submissions/{submission_id}", source=SOURCE)
        except UpstreamError as exc:
            if "HTTP 404" in str(exc):
                raise ValueError(f"Astrometry.net has no submission {submission_id}.") from exc
            raise
        jobs = [j for j in sub.get("jobs") or [] if j]
        if jobs:
            job_id = jobs[-1]
            status = (await get_json(f"{API_URL}/jobs/{job_id}", source=SOURCE)).get("status")
            if status in ("success", "failure"):
                return status, job_id
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return "pending", job_id
        await asyncio.sleep(min(POLL_SECONDS, remaining))


# ---------------------------------------------------------------- reading the solution

def _edge(angle_ccw_from_up: float) -> str:
    edges = ("top", "left", "bottom", "right")
    return edges[round(angle_ccw_from_up / 90) % 4]


def orientation(cd: tuple[float, float, float, float], width: int | None, height: int | None) -> dict[str, Any]:
    """Which way north and east point in the image as displayed (first row at the top).

    The CD matrix maps a pixel step (dx right, dy down) to (east, north) degrees on the sky.
    """
    c11, c12, c21, c22 = cd
    det = c11 * c22 - c12 * c21

    def pa(dx: float, dy: float) -> float:  # position angle (east of north) of a direction in the image
        return math.degrees(math.atan2(c11 * dx + c12 * dy, c21 * dx + c22 * dy)) % 360

    def screen_angle(east: float, north: float) -> float:  # counterclockwise from up, as seen on screen
        dx, dy = (c22 * east - c12 * north) / det, (-c21 * east + c11 * north) / det
        return math.degrees(math.atan2(-dx, -dy)) % 360

    north, east = screen_angle(0, 1), screen_angle(1, 0)
    landscape = width is None or height is None or width >= height
    return {
        "north": f"{north:.0f}° counterclockwise from straight up (toward the {_edge(north)} edge)",
        "east": f"{east:.0f}° counterclockwise from straight up (toward the {_edge(east)} edge)",
        "mirrored": det < 0,
        "image_up_position_angle_deg": round(pa(0, -1), 1),
        "long_side_position_angle_deg": round((pa(1, 0) if landscape else pa(0, -1)) % 180, 1),
    }


async def solution(submission_id: int, job_id: int, upload: Upload | None) -> dict[str, Any]:
    calibration = await get_json(f"{API_URL}/jobs/{job_id}/calibration/", source=SOURCE)
    info = await get_json(f"{API_URL}/jobs/{job_id}/info/", source=SOURCE)
    wcs = await get_bytes(f"{SITE_URL}/wcs_file/{job_id}", source=SOURCE)
    header = fits_header(wcs)
    path = data_dir() / "platesolve" / f"job_{job_id}.wcs"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(wcs)

    shrink = upload.shrink if upload else 1.0
    width = upload.width if upload else int(header.get("IMAGEW") or 0) or None
    height = upload.height if upload else int(header.get("IMAGEH") or 0) or None
    ra, dec = calibration["ra"], calibration["dec"]
    w_arcsec, h_arcsec = calibration.get("width_arcsec"), calibration.get("height_arcsec")
    out: dict[str, Any] = {
        "status": "solved",
        "center": {"ra_deg": round(ra, 5), "dec_deg": round(dec, 5), "ra": hms(ra), "dec": dms(dec),
                   "constellation": sky.constellation(ra, dec)["name"]},
        "arcsec_per_pixel": round(calibration["pixscale"] * shrink, 3),
    }
    if w_arcsec and h_arcsec:
        out["field"] = {"width_arcmin": round(w_arcsec / 60, 1), "height_arcmin": round(h_arcsec / 60, 1),
                        "width_deg": round(w_arcsec / 3600, 3), "height_deg": round(h_arcsec / 3600, 3)}
    if all(k in header for k in ("CD1_1", "CD1_2", "CD2_1", "CD2_2")):
        out["orientation"] = orientation((header["CD1_1"], header["CD1_2"], header["CD2_1"], header["CD2_2"]), width, height)
    out |= {
        "objects_in_field": (info.get("objects_in_field") or [])[:40],
        "image_size_px": {"width": width, "height": height} if width and height else None,
        "links": {
            "job": f"{SITE_URL}/status/{submission_id}",
            "annotated_image": f"{SITE_URL}/annotated_display/{job_id}",
            "wcs_file": f"{SITE_URL}/wcs_file/{job_id}",
            "fits_with_wcs": f"{SITE_URL}/new_fits_file/{job_id}",
        },
        "wcs_saved_to": str(path),
        "submission_id": submission_id,
        "job_id": job_id,
        "note": "Orientation is for the image displayed with its first row at the top, as JPEG, PNG and TIFF files "
                "and most astro software show it. DS9 and some FITS viewers put the first row at the bottom, "
                "which flips north and south. long_side_position_angle_deg matches the rotation used by "
                "frame_target and generate_finder_chart.",
    }
    if shrink > 1:
        out["note"] += f" A copy shrunk {shrink:.2f}x was uploaded; the scale is for the original pixels."
    return {k: v for k, v in out.items() if v is not None}


def pending(submission_id: int, job_id: int | None, waited: float) -> dict[str, Any]:
    return {
        "status": "pending",
        "submission_id": submission_id,
        "job_id": job_id,
        "message": f"Still solving after {waited:.0f} s (a solve usually takes 1-5 minutes, longer when the queue "
                   f"is busy). Call plate_solve_image again with submission_id={submission_id} to check.",
        "job_page": f"{SITE_URL}/status/{submission_id}",
    }


def failed(submission_id: int, job_id: int | None, hinted: bool) -> dict[str, Any]:
    advice = ("Astrometry.net could not solve the image. Common causes: too few stars (a longer exposure or a "
              "less heavily processed image helps), trailed or badly out-of-focus stars, or a field narrower than "
              "about 5 arcminutes.")
    if hinted:
        advice += " The scale or position hints may be wrong; try again without them."
    return {"status": "failed", "submission_id": submission_id, "job_id": job_id, "message": advice,
            "job_page": f"{SITE_URL}/status/{submission_id}"}
