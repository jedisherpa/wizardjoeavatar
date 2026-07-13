import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand


def run_seconds(source, seconds):
    source.advance_simulation(seconds)
    source.render_current_frame()


class AnimationChannelTests(unittest.TestCase):
    def test_speech_does_not_cancel_locomotion(self):
        source = ProceduralWizardFrameSource()
        self.assertTrue(
            source.apply_command_sync(WizardCommand("move", {"x": 1.5, "z": 5.0})).ok
        )
        run_seconds(source, 0.5)
        self.assertEqual(source.current_state().locomotion, "walking")

        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("speak", {"text": "Still walking.", "duration_ms": 300})
            ).ok
        )
        state = source.current_state()
        self.assertEqual(state.locomotion, "walking")
        self.assertIsNotNone(state.speech_id)

        run_seconds(source, 0.5)
        state = source.current_state()
        self.assertIsNone(state.speech_id)
        self.assertEqual(state.locomotion, "walking")
        self.assertNotEqual(state.mouth, "open_small")

    def test_speech_does_not_replace_active_cast_channel(self):
        source = ProceduralWizardFrameSource()
        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("action", {"action": "magic_cast", "duration_ms": 900})
            ).ok
        )
        before = source.current_state()
        self.assertEqual(before.action, "magic_cast")
        self.assertEqual(before.staff_state, "cast")

        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("speak", {"text": "A spell within a spell.", "duration_ms": 300})
            ).ok
        )
        during = source.current_state()
        self.assertEqual(during.action, "magic_cast")
        self.assertEqual(during.staff_state, "cast")
        self.assertIsNotNone(during.speech_id)

        run_seconds(source, 0.4)
        after_speech = source.current_state()
        self.assertIsNone(after_speech.speech_id)
        self.assertEqual(after_speech.action, "magic_cast")
        self.assertEqual(after_speech.staff_state, "cast")

    def test_reaction_restores_previous_active_action(self):
        source = ProceduralWizardFrameSource()
        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("action", {"action": "magic_cast", "duration_ms": 5000})
            ).ok
        )
        run_seconds(source, 0.25)
        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("action", {"action": "reaction", "duration_ms": 300})
            ).ok
        )
        self.assertEqual(source.current_state().action, "reaction")

        run_seconds(source, 0.5)
        restored = source.current_state()
        self.assertEqual(restored.action, "magic_cast")
        self.assertEqual(restored.upper_body_action, "cast")
        self.assertEqual(restored.staff_state, "cast")


if __name__ == "__main__":
    unittest.main()
