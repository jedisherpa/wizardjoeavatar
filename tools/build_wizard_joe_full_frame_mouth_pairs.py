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
    if candidate.size == canonical.size:
        return candidate.copy()
    candidate_bbox = candidate.getchannel("A").getbbox()
    canonical_bbox = canonical.getchannel("A").getbbox()
    if candidate_bbox is None or canonical_bbox is None:
        raise ValueError("candidate and canonical frames must contain visible pixels")
    subject = candidate.crop(candidate_bbox)
    canonical_width = canonical_bbox[2] - canonical_bbox[0]
    canonical_height = canonical_bbox[3] - canonical_bbox[1]
    scale = min(canonical_width / subject.width, canonical_height / subject.height)
    size = (
        max(1, round(subject.width * scale)),
        max(1, round(subject.height * scale)),
    )
    subject = subject.resize(size, Image.Resampling.LANCZOS)
    center_x = (canonical_bbox[0] + canonical_bbox[2]) / 2
    center_y = (canonical_bbox[1] + canonical_bbox[3]) / 2
    position = (
        round(center_x - subject.width / 2),
        round(center_y - subject.height / 2),
    )
    canvas = Image.new("RGBA", canonical.size, (0, 0, 0, 0))
    canvas.alpha_composite(subject, position)
    return canvas


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
    for source_path in source_paths:
        base_pose_id = source_path.stem.removesuffix("__mouth_closed")
        if base_pose_id not in library.pose_ids:
            raise ValueError(f"unknown canonical pose: {base_pose_id}")
        variant_id = f"{base_pose_id}__mouth_closed_full_frame_v2"
        normalized = normalize_to_canonical_canvas(
            remove_chroma(Image.open(source_path)),
            library.load_pose(base_pose_id),
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
    pair_by_id = {pair["base_pose_id"]: pair for pair in manifest["pairs"]}
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
