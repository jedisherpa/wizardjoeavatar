import unittest
from pathlib import Path

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import STAFF_STATES, WizardCommand
from wizard_avatar.stream import WizardFrameHub


SERENA_PACKAGE_PATH = (
    Path(__file__).resolve().parents[2]
    / "wizard_avatar"
    / "definitions"
    / "characters"
    / "serena_quill"
    / "serena_quill_character_package_v2.json"
)


class SerenaPackageControlTests(unittest.IsolatedAsyncioTestCase):
    def create_source(self):
        return ProceduralWizardFrameSource(
            cols=96,
            rows=54,
            fps=24,
            character_package_path=SERENA_PACKAGE_PATH,
        )

    def test_staffless_package_state_is_in_public_runtime_vocabulary(self):
        source = self.create_source()

        self.assertEqual(source.controller.state.staff_state, "none")
        self.assertIn(source.controller.state.staff_state, STAFF_STATES)

    def test_facing_uses_the_package_graph(self):
        source = self.create_source()

        result = source.controller.apply_command(
            WizardCommand("face", {"direction": "east"})
        )
        source.controller.advance_tick()
        source.resolve_authoritative_animation_state()

        self.assertTrue(result.ok)
        self.assertEqual(source.controller.state.pose_id, "neutral_right_profile")
        self.assertEqual(
            source.controller.state.animation_node_id,
            "node_neutral_right_profile",
        )

    def test_package_declared_action_selects_its_authored_pose(self):
        source = self.create_source()

        result = source.controller.apply_command(
            WizardCommand(
                "action",
                {"action": "mentoring_invitation", "duration_ms": 1200},
            )
        )
        source.controller.advance_tick()
        source.resolve_authoritative_animation_state()

        self.assertTrue(result.ok)
        self.assertEqual(source.controller.state.action, "mentoring_invitation")
        self.assertEqual(source.controller.state.pose_id, "mentoring_invitation")
        self.assertEqual(
            source.controller.state.animation_node_id,
            "node_mentoring_invitation",
        )

    def test_unbound_airborne_action_is_not_admitted_as_a_static_action(self):
        source = self.create_source()
        before = source.controller.state.as_public_dict()

        result = source.controller.apply_command(
            WizardCommand(
                "action",
                {"action": "jump", "duration_ms": 1200},
            )
        )

        self.assertFalse(result.ok)
        self.assertIn("Unsupported action", result.message)
        self.assertEqual(source.controller.state.as_public_dict(), before)

    def test_wizard_only_action_is_rejected_without_state_mutation(self):
        source = self.create_source()
        before = source.controller.state.as_public_dict()
        source.controller._prism_manual_suppressed.clear()

        result = source.controller.apply_command(
            WizardCommand("action", {"action": "staff_spin"})
        )

        self.assertFalse(result.ok)
        self.assertIn("Unsupported action", result.message)
        self.assertEqual(source.controller.state.as_public_dict(), before)
        self.assertNotIn("action", source.controller._prism_manual_suppressed)

    def test_package_cast_uses_generic_action_timing_not_wizard_markers(self):
        source = self.create_source()

        result = source.controller.apply_command(
            WizardCommand(
                "action",
                {"action": "magic_cast", "duration_ms": 100},
            )
        )
        self.assertTrue(result.ok)
        for _ in range(7):
            source.controller.advance_tick()
            source.resolve_authoritative_animation_state()

        self.assertEqual(source.controller.state.action, "idle")

    def test_invalid_action_duration_is_atomic(self):
        source = self.create_source()
        source.controller._queued_speech = {
            "speech_id": "queued",
            "text": "Keep me queued.",
            "duration_ms": 900,
        }
        source.controller._prism_manual_suppressed.clear()
        before = source.controller.state.as_public_dict()
        queued_before = dict(source.controller._queued_speech)

        result = source.controller.apply_command(
            WizardCommand(
                "action",
                {
                    "action": "mentoring_invitation",
                    "duration_ms": "not-an-integer",
                },
            )
        )

        self.assertFalse(result.ok)
        self.assertIn("duration_ms", result.message)
        self.assertEqual(source.controller.state.as_public_dict(), before)
        self.assertEqual(source.controller._queued_speech, queued_before)
        self.assertNotIn("action", source.controller._prism_manual_suppressed)

    def test_invalid_speech_duration_is_atomic(self):
        source = self.create_source()
        before = source.controller.state.as_public_dict()

        result = source.controller.apply_command(
            WizardCommand(
                "speak",
                {
                    "speech_id": "invalid-duration",
                    "text": "This must not start.",
                    "duration_ms": "not-an-integer",
                },
            )
        )

        self.assertFalse(result.ok)
        self.assertIn("duration_ms", result.message)
        self.assertEqual(source.controller.state.as_public_dict(), before)
        self.assertEqual(source.controller._prism_suspensions, {})

    def test_speech_mouth_shape_selects_explicit_package_viseme(self):
        source = self.create_source()

        result = source.controller.apply_command(
            WizardCommand(
                "speak",
                {
                    "speech_id": "serena-speech",
                    "text": "A careful answer.",
                    "duration_ms": 1000,
                },
            )
        )
        self.assertTrue(result.ok)
        source.controller.state.mouth = "open_wide"
        source.controller.advance_tick()
        source.resolve_authoritative_animation_state()

        self.assertEqual(source.controller.state.pose_id, "viseme_wide_vowel")
        self.assertEqual(
            source.controller.state.animation_node_id,
            "node_viseme_wide_vowel",
        )
        self.assertEqual(source.controller.state.upper_body_action, "none")
        self.assertEqual(source.controller.state.staff_state, "none")

    def test_idle_blink_selects_explicit_package_closed_pose(self):
        source = self.create_source()

        source.controller.advance_tick()
        source.controller.state.blink_phase = 1.0
        source.resolve_authoritative_animation_state()

        self.assertEqual(source.controller.state.pose_id, "blink_closed")
        self.assertEqual(
            source.controller.state.animation_node_id,
            "node_blink_closed",
        )

    def test_missing_locomotion_cycle_rejects_before_movement_mutation(self):
        source = self.create_source()
        before = source.controller.state.as_public_dict()

        result = source.controller.apply_command(
            WizardCommand("move", {"x": 4.0, "z": 5.0})
        )

        self.assertFalse(result.ok)
        self.assertIn("walk locomotion is not admitted", result.message)
        self.assertEqual(source.controller.state.as_public_dict(), before)
        self.assertFalse(source.controller.locomotion.path.active)
        self.assertIsNone(source.controller.locomotion.movement.target_x)
        self.assertIsNone(source.controller.locomotion.movement.target_z)

    async def test_performance_application_uses_the_package_graph(self):
        source = self.create_source()
        hub = WizardFrameHub(source)

        self.assertIs(hub.performance.animation_graph, source.animation_graph)
        self.assertIs(
            hub.performance.runtime_profile,
            source.character_package.runtime_profile_contract,
        )
        self.assertTrue(hub.performance.supports_action("mentoring_invitation"))
        self.assertFalse(hub.performance.supports_action("staff_spin"))
        await hub.stop()

    async def test_reduced_motion_releases_package_owned_action(self):
        source = self.create_source()
        hub = WizardFrameHub(source)
        source.controller._set_action("mentoring_invitation", 0)
        hub.performance._last_applied_action = "mentoring_invitation"

        hub.performance._release_body_projection(source.controller)

        self.assertEqual(source.controller.state.action, "idle")
        self.assertIsNone(hub.performance._last_applied_action)
        await hub.stop()


if __name__ == "__main__":
    unittest.main()
