"""Calibration benchmark for the detectability model.

Cases come from Bortle's class descriptions (J. Bortle, "Introducing the Bortle
Dark-Sky Scale", Sky & Telescope, Feb 2001) and long-standing observing
experience (every Messier object is reachable in a 100 mm scope from a dark site,
the Messier-marathon standard; low-surface-brightness face-on galaxies wash out
under city skies). Objects are assumed high in a moonless sky. Magnitudes and
sizes are OpenNGC's.
"""

import pytest

from astronomy_mcp import conditions
from astronomy_mcp.visibility import detect, stellar_limit

# name: (V mag, major arcmin, minor arcmin, group)
OBJECTS = {
    "M1": (8.4, 8.0, 4.0, "supernova_remnant"),
    "M4": (5.4, 28.2, None, "globular_cluster"),
    "M5": (5.95, 15.0, None, "globular_cluster"),
    "M13": (5.8, 16.5, None, "globular_cluster"),
    "M15": (6.3, 11.1, None, "globular_cluster"),
    "M22": (6.17, 12.6, None, "globular_cluster"),
    "M27": (7.4, 6.7, None, "planetary_nebula"),
    "M31": (3.44, 177.83, 69.66, "galaxy"),
    "M33": (5.79, 62.09, 36.73, "galaxy"),
    "M42": (4.0, 90.0, 60.0, "nebula"),
    "M44": (3.1, 108.6, None, "open_cluster"),
    "M45": (1.2, 150.0, 150.0, "open_cluster"),
    "M51": (8.36, 13.71, 11.67, "galaxy"),
    "M57": (8.8, 1.27, None, "planetary_nebula"),
    "M74": (9.31, 9.89, 9.33, "galaxy"),
    "M76": (10.1, 1.12, None, "planetary_nebula"),
    "M81": (6.92, 21.63, 11.25, "galaxy"),
    "M82": (8.3, 10.99, 5.11, "galaxy"),
    "M91": (10.96, 5.55, 4.52, "galaxy"),
    "M97": (9.9, 3.58, None, "planetary_nebula"),
    "M98": (10.84, 11.04, 2.66, "galaxy"),
    "M101": (7.9, 23.99, 23.07, "galaxy"),
}


def visible(name, bortle, equipment, aperture=None, sqm=None):
    mag, a, b, group = OBJECTS[name]
    sky = sqm if sqm is not None else conditions.sqm_from_bortle(bortle)
    return detect(mag, sky, equipment, aperture, a, b, group).visible


# (object, Bortle class, expected naked-eye visibility)
NAKED_EYE = [
    # Class 1: "M33 ... an obvious naked-eye object"; "M4, M5, M15 and M22 are all distinct naked-eye objects"
    ("M33", 1, True), ("M4", 1, True), ("M5", 1, True), ("M15", 1, True), ("M22", 1, True),
    # Class 2: "M33 is easily seen with direct vision"; Class 3: M33 still seen with averted vision
    ("M33", 2, True), ("M33", 3, True),
    # Class 6: "M33 is impossible to see without binoculars, and M31 is only modestly apparent"
    ("M33", 5, False), ("M33", 6, False), ("M31", 6, True), ("M44", 6, True),
    # Class 9: only the brightest clusters, such as the Pleiades, remain
    ("M31", 9, False), ("M44", 9, False), ("M45", 9, True),
    # M81 needs exceptional skies and eyes; not a rural-sky naked-eye object
    ("M81", 3, False),
]


@pytest.mark.parametrize("name, bortle, expected", NAKED_EYE)
def test_bortle_scale_naked_eye(name, bortle, expected):
    assert visible(name, bortle, "naked_eye") is expected


@pytest.mark.parametrize("bortle", [1, 2, 3, 4, 5, 6])
def test_m31_naked_eye_through_bortle_6(bortle):
    assert visible("M31", bortle, "naked_eye")


@pytest.mark.parametrize("name", ["M74", "M76", "M91", "M98", "M101", "M1", "M97", "M33"])
def test_hardest_messiers_in_100mm_from_a_dark_site(name):
    assert visible(name, 3, "telescope", 100)


@pytest.mark.parametrize("name, expected", [
    ("M57", True), ("M13", True), ("M27", True), ("M42", True), ("M82", True),
    ("M74", False), ("M101", False),
])
def test_city_sky_200mm(name, expected):
    assert visible(name, 8, "telescope", 200) is expected


# Cases observers describe as borderline should land near zero margin, not firmly either side.
MARGINAL = [
    ("M33", 4, "naked_eye", None),  # Class 4: "M33 is a difficult averted-vision object"
    ("M31", 7, "naked_eye", None),  # Class 7: "M31 and M44 may be glimpsed ... but are very indistinct"
    ("M44", 7, "naked_eye", None),
    ("M33", 8, "telescope", 200),  # the core is sometimes glimpsed from a city
]


@pytest.mark.parametrize("name, bortle, equipment, aperture", MARGINAL)
def test_borderline_cases_are_marginal(name, bortle, equipment, aperture):
    mag, a, b, group = OBJECTS[name]
    margin = detect(mag, conditions.sqm_from_bortle(bortle), equipment, aperture, a, b, group).margin_mag
    assert -0.75 <= margin <= 0.75


@pytest.mark.parametrize("name", ["M31", "M33", "M13", "M81", "M82", "M51", "M42"])
def test_10x50_binoculars_dark_site(name):
    assert visible(name, 3, "binoculars", 50)


def test_full_moon_hides_m33_from_a_dark_site():
    moonlit = conditions.sqm_with_moon(conditions.sqm_from_bortle(2), -12.7, 60)
    assert not visible("M33", 2, "naked_eye", sqm=moonlit)


@pytest.mark.parametrize(
    "bortle, equipment, aperture, low, high",
    [
        (2, "naked_eye", None, 6.2, 7.3),  # typical dark-site NELM
        (8, "naked_eye", None, 3.6, 4.8),
        (3, "binoculars", 50, 9.5, 11.5),  # 10x50 from a dark site
        (3, "telescope", 200, 14.0, 15.8),  # 8-inch at high power
    ],
)
def test_stellar_limits_are_plausible(bortle, equipment, aperture, low, high):
    assert low <= stellar_limit(conditions.sqm_from_bortle(bortle), equipment, aperture) <= high


def test_low_altitude_makes_things_harder():
    mag, a, b, group = OBJECTS["M13"]
    high = detect(mag, 21.4, "telescope", 150, a, b, group, altitude_deg=80)
    low = detect(mag, 21.4, "telescope", 150, a, b, group, altitude_deg=10)
    assert low.margin_mag < high.margin_mag
