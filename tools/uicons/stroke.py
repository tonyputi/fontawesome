"""Convert stroke-based SVGs to mono-vertical bitmaps.

Shared dependency-free pipeline used by every outline icon pack (Lucide,
Heroicons). It runs fully offline on the vendored SVGs using only the Python
standard library. Icons live on a 24x24 viewBox and are drawn as round-capped
strokes, so every shape is flattened to polylines and rasterized with fixed
supersampling. The output byte layout matches the Font Awesome catalog:
column-major pages with the top pixel in the least significant bit
(``uicons::PixelFormat::MonoVertical``).
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from typing import List, Sequence, Tuple

VIEWBOX = 24.0
DEFAULT_STROKE_WIDTH = 2.0
SUPERSAMPLE = 4
COVERAGE_THRESHOLD = 0.5
FLATNESS_TOLERANCE = 0.02
MAX_SUBDIVISION_DEPTH = 12
CIRCLE_SEGMENTS = 64
ARC_STEP_RADIANS = math.radians(5.0)

_SHAPE_TAGS = ("path", "circle", "rect", "line", "polyline", "polygon")
_METADATA_TAGS = ("title", "desc", "defs", "metadata")
_NUMBER_PATTERN = r"[-+]?(?:[0-9]*\.[0-9]+|[0-9]+\.?)(?:[eE][-+]?[0-9]+)?"
_TOKEN = re.compile(r"[AaCcHhLlMmQqSsTtVvZz]|" + _NUMBER_PATTERN)
_SEPARATOR = re.compile(r"[,\s]+")


def _local_name(tag: str) -> str:
    """Strip any XML namespace prefix so vendored SVGs parse identically."""

    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag.rsplit(":", 1)[-1]


def _parse_points(text: str) -> List[Tuple[float, float]]:
    numbers = [float(value) for value in re.findall(_NUMBER_PATTERN, text)]
    if len(numbers) % 2:
        raise ValueError(f"odd coordinate count in points {text!r}")
    return [(numbers[i], numbers[i + 1]) for i in range(0, len(numbers), 2)]


def _split_tokens(data: str) -> List[str]:
    return [token for token in _TOKEN.findall(data) if token.strip()]


def _flatten_cubic(p0, p1, p2, p3, depth=0) -> List[Tuple[float, float]]:
    flatness = abs((p0[0] + 3 * p1[0] - 3 * p2[0] - p3[0]) / 8) + abs(
        (p0[1] + 3 * p1[1] - 3 * p2[1] - p3[1]) / 8
    )
    if flatness <= FLATNESS_TOLERANCE or depth >= MAX_SUBDIVISION_DEPTH:
        return [p3]
    m01 = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    m12 = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    m23 = ((p2[0] + p3[0]) / 2, (p2[1] + p3[1]) / 2)
    m012 = ((m01[0] + m12[0]) / 2, (m01[1] + m12[1]) / 2)
    m123 = ((m12[0] + m23[0]) / 2, (m12[1] + m23[1]) / 2)
    mid = ((m012[0] + m123[0]) / 2, (m012[1] + m123[1]) / 2)
    return _flatten_cubic(p0, m01, m012, mid, depth + 1) + _flatten_cubic(
        mid, m123, m23, p3, depth + 1
    )


def _flatten_quadratic(p0, p1, p2) -> List[Tuple[float, float]]:
    cubic = (
        (p0[0] + 2 * p1[0]) / 3,
        (p0[1] + 2 * p1[1]) / 3,
        (p2[0] + 2 * p1[0]) / 3,
        (p2[1] + 2 * p1[1]) / 3,
    )
    return _flatten_cubic(p0, (cubic[0], cubic[1]), (cubic[2], cubic[3]), p2)


def _arc_center(current, rx, ry, rotation_deg, large_arc, sweep, target):
    """Return ``(center, rx, ry, start_angle, sweep_angle, phi)`` for an SVG arc."""
    phi = math.radians(rotation_deg % 360.0)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)
    dx = (current[0] - target[0]) / 2
    dy = (current[1] - target[1]) / 2
    x1p = cos_phi * dx + sin_phi * dy
    y1p = -sin_phi * dx + cos_phi * dy
    rx, ry = abs(rx), abs(ry)
    if rx < 1e-9 or ry < 1e-9:
        return current, 0.0, 0.0, 0.0
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1.0:
        scale = math.sqrt(lam)
        rx *= scale
        ry *= scale
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    factor = math.sqrt(max(0.0, num / den)) if den > 1e-12 else 0.0
    if large_arc == sweep:
        factor = -factor
    cxp = factor * rx * y1p / ry
    cyp = -factor * ry * x1p / rx
    center = (
        cos_phi * cxp - sin_phi * cyp + (current[0] + target[0]) / 2,
        sin_phi * cxp + cos_phi * cyp + (current[1] + target[1]) / 2,
    )

    def angle(ux, uy, vx, vy) -> float:
        dot = ux * vx + uy * vy
        norm = math.hypot(ux, uy) * math.hypot(vx, vy)
        cosine = max(-1.0, min(1.0, dot / norm)) if norm > 1e-12 else 1.0
        sign = 1.0 if ux * vy - uy * vx >= 0 else -1.0
        return sign * math.acos(cosine)

    start = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    sweep_angle = angle(
        (x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry
    )
    if not sweep and sweep_angle > 0:
        sweep_angle -= 2 * math.pi
    elif sweep and sweep_angle < 0:
        sweep_angle += 2 * math.pi
    return center, rx, ry, start, sweep_angle, phi


def _flatten_arc(
    current, rx, ry, rotation_deg, large_arc, sweep, target
) -> List[Tuple[float, float]]:
    center, rx, ry, start, sweep_angle, phi = _arc_center(
        current, rx, ry, rotation_deg, large_arc, sweep, target
    )
    if abs(sweep_angle) < 1e-9:
        return [target]
    steps = max(1, int(math.ceil(abs(sweep_angle) / ARC_STEP_RADIANS)))
    points = []
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)
    for step in range(1, steps + 1):
        theta = start + sweep_angle * step / steps
        x = rx * math.cos(theta)
        y = ry * math.sin(theta)
        points.append(
            (
                center[0] + cos_phi * x - sin_phi * y,
                center[1] + sin_phi * x + cos_phi * y,
            )
        )
    points[-1] = target
    return points


class _PathParser:
    def __init__(self, data: str):
        self.tokens = _split_tokens(data)
        self.position = 0
        self.current = (0.0, 0.0)
        self.subpath_start = (0.0, 0.0)
        self.previous = ""
        self.previous_cubic = (0.0, 0.0)
        self.previous_quadratic = (0.0, 0.0)
        self.polylines: List[Tuple[List[Tuple[float, float]], bool]] = []
        self.active: List[Tuple[float, float]] = []
        self.closed = False

    def _peek_command(self) -> bool:
        return (
            self.position < len(self.tokens)
            and len(self.tokens[self.position]) == 1
            and self.tokens[self.position].isalpha()
        )

    def _next_number(self) -> float:
        if self.position >= len(self.tokens) or self._peek_command():
            raise ValueError("unexpected end of path data")
        try:
            value = float(self.tokens[self.position])
        except ValueError as error:
            raise ValueError(f"invalid path number {self.tokens[self.position]!r}") from error
        self.position += 1
        return value

    def _flush(self) -> None:
        if len(self.active) > 1:
            self.polylines.append((list(self.active), self.closed))
        self.active = []
        self.closed = False

    def parse(self) -> List[Tuple[List[Tuple[float, float]], bool]]:
        command = ""
        while self.position < len(self.tokens):
            if self._peek_command():
                command = self.tokens[self.position]
                self.position += 1
                if command in "Zz":
                    if self.active:
                        self.active.append(self.subpath_start)
                        self.current = self.subpath_start
                        self.closed = True
                    self._flush()
                    self.previous = command
                    continue
            if not command:
                raise ValueError("path data must start with a command")
            self._run(command)
            if command in "Mm":
                command = "L" if command == "M" else "l"
        self._flush()
        return self.polylines

    def _point(self, relative: bool) -> Tuple[float, float]:
        x = self._next_number()
        y = self._next_number()
        if relative:
            return (self.current[0] + x, self.current[1] + y)
        return (x, y)

    def _line_to(self, point) -> None:
        if not self.active:
            self.active.append(self.current)
        self.active.append(point)
        self.current = point

    def _run(self, command: str) -> None:
        relative = command.islower()
        kind = command.upper()
        if kind == "M":
            point = self._point(relative)
            self._flush()
            self.current = point
            self.subpath_start = point
            self.active.append(point)
        elif kind == "L":
            self._line_to(self._point(relative))
        elif kind == "H":
            x = self._next_number()
            target = (self.current[0] + x if relative else x, self.current[1])
            self._line_to(target)
        elif kind == "V":
            y = self._next_number()
            target = (self.current[0], self.current[1] + y if relative else y)
            self._line_to(target)
        elif kind == "C":
            p1 = self._point(relative)
            p2 = self._point(relative)
            p3 = self._point(relative)
            if not self.active:
                self.active.append(self.current)
            self.active.extend(_flatten_cubic(self.current, p1, p2, p3))
            self.previous_cubic = p2
            self.current = p3
        elif kind == "S":
            p2 = self._point(relative)
            p3 = self._point(relative)
            if self.previous.upper() in ("C", "S"):
                p1 = (
                    2 * self.current[0] - self.previous_cubic[0],
                    2 * self.current[1] - self.previous_cubic[1],
                )
            else:
                p1 = self.current
            if not self.active:
                self.active.append(self.current)
            self.active.extend(_flatten_cubic(self.current, p1, p2, p3))
            self.previous_cubic = p2
            self.current = p3
        elif kind == "Q":
            p1 = self._point(relative)
            p2 = self._point(relative)
            if not self.active:
                self.active.append(self.current)
            self.active.extend(_flatten_quadratic(self.current, p1, p2))
            self.previous_quadratic = p1
            self.current = p2
        elif kind == "T":
            p2 = self._point(relative)
            if self.previous.upper() in ("Q", "T"):
                p1 = (
                    2 * self.current[0] - self.previous_quadratic[0],
                    2 * self.current[1] - self.previous_quadratic[1],
                )
            else:
                p1 = self.current
            if not self.active:
                self.active.append(self.current)
            self.active.extend(_flatten_quadratic(self.current, p1, p2))
            self.previous_quadratic = p1
            self.current = p2
        elif kind == "A":
            rx = self._next_number()
            ry = self._next_number()
            rotation = self._next_number()
            large_arc = self._flag()
            sweep = self._flag()
            target = self._point(relative)
            if not self.active:
                self.active.append(self.current)
            self.active.extend(
                _flatten_arc(self.current, rx, ry, rotation, large_arc, sweep, target)
            )
            self.current = target
        else:
            raise ValueError(f"unsupported path command {command!r}")
        self.previous = command

    def _flag(self) -> int:
        if self.position >= len(self.tokens):
            raise ValueError("unexpected end of path data in arc flags")
        token = self.tokens[self.position]
        if token in ("0", "1"):
            self.position += 1
            return int(token)
        # Flags may be packed against the next number (for example "1.528").
        match = re.match(r"([01])(\..*)", token)
        if match:
            self.tokens[self.position] = match.group(2)
            return int(match.group(1))
        raise ValueError(f"invalid arc flag {token!r}")


def _parse_path(data: str) -> List[Tuple[List[Tuple[float, float]], bool]]:
    return _PathParser(data).parse()


def _shapes_from_svg(text: str) -> Tuple[List[Tuple[List[Tuple[float, float]], bool]], float]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        raise ValueError(f"invalid SVG document: {error}") from error
    if _local_name(root.tag) != "svg":
        raise ValueError(f"expected an <svg> root, got <{_local_name(root.tag)}>")
    stroke_width = DEFAULT_STROKE_WIDTH
    if "stroke-width" in root.attrib:
        stroke_width = float(root.attrib["stroke-width"])
    polylines: List[Tuple[List[Tuple[float, float]], bool]] = []
    for element in root.iter():
        if element is root:
            continue
        kind = _local_name(element.tag)
        if kind in _METADATA_TAGS:
            continue
        if kind not in _SHAPE_TAGS:
            raise ValueError(
                f"unsupported SVG element <{kind}>: only {', '.join(_SHAPE_TAGS)} render"
            )
        transform = (element.get("transform") or "").strip()
        if transform:
            raise ValueError(
                f"<{kind}> uses transform={transform!r}, "
                "which the offline rasterizer does not support"
            )
        attrs = element.attrib
        if kind == "path":
            polylines.extend(_parse_path(attrs.get("d", "")))
        elif kind == "circle":
            cx = float(attrs.get("cx", "0"))
            cy = float(attrs.get("cy", "0"))
            radius = float(attrs.get("r", "0"))
            ring = [
                (cx + radius * math.cos(2 * math.pi * i / CIRCLE_SEGMENTS),
                 cy + radius * math.sin(2 * math.pi * i / CIRCLE_SEGMENTS))
                for i in range(CIRCLE_SEGMENTS)
            ]
            ring.append(ring[0])
            polylines.append((ring, True))
        elif kind == "rect":
            x, y = float(attrs.get("x", "0")), float(attrs.get("y", "0"))
            width, height = float(attrs.get("width", "0")), float(attrs.get("height", "0"))
            radius = float(attrs.get("rx", attrs.get("ry", "0") or "0") or "0")
            corner = min(radius, width / 2, height / 2)
            polylines.append((_rounded_rect(x, y, width, height, corner), True))
        elif kind == "line":
            polylines.append(
                (
                    [
                        (float(attrs.get("x1", "0")), float(attrs.get("y1", "0"))),
                        (float(attrs.get("x2", "0")), float(attrs.get("y2", "0"))),
                    ],
                    False,
                )
            )
        elif kind in ("polyline", "polygon"):
            points = _parse_points(attrs.get("points", ""))
            if len(points) > 1:
                if kind == "polygon":
                    points.append(points[0])
                polylines.append((points, kind == "polygon"))
    return polylines, stroke_width


def _rounded_rect(x, y, width, height, radius) -> List[Tuple[float, float]]:
    if radius <= 0:
        return [(x, y), (x + width, y), (x + width, y + height), (x, y + height), (x, y)]
    corners = [
        ((x + width - radius, y + radius), math.radians(270), math.radians(360)),
        ((x + width - radius, y + height - radius), math.radians(0), math.radians(90)),
        ((x + radius, y + height - radius), math.radians(90), math.radians(180)),
        ((x + radius, y + radius), math.radians(180), math.radians(270)),
    ]
    outline = [(x + radius, y)]
    for (cx, cy), start, end in corners:
        steps = max(2, int(math.ceil((end - start) / ARC_STEP_RADIANS)))
        for step in range(steps + 1):
            theta = start + (end - start) * step / steps
            outline.append((cx + radius * math.cos(theta), cy + radius * math.sin(theta)))
    outline.append(outline[0])
    return outline


def _distance_to_segment(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    length_squared = dx * dx + dy * dy
    if length_squared < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_squared))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def rasterize_svg(text: str, size: int) -> Tuple[int, ...]:
    """Rasterize one stroke SVG to mono-vertical bytes at ``size`` pixels."""

    if size <= 0:
        raise ValueError(f"size must be positive, got {size}")
    polylines, stroke_width = _shapes_from_svg(text)
    scale = size / VIEWBOX
    stroke_px = max(1.0, stroke_width * scale)
    grid = size * SUPERSAMPLE
    radius = stroke_px * SUPERSAMPLE / 2.0
    cells = [[0] * grid for _ in range(grid)]

    segments = []
    for points, _ in polylines:
        for index in range(len(points) - 1):
            ax = points[index][0] * scale * SUPERSAMPLE
            ay = points[index][1] * scale * SUPERSAMPLE
            bx = points[index + 1][0] * scale * SUPERSAMPLE
            by = points[index + 1][1] * scale * SUPERSAMPLE
            segments.append((ax, ay, bx, by))
        for vx, vy in points:
            segments.append((vx * scale * SUPERSAMPLE, vy * scale * SUPERSAMPLE,
                             vx * scale * SUPERSAMPLE, vy * scale * SUPERSAMPLE))

    for ax, ay, bx, by in segments:
        min_x = max(0, int(math.floor(min(ax, bx) - radius)))
        max_x = min(grid - 1, int(math.ceil(max(ax, bx) + radius)))
        min_y = max(0, int(math.floor(min(ay, by) - radius)))
        max_y = min(grid - 1, int(math.ceil(max(ay, by) + radius)))
        for gy in range(min_y, max_y + 1):
            for gx in range(min_x, max_x + 1):
                if cells[gy][gx]:
                    continue
                if _distance_to_segment(gx + 0.5, gy + 0.5, ax, ay, bx, by) <= radius:
                    cells[gy][gx] = 1

    pixels = [[0] * size for _ in range(size)]
    needed = SUPERSAMPLE * SUPERSAMPLE * COVERAGE_THRESHOLD
    for y in range(size):
        for x in range(size):
            total = sum(
                cells[y * SUPERSAMPLE + dy][x * SUPERSAMPLE + dx]
                for dy in range(SUPERSAMPLE)
                for dx in range(SUPERSAMPLE)
            )
            pixels[y][x] = 1 if total >= needed else 0

    data = []
    for x in range(size):
        for page in range((size + 7) // 8):
            byte = 0
            for bit in range(8):
                y = page * 8 + bit
                if y < size and pixels[y][x]:
                    byte |= 1 << bit
            data.append(byte)
    return tuple(data)


def pixel_density(data: Sequence[int]) -> float:
    """Return the fraction of set bits in mono-vertical ``data``."""

    if not data:
        return 0.0
    lit = sum(bin(byte).count("1") for byte in data)
    return lit / (len(data) * 8)
