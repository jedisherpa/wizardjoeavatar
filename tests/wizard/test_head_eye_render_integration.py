import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand


class HeadEyeRenderIntegrationTests(unittest.TestCase):
    def test_opposite_face_command_uses_eye_lead_and_atomic_intermediate_poses(self):
        source = ProceduralWizardFrameSource(cols=180, rows=101, fps=24)
        source.render_current_frame()
        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("face", {"direction": "north"})
            ).ok
        )

        samples = []
        for _ in range(24):
            source.advance_simulation(1.0 / 60.0)
            source.render_current_frame()
            presentation = source._last_presentation_state
            samples.append(
                (
                    source.current_state().simulation_tick,
                    presentation.presented_facing,
                    presentation.pose_id,
                    presentation.gaze_aim,
                    presentation.head_eye_phase,
                )
            )

        self.assertEqual(samples[0][1:3], ("south", "front_idle"))
        self.assertEqual(samples[0][3:], (-1, "leading"))
        self.assertIn(("west", "profile_left"), [(item[1], item[2]) for item in samples])
        self.assertEqual(samples[-1][1:3], ("north", "back_idle"))
        self.assertEqual(samples[-1][4], "steady")

        pose_sequence = []
        for _, _, pose_id, _, _ in samples:
            if not pose_sequence or pose_sequence[-1] != pose_id:
                pose_sequence.append(pose_id)
        self.assertEqual(
            pose_sequence,
            [
                "front_idle",
                "walk_front_left",
                "profile_left",
                "back_left",
                "back_idle",
            ],
        )

    def test_same_tick_rerender_cannot_accelerate_head_turn(self):
        source = ProceduralWizardFrameSource(cols=180, rows=101, fps=24)
        source.render_current_frame()
        source.apply_command_sync(WizardCommand("face", {"direction": "north"}))
        source.advance_simulation(1.0 / 60.0)

        first = source.render_current_frame().cells
        first_state = source._head_eye_state
        second = source.render_current_frame().cells
        second_state = source._head_eye_state

        self.assertEqual(first, second)
        self.assertEqual(first_state, second_state)
        self.assertEqual(source._last_presentation_state.presented_facing, "south")
        self.assertEqual(source._last_presentation_state.head_eye_phase, "leading")

    def test_discarded_first_turn_candidate_catches_up_to_same_visible_tick(self):
        committed = ProceduralWizardFrameSource(cols=180, rows=101, fps=24)
        discarded = ProceduralWizardFrameSource(cols=180, rows=101, fps=24)
        committed.render_current_frame()
        discarded.render_current_frame()

        for source in (committed, discarded):
            source.current_state().simulation_tick = 5
            source.current_state().state_revision = 5
            source.current_state().set_facing("north")

        first = committed.render_captured_candidate_sync(
            committed.capture_render_state(), "adaptive"
        )
        committed.commit_render_candidate(first)
        discarded.render_captured_candidate_sync(
            discarded.capture_render_state(), "adaptive"
        )  # Deliberately not committed.

        for source in (committed, discarded):
            source.current_state().simulation_tick = 15
            source.current_state().state_revision = 15

        committed_later = committed.render_captured_candidate_sync(
            committed.capture_render_state(), "adaptive"
        )
        discarded_later = discarded.render_captured_candidate_sync(
            discarded.capture_render_state(), "adaptive"
        )

        self.assertEqual(committed_later.cells, discarded_later.cells)
        self.assertEqual(
            committed_later.presentation.head_eye_state,
            discarded_later.presentation.head_eye_state,
        )
        self.assertEqual(
            committed_later.presentation.last_presentation_state.presented_facing,
            discarded_later.presentation.last_presentation_state.presented_facing,
        )
        self.assertEqual(
            committed_later.presentation.last_presentation_state.head_eye_phase,
            discarded_later.presentation.last_presentation_state.head_eye_phase,
        )


if __name__ == "__main__":
    unittest.main()
