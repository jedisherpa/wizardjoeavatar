import unittest

from PIL import Image

from tools.build_wizard_joe_full_frame_mouth_pairs import (
    normalize_to_canonical_canvas,
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

    def test_canonical_size_frame_is_not_rescaled_from_its_silhouette(self):
        canonical = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        candidate = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        candidate.putpixel((1, 6), (12, 34, 56, 255))

        result = normalize_to_canonical_canvas(candidate, canonical)

        self.assertEqual(result.tobytes(), candidate.tobytes())


if __name__ == "__main__":
    unittest.main()
