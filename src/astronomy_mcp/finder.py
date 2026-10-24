"""Finder charts: a survey image with the target marked, the camera frame or eyepiece field,
Telrad rings, nearby catalogued objects, compass and scale bar, drawn with Pillow (offline once
the survey image is in hand).

Positions go through the same gnomonic projection hips2fits uses, so overlays line up with the
image. Text sticks to characters Pillow's bundled font has (no primes or multiplication sign).
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont, ImageOps

ORIENTATIONS = {
    "north_up": "north up, east left: the naked-eye, binocular and correct-image finder view",
    "mirrored": "north up, east right: the mirror image through a star diagonal (refractor, SCT, Maksutov)",
    "rotated": "north down, east right: rotated 180° as in a Newtonian or straight-through finder",
}
STYLES = ("print", "photo")
TELRAD_RADII_ARCMIN = (15.0, 60.0, 120.0)  # the 0.5°, 2° and 4° rings
NICE_SCALES_ARCMIN = (0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600)


@dataclass
class Frame:
    """A camera field: long side along `angle_deg` (position angle, east of north)."""

    width_arcmin: float
    height_arcmin: float
    angle_deg: float
    label: str


@dataclass
class Marker:
    name: str
    ra_deg: float
    dec_deg: float
    size_arcmin: float | None = None


@dataclass
class ChartSpec:
    ra_deg: float
    dec_deg: float
    fov_deg: float
    title: str
    subtitle: str
    target_label: str
    credit: str
    frame: Frame | None = None
    eyepiece_arcmin: float | None = None
    eyepiece_label: str | None = None
    telrad: bool = False
    objects: list[Marker] = field(default_factory=list)
    orientation: str = "north_up"
    style: str = "print"


def project(ra: float, dec: float, ra0: float, dec0: float) -> tuple[float, float] | None:
    """Gnomonic projection: (east, north) tangent-plane offsets in degrees, or None if more than 90° away."""
    a, d, a0, d0 = map(math.radians, (ra, dec, ra0, dec0))
    cos_c = math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(a - a0)
    if cos_c <= 0:
        return None
    xi = math.cos(d) * math.sin(a - a0) / cos_c
    eta = (math.cos(d0) * math.sin(d) - math.sin(d0) * math.cos(d) * math.cos(a - a0)) / cos_c
    return math.degrees(xi), math.degrees(eta)


def angle_label(arcmin: float) -> str:
    if arcmin >= 60:
        return f"{arcmin / 60:.3g}°"
    if arcmin >= 1:
        return f"{arcmin:.3g}'"
    return f"{arcmin * 60:.3g}\""


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=size)
    except (TypeError, OSError):  # Pillow built without FreeType
        return ImageFont.load_default()


class _Canvas:
    """Maps tangent-plane offsets to chart pixels, applying the chosen orientation."""

    def __init__(self, size: int, header: int, fov_deg: float, orientation: str):
        self.size, self.header, self.orientation = size, header, orientation
        self.deg_per_px = fov_deg / size

    def offset(self, east_deg: float, north_deg: float) -> tuple[float, float]:
        x = self.size / 2 - east_deg / self.deg_per_px
        y = self.size / 2 - north_deg / self.deg_per_px
        if self.orientation in ("mirrored", "rotated"):
            x = self.size - x
        if self.orientation == "rotated":
            y = self.size - y
        return x, y + self.header

    def direction(self, east: float, north: float) -> tuple[float, float]:
        """Unit vector on the chart for a direction on the sky."""
        (x0, y0), (x1, y1) = self.offset(0, 0), self.offset(east, north)
        length = math.hypot(x1 - x0, y1 - y0)
        return (x1 - x0) / length, (y1 - y0) / length

    def inside(self, x: float, y: float, margin: float = 0) -> bool:
        return margin <= x <= self.size - margin and self.header + margin <= y <= self.header + self.size - margin


def _base_image(data: bytes, size: int, orientation: str, style: str) -> Image.Image:
    image = Image.open(io.BytesIO(data))
    if image.size != (size, size):
        image = image.resize((size, size), Image.Resampling.LANCZOS)
    if style == "print":
        image = ImageOps.invert(ImageOps.autocontrast(image.convert("L"), cutoff=(1, 0.2))).convert("RGB")
    else:
        image = image.convert("RGB")
    if orientation in ("mirrored", "rotated"):
        image = ImageOps.mirror(image)
    if orientation == "rotated":
        image = ImageOps.flip(image)
    return image


def render(data: bytes, spec: ChartSpec, size: int = 900) -> Image.Image:
    """Draw the chart on a size x size survey image (north up, east left, `spec.fov_deg` wide)."""
    if spec.orientation not in ORIENTATIONS:
        raise ValueError(f"orientation must be one of {', '.join(ORIENTATIONS)}")
    big, small = _font(max(14, size // 40)), _font(max(11, size // 60))
    header, footer = size // 40 + size // 60 + 24, size // 60 + 16
    print_style = spec.style == "print"
    background, ink = ((255, 255, 255), (0, 0, 0)) if print_style else ((0, 0, 0), (235, 235, 235))
    accent, faint = ((205, 25, 25), (40, 110, 200)) if print_style else ((255, 200, 0), (120, 190, 255))
    line = max(2, size // 450)

    chart = Image.new("RGB", (size, size + header + footer), background)
    chart.paste(_base_image(data, size, spec.orientation, spec.style), (0, header))
    draw = ImageDraw.Draw(chart)
    cv = _Canvas(size, header, spec.fov_deg, spec.orientation)
    arcmin_px = 1 / (cv.deg_per_px * 60)

    def text(xy: tuple[float, float], s: str, font: ImageFont.ImageFont, fill: tuple[int, int, int], anchor: str = "la") -> None:
        draw.text(xy, s, font=font, fill=fill, anchor=anchor, stroke_width=2, stroke_fill=background)

    # Telrad rings and other catalogued objects first, so the target and frame sit on top.
    if spec.telrad:
        cx, cy = cv.offset(0, 0)
        for r_arcmin in TELRAD_RADII_ARCMIN:
            r = r_arcmin * arcmin_px
            if r < size * 0.8:
                draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=faint, width=max(1, line - 1))
                if cy - r > header + 10 and r > size * 0.08:
                    text((cx + 4, cy - r - 2), f"Telrad {angle_label(2 * r_arcmin)}", small, faint, "lb")

    for obj in spec.objects:
        offset = project(obj.ra_deg, obj.dec_deg, spec.ra_deg, spec.dec_deg)
        if offset is None:
            continue
        x, y = cv.offset(*offset)
        if not cv.inside(x, y, 8) or math.hypot(x - size / 2, y - header - size / 2) < size * 0.03:
            continue
        r = max(size * 0.008, (obj.size_arcmin or 0) / 2 * arcmin_px)
        draw.ellipse((x - r, y - r, x + r, y + r), outline=faint, width=max(1, line - 1))
        text((x + r + 3, y), obj.name, small, faint, "lm")

    if spec.frame:
        f = spec.frame
        pa = math.radians(f.angle_deg)
        along, across = (math.sin(pa), math.cos(pa)), (math.cos(pa), -math.sin(pa))
        a, b = f.width_arcmin / 120, f.height_arcmin / 120  # half-sizes in degrees
        corners = [cv.offset(sa * a * along[0] + sb * b * across[0], sa * a * along[1] + sb * b * across[1])
                   for sa, sb in ((1, 1), (1, -1), (-1, -1), (-1, 1))]
        draw.polygon(corners, outline=accent, width=line)
        top = min(corners, key=lambda p: p[1])
        text((top[0], top[1] - 4), f.label, small, accent, "mb")

    if spec.eyepiece_arcmin:
        cx, cy = cv.offset(0, 0)
        r = spec.eyepiece_arcmin / 2 * arcmin_px
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=accent, width=line)
        if spec.eyepiece_label:
            text((cx, cy + r + 4), spec.eyepiece_label, small, accent, "ma")

    # Target reticle: four ticks with a gap, so the object itself stays visible.
    cx, cy = cv.offset(0, 0)
    inner, outer = size * 0.018, size * 0.05
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        draw.line((cx + dx * inner, cy + dy * inner, cx + dx * outer, cy + dy * outer), fill=accent, width=line)
    text((cx + outer * 0.6, cy + outer * 0.6), spec.target_label, big, accent, "lt")

    # Compass: N and E arrows, which turn and flip with the orientation.
    ox, oy = size * 0.88, header + size * 0.88
    length = size * 0.06
    for label, (e, n) in (("N", (0.0, 1e-3)), ("E", (1e-3, 0.0))):
        ux, uy = cv.direction(e, n)
        tip = (ox + ux * length, oy + uy * length)
        draw.line((ox, oy, *tip), fill=ink, width=line)
        for turn in (2.6, -2.6):  # arrowhead
            hx = ux * math.cos(turn) - uy * math.sin(turn)
            hy = ux * math.sin(turn) + uy * math.cos(turn)
            draw.line((*tip, tip[0] + hx * length * 0.25, tip[1] + hy * length * 0.25), fill=ink, width=line)
        text((tip[0] + ux * 12, tip[1] + uy * 12), label, big, ink, "mm")

    # Scale bar, bottom left: the round length nearest a fifth of the field.
    bar_arcmin = min(NICE_SCALES_ARCMIN, key=lambda s: abs(math.log(s / (spec.fov_deg * 60 / 5))))
    x0, y0 = size * 0.05, header + size * 0.95
    x1 = x0 + bar_arcmin * arcmin_px
    draw.line((x0, y0, x1, y0), fill=ink, width=line + 1)
    for x in (x0, x1):
        draw.line((x, y0 - 6, x, y0 + 6), fill=ink, width=line)
    text(((x0 + x1) / 2, y0 - 8), angle_label(bar_arcmin), small, ink, "mb")

    draw.text((10, 8), spec.title, font=big, fill=ink)
    draw.text((10, 12 + size // 40), spec.subtitle, font=small, fill=ink)
    draw.text((10, size + header + 6), f"{ORIENTATIONS[spec.orientation].split(':')[0]} · {spec.credit}", font=small, fill=ink)
    return chart
