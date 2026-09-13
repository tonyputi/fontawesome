import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.uicons.catalog import LucideCatalog, open_catalog
from tools.uicons.cli import main
from tools.uicons.generator import build
from tools.uicons.lucide import SIZES, pixel_density, read_pack_metadata

ROOT = Path(__file__).resolve().parents[1]
ICONS_DIR = ROOT / "assets" / "lucide" / "icons"


class LucideCatalogTest(unittest.TestCase):
    def test_pack_version_and_license_are_pinned(self):
        version, license_name = read_pack_metadata(ICONS_DIR)
        self.assertRegex(version, r"^[0-9]+\.[0-9]+\.[0-9]+$")
        self.assertEqual(license_name, "ISC")

    def test_home_alias_resolves_to_house(self):
        catalog = LucideCatalog(ICONS_DIR)
        asset = catalog.resolve("lucide/home", 16)
        self.assertEqual(asset.name, "house")
        self.assertEqual(asset.family, "lucide")

    def test_unknown_icon_and_size_have_actionable_errors(self):
        catalog = LucideCatalog(ICONS_DIR)
        with self.assertRaisesRegex(ValueError, "not in the vendored Lucide subset"):
            catalog.resolve("lucide/definitely-not-an-icon", 16)
        with self.assertRaisesRegex(ValueError, "available Lucide sizes"):
            catalog.resolve("lucide/heart", 32)

    def test_curated_subset_is_legible_at_supported_sizes(self):
        catalog = LucideCatalog(ICONS_DIR)
        for identifier in catalog.available_icons():
            for size in SIZES:
                asset = catalog.resolve(identifier, size)
                density = pixel_density(asset.data)
                self.assertGreater(density, 0.02, f"{identifier} at {size}x{size} is nearly empty")
                self.assertLess(density, 0.50, f"{identifier} at {size}x{size} is a filled blob")
                self.assertEqual(len(asset.data), size * ((size + 7) // 8))

    def test_build_is_deterministic_and_carries_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            manifest = workspace / "uicons.json"
            manifest.write_text(
                json.dumps(
                    {
                        "catalog": "lucide",
                        "sizes": [16],
                        "format": "mono-vertical",
                        "icons": ["lucide/heart", "lucide/settings"],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = workspace / "generated"

            output = build(manifest, ICONS_DIR, output_dir)
            first = output.read_text(encoding="utf-8")
            build(manifest, ICONS_DIR, output_dir)
            second = output.read_text(encoding="utf-8")

            self.assertEqual(first, second)
            version, _ = read_pack_metadata(ICONS_DIR)
            self.assertIn(f"Lucide {version} (ISC,", first)
            self.assertIn("lucide_heart_16x16_data", first)
            self.assertNotIn("lucide_bell_16x16_data", first)

    def test_fontawesome_sizes_are_rejected_for_lucide(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            manifest = workspace / "uicons.json"
            manifest.write_text(
                json.dumps(
                    {
                        "catalog": "lucide",
                        "sizes": [32],
                        "format": "mono-vertical",
                        "icons": ["lucide/heart"],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "available sizes"):
                build(manifest, ICONS_DIR, workspace / "generated")

    def test_cli_init_add_build_roundtrip(self):
        previous = os.getcwd()
        os.chdir(ROOT)
        try:
            with tempfile.TemporaryDirectory() as directory:
                workspace = Path(directory)
                manifest = workspace / "uicons.json"
                self.assertEqual(
                    main(["init", "--manifest", str(manifest), "--catalog", "lucide", "--sizes", "16,24"]),
                    0,
                )
                self.assertEqual(
                    main(["add", "lucide/home", "--manifest", str(manifest)]),
                    0,
                )
                result = json.loads(manifest.read_text(encoding="utf-8"))
                self.assertEqual(result["catalog"], "lucide")
                self.assertEqual(result["icons"], ["lucide/house"])
                self.assertEqual(
                    main(["build", "--manifest", str(manifest), "--output-dir", str(workspace / "gen")]),
                    0,
                )
                header = (workspace / "gen" / "uicons_generated.h").read_text(encoding="utf-8")
                self.assertIn("lucide_house_16x16_data", header)
                self.assertIn("lucide_house_24x24_data", header)
        finally:
            os.chdir(previous)

    def test_open_catalog_factory(self):
        self.assertIsInstance(open_catalog("fontawesome"), object)
        self.assertIsInstance(open_catalog("lucide", ICONS_DIR), LucideCatalog)
        with self.assertRaisesRegex(ValueError, "unsupported catalog"):
            open_catalog("material")


if __name__ == "__main__":
    unittest.main()
