import copy
import math
import unittest

from tools.analyze_character_director_v5 import (
    EXPECTED_FRAME_COUNTS,
    EXPECTED_SCENARIOS,
    analyze_v5,
)


def _trace(frame_index, root_z, clip_id, pose_id, contact, markers=()):
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
            pose, contact, clip = "front_idle", "both_feet", "idle_front"
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

    def test_missing_cycle_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        event_trace = next(
            trace
            for trace in reversed(broken)
            if trace["presentation_marker_events"]
        )
        event_trace["presentation_marker_events"] = []

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
