"""Sky survey images: cutouts from DSS, Pan-STARRS, SDSS, 2MASS and others through CDS hips2fits,
with NASA SkyView as a fallback for the DSS plates.

Images are gnomonic (TAN) projections centred on the target, north up and east left. hips2fits
takes the field as the image width, so the scale is fov / width degrees per pixel.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from astronomy_mcp.http import UpstreamError, get_bytes
from astronomy_mcp.location import data_dir

HIPS2FITS_URL = "https://alasky.cds.unistra.fr/hips-image-services/hips2fits"
SKYVIEW_URL = "https://skyview.gsfc.nasa.gov/current/cgi/runquery.pl"
WIDE_FIELD_DEG = 5.0  # above this, the all-sky photographic mosaic looks better than plate scans


@dataclass(frozen=True)
class Survey:
    hips: str
    label: str
    skyview: str | None = None  # SkyView survey name to fall back on
    min_dec: float = -90.0
    coverage: str = "whole sky"


SURVEYS: dict[str, Survey] = {
    "dss2_color": Survey("CDS/P/DSS2/color", "DSS2 colour (POSS-II and UKST plates)", "DSS2 Red"),
    "dss2_red": Survey("CDS/P/DSS2/red", "DSS2 red", "DSS2 Red"),
    "dss2_blue": Survey("CDS/P/DSS2/blue", "DSS2 blue", "DSS2 Blue"),
    "panstarrs_color": Survey("CDS/P/PanSTARRS/DR1/color-z-zg-g", "Pan-STARRS DR1 colour (g, z)", min_dec=-30.0,
                              coverage="north of declination -30°"),
    "panstarrs_g": Survey("CDS/P/PanSTARRS/DR1/g", "Pan-STARRS DR1 g", min_dec=-30.0, coverage="north of declination -30°"),
    "panstarrs_r": Survey("CDS/P/PanSTARRS/DR1/r", "Pan-STARRS DR1 r", min_dec=-30.0, coverage="north of declination -30°"),
    "sdss_color": Survey("CDS/P/SDSS9/color", "SDSS DR9 colour", coverage="about a third of the sky, mostly away from the Milky Way"),
    "legacy_color": Survey("CDS/P/DESI-Legacy-Surveys/DR10/color", "DESI Legacy Imaging Surveys DR10 colour",
                           coverage="most of the sky away from the Milky Way"),
    "2mass_color": Survey("CDS/P/2MASS/color", "2MASS near-infrared colour (J, H, K)"),
    "wise_color": Survey("CDS/P/allWISE/color", "AllWISE mid-infrared colour"),
    "mellinger_color": Survey("CDS/P/Mellinger/color", "Mellinger all-sky photographic mosaic (for wide fields)"),
}
FORMATS = ("jpg", "png", "fits")


def pick_survey(name: str, fov_deg: float, grayscale: bool = False) -> str:
    """Resolve 'auto' to a survey that suits the field."""
    if name != "auto":
        if name not in SURVEYS:
            raise ValueError(f"Unknown survey '{name}'. Choose from: auto, {', '.join(SURVEYS)}.")
        return name
    if fov_deg > WIDE_FIELD_DEG:
        return "mellinger_color"
    return "dss2_red" if grayscale else "dss2_color"


def _check_coverage(survey: Survey, dec: float) -> None:
    if dec < survey.min_dec:
        raise ValueError(f"{survey.label} covers only {survey.coverage}; this position is at declination {dec:.1f}°. "
                         "Use a DSS2 survey instead.")


def _is_blank(data: bytes) -> bool:
    """hips2fits returns a uniform image where a survey has no data."""
    lo, hi = Image.open(io.BytesIO(data)).convert("L").getextrema()
    return hi - lo < 3


async def _skyview(survey: Survey, ra: float, dec: float, fov_deg: float, width: int, height: int, fmt: str) -> bytes:
    params = {
        "Survey": survey.skyview, "Position": f"{ra:.6f},{dec:.6f}", "Coordinates": "J2000", "Projection": "Tan",
        "Pixels": f"{width},{height}", "Size": f"{fov_deg:.6f},{fov_deg * height / width:.6f}",
        "Return": {"jpg": "JPEG", "png": "PNG", "fits": "FITS"}[fmt],
    }
    return await get_bytes(SKYVIEW_URL, params, source="NASA SkyView", timeout=90)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9.+-]+", "_", text.lower()).strip("_")[:80] or "field"


def output_path(folder: str, stem: str, ext: str) -> Path:
    path = data_dir() / folder / f"{slug(stem)}.{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


async def fetch(survey_key: str, ra: float, dec: float, fov_deg: float, width: int, height: int,
                fmt: str = "jpg", name: str | None = None) -> tuple[bytes, str, Path]:
    """(image bytes, where they came from, saved file) for a north-up, east-left cutout.

    Survey images don't change, so the saved file doubles as a cache. Its name carries the
    position, so a planet's chart on another night isn't served from an old cutout.
    """
    survey = SURVEYS[survey_key]
    _check_coverage(survey, dec)
    stem = f"{name + '_' if name else ''}{survey_key}_{fov_deg:.4g}deg_{width}x{height}_{ra:.3f}{dec:+.3f}"
    path = output_path("images", stem, fmt)
    if path.exists():
        return path.read_bytes(), f"{survey.label} (saved copy of an earlier download)", path
    source = f"{survey.label} via CDS hips2fits ({survey.hips})"
    params = {"hips": survey.hips, "ra": f"{ra:.6f}", "dec": f"{dec:.6f}", "fov": f"{fov_deg:.6f}", "width": width,
              "height": height, "projection": "TAN", "coordsys": "icrs", "format": fmt}
    try:
        data = await get_bytes(HIPS2FITS_URL, params, source="CDS hips2fits", timeout=90)
    except UpstreamError as exc:
        if not survey.skyview:
            raise
        try:
            data = await _skyview(survey, ra, dec, fov_deg, width, height, fmt)
        except UpstreamError:
            raise exc from None
        source = f"{survey.skyview} via NASA SkyView (hips2fits unavailable)"
    if fmt != "fits" and _is_blank(data):
        raise ValueError(f"{survey.label} has no data at RA {ra:.3f}°, Dec {dec:.3f}° (it covers {survey.coverage}). "
                         "Try dss2_color, which covers the whole sky.")
    path.write_bytes(data)
    return data, source, path


def preview(data: bytes, max_px: int = 1024, max_bytes: int = 600_000) -> tuple[bytes, str]:
    """A copy small enough to return inline: (bytes, image format)."""
    image = Image.open(io.BytesIO(data))
    if max(image.size) <= max_px and len(data) <= max_bytes and image.format in ("JPEG", "PNG"):
        return data, image.format.lower()
    image.thumbnail((max_px, max_px))
    out = io.BytesIO()
    image.convert("RGB").save(out, "JPEG", quality=88)
    return out.getvalue(), "jpeg"


def describe(survey_key: str, fov_deg: float, width: int, height: int) -> dict[str, Any]:
    scale = fov_deg * 3600 / width
    return {
        "survey": survey_key,
        "field_deg": {"width": round(fov_deg, 4), "height": round(fov_deg * height / width, 4)},
        "field_arcmin": {"width": round(fov_deg * 60, 2), "height": round(fov_deg * 60 * height / width, 2)},
        "arcsec_per_pixel": round(scale, 3),
        "size_px": {"width": width, "height": height},
        "orientation": "north up, east left (as on the sky, not mirrored)",
    }
