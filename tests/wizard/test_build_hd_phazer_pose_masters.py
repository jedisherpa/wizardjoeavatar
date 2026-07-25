import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.build_hd_phazer_pose_masters import (
    _edge_connected_background,
    _extract_sheet_frames,
)
from wizard_avatar.hd_pose_artifact import HDPoseArtifact, HDPoseLibrary


ROOT = Path(__file__).resolve().parents[2]


class HDPhazerPoseBuilderTests(unittest.TestCase):
    def test_edge_background_removal_preserves_enclosed_white_pixels(self):
        image = Image.new("RGB", (24, 24), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((5, 5, 18, 18), fill=(40, 30, 20))
        draw.rectangle((8, 8, 15, 15), fill="white")

        background = _edge_connected_background(image, minimum=225, spread=32)

        self.assertEqual(background[0], 1)
        self.assertEqual(background[11 * 24 + 11], 0)

    def test_frame_grouping_keeps_a_crossing_component_whole(self):
        image = Image.new("RGB", (120, 60), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((12, 14, 38, 54), fill=(12, 72, 160))
        draw.rectangle((32, 26, 65, 34), fill=(12, 72, 160))
        draw.rectangle((82, 14, 108, 54), fill=(180, 75, 24))

        frames = _extract_sheet_frames(
            image,
            frame_count=2,
            minimum=225,
            spread=32,
            minimum_area=8,
        )

        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0]["source_bbox"], (12, 14, 66, 55))
        self.assertEqual(frames[1]["source_bbox"], (82, 14, 109, 55))
        self.assertEqual(frames[0]["image"].getbbox(), (0, 0, 54, 41))
        self.assertEqual(frames[1]["image"].getbbox(), (0, 0, 27, 41))

    def test_compiled_candidate_contains_48_complete_transparent_frames(self):
        artifact = HDPoseArtifact(
            ROOT
            / "assets"
            / "reference"
            / "hd_canonical"
            / "compiled"
            / "candidate-phazer-motion-v001.wjpose"
        )
        self.assertEqual(len(artifact.records), 48)
        self.assertEqual(artifact.canvas_size, (1254, 1254))
        corner_alpha_offsets = (
            3,
            (1254 - 1) * 4 + 3,
            ((1254 - 1) * 1254) * 4 + 3,
            (1254 * 1254 - 1) * 4 + 3,
        )
        for pose_id in sorted(artifact.records):
            rgba = artifact.load_rgba(pose_id)
            self.assertTrue(any(rgba[offset] for offset in range(3, len(rgba), 4)))
            self.assertTrue(all(rgba[offset] == 0 for offset in corner_alpha_offsets))

    def test_library_keeps_candidate_and_approval_counts_separate(self):
        library = HDPoseLibrary(
            ROOT
            / "assets"
            / "reference"
            / "hd_canonical"
            / "compiled"
            / "library-index.json"
        )

        self.assertEqual(len(library.pose_ids), 308)
        self.assertEqual(library.index["approved_pose_count"], 250)
        self.assertEqual(library.index["candidate_pose_count"], 58)
        self.assertEqual(
            len(library.index["sequences"]["approved_hd_frames"]["pose_ids"]), 250
        )
        self.assertEqual(len(library.index["sequences"]["phazer_all"]["pose_ids"]), 48)


if __name__ == "__main__":
    unittest.main()
