import copy
import unittest

from tools.analyze_character_director_v6 import (
    EXPECTED_FRAME_COUNTS,
    EXPECTED_SCENARIOS,
    analyze_v6,
)


def fixture():
    manifest = {
        "scenario_program": {
            "program_id": "v6-directional-walk",
            "acceptance_scenario": "V6",
            "total_duration_seconds": 8.75,
        },
        "scenarios": [{"name": name} for name in EXPECTED_SCENARIOS],
        "init": {"cols": 240, "rows": 135, "fps": 24.0},
        "contact_verification": {
            "passed": True,
            "maximum_planted_drift_cells": 0.0,
            "maximum_planted_raster_span_drift_cells": 0.0,
        },
        "frames": [],
    }
    traces = []
    frame_index = 0

    def append(scenario, root, facing, clip, pose, contact):
        nonlocal frame_index
        manifest["frames"].append(
            {"frame_index": frame_index, "capture_owned": True, "scenario": scenario}
        )
        traces.append(
            {
                "frame_index": frame_index,
                "simulation_tick": frame_index * 3,
                "world_root_x": root[0],
                "world_root_z": root[1],
                "presented_facing": facing,
                "animation_clip_id": clip,
                "rendered_pose_id": pose,
                "support_contact": contact,
                "animation_phase_numerator": frame_index % 16,
                "animation_phase_denominator": 16,
                "silhouette_raster_span": {
                    "min_x": 72,
                    "max_x": 168,
                    "min_y": 18,
                    "max_y": 126,
                },
            }
        )
        frame_index += 1

    for _ in range(EXPECTED_FRAME_COUNTS["v6-idle"]):
        append("v6-idle", (0.0, 5.0), "south", "idle_front", "front_idle", "both_feet")

    def contact(local):
        phase = local % 16
        if phase < 4:
            return "left_foot"
        if 8 <= phase < 12:
            return "right_foot"
        return "none"

    for local in range(EXPECTED_FRAME_COUNTS["v6-south-approach"]):
        progress = (local + 1) / EXPECTED_FRAME_COUNTS["v6-south-approach"]
        support = contact(local)
        pose = "walk_front_left" if support == "left_foot" else (
            "walk_front_right" if support == "right_foot" else "walk_front_left_to_right"
        )
        append("v6-south-approach", (0.0, 5.0 - 1.2 * progress), "south", "walk_front", pose, support)

    for local in range(EXPECTED_FRAME_COUNTS["v6-turn-east"]):
        progress = (local + 1) / EXPECTED_FRAME_COUNTS["v6-turn-east"]
        facing = "south" if local < 4 else ("southeast" if local < 8 else "east")
        support = contact(local)
        if local < 8:
            clip = "walk_front"
            pose = "walk_front_right" if support == "right_foot" else "walk_front_left"
        else:
            clip = "walk_right"
            pose = "profile_right" if support != "none" else "walk_profile_right_passing"
        append("v6-turn-east", (2.4 * progress, 3.8), facing, clip, pose, support)

    moving_frames = 95
    for local in range(EXPECTED_FRAME_COUNTS["v6-reverse-west"]):
        progress = min(1.0, (local + 1) / moving_frames)
        facing = (
            "east" if local < 4 else
            "southeast" if local < 8 else
            "south" if local < 12 else
            "southwest" if local < 16 else
            "west"
        )
        support = contact(local)
        if local < 8:
            clip = "walk_right"
            pose = "profile_right" if support != "none" else "walk_profile_right_passing"
        elif local < 98:
            clip = "walk_left"
            pose = "profile_left" if support != "none" else "walk_profile_left_passing"
        else:
            clip = "stop_left"
            pose = "walk_front_left"
            support = "left_foot"
        append("v6-reverse-west", (2.4 - 4.8 * progress, 3.8), facing, clip, pose, support)

    for _ in range(EXPECTED_FRAME_COUNTS["v6-stop-settle"]):
        append("v6-stop-settle", (-2.4, 3.8), "west", "idle_left", "profile_left", "both_feet")
    return manifest, traces


def check(report, name):
    return next(item for item in report["checks"] if item["name"] == name)


class CharacterDirectorV6AcceptanceTests(unittest.TestCase):
    def test_directional_turn_reversal_and_stop_pass(self):
        manifest, traces = fixture()
        report = analyze_v6(manifest, traces)
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["metrics"]["east_turn_sector_count"], 2)
        self.assertEqual(report["metrics"]["reversal_sector_count"], 4)

    def test_instant_facing_jump_fails_turn_gate(self):
        manifest, traces = fixture()
        east_indexes = [
            frame["frame_index"] for frame in manifest["frames"]
            if frame["scenario"] == "v6-turn-east"
        ]
        for frame_index in east_indexes:
            traces[frame_index]["presented_facing"] = "east"
        report = analyze_v6(manifest, traces)
        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "readable_90_degree_turn")["passed"])

    def test_front_pose_used_for_side_travel_fails_alignment(self):
        manifest, traces = fixture()
        damaged = copy.deepcopy(traces)
        for trace in damaged:
            if trace["animation_clip_id"] == "walk_right":
                trace["rendered_pose_id"] = "walk_front_right"
        report = analyze_v6(manifest, damaged)
        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "directional_profile_clip_alignment")["passed"])

    def test_contact_drift_root_jump_target_error_and_clipping_fail_closed(self):
        manifest, traces = fixture()
        manifest["contact_verification"]["maximum_planted_drift_cells"] = 2.0
        damaged = copy.deepcopy(traces)
        damaged[50]["world_root_x"] += 0.5
        damaged[-1]["world_root_x"] = -2.0
        damaged[0]["silhouette_raster_span"]["max_x"] = 240
        report = analyze_v6(manifest, damaged)
        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "contact_and_root_continuity")["passed"])
        self.assertFalse(check(report, "target_stop_and_profile_settle")["passed"])
        self.assertFalse(check(report, "directional_walk_within_canonical_stage")["passed"])


if __name__ == "__main__":
    unittest.main()
