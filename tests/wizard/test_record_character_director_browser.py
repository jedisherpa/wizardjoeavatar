import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from tools.record_character_director_browser import (
    BrowserCaptureFailure,
    load_expected_start_identity,
    parse_args,
    parse_browser_scenario_program,
    presentation_identity_errors,
    scenario_capture_events,
    wait_for_presented_advance,
)

ROOT = Path(__file__).resolve().parents[2]


def program_v1(scenarios):
    return {
        "schema": "character_director_scenario_program_v1",
        "schema_version": 1,
        "program_id": "browser-v1",
        "acceptance_scenario": "V1",
        "scenarios": scenarios,
    }


def program_v2(scenarios):
    return {
        "schema": "character_director_scenario_program_v2",
        "schema_version": 2,
        "program_id": "browser-v2",
        "acceptance_scenario": "V8",
        "scenarios": scenarios,
    }


class BrowserScenarioProgramTests(unittest.TestCase):
    def test_start_identity_is_loaded_from_first_owned_trace_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence_dir = Path(directory)
            (evidence_dir / "animation_truth_trace.ndjson").write_text(
                json.dumps(
                    {
                        "frame_index": 7,
                        "frame_fnv1a32": "fnv1a32:0123abcd",
                        "world_root_x": -3.2,
                        "world_root_z": 5.0,
                        "presented_facing": "west",
                        "presentation_channels": {
                            "action": "idle",
                            "expression": "neutral",
                            "rendered_mouth_shape": "closed",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            manifest = {
                "animation_truth_trace": {
                    "path": "animation_truth_trace.ndjson",
                },
                "scenario_ranges": [{"first_frame_index": 7}],
            }

            identity = load_expected_start_identity(manifest, evidence_dir)

        self.assertEqual(identity["frame_index"], 7)
        self.assertEqual(identity["frame_fnv1a32"], "fnv1a32:0123abcd")
        self.assertEqual(identity["world_root_x"], -3.2)
        self.assertEqual(identity["presented_facing"], "west")

    def test_start_identity_rejects_stale_diagnostics_and_canvas(self):
        expected = {
            "frame_index": 0,
            "frame_fnv1a32": "fnv1a32:0123abcd",
            "world_root_x": 0.0,
            "world_root_z": 5.0,
            "presented_facing": "south",
            "action": "idle",
            "expression": "neutral",
            "mouth": "closed",
        }
        snapshot = {
            "client_metrics": {
                "presentedFrames": 13,
                "rawQueueDepth": 0,
                "decodedQueueDepth": 2,
                "canvas": {
                    "lastPresentedLogicalHash": "fnv1a32:deadbeef",
                    "dpr": 1.0,
                },
            },
            "state_response": {
                "state": {
                    "world_position": {"x": 3.2, "z": 5.0},
                    "facing": "east",
                    "action": "idle",
                    "expression": "neutral",
                },
                "diagnostics": {"presented_facing": "east"},
            },
            "diagnostics_text": (
                "x 3.20  z 5.00\nfacing east\n"
                "action idle  face neutral\ncell 4px  dpr 1.00"
            ),
        }

        errors = presentation_identity_errors(
            snapshot,
            expected,
            device_scale_factor=1.0,
            baseline=10,
            minimum_frames=3,
        )

        self.assertIn("canvas_hash_mismatch", errors)
        self.assertIn("runtime_x_mismatch", errors)
        self.assertIn("runtime_facing_mismatch", errors)
        self.assertIn("presented_facing_mismatch", errors)
        self.assertTrue(
            any(error.startswith("diagnostics_text_mismatch") for error in errors)
        )

    def test_start_identity_accepts_synchronized_browser_state(self):
        expected = {
            "frame_index": 0,
            "frame_fnv1a32": "fnv1a32:0123abcd",
            "world_root_x": 0.0,
            "world_root_z": 5.0,
            "presented_facing": "south",
            "action": "idle",
            "expression": "neutral",
            "mouth": "closed",
        }
        snapshot = {
            "client_metrics": {
                "presentedFrames": 13,
                "rawQueueDepth": 0,
                "decodedQueueDepth": 2,
                "canvas": {
                    "lastPresentedLogicalHash": "fnv1a32:0123abcd",
                    "dpr": 2.0,
                },
            },
            "state_response": {
                "state": {
                    "world_position": {"x": 0.0, "z": 5.0},
                    "facing": "south",
                    "action": "idle",
                    "expression": "neutral",
                },
                "diagnostics": {"presented_facing": "south"},
            },
            "diagnostics_text": (
                "x 0.00  z 5.00\nfacing south\n"
                "action idle  face neutral\ncell 8px  dpr 2.00"
            ),
        }

        errors = presentation_identity_errors(
            snapshot,
            expected,
            device_scale_factor=2.0,
            baseline=10,
            minimum_frames=3,
        )

        self.assertEqual(errors, ())

    def test_reset_preroll_waits_for_three_drained_presentations(self):
        class FakeCDP:
            def __init__(self):
                self.results = [
                    {
                        "presentedFrames": 11,
                        "rawQueueDepth": 0,
                        "decodedQueueDepth": 0,
                    },
                    {
                        "presentedFrames": 13,
                        "rawQueueDepth": 1,
                        "decodedQueueDepth": 0,
                    },
                    {
                        "presentedFrames": 13,
                        "rawQueueDepth": 0,
                        "decodedQueueDepth": 2,
                    },
                ]

            async def evaluate(self, expression):
                self.assert_expression = expression
                return self.results.pop(0)

        result = asyncio.run(
            wait_for_presented_advance(
                FakeCDP(),
                baseline=10,
                minimum_frames=3,
                timeout=1.0,
            )
        )

        self.assertEqual(result["presentedFrames"], 13)

    def test_exact_desktop_and_mobile_viewport_profiles_parse(self):
        desktop = parse_args(
            [
                "--manifest",
                "manifest.json",
                "--video",
                "desktop.mp4",
                "--metrics",
                "desktop.json",
                "--width",
                "1280",
                "--height",
                "720",
                "--device-scale-factor",
                "2",
                "--profile",
                "desktop-dpr2",
            ]
        )
        mobile = parse_args(
            [
                "--manifest",
                "manifest.json",
                "--video",
                "mobile.mp4",
                "--metrics",
                "mobile.json",
                "--width",
                "390",
                "--height",
                "844",
                "--device-scale-factor",
                "3",
                "--mobile",
                "--profile",
                "mobile-390x844-dpr3",
            ]
        )

        self.assertEqual(desktop.device_scale_factor, 2.0)
        self.assertFalse(desktop.mobile)
        self.assertEqual(mobile.device_scale_factor, 3.0)
        self.assertTrue(mobile.mobile)

    def test_invalid_viewport_profiles_fail_closed(self):
        invalid = (
            ["--device-scale-factor", "0.5"],
            ["--device-scale-factor", "5"],
            ["--profile", "Desktop DPR1"],
            ["--width", "390", "--height", "844"],
            ["--width", "300", "--height", "844", "--mobile"],
        )
        base = [
            "--manifest",
            "manifest.json",
            "--video",
            "capture.mp4",
            "--metrics",
            "metrics.json",
        ]

        for values in invalid:
            with self.subTest(values=values), self.assertRaises(SystemExit):
                parse_args(base + values)

    def test_v1_preserves_seconds_based_frame_budget(self):
        parsed = parse_browser_scenario_program(
            program_v1(
                [
                    {
                        "name": "first",
                        "kind": "reset",
                        "payload": {},
                        "settle_seconds": 0.25,
                        "capture_seconds": 0.01,
                    },
                    {
                        "name": "second",
                        "kind": "gaze",
                        "payload": {"target": "left"},
                        "settle_seconds": 0.0,
                        "capture_seconds": 1.25,
                    },
                ]
            ),
            fps=24.0,
        )

        self.assertEqual(parsed.schema_version, 1)
        self.assertEqual(parsed.program_id, "browser-v1")
        self.assertEqual(parsed.acceptance_scenario, "V1")
        self.assertEqual(
            [scenario.capture_frames for scenario in parsed.scenarios],
            [1, 30],
        )
        self.assertEqual(parsed.expected_frame_count, 31)
        self.assertEqual(parsed.scenarios[0].settle_seconds, 0.25)
        self.assertEqual(parsed.scenarios[0].scheduled_commands, ())

    def test_v2_reports_exact_frames_and_schedules_after_declared_offsets(self):
        parsed = parse_browser_scenario_program(
            program_v2(
                [
                    {
                        "name": "continuous-performance",
                        "kind": "reset",
                        "payload": {},
                        "timing": {
                            "capture_frames": 6,
                            "scheduled_commands": [
                                {
                                    "name": "speak-on-two",
                                    "at_frame": 2,
                                    "kind": "speak",
                                    "payload": {
                                        "speech_id": "line-one",
                                        "text": "Hello.",
                                        "duration_ms": 500,
                                    },
                                },
                                {
                                    "name": "point-on-five",
                                    "at_frame": 5,
                                    "kind": "action",
                                    "payload": {
                                        "action": "pointing",
                                        "duration_ms": 300,
                                    },
                                },
                            ],
                        },
                    },
                    {
                        "name": "final-hold",
                        "kind": "stop",
                        "payload": {},
                        "timing": {"capture_frames": 3},
                    },
                ]
            ),
            fps=60.0,
        )

        self.assertEqual(parsed.schema_version, 2)
        self.assertEqual(parsed.expected_frame_count, 9)
        events = [
            (frame, command.name if command is not None else "capture")
            for frame, command in scenario_capture_events(parsed.scenarios[0])
        ]
        self.assertEqual(
            events,
            [
                (1, "capture"),
                (2, "capture"),
                (2, "speak-on-two"),
                (3, "capture"),
                (4, "capture"),
                (5, "capture"),
                (5, "point-on-five"),
                (6, "capture"),
            ],
        )

    def test_real_v8_fixture_reports_exact_capture_budget(self):
        fixture = json.loads(
            (
                ROOT
                / "tools"
                / "character_director_scenarios"
                / "v8-purposeful-performance.json"
            ).read_text(encoding="utf-8")
        )

        parsed = parse_browser_scenario_program(fixture, fps=24.0)

        self.assertEqual(parsed.expected_frame_count, 1440)
        self.assertEqual(len(parsed.scenarios), 1)
        self.assertEqual(len(parsed.scenarios[0].scheduled_commands), 12)
        self.assertEqual(
            [command.at_frame for command in parsed.scenarios[0].scheduled_commands],
            [96, 192, 288, 336, 432, 528, 624, 672, 768, 864, 960, 1008],
        )

    def test_real_v10_fixture_reports_exact_capture_budget(self):
        fixture = json.loads(
            (
                ROOT
                / "tools"
                / "character_director_scenarios"
                / "v10-responsive-framing.json"
            ).read_text(encoding="utf-8")
        )

        parsed = parse_browser_scenario_program(fixture, fps=24.0)

        self.assertEqual(parsed.expected_frame_count, 528)
        self.assertEqual(
            [scenario.command.name for scenario in parsed.scenarios],
            [
                "v10-center",
                "v10-near",
                "v10-far",
                "v10-left-edge",
                "v10-right-edge",
            ],
        )
        self.assertEqual(
            [scenario.capture_frames for scenario in parsed.scenarios],
            [48, 96, 144, 120, 120],
        )

    def test_v2_fails_closed_on_unsupported_or_ambiguous_timing(self):
        invalid_timing = (
            {"until_trace": {"clip": "cast_front", "authored_frame": 8}, "max_frames": 12},
            {"capture_frames": 12, "unknown": True},
            {"capture_frames": 0},
            {
                "capture_frames": 12,
                "scheduled_commands": [
                    {
                        "name": "too-late",
                        "at_frame": 12,
                        "kind": "stop",
                        "payload": {},
                    }
                ],
            },
            {
                "capture_frames": 12,
                "scheduled_commands": [
                    {
                        "name": "media",
                        "at_frame": 4,
                        "kind": "media_session",
                        "payload": {},
                    }
                ],
            },
        )

        for timing in invalid_timing:
            with self.subTest(timing=timing):
                with self.assertRaises(BrowserCaptureFailure):
                    parse_browser_scenario_program(
                        program_v2(
                            [
                                {
                                    "name": "strict-capture",
                                    "kind": "reset",
                                    "payload": {},
                                    "timing": timing,
                                }
                            ]
                        ),
                        fps=24.0,
                    )

    def test_rejects_unknown_program_and_scenario_fields(self):
        unknown_program = program_v2(
            [
                {
                    "name": "strict-capture",
                    "kind": "reset",
                    "payload": {},
                    "timing": {"capture_frames": 12},
                }
            ]
        )
        unknown_program["extra"] = True
        with self.assertRaisesRegex(BrowserCaptureFailure, "program schema mismatch"):
            parse_browser_scenario_program(unknown_program, fps=24.0)

        unknown_scenario = program_v2(
            [
                {
                    "name": "strict-capture",
                    "kind": "reset",
                    "payload": {},
                    "timing": {"capture_frames": 12},
                    "extra": True,
                }
            ]
        )
        with self.assertRaisesRegex(BrowserCaptureFailure, "scenario 0 schema mismatch"):
            parse_browser_scenario_program(unknown_scenario, fps=24.0)

        boolean_version = program_v1(
            [
                {
                    "name": "strict-capture",
                    "kind": "reset",
                    "payload": {},
                    "settle_seconds": 0.0,
                    "capture_seconds": 1.0,
                }
            ]
        )
        boolean_version["schema_version"] = True
        with self.assertRaisesRegex(BrowserCaptureFailure, "unsupported scenario"):
            parse_browser_scenario_program(boolean_version, fps=24.0)


if __name__ == "__main__":
    unittest.main()
