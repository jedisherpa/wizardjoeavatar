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

    def test_target_arrival_decelerates_without_a_late_snap(self):
        source = ProceduralWizardFrameSource(fps=24)
        source.apply_command_sync(
            WizardCommand("move", {"x": 0.0, "z": 2.45, "speed": 1.25})
        )
        observations = []
        previous_position = dict(source.current_state().world_position)
        previous_tick = source.current_state().simulation_tick
        for _ in range(96):
            source.render_next_frame()
            state = source.current_state()
            elapsed_ticks = state.simulation_tick - previous_tick
            distance = math.hypot(
                state.world_position["x"] - previous_position["x"],
                state.world_position["z"] - previous_position["z"],
            )
            observations.append(distance * 60.0 / elapsed_ticks)
            previous_position = dict(state.world_position)
            previous_tick = state.simulation_tick

        peak = max(observations)
        last_cruise = max(
            index for index, speed in enumerate(observations) if speed >= peak * 0.9
        )
        tail = observations[last_cruise:]
        self.assertGreaterEqual(len({round(speed, 2) for speed in tail}), 5)
        self.assertTrue(
            all(right <= left + 0.08 for left, right in zip(tail, tail[1:])),
            tail,
        )
        self.assertEqual(source.current_state().locomotion, "idle")
        self.assertAlmostEqual(source.current_state().world_position["z"], 2.45)


if __name__ == "__main__":
    unittest.main()
