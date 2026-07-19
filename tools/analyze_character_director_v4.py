#!/usr/bin/env python3
"""Evaluate the machine-verifiable portion of Character Director scenario V4."""

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
from wizard_avatar.animation_graph import load_reference_animation_graph_v2
from wizard_avatar.animation_trace import AnimationTruthTraceV1
from wizard_avatar.reference_avatar import get_reference_pose


REPORT_SCHEMA = "character_director_v4_machine_acceptance_v1"
EXPECTED_SCENARIOS = (
    "v4-ready",
    "v4-thought-one-explain",
    "v4-thought-one-hold",
    "v4-thought-two-explain",
    "v4-thought-two-hold",
    "v4-thought-three-point",
    "v4-settle",
)
EXPECTED_FRAME_COUNTS = {
    "v4-ready": 12,
    "v4-thought-one-explain": 30,
    "v4-thought-one-hold": 18,
    "v4-thought-two-explain": 30,
    "v4-thought-two-hold": 18,
    "v4-thought-three-point": 30,
    "v4-settle": 24,
}
EXPLAIN_SCENARIOS = ("v4-thought-one-explain", "v4-thought-two-explain")
POINT_SCENARIO = "v4-thought-three-point"
HOLD_SCENARIOS = ("v4-thought-one-hold", "v4-thought-two-hold", "v4-settle")
EXPECTED_EXPLAIN_MARKERS = (
    ("action_commit", 2),
    ("speech_open", 6),
    ("action_effect", 6),
    ("speech_close", 13),
    ("action_recoverable", 18),
    ("action_settled", 19),
)
EXPECTED_POINT_MARKERS = (
    ("action_commit", 2),
    ("action_effect", 6),
    ("action_recoverable", 16),
    ("action_settled", 17),
)


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
    return max(max(abs(x - origin[0]), abs(y - origin[1])) for x, y in points)


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


def _pose_colors(pose_id: str) -> set[Tuple[int, int, int]]:
    return {cell.rgb for cell in get_reference_pose(pose_id).cells}


def _clip_pose_sequence(clip_id: str) -> List[str]:
    clip = load_reference_animation_graph_v2().clips[clip_id]
    return [sample.pose_id for sample in clip.samples for _ in range(sample.duration_frames)]


def analyze_v4(
    manifest: Mapping[str, Any],
    trace_records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "schema_version": 1,
        "acceptance_scenario": "V4",
        "passed": False,
        "checks": [],
        "metrics": {},
        "review_boundary": (
            "Machine checks do not replace normal-speed and quarter-speed review "
            "of gesture motivation, accents, silhouette, restraint, and acting rhythm."
        ),
    }
    program = manifest.get("scenario_program")
    _check(
        report,
        "scenario_program_identity",
        isinstance(program, Mapping)
        and program.get("program_id") == "v4-thought-groups"
        and program.get("acceptance_scenario") == "V4"
        and program.get("total_duration_seconds") == 6.75,
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
        and all(right == left + 1 for left, right in zip(indexes, indexes[1:]))
        for indexes in scenario_indexes.values()
    )
    boundary_ranges = [
        range(scenario_indexes[left][-1] + 1, scenario_indexes[right][0])
        for left, right in zip(EXPECTED_SCENARIOS, EXPECTED_SCENARIOS[1:])
    ]
    unowned_indexes = [frame.get("frame_index") for frame in unowned_frames]
    unowned_are_bounded = (
        len(unowned_frames) <= len(EXPECTED_SCENARIOS) - 1
        and all(frame.get("scenario") is None for frame in unowned_frames)
        and all(
            type(index) is int and any(index in boundary for boundary in boundary_ranges)
            for index in unowned_indexes
        )
    )
    _check(
        report,
        "complete_contiguous_capture",
        len(frames) == len(trace_records) == len(complete)
        and not missing
        and len(owned_frames) == 162
        and transport_contiguous
        and scenario_blocks_contiguous
        and unowned_are_bounded
        and counts == EXPECTED_FRAME_COUNTS,
        {
            "frame_count": len(frames),
            "trace_count": len(trace_records),
            "owned_frame_count": len(owned_frames),
            "unowned_transition_frame_indexes": unowned_indexes,
            "missing_trace_frames": missing,
            "transport_contiguous": transport_contiguous,
            "scenario_blocks_contiguous": scenario_blocks_contiguous,
            "unowned_are_bounded_transitions": unowned_are_bounded,
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
    explain_markers = {name: _marker_events(by_scenario[name]) for name in EXPLAIN_SCENARIOS}
    point_markers = _marker_events(by_scenario[POINT_SCENARIO])
    _check(
        report,
        "three_motivated_strokes_in_authored_order",
        all(tuple(explain_markers[name]) == EXPECTED_EXPLAIN_MARKERS for name in EXPLAIN_SCENARIOS)
        and tuple(point_markers) == EXPECTED_POINT_MARKERS,
        {"explain": explain_markers, "point": point_markers},
    )

    explain_coverage = {
        name: sorted(
            {
                int(trace["animation_authored_frame"])
                for trace in by_scenario[name]
                if trace.get("animation_clip_id") == "explain_front"
            }
        )
        for name in EXPLAIN_SCENARIOS
    }
    point_coverage = sorted(
        {
            int(trace["animation_authored_frame"])
            for trace in by_scenario[POINT_SCENARIO]
            if trace.get("animation_clip_id") == "point_front"
        }
    )
    hold_pose_failures = {
        name: [
            trace.get("frame_index")
            for trace in by_scenario[name]
            if trace.get("rendered_pose_id") != "front_idle"
            or trace.get("animation_clip_id") != "idle_front"
        ]
        for name in HOLD_SCENARIOS
    }
    _check(
        report,
        "thought_group_holds_and_recovery",
        set().union(*(set(frames_seen) for frames_seen in explain_coverage.values()))
        >= set(range(20))
        and set(point_coverage) >= set(range(1, 18))
        and by_scenario[POINT_SCENARIO]
        and by_scenario[POINT_SCENARIO][0].get("rendered_pose_id") == "front_idle"
        and not any(hold_pose_failures.values()),
        {
            "explain_authored_coverage": explain_coverage,
            "point_authored_coverage": point_coverage,
            "hold_pose_failures": hold_pose_failures,
        },
    )

    explain_sequence = _clip_pose_sequence("explain_front")
    point_sequence = _clip_pose_sequence("point_front")
    expected_explain = [
        "front_idle",
        "front_idle",
        "explain_front_in_20",
        "explain_front_in_40",
        "explain_front_in_60",
        "explain_front_in_80",
        *(["explaining"] * 8),
        "explain_front_in_80",
        "explain_front_in_60",
        "explain_front_in_40",
        "explain_front_in_20",
        "front_idle",
        "front_idle",
    ]
    expected_point = [
        "front_idle",
        "front_idle",
        "point_front_in_20",
        "point_front_in_40",
        "point_front_in_60",
        "point_front_in_80",
        *(["point_front_contact_locked"] * 6),
        "point_front_in_80",
        "point_front_in_60",
        "point_front_in_40",
        "point_front_in_20",
        "front_idle",
        "front_idle",
    ]
    endpoint_colors = {
        "explain": _pose_colors("front_idle") | _pose_colors("explaining"),
        "point": _pose_colors("front_idle")
        | _pose_colors("front_point_direct_staff_held"),
    }
    color_failures = []
    for family, prefix in (("explain", "explain_front_in_"), ("point", "point_front_in_")):
        for amount in (20, 40, 60, 80):
            pose_id = f"{prefix}{amount}"
            unexpected = _pose_colors(pose_id) - endpoint_colors[family]
            if unexpected:
                color_failures.append({"pose_id": pose_id, "unexpected_color_count": len(unexpected)})
    _check(
        report,
        "atomic_landmark_warp_graph_contract",
        explain_sequence == expected_explain
        and point_sequence == expected_point
        and not color_failures
        and get_reference_pose("front_idle").root_anchor
        == get_reference_pose("explaining").root_anchor
        == get_reference_pose("point_front_contact_locked").root_anchor
        and get_reference_pose("front_idle").anchors["left_foot"]
        == get_reference_pose("point_front_contact_locked").anchors["left_foot"],
        {
            "explain_sequence": explain_sequence,
            "point_sequence": point_sequence,
            "color_failures": color_failures,
        },
    )

    action_records = [
        trace
        for name in (*EXPLAIN_SCENARIOS, POINT_SCENARIO)
        for trace in by_scenario[name]
        if trace.get("animation_clip_id") in {"explain_front", "point_front"}
    ]
    world_roots = [
        (float(trace.get("world_root_x", math.inf)), float(trace.get("world_root_z", math.inf)))
        for trace in action_records
    ]
    stage_roots = [
        point
        for trace in action_records
        if (point := _point(trace.get("presented_root_stage"))) is not None
    ]
    world_root_drift = _maximum_axis_drift(world_roots)
    stage_root_drift = _maximum_axis_drift(stage_roots)
    contact = manifest.get("contact_verification", {})
    _check(
        report,
        "planted_root_during_all_gestures",
        len(world_roots) == len(stage_roots) == len(action_records)
        and world_root_drift <= 1e-6
        and stage_root_drift <= 1e-6
        and isinstance(contact, Mapping)
        and contact.get("passed") is True
        and float(contact.get("maximum_planted_drift_cells", math.inf)) <= 1.0,
        {
            "world_root_max_axis_drift": world_root_drift,
            "stage_root_max_axis_drift": stage_root_drift,
            "contact_passed": contact.get("passed") if isinstance(contact, Mapping) else None,
            "maximum_planted_drift_cells": contact.get("maximum_planted_drift_cells") if isinstance(contact, Mapping) else None,
        },
    )

    cols = int(manifest.get("init", {}).get("cols", 0) or 0)
    rows = int(manifest.get("init", {}).get("rows", 0) or 0)
    clipped = []
    for trace in action_records:
        span = trace.get("silhouette_raster_span")
        if not isinstance(span, Mapping) or not (
            0 <= int(span.get("min_x", -1)) <= int(span.get("max_x", cols)) < cols
            and 0 <= int(span.get("min_y", -1)) <= int(span.get("max_y", rows)) < rows
        ):
            clipped.append(trace.get("frame_index"))
    _check(
        report,
        "gesture_silhouettes_within_canonical_stage",
        bool(action_records) and cols > 0 and rows > 0 and not clipped,
        {"stage": [cols, rows], "clipped_frames": clipped},
    )

    report["metrics"] = {
        "frame_count": len(frames),
        "owned_frame_count": len(owned_frames),
        "action_trace_count": len(action_records),
        "stroke_count": sum(
            marker == "action_effect"
            for marker, _frame in [
                *(event for events in explain_markers.values() for event in events),
                *point_markers,
            ]
        ),
        "world_root_max_axis_drift": world_root_drift,
        "stage_root_max_axis_drift": stage_root_drift,
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
    return analyze_v4(manifest, traces)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Character Director V4 evidence.")
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
