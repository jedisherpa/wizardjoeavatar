import unittest

from wizard_avatar.palette import PALETTE, RGB, hex_to_rgb


class PaletteTests(unittest.TestCase):
    def test_reference_palette_values_are_stable(self):
        self.assertEqual(PALETTE["blue_mid"], "#0E4C89")
        self.assertEqual(PALETTE["gold"], "#EFA000")
        self.assertEqual(PALETTE["magenta"], "#C51E72")
        self.assertEqual(PALETTE["cyan_magic"], "#26D7E8")
        self.assertEqual(RGB["skin_light"], (233, 170, 113))

    def test_hex_parser_rejects_bad_values(self):
        self.assertEqual(hex_to_rgb("#FFFFFF"), (255, 255, 255))
        with self.assertRaises(ValueError):
            hex_to_rgb("#FFF")


if __name__ == "__main__":
    unittest.main()
