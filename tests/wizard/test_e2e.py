import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.reference_avatar import reference_pose_ids


class EndToEndTests(unittest.TestCase):
    def test_demo_can_show_every_pose_while_moving(self):
        source = ProceduralWizardFrameSource()
        moving = source.apply_command_sync(
            WizardCommand(
                "path",
                {
                    "points": [{"x": -2.0, "z": 4.0}, {"x": 2.0, "z": 6.0}],
                    "loop": True,
                    "speed": 0.85,
                },
            )
        )
        self.assertTrue(moving.ok, moving.message)
        for pose_id in reference_pose_ids():
            result = source.apply_command_sync(
                WizardCommand("pose", {"pose_id": pose_id, "duration_ms": 900})
            )
            self.assertTrue(result.ok, result.message)
            for _ in range(source._transition_frames + 1):
                source.render_next_frame()
            self.assertEqual(source.current_state().pose_id, pose_id)
            self.assertEqual(source.current_state().locomotion, "walking")

        cleared = source.apply_command_sync(WizardCommand("pose", {"pose_id": None}))
        self.assertTrue(cleared.ok, cleared.message)
        self.assertIsNone(source.current_state().pose_override_id)

    def test_pose_override_rejects_unknown_pose(self):
        source = ProceduralWizardFrameSource()
        result = source.apply_command_sync(
            WizardCommand("pose", {"pose_id": "not-a-real-pose", "duration_ms": 900})
        )
        self.assertFalse(result.ok)

    def test_required_demo_sequence_core_runs(self):
        source = ProceduralWizardFrameSource()
        sequence = [
            ("expression", {"expression": "happy"}),
            ("speak", {"text": "A tidy spellbook keeps the stars aligned.", "duration_ms": 800}),
            ("move", {"x": -1.0, "z": 5.0}),
            ("move", {"x": 1.0, "z": 5.0}),
            ("move", {"x": 0.0, "z": 7.0}),
            ("move", {"x": 0.0, "z": 3.0}),
            ("circle", {"center_x": 0, "center_z": 5, "radius": 1.0, "clockwise": True, "duration_seconds": 4}),
            ("circle", {"center_x": 0, "center_z": 5, "radius": 1.0, "clockwise": False, "duration_seconds": 4}),
            ("figure_eight", {"center_x": 0, "center_z": 5, "radius": 1.0}),
            ("action", {"action": "thinking", "duration_ms": 500}),
            ("action", {"action": "pointing", "duration_ms": 500}),
            ("action", {"action": "explaining", "duration_ms": 500}),
            ("action", {"action": "magic_cast", "duration_ms": 500}),
            ("action", {"action": "reaction", "duration_ms": 500}),
            ("expression", {"expression": "neutral"}),
            ("stop", {}),
        ]
        for type_, payload in sequence:
            result = source.apply_command_sync(WizardCommand(type_, payload))
            self.assertTrue(result.ok, result.message)
            for _ in range(4):
                source.render_next_frame()
        self.assertEqual(source.current_state().expression, "neutral")


if __name__ == "__main__":
    unittest.main()
