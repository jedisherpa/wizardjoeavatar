import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand


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


if __name__ == "__main__":
    unittest.main()
