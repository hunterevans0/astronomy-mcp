"""Visual detectability of stars and deep-sky objects.

A threshold model in the spirit of Blackwell (1946), Schaefer (1990) and Clark's
"Visual Astronomy of the Deep Sky":

* The eye's point-source threshold against a background of surface brightness S
  follows the Hecht/Schaefer form already used for naked-eye limiting magnitude.
* An extended object's light can be spread over an area up to a critical area
  (Ricco's law) and still be detected, so the threshold for its surface
  brightness rises with apparent area and then saturates.
* A telescope at exit pupil e darkens sky and object alike by (e/7mm)^2 but
  magnifies the object's apparent area by M^2. We try a range of exit pupils and
  keep the best, as an observer swaps eyepieces.
* Galaxies and globular clusters are concentrated: we model the visible part as
  the central quarter of the catalogued area holding half the light.

The free constants (observer bonus, critical area) are calibrated against
Bortle's published class descriptions (Sky & Telescope, Feb 2001) and standard
Messier-marathon experience. See tests/test_visibility.py for the benchmark.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

EYE_PUPIL_MM = 7.0
OPTICS_LOSS_MAG = 0.25  # light lost in binoculars/telescopes
OBSERVER_BONUS_MAG = 0.5  # experienced observer, averted vision, dark adaptation
CRITICAL_AREA_ARCSEC2 = 1.0e7  # apparent area beyond which spreading light no longer helps
EXTINCTION_MAG_PER_AIRMASS = 0.2
CONCENTRATED_GROUPS = {"galaxy", "globular_cluster"}
TELESCOPE_EXIT_PUPILS_MM = (6.0, 4.0, 3.0, 2.0, 1.5, 1.0, 0.75)


def eye_threshold(background_sqm: float) -> float:
    """Faintest point source (mag) the dark-adapted eye sees against this background."""
    return 7.93 - 5 * math.log10(10 ** (4.316 - background_sqm / 5) + 1)


def _airmass(altitude_deg: float) -> float:
    alt = max(altitude_deg, 1.0)
    return 1.0 / (math.sin(math.radians(alt)) + 0.50572 * (alt + 6.07995) ** -1.6364)


def configurations(equipment: str, aperture_mm: float | None) -> list[tuple[float, float, float]]:
    """(aperture mm, exit pupil mm, magnification) options for the equipment."""
    if equipment == "naked_eye":
        return [(EYE_PUPIL_MM, EYE_PUPIL_MM, 1.0)]
    if equipment == "binoculars":
        d = aperture_mm or 50.0
        e = min(EYE_PUPIL_MM, 5.0)  # 10x50, 8x40, 15x70...
        return [(d, e, d / e)]
    d = aperture_mm or 150.0
    return [(d, e, d / e) for e in TELESCOPE_EXIT_PUPILS_MM if d / e <= 2.5 * d]


@dataclass
class Detection:
    margin_mag: float  # > 0 visible; larger is easier
    magnification: float
    exit_pupil_mm: float

    @property
    def visible(self) -> bool:
        return self.margin_mag >= 0


def detect(
    magnitude: float,
    sky_sqm: float,
    equipment: str,
    aperture_mm: float | None = None,
    major_arcmin: float | None = None,
    minor_arcmin: float | None = None,
    group: str | None = None,
    altitude_deg: float = 90.0,
) -> Detection:
    """Best-case detectability of an object (point source when no size is given)."""
    mag = magnitude + EXTINCTION_MAG_PER_AIRMASS * (_airmass(altitude_deg) - 1)
    if major_arcmin:
        area = math.pi / 4 * major_arcmin * (minor_arcmin or major_arcmin) * 3600
        if group in CONCENTRATED_GROUPS:
            area /= 4
            mag += 0.75
    else:
        area = 1.0  # a point source; any tiny area gives the same answer
    best: Detection | None = None
    for d, e, m in configurations(equipment, aperture_mm):
        loss = 0.0 if equipment == "naked_eye" else OPTICS_LOSS_MAG
        darken = 5 * math.log10(EYE_PUPIL_MM / e)
        threshold = eye_threshold(sky_sqm + darken + loss) + OBSERVER_BONUS_MAG
        apparent = area * m * m
        effective = apparent * CRITICAL_AREA_ARCSEC2 / (apparent + CRITICAL_AREA_ARCSEC2)
        surface = mag + 2.5 * math.log10(area) + darken + loss
        margin = threshold - (surface - 2.5 * math.log10(effective))
        if best is None or margin > best.margin_mag:
            best = Detection(round(margin, 2), round(m, 1), e)
    assert best is not None
    return best


def stellar_limit(sky_sqm: float, equipment: str, aperture_mm: float | None = None) -> float:
    """Faintest star visible at the best magnification."""
    return detect(0.0, sky_sqm, equipment, aperture_mm).margin_mag
