import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.pathing import circle_points, figure_eight_points, validate_path


class PathingTests(unittest.TestCase):
    def test_circle_and_figure_eight_points_are_bounded(self):
        self.assertGreater(len(circle_points(0, 5, 2, True)), 20)
        self.assertGreater(len(figure_eight_points()), 20)

    def test_rejects_out_of_bounds_path(self):
        with self.assertRaises(ValueError):
            validate_path([(99, 5)])

    def test_cancellation_stops_path_safely(self):
        source = ProceduralWizardFrameSource()
        source.apply_command_sync(WizardCommand("circle", {"center_x": 0, "center_z": 5, "radius": 2}))
        source.render_next_frame()
        result = source.apply_command_sync(WizardCommand("stop", {}))
        self.assertTrue(result.ok)
        self.assertEqual(source.current_state().locomotion, "idle")


if __name__ == "__main__":
    unittest.main()
