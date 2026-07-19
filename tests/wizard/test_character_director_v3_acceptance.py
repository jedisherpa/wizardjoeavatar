import copy
import unittest
from unittest.mock import patch

from tools.analyze_character_director_v3 import (
    CAST_SCENARIOS,
    EXPECTED_FRAME_COUNTS,
    EXPECTED_MARKERS,
    EXPECTED_SCENARIOS,
    analyze_v3,
    _staff_raster,
)
from wizard_avatar.reference_avatar import get_reference_pose


def fixture():
    manifest = {
        "scenario_program": {
            "program_id": "v3-canonical-cast",
            "acceptance_scenario": "V3",
            "total_duration_seconds": 11.5,
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
        is_cast = scenario in CAST_SCENARIOS
        for local_frame in range(EXPECTED_FRAME_COUNTS[scenario]):
            manifest["frames"].append(
                {
                    "frame_index": frame_index,
                    "capture_owned": True,
                    "scenario": scenario,
                }
            )
            active_cast = is_cast and local_frame < 32
            authored_frame = local_frame if active_cast else 0
            pose_id = f"cast_front_{authored_frame:02d}" if active_cast else "front_idle"
            pose = get_reference_pose(pose_id)
            marker_events = []
            for marker_id, marker_frame in EXPECTED_MARKERS:
                if active_cast and authored_frame == marker_frame:
                    marker_events.append(
                        {
                            "marker_id": marker_id,
                            "animation_authored_frame": marker_frame,
                        }
                    )
            effect_phase = "inactive"
            effect_intensity = 0.0
            if active_cast and 14 <= authored_frame < 18:
                effect_phase = "stroke"
                effect_intensity = 1.0
            elif active_cast and 18 <= authored_frame < 23:
                effect_phase = "hold"
                effect_intensity = 1.0
            elif active_cast and 23 <= authored_frame < 28:
                effect_phase = "recovery"
                effect_intensity = (28 - authored_frame) / 5.0
            traces.append(
                {
                    "frame_index": frame_index,
                    "rendered_pose_id": pose_id,
                    "animation_clip_id": "cast_front" if active_cast else "idle_front",
                    "animation_authored_frame": authored_frame,
                    "presentation_marker_events": marker_events,
                    "world_root_x": 0.0,
                    "world_root_z": 5.0,
                    "presented_root_stage": {"x": 120.0, "y": 127.0},
                    "render_scale_x": 1.0,
                    "render_scale_y": 1.0,
                    "staff_tip_local": {
                        "x": pose.anchors["staff_tip"][0],
                        "y": pose.anchors["staff_tip"][1],
                    },
                    "staff_tip_stage": {
                        "x": 120.0 + pose.anchors["staff_tip"][0] - pose.root_anchor[0],
                        "y": 127.0 + pose.anchors["staff_tip"][1] - pose.root_anchor[1],
                    },
                    "effect_phase": effect_phase,
                    "effect_intensity": effect_intensity,
                    "silhouette_raster_span": {
                        "min_x": 78,
                        "max_x": 164,
                        "min_y": 20,
                        "max_y": 126,
                    },
                }
            )
            frame_index += 1
    return manifest, traces


def check(report, name):
    return next(item for item in report["checks"] if item["name"] == name)


class CharacterDirectorV3AcceptanceTests(unittest.TestCase):
    def test_complete_canonical_cast_fixture_passes(self):
        manifest, traces = fixture()

        report = analyze_v3(manifest, traces)

        self.assertTrue(report["passed"], report)
        self.assertEqual(report["metrics"]["frame_count"], 276)
        self.assertEqual(report["metrics"]["staff_continuity_failure_count"], 0)

    def test_staff_jump_and_missing_marker_fail_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        first_cast = next(
            trace
            for trace in broken
            if trace["animation_clip_id"] == "cast_front"
            and trace["animation_authored_frame"] == 15
        )
        first_cast["staff_tip_local"]["x"] += 10
        first_cast["presentation_marker_events"] = []
        effect = next(
            trace
            for trace in broken
            if trace["animation_clip_id"] == "cast_front"
            and trace["animation_authored_frame"] == 14
        )
        effect["presentation_marker_events"] = []

        report = analyze_v3(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "continuous_repeatable_staff_arc")["passed"])
        self.assertFalse(check(report, "authored_marker_order_per_cast")["passed"])

    def test_exact_terminal_neutral_may_follow_cast_capture(self):
        manifest, traces = fixture()
        for trace in traces:
            if (
                trace["animation_clip_id"] == "cast_front"
                and trace["animation_authored_frame"] == 31
            ):
                trace["animation_authored_frame"] = 30
                trace["rendered_pose_id"] = "cast_front_30"
                pose = get_reference_pose("cast_front_30")
                trace["staff_tip_local"] = {
                    "x": pose.anchors["staff_tip"][0],
                    "y": pose.anchors["staff_tip"][1],
                }

        report = analyze_v3(manifest, traces)

        self.assertTrue(report["passed"], report)
        coverage = check(report, "authored_coverage_and_terminal_neutral")
        self.assertTrue(coverage["passed"])
        self.assertTrue(coverage["detail"]["terminal_frame_31_is_exact_neutral"])

    def test_boundary_transport_frame_and_latched_marker_event_are_accepted(self):
        manifest, traces = fixture()
        first_hold = next(
            index
            for index, frame in enumerate(manifest["frames"])
            if frame["scenario"] == "v3-hold-one"
        )
        boundary_index = manifest["frames"][first_hold]["frame_index"]
        manifest["frames"].insert(
            first_hold,
            {
                "frame_index": boundary_index,
                "capture_owned": False,
                "scenario": None,
            },
        )
        boundary_trace = copy.deepcopy(traces[boundary_index - 1])
        boundary_trace["frame_index"] = boundary_index
        traces.insert(boundary_index, boundary_trace)
        for frame in manifest["frames"][first_hold + 1 :]:
            frame["frame_index"] += 1
        for trace in traces[boundary_index + 1 :]:
            trace["frame_index"] += 1

        marker_sample = next(
            trace
            for trace in traces
            if trace["animation_clip_id"] == "cast_front"
            and trace["animation_authored_frame"] == 14
            and trace["presentation_marker_events"]
        )
        pose = get_reference_pose("cast_front_13")
        marker_sample["animation_authored_frame"] = 13
        marker_sample["rendered_pose_id"] = "cast_front_13"
        marker_sample["staff_tip_local"] = {
            "x": pose.anchors["staff_tip"][0],
            "y": pose.anchors["staff_tip"][1],
        }

        report = analyze_v3(manifest, traces)

        self.assertTrue(report["passed"], report)
        capture = check(report, "complete_contiguous_capture")
        self.assertEqual(capture["detail"]["unowned_transition_frame_indexes"], [60])
        coverage = check(report, "authored_coverage_and_terminal_neutral")
        self.assertTrue(coverage["passed"])

    def test_each_cast_must_present_complete_recovery(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        first_cast_indexes = {
            frame["frame_index"]
            for frame in manifest["frames"]
            if frame["scenario"] == "v3-cast-one"
        }
        for trace in broken:
            if trace["frame_index"] in first_cast_indexes and trace.get(
                "animation_authored_frame"
            ) == 26:
                trace["animation_authored_frame"] = 27
                trace["rendered_pose_id"] = "cast_front_27"

        report = analyze_v3(manifest, broken)

        self.assertFalse(report["passed"])
        coverage = check(report, "authored_coverage_and_terminal_neutral")
        self.assertFalse(coverage["passed"])
        self.assertNotIn(26, coverage["detail"]["recovery_coverage_per_cast"]["v3-cast-one"])

    def test_full_staff_raster_discontinuity_fails_closed(self):
        manifest, traces = fixture()

        def broken_raster(pose_id):
            raster = dict(_staff_raster(pose_id))
            if pose_id == "cast_front_15":
                raster[(0, 0)] = (255, 0, 255)
            return raster

        with patch(
            "tools.analyze_character_director_v3._staff_raster",
            side_effect=broken_raster,
        ):
            report = analyze_v3(manifest, traces)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "full_staff_raster_object_continuity")["passed"])


if __name__ == "__main__":
    unittest.main()
