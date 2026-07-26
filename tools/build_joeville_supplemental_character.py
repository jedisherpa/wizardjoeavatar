#!/usr/bin/env python3
"""Compile 48 authored supplemental poses into a review-only pixel graph."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import (
    HDPoseArtifact,
    sha256_path,
    write_pose_artifact,
)


DEFAULT_AUTHORITY = (
    ROOT / "assets" / "reference" / "hd_canonical" / "manifest.json"
)
TARGET_POSE_COUNT = 48
SEQUENCE_COUNT = 8
FRAMES_PER_SEQUENCE = 6
APPROVAL_STATE = "pending_visual_parity"
CANONICAL_PROFILE = {
    "profile_id": "wizardjoe_hd_alpha_1254_v001",
    "canvas_width": 1254,
    "canvas_height": 1254,
    "baseline_y": 1185,
    "minimum_margin": 69,
    "color_space": "sRGB",
    "alpha_mode": "straight",
}
CHARACTER_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MOTION_CONTRACT_FIELDS = {
    "entry_handoffs",
    "exit_handoffs",
    "family",
    "hold_frame_indices",
    "interrupt_policy",
    "interruptible_frame_indices",
    "loop_mode",
    "root_policy",
    "support_policy",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as destination:
        destination.write(payload)
        destination.flush()
        os.fsync(destination.fileno())
    temporary.replace(path)


def _validate_character_id(character_id: str) -> None:
    if not CHARACTER_ID_PATTERN.fullmatch(character_id):
        raise ValueError("supplemental character_id must be a safe slug")


def _project_path(path: Path, project_root: Path, role: str) -> str:
    root = project_root.resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{role} must stay inside the project root") from exc
    if not relative.parts:
        raise ValueError(f"{role} must identify a project file")
    return relative.as_posix()


def _resolve_project_path(
    project_root: Path, value: object, role: str
) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{role} must be a project-relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{role} must be a project-relative path")
    root = project_root.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{role} escaped the project root") from exc
    return resolved


def _resolve_output_shard(
    index_path: Path, value: object
) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("supplemental shard path must be relative")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("supplemental shard path must be contained")
    root = index_path.parent.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("supplemental shard path escaped library root") from exc
    return resolved


def _validate_profile(profile: object) -> dict[str, Any]:
    if not isinstance(profile, dict) or profile != CANONICAL_PROFILE:
        raise ValueError("supplemental poses require the canonical 1254 profile")
    return dict(profile)


def _validate_portable_receipt(
    receipt_path: Path, project_root: Path, role: str
) -> None:
    receipt = _read_json(receipt_path)

    def visit(value: object, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, str(child_key))
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif key.endswith("_path"):
            resolved = _resolve_project_path(
                project_root, value, f"{role} {key}"
            )
            if not resolved.is_file():
                raise ValueError(f"{role} references a missing project file")

    visit(receipt)


def _validate_manifest(
    *,
    character_id: str,
    manifest: dict[str, Any],
) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    if manifest.get("schema_version") != 1:
        raise ValueError("supplemental motion schema_version must be 1")
    if manifest.get("manifest_type") != (
        "joeville_supplemental_character_motion"
    ):
        raise ValueError("supplemental motion manifest_type mismatch")
    if manifest.get("character_id") != character_id:
        raise ValueError("supplemental motion character_id mismatch")
    if manifest.get("roster_state") != "supplemental_authored_character":
        raise ValueError("supplemental motion roster_state mismatch")
    if manifest.get("review_projection") is not True:
        raise ValueError("supplemental motion must be a review projection")
    if manifest.get("runtime_admitted") is not False:
        raise ValueError("supplemental motion must deny runtime admission")
    if manifest.get("pose_count") != TARGET_POSE_COUNT:
        raise ValueError("supplemental motion must declare exactly 48 poses")
    _validate_profile(manifest.get("profile"))

    sequences = manifest.get("sequences")
    sequence_order = manifest.get("sequence_order")
    if not isinstance(sequences, dict):
        raise ValueError("supplemental motion sequences must be an object")
    if (
        not isinstance(sequence_order, list)
        or len(sequence_order) != SEQUENCE_COUNT
        or len(set(sequence_order)) != SEQUENCE_COUNT
        or set(sequence_order) != set(sequences)
    ):
        raise ValueError("supplemental motion requires eight unique sequences")

    ordered: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    seen_paths: set[str] = set()
    seen_source_hashes: set[str] = set()
    seen_rgba_hashes: set[str] = set()
    pose_number = 1
    for sequence_id in sequence_order:
        sequence = sequences[sequence_id]
        if not isinstance(sequence, dict):
            raise ValueError(f"{sequence_id} must be an object")
        if not isinstance(sequence.get("intent"), str) or not sequence["intent"]:
            raise ValueError(f"{sequence_id} must declare an intent")
        if not isinstance(sequence.get("fps"), int) or sequence["fps"] <= 0:
            raise ValueError(f"{sequence_id} must declare a positive fps")
        if not isinstance(sequence.get("loop"), bool):
            raise ValueError(f"{sequence_id} must declare loop as a boolean")
        contract = sequence.get("motion_contract")
        if not isinstance(contract, dict) or set(contract) != (
            MOTION_CONTRACT_FIELDS
        ):
            raise ValueError(f"{sequence_id} motion contract fields mismatch")
        expected_loop_mode = "loop" if sequence["loop"] else "hold_last"
        if contract["loop_mode"] != expected_loop_mode:
            raise ValueError(f"{sequence_id} loop mode contradicts loop flag")
        frames = sequence.get("frames")
        if not isinstance(frames, list) or len(frames) != FRAMES_PER_SEQUENCE:
            raise ValueError(f"{sequence_id} must contain exactly six frames")
        for frame_index, frame in enumerate(frames, start=1):
            if not isinstance(frame, dict):
                raise ValueError(f"{sequence_id} frame must be an object")
            expected_pose_id = (
                f"{character_id.replace('-', '_')}_motion_{pose_number:03d}"
            )
            if frame.get("pose_id") != expected_pose_id:
                raise ValueError(f"{sequence_id} pose_id topology mismatch")
            if frame.get("slot_id") != f"motion-{pose_number:03d}":
                raise ValueError(f"{sequence_id} slot_id topology mismatch")
            if frame.get("frame_index") != frame_index:
                raise ValueError(f"{sequence_id} frame_index must be contiguous")
            for field in (
                "source_path",
                "source_sha256",
                "rgba_sha256",
                "alpha_extracted_path",
                "alpha_extracted_sha256",
                "chroma_source_path",
                "chroma_source_sha256",
            ):
                if not isinstance(frame.get(field), str) or not frame[field]:
                    raise ValueError(f"{expected_pose_id} lacks {field}")
            source_path = frame["source_path"]
            source_sha256 = frame["source_sha256"]
            rgba_sha256 = frame["rgba_sha256"]
            if source_path in seen_paths:
                raise ValueError("supplemental source paths must be distinct")
            if source_sha256 in seen_source_hashes:
                raise ValueError("supplemental PNG poses must be unique")
            if rgba_sha256 in seen_rgba_hashes:
                raise ValueError("supplemental RGBA poses must be unique")
            for role in (
                "alpha_extraction_receipt",
                "canonicalization_receipt",
            ):
                receipt = frame.get(role)
                if (
                    not isinstance(receipt, dict)
                    or set(receipt) != {"path", "sha256"}
                    or not all(
                        isinstance(receipt[field], str) and receipt[field]
                        for field in ("path", "sha256")
                    )
                ):
                    raise ValueError(f"{expected_pose_id} lacks {role}")
            seen_paths.add(source_path)
            seen_source_hashes.add(source_sha256)
            seen_rgba_hashes.add(rgba_sha256)
            ordered.append((sequence_id, sequence, frame))
            pose_number += 1
    if len(ordered) != TARGET_POSE_COUNT:
        raise ValueError("supplemental motion topology must contain 48 poses")
    return ordered


def _load_frame(
    *,
    frame: dict[str, Any],
    profile: dict[str, Any],
    project_root: Path,
) -> tuple[Image.Image, dict[str, Any]]:
    pose_id = frame["pose_id"]
    source_path = _resolve_project_path(
        project_root, frame["source_path"], f"{pose_id} source"
    )
    if source_path.suffix.lower() != ".png":
        raise ValueError(f"{pose_id} source must be a PNG")
    if sha256_path(source_path) != frame["source_sha256"]:
        raise ValueError(f"{pose_id} source checksum mismatch")

    for path_field, hash_field in (
        ("alpha_extracted_path", "alpha_extracted_sha256"),
        ("chroma_source_path", "chroma_source_sha256"),
    ):
        related = _resolve_project_path(
            project_root, frame[path_field], f"{pose_id} {path_field}"
        )
        if sha256_path(related) != frame[hash_field]:
            raise ValueError(f"{pose_id} {path_field} checksum mismatch")
    for role in (
        "alpha_extraction_receipt",
        "canonicalization_receipt",
    ):
        receipt = frame[role]
        receipt_path = _resolve_project_path(
            project_root, receipt["path"], f"{pose_id} {role}"
        )
        if sha256_path(receipt_path) != receipt["sha256"]:
            raise ValueError(f"{pose_id} {role} checksum mismatch")
        _validate_portable_receipt(
            receipt_path, project_root, f"{pose_id} {role}"
        )

    with Image.open(source_path) as source:
        source.load()
        if source.format != "PNG" or source.mode != "RGBA":
            raise ValueError(f"{pose_id} must be a decoded RGBA PNG")
        if source.size != (
            profile["canvas_width"],
            profile["canvas_height"],
        ):
            raise ValueError(f"{pose_id} must match the canonical canvas")
        image = source.copy()
    alpha = image.getchannel("A")
    if alpha.getextrema()[0] != 0 or alpha.getextrema()[1] == 0:
        raise ValueError(
            f"{pose_id} must contain transparent and visible pixels"
        )
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError(f"{pose_id} has no visible silhouette")
    if bbox[3] != profile["baseline_y"]:
        raise ValueError(f"{pose_id} canonical baseline mismatch")
    margin = profile["minimum_margin"]
    if (
        bbox[0] < margin
        or bbox[1] < margin
        or profile["canvas_width"] - bbox[2] < margin
    ):
        raise ValueError(f"{pose_id} violates the canonical margin")
    if list(bbox) != frame.get("canonical_bbox"):
        raise ValueError(f"{pose_id} canonical bbox mismatch")
    rgba_sha256 = hashlib.sha256(image.tobytes()).hexdigest()
    if rgba_sha256 != frame["rgba_sha256"]:
        raise ValueError(f"{pose_id} RGBA checksum mismatch")
    return image, {
        "source_path": frame["source_path"],
        "source_sha256": frame["source_sha256"],
        "rgba_sha256": rgba_sha256,
        "canonical_bbox": list(bbox),
        "alpha_extracted_path": frame["alpha_extracted_path"],
        "alpha_extracted_sha256": frame["alpha_extracted_sha256"],
        "chroma_source_path": frame["chroma_source_path"],
        "chroma_source_sha256": frame["chroma_source_sha256"],
        "alpha_extraction_receipt": dict(
            frame["alpha_extraction_receipt"]
        ),
        "canonicalization_receipt": dict(
            frame["canonicalization_receipt"]
        ),
        "authorship": frame.get("authorship", "authored_full_size"),
        "brief_id": frame.get("brief_id"),
    }


def build_supplemental_character(
    *,
    character_id: str,
    manifest_path: Path,
    output_dir: Path,
    authority_path: Path = DEFAULT_AUTHORITY,
    project_root: Path = ROOT,
) -> dict[str, Any]:
    """Build a deterministic, review-only 48-pose supplemental library."""

    _validate_character_id(character_id)
    project_root = project_root.resolve()
    manifest_path = manifest_path.resolve()
    authority_path = authority_path.resolve()
    output_dir = output_dir.resolve()
    _project_path(manifest_path, project_root, "supplemental manifest")
    _project_path(authority_path, project_root, "authority manifest")
    _project_path(
        output_dir / "library-index.json",
        project_root,
        "supplemental output",
    )

    manifest = _read_json(manifest_path)
    authority = _read_json(authority_path)
    profile = _validate_profile(authority.get("master_profile"))
    if manifest.get("profile") != profile:
        raise ValueError("supplemental manifest profile mismatch")
    authority_record = manifest.get("authority_manifest")
    if not isinstance(authority_record, dict):
        raise ValueError("supplemental authority record is missing")
    if authority_record.get("path") != _project_path(
        authority_path, project_root, "authority manifest"
    ):
        raise ValueError("supplemental authority path mismatch")
    if authority_record.get("sha256") != sha256_path(authority_path):
        raise ValueError("supplemental authority checksum mismatch")
    ordered = _validate_manifest(
        character_id=character_id, manifest=manifest
    )

    poses: dict[str, Image.Image] = {}
    pose_records: list[dict[str, Any]] = []
    sequence_pose_ids: dict[str, list[str]] = {
        sequence_id: [] for sequence_id in manifest["sequence_order"]
    }
    actual_rgba_hashes: set[str] = set()
    for sequence_id, sequence, frame in ordered:
        image, provenance = _load_frame(
            frame=frame,
            profile=profile,
            project_root=project_root,
        )
        if provenance["rgba_sha256"] in actual_rgba_hashes:
            raise ValueError("supplemental decoded RGBA poses must be unique")
        actual_rgba_hashes.add(provenance["rgba_sha256"])
        pose_id = frame["pose_id"]
        poses[pose_id] = image
        sequence_pose_ids[sequence_id].append(pose_id)
        pose_records.append(
            {
                "pose_id": pose_id,
                "motion_slot_id": frame["slot_id"],
                "sequence_id": sequence_id,
                "source_frame_index": frame["frame_index"],
                "pose_summary": frame.get("pose_summary"),
                **provenance,
                "approval_state": APPROVAL_STATE,
                "review_projection": True,
                "runtime_admitted": False,
            }
        )
    if len(poses) != TARGET_POSE_COUNT:
        raise ValueError("supplemental build did not produce 48 poses")

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_name = (
        f"{character_id}-candidate-supplemental-48-v001.wjpose"
    )
    artifact_path = output_dir / artifact_name
    index_path = output_dir / "library-index.json"
    if _resolve_output_shard(index_path, artifact_name) != (
        artifact_path.resolve()
    ):
        raise ValueError("supplemental shard output escaped library root")
    temporary_artifact = artifact_path.with_name(
        f".{artifact_name}.{os.getpid()}.tmp"
    )
    artifact_receipt = write_pose_artifact(
        temporary_artifact,
        poses,
        profile=profile,
        provenance={
            "asset_set_id": (
                f"{character_id}-supplemental-motion-48-v001"
            ),
            "character_id": character_id,
            "supplemental_manifest_sha256": sha256_path(manifest_path),
            "authority_manifest_sha256": sha256_path(authority_path),
            "approval_state": APPROVAL_STATE,
            "review_projection": True,
            "runtime_admitted": False,
            "reconstruction": "authored_full_size_rgba_v1",
        },
    )
    temporary_artifact.replace(artifact_path)
    artifact_receipt = {
        **artifact_receipt,
        "path": artifact_name,
        "sha256": sha256_path(artifact_path),
    }
    artifact = HDPoseArtifact(artifact_path)
    if len(artifact.records) != TARGET_POSE_COUNT:
        raise ValueError("supplemental artifact pose count mismatch")

    all_pose_ids = [
        pose_id
        for sequence_id in manifest["sequence_order"]
        for pose_id in sequence_pose_ids[sequence_id]
    ]
    index_sequences: dict[str, Any] = {
        f"{character_id}-supplemental-all": {
            "fps": 8,
            "loop": True,
            "pose_ids": all_pose_ids,
            "approval_state": APPROVAL_STATE,
            "review_projection": True,
            "runtime_admitted": False,
        }
    }
    for sequence_id in manifest["sequence_order"]:
        sequence = manifest["sequences"][sequence_id]
        index_sequences[sequence_id] = {
            "intent": sequence["intent"],
            "family": sequence["motion_contract"]["family"],
            "fps": sequence["fps"],
            "loop": sequence["loop"],
            "loop_mode": sequence["motion_contract"]["loop_mode"],
            "pose_ids": sequence_pose_ids[sequence_id],
            "approval_state": APPROVAL_STATE,
            "review_projection": True,
            "runtime_admitted": False,
        }
    index = {
        "schema_version": 1,
        "asset_set_id": f"{character_id}-supplemental-motion-48-v001",
        "character_id": character_id,
        "display_name": manifest["display_name"],
        "roster_state": "supplemental_authored_character",
        "profile": profile,
        "payload_encoding": "rgba8-zlib",
        "pose_count": TARGET_POSE_COUNT,
        "approved_pose_count": 0,
        "candidate_pose_count": TARGET_POSE_COUNT,
        "review_projection": True,
        "runtime_admitted": False,
        "sequences": index_sequences,
        "shards": [
            {
                "shard_id": (
                    f"{character_id}-supplemental-motion-48-v001"
                ),
                "source": "authored_supplemental_full_size",
                "path": artifact_name,
                "sha256": artifact_receipt["sha256"],
                "bytes": artifact_receipt["bytes"],
                "pose_count": TARGET_POSE_COUNT,
                "pose_ids": artifact_receipt["pose_ids"],
                "approval_state": APPROVAL_STATE,
                "review_projection": True,
                "runtime_admitted": False,
            }
        ],
        "poses": sorted(pose_records, key=lambda record: record["pose_id"]),
    }
    index_bytes = _json_bytes(index)
    _write_bytes_atomic(index_path, index_bytes)
    index_sha256 = hashlib.sha256(index_bytes).hexdigest()

    build_receipt = {
        "schema_version": 1,
        "character_id": character_id,
        "asset_set_id": index["asset_set_id"],
        "supplemental_manifest": {
            "path": _project_path(
                manifest_path, project_root, "supplemental manifest"
            ),
            "sha256": sha256_path(manifest_path),
        },
        "authority_manifest": {
            "path": _project_path(
                authority_path, project_root, "authority manifest"
            ),
            "sha256": sha256_path(authority_path),
        },
        "artifact": {
            "path": _project_path(
                artifact_path, project_root, "supplemental artifact"
            ),
            "sha256": artifact_receipt["sha256"],
            "bytes": artifact_receipt["bytes"],
            "pose_count": TARGET_POSE_COUNT,
        },
        "library_index": {
            "path": _project_path(
                index_path, project_root, "supplemental library index"
            ),
            "sha256": index_sha256,
        },
        "pose_count": TARGET_POSE_COUNT,
        "review_projection": True,
        "runtime_admitted": False,
    }
    receipt_path = output_dir / "build-receipt.json"
    receipt_bytes = _json_bytes(build_receipt)
    _write_bytes_atomic(receipt_path, receipt_bytes)
    return {
        **build_receipt,
        "artifact_path": str(artifact_path),
        "artifact_sha256": artifact_receipt["sha256"],
        "library_index_path": str(index_path),
        "library_index_sha256": index_sha256,
        "build_receipt_path": str(receipt_path),
        "build_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("character_id")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = build_supplemental_character(
        character_id=args.character_id,
        manifest_path=args.manifest,
        output_dir=args.output,
        authority_path=args.authority,
        project_root=args.project_root,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
