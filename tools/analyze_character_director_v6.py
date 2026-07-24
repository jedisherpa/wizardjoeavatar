#!/usr/bin/env python3
"""Evaluate the machine-verifiable portion of Character Director scenario V6."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_character_director_visual_review import validate_manifest
from wizard_avatar.animation_graph import load_pose_catalog
from wizard_avatar.animation_trace import AnimationTruthTraceV1
from wizard_avatar.reference_avatar import reference_pose_anchor, reference_pose_root_anchor


REPORT_SCHEMA = "character_director_v6_machine_acceptance_v3"
EXPECTED_SCENARIOS = (
    "v6-idle",
    "v6-south-approach",
    "v6-turn-east",
    "v6-reverse-west",
    "v6-stop-settle",
)
EXPECTED_FRAME_COUNTS = {
    "v6-idle": 12,
    "v6-south-approach": 24,
    "v6-turn-east": 54,
    "v6-reverse-west": 108,
    "v6-stop-settle": 24,
}
EXPECTED_SCENARIO_SPECS = (
    {
        "name": "v6-idle",
        "kind": "reset",
        "payload": {},
        "settle_seconds": 0.0,
        "capture_seconds": 0.5,
    },
    {
        "name": "v6-south-approach",
        "kind": "move",
        "payload": {"x": 0.0, "z": 2.0, "speed": 1.25},
        "settle_seconds": 0.0,
        "capture_seconds": 1.0,
    },
    {
        "name": "v6-turn-east",
        "kind": "move",
        "payload": {"x": 2.4, "z": 3.8, "speed": 1.25},
        "settle_seconds": 0.0,
        "capture_seconds": 2.25,
    },
    {
        "name": "v6-reverse-west",
        "kind": "move",
        "payload": {"x": -2.4, "z": 3.8, "speed": 1.25},
        "settle_seconds": 0.0,
        "capture_seconds": 4.5,
    },
    {
        "name": "v6-stop-settle",
        "kind": "gaze",
        "payload": {"target": "viewer"},
        "settle_seconds": 0.0,
        "capture_seconds": 1.0,
    },
)
TARGET = (-2.4, 3.8)
FACINGS = (
    "south",
    "southwest",
    "west",
    "northwest",
    "north",
    "northeast",
    "east",
    "southeast",
)
WALK_CLIPS = {"walk_front", "walk_left", "walk_right"}
PROFILE_POSE_SEQUENCES = {
    "walk_left": (
        "walk_profile_left_contact_left",
        "walk_profile_left_contact_left_to_passing_250",
        "walk_profile_left_contact_left_to_passing_500",
        "walk_profile_left_contact_left_to_passing_750",
        "walk_profile_left_passing_left_to_right",
        "walk_profile_left_passing_to_contact_right_250",
        "walk_profile_left_passing_to_contact_right_500",
        "walk_profile_left_passing_to_contact_right_750",
        "walk_profile_left_contact_right",
        "walk_profile_left_contact_right_to_passing_250",
        "walk_profile_left_contact_right_to_passing_500",
        "walk_profile_left_contact_right_to_passing_750",
        "walk_profile_left_passing_right_to_left",
        "walk_profile_left_passing_to_contact_left_250",
        "walk_profile_left_passing_to_contact_left_500",
        "walk_profile_left_passing_to_contact_left_750",
    ),
    "walk_right": (
        "walk_profile_right_contact_left",
        "walk_profile_right_contact_left_to_passing_250",
        "walk_profile_right_contact_left_to_passing_500",
        "walk_profile_right_contact_left_to_passing_750",
        "walk_profile_right_passing_left_to_right",
        "walk_profile_right_passing_to_contact_right_250",
        "walk_profile_right_passing_to_contact_right_500",
        "walk_profile_right_passing_to_contact_right_750",
        "walk_profile_right_contact_right",
        "walk_profile_right_contact_right_to_passing_250",
        "walk_profile_right_contact_right_to_passing_500",
        "walk_profile_right_contact_right_to_passing_750",
        "walk_profile_right_passing_right_to_left",
        "walk_profile_right_passing_to_contact_left_250",
        "walk_profile_right_passing_to_contact_left_500",
        "walk_profile_right_passing_to_contact_left_750",
    ),
}
TRANSITION_POSE_SEQUENCES = {
    "turn_front_to_east": (
        "walk_front_right",
        "turn_front_to_right_entry_250",
        "turn_front_to_right_entry_500",
        "turn_front_to_right_entry_750",
        "hd_turn_right_anticipation",
        "hd_turn_right_mid",
        "hd_turn_right_complete",
        "walk_profile_right_contact_left",
    ),
    "reverse_east_to_west": (
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
    ),
}
STOP_LEFT_POSE_SEQUENCE = (
    "walk_profile_left_passing_left_to_right",
    "stop_profile_left_hd_settle_200",
    "stop_profile_left_hd_settle_400",
    "stop_profile_left_hd_settle_600",
    "stop_profile_left_hd_settle_800",
    "hd_turn_left_complete",
)
MAX_TURN_STAFF_TIP_STEP = 14.0
MAX_TURN_STAFF_GRIP_STEP = 12.5
DEPRECATED_PROFILE_POSES = {
    "profile_left",
    "profile_right",
    "walk_profile_left_passing",
    "walk_profile_right_passing",
}


def _check(report: Dict[str, Any], name: str, passed: bool, detail: object) -> None:
    report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})


def _root(trace: Mapping[str, Any]) -> Optional[Tuple[float, float]]:
    values = trace.get("world_root_x"), trace.get("world_root_z")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        return None
    point = float(values[0]), float(values[1])
    return point if all(math.isfinite(value) for value in point) else None


def _stage_point(trace: Mapping[str, Any], field: str) -> Optional[Tuple[float, float]]:
    value = trace.get(field)
    if not isinstance(value, Mapping):
        return None
    coordinates = value.get("x"), value.get("y")
    if any(
        isinstance(item, bool) or not isinstance(item, (int, float))
        for item in coordinates
    ):
        return None
    point = float(coordinates[0]), float(coordinates[1])
    return point if all(math.isfinite(item) for item in point) else None


def _pose_anchor_stage(
    trace: Mapping[str, Any],
    anchor_name: str,
) -> Optional[Tuple[float, float]]:
    pose_id = trace.get("rendered_pose_id")
    root_stage = _stage_point(trace, "presented_root_stage")
    if not isinstance(pose_id, str) or root_stage is None:
        return None
    scale_x = trace.get("render_scale_x")
    scale_y = trace.get("render_scale_y")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        for value in (scale_x, scale_y)
    ):
        return None
    try:
        anchor = reference_pose_anchor(pose_id, anchor_name)
        root = reference_pose_root_anchor(pose_id)
    except KeyError:
        return None
    return (
        root_stage[0] + (anchor[0] - root[0]) * float(scale_x),
        root_stage[1] + (anchor[1] - root[1]) * float(scale_y),
    )


def _adjacent_stage_steps(
    records: Sequence[Mapping[str, Any]],
    resolver,
) -> Tuple[List[float], List[Dict[str, Any]]]:
    steps: List[float] = []
    missing: List[Dict[str, Any]] = []
    for left, right in zip(records, records[1:]):
        if right.get("frame_index") != left.get("frame_index", -2) + 1:
            continue
        left_point = resolver(left)
        right_point = resolver(right)
        if left_point is None or right_point is None:
            missing.append(
                {
                    "left_frame": left.get("frame_index"),
                    "right_frame": right.get("frame_index"),
                }
            )
            continue
        steps.append(math.dist(left_point, right_point))
    return steps, missing


def _collapsed(records: Sequence[Mapping[str, Any]], field: str) -> List[str]:
    result: List[str] = []
    for record in records:
        value = record.get(field)
        if not isinstance(value, str):
            continue
        if not result or result[-1] != value:
            result.append(value)
    return result


def _collapsed_contacts(records: Sequence[Mapping[str, Any]]) -> List[str]:
    result: List[str] = []
    for record in records:
        value = record.get("support_contact")
        if value not in {"left_foot", "right_foot"}:
            continue
        if not result or result[-1] != value:
            result.append(str(value))
    return result


def _contains_sequence(values: Sequence[str], expected: Sequence[str]) -> bool:
    if not expected or len(values) < len(expected):
        return False
    width = len(expected)
    return any(tuple(values[index:index + width]) == tuple(expected) for index in range(len(values) - width + 1))


def _sector_delta(left: str, right: str) -> int:
    raw = FACINGS.index(right) - FACINGS.index(left)
    return ((raw + 4) % 8) - 4


def _turn_metrics(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    facings = _collapsed(records, "presented_facing")
    deltas = [_sector_delta(left, right) for left, right in zip(facings, facings[1:])]
    violations: List[Dict[str, Any]] = []
    for left, right in zip(records, records[1:]):
        left_facing = left.get("presented_facing")
        right_facing = right.get("presented_facing")
        left_tick = left.get("simulation_tick")
        right_tick = right.get("simulation_tick")
        if left_facing not in FACINGS or right_facing not in FACINGS:
            violations.append({"reason": "invalid_facing"})
            continue
        if type(left_tick) is not int or type(right_tick) is not int or right_tick <= left_tick:
            violations.append({"reason": "invalid_tick"})
            continue
        sector_step = abs(_sector_delta(str(left_facing), str(right_facing)))
        if sector_step > right_tick - left_tick:
            violations.append(
                {
                    "left_frame": left.get("frame_index"),
                    "right_frame": right.get("frame_index"),
                    "sector_step": sector_step,
                    "elapsed_ticks": right_tick - left_tick,
                }
            )
    return {
        "collapsed_facings": facings,
        "sector_deltas": deltas,
        "cumulative_sector_delta": sum(deltas),
        "per_tick_violations": violations,
    }


def _inside_stage(trace: Mapping[str, Any], cols: int, rows: int) -> bool:
    span = trace.get("silhouette_raster_span")
    if not isinstance(span, Mapping):
        return False
    try:
        return (
            0 <= int(span["min_x"]) <= int(span["max_x"]) < cols
            and 0 <= int(span["min_y"]) <= int(span["max_y"]) < rows
        )
    except (KeyError, TypeError, ValueError):
        return False


def analyze_v6(
    manifest: Mapping[str, Any],
    trace_records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "schema_version": 1,
        "acceptance_scenario": "V6",
        "passed": False,
        "checks": [],
        "metrics": {},
        "review_boundary": (
            "Machine checks do not replace normal-speed and quarter-speed review of "
            "turn anticipation, weight, silhouette readability, reversal, and foot skating."
        ),
    }
    program = manifest.get("scenario_program")
    _check(
        report,
        "scenario_program_identity",
        isinstance(program, Mapping)
        and program.get("program_id") == "v6-directional-walk"
        and program.get("acceptance_scenario") == "V6"
        and program.get("total_duration_seconds") == 9.25,
        program,
    )
    scenarios = manifest.get("scenarios", ())
    scenario_names = tuple(item.get("name") for item in scenarios)
    _check(report, "scenario_order", scenario_names == EXPECTED_SCENARIOS, list(scenario_names))
    _check(
        report,
        "scenario_directional_targets",
        list(scenarios) == list(EXPECTED_SCENARIO_SPECS),
        {
            "expected": EXPECTED_SCENARIO_SPECS,
            "observed": scenarios,
        },
    )

    frames = manifest.get("frames", ())
    trace_by_index = {item.get("frame_index"): item for item in trace_records}
    paired = [(frame, trace_by_index.get(frame.get("frame_index"))) for frame in frames]
    complete = [(frame, trace) for frame, trace in paired if trace is not None]
    owned = [frame for frame in frames if frame.get("capture_owned") is True]
    unowned = [frame for frame in frames if frame.get("capture_owned") is not True]
    indexes = [frame.get("frame_index") for frame in frames]
    counts = {
        name: sum(
            frame.get("capture_owned") is True and frame.get("scenario") == name
            for frame in frames
        )
        for name in EXPECTED_SCENARIOS
    }
    contiguous = bool(indexes) and all(
        type(left) is int and type(right) is int and right == left + 1
        for left, right in zip(indexes, indexes[1:])
    )
    scenario_indexes = {
        name: [
            frame.get("frame_index")
            for frame in frames
            if frame.get("capture_owned") is True and frame.get("scenario") == name
        ]
        for name in EXPECTED_SCENARIOS
    }
    _check(
        report,
        "complete_contiguous_capture",
        len(frames) == len(trace_records) == len(complete)
        and len(owned) == sum(EXPECTED_FRAME_COUNTS.values())
        and len(unowned) <= 2
        and all(frame.get("scenario") is None for frame in unowned)
        and contiguous
        and counts == EXPECTED_FRAME_COUNTS
        and all(
            values and all(right == left + 1 for left, right in zip(values, values[1:]))
            for values in scenario_indexes.values()
        ),
        {
            "frame_count": len(frames),
            "trace_count": len(trace_records),
            "owned_frame_count": len(owned),
            "scenario_frame_counts": counts,
            "unowned_frame_indexes": [frame.get("frame_index") for frame in unowned],
            "transport_contiguous": contiguous,
        },
    )
    by_scenario: Dict[str, List[Mapping[str, Any]]] = {
        name: [
            trace
            for frame, trace in complete
            if frame.get("capture_owned") is True and frame.get("scenario") == name
        ]
        for name in EXPECTED_SCENARIOS
    }
    idle = by_scenario["v6-idle"]
    south = by_scenario["v6-south-approach"]
    east = by_scenario["v6-turn-east"]
    west = by_scenario["v6-reverse-west"]
    settle = by_scenario["v6-stop-settle"]

    start_offsets: Dict[str, Optional[int]] = {}
    previous = idle[-1:] + south[-1:] + east[-1:]
    for name, records, prior in zip(EXPECTED_SCENARIOS[1:4], (south, east, west), previous):
        prior_root = _root(prior)
        start_offsets[name] = next(
            (
                index
                for index, trace in enumerate(records)
                if prior_root is not None
                and _root(trace) is not None
                and math.dist(prior_root, _root(trace)) > 1e-6  # type: ignore[arg-type]
            ),
            None,
        )
    _check(
        report,
        "idle_and_motion_response_within_two_frames",
        bool(idle)
        and all(
            trace.get("animation_clip_id") == "idle_front"
            and trace.get("rendered_pose_id") == "front_idle"
            for trace in idle
        )
        and all(offset is not None and offset <= 2 for offset in start_offsets.values()),
        {"motion_start_owned_frame_offsets": start_offsets},
    )

    east_turn = _turn_metrics(east)
    west_turn = _turn_metrics(west)
    _check(
        report,
        "readable_90_degree_turn",
        bool(east_turn["collapsed_facings"])
        and east_turn["collapsed_facings"][0] == "south"
        and east_turn["collapsed_facings"][-1] == "east"
        and abs(east_turn["cumulative_sector_delta"]) == 2
        and not east_turn["per_tick_violations"],
        east_turn,
    )
    _check(
        report,
        "readable_180_degree_reversal",
        bool(west_turn["collapsed_facings"])
        and west_turn["collapsed_facings"][0] == "east"
        and west_turn["collapsed_facings"][-1] == "west"
        and abs(west_turn["cumulative_sector_delta"]) == 4
        and not west_turn["per_tick_violations"],
        west_turn,
    )

    pose_catalog = load_pose_catalog()
    facing_mismatches = []
    for trace in south + east + west:
        pose_id = trace.get("rendered_pose_id")
        metadata = pose_catalog.get(str(pose_id))
        expected_facing = metadata.facing if metadata is not None else None
        if expected_facing != trace.get("presented_facing"):
            facing_mismatches.append(
                {
                    "frame_index": trace.get("frame_index"),
                    "pose_id": pose_id,
                    "authored_facing": expected_facing,
                    "presented_facing": trace.get("presented_facing"),
                }
            )
    _check(
        report,
        "rendered_pose_facing_alignment",
        not facing_mismatches,
        {"mismatches": facing_mismatches},
    )

    directional: Dict[str, Any] = {}
    directional_ok = True
    for clip_id, records in (("walk_right", east), ("walk_left", west)):
        clip_records = [trace for trace in records if trace.get("animation_clip_id") == clip_id]
        poses = tuple(_collapsed(clip_records, "rendered_pose_id"))
        expected = PROFILE_POSE_SEQUENCES[clip_id]
        directional[clip_id] = {
            "frame_count": len(clip_records),
            "collapsed_pose_sequence": list(poses),
            "expected_pose_sequence": list(expected),
        }
        directional_ok = (
            directional_ok
            and len(clip_records) >= 12
            and _contains_sequence(poses, expected)
        )
    observed_walk_clips = {
        trace.get("animation_clip_id")
        for trace in south + east + west
        if str(trace.get("animation_clip_id", "")).startswith("walk_")
    }
    _check(
        report,
        "directional_profile_clip_alignment",
        directional_ok
        and observed_walk_clips.issubset(WALK_CLIPS)
        and "walk_back" not in observed_walk_clips,
        {"directional": directional, "observed_walk_clips": sorted(observed_walk_clips)},
    )

    transition_topology: Dict[str, Any] = {}
    transition_ok = True
    for clip_id, records in (
        ("turn_front_to_east", east),
        ("reverse_east_to_west", west),
    ):
        clip_records = [trace for trace in records if trace.get("animation_clip_id") == clip_id]
        poses = tuple(_collapsed(clip_records, "rendered_pose_id"))
        expected = TRANSITION_POSE_SEQUENCES[clip_id]
        transition_topology[clip_id] = {
            "frame_count": len(clip_records),
            "collapsed_pose_sequence": list(poses),
            "expected_pose_sequence": list(expected),
        }
        transition_ok = transition_ok and len(clip_records) >= len(expected) and poses == expected
    all_motion_poses = {
        str(trace.get("rendered_pose_id"))
        for trace in south + east + west
        if trace.get("animation_clip_id") in {
            *WALK_CLIPS,
            *TRANSITION_POSE_SEQUENCES,
        }
    }
    deprecated_observed = sorted(all_motion_poses.intersection(DEPRECATED_PROFILE_POSES))
    _check(
        report,
        "authored_turn_reversal_pose_topology",
        transition_ok and not deprecated_observed,
        {
            "transitions": transition_topology,
            "deprecated_profile_poses_observed": deprecated_observed,
        },
    )

    turn_records = [
        trace
        for trace in east + west
        if trace.get("animation_clip_id") in TRANSITION_POSE_SEQUENCES
    ]
    tip_steps, missing_tip = _adjacent_stage_steps(
        turn_records,
        lambda trace: _stage_point(trace, "staff_tip_stage"),
    )
    grip_steps, missing_grip = _adjacent_stage_steps(
        turn_records,
        lambda trace: _pose_anchor_stage(trace, "staff_hand"),
    )
    _check(
        report,
        "turn_staff_path_continuity",
        bool(tip_steps)
        and bool(grip_steps)
        and not missing_tip
        and not missing_grip
        and max(tip_steps) <= MAX_TURN_STAFF_TIP_STEP
        and max(grip_steps) <= MAX_TURN_STAFF_GRIP_STEP,
        {
            "maximum_staff_tip_step": max(tip_steps, default=math.inf),
            "maximum_staff_grip_step": max(grip_steps, default=math.inf),
            "staff_tip_limit": MAX_TURN_STAFF_TIP_STEP,
            "staff_grip_limit": MAX_TURN_STAFF_GRIP_STEP,
            "missing_tip_pairs": missing_tip,
            "missing_grip_pairs": missing_grip,
        },
    )

    motion = south + east + west
    contacts = _collapsed_contacts(motion)
    phases_valid = all(
        type(trace.get("animation_phase_numerator")) is int
        and type(trace.get("animation_phase_denominator")) is int
        and trace["animation_phase_denominator"] > 0
        and 0 <= trace["animation_phase_numerator"] <= trace["animation_phase_denominator"]
        for trace in motion
    )
    clip_switches: List[Dict[str, Any]] = []
    for left, right in zip(motion, motion[1:]):
        if left.get("animation_clip_id") == right.get("animation_clip_id"):
            continue
        if right.get("animation_clip_id") not in WALK_CLIPS:
            continue
        clip_switches.append(
            {
                "frame_index": right.get("frame_index"),
                "from": left.get("animation_clip_id"),
                "to": right.get("animation_clip_id"),
                "contact": right.get("support_contact"),
            }
        )
    _check(
        report,
        "phase_and_support_continuity",
        len(contacts) >= 12
        and all(left != right for left, right in zip(contacts, contacts[1:]))
        and phases_valid
        and len(clip_switches) >= 2
        and all(item["contact"] in {"left_foot", "right_foot"} for item in clip_switches),
        {
            "collapsed_support_contacts": contacts,
            "phases_valid": phases_valid,
            "walk_clip_switches": clip_switches,
        },
    )

    roots = [_root(trace) for trace in trace_records]
    root_steps = [
        math.dist(left, right)
        for left, right in zip(roots, roots[1:])
        if left is not None and right is not None
    ]
    contact = manifest.get("contact_verification", {})
    _check(
        report,
        "contact_and_root_continuity",
        bool(root_steps)
        and max(root_steps) <= 0.09
        and isinstance(contact, Mapping)
        and contact.get("passed") is True
        and float(contact.get("maximum_planted_drift_cells", math.inf)) <= 1.0
        and float(contact.get("maximum_planted_raster_span_drift_cells", math.inf)) <= 1.0,
        {
            "maximum_world_root_step": max(root_steps, default=math.inf),
            "contact_passed": contact.get("passed") if isinstance(contact, Mapping) else None,
            "maximum_planted_drift_cells": contact.get("maximum_planted_drift_cells") if isinstance(contact, Mapping) else None,
            "maximum_planted_raster_span_drift_cells": contact.get("maximum_planted_raster_span_drift_cells") if isinstance(contact, Mapping) else None,
        },
    )

    final_root = _root(settle[-1]) if settle else None
    target_error = math.dist(final_root, TARGET) if final_root is not None else math.inf
    all_finish = west + settle
    stop_records = [
        trace for trace in all_finish if trace.get("animation_clip_id") == "stop_left"
    ]
    stop_poses = tuple(_collapsed(stop_records, "rendered_pose_id"))
    zero_suffix = 0
    finish_roots = [_root(trace) for trace in all_finish]
    for left, right in reversed(list(zip(finish_roots, finish_roots[1:]))):
        if left is not None and right is not None and math.dist(left, right) <= 1e-6:
            zero_suffix += 1
        else:
            break
    _check(
        report,
        "target_stop_and_profile_settle",
        target_error <= 0.08
        and _contains_sequence(stop_poses, STOP_LEFT_POSE_SEQUENCE)
        and len(set(stop_poses)) >= len(STOP_LEFT_POSE_SEQUENCE)
        and len(settle) >= 8
        and all(
            trace.get("animation_clip_id") == "idle_left"
            and trace.get("rendered_pose_id") == "profile_left"
            and trace.get("support_contact") == "both_feet"
            for trace in settle[-8:]
        )
        and zero_suffix >= 4,
        {
            "target": list(TARGET),
            "final_root": list(final_root) if final_root is not None else None,
            "target_error": target_error,
            "zero_speed_suffix_frames": zero_suffix,
            "collapsed_stop_pose_sequence": list(stop_poses),
            "required_stop_pose_sequence": list(STOP_LEFT_POSE_SEQUENCE),
        },
    )

    cols = int(manifest.get("init", {}).get("cols", 0) or 0)
    rows = int(manifest.get("init", {}).get("rows", 0) or 0)
    clipped = [
        trace.get("frame_index")
        for trace in trace_records
        if not _inside_stage(trace, cols, rows)
    ]
    _check(
        report,
        "directional_walk_within_canonical_stage",
        cols > 0 and rows > 0 and not clipped,
        {"stage": [cols, rows], "clipped_frames": clipped},
    )

    report["metrics"] = {
        "frame_count": len(frames),
        "owned_frame_count": len(owned),
        "target_error": target_error,
        "maximum_world_root_step": max(root_steps, default=math.inf),
        "contact_change_count": len(contacts),
        "east_turn_sector_count": abs(east_turn["cumulative_sector_delta"]),
        "reversal_sector_count": abs(west_turn["cumulative_sector_delta"]),
        "clipped_frame_count": len(clipped),
    }
    report["passed"] = bool(report["checks"]) and all(item["passed"] for item in report["checks"])
    return report


def load_and_analyze(manifest_path: Path) -> Dict[str, Any]:
    evidence_dir = manifest_path.resolve().parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest, evidence_dir)
    trace_path = evidence_dir / manifest["animation_truth_trace"]["path"]
    traces: List[Mapping[str, Any]] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if line:
            traces.append(AnimationTruthTraceV1.from_mapping(json.loads(line)).to_mapping())
    return analyze_v6(manifest, traces)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Character Director V6 evidence.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    report = load_and_analyze(args.manifest)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    else:
        print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
