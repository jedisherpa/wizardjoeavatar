import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.palette import RGB


class ReferenceOverlayTests(unittest.TestCase):
    def test_speech_does_not_move_reference_root_screen(self):
        source = ProceduralWizardFrameSource()
        state = source.current_state()
        base = source._reference_root_screen(120.0, 80.0, state, 1.0)

        source.apply_command_sync(WizardCommand("speak", {"text": "Root stays put.", "duration_ms": 500}))
        speaking_a = source._reference_root_screen(120.0, 80.0, source.current_state(), 1.0)
        source.advance_simulation(0.2)
        speaking_b = source._reference_root_screen(120.0, 80.0, source.current_state(), 1.0)

        self.assertEqual(base, speaking_a)
        self.assertEqual(base, speaking_b)

    def test_cast_effect_follows_authored_markers_and_staff_tip(self):
        source = ProceduralWizardFrameSource()
        result = source.apply_command_sync(
            WizardCommand("action", {"action": "magic_cast", "duration_ms": 5000})
        )
        self.assertTrue(result.ok, result.message)

        by_authored_frame = {}
        for _ in range(100):
            candidate = source.render_captured_candidate_sync(
                source.capture_render_state()
            )
            trace = candidate.animation_truth
            if trace.animation_clip_id == "cast_front":
                by_authored_frame.setdefault(trace.animation_authored_frame, candidate)
            source.advance_simulation(1 / 60)

        for frame in range(14):
            self.assertEqual(by_authored_frame[frame].animation_truth.effect_intensity, 0.0)
        for frame in range(14, 23):
            self.assertEqual(by_authored_frame[frame].animation_truth.effect_intensity, 1.0)
        self.assertEqual(
            [by_authored_frame[frame].animation_truth.effect_intensity for frame in range(23, 28)],
            [1.0, 0.8, 0.6, 0.4, 0.2],
        )
        settled = by_authored_frame[28].animation_truth
        self.assertEqual(settled.effect_intensity, 0.0)
        self.assertIn("action_settled", settled.active_markers)

        onset = by_authored_frame[14]
        tip = onset.animation_truth.staff_tip_stage
        self.assertIsNotNone(tip)
        x, y = round(tip.x), round(tip.y)
        offset = (y * onset.cols + x) * 4
        self.assertEqual(
            tuple(onset.cells[offset + 1 : offset + 4]),
            RGB["gold_light"],
        )


if __name__ == "__main__":
    unittest.main()
