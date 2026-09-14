"""Read the checked-in Font Awesome bitmap catalog.

The generator intentionally consumes the repository's existing bitmap headers
instead of rasterizing fonts. This keeps normal generation deterministic and
free of Inkscape, ImageMagick, FreeType, or network dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .heroicons import ALIASES as _HEROICONS_ALIASES
from .heroicons import SIZES as _HEROICONS_SIZES
from .heroicons import SOURCE_URL as _HEROICONS_SOURCE_URL
from .heroicons import read_pack_metadata as _heroicons_pack_metadata
from .lucide import ALIASES as _LUCIDE_ALIASES
from .lucide import SIZES as _LUCIDE_SIZES
from .lucide import read_pack_metadata as _lucide_pack_metadata
from .stroke import pixel_density as _stroke_density
from .stroke import rasterize_svg as _rasterize_svg



_HEADER_NAME = re.compile(r"^(?P<family>fas|far|fab)_(?P<size>[0-9]+)x(?P=size)\.h$")
_ICON = re.compile(
    r"// '(?P<name>[^']+)', (?P<width>[0-9]+)x(?P<height>[0-9]+)px\s*"
    r"const unsigned char (?P<symbol>[A-Za-z0-9_]+)\s*\[\] PROGMEM = \{"
    r"(?P<data>.*?)\n\};",
    re.DOTALL,
)
_BYTE = re.compile(r"0[xX][0-9a-fA-F]+|[0-9]+")

_FAMILY_ALIASES = {
    "fas": "fas",
    "solid": "fas",
    "far": "far",
    "regular": "far",
    "fab": "fab",
    "brands": "fab",
}


@dataclass(frozen=True)
class IconAsset:
    """One bitmap extracted from a checked-in catalog header."""

    family: str
    name: str
    width: int
    height: int
    data: Tuple[int, ...]
    source_symbol: str

    @property
    def stride(self) -> int:
        """Return the byte stride for the vertical page format."""

        return self.width


def normalize_identifier(identifier: str) -> str:
    """Return the canonical ``family/name`` form for an icon identifier."""

    parts = identifier.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"invalid icon {identifier!r}; use FAMILY/NAME, for example fas/heart")
    family = _FAMILY_ALIASES.get(parts[0].lower())
    if family is None:
        valid = ", ".join(sorted(_FAMILY_ALIASES))
        raise ValueError(f"unsupported family {parts[0]!r}; choose one of: {valid}")
    return f"{family}/{parts[1]}"


CATALOGS = ("fontawesome", "lucide", "heroicons")

_DEFAULT_DIRECTORIES = {
    "fontawesome": Path("src/vertical"),
    "lucide": Path("assets/lucide/icons"),
    "heroicons": Path("assets/heroicons/icons"),
}


def default_directory(catalog: str) -> Path:
    """Return the repository-relative catalog directory for ``catalog``."""

    try:
        return _DEFAULT_DIRECTORIES[catalog]
    except KeyError as error:
        raise ValueError(
            f"unsupported catalog {catalog!r}; choose one of: {', '.join(CATALOGS)}"
        ) from error


class Catalog:
    """Index Font Awesome's generated vertical bitmap headers."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self._assets: Dict[Tuple[str, int, str], IconAsset] = {}
        self._sizes: Dict[str, List[int]] = {}
        self._load()

    def _load(self) -> None:
        headers = sorted(self.directory.glob("*.h"), key=lambda path: path.name)
        for header in headers:
            match = _HEADER_NAME.match(header.name)
            if match is None:
                continue
            family = match.group("family")
            size = int(match.group("size"))
            self._sizes.setdefault(family, []).append(size)
            text = header.read_text(encoding="utf-8")
            for icon_match in _ICON.finditer(text):
                width = int(icon_match.group("width"))
                height = int(icon_match.group("height"))
                values = tuple(int(value, 0) for value in _BYTE.findall(icon_match.group("data")))
                expected = width * ((height + 7) // 8)
                if len(values) != expected:
                    raise ValueError(
                        f"{header}: {icon_match.group('name')!r} contains {len(values)} bytes; "
                        f"expected {expected} for {width}x{height} vertical data"
                    )
                key = (family, size, icon_match.group("name"))
                self._assets[key] = IconAsset(
                    family=family,
                    name=icon_match.group("name"),
                    width=width,
                    height=height,
                    data=values,
                    source_symbol=icon_match.group("symbol"),
                )
        for family in self._sizes:
            self._sizes[family] = sorted(set(self._sizes[family]))

    @property
    def sizes(self) -> Dict[str, List[int]]:
        """Return available sizes grouped by Font Awesome family."""

        return {family: list(sizes) for family, sizes in self._sizes.items()}

    normalize_identifier = staticmethod(normalize_identifier)

    def resolve(self, identifier: str, size: int) -> IconAsset:
        """Resolve ``family/name`` using family aliases and a requested size."""

        canonical = self.normalize_identifier(identifier)
        family, name = canonical.split("/", 1)
        key = (family, size, name)
        try:
            return self._assets[key]
        except KeyError as error:
            available = self._sizes.get(family, [])
            if not available:
                raise ValueError(f"family {family!r} is not available in this catalog") from error
            raise ValueError(
                f"icon {canonical!r} is unavailable at {size}x{size}; "
                f"available sizes for {family}: {', '.join(map(str, available))}"
            ) from error

    def resolve_many(self, identifiers: Iterable[str], sizes: Iterable[int]) -> List[IconAsset]:
        """Resolve and return assets in deterministic family/name/size order."""

        assets = [self.resolve(identifier, size) for identifier in identifiers for size in sizes]
        return sorted(assets, key=_asset_order)

    @property
    def available_sizes(self) -> List[int]:
        """Return every raster size offered by this catalog, sorted."""

        sizes = {size for family_sizes in self._sizes.values() for size in family_sizes}
        return sorted(sizes)

    @property
    def provenance(self) -> str:
        """Return a one-line source description for generated headers."""

        return "Font Awesome checked-in bitmap catalog (see src/vertical/README.md)"


class LucideCatalog:
    """Rasterize the pinned Lucide SVG pack to mono-vertical bitmaps."""

    name = "lucide"

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        svgs = sorted(self.directory.glob("*.svg"), key=lambda path: path.name)
        if not svgs:
            raise ValueError(f"no Lucide SVGs found in {self.directory}")
        self._sources: Dict[str, str] = {}
        for svg in svgs:
            self._sources[svg.stem] = svg.read_text(encoding="utf-8")
        self._version, self._license = _lucide_pack_metadata(self.directory)

    @staticmethod
    def normalize_identifier(identifier: str) -> str:
        """Return the canonical ``lucide/name`` form for an icon identifier."""

        parts = identifier.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"invalid icon {identifier!r}; use lucide/NAME, for example lucide/heart"
            )
        if parts[0].lower() != "lucide":
            raise ValueError(
                f"unsupported family {parts[0]!r} for the Lucide catalog; use 'lucide'"
            )
        return f"lucide/{_LUCIDE_ALIASES.get(parts[1], parts[1])}"

    @property
    def available_sizes(self) -> List[int]:
        """Return every raster size offered by this catalog, sorted."""

        return list(_LUCIDE_SIZES)

    @property
    def provenance(self) -> str:
        """Return a one-line source description for generated headers."""

        return f"Lucide {self._version} ({self._license}, https://github.com/lucide-icons/lucide)"

    def available_icons(self) -> List[str]:
        """Return canonical ``lucide/name`` identifiers, sorted."""

        return sorted(f"lucide/{name}" for name in self._sources)

    def resolve(self, identifier: str, size: int) -> IconAsset:
        """Resolve ``lucide/name`` by rasterizing the vendored SVG at ``size``."""

        canonical = self.normalize_identifier(identifier)
        _, name = canonical.split("/", 1)
        if size not in _LUCIDE_SIZES:
            raise ValueError(
                f"icon {canonical!r} is unavailable at {size}x{size}; "
                f"available Lucide sizes: {', '.join(map(str, _LUCIDE_SIZES))}"
            )
        try:
            source = self._sources[name]
        except KeyError as error:
            raise ValueError(
                f"icon {canonical!r} is not in the vendored Lucide subset; "
                f"available icons: {', '.join(self.available_icons())}"
            ) from error
        data = _rasterize_svg(source, size)
        if _stroke_density(data) == 0.0:
            raise ValueError(f"icon {canonical!r} rasterized empty at {size}x{size}")
        return IconAsset(
            family="lucide",
            name=name,
            width=size,
            height=size,
            data=data,
            source_symbol=f"lucide_{name}.svg",
        )

    def resolve_many(self, identifiers: Iterable[str], sizes: Iterable[int]) -> List[IconAsset]:
        """Resolve and return assets in deterministic family/name/size order."""

        assets = [self.resolve(identifier, size) for identifier in identifiers for size in sizes]
        return sorted(assets, key=_asset_order)


class HeroiconsCatalog:
    """Rasterize the pinned Heroicons outline SVG pack to mono-vertical bitmaps."""

    name = "heroicons"

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        svgs = sorted(self.directory.glob("*.svg"), key=lambda path: path.name)
        if not svgs:
            raise ValueError(f"no Heroicons SVGs found in {self.directory}")
        self._sources: Dict[str, str] = {}
        for svg in svgs:
            self._sources[svg.stem] = svg.read_text(encoding="utf-8")
        self._version, self._license = _heroicons_pack_metadata(self.directory)

    @staticmethod
    def normalize_identifier(identifier: str) -> str:
        """Return the canonical ``heroicons/name`` form for an icon identifier."""

        parts = identifier.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"invalid icon {identifier!r}; use heroicons/NAME, for example heroicons/heart"
            )
        if parts[0].lower() != "heroicons":
            raise ValueError(
                f"unsupported family {parts[0]!r} for the Heroicons catalog; use 'heroicons'"
            )
        return f"heroicons/{_HEROICONS_ALIASES.get(parts[1], parts[1])}"

    @property
    def available_sizes(self) -> List[int]:
        """Return every raster size offered by this catalog, sorted."""

        return list(_HEROICONS_SIZES)

    @property
    def provenance(self) -> str:
        """Return a one-line source description for generated headers."""

        return f"Heroicons {self._version} ({self._license}, {_HEROICONS_SOURCE_URL})"

    def available_icons(self) -> List[str]:
        """Return canonical ``heroicons/name`` identifiers, sorted."""

        return sorted(f"heroicons/{name}" for name in self._sources)

    def resolve(self, identifier: str, size: int) -> IconAsset:
        """Resolve ``heroicons/name`` by rasterizing the vendored SVG at ``size``."""

        canonical = self.normalize_identifier(identifier)
        _, name = canonical.split("/", 1)
        if size not in _HEROICONS_SIZES:
            raise ValueError(
                f"icon {canonical!r} is unavailable at {size}x{size}; "
                f"available Heroicons sizes: {', '.join(map(str, _HEROICONS_SIZES))}"
            )
        try:
            source = self._sources[name]
        except KeyError as error:
            raise ValueError(
                f"icon {canonical!r} is not in the vendored Heroicons subset; "
                f"available icons: {', '.join(self.available_icons())}"
            ) from error
        data = _rasterize_svg(source, size)
        if _stroke_density(data) == 0.0:
            raise ValueError(f"icon {canonical!r} rasterized empty at {size}x{size}")
        return IconAsset(
            family="heroicons",
            name=name,
            width=size,
            height=size,
            data=data,
            source_symbol=f"heroicons_{name}.svg",
        )

    def resolve_many(self, identifiers: Iterable[str], sizes: Iterable[int]) -> List[IconAsset]:
        """Resolve and return assets in deterministic family/name/size order."""

        assets = [self.resolve(identifier, size) for identifier in identifiers for size in sizes]
        return sorted(assets, key=_asset_order)


def _asset_order(asset: IconAsset) -> Tuple[str, str, int, int]:
    return (asset.family, asset.name, asset.width, asset.height)


def open_catalog(name: str, directory: Optional[Path] = None):
    """Open a catalog by name, defaulting to its directory."""

    if name == "fontawesome":
        return Catalog(default_directory(name) if directory is None else directory)
    if name == "lucide":
        return LucideCatalog(default_directory(name) if directory is None else directory)
    if name == "heroicons":
        return HeroiconsCatalog(default_directory(name) if directory is None else directory)
    raise ValueError(f"unsupported catalog {name!r}; choose one of: {', '.join(CATALOGS)}")
