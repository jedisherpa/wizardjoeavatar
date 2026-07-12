import unittest

from wizard_avatar.floor import background_hash, build_background
from wizard_avatar.palette import ENV_RGB


class EnvironmentTests(unittest.TestCase):
    def test_background_hash_is_stable(self):
        self.assertEqual(background_hash(240, 135), background_hash(240, 135))

    def test_upper_background_is_white(self):
        bg = build_background(240, 135)
        for y in range(0, 50, 10):
            for x in range(0, 240, 30):
                self.assertEqual(bg.get(x, y).rgb, ENV_RGB["background"])

    def test_floor_is_faint(self):
        bg = build_background(240, 135)
        floor_cells = [bg.get(x, 100).rgb for x in range(0, 240, 12)]
        for rgb in floor_cells:
            self.assertGreaterEqual(min(rgb), 235)


if __name__ == "__main__":
    unittest.main()
