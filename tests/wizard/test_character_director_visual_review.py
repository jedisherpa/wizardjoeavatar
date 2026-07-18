import asyncio
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

from tools.run_character_director_visual_review import (
    CaptureIntegrity,
    EvidenceFailure,
    FrameGapError,
    ManifestValidationError,
    QueueOverflowError,
    QueueStats,
    StrictFrameDecoder,
    enqueue_decoded_frame,
    parse_init,
    runtime_urls,
    select_atomic_animation_trace,
    square_cell_image,
    validate_manifest,
    validate_scenarios,
)
from wizard_avatar.protocol import TAG_RAW


class InitParsingTests(unittest.TestCase):
    def test_parses_baseline_and_extended_init(self):
        baseline = parse_init("INIT:24:5:240:135:0:0:0.000")
        self.assertEqual(baseline.fps, 24.0)
        self.assertEqual((baseline.cols, baseline.rows), (240, 135))
        self.assertEqual(baseline.cell_bytes, 4)
        self.assertEqual(baseline.expected_decoded_length, 240 * 135 * 4)

        extended = parse_init(
            "INIT:24.0:5:80:45:0:7:1.250:EPOCH:runtime-a:CELL_BYTES:4:CODEC:1"
        )
        self.assertEqual(extended.extras["EPOCH"], "runtime-a")
        self.assertEqual(extended.source_index, 7)
        self.assertEqual(extended.duration_seconds, 1.25)

    def test_rejects_malformed_or_incompatible_init(self):
        for value in (
            "hello",
            "INIT:0:5:240:135:0:0:0.000",
            "INIT:24:4:240:135:0:0:0.000",
            "INIT:24:5:0:135:0:0:0.000",
            "INIT:24:5:240:135:0:0:0.000:CELL_BYTES:3",
            "INIT:24:5:240:135:0:0:0.000:EPOCH",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_init(value)


class ScenarioSchemaTests(unittest.TestCase):
    def test_accepts_strict_unique_scenarios(self):
        scenarios = validate_scenarios(
            [
                {
                    "name": "front-idle",
                    "kind": "reset",
                    "payload": {},
                    "settle_seconds": 0.1,
                    "capture_seconds": 0.2,
                },
                {
                    "name": "gaze-left",
                    "kind": "gaze",
                    "payload": {"target": "left"},
                    "settle_seconds": 0.0,
                    "capture_seconds": 0.2,
                },
            ]
        )
        self.assertEqual([scenario.name for scenario in scenarios], ["front-idle", "gaze-left"])
        self.assertEqual(scenarios[1].payload, {"target": "left"})

    def test_rejects_unknown_fields_duplicate_names_and_empty_capture(self):
        base = {
            "name": "idle",
            "kind": "reset",
            "payload": {},
            "settle_seconds": 0.0,
            "capture_seconds": 0.2,
        }
        invalid = (
            [{**base, "extra": True}],
            [base, dict(base)],
            [{**base, "capture_seconds": 0.0}],
            [{**base, "name": "not valid"}],
            [{**base, "payload": {1: "non-string-key"}}],
            [{**base, "payload": {"tuple": (1, 2)}}],
        )
        for scenarios in invalid:
            with self.subTest(scenarios=scenarios):
                with self.assertRaises(ValueError):
                    validate_scenarios(scenarios)

    def test_protected_legacy_port_is_never_a_capture_target(self):
        with self.assertRaisesRegex(ValueError, "never contact protected port 8765"):
            runtime_urls("http://127.0.0.1:8765")

    def test_runtime_urls_include_atomic_animation_trace_endpoint(self):
        urls = runtime_urls("http://127.0.0.1:8875")
        self.assertEqual(len(urls), 4)
        self.assertEqual(
            urls[-1],
            "http://127.0.0.1:8875/api/avatar/wizard/animation-trace",
        )

    def test_atomic_trace_selection_requires_exact_frame_hash_and_codec(self):
        digest = "a" * 64
        frames = [{"frame_index": 12, "sha256": digest, "codec_tag": 2}]
        payload = {
            "schema": "animation_truth_trace_v1",
            "records": [
                {
                    "frame_index": 12,
                    "frame_sha256": digest,
                    "codec_tag": 2,
                    "simulation_tick": 30,
                }
            ],
        }

        selected = select_atomic_animation_trace(payload, frames)
        self.assertEqual(selected[0]["simulation_tick"], 30)

        payload["records"][0]["frame_sha256"] = "b" * 64
        with self.assertRaisesRegex(EvidenceFailure, "hash mismatch"):
            select_atomic_animation_trace(payload, frames)

    def test_square_cell_renderer_uses_rgb_even_for_space_glyphs(self):
        image = square_cell_image(b"\x20\x0a\x14\x1e", 1, 1, 3)
        self.assertEqual(image.size, (3, 3))
        self.assertEqual(set(image.getdata()), {(10, 20, 30)})


class StrictCaptureTests(unittest.IsolatedAsyncioTestCase):
    async def test_queue_overflow_is_terminal_and_never_drops_silently(self):
        queue = asyncio.Queue(maxsize=1)
        stats = QueueStats(capacity=1)
        integrity = CaptureIntegrity()

        enqueue_decoded_frame(queue, object(), stats, integrity)
        with self.assertRaises(QueueOverflowError):
            enqueue_decoded_frame(queue, object(), stats, integrity)

        self.assertFalse(integrity.valid)
        self.assertEqual(integrity.failure_reason, "decoded frame queue overflow")
        self.assertEqual(stats.high_water_mark, 1)
        self.assertEqual(stats.overrun_count, 1)
        self.assertEqual(queue.qsize(), 1)

    async def test_index_gap_invalidates_decoder_without_recovery(self):
        integrity = CaptureIntegrity()
        decoder = StrictFrameDecoder(expected_length=8, integrity=integrity)
        first = struct.pack(">IB", 41, TAG_RAW) + b"abcdefgh"
        gap = struct.pack(">IB", 43, TAG_RAW) + b"ABCDEFGH"

        self.assertEqual(decoder.decode(first), (41, b"abcdefgh"))
        with self.assertRaises(FrameGapError):
            decoder.decode(gap)

        self.assertFalse(integrity.valid)
        self.assertEqual(
            integrity.decoded_gaps,
            [{"previous_frame_index": 41, "expected_frame_index": 42, "actual_frame_index": 43}],
        )
        self.assertIn("frame index gap", integrity.failure_reason)
        self.assertEqual(decoder.previous_frame, b"abcdefgh")


class ManifestValidationTests(unittest.TestCase):
    def valid_manifest(self):
        digest = "a" * 64
        return {
            "schema_version": 1,
            "evidence_kind": "external_real_runtime_visual_review",
            "valid": True,
            "failure_reason": None,
            "replay_exported": False,
            "frame_state_pairing": "atomic_animation_truth_trace_v1",
            "provenance": {
                "head": digest,
                "branch": "codex/character-director",
                "worktree_clean": True,
                "status_sha256": digest,
                "tracked_diff_sha256": digest,
                "status_lines": [],
            },
            "init": {
                "fps": 24.0,
                "cols": 1,
                "rows": 2,
                "cell_bytes": 4,
                "expected_decoded_length": 8,
            },
            "timings": {
                "started_at_utc": "2026-07-18T00:00:00Z",
                "ended_at_utc": "2026-07-18T00:00:01Z",
                "duration_seconds": 1.0,
            },
            "capture": {
                "frame_count": 2,
                "first_frame_index": 10,
                "last_frame_index": 11,
            },
            "queue": {"capacity": 2, "high_water_mark": 1, "overrun_count": 0},
            "decoded_gaps": [],
            "decoder_errors": [],
            "dropped_frames": 0,
            "scenarios": [
                {
                    "name": "idle",
                    "kind": "reset",
                    "payload": {},
                    "settle_seconds": 0.0,
                    "capture_seconds": 0.2,
                }
            ],
            "scenario_ranges": [
                {
                    "name": "idle",
                    "first_frame_index": 10,
                    "last_frame_index": 11,
                    "frame_count": 2,
                }
            ],
            "commands": [
                {
                    "scenario": "idle",
                    "command_id": "visual-review-0001-idle",
                    "source_sequence": 1,
                    "ack": {"disposition": "applied"},
                    "response_state": {},
                    "state_snapshot": {},
                }
            ],
            "frames": [
                {
                    "frame_index": 10,
                    "sha256": digest,
                    "wire_sha256": digest,
                    "wire_offset": 0,
                    "wire_size": 8,
                    "codec_tag": 0,
                    "scenario": "idle",
                    "received_at_utc": "2026-07-18T00:00:00Z",
                    "elapsed_seconds": 0.1,
                },
                {
                    "frame_index": 11,
                    "sha256": digest,
                    "wire_sha256": digest,
                    "wire_offset": 8,
                    "wire_size": 8,
                    "codec_tag": 0,
                    "scenario": "idle",
                    "received_at_utc": "2026-07-18T00:00:00Z",
                    "elapsed_seconds": 0.2,
                },
            ],
            "animation_truth_trace": {
                "schema": "animation_truth_trace_v1",
                "record_count": 2,
                "first_frame_index": 10,
                "last_frame_index": 11,
                "path": "animation_truth_trace.ndjson",
            },
            "contact_verification": {
                "schema": "contact_verification_report_v1",
                "schema_version": 1,
                "passed": True,
                "path": "contact_verification.json",
            },
            "artifacts": [
                {"path": "samples/idle.png", "sha256": digest, "bytes": 123},
                {
                    "path": "animation_truth_trace.ndjson",
                    "sha256": digest,
                    "bytes": 456,
                },
                {
                    "path": "contact_verification.json",
                    "sha256": digest,
                    "bytes": 456,
                },
            ],
            "video": {"available": False, "path": None, "codec": None},
            "rendering": {"cell_shape": "square", "pixel_format": "rgb24"},
        }

    def test_validates_complete_manifest_and_rejects_false_validity(self):
        manifest = self.valid_manifest()
        validate_manifest(manifest)

        for mutate in (
            lambda value: value.update(dropped_frames=1),
            lambda value: value["decoded_gaps"].append({"expected_frame_index": 11}),
            lambda value: value["queue"].update(overrun_count=1),
            lambda value: value["frames"][1].update(frame_index=12),
            lambda value: value.update(frame_state_pairing="atomic"),
        ):
            invalid = self.valid_manifest()
            mutate(invalid)
            with self.subTest(invalid=invalid):
                with self.assertRaises(ManifestValidationError):
                    validate_manifest(invalid)

    def test_verifies_artifact_bytes_and_hashes_when_output_dir_is_supplied(self):
        manifest = self.valid_manifest()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "samples" / "idle.png"
            artifact.parent.mkdir()
            artifact.write_bytes(b"png-evidence")
            manifest["artifacts"][0].update(
                bytes=artifact.stat().st_size,
                sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
            )
            trace = root / "animation_truth_trace.ndjson"
            trace.write_bytes(b'{"frame_index":10}\n')
            manifest["artifacts"][1].update(
                bytes=trace.stat().st_size,
                sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
            )
            contact = root / "contact_verification.json"
            contact.write_bytes(b'{"passed":true}\n')
            manifest["artifacts"][2].update(
                bytes=contact.stat().st_size,
                sha256=hashlib.sha256(contact.read_bytes()).hexdigest(),
            )
            validate_manifest(manifest, root)

            artifact.write_bytes(b"tampered")
            with self.assertRaises(ManifestValidationError):
                validate_manifest(manifest, root)


if __name__ == "__main__":
    unittest.main()
