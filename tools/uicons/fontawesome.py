"""Pinned Font Awesome bitmap pack metadata.

Font Awesome is the bitmap-backed pack: icons ship as pre-rasterized
mono-vertical headers under ``src/vertical/`` (frozen blobs that also serve
``<fontawesome.h>``), so there is nothing to rasterize and this module only
carries the pack-specific metadata (families, aliases, source, license) while
``catalog.Catalog`` parses the headers.

The vendored ``assets/svgs/`` sources stay out of the pipeline on purpose:
they are fill-based shapes on non-square viewBoxes, which the shared
stroke-only SVG rasterizer cannot paint. Promoting them to inputs needs fill
support and is tracked separately; sizes therefore stay dynamic (read from
the headers) and there is no ``VERSION`` pin nor ``read_pack_metadata`` here.
"""

from __future__ import annotations

SOURCE_URL = "https://github.com/FortAwesome/Font-Awesome"
LICENSE_NAME = "CC BY 4.0"

FAMILIES = ("fas", "far", "fab")

FAMILY_ALIASES = {
    "fas": "fas",
    "solid": "fas",
    "far": "far",
    "regular": "far",
    "fab": "fab",
    "brands": "fab",
}

__all__ = [
    "FAMILIES",
    "FAMILY_ALIASES",
    "LICENSE_NAME",
    "SOURCE_URL",
]
