import copy
import math
import unittest

from tools.analyze_character_director_v5 import (
    EXPECTED_FRAME_COUNTS,
    EXPECTED_SCENARIOS,
    analyze_v5,
)


def _trace(frame_index, root_z, clip_id, pose_id, contact, markers=()):
    if pose_id in {
        "walk_front_right",
        "stop_front_from_right_25",
        "stop_front_from_right_50",
        "stop_front_from_right_625",
    }:
        body_hash = "atomic-walk-contact"
    elif pose_id in {
        "stop_front_from_right_75",
        "stop_front_from_right_875",
        "stop_front_from_right_100",
    }:
        body_hash = "atomic-idle-recovery"
    else:
        body_hash = f"authored-{pose_id}"
    return {
        "frame_index": frame_index,
        "world_root_x": 0.0,
        "world_root_z": root_z,
        "animation_clip_id": clip_id,
        "rendered_pose_id": pose_id,
        "support_contact": contact,
        "presentation_marker_events": [
            {"marker_id": marker, "animation_authored_frame": 15}
            for marker in markers
        ],
        "presentation_channels": {"body_pixel_sha256": body_hash},
        "silhouette_raster_span": {
            "min_x": 72,
            "max_x": 168,
            "min_y": 18,
            "max_y": 126,
        },
    }


def fixture():
    manifest = {
        "scenario_program": {
            "program_id": "v5-front-walk",
            "acceptance_scenario": "V5",
            "total_duration_seconds": 4.25,
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

    def append(scenario, trace):
        nonlocal frame_index
        manifest["frames"].append(
            {
                "frame_index": frame_index,
                "capture_owned": True,
                "scenario": scenario,
            }
        )
        trace["frame_index"] = frame_index
        trace["simulation_tick"] = frame_index * 3
        traces.append(trace)
        frame_index += 1

    for _ in range(EXPECTED_FRAME_COUNTS["v5-idle"]):
        append(
            "v5-idle",
            _trace(0, 5.0, "idle_front", "front_idle", "both_feet"),
        )

    raw_steps = [0.015, 0.035, 0.05] + [0.052] * 38 + [
        0.050,
        0.046,
        0.042,
        0.038,
        0.034,
        0.030,
        0.026,
        0.022,
        0.018,
        0.014,
        0.009,
        0.004,
    ]
    scale = 2.55 / sum(raw_steps)
    steps = [value * scale for value in raw_steps]
    stop_poses = (
        [("walk_front_right", "right_foot")] * 2
        + [("stop_front_from_right_25", "right_foot")] * 2
        + [("stop_front_from_right_50", "right_foot")] * 2
        + [("stop_front_from_right_625", "right_foot")]
        + [("stop_front_from_right_75", "right_foot")]
        + [("stop_front_from_right_875", "right_foot")]
        + [("stop_front_from_right_100", "right_foot")]
        + [("front_idle", "both_feet")] * 3
    )
    cumulative = 0.0
    completed_cycles = 0
    for local_frame in range(EXPECTED_FRAME_COUNTS["v5-three-cycle-walk"]):
        markers = []
        if local_frame < len(steps):
            cumulative += steps[local_frame]
            new_cycles = min(3, int(math.floor((cumulative + 1e-9) / 0.85)))
            if new_cycles > completed_cycles:
                markers.append("loop_boundary")
                completed_cycles = new_cycles
            phase = (cumulative / 0.85) % 1.0
            if phase < 0.25:
                pose, contact = "walk_front_left", "left_foot"
            elif phase < 0.5:
                pose, contact = "walk_front_left_to_right", "none"
            elif phase < 0.75:
                pose, contact = "walk_front_right", "right_foot"
            else:
                pose, contact = "walk_front_right_to_left", "none"
            clip = "walk_front"
        else:
            pose, contact = stop_poses[local_frame - len(steps)]
            clip = "stop_front_right"
        append(
            "v5-three-cycle-walk",
            _trace(0, 5.0 - cumulative, clip, pose, contact, markers),
        )

    for _ in range(EXPECTED_FRAME_COUNTS["v5-stop-settle"]):
        append(
            "v5-stop-settle",
            _trace(0, 2.45, "idle_front", "front_idle", "both_feet"),
        )
    return manifest, traces


def check(report, name):
    return next(item for item in report["checks"] if item["name"] == name)


class CharacterDirectorV5AcceptanceTests(unittest.TestCase):
    def test_complete_three_cycle_walk_passes(self):
        manifest, traces = fixture()

        report = analyze_v5(manifest, traces)

        self.assertTrue(report["passed"], report)
        self.assertEqual(report["metrics"]["loop_boundary_count"], 3)
        self.assertAlmostEqual(report["metrics"]["displacement"], 2.55)

    def test_single_leading_transport_boundary_is_bounded(self):
        manifest, traces = fixture()
        for frame in manifest["frames"]:
            frame["frame_index"] += 1
        for trace in traces:
            trace["frame_index"] += 1
            trace["simulation_tick"] += 3
        manifest["frames"].insert(
            0,
            {"frame_index": 0, "capture_owned": False, "scenario": None},
        )
        leading = copy.deepcopy(traces[0])
        leading["frame_index"] = 0
        leading["simulation_tick"] = 0
        traces.insert(0, leading)

        report = analyze_v5(manifest, traces)

        self.assertTrue(report["passed"], report)
        self.assertTrue(check(report, "complete_contiguous_capture")["passed"])

    def test_missing_cycle_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        settle_indexes = {
            frame["frame_index"]
            for frame in manifest["frames"]
            if frame["scenario"] == "v5-stop-settle"
        }
        for trace in broken:
            if trace["frame_index"] in settle_indexes:
                trace["world_root_z"] = 3.30

        report = analyze_v5(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "three_complete_distance_driven_cycles")["passed"])

    def test_constant_speed_snap_stop_fails_deceleration_gate(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        walk_indexes = [
            frame["frame_index"]
            for frame in manifest["frames"]
            if frame["scenario"] == "v5-three-cycle-walk"
        ]
        for offset, frame_index in enumerate(walk_indexes):
            trace = next(item for item in broken if item["frame_index"] == frame_index)
            progress = min(1.0, (offset + 1) / 49.0)
            trace["world_root_z"] = 5.0 - 2.55 * progress

        report = analyze_v5(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "decelerated_stop_profile")["passed"])

    def test_missing_authored_stop_inbetween_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        for trace in broken:
            if trace["rendered_pose_id"] == "stop_front_from_right_50":
                trace["rendered_pose_id"] = "stop_front_from_right_75"

        report = analyze_v5(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "front_walk_pose_and_stop_settle")["passed"])

    def test_partial_stop_topology_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        for trace in broken:
            if trace["rendered_pose_id"] == "stop_front_from_right_625":
                trace["presentation_channels"]["body_pixel_sha256"] = "partial-row-wipe"

        report = analyze_v5(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "atomic_stop_pose_topology")["passed"])

    def test_contact_drift_target_error_and_clipping_fail_closed(self):
        manifest, traces = fixture()
        manifest["contact_verification"]["maximum_planted_drift_cells"] = 2.0
        broken = copy.deepcopy(traces)
        settle_indexes = {
            frame["frame_index"]
            for frame in manifest["frames"]
            if frame["scenario"] == "v5-stop-settle"
        }
        for trace in broken:
            if trace["frame_index"] in settle_indexes:
                trace["world_root_z"] = 2.65
        broken[0]["silhouette_raster_span"]["max_x"] = 240

        report = analyze_v5(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "alternating_contacts_without_planted_drift")["passed"])
        self.assertFalse(check(report, "front_walk_pose_and_stop_settle")["passed"])
        self.assertFalse(check(report, "walk_silhouette_within_canonical_stage")["passed"])


if __name__ == "__main__":
    unittest.main()
