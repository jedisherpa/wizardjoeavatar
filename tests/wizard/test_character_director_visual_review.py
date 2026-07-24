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
    add_transition_samples,
    collect_runtime_observations,
    create_contact_sheet,
    dispatch_runtime_operation,
    enqueue_decoded_frame,
    load_scenario_program,
    minimize_evidence_content,
    parse_init,
    runtime_urls,
    run_visual_review,
    select_capture_owned_contact_records,
    select_atomic_animation_trace,
    square_cell_image,
    validate_artifact_semantics,
    validate_evidence_content_minimization,
    validate_manifest,
    validate_review_bundle_manifest,
    validate_runtime_binding,
    validate_scenarios,
    validate_scenarios_v2,
)
from wizard_avatar.protocol import TAG_RAW
from wizard_avatar.contact_verifier import DecodedRasterFrameV1
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

    def test_loads_trace_triggered_scenario_program_v2(self):
        program = load_scenario_program(
            ROOT
            / "tools"
            / "character_director_scenarios"
            / "v7-cast-interruption.json"
        )

        self.assertEqual(program.schema_version, 2)
        self.assertEqual(program.acceptance_scenario, "V7")
        self.assertEqual(program.maximum_capture_frame_count, 172)
        self.assertEqual(program.scenarios[1].until_trace.clip, "cast_front")
        self.assertEqual(program.scenarios[1].until_trace.authored_frame, 8)
        self.assertEqual(program.scenarios[5].until_trace.marker_id, "action_commit")
        self.assertEqual(program.scenarios[5].max_frames, 16)

    def test_rejects_ambiguous_or_unbounded_scenario_program_v2_timing(self):
        base = {
            "name": "cast",
            "kind": "action",
            "payload": {"action": "magic_cast"},
        }
        invalid = (
            [{**base, "timing": {"until_trace": {"clip": "cast_front", "authored_frame": 8}}}],
            [
                {
                    **base,
                    "timing": {
                        "capture_frames": 12,
                        "max_frames": 12,
                    },
                }
            ],
            [
                {
                    **base,
                    "timing": {
                        "until_trace": {
                            "clip": "cast_front",
                            "marker_id": "action_commit",
                            "authored_frame": 10,
                        },
                        "max_frames": 16,
                    },
                }
            ],
            [
                {
                    **base,
                    "timing": {
                        "until_trace": {
                            "marker_id": "unknown_marker",
                            "authored_frame": 10,
                        },
                        "max_frames": 16,
                    },
                }
            ],
        )
        for scenarios in invalid:
            with self.subTest(scenarios=scenarios):
                with self.assertRaises(ValueError):
                    validate_scenarios_v2(scenarios)

    def test_loads_continuous_capture_with_strict_scheduled_commands(self):
        scenarios = validate_scenarios_v2(
            [
                {
                    "name": "continuous-performance",
                    "kind": "reset",
                    "payload": {},
                    "timing": {
                        "capture_frames": 1440,
                        "scheduled_commands": [
                            {
                                "name": "phrase-one",
                                "at_frame": 120,
                                "kind": "speak",
                                "payload": {
                                    "speech_id": "v8-phrase-one",
                                    "text": "A repeated phrase.",
                                    "duration_ms": 2400,
                                },
                            },
                            {
                                "name": "gesture-one",
                                "at_frame": 240,
                                "kind": "action",
                                "payload": {
                                    "action": "explaining",
                                    "duration_ms": 1200,
                                },
                            },
                        ],
                    },
                }
            ]
        )

        self.assertEqual(scenarios[0].capture_frames, 1440)
        self.assertEqual(len(scenarios[0].scheduled_commands), 2)
        self.assertEqual(scenarios[0].scheduled_commands[0].at_frame, 120)
        self.assertEqual(
            scenarios[0].to_mapping()["timing"]["scheduled_commands"][1]["kind"],
            "action",
        )

        invalid_schedules = (
            [dict(scenarios[0].scheduled_commands[0].to_mapping(), at_frame=0)],
            [
                scenarios[0].scheduled_commands[0].to_mapping(),
                dict(scenarios[0].scheduled_commands[1].to_mapping(), at_frame=120),
            ],
            [dict(scenarios[0].scheduled_commands[0].to_mapping(), at_frame=1440)],
        )
        for scheduled_commands in invalid_schedules:
            with self.subTest(scheduled_commands=scheduled_commands):
                with self.assertRaises(ValueError):
                    validate_scenarios_v2(
                        [
                            {
                                "name": "continuous-performance",
                                "kind": "reset",
                                "payload": {},
                                "timing": {
                                    "capture_frames": 1440,
                                    "scheduled_commands": scheduled_commands,
                                },
                            }
                        ]
                    )

    def test_media_session_is_an_explicit_scenario_transport(self):
        scenarios = validate_scenarios_v2(
            [
                {
                    "name": "full-profile",
                    "kind": "media_session",
                    "payload": {
                        "schema": "prism_media_session_v1",
                        "schema_version": 1,
                    },
                    "timing": {"capture_frames": 24},
                }
            ]
        )

        self.assertEqual(scenarios[0].kind, "media_session")


class RuntimeOperationDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_authenticated_media_session_uses_accepted_ack(self):
        accepted = {
            "schema": "prism_media_session_ack_v1",
            "schema_version": 1,
            "disposition": "accepted",
            "accepted_sequence": 7,
        }
        with mock.patch(
            "tools.run_character_director_visual_review.request_json_async",
            new=mock.AsyncMock(return_value=(accepted, 2.5)),
        ) as request:
            response, ack, state, latency_ms, transport = (
                await dispatch_runtime_operation(
                    kind="media_session",
                    payload={"sequence": 7},
                    envelope={},
                    command_url="http://127.0.0.1:8875/api/avatar/wizard/command",
                    media_url="http://127.0.0.1:8875/api/avatar/wizard/media-session",
                    media_token="proof-token",
                )
            )

        self.assertEqual(response, accepted)
        self.assertEqual(ack, accepted)
        self.assertEqual(state, accepted)
        self.assertEqual(latency_ms, 2.5)
        self.assertEqual(transport, "media_session")
        request.assert_awaited_once_with(
            "POST",
            "http://127.0.0.1:8875/api/avatar/wizard/media-session",
            {"sequence": 7},
            {"Authorization": "Bearer proof-token"},
        )

    async def test_media_session_requires_connector_token(self):
        with self.assertRaisesRegex(
            EvidenceFailure,
            "WIZARD_MEDIA_CONNECTOR_TOKEN",
        ):
            await dispatch_runtime_operation(
                kind="media_session",
                payload={"sequence": 7},
                envelope={},
                command_url="http://127.0.0.1:8875/api/avatar/wizard/command",
                media_url="http://127.0.0.1:8875/api/avatar/wizard/media-session",
                media_token=None,
            )

    def test_loads_v8_as_one_continuous_sixty_second_take(self):
        program = load_scenario_program(
            ROOT
            / "tools"
            / "character_director_scenarios"
            / "v8-purposeful-performance.json"
        )

        self.assertEqual(program.acceptance_scenario, "V8")
        self.assertEqual(program.maximum_capture_frame_count, 1440)
        self.assertEqual(len(program.scenarios), 1)
        self.assertEqual(len(program.scenarios[0].scheduled_commands), 12)
        self.assertEqual(
            [
                command.payload["speech_id"]
                for command in program.scenarios[0].scheduled_commands
                if command.kind == "speak"
            ],
            ["v8-phrase-1", "v8-phrase-2", "v8-phrase-3"],
        )

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

    def test_contact_verification_excludes_transport_warmup_frames(self):
        source = ProceduralWizardFrameSource()
        records = []
        frames = []
        for capture_owned in (False, True):
            source.advance_simulation(1 / source.fps)
            candidate = source.render_captured_candidate_sync(
                source.capture_render_state()
            )
            source.commit_render_candidate(candidate)
            records.append(candidate.animation_truth)
            frames.append(
                {
                    "frame_index": candidate.frame.frame_index,
                    "capture_owned": capture_owned,
                }
            )

        selected = select_capture_owned_contact_records(records, frames)

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].frame_index, records[1].frame_index)

        legacy = select_capture_owned_contact_records(
            records,
            [{"frame_index": record.frame_index} for record in records],
        )
        self.assertEqual(legacy, tuple(records))

    def test_square_cell_renderer_uses_rgb_even_for_space_glyphs(self):
        image = square_cell_image(b"\x20\x0a\x14\x1e", 1, 1, 3)
        self.assertEqual(image.size, (3, 3))
        self.assertEqual(set(image.getdata()), {(10, 20, 30)})

    def test_transition_samples_and_contact_sheet_preserve_traceability(self):
        digest_a = "a" * 64
        digest_b = "b" * 64
        state_a = "c" * 64
        state_b = "d" * 64
        records = CaptureRecords(
            frames=[
                {
                    "frame_index": 10,
                    "scenario": "listen",
                    "presentation_frame_index": 0,
                    "sha256": digest_a,
                    "capture_owned": True,
                },
                {
                    "frame_index": 11,
                    "scenario": "listen",
                    "presentation_frame_index": 1,
                    "sha256": digest_b,
                    "capture_owned": True,
                },
            ],
            commands=[{"scenario": "listen", "command_id": "command-123"}],
            samples=[
                {
                    "path": "samples/cadence.png",
                    "frame_index": 10,
                    "scenario": "listen",
                    "presentation_frame_index": 0,
                    "frame_sha256": digest_a,
                    "sample_reason": "scenario_start",
                }
            ],
            animation_truth_trace=[
                {
                    "frame_index": 10,
                    "simulation_tick": 20,
                    "authoritative_state_sha256": state_a,
                    "presentation_channels": {
                        "rendered_head_pose_id": "front_idle",
                        "head_eye_phase": "eyes_lead",
                        "blink_closed": False,
                        "head_offset_x": 0,
                        "head_offset_y": 0,
                    },
                },
                {
                    "frame_index": 11,
                    "simulation_tick": 21,
                    "authoritative_state_sha256": state_b,
                    "presentation_channels": {
                        "rendered_head_pose_id": "walk_front_left",
                        "head_eye_phase": "head_follow",
                        "blink_closed": False,
                        "head_offset_x": -1,
                        "head_offset_y": 0,
                    },
                },
            ],
            decoded_raster_frames={
                10: DecodedRasterFrameV1(2, 1, b" \xff\xff\xff \xff\xff\xff"),
                11: DecodedRasterFrameV1(2, 1, b"#\x10\x20\x30 \xff\xff\xff"),
            },
        )
        init = parse_init("INIT:24:5:2:1:0:0:0.000")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "samples").mkdir()
            square_cell_image(records.decoded_raster_frames[10].cells, 2, 1, 2).save(
                root / "samples" / "cadence.png"
            )
            add_transition_samples(records, init, root, "run", 2)
            self.assertEqual([sample["frame_index"] for sample in records.samples], [10, 11])
            self.assertEqual(records.samples[1]["sample_reason"], "presentation_transition")

            contact = root / "contact.png"
            create_contact_sheet(
                records.samples,
                records.animation_truth_trace,
                records.commands,
                root,
                contact,
                24.0,
            )
            self.assertTrue(contact.is_file())
            self.assertGreater(contact.stat().st_size, 0)

    def test_transition_sampling_ignores_unowned_preroll(self):
        digest = "a" * 64
        records = CaptureRecords(
            frames=[
                {
                    "frame_index": 9,
                    "capture_owned": False,
                    "scenario": None,
                    "presentation_frame_index": None,
                    "sha256": digest,
                },
                {
                    "frame_index": 10,
                    "capture_owned": True,
                    "scenario": "speech",
                    "presentation_frame_index": 0,
                    "sha256": digest,
                },
            ],
            animation_truth_trace=[
                {
                    "frame_index": 9,
                    "presentation_channels": {
                        "rendered_head_pose_id": "front_idle",
                        "head_eye_phase": "steady",
                        "blink_closed": False,
                        "head_offset_x": 0,
                        "head_offset_y": 0,
                    },
                },
                {
                    "frame_index": 10,
                    "presentation_channels": {
                        "rendered_head_pose_id": "front_idle",
                        "head_eye_phase": "steady",
                        "blink_closed": False,
                        "head_offset_x": 0,
                        "head_offset_y": 0,
                    },
                },
            ],
            decoded_raster_frames={
                9: DecodedRasterFrameV1(1, 1, b" \xff\xff\xff"),
                10: DecodedRasterFrameV1(1, 1, b"#\x10\x20\x30"),
            },
        )
        init = parse_init("INIT:24:5:1:1:0:0:0.000")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "samples").mkdir()
            add_transition_samples(records, init, root, "run", 2)

        self.assertEqual(records.samples, [])


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
        self.assertEqual(clock.claimed_frames, 3)
        self.assertTrue(clock.completed.is_set())
        self.assertIsNone(clock.claim())
        self.assertIsNone(clock.current)

        clock.activate("return-viewer", 2)
        self.assertEqual(clock.claimed_frames, 0)
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
                "status_lines": [],
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
            "content_minimization": {
                "schema": "evidence_content_minimization_v1",
                "sensitive_fields": ["speech_text"],
                "replacement": "sha256_and_size_metadata",
            },
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

    def test_validates_media_session_ack_transport(self):
        manifest = self.valid_manifest()
        manifest["commands"][0].update(
            kind="media_session",
            transport="media_session",
        )
        manifest["commands"][0]["ack"]["disposition"] = "accepted"
        manifest["commands"][0]["ack"]["wizard_runtime_epoch"] = (
            manifest["commands"][0]["ack"].pop("runtime_epoch")
        )

        validate_manifest(manifest)

        manifest["commands"][0]["ack"]["disposition"] = "applied"
        with self.assertRaisesRegex(
            ManifestValidationError,
            "accepted media_session",
        ):
            validate_manifest(manifest)

    def test_validates_version_two_runtime_epoch_map(self):
        manifest = self.valid_manifest()
        manifest["commands"][0]["ack"]["wizard_runtime_epoch"] = "wizard-runtime-test"
        manifest["runtime_observations"] = {
            "schema": "character_director_runtime_observations_v2",
            "schema_version": 2,
            "identity_process_epoch": "runtime-test",
            "command_runtime_epoch": "command-runtime-test",
            "runtime_epochs": {
                "runtime_epoch": "command-runtime-test",
                "wizard_runtime_epoch": "wizard-runtime-test",
            },
            "subscriber_count": 1,
            "snapshot_count": 1,
            "acknowledgement_count": 1,
        }

        validate_manifest(manifest)

        manifest["runtime_observations"]["runtime_epochs"][
            "wizard_runtime_epoch"
        ] = "different"
        with self.assertRaisesRegex(
            ManifestValidationError,
            "acknowledgement runtime epoch mismatch",
        ):
            validate_manifest(manifest)

    def test_sensitive_runtime_text_is_minimized_recursively(self):
        speech = "A governed line with a snowman \u2603 and no place in machine evidence."
        minimized = minimize_evidence_content(
            {
                "state": {"speech_text": speech},
                "history": [{"speech_text": "short"}],
            }
        )

        encoded = speech.encode("utf-8")
        self.assertNotIn("speech_text", minimized["state"])
        self.assertEqual(
            minimized["state"]["speech_text_evidence"],
            {
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "utf8_bytes": len(encoded),
                "character_count": len(speech),
            },
        )
        self.assertNotIn(speech, json.dumps(minimized))
        validate_evidence_content_minimization(minimized)

    def test_nullable_sensitive_runtime_text_is_omitted(self):
        minimized = minimize_evidence_content(
            {"state": {"speech_text": None, "speech_id": None}}
        )

        self.assertEqual(minimized, {"state": {"speech_id": None}})
        validate_evidence_content_minimization(minimized)

    def test_manifest_rejects_raw_or_malformed_sensitive_text(self):
        raw = self.valid_manifest()
        raw["commands"][0]["response_state"] = {"speech_text": "do not serialize"}
        with self.assertRaisesRegex(ManifestValidationError, "raw sensitive field"):
            validate_manifest(raw)

        malformed = self.valid_manifest()
        malformed["commands"][0]["response_state"] = {
            "speech_text_evidence": {
                "sha256": "not-a-digest",
                "utf8_bytes": 16,
                "character_count": 16,
            }
        }
        with self.assertRaisesRegex(ManifestValidationError, "invalid sensitive-text evidence"):
            validate_manifest(malformed)

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

    def test_runtime_binding_allows_only_its_untracked_evidence_output(self):
        manifest = self.valid_manifest()
        binding = manifest["runtime_binding"]
        start = binding["start"]
        end = json.loads(json.dumps(start))
        output = ROOT / "evidence" / "character-director" / "strict-run"
        end["git"].update(
            worktree_clean=False,
            status_sha256="c" * 64,
            status_lines=[
                "?? evidence/character-director/strict-run/manifest.json",
                "?? evidence/character-director/strict-run/wire/frames.bin",
            ],
        )

        validate_runtime_binding(
            start,
            end,
            manifest["provenance"],
            binding["base_url"],
            evidence_output_dir=output,
        )

        end["git"]["status_lines"].append("?? unrelated.txt")
        with self.assertRaisesRegex(EvidenceFailure, "outside the evidence output"):
            validate_runtime_binding(
                start,
                end,
                manifest["provenance"],
                binding["base_url"],
                evidence_output_dir=output,
            )

    def test_runtime_observations_reconcile_command_epoch_and_subscribers(self):
        records = CaptureRecords(
            commands=[
                {
                    "transport": "command",
                    "ack": {"runtime_epoch": "command-runtime-a"},
                },
                {
                    "transport": "media_session",
                    "ack": {"wizard_runtime_epoch": "command-runtime-a"},
                },
                {
                    "transport": "media_session",
                    "ack": {"wizard_runtime_epoch": "command-runtime-a"},
                },
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
        self.assertEqual(
            observations["runtime_epochs"],
            {
                "runtime_epoch": "command-runtime-a",
                "wizard_runtime_epoch": "command-runtime-a",
            },
        )
        self.assertEqual(observations["subscriber_count"], 1)

        records.state_snapshots[1]["body"]["diagnostics"]["subscriber_count"] = 2
        with self.assertRaisesRegex(EvidenceFailure, "subscriber count changed"):
            collect_runtime_observations({"runtime_epoch": "process-runtime-a"}, records)

        records.state_snapshots[1]["body"]["diagnostics"]["subscriber_count"] = 1
        records.commands[2]["ack"]["wizard_runtime_epoch"] = "command-runtime-b"
        with self.assertRaisesRegex(EvidenceFailure, "runtime epoch changed"):
            collect_runtime_observations({"runtime_epoch": "process-runtime-a"}, records)

    def test_runtime_observations_include_every_joeville_character_epoch(self):
        character_fields = (
            "wizard_runtime_epoch",
            "robin_runtime_epoch",
            "dragon_runtime_epoch",
            "kingfisher_runtime_epoch",
            "crystail_runtime_epoch",
            "falcor_runtime_epoch",
            "serena_quill_runtime_epoch",
            "aurelia_finch_runtime_epoch",
            "selene_hart_runtime_epoch",
            "thorne_vale_runtime_epoch",
            "elara_voss_runtime_epoch",
            "kai_renner_runtime_epoch",
            "mira_solen_runtime_epoch",
            "draven_holt_runtime_epoch",
            "liora_kane_runtime_epoch",
            "rohan_slate_runtime_epoch",
            "finn_calder_runtime_epoch",
            "orion_vale_runtime_epoch",
        )
        character_epochs = {
            field: "epoch-{:02d}".format(index)
            for index, field in enumerate(character_fields, 1)
        }
        records = CaptureRecords(
            commands=[
                {
                    "transport": "media_session",
                    "ack": character_epochs,
                }
            ],
            state_snapshots=[
                {
                    "body": {
                        "diagnostics": {
                            "runtime_epoch": "remote-command-runtime-a",
                            "subscriber_count": 1,
                        }
                    }
                }
            ],
        )

        observations = collect_runtime_observations(
            {"runtime_epoch": "process-runtime-a"},
            records,
        )

        self.assertEqual(observations["schema_version"], 2)
        self.assertEqual(
            observations["runtime_epochs"],
            {
                "runtime_epoch": "remote-command-runtime-a",
                **character_epochs,
            },
        )

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
            browser_video = root / "v1-browser-layout.mp4"
            browser_video.write_bytes(b"browser-layout-video")
            browser_metrics = root / "v1-browser-layout-metrics.json"
            browser_metrics.write_text(
                json.dumps(
                    {
                        "schema": "character_director_browser_layout_v1",
                        "schema_version": 1,
                        "run_id": capture["source_epoch"],
                        "candidate_commit": capture["provenance"]["head"],
                        "capture_manifest_sha256": hashlib.sha256(
                            capture_manifest.read_bytes()
                        ).hexdigest(),
                        "frame_count": 2,
                        "expected_frame_count": 2,
                        "final_client_metrics": {
                            "decodeErrorCount": 0,
                            "canvas": {
                                "cols": capture["init"]["cols"],
                                "rows": capture["init"]["rows"],
                            },
                        },
                        "page_errors": [],
                        "video_path": browser_video.name,
                        "video_bytes": browser_video.stat().st_size,
                        "video_sha256": hashlib.sha256(
                            browser_video.read_bytes()
                        ).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )

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
                        (
                            "browser_layout",
                            browser_video,
                            "video/mp4",
                            browser_metrics,
                        ),
                    ),
                )
                self.assertTrue(bundle["complete"])
                self.assertEqual(capture_manifest.read_bytes(), capture_manifest_bytes)
                validate_review_bundle_manifest(bundle, root)

                bundle["artifacts"][0]["source_sha256"] = "b" * 64
                with self.assertRaisesRegex(ManifestValidationError, "source SHA-256 mismatch"):
                    validate_review_bundle_manifest(bundle, root)

                legacy_bundle = build_review_bundle_manifest(
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
                legacy_bundle["schema_version"] = 1
                legacy_bundle["complete"] = True
                validate_review_bundle_manifest(legacy_bundle, root)

                capture["scenario_program"] = {"acceptance_scenario": "V3"}
                capture_manifest.write_text(json.dumps(capture), encoding="utf-8")
                v3_quarter = root / "v3-quarter-speed.mp4"
                v3_quarter.write_bytes(b"v3-quarter-speed-video")
                v3_machine = root / "v3-machine-acceptance.json"
                v3_machine.write_text('{"passed":true}\n', encoding="utf-8")
                v3_browser = root / "v3-browser-layout.mp4"
                v3_browser.write_bytes(b"v3-browser-layout-video")
                v3_metrics = root / "v3-browser-layout-metrics.json"
                v3_metrics.write_text(
                    json.dumps(
                        {
                            "schema": "character_director_browser_layout_v1",
                            "schema_version": 1,
                            "run_id": capture["source_epoch"],
                            "candidate_commit": capture["provenance"]["head"],
                            "capture_manifest_sha256": hashlib.sha256(
                                capture_manifest.read_bytes()
                            ).hexdigest(),
                            "frame_count": 2,
                            "expected_frame_count": 2,
                            "final_client_metrics": {
                                "decodeErrorCount": 0,
                                "canvas": {
                                    "cols": capture["init"]["cols"],
                                    "rows": capture["init"]["rows"],
                                },
                            },
                            "page_errors": [],
                            "video_path": v3_browser.name,
                            "video_bytes": v3_browser.stat().st_size,
                            "video_sha256": hashlib.sha256(
                                v3_browser.read_bytes()
                            ).hexdigest(),
                        }
                    ),
                    encoding="utf-8",
                )
                v3_bundle = build_review_bundle_manifest(
                    capture_manifest,
                    root,
                    (
                        ("quarter_speed", v3_quarter, "video/mp4", normal_video),
                        (
                            "machine_acceptance",
                            v3_machine,
                            "application/json",
                            capture_manifest,
                        ),
                        (
                            "browser_layout",
                            v3_browser,
                            "video/mp4",
                            v3_metrics,
                        ),
                    ),
                )
                self.assertTrue(v3_bundle["complete"])
                validate_review_bundle_manifest(v3_bundle, root)

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
