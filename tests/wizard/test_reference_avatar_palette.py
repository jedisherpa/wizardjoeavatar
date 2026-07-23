import json
import unittest
from pathlib import Path

from PIL import Image

from tools.build_reference_avatar_palette import build_palette
from tools.generate_reference_avatar_cells import quantize_to_palette


ROOT = Path(__file__).resolve().parents[2]
PALETTE_PATH = (
    ROOT
    / "assets"
    / "reference"
    / "motion_sources"
    / "canonical_palette_v1.json"
)
MANIFEST_PATH = ROOT / "assets" / "reference" / "motion_sources" / "manifest.json"
POSE_LIBRARY_PATH = (
    ROOT
    / "wizard_avatar"
    / "definitions"
    / "reference_avatar_pose_cells.json"
)
REFERENCE_PATH = ROOT / "assets" / "reference" / "target_voxel_wizard.png"


class ReferenceAvatarPaletteTests(unittest.TestCase):
    def test_committed_palette_matches_canonical_reference(self):
        committed = json.loads(PALETTE_PATH.read_text(encoding="utf-8"))
        rebuilt = build_palette(
            REFERENCE_PATH,
            color_count=64,
            threshold=30.0,
        )
        self.assertEqual(rebuilt, committed)

    def test_manifest_selects_the_canonical_palette(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(manifest["palette_id"], "wizardjoe_canonical_64_v1")
        self.assertEqual(
            manifest["canonical_palette_path"],
            "assets/reference/motion_sources/canonical_palette_v1.json",
        )

    def test_quantization_uses_only_declared_colors(self):
        palette = ((0, 0, 0), (255, 255, 255), (255, 0, 0))
        source = Image.new("RGB", (3, 1))
        source.putdata(((9, 8, 7), (245, 240, 238), (230, 20, 18)))
        result = quantize_to_palette(source, palette)
        self.assertEqual(set(result.getdata()), set(palette))

    def test_pose_library_cells_use_only_the_canonical_palette(self):
        palette = json.loads(PALETTE_PATH.read_text(encoding="utf-8"))
        allowed = {tuple(color) for color in palette["colors"]}
        library = json.loads(POSE_LIBRARY_PATH.read_text(encoding="utf-8"))
        used = {
            tuple(cell["rgb"])
            for pose in library["poses"]
            for cell in pose["cells"]
        }
        self.assertTrue(used)
        self.assertLessEqual(used, allowed)
        self.assertEqual(library["palette"]["id"], palette["palette_id"])
        self.assertEqual(library["palette"]["declared_color_count"], len(allowed))


if __name__ == "__main__":
    unittest.main()
