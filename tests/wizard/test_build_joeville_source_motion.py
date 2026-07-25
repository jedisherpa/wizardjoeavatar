import json
import unittest
from pathlib import Path

from tools.build_joeville_source_motion import (
    _character_record,
    _refine_checkerboard_matte,
    _selected_source,
    _trim_neutral_fringe,
)
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
TRACKER = (
    ROOT
    / "assets"
    / "reference"
    / "joeville_48_parity"
    / "source-metadata"
    / "parity-tracker-v001.json"
)


class JoeVilleSourceMotionBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tracker = json.loads(TRACKER.read_text(encoding="utf-8"))

    def test_serena_has_eight_selected_source_sequences(self):
        serena = _character_record(cls_tracker := self.tracker, "serena-quill")
        selected = [
            _selected_source(sequence)
            for sequence in serena["source_sequences"]
        ]
        self.assertEqual(len(selected), 8)
        self.assertTrue(all(source is not None for source in selected))
        self.assertEqual(cls_tracker["contract"]["target_pose_count_per_character"], 48)

    def test_missing_authored_sequence_has_no_selected_source(self):
        selene = _character_record(self.tracker, "selene-hart")
        self.assertIsNone(_selected_source(selene["source_sequences"][-1]))

    def test_visual_conflict_decision_selects_exact_pack(self):
        elara = _character_record(self.tracker, "elara-voss")
        selected = _selected_source(elara["source_sequences"][2])
        self.assertIsNotNone(selected)
        self.assertEqual(selected["archive_id"], "sprites-3")

    def test_checkerboard_matte_removes_neutral_fringe(self):
        source = Image.new("RGBA", (7, 7), (250, 250, 250, 0))
        pixels = source.load()
        for y in range(2, 5):
            for x in range(2, 5):
                pixels[x, y] = (238, 224, 180, 255)
        pixels[3, 3] = (220, 150, 20, 255)

        refined = _refine_checkerboard_matte(source)

        self.assertEqual(refined.getpixel((3, 3)), (220, 150, 20, 255))
        edge = refined.getpixel((2, 3))
        self.assertLess(edge[3], 255)
        self.assertLess(edge[2], 180)
        self.assertEqual(refined.getpixel((0, 0))[3], 0)

    def test_neutral_trim_removes_only_outer_white_ring(self):
        source = Image.new("RGBA", (11, 11), (0, 0, 0, 0))
        pixels = source.load()
        for y in range(3, 8):
            for x in range(3, 8):
                pixels[x, y] = (255, 255, 255, 255)
        for y in range(4, 7):
            for x in range(4, 7):
                pixels[x, y] = (220, 150, 20, 255)

        trimmed = _trim_neutral_fringe(source)

        self.assertEqual(trimmed.getpixel((3, 5))[3], 0)
        self.assertEqual(trimmed.getpixel((5, 5)), (220, 150, 20, 255))


if __name__ == "__main__":
    unittest.main()
