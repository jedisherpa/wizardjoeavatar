#!/usr/bin/env python3
"""Evaluate the machine-verifiable portion of Character Director scenario V7."""

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


REPORT_SCHEMA = "character_director_v7_machine_acceptance_v1"
EXPECTED_SCENARIOS = (
    "v7-ready",
    "v7-precommit-cast",
    "v7-precommit-new-turn",
    "v7-precommit-settle",
    "v7-postcommit-reset",
    "v7-postcommit-cast",
    "v7-postcommit-new-turn",
    "v7-final-settle",
)
EXPECTED_FRAME_COUNTS = {
    "v7-ready": 12,
    "v7-precommit-cast": 3,
    "v7-precommit-new-turn": 36,
    "v7-precommit-settle": 12,
    "v7-postcommit-reset": 12,
    "v7-postcommit-cast": 6,
    "v7-postcommit-new-turn": 54,
    "v7-final-settle": 18,
}
EXPECTED_MARKERS = (
    "action_commit",
    "action_effect",
    "action_recoverable",
    "action_settled",
)


def _check(report: Dict[str, Any], name: str, passed: bool, detail: object) -> None:
    report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})


def _channels(trace: Mapping[str, Any]) -> Mapping[str, Any]:
    value = trace.get("presentation_channels")
    return value if isinstance(value, Mapping) else {}


def _point(trace: Mapping[str, Any]) -> Optional[Tuple[float, float]]:
    value = trace.get("presented_root_stage")
    if not isinstance(value, Mapping):
        return None
    x, y = value.get("x"), value.get("y")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in (x, y)):
        return None
    point = float(x), float(y)
    return point if all(math.isfinite(item) for item in point) else None


def _events(records: Sequence[Mapping[str, Any]]) -> List[Tuple[str, int, int]]:
    result: List[Tuple[str, int, int]] = []
    for trace in records:
        for event in trace.get("presentation_marker_events", ()):
            if not isinstance(event, Mapping):
                continue
            marker = event.get("marker_id")
            authored = event.get("animation_authored_frame")
            frame_index = trace.get("frame_index")
            if isinstance(marker, str) and type(authored) is int and type(frame_index) is int:
                result.append((marker, authored, frame_index))
    return result


def _inside_stage(trace: Mapping[str, Any], cols: int, rows: int) -> bool:
    span = trace.get("silhouette_raster_span")
    return isinstance(span, Mapping) and (
        0 <= int(span.get("min_x", -1)) <= int(span.get("max_x", cols)) < cols
        and 0 <= int(span.get("min_y", -1)) <= int(span.get("max_y", rows)) < rows
    )


def analyze_v7(
    manifest: Mapping[str, Any],
    trace_records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "schema_version": 1,
        "acceptance_scenario": "V7",
        "passed": False,
        "checks": [],
        "metrics": {},
        "review_boundary": (
            "Machine checks do not replace normal-speed and quarter-speed review "
            "of interruption recovery, emotional continuity, and pose appeal."
        ),
    }
    program = manifest.get("scenario_program")
    _check(
        report,
        "scenario_program_identity",
        isinstance(program, Mapping)
        and program.get("program_id") == "v7-cast-interruption"
        and program.get("acceptance_scenario") == "V7"
        and program.get("total_duration_seconds") == 6.375,
        program,
    )
    scenario_names = tuple(item.get("name") for item in manifest.get("scenarios", ()))
    _check(report, "scenario_order", scenario_names == EXPECTED_SCENARIOS, list(scenario_names))

    frames = manifest.get("frames", ())
    trace_by_index = {item.get("frame_index"): item for item in trace_records}
    owned = [frame for frame in frames if frame.get("capture_owned") is True]
    unowned = [frame for frame in frames if frame.get("capture_owned") is not True]
    frame_indexes = [frame.get("frame_index") for frame in frames]
    counts = {
        name: sum(frame.get("capture_owned") is True and frame.get("scenario") == name for frame in frames)
        for name in EXPECTED_SCENARIOS
    }
    missing_trace = [
        frame.get("frame_index") for frame in frames
        if frame.get("frame_index") not in trace_by_index
    ]
    contiguous = bool(frame_indexes) and all(
        type(left) is int and type(right) is int and right == left + 1
        for left, right in zip(frame_indexes, frame_indexes[1:])
    )
    _check(
        report,
        "complete_contiguous_capture",
        len(frames) == len(trace_records)
        and not missing_trace
        and len(owned) == sum(EXPECTED_FRAME_COUNTS.values())
        and len(unowned) <= len(EXPECTED_SCENARIOS) - 1
        and all(frame.get("scenario") is None for frame in unowned)
        and contiguous
        and counts == EXPECTED_FRAME_COUNTS,
        {
            "frame_count": len(frames),
            "owned_frame_count": len(owned),
            "unowned_frame_indexes": [frame.get("frame_index") for frame in unowned],
            "missing_trace_frames": missing_trace,
            "transport_contiguous": contiguous,
            "scenario_frame_counts": counts,
        },
    )
    by_scenario = {
        name: [
            trace_by_index[frame["frame_index"]]
            for frame in frames
            if frame.get("capture_owned") is True
            and frame.get("scenario") == name
            and frame.get("frame_index") in trace_by_index
        ]
        for name in EXPECTED_SCENARIOS
    }

    pre_cast = by_scenario["v7-precommit-cast"]
    pre_turn = by_scenario["v7-precommit-new-turn"]
    pre_records = pre_cast + pre_turn
    pre_events = _events(pre_records)
    pre_speech_offsets = [
        index for index, trace in enumerate(pre_turn)
        if _channels(trace).get("speech_mouth_authority") != "none"
        and _channels(trace).get("action") == "speaking"
    ]
    _check(
        report,
        "precommit_interrupt_cancels_without_effect",
        bool(pre_cast)
        and all(trace.get("animation_clip_id") == "cast_front" for trace in pre_cast)
        and not pre_events
        and all(float(trace.get("effect_intensity", 0.0)) == 0.0 for trace in pre_records)
        and bool(pre_speech_offsets)
        and pre_speech_offsets[0] <= 2
        and all(
            trace.get("animation_clip_id") != "cast_front"
            for trace in pre_turn[pre_speech_offsets[0] :]
        ),
        {
            "marker_events": pre_events,
            "speech_start_owned_frame_offset": pre_speech_offsets[0] if pre_speech_offsets else None,
            "cast_frames_after_speech_start": [
                trace.get("frame_index")
                for trace in pre_turn[pre_speech_offsets[0] if pre_speech_offsets else 0 :]
                if trace.get("animation_clip_id") == "cast_front"
            ],
        },
    )

    post_cast = by_scenario["v7-postcommit-cast"]
    post_turn = by_scenario["v7-postcommit-new-turn"]
    post_records = post_cast + post_turn
    post_events = _events(post_records)
    post_markers = [item[0] for item in post_events]
    post_speech_offsets = [
        index for index, trace in enumerate(post_turn)
        if _channels(trace).get("speech_mouth_authority") != "none"
        and _channels(trace).get("action") == "speaking"
    ]
    settled_event = next((item for item in post_events if item[0] == "action_settled"), None)
    first_speech_frame = (
        post_turn[post_speech_offsets[0]].get("frame_index") if post_speech_offsets else None
    )
    _check(
        report,
        "postcommit_interrupt_finishes_recovery_then_speaks",
        post_markers == list(EXPECTED_MARKERS)
        and bool(post_speech_offsets)
        and post_speech_offsets[0] <= 12
        and settled_event is not None
        and type(first_speech_frame) is int
        and settled_event[2] <= first_speech_frame
        and all(
            trace.get("animation_clip_id") != "cast_front"
            and trace.get("effect_phase") == "inactive"
            and float(trace.get("effect_intensity", 0.0)) == 0.0
            for trace in post_turn[post_speech_offsets[0] :]
        ),
        {
            "marker_events": post_events,
            "speech_start_owned_frame_offset": post_speech_offsets[0] if post_speech_offsets else None,
            "action_settled_frame": settled_event[2] if settled_event else None,
            "first_speech_frame": first_speech_frame,
        },
    )

    all_records = [
        trace_by_index[frame["frame_index"]]
        for frame in frames
        if frame.get("frame_index") in trace_by_index
    ]
    roots = [_point(trace) for trace in all_records]
    root_steps = [
        max(abs(right[0] - left[0]), abs(right[1] - left[1]))
        for left, right in zip(roots, roots[1:])
        if left is not None and right is not None
    ]
    _check(
        report,
        "interruption_root_continuity",
        bool(root_steps) and max(root_steps) <= 1.0,
        {"maximum_presented_root_axis_step": max(root_steps, default=math.inf)},
    )

    final_records = by_scenario["v7-final-settle"]
    _check(
        report,
        "final_neutral_settle",
        len(final_records) >= 8
        and all(
            trace.get("animation_clip_id") == "idle_front"
            and trace.get("effect_phase") == "inactive"
            and float(trace.get("effect_intensity", 0.0)) == 0.0
            and _channels(trace).get("action") == "idle"
            and _channels(trace).get("speech_mouth_authority") == "none"
            for trace in final_records[-8:]
        ),
        {
            "terminal_pose_ids": [trace.get("rendered_pose_id") for trace in final_records[-8:]],
            "terminal_actions": [_channels(trace).get("action") for trace in final_records[-8:]],
        },
    )

    cols = int(manifest.get("init", {}).get("cols", 0) or 0)
    rows = int(manifest.get("init", {}).get("rows", 0) or 0)
    clipped = [
        trace.get("frame_index") for trace in all_records
        if not _inside_stage(trace, cols, rows)
    ]
    _check(
        report,
        "interruption_performance_within_canonical_stage",
        cols > 0 and rows > 0 and not clipped,
        {"stage": [cols, rows], "clipped_frames": clipped},
    )

    report["metrics"] = {
        "frame_count": len(frames),
        "owned_frame_count": len(owned),
        "precommit_speech_start_offset": pre_speech_offsets[0] if pre_speech_offsets else None,
        "postcommit_speech_start_offset": post_speech_offsets[0] if post_speech_offsets else None,
        "postcommit_marker_count": len(post_events),
        "maximum_presented_root_axis_step": max(root_steps, default=math.inf),
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
    return analyze_v7(manifest, traces)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Character Director V7 evidence.")
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
