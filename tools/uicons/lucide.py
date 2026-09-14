"""Pinned Lucide outline pack metadata.

Lucide outlines are stroke-based SVGs on a 24x24 grid, so they reuse the
shared dependency-free stroke pipeline in ``stroke.py`` verbatim. This module
only carries the pack-specific metadata (sizes, aliases, source, license).
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from .stroke import pixel_density, rasterize_svg

SIZES = (16, 24)
SOURCE_URL = "https://github.com/lucide-icons/lucide"
LICENSE_NAME = "ISC"

ALIASES = {
    "home": "house",
}


def read_pack_metadata(icons_dir: Path) -> Tuple[str, str]:
    """Return the pinned (version, license) pair for the Lucide pack."""

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
