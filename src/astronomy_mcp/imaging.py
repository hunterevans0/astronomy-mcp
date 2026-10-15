"""Astrophotography arithmetic: field of view, image scale, framing a target, mosaics, and
untracked exposure limits (offline).

Image scale is 206.265 x pixel size (um) / focal length (mm) arcsec per pixel. Sampling is
judged against the seeing: about 2-3 pixels across the star's blur (FWHM) is well matched.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

# Sensor presets: width x height in mm, pixel size in um, resolution (where it's a fixed camera).
SENSORS: dict[str, dict[str, Any]] = {
    "full_frame": {"width_mm": 36.0, "height_mm": 24.0, "label": "35 mm full frame"},
    "aps_c_canon": {"width_mm": 22.3, "height_mm": 14.9, "label": "Canon APS-C"},
    "aps_c": {"width_mm": 23.5, "height_mm": 15.6, "label": "APS-C (Nikon, Sony, Fujifilm)"},
    "micro_four_thirds": {"width_mm": 17.3, "height_mm": 13.0, "label": "Micro Four Thirds"},
    "asi6200": {"width_px": 9576, "height_px": 6388, "pixel_um": 3.76, "label": "ZWO ASI6200 (IMX455)"},
    "asi2600": {"width_px": 6248, "height_px": 4176, "pixel_um": 3.76, "label": "ZWO ASI2600 (IMX571)"},
    "asi533": {"width_px": 3008, "height_px": 3008, "pixel_um": 3.76, "label": "ZWO ASI533 (IMX533)"},
    "asi294": {"width_px": 4144, "height_px": 2822, "pixel_um": 4.63, "label": "ZWO ASI294 (IMX294)"},
    "asi183": {"width_px": 5496, "height_px": 3672, "pixel_um": 2.4, "label": "ZWO ASI183 (IMX183)"},
    "asi585": {"width_px": 3840, "height_px": 2160, "pixel_um": 2.9, "label": "ZWO ASI585 (IMX585)"},
    "asi462": {"width_px": 1936, "height_px": 1096, "pixel_um": 2.9, "label": "ZWO ASI462 (IMX462)"},
    "asi120": {"width_px": 1280, "height_px": 960, "pixel_um": 3.75, "label": "ZWO ASI120"},
}
ARCSEC_PER_RADIAN = 206264.806


@dataclass
class Camera:
    width_mm: float
    height_mm: float
    pixel_um: float | None
    label: str


def camera(sensor: str | None, width_mm: float | None, height_mm: float | None, pixel_um: float | None,
           megapixels: float | None = None) -> Camera:
    """A preset sensor, or custom dimensions; pixel size can come from megapixels."""
    if sensor:
        key = sensor.strip().lower().replace(" ", "_").replace("-", "_")
        preset = SENSORS.get(key)
        if preset is None:
            raise ValueError(f"Unknown sensor '{sensor}'. Presets: {', '.join(SENSORS)}; or give width_mm and height_mm.")
        w = preset.get("width_mm") or preset["width_px"] * preset["pixel_um"] / 1000
        h = preset.get("height_mm") or preset["height_px"] * preset["pixel_um"] / 1000
        return Camera(w, h, pixel_um or preset.get("pixel_um") or _pixel_from_megapixels(w, h, megapixels), preset["label"])
    if width_mm and height_mm:
        return Camera(width_mm, height_mm, pixel_um or _pixel_from_megapixels(width_mm, height_mm, megapixels),
                      f"{width_mm:g} x {height_mm:g} mm sensor")
    raise ValueError("Give a sensor preset or the sensor's width_mm and height_mm.")


def _pixel_from_megapixels(width_mm: float, height_mm: float, megapixels: float | None) -> float | None:
    if not megapixels:
        return None
    return math.sqrt(width_mm * height_mm / (megapixels * 1e6)) * 1000


def angle_arcmin(size_mm: float, focal_mm: float) -> float:
    return math.degrees(2 * math.atan(size_mm / (2 * focal_mm))) * 60


def sampling(scale: float, seeing: float) -> dict[str, Any]:
    pixels_per_fwhm = seeing / scale
    if pixels_per_fwhm < 1.5:
        verdict = "undersampled: stars may look blocky; a longer focal length or smaller pixels would use the seeing"
    elif pixels_per_fwhm <= 3.5:
        verdict = "well matched to the seeing"
    else:
        verdict = "oversampled: binning 2x2 would improve signal per pixel without losing detail"
    return {"pixels_across_seeing_disk": round(pixels_per_fwhm, 1), "verdict": verdict}


def field_of_view(focal_mm: float, aperture_mm: float | None, cam: Camera | None, seeing: float,
                  eyepiece_mm: float | None, eyepiece_afov_deg: float | None) -> dict[str, Any]:
    out: dict[str, Any] = {"focal_length_mm": round(focal_mm, 1)}
    if aperture_mm:
        out["focal_ratio"] = f"f/{focal_mm / aperture_mm:.1f}"
        out["resolution_limit_arcsec"] = round(116 / aperture_mm, 2)
    if cam:
        w, h = angle_arcmin(cam.width_mm, focal_mm), angle_arcmin(cam.height_mm, focal_mm)
        camera_out: dict[str, Any] = {
            "sensor": cam.label,
            "field_arcmin": {"width": round(w, 1), "height": round(h, 1)},
            "field_deg": {"width": round(w / 60, 2), "height": round(h / 60, 2)},
            "diagonal_deg": round(math.hypot(w, h) / 60, 2),
        }
        if cam.pixel_um:
            scale = ARCSEC_PER_RADIAN * cam.pixel_um / 1000 / focal_mm
            camera_out["image_scale_arcsec_per_pixel"] = round(scale, 2)
            camera_out["sampling"] = sampling(scale, seeing)
        out["camera"] = camera_out
    if eyepiece_mm:
        magnification = focal_mm / eyepiece_mm
        afov = eyepiece_afov_deg or 52.0
        visual: dict[str, Any] = {
            "magnification": round(magnification),
            "true_field_deg": round(afov / magnification, 2),
            "true_field_arcmin": round(afov / magnification * 60),
            "apparent_field_assumed_deg": None if eyepiece_afov_deg else 52,
        }
        if aperture_mm:
            visual["exit_pupil_mm"] = round(aperture_mm / magnification, 1)
            if magnification > 2 * aperture_mm:
                visual["warning"] = f"above the useful maximum of about {round(2 * aperture_mm)}x for this aperture"
            elif aperture_mm / magnification > 7:
                visual["warning"] = "exit pupil wider than a dark-adapted eye's ~7 mm; some light is wasted"
        out["eyepiece"] = {k: v for k, v in visual.items() if v is not None}
    return out


# ---------------------------------------------------------------- framing and mosaics

def frame(target_name: str, width_arcmin: float, height_arcmin: float, angle_deg: float | None,
          fov_w: float, fov_h: float, focal_mm: float) -> dict[str, Any]:
    """How a target sits in the frame, and what to change if it doesn't fit well."""
    long_fov, short_fov = max(fov_w, fov_h), min(fov_w, fov_h)
    major, minor = max(width_arcmin, height_arcmin), min(width_arcmin, height_arcmin)
    fits = major <= long_fov * 0.95 and minor <= short_fov * 0.95
    fill = major / long_fov
    out: dict[str, Any] = {
        "target": target_name,
        "target_size_arcmin": {"major": round(major, 1), "minor": round(minor, 1)},
        "field_arcmin": {"width": round(fov_w, 1), "height": round(fov_h, 1)},
        "fits": fits,
        "fills_percent_of_long_side": round(100 * fill),
    }
    if angle_deg is not None and major > minor * 1.2:
        out["orientation"] = (f"Major axis at position angle {angle_deg:.0f}° (east of north). Rotate the camera so "
                              f"the sensor's long side lies along it: long side at {angle_deg % 180:.0f}° from north.")
    if not fits:
        out["suggestion"] = (f"Too big for one frame. A focal length of about {focal_mm * long_fov * 0.8 / major:.0f} mm "
                             "would fit it, or use plan_mosaic.")
    elif fill < 0.15:
        out["suggestion"] = (f"Small in the frame. About {focal_mm * 0.6 / fill:.0f} mm of focal length (e.g. a Barlow) "
                             "would make it fill ~60% of the long side, if the seeing allows.")
    else:
        out["suggestion"] = "A good fit."
    return out


def _offset_to_radec(ra0: float, dec0: float, xi_arcmin: float, eta_arcmin: float) -> tuple[float, float]:
    """Inverse gnomonic projection: east (xi) and north (eta) offsets from (ra0, dec0) to RA/Dec."""
    xi, eta = math.radians(xi_arcmin / 60), math.radians(eta_arcmin / 60)
    a0, d0 = math.radians(ra0), math.radians(dec0)
    denom = math.cos(d0) - eta * math.sin(d0)
    ra = a0 + math.atan2(xi, denom)
    dec = math.atan2(math.sin(d0) + eta * math.cos(d0), math.hypot(xi, denom))
    return math.degrees(ra) % 360, math.degrees(dec)


def hms(ra_deg: float) -> str:
    total = ra_deg / 15 * 3600
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}h{int(m):02d}m{s:04.1f}s"


def dms(dec_deg: float) -> str:
    sign = "-" if dec_deg < 0 else "+"
    total = abs(dec_deg) * 3600
    d, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{sign}{int(d):02d}°{int(m):02d}'{s:04.1f}\""


def panels_needed(size: float, fov: float, overlap: float) -> int:
    if size <= fov:
        return 1
    return math.ceil((size - fov * overlap) / (fov * (1 - overlap)))


def mosaic(ra: float, dec: float, width_arcmin: float, height_arcmin: float, angle_deg: float,
           fov_w: float, fov_h: float, overlap: float) -> dict[str, Any]:
    """A grid of panels covering width x height arcminutes around (ra, dec).

    `angle_deg` is the position angle (east of north) of the mosaic's width axis; the camera is
    rotated to the same angle so the sensor's width runs along it.
    """
    cols, rows = panels_needed(width_arcmin, fov_w, overlap), panels_needed(height_arcmin, fov_h, overlap)
    step_x, step_y = fov_w * (1 - overlap), fov_h * (1 - overlap)
    pa = math.radians(angle_deg)
    along = (math.sin(pa), math.cos(pa))  # (east, north) unit vector of the width axis
    across = (-math.cos(pa), math.sin(pa))  # perpendicular: the height axis
    panels = []
    for r in range(rows):
        for c in range(cols):
            x = (c - (cols - 1) / 2) * step_x
            y = (r - (rows - 1) / 2) * step_y
            east, north = x * along[0] + y * across[0], x * along[1] + y * across[1]
            p_ra, p_dec = _offset_to_radec(ra, dec, east, north)
            panels.append({"panel": len(panels) + 1, "row": r + 1, "column": c + 1,
                           "offset_arcmin": {"east": round(east, 1), "north": round(north, 1)},
                           "ra_deg": round(p_ra, 5), "dec_deg": round(p_dec, 5), "ra": hms(p_ra), "dec": dms(p_dec)})
    return {
        "grid": f"{cols} columns x {rows} rows",
        "panels_total": cols * rows,
        "overlap_percent": round(overlap * 100),
        "camera_rotation_deg": round(angle_deg % 180, 1),
        "covered_arcmin": {"width": round(fov_w + (cols - 1) * step_x, 1), "height": round(fov_h + (rows - 1) * step_y, 1)},
        "panels": panels,
        "note": f"Columns step along position angle {angle_deg % 360:.0f}°, rows along {(angle_deg - 90) % 360:.0f}°; "
                "each panel's offset from the centre is given in arcminutes east and north. Rotate the camera so the "
                "sensor's long side lies along the mosaic's width.",
    }


# ---------------------------------------------------------------- untracked exposures

def npf_seconds(focal_mm: float, f_number: float, pixel_um: float, dec_deg: float = 0.0) -> float:
    """Simplified NPF rule (F. Michaud, Societe Astronomique du Havre): (35 N + 30 p) / f, lengthened by
    1/cos(dec) because stars away from the celestial equator drift more slowly across the sensor."""
    return (35 * f_number + 30 * pixel_um) / focal_mm / max(math.cos(math.radians(dec_deg)), 0.05)


def exposure(focal_mm: float, f_number: float, cam: Camera | None, pixel_um: float | None, crop_factor: float | None,
             dec_deg: float | None) -> dict[str, Any]:
    pixel = pixel_um or (cam.pixel_um if cam else None)
    if pixel is None:
        raise ValueError("The NPF rule needs the pixel size: give pixel_um, a sensor preset, or the sensor size with megapixels.")
    crop = crop_factor or (round(43.27 / math.hypot(cam.width_mm, cam.height_mm), 2) if cam else 1.0)
    at_equator = npf_seconds(focal_mm, f_number, pixel)
    out: dict[str, Any] = {
        "npf_seconds_celestial_equator": round(at_equator, 1),
        "rule_of_500_seconds": round(500 / (focal_mm * crop), 1),
        "pixel_um": round(pixel, 2),
        "crop_factor": crop,
    }
    if dec_deg is not None:
        out["target_declination_deg"] = round(dec_deg, 1)
        out["npf_seconds_at_target"] = round(npf_seconds(focal_mm, f_number, pixel, dec_deg), 1)
    out["note"] = ("NPF limits star trailing to about what the pixels and lens can resolve: the simplified rule "
                   "(35 x f-number + 30 x pixel pitch) / focal length. The 500 rule is older and too long for modern "
                   "high-resolution sensors. Near the celestial pole stars barely move, so exposures there can be far longer.")
    return out
