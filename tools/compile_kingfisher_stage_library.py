#!/usr/bin/env python3
"""Compile the audited Kingfisher stage expansion into its review library."""

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

from wizard_avatar.hd_pose_artifact import (
    HDPoseLibrary,
    sha256_path,
    write_pose_artifact,
)
from wizard_avatar.character_choreography import (
    load_character_choreography_dictionary,
)
from tools.stabilize_kingfisher_stage_pair import (
    validate_articulation_region,
)

BASE_POSE_COUNT = 66
EXPANSION_FIRST_ORDINAL = 67
EXPANSION_LAST_ORDINAL = 110
EXPANSION_SHARD_ID = "kingfisher_act_067_110"
CANVAS_SIZE = (960, 540)
TARGET_BASELINE_Y = 529


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


def _sequence(
    pose_ids: list[str],
    ordinals: list[int],
    *,
    fps: int,
    loop: bool,
) -> dict[str, object]:
    pose_by_ordinal = {
        int(pose_id.split(".")[2]): pose_id
        for pose_id in pose_ids
    }
    return {
        "approval_state": "candidate_visual_review",
        "fps": fps,
        "loop": loop,
        "pose_ids": [pose_by_ordinal[ordinal] for ordinal in ordinals],
        "review_projection": True,
        "runtime_admitted": False,
    }


def _stage_sequences(pose_ids: list[str]) -> dict[str, dict[str, object]]:
    return {
        "kingfisher-stage-center": _sequence(
            pose_ids, [67, 68, 67], fps=4, loop=True
        ),
        "kingfisher-pace-left": _sequence(
            pose_ids,
            [67, 69, 70, 71, 72, 73, 74, 75, 76, 73, 67],
            fps=6,
            loop=True,
        ),
        "kingfisher-pace-right": _sequence(
            pose_ids,
            [67, 77, 78, 79, 80, 81, 82, 83, 84, 81, 67],
            fps=6,
            loop=True,
        ),
        "kingfisher-stage-explain": _sequence(
            pose_ids,
            [67, 68, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 67],
            fps=5,
            loop=True,
        ),
        "kingfisher-stage-story": _sequence(
            pose_ids, list(range(97, 111)), fps=5, loop=True
        ),
        "kingfisher-stage-resolution": _sequence(
            pose_ids, [107, 108, 109, 110, 109, 67], fps=4, loop=True
        ),
        "kingfisher-stage-performance-all": _sequence(
            pose_ids, list(range(67, 111)), fps=5, loop=True
        ),
    }


def _load_plan(
    plan_path: Path,
) -> tuple[
    dict[str, object],
    list[tuple[int, str, str]],
    dict[int, tuple[int, int, int, int]],
]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("character_id") != "kingfisher":
        raise ValueError("stage expansion plan must target Kingfisher")
    if plan.get("runtime_admitted") is not False:
        raise ValueError("stage expansion plan must remain review-only")
    entries = []
    articulation_regions = {}
    for performance_key in plan["performance_keys"]:
        poses = performance_key["poses"]
        if len(poses) != 2:
            raise ValueError("each stage performance key must contain one pair")
        resting_ordinal = int(poses[0]["ordinal"])
        region = validate_articulation_region(
            tuple(performance_key["articulation_region"])
        )
        articulation_regions[resting_ordinal] = region
        for pose in poses:
            ordinal = int(pose["ordinal"])
            slug = str(pose["slug"])
            entries.append(
                (
                    ordinal,
                    slug,
                    f"kingfisher.act.{ordinal:03d}.{slug}",
                )
            )
    entries.sort()
    ordinals = [ordinal for ordinal, _, _ in entries]
    if ordinals != list(
        range(EXPANSION_FIRST_ORDINAL, EXPANSION_LAST_ORDINAL + 1)
    ):
        raise ValueError("stage expansion plan must contain ACT067 through ACT110")
    if sorted(articulation_regions) != list(
        range(EXPANSION_FIRST_ORDINAL, EXPANSION_LAST_ORDINAL + 1, 2)
    ):
        raise ValueError("stage expansion plan articulation regions are incomplete")
    return plan, entries, articulation_regions


def _alpha_path(
    alpha_root: Path,
    entry: tuple[int, str, str],
) -> Path:
    ordinal, slug, _ = entry
    return alpha_root / (
        f"{ordinal:03d}_ACT{ordinal:03d}_"
        f"{slug.replace('-', '_')}_alpha.png"
    )


def _load_stage_poses(
    entries: list[tuple[int, str, str]],
    alpha_root: Path,
) -> OrderedDict[str, Image.Image]:
    poses: OrderedDict[str, Image.Image] = OrderedDict()
    for entry in entries:
        _, _, pose_id = entry
        source_path = _alpha_path(alpha_root, entry)
        with Image.open(source_path) as loaded:
            image = loaded.convert("RGBA")
        if image.size != CANVAS_SIZE:
            raise ValueError(f"{pose_id} must use the 960 x 540 canvas")
        alpha = image.getchannel("A")
        if not set(alpha.getdata()).issubset({0, 255}):
            raise ValueError(f"{pose_id} must use binary alpha")
        bbox = alpha.getbbox()
        if bbox is None or bbox[3] != TARGET_BASELINE_Y:
            raise ValueError(f"{pose_id} baseline is not registered")
        poses[pose_id] = image
    return poses


def _load_pair_audits(
    entries: list[tuple[int, str, str]],
    audit_root: Path,
    alpha_root: Path,
    articulation_regions: dict[int, tuple[int, int, int, int]],
) -> list[dict[str, object]]:
    audits = []
    for index in range(0, len(entries), 2):
        resting_entry = entries[index]
        speaking_entry = entries[index + 1]
        resting = resting_entry[0]
        speaking = speaking_entry[0]
        audit_path = audit_root / f"{resting:03d}_{speaking:03d}_pair.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        if audit.get("schema_version") != 2:
            raise ValueError(
                f"Kingfisher stage pair ACT{resting:03d}/"
                f"ACT{speaking:03d} audit schema is invalid"
            )
        if audit.get("passed") is not True:
            raise ValueError(
                f"Kingfisher stage pair ACT{resting:03d}/ACT{speaking:03d} failed"
            )
        alpha_hashes = {
            "resting_sha256": sha256_path(
                _alpha_path(alpha_root, resting_entry)
            ),
            "speaking_sha256": sha256_path(
                _alpha_path(alpha_root, speaking_entry)
            ),
        }
        for field, expected_sha256 in alpha_hashes.items():
            reported_sha256 = audit.get(field)
            if not isinstance(reported_sha256, str):
                raise ValueError(
                    f"Kingfisher stage pair ACT{resting:03d}/"
                    f"ACT{speaking:03d} audit must include {field}"
                )
            if reported_sha256 != expected_sha256:
                pose_kind = field.removesuffix("_sha256")
                raise ValueError(
                    f"Kingfisher stage pair ACT{resting:03d}/"
                    f"ACT{speaking:03d} {pose_kind} alpha checksum mismatch"
                )
        expected_region = list(articulation_regions[resting])
        if audit.get("mouth_region") != expected_region:
            raise ValueError(
                f"Kingfisher stage pair ACT{resting:03d}/"
                f"ACT{speaking:03d} articulation region mismatch"
            )
        audits.append(
            {
                "resting_ordinal": resting,
                "speaking_ordinal": speaking,
                "path": audit_path.name,
                "sha256": sha256_path(audit_path),
                **alpha_hashes,
                "silhouette_iou": audit["silhouette_iou"],
                "outside_mouth_mean_abs": audit["outside_mouth_mean_abs"],
                "mouth_mean_abs": audit["mouth_mean_abs"],
                "changed_rendered_pixels": audit["changed_rendered_pixels"],
                "mouth_region": expected_region,
            }
        )
    return audits


def _copy_base_shards(
    base_library: HDPoseLibrary,
    base_shards: list[dict[str, object]],
    output_root: Path,
) -> None:
    for shard in base_shards:
        shard_id = str(shard["shard_id"])
        expected_sha256 = str(shard["sha256"])
        source_path = base_library.artifacts[shard_id].path.resolve()
        if sha256_path(source_path) != expected_sha256:
            raise ValueError(f"Kingfisher base shard checksum mismatch: {shard_id}")

        relative_path = Path(str(shard["path"]))
        if relative_path.is_absolute():
            raise ValueError("Kingfisher base shard path must be relative")
        destination_path = (output_root / relative_path).resolve()
        try:
            destination_path.relative_to(output_root)
        except ValueError as exc:
            raise ValueError(
                "Kingfisher base shard path escapes output root"
            ) from exc

        if destination_path != source_path:
            _write_bytes_atomic(destination_path, source_path.read_bytes())
        if sha256_path(destination_path) != expected_sha256:
            raise ValueError(
                f"Copied Kingfisher base shard checksum mismatch: {shard_id}"
            )


def compile_stage_library(
    base_index_path: Path,
    plan_path: Path,
    choreography_path: Path,
    alpha_root: Path,
    audit_root: Path,
    output_root: Path,
) -> dict[str, object]:
    base_index_path = base_index_path.resolve()
    plan_path = plan_path.resolve()
    choreography_path = choreography_path.resolve()
    alpha_root = alpha_root.resolve()
    audit_root = audit_root.resolve()
    output_root = output_root.resolve()
    base_library = HDPoseLibrary(base_index_path)
    if base_library.canvas_size != CANVAS_SIZE:
        raise ValueError("Kingfisher base library must use the 960 x 540 canvas")
    base_index = base_library.index
    base_pose_ids = list(base_index["pose_ids"])[:BASE_POSE_COUNT]
    if len(base_pose_ids) != BASE_POSE_COUNT:
        raise ValueError("Kingfisher base library must contain 66 canonical poses")
    base_shards = [
        shard
        for shard in base_index["shards"]
        if shard["shard_id"] != EXPANSION_SHARD_ID
        and all(pose_id in base_pose_ids for pose_id in shard["pose_ids"])
    ]
    if sum(int(shard["pose_count"]) for shard in base_shards) != BASE_POSE_COUNT:
        raise ValueError("Kingfisher base shard inventory is incomplete")

    plan, entries, articulation_regions = _load_plan(plan_path)
    pair_audits = _load_pair_audits(
        entries,
        audit_root,
        alpha_root,
        articulation_regions,
    )
    stage_poses = _load_stage_poses(entries, alpha_root)
    stage_pose_ids = list(stage_poses)
    combined_pose_ids = base_pose_ids + stage_pose_ids
    choreography = load_character_choreography_dictionary(
        choreography_path,
        character_id="kingfisher",
        pose_ids=set(combined_pose_ids),
        action_ids=set(),
        clip_ids=set(),
    )
    output_root.mkdir(parents=True, exist_ok=True)
    _copy_base_shards(base_library, base_shards, output_root)
    compiled_choreography_path = output_root / choreography_path.name
    if compiled_choreography_path.resolve() != choreography_path:
        _write_bytes_atomic(
            compiled_choreography_path,
            choreography_path.read_bytes(),
        )

    artifact_path = output_root / f"{EXPANSION_SHARD_ID}.wjpose"
    artifact_receipt = write_pose_artifact(
        artifact_path,
        stage_poses,
        profile=base_index["profile"],
        provenance={
            "source": "kingfisher_stage_performance_expansion_v1",
            "plan_path": plan_path.name,
            "plan_sha256": sha256_path(plan_path),
            "pair_audit_sha256": [audit["sha256"] for audit in pair_audits],
            "ordinal_range": [
                EXPANSION_FIRST_ORDINAL,
                EXPANSION_LAST_ORDINAL,
            ],
        },
    )

    stage_shard = {
        "shard_id": EXPANSION_SHARD_ID,
        "path": artifact_path.name,
        "sha256": artifact_receipt["sha256"],
        "bytes": artifact_receipt["bytes"],
        "pose_count": len(stage_pose_ids),
        "pose_ids": stage_pose_ids,
        "approval_state": "candidate_visual_review",
        "review_projection": True,
        "runtime_admitted": False,
        "source": "kingfisher_stage_performance_expansion_v1",
    }

    sequences = dict(base_index["sequences"])
    sequences["kingfisher-all"] = {
        "approval_state": "candidate_visual_review",
        "fps": 6,
        "loop": True,
        "pose_ids": combined_pose_ids,
        "review_projection": True,
        "runtime_admitted": False,
    }
    sequences.update(_stage_sequences(combined_pose_ids))

    output_index = {
        **base_index,
        "asset_set_id": "kingfisher-registered-alpha-110-stage-v001",
        "pose_count": len(combined_pose_ids),
        "pose_ids": combined_pose_ids,
        "shards": base_shards + [stage_shard],
        "sequences": sequences,
        "stage_expansion": {
            "expansion_id": plan["expansion_id"],
            "approval_state": "candidate_visual_review",
            "review_projection": True,
            "runtime_admitted": False,
            "pose_count": len(stage_pose_ids),
            "pair_count": len(pair_audits),
            "plan_path": plan_path.name,
            "plan_sha256": sha256_path(plan_path),
            "pair_audits": pair_audits,
        },
        "choreography_dictionary": {
            "path": compiled_choreography_path.name,
            "sha256": sha256_path(compiled_choreography_path),
            "dictionary_id": choreography.dictionary_id,
            "library_class": choreography.library_class,
            "review_projection": True,
            "runtime_admitted": False,
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
        "pose_count": len(combined_pose_ids),
        "pair_count": len(pair_audits),
        "sequence_count": len(sequences),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile the audited 44-pose Kingfisher stage expansion."
    )
    parser.add_argument("--base-index", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--choreography", type=Path, required=True)
    parser.add_argument("--alpha-root", type=Path, required=True)
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = compile_stage_library(
        args.base_index,
        args.plan,
        args.choreography,
        args.alpha_root,
        args.audit_root,
        args.output_root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
