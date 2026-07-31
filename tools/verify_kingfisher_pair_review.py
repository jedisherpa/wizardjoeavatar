#!/usr/bin/env python3
"""Verify Kingfisher's review-only closed/open pair library and evidence."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import HDPoseLibrary, sha256_path  # noqa: E402

PAIR_COUNT = 66
PAIR_SEQUENCE = "kingfisher-paired-beaks-review"
PASSING_REVIEW_STATES = {"pass", "not_observable"}


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _evidence_path(raw_path: object, ledger_root: Path) -> Path:
    path = Path(str(raw_path))
    if path.is_absolute():
        return path.resolve()
    repository_path = (ROOT / path).resolve()
    if repository_path.exists():
        return repository_path
    return (ledger_root / path).resolve()


def _report_path(path: Path) -> str:
    return (
        path.relative_to(ROOT).as_posix()
        if path.is_relative_to(ROOT)
        else path.as_posix()
    )


def blocked_pair_review_report(
    index_path: Path,
    ledger_path: Path,
    error: ValueError,
) -> dict[str, object]:
    index_path = index_path.resolve()
    ledger_path = ledger_path.resolve()
    index = json.loads(index_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    summary = ledger.get("pairwise_full_size_review_summary", {})
    pair_shard = next(
        (
            shard
            for shard in index.get("shards", [])
            if shard.get("shard_id")
            == "kingfisher_act_001_066_111_176_pair_review"
        ),
        {},
    )
    return {
        "schema_version": 1,
        "character_id": "kingfisher",
        "index_path": _report_path(index_path),
        "index_sha256": sha256_path(index_path),
        "ledger_path": _report_path(ledger_path),
        "ledger_sha256": sha256_path(ledger_path),
        "pose_count": int(index.get("pose_count", 0)),
        "pair_count": int(summary.get("pair_count", 0)),
        "pairwise_full_size_pass_count": int(summary.get("pass_count", 0)),
        "pending_count": int(summary.get("pending_count", 0)),
        "needs_rebuild_count": int(summary.get("needs_rebuild_count", 0)),
        "not_observable_count": int(summary.get("not_observable_count", 0)),
        "user_approved_count": int(
            index.get("legacy_pair_review", {}).get("user_approved_count", 0)
        ),
        "runtime_admitted_count": 0,
        "pair_artifact_path": str(pair_shard.get("path", "")),
        "pair_artifact_sha256": str(pair_shard.get("sha256", "")),
        "passed": False,
        "verification_state": "blocked_by_pairwise_full_size_review",
        "verification_error": str(error),
    }


def verify_pair_review(
    index_path: Path,
    ledger_path: Path,
) -> dict[str, object]:
    index_path = index_path.resolve()
    ledger_path = ledger_path.resolve()
    library = HDPoseLibrary(index_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    pairs = list(ledger.get("pairs", []))
    if len(pairs) != PAIR_COUNT:
        raise ValueError("pair ledger must contain exactly 66 rows")
    if library.index.get("runtime_admitted") is not False:
        raise ValueError("review library must not be runtime admitted")
    if library.index.get("review_projection") is not True:
        raise ValueError("review library must be marked as a review projection")

    sequence = library.index.get("sequences", {}).get(PAIR_SEQUENCE)
    if not isinstance(sequence, dict):
        raise ValueError("paired review sequence is missing")
    if sequence.get("runtime_admitted") is not False:
        raise ValueError("paired review sequence must remain review-only")
    expected_sequence: list[str] = []
    expected_pair_review_states: list[str] = []
    ledger_root = ledger_path.parent
    observable_count = 0
    not_observable_count = 0
    minimum_silhouette_iou = 1.0
    maximum_registration_delta = 0

    for pair in pairs:
        if pair.get("user_approved") is not False:
            raise ValueError("pair review cannot imply user approval")
        if pair.get("runtime_admitted") is not False:
            raise ValueError("pair review cannot imply runtime admission")
        visual = pair.get("pairwise_full_size_review", {})
        state = visual.get("state")
        if state not in PASSING_REVIEW_STATES:
            raise ValueError(
                f"pair {pair.get('ordinal')} lacks a passing full-size "
                "pairwise disposition"
            )
        if visual.get("user_approval_implied") is not False:
            raise ValueError("internal review cannot imply user approval")
        if visual.get("runtime_admission_implied") is not False:
            raise ValueError("internal review cannot imply runtime admission")
        if state == "pass":
            observable_count += 1
        else:
            not_observable_count += 1
        expected_pair_review_states.append(str(state))

        expected_sequence.extend(
            (str(pair["resting_pose_id"]), str(pair["speaking_pose_id"]))
        )
        receipt_path = _evidence_path(pair["receipt_path"], ledger_root)
        audit_path = _evidence_path(pair["audit_path"], ledger_root)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        if audit.get("passed") is not True:
            raise ValueError(f"pair audit failed: {pair['ordinal']}")
        for field in ("resting", "speaking"):
            image_path = _evidence_path(receipt[f"{field}_path"], ledger_root)
            digest = sha256_path(image_path)
            checksum_field = f"{field}_sha256"
            if receipt.get(checksum_field) != digest:
                raise ValueError(f"receipt checksum mismatch: {pair['ordinal']}")
            if audit.get(checksum_field) != digest:
                raise ValueError(f"audit checksum mismatch: {pair['ordinal']}")
        minimum_silhouette_iou = min(
            minimum_silhouette_iou,
            float(audit.get("silhouette_iou", 1.0)),
        )
        maximum_registration_delta = max(
            maximum_registration_delta,
            int(audit.get("registration_bound_delta", 0)),
        )

    if sequence.get("pose_ids") != expected_sequence:
        raise ValueError("paired review sequence is not exact closed/open order")
    if sequence.get("pair_review_states") != expected_pair_review_states:
        raise ValueError("paired review sequence dispositions do not match ledger")
    if len(library.pose_ids) != len(set(library.pose_ids)):
        raise ValueError("review library pose ids must be unique")

    non_binary_alpha: list[str] = []
    wrong_canvas: list[str] = []
    for pose_id in library.pose_ids:
        frame = library.load_pose(pose_id)
        if frame.size != library.canvas_size:
            wrong_canvas.append(pose_id)
        if not set(frame.getchannel("A").getdata()).issubset({0, 255}):
            non_binary_alpha.append(pose_id)
    if wrong_canvas:
        raise ValueError(f"poses use the wrong canvas: {wrong_canvas[:3]}")
    if non_binary_alpha:
        raise ValueError(f"poses use non-binary alpha: {non_binary_alpha[:3]}")

    pair_shards = [
        shard
        for shard in library.index["shards"]
        if shard.get("shard_id")
        == "kingfisher_act_001_066_111_176_pair_review"
    ]
    if len(pair_shards) != 1:
        raise ValueError("expected exactly one pair-review artifact")
    pair_shard = pair_shards[0]
    if str(pair_shard["sha256"])[:16] not in str(pair_shard["path"]):
        raise ValueError("pair-review artifact must be content addressed")

    return {
        "schema_version": 1,
        "character_id": "kingfisher",
        "index_path": _report_path(index_path),
        "index_sha256": sha256_path(index_path),
        "ledger_path": _report_path(ledger_path),
        "ledger_sha256": sha256_path(ledger_path),
        "pose_count": len(library.pose_ids),
        "pair_count": len(pairs),
        "paired_sequence_frame_count": len(expected_sequence),
        "canvas": list(library.canvas_size),
        "binary_alpha_pose_count": len(library.pose_ids),
        "pairwise_full_size_pass_count": observable_count,
        "not_observable_count": not_observable_count,
        "user_approved_count": 0,
        "runtime_admitted_count": 0,
        "minimum_pair_silhouette_iou": minimum_silhouette_iou,
        "maximum_registration_bound_delta": maximum_registration_delta,
        "pair_artifact_path": str(pair_shard["path"]),
        "pair_artifact_sha256": str(pair_shard["sha256"]),
        "passed": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = verify_pair_review(args.index, args.ledger)
    except ValueError as error:
        report = blocked_pair_review_report(args.index, args.ledger, error)
        if args.output:
            _write_json_atomic(args.output, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1) from None
    if args.output:
        _write_json_atomic(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
