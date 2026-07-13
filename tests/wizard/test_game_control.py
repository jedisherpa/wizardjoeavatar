import time
import unittest
import uuid

from wizard_avatar.controller import WizardAvatarController
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand


def control_payload(sequence, intent, source_id="test-controller"):
    return {
        "command_id": "control-{}".format(sequence),
        "source_id": source_id,
        "source_kind": "keyboard",
        "source_sequence": sequence,
        "source_epoch": "test-epoch",
        "lease_id": "test-lease",
        "ttl_ms": 250,
        "intent": intent,
    }


class GameControlIntegrationTests(unittest.TestCase):
    def test_takeoff_directional_flight_and_landing(self):
        controller = WizardAvatarController()
        takeoff = controller.apply_command(
            WizardCommand(
                "control",
                control_payload(
                    1,
                    {
                        "move_x": 1.0,
                        "move_z": -0.4,
                        "ascend": 0.0,
                        "speed_mode": "run",
                        "mobility_request": "takeoff",
                        "held_actions": [],
                    },
                ),
            )
        )
        self.assertTrue(takeoff.ok, takeoff.message)
        for _ in range(12):
            controller.advance_tick()

        state = controller.current_state()
        self.assertTrue(state.airborne)
        self.assertGreater(state.altitude, 0.05)
        self.assertGreater(state.world_position["x"], 0.0)
        self.assertLess(state.world_position["z"], 5.0)

        for _ in range(120):
            controller.advance_tick()
        self.assertEqual(controller.current_state().mobility_mode, "hover")

        landing = controller.apply_command(
            WizardCommand(
                "control",
                control_payload(
                    2,
                    {
                        "move_x": 0.0,
                        "move_z": 0.0,
                        "ascend": 0.0,
                        "speed_mode": "walk",
                        "mobility_request": "land",
                        "held_actions": [],
                    },
                ),
            )
        )
        self.assertTrue(landing.ok, landing.message)
        for _ in range(180):
            controller.advance_tick()

        state = controller.current_state()
        self.assertFalse(state.airborne)
        self.assertEqual(state.mobility_mode, "grounded_idle")
        self.assertEqual(state.altitude, 0.0)

    def test_pose_override_remains_active_during_direct_movement(self):
        source = ProceduralWizardFrameSource()
        move = source.apply_command_sync(
            WizardCommand(
                "control",
                control_payload(
                    1,
                    {
                        "move_x": -1.0,
                        "move_z": 0.0,
                        "ascend": 0.0,
                        "speed_mode": "walk",
                        "mobility_request": "keep",
                        "held_actions": [],
                    },
                ),
            )
        )
        pose = source.apply_command_sync(
            WizardCommand("pose", {"pose_id": "magic_cast", "duration_ms": 0})
        )
        self.assertTrue(move.ok, move.message)
        self.assertTrue(pose.ok, pose.message)
        for _ in range(8):
            source.render_next_frame()

        state = source.current_state()
        self.assertEqual(state.pose_id, "magic_cast")
        self.assertLess(state.world_position["x"], 0.0)

    def test_prism_advice_cannot_take_movement_authority(self):
        controller = WizardAvatarController()
        user_control = controller.apply_command(
            WizardCommand(
                "control",
                control_payload(
                    1,
                    {
                        "move_x": 1.0,
                        "move_z": 0.0,
                        "ascend": 0.0,
                        "speed_mode": "walk",
                        "mobility_request": "keep",
                        "held_actions": [],
                    },
                ),
            )
        )
        self.assertTrue(user_control.ok, user_control.message)
        before = dict(controller.current_state().world_position)
        now_ms = int(time.time() * 1000)
        signal = controller.apply_command(
            WizardCommand(
                "prism_signal",
                {
                    "schema_version": 1,
                    "event_id": str(uuid.uuid4()),
                    "source_epoch": "test-prism",
                    "source_sequence": 1,
                    "emitted_at_ms": now_ms,
                    "ttl_ms": 1000,
                    "kind": "stage",
                    "classification": "visual_advisory_only",
                    "provenance_class": "runtime_lifecycle",
                    "sanitization_version": 1,
                    "payload": {"stage": "reviewing", "status": "active"},
                },
            )
        )

        self.assertTrue(signal.ok, signal.message)
        state = controller.current_state()
        self.assertEqual(state.semantic_cue, "review")
        self.assertEqual(state.control_source, "keyboard")
        self.assertEqual(state.expression, "focused")
        self.assertEqual(state.action, "thinking")
        self.assertEqual(state.world_position, before)
        for _ in range(5):
            controller.advance_tick()
        self.assertGreater(controller.current_state().world_position["x"], before["x"])

    def test_speech_text_and_mouth_share_one_lifecycle(self):
        controller = WizardAvatarController()
        started = controller.apply_command(
            WizardCommand(
                "speak",
                {"speech_id": "line-1", "text": "Hello there.", "duration_ms": 1000},
            )
        )
        self.assertTrue(started.ok, started.message)
        self.assertEqual(controller.current_state().speech_text, "Hello there.")
        self.assertEqual(controller.current_state().mouth, "open_small")

        for _ in range(60):
            controller.advance_tick()
        state = controller.current_state()
        self.assertIsNone(state.speech_id)
        self.assertIsNone(state.speech_text)
        self.assertEqual(state.action, "idle")


if __name__ == "__main__":
    unittest.main()
