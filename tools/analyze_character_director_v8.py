#!/usr/bin/env python3
"""Evaluate the machine-verifiable portion of Character Director scenario V8."""

from __future__ import annotations

import argparse
import hashlib
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


REPORT_SCHEMA = "character_director_v8_machine_acceptance_v1"
SCENARIO = "v8-continuous-performance"
EXPECTED_FRAMES = 1440
EXPECTED_SPEECH_IDS = ("v8-phrase-1", "v8-phrase-2", "v8-phrase-3")
EXPECTED_GESTURES = ("v8-gesture-one", "v8-gesture-two", "v8-gesture-three")
MINIMUM_GESTURE_SPACING_FRAMES = 192
MINIMUM_BLINK_COUNT = 8
MINIMUM_BLINK_INTERVAL_FRAMES = 60
MAXIMUM_BLINK_INTERVAL_FRAMES = 156
MINIMUM_BODY_STILLNESS = 0.70
MINIMUM_PHRASE_STILLNESS = 0.90


def _check(report: Dict[str, Any], name: str, passed: bool, detail: object) -> None:
    report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})


def _channels(trace: Mapping[str, Any]) -> Mapping[str, Any]:
    value = trace.get("presentation_channels")
    return value if isinstance(value, Mapping) else {}


def _inside_stage(trace: Mapping[str, Any], cols: int, rows: int) -> bool:
    span = trace.get("silhouette_raster_span")
    return isinstance(span, Mapping) and (
        0 <= int(span.get("min_x", -1)) <= int(span.get("max_x", cols)) < cols
        and 0 <= int(span.get("min_y", -1)) <= int(span.get("max_y", rows)) < rows
    )


def _point(trace: Mapping[str, Any]) -> Optional[Tuple[float, float]]:
    value = trace.get("presented_root_stage")
    if not isinstance(value, Mapping):
        return None
    x, y = value.get("x"), value.get("y")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in (x, y)):
        return None
    result = float(x), float(y)
    return result if all(math.isfinite(item) for item in result) else None


def _stillness_ratio(records: Sequence[Mapping[str, Any]]) -> float:
    hashes = [_channels(item).get("body_pixel_sha256") for item in records]
    pairs = list(zip(hashes, hashes[1:]))
    if not pairs:
        return 0.0
    return sum(left == right for left, right in pairs) / len(pairs)


def _closed_ranges(records: Sequence[Mapping[str, Any]]) -> List[Tuple[int, int]]:
    result: List[Tuple[int, int]] = []
    start: Optional[int] = None
    for index, trace in enumerate(records):
        if _channels(trace).get("blink_closed") is True and start is None:
            start = index
        elif _channels(trace).get("blink_closed") is not True and start is not None:
            result.append((start, index))
            start = None
    if start is not None:
        result.append((start, len(records)))
    return result


def _nonconstant_loop_period(signatures: Sequence[Tuple[object, ...]]) -> Optional[int]:
    for period in range(2, min(192, len(signatures) // 3 + 1)):
        run = 0
        for index in range(period, len(signatures)):
            if signatures[index] == signatures[index - period]:
                run += 1
                if run >= period * 3:
                    start = index - run + 1
                    sample = signatures[max(0, start - period) : index + 1]
                    if len(set(sample)) > 1:
                        return period
            else:
                run = 0
    return None


def _effect_events(records: Sequence[Mapping[str, Any]]) -> List[int]:
    result: List[int] = []
    for trace in records:
        for event in trace.get("presentation_marker_events", ()):
            if (
                isinstance(event, Mapping)
                and event.get("marker_id") == "action_effect"
                and type(trace.get("frame_index")) is int
            ):
                result.append(int(trace["frame_index"]))
    return result


def analyze_v8(
    manifest: Mapping[str, Any],
    trace_records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "schema_version": 1,
        "acceptance_scenario": "V8",
        "passed": False,
        "checks": [],
        "metrics": {},
        "review_boundary": (
            "Machine checks do not replace normal-speed and quarter-speed review "
            "of purposeful stillness, repeated-phrase freshness, and acting appeal."
        ),
    }
    program = manifest.get("scenario_program")
    _check(
        report,
        "scenario_program_identity",
        isinstance(program, Mapping)
        and program.get("schema") == "character_director_scenario_program_v2"
        and program.get("schema_version") == 2
        and program.get("program_id") == "v8-purposeful-performance"
        and program.get("acceptance_scenario") == "V8"
        and program.get("maximum_capture_frame_count") == EXPECTED_FRAMES,
        program,
    )

    frames = manifest.get("frames", ())
    trace_by_index = {item.get("frame_index"): item for item in trace_records}
    owned_frames = [
        frame
        for frame in frames
        if frame.get("capture_owned") is True and frame.get("scenario") == SCENARIO
    ]
    owned_indexes = [frame.get("frame_index") for frame in owned_frames]
    owned_traces = [
        trace_by_index[index]
        for index in owned_indexes
        if index in trace_by_index
    ]
    contiguous = bool(owned_indexes) and all(
        type(left) is int and type(right) is int and right == left + 1
        for left, right in zip(owned_indexes, owned_indexes[1:])
    )
    missing_trace = [index for index in owned_indexes if index not in trace_by_index]
    _check(
        report,
        "continuous_sixty_second_capture",
        len(owned_frames) == EXPECTED_FRAMES
        and len(owned_traces) == EXPECTED_FRAMES
        and not missing_trace
        and contiguous
        and all(
            frame.get("scenario") in {None, SCENARIO}
            for frame in frames
        ),
        {
            "owned_frame_count": len(owned_frames),
            "trace_count": len(owned_traces),
            "first_owned_frame": owned_indexes[0] if owned_indexes else None,
            "last_owned_frame": owned_indexes[-1] if owned_indexes else None,
            "missing_trace_frames": missing_trace,
            "owned_transport_contiguous": contiguous,
        },
    )

    commands = [
        item for item in manifest.get("commands", ()) if isinstance(item, Mapping)
    ]
    scheduled = [
        item for item in commands if item.get("scheduled_for_scenario") == SCENARIO
    ]
    schedule_timing = {
        item.get("scenario"): {
            "scheduled": item.get("scheduled_at_frame"),
            "observed": item.get("dispatch_observed_after_frame_count"),
            "completed": item.get("dispatch_completed_after_frame_count"),
        }
        for item in scheduled
    }
    schedule_exact = all(
        type(item.get("scheduled_at_frame")) is int
        and type(item.get("dispatch_observed_after_frame_count")) is int
        and item["scheduled_at_frame"]
        <= item["dispatch_observed_after_frame_count"]
        <= item["scheduled_at_frame"] + 2
        and isinstance(item.get("ack"), Mapping)
        and item["ack"].get("disposition") == "applied"
        for item in scheduled
    )
    _check(
        report,
        "bounded_trace_synchronized_command_schedule",
        len(scheduled) == 12
        and schedule_exact
        and [item.get("source_sequence") for item in commands]
        == list(range(1, len(commands) + 1)),
        schedule_timing,
    )

    speech_commands = [item for item in scheduled if item.get("kind") == "speak"]
    phrase_hashes = [
        hashlib.sha256(
            str(item.get("payload", {}).get("text", "")).encode("utf-8")
        ).hexdigest()
        for item in speech_commands
    ]
    phrase_ids = tuple(
        item.get("payload", {}).get("speech_id") for item in speech_commands
    )
    phrase_windows = {
        speech_id: [
            trace
            for trace in owned_traces
            if _channels(trace).get("speech_id") == speech_id
        ]
        for speech_id in EXPECTED_SPEECH_IDS
    }
    phrase_stillness = {
        speech_id: _stillness_ratio(records)
        for speech_id, records in phrase_windows.items()
    }
    _check(
        report,
        "three_identical_phrases_with_distinct_identity",
        phrase_ids == EXPECTED_SPEECH_IDS
        and len(set(phrase_hashes)) == 1
        and all(len(records) >= 48 for records in phrase_windows.values())
        and all(
            ratio >= MINIMUM_PHRASE_STILLNESS
            for ratio in phrase_stillness.values()
        ),
        {
            "speech_ids": list(phrase_ids),
            "phrase_sha256": phrase_hashes,
            "phrase_frame_counts": {
                key: len(value) for key, value in phrase_windows.items()
            },
            "phrase_body_stillness": phrase_stillness,
        },
    )

    effect_events = _effect_events(owned_traces)
    effect_spacing = [
        right - left for left, right in zip(effect_events, effect_events[1:])
    ]
    gesture_commands = tuple(
        item.get("scenario") for item in scheduled if item.get("kind") == "action"
    )
    _check(
        report,
        "three_deliberate_gestures",
        gesture_commands == EXPECTED_GESTURES
        and len(effect_events) == 3
        and all(value >= MINIMUM_GESTURE_SPACING_FRAMES for value in effect_spacing),
        {
            "gesture_commands": list(gesture_commands),
            "effect_event_frames": effect_events,
            "effect_spacing_frames": effect_spacing,
        },
    )

    aggregate_stillness = _stillness_ratio(owned_traces)
    signatures = [
        (
            _channels(trace).get("body_pixel_sha256"),
            _channels(trace).get("gaze_aim"),
            _channels(trace).get("gaze_vertical_aim"),
            _channels(trace).get("action"),
            trace.get("rendered_pose_id"),
        )
        for trace in owned_traces
    ]
    loop_period = _nonconstant_loop_period(signatures)
    _check(
        report,
        "purposeful_stillness_without_short_exact_loop",
        aggregate_stillness >= MINIMUM_BODY_STILLNESS and loop_period is None,
        {
            "body_stillness_ratio": aggregate_stillness,
            "detected_nonconstant_loop_period_frames": loop_period,
            "searched_period_frames": [2, 191],
        },
    )

    blink_ranges = _closed_ranges(owned_traces)
    blink_lengths = [end - start for start, end in blink_ranges]
    blink_intervals = [
        right[0] - left[0] for left, right in zip(blink_ranges, blink_ranges[1:])
    ]
    blink_stability = []
    for start, end in blink_ranges:
        closed = owned_traces[start:end]
        body_hashes = {
            _channels(trace).get("body_pixel_sha256") for trace in closed
        }
        roots = {_point(trace) for trace in closed}
        blink_stability.append(
            {
                "first_frame_index": closed[0].get("frame_index") if closed else None,
                "last_frame_index": closed[-1].get("frame_index") if closed else None,
                "body_hash_count": len(body_hashes),
                "root_count": len(roots),
                "passed": bool(closed)
                and len(body_hashes) == 1
                and len(roots) == 1
                and None not in roots,
            }
        )
    _check(
        report,
        "varied_natural_blinks",
        len(blink_ranges) >= MINIMUM_BLINK_COUNT
        and all(3 <= length <= 4 for length in blink_lengths)
        and all(
            MINIMUM_BLINK_INTERVAL_FRAMES
            <= interval
            <= MAXIMUM_BLINK_INTERVAL_FRAMES
            for interval in blink_intervals
        )
        and len(set(blink_intervals)) >= 3,
        {
            "blink_count": len(blink_ranges),
            "closure_lengths_frames": blink_lengths,
            "open_intervals_frames": blink_intervals,
            "allowed_interval_frames": [
                MINIMUM_BLINK_INTERVAL_FRAMES,
                MAXIMUM_BLINK_INTERVAL_FRAMES,
            ],
            "distinct_interval_count": len(set(blink_intervals)),
        },
    )
    _check(
        report,
        "blink_body_and_root_stability",
        bool(blink_stability)
        and all(item["passed"] for item in blink_stability),
        {"closures": blink_stability},
    )

    roots = [_point(trace) for trace in owned_traces]
    root_steps = [
        max(abs(right[0] - left[0]), abs(right[1] - left[1]))
        for left, right in zip(roots, roots[1:])
        if left is not None and right is not None
    ]
    final = owned_traces[-48:]
    final_body_hashes = {
        _channels(trace).get("body_pixel_sha256") for trace in final
    }
    final_roots = {_point(trace) for trace in final}
    final_poses = {trace.get("rendered_pose_id") for trace in final}
    final_head_offsets = {
        (
            _channels(trace).get("head_offset_x", 0),
            _channels(trace).get("head_offset_y", 0),
        )
        for trace in final
    }
    _check(
        report,
        "stable_root_and_final_hold",
        bool(root_steps)
        and max(root_steps) <= 1.0
        and len(final) == 48
        and len(final_body_hashes) <= 2
        and len(final_roots) == 1
        and len(final_poses) == 1
        and final_head_offsets.issubset({(0, 0), (0, -1)})
        and all(
            _channels(trace).get("action") == "idle"
            and _channels(trace).get("speech_id") is None
            for trace in final
        ),
        {
            "maximum_presented_root_axis_step": max(root_steps, default=math.inf),
            "final_body_hash_count": len(final_body_hashes),
            "final_root_count": len(final_roots),
            "final_pose_ids": sorted(str(value) for value in final_poses),
            "final_head_offsets": sorted([list(value) for value in final_head_offsets]),
            "final_frame_count": len(final),
        },
    )

    cols = int(manifest.get("init", {}).get("cols", 0) or 0)
    rows = int(manifest.get("init", {}).get("rows", 0) or 0)
    clipped = [
        trace.get("frame_index")
        for trace in owned_traces
        if not _inside_stage(trace, cols, rows)
    ]
    contact = manifest.get("contact_verification", {})
    _check(
        report,
        "canonical_stage_and_contact_integrity",
        cols > 0
        and rows > 0
        and not clipped
        and isinstance(contact, Mapping)
        and contact.get("passed") is True,
        {
            "stage": [cols, rows],
            "clipped_frames": clipped,
            "contact_passed": contact.get("passed") if isinstance(contact, Mapping) else None,
        },
    )

    report["metrics"] = {
        "owned_frame_count": len(owned_frames),
        "body_stillness_ratio": aggregate_stillness,
        "gesture_effect_count": len(effect_events),
        "blink_count": len(blink_ranges),
        "distinct_blink_interval_count": len(set(blink_intervals)),
        "detected_nonconstant_loop_period_frames": loop_period,
        "maximum_presented_root_axis_step": max(root_steps, default=math.inf),
        "clipped_frame_count": len(clipped),
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
    traces: List[Mapping[str, Any]] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if line:
            traces.append(
                AnimationTruthTraceV1.from_mapping(json.loads(line)).to_mapping()
            )
    return analyze_v8(manifest, traces)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Character Director V8 evidence.")
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
