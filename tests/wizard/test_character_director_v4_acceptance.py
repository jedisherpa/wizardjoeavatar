import copy
import unittest

from tools.analyze_character_director_v4 import (
    EXPLAIN_SCENARIOS,
    EXPECTED_FRAME_COUNTS,
    EXPECTED_SCENARIOS,
    POINT_SCENARIO,
    analyze_v4,
)
from wizard_avatar.animation_graph import load_reference_animation_graph_v2


def _frame_sample(clip_id, frame):
    clip = load_reference_animation_graph_v2().clips[clip_id]
    cursor = 0
    for sample in clip.samples:
        if frame < cursor + sample.duration_frames:
            return sample, frame - cursor
        cursor += sample.duration_frames
    raise AssertionError((clip_id, frame))


def fixture():
    manifest = {
        "scenario_program": {
            "program_id": "v4-thought-groups",
            "acceptance_scenario": "V4",
            "total_duration_seconds": 6.75,
        },
        "scenarios": [{"name": name} for name in EXPECTED_SCENARIOS],
        "init": {"cols": 240, "rows": 135, "fps": 24.0},
        "contact_verification": {
            "passed": True,
            "maximum_planted_drift_cells": 0.0,
        },
        "frames": [],
    }
    traces = []
    frame_index = 0
    for scenario in EXPECTED_SCENARIOS:
        clip_id = None
        if scenario in EXPLAIN_SCENARIOS:
            clip_id = "explain_front"
        elif scenario == POINT_SCENARIO:
            clip_id = "point_front"
        total = load_reference_animation_graph_v2().clips[clip_id].total_frames if clip_id else 0
        for local_frame in range(EXPECTED_FRAME_COUNTS[scenario]):
            manifest["frames"].append(
                {
                    "frame_index": frame_index,
                    "capture_owned": True,
                    "scenario": scenario,
                }
            )
            markers = []
            if clip_id and local_frame < total:
                sample, sample_frame = _frame_sample(clip_id, local_frame)
                pose_id = sample.pose_id
                authored_frame = local_frame
                rendered_clip_id = clip_id
                for marker in sample.markers:
                    if marker.frame_offset == sample_frame:
                        markers.append(
                            {
                                "marker_id": marker.marker_id,
                                "animation_authored_frame": authored_frame,
                            }
                        )
            else:
                pose_id = "front_idle"
                authored_frame = 0
                rendered_clip_id = "idle_front"
            traces.append(
                {
                    "frame_index": frame_index,
                    "rendered_pose_id": pose_id,
                    "animation_clip_id": rendered_clip_id,
                    "animation_authored_frame": authored_frame,
                    "presentation_marker_events": markers,
                    "world_root_x": 0.0,
                    "world_root_z": 5.0,
                    "presented_root_stage": {"x": 120.0, "y": 127.0},
                    "silhouette_raster_span": {
                        "min_x": 72,
                        "max_x": 168,
                        "min_y": 18,
                        "max_y": 126,
                    },
                }
            )
            frame_index += 1
    return manifest, traces


def check(report, name):
    return next(item for item in report["checks"] if item["name"] == name)


class CharacterDirectorV4AcceptanceTests(unittest.TestCase):
    def test_complete_thought_group_fixture_passes(self):
        manifest, traces = fixture()

        report = analyze_v4(manifest, traces)

        self.assertTrue(report["passed"], report)
        self.assertEqual(report["metrics"]["frame_count"], 162)
        self.assertEqual(report["metrics"]["stroke_count"], 3)

    def test_first_owned_gesture_frame_may_follow_bounded_transition(self):
        manifest, traces = fixture()
        for scenario in (*EXPLAIN_SCENARIOS, POINT_SCENARIO):
            first_frame_index = next(
                frame["frame_index"]
                for frame in manifest["frames"]
                if frame["scenario"] == scenario
            )
            first_trace = next(
                trace for trace in traces if trace["frame_index"] == first_frame_index
            )
            first_trace["animation_authored_frame"] = 1

        report = analyze_v4(manifest, traces)

        self.assertTrue(report["passed"], report)

    def test_missing_stroke_and_non_neutral_hold_fail_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        stroke = next(
            trace
            for trace in broken
            if trace["animation_clip_id"] == "point_front"
            and any(
                event["marker_id"] == "action_effect"
                for event in trace["presentation_marker_events"]
            )
        )
        stroke["presentation_marker_events"] = []
        hold = next(
            trace
            for trace in broken
            if trace["frame_index"]
            == next(
                frame["frame_index"]
                for frame in manifest["frames"]
                if frame["scenario"] == "v4-thought-one-hold"
            )
        )
        hold["rendered_pose_id"] = "explaining"

        report = analyze_v4(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "three_motivated_strokes_in_authored_order")["passed"])
        self.assertFalse(check(report, "thought_group_holds_and_recovery")["passed"])

    def test_root_drift_and_clipping_fail_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        action = next(trace for trace in broken if trace["animation_clip_id"] == "explain_front")
        action["presented_root_stage"]["x"] += 2.0
        action["silhouette_raster_span"]["max_x"] = 240

        report = analyze_v4(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "planted_root_during_all_gestures")["passed"])
        self.assertFalse(check(report, "gesture_silhouettes_within_canonical_stage")["passed"])

    def test_missing_observed_point_frame_fails_closed(self):
        manifest, traces = fixture()
        broken = [
            trace
            for trace in traces
            if not (
                trace["animation_clip_id"] == "point_front"
                and trace["animation_authored_frame"] == 8
            )
        ]
        missing_index = next(
            frame["frame_index"]
            for frame in manifest["frames"]
            if frame["scenario"] == POINT_SCENARIO
            and frame["frame_index"] not in {trace["frame_index"] for trace in broken}
        )
        manifest["frames"] = [
            frame for frame in manifest["frames"] if frame["frame_index"] != missing_index
        ]

        report = analyze_v4(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "thought_group_holds_and_recovery")["passed"])


if __name__ == "__main__":
    unittest.main()
