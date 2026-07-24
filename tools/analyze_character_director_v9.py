#!/usr/bin/env python3
"""Evaluate the machine-verifiable Character Director V9 accessibility proof."""

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

from tools.prepare_character_director_v9_fixture import (
    CAPTURE_FRAMES,
    PROFILE_ORDER,
    PROGRAM_ID,
)
from tools.run_character_director_visual_review import validate_manifest
from wizard_avatar.animation_trace import AnimationTruthTraceV1


REPORT_SCHEMA = "character_director_v9_machine_acceptance_v1"
SCENARIOS = tuple("v9-{}-profile".format(profile) for profile in PROFILE_ORDER)
EXPECTED_TOTAL_FRAMES = CAPTURE_FRAMES * len(PROFILE_ORDER)
ALLOWED_ACCESSIBLE_CHANNELS = frozenset(
    {"speech", "mouth", "face", "eyes", "gaze", "blink"}
)
BLOCKED_BODY_CHANNELS = frozenset(
    {"body", "body_base", "gesture", "effects", "locomotion", "stage", "position"}
)
BODY_WINDOWS = ((12, 53), (62, 92), (100, 125), (134, 192))


def _check(report: Dict[str, Any], name: str, passed: bool, detail: object) -> None:
    report["checks"].append(
        {"name": name, "passed": bool(passed), "detail": detail}
    )


def _channels(trace: Mapping[str, Any]) -> Mapping[str, Any]:
    value = trace.get("presentation_channels")
    return value if isinstance(value, Mapping) else {}


def _root(trace: Mapping[str, Any]) -> Optional[Tuple[float, float]]:
    value = trace.get("presented_root_stage")
    if not isinstance(value, Mapping):
        return None
    x, y = value.get("x"), value.get("y")
    if any(
        isinstance(item, bool) or not isinstance(item, (int, float))
        for item in (x, y)
    ):
        return None
    point = float(x), float(y)
    return point if all(math.isfinite(item) for item in point) else None


def _inside_stage(trace: Mapping[str, Any], cols: int, rows: int) -> bool:
    span = trace.get("silhouette_raster_span")
    return isinstance(span, Mapping) and (
        0 <= int(span.get("min_x", -1)) <= int(span.get("max_x", cols)) < cols
        and 0 <= int(span.get("min_y", -1)) <= int(span.get("max_y", rows)) < rows
    )


def _profile_traces(
    manifest: Mapping[str, Any],
    trace_records: Sequence[Mapping[str, Any]],
) -> Dict[str, List[Mapping[str, Any]]]:
    trace_by_index = {
        item.get("frame_index"): item
        for item in trace_records
        if type(item.get("frame_index")) is int
    }
    result: Dict[str, List[Mapping[str, Any]]] = {}
    for scenario, profile in zip(SCENARIOS, PROFILE_ORDER):
        frames = [
            item
            for item in manifest.get("frames", ())
            if isinstance(item, Mapping)
            and item.get("capture_owned") is True
            and item.get("scenario") == scenario
        ]
        result[profile] = [
            trace_by_index[item["frame_index"]]
            for item in frames
            if item.get("frame_index") in trace_by_index
        ]
    return result


def _window(
    records: Sequence[Mapping[str, Any]],
    start: int,
    end: int,
) -> Sequence[Mapping[str, Any]]:
    return records[max(0, start) : min(len(records), end)]


def _body_window_records(
    records: Sequence[Mapping[str, Any]],
) -> List[Mapping[str, Any]]:
    return [
        trace
        for start, end in BODY_WINDOWS
        for trace in _window(records, start, end)
    ]


def _profile_metrics(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    channels = [_channels(item) for item in records]
    roots = [_root(item) for item in records]
    valid_roots = [item for item in roots if item is not None]
    body_hashes = {
        item.get("body_pixel_sha256")
        for item in channels
        if item.get("body_pixel_sha256") is not None
    }
    mouth_hashes = {
        item.get("mouth_pixel_sha256")
        for item in channels[:134]
        if item.get("mouth_pixel_sha256") is not None
    }
    return {
        "frame_count": len(records),
        "body_hash_count": len(body_hashes),
        "mouth_hash_count": len(mouth_hashes),
        "mouth_active_frame_count": sum(
            int(item.get("mouth_painted_cells", 0) or 0) > 0
            for item in channels[:134]
        ),
        "root_count": len(set(valid_roots)),
        "root_x_span": (
            max(point[0] for point in valid_roots)
            - min(point[0] for point in valid_roots)
            if valid_roots
            else 0.0
        ),
        "actions": sorted({str(item.get("action")) for item in channels}),
        "locomotion": sorted({str(item.get("locomotion")) for item in channels}),
        "gaze_aims": sorted(
            {
                item.get("gaze_aim")
                for item in channels
                if type(item.get("gaze_aim")) is int
            }
        ),
        "effect_frame_count": sum(
            float(item.get("effect_intensity", 0.0) or 0.0) > 0.0
            for item in records
        ),
        "owned_channels": sorted(
            {
                channel
                for item in records
                for channel in item.get("performance_owned_channels", ())
            }
        ),
        "suppression_codes": sorted(
            {
                code
                for item in records
                for code in item.get("performance_suppression_codes", ())
            }
        ),
    }


def analyze_v9(
    manifest: Mapping[str, Any],
    trace_records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "schema_version": 1,
        "acceptance_scenario": "V9",
        "passed": False,
        "checks": [],
        "metrics": {},
        "review_boundary": (
            "Machine checks prove transport, score identity, channel suppression, "
            "framing, and pixel behavior. Human normal-speed and quarter-speed "
            "review must still judge whether retained face and mouth acting reads well."
        ),
    }

    program = manifest.get("scenario_program")
    _check(
        report,
        "scenario_program_identity",
        isinstance(program, Mapping)
        and program.get("schema") == "character_director_scenario_program_v2"
        and program.get("schema_version") == 2
        and program.get("program_id") == PROGRAM_ID
        and program.get("acceptance_scenario") == "V9"
        and program.get("scenario_count") == 3
        and program.get("maximum_capture_frame_count") == EXPECTED_TOTAL_FRAMES,
        program,
    )

    profile_traces = _profile_traces(manifest, trace_records)
    frame_counts = {
        profile: len(records) for profile, records in profile_traces.items()
    }
    trace_profiles = {
        profile: sorted(
            {item.get("performance_motion_profile") for item in records}
        )
        for profile, records in profile_traces.items()
    }
    contiguous = {}
    for profile, scenario in zip(PROFILE_ORDER, SCENARIOS):
        indexes = [
            item.get("frame_index")
            for item in manifest.get("frames", ())
            if isinstance(item, Mapping)
            and item.get("capture_owned") is True
            and item.get("scenario") == scenario
        ]
        contiguous[profile] = bool(indexes) and all(
            type(left) is int
            and type(right) is int
            and right == left + 1
            for left, right in zip(indexes, indexes[1:])
        )
    _check(
        report,
        "three_exact_profile_ranges",
        all(frame_counts.get(profile) == CAPTURE_FRAMES for profile in PROFILE_ORDER)
        and all(contiguous.values())
        and all(
            trace_profiles.get(profile) == [profile] for profile in PROFILE_ORDER
        ),
        {
            "frame_counts": frame_counts,
            "trace_profiles": trace_profiles,
            "transport_contiguous": contiguous,
        },
    )

    commands = [
        item for item in manifest.get("commands", ()) if isinstance(item, Mapping)
    ]
    score_ids = {
        item.get("payload", {}).get("performance", {}).get("score_id")
        for item in commands
    }
    score_hashes = {
        item.get("payload", {}).get("performance", {}).get("score_sha256")
        for item in commands
    }
    package_hashes = {
        item.get("payload", {})
        .get("performance", {})
        .get("character_package_sha256")
        for item in commands
    }
    sequences = [
        item.get("payload", {}).get("sequence") for item in commands
    ]
    accepted = all(
        item.get("kind") == "media_session"
        and item.get("transport") == "media_session"
        and isinstance(item.get("ack"), Mapping)
        and item["ack"].get("disposition") == "accepted"
        and item["ack"].get("accepted_sequence")
        == item.get("payload", {}).get("sequence")
        and item["ack"].get("accepted_media_epoch")
        == item.get("payload", {}).get("media_epoch")
        for item in commands
    )
    _check(
        report,
        "one_authenticated_score_bound_media_replay",
        len(commands) == 27
        and accepted
        and sequences == list(range(1, 28))
        and len(score_ids) == 1
        and None not in score_ids
        and len(score_hashes) == 1
        and None not in score_hashes
        and len(package_hashes) == 1
        and None not in package_hashes,
        {
            "command_count": len(commands),
            "all_media_acks_accepted": accepted,
            "sequences": sequences,
            "score_ids": sorted(str(item) for item in score_ids),
            "score_hashes": sorted(str(item) for item in score_hashes),
            "package_hashes": sorted(str(item) for item in package_hashes),
        },
    )

    metrics = {
        profile: _profile_metrics(records)
        for profile, records in profile_traces.items()
    }
    full = profile_traces.get("full", [])
    full_channels = [_channels(item) for item in full]
    full_actions = {item.get("action") for item in full_channels}
    full_roots = [_root(item) for item in _window(full, 134, 192)]
    valid_full_roots = [item for item in full_roots if item is not None]
    full_root_span = (
        max(item[0] for item in valid_full_roots)
        - min(item[0] for item in valid_full_roots)
        if valid_full_roots
        else 0.0
    )
    _check(
        report,
        "full_profile_preserves_authored_body_performance",
        {"magic_cast", "explaining", "pointing", "walking"}.issubset(full_actions)
        and any(
            float(item.get("effect_intensity", 0.0) or 0.0) > 0.0
            for item in _window(full, 12, 53)
        )
        and full_root_span >= 2.0
        and metrics["full"]["body_hash_count"] >= 8,
        {
            "actions": sorted(str(item) for item in full_actions),
            "cast_effect_frame_count": sum(
                float(item.get("effect_intensity", 0.0) or 0.0) > 0.0
                for item in _window(full, 12, 53)
            ),
            "walk_root_x_span": full_root_span,
            "body_hash_count": metrics["full"]["body_hash_count"],
        },
    )

    accessible_details: Dict[str, Any] = {}
    accessible_pass = True
    for profile in ("reduced", "still"):
        records = profile_traces.get(profile, [])
        channels = [_channels(item) for item in records]
        body_records = _body_window_records(records)
        body_channels = [_channels(item) for item in body_records]
        owned = {
            channel
            for item in records
            for channel in item.get("performance_owned_channels", ())
        }
        body_hashes = {
            item.get("body_pixel_sha256")
            for item in channels
            if item.get("body_pixel_sha256") is not None
        }
        roots = {_root(item) for item in records}
        suppressions = {
            code
            for item in body_records
            for code in item.get("performance_suppression_codes", ())
        }
        profile_pass = (
            bool(records)
            and len(body_hashes) == 1
            and len(roots) == 1
            and None not in roots
            and all(item.get("action") == "idle" for item in body_channels)
            and all(item.get("locomotion") == "idle" for item in body_channels)
            and all(
                float(item.get("effect_intensity", 0.0) or 0.0) == 0.0
                for item in body_records
            )
            and not (owned & BLOCKED_BODY_CHANNELS)
            and owned.issubset(ALLOWED_ACCESSIBLE_CHANNELS)
            and {
                "accessibility_projection",
                "motion_profile_projection",
            }.issubset(suppressions)
        )
        accessible_pass = accessible_pass and profile_pass
        accessible_details[profile] = {
            "passed": profile_pass,
            "body_hash_count": len(body_hashes),
            "root_count": len(roots),
            "actions": sorted({str(item.get("action")) for item in body_channels}),
            "locomotion": sorted(
                {str(item.get("locomotion")) for item in body_channels}
            ),
            "effect_frame_count": sum(
                float(item.get("effect_intensity", 0.0) or 0.0) > 0.0
                for item in body_records
            ),
            "owned_channels": sorted(owned),
            "suppression_codes": sorted(suppressions),
        }
    _check(
        report,
        "reduced_and_still_suppress_all_body_motion",
        accessible_pass,
        accessible_details,
    )

    retained_details: Dict[str, Any] = {}
    retained_pass = True
    for profile in PROFILE_ORDER:
        records = profile_traces.get(profile, [])
        speech_records = _window(records, 5, 134)
        channels = [_channels(item) for item in speech_records]
        mouth_hashes = {
            item.get("mouth_pixel_sha256")
            for item in channels
            if item.get("mouth_pixel_sha256") is not None
        }
        gaze_aims = {
            item.get("gaze_aim")
            for item in channels
            if type(item.get("gaze_aim")) is int
        }
        expression_frames = sum(
            item.get("expression") == "explaining" for item in channels
        )
        profile_pass = (
            len(mouth_hashes) >= 3
            and sum(
                int(item.get("mouth_painted_cells", 0) or 0) > 0
                for item in channels
            )
            >= 72
            and {0, 1}.issubset(gaze_aims)
            and expression_frames >= 72
        )
        retained_pass = retained_pass and profile_pass
        retained_details[profile] = {
            "passed": profile_pass,
            "mouth_hash_count": len(mouth_hashes),
            "mouth_active_frame_count": sum(
                int(item.get("mouth_painted_cells", 0) or 0) > 0
                for item in channels
            ),
            "gaze_aims": sorted(gaze_aims),
            "explaining_expression_frame_count": expression_frames,
        }
    _check(
        report,
        "speech_face_mouth_and_gaze_intent_survive_projection",
        retained_pass,
        retained_details,
    )

    resolution_hashes = {
        profile: {
            item.get("performance_resolution_hash")
            for item in records
            if item.get("performance_resolution_hash") is not None
        }
        for profile, records in profile_traces.items()
    }
    _check(
        report,
        "profile_specific_resolution_is_traceable",
        all(resolution_hashes.get(profile) for profile in PROFILE_ORDER)
        and all(
            left.isdisjoint(right)
            for index, left in enumerate(resolution_hashes.values())
            for right in list(resolution_hashes.values())[index + 1 :]
        ),
        {
            profile: {
                "count": len(values),
                "sample": sorted(str(item) for item in values)[:3],
            }
            for profile, values in resolution_hashes.items()
        },
    )

    cols = int(manifest.get("init", {}).get("cols", 0) or 0)
    rows = int(manifest.get("init", {}).get("rows", 0) or 0)
    all_records = [
        item for profile in PROFILE_ORDER for item in profile_traces.get(profile, [])
    ]
    clipped = [
        item.get("frame_index")
        for item in all_records
        if not _inside_stage(item, cols, rows)
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
            "contact_passed": (
                contact.get("passed") if isinstance(contact, Mapping) else None
            ),
        },
    )

    report["metrics"] = metrics
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
    return analyze_v9(manifest, traces)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze Character Director V9 accessibility evidence."
    )
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
