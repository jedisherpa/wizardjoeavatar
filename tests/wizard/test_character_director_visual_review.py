import asyncio
import hashlib
import json
import struct
import tempfile
import unittest
import sys
from pathlib import Path
from unittest import mock

from tools.run_character_director_visual_review import (
    CaptureRecords,
    CaptureIntegrity,
    EvidenceFailure,
    FrameGapError,
    ManifestValidationError,
    QueueOverflowError,
    QueueStats,
    ScenarioClock,
    StrictFrameDecoder,
    build_review_bundle_manifest,
    collect_runtime_observations,
    enqueue_decoded_frame,
    load_scenario_program,
    parse_init,
    runtime_urls,
    run_visual_review,
    select_atomic_animation_trace,
    square_cell_image,
    validate_artifact_semantics,
    validate_manifest,
    validate_review_bundle_manifest,
    validate_runtime_binding,
    validate_scenarios,
)
from wizard_avatar.protocol import TAG_RAW
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.server import create_app


ROOT = Path(__file__).resolve().parents[2]


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

    def test_loads_versioned_bounded_scenario_program(self):
        program = load_scenario_program(
            ROOT / "tools" / "character_director_scenarios" / "v1-listening.json"
        )

        self.assertEqual(program.program_id, "v1-listening")
        self.assertEqual(program.acceptance_scenario, "V1")
        self.assertEqual(len(program.scenarios), 5)
        self.assertEqual(program.total_duration_seconds, 12.0)
        self.assertRegex(program.source_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(program.to_manifest()["artifact_path"], "scenario-program.json")

    def test_rejects_unversioned_or_unbounded_scenario_program(self):
        valid = json.loads(
            (
                ROOT
                / "tools"
                / "character_director_scenarios"
                / "v1-listening.json"
            ).read_text(encoding="utf-8")
        )
        invalid_programs = (
            {key: value for key, value in valid.items() if key != "schema_version"},
            {**valid, "schema_version": 2},
            {**valid, "acceptance_scenario": "V11"},
            {
                **valid,
                "scenarios": [
                    {
                        **valid["scenarios"][0],
                        "capture_seconds": 601.0,
                    }
                ],
            },
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "program.json"
            for raw in invalid_programs:
                with self.subTest(raw=raw):
                    path.write_text(json.dumps(raw), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_scenario_program(path)

    def test_runtime_urls_include_atomic_animation_trace_endpoint(self):
        urls = runtime_urls("http://127.0.0.1:8875")
        self.assertEqual(len(urls), 5)
        self.assertEqual(
            urls[-2],
            "http://127.0.0.1:8875/api/avatar/wizard/animation-trace",
        )
        self.assertEqual(
            urls[-1],
            "http://127.0.0.1:8875/api/avatar/wizard/runtime-identity",
        )

    def test_runtime_urls_reject_credentials_query_and_fragment(self):
        for value in (
            "http://user:password@127.0.0.1:8875",
            "http://127.0.0.1:8875?token=secret",
            "http://127.0.0.1:8875#secret",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    runtime_urls(value)

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
    async def test_seals_runtime_identity_before_creating_evidence_output(self):
        class StopAfterSealCheck(Exception):
            pass

        provenance = {
            "head": "a" * 40,
            "head_tree": "b" * 40,
            "branch": "codex/test",
            "worktree_clean": True,
            "status_sha256": hashlib.sha256(b"").hexdigest(),
            "tracked_diff_sha256": hashlib.sha256(b"").hexdigest(),
            "status_lines": [],
        }
        identity_checks = []
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "not-created-yet"

            def seal_check(*_args, **_kwargs):
                identity_checks.append(output.exists())
                if len(identity_checks) == 1:
                    raise StopAfterSealCheck("stop after ordering assertion")

            with mock.patch(
                "tools.run_character_director_visual_review.collect_git_provenance",
                return_value=provenance,
            ), mock.patch(
                "tools.run_character_director_visual_review.request_json_async",
                new=mock.AsyncMock(return_value=({}, 0.0)),
            ), mock.patch(
                "tools.run_character_director_visual_review.validate_runtime_binding",
                side_effect=seal_check,
            ), mock.patch(
                "tools.run_character_director_visual_review.validate_manifest",
            ):
                await run_visual_review(
                    "http://127.0.0.1:8896",
                    output,
                    scenarios=(),
                )

        self.assertGreaterEqual(len(identity_checks), 1)
        self.assertFalse(identity_checks[0])

    async def test_scenario_clock_owns_exact_frame_budget_without_spill(self):
        clock = ScenarioClock()

        self.assertIsNone(clock.claim())
        clock.activate("listen-left", 3)
        self.assertEqual([clock.claim(), clock.claim(), clock.claim()], ["listen-left"] * 3)
        self.assertTrue(clock.completed.is_set())
        self.assertIsNone(clock.claim())
        self.assertIsNone(clock.current)

        clock.activate("return-viewer", 2)
        self.assertEqual([clock.claim(), clock.claim()], ["return-viewer"] * 2)
        self.assertTrue(clock.completed.is_set())

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


class RuntimeIdentityEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_process_identity_is_fixed_and_git_is_refreshed(self):
        app = create_app(
            ProceduralWizardFrameSource(80, 45, 24.0),
            runtime_server_config={"host": "127.0.0.1", "port": 8875},
        )
        route = next(
            route
            for route in app.routes
            if getattr(route, "path", None) == "/api/avatar/wizard/runtime-identity"
        )
        first = await route.endpoint()
        second = await route.endpoint()
        self.assertEqual(first["runtime_epoch"], second["runtime_epoch"])
        self.assertEqual(first["pid"], second["pid"])
        self.assertEqual(first["started_at_utc"], second["started_at_utc"])
        self.assertEqual(first["schema"], "wizard_runtime_identity_v1")
        self.assertEqual(first["server"]["port"], 8875)
        self.assertEqual(
            first["render"],
            {"cols": 80, "rows": 45, "fps": 24.0, "cell_bytes": 4},
        )
        self.assertRegex(first["python"]["executable_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(first["launch"]["argv_sha256"], r"^[0-9a-f]{64}$")
        await app.state.frame_hub.stop()


class ManifestValidationTests(unittest.TestCase):
    @staticmethod
    def runtime_identity(digest):
        python = Path(sys.executable).resolve()
        launcher = ROOT / "tools" / "run_wizard_avatar_server.py"
        return {
            "schema": "wizard_runtime_identity_v1",
            "schema_version": 1,
            "runtime_epoch": "runtime-test",
            "pid": 123,
            "started_at_utc": "2026-07-18T00:00:00Z",
            "started_at_monotonic_ns": 123456,
            "working_directory": str(ROOT),
            "repository_root": str(ROOT),
            "git": {
                "available": True,
                "head": digest,
                "head_tree": digest,
                "branch": "codex/character-director",
                "worktree_clean": True,
                "status_sha256": digest,
                "tracked_diff_sha256": digest,
            },
            "python": {
                "executable": str(python),
                "executable_sha256": hashlib.sha256(python.read_bytes()).hexdigest(),
            },
            "launch": {
                "argv": [str(launcher), "--port", "8875"],
                "argv_sha256": hashlib.sha256(
                    "\0".join([str(launcher), "--port", "8875"]).encode("utf-8")
                ).hexdigest(),
                "launcher": str(launcher),
                "launcher_sha256": hashlib.sha256(launcher.read_bytes()).hexdigest(),
            },
            "server": {
                "host": "127.0.0.1",
                "port": 8875,
                "companion_mode": False,
            },
            "render": {"cols": 1, "rows": 2, "fps": 24.0, "cell_bytes": 4},
        }

    def valid_manifest(self):
        digest = "a" * 64
        identity = self.runtime_identity(digest)
        return {
            "schema_version": 3,
            "evidence_kind": "external_real_runtime_visual_review",
            "valid": True,
            "failure_reason": None,
            "replay_exported": False,
            "frame_state_pairing": "atomic_animation_truth_trace_v1",
            "provenance": {
                "head": digest,
                "head_tree": digest,
                "branch": "codex/character-director",
                "worktree_clean": True,
                "status_sha256": digest,
                "tracked_diff_sha256": digest,
                "status_lines": [],
            },
            "runtime_binding": {
                "verified": True,
                "failure_reason": None,
                "base_url": "http://127.0.0.1:8875",
                "start": identity,
                "end": identity,
            },
            "runtime_observations": {
                "schema": "character_director_runtime_observations_v1",
                "schema_version": 1,
                "identity_process_epoch": "runtime-test",
                "command_runtime_epoch": "command-runtime-test",
                "subscriber_count": 1,
                "snapshot_count": 1,
                "acknowledgement_count": 1,
            },
            "subscriber_count": 1,
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
                "owned_frame_count": 2,
                "unowned_frame_count": 0,
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
                    "first_presentation_frame_index": 0,
                    "last_presentation_frame_index": 1,
                }
            ],
            "commands": [
                {
                    "scenario": "idle",
                    "command_id": "visual-review-0001-idle",
                    "source_sequence": 1,
                    "capture_planned_frame_count": 2,
                    "ack": {
                        "disposition": "applied",
                        "runtime_epoch": "command-runtime-test",
                    },
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
                    "capture_owned": True,
                    "presentation_frame_index": 0,
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
                    "capture_owned": True,
                    "presentation_frame_index": 1,
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
            "state_snapshots": [
                {
                    "body": {
                        "diagnostics": {
                            "runtime_epoch": "command-runtime-test",
                            "subscriber_count": 1,
                        }
                    }
                }
            ],
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
                {"path": "wire/frames.bin", "sha256": digest, "bytes": 16},
                {"path": "wire/index.ndjson", "sha256": digest, "bytes": 456},
                {"path": "capture.mp4", "sha256": digest, "bytes": 456},
            ],
            "video": {
                "available": True,
                "path": "capture.mp4",
                "codec": "h264",
                "frame_count": 2,
            },
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
            lambda value: value["runtime_binding"].update(verified=False),
        ):
            invalid = self.valid_manifest()
            mutate(invalid)
            with self.subTest(invalid=invalid):
                with self.assertRaises(ManifestValidationError):
                    validate_manifest(invalid)

    def test_runtime_binding_rejects_commit_process_and_render_mismatch(self):
        manifest = self.valid_manifest()
        binding = manifest["runtime_binding"]
        validate_runtime_binding(
            binding["start"],
            binding["end"],
            manifest["provenance"],
            binding["base_url"],
        )
        for mutate in (
            lambda value: value["git"].update(head="b" * 64),
            lambda value: value.update(runtime_epoch="different"),
            lambda value: value["server"].update(port=9999),
        ):
            end = {key: (dict(value) if isinstance(value, dict) else value) for key, value in binding["end"].items()}
            mutate(end)
            with self.subTest(end=end):
                with self.assertRaises(EvidenceFailure):
                    validate_runtime_binding(
                        binding["start"],
                        end,
                        manifest["provenance"],
                        binding["base_url"],
                    )

    def test_runtime_observations_reconcile_command_epoch_and_subscribers(self):
        records = CaptureRecords(
            commands=[
                {"ack": {"runtime_epoch": "command-runtime-a"}},
                {"ack": {"runtime_epoch": "command-runtime-a"}},
            ],
            state_snapshots=[
                {
                    "body": {
                        "diagnostics": {
                            "runtime_epoch": "command-runtime-a",
                            "subscriber_count": 1,
                        }
                    }
                },
                {
                    "body": {
                        "diagnostics": {
                            "runtime_epoch": "command-runtime-a",
                            "subscriber_count": 1,
                        }
                    }
                },
            ],
        )
        observations = collect_runtime_observations(
            {"runtime_epoch": "process-runtime-a"},
            records,
        )
        self.assertEqual(observations["identity_process_epoch"], "process-runtime-a")
        self.assertEqual(observations["command_runtime_epoch"], "command-runtime-a")
        self.assertEqual(observations["subscriber_count"], 1)

        records.state_snapshots[1]["body"]["diagnostics"]["subscriber_count"] = 2
        with self.assertRaisesRegex(EvidenceFailure, "subscriber count changed"):
            collect_runtime_observations({"runtime_epoch": "process-runtime-a"}, records)

        records.state_snapshots[1]["body"]["diagnostics"]["subscriber_count"] = 1
        records.commands[1]["ack"]["runtime_epoch"] = "command-runtime-b"
        with self.assertRaisesRegex(EvidenceFailure, "runtime epoch changed"):
            collect_runtime_observations({"runtime_epoch": "process-runtime-a"}, records)

    def test_schema_three_rejects_scenario_spill_and_snapshot_conflicts(self):
        manifest = self.valid_manifest()
        manifest["frames"][0].update(
            capture_owned=False,
            scenario=None,
            presentation_frame_index=None,
        )
        manifest["frames"][1]["presentation_frame_index"] = 0
        manifest["capture"].update(owned_frame_count=1, unowned_frame_count=1)
        manifest["video"]["frame_count"] = 1
        with self.assertRaisesRegex(ManifestValidationError, "pre/post-window spill"):
            validate_manifest(manifest)

        manifest = self.valid_manifest()
        manifest["state_snapshots"][0]["body"]["diagnostics"]["subscriber_count"] = 2
        with self.assertRaisesRegex(ManifestValidationError, "subscriber count mismatch"):
            validate_manifest(manifest)

    def test_review_bundle_binds_capture_machine_and_quarter_speed_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture = self.valid_manifest()
            capture["source_epoch"] = "visual-review-test"
            capture["video"]["path"] = "normal-speed.mp4"
            capture_manifest = root / "manifest.json"
            capture_manifest.write_text(json.dumps(capture), encoding="utf-8")
            capture_manifest_bytes = capture_manifest.read_bytes()
            normal_video = root / "normal-speed.mp4"
            normal_video.write_bytes(b"normal-video")
            quarter_speed = root / "v1-quarter-speed.mp4"
            quarter_speed.write_bytes(b"quarter-speed-video")
            machine_report = root / "v1-machine-acceptance.json"
            machine_report.write_text('{"passed":false}\n', encoding="utf-8")

            with mock.patch(
                "tools.run_character_director_visual_review.validate_manifest"
            ):
                bundle = build_review_bundle_manifest(
                    capture_manifest,
                    root,
                    (
                        ("quarter_speed", quarter_speed, "video/mp4", normal_video),
                        (
                            "machine_acceptance",
                            machine_report,
                            "application/json",
                            capture_manifest,
                        ),
                    ),
                )
                self.assertTrue(bundle["complete"])
                self.assertEqual(capture_manifest.read_bytes(), capture_manifest_bytes)
                validate_review_bundle_manifest(bundle, root)

                bundle["artifacts"][0]["source_sha256"] = "b" * 64
                with self.assertRaisesRegex(ManifestValidationError, "source SHA-256 mismatch"):
                    validate_review_bundle_manifest(bundle, root)

    def test_rejects_hashed_artifacts_that_do_not_replay_semantically(self):
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
            wire = root / "wire" / "frames.bin"
            wire.parent.mkdir()
            wire.write_bytes(b"not-replayable")
            manifest["artifacts"][3].update(
                bytes=wire.stat().st_size,
                sha256=hashlib.sha256(wire.read_bytes()).hexdigest(),
            )
            index = root / "wire" / "index.ndjson"
            index.write_text("{}\n{}\n", encoding="utf-8")
            manifest["artifacts"][4].update(
                bytes=index.stat().st_size,
                sha256=hashlib.sha256(index.read_bytes()).hexdigest(),
            )
            with self.assertRaises(ManifestValidationError):
                validate_manifest(manifest, root)

    def test_rejects_historical_runtime_evidence_with_unverified_contact(self):
        root = (
            ROOT
            / "evidence"
            / "character-director"
            / "runtime-bound-contact-653d400-2026-07-18"
        )
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(
            ManifestValidationError,
            "stored contact report differs from semantic replay",
        ):
            validate_artifact_semantics(manifest, root)


if __name__ == "__main__":
    unittest.main()
