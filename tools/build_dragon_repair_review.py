#!/usr/bin/env python3
"""Compile the incomplete Dragon source set for isolated HD repair review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import (  # noqa: E402
    HDPoseLibrary,
    sha256_path,
    write_pose_artifact_from_loader,
)

DEFAULT_SOURCE_MANIFEST = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "dragon"
    / "source"
    / "source-manifest-v001.json"
)
DEFAULT_REPAIR_MANIFEST = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "dragon"
    / "source-repair"
    / "repair-intake-manifest-v001.json"
)
DEFAULT_INTERIM_MANIFEST = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "dragon"
    / "interim-v001"
    / "interim-candidate-manifest-v001.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "dragon"
    / "compiled"
    / "repair-review"
)
CANVAS_SIZE = (1920, 1080)
SHARD_SIZE = 24
PROFILE = {
    "profile_id": "dragon_drg001_hd_alpha_repair_review_v001",
    "canvas_width": CANVAS_SIZE[0],
    "canvas_height": CANVAS_SIZE[1],
    "color_space": "sRGB",
    "alpha_mode": "binary_straight",
    "coordinate_policy": "preserve_source_canvas",
}
CANONICAL_PATTERN = re.compile(
    r"^CAN(?P<ordinal>\d{3})_DRG001_(?P<slug>[a-z0-9_]+)_v001_alpha\.png$"
)
ACTION_PATTERN = re.compile(
    r"^(?P<ordinal>\d{3})_ACT(?P=ordinal)_(?P<slug>[a-z0-9_]+)_alpha\.png$"
)


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as destination:
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _pose_fields(filename: str) -> tuple[str, int, str]:
    match = CANONICAL_PATTERN.fullmatch(filename)
    if match is not None:
        return "CAN", int(match.group("ordinal")), match.group("slug")
    match = ACTION_PATTERN.fullmatch(filename)
    if match is not None:
        return "ACT", int(match.group("ordinal")), match.group("slug")
    raise ValueError(f"unsupported Dragon source filename: {filename}")


def _pose_id(filename: str) -> str:
    family, ordinal, slug = _pose_fields(filename)
    return "dragon.{}.{:03d}.{}".format(
        family.lower(),
        ordinal,
        slug.replace("_", "-"),
    )


def _image_bytes(path: Path) -> bytes:
    with Image.open(path) as image:
        image.load()
        if image.mode != "RGBA" or image.size != CANVAS_SIZE:
            raise ValueError(f"invalid Dragon review image: {path.name}")
        return image.tobytes()


def _load_pose_image(path: Path) -> Image.Image:
    with Image.open(path) as image:
        image.load()
        return image.convert("RGBA")


def _chunks(records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    return [
        records[index : index + SHARD_SIZE]
        for index in range(0, len(records), SHARD_SIZE)
    ]


def _review_records(
    source_manifest_path: Path,
    repair_manifest_path: Path,
    interim_manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    source = _read_json(source_manifest_path)
    repair = _read_json(repair_manifest_path)
    interim = _read_json(interim_manifest_path)
    if source.get("runtime_admitted") is not False:
        raise ValueError("Dragon source must remain runtime_admitted=false")
    if repair.get("approval_state") != "source_repair_incomplete":
        raise ValueError("Dragon repair intake must remain incomplete")
    if repair.get("runtime_admitted") is not False:
        raise ValueError("Dragon repair intake must remain runtime_admitted=false")
    if repair.get("complete_replacement_inventory") is not False:
        raise ValueError("complete Dragon repair inventory requires a new admission path")
    if interim.get("approval_state") != "candidate_inventory_complete":
        raise ValueError("Dragon interim candidate inventory must be complete")
    if interim.get("candidate_count") != 48:
        raise ValueError("Dragon interim review requires exactly 48 candidates")
    if interim.get("runtime_admitted") is not False:
        raise ValueError("Dragon interim candidates must remain runtime_admitted=false")

    source_root = source_manifest_path.parent
    by_id = {record["asset_id"]: record for record in source["assets"]}
    repair_by_id = {record["asset_id"]: record for record in repair["assets"]}
    records: list[dict[str, Any]] = []
    for asset_id in sorted(
        by_id,
        key=lambda value: (0 if value.startswith("CAN") else 1, int(value[-3:])),
    ):
        source_record = by_id[asset_id]
        if source_record["status"] == "validated_source":
            path = source_root / source_record["path"]
            records.append(
                {
                    "asset_id": asset_id,
                    "filename": source_record["filename"],
                    "path": path,
                    "source_sha256": source_record["sha256"],
                    "source_bbox": source_record["image_audit"]["visible_bbox"],
                    "source_state": "validated_source",
                    "replacement_approval": "not_required",
                }
            )
            continue
        repair_record = repair_by_id[asset_id]
        candidate = repair_record.get("candidate")
        if candidate is None:
            continue
        path = ROOT / candidate["path"]
        records.append(
            {
                "asset_id": asset_id,
                "filename": source_record["filename"],
                "path": path,
                "source_sha256": candidate["sha256"],
                "source_bbox": candidate["image_audit"]["visible_bbox"],
                "source_state": "replacement_candidate_unapproved",
                "replacement_approval": repair_record["replacement_approval"],
                "opaque_pixel_delta": candidate["opaque_pixel_delta"],
            }
        )
    existing_ids = {record["asset_id"] for record in records}
    for candidate in interim["assets"]:
        asset_id = candidate["asset_id"]
        if asset_id in existing_ids:
            raise ValueError(f"duplicate Dragon interim asset: {asset_id}")
        path = ROOT / candidate["path"]
        records.append(
            {
                "asset_id": asset_id,
                "filename": candidate["filename"],
                "path": path,
                "source_sha256": candidate["sha256"],
                "source_bbox": candidate["image_audit"]["visible_bbox"],
                "source_state": "interim_candidate_unapproved",
                "replacement_approval": "not_approved",
                "candidate_method": candidate["method"],
            }
        )
        existing_ids.add(asset_id)
    records.sort(
        key=lambda record: (
            0 if record["asset_id"].startswith("CAN") else 1,
            int(record["asset_id"][-3:]),
        )
    )
    return source, repair, interim, records


def build_dragon_repair_review(
    *,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
    repair_manifest_path: Path = DEFAULT_REPAIR_MANIFEST,
    interim_manifest_path: Path = DEFAULT_INTERIM_MANIFEST,
    output_dir: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    source, repair, interim, records = _review_records(
        source_manifest_path,
        repair_manifest_path,
        interim_manifest_path,
    )
    if len(records) != 134:
        raise ValueError(f"Dragon interim review expected 134 poses, found {len(records)}")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    pose_catalog = []
    for record in records:
        family, ordinal, slug = _pose_fields(record["filename"])
        pose_catalog.append(
            {
                "pose_id": _pose_id(record["filename"]),
                "asset_id": record["asset_id"],
                "ordinal": ordinal,
                "family": family,
                "slug": slug,
                "source_path": record["path"].resolve().relative_to(ROOT).as_posix(),
                "source_sha256": record["source_sha256"],
                "source_bbox": record["source_bbox"],
                "source_state": record["source_state"],
                "replacement_approval": record["replacement_approval"],
                **(
                    {"candidate_method": record["candidate_method"]}
                    if "candidate_method" in record
                    else {}
                ),
                **(
                    {"opaque_pixel_delta": record["opaque_pixel_delta"]}
                    if "opaque_pixel_delta" in record
                    else {}
                ),
            }
        )

    shards = []
    for chunk_index, chunk in enumerate(_chunks(records), start=1):
        pose_records = {_pose_id(record["filename"]): record for record in chunk}
        first_id = chunk[0]["asset_id"].lower()
        last_id = chunk[-1]["asset_id"].lower()
        shard_id = f"dragon_repair_{chunk_index:02d}_{first_id}_{last_id}"
        path = output_dir / f"{shard_id}.wjpose"
        provenance = {
            "schema_version": 1,
            "character_id": "dragon",
            "display_name": "Dragon",
            "asset_set_id": "dragon-drg001-repair-review-v001",
            "source_manifest_sha256": sha256_path(source_manifest_path),
            "repair_manifest_sha256": sha256_path(repair_manifest_path),
            "interim_manifest_sha256": sha256_path(interim_manifest_path),
            "coordinate_policy": "preserve_source_canvas",
            "approval_state": "incomplete_source_repair_review",
            "review_projection": True,
            "runtime_admitted": False,
        }
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            receipt = write_pose_artifact_from_loader(
                temporary,
                pose_records,
                load_pose=lambda pose_id: _load_pose_image(
                    pose_records[pose_id]["path"]
                ),
                profile=PROFILE,
                provenance=provenance,
            )
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        shards.append(
            {
                "shard_id": shard_id,
                "path": path.name,
                "sha256": sha256_path(path),
                "bytes": path.stat().st_size,
                "pose_count": receipt["pose_count"],
                "pose_ids": receipt["pose_ids"],
                "source": "dragon_source_repair_intake",
                "approval_state": "incomplete_source_repair_review",
                "review_projection": True,
                "runtime_admitted": False,
            }
        )

    pose_ids = [record["pose_id"] for record in pose_catalog]

    def pose_range(family: str, start: int, end: int) -> list[str]:
        return [
            record["pose_id"]
            for record in pose_catalog
            if record["family"] == family and start <= record["ordinal"] <= end
        ]

    def review_sequence(fps: int, sequence_pose_ids: list[str]) -> dict[str, Any]:
        if not sequence_pose_ids:
            raise ValueError("Dragon review sequence must contain at least one pose")
        return {
            "fps": fps,
            "loop": True,
            "pose_ids": sequence_pose_ids,
            "approval_state": "incomplete_source_repair_review",
            "review_projection": True,
            "runtime_admitted": False,
        }

    missing_ids: list[str] = []
    candidate_ids = repair["candidate_asset_ids"] + [
        record["asset_id"] for record in interim["assets"]
    ]
    acceptance = {
        "schema_version": 1,
        "character_id": "dragon",
        "asset_set_id": "dragon-drg001-repair-review-v001",
        "approval_state": "blocked_incomplete_source",
        "review_projection": True,
        "runtime_admitted": False,
        "present_pose_count": len(pose_ids),
        "validated_source_pose_count": 84,
        "replacement_candidate_pose_count": len(candidate_ids),
        "missing_pose_count": 0,
        "replacement_candidate_asset_ids": candidate_ids,
        "missing_asset_ids": missing_ids,
        "runtime_admission_recommendation": "blocked",
        "blocking_reasons": [
            "all 50 replacement and interim candidates require explicit approval",
            "the 134-pose interim review does not replace the deferred full Dragon corpus",
            "motion anchors, semantic transitions, rights, and governance admission are not closed",
        ],
    }
    acceptance_path = output_dir / "repair-review-acceptance-audit.json"
    _write_atomic(acceptance_path, _json_bytes(acceptance))

    index = {
        "schema_version": 1,
        "character_id": "dragon",
        "display_name": "Dragon",
        "asset_set_id": "dragon-drg001-repair-review-v001",
        "source_asset_set_id": source["asset_set_id"],
        "source_manifest_sha256": sha256_path(source_manifest_path),
        "repair_manifest_sha256": sha256_path(repair_manifest_path),
        "interim_manifest_sha256": sha256_path(interim_manifest_path),
        "payload_encoding": "rgba8-zlib",
        "profile": PROFILE,
        "pose_count": len(pose_ids),
        "approved_pose_count": 0,
        "validated_source_pose_count": 84,
        "candidate_pose_count": len(candidate_ids),
        "missing_pose_count": 0,
        "missing_asset_ids": missing_ids,
        "approval_state": "incomplete_source_repair_review",
        "review_projection": True,
        "runtime_admitted": False,
        "repair_review_acceptance_audit": {
            "path": acceptance_path.name,
            "sha256": sha256_path(acceptance_path),
            "runtime_admission_recommendation": "blocked",
        },
        "shards": shards,
        "sequences": {
            "dragon-repair-review": review_sequence(4, pose_ids),
            "dragon-flight-review": review_sequence(
                6, pose_range("ACT", 82, 84) + pose_range("ACT", 88, 99)
            ),
            "dragon-ground-speech-review": review_sequence(
                4, pose_range("ACT", 85, 87)
            ),
            "dragon-hover-speech-review": review_sequence(
                5, pose_range("ACT", 95, 99)
            ),
            "dragon-storytelling-review": review_sequence(
                4, pose_range("ACT", 100, 123)
            ),
        },
        "poses": pose_catalog,
        "review_guidance": {
            "acceptance_surface": "live_full_resolution_observer",
            "incomplete_inventory_visible": True,
            "runtime_admission_requires_complete_repair_and_separate_approval": True,
        },
    }
    index_path = output_dir / "library-index.json"
    _write_atomic(index_path, _json_bytes(index))
    library = HDPoseLibrary(index_path)
    if len(library.pose_ids) != 134 or library.canvas_size != CANVAS_SIZE:
        raise ValueError("Dragon repair review failed load verification")
    for record in records:
        pose_id = _pose_id(record["filename"])
        if hashlib.sha256(library.load_rgba(pose_id)).hexdigest() != hashlib.sha256(
            _image_bytes(record["path"])
        ).hexdigest():
            raise ValueError(f"Dragon review payload mismatch: {pose_id}")

    receipt = {
        "schema_version": 1,
        "character_id": "dragon",
        "asset_set_id": index["asset_set_id"],
        "source_manifest_sha256": index["source_manifest_sha256"],
        "repair_manifest_sha256": index["repair_manifest_sha256"],
        "pose_count": len(pose_ids),
        "missing_asset_ids": missing_ids,
        "review_projection": True,
        "runtime_admitted": False,
        "library_index": {
            "path": "library-index.json",
            "sha256": sha256_path(index_path),
        },
        "repair_review_acceptance_audit": index[
            "repair_review_acceptance_audit"
        ],
        "shards": shards,
    }
    _write_atomic(output_dir / "build-receipt.json", _json_bytes(receipt))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile the incomplete Dragon source for isolated repair review."
    )
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--repair-manifest", type=Path, default=DEFAULT_REPAIR_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = build_dragon_repair_review(
        source_manifest_path=args.source_manifest,
        repair_manifest_path=args.repair_manifest,
        output_dir=args.output,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "pose_count": receipt["pose_count"],
                "missing_asset_ids": receipt["missing_asset_ids"],
                "runtime_admitted": receipt["runtime_admitted"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
