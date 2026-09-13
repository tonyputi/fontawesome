"""Read the checked-in Font Awesome bitmap catalog.

The generator intentionally consumes the repository's existing bitmap headers
instead of rasterizing fonts. This keeps normal generation deterministic and
free of Inkscape, ImageMagick, FreeType, or network dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


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
        return sorted(assets, key=lambda asset: (asset.family, asset.name, asset.width, asset.height))
