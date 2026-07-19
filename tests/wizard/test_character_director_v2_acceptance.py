import copy
import unittest

from tools.analyze_character_director_v2 import analyze_v2


SCENARIOS = (
    ("speech-steady-center", 84, 0),
    ("speech-gaze-left", 72, -1),
    ("speech-return-center-one", 96, 0),
    ("speech-gaze-right", 72, 1),
    ("speech-return-center-two", 156, 0),
)
MOUTHS = ("closed", "open_small", "open_medium", "open_wide", "rounded")


def evidence():
    frames = []
    trace = []
    frame_index = 1000
    global_offset = 0
    blink_offsets = {100, 101, 102, 103, 302, 303, 304, 305}
    for scenario, count, gaze in SCENARIOS:
        for _ in range(count):
            mouth = MOUTHS[global_offset % len(MOUTHS)]
            blink_closed = global_offset in blink_offsets
            mouth_digest = "{:064x}".format(MOUTHS.index(mouth) + 1)
            frames.append(
                {
                    "frame_index": frame_index,
                    "scenario": scenario,
                    "capture_owned": True,
                }
            )
            trace.append(
                {
                    "frame_index": frame_index,
                    "frame_sha256": "{:064x}".format(frame_index),
                    "world_root_x": 0.0,
                    "world_root_z": 5.0,
                    "animation_root_policy": "fixed",
                    "support_contact": "both_feet",
                    "presentation_channels": {
                        "action": "speaking" if global_offset % 2 else "explaining",
                        "locomotion": "idle",
                        "speech_mouth_authority": "media_alignment",
                        "rendered_mouth_shape": mouth,
                        "gaze_aim": gaze,
                        "gaze_authoritative": True,
                        "blink_closed": blink_closed,
                        "blink_painted_cells": 8 if blink_closed else 0,
                        "body_pixel_sha256": "a" * 64,
                        "mouth_pixel_sha256": mouth_digest,
                        "mouth_painted_cells": 5,
                        "eye_apertures": [
                            {"min_x": 10, "max_x": 14, "min_y": 10, "max_y": 12},
                            {"min_x": 20, "max_x": 24, "min_y": 10, "max_y": 12},
                        ],
                        "eye_blue_cells": [] if blink_closed else [
                            {"x": 12 + gaze, "y": 11},
                            {"x": 22 + gaze, "y": 11},
                        ],
                    },
                }
            )
            frame_index += 1
            global_offset += 1
    manifest = {
        "source_epoch": "capture:test-v2",
        "provenance": {"head": "a" * 40},
        "runtime_binding": {"start": {"runtime_epoch": "runtime:test-v2"}},
        "scenario_program": {
            "program_id": "v2-governed-speech",
            "acceptance_scenario": "V2",
            "total_duration_seconds": 20.0,
        },
        "scenarios": [{"name": item[0]} for item in SCENARIOS],
        "frames": frames,
        "init": {"fps": 24.0},
        "contact_verification": {
            "passed": True,
            "maximum_planted_drift_cells": 0.0,
        },
    }
    receipt = {
        "schema": "character_director_prism_governed_speech_v1",
        "audio_artifact": {
            "path": "governed-speech-audio.mp3",
            "media_type": "audio/mpeg",
            "bytes": 4096,
            "sha256": "d" * 64,
        },
        "atomic_capture": {
            "exit_code": 0,
            "manifest_sha256": "e" * 64,
            "source_epoch": "capture:test-v2",
            "candidate_commit": "a" * 40,
            "runtime_epoch": "runtime:test-v2",
        },
        "capture_edge": {
            "browser": {
                "durationMs": 40_000,
                "currentTimeMs": 100,
                "paused": False,
            },
            "wizard_media": {
                "application": {
                    "active": True,
                    "source_slot": "speech",
                    "media_time_ms": 120,
                },
                "governed_speech": {
                    "active": True,
                    "status": "release_active",
                },
                "session": {"media_hash_prefix": "sha256:dddddddd"},
            },
            "wizard_state": {
                "speech_id": "speech:test-v2",
                "speech_mouth_authority": "media_alignment",
            },
        },
        "av_timeline": {
            "schema": "character_director_av_timeline_v1",
            "schema_version": 1,
            "sample_interval_target_ms": 100,
            "samples": [
                {
                    "observed_at_utc": "2026-07-19T00:00:00Z",
                    "elapsed_ms": index * 100,
                    "browser_media_time_ms": 100 + index * 100,
                    "wizard_media_time_ms": 120 + index * 100,
                    "absolute_offset_ms": 20,
                    "browser_playing": True,
                    "application_active": True,
                    "application_source_slot": "speech",
                    "speech_id": "speech:test-v2",
                    "speech_mouth_authority": "media_alignment",
                    "media_hash_prefix": "sha256:dddddddd",
                }
                for index in range(201)
            ],
        },
    }
    return manifest, trace, receipt


def analyze(manifest, trace, receipt):
    return analyze_v2(manifest, trace, receipt, manifest_sha256="e" * 64)


class CharacterDirectorV2AcceptanceTests(unittest.TestCase):
    def test_complete_governed_speech_evidence_passes(self):
        manifest, trace, receipt = evidence()
        report = analyze(manifest, trace, receipt)
        self.assertTrue(report["passed"])
        self.assertTrue(all(check["passed"] for check in report["checks"]))
        self.assertEqual(report["metrics"]["body_still_percentage"], 100.0)
        self.assertEqual(report["metrics"]["av_edge_offset_ms"], 20)

    def test_wrong_authority_and_excessive_av_offset_fail(self):
        manifest, trace, receipt = evidence()
        invalid_trace = copy.deepcopy(trace)
        invalid_receipt = copy.deepcopy(receipt)
        invalid_trace[0]["presentation_channels"]["speech_mouth_authority"] = "local_fallback"
        invalid_receipt["capture_edge"]["wizard_media"]["application"]["media_time_ms"] = 900
        for sample in invalid_receipt["av_timeline"]["samples"]:
            sample["wizard_media_time_ms"] = sample["browser_media_time_ms"] + 800
            sample["absolute_offset_ms"] = 800
        report = analyze(manifest, invalid_trace, invalid_receipt)
        failed = {check["name"] for check in report["checks"] if not check["passed"]}
        self.assertFalse(report["passed"])
        self.assertIn("governed_aligned_speech_authority", failed)
        self.assertIn("browser_wizard_av_timeline_alignment", failed)

    def test_blink_punctuation_without_mouth_independence_fails(self):
        manifest, trace, receipt = evidence()
        invalid_trace = copy.deepcopy(trace)
        for item in invalid_trace:
            channels = item["presentation_channels"]
            if channels["blink_closed"]:
                channels["rendered_mouth_shape"] = "closed"
        report = analyze(manifest, invalid_trace, receipt)
        failed = {check["name"] for check in report["checks"] if not check["passed"]}
        self.assertFalse(report["passed"])
        self.assertIn("mouth_blink_independence", failed)

    def test_pose_popping_fails_body_pixel_stillness(self):
        manifest, trace, receipt = evidence()
        invalid_trace = copy.deepcopy(trace)
        for index, item in enumerate(invalid_trace):
            item["presentation_channels"]["body_pixel_sha256"] = (
                "a" * 64 if (index // 24) % 2 == 0 else "b" * 64
            )
        report = analyze(manifest, invalid_trace, receipt)
        failed = {check["name"] for check in report["checks"] if not check["passed"]}
        self.assertFalse(report["passed"])
        self.assertIn("purposeful_planted_body_stillness", failed)

    def test_static_mouth_pixels_fail_visible_lip_sync(self):
        manifest, trace, receipt = evidence()
        invalid_trace = copy.deepcopy(trace)
        for item in invalid_trace:
            item["presentation_channels"]["mouth_pixel_sha256"] = "c" * 64
        report = analyze(manifest, invalid_trace, receipt)
        failed = {check["name"] for check in report["checks"] if not check["passed"]}
        self.assertFalse(report["passed"])
        self.assertIn("visible_mouth_pixel_animation", failed)

    def test_missing_or_static_blue_eye_pixels_fail_visible_gaze(self):
        manifest, trace, receipt = evidence()
        invalid_trace = copy.deepcopy(trace)
        for item in invalid_trace:
            if not item["presentation_channels"]["blink_closed"]:
                item["presentation_channels"]["eye_blue_cells"] = []
        report = analyze(manifest, invalid_trace, receipt)
        failed = {check["name"] for check in report["checks"] if not check["passed"]}
        self.assertFalse(report["passed"])
        self.assertIn("left_center_right_gaze_returns", failed)

    def test_unrelated_receipt_fails_capture_binding(self):
        manifest, trace, receipt = evidence()
        unrelated = copy.deepcopy(receipt)
        unrelated["atomic_capture"]["source_epoch"] = "capture:other"
        unrelated["atomic_capture"]["candidate_commit"] = "b" * 40
        report = analyze(manifest, trace, unrelated)
        failed = {check["name"] for check in report["checks"] if not check["passed"]}
        self.assertFalse(report["passed"])
        self.assertIn("receipt_manifest_runtime_binding", failed)

    def test_short_or_wrong_media_timeline_fails(self):
        manifest, trace, receipt = evidence()
        invalid = copy.deepcopy(receipt)
        invalid["av_timeline"]["samples"] = invalid["av_timeline"]["samples"][:20]
        for sample in invalid["av_timeline"]["samples"]:
            sample["media_hash_prefix"] = "sha256:ffffffff"
        report = analyze(manifest, trace, invalid)
        failed = {check["name"] for check in report["checks"] if not check["passed"]}
        self.assertFalse(report["passed"])
        self.assertIn("browser_wizard_av_timeline_alignment", failed)


if __name__ == "__main__":
    unittest.main()
