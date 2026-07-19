#!/usr/bin/env python3
"""Evaluate the machine-verifiable portion of Character Director scenario V3."""

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
from wizard_avatar.pose_compositor import authored_staff_cells
from wizard_avatar.reference_avatar import (
    get_reference_pose,
    render_reference_pose_local,
)


REPORT_SCHEMA = "character_director_v3_machine_acceptance_v1"
EXPECTED_SCENARIOS = (
    "v3-ready",
    "v3-cast-one",
    "v3-hold-one",
    "v3-cast-two",
    "v3-hold-two",
    "v3-cast-three",
    "v3-settle",
)
EXPECTED_FRAME_COUNTS = {
    "v3-ready": 12,
    "v3-cast-one": 48,
    "v3-hold-one": 48,
    "v3-cast-two": 48,
    "v3-hold-two": 48,
    "v3-cast-three": 48,
    "v3-settle": 24,
}
CAST_SCENARIOS = ("v3-cast-one", "v3-cast-two", "v3-cast-three")
EXPECTED_MARKERS = (
    ("action_commit", 10),
    ("action_effect", 14),
    ("action_recoverable", 23),
    ("action_settled", 28),
)
MAXIMUM_STAFF_AXIS_CELLS_PER_AUTHORED_FRAME = 2.0
# Inverse-nearest rigid rotation can move the outside edge of the staff's
# asymmetric hook one cell farther than its authored tip anchor. A value of
# three is the measured grid-quantization bound; palette, count, endpoints,
# and the two-cell anchor bound below still fail closed on prop replacement.
MAXIMUM_STAFF_RASTER_DISTANCE_PER_AUTHORED_FRAME = 3.0


def _check(report: Dict[str, Any], name: str, passed: bool, detail: object) -> None:
    report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})


def _point(value: object) -> Optional[Tuple[float, float]]:
    if not isinstance(value, Mapping):
        return None
    x = value.get("x")
    y = value.get("y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None
    return float(x), float(y)


def _maximum_axis_drift(points: Sequence[Tuple[float, float]]) -> float:
    if not points:
        return math.inf
    origin = points[0]
    return max(
        max(abs(point[0] - origin[0]), abs(point[1] - origin[1]))
        for point in points
    )


def _staff_hand_stage(trace: Mapping[str, Any]) -> Optional[Tuple[float, float]]:
    pose_id = trace.get("rendered_pose_id")
    root_stage = _point(trace.get("presented_root_stage"))
    if not isinstance(pose_id, str) or root_stage is None:
        return None
    pose = get_reference_pose(pose_id)
    hand = pose.anchors.get("staff_hand")
    if hand is None:
        return None
    scale_x = trace.get("render_scale_x")
    scale_y = trace.get("render_scale_y")
    if not isinstance(scale_x, (int, float)) or not isinstance(scale_y, (int, float)):
        return None
    return (
        root_stage[0] + (hand[0] - pose.root_anchor[0]) * float(scale_x),
        root_stage[1] + (hand[1] - pose.root_anchor[1]) * float(scale_y),
    )


def _marker_events(records: Sequence[Mapping[str, Any]]) -> List[Tuple[str, int]]:
    result: List[Tuple[str, int]] = []
    for trace in records:
        events = trace.get("presentation_marker_events", ())
        if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
            continue
        for event in events:
            if not isinstance(event, Mapping):
                continue
            marker = event.get("marker_id")
            frame = event.get("animation_authored_frame")
            if isinstance(marker, str) and type(frame) is int:
                result.append((marker, frame))
    return result


def _pose_cells(pose_id: str) -> set[Tuple[int, int, Tuple[int, int, int]]]:
    return {
        (cell.x, cell.y, cell.rgb)
        for cell in get_reference_pose(pose_id).cells
    }


def _staff_raster(pose_id: str) -> Dict[Tuple[int, int], Tuple[int, int, int]]:
    pose = get_reference_pose(pose_id)
    canvas = render_reference_pose_local(pose_id)
    return {
        point: cell.rgb
        for point, cell in authored_staff_cells(
            canvas,
            pose.anchors["staff_tip"],
            pose.anchors["staff_hand"],
            pose.root_anchor,
        ).items()
    }


def _raster_nearest_distance(
    left: Mapping[Tuple[int, int], Tuple[int, int, int]],
    right: Mapping[Tuple[int, int], Tuple[int, int, int]],
) -> float:
    if not left or not right:
        return math.inf

    def directed(source: Sequence[Tuple[int, int]], target: Sequence[Tuple[int, int]]) -> int:
        return max(
            min(max(abs(x - tx), abs(y - ty)) for tx, ty in target)
            for x, y in source
        )

    left_points = tuple(left)
    right_points = tuple(right)
    return float(max(directed(left_points, right_points), directed(right_points, left_points)))


def analyze_v3(
    manifest: Mapping[str, Any],
    trace_records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "schema_version": 1,
        "acceptance_scenario": "V3",
        "passed": False,
        "checks": [],
        "metrics": {},
        "review_boundary": (
            "Machine checks do not replace normal-speed and quarter-speed review "
            "of silhouette, staging, acting, and effect readability."
        ),
    }
    program = manifest.get("scenario_program")
    _check(
        report,
        "scenario_program_identity",
        isinstance(program, Mapping)
        and program.get("program_id") == "v3-canonical-cast"
        and program.get("acceptance_scenario") == "V3"
        and program.get("total_duration_seconds") == 11.5,
        program,
    )
    scenario_names = tuple(item.get("name") for item in manifest.get("scenarios", ()))
    _check(report, "scenario_order", scenario_names == EXPECTED_SCENARIOS, list(scenario_names))

    frames = manifest.get("frames", ())
    trace_by_index = {item.get("frame_index"): item for item in trace_records}
    paired = [(frame, trace_by_index.get(frame.get("frame_index"))) for frame in frames]
    missing = [frame.get("frame_index") for frame, trace in paired if trace is None]
    complete = [(frame, trace) for frame, trace in paired if trace is not None]
    frame_indexes = [frame.get("frame_index") for frame in frames]
    transport_contiguous = bool(frame_indexes) and all(
        type(left) is int and type(right) is int and right == left + 1
        for left, right in zip(frame_indexes, frame_indexes[1:])
    )
    owned_frames = [frame for frame in frames if frame.get("capture_owned") is True]
    unowned_frames = [frame for frame in frames if frame.get("capture_owned") is not True]
    counts = {
        name: sum(
            frame.get("capture_owned") is True and frame.get("scenario") == name
            for frame in frames
        )
        for name in EXPECTED_SCENARIOS
    }
    scenario_indexes = {
        name: [
            frame.get("frame_index")
            for frame in frames
            if frame.get("capture_owned") is True and frame.get("scenario") == name
        ]
        for name in EXPECTED_SCENARIOS
    }
    scenario_blocks_contiguous = all(
        indexes
        and all(
            type(left) is int and type(right) is int and right == left + 1
            for left, right in zip(indexes, indexes[1:])
        )
        for indexes in scenario_indexes.values()
    )
    boundary_gaps = [
        range(scenario_indexes[left][-1] + 1, scenario_indexes[right][0])
        for left, right in zip(EXPECTED_SCENARIOS, EXPECTED_SCENARIOS[1:])
    ]
    unowned_indexes = [frame.get("frame_index") for frame in unowned_frames]
    unowned_are_bounded_transitions = (
        len(unowned_frames) <= len(EXPECTED_SCENARIOS) - 1
        and all(frame.get("scenario") is None for frame in unowned_frames)
        and all(
            type(index) is int
            and any(index in boundary_gap for boundary_gap in boundary_gaps)
            for index in unowned_indexes
        )
    )
    _check(
        report,
        "complete_contiguous_capture",
        len(frames) == len(trace_records) == len(complete)
        and not missing
        and len(owned_frames) == 276
        and transport_contiguous
        and scenario_blocks_contiguous
        and unowned_are_bounded_transitions
        and counts == EXPECTED_FRAME_COUNTS,
        {
            "frame_count": len(frames),
            "trace_count": len(trace_records),
            "owned_frame_count": len(owned_frames),
            "unowned_transition_frame_indexes": unowned_indexes,
            "missing_trace_frames": missing,
            "transport_contiguous": transport_contiguous,
            "scenario_blocks_contiguous": scenario_blocks_contiguous,
            "unowned_are_bounded_transitions": unowned_are_bounded_transitions,
            "scenario_frame_counts": counts,
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
    cast_records = [trace for name in CAST_SCENARIOS for trace in by_scenario[name]]
    authored_records = [
        trace for trace in cast_records if trace.get("animation_clip_id") == "cast_front"
    ]
    pose_mismatches = [
        {
            "frame_index": trace.get("frame_index"),
            "authored_frame": trace.get("animation_authored_frame"),
            "pose_id": trace.get("rendered_pose_id"),
        }
        for trace in authored_records
        if trace.get("rendered_pose_id")
        != "cast_front_{:02d}".format(int(trace.get("animation_authored_frame", -1)))
    ]
    _check(
        report,
        "canonical_atomic_cast_poses",
        bool(authored_records)
        and not pose_mismatches
        and all(0 <= int(trace.get("animation_authored_frame", -1)) <= 31 for trace in authored_records),
        {
            "cast_trace_count": len(authored_records),
            "pose_ids": sorted({trace.get("rendered_pose_id") for trace in authored_records}),
            "mismatches": pose_mismatches,
        },
    )

    cast_poses = [get_reference_pose(f"cast_front_{frame:02d}") for frame in range(32)]
    front_idle = get_reference_pose("front_idle")
    static_tip_failures = []
    for frame, (left, right) in enumerate(zip(cast_poses, cast_poses[1:])):
        left_tip = left.anchors["staff_tip"]
        right_tip = right.anchors["staff_tip"]
        if max(abs(right_tip[0] - left_tip[0]), abs(right_tip[1] - left_tip[1])) > 2:
            static_tip_failures.append(frame)
    neutral_cells = _pose_cells("front_idle")
    staff_rasters = {
        frame: _staff_raster(f"cast_front_{frame:02d}")
        for frame in range(32)
    }
    neutral_staff = staff_rasters[0]
    staff_raster_failures = []
    staff_raster_changes = []
    for frame in range(31):
        left = staff_rasters[frame]
        right = staff_rasters[frame + 1]
        changed_points = {
            point
            for point in set(left) | set(right)
            if left.get(point) != right.get(point)
        }
        changed_bounds = None
        if changed_points:
            xs = [point[0] for point in changed_points]
            ys = [point[1] for point in changed_points]
            changed_bounds = [min(xs), min(ys), max(xs), max(ys)]
        nearest_distance = _raster_nearest_distance(left, right)
        change = {
            "from_frame": frame,
            "to_frame": frame + 1,
            "changed_cell_count": len(changed_points),
            "changed_bounds": changed_bounds,
            "nearest_cell_distance": nearest_distance,
            "left_cell_count": len(left),
            "right_cell_count": len(right),
        }
        staff_raster_changes.append(change)
        if (
            nearest_distance > MAXIMUM_STAFF_RASTER_DISTANCE_PER_AUTHORED_FRAME
            or not set(left.values()).issubset(set(neutral_staff.values()))
            or not set(right.values()).issubset(set(neutral_staff.values()))
            or not 0.85 <= len(left) / len(neutral_staff) <= 1.20
            or not 0.85 <= len(right) / len(neutral_staff) <= 1.20
        ):
            staff_raster_failures.append(change)
    _check(
        report,
        "complete_static_cast_graph_contract",
        not static_tip_failures
        and {pose.anchors["staff_hand"] for pose in cast_poses} == {(56, 50)}
        and _pose_cells("cast_front_00") == neutral_cells
        and _pose_cells("cast_front_31") == neutral_cells
        and cast_poses[0].anchors["staff_tip"] == front_idle.anchors["staff_tip"]
        and cast_poses[-1].anchors["staff_tip"] == front_idle.anchors["staff_tip"],
        {
            "pose_count": len(cast_poses),
            "staff_hand_anchors": sorted({pose.anchors["staff_hand"] for pose in cast_poses}),
            "staff_tip_step_failures": static_tip_failures,
            "frame_zero_is_exact_neutral": _pose_cells("cast_front_00") == neutral_cells,
            "frame_31_is_exact_neutral": _pose_cells("cast_front_31") == neutral_cells,
        },
    )
    _check(
        report,
        "full_staff_raster_object_continuity",
        not staff_raster_failures
        and staff_rasters[0] == neutral_staff
        and staff_rasters[31] == neutral_staff,
        {
            "neutral_staff_cell_count": len(neutral_staff),
            "maximum_changed_cell_count": max(
                change["changed_cell_count"] for change in staff_raster_changes
            ),
            "maximum_nearest_cell_distance": max(
                change["nearest_cell_distance"] for change in staff_raster_changes
            ),
            "adjacent_changes": staff_raster_changes,
            "failures": staff_raster_failures,
        },
    )

    marker_detail = {name: _marker_events(by_scenario[name]) for name in CAST_SCENARIOS}
    _check(
        report,
        "authored_marker_order_per_cast",
        all(tuple(marker_detail[name]) == EXPECTED_MARKERS for name in CAST_SCENARIOS),
        marker_detail,
    )

    following_scenario = {
        "v3-cast-one": "v3-hold-one",
        "v3-cast-two": "v3-hold-two",
        "v3-cast-three": "v3-settle",
    }
    observed_by_cast = {
        name: sorted(
            {
                int(trace["animation_authored_frame"])
                for trace in by_scenario[name]
                if trace.get("animation_clip_id") == "cast_front"
            }
        )
        for name in CAST_SCENARIOS
    }
    observed_union = sorted({frame for frames_seen in observed_by_cast.values() for frame in frames_seen})
    recovery_coverage = {
        name: sorted(set(observed_by_cast[name]) & set(range(23, 31)))
        for name in CAST_SCENARIOS
    }
    recovery_gaps = {
        name: [
            [left, right]
            for left, right in zip(recovery_coverage[name], recovery_coverage[name][1:])
            if right != left + 1
        ]
        for name in CAST_SCENARIOS
    }
    terminal_neutral = {
        name: bool(by_scenario[following_scenario[name]])
        and by_scenario[following_scenario[name]][0].get("rendered_pose_id") == "front_idle"
        for name in CAST_SCENARIOS
    }
    _check(
        report,
        "authored_coverage_and_terminal_neutral",
        set(observed_union) >= set(range(31))
        and all(set(recovery_coverage[name]) == set(range(23, 31)) for name in CAST_SCENARIOS)
        and not any(recovery_gaps.values())
        and all(tuple(marker_detail[name]) == EXPECTED_MARKERS for name in CAST_SCENARIOS)
        and all(terminal_neutral.values())
        and _pose_cells("cast_front_31") == neutral_cells,
        {
            "observed_by_cast": observed_by_cast,
            "observed_union": observed_union,
            "required_nonterminal_frames": list(range(31)),
            "required_recovery_frames_per_cast": list(range(23, 31)),
            "recovery_coverage_per_cast": recovery_coverage,
            "recovery_gaps_per_cast": recovery_gaps,
            "marker_events_per_cast": marker_detail,
            "following_neutral_by_cast": terminal_neutral,
            "terminal_frame_31_is_exact_neutral": _pose_cells("cast_front_31") == neutral_cells,
        },
    )

    world_roots = [
        (float(trace.get("world_root_x", math.inf)), float(trace.get("world_root_z", math.inf)))
        for trace in authored_records
    ]
    stage_roots = [
        point for trace in authored_records if (point := _point(trace.get("presented_root_stage"))) is not None
    ]
    hand_stages = [
        point for trace in authored_records if (point := _staff_hand_stage(trace)) is not None
    ]
    root_drift = _maximum_axis_drift(world_roots)
    stage_root_drift = _maximum_axis_drift(stage_roots)
    hand_drift = _maximum_axis_drift(hand_stages)
    contact = manifest.get("contact_verification", {})
    _check(
        report,
        "planted_root_and_fixed_staff_grip",
        len(world_roots) == len(stage_roots) == len(hand_stages) == len(authored_records)
        and root_drift <= 1e-6
        and stage_root_drift <= 1e-6
        and hand_drift <= 1e-6
        and isinstance(contact, Mapping)
        and contact.get("passed") is True
        and float(contact.get("maximum_planted_drift_cells", math.inf)) <= 1.0,
        {
            "world_root_max_axis_drift": root_drift,
            "stage_root_max_axis_drift": stage_root_drift,
            "staff_hand_max_axis_drift": hand_drift,
            "contact_passed": contact.get("passed") if isinstance(contact, Mapping) else None,
            "maximum_planted_drift_cells": contact.get("maximum_planted_drift_cells") if isinstance(contact, Mapping) else None,
        },
    )

    continuity_failures: List[Dict[str, Any]] = []
    tip_by_authored_frame: Dict[int, set[Tuple[float, float]]] = {}
    for name in CAST_SCENARIOS:
        sequence = [
            trace for trace in by_scenario[name] if trace.get("animation_clip_id") == "cast_front"
        ]
        for trace in sequence:
            frame = int(trace["animation_authored_frame"])
            point = _point(trace.get("staff_tip_local"))
            if point is not None:
                tip_by_authored_frame.setdefault(frame, set()).add(point)
        for left, right in zip(sequence, sequence[1:]):
            left_frame = int(left["animation_authored_frame"])
            right_frame = int(right["animation_authored_frame"])
            if right_frame <= left_frame:
                continue
            left_tip = _point(left.get("staff_tip_local"))
            right_tip = _point(right.get("staff_tip_local"))
            if left_tip is None or right_tip is None:
                continuity_failures.append({"scenario": name, "reason": "missing_staff_tip"})
                continue
            frame_delta = right_frame - left_frame
            axis_rate = max(
                abs(right_tip[0] - left_tip[0]),
                abs(right_tip[1] - left_tip[1]),
            ) / frame_delta
            if axis_rate > MAXIMUM_STAFF_AXIS_CELLS_PER_AUTHORED_FRAME:
                continuity_failures.append(
                    {
                        "scenario": name,
                        "from_frame": left_frame,
                        "to_frame": right_frame,
                        "axis_cells_per_authored_frame": axis_rate,
                    }
                )
    repeated_tip_conflicts = {
        str(frame): sorted(points)
        for frame, points in tip_by_authored_frame.items()
        if len(points) != 1
    }
    _check(
        report,
        "continuous_repeatable_staff_arc",
        bool(tip_by_authored_frame)
        and not continuity_failures
        and not repeated_tip_conflicts,
        {
            "maximum_axis_cells_per_authored_frame": MAXIMUM_STAFF_AXIS_CELLS_PER_AUTHORED_FRAME,
            "observed_authored_frames": sorted(tip_by_authored_frame),
            "continuity_failures": continuity_failures,
            "repeated_frame_conflicts": repeated_tip_conflicts,
        },
    )

    effect_failures = []
    for name in CAST_SCENARIOS:
        records = by_scenario[name]
        effect_events = [
            trace for trace in records if ("action_effect", 14) in _marker_events([trace])
        ]
        active = [trace for trace in records if trace.get("effect_phase") != "inactive"]
        if len(effect_events) != 1 or not active:
            effect_failures.append({"scenario": name, "reason": "missing_effect_event_or_phase"})
            continue
        event = effect_events[0]
        if event.get("effect_phase") != "stroke" or float(event.get("effect_intensity", 0.0)) <= 0.0:
            effect_failures.append({"scenario": name, "reason": "effect_not_started_at_marker"})
        if any(_point(trace.get("staff_tip_stage")) is None for trace in active):
            effect_failures.append({"scenario": name, "reason": "effect_without_staff_tip"})
    _check(report, "effect_follows_authored_staff_event", not effect_failures, effect_failures)

    cols = int(manifest.get("init", {}).get("cols", 0) or 0)
    rows = int(manifest.get("init", {}).get("rows", 0) or 0)
    clipped = []
    for trace in authored_records:
        span = trace.get("silhouette_raster_span")
        if not isinstance(span, Mapping) or not (
            0 <= int(span.get("min_x", -1)) <= int(span.get("max_x", cols)) < cols
            and 0 <= int(span.get("min_y", -1)) <= int(span.get("max_y", rows)) < rows
        ):
            clipped.append(trace.get("frame_index"))
    _check(
        report,
        "cast_silhouette_within_canonical_stage",
        bool(authored_records) and cols > 0 and rows > 0 and not clipped,
        {"stage": [cols, rows], "clipped_frames": clipped},
    )

    report["metrics"] = {
        "frame_count": len(frames),
        "owned_frame_count": len(owned_frames),
        "cast_trace_count": len(authored_records),
        "observed_cast_authored_frames": sorted(tip_by_authored_frame),
        "static_cast_pose_count": len(cast_poses),
        "staff_raster_maximum_changed_cell_count": max(
            change["changed_cell_count"] for change in staff_raster_changes
        ),
        "staff_raster_maximum_nearest_cell_distance": max(
            change["nearest_cell_distance"] for change in staff_raster_changes
        ),
        "staff_raster_failure_count": len(staff_raster_failures),
        "world_root_max_axis_drift": root_drift,
        "stage_root_max_axis_drift": stage_root_drift,
        "staff_hand_max_axis_drift": hand_drift,
        "staff_continuity_failure_count": len(continuity_failures),
        "effect_failure_count": len(effect_failures),
        "clipped_frame_count": len(clipped),
    }
    report["passed"] = bool(report["checks"]) and all(item["passed"] for item in report["checks"])
    return report


def load_and_analyze(manifest_path: Path) -> Dict[str, Any]:
    evidence_dir = manifest_path.resolve().parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest, evidence_dir)
    trace_path = evidence_dir / manifest["animation_truth_trace"]["path"]
    trace_records: List[Mapping[str, Any]] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if line:
            trace_records.append(AnimationTruthTraceV1.from_mapping(json.loads(line)).to_mapping())
    return analyze_v3(manifest, trace_records)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Character Director V3 evidence.")
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
