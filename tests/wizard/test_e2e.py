import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand


class EndToEndTests(unittest.TestCase):
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
