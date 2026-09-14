"""Pinned Heroicons outline pack metadata.

Heroicons outlines are stroke-based SVGs on a 24x24 grid, so they reuse the
shared dependency-free stroke pipeline in ``stroke.py`` verbatim. This module
only carries the pack-specific metadata (sizes, aliases, source, license);
solid icons are intentionally out of scope because they are fill-based and
the converter paints strokes only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from .stroke import pixel_density, rasterize_svg

SIZES = (16, 24)
SOURCE_URL = "https://github.com/tailwindlabs/heroicons"
LICENSE_NAME = "MIT"

ALIASES: dict = {}


def read_pack_metadata(icons_dir: Path) -> Tuple[str, str]:
    """Return the pinned (version, license) pair for the Heroicons pack."""

    pack_dir = Path(icons_dir).parent
    version = (pack_dir / "VERSION").read_text(encoding="utf-8").strip()
    return version, LICENSE_NAME


__all__ = [
    "ALIASES",
    "LICENSE_NAME",
    "SIZES",
    "SOURCE_URL",
    "pixel_density",
    "rasterize_svg",
    "read_pack_metadata",
]
