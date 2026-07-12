import unittest

from wizard_avatar.geometry import quantize_scale
from wizard_avatar.projection import project_world_to_screen


class ProjectionTests(unittest.TestCase):
    def test_depth_changes_y_and_scale(self):
        near = project_world_to_screen(0, 1.5, 240, 135)
        far = project_world_to_screen(0, 10.0, 240, 135)
        self.assertGreater(near[1], far[1])
        self.assertGreater(near[2], far[2])

    def test_scale_quantizes_to_eighths(self):
        self.assertEqual(quantize_scale(1.19), 1.25)
        self.assertEqual(quantize_scale(0.56), 0.5)


if __name__ == "__main__":
    unittest.main()
