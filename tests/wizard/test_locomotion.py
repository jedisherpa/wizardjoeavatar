import math
import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand


def run_seconds(source, seconds):
    for _ in range(round(source.fps * seconds)):
        source.render_next_frame()


class LocomotionTests(unittest.TestCase):
    def test_walks_left_and_right(self):
        source = ProceduralWizardFrameSource()
        source.apply_command_sync(WizardCommand("move", {"x": -2.0, "z": 5.0}))
        run_seconds(source, 4.0)
        self.assertLess(source.current_state().world_position["x"], -1.8)
        source.apply_command_sync(WizardCommand("move", {"x": 2.0, "z": 5.0}))
        run_seconds(source, 5.0)
        self.assertGreater(source.current_state().world_position["x"], 1.8)

    def test_toward_and_away_camera(self):
        source = ProceduralWizardFrameSource()
        source.apply_command_sync(WizardCommand("move", {"x": 0.0, "z": 3.0}))
        run_seconds(source, 4.0)
        self.assertLess(source.current_state().world_position["z"], 3.2)
        near_scale = source.diagnostics_dict()["display_scale"]
        source.apply_command_sync(WizardCommand("move", {"x": 0.0, "z": 7.0}))
        run_seconds(source, 5.0)
        self.assertGreater(source.current_state().world_position["z"], 6.8)
        self.assertLess(source.diagnostics_dict()["display_scale"], near_scale)

    def test_walk_phase_follows_distance(self):
        source_a = ProceduralWizardFrameSource(fps=24)
        source_b = ProceduralWizardFrameSource(fps=30)
        for source in [source_a, source_b]:
            source.apply_command_sync(WizardCommand("move", {"x": 1.5, "z": 5.0}))
            run_seconds(source, 3.0)
        self.assertAlmostEqual(
            source_a.current_state().world_position["x"],
            source_b.current_state().world_position["x"],
            delta=0.08,
        )

    def test_stops_inside_target_tolerance(self):
        source = ProceduralWizardFrameSource()
        source.apply_command_sync(WizardCommand("move", {"x": 1.0, "z": 5.0}))
        run_seconds(source, 4.0)
        state = source.current_state()
        self.assertLess(math.hypot(state.world_position["x"] - 1.0, state.world_position["z"] - 5.0), 0.08)


if __name__ == "__main__":
    unittest.main()
