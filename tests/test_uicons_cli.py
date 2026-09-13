import json
import tempfile
import unittest
from pathlib import Path

from tools.uicons.catalog import Catalog
from tools.uicons.cli import main
from tools.uicons.generator import build


ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "src" / "vertical"


class UiconsGeneratorTest(unittest.TestCase):
    def test_aliases_resolve_to_canonical_family(self):
        asset = Catalog(CATALOG_DIR).resolve("solid/heart", 16)
        self.assertEqual(asset.family, "fas")
        self.assertEqual(asset.name, "heart")

    def test_unknown_icon_and_size_have_actionable_errors(self):
        catalog = Catalog(CATALOG_DIR)
        with self.assertRaisesRegex(ValueError, "unavailable"):
            catalog.resolve("fas/definitely-not-an-icon", 16)
        with self.assertRaisesRegex(ValueError, "available sizes"):
            catalog.resolve("fas/heart", 24)

    def test_build_is_selective_and_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            manifest = workspace / "uicons.json"
            manifest.write_text(
                json.dumps(
                    {
                        "catalog": "fontawesome",
                        "sizes": [16],
                        "format": "mono-vertical",
                        "icons": ["fas/heart", "fab/github"],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = workspace / "generated"

            output = build(manifest, CATALOG_DIR, output_dir)
            first = output.read_text(encoding="utf-8")
            build(manifest, CATALOG_DIR, output_dir)
            second = output.read_text(encoding="utf-8")

            self.assertEqual(first, second)
            self.assertIn("fas_heart_16x16_data", first)
            self.assertIn("fab_github_16x16_data", first)
            self.assertNotIn("fas_address_book_16x16_data", first)

    def test_build_removes_removed_icons_from_output(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            manifest = workspace / "uicons.json"
            manifest.write_text(
                json.dumps({"sizes": [16], "format": "mono-vertical", "icons": ["fas/heart"]}),
                encoding="utf-8",
            )
            output_dir = workspace / "generated"

            output = build(manifest, CATALOG_DIR, output_dir)
            self.assertIn("fas_heart_16x16_data", output.read_text(encoding="utf-8"))

            manifest.write_text(
                json.dumps({"sizes": [16], "format": "mono-vertical", "icons": []}),
                encoding="utf-8",
            )
            build(manifest, CATALOG_DIR, output_dir)
            self.assertNotIn("fas_heart_16x16_data", output.read_text(encoding="utf-8"))

    def test_cli_init_and_add_canonicalize_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            manifest = workspace / "uicons.json"
            self.assertEqual(
                main(["init", "--manifest", str(manifest), "--sizes", "16"]),
                0,
            )
            self.assertEqual(
                main(
                    [
                        "add",
                        "solid/heart",
                        "--manifest",
                        str(manifest),
                        "--catalog-dir",
                        str(CATALOG_DIR),
                    ]
                ),
                0,
            )
            result = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(result["icons"], ["fas/heart"])


if __name__ == "__main__":
    unittest.main()
