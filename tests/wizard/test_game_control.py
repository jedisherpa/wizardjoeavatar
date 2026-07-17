import copy
import json
import time
import unittest
import uuid
from pathlib import Path

from wizard_avatar.controller import WizardAvatarController
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.media_session import MediaSessionSnapshotV1
from wizard_avatar.models import WizardCommand
from wizard_avatar.performance_application import PerformanceApplication


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


def prism_v2(sequence, now_ms, turn_id, *, stage="reviewing", status="active", ttl_ms=1000):
    return {
        "schema_version": 2,
        "event_id": str(uuid.uuid4()),
        "source_epoch": "test-prism-v2",
        "source_sequence": sequence,
        "emitted_at_ms": now_ms,
        "ttl_ms": ttl_ms,
        "kind": "stage",
        "classification": "visual_advisory_only",
        "provenance_class": "runtime_lifecycle",
        "sanitization_version": 1,
        "turn_id": turn_id,
        "utterance_id": "utterance-{}".format(turn_id),
        "payload": {"stage": stage, "status": status},
    }


def live_music_snapshot():
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "audiobook_contracts"
        / "media_session_snapshot_v1.json"
    )
    value = json.loads(fixture.read_text(encoding="utf-8"))
    value["media"].update(
        {
            "media_id": "prism-overlap",
            "media_sha256": None,
            "kind": "music",
            "source_slot": "main",
            "source_kind": "library",
            "book_id": None,
            "chapter_id": None,
            "duration_ms": 60_000,
        }
    )
    value["playback"].update(
        {"state": "playing", "position_ms": 0, "rate_milli": 1000, "seeking": False}
    )
    value["performance"].update(
        {
            "mode": "music",
            "score_id": None,
            "score_revision": None,
            "score_sha256": None,
            "character_package_sha256": None,
            "motion_profile": "full",
            "disabled_channels": [],
        }
    )
    return MediaSessionSnapshotV1.from_mapping(copy.deepcopy(value))


class GameControlIntegrationTests(unittest.TestCase):
    def test_director_gaze_is_explicit_and_can_return_to_automatic(self):
        controller = WizardAvatarController()
        result = controller.apply_command(WizardCommand("gaze", {"target": "up"}))
        self.assertTrue(result.ok, result.message)
        self.assertTrue(controller.state.gaze_authoritative)
        self.assertEqual(controller.state.gaze_aim, 0)
        self.assertEqual(controller.state.gaze_vertical_aim, -1)

        result = controller.apply_command(
            WizardCommand("gaze", {"target": "automatic"})
        )
        self.assertTrue(result.ok, result.message)
        self.assertFalse(controller.state.gaze_authoritative)
        self.assertEqual(controller.state.gaze_vertical_aim, 0)

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

    def test_v2_terminal_and_expiry_restore_only_prism_owned_values(self):
        clock = {"now": 20_000}
        controller = WizardAvatarController(clock_ms=lambda: clock["now"])
        accepted = controller.apply_command(
            WizardCommand("prism_signal", prism_v2(1, clock["now"], "turn-a", ttl_ms=100))
        )
        self.assertTrue(accepted.ok, accepted.message)
        self.assertEqual(controller.state.expression, "focused")
        self.assertEqual(controller.state.action, "thinking")

        manual = controller.apply_command(
            WizardCommand("expression", {"expression": "happy"})
        )
        self.assertTrue(manual.ok, manual.message)
        clock["now"] += 100
        controller.advance_tick()
        self.assertFalse(controller.state.semantic_advisory_active)
        self.assertEqual(controller.state.expression, "happy")

        controller.apply_command(
            WizardCommand("prism_signal", prism_v2(2, clock["now"], "turn-new"))
        )
        stale = controller.apply_command(
            WizardCommand(
                "prism_signal",
                prism_v2(3, clock["now"], "turn-a", stage="ready", status="completed"),
            )
        )
        self.assertTrue(stale.ok, stale.message)
        self.assertTrue(controller.state.semantic_advisory_active)
        self.assertEqual(controller.state.semantic_turn_id, "turn-new")

    def test_speech_and_performance_release_reprojects_live_prism_channels(self):
        clock = {"now": 30_000}
        controller = WizardAvatarController(clock_ms=lambda: clock["now"])
        controller.apply_command(
            WizardCommand("prism_signal", prism_v2(1, clock["now"], "turn-overlap", ttl_ms=5000))
        )
        self.assertEqual(
            (controller.state.expression, controller.state.action),
            ("focused", "thinking"),
        )

        performance = PerformanceApplication("prism-overlap-runtime")
        performance.accept_snapshot(live_music_snapshot(), 0)
        self.assertTrue(performance.apply(controller, 100_000).active)
        controller.apply_command(
            WizardCommand(
                "speak",
                {"speech_id": "overlap-line", "text": "Reviewing.", "duration_ms": 1000},
            )
        )

        self.assertFalse(performance.apply(controller, 1_500_001).active)
        self.assertEqual(controller.state.expression, "focused")
        self.assertEqual(controller.state.action, "speaking")
        self.assertEqual(controller.state.mouth, "open_small")

        controller.apply_command(WizardCommand("speech_stop", {}))
        self.assertEqual(controller.state.expression, "focused")
        self.assertEqual(controller.state.action, "thinking")
        self.assertEqual(controller.state.mouth, "closed")

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
