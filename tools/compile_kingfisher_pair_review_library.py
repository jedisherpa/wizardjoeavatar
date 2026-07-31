#!/usr/bin/env python3
"""Compile Kingfisher's legacy closed/open pairs into a review-only library."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import (  # noqa: E402
    HDPoseLibrary,
    sha256_path,
    write_pose_artifact,
)

BASE_POSE_COUNT = 66
SPEAKING_FIRST_ORDINAL = 111
SPEAKING_LAST_ORDINAL = 176
PAIR_REVIEW_SHARD_ID = "kingfisher_act_001_066_111_176_pair_review"


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_pose_artifact_atomic(
    path: Path,
    poses: OrderedDict[str, Image.Image],
    *,
    profile: dict[str, object],
    provenance: dict[str, object],
) -> dict[str, object]:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        receipt = write_pose_artifact(
            temporary,
            poses,
            profile=profile,
            provenance=provenance,
        )
        digest = sha256_path(temporary)
        published = path.with_name(
            f"{path.stem}-{digest[:16]}{path.suffix}"
        )
        if published.exists():
            if sha256_path(published) != digest:
                raise ValueError("content-addressed artifact checksum mismatch")
            temporary.unlink()
        else:
            temporary.replace(published)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        **receipt,
        "path": published.as_posix(),
        "sha256": digest,
        "bytes": published.stat().st_size,
    }


def _evidence_path(raw_path: object, ledger_root: Path) -> Path:
    path = Path(str(raw_path))
    if path.is_absolute():
        return path.resolve()
    repository_path = (ROOT / path).resolve()
    if repository_path.exists():
        return repository_path
    return (ledger_root / path).resolve()


def _copy_base_shards(
    base_library: HDPoseLibrary,
    output_root: Path,
) -> list[dict[str, object]]:
    shards: list[dict[str, object]] = []
    for original in base_library.index["shards"]:
        shard_ordinals = {
            int(str(pose_id).split(".")[2])
            for pose_id in original["pose_ids"]
        }
        if original["shard_id"] == PAIR_REVIEW_SHARD_ID:
            continue
        if any(ordinal <= BASE_POSE_COUNT for ordinal in shard_ordinals):
            continue
        shard = dict(original)
        source_path = base_library.artifacts[str(shard["shard_id"])].path.resolve()
        if sha256_path(source_path) != shard["sha256"]:
            raise ValueError(f"Kingfisher base shard checksum mismatch: {shard['shard_id']}")
        destination_path = (output_root / Path(str(shard["path"]))).resolve()
        try:
            destination_path.relative_to(output_root)
        except ValueError as exc:
            raise ValueError("Kingfisher base shard path escapes output root") from exc
        if destination_path != source_path:
            _write_bytes_atomic(destination_path, source_path.read_bytes())
        shards.append(shard)
    return shards


def _load_pair_candidates(
    base_library: HDPoseLibrary,
    ledger_path: Path,
) -> tuple[
    OrderedDict[str, Image.Image],
    list[str],
    list[dict[str, object]],
]:
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if ledger.get("character_id") != "kingfisher":
        raise ValueError("pair ledger must target Kingfisher")
    pairs = list(ledger.get("pairs", []))
    if len(pairs) != BASE_POSE_COUNT:
        raise ValueError("pair ledger must contain exactly 66 Kingfisher pairs")
    if ledger.get("runtime_admitted_count") != 0:
        raise ValueError("pair ledger must remain review-only")

    ledger_root = ledger_path.parent.resolve()
    pair_poses: OrderedDict[str, Image.Image] = OrderedDict()
    alternating_pose_ids: list[str] = []
    evidence: list[dict[str, object]] = []
    expected_speaking_ordinals = list(
        range(SPEAKING_FIRST_ORDINAL, SPEAKING_LAST_ORDINAL + 1)
    )

    for expected_ordinal, pair in zip(expected_speaking_ordinals, pairs):
        if pair.get("status") != "candidate_visual_review":
            raise ValueError("all pair rows must be candidate_visual_review")
        if pair.get("automated_audit_passed") is not True:
            raise ValueError("all pair rows must pass automated audit")
        if pair.get("user_approved") is not False:
            raise ValueError("pair review compilation cannot imply user approval")
        if pair.get("runtime_admitted") is not False:
            raise ValueError("pair review compilation cannot admit runtime poses")

        speaking_ordinal = int(pair["speaking_ordinal"])
        if speaking_ordinal != expected_ordinal:
            raise ValueError("pair speaking ordinals must be contiguous ACT111-ACT176")
        resting_pose_id = str(pair["resting_pose_id"])
        speaking_pose_id = str(pair["speaking_pose_id"])
        if resting_pose_id not in base_library.pose_ids:
            raise ValueError(f"missing resting pose in base library: {resting_pose_id}")

        receipt_path = _evidence_path(pair["receipt_path"], ledger_root)
        audit_path = _evidence_path(pair["audit_path"], ledger_root)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        if receipt.get("approval_state") != "candidate_visual_review":
            raise ValueError("pair receipt must remain candidate_visual_review")
        if receipt.get("runtime_admitted") is not False:
            raise ValueError("pair receipt cannot admit the candidate")
        if audit.get("passed") is not True:
            raise ValueError("pair audit must pass")

        resting_path = _evidence_path(receipt["resting_path"], ledger_root)
        speaking_path = _evidence_path(receipt["speaking_path"], ledger_root)
        hashes = {
            "resting_sha256": sha256_path(resting_path),
            "speaking_sha256": sha256_path(speaking_path),
        }
        for field, digest in hashes.items():
            if receipt.get(field) != digest or audit.get(field) != digest:
                raise ValueError(f"pair evidence checksum mismatch: {field}")

        with Image.open(resting_path) as loaded:
            resting = loaded.convert("RGBA")
        with Image.open(speaking_path) as loaded:
            speaking = loaded.convert("RGBA")
        if resting.size != base_library.canvas_size or speaking.size != base_library.canvas_size:
            raise ValueError("pair candidates must match the base library canvas")
        if not set(resting.getchannel("A").getdata()).issubset({0, 255}):
            raise ValueError(f"resting master must use binary alpha: {resting_pose_id}")
        if not set(speaking.getchannel("A").getdata()).issubset({0, 255}):
            raise ValueError(f"speaking candidate must use binary alpha: {speaking_pose_id}")

        pair_poses[resting_pose_id] = resting
        pair_poses[speaking_pose_id] = speaking
        alternating_pose_ids.extend((resting_pose_id, speaking_pose_id))
        evidence.append(
            {
                "ordinal": int(pair["ordinal"]),
                "speaking_ordinal": speaking_ordinal,
                "resting_pose_id": resting_pose_id,
                "speaking_pose_id": speaking_pose_id,
                "resting_sha256": hashes["resting_sha256"],
                "speaking_sha256": hashes["speaking_sha256"],
                "receipt_path": receipt_path.relative_to(ROOT).as_posix()
                if receipt_path.is_relative_to(ROOT)
                else receipt_path.as_posix(),
                "receipt_sha256": sha256_path(receipt_path),
                "audit_path": audit_path.relative_to(ROOT).as_posix()
                if audit_path.is_relative_to(ROOT)
                else audit_path.as_posix(),
                "audit_sha256": sha256_path(audit_path),
                "automated_audit_passed": True,
                "user_approved": False,
                "runtime_admitted": False,
            }
        )
    return pair_poses, alternating_pose_ids, evidence


def compile_pair_review_library(
    base_index_path: Path,
    ledger_path: Path,
    output_root: Path,
) -> dict[str, object]:
    base_index_path = base_index_path.resolve()
    ledger_path = ledger_path.resolve()
    output_root = output_root.resolve()
    base_library = HDPoseLibrary(base_index_path)
    if base_library.index.get("character_id") != "kingfisher":
        raise ValueError("base library must target Kingfisher")

    pair_poses, alternating_pose_ids, pair_evidence = _load_pair_candidates(
        base_library,
        ledger_path,
    )
    output_root.mkdir(parents=True, exist_ok=True)
    base_shards = _copy_base_shards(base_library, output_root)
    artifact_seed_path = output_root / f"{PAIR_REVIEW_SHARD_ID}.wjpose"
    artifact_receipt = _write_pose_artifact_atomic(
        artifact_seed_path,
        pair_poses,
        profile=base_library.index["profile"],
        provenance={
            "source": "kingfisher_pair_specific_beak_review_v1",
            "ledger_path": ledger_path.relative_to(ROOT).as_posix()
            if ledger_path.is_relative_to(ROOT)
            else ledger_path.as_posix(),
            "ledger_sha256": sha256_path(ledger_path),
            "pair_audit_sha256": [item["audit_sha256"] for item in pair_evidence],
        },
    )
    artifact_path = Path(str(artifact_receipt["path"]))
    pair_review_shard = {
        "shard_id": PAIR_REVIEW_SHARD_ID,
        "path": artifact_path.name,
        "sha256": artifact_receipt["sha256"],
        "bytes": artifact_receipt["bytes"],
        "pose_count": len(pair_poses),
        "pose_ids": list(pair_poses),
        "approval_state": "candidate_visual_review",
        "review_projection": True,
        "runtime_admitted": False,
        "source": "kingfisher_pair_specific_beak_review_v1",
    }

    stage_pose_ids = [
        pose_id
        for pose_id in base_library.pose_ids
        if 67 <= int(pose_id.split(".")[2]) <= 110
    ]
    pose_ids = list(pair_poses) + stage_pose_ids
    sequences = dict(base_library.index.get("sequences", {}))
    sequences["kingfisher-paired-beaks-review"] = {
        "approval_state": "candidate_visual_review",
        "fps": 2,
        "loop": True,
        "pose_ids": alternating_pose_ids,
        "review_projection": True,
        "runtime_admitted": False,
    }
    sequences["kingfisher-all"] = {
        "approval_state": "candidate_visual_review",
        "fps": 3,
        "loop": True,
        "pose_ids": alternating_pose_ids + stage_pose_ids,
        "review_projection": True,
        "runtime_admitted": False,
    }

    output_index = {
        **base_library.index,
        "asset_set_id": "kingfisher-registered-alpha-176-pair-review-v001",
        "pose_count": len(pose_ids),
        "pose_ids": pose_ids,
        "shards": base_shards + [pair_review_shard],
        "sequences": sequences,
        "legacy_pair_review": {
            "approval_state": "candidate_visual_review",
            "review_projection": True,
            "runtime_admitted": False,
            "user_approved_count": 0,
            "pair_count": len(pair_evidence),
            "ledger_path": ledger_path.relative_to(ROOT).as_posix()
            if ledger_path.is_relative_to(ROOT)
            else ledger_path.as_posix(),
            "ledger_sha256": sha256_path(ledger_path),
            "pairs": pair_evidence,
        },
        "review_projection": True,
        "runtime_admitted": False,
    }
    index_path = output_root / "library-index.json"
    _write_json_atomic(index_path, output_index)
    HDPoseLibrary(index_path)
    return {
        "index_path": index_path.as_posix(),
        "index_sha256": sha256_path(index_path),
        "artifact_path": artifact_path.as_posix(),
        "artifact_sha256": artifact_receipt["sha256"],
        "pose_count": len(pose_ids),
        "pair_count": len(pair_evidence),
        "runtime_admitted": False,
        "user_approved_count": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile Kingfisher's 66 closed/open beak pairs for review."
    )
    parser.add_argument("--base-index", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            compile_pair_review_library(
                args.base_index,
                args.ledger,
                args.output_root,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
