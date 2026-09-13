"""Dependency-free uIcons catalog and generation tools."""

from .catalog import CATALOGS, Catalog, IconAsset, LucideCatalog, normalize_identifier, open_catalog
from .formats import FORMATS, analyze, convert, stride, summarize

__all__ = [
    "CATALOGS",
    "FORMATS",
    "Catalog",
    "IconAsset",
    "LucideCatalog",
    "analyze",
    "convert",
    "normalize_identifier",
    "open_catalog",
    "stride",
    "summarize",
]
