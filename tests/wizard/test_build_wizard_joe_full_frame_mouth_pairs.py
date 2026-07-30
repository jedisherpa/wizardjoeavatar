import unittest

from PIL import Image

from tools.build_wizard_joe_full_frame_mouth_pairs import (
    composite_registered_mouth,
    normalize_to_canonical_canvas,
    outside_region_is_identical,
    remove_chroma,
)


class WizardJoeFullFrameMouthPairTests(unittest.TestCase):
    def test_chroma_key_removes_bright_background_but_preserves_wing_green(self):
        source = Image.new("RGB", (5, 5), (0, 255, 0))
        for y in range(1, 4):
            for x in range(1, 4):
                source.putpixel((x, y), (18, 142, 48))

        result = remove_chroma(source)

        self.assertEqual(result.getpixel((0, 0))[3], 0)
        self.assertEqual(result.getpixel((2, 2))[3], 255)

    def test_candidate_silhouette_is_registered_to_canonical_bounds(self):
        canonical = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        candidate = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        for y in range(2, 6):
            for x in range(2, 6):
                canonical.putpixel((x, y), (12, 34, 56, 255))
        for y in range(1, 7):
            for x in range(1, 7):
                candidate.putpixel((x, y), (12, 34, 56, 255))

        result = normalize_to_canonical_canvas(candidate, canonical)

        self.assertEqual(result.getchannel("A").getbbox(), (2, 2, 6, 6))

    def test_registered_mouth_produces_whole_frame_with_canonical_body(self):
        canonical = Image.new("RGBA", (12, 12), (20, 30, 40, 255))
        candidate = Image.new("RGBA", (12, 12), (80, 90, 100, 255))
        region = [3, 4, 9, 8]

        result = composite_registered_mouth(canonical, candidate, region)

        self.assertTrue(outside_region_is_identical(canonical, result, region))
        self.assertNotEqual(
            result.crop(tuple(region)).tobytes(),
            canonical.crop(tuple(region)).tobytes(),
        )


if __name__ == "__main__":
    unittest.main()
