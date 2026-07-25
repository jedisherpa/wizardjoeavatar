#!/usr/bin/env python3
"""Merge reviewed full-size authored poses into a JoeVille source library."""

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

from tools.build_hd_phazer_pose_masters import _build_contact_sheet
from wizard_avatar.hd_pose_artifact import (
    HDPoseArtifact,
    sha256_path,
    write_pose_artifact,
)


DEFAULT_AUTHORITY = (
    ROOT / "assets" / "reference" / "hd_canonical" / "manifest.json"
)
DEFAULT_OUTPUT_ROOT = (
    ROOT / "assets" / "reference" / "joeville_48_parity"
)
TARGET_POSE_COUNT = 48
FRAMES_PER_SEQUENCE = 6
AUTHORED_APPROVAL_STATE = "pending_visual_parity"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    _write_bytes_atomic(path, _json_bytes(value))


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as destination:
        destination.write(payload)
        destination.flush()
        os.fsync(destination.fileno())
    temporary.replace(path)


def _expected_pose_id(character_id: str, pose_number: int) -> str:
    return f"{character_id.replace('-', '_')}_motion_{pose_number:03d}"


def _resolve_authored_source(manifest_path: Path, value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("authored pose source_path must be a relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("authored pose source_path must stay inside its manifest")
    root = manifest_path.parent.resolve()
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("authored pose source_path escaped its manifest")
    return resolved


def _load_authored_frame(
    *,
    manifest_path: Path,
    frame: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[Image.Image, dict[str, Any]]:
    source_path = _resolve_authored_source(
        manifest_path, frame.get("source_path")
    )
    if source_path.suffix.lower() != ".png":
        raise ValueError(f"{source_path.name} must be a PNG")
    expected_sha256 = frame.get("source_sha256")
    actual_sha256 = sha256_path(source_path)
    if expected_sha256 != actual_sha256:
        raise ValueError(f"{source_path.name} source checksum mismatch")
    with Image.open(source_path) as source:
        source.load()
        if source.format != "PNG" or source.mode != "RGBA":
            raise ValueError(
                f"{source_path.name} must be a decoded RGBA PNG"
            )
        rgba = source.copy()
    expected_size = (
        int(profile["canvas_width"]),
        int(profile["canvas_height"]),
    )
    if rgba.size != expected_size:
        raise ValueError(
            f"{source_path.name} must match the canonical canvas"
        )
    alpha = rgba.getchannel("A")
    alpha_extrema = alpha.getextrema()
    if alpha_extrema[0] != 0 or alpha_extrema[1] == 0:
        raise ValueError(
            f"{source_path.name} must contain transparent and visible pixels"
        )
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError(f"{source_path.name} has no visible silhouette")
    if bbox[0] == 0 or bbox[1] == 0 or bbox[2] == rgba.width or bbox[3] == rgba.height:
        raise ValueError(
            f"{source_path.name} silhouette touches the source boundary"
        )
    margin = int(profile["minimum_margin"])
    baseline_y = int(profile["baseline_y"])
    if bbox[3] != baseline_y:
        raise ValueError(
            f"{source_path.name} must land on canonical baseline {baseline_y}"
        )
    if bbox[0] < margin or bbox[1] < margin or rgba.width - bbox[2] < margin:
        raise ValueError(
            f"{source_path.name} violates the canonical safety margin"
        )
    rgba_sha256 = hashlib.sha256(rgba.tobytes()).hexdigest()
    if frame.get("rgba_sha256") != rgba_sha256:
        raise ValueError(f"{source_path.name} RGBA checksum mismatch")
    provenance = {
        "source_path": str(source_path.relative_to(manifest_path.parent)),
        "source_sha256": actual_sha256,
        "source_rgba_sha256": rgba_sha256,
        "source_width": rgba.width,
        "source_height": rgba.height,
        "source_bbox": list(bbox),
        "authorship": frame.get("authorship", "authored_full_size"),
        "brief_id": frame.get("brief_id"),
    }
    return rgba, provenance


def _validate_authored_manifest(
    *,
    character_id: str,
    authored_manifest: dict[str, Any],
    existing_manifest: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    if authored_manifest.get("schema_version") != 1:
        raise ValueError("authored pose manifest schema_version must be 1")
    if authored_manifest.get("character_id") != character_id:
        raise ValueError("authored pose manifest character_id mismatch")
    if authored_manifest.get("runtime_admitted") is not False:
        raise ValueError("authored pose manifest must deny runtime admission")
    existing_count = int(existing_manifest["compiled_pose_count"])
    if existing_count >= TARGET_POSE_COUNT:
        raise ValueError("source library already meets the parity target")
    missing_sequences = list(existing_manifest["missing_sequences"])
    sequences = authored_manifest.get("sequences")
    if not isinstance(sequences, dict):
        raise ValueError("authored pose manifest sequences must be an object")
    if list(sequences) != missing_sequences:
        raise ValueError(
            "authored pose sequences must exactly match the source gaps"
        )
    expected_authored_count = TARGET_POSE_COUNT - existing_count
    if expected_authored_count != len(missing_sequences) * FRAMES_PER_SEQUENCE:
        raise ValueError("source gap does not divide into six-frame sequences")

    ordered: list[tuple[str, dict[str, Any]]] = []
    seen_paths: set[str] = set()
    seen_source_hashes: set[str] = set()
    seen_rgba_hashes: set[str] = set()
    pose_number = existing_count + 1
    for sequence_id in missing_sequences:
        sequence = sequences[sequence_id]
        frames = sequence.get("frames") if isinstance(sequence, dict) else None
        if not isinstance(sequence.get("intent"), str) or not sequence["intent"]:
            raise ValueError(f"{sequence_id} must declare an intent")
        if not isinstance(sequence.get("fps"), int) or sequence["fps"] <= 0:
            raise ValueError(f"{sequence_id} must declare a positive fps")
        if not isinstance(sequence.get("loop"), bool):
            raise ValueError(f"{sequence_id} must declare loop as a boolean")
        motion_contract = sequence.get("motion_contract")
        if not isinstance(motion_contract, dict):
            raise ValueError(f"{sequence_id} must declare a motion contract")
        required_contract_fields = {
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
        if set(motion_contract) != required_contract_fields:
            raise ValueError(f"{sequence_id} motion contract fields mismatch")
        expected_loop_mode = "loop" if sequence["loop"] else "hold_last"
        if motion_contract["loop_mode"] != expected_loop_mode:
            raise ValueError(f"{sequence_id} loop mode contradicts loop flag")
        if not isinstance(frames, list) or len(frames) != FRAMES_PER_SEQUENCE:
            raise ValueError(
                f"{sequence_id} must contain exactly six authored frames"
            )
        for frame_index, frame in enumerate(frames, start=1):
            if not isinstance(frame, dict):
                raise ValueError(f"{sequence_id} frame must be an object")
            expected_pose_id = _expected_pose_id(character_id, pose_number)
            expected_slot_id = f"motion-{pose_number:03d}"
            if frame.get("pose_id") != expected_pose_id:
                raise ValueError(
                    f"{sequence_id} frame {frame_index} pose_id mismatch"
                )
            if frame.get("slot_id") != expected_slot_id:
                raise ValueError(
                    f"{sequence_id} frame {frame_index} slot_id mismatch"
                )
            if frame.get("frame_index") != frame_index:
                raise ValueError(
                    f"{sequence_id} frame_index must be contiguous"
                )
            source_path = frame.get("source_path")
            source_sha256 = frame.get("source_sha256")
            rgba_sha256 = frame.get("rgba_sha256")
            if not all(
                isinstance(value, str) and value
                for value in (source_path, source_sha256, rgba_sha256)
            ):
                raise ValueError(
                    f"{sequence_id} frame {frame_index} lacks source hashes"
                )
            if source_path in seen_paths:
                raise ValueError("authored pose source paths must be distinct")
            if source_sha256 in seen_source_hashes:
                raise ValueError("authored PNG hashes must be distinct")
            if rgba_sha256 in seen_rgba_hashes:
                raise ValueError("authored RGBA hashes must be distinct")
            seen_paths.add(source_path)
            seen_source_hashes.add(source_sha256)
            seen_rgba_hashes.add(rgba_sha256)
            ordered.append((sequence_id, frame))
            pose_number += 1
    return ordered


def _build_library_index(
    *,
    character_id: str,
    display_name: str,
    profile: dict[str, Any],
    artifact_name: str,
    receipt: dict[str, Any],
    sequence_pose_ids: dict[str, list[str]],
    authored_sequences: dict[str, Any],
) -> dict[str, Any]:
    all_pose_ids = [
        pose_id
        for sequence in sequence_pose_ids.values()
        for pose_id in sequence
    ]
    return {
        "schema_version": 1,
        "asset_set_id": f"{character_id}-authored-parity-v001",
        "character_id": character_id,
        "display_name": display_name,
        "profile": profile,
        "pose_count": len(all_pose_ids),
        "approved_pose_count": 0,
        "candidate_pose_count": len(all_pose_ids),
        "review_projection": True,
        "runtime_admitted": False,
        "sequences": {
            f"{character_id}-parity-all": {
                "fps": 8,
                "loop": True,
                "pose_ids": all_pose_ids,
                "approval_state": AUTHORED_APPROVAL_STATE,
                "runtime_admitted": False,
            },
            **{
                sequence_id: {
                    "fps": int(
                        authored_sequences.get(sequence_id, {}).get("fps", 8)
                    ),
                    "loop": bool(
                        authored_sequences.get(sequence_id, {}).get(
                            "loop", True
                        )
                    ),
                    **(
                        {
                            "intent": authored_sequences[sequence_id]["intent"],
                            "loop_mode": authored_sequences[sequence_id][
                                "motion_contract"
                            ]["loop_mode"],
                        }
                        if sequence_id in authored_sequences
                        else {}
                    ),
                    "pose_ids": pose_ids,
                    "approval_state": AUTHORED_APPROVAL_STATE,
                    "runtime_admitted": False,
                }
                for sequence_id, pose_ids in sequence_pose_ids.items()
            },
        },
        "shards": [
            {
                "shard_id": f"{character_id}-authored-parity-v001",
                "source": "joeville_supplied_plus_authored_full_size",
                "approval_state": AUTHORED_APPROVAL_STATE,
                "runtime_admitted": False,
                "path": artifact_name,
                "sha256": receipt["sha256"],
                "bytes": receipt["bytes"],
                "pose_count": receipt["pose_count"],
                "pose_ids": receipt["pose_ids"],
            }
        ],
    }


def _build_review_motion_contract(
    *,
    character_id: str,
    profile: dict[str, Any],
    authored_manifest: dict[str, Any],
    sequence_pose_ids: dict[str, list[str]],
    artifact_sha256: str,
    library_index_sha256: str,
) -> dict[str, Any]:
    sequences: dict[str, Any] = {}
    transitions: list[dict[str, Any]] = []
    for sequence_id, authored_sequence in authored_manifest[
        "sequences"
    ].items():
        motion_contract = authored_sequence["motion_contract"]
        frames = []
        interruptible = set(
            motion_contract["interruptible_frame_indices"]
        )
        holds = set(motion_contract["hold_frame_indices"])
        for frame in authored_sequence["frames"]:
            frame_index = int(frame["frame_index"])
            frames.append(
                {
                    "pose_id": frame["pose_id"],
                    "frame_index": frame_index,
                    "duration_ms": round(
                        1000 / int(authored_sequence["fps"])
                    ),
                    "phase": frame["pose_summary"],
                    "root_policy": motion_contract["root_policy"],
                    "support_contact": motion_contract["support_policy"],
                    "baseline_y": int(profile["baseline_y"]),
                    "interruptible": frame_index in interruptible,
                    "hold_marker": frame_index in holds,
                }
            )
        sequences[sequence_id] = {
            "intent": authored_sequence["intent"],
            "family": motion_contract["family"],
            "fps": int(authored_sequence["fps"]),
            "loop_mode": motion_contract["loop_mode"],
            "interrupt_policy": motion_contract["interrupt_policy"],
            "pose_ids": list(sequence_pose_ids[sequence_id]),
            "frames": frames,
            "entry_handoffs": list(motion_contract["entry_handoffs"]),
            "exit_handoffs": list(motion_contract["exit_handoffs"]),
        }
        for target in motion_contract["exit_handoffs"]:
            transitions.append(
                {
                    "from": sequence_id,
                    "to": target,
                    "status": (
                        "resolved"
                        if target in authored_manifest["sequences"]
                        else "deferred_until_character_package"
                    ),
                }
            )
    return {
        "schema_version": 1,
        "contract_id": f"{character_id}-review-motion-v001",
        "character_id": character_id,
        "status": AUTHORED_APPROVAL_STATE,
        "review_projection": True,
        "runtime_admitted": False,
        "profile_id": profile["profile_id"],
        "artifact_sha256": artifact_sha256,
        "library_index_sha256": library_index_sha256,
        "sequences": sequences,
        "transitions": transitions,
    }


def build_authored_parity(
    *,
    character_id: str,
    authored_manifest_path: Path,
    existing_manifest_path: Path,
    authority_path: Path = DEFAULT_AUTHORITY,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    authored_manifest_path = authored_manifest_path.resolve()
    existing_manifest_path = existing_manifest_path.resolve()
    authority_path = authority_path.resolve()
    output_root = output_root.resolve()
    authored_manifest = _read_json(authored_manifest_path)
    existing_manifest = _read_json(existing_manifest_path)
    authority = _read_json(authority_path)
    if existing_manifest.get("character_id") != character_id:
        raise ValueError("existing reconstruction character_id mismatch")
    if existing_manifest.get("runtime_admitted") is not False:
        raise ValueError("existing reconstruction must deny runtime admission")
    authority_sha256 = sha256_path(authority_path)
    existing_manifest_sha256 = sha256_path(existing_manifest_path)
    if (
        authored_manifest.get("authority_manifest_sha256")
        != authority_sha256
    ):
        raise ValueError("authored authority manifest checksum mismatch")
    if (
        authored_manifest.get("existing_reconstruction_sha256")
        != existing_manifest_sha256
    ):
        raise ValueError("authored existing reconstruction checksum mismatch")
    if (
        authored_manifest.get("existing_artifact_sha256")
        != existing_manifest["artifact"]["sha256"]
    ):
        raise ValueError("authored existing artifact checksum mismatch")
    ordered_authored = _validate_authored_manifest(
        character_id=character_id,
        authored_manifest=authored_manifest,
        existing_manifest=existing_manifest,
    )

    profile = dict(authority["master_profile"])
    if authored_manifest.get("profile_id") != profile["profile_id"]:
        raise ValueError("authored pose profile_id mismatch")
    existing_artifact_path = output_root / existing_manifest["artifact"]["path"]
    if sha256_path(existing_artifact_path) != existing_manifest["artifact"]["sha256"]:
        raise ValueError("existing source artifact checksum mismatch")
    existing_artifact = HDPoseArtifact(existing_artifact_path)
    if existing_artifact.canvas_size != (
        int(profile["canvas_width"]),
        int(profile["canvas_height"]),
    ):
        raise ValueError("existing source artifact profile mismatch")

    poses = {
        pose_id: existing_artifact.load_pose(pose_id)
        for pose_id in existing_artifact.records
    }
    records = [dict(record) for record in existing_manifest["poses"]]
    existing_rgba_hashes = {
        record["pose_id"]: record["rgba_sha256"] for record in records
    }
    for pose_id, image in poses.items():
        if hashlib.sha256(image.tobytes()).hexdigest() != existing_rgba_hashes.get(
            pose_id
        ):
            raise ValueError(f"existing pose RGBA checksum mismatch: {pose_id}")
    sequence_pose_ids = {
        sequence_id: list(pose_ids)
        for sequence_id, pose_ids in existing_manifest["sequences"].items()
    }
    authored_images: dict[str, Image.Image] = {}
    provenance_by_pose: dict[str, dict[str, Any]] = {}
    for sequence_id, frame in ordered_authored:
        image, provenance = _load_authored_frame(
            manifest_path=authored_manifest_path,
            frame=frame,
            profile=profile,
        )
        authored_images[frame["pose_id"]] = image
        provenance_by_pose[frame["pose_id"]] = provenance

    for sequence_id in existing_manifest["missing_sequences"]:
        manifest_frames = authored_manifest["sequences"][sequence_id][
            "frames"
        ]
        sequence_pose_ids[sequence_id] = []
        for frame in manifest_frames:
            pose_id = frame["pose_id"]
            image = authored_images[pose_id]
            poses[pose_id] = image
            sequence_pose_ids[sequence_id].append(pose_id)
            rgba_sha256 = hashlib.sha256(image.tobytes()).hexdigest()
            source_provenance = provenance_by_pose[pose_id]
            records.append(
                {
                    "pose_id": pose_id,
                    "motion_slot_id": frame["slot_id"],
                    "sequence_id": sequence_id,
                    "source_frame_index": frame["frame_index"],
                    **source_provenance,
                    "normalization_scale": 1.0,
                    "output_bbox": source_provenance["source_bbox"],
                    "rgba_sha256": rgba_sha256,
                    "approval_state": AUTHORED_APPROVAL_STATE,
                    "runtime_admitted": False,
                }
            )

    if len(poses) != TARGET_POSE_COUNT:
        raise ValueError("authored parity build did not produce 48 poses")
    expected_pose_ids = {
        _expected_pose_id(character_id, number)
        for number in range(1, TARGET_POSE_COUNT + 1)
    }
    if set(poses) != expected_pose_ids:
        raise ValueError("authored parity build has a pose topology mismatch")
    records.sort(key=lambda record: record["pose_id"])

    compiled_dir = output_root / "compiled" / character_id
    compiled_dir.mkdir(parents=True, exist_ok=True)
    artifact_name = f"{character_id}-candidate-authored-parity-v001.wjpose"
    artifact_path = compiled_dir / artifact_name
    temporary_artifact = artifact_path.with_name(
        f".{artifact_name}.{os.getpid()}.tmp"
    )
    receipt = write_pose_artifact(
        temporary_artifact,
        poses,
        profile=profile,
        provenance={
            "asset_set_id": f"{character_id}-authored-parity-v001",
            "character_id": character_id,
            "existing_source_artifact_sha256": existing_manifest["artifact"][
                "sha256"
            ],
            "existing_reconstruction_sha256": existing_manifest_sha256,
            "authority_manifest_sha256": authority_sha256,
            "authored_manifest_sha256": sha256_path(
                authored_manifest_path
            ),
            "approval_state": AUTHORED_APPROVAL_STATE,
            "runtime_admitted": False,
            "reconstruction": "supplied_graph_plus_full_size_authored_rgba_v1",
        },
    )
    temporary_artifact.replace(artifact_path)
    receipt["path"] = artifact_name

    index = _build_library_index(
        character_id=character_id,
        display_name=existing_manifest["display_name"],
        profile=profile,
        artifact_name=artifact_name,
        receipt=receipt,
        sequence_pose_ids=sequence_pose_ids,
        authored_sequences=authored_manifest["sequences"],
    )
    index_path = compiled_dir / "library-index.json"
    index_bytes = _json_bytes(index)
    index_sha256 = hashlib.sha256(index_bytes).hexdigest()

    review_dir = output_root / "source-metadata" / character_id
    contact_sheet_path = review_dir / "parity-motion-contact-sheet-v001.png"
    _build_contact_sheet(poses, records, contact_sheet_path)
    motion_contract_path = review_dir / "review-motion-contract-v001.json"
    motion_contract = _build_review_motion_contract(
        character_id=character_id,
        profile=profile,
        authored_manifest=authored_manifest,
        sequence_pose_ids=sequence_pose_ids,
        artifact_sha256=receipt["sha256"],
        library_index_sha256=index_sha256,
    )
    _write_json_atomic(motion_contract_path, motion_contract)
    try:
        existing_manifest_relative = existing_manifest_path.relative_to(
            output_root
        )
        authored_manifest_relative = authored_manifest_path.relative_to(
            output_root
        )
    except ValueError as error:
        raise ValueError(
            "character manifests must live beneath the parity output root"
        ) from error
    reconstruction = {
        "schema_version": 1,
        "character_id": character_id,
        "display_name": existing_manifest["display_name"],
        "status": AUTHORED_APPROVAL_STATE,
        "runtime_admitted": False,
        "target_pose_count": TARGET_POSE_COUNT,
        "compiled_pose_count": len(poses),
        "missing_sequences": [],
        "authority_manifest_sha256": authority_sha256,
        "existing_reconstruction_manifest": {
            "path": str(existing_manifest_relative),
            "sha256": existing_manifest_sha256,
        },
        "existing_source_artifact": {
            "path": str(existing_artifact_path.relative_to(output_root)),
            "sha256": existing_manifest["artifact"]["sha256"],
        },
        "authored_manifest": {
            "path": str(authored_manifest_relative),
            "sha256": sha256_path(authored_manifest_path),
        },
        "artifact": {
            **receipt,
            "path": str(artifact_path.relative_to(output_root)),
        },
        "library_index": {
            "path": str(index_path.relative_to(output_root)),
            "sha256": index_sha256,
        },
        "review_contact_sheet": {
            "path": str(contact_sheet_path.relative_to(output_root)),
            "sha256": sha256_path(contact_sheet_path),
        },
        "review_motion_contract": {
            "path": str(motion_contract_path.relative_to(output_root)),
            "sha256": sha256_path(motion_contract_path),
        },
        "sequences": sequence_pose_ids,
        "poses": records,
    }
    reconstruction_path = (
        review_dir / "reconstruction-manifest-parity-v001.json"
    )
    _write_json_atomic(reconstruction_path, reconstruction)
    _write_bytes_atomic(index_path, index_bytes)
    return {
        "character_id": character_id,
        "complete": True,
        "pose_count": len(poses),
        "runtime_admitted": False,
        "artifact_path": str(artifact_path),
        "artifact_sha256": receipt["sha256"],
        "library_index_path": str(index_path),
        "library_index_sha256": index_sha256,
        "reconstruction_manifest_path": str(reconstruction_path),
        "contact_sheet_path": str(contact_sheet_path),
        "motion_contract_path": str(motion_contract_path),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge exactly authored full-size JoeVille gap poses with an "
            "immutable supplied-source pixel-graph artifact."
        )
    )
    parser.add_argument("character_id")
    parser.add_argument("authored_manifest", type=Path)
    parser.add_argument("existing_manifest", type=Path)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = build_authored_parity(
        character_id=args.character_id,
        authored_manifest_path=args.authored_manifest,
        existing_manifest_path=args.existing_manifest,
        authority_path=args.authority,
        output_root=args.output_root,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
