#!/usr/bin/env python3
"""Evaluate the machine-verifiable portion of Character Director scenario V5."""

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
from wizard_avatar.animation_trace import AnimationTruthTraceV1


REPORT_SCHEMA = "character_director_v5_machine_acceptance_v1"
EXPECTED_SCENARIOS = ("v5-idle", "v5-three-cycle-walk", "v5-stop-settle")
EXPECTED_FRAME_COUNTS = {
    "v5-idle": 12,
    "v5-three-cycle-walk": 66,
    "v5-stop-settle": 24,
}
TARGET = (0.0, 2.45)
EXPECTED_DISTANCE = 2.55
EXPECTED_WALK_POSES = {
    "walk_front_left",
    "walk_front_left_to_right",
    "walk_front_right",
    "walk_front_right_to_left",
}
EXPECTED_STOP_POSES = {
    "stop_front_left": (
        "walk_front_left",
        "stop_front_from_left_25",
        "stop_front_from_left_50",
        "stop_front_from_left_75",
        "stop_front_from_left_100",
        "front_idle",
    ),
    "stop_front_right": (
        "walk_front_right",
        "stop_front_from_right_25",
        "stop_front_from_right_50",
        "stop_front_from_right_75",
        "stop_front_from_right_100",
        "front_idle",
    ),
    "stop_front_left_passing": (
        "walk_front_left_to_right",
        "stop_front_from_left_passing_25",
        "stop_front_from_left_passing_50",
        "stop_front_from_left_passing_75",
        "stop_front_from_left_passing_100",
        "front_idle",
    ),
    "stop_front_right_passing": (
        "walk_front_right_to_left",
        "stop_front_from_right_passing_25",
        "stop_front_from_right_passing_50",
        "stop_front_from_right_passing_75",
        "stop_front_from_right_passing_100",
        "front_idle",
    ),
}


def _check(report: Dict[str, Any], name: str, passed: bool, detail: object) -> None:
    report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})


def _root(trace: Mapping[str, Any]) -> Optional[Tuple[float, float]]:
    x = trace.get("world_root_x")
    z = trace.get("world_root_z")
    if isinstance(x, bool) or isinstance(z, bool):
        return None
    if not isinstance(x, (int, float)) or not isinstance(z, (int, float)):
        return None
    point = float(x), float(z)
    return point if all(math.isfinite(value) for value in point) else None


def _trace_speed(left: Mapping[str, Any], right: Mapping[str, Any]) -> Optional[float]:
    left_root = _root(left)
    right_root = _root(right)
    left_tick = left.get("simulation_tick")
    right_tick = right.get("simulation_tick")
    if (
        left_root is None
        or right_root is None
        or type(left_tick) is not int
        or type(right_tick) is not int
        or right_tick <= left_tick
    ):
        return None
    elapsed_seconds = (right_tick - left_tick) / 60.0
    return math.hypot(
        right_root[0] - left_root[0],
        right_root[1] - left_root[1],
    ) / elapsed_seconds


def _marker_count(records: Sequence[Mapping[str, Any]], marker_id: str) -> Tuple[int, List[int]]:
    frames: List[int] = []
    for trace in records:
        for event in trace.get("presentation_marker_events", ()):
            if isinstance(event, Mapping) and event.get("marker_id") == marker_id:
                frame = trace.get("frame_index")
                if type(frame) is int:
                    frames.append(frame)
    return len(frames), frames


def _collapsed_contacts(records: Sequence[Mapping[str, Any]]) -> List[str]:
    result: List[str] = []
    for trace in records:
        contact = trace.get("support_contact")
        if contact not in {"left_foot", "right_foot"}:
            continue
        if not result or result[-1] != contact:
            result.append(str(contact))
    return result


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


def analyze_v5(
    manifest: Mapping[str, Any],
    trace_records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "schema_version": 1,
        "acceptance_scenario": "V5",
        "passed": False,
        "checks": [],
        "metrics": {},
        "review_boundary": (
            "Machine checks do not replace normal-speed and quarter-speed review "
            "of weight transfer, cadence, foot skating, and stop settle."
        ),
    }
    program = manifest.get("scenario_program")
    _check(
        report,
        "scenario_program_identity",
        isinstance(program, Mapping)
        and program.get("program_id") == "v5-front-walk"
        and program.get("acceptance_scenario") == "V5"
        and program.get("total_duration_seconds") == 4.25,
        program,
    )
    scenario_names = tuple(item.get("name") for item in manifest.get("scenarios", ()))
    _check(report, "scenario_order", scenario_names == EXPECTED_SCENARIOS, list(scenario_names))

    frames = manifest.get("frames", ())
    trace_by_index = {item.get("frame_index"): item for item in trace_records}
    paired = [(frame, trace_by_index.get(frame.get("frame_index"))) for frame in frames]
    complete = [(frame, trace) for frame, trace in paired if trace is not None]
    owned = [frame for frame in frames if frame.get("capture_owned") is True]
    unowned = [frame for frame in frames if frame.get("capture_owned") is not True]
    counts = {
        name: sum(
            frame.get("capture_owned") is True and frame.get("scenario") == name
            for frame in frames
        )
        for name in EXPECTED_SCENARIOS
    }
    indexes = [frame.get("frame_index") for frame in frames]
    transport_contiguous = bool(indexes) and all(
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
    bounded_ranges = [
        range(scenario_indexes[left][-1] + 1, scenario_indexes[right][0])
        for left, right in zip(EXPECTED_SCENARIOS, EXPECTED_SCENARIOS[1:])
    ] if all(scenario_indexes.values()) else []
    unowned_indexes = [frame.get("frame_index") for frame in unowned]
    unowned_bounded = (
        len(unowned) <= 2
        and all(frame.get("scenario") is None for frame in unowned)
        and all(any(index in boundary for boundary in bounded_ranges) for index in unowned_indexes)
    )
    _check(
        report,
        "complete_contiguous_capture",
        len(frames) == len(trace_records) == len(complete)
        and len(owned) == 102
        and transport_contiguous
        and counts == EXPECTED_FRAME_COUNTS
        and all(
            values and all(right == left + 1 for left, right in zip(values, values[1:]))
            for values in scenario_indexes.values()
        )
        and unowned_bounded,
        {
            "frame_count": len(frames),
            "trace_count": len(trace_records),
            "owned_frame_count": len(owned),
            "scenario_frame_counts": counts,
            "transport_contiguous": transport_contiguous,
            "unowned_transition_frame_indexes": unowned_indexes,
            "unowned_are_bounded_transitions": unowned_bounded,
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
    idle = by_scenario["v5-idle"]
    walk = by_scenario["v5-three-cycle-walk"]
    settle = by_scenario["v5-stop-settle"]

    first_walk_offset = next(
        (
            index
            for index, trace in enumerate(walk)
            if trace.get("animation_clip_id") == "walk_front"
        ),
        None,
    )
    _check(
        report,
        "idle_and_bounded_walk_start",
        bool(idle)
        and all(
            trace.get("animation_clip_id") == "idle_front"
            and trace.get("rendered_pose_id") == "front_idle"
            for trace in idle
        )
        and first_walk_offset is not None
        and first_walk_offset <= 2,
        {
            "idle_frame_count": len(idle),
            "first_walk_owned_frame_offset": first_walk_offset,
        },
    )

    start_root = _root(idle[-1]) if idle else None
    walk_roots = [_root(trace) for trace in walk]
    settle_roots = [_root(trace) for trace in settle]
    valid_roots = (
        start_root is not None
        and all(root is not None for root in walk_roots)
        and all(root is not None for root in settle_roots)
    )
    typed_walk_roots = [root for root in walk_roots if root is not None]
    typed_settle_roots = [root for root in settle_roots if root is not None]
    final_root = typed_settle_roots[-1] if typed_settle_roots else None
    displacement = (
        math.hypot(final_root[0] - start_root[0], final_root[1] - start_root[1])
        if start_root is not None and final_root is not None
        else math.inf
    )
    target_error = (
        math.hypot(final_root[0] - TARGET[0], final_root[1] - TARGET[1])
        if final_root is not None
        else math.inf
    )
    loop_count, loop_frames = _marker_count(walk, "loop_boundary")
    derived_cycle_count = displacement / 0.85
    _check(
        report,
        "three_complete_distance_driven_cycles",
        valid_roots
        and abs(displacement - EXPECTED_DISTANCE) <= 0.03
        and abs(derived_cycle_count - 3.0) <= 0.04,
        {
            "displacement": displacement,
            "expected_distance": EXPECTED_DISTANCE,
            "stride_length": 0.85,
            "derived_cycle_count": derived_cycle_count,
            "loop_boundary_count": loop_count,
            "loop_boundary_frame_indexes": loop_frames,
        },
    )

    speed_records = ([idle[-1]] if idle else []) + walk
    measured_speeds = [
        _trace_speed(left, right)
        for left, right in zip(speed_records, speed_records[1:])
    ]
    speeds = [speed for speed in measured_speeds if speed is not None]
    peak_speed = max(speeds, default=0.0)
    cruise_indexes = [
        index for index, speed in enumerate(speeds) if speed >= peak_speed * 0.9
    ]
    tail = speeds[cruise_indexes[-1]:] if cruise_indexes else []
    tail_rises = [
        index
        for index, (left, right) in enumerate(zip(tail, tail[1:]))
        if right > left + 0.08
    ]
    distinct_tail_speeds = len({round(speed, 2) for speed in tail})
    zero_suffix = 0
    for speed in reversed(speeds):
        if speed <= 0.01:
            zero_suffix += 1
        else:
            break
    _check(
        report,
        "decelerated_stop_profile",
        len(speeds) == len(walk)
        and 1.0 <= peak_speed <= 1.5
        and len(tail) >= 8
        and distinct_tail_speeds >= 5
        and not tail_rises
        and zero_suffix >= 4,
        {
            "peak_speed_units_per_second": peak_speed,
            "deceleration_tail_speeds": tail,
            "tail_rise_indexes": tail_rises,
            "distinct_tail_speed_count": distinct_tail_speeds,
            "zero_speed_suffix_frames": zero_suffix,
        },
    )

    contacts = _collapsed_contacts(walk)
    alternates = all(left != right for left, right in zip(contacts, contacts[1:]))
    contact = manifest.get("contact_verification", {})
    _check(
        report,
        "alternating_contacts_without_planted_drift",
        len(contacts) >= 6
        and contacts[:6] == [
            "left_foot",
            "right_foot",
            "left_foot",
            "right_foot",
            "left_foot",
            "right_foot",
        ]
        and alternates
        and isinstance(contact, Mapping)
        and contact.get("passed") is True
        and float(contact.get("maximum_planted_drift_cells", math.inf)) <= 1.0,
        {
            "collapsed_support_contacts": contacts,
            "alternates": alternates,
            "contact_passed": contact.get("passed") if isinstance(contact, Mapping) else None,
            "maximum_planted_drift_cells": (
                contact.get("maximum_planted_drift_cells")
                if isinstance(contact, Mapping)
                else None
            ),
        },
    )

    observed_walk_poses = {
        trace.get("rendered_pose_id")
        for trace in walk
        if trace.get("animation_clip_id") == "walk_front"
    }
    owned_performance = walk + settle
    stop_records = [
        trace
        for trace in owned_performance
        if trace.get("animation_clip_id") in EXPECTED_STOP_POSES
    ]
    stop_clip_ids = tuple(
        dict.fromkeys(str(trace.get("animation_clip_id")) for trace in stop_records)
    )
    stop_pose_sequence = tuple(
        dict.fromkeys(str(trace.get("rendered_pose_id")) for trace in stop_records)
    )
    expected_stop_sequence = (
        EXPECTED_STOP_POSES.get(stop_clip_ids[0], ())
        if len(stop_clip_ids) == 1
        else ()
    )
    last_stop_offset = max(
        (
            index
            for index, trace in enumerate(owned_performance)
            if trace.get("animation_clip_id") in EXPECTED_STOP_POSES
        ),
        default=-1,
    )
    final_idle = owned_performance[last_stop_offset + 1 :]
    _check(
        report,
        "front_walk_pose_and_stop_settle",
        observed_walk_poses == EXPECTED_WALK_POSES
        and target_error <= 0.08
        and len(stop_clip_ids) == 1
        and stop_pose_sequence == expected_stop_sequence
        and len(final_idle) >= 8
        and all(
            trace.get("animation_clip_id") == "idle_front"
            and trace.get("rendered_pose_id") == "front_idle"
            and trace.get("support_contact") == "both_feet"
            for trace in final_idle
        ),
        {
            "observed_walk_poses": sorted(str(item) for item in observed_walk_poses),
            "stop_clip_ids": list(stop_clip_ids),
            "stop_pose_sequence": list(stop_pose_sequence),
            "expected_stop_pose_sequence": list(expected_stop_sequence),
            "target": list(TARGET),
            "final_root": list(final_root) if final_root is not None else None,
            "target_error": target_error,
            "settle_frame_count": len(settle),
            "final_idle_frame_count": len(final_idle),
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
        "walk_silhouette_within_canonical_stage",
        cols > 0 and rows > 0 and not clipped,
        {"stage": [cols, rows], "clipped_frames": clipped},
    )

    report["metrics"] = {
        "frame_count": len(frames),
        "owned_frame_count": len(owned),
        "walk_frame_count": len(walk),
        "loop_boundary_count": loop_count,
        "derived_cycle_count": derived_cycle_count,
        "displacement": displacement,
        "target_error": target_error,
        "peak_speed_units_per_second": peak_speed,
        "contact_change_count": len(contacts),
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
    return analyze_v5(manifest, traces)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Character Director V5 evidence.")
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
