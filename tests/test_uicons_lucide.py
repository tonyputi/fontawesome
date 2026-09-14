import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.uicons.catalog import LucideCatalog, open_catalog
from tools.uicons.cli import main
from tools.uicons.generator import build
from tools.uicons.lucide import SIZES, pixel_density, rasterize_svg, read_pack_metadata

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


def _hex(data):
    return bytes(data).hex()


class LucideRasterGoldenTest(unittest.TestCase):
    # Byte-exact pins for every vendored icon at every supported size. Any
    # rasterizer change that alters a single pixel fails here by design.
    GOLDENS = {
        ("bell", 16): "00000004000ef00b7c080608026802480248026806087c08f00b000e00040000",
        ("bell", 24): "00000000000000800100c003007003e03f03f00f033800030c00030e00330600730600630600630600730e00330c0003380003f00f03e03f0300700300c003008001000000000000",
        ("check", 16): "00000000800100030006000c000c000600038001c00060003000180000000000",
        ("check", 24): "00000000000000000000180000380000700000e00000c00100800300800300c00100e000007000003800001c00000e00000700800300c00100e00000600000000000000000000000",
        ("heart", 16): "0000f00118030c06040c04180c30186018600c300418040c0c061803f0010000",
        ("heart", 24): "000000800f00e03f00f0780030e00038c00118800318000718000e38001c30003870003070003030003838001c18000e18000718800338c00130e000f07800e03f00800f00000000",
        ("house", 16): "0000c01fe03f306018600c7f867f82618261867f0c7f18603060e03fc01f0000",
        ("house", 24): "00000000000000ff1f80ff3fc00130c0003060003070003038f03f1cf83f0e18300618300618300e18301cf83f38f03f700030600030c00030c0013080ff3f00ff1f000000000000",
        ("menu", 16): "0000000088118811881188118811881188118811881188118811881100000000",
        ("menu", 24): "00000000000000000030180c30180c30180c30180c30180c30180c30180c30180c30180c30180c30180c30180c30180c30180c30180c30180c30180c30180c000000000000000000",
        ("search", 16): "0000c001f007180c0c18041006100610061004180c08180ef013002000000000",
        ("search", 24): "000000000000003f00c0ff00e0e1017080033800071800061c000e0c000c0c000c0c000c0c000c1c000e180006380007708003e0e107c0ff0e003f1c000038000030000000000000",
        ("settings", 16): "00002004f81f981918189819ce7362466246ce73981918189819f81f20040000",
        ("settings", 24): "000000000000c0c303e0e707607e06603c06600006600006703c0e3c7e3c1ee77806c36006c3601ee7783c7e3c703c0e600006600006603c06607e06e0e707c0c303000000000000",
        ("star", 16): "0000e000e000203b207e30201c300e100e101c303020207e203be000e0000000",
        ("star", 24): "000000000700000f00000f00001b0080f33f80e13f80c138c00118f0001c7c000c1e000e1e000e7c000cf0001cc0011880c13880e13f80f33f001b00000f00000f00000700000000",
        ("x", 16): "0000000000000000100820044002800180014002200410080000000000000000",
        ("x", 24): "000000000000000000000000000000600006e00007c0810380c30100e700007e00003c00003c00007e0000e70080c301c08103e00007600006000000000000000000000000000000",
    }

    def test_all_vendored_icons_match_goldens(self):
        self.assertEqual(set(self.GOLDENS), {(p.stem, s) for p in ICONS_DIR.glob("*.svg") for s in SIZES})
        for (name, size), expected in sorted(self.GOLDENS.items()):
            text = (ICONS_DIR / f"{name}.svg").read_text(encoding="utf-8")
            self.assertEqual(_hex(rasterize_svg(text, size)), expected, f"{name} at {size}")

    COMMANDS_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M2 12 L6 12 H10 V16 H6 Z" />'
        '<path d="M12 4 C14 4 16 6 16 8 S20 12 20 12" />'
        '<path d="M2 20 Q6 16 10 20 T18 20" />'
        '<path d="M12 12 A4 4 0 0 1 20 12" />'
        '<circle cx="18" cy="18" r="3" />'
        '<rect x="2" y="2" width="4" height="4" rx="1" />'
        '<line x1="2" y1="22" x2="22" y2="22" />'
        '<polyline points="2,2 4,4 6,2" />'
        '<polygon points="10,2 12,4 10,6 8,4" />'
        "</svg>"
    )

    def test_every_path_command_and_shape_renders(self):
        # Exercises M/L/H/V/C/S/Q/T/A/Z plus circle, rect, line, polyline,
        # polygon so no command rots unnoticed.
        self.assertEqual(
            _hex(rasterize_svg(self.COMMANDS_SVG, 16)),
            "00009e719e539e5f8e5d8c5d9e778e61ec402c58787ce066e066c07d00580000",
        )
        self.assertEqual(
            _hex(rasterize_svg(self.COMMANDS_SVG, 24)),
            "0000003e18787e387c7e786c7ef8667ed8673e98671898673c986d7ef87d7ef8793c1c70181f60380360f0016fe0837fc0c77980cf7800cf7800df79009c7f00006f000060000000",
        )


class LucideSvgIngestionTest(unittest.TestCase):
    ROOT_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )

    def test_transform_fails_loudly_instead_of_rendering_wrong(self):
        body = '<path d="M2 12 H22" transform="translate(1 1)" />'
        with self.assertRaisesRegex(ValueError, "transform"):
            rasterize_svg(self.ROOT_SVG.format(body=body), 16)

    def test_unsupported_elements_are_rejected(self):
        body = '<ellipse cx="12" cy="12" rx="6" ry="4" />'
        with self.assertRaisesRegex(ValueError, "unsupported SVG element"):
            rasterize_svg(self.ROOT_SVG.format(body=body), 16)

    def test_invalid_documents_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid SVG"):
            rasterize_svg("<svg><path", 16)
        with self.assertRaisesRegex(ValueError, "expected an <svg> root"):
            rasterize_svg("<g></g>", 16)

    def test_single_quoted_attributes_parse(self):
        body = "<path d='M2 12 H22' />"
        self.assertGreater(sum(rasterize_svg(self.ROOT_SVG.format(body=body), 16)), 0)

    def test_comments_with_fake_tags_are_ignored(self):
        body = '<!-- <path d="M0 0 H24 V24 H0 Z" /> --><path d="M2 12 H22" />'
        plain = self.ROOT_SVG.format(body='<path d="M2 12 H22" />')
        self.assertEqual(
            rasterize_svg(self.ROOT_SVG.format(body=body), 16),
            rasterize_svg(plain, 16),
        )


if __name__ == "__main__":
    unittest.main()
