import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand


class AnchorContinuityTests(unittest.TestCase):
    def test_reference_pose_facings_keep_screen_position_and_scale_stable(self):
        source = ProceduralWizardFrameSource()
        observed = []
        for direction in ("south", "east", "north"):
            result = source.apply_command_sync(WizardCommand("face", {"direction": direction}))
            self.assertTrue(result.ok)
            frame = source.render_next_frame()
            state = source.current_state()
            observed.append(
                (
                    frame.raw_size,
                    state.screen_position["x"],
                    state.screen_position["y"],
                    state.display_scale,
                )
            )

        raw_sizes = {item[0] for item in observed}
        screen_positions = {(item[1], item[2]) for item in observed}
        display_scales = {item[3] for item in observed}
        self.assertEqual(raw_sizes, {240 * 135 * 4})
        self.assertEqual(len(screen_positions), 1)
        self.assertEqual(len(display_scales), 1)


if __name__ == "__main__":
    unittest.main()
