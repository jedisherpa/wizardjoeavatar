import copy
import unittest

from tools.analyze_character_director_v8 import (
    EXPECTED_FRAMES,
    EXPECTED_GESTURES,
    EXPECTED_SPEECH_IDS,
    SCENARIO,
    analyze_v8,
)


def fixture():
    phrase = "The same clear idea deserves a fresh, deliberate performance."
    schedule = [
        ("v8-phrase-one", 96, "speak", {"speech_id": EXPECTED_SPEECH_IDS[0], "text": phrase}),
        ("v8-gesture-one", 192, "action", {"action": "explaining"}),
        ("v8-listen-left", 288, "gaze", {"target": "left"}),
        ("v8-return-viewer-one", 336, "gaze", {"target": "viewer"}),
        ("v8-phrase-two", 432, "speak", {"speech_id": EXPECTED_SPEECH_IDS[1], "text": phrase}),
        ("v8-gesture-two", 528, "action", {"action": "pointing"}),
        ("v8-listen-right", 624, "gaze", {"target": "right"}),
        ("v8-return-viewer-two", 672, "gaze", {"target": "viewer"}),
        ("v8-phrase-three", 768, "speak", {"speech_id": EXPECTED_SPEECH_IDS[2], "text": phrase}),
        ("v8-gesture-three", 864, "action", {"action": "explaining"}),
        ("v8-listen-up", 960, "gaze", {"target": "up"}),
        ("v8-final-viewer-hold", 1008, "gaze", {"target": "viewer"}),
    ]
    commands = [
        {
            "scenario": SCENARIO,
            "source_sequence": 1,
            "capture_planned_frame_count": EXPECTED_FRAMES,
        }
    ]
    for source_sequence, (name, at_frame, kind, payload) in enumerate(schedule, start=2):
        commands.append(
            {
                "scenario": name,
                "scheduled_for_scenario": SCENARIO,
                "scheduled_at_frame": at_frame,
                "dispatch_observed_after_frame_count": at_frame,
                "dispatch_completed_after_frame_count": at_frame + 1,
                "source_sequence": source_sequence,
                "kind": kind,
                "payload": payload,
                "ack": {"disposition": "applied"},
            }
        )

    manifest = {
        "scenario_program": {
            "schema": "character_director_scenario_program_v2",
            "schema_version": 2,
            "program_id": "v8-purposeful-performance",
            "acceptance_scenario": "V8",
            "maximum_capture_frame_count": EXPECTED_FRAMES,
        },
        "commands": commands,
        "init": {"cols": 240, "rows": 135, "fps": 24.0},
        "contact_verification": {"passed": True},
        "frames": [
            {
                "frame_index": index,
                "capture_owned": True,
                "scenario": SCENARIO,
            }
            for index in range(EXPECTED_FRAMES)
        ],
    }

    blink_starts = (60, 180, 315, 465, 590, 730, 860, 1015, 1135, 1270, 1420)
    speech_ranges = {
        EXPECTED_SPEECH_IDS[0]: range(97, 159),
        EXPECTED_SPEECH_IDS[1]: range(433, 495),
        EXPECTED_SPEECH_IDS[2]: range(769, 831),
    }
    gesture_ranges = (
        range(193, 223),
        range(529, 559),
        range(865, 895),
    )
    effect_frames = {205, 541, 877}
    traces = []
    for index in range(EXPECTED_FRAMES):
        speech_id = next(
            (key for key, values in speech_ranges.items() if index in values),
            None,
        )
        gesture_index = next(
            (
                number
                for number, values in enumerate(gesture_ranges)
                if index in values
            ),
            None,
        )
        body_hash = (
            "gesture-{}-{}".format(
                gesture_index,
                index - gesture_ranges[gesture_index].start,
            )
            if gesture_index is not None
            else "idle-head-breath"
            if 1395 <= index < 1399
            else "idle-body"
        )
        gaze = -1 if 288 <= index < 336 else 1 if 624 <= index < 672 else 0
        vertical_gaze = 1 if 960 <= index < 1008 else 0
        blink_closed = any(start <= index < start + 3 for start in blink_starts)
        traces.append(
            {
                "frame_index": index,
                "rendered_pose_id": (
                    "gesture-{}".format(gesture_index)
                    if gesture_index is not None
                    else "front_idle"
                ),
                "presentation_marker_events": (
                    [{"marker_id": "action_effect"}]
                    if index in effect_frames
                    else []
                ),
                "presented_root_stage": {"x": 120.0, "y": 126.0},
                "silhouette_raster_span": {
                    "min_x": 78,
                    "max_x": 164,
                    "min_y": 18,
                    "max_y": 126,
                },
                "presentation_channels": {
                    "action": (
                        "speaking"
                        if speech_id is not None
                        else "explaining"
                        if gesture_index is not None
                        else "idle"
                    ),
                    "speech_id": speech_id,
                    "body_pixel_sha256": body_hash,
                    "gaze_aim": gaze,
                    "gaze_vertical_aim": vertical_gaze,
                    "blink_closed": blink_closed,
                    "head_offset_x": 0,
                    "head_offset_y": -1 if 1395 <= index < 1399 else 0,
                },
            }
        )
    return manifest, traces


def check(report, name):
    return next(item for item in report["checks"] if item["name"] == name)


class CharacterDirectorV8AcceptanceTests(unittest.TestCase):
    def test_continuous_purposeful_performance_passes(self):
        manifest, traces = fixture()

        report = analyze_v8(manifest, traces)

        self.assertTrue(report["passed"], report)
        self.assertEqual(report["metrics"]["owned_frame_count"], EXPECTED_FRAMES)
        self.assertEqual(report["metrics"]["gesture_effect_count"], 3)

    def test_changed_repeated_phrase_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(manifest)
        phrase_two = next(
            command
            for command in broken["commands"]
            if command["scenario"] == "v8-phrase-two"
        )
        phrase_two["payload"]["text"] = "This is no longer the same phrase."

        report = analyze_v8(broken, traces)

        self.assertFalse(report["passed"])
        self.assertFalse(
            check(report, "three_identical_phrases_with_distinct_identity")["passed"]
        )

    def test_missing_gesture_effect_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        marker_trace = next(
            trace for trace in broken if trace["presentation_marker_events"]
        )
        marker_trace["presentation_marker_events"] = []

        report = analyze_v8(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "three_deliberate_gestures")["passed"])

    def test_mechanical_blink_cadence_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        for trace in broken:
            trace["presentation_channels"]["blink_closed"] = (
                trace["frame_index"] % 120 < 3
            )

        report = analyze_v8(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "varied_natural_blinks")["passed"])

    def test_blink_with_body_or_root_change_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        broken[61]["presentation_channels"]["body_pixel_sha256"] = "moving-body"
        broken[62]["presented_root_stage"]["x"] = 121.0

        report = analyze_v8(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(
            check(report, "blink_body_and_root_stability")["passed"]
        )

    def test_blink_interval_outside_contract_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        for trace in broken:
            trace["presentation_channels"]["blink_closed"] = False
        starts = (60, 120, 181, 243, 306, 370, 435, 501, 668)
        for start in starts:
            for index in range(start, start + 3):
                broken[index]["presentation_channels"]["blink_closed"] = True

        report = analyze_v8(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "varied_natural_blinks")["passed"])


if __name__ == "__main__":
    unittest.main()
