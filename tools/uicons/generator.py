"""Deterministic C++ header generation for selected uIcons assets."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .catalog import CATALOGS, IconAsset, open_catalog
from .formats import FORMATS, PIXEL_FORMAT_ENUM, analyze, convert, stride, summarize


_IDENTIFIER = re.compile(r"[^A-Za-z0-9_]")


def read_manifest(path: Path) -> Dict[str, Any]:
    """Read and validate a JSON project manifest."""

    try:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(manifest, dict):
        raise ValueError(f"manifest {path} must contain a JSON object")
    return manifest


def validate_animations(value: Any) -> List[Dict[str, Any]]:
    """Return normalized animations sorted by name; frames keep manifest order."""

    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("manifest 'animations' must be a JSON array")
    animations = []
    for entry in value:
        if not isinstance(entry, dict):
            raise ValueError("each manifest animation must be a JSON object")
        name = entry.get("name", "")
        if not isinstance(name, str) or not name:
            raise ValueError("each manifest animation needs a non-empty 'name'")
        loop = entry.get("loop", 0)
        if not isinstance(loop, int) or loop < 0 or loop > 65535:
            raise ValueError(f"animation {name!r} needs a 'loop' count from 0 to 65535")
        frames = entry.get("frames", [])
        if not isinstance(frames, list) or not frames:
            raise ValueError(f"animation {name!r} needs a non-empty 'frames' array")
        if len(frames) > 65535:
            raise ValueError(f"animation {name!r} holds too many frames (maximum 65535)")
        normalized_frames = []
        for position, frame in enumerate(frames):
            if not isinstance(frame, dict):
                raise ValueError(f"animation {name!r} frame {position} must be a JSON object")
            icon = frame.get("icon", "")
            size = frame.get("size", 0)
            duration = frame.get("duration_ms", 0)
            if not isinstance(icon, str) or not icon:
                raise ValueError(f"animation {name!r} frame {position} needs a non-empty 'icon'")
            if not isinstance(size, int) or size <= 0:
                raise ValueError(f"animation {name!r} frame {position} needs a positive 'size'")
            if not isinstance(duration, int) or duration <= 0:
                raise ValueError(
                    f"animation {name!r} frame {position} needs a positive 'duration_ms'"
                )
            normalized_frames.append({"icon": icon, "size": size, "duration_ms": duration})
        animations.append({"name": name, "loop": loop, "frames": normalized_frames})
    names = [animation["name"] for animation in animations]
    if len(set(names)) != len(names):
        raise ValueError("manifest animation names must be unique")
    return sorted(animations, key=lambda animation: animation["name"])


def validate_manifest(manifest: Dict[str, Any]) -> tuple:
    """Return normalized catalog, sizes, format, icon identifiers, and animations."""

    catalog_name = manifest.get("catalog", "fontawesome")
    if catalog_name not in CATALOGS:
        raise ValueError(
            "unsupported catalog {!r}; choose one of: {}".format(catalog_name, ", ".join(CATALOGS))
        )

    sizes = manifest.get("sizes", [16])
    if not isinstance(sizes, list) or not sizes or not all(isinstance(size, int) for size in sizes):
        raise ValueError("manifest 'sizes' must be a non-empty JSON array of integers")
    normalized_sizes = tuple(sorted(set(sizes)))
    if any(size <= 0 for size in normalized_sizes):
        raise ValueError("manifest 'sizes' must contain positive integers")

    output_format = manifest.get("format", "mono-vertical")
    if output_format not in FORMATS:
        raise ValueError(
            "unsupported format {!r}; choose one of: {}".format(output_format, ", ".join(FORMATS))
        )

    icons = manifest.get("icons", [])
    if not isinstance(icons, list) or not all(isinstance(icon, str) and icon for icon in icons):
        raise ValueError("manifest 'icons' must be a JSON array of non-empty strings")
    normalized_icons = tuple(sorted(set(icons)))
    animations = validate_animations(manifest.get("animations"))
    return catalog_name, normalized_sizes, output_format, normalized_icons, animations


def _symbol(asset: IconAsset) -> str:
    name = _IDENTIFIER.sub("_", asset.name).strip("_") or "icon"
    if name[0].isdigit():
        name = "icon_" + name
    return f"{asset.family}_{name}_{asset.width}x{asset.height}"


def _format_bytes(values: Sequence[int]) -> str:
    lines: List[str] = []
    for start in range(0, len(values), 12):
        chunk = values[start : start + 12]
        lines.append("    " + ", ".join(f"0x{value:02x}" for value in chunk) + ",")
    return "\n".join(lines)


def _animation_symbol(name: str) -> str:
    symbol = _IDENTIFIER.sub("_", name).strip("_") or "animation"
    if symbol[0].isdigit():
        symbol = "animation_" + symbol
    return f"anim_{symbol}"


def _resolve_animations(
    animations: Sequence[Dict[str, Any]],
    catalog,
    identifiers: Sequence[str],
    sizes: Sequence[int],
    symbols: Dict[tuple, str],
) -> List[Dict[str, Any]]:
    """Bind animation frames to selected icons, failing with actionable errors."""

    resolved = []
    for animation in animations:
        frames = []
        for position, frame in enumerate(animation["frames"]):
            canonical = catalog.normalize_identifier(frame["icon"])
            if canonical not in identifiers:
                raise ValueError(
                    "animation {!r} frame {} references {!r}, which is not in "
                    "manifest 'icons'; add it before building".format(
                        animation["name"], position, canonical
                    )
                )
            if frame["size"] not in sizes:
                raise ValueError(
                    "animation {!r} frame {} uses size {}, which is not in manifest "
                    "'sizes'; add it before building".format(
                        animation["name"], position, frame["size"]
                    )
                )
            family, name = canonical.split("/", 1)
            key = (family, name, frame["size"], frame["size"])
            frames.append({"symbol": symbols[key], "duration_ms": frame["duration_ms"]})
        resolved.append(
            {
                "symbol": _animation_symbol(animation["name"]),
                "loop": animation["loop"],
                "frames": frames,
            }
        )
    return resolved


def render_header(
    assets: Sequence[IconAsset],
    manifest: Dict[str, Any],
    provenance: str = "",
    output_format: str = "mono-vertical",
    animations: Sequence[Dict[str, Any]] = (),
) -> str:
    """Render a stable C++11 header for the selected assets."""

    lines = [
        "#ifndef UICONS_GENERATED_H",
        "#define UICONS_GENERATED_H",
        "",
        "#include <uicons.h>",
        "",
        "// Generated by uicons. Do not edit; run the generator instead.",
    ]
    if provenance:
        lines.append(f"// Source: {provenance}.")
    lines.extend(
        [
            "",
            "namespace uicons {",
            "namespace generated {",
            "",
        ]
    )
    for asset in assets:
        symbol = _symbol(asset)
        packed = convert(asset.data, asset.width, asset.height, output_format)
        lines.extend(
            [
                f"static const uint8_t {symbol}_data[] UICONS_PROGMEM = {{",
                _format_bytes(packed),
                "};",
                f"static const Icon {symbol}({symbol}_data, {asset.width}, {asset.height},",
                f"                          {stride(asset.width, output_format)},"
                f" sizeof({symbol}_data),",
                f"                          {PIXEL_FORMAT_ENUM[output_format]});",
                "",
            ]
        )
    for animation in animations:
        symbol = animation["symbol"]
        frame_lines = ",\n".join(
            f"    {{&{frame['symbol']}, {frame['duration_ms']}}}" for frame in animation["frames"]
        )
        lines.extend(
            [
                f"static const AnimationFrame {symbol}_frames[] = {{",
                frame_lines,
                "};",
                f"static const Animation {symbol}({symbol}_frames, {len(animation['frames'])},",
                f"                             {animation['loop']});",
                "",
            ]
        )
    lines.extend(["} // namespace generated", "} // namespace uicons", "", "#endif", ""])
    return "\n".join(lines)


def build(manifest_path: Path, catalog_dir: Path, output_dir: Path) -> Path:
    """Build the selected manifest into one deterministic generated header."""

    manifest = read_manifest(manifest_path)
    _, sizes, output_format, identifiers, animations = validate_manifest(manifest)
    catalog_name = manifest.get("catalog", "fontawesome")
    catalog = open_catalog(catalog_name, catalog_dir)
    unsupported = sorted(set(sizes) - set(catalog.available_sizes))
    if unsupported:
        raise ValueError(
            "sizes {} are unavailable in the {!r} catalog; available sizes: {}".format(
                ", ".join(map(str, unsupported)),
                catalog_name,
                ", ".join(map(str, catalog.available_sizes)),
            )
        )
    canonical_identifiers = tuple(
        sorted({catalog.normalize_identifier(icon) for icon in identifiers})
    )
    assets = catalog.resolve_many(canonical_identifiers, sizes)
    symbols = {
        (asset.family, asset.name, asset.width, asset.height): _symbol(asset) for asset in assets
    }
    resolved = _resolve_animations(
        animations, catalog, canonical_identifiers, sizes, symbols
    )
    header = render_header(assets, manifest, catalog.provenance, output_format, resolved)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "uicons_generated.h"
    temporary_path = output_path.with_suffix(".tmp")
    temporary_path.write_text(header, encoding="utf-8", newline="\n")
    temporary_path.replace(output_path)
    return output_path


def report(manifest_path: Path, catalog_dir: Path) -> Dict[str, Any]:
    """Analyze the selected manifest and return deterministic footprint data."""

    manifest = read_manifest(manifest_path)
    catalog_name, sizes, output_format, identifiers, animations = validate_manifest(manifest)
    catalog = open_catalog(catalog_name, catalog_dir)
    unsupported = sorted(set(sizes) - set(catalog.available_sizes))
    if unsupported:
        raise ValueError(
            "sizes {} are unavailable in the {!r} catalog; available sizes: {}".format(
                ", ".join(map(str, unsupported)),
                catalog_name,
                ", ".join(map(str, catalog.available_sizes)),
            )
        )
    canonical_identifiers = tuple(
        sorted({catalog.normalize_identifier(icon) for icon in identifiers})
    )
    assets = catalog.resolve_many(canonical_identifiers, sizes)
    symbols = {
        (asset.family, asset.name, asset.width, asset.height): _symbol(asset) for asset in assets
    }
    resolved = _resolve_animations(
        animations, catalog, canonical_identifiers, sizes, symbols
    )
    rows = [
        analyze(asset.family, asset.name, asset.width, asset.height, asset.data, output_format)
        for asset in assets
    ]
    animation_rows = [
        {
            "name": animation["name"],
            "frames": len(animation["frames"]),
            "loop": animation["loop"],
            "total_duration_ms": sum(frame["duration_ms"] for frame in animation["frames"]),
        }
        for animation in animations
    ]
    header = render_header(assets, manifest, catalog.provenance, output_format, resolved)
    totals = summarize(rows, len(header.encode("utf-8")))
    totals["animations"] = len(animation_rows)
    totals["animation_frames"] = sum(row["frames"] for row in animation_rows)
    return {
        "catalog": catalog_name,
        "format": output_format,
        "provenance": catalog.provenance,
        "icons": rows,
        "animations": animation_rows,
        "totals": totals,
    }


def update_manifest(
    path: Path,
    icons: Sequence[str],
    sizes: Sequence[int] = None,
    output_format: str = None,
    catalog: str = None,
) -> None:
    """Add or remove normalized values while preserving a readable manifest."""

    manifest = read_manifest(path) if Path(path).exists() else {}
    if catalog is not None:
        manifest["catalog"] = catalog
    manifest.setdefault("catalog", "fontawesome")
    if sizes is not None:
        manifest["sizes"] = list(sorted(set(sizes)))
    if output_format is not None:
        manifest["format"] = output_format
    manifest["icons"] = sorted(set(icons))
    validate_manifest(manifest)
    Path(path).write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
