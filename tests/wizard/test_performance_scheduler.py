import copy
import json
import random
import unittest

from wizard_avatar.media_session import MediaSessionCoordinator, MediaSessionSnapshotV1
from wizard_avatar.performance_scheduler import (
    AccessibilityMotionProfile,
    PerformanceScheduler,
    SchedulerState,
)
from wizard_avatar.performance_score import CompiledScoreLoader

from tests.wizard.test_performance_score import digest, score_document


def runtime_score(
    compiled_id="compiled:book",
    media_id="media:sha256:" + "1" * 64,
    media_hash=None,
    cue_prefix="",
):
    document = copy.deepcopy(score_document())
    document["compiled_score_id"] = compiled_id
    document["media"]["media_id"] = media_id
    document["media"]["media_sha256"] = media_hash or digest("1")
    for track in document["tracks"]:
        for cue in track["cues"]:
            cue["cue_id"] = cue_prefix + cue["cue_id"]
    document["tracks"].extend(
        [
            {
                "track_id": "movement",
                "kind": "locomotion",
                "exclusive": True,
                "max_active": 1,
                "gap_policy": "clear",
                "cues": [
                    {
                        "cue_id": cue_prefix + "move.center-right",
                        "start_ms": 0,
                        "end_ms": 4000,
                        "intent": "travel",
                        "priority": 25,
                        "owned_channels": ["locomotion", "stage"],
                        "phase_ranges": {},
                        "trajectory": {
                            "source_position_milli": [0, 0],
                            "destination_position_milli": [1000, 0],
                            "easing_id": "linear_v1",
                        },
                        "facing": "south",
                    }
                ],
            },
            {
                "track_id": "speech",
                "kind": "speech",
                "exclusive": True,
                "max_active": 1,
                "gap_policy": "clear",
                "cues": [
                    {
                        "cue_id": cue_prefix + "speech.line",
                        "start_ms": 500,
                        "end_ms": 3500,
                        "intent": "speaking",
                        "priority": 50,
                        "owned_channels": ["speech", "mouth"],
                        "phase_ranges": {},
                        "mouth_shape": "open",
                        "speaking": True,
                    }
                ],
            },
            {
                "track_id": "dance",
                "kind": "dance",
                "exclusive": False,
                "max_active": 1,
                "gap_policy": "clear",
                "cues": [
                    {
                        "cue_id": cue_prefix + "dance.accent",
                        "start_ms": 1500,
                        "end_ms": 2200,
                        "intent": "beat_accent",
                        "priority": 5,
                        "owned_channels": ["dance"],
                        "phase_ranges": {},
                    }
                ],
            },
        ]
    )
    return CompiledScoreLoader(contract_validator=lambda _name, _value: None).from_mapping(document)


def bound_snapshot(
    score,
    sequence=0,
    epoch=0,
    cause="initial",
    state="playing",
    position=1000,
    rate=1000,
    source_slot="main",
    kind="audiobook",
    motion_profile="full",
    mode=None,
    with_score=True,
):
    mode = mode or ("speech" if kind in {"speech", "tts"} else ("music" if kind == "music" else "narrative"))
    return MediaSessionSnapshotV1.from_mapping(
        {
            "schema_version": 1,
            "message_id": "00000000-0000-4000-8000-{:012x}".format(sequence + 100),
            "connector_session_id": "00000000-0000-4000-8000-000000000032",
            "sequence": sequence,
            "media_epoch": epoch,
            "cause": cause,
            "sampled_at_monotonic_ms": sequence,
            "media": {
                "media_id": score.media_id,
                "media_sha256": score.media_sha256 if with_score else None,
                "kind": kind,
                "source_slot": source_slot,
                "source_kind": "tts" if kind == "tts" else ("speech" if kind == "speech" else "studio_chapter"),
                "book_id": "book:one" if source_slot == "main" else None,
                "chapter_id": "chapter:one" if source_slot == "main" else None,
                "duration_ms": score.duration_ms,
            },
            "playback": {
                "state": state,
                "position_ms": position,
                "rate_milli": rate,
                "ready_state": 4,
                "seeking": state == "seeking",
            },
            "performance": {
                "mode": mode,
                "score_id": score.compiled_score_id if with_score else None,
                "score_revision": 1 if with_score else None,
                "score_sha256": score.artifact_sha256 if with_score else None,
                "character_id": score.character_id,
                "character_package_sha256": score.package_digest if with_score else None,
                "intensity_milli": 700,
                "motion_profile": motion_profile,
                "disabled_channels": [],
            },
        }
    )


class PureSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.score = runtime_score()

    def test_linear_and_cold_seek_are_identical_at_random_times(self):
        scheduler = PerformanceScheduler(self.score)
        cold = PerformanceScheduler(self.score)
        generator = random.Random(93751)
        for media_time in [0, 999, 1000, 1200, 1400, 2999, 3000, 3999] + [
            generator.randrange(0, 4000) for _ in range(1000)
        ]:
            linear_state = scheduler.evaluate(media_time)
            cold_state = cold.state_at_media_time(media_time)
            self.assertEqual(linear_state.resolution_hash, cold_state.resolution_hash)
            self.assertEqual(linear_state.score_cue_ids, cold_state.score_cue_ids)
            self.assertEqual(linear_state.world_position_milli, cold_state.world_position_milli)

    def test_rate_is_absent_from_state_at_media_time(self):
        scheduler = PerformanceScheduler(self.score)
        at_time = scheduler.evaluate(1750)
        for _rate in (500, 750, 1000, 1250, 1500, 2000):
            self.assertEqual(scheduler.evaluate(1750).resolution_hash, at_time.resolution_hash)
        self.assertEqual(at_time.clip_elapsed_ticks, 45)

    def test_fixed_point_trajectory_and_phrase_boundaries(self):
        scheduler = PerformanceScheduler(self.score)
        self.assertEqual(scheduler.evaluate(2000).world_position_milli, (500, 0))
        self.assertEqual(scheduler.evaluate(1199).cue_phases["body.explain"], "anticipation")
        self.assertEqual(scheduler.evaluate(1200).cue_phases["body.explain"], "stroke")
        self.assertNotIn("body.neutral", scheduler.evaluate(1000).score_cue_ids)

    def test_reduced_and_still_projection_preserve_speech_without_motion(self):
        scheduler = PerformanceScheduler(self.score)
        full = scheduler.evaluate(1800, motion_profile="full")
        reduced = scheduler.evaluate(1800, motion_profile="reduced")
        still = scheduler.evaluate(1800, motion_profile="still")

        self.assertIn("locomotion", full.owned_channels)
        self.assertIn("dance", full.owned_channels)
        self.assertNotIn("locomotion", reduced.owned_channels)
        self.assertNotIn("dance", reduced.owned_channels)
        self.assertNotIn("body", reduced.owned_channels)
        self.assertNotIn("gesture", reduced.owned_channels)
        self.assertNotIn("effects", reduced.owned_channels)
        self.assertEqual(reduced.world_position_milli, (0, 0))
        self.assertTrue(reduced.speaking)
        self.assertEqual(still.body_mapping_id, "body.characterful_neutral")
        self.assertEqual(still.world_position_milli, (0, 0))
        self.assertTrue(still.speaking)
        self.assertTrue(all(channel in {"speech", "mouth", "face", "eyes", "gaze", "blink"} for channel in still.owned_channels))

    def test_disabled_channel_is_suppressed_with_reason(self):
        scheduler = PerformanceScheduler(self.score)
        state = scheduler.evaluate(1800, disabled_channels=("mouth",))
        self.assertNotIn("mouth", state.owned_channels)
        self.assertEqual(state.mouth_shape, "rest")
        self.assertTrue(state.speaking)
        self.assertTrue(any(record.reason_code == "channel_disabled" for record in state.suppressed_requests))


class SnapshotSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.main_score = runtime_score()
        self.coordinator = MediaSessionCoordinator("wizard-scheduler-runtime")
        self.scheduler = PerformanceScheduler(self.main_score, coordinator=self.coordinator)

    def test_pause_rate_seek_and_reconnect_are_state_equivalent(self):
        first = bound_snapshot(self.main_score, rate=1500)
        self.scheduler.accept_snapshot(first, 0)
        advanced = self.scheduler.current_state(500_000)
        self.assertEqual(advanced.resolution_hash, self.scheduler.evaluate(1750, intensity_milli=700).resolution_hash)

        paused = bound_snapshot(
            self.main_score,
            sequence=1,
            cause="pause",
            state="paused",
            position=1750,
            rate=1500,
        )
        self.scheduler.accept_snapshot(paused, 500_000)
        self.assertEqual(self.scheduler.current_state(1_400_000).resolution_hash, advanced.resolution_hash)

        seeked = bound_snapshot(
            self.main_score,
            sequence=2,
            epoch=1,
            cause="seeked",
            state="paused",
            position=2400,
            rate=1500,
        )
        self.scheduler.accept_snapshot(seeked, 1_500_000)
        sought = self.scheduler.current_state(1_500_000)
        self.assertEqual(sought.resolution_hash, self.scheduler.evaluate(2400, intensity_milli=700).resolution_hash)

        self.coordinator.rotate_runtime_epoch("wizard-scheduler-restarted")
        reconnect = bound_snapshot(
            self.main_score,
            sequence=3,
            epoch=1,
            cause="reconnect",
            state="paused",
            position=2400,
            rate=1500,
        )
        ack = self.scheduler.accept_snapshot(reconnect, 1_600_000)
        self.assertEqual(ack.disposition, "accepted")
        self.assertEqual(self.scheduler.current_state(1_600_000).resolution_hash, sought.resolution_hash)

    def test_stale_clock_holds_last_safe_state_and_launches_no_new_cue(self):
        self.scheduler.accept_snapshot(bound_snapshot(self.main_score, position=1000), 0)
        fresh = self.scheduler.current_state(1_000_000)
        uncertain = self.scheduler.current_state(1_500_001)
        self.assertEqual(uncertain.resolution_hash, fresh.resolution_hash)
        self.assertEqual(self.scheduler.scheduler_state, SchedulerState.CLOCK_UNCERTAIN)

    def test_tts_handoff_cold_restores_latest_main_without_stale_cues(self):
        tts_score = runtime_score(
            compiled_id="compiled:tts",
            media_id="media:sha256:" + "2" * 64,
            media_hash=digest("2"),
            cue_prefix="tts.",
        )
        scores = {
            self.main_score.compiled_score_id: self.main_score,
            tts_score.compiled_score_id: tts_score,
        }
        scheduler = PerformanceScheduler(
            self.main_score,
            coordinator=MediaSessionCoordinator("wizard-source-handoff"),
            score_resolver=lambda active: scores.get(active.performance.score_id),
        )
        scheduler.accept_snapshot(bound_snapshot(self.main_score, position=1000), 0)

        scheduler.accept_snapshot(
            bound_snapshot(
                tts_score,
                sequence=1,
                cause="play",
                position=800,
                source_slot="speech",
                kind="tts",
            ),
            10_000,
        )
        tts_state = scheduler.current_state(10_000)
        self.assertTrue(all(cue_id.startswith("tts.") for cue_id in tts_state.score_cue_ids))

        scheduler.accept_snapshot(
            bound_snapshot(self.main_score, sequence=2, cause="trackchange", state="paused", position=1600),
            20_000,
        )
        restored_main = scheduler.current_state(20_000)
        self.assertEqual(restored_main.resolution_hash, scheduler.evaluate(1600, intensity_milli=700).resolution_hash)
        self.assertFalse(any(cue_id.startswith("tts.") for cue_id in restored_main.score_cue_ids))

        scheduler.accept_snapshot(
            bound_snapshot(
                tts_score,
                sequence=3,
                cause="ended",
                state="ended",
                position=2000,
                source_slot="speech",
                kind="tts",
            ),
            30_000,
        )
        restored = scheduler.current_state(30_000)
        expected = scheduler.evaluate(1600, intensity_milli=700)
        self.assertEqual(restored.resolution_hash, expected.resolution_hash)
        self.assertFalse(any(cue_id.startswith("tts.") for cue_id in restored.score_cue_ids))
        self.assertEqual(scheduler.diagnostics(30_000).hard_reconcile_count, 3)

    def test_score_mismatch_degrades_neutral_without_private_diagnostics(self):
        wrong = bound_snapshot(self.main_score)
        value = dict(wrong.to_dict())
        value["performance"] = dict(value["performance"])
        value["performance"]["score_sha256"] = digest("0")
        ack = self.scheduler.accept_snapshot(MediaSessionSnapshotV1.from_mapping(value), 0)
        self.assertEqual(ack.scheduler_state, "error")
        self.assertEqual(ack.error_code, "score_mismatch")
        self.assertEqual(self.scheduler.current_state(10).score_cue_ids, ())
        rendered = json.dumps(self.scheduler.diagnostics(0).to_dict(), sort_keys=True)
        self.assertNotIn(self.main_score.package_digest, rendered)
        self.assertNotIn("transcript", rendered)
        self.assertNotIn("audio_bytes", rendered)

    def test_scoreless_narrative_and_speech_use_duration_only_live_fallback(self):
        scheduler = PerformanceScheduler(coordinator=MediaSessionCoordinator("wizard-scoreless-speech"))
        live = bound_snapshot(self.main_score, position=720, with_score=False, mode="narrative")
        ack = scheduler.accept_snapshot(live, 0)
        first = scheduler.current_state(0)
        cold = PerformanceScheduler(coordinator=MediaSessionCoordinator("wizard-scoreless-speech-cold"))
        cold.accept_snapshot(live, 0)
        second = cold.current_state(0)

        self.assertEqual(ack.scheduler_state, "scoreless")
        self.assertTrue(first.speaking)
        self.assertIn(first.mouth_shape, {"closed", "open", "wide"})
        self.assertEqual(first.body_mapping_id, "body.characterful_neutral")
        self.assertNotIn("gesture", first.owned_channels)
        self.assertEqual(first.resolution_hash, second.resolution_hash)
        rendered = json.dumps(first.to_dict(), sort_keys=True)
        for forbidden in ("text", "audio", "url", "path", "transcript"):
            self.assertNotIn(forbidden, rendered)

    def test_scoreless_music_groove_is_restrained_time_pure_and_not_neutral(self):
        scheduler = PerformanceScheduler(coordinator=MediaSessionCoordinator("wizard-scoreless-music"))
        live = bound_snapshot(self.main_score, position=1250, kind="music", mode="music", with_score=False)
        scheduler.accept_snapshot(live, 0)
        first = scheduler.current_state(0)
        same = scheduler.current_state(0)
        later = scheduler.current_state(500_000)

        self.assertTrue(first.body_mapping_id.startswith("body.music_groove_restrained."))
        self.assertEqual(first.resolution_hash, same.resolution_hash)
        self.assertNotEqual(first.resolution_hash, later.resolution_hash)
        self.assertFalse(first.speaking)

    def test_scoreless_tts_preempts_and_cold_restores_latest_main_without_replay(self):
        scheduler = PerformanceScheduler(coordinator=MediaSessionCoordinator("wizard-scoreless-handoff"))
        scheduler.accept_snapshot(
            bound_snapshot(self.main_score, position=600, with_score=False, mode="narrative"),
            0,
        )
        scheduler.accept_snapshot(
            bound_snapshot(
                self.main_score,
                sequence=1,
                source_slot="speech",
                kind="tts",
                position=240,
                with_score=False,
                mode="speech",
            ),
            10_000,
        )
        speech_state = scheduler.current_state(10_000)
        scheduler.accept_snapshot(
            bound_snapshot(self.main_score, sequence=2, position=1800, with_score=False, mode="narrative"),
            20_000,
        )
        restored_main = scheduler.current_state(20_000)
        self.assertEqual(restored_main.fallback_records[0]["mode"], "narrative")
        self.assertEqual(restored_main.media_time_ms, 1800)
        scheduler.accept_snapshot(
            bound_snapshot(
                self.main_score,
                sequence=3,
                source_slot="speech",
                kind="tts",
                cause="ended",
                state="ended",
                position=1000,
                with_score=False,
                mode="speech",
            ),
            30_000,
        )
        restored = scheduler.current_state(30_000)
        self.assertEqual(restored.media_time_ms, 1810)
        self.assertNotEqual(restored.resolution_hash, speech_state.resolution_hash)
        self.assertEqual(restored.fallback_records[0]["mode"], "narrative")


if __name__ == "__main__":
    unittest.main()
