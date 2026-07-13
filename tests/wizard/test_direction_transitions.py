import unittest

from wizard_avatar.views import step_direction_towards


class DirectionTransitionTests(unittest.TestCase):
    def test_direction_step_moves_only_one_adjacent_sector(self):
        self.assertEqual(step_direction_towards("south", "north"), "southwest")
        self.assertEqual(step_direction_towards("southwest", "north"), "west")
        self.assertEqual(step_direction_towards("east", "northwest"), "northeast")
        self.assertEqual(step_direction_towards("north", "north"), "north")


if __name__ == "__main__":
    unittest.main()
