"""Dependency-free uIcons catalog and generation tools."""

from .catalog import CATALOGS, Catalog, IconAsset, LucideCatalog, normalize_identifier, open_catalog

__all__ = [
    "CATALOGS",
    "Catalog",
    "IconAsset",
    "LucideCatalog",
    "normalize_identifier",
    "open_catalog",
]
