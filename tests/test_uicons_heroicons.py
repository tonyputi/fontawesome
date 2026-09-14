import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.uicons.catalog import HeroiconsCatalog, open_catalog
from tools.uicons.cli import main
from tools.uicons.generator import build
from tools.uicons.heroicons import SIZES, pixel_density, rasterize_svg, read_pack_metadata

ROOT = Path(__file__).resolve().parents[1]
ICONS_DIR = ROOT / "assets" / "heroicons" / "icons"


class HeroiconsCatalogTest(unittest.TestCase):
    def test_pack_version_and_license_are_pinned(self):
        version, license_name = read_pack_metadata(ICONS_DIR)
        self.assertRegex(version, r"^[0-9]+\.[0-9]+\.[0-9]+$")
        self.assertEqual(license_name, "MIT")

    def test_unknown_icon_and_size_have_actionable_errors(self):
        catalog = HeroiconsCatalog(ICONS_DIR)
        with self.assertRaisesRegex(ValueError, "not in the vendored Heroicons subset"):
            catalog.resolve("heroicons/definitely-not-an-icon", 16)
        with self.assertRaisesRegex(ValueError, "available Heroicons sizes"):
            catalog.resolve("heroicons/heart", 32)

    def test_curated_subset_is_legible_at_supported_sizes(self):
        catalog = HeroiconsCatalog(ICONS_DIR)
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
                        "catalog": "heroicons",
                        "sizes": [16],
                        "format": "mono-vertical",
                        "icons": ["heroicons/heart", "heroicons/home"],
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
            self.assertIn(f"Heroicons {version} (MIT,", first)
            self.assertIn("heroicons_heart_16x16_data", first)
            self.assertNotIn("heroicons_bell_16x16_data", first)

    def test_fontawesome_sizes_are_rejected_for_heroicons(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            manifest = workspace / "uicons.json"
            manifest.write_text(
                json.dumps(
                    {
                        "catalog": "heroicons",
                        "sizes": [32],
                        "format": "mono-vertical",
                        "icons": ["heroicons/heart"],
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
                    main(
                        [
                            "init",
                            "--manifest",
                            str(manifest),
                            "--catalog",
                            "heroicons",
                            "--sizes",
                            "16,24",
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    main(["add", "heroicons/heart", "--manifest", str(manifest)]),
                    0,
                )
                result = json.loads(manifest.read_text(encoding="utf-8"))
                self.assertEqual(result["catalog"], "heroicons")
                self.assertEqual(result["icons"], ["heroicons/heart"])
                self.assertEqual(
                    main(
                        ["build", "--manifest", str(manifest), "--output-dir", str(workspace / "gen")]
                    ),
                    0,
                )
                header = (workspace / "gen" / "uicons_generated.h").read_text(encoding="utf-8")
                self.assertIn("heroicons_heart_16x16_data", header)
                self.assertIn("heroicons_heart_24x24_data", header)
        finally:
            os.chdir(previous)

    def test_open_catalog_factory(self):
        self.assertIsInstance(open_catalog("heroicons", ICONS_DIR), HeroiconsCatalog)
        with self.assertRaisesRegex(ValueError, "unsupported catalog"):
            open_catalog("material")


def _hex(data):
    return bytes(data).hex()


class HeroiconsRasterGoldenTest(unittest.TestCase):
    # Byte-exact pins for every vendored icon at every supported size. Any
    # rasterizer change that alters a single pixel fails here by design.
    GOLDENS = {
        ("bars-3", 16): "0000000010089009900990099009900990099009900990099009100800000000",
        (
            "bars-3",
            24,
        ): "000000000000000000401802c01803c01803c01803c01803c01803c01803c01803c01803c01803c01803c01803c01803c01803c01803c01803c01803401802000000000000000000",
        ("bell", 16): "000000000004e00778080c0804380628062804380c087808e007000400000000",
        (
            "bell",
            24,
        ): "00000000000000000000800100e00180ff01e00f0130000318000708001f0c00130c00330c00330c001308001f180007300003e00f0180ff0100e001008000000000000000000000",
        ("check", 16): "00000000000000030006000c0018001800060003c00060001800000000000000",
        (
            "check",
            24,
        ): "00000000000000000000000000300000600000c00000800100000300000600000e00000700c00100e000003800001c00000700800300e00000700000000000000000000000000000",
        (
            "cog-6-tooth",
            16,
        ): "00000000700e900910081818cc3346624662cc33181810089009700e00000000",
        (
            "cog-6-tooth",
            24,
        ): "00000000000000000080e701c0bd03601806600006400002601806387e1c0c42300cc3300cc3300c4230387e1c601806400002600006601806c0bd0380e701000000000000000000",
        ("heart", 16): "00002000f8010c02040c040804100820082004100408040c0c02f80120000000",
        (
            "heart",
            24,
        ): "000000000000800700e01f0030700018e00018800118000318000618000c30000c60001860001830000c18000c18000618000318800118e000307000e01f00800700000000000000",
        ("home", 16): "00008000c01fe03f306018600c7c066606660c7c18603060e03fc01f80000000",
        (
            "home",
            24,
        ): "000000000000001800000c0000fe1f000330800130c0003060003030803f18c03f0cc0300cc03018c03f30803f600030c0003080013000033000fe1f000c00001800000000000000",
        (
            "magnifying-glass",
            16,
        ): "0000c000f00308040408040806180618040804080804f00bc010002000000000",
        (
            "magnifying-glass",
            24,
        ): "000000000000001f00c07f00e0e0003080011800031800030c00060c00060c00060c00060c0006180003180003308001e0e003c07f07001f0e00001c000038000030000000000000",
        ("star", 16): "00004000c0004001603f602030100c180c1830106020603f4001c00040000000",
        (
            "star",
            24,
        ): "000000000000000600000e00001b00001b0800f31f00e31b000318c0030cf00006180006180006f00006c0030c00031800e31b00f31f001b08001b00000e00000600000000000000",
        ("x-mark", 16): "0000000000000000100820044002800180014002200410080000000000000000",
        (
            "x-mark",
            24,
        ): "000000000000000000000000000000600006e00007c0810380c30100e700007e00003c00003c00007e0000e70080c301c08103e00007600006000000000000000000000000000000",
    }

    def test_all_vendored_icons_match_goldens(self):
        self.assertEqual(
            set(self.GOLDENS), {(p.stem, s) for p in ICONS_DIR.glob("*.svg") for s in SIZES}
        )
        for (name, size), expected in sorted(self.GOLDENS.items()):
            text = (ICONS_DIR / f"{name}.svg").read_text(encoding="utf-8")
            self.assertEqual(_hex(rasterize_svg(text, size)), expected, f"{name} at {size}")


if __name__ == "__main__":
    unittest.main()
