import copy
import dataclasses
import re
import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand


class RenderCommitAtomicityTests(unittest.TestCase):
    def setUp(self):
        self.source = ProceduralWizardFrameSource(cols=96, rows=54, fps=24)

    def committed_render_state(self):
        return {
            "frame_index": self.source.frame_index,
            "encoder_baseline": self.source._prev_encoded_frame,
            "encoder_generation": self.source._encoder_generation,
            "diagnostics": copy.deepcopy(self.source.diagnostics.as_dict()),
            "presentation_generation": self.source._presentation_generation,
            "display_pose_id": self.source._display_pose_id,
            "last_presentation_state": copy.deepcopy(
                self.source._last_presentation_state
            ),
            "head_eye_state": self.source._head_eye_state,
        }

    def test_rendering_one_snapshot_twice_is_pure_and_deterministic(self):
        snapshot = self.source.capture_render_state()
        before = self.committed_render_state()
        authoritative_before = copy.deepcopy(
            self.source.current_state().as_public_dict()
        )

        first = self.source.render_captured_candidate_sync(snapshot, "adaptive")
        second = self.source.render_captured_candidate_sync(snapshot, "adaptive")

        self.assertEqual(first.frame.cells, second.frame.cells)
        self.assertEqual(first.message, second.message)
        self.assertEqual(first.presentation, second.presentation)
        self.assertEqual(first.shown_frame, second.shown_frame)
        self.assertEqual(self.committed_render_state(), before)
        self.assertEqual(
            self.source.current_state().as_public_dict(),
            authoritative_before,
        )
        self.assertEqual(
            first.authoritative_state_sha256,
            snapshot.authoritative_state_sha256,
        )
        self.assertTrue(dataclasses.is_dataclass(first))
        self.assertTrue(first.__dataclass_params__.frozen)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            first.message = b"mutated"

    def test_rendering_cannot_advance_pending_animation_transition(self):
        state = self.source.current_state()
        state.locomotion = "walking"
        state.walk_phase = 0.1
        self.source.resolve_authoritative_animation_state()
        self.assertEqual(state.animation_transition_phase, "wait_gate")
        authoritative_before = copy.deepcopy(state.as_public_dict())
        snapshot = self.source.capture_render_state()

        first = self.source.render_captured_candidate_sync(snapshot, "adaptive")
        second = self.source.render_captured_candidate_sync(snapshot, "adaptive")

        self.assertEqual(first.frame.cells, second.frame.cells)
        self.assertEqual(state.as_public_dict(), authoritative_before)
        self.assertEqual(state.animation_node_id, "ground_idle")
        self.assertEqual(state.animation_transition_id, "idle_to_walk")

    def test_commit_advances_every_committed_render_field_once(self):
        snapshot = self.source.capture_render_state()
        candidate = self.source.render_captured_candidate_sync(snapshot, "adaptive")
        before = self.committed_render_state()

        self.source.commit_render_candidate(candidate)

        after = self.committed_render_state()
        self.assertEqual(after["frame_index"], before["frame_index"] + 1)
        self.assertEqual(after["encoder_baseline"], candidate.shown_frame)
        self.assertEqual(
            after["encoder_generation"], before["encoder_generation"] + 1
        )
        self.assertEqual(
            after["presentation_generation"],
            before["presentation_generation"] + 1,
        )
        self.assertEqual(
            after["presentation_generation"], candidate.presentation.generation
        )
        self.assertEqual(
            after["display_pose_id"], candidate.presentation.display_pose_id
        )
        self.assertEqual(
            after["last_presentation_state"],
            candidate.presentation.last_presentation_state,
        )
        self.assertEqual(
            after["head_eye_state"], candidate.presentation.head_eye_state
        )
        self.assertEqual(
            after["diagnostics"]["frame_sequence"], candidate.frame.frame_index
        )
        self.assertEqual(
            after["diagnostics"]["codec_tag"], candidate.frame.codec_tag
        )
        self.assertEqual(
            after["diagnostics"]["raw_frame_size"], candidate.frame.raw_size
        )
        self.assertEqual(
            after["diagnostics"]["encoded_frame_size"],
            candidate.frame.encoded_size,
        )
        self.assertEqual(
            after["diagnostics"]["delta_cell_count"],
            candidate.frame.changed_cells,
        )
        self.assertEqual(
            after["diagnostics"]["keyframe_count"],
            before["diagnostics"]["keyframe_count"]
            + int(candidate.frame.is_keyframe),
        )
        self.assertEqual(
            after["diagnostics"]["reconnect_count"],
            before["diagnostics"]["reconnect_count"],
        )

    def test_second_candidate_from_same_snapshot_is_rejected_atomically(self):
        snapshot = self.source.capture_render_state()
        accepted = self.source.render_captured_candidate_sync(snapshot, "adaptive")
        stale = self.source.render_captured_candidate_sync(snapshot, "adaptive")
        self.source.commit_render_candidate(accepted)
        committed = self.committed_render_state()

        with self.assertRaises(ValueError):
            self.source.commit_render_candidate(stale)

        self.assertEqual(self.committed_render_state(), committed)

    def test_reset_encoder_preserves_committed_presentation(self):
        snapshot = self.source.capture_render_state()
        candidate = self.source.render_captured_candidate_sync(snapshot, "adaptive")
        self.source.commit_render_candidate(candidate)
        presentation_before = (
            self.source._presentation_generation,
            self.source._display_pose_id,
            copy.deepcopy(self.source._last_presentation_state),
            self.source._head_eye_state,
        )

        self.source.reset_encoder()

        self.assertIsNone(self.source._prev_encoded_frame)
        self.assertEqual(
            (
                self.source._presentation_generation,
                self.source._display_pose_id,
                self.source._last_presentation_state,
                self.source._head_eye_state,
            ),
            presentation_before,
        )

    def test_authoritative_reset_discards_pre_reset_contact_presentation(self):
        self.source.apply_command_sync(
            WizardCommand("move", {"x": -2.0, "z": 5.0})
        )
        for _ in range(24):
            self.source.advance_simulation(1 / self.source.fps)
            candidate = self.source.render_captured_candidate_sync(
                self.source.capture_render_state(),
                "adaptive",
            )
            self.source.commit_render_candidate(candidate)
        stale = self.source.render_captured_candidate_sync(
            self.source.capture_render_state(),
            "adaptive",
        )
        self.assertNotEqual(self.source._contact_root_offset, (0.0, 0.0))

        result = self.source.apply_command_sync(WizardCommand("reset", {}))

        self.assertTrue(result.ok, result.message)
        self.assertEqual(self.source._contact_root_offset, (0.0, 0.0))
        self.assertIsNone(self.source._contact_anchor)
        self.assertIsNone(self.source._contact_lock_stage)
        self.assertIsNone(self.source._prev_encoded_frame)
        with self.assertRaisesRegex(ValueError, "encoder generation"):
            self.source.commit_render_candidate(stale)

    def test_encoder_reset_rejects_pre_reset_candidate_and_forces_keyframe(self):
        first = self.source.render_captured_candidate_sync(
            self.source.capture_render_state(), "adaptive"
        )
        self.source.commit_render_candidate(first)
        stale_snapshot = self.source.capture_render_state()
        stale = self.source.render_captured_candidate_sync(stale_snapshot, "adaptive")

        self.source.reset_encoder()
        after_reset = self.committed_render_state()
        with self.assertRaisesRegex(ValueError, "encoder generation"):
            self.source.commit_render_candidate(stale)
        self.assertEqual(self.committed_render_state(), after_reset)

        replacement = self.source.render_captured_candidate_sync(
            self.source.capture_render_state(), "adaptive"
        )
        self.assertTrue(replacement.is_keyframe)

    def test_authoritative_mutation_rejects_direct_candidate_atomically(self):
        snapshot = self.source.capture_render_state()
        candidate = self.source.render_captured_candidate_sync(snapshot, "adaptive")
        before = self.committed_render_state()
        self.source.current_state().expression = "happy"

        with self.assertRaisesRegex(ValueError, "authoritative state"):
            self.source.commit_render_candidate(candidate)

        self.assertEqual(self.committed_render_state(), before)

    def test_capture_deep_copies_authoritative_state(self):
        live_state = self.source.current_state()
        live_state.world_position["x"] = 1.25
        live_state.velocity["x"] = -3.5
        snapshot = self.source.capture_render_state()

        self.assertIsNot(snapshot.state, live_state)
        self.assertIsNot(snapshot.state.world_position, live_state.world_position)
        self.assertIsNot(snapshot.state.velocity, live_state.velocity)
        self.assertEqual(snapshot.presentation_generation, 0)
        self.assertRegex(
            snapshot.authoritative_state_sha256,
            re.compile(r"^[0-9a-f]{64}$"),
        )

        live_state.world_position["x"] = 8.0
        live_state.velocity["x"] = 9.0
        self.assertEqual(snapshot.state.world_position["x"], 1.25)
        self.assertEqual(snapshot.state.velocity["x"], -3.5)

        snapshot.state.world_position["z"] = 99.0
        self.assertNotEqual(live_state.world_position["z"], 99.0)

        with self.assertRaisesRegex(ValueError, "authoritative hash"):
            self.source.render_captured_candidate_sync(snapshot, "adaptive")

    def test_materialized_frame_cannot_mutate_frozen_candidate(self):
        snapshot = self.source.capture_render_state()
        candidate = self.source.render_captured_candidate_sync(snapshot, "adaptive")
        materialized = candidate.frame

        materialized.cells = b"changed"
        materialized.frame_index = 999

        self.assertEqual(candidate.cells, candidate.frame.cells)
        self.assertEqual(snapshot.frame_index, candidate.frame.frame_index)


if __name__ == "__main__":
    unittest.main()
