#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import HDPoseLibrary, write_pose_artifact


BASE_INDEX = ROOT / "assets/reference/hd_canonical/compiled/library-index.json"
LEGACY_REVIEW_INDEX = ROOT / "assets/reference/wizard-joe-mouth-review-library-index.json"
LEGACY_MANIFEST = (
    ROOT
    / "assets/reference/characters/wizard-joe/mouth-pairs-v1/mouth-pair-manifest.json"
)
OUTPUT_DIR = ROOT / "assets/reference/characters/wizard-joe/mouth-pairs-full-frame-v2"
SOURCE_DIR = OUTPUT_DIR / "source-chroma"
ALPHA_DIR = OUTPUT_DIR / "processed-alpha"
ARTIFACT_PATH = OUTPUT_DIR / "full-frame-closed-mouth-candidates-v2.wjpose"
MANIFEST_PATH = OUTPUT_DIR / "mouth-pair-manifest.json"
REVIEW_INDEX_PATH = (
    ROOT / "assets/reference/wizard-joe-mouth-full-frame-review-library-index.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remove_chroma(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    rgba = Image.new("RGBA", rgb.size)
    output: list[tuple[int, int, int, int]] = []
    for red, green, blue in rgb.getdata():
        chroma_dominant = green > red * 1.7 and green > blue * 1.7
        alpha = 0 if chroma_dominant and green > 170 else 255
        output.append((red, green, blue, alpha))
    rgba.putdata(output)
    rgba.putalpha(rgba.getchannel("A").filter(ImageFilter.MinFilter(3)))
    return rgba


def normalize_to_canonical_canvas(
    candidate: Image.Image,
    canonical: Image.Image,
) -> Image.Image:
    candidate_bbox = candidate.getchannel("A").getbbox()
    canonical_bbox = canonical.getchannel("A").getbbox()
    if candidate_bbox is None or canonical_bbox is None:
        raise ValueError("candidate and canonical frames must contain visible pixels")
    subject = candidate.crop(candidate_bbox)
    canonical_width = canonical_bbox[2] - canonical_bbox[0]
    canonical_height = canonical_bbox[3] - canonical_bbox[1]
    subject = subject.resize(
        (canonical_width, canonical_height),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", canonical.size, (0, 0, 0, 0))
    canvas.alpha_composite(subject, (canonical_bbox[0], canonical_bbox[1]))
    return canvas


def composite_registered_mouth(
    canonical: Image.Image,
    registered_candidate: Image.Image,
    mouth_region: list[int],
) -> Image.Image:
    target = canonical.convert("RGBA")
    source = registered_candidate.convert("RGBA")
    left, top, right, bottom = mouth_region
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        raise ValueError("mouth region must have positive dimensions")
    donor = source.crop((left, top, right, bottom))
    mask = Image.new("L", (width, height), 0)
    inset_x = max(1, round(width * 0.025))
    inset_y = max(1, round(height * 0.04))
    mask.paste(255, (inset_x, inset_y, width - inset_x, height - inset_y))
    mask = mask.filter(
        ImageFilter.GaussianBlur(radius=max(1, round(min(width, height) * 0.035)))
    )
    result = target.copy()
    result.paste(donor, (left, top), mask)
    return result


def outside_region_is_identical(
    first: Image.Image,
    second: Image.Image,
    region: list[int],
) -> bool:
    width, height = first.size
    left, top, right, bottom = region
    boxes = (
        (0, 0, width, top),
        (0, bottom, width, height),
        (0, top, left, bottom),
        (right, top, width, bottom),
    )
    return all(first.crop(box).tobytes() == second.crop(box).tobytes() for box in boxes)


def build() -> dict[str, Any]:
    base_index = _read_json(BASE_INDEX)
    review_index = _read_json(LEGACY_REVIEW_INDEX)
    manifest = _read_json(LEGACY_MANIFEST)
    library = HDPoseLibrary(BASE_INDEX)
    source_paths = sorted(SOURCE_DIR.glob("*__mouth_closed.png"))
    if not source_paths:
        raise ValueError(f"no full-frame mouth candidates found in {SOURCE_DIR}")

    ALPHA_DIR.mkdir(parents=True, exist_ok=True)
    poses: dict[str, Image.Image] = {}
    source_records: dict[str, dict[str, Any]] = {}
    pair_by_id = {pair["base_pose_id"]: pair for pair in manifest["pairs"]}
    for source_path in source_paths:
        base_pose_id = source_path.stem.removesuffix("__mouth_closed")
        if base_pose_id not in library.pose_ids:
            raise ValueError(f"unknown canonical pose: {base_pose_id}")
        variant_id = f"{base_pose_id}__mouth_closed_full_frame_v2"
        canonical = library.load_pose(base_pose_id)
        registered_candidate = normalize_to_canonical_canvas(
            remove_chroma(Image.open(source_path)),
            canonical,
        )
        mouth_region = pair_by_id[base_pose_id]["mouth_region"]
        normalized = composite_registered_mouth(
            canonical,
            registered_candidate,
            mouth_region,
        )
        if not outside_region_is_identical(canonical, normalized, mouth_region):
            raise ValueError(
                f"{variant_id} changed pixels outside its articulation region"
            )
        canonical_bbox = canonical.getchannel("A").getbbox()
        registered_bbox = normalized.getchannel("A").getbbox()
        if registered_bbox != canonical_bbox:
            raise ValueError(
                f"{variant_id} registration mismatch: "
                f"{registered_bbox} != {canonical_bbox}"
            )
        alpha_path = ALPHA_DIR / f"{variant_id}.png"
        normalized.save(alpha_path, "PNG", optimize=True)
        poses[variant_id] = normalized
        source_records[base_pose_id] = {
            "pose_id": variant_id,
            "source": "generated_full_frame_candidate",
            "source_chroma": source_path.relative_to(ROOT).as_posix(),
            "source_sha256": _sha256(source_path),
            "alpha_path": alpha_path.relative_to(ROOT).as_posix(),
            "alpha_sha256": _sha256(alpha_path),
            "registration": {
                "method": "canonical_frame_with_registered_generated_mouth",
                "canonical_bbox": list(canonical_bbox),
                "registered_bbox": list(registered_bbox),
                "mouth_region": list(mouth_region),
                "outside_mouth_region": "byte_identical",
                "status": "pass",
            },
            "frame_construction": (
                "complete canonical frame with build-time registered generated "
                "mouth transfer"
            ),
            "approval_state": "candidate_visual_review",
        }

    receipt = write_pose_artifact(
        ARTIFACT_PATH,
        poses,
        profile=base_index["profile"],
        provenance={
            "character_id": "wizard-joe-v1",
            "source": "full_frame_generated_mouth_alternates",
            "approval_state": "candidate_visual_review",
            "runtime_admitted": False,
        },
    )
    for base_pose_id, state in source_records.items():
        pair = pair_by_id[base_pose_id]
        pair["states"]["closed"] = state
        pair["approval_state"] = "candidate_visual_review"
    manifest["schema_version"] = 2
    manifest["program_id"] = "wizard-joe-full-frame-mouth-pairs-v2"
    manifest["full_frame_artifact"] = {
        "path": ARTIFACT_PATH.relative_to(OUTPUT_DIR).as_posix(),
        "sha256": receipt["sha256"],
        "bytes": receipt["bytes"],
        "pose_count": receipt["pose_count"],
        "approval_state": "candidate_visual_review",
        "runtime_admitted": False,
        "registration_gate": {
            "method": "canonical_frame_with_registered_generated_mouth",
            "passed_pose_count": len(poses),
            "failed_pose_count": 0,
            "outside_mouth_region": "byte_identical",
        },
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    artifact_relative = ARTIFACT_PATH.relative_to(REVIEW_INDEX_PATH.parent)
    shard = {
        "shard_id": "wizard_joe_full_frame_closed_mouth_v2",
        "source": "generated_full_frame_mouth_alternates",
        "approval_state": "candidate_visual_review",
        "runtime_admitted": False,
        "path": artifact_relative.as_posix(),
        "sha256": receipt["sha256"],
        "bytes": receipt["bytes"],
        "pose_count": receipt["pose_count"],
        "pose_ids": receipt["pose_ids"],
    }
    review_index["asset_set_id"] = "wizard-joe-mouth-full-frame-review-v2"
    review_index["pose_count"] = int(review_index["pose_count"]) + len(poses)
    review_index["candidate_pose_count"] = (
        int(review_index.get("candidate_pose_count", 0)) + len(poses)
    )
    review_index["shards"] = [*review_index["shards"], shard]
    REVIEW_INDEX_PATH.write_text(
        json.dumps(review_index, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "artifact": ARTIFACT_PATH.relative_to(ROOT).as_posix(),
        "manifest": MANIFEST_PATH.relative_to(ROOT).as_posix(),
        "review_index": REVIEW_INDEX_PATH.relative_to(ROOT).as_posix(),
        "pose_count": len(poses),
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
