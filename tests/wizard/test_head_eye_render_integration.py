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
        for _ in range(66):
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
                    presentation.rendered_head_pose_id,
                )
            )

        self.assertEqual(samples[0][1:3], ("south", "front_idle"))
        self.assertEqual(samples[0][3:5], (-1, "leading"))
        self.assertIn("profile_left", [item[5] for item in samples])
        self.assertEqual(samples[-1][1:3], ("north", "front_idle"))
        self.assertEqual(samples[-1][4], "steady")
        self.assertEqual(samples[-1][5], "back_idle")

        target_arrival = next(item for item in samples if item[1] == "north")
        self.assertEqual(target_arrival[3], 0)
        self.assertIn(target_arrival[4], {"turning", "settling"})

        pose_sequence = []
        for item in samples:
            head_pose_id = item[5]
            if not pose_sequence or pose_sequence[-1] != head_pose_id:
                pose_sequence.append(head_pose_id)
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

    def test_idle_head_turn_preserves_body_pose_and_planted_contact(self):
        source = ProceduralWizardFrameSource(cols=180, rows=101, fps=24)
        first = source.render_captured_candidate_sync(source.capture_render_state())
        source.commit_render_candidate(first)
        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("face", {"direction": "west"})
            ).ok
        )

        traces = []
        for _ in range(36):
            source.advance_simulation(1.0 / 60.0)
            candidate = source.render_captured_candidate_sync(
                source.capture_render_state()
            )
            source.commit_render_candidate(candidate)
            traces.append(candidate.animation_truth)

        self.assertEqual({trace.rendered_pose_id for trace in traces}, {"front_idle"})
        self.assertEqual({trace.render_scale for trace in traces}, {traces[0].render_scale})
        self.assertTrue(
            all(
                trace.silhouette_raster_span is not None
                and trace.silhouette_raster_span.min_x >= 4
                and trace.silhouette_raster_span.max_x <= 175
                and trace.silhouette_raster_span.min_y >= 4
                and trace.silhouette_raster_span.max_y <= 94
                for trace in traces
            )
        )
        self.assertEqual(
            {trace.presentation_channels.head_offset_y for trace in traces},
            {-1, 0},
        )
        self.assertIn(
            "profile_left",
            {
                trace.presentation_channels.rendered_head_pose_id
                for trace in traces
            },
        )
        self.assertIn(
            "walk_front_left",
            {
                trace.presentation_channels.rendered_head_pose_id
                for trace in traces
            },
        )
        three_quarter = [
            trace
            for trace in traces
            if trace.presentation_channels.rendered_head_pose_id
            == "walk_front_left"
        ]
        self.assertGreaterEqual(len(three_quarter), 10)
        breathing = [
            trace
            for trace in traces
            if trace.presentation_channels.head_offset_y == -1
        ]
        self.assertTrue(breathing)
        self.assertTrue(
            all(
                trace.presentation_channels.rendered_head_pose_id == "profile_left"
                and trace.presentation_channels.head_eye_phase == "steady"
                for trace in breathing
            )
        )
        planted = [
            (trace.planted_anchor_stage.x, trace.planted_anchor_stage.y)
            for trace in traces
            if trace.planted_anchor_stage is not None
        ]
        self.assertTrue(planted)
        self.assertEqual(len(set(planted)), 1)
        turn_blinks = [
            trace
            for trace in traces
            if "turn" in trace.presentation_channels.blink_source
        ]
        self.assertTrue(turn_blinks)
        self.assertTrue(
            all(
                trace.presentation_channels.blink_painted_cells > 0
                for trace in turn_blinks
            )
        )

    def test_idle_breath_moves_only_the_head_and_is_tick_deterministic(self):
        source = ProceduralWizardFrameSource(cols=180, rows=101, fps=24)
        initial = source.render_captured_candidate_sync(source.capture_render_state())
        source.commit_render_candidate(initial)

        state = source.current_state()
        state.simulation_tick = 36
        state.state_revision = 36
        inhale = source.render_captured_candidate_sync(source.capture_render_state())
        inhale_again = source.render_captured_candidate_sync(source.capture_render_state())

        state.simulation_tick = 48
        state.state_revision = 48
        release = source.render_captured_candidate_sync(source.capture_render_state())

        self.assertEqual(inhale.cells, inhale_again.cells)
        self.assertEqual(inhale.animation_truth.frame_sha256, inhale_again.animation_truth.frame_sha256)
        self.assertEqual(inhale.animation_truth.presentation_channels.head_offset_y, -1)
        self.assertEqual(release.animation_truth.presentation_channels.head_offset_y, 0)
        self.assertNotEqual(inhale.animation_truth.frame_sha256, release.animation_truth.frame_sha256)
        self.assertEqual(
            inhale.animation_truth.presented_root_stage,
            release.animation_truth.presented_root_stage,
        )
        self.assertEqual(
            inhale.animation_truth.planted_anchor_stage,
            release.animation_truth.planted_anchor_stage,
        )

        state.simulation_tick = 36
        state.state_revision = 49
        state.speech_mouth_authority = "media_alignment"
        speech = source.render_captured_candidate_sync(source.capture_render_state())
        self.assertEqual(speech.animation_truth.presentation_channels.head_offset_y, 0)

    def test_profile_listening_hold_keeps_restrained_head_only_breath(self):
        source = ProceduralWizardFrameSource(cols=180, rows=101, fps=24)
        state = source.current_state()

        state.simulation_tick = 228
        state.locomotion = "idle"
        state.action = "idle"
        state.speech_mouth_authority = "none"

        self.assertEqual(source._idle_head_breath_offset(state, "steady", "west"), -1)
        self.assertEqual(source._idle_head_breath_offset(state, "steady", "east"), -1)
        self.assertEqual(source._idle_head_breath_offset(state, "settling", "west"), 0)
        self.assertEqual(source._idle_head_breath_offset(state, "steady", "north"), 0)

    def test_accessibility_profiles_suppress_idle_head_breath(self):
        source = ProceduralWizardFrameSource(cols=180, rows=101, fps=24)
        state = source.current_state()
        state.simulation_tick = 228
        state.locomotion = "idle"
        state.action = "idle"
        state.speech_mouth_authority = "none"

        for profile in ("reduced", "still"):
            with self.subTest(profile=profile):
                state.performance_motion_profile = profile
                self.assertEqual(
                    source._idle_head_breath_offset(state, "steady", "south"),
                    0,
                )

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
