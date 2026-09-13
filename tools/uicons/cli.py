"""Command-line interface for the dependency-free uIcons generator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional, Sequence

from .catalog import CATALOGS, open_catalog
from .generator import build, read_manifest, update_manifest, validate_manifest


def _sizes(value: str) -> List[int]:
    try:
        result = [int(item) for item in value.split(",") if item]
    except ValueError as error:
        raise argparse.ArgumentTypeError("sizes must be comma-separated integers") from error
    if not result or any(size <= 0 for size in result):
        raise argparse.ArgumentTypeError("sizes must contain positive integers")
    return sorted(set(result))


def _manifest_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("uicons.json"),
        help="project manifest (default: uicons.json)",
    )


def _catalog_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--catalog-dir",
        type=Path,
        default=None,
        help="catalog directory override (default: per-catalog repository directory)",
    )


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="uicons", description="Select and generate embedded uIcons headers")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create a project manifest")
    _manifest_argument(init)
    init.add_argument(
        "--catalog",
        choices=sorted(CATALOGS),
        default="fontawesome",
        help="icon catalog (default: fontawesome)",
    )
    init.add_argument("--sizes", type=_sizes, default=[16], help="comma-separated sizes (default: 16)")
    init.add_argument("--format", default="mono-vertical", help="bitmap format")

    add = commands.add_parser("add", help="add icons to the project manifest")
    add.add_argument("icons", nargs="+", help="icons in FAMILY/NAME form, for example fas/heart")
    _manifest_argument(add)
    _catalog_argument(add)
    add.add_argument("--sizes", type=_sizes, help="replace manifest sizes")
    add.add_argument("--format", help="replace manifest format")

    remove = commands.add_parser("remove", help="remove icons from the project manifest")
    remove.add_argument("icons", nargs="+", help="icons in FAMILY/NAME form")
    _manifest_argument(remove)

    build_parser = commands.add_parser("build", help="generate the selected header")
    _manifest_argument(build_parser)
    _catalog_argument(build_parser)
    build_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("include/uicons/generated"),
        help="generated header directory (default: include/uicons/generated)",
    )
    return parser


def _write_manifest(
    path: Path,
    icons: Sequence[str],
    sizes: Sequence[int],
    output_format: str,
    catalog: str,
) -> None:
    update_manifest(path, icons, sizes=sizes, output_format=output_format, catalog=catalog)
    print(f"updated {path}")


def _init(args: argparse.Namespace) -> None:
    if args.manifest.exists():
        raise ValueError(f"manifest already exists: {args.manifest}")
    manifest = {"catalog": args.catalog, "sizes": args.sizes, "format": args.format, "icons": []}
    validate_manifest(manifest)
    catalog = open_catalog(args.catalog, None)
    unsupported = sorted(set(args.sizes) - set(catalog.available_sizes))
    if unsupported:
        raise ValueError(
            "sizes {} are unavailable in the {!r} catalog; available sizes: {}".format(
                ", ".join(map(str, unsupported)),
                args.catalog,
                ", ".join(map(str, catalog.available_sizes)),
            )
        )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"created {args.manifest}")


def _add(args: argparse.Namespace) -> None:
    manifest = read_manifest(args.manifest) if args.manifest.exists() else {}
    catalog_name = manifest.get("catalog", "fontawesome")
    current_sizes = manifest.get("sizes", [16])
    sizes = args.sizes if args.sizes is not None else current_sizes
    output_format = args.format or manifest.get("format", "mono-vertical")
    catalog = open_catalog(catalog_name, args.catalog_dir)
    requested = [catalog.normalize_identifier(icon) for icon in args.icons]
    existing = {catalog.normalize_identifier(icon) for icon in manifest.get("icons", [])}
    icons = sorted(existing | set(requested))
    for icon in requested:
        for size in sizes:
            catalog.resolve(icon, size)
    _write_manifest(args.manifest, icons, sizes, output_format, catalog_name)


def _remove(args: argparse.Namespace) -> None:
    manifest = read_manifest(args.manifest)
    catalog_name = manifest.get("catalog", "fontawesome")
    catalog = open_catalog(catalog_name, None)
    icons = {catalog.normalize_identifier(icon) for icon in manifest.get("icons", [])}
    requested = {catalog.normalize_identifier(icon) for icon in args.icons}
    missing = sorted(requested - icons)
    if missing:
        raise ValueError("icons are not installed: " + ", ".join(missing))
    _write_manifest(
        args.manifest,
        sorted(icons - requested),
        manifest.get("sizes", [16]),
        manifest.get("format", "mono-vertical"),
        catalog_name,
    )


def _build(args: argparse.Namespace) -> None:
    output = build(args.manifest, args.catalog_dir, args.output_dir)
    print(f"generated {output}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    try:
        {"init": _init, "add": _add, "remove": _remove, "build": _build}[args.command](args)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0
