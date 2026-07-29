import unittest

from PIL import Image, ImageDraw

from tools.build_wizard_joe_hd_mouth_pairs import (
    _outside_region_is_identical,
    composite_opposite_mouth,
    select_donor,
)


class WizardJoeMouthPairBuildTests(unittest.TestCase):
    def test_selects_opposite_state_with_matching_geometry(self):
        target = {
            "pose_id": "target",
            "mouth_state": "closed",
            "mouth_region": [10, 20, 70, 40],
            "eye_landmarks": [[20, 10, 10, 5], [60, 10, 10, 5]],
        }
        near = {
            "pose_id": "near",
            "mouth_state": "open",
            "mouth_region": [12, 22, 72, 44],
            "eye_landmarks": [[22, 11, 10, 5], [62, 11, 10, 5]],
            "confidence_milli": 900,
        }
        far = {
            "pose_id": "far",
            "mouth_state": "open",
            "mouth_region": [0, 0, 150, 90],
            "eye_landmarks": [[10, 10, 10, 5]],
            "confidence_milli": 900,
        }
        self.assertEqual(select_donor(target, [near, far])["pose_id"], "near")

    def test_composite_changes_only_the_declared_articulation_region(self):
        target = Image.new("RGBA", (100, 80), (80, 40, 20, 255))
        donor = Image.new("RGBA", (100, 80), (80, 40, 20, 255))
        ImageDraw.Draw(donor).rectangle((20, 25, 70, 50), fill=(240, 230, 210, 255))
        region = [20, 25, 71, 51]
        result = composite_opposite_mouth(target, region, donor, region)
        self.assertTrue(_outside_region_is_identical(target, result, region))
        self.assertNotEqual(target.crop(region).tobytes(), result.crop(region).tobytes())


if __name__ == "__main__":
    unittest.main()
