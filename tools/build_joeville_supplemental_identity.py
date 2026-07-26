#!/usr/bin/env python3
"""Compile one supplemental JoeVille identity into a review-only pixel graph."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import write_pose_artifact


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json_atomic(path: Path, value: dict[str, Any]) -> str:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as destination:
        destination.write(payload)
        destination.flush()
        os.fsync(destination.fileno())
    temporary.replace(path)
    return hashlib.sha256(payload).hexdigest()


def _project_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError as exc:
        raise ValueError("supplemental identity manifest must be in the project") from exc


def build_identity(manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != 1:
        raise ValueError("supplemental identity schema_version must be 1")
    if manifest.get("roster_state") != "supplemental_authored_character":
        raise ValueError("supplemental identity must declare its roster state")
    if manifest.get("review_projection") is not True:
        raise ValueError("supplemental identity must be a review projection")
    if manifest.get("runtime_admitted") is not False:
        raise ValueError("supplemental identity must fail closed")

    character_id = str(manifest["character_id"])
    display_name = str(manifest["display_name"])
    pose = manifest["identity_pose"]
    pose_id = str(pose["pose_id"])
    frame_path = (manifest_path.parent / str(pose["path"])).resolve()
    if _sha256(frame_path) != pose["sha256"]:
        raise ValueError("supplemental identity frame checksum mismatch")

    profile = manifest["profile"]
    expected_size = (
        int(profile["canvas_width"]),
        int(profile["canvas_height"]),
    )
    with Image.open(frame_path) as source:
        source.load()
        if source.format != "PNG" or source.mode != "RGBA":
            raise ValueError("supplemental identity must be an RGBA PNG")
        if source.size != expected_size:
            raise ValueError("supplemental identity profile mismatch")
        image = source.copy()
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("supplemental identity has no visible silhouette")
    if bbox[3] != int(profile["baseline_y"]):
        raise ValueError("supplemental identity baseline mismatch")

    receipt_paths = manifest["receipt_chain"]
    for role in ("alpha_extraction", "canonicalization"):
        receipt = receipt_paths[role]
        receipt_path = (manifest_path.parent / str(receipt["path"])).resolve()
        if _sha256(receipt_path) != receipt["sha256"]:
            raise ValueError(f"{role} receipt checksum mismatch")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / f"{character_id}-identity-review-v001.wjpose"
    artifact = write_pose_artifact(
        artifact_path,
        {pose_id: image},
        profile=profile,
        provenance={
            "asset_set_id": f"{character_id}-supplemental-identity-v001",
            "character_id": character_id,
            "identity_manifest_sha256": _sha256(manifest_path),
            "approval_state": "pending_identity_review",
            "review_projection": True,
            "runtime_admitted": False,
        },
    )
    index = {
        "schema_version": 1,
        "asset_set_id": f"{character_id}-supplemental-identity-v001",
        "character_id": character_id,
        "display_name": display_name,
        "roster_state": "supplemental_authored_character",
        "profile": profile,
        "payload_encoding": "rgba8-zlib",
        "review_projection": True,
        "runtime_admitted": False,
        "pose_count": 1,
        "approved_pose_count": 0,
        "candidate_pose_count": 1,
        "shards": [
            {
                "shard_id": "identity_review",
                "source": "authored_supplemental_identity",
                "path": artifact_path.name,
                "sha256": artifact["sha256"],
                "bytes": artifact["bytes"],
                "pose_count": 1,
                "pose_ids": [pose_id],
                "approval_state": "pending_identity_review",
                "runtime_admitted": False,
            }
        ],
        "sequences": {
            f"{character_id}-identity-review": {
                "fps": 1,
                "loop": True,
                "pose_ids": [pose_id],
                "approval_state": "pending_identity_review",
                "runtime_admitted": False,
                "runtime_note": (
                    "Identity-gate projection only; no animation or production "
                    "runtime admission is implied."
                ),
            }
        },
    }
    index_path = output_dir / "library-index.json"
    index_sha256 = _write_json_atomic(index_path, index)
    build_receipt = {
        "schema_version": 1,
        "character_id": character_id,
        "identity_manifest": {
            "path": _project_path(manifest_path),
            "sha256": _sha256(manifest_path),
        },
        "artifact": {
            "path": artifact_path.name,
            "sha256": artifact["sha256"],
            "bytes": artifact["bytes"],
            "pose_count": 1,
        },
        "library_index": {
            "path": index_path.name,
            "sha256": index_sha256,
        },
        "review_projection": True,
        "runtime_admitted": False,
    }
    receipt_path = output_dir / "build-receipt.json"
    receipt_sha256 = _write_json_atomic(receipt_path, build_receipt)
    return {
        **build_receipt,
        "build_receipt": {
            "path": receipt_path.name,
            "sha256": receipt_sha256,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build_identity(args.manifest, args.output),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
