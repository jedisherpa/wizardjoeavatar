#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import HDPoseLibrary, write_pose_artifact_from_loader


DEFAULT_INDEX = (
    ROOT / "assets" / "reference" / "hd_canonical" / "compiled" / "library-index.json"
)
DEFAULT_LEDGER = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "wizard-joe"
    / "mouth-pairs-v1"
    / "mouth-state-ledger.json"
)
DEFAULT_OUTPUT = DEFAULT_LEDGER.parent
ARTIFACT_NAME = "candidate-opposite-mouth-variants-v1.wjpose"
PAIR_MANIFEST_NAME = "mouth-pair-manifest.json"
DEFAULT_REVIEW_INDEX = (
    ROOT
    / "assets"
    / "reference"
    / "wizard-joe-mouth-review-library-index.json"
)
MINIMUM_DONOR_CONFIDENCE = 700


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _geometry(record: dict[str, Any]) -> tuple[float, ...]:
    region = record["mouth_region"]
    eyes = record.get("eye_landmarks", [])
    width = region[2] - region[0]
    height = region[3] - region[1]
    if len(eyes) == 2:
        dx = eyes[1][0] - eyes[0][0]
        dy = eyes[1][1] - eyes[0][1]
        eye_span = math.hypot(dx, dy)
        angle = math.atan2(dy, dx)
    elif eyes:
        eye_span = eyes[0][2]
        angle = 0.0
    else:
        eye_span = 0.0
        angle = 0.0
    return (float(len(eyes)), width, height, eye_span, angle)


def _donor_score(target: dict[str, Any], donor: dict[str, Any]) -> float:
    target_geometry = _geometry(target)
    donor_geometry = _geometry(donor)
    return (
        abs(target_geometry[0] - donor_geometry[0]) * 10000
        + abs(target_geometry[1] - donor_geometry[1]) * 5
        + abs(target_geometry[2] - donor_geometry[2]) * 8
        + abs(target_geometry[3] - donor_geometry[3]) * 4
        + abs(target_geometry[4] - donor_geometry[4]) * 500
    )


def select_donor(
    target: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    opposite = "closed" if target["mouth_state"] == "open" else "open"
    candidates = [
        record
        for record in records
        if record["mouth_state"] == opposite
        and record.get("mouth_region")
        and int(record.get("confidence_milli", 0)) >= MINIMUM_DONOR_CONFIDENCE
    ]
    if not candidates:
        raise ValueError(f"no {opposite} mouth donor is available for {target['pose_id']}")
    return min(candidates, key=lambda record: (_donor_score(target, record), record["pose_id"]))


def composite_opposite_mouth(
    target_image: Image.Image,
    target_region: list[int],
    donor_image: Image.Image,
    donor_region: list[int],
) -> Image.Image:
    target = target_image.convert("RGBA")
    donor = donor_image.convert("RGBA").crop(tuple(donor_region))
    width = target_region[2] - target_region[0]
    height = target_region[3] - target_region[1]
    donor = donor.resize((width, height), Image.Resampling.LANCZOS)
    mask = Image.new("L", (width, height), 0)
    inset_x = max(1, round(width * 0.025))
    inset_y = max(1, round(height * 0.04))
    mask.paste(
        255,
        (inset_x, inset_y, width - inset_x, height - inset_y),
    )
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(1, round(min(width, height) * 0.035))))
    result = target.copy()
    result.paste(donor, (target_region[0], target_region[1]), mask)
    return result


def _outside_region_is_identical(
    first: Image.Image,
    second: Image.Image,
    region: list[int],
) -> bool:
    width, height = first.size
    boxes = (
        (0, 0, width, region[1]),
        (0, region[3], width, height),
        (0, region[1], region[0], region[3]),
        (region[2], region[1], width, region[3]),
    )
    return all(first.crop(box).tobytes() == second.crop(box).tobytes() for box in boxes)


def _write_review_index(
    *,
    source_index_path: Path,
    source_index: dict[str, Any],
    artifact_path: Path,
    receipt: dict[str, Any],
    variant_ids: list[str],
    review_index_path: Path,
) -> None:
    review_root = review_index_path.parent.resolve()
    source_root = source_index_path.parent.resolve()
    artifact_path = artifact_path.resolve()
    rewritten_shards = []
    for shard in source_index["shards"]:
        source_shard = (source_root / shard["path"]).resolve()
        try:
            relative_path = source_shard.relative_to(review_root)
        except ValueError as exc:
            raise ValueError(
                "review index must be an ancestor of every source shard"
            ) from exc
        rewritten_shards.append({**shard, "path": relative_path.as_posix()})
    try:
        artifact_relative_path = artifact_path.relative_to(review_root)
    except ValueError as exc:
        raise ValueError(
            "review index must be an ancestor of the mouth-pair artifact"
        ) from exc
    mouth_shard = {
        "shard_id": "wizard_joe_candidate_mouth_opposites_v1",
        "source": "derived_opposite_mouth_candidate",
        "approval_state": "candidate_mouth_pair_review",
        "runtime_admitted": False,
        "path": artifact_relative_path.as_posix(),
        "sha256": receipt["sha256"],
        "bytes": receipt["bytes"],
        "pose_count": receipt["pose_count"],
        "pose_ids": variant_ids,
    }
    review_index = {
        **source_index,
        "asset_set_id": f"{source_index['asset_set_id']}-mouth-review-v1",
        "review_projection": True,
        "runtime_admitted": False,
        "pose_count": int(source_index["pose_count"]) + len(variant_ids),
        "candidate_pose_count": int(source_index.get("candidate_pose_count", 0))
        + len(variant_ids),
        "shards": [*rewritten_shards, mouth_shard],
    }
    review_index_path.parent.mkdir(parents=True, exist_ok=True)
    review_index_path.write_text(
        json.dumps(review_index, indent=2) + "\n",
        encoding="utf-8",
    )


def build_pairs(
    index_path: Path,
    ledger_path: Path,
    output_dir: Path,
    review_index_path: Path = DEFAULT_REVIEW_INDEX,
) -> dict[str, Any]:
    index_path = index_path.resolve()
    ledger_path = ledger_path.resolve()
    output_dir = output_dir.resolve()
    library = HDPoseLibrary(index_path)
    library_index = _read_json(index_path)
    ledger = _read_json(ledger_path)
    records = [
        record
        for record in ledger["poses"]
        if record["mouth_state"] in {"open", "closed"} and record.get("mouth_region")
    ]
    hidden_records = [
        record
        for record in ledger["poses"]
        if record["mouth_state"] == "not_visible"
    ]
    record_by_id = {record["pose_id"]: record for record in records}
    donor_by_id = {
        record["pose_id"]: select_donor(record, records)
        for record in records
    }
    variant_ids = [
        f"{record['pose_id']}__mouth_{'closed' if record['mouth_state'] == 'open' else 'open'}"
        for record in records
    ] + [f"{record['pose_id']}__mouth_open" for record in hidden_records]
    source_by_variant = {
        variant_id: record
        for variant_id, record in zip(variant_ids, [*records, *hidden_records])
    }

    def load_variant(variant_id: str) -> Image.Image:
        record = source_by_variant[variant_id]
        if record["mouth_state"] == "not_visible":
            return library.load_pose(record["pose_id"])
        donor = donor_by_id[record["pose_id"]]
        source_image = library.load_pose(record["pose_id"])
        result = composite_opposite_mouth(
            source_image,
            record["mouth_region"],
            library.load_pose(donor["pose_id"]),
            donor["mouth_region"],
        )
        if not _outside_region_is_identical(source_image, result, record["mouth_region"]):
            raise ValueError(f"mouth edit escaped articulation region for {record['pose_id']}")
        return result

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / ARTIFACT_NAME
    receipt = write_pose_artifact_from_loader(
        artifact_path,
        variant_ids,
        load_pose=load_variant,
        profile=library_index["profile"],
        provenance={
            "character_id": "wizard-joe-v1",
            "source_library_sha256": _sha256_file(index_path),
            "mouth_state_ledger_sha256": _sha256_file(ledger_path),
            "approval_state": "candidate_mouth_pair_review",
            "outside_articulation_region": "byte_identical",
        },
    )
    pairs = []
    for record, variant_id in zip(records, variant_ids):
        donor = donor_by_id[record["pose_id"]]
        original_state = record["mouth_state"]
        opposite_state = "closed" if original_state == "open" else "open"
        pairs.append(
            {
                "base_pose_id": record["pose_id"],
                "mouth_visibility": "visible",
                "audited_source_state": original_state,
                "mouth_region": record["mouth_region"],
                "states": {
                    original_state: {
                        "pose_id": record["pose_id"],
                        "source": "approved_production_alpha",
                    },
                    opposite_state: {
                        "pose_id": variant_id,
                        "source": "derived_opposite_mouth_candidate",
                        "donor_pose_id": donor["pose_id"],
                    },
                },
                "approval_state": "candidate_visual_review",
            }
        )
    for record in hidden_records:
        variant_id = f"{record['pose_id']}__mouth_open"
        pairs.append(
            {
                "base_pose_id": record["pose_id"],
                "mouth_visibility": "not_visible",
                "audited_source_state": "not_visible",
                "mouth_region": None,
                "states": {
                    "closed": {
                        "pose_id": record["pose_id"],
                        "source": "approved_production_alpha",
                    },
                    "open": {
                        "pose_id": variant_id,
                        "source": "derived_nonvisible_mouth_alias",
                    },
                },
                "approval_state": "candidate_visual_review",
            }
        )
    manifest = {
        "schema_version": 1,
        "character_id": "wizard-joe-v1",
        "source_library": index_path.relative_to(ROOT).as_posix(),
        "mouth_state_ledger": ledger_path.relative_to(ROOT).as_posix(),
        "artifact": {
            "path": artifact_path.name,
            "sha256": receipt["sha256"],
            "bytes": receipt["bytes"],
            "pose_count": receipt["pose_count"],
            "approval_state": "candidate_mouth_pair_review",
        },
        "coverage": {
            "approved_pose_count": int(ledger["pose_count"]),
            "paired_pose_count": len(pairs),
            "unpaired_pose_count": int(ledger["pose_count"]) - len(pairs),
        },
        "pairs": pairs,
    }
    manifest_path = output_dir / PAIR_MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    _write_review_index(
        source_index_path=index_path,
        source_index=library_index,
        artifact_path=artifact_path,
        receipt=receipt,
        variant_ids=variant_ids,
        review_index_path=review_index_path.resolve(),
    )
    return {
        "manifest": manifest_path.relative_to(ROOT).as_posix(),
        "artifact": artifact_path.relative_to(ROOT).as_posix(),
        "review_index": review_index_path.resolve().relative_to(ROOT).as_posix(),
        "paired_pose_count": len(pairs),
        "unpaired_pose_count": manifest["coverage"]["unpaired_pose_count"],
        "bytes": receipt["bytes"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build review-gated open/closed mouth pairs for Wizard Joe HD poses."
    )
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review-index", type=Path, default=DEFAULT_REVIEW_INDEX)
    args = parser.parse_args()
    print(
        json.dumps(
            build_pairs(
                args.index,
                args.ledger,
                args.output,
                args.review_index,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
