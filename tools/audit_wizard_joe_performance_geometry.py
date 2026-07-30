#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import HDPoseLibrary


DEFAULT_MANIFEST = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "wizard-joe"
    / "audio-performances-v1"
    / "manifest.json"
)
DEFAULT_LIBRARY_INDEX = (
    ROOT / "assets" / "reference" / "hd_canonical" / "compiled" / "library-index.json"
)
DEFAULT_OUTPUT = DEFAULT_MANIFEST.parent / "performance-geometry-audit.json"
MAX_CENTER_SHIFT_PX = 80.0
MAX_DIMENSION_RATIO = 1.5
INTENTIONAL_DYNAMIC_TRANSITIONS = {
    ("175_flight_recoverystroke_up", "184_flight_accelerate"),
    ("184_flight_accelerate", "185_flight_brake"),
    ("199_magic_gather_hand", "200_magic_trace_symbol"),
}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def projected_pose_sequence(performance: dict[str, Any]) -> list[str]:
    """Return body poses in the order the observer can actually project them."""
    approach = performance["approach"]
    approach_end_ms = int(approach["end_ms"])
    duration_ms = int(performance["_duration_ms"])
    sequence: list[str] = []
    if approach_end_ms > 0:
        sequence.extend(str(pose_id) for pose_id in approach["pose_ids"])
        sequence.extend(
            str(pose_id) for pose_id in approach.get("arrival_pose_ids", [])
        )
        if approach_end_ms >= duration_ms:
            return _without_adjacent_duplicates(sequence)

    beats = performance.get("motion_beats", [])
    if not beats:
        return _without_adjacent_duplicates(sequence)
    active_index = 0
    for index, beat in enumerate(beats):
        if int(beat["time_ms"]) <= approach_end_ms:
            active_index = index
        else:
            break
    if approach_end_ms <= 0:
        active_index = 0
    sequence.extend(str(beat["pose_id"]) for beat in beats[active_index:])
    return _without_adjacent_duplicates(sequence)


def _without_adjacent_duplicates(pose_ids: list[str]) -> list[str]:
    result: list[str] = []
    for pose_id in pose_ids:
        if not result or result[-1] != pose_id:
            result.append(pose_id)
    return result


def _pose_geometry(library: HDPoseLibrary, pose_id: str) -> dict[str, Any]:
    bbox = library.load_pose(pose_id).getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"{pose_id} has no visible pixels")
    left, top, right, bottom = bbox
    return {
        "bbox": [left, top, right, bottom],
        "width": right - left,
        "height": bottom - top,
        "center_x": (left + right) / 2,
        "center_y": (top + bottom) / 2,
        "baseline_y": bottom,
    }


def transition_geometry(
    source_pose_id: str,
    target_pose_id: str,
    source: dict[str, Any],
    target: dict[str, Any],
) -> dict[str, Any]:
    center_shift = math.hypot(
        float(target["center_x"]) - float(source["center_x"]),
        float(target["center_y"]) - float(source["center_y"]),
    )
    dimension_ratio = max(
        float(source["width"]) / max(1, float(target["width"])),
        float(target["width"]) / max(1, float(source["width"])),
        float(source["height"]) / max(1, float(target["height"])),
        float(target["height"]) / max(1, float(source["height"])),
    )
    baseline_shift = abs(int(target["baseline_y"]) - int(source["baseline_y"]))
    issues: list[str] = []
    intentional_dynamic = (
        source_pose_id,
        target_pose_id,
    ) in INTENTIONAL_DYNAMIC_TRANSITIONS
    if center_shift > MAX_CENTER_SHIFT_PX and not intentional_dynamic:
        issues.append("center_shift_outlier")
    if dimension_ratio > MAX_DIMENSION_RATIO and not intentional_dynamic:
        issues.append("dimension_change_outlier")
    return {
        "source_pose_id": source_pose_id,
        "target_pose_id": target_pose_id,
        "center_shift_px": round(center_shift, 2),
        "dimension_ratio": round(dimension_ratio, 4),
        "baseline_shift_px": baseline_shift,
        "intentional_dynamic_transition": intentional_dynamic,
        "issues": issues,
    }


def audit_geometry(
    manifest_path: Path,
    library_index_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    manifest = _read_json(manifest_path.resolve())
    library = HDPoseLibrary(library_index_path.resolve())
    geometry_cache: dict[str, dict[str, Any]] = {}

    def geometry(pose_id: str) -> dict[str, Any]:
        if pose_id not in geometry_cache:
            geometry_cache[pose_id] = _pose_geometry(library, pose_id)
        return geometry_cache[pose_id]

    records = []
    for clip in manifest["clips"]:
        performance = {
            **clip["performance"],
            "_duration_ms": int(clip["audio"]["duration_ms"]),
        }
        pose_ids = projected_pose_sequence(performance)
        transitions = [
            transition_geometry(source_id, target_id, geometry(source_id), geometry(target_id))
            for source_id, target_id in zip(pose_ids, pose_ids[1:])
        ]
        issues = sorted(
            {
                issue
                for transition in transitions
                for issue in transition["issues"]
            }
        )
        records.append(
            {
                "clip_id": clip["clip_id"],
                "projected_pose_sequence": pose_ids,
                "transition_count": len(transitions),
                "maximum_center_shift_px": max(
                    (item["center_shift_px"] for item in transitions), default=0
                ),
                "maximum_dimension_ratio": max(
                    (item["dimension_ratio"] for item in transitions), default=1
                ),
                "maximum_baseline_shift_px": max(
                    (item["baseline_shift_px"] for item in transitions), default=0
                ),
                "issues": issues,
                "status": "pass" if not issues else "review",
                "transitions": transitions,
            }
        )
    review_records = [record for record in records if record["issues"]]
    report = {
        "schema_version": 1,
        "program_id": manifest["program_id"],
        "scope": "projected_full_frame_body_pose_geometry",
        "thresholds": {
            "maximum_center_shift_px": MAX_CENTER_SHIFT_PX,
            "maximum_dimension_ratio": MAX_DIMENSION_RATIO,
            "baseline_shift": (
                "diagnostic_only; staffs, wings, tails, and flight poses do not "
                "share a meaningful lowest-visible-pixel contact line"
            ),
        },
        "intentional_dynamic_transitions": [
            {
                "source_pose_id": source_pose_id,
                "target_pose_id": target_pose_id,
                "reason": (
                    "visually reviewed authored flight acceleration or braking "
                    "silhouette change"
                ),
            }
            for source_pose_id, target_pose_id in sorted(
                INTENTIONAL_DYNAMIC_TRANSITIONS
            )
        ],
        "clip_count": len(records),
        "pass_count": len(records) - len(review_records),
        "review_count": len(review_records),
        "review_clip_ids": [record["clip_id"] for record in review_records],
        "clips": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit full-frame geometry across Wizard Joe performances."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--library-index", type=Path, default=DEFAULT_LIBRARY_INDEX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = audit_geometry(args.manifest, args.library_index, args.output)
    print(
        json.dumps(
            {
                "output": args.output.resolve().relative_to(ROOT).as_posix(),
                "clip_count": report["clip_count"],
                "pass_count": report["pass_count"],
                "review_count": report["review_count"],
                "review_clip_ids": report["review_clip_ids"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
