import json
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.rebuild_kingfisher_legacy_pairs import (
    FaceFeature,
    _binary_alpha,
    _donor_score,
    _normalize_registration,
)
from tools.stabilize_kingfisher_stage_pair import (
    validate_articulation_region,
)


class RebuildKingfisherLegacyPairsTests(unittest.TestCase):
    def test_normalization_uses_body_core_height_not_appendage_bounds(self):
        image = Image.new("RGBA", (960, 540), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((350, 87, 610, 528), fill=(20, 30, 40, 255))
        draw.rectangle((120, 2, 160, 300), fill=(20, 30, 40, 255))

        normalized, receipt = _normalize_registration(
            image,
            source_body_core_height=442,
        )

        self.assertEqual(receipt["target_body_core_height"], 432)
        self.assertEqual(receipt["target_baseline_y"], 529)
        self.assertLess(receipt["scale"], 1.0)
        self.assertEqual(normalized.getchannel("A").getbbox()[3], 529)

    def test_wide_pose_can_scale_up_without_cropping(self):
        image = Image.new("RGBA", (960, 540), (0, 0, 0, 0))
        ImageDraw.Draw(image).rectangle(
            (108, 157, 851, 522),
            fill=(20, 30, 40, 255),
        )

        normalized, receipt = _normalize_registration(
            image,
            source_body_core_height=366,
        )

        bbox = normalized.getchannel("A").getbbox()
        self.assertEqual(bbox[3], 529)
        self.assertLessEqual(bbox[2] - bbox[0], 900)
        self.assertGreater(receipt["scale"], 1.0)

    def test_binary_alpha_removes_interpolation_fringe(self):
        image = Image.new("RGBA", (2, 1), (20, 30, 40, 0))
        image.putpixel((1, 0), (20, 30, 40, 127))
        result = _binary_alpha(image)
        self.assertEqual(list(result.getchannel("A").getdata()), [0, 0])

    def test_donor_score_prefers_matching_beak_direction(self):
        target = FaceFeature(480, 250, 90, 50, 70)

        class Donor:
            def __init__(self, direction):
                self.feature = FaceFeature(480, 250, 90, 50, direction)

        self.assertLess(
            _donor_score(target, Donor(60)),
            _donor_score(target, Donor(-60)),
        )

    def test_profile_articulation_requires_explicit_larger_bound(self):
        region = (325, 196, 420, 337)
        with self.assertRaises(ValueError):
            validate_articulation_region(region)
        self.assertEqual(
            validate_articulation_region(
                region,
                maximum_width=220,
                maximum_height=190,
            ),
            region,
        )

    def test_committed_rebuild_plan_tracks_all_required_ranges(self):
        root = Path(__file__).resolve().parents[2]
        plan_path = (
            root
            / "assets"
            / "reference"
            / "characters"
            / "kingfisher"
            / "legacy-pairs-v1"
            / "rebuild-plan.json"
        )
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        self.assertEqual(plan["source_pose_ordinals"], {"first": 1, "last": 66})
        self.assertEqual(
            plan["speaking_variant_ordinals"],
            {"first": 111, "last": 176},
        )
        self.assertEqual(
            set(plan["mouth_occluded_ordinals"]),
            {4, 5},
        )
        self.assertEqual(
            set(plan["hard_reject_until_rebuilt"]),
            {30, 34, 35, 39, 42, 43, 48},
        )


if __name__ == "__main__":
    unittest.main()
