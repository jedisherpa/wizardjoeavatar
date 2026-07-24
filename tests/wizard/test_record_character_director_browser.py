import json
import unittest
from pathlib import Path

from tools.record_character_director_browser import (
    BrowserCaptureFailure,
    parse_browser_scenario_program,
    scenario_capture_events,
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
