#!/usr/bin/env python3
"""Evaluate the machine-verifiable portion of Character Director scenario V1."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_character_director_visual_review import validate_manifest
from wizard_avatar.animation_trace import AnimationTruthTraceV1


REPORT_SCHEMA = "character_director_v1_machine_acceptance_v1"
EXPECTED_SCENARIOS = (
    "v1-viewer-listen",
    "v1-left-target",
    "v1-viewer-return",
    "v1-release-gaze",
    "v1-ninety-degree-turn",
)


def _utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("capture timestamp must be text")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("capture timestamp is not ISO-8601 UTC") from exc


def _compact(values: Sequence[object]) -> List[object]:
    result: List[object] = []
    for value in values:
        if not result or result[-1] != value:
            result.append(value)
    return result


def _closed_ranges(records: Sequence[Mapping[str, Any]]) -> List[Tuple[int, int]]:
    runs: List[Tuple[int, int]] = []
    start: Optional[int] = None
    for index, record in enumerate(records):
        channels = record["presentation_channels"]
        if channels["blink_closed"]:
            if start is None:
                start = index
        elif start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(records)))
    return runs


def _check(report: Dict[str, Any], name: str, passed: bool, detail: object) -> None:
    report["checks"].append(
        {"name": name, "passed": bool(passed), "detail": detail}
    )


def analyze_v1(
    manifest: Mapping[str, Any],
    trace_records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "schema_version": 1,
        "acceptance_scenario": "V1",
        "passed": False,
        "checks": [],
        "metrics": {},
        "review_boundary": (
            "Machine checks do not replace normal-speed, quarter-speed, or "
            "two-independent-reviewer acting judgment."
        ),
    }
    program = manifest.get("scenario_program")
    _check(
        report,
        "scenario_program_identity",
        isinstance(program, Mapping)
        and program.get("program_id") == "v1-listening"
        and program.get("acceptance_scenario") == "V1"
        and program.get("total_duration_seconds") == 12.0,
        program,
    )
    scenario_names = tuple(item.get("name") for item in manifest.get("scenarios", ()))
    _check(
        report,
        "scenario_order",
        scenario_names == EXPECTED_SCENARIOS,
        list(scenario_names),
    )

    frames = manifest.get("frames", ())
    commands = manifest.get("commands", ())
    trace_by_index = {item.get("frame_index"): item for item in trace_records}
    paired: List[Tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    missing_channels: List[int] = []
    for frame in frames:
        trace = trace_by_index.get(frame.get("frame_index"))
        if trace is None:
            continue
        if not isinstance(trace.get("presentation_channels"), Mapping):
            missing_channels.append(frame["frame_index"])
        paired.append((frame, trace))
    _check(
        report,
        "atomic_channel_coverage",
        len(paired) == len(frames) == len(trace_records) and not missing_channels,
        {
            "frame_count": len(frames),
            "trace_count": len(trace_records),
            "paired_count": len(paired),
            "missing_channel_frames": missing_channels,
        },
    )

    captured: Dict[str, List[Mapping[str, Any]]] = {}
    for command in commands:
        name = command.get("scenario")
        try:
            started = _utc(command.get("capture_started_at_utc"))
            completed = _utc(command.get("capture_completed_at_utc"))
        except ValueError:
            captured[str(name)] = []
            continue
        captured[str(name)] = [
            trace
            for frame, trace in paired
            if frame.get("scenario") == name
            and started <= _utc(frame.get("received_at_utc")) <= completed
        ]
    _check(
        report,
        "acknowledged_capture_windows",
        set(captured) == set(EXPECTED_SCENARIOS)
        and all(captured.get(name) for name in EXPECTED_SCENARIOS),
        {name: len(captured.get(name, ())) for name in EXPECTED_SCENARIOS},
    )

    def channels(name: str) -> List[Mapping[str, Any]]:
        return [item["presentation_channels"] for item in captured.get(name, ())]

    viewer = channels("v1-viewer-listen")
    left = channels("v1-left-target")
    returned = channels("v1-viewer-return")
    released = channels("v1-release-gaze")
    turn_records = captured.get("v1-ninety-degree-turn", ())
    turn = channels("v1-ninety-degree-turn")
    _check(
        report,
        "viewer_left_viewer_gaze",
        bool(viewer and left and returned and released)
        and all(item["gaze_aim"] == 0 for item in viewer)
        and all(item["gaze_aim"] == -1 and item["gaze_authoritative"] for item in left)
        and all(item["gaze_aim"] == 0 and item["gaze_authoritative"] for item in returned)
        and all(item["gaze_aim"] == 0 and not item["gaze_authoritative"] for item in released),
        {
            "viewer_aims": sorted({item["gaze_aim"] for item in viewer}),
            "left_aims": sorted({item["gaze_aim"] for item in left}),
            "return_aims": sorted({item["gaze_aim"] for item in returned}),
            "released_authority": sorted({item["gaze_authoritative"] for item in released}),
        },
    )

    turn_facings = [item.get("presented_facing") for item in turn_records]
    turn_phases = [item["head_eye_phase"] for item in turn]
    turn_head_poses = [item.get("rendered_head_pose_id") for item in turn]
    target_indexes = [
        index for index, facing in enumerate(turn_facings) if facing == "west"
    ]
    first_target = target_indexes[0] if target_indexes else None
    _check(
        report,
        "ninety_degree_eye_lead_head_follow_settle",
        bool(turn)
        and _compact(turn_facings) == ["south", "southwest", "west"]
        and "leading" in turn_phases
        and "turning" in turn_phases
        and "settling" in turn_phases
        and "steady" in turn_phases
        and any(
            item["head_eye_phase"] == "leading" and item["gaze_aim"] == -1
            for item in turn
        )
        and first_target is not None
        and turn[first_target]["gaze_aim"] == 0
        and all(item["gaze_aim"] == 0 for item in turn[first_target:]),
        {
            "facing_sequence": _compact(turn_facings),
            "phase_sequence": _compact(turn_phases),
            "first_target_frame_offset": first_target,
            "first_target_gaze_aim": (
                None if first_target is None else turn[first_target]["gaze_aim"]
            ),
            "rendered_head_pose_sequence": _compact(turn_head_poses),
        },
    )
    _check(
        report,
        "head_only_turn_uses_no_locomotion_pose",
        bool(turn_records)
        and all(item.get("rendered_pose_id") == "front_idle" for item in turn_records)
        and "profile_left" in turn_head_poses,
        {
            "body_pose_sequence": _compact(
                [item.get("rendered_pose_id") for item in turn_records]
            ),
            "head_pose_sequence": _compact(turn_head_poses),
        },
    )
    _check(
        report,
        "authored_three_quarter_head_bridge",
        bool(turn_records)
        and _compact(turn_head_poses)
        == ["front_idle", "walk_front_left", "profile_left"],
        {
            "head_pose_sequence": _compact(turn_head_poses),
            "body_pose_sequence": _compact(
                [item.get("rendered_pose_id") for item in turn_records]
            ),
        },
    )

    all_trace = [trace for _, trace in paired]
    blink_ranges = _closed_ranges(all_trace) if not missing_channels else []
    blink_runs = [end - start for start, end in blink_ranges]
    fps = float(manifest.get("init", {}).get("fps", 0.0) or 0.0)
    blink_durations_ms = [round(run * 1000.0 / fps, 3) for run in blink_runs] if fps else []
    visible_blink_runs = []
    for start, end in blink_ranges:
        painted = all(
            int(all_trace[index]["presentation_channels"].get("blink_painted_cells", 0))
            > 0
            for index in range(start, end)
        )
        changed_on_close = start == 0 or (
            all_trace[start].get("frame_sha256")
            != all_trace[start - 1].get("frame_sha256")
        )
        changed_on_open = end == len(all_trace) or (
            all_trace[end - 1].get("frame_sha256")
            != all_trace[end].get("frame_sha256")
        )
        visible_blink_runs.append(painted and changed_on_close and changed_on_open)
    _check(
        report,
        "two_blinks_with_bounded_closure",
        len(blink_runs) >= 2
        and all(3 <= run <= 4 for run in blink_runs[:2])
        and all(100.0 <= duration <= 200.0 for duration in blink_durations_ms[:2])
        and all(visible_blink_runs[:2]),
        {
            "closed_frame_runs": blink_runs,
            "durations_ms": blink_durations_ms,
            "visible_runs": visible_blink_runs,
        },
    )

    eye_bound_failures = []
    for trace in all_trace:
        channels_value = trace["presentation_channels"]
        apertures = channels_value.get("eye_apertures", ())
        for point in channels_value.get("eye_blue_cells", ()):
            if not any(
                aperture["min_x"] <= point["x"] <= aperture["max_x"]
                and aperture["min_y"] <= point["y"] <= aperture["max_y"]
                for aperture in apertures
            ):
                eye_bound_failures.append(trace.get("frame_index"))
    _check(
        report,
        "explicit_eye_aperture_bounds",
        bool(all_trace)
        and all(
            item["presentation_channels"].get("eye_apertures")
            for item in all_trace
        )
        and not eye_bound_failures,
        {"escaped_frames": eye_bound_failures},
    )

    roots = [(item.get("world_root_x"), item.get("world_root_z")) for item in all_trace]
    root_x = [float(item[0]) for item in roots if isinstance(item[0], (int, float))]
    root_z = [float(item[1]) for item in roots if isinstance(item[1], (int, float))]
    root_span = {
        "x": max(root_x) - min(root_x) if root_x else math.inf,
        "z": max(root_z) - min(root_z) if root_z else math.inf,
    }
    all_channels = [item["presentation_channels"] for item in all_trace if isinstance(item.get("presentation_channels"), Mapping)]
    unique_frame_hashes = len({item.get("frame_sha256") for item in all_trace})
    _check(
        report,
        "listening_stillness_and_silence",
        root_span["x"] <= 1e-9
        and root_span["z"] <= 1e-9
        and bool(all_channels)
        and all(item["locomotion"] == "idle" for item in all_channels)
        and all(item["action"] == "idle" for item in all_channels)
        and all(item["rendered_mouth_shape"] == "closed" for item in all_channels)
        and all(item["speech_mouth_authority"] == "none" for item in all_channels)
        and unique_frame_hashes >= 8,
        {
            "root_span": root_span,
            "locomotion_values": sorted({item["locomotion"] for item in all_channels}),
            "action_values": sorted({item["action"] for item in all_channels}),
            "mouth_values": sorted({item["rendered_mouth_shape"] for item in all_channels}),
            "speech_authorities": sorted({item["speech_mouth_authority"] for item in all_channels}),
            "unique_presented_frame_hashes": unique_frame_hashes,
        },
    )

    report["metrics"] = {
        "frame_count": len(frames),
        "paired_trace_count": len(paired),
        "blink_count": len(blink_runs),
        "blink_durations_ms": blink_durations_ms,
        "turn_facing_sequence": _compact(turn_facings),
        "turn_phase_sequence": _compact(turn_phases),
        "turn_head_pose_sequence": _compact(turn_head_poses),
        "root_span": root_span,
        "unique_presented_frame_hashes": unique_frame_hashes,
    }
    report["passed"] = bool(report["checks"]) and all(
        item["passed"] for item in report["checks"]
    )
    return report


def load_and_analyze(manifest_path: Path) -> Dict[str, Any]:
    evidence_dir = manifest_path.resolve().parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest, evidence_dir)
    trace_path = evidence_dir / manifest["animation_truth_trace"]["path"]
    trace_records: List[Mapping[str, Any]] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if line:
            record = AnimationTruthTraceV1.from_mapping(json.loads(line))
            trace_records.append(record.to_mapping())
    return analyze_v1(manifest, trace_records)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Character Director V1 evidence.")
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
