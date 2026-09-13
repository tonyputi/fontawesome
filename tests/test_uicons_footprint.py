import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.uicons.catalog import Catalog, LucideCatalog, open_catalog
from tools.uicons.cli import main
from tools.uicons.formats import (
    FORMATS,
    analyze,
    bounding_box,
    convert,
    cropped_bytes,
    decode_vertical,
    rle_bytes,
    stride,
    summarize,
    to_row_major,
    to_vertical,
)
from tools.uicons.generator import build, report

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "src" / "vertical"
ICONS_DIR = ROOT / "assets" / "lucide" / "icons"

REPRESENTATIVE = [
    ("fontawesome", "fas/heart", 16),
    ("fontawesome", "fas/heart", 64),
    ("fontawesome", "fab/github", 16),
    ("lucide", "lucide/heart", 16),
    ("lucide", "lucide/settings", 24),
]


def _resolve(catalog_name, identifier, size):
    directory = CATALOG_DIR if catalog_name == "fontawesome" else ICONS_DIR
    return open_catalog(catalog_name, directory).resolve(identifier, size)


class FormatConversionTest(unittest.TestCase):
    def test_supported_formats(self):
        self.assertEqual(tuple(sorted(FORMATS)), ("mono-rowmajor", "mono-vertical"))
        self.assertEqual(stride(16, "mono-vertical"), 16)
        self.assertEqual(stride(16, "mono-rowmajor"), 2)
        self.assertEqual(stride(24, "mono-rowmajor"), 3)

    def test_transpose_roundtrip_on_real_assets(self):
        for catalog_name, identifier, size in REPRESENTATIVE:
            asset = _resolve(catalog_name, identifier, size)
            with self.subTest(icon=identifier, size=size):
                rowmajor = to_row_major(asset.data, asset.width, asset.height)
                self.assertEqual(len(rowmajor), asset.height * ((asset.width + 7) // 8))
                self.assertEqual(to_vertical(rowmajor, asset.width, asset.height), asset.data)

    def test_both_layouts_decode_to_same_pixels(self):
        for catalog_name, identifier, size in REPRESENTATIVE:
            asset = _resolve(catalog_name, identifier, size)
            with self.subTest(icon=identifier, size=size):
                expected = decode_vertical(asset.data, asset.width, asset.height)
                rowmajor = to_row_major(asset.data, asset.width, asset.height)
                row_stride = (asset.width + 7) // 8
                decoded = [
                    [
                        1 if rowmajor[y * row_stride + x // 8] & (0x80 >> (x % 8)) else 0
                        for x in range(asset.width)
                    ]
                    for y in range(asset.height)
                ]
                self.assertEqual(decoded, expected)

    def test_unknown_format_rejected(self):
        asset = _resolve("fontawesome", "fas/heart", 16)
        with self.assertRaisesRegex(ValueError, "unsupported format"):
            convert(asset.data, asset.width, asset.height, "grayscale")
        with self.assertRaisesRegex(ValueError, "unsupported format"):
            stride(asset.width, "grayscale")


class FootprintAnalysisTest(unittest.TestCase):
    def test_rows_are_deterministic_and_consistent(self):
        asset = _resolve("fontawesome", "fas/heart", 16)
        first = analyze(asset.family, asset.name, asset.width, asset.height, asset.data, "mono-vertical")
        second = analyze(asset.family, asset.name, asset.width, asset.height, asset.data, "mono-vertical")
        self.assertEqual(first, second)
        self.assertEqual(first["bytes"], 32)
        self.assertEqual(first["lit"], sum(sum(row) for row in decode_vertical(asset.data, 16, 16)))
        self.assertEqual(first["cropped_bytes"], cropped_bytes(bounding_box(decode_vertical(asset.data, 16, 16))))
        self.assertEqual(first["rle_bytes"], rle_bytes(asset.data))

    def test_crop_never_exceeds_full_size(self):
        for catalog_name, identifier, size in REPRESENTATIVE:
            asset = _resolve(catalog_name, identifier, size)
            with self.subTest(icon=identifier, size=size):
                row = analyze(asset.family, asset.name, size, size, asset.data, "mono-vertical")
                self.assertLessEqual(row["cropped_bytes"], row["bytes"])
                self.assertGreater(row["lit"], 0)

    def test_report_totals_match_built_header(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            manifest = workspace / "uicons.json"
            manifest.write_text(
                json.dumps(
                    {
                        "catalog": "fontawesome",
                        "sizes": [16],
                        "format": "mono-rowmajor",
                        "icons": ["fas/heart", "fab/github"],
                    }
                ),
                encoding="utf-8",
            )
            data = report(manifest, CATALOG_DIR)
            again = report(manifest, CATALOG_DIR)
            self.assertEqual(data, again)
            self.assertEqual(data["format"], "mono-rowmajor")
            self.assertEqual(data["totals"]["icons"], 2)
            self.assertEqual(data["totals"]["data_bytes"], sum(row["bytes"] for row in data["icons"]))

            output = build(manifest, CATALOG_DIR, workspace / "generated")
            header = output.read_text(encoding="utf-8")
            self.assertEqual(data["totals"]["header_bytes"], len(header.encode("utf-8")))
            self.assertIn("PixelFormat::MonoRowMajor", header)
            self.assertNotIn("PixelFormat::MonoVertical", header)

    def test_report_matches_summarize(self):
        rows = [
            analyze("fas", "heart", 16, 16, _resolve("fontawesome", "fas/heart", 16).data, "mono-vertical"),
        ]
        totals = summarize(rows, 100)
        self.assertEqual(totals["icons"], 1)
        self.assertEqual(totals["data_bytes"], rows[0]["bytes"])
        self.assertEqual(totals["header_bytes"], 100)

    def test_cli_report_text_and_json(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            manifest = workspace / "uicons.json"
            manifest.write_text(
                json.dumps(
                    {
                        "catalog": "lucide",
                        "sizes": [16],
                        "format": "mono-vertical",
                        "icons": ["lucide/heart"],
                    }
                ),
                encoding="utf-8",
            )
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                self.assertEqual(
                    main(["report", "--manifest", str(manifest), "--catalog-dir", str(ICONS_DIR)]),
                    0,
                )
            self.assertIn("lucide/heart", buffer.getvalue())
            self.assertIn("data bytes:", buffer.getvalue())

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                self.assertEqual(
                    main(
                        [
                            "report",
                            "--manifest",
                            str(manifest),
                            "--catalog-dir",
                            str(ICONS_DIR),
                            "--as",
                            "json",
                        ]
                    ),
                    0,
                )
            parsed = json.loads(buffer.getvalue())
            self.assertEqual(parsed["totals"]["icons"], 1)
            self.assertEqual(parsed["icons"][0]["icon"], "lucide/heart")


if __name__ == "__main__":
    unittest.main()
