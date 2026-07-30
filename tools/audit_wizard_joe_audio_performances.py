#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
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
DEFAULT_MOUTH_PAIRS = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "wizard-joe"
    / "mouth-pairs-full-frame-v2"
    / "mouth-pair-manifest.json"
)
DEFAULT_OUTPUT = DEFAULT_MANIFEST.parent / "performance-audit.json"
MIN_MOTION_BEAT_SPACING_MS = 1400
MAX_MOTION_BEAT_GAP_MS = 6000
MOTION_REPETITION_WINDOW = 4
MIN_BODY_TRANSITION_MS = 120
MAX_BODY_TRANSITION_MS = 240


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pose_ids(index: dict[str, Any]) -> set[str]:
    return {
        pose_id
        for shard in index["shards"]
        for pose_id in shard["pose_ids"]
    }


def _paired_pose_ids(mouth_manifest: dict[str, Any]) -> set[str]:
    return {
        pair["base_pose_id"]
        for pair in mouth_manifest["pairs"]
        if set(pair.get("states", {})) == {"closed", "open"}
    }


def _clip_pose_ids(clip: dict[str, Any]) -> set[str]:
    performance = clip["performance"]
    result = {
        performance["settle_pose_id"],
        *performance["approach"]["pose_ids"],
    }
    for cue in performance["body_cues"]:
        result.update(cue["pose_ids"])
    for beat in performance.get("motion_beats", []):
        result.add(beat["pose_id"])
    return result


def _motion_quality(performance: dict[str, Any], duration_ms: int) -> dict[str, Any]:
    beats = performance.get("motion_beats", [])
    pose_ids = [str(beat["pose_id"]) for beat in beats]
    gaps = [
        int(second["time_ms"]) - int(first["time_ms"])
        for first, second in zip(beats, beats[1:])
    ]
    short_window_repetitions = [
        {
            "beat_index": index,
            "pose_id": pose_id,
            "previous_window": pose_ids[
                max(0, index - MOTION_REPETITION_WINDOW) : index
            ],
        }
        for index, pose_id in enumerate(pose_ids)
        if pose_id
        in pose_ids[max(0, index - MOTION_REPETITION_WINDOW) : index]
    ]
    transition_pairs = [
        (first, second) for first, second in zip(pose_ids, pose_ids[1:])
    ]
    transition_counts: dict[tuple[str, str], int] = {}
    for transition in transition_pairs:
        transition_counts[transition] = transition_counts.get(transition, 0) + 1
    repeated_transitions = [
        {
            "source_pose_id": source,
            "target_pose_id": target,
            "count": count,
        }
        for (source, target), count in sorted(transition_counts.items())
        if count > 1
    ]
    approach = performance["approach"]
    approach_end_ms = int(approach.get("end_ms", 0))
    projected_beats: list[dict[str, Any]] = []
    if approach_end_ms < duration_ms and beats:
        active_index = 0
        for index, beat in enumerate(beats):
            if int(beat["time_ms"]) <= approach_end_ms:
                active_index = index
            else:
                break
        projected_beats.append(
            {
                "time_ms": approach_end_ms,
                "pose_id": beats[active_index]["pose_id"],
            }
        )
        projected_beats.extend(
            beat
            for beat in beats[active_index + 1 :]
            if int(beat["time_ms"]) > approach_end_ms
        )
    projected_hold_gaps = [
        int(second["time_ms"]) - int(first["time_ms"])
        for first, second in zip(projected_beats, projected_beats[1:])
    ]
    if projected_beats:
        projected_hold_gaps.append(
            duration_ms - int(projected_beats[-1]["time_ms"])
        )
    transition_ms = int(performance.get("body_transition_ms", 0))
    cue_crossfades = {
        int(cue.get("crossfade_ms", 0))
        for cue in performance.get("body_cues", [])
    }
    issues: list[str] = []
    if any(gap < MIN_MOTION_BEAT_SPACING_MS for gap in gaps):
        issues.append("motion_beats_too_close")
    if gaps and max(gaps) > MAX_MOTION_BEAT_GAP_MS:
        issues.append("motion_beat_gap_too_long")
    if (
        projected_hold_gaps
        and max(projected_hold_gaps) > MAX_MOTION_BEAT_GAP_MS
    ):
        issues.append("projected_pose_hold_too_long")
    if short_window_repetitions:
        issues.append("short_window_pose_repetition")
    if repeated_transitions:
        issues.append("repeated_pose_transition")
    if not MIN_BODY_TRANSITION_MS <= transition_ms <= MAX_BODY_TRANSITION_MS:
        issues.append("body_transition_out_of_range")
    if cue_crossfades != {transition_ms}:
        issues.append("cue_transition_mismatch")
    if (
        approach.get("mode") == "walk_toward_camera"
        and (
            len(set(approach.get("pose_ids", []))) != 1
            or "248_camera_retreat" in approach.get("pose_ids", [])
            or approach.get("arrival_pose_ids") != ["247_camera_intimate_hold"]
        )
    ):
        issues.append("incoherent_camera_approach")
    gesture_rate = len(beats) / max(0.001, duration_ms / 1000)
    if gesture_rate > 0.7:
        issues.append("gesture_density_too_high")
    return {
        "issues": issues,
        "minimum_beat_gap_ms": min(gaps) if gaps else None,
        "maximum_beat_gap_ms": max(gaps) if gaps else None,
        "maximum_projected_pose_hold_ms": (
            max(projected_hold_gaps) if projected_hold_gaps else None
        ),
        "gesture_rate_hz": round(gesture_rate, 4),
        "short_window_repetitions": short_window_repetitions,
        "repeated_transitions": repeated_transitions,
        "body_transition_ms": transition_ms,
        "cue_crossfade_ms": sorted(cue_crossfades),
    }


def audit_performances(
    manifest_path: Path,
    library_index_path: Path,
    mouth_pair_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = _read_json(manifest_path)
    valid_poses = _pose_ids(_read_json(library_index_path.resolve()))
    paired_poses = _paired_pose_ids(_read_json(mouth_pair_path.resolve()))
    records = []
    signatures: set[tuple[str, ...]] = set()
    for clip in manifest["clips"]:
        performance = clip["performance"]
        duration_ms = int(clip["audio"]["duration_ms"])
        cues = performance["body_cues"]
        beats = performance.get("motion_beats", [])
        used_poses = _clip_pose_ids(clip)
        issues: list[str] = []
        motion_quality = _motion_quality(performance, duration_ms)
        if not cues or cues[0]["start_ms"] != 0 or cues[-1]["end_ms"] != duration_ms:
            issues.append("cue_coverage")
        if any(
            first["end_ms"] != second["start_ms"]
            for first, second in zip(cues, cues[1:])
        ):
            issues.append("cue_gap_or_overlap")
        if any(cue["end_ms"] <= cue["start_ms"] for cue in cues):
            issues.append("nonpositive_cue")
        if not beats or beats[0]["time_ms"] != 0:
            issues.append("missing_initial_motion_beat")
        if any(
            first["pose_id"] == second["pose_id"]
            for first, second in zip(beats, beats[1:])
        ):
            issues.append("adjacent_pose_repetition")
        issues.extend(motion_quality["issues"])
        unknown = sorted(used_poses - valid_poses)
        if unknown:
            issues.append("unknown_pose")
        unpaired = sorted(used_poses - paired_poses)
        if unpaired:
            issues.append("missing_mouth_pair")
        audio_path = (manifest_path.parent / clip["audio"]["path"]).resolve()
        if not audio_path.is_file():
            issues.append("missing_audio")
        elif _sha256(audio_path) != str(clip["audio"]["sha256"]).removeprefix(
            "sha256:"
        ):
            issues.append("audio_checksum")
        signature = tuple(beat["pose_id"] for beat in beats)
        signatures.add(signature)
        records.append(
            {
                "clip_id": clip["clip_id"],
                "display_name": clip["display_name"],
                "duration_ms": duration_ms,
                "cue_count": len(cues),
                "motion_beat_count": len(beats),
                "unique_pose_count": len(used_poses),
                "mouth_pair_coverage": len(used_poses - set(unpaired))
                == len(used_poses),
                "unknown_pose_ids": unknown,
                "unpaired_pose_ids": unpaired,
                "motion_quality": motion_quality,
                "issues": issues,
                "status": "pass" if not issues else "fail",
            }
        )
    failed = [record for record in records if record["issues"]]
    report = {
        "schema_version": 1,
        "program_id": manifest["program_id"],
        "scope": "all_prerecorded_wizard_joe_clips",
        "clip_count": len(records),
        "passed_clip_count": len(records) - len(failed),
        "failed_clip_count": len(failed),
        "unique_motion_signatures": len(signatures),
        "mouth_pair_coverage": {
            "paired_approved_pose_count": len(paired_poses),
            "required_approved_pose_count": 250,
        },
        "automated_gate": {
            "audio_checksum": True,
            "continuous_cues": True,
            "minimum_motion_beat_spacing_ms": MIN_MOTION_BEAT_SPACING_MS,
            "maximum_motion_beat_gap_ms": MAX_MOTION_BEAT_GAP_MS,
            "adjacent_pose_repetition_forbidden": True,
            "rolling_pose_repetition_window": MOTION_REPETITION_WINDOW,
            "repeated_pose_transitions_forbidden": True,
            "body_transition_range_ms": [
                MIN_BODY_TRANSITION_MS,
                MAX_BODY_TRANSITION_MS,
            ],
            "stable_camera_approach_required": True,
            "all_pose_references_valid": True,
            "all_used_poses_require_open_closed_pair": True,
        },
        "human_gate": (
            "Visual choreography approval remains explicit in review-state.json; "
            "this report does not grant runtime admission."
        ),
        "clips": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit every prerecorded Wizard Joe audio performance."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--library-index", type=Path, default=DEFAULT_LIBRARY_INDEX)
    parser.add_argument("--mouth-pairs", type=Path, default=DEFAULT_MOUTH_PAIRS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = audit_performances(
        args.manifest,
        args.library_index,
        args.mouth_pairs,
        args.output,
    )
    print(
        json.dumps(
            {
                "output": args.output.resolve().relative_to(ROOT).as_posix(),
                "clip_count": report["clip_count"],
                "passed_clip_count": report["passed_clip_count"],
                "failed_clip_count": report["failed_clip_count"],
                "unique_motion_signatures": report["unique_motion_signatures"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
