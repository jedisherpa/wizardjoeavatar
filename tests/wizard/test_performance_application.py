import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from wizard_avatar.controller import WizardAvatarController
from wizard_avatar.media_session import MediaSessionSnapshotV1
from wizard_avatar.performance_application import PerformanceApplication
from wizard_avatar.performance_score import CompiledScoreLoader, CompiledScoreRepository

from tests.wizard.test_performance_scheduler import bound_snapshot, runtime_score


def make_score_repository(root):
    return CompiledScoreRepository(
        root,
        CompiledScoreLoader(contract_validator=lambda _name, _value: None),
    )


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

    def test_live_media_releases_scripted_demo_locomotion(self):
        self.controller.apply_command(
            type("Command", (), {"type": "path", "payload": {
                "points": [{"x": -2.0, "z": 4.0}, {"x": 2.0, "z": 4.0}],
                "loop": True,
                "speed": 0.9,
            }})()
        )
        self.assertTrue(self.controller.locomotion.path.active)
        self.assertEqual(self.controller.state.action, "walking")

        self.accept(snapshot_mapping(), 0)
        result = self.application.apply(self.controller, 500_000)

        self.assertTrue(result.active)
        self.assertEqual(result.action, "staff_spin")
        self.assertFalse(self.controller.locomotion.path.active)
        self.assertEqual(self.controller.state.locomotion, "idle")

    def test_stale_heartbeat_releases_animation(self):
        self.accept(snapshot_mapping(), 0)
        self.assertTrue(self.application.apply(self.controller, 100_000).active)
        self.assertFalse(self.application.apply(self.controller, 1_500_001).active)

    def test_reaction_pause_suppresses_performance_without_losing_media_clock(self):
        self.accept(snapshot_mapping(), 0)
        self.assertTrue(self.application.apply(self.controller, 100_000).active)

        self.application.set_paused(True, self.controller)
        self.assertFalse(self.application.apply(self.controller, 200_000).active)
        self.assertEqual(self.controller.state.action, "idle")
        self.assertTrue(self.application.diagnostics(200_000)["reactions_paused"])

        self.application.set_paused(False)
        resumed = self.application.apply(self.controller, 300_000)
        self.assertTrue(resumed.active)
        self.assertEqual(resumed.media_time_ms, 300)

    def test_prepared_bound_score_is_resolved_without_tick_disk_io(self):
        score = runtime_score()
        snapshot = bound_snapshot(score, position=1500)
        with tempfile.TemporaryDirectory() as temporary:
            repository = make_score_repository(temporary)
            repository.publish(score)
            application = PerformanceApplication(
                "wizard-runtime-repository",
                score_repository=repository,
            )

            prepared = application.prepare_snapshot(snapshot)
            self.assertTrue(prepared.ready)
            with mock.patch.object(
                repository,
                "load_current",
                side_effect=AssertionError("event-loop path touched disk"),
            ):
                ack = application.accept_snapshot(snapshot, 0)
                result = application.apply(WizardAvatarController(), 0)
                current = application.scheduler.current_state(0)

            self.assertEqual(ack.scheduler_state, "playing")
            self.assertTrue(result.active)
            self.assertEqual(current.score_id, score.compiled_score_id)

    def test_bound_score_not_prepared_fails_closed_without_named_fallback(self):
        score = runtime_score()
        snapshot = bound_snapshot(score, position=1500)
        with tempfile.TemporaryDirectory() as temporary:
            repository = make_score_repository(temporary)
            repository.publish(score)
            application = PerformanceApplication(
                "wizard-runtime-not-prepared",
                score_repository=repository,
            )
            controller = WizardAvatarController()

            ack = application.accept_snapshot(snapshot, 0)
            result = application.apply(controller, 0)

            self.assertEqual(ack.scheduler_state, "error")
            self.assertEqual(ack.error_code, "score_not_ready")
            self.assertFalse(result.active)
            self.assertEqual(controller.state.action, "idle")
            self.assertEqual(
                application.diagnostics(0)["score_runtime"]["code"],
                "score_not_ready",
            )

        unconfigured = PerformanceApplication("wizard-runtime-no-repository")
        unconfigured_ack = unconfigured.accept_snapshot(snapshot, 0)
        unconfigured_result = unconfigured.apply(WizardAvatarController(), 0)
        self.assertEqual(unconfigured_ack.error_code, "score_not_ready")
        self.assertFalse(unconfigured_result.active)

    def test_prepare_failure_codes_are_returned_by_accept_snapshot(self):
        score = runtime_score()
        snapshot = bound_snapshot(score)
        other = runtime_score(compiled_id="compiled:other")
        with tempfile.TemporaryDirectory() as temporary:
            repository = make_score_repository(temporary)
            repository.publish(other)
            application = PerformanceApplication(
                "wizard-runtime-mismatch",
                score_repository=repository,
            )

            prepared = application.prepare_snapshot(snapshot)
            ack = application.accept_snapshot(snapshot, 0)

            self.assertEqual(prepared.code, "score_mismatch")
            self.assertEqual(ack.error_code, "score_mismatch")

    def test_repository_configuration_preserves_scoreless_migration_fallback(self):
        score = runtime_score()
        snapshot = bound_snapshot(score, with_score=False, mode="narrative")
        with tempfile.TemporaryDirectory() as temporary:
            application = PerformanceApplication(
                "wizard-runtime-scoreless",
                score_repository=CompiledScoreRepository(temporary),
            )

            prepared = application.prepare_snapshot(snapshot)
            ack = application.accept_snapshot(snapshot, 0)
            resolved = application.scheduler.current_state(0)

            self.assertEqual(prepared.code, "scoreless_v1")
            self.assertEqual(ack.scheduler_state, "scoreless")
            self.assertEqual(resolved.fallback_records[0]["fallback_id"], "scoreless-v1")

    def test_scoreless_preparation_without_repository_keeps_migration_name(self):
        score = runtime_score()
        snapshot = bound_snapshot(score, with_score=False, mode="narrative")

        prepared = PerformanceApplication("wizard-runtime-scoreless-no-repo").prepare_snapshot(
            snapshot
        )

        self.assertEqual(prepared.code, "scoreless_v1")

    def test_stage_and_gaze_reach_authoritative_state_or_report_suppression(self):
        self.accept(snapshot_mapping(), 0)
        resolved = replace(
            self.application.scheduler.current_state(500_000),
            world_position_milli=(750, 500),
            gaze_target="semantic:gaze:viewer_left",
            owned_channels=frozenset({"stage", "locomotion", "gaze"}),
        )

        suppressions = self.application._apply_stage_and_gaze(
            self.controller,
            resolved,
            body_allowed=True,
            gaze_allowed=True,
        )

        self.assertEqual(suppressions, ())
        self.assertAlmostEqual(self.controller.state.world_position["x"], 2.5)
        self.assertAlmostEqual(self.controller.state.world_position["z"], 5.75)
        self.assertTrue(self.controller.state.gaze_authoritative)
        self.assertEqual(self.controller.state.gaze_aim, -1)

        unsupported = replace(resolved, gaze_target="semantic:gaze:up")
        suppressions = self.application._apply_stage_and_gaze(
            self.controller,
            unsupported,
            body_allowed=True,
            gaze_allowed=True,
        )
        self.assertIn(
            {"channel": "gaze", "reason_code": "gaze_target_unsupported"},
            suppressions,
        )

    def test_user_control_lease_suppresses_score_stage_authority(self):
        self.accept(snapshot_mapping(), 0)
        self.controller.apply_command(
            type("Command", (), {"type": "control", "payload": {
                "source_kind": "keyboard",
                "lease_id": "manual-stage",
                "ttl_ms": 1000,
                "intent": {"move_x": 1.0, "move_z": 0.0},
            }})()
        )
        resolved = replace(
            self.application.scheduler.current_state(100_000),
            world_position_milli=(1000, 1000),
            owned_channels=frozenset({"stage", "locomotion"}),
        )
        before = dict(self.controller.state.world_position)

        suppressions = self.application._apply_stage_and_gaze(
            self.controller,
            resolved,
            body_allowed=False,
            gaze_allowed=True,
        )

        self.assertEqual(self.controller.state.world_position, before)
        self.assertIn(
            {"channel": "stage", "reason_code": "user_control_lease"},
            suppressions,
        )


if __name__ == "__main__":
    unittest.main()
