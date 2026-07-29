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
    / "mouth-pairs-v1"
    / "mouth-pair-manifest.json"
)
DEFAULT_OUTPUT = DEFAULT_MANIFEST.parent / "performance-audit.json"


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
            second["time_ms"] - first["time_ms"] < 950
            for first, second in zip(beats, beats[1:])
        ):
            issues.append("motion_beats_too_close")
        if any(
            first["pose_id"] == second["pose_id"]
            for first, second in zip(beats, beats[1:])
        ):
            issues.append("adjacent_pose_repetition")
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
            "minimum_motion_beat_spacing_ms": 950,
            "adjacent_pose_repetition_forbidden": True,
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
