import json
import tempfile
import unittest
from pathlib import Path

from tools.uicons.catalog import Catalog
from tools.uicons.generator import build, report, validate_animations, validate_manifest

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "src" / "vertical"


def _manifest(**overrides):
    manifest = {
        "catalog": "fontawesome",
        "sizes": [16],
        "format": "mono-vertical",
        "icons": ["fas/heart"],
        "animations": [
            {
                "name": "heartbeat",
                "loop": 0,
                "frames": [
                    {"icon": "fas/heart", "size": 16, "duration_ms": 400},
                    {"icon": "fas/heart", "size": 16, "duration_ms": 200},
                ],
            }
        ],
    }
    manifest.update(overrides)
    return manifest


class AnimationManifestTest(unittest.TestCase):
    def test_animations_are_optional(self):
        _, _, _, _, animations = validate_manifest({"icons": []})
        self.assertEqual(animations, [])

    def test_animations_sorted_by_name(self):
        animations = validate_animations(
            [
                {"name": "b-second", "frames": [{"icon": "fas/heart", "size": 16, "duration_ms": 1}]},
                {"name": "a-first", "frames": [{"icon": "fas/heart", "size": 16, "duration_ms": 1}]},
            ]
        )
        self.assertEqual([animation["name"] for animation in animations], ["a-first", "b-second"])

    def test_invalid_animations_have_actionable_errors(self):
        bad = [
            ({"animations": {}}, "JSON array"),
            ({"animations": [[]]}, "JSON object"),
            ({"animations": [{"frames": []}]}, "non-empty 'name'"),
            ({"animations": [{"name": "x", "loop": -1, "frames": []}]}, "'loop'"),
            ({"animations": [{"name": "x", "frames": []}]}, "non-empty 'frames'"),
            (
                {"animations": [{"name": "x", "frames": [{"size": 16, "duration_ms": 1}]}]},
                "non-empty 'icon'",
            ),
            (
                {"animations": [{"name": "x", "frames": [{"icon": "fas/heart", "duration_ms": 1}]}]},
                "positive 'size'",
            ),
            (
                {"animations": [{"name": "x", "frames": [{"icon": "fas/heart", "size": 16}]}]},
                "positive 'duration_ms'",
            ),
            (
                {
                    "animations": [
                        {"name": "x", "frames": [{"icon": "fas/heart", "size": 16, "duration_ms": 1}]},
                        {"name": "x", "frames": [{"icon": "fas/heart", "size": 16, "duration_ms": 1}]},
                    ]
                },
                "unique",
            ),
        ]
        for manifest, message in bad:
            with self.subTest(manifest=manifest):
                with self.assertRaisesRegex(ValueError, message):
                    validate_manifest(manifest)

    def test_frames_must_reference_selected_icons_and_sizes(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            output_dir = workspace / "generated"

            manifest = workspace / "uicons.json"
            manifest.write_text(
                json.dumps(
                    _manifest(
                        animations=[
                            {
                                "name": "bad",
                                "frames": [
                                    {"icon": "fas/bell", "size": 16, "duration_ms": 100},
                                ],
                            }
                        ]
                    )
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "not in.*manifest 'icons'"):
                build(manifest, CATALOG_DIR, output_dir)

            manifest.write_text(
                json.dumps(
                    _manifest(
                        animations=[
                            {
                                "name": "bad",
                                "frames": [
                                    {"icon": "fas/heart", "size": 32, "duration_ms": 100},
                                ],
                            }
                        ]
                    )
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "not in manifest.*'sizes'"):
                build(manifest, CATALOG_DIR, output_dir)

    def test_build_emits_animations_deterministically(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            manifest = workspace / "uicons.json"
            manifest.write_text(json.dumps(_manifest()), encoding="utf-8")
            output_dir = workspace / "generated"

            output = build(manifest, CATALOG_DIR, output_dir)
            first = output.read_text(encoding="utf-8")
            build(manifest, CATALOG_DIR, output_dir)
            self.assertEqual(first, output.read_text(encoding="utf-8"))

            self.assertIn("anim_heartbeat_frames", first)
            self.assertIn("static const Animation anim_heartbeat(anim_heartbeat_frames, 2,", first)
            self.assertIn("{&fas_heart_16x16, 400}", first)

    def test_build_without_animations_emits_no_animation_symbols(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            manifest = workspace / "uicons.json"
            manifest.write_text(json.dumps(_manifest(animations=[])), encoding="utf-8")
            output = build(manifest, CATALOG_DIR, workspace / "generated")
            self.assertNotIn("Animation", output.read_text(encoding="utf-8"))

    def test_report_covers_animations(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            manifest = workspace / "uicons.json"
            manifest.write_text(json.dumps(_manifest()), encoding="utf-8")
            data = report(manifest, CATALOG_DIR)
            self.assertEqual(len(data["animations"]), 1)
            row = data["animations"][0]
            self.assertEqual(row["name"], "heartbeat")
            self.assertEqual(row["frames"], 2)
            self.assertEqual(row["total_duration_ms"], 600)
            self.assertEqual(data["totals"]["animations"], 1)
            self.assertEqual(data["totals"]["animation_frames"], 2)

    def test_alias_frames_resolve_to_canonical_icons(self):
        catalog = Catalog(CATALOG_DIR)
        self.assertEqual(catalog.normalize_identifier("solid/heart"), "fas/heart")


if __name__ == "__main__":
    unittest.main()
