"""Bitmap format conversion and footprint analysis for uIcons assets.

The catalog layer always stores 1-bpp mono-vertical pixels (column-major
pages, top pixel in the least significant bit). This module converts that
canonical layout to the other formats the renderer understands and measures
what each choice costs in flash. Everything here uses only the Python standard
library so generation stays offline and deterministic.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

FORMATS = ("mono-vertical", "mono-rowmajor")

PIXEL_FORMAT_ENUM = {
    "mono-vertical": "PixelFormat::MonoVertical",
    "mono-rowmajor": "PixelFormat::MonoRowMajor",
}


def convert(data: Sequence[int], width: int, height: int, output_format: str) -> Tuple[int, ...]:
    """Convert canonical mono-vertical ``data`` to ``output_format``."""

    if output_format == "mono-vertical":
        return tuple(data)
    if output_format == "mono-rowmajor":
        return to_row_major(data, width, height)
    raise ValueError(
        f"unsupported format {output_format!r}; choose one of: {', '.join(FORMATS)}"
    )


def stride(width: int, output_format: str) -> int:
    """Return the row/page stride for ``width`` in ``output_format``."""

    if output_format == "mono-vertical":
        return width
    if output_format == "mono-rowmajor":
        return (width + 7) // 8
    raise ValueError(
        f"unsupported format {output_format!r}; choose one of: {', '.join(FORMATS)}"
    )


def to_row_major(data: Sequence[int], width: int, height: int) -> Tuple[int, ...]:
    """Transpose mono-vertical bytes to MSB-first row-major bytes.

    The bit order matches ``uicons::PixelFormat::MonoRowMajor``: the leftmost
    pixel of each byte is the most significant bit.
    """

    row_stride = (width + 7) // 8
    output = [0] * (row_stride * height)
    for y in range(height):
        for x in range(width):
            vertical_index = (y // 8) * width + x
            if data[vertical_index] & (1 << (y % 8)):
                output[y * row_stride + x // 8] |= 0x80 >> (x % 8)
    return tuple(output)


def to_vertical(data: Sequence[int], width: int, height: int) -> Tuple[int, ...]:
    """Transpose MSB-first row-major bytes back to mono-vertical bytes."""

    row_stride = (width + 7) // 8
    output = [0] * (width * ((height + 7) // 8))
    for y in range(height):
        for x in range(width):
            if data[y * row_stride + x // 8] & (0x80 >> (x % 8)):
                output[(y // 8) * width + x] |= 1 << (y % 8)
    return tuple(output)


def decode_vertical(data: Sequence[int], width: int, height: int) -> List[List[int]]:
    """Decode mono-vertical bytes to a row-major 0/1 pixel grid."""

    return [
        [1 if data[(y // 8) * width + x] & (1 << (y % 8)) else 0 for x in range(width)]
        for y in range(height)
    ]


def bounding_box(pixels: Sequence[Sequence[int]]) -> Optional[Tuple[int, int, int, int]]:
    """Return the ``(x0, y0, x1, y1)`` box of lit pixels, or ``None`` when empty."""

    lit = [(x, y) for y, row in enumerate(pixels) for x, value in enumerate(row) if value]
    if not lit:
        return None
    xs = [point[0] for point in lit]
    ys = [point[1] for point in lit]
    return (min(xs), min(ys), max(xs), max(ys))


def cropped_bytes(box: Optional[Tuple[int, int, int, int]]) -> int:
    """Return the mono-vertical byte count for the cropped ``box`` region."""

    if box is None:
        return 0
    width = box[2] - box[0] + 1
    height = box[3] - box[1] + 1
    return width * ((height + 7) // 8)


def rle_bytes(data: Sequence[int]) -> int:
    """Return the size of a byte-run encoding of ``data``.

    The candidate encoding stores each run as a ``(count, value)`` pair with a
    one-byte count (1-255). It is reported for comparison only; generated
    headers stay uncompressed so the renderer needs no decoder.
    """

    if not data:
        return 0
    runs = 1
    run_length = 1
    for previous, current in zip(data, data[1:]):
        if current == previous and run_length < 255:
            run_length += 1
        else:
            runs += 1
            run_length = 1
    return runs * 2


def analyze(
    family: str,
    name: str,
    width: int,
    height: int,
    data: Sequence[int],
    output_format: str,
) -> Dict[str, object]:
    """Analyze one asset and return a deterministic footprint row."""

    packed = convert(data, width, height, output_format)
    pixels = decode_vertical(data, width, height)
    lit = sum(sum(row) for row in pixels)
    box = bounding_box(pixels)
    cropped = cropped_bytes(box)
    return {
        "icon": f"{family}/{name}",
        "size": f"{width}x{height}",
        "format": output_format,
        "bytes": len(packed),
        "pixels": width * height,
        "lit": lit,
        "density": round(lit / (width * height), 4) if width * height else 0.0,
        "bbox": list(box) if box is not None else None,
        "cropped_bytes": cropped,
        "rle_bytes": rle_bytes(packed),
    }


def summarize(rows: Sequence[Dict[str, object]], header_bytes: int = 0) -> Dict[str, object]:
    """Aggregate per-icon ``rows`` into deterministic pack totals."""

    total_bytes = sum(int(row["bytes"]) for row in rows)
    total_cropped = sum(int(row["cropped_bytes"]) for row in rows)
    total_rle = sum(int(row["rle_bytes"]) for row in rows)
    return {
        "icons": len(rows),
        "data_bytes": total_bytes,
        "cropped_bytes": total_cropped,
        "rle_bytes": total_rle,
        "header_bytes": header_bytes,
    }
