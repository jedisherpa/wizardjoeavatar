#!/usr/bin/env python3
"""Rebuild the Kingfisher review library from its registered alpha archive."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import zipfile
from collections import OrderedDict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import sha256_path, write_pose_artifact


SHARD_RANGES = (
    ("kingfisher_act_001_025", 1, 25),
    ("kingfisher_act_026_050", 26, 50),
    ("kingfisher_act_051_066", 51, 66),
)
EXPECTED_CHARACTER_ID = "kingfisher"
EXPECTED_DISPLAY_NAME = "Kingfisher"
EXPECTED_RUNTIME_IDS = tuple(range(1, 67))
EXPECTED_RUNTIME_SIZE = (960, 540)
SUPPORTED_PROFILE_POSE_COUNTS = (66, 110)


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _archive_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_archive_frame_metadata(
    metadata: dict[str, object],
    runtime_id: int,
) -> None:
    for field, expected in (
        ("character_id", EXPECTED_CHARACTER_ID),
        ("display_name", EXPECTED_DISPLAY_NAME),
        ("source_pack", EXPECTED_CHARACTER_ID),
    ):
        if field in metadata and metadata[field] != expected:
            raise ValueError(
                f"Kingfisher archive frame {runtime_id} {field} mismatch"
            )

    pose_id = metadata.get("pose_id")
    expected_pose_prefix = (
        f"{EXPECTED_CHARACTER_ID}_{runtime_id:03d}_act{runtime_id:03d}_"
    )
    if pose_id is not None and (
        not isinstance(pose_id, str)
        or not pose_id.startswith(expected_pose_prefix)
    ):
        raise ValueError(
            f"Kingfisher archive frame {runtime_id} pose_id mismatch"
        )

    runtime_size = metadata.get("runtime_size")
    if runtime_size is not None and runtime_size != list(EXPECTED_RUNTIME_SIZE):
        raise ValueError(
            f"Kingfisher archive frame {runtime_id} runtime_size mismatch"
        )


def _filter_base_sequences(
    sequences: object,
    all_pose_ids: list[str],
    base_pose_ids: list[str],
) -> dict[str, dict[str, object]]:
    if not isinstance(sequences, dict):
        raise ValueError("Kingfisher live profile sequences must be an object")

    known_pose_ids = set(all_pose_ids)
    base_pose_id_set = set(base_pose_ids)
    filtered_sequences: dict[str, dict[str, object]] = {}
    for sequence_id, sequence in sequences.items():
        if not isinstance(sequence_id, str) or not sequence_id:
            raise ValueError("Kingfisher sequence ids must be nonempty strings")
        if not isinstance(sequence, dict):
            raise ValueError(
                f"Kingfisher sequence {sequence_id} must be an object"
            )
        sequence_pose_ids = sequence.get("pose_ids")
        if not isinstance(sequence_pose_ids, list) or any(
            not isinstance(pose_id, str) or not pose_id
            for pose_id in sequence_pose_ids
        ):
            raise ValueError(
                f"Kingfisher sequence {sequence_id} pose_ids must be strings"
            )
        unknown_pose_ids = [
            pose_id
            for pose_id in sequence_pose_ids
            if pose_id not in known_pose_ids
        ]
        if unknown_pose_ids:
            raise ValueError(
                f"Kingfisher sequence {sequence_id} references unknown pose id "
                f"{unknown_pose_ids[0]}"
            )
        filtered_pose_ids = [
            pose_id
            for pose_id in sequence_pose_ids
            if pose_id in base_pose_id_set
        ]
        if filtered_pose_ids:
            filtered_sequences[sequence_id] = {
                **sequence,
                "pose_ids": filtered_pose_ids,
            }
    return filtered_sequences


def _validate_live_profile(
    live_profile: object,
) -> tuple[list[str], dict[str, dict[str, object]]]:
    if not isinstance(live_profile, dict):
        raise ValueError("Kingfisher live profile must be a JSON object")
    if live_profile.get("character_id") != EXPECTED_CHARACTER_ID:
        raise ValueError("Kingfisher live profile character_id mismatch")
    if live_profile.get("display_name") != EXPECTED_DISPLAY_NAME:
        raise ValueError("Kingfisher live profile display_name mismatch")

    pose_ids = live_profile.get("pose_ids")
    if not isinstance(pose_ids, list):
        raise ValueError("Kingfisher live profile pose_ids must be a list")
    pose_count = live_profile.get("pose_count")
    if type(pose_count) is not int or pose_count != len(pose_ids):
        raise ValueError(
            "Kingfisher live profile pose_count must match its pose_ids"
        )
    if len(pose_ids) not in SUPPORTED_PROFILE_POSE_COUNTS:
        raise ValueError(
            "Kingfisher live profile must contain either 66 or 110 pose ids"
        )
    for runtime_id, pose_id in enumerate(pose_ids, start=1):
        expected_prefix = f"{EXPECTED_CHARACTER_ID}.act.{runtime_id:03d}."
        if not isinstance(pose_id, str) or not pose_id.startswith(
            expected_prefix
        ):
            raise ValueError(
                "Kingfisher live profile pose ids must be canonical and ordered"
            )
    base_pose_ids = pose_ids[: len(EXPECTED_RUNTIME_IDS)]
    filtered_sequences = _filter_base_sequences(
        live_profile.get("sequences"),
        pose_ids,
        base_pose_ids,
    )
    return base_pose_ids, filtered_sequences


def _load_archive_frames(
    archive_path: Path,
) -> dict[int, tuple[str, Image.Image, dict[str, object]]]:
    frames: dict[int, tuple[str, Image.Image, dict[str, object]]] = {}
    with zipfile.ZipFile(archive_path) as archive:
        meta_members = sorted(
            name
            for name in archive.namelist()
            if not name.startswith("__MACOSX/")
            and name.endswith("/meta.json")
        )
        for meta_member in meta_members:
            metadata = json.loads(archive.read(meta_member).decode("utf-8"))
            if not isinstance(metadata, dict):
                raise ValueError(
                    f"Kingfisher archive metadata {meta_member} must be an object"
                )
            runtime_id = metadata.get("runtime_id")
            if type(runtime_id) is not int:
                raise ValueError(
                    f"Kingfisher archive metadata {meta_member} "
                    "must contain an integer runtime_id"
                )
            if runtime_id in frames:
                raise ValueError(
                    f"Kingfisher archive contains duplicate runtime id "
                    f"{runtime_id}"
                )
            _validate_archive_frame_metadata(metadata, runtime_id)
            directory = meta_member.rsplit("/", 1)[0]
            image_member = f"{directory}/runtime-960x540.png"
            with Image.open(io.BytesIO(archive.read(image_member))) as loaded:
                image = loaded.convert("RGBA")
            if image.size != EXPECTED_RUNTIME_SIZE:
                raise ValueError(
                    f"Kingfisher frame {runtime_id} is not 960 x 540"
                )
            frames[runtime_id] = (image_member, image.copy(), metadata)
    if len(meta_members) != len(EXPECTED_RUNTIME_IDS):
        raise ValueError("Kingfisher archive must contain exactly 66 frames")
    if tuple(sorted(frames)) != EXPECTED_RUNTIME_IDS:
        raise ValueError("Kingfisher archive must contain runtime ids 1 through 66")
    return frames


def recover_library(
    archive_path: Path,
    profile_path: Path,
    output_root: Path,
) -> dict[str, object]:
    archive_path = archive_path.resolve()
    profile_path = profile_path.resolve()
    output_root = output_root.resolve()
    live_profile = json.loads(profile_path.read_text(encoding="utf-8"))
    pose_ids, sequences = _validate_live_profile(live_profile)
    frames = _load_archive_frames(archive_path)
    archive_digest = _archive_sha256(archive_path)

    output_root.mkdir(parents=True, exist_ok=True)
    shard_records = []
    for shard_id, first, last in SHARD_RANGES:
        shard_pose_ids = pose_ids[first - 1 : last]
        poses = OrderedDict(
            (pose_id, frames[runtime_id][1])
            for runtime_id, pose_id in zip(
                range(first, last + 1),
                shard_pose_ids,
            )
        )
        artifact_path = output_root / f"{shard_id}.wjpose"
        receipt = write_pose_artifact(
            artifact_path,
            poses,
            profile=live_profile["profile"],
            provenance={
                "source": "kingfisher_registered_alpha_archive",
                "archive_path": archive_path.name,
                "archive_sha256": archive_digest,
                "runtime_id_range": [first, last],
            },
        )
        shard_records.append(
            {
                "shard_id": shard_id,
                "path": artifact_path.name,
                "sha256": receipt["sha256"],
                "bytes": receipt["bytes"],
                "pose_count": len(shard_pose_ids),
                "pose_ids": shard_pose_ids,
                "approval_state": "candidate_visual_review",
                "review_projection": True,
                "runtime_admitted": False,
                "source": "kingfisher_registered_alpha_source",
            }
        )

    index = {
        "schema_version": 1,
        "asset_set_id": live_profile["asset_set_id"],
        "character_id": live_profile.get("character_id"),
        "display_name": live_profile.get("display_name"),
        "identity_side": live_profile.get("identity_side"),
        "profile": live_profile["profile"],
        "presentation_normalization": live_profile.get(
            "presentation_normalization"
        ),
        "pose_count": len(pose_ids),
        "pose_ids": pose_ids,
        "shards": shard_records,
        "sequences": sequences,
        "review_projection": True,
        "runtime_admitted": False,
        "source_archive": {
            "path": archive_path.name,
            "sha256": archive_digest,
        },
    }
    index_path = output_root / "library-index.json"
    _write_json_atomic(index_path, index)
    return {
        "index_path": index_path.as_posix(),
        "index_sha256": sha256_path(index_path),
        "pose_count": len(pose_ids),
        "shard_count": len(shard_records),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = recover_library(args.archive, args.profile, args.output_root)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
