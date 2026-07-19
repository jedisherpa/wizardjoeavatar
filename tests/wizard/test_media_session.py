import json
import unittest
from pathlib import Path

from wizard_avatar.media_session import (
    MediaClockEstimator,
    MediaSessionAckV1,
    MediaSessionCoordinator,
    MediaSessionError,
    MediaSessionSnapshotV1,
)


def digest(character):
    return "sha256:" + character * 64


def snapshot_mapping(
    sequence=0,
    media_epoch=0,
    cause="initial",
    state="playing",
    position_ms=1000,
    rate_milli=1000,
    source_slot="main",
    kind="audiobook",
    media_id=None,
    score_id=None,
    mode=None,
    with_hashes=True,
):
    hash_character = {"main": "1", "speech": "2"}[source_slot]
    media_hash = digest(hash_character) if with_hashes else None
    media_id = media_id or (
        "media:sha256:" + hash_character * 64 if with_hashes else "live-" + source_slot
    )
    score_id = score_id or ("compiled:" + source_slot)
    mode = mode or ("speech" if kind in {"speech", "tts"} else ("music" if kind == "music" else "narrative"))
    return {
        "schema_version": 1,
        "message_id": "00000000-0000-4000-8000-{:012x}".format(sequence + 1),
        "connector_session_id": "00000000-0000-4000-8000-000000000002",
        "sequence": sequence,
        "media_epoch": media_epoch,
        "cause": cause,
        "sampled_at_monotonic_ms": sequence,
        "media": {
            "media_id": media_id,
            "media_sha256": media_hash,
            "kind": kind,
            "source_slot": source_slot,
            "source_kind": "tts" if kind == "tts" else ("speech" if kind == "speech" else "studio_chapter"),
            "book_id": "book:one" if source_slot == "main" else None,
            "chapter_id": "chapter:one" if source_slot == "main" else None,
            "duration_ms": 10000,
        },
        "playback": {
            "state": state,
            "position_ms": position_ms,
            "rate_milli": rate_milli,
            "ready_state": 4,
            "seeking": state == "seeking",
        },
        "performance": {
            "mode": mode,
            "score_id": score_id if with_hashes else None,
            "score_revision": 1 if with_hashes else None,
            "score_sha256": digest(hash_character) if with_hashes else None,
            "character_id": "wizard-joe",
            "character_package_sha256": digest("a") if with_hashes else None,
            "intensity_milli": 700,
            "motion_profile": "full",
            "disabled_channels": [],
        },
    }


def snapshot(**changes):
    return MediaSessionSnapshotV1.from_mapping(snapshot_mapping(**changes))


class MediaSessionContractTests(unittest.TestCase):
    def test_snapshot_is_full_state_strict_and_content_free(self):
        parsed = snapshot()
        self.assertEqual(parsed.media.source_slot, "main")
        self.assertEqual(parsed.playback.position_ms, 1000)
        self.assertEqual(parsed.performance.disabled_channels, ())

        for private_field in ("transcript", "audio_bytes", "url", "path"):
            value = snapshot_mapping()
            value[private_field] = "private-canary"
            with self.assertRaises(MediaSessionError) as error:
                MediaSessionSnapshotV1.from_mapping(value)
            self.assertEqual(error.exception.code, "unknown_field")
            self.assertNotIn("private-canary", str(error.exception))

    def test_main_and_speech_slots_cover_all_six_media_kinds(self):
        self.assertEqual(snapshot(source_slot="speech", kind="tts").media.kind, "tts")
        self.assertEqual(snapshot(source_slot="speech", kind="speech").media.source_slot, "speech")
        self.assertEqual(snapshot(kind="podcast").media.kind, "podcast")
        self.assertEqual(snapshot(kind="video").media.kind, "video")
        invalid = snapshot_mapping(source_slot="speech", kind="music")
        with self.assertRaises(MediaSessionError) as error:
            MediaSessionSnapshotV1.from_mapping(invalid)
        self.assertEqual(error.exception.code, "invalid_enum")

    def test_speech_slot_rejects_a_leaked_main_performance_mode(self):
        invalid = snapshot_mapping(source_slot="speech", kind="tts", mode="music")

        with self.assertRaises(MediaSessionError) as error:
            MediaSessionSnapshotV1.from_mapping(invalid)

        self.assertEqual(error.exception.code, "invalid_enum")
        self.assertEqual(error.exception.path, "$.performance.mode")

    def test_golden_snapshot_documents_qualified_hash_and_integer_wire_format(self):
        fixture = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "audiobook_contracts"
            / "media_session_snapshot_v1.json"
        )
        value = json.loads(fixture.read_text(encoding="utf-8"))
        parsed = MediaSessionSnapshotV1.from_mapping(value)
        self.assertEqual(parsed.media.source_slot, "main")
        self.assertEqual(parsed.playback.rate_milli, 1250)
        self.assertEqual(parsed.performance.intensity_milli, 650)
        self.assertTrue(parsed.media.media_sha256.startswith("sha256:"))
        self.assertEqual(parsed.to_dict(), value)

    def test_score_and_hashes_are_optional_for_live_mode(self):
        parsed = snapshot(with_hashes=False, mode="narrative")
        self.assertEqual(parsed.performance.mode, "narrative")
        self.assertIsNone(parsed.performance.score_id)
        self.assertIsNone(parsed.media.media_sha256)

    def test_json_body_limit_is_enforced_before_parsing(self):
        with self.assertRaises(MediaSessionError) as error:
            MediaSessionSnapshotV1.from_json(b" " * (16 * 1024 + 1))
        self.assertEqual(error.exception.code, "body_too_large")

    def test_ack_golden_round_trips_with_exact_v1_fields(self):
        fixture = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "audiobook_contracts"
            / "media_session_ack_v1.json"
        )
        value = json.loads(fixture.read_text(encoding="utf-8"))
        parsed = MediaSessionAckV1.from_mapping(value)
        self.assertEqual(parsed.to_dict(), value)
        self.assertEqual(parsed.error_code, None)

        value["capabilities"]["private_path"] = "/private"
        with self.assertRaises(MediaSessionError) as error:
            MediaSessionAckV1.from_mapping(value)
        self.assertEqual(error.exception.code, "unknown_field")

    def test_duplicate_json_keys_and_unsorted_disabled_channels_fail(self):
        with self.assertRaises(MediaSessionError) as duplicate:
            MediaSessionSnapshotV1.from_json(b'{"schema_version":1,"schema_version":1}')
        self.assertEqual(duplicate.exception.code, "duplicate_json_key")
        value = snapshot_mapping()
        value["performance"]["disabled_channels"] = ["mouth", "face"]
        with self.assertRaises(MediaSessionError):
            MediaSessionSnapshotV1.from_mapping(value)


class MediaClockTests(unittest.TestCase):
    def test_rate_interpolation_and_nonplaying_freeze(self):
        estimator = MediaClockEstimator()
        estimator.observe(snapshot(rate_milli=1500), 1_000_000)
        self.assertEqual(estimator.position_at(1_200_000), 1300)

        estimator.observe(snapshot(sequence=1, cause="pause", state="paused", position_ms=1300), 1_200_000)
        self.assertEqual(estimator.position_at(2_000_000), 1300)

    def test_stale_clock_holds_authoritative_position(self):
        estimator = MediaClockEstimator()
        estimator.observe(snapshot(), 0)
        self.assertEqual(estimator.position_at(1_500_000), 2500)
        self.assertEqual(estimator.position_at(1_500_001), 1000)
        self.assertFalse(estimator.is_fresh(1_500_001))


class MediaSessionCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.coordinator = MediaSessionCoordinator("wizard-runtime-one")

    def test_dedup_stale_epoch_and_hard_generation_semantics(self):
        first = snapshot()
        accepted = self.coordinator.accept_with_result(first, 0)
        self.assertEqual(accepted.ack.disposition, "accepted")
        self.assertTrue(accepted.hard_reconcile)
        self.assertEqual(accepted.reconciliation_generation, 1)

        duplicate = self.coordinator.accept_with_result(first, 1)
        self.assertEqual(duplicate.ack.disposition, "duplicate")
        self.assertEqual(duplicate.reconciliation_generation, 1)

        heartbeat = snapshot(sequence=5, cause="heartbeat", position_ms=1100)
        ordinary = self.coordinator.accept_with_result(heartbeat, 100_000)
        self.assertFalse(ordinary.hard_reconcile)

        stale_sequence = self.coordinator.accept_with_result(snapshot(sequence=4), 100_001)
        self.assertEqual(stale_sequence.ack.disposition, "stale")
        self.assertEqual(stale_sequence.ack.error_code, "stale_sequence")

        seek = snapshot(sequence=6, media_epoch=1, cause="seeked", position_ms=7000)
        reconciled = self.coordinator.accept_with_result(seek, 110_000)
        self.assertTrue(reconciled.hard_reconcile)
        self.assertEqual(reconciled.reconciliation_generation, 2)

        old_epoch = snapshot(sequence=7, media_epoch=0, cause="heartbeat")
        stale_epoch = self.coordinator.accept_with_result(old_epoch, 120_000)
        self.assertEqual(stale_epoch.ack.error_code, "stale_media_epoch")

    def test_runtime_epoch_change_requires_full_reconnect(self):
        self.coordinator.accept(snapshot(), 0)
        self.coordinator.rotate_runtime_epoch("wizard-runtime-two")
        refused = self.coordinator.accept(snapshot(sequence=1, cause="heartbeat"), 10)
        self.assertEqual(refused.disposition, "resync_required")
        reconnected = self.coordinator.accept_with_result(snapshot(sequence=2, cause="reconnect"), 20)
        self.assertEqual(reconnected.ack.wizard_runtime_epoch, "wizard-runtime-two")
        self.assertTrue(reconnected.hard_reconcile)

    def test_runtime_reconnect_must_describe_the_active_source(self):
        self.coordinator.accept(snapshot(), 0)
        self.coordinator.accept(snapshot(sequence=1, source_slot="speech", kind="tts"), 10)
        self.coordinator.rotate_runtime_epoch("wizard-runtime-two")
        wrong_source = self.coordinator.accept(snapshot(sequence=2, cause="reconnect"), 20)
        self.assertEqual(wrong_source.disposition, "resync_required")
        self.assertEqual(wrong_source.error_code, "active_source_required")
        right_source = self.coordinator.accept(
            snapshot(sequence=3, cause="reconnect", source_slot="speech", kind="tts"), 30
        )
        self.assertEqual(right_source.disposition, "accepted")

    def test_expired_controller_takeover_resets_sequence_space(self):
        self.coordinator.accept(snapshot(sequence=8), 0)
        # Every V1 message is a complete state snapshot. A reloaded browser may
        # coalesce mount behind a newer lifecycle event, so takeover after the
        # old lease expires cannot depend on a particular event label.
        value = snapshot_mapping(sequence=0, cause="heartbeat")
        value["connector_session_id"] = "00000000-0000-4000-8000-000000000022"
        takeover = self.coordinator.accept(
            MediaSessionSnapshotV1.from_mapping(value),
            5_000_001,
        )
        self.assertEqual(takeover.disposition, "accepted")
        self.assertEqual(takeover.connector_session_id, "00000000-0000-4000-8000-000000000022")

    def test_tts_preempts_main_and_terminal_tts_restores_main(self):
        main = self.coordinator.accept_with_result(snapshot(position_ms=1000), 0)
        self.assertEqual(main.snapshot.media.source_slot, "main")

        tts = self.coordinator.accept_with_result(
            snapshot(
                sequence=1,
                cause="play",
                source_slot="speech",
                kind="tts",
                position_ms=100,
            ),
            10_000,
        )
        self.assertEqual(tts.snapshot.media.source_slot, "speech")
        self.assertTrue(tts.hard_reconcile)
        tts_generation = tts.reconciliation_generation

        restored = self.coordinator.accept_with_result(
            snapshot(
                sequence=2,
                cause="ended",
                state="ended",
                source_slot="speech",
                kind="tts",
                position_ms=500,
            ),
            30_000,
        )
        self.assertTrue(restored.hard_reconcile)
        self.assertEqual(restored.snapshot.media.source_slot, "main")
        self.assertEqual(restored.snapshot.playback.position_ms, 1000)
        self.assertEqual(restored.reconciliation_generation, tts_generation + 1)

    def test_main_full_state_snapshot_reclaims_ownership_after_speech(self):
        self.coordinator.accept(snapshot(position_ms=1000), 0)
        self.coordinator.accept(
            snapshot(
                sequence=1,
                cause="playing",
                source_slot="speech",
                kind="tts",
                position_ms=0,
            ),
            10_000,
        )

        restored = self.coordinator.accept_with_result(
            snapshot(sequence=2, cause="trackchange", state="paused", position_ms=0),
            20_000,
        )

        self.assertEqual(restored.ack.disposition, "accepted")
        self.assertTrue(restored.hard_reconcile)
        self.assertEqual(restored.snapshot.media.source_slot, "main")

        playing = self.coordinator.accept_with_result(
            snapshot(sequence=3, cause="playing", position_ms=1400),
            30_000,
        )
        self.assertEqual(playing.snapshot.media.source_slot, "main")
        self.assertEqual(playing.snapshot.playback.position_ms, 1400)

    def test_paused_tts_restores_latest_main_immediately(self):
        self.coordinator.accept(snapshot(position_ms=1000), 0)
        self.coordinator.accept(
            snapshot(
                sequence=1,
                cause="playing",
                source_slot="speech",
                kind="tts",
                position_ms=100,
            ),
            10_000,
        )
        restored = self.coordinator.accept_with_result(
            snapshot(
                sequence=2,
                cause="pause",
                state="paused",
                source_slot="speech",
                kind="tts",
                position_ms=500,
            ),
            30_000,
        )

        self.assertEqual(restored.ack.disposition, "accepted")
        self.assertTrue(restored.hard_reconcile)
        self.assertEqual(restored.snapshot.media.source_slot, "main")
        self.assertEqual(restored.snapshot.playback.position_ms, 1000)

    def test_loading_tts_does_not_preempt_main(self):
        self.coordinator.accept(snapshot(media_epoch=3, position_ms=1000), 0)
        loading = self.coordinator.accept_with_result(
            snapshot(
                sequence=1,
                media_epoch=4,
                cause="play",
                state="loading",
                source_slot="speech",
                kind="tts",
                position_ms=0,
            ),
            10_000,
        )

        self.assertEqual(loading.ack.disposition, "accepted")
        self.assertEqual(loading.ack.accepted_sequence, 1)
        self.assertEqual(loading.ack.accepted_media_epoch, 4)
        self.assertEqual(self.coordinator.accepted_snapshot.media.source_slot, "main")
        self.assertEqual(self.coordinator.accepted_snapshot.media_epoch, 3)
        self.assertIsNone(loading.snapshot)

    def test_stale_tts_terminal_cannot_restore_main(self):
        self.coordinator.accept(snapshot(sequence=0), 0)
        self.coordinator.accept(snapshot(sequence=5, source_slot="speech", kind="tts"), 10)
        stale_end = self.coordinator.accept_with_result(
            snapshot(sequence=4, cause="ended", state="ended", source_slot="speech", kind="tts"), 20
        )
        self.assertEqual(stale_end.ack.disposition, "stale")
        self.assertEqual(self.coordinator.accepted_snapshot.media.source_slot, "speech")

    def test_diagnostics_are_sanitized(self):
        self.coordinator.accept(snapshot(), 0)
        rendered = json.dumps(self.coordinator.diagnostics(1000).to_dict(), sort_keys=True)
        self.assertIn('"active_source_slot": "main"', rendered)
        self.assertNotIn("00000000-0000-4000-8000-000000000002", rendered)
        self.assertNotIn("media:sha256:" + "1" * 64, rendered)
        self.assertNotIn("transcript", rendered)
        self.assertNotIn("audio_bytes", rendered)


if __name__ == "__main__":
    unittest.main()
