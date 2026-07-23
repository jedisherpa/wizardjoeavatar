import copy
import unittest

from tools.analyze_character_director_v6 import (
    EXPECTED_FRAME_COUNTS,
    EXPECTED_SCENARIOS,
    EXPECTED_SCENARIO_SPECS,
    analyze_v6,
)
from wizard_avatar.animation_graph import load_pose_catalog
from wizard_avatar.reference_avatar import reference_pose_anchor


POSE_CATALOG = load_pose_catalog()


def fixture():
    manifest = {
        "scenario_program": {
            "program_id": "v6-directional-walk",
            "acceptance_scenario": "V6",
            "total_duration_seconds": 9.25,
        },
        "scenarios": copy.deepcopy(list(EXPECTED_SCENARIO_SPECS)),
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
        facing = POSE_CATALOG[pose].facing
        staff_tip = reference_pose_anchor(pose, "staff_tip")
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
                "presented_root_stage": {"x": 0.0, "y": 0.0},
                "staff_tip_stage": {"x": staff_tip[0], "y": staff_tip[1]},
                "render_scale_x": 1.0,
                "render_scale_y": 1.0,
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

    east_turn_poses = (
        "walk_front_right",
        "turn_front_to_right_entry_250",
        "turn_front_to_right_entry_500",
        "turn_front_to_right_entry_750",
        "hd_turn_right_anticipation",
        "hd_turn_right_mid",
        "hd_turn_right_complete",
        "walk_profile_right_contact_left",
    )
    right_gait = (
        "walk_profile_right_contact_left",
        "walk_profile_right_passing_left_to_right",
        "walk_profile_right_contact_right",
        "walk_profile_right_passing_right_to_left",
    )
    left_gait = (
        "walk_profile_left_contact_left",
        "walk_profile_left_passing_left_to_right",
        "walk_profile_left_contact_right",
        "walk_profile_left_passing_right_to_left",
    )

    for local in range(EXPECTED_FRAME_COUNTS["v6-turn-east"]):
        progress = (local + 1) / EXPECTED_FRAME_COUNTS["v6-turn-east"]
        facing = "south" if local < 4 else ("southeast" if local < 8 else "east")
        support = contact(local)
        if local < 24:
            clip = "turn_front_to_east"
            pose = east_turn_poses[min(local // 3, len(east_turn_poses) - 1)]
        else:
            clip = "walk_right"
            pose = right_gait[((local - 24) // 4) % len(right_gait)]
            if local == 24:
                support = "left_foot"
        append("v6-turn-east", (2.4 * progress, 3.8), facing, clip, pose, support)

    moving_frames = 95
    reversal_poses = (
        "walk_profile_right_contact_right",
        "hd_turn_right_complete",
        "hd_turn_right_mid",
        "hd_turn_right_anticipation",
        "hd_turn_front_neutral",
        "hd_turn_left_anticipation",
        "hd_turn_left_mid",
        "turn_left_mid_to_complete_166",
        "turn_left_mid_to_complete_333",
        "turn_left_mid_to_complete_500",
        "turn_left_mid_to_complete_667",
        "turn_left_mid_to_complete_833",
        "hd_turn_left_complete",
        "walk_profile_left_contact_left",
    )
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
        if local < 42:
            clip = "reverse_east_to_west"
            pose = reversal_poses[min(local // 3, len(reversal_poses) - 1)]
        elif local < 96:
            clip = "walk_left"
            pose = left_gait[((local - 42) // 4) % len(left_gait)]
            if local == 42:
                support = "left_foot"
        else:
            clip = "stop_left"
            stop_poses = (
                "walk_profile_left_passing_left_to_right",
                "stop_profile_left_hd_settle_200",
                "stop_profile_left_hd_settle_400",
                "stop_profile_left_hd_settle_600",
                "stop_profile_left_hd_settle_800",
                "hd_turn_left_complete",
            )
            pose = stop_poses[min((local - 96) // 2, len(stop_poses) - 1)]
            support = (
                "both_feet"
                if pose in {
                    "stop_profile_left_hd_settle_600",
                    "stop_profile_left_hd_settle_800",
                    "hd_turn_left_complete",
                }
                else "left_foot"
            )
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

    def test_short_east_target_fails_directional_scenario_gate(self):
        manifest, traces = fixture()
        turn = next(
            scenario
            for scenario in manifest["scenarios"]
            if scenario["name"] == "v6-turn-east"
        )
        turn["payload"]["x"] = 1.6
        report = analyze_v6(manifest, traces)
        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "scenario_directional_targets")["passed"])

    def test_pose_facing_mismatch_fails_body_alignment_gate(self):
        manifest, traces = fixture()
        damaged = copy.deepcopy(traces)
        target = next(
            trace
            for trace in damaged
            if trace["rendered_pose_id"] == "hd_turn_right_mid"
        )
        target["presented_facing"] = "east"
        report = analyze_v6(manifest, damaged)
        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "rendered_pose_facing_alignment")["passed"])

    def test_staff_tip_teleport_fails_continuity_gate(self):
        manifest, traces = fixture()
        damaged = copy.deepcopy(traces)
        target = next(
            trace
            for trace in damaged
            if trace["rendered_pose_id"] == "turn_left_mid_to_complete_500"
        )
        target["staff_tip_stage"]["x"] += 30.0
        report = analyze_v6(manifest, damaged)
        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "turn_staff_path_continuity")["passed"])

    def test_static_profile_stop_fails_performed_settle_gate(self):
        manifest, traces = fixture()
        damaged = copy.deepcopy(traces)
        for trace in damaged:
            if trace["animation_clip_id"] == "stop_left":
                trace["rendered_pose_id"] = "profile_left"
        report = analyze_v6(manifest, damaged)
        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "target_stop_and_profile_settle")["passed"])

    def test_front_pose_used_for_side_travel_fails_alignment(self):
        manifest, traces = fixture()
        damaged = copy.deepcopy(traces)
        for trace in damaged:
            if trace["animation_clip_id"] == "walk_right":
                trace["rendered_pose_id"] = "walk_front_right"
        report = analyze_v6(manifest, damaged)
        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "directional_profile_clip_alignment")["passed"])

    def test_placeholder_profile_and_missing_turn_inbetweens_fail_topology(self):
        manifest, traces = fixture()
        damaged = copy.deepcopy(traces)
        for trace in damaged:
            if trace["animation_clip_id"] == "walk_right":
                trace["rendered_pose_id"] = "profile_right"
            if trace["animation_clip_id"] == "turn_front_to_east":
                trace["rendered_pose_id"] = "walk_front_right"
        report = analyze_v6(manifest, damaged)
        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "directional_profile_clip_alignment")["passed"])
        self.assertFalse(check(report, "authored_turn_reversal_pose_topology")["passed"])

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
