import copy
import json
import unittest
from pathlib import Path

from wizard_avatar.controller import WizardAvatarController
from wizard_avatar.media_session import MediaSessionSnapshotV1
from wizard_avatar.performance_application import PerformanceApplication


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "audiobook_contracts"
    / "media_session_snapshot_v1.json"
)


def snapshot_mapping(*, sequence=0, slot="main", kind="music", mode="music", state="playing"):
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))
    value["sequence"] = sequence
    value["cause"] = "heartbeat" if sequence else "initial"
    value["media_epoch"] = 0
    value["media"].update(
        {
            "media_id": "live-{}".format(slot),
            "media_sha256": None,
            "kind": kind,
            "source_slot": slot,
            "source_kind": "tts" if slot == "speech" else "library",
            "book_id": None,
            "chapter_id": None,
            "duration_ms": 60_000,
        }
    )
    value["playback"].update(
        {"state": state, "position_ms": 0, "rate_milli": 1000, "seeking": False}
    )
    value["performance"].update(
        {
            "mode": mode,
            "score_id": None,
            "score_revision": None,
            "score_sha256": None,
            "character_package_sha256": None,
            "motion_profile": "full",
            "disabled_channels": [],
        }
    )
    return value


class PerformanceApplicationTests(unittest.TestCase):
    def setUp(self):
        self.application = PerformanceApplication("wizard-runtime-test")
        self.controller = WizardAvatarController()

    def accept(self, value, receipt_us):
        return self.application.accept_snapshot(
            MediaSessionSnapshotV1.from_mapping(copy.deepcopy(value)), receipt_us
        )

    def test_music_drives_native_action_and_releases_when_paused(self):
        ack = self.accept(snapshot_mapping(), 0)
        self.assertEqual(ack.disposition, "accepted")
        result = self.application.apply(self.controller, 500_000)
        self.assertTrue(result.active)
        self.assertEqual(result.action, "staff_spin")
        self.assertEqual(self.controller.state.expression, "happy")

        paused = snapshot_mapping(sequence=1, state="paused")
        paused["cause"] = "pause"
        self.accept(paused, 600_000)
        result = self.application.apply(self.controller, 600_000)
        self.assertFalse(result.active)
        self.assertEqual(self.controller.state.action, "idle")

    def test_tts_preempts_then_restores_latest_main_without_restarting(self):
        self.accept(snapshot_mapping(), 0)
        speech = snapshot_mapping(sequence=1, slot="speech", kind="tts", mode="speech")
        speech["cause"] = "play"
        self.accept(speech, 100_000)
        result = self.application.apply(self.controller, 220_000)
        self.assertEqual(result.source_slot, "speech")
        self.assertIn(self.controller.state.mouth, {"closed", "open_medium", "open_wide"})

        ended = snapshot_mapping(
            sequence=2, slot="speech", kind="tts", mode="speech", state="ended"
        )
        ended["cause"] = "ended"
        self.accept(ended, 300_000)
        restored = self.application.apply(self.controller, 300_000)
        self.assertEqual(restored.source_slot, "main")
        self.assertEqual(restored.media_time_ms, 300)

    def test_active_control_lease_keeps_body_authority(self):
        self.accept(snapshot_mapping(), 0)
        self.controller.apply_command(
            type("Command", (), {"type": "control", "payload": {
                "source_kind": "keyboard",
                "lease_id": "manual",
                "ttl_ms": 1000,
                "intent": {"move_x": 1.0, "move_z": 0.0},
            }})()
        )
        result = self.application.apply(self.controller, 100_000)
        self.assertTrue(result.active)
        self.assertIsNone(result.action)

    def test_stale_heartbeat_releases_animation(self):
        self.accept(snapshot_mapping(), 0)
        self.assertTrue(self.application.apply(self.controller, 100_000).active)
        self.assertFalse(self.application.apply(self.controller, 1_500_001).active)


if __name__ == "__main__":
    unittest.main()
