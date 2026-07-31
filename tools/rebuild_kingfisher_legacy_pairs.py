#!/usr/bin/env python3
"""Rebuild legacy Kingfisher poses as registered resting/speaking pairs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_kingfisher_stage_pair import audit_pair
from wizard_avatar.hd_pose_artifact import HDPoseLibrary

CANVAS_SIZE = (960, 540)
TARGET_BASELINE_Y = 529
TARGET_BODY_CORE_HEIGHT = 432
LEGACY_BODY_CORE_HEIGHT = 442
MAX_VISIBLE_WIDTH = 900
MAX_LEGACY_ARTICULATION_WIDTH = 220
MAX_LEGACY_ARTICULATION_HEIGHT = 190
MAX_LEGACY_REGISTRATION_BOUND_DELTA = 8
LEGACY_POSE_COUNT = 66
SPEAKING_FIRST_ORDINAL = 111


@dataclass(frozen=True)
class FaceFeature:
    center_x: float
    center_y: float
    width: int
    height: int
    direction: float


@dataclass(frozen=True)
class DonorPair:
    resting_ordinal: int
    resting: Image.Image
    speaking: Image.Image
    feature: FaceFeature
    difference_mask: Image.Image
    articulation_region: tuple[int, int, int, int]


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _save_png_atomic(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        image.save(temporary, format="PNG", optimize=True)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _binary_alpha(image: Image.Image) -> Image.Image:
    result = image.convert("RGBA")
    result.putalpha(
        result.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    )
    return result


def _normalize_registration(
    image: Image.Image,
    *,
    source_body_core_height: int,
) -> tuple[Image.Image, dict[str, object]]:
    image = image.convert("RGBA")
    source_bbox = image.getchannel("A").getbbox()
    if source_bbox is None:
        raise ValueError("Kingfisher source pose cannot be empty")
    source_width = source_bbox[2] - source_bbox[0]
    scale = TARGET_BODY_CORE_HEIGHT / source_body_core_height
    scale = min(scale, MAX_VISIBLE_WIDTH / source_width)
    crop = image.crop(source_bbox)
    target_size = (
        max(1, round(crop.width * scale)),
        max(1, round(crop.height * scale)),
    )
    crop = crop.resize(target_size, Image.Resampling.LANCZOS)
    crop = _binary_alpha(crop)
    target_x = round(CANVAS_SIZE[0] / 2 - crop.width / 2)
    target_y = TARGET_BASELINE_Y - crop.height
    if (
        target_x < 0
        or target_y < 0
        or target_x + crop.width > CANVAS_SIZE[0]
        or target_y + crop.height > CANVAS_SIZE[1]
    ):
        raise ValueError("normalized Kingfisher pose would crop the silhouette")
    output = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    output.alpha_composite(crop, (target_x, target_y))
    output_bbox = output.getchannel("A").getbbox()
    if output_bbox is None:
        raise ValueError("normalized Kingfisher pose cannot be empty")
    return output, {
        "source_bbox": list(source_bbox),
        "normalized_bbox": list(output_bbox),
        "scale": round(scale, 8),
        "target_center_x": CANVAS_SIZE[0] // 2,
        "target_baseline_y": TARGET_BASELINE_Y,
        "target_body_core_height": TARGET_BODY_CORE_HEIGHT,
        "source_body_core_height": source_body_core_height,
        "interpolation": "lanczos_rgb_binary_alpha",
    }


def _connected_components(mask: np.ndarray) -> Iterable[list[tuple[int, int]]]:
    height, width = mask.shape
    seen = np.zeros(mask.shape, dtype=bool)
    for y, x in zip(*np.where(mask)):
        if seen[y, x]:
            continue
        stack = [(int(y), int(x))]
        seen[y, x] = True
        component: list[tuple[int, int]] = []
        while stack:
            current_y, current_x = stack.pop()
            component.append((current_y, current_x))
            for next_y, next_x in (
                (current_y - 1, current_x),
                (current_y + 1, current_x),
                (current_y, current_x - 1),
                (current_y, current_x + 1),
            ):
                if (
                    0 <= next_y < height
                    and 0 <= next_x < width
                    and mask[next_y, next_x]
                    and not seen[next_y, next_x]
                ):
                    seen[next_y, next_x] = True
                    stack.append((next_y, next_x))
        yield component


def _face_feature(image: Image.Image) -> FaceFeature | None:
    pixels = np.asarray(image.convert("RGBA"))
    red = pixels[:, :, 0].astype(np.int16)
    green = pixels[:, :, 1].astype(np.int16)
    blue = pixels[:, :, 2].astype(np.int16)
    alpha = pixels[:, :, 3]
    y_grid, x_grid = np.indices(alpha.shape)
    light_throat = (
        (alpha > 0)
        & (y_grid < 360)
        & (red > 115)
        & (green > 105)
        & (blue > 90)
        & ((red - blue) < 105)
    )
    components = list(_connected_components(light_throat))
    if not components:
        return None
    component = max(components, key=len)
    if len(component) < 250:
        return None
    component_y = np.asarray([point[0] for point in component])
    component_x = np.asarray([point[1] for point in component])
    center_x = float(component_x.mean())
    center_y = float(component_y.mean())
    width = int(component_x.max() - component_x.min() + 1)
    height = int(component_y.max() - component_y.min() + 1)

    dark_beak = (
        (alpha > 0)
        & (red < 85)
        & (green < 85)
        & (blue < 85)
        & (y_grid >= center_y - 70)
        & (y_grid <= center_y + 5)
        & (x_grid >= center_x - 180)
        & (x_grid <= center_x + 180)
    )
    _, dark_x = np.where(dark_beak)
    if len(dark_x):
        left_extent = center_x - float(dark_x.min())
        right_extent = float(dark_x.max()) - center_x
        direction = right_extent - left_extent
    else:
        direction = 0.0
    return FaceFeature(
        center_x=center_x,
        center_y=center_y,
        width=width,
        height=height,
        direction=direction,
    )


def _load_stage_donors(
    stage_plan_path: Path,
    stage_alpha_root: Path,
) -> list[DonorPair]:
    plan = json.loads(stage_plan_path.read_text(encoding="utf-8"))
    donors: list[DonorPair] = []
    for key in plan["performance_keys"]:
        resting_spec, speaking_spec = key["poses"]
        resting_ordinal = int(resting_spec["ordinal"])
        speaking_ordinal = int(speaking_spec["ordinal"])
        resting_path = next(
            stage_alpha_root.glob(f"{resting_ordinal:03d}_*_alpha.png")
        )
        speaking_path = next(
            stage_alpha_root.glob(f"{speaking_ordinal:03d}_*_alpha.png")
        )
        resting = Image.open(resting_path).convert("RGBA")
        speaking = Image.open(speaking_path).convert("RGBA")
        feature = _face_feature(resting)
        if feature is None:
            raise ValueError(
                f"stage donor ACT{resting_ordinal:03d} has no face feature"
            )
        region = tuple(int(value) for value in key["articulation_region"])
        difference = ImageChops.difference(resting, speaking).convert("RGB")
        difference_mask = difference.convert("L").point(
            lambda value: 255 if value else 0
        )
        bounded = Image.new("L", CANVAS_SIZE, 0)
        bounded.paste(difference_mask.crop(region), region)
        difference_mask = bounded.filter(ImageFilter.MaxFilter(15))
        donors.append(
            DonorPair(
                resting_ordinal=resting_ordinal,
                resting=resting,
                speaking=speaking,
                feature=feature,
                difference_mask=difference_mask,
                articulation_region=region,
            )
        )
    if len(donors) != 22:
        raise ValueError("Kingfisher stage donor set must contain 22 pairs")
    return donors


def _donor_score(target: FaceFeature, donor: DonorPair) -> float:
    feature = donor.feature
    return (
        abs(math.log(target.width / feature.width))
        + abs(math.log(target.height / feature.height))
        + abs(target.direction - feature.direction) / 24.0
        + abs(target.center_y - feature.center_y) / 180.0
    )


def _synthetic_state(
    source: Image.Image,
    target_feature: FaceFeature,
    donor: DonorPair,
    *,
    speaking: bool,
) -> tuple[Image.Image, tuple[int, int, int, int], dict[str, object]]:
    donor_feature = donor.feature
    scale = (
        target_feature.width / donor_feature.width
        + target_feature.height / donor_feature.height
    ) / 2.0
    scale = max(0.75, min(1.35, scale))
    mask_bbox = donor.difference_mask.getbbox()
    if mask_bbox is None:
        raise ValueError("Kingfisher donor pair has no articulation change")
    pad = 10
    x0 = max(0, mask_bbox[0] - pad)
    y0 = max(0, mask_bbox[1] - pad)
    x1 = min(CANVAS_SIZE[0], mask_bbox[2] + pad)
    y1 = min(CANVAS_SIZE[1], mask_bbox[3] + pad)
    crop_box = (x0, y0, x1, y1)
    target_size = (
        max(1, round((x1 - x0) * scale)),
        max(1, round((y1 - y0) * scale)),
    )
    donor_state = donor.speaking if speaking else donor.resting
    patch = donor_state.crop(crop_box).resize(
        target_size,
        Image.Resampling.LANCZOS,
    )
    patch_mask = donor.difference_mask.crop(crop_box).resize(
        target_size,
        Image.Resampling.NEAREST,
    )
    destination_x = round(
        target_feature.center_x
        - (donor_feature.center_x - x0) * scale
    )
    destination_y = round(
        target_feature.center_y
        - (donor_feature.center_y - y0) * scale
    )
    output = source.copy()
    output.paste(patch, (destination_x, destination_y), patch_mask)
    output = _binary_alpha(output)
    mask_canvas = Image.new("L", CANVAS_SIZE, 0)
    mask_canvas.paste(patch_mask, (destination_x, destination_y))
    articulation_bbox = mask_canvas.getbbox()
    if articulation_bbox is None:
        raise ValueError("transformed Kingfisher articulation mask is empty")
    articulation_bbox = (
        max(0, articulation_bbox[0] - 2),
        max(0, articulation_bbox[1] - 2),
        min(CANVAS_SIZE[0], articulation_bbox[2] + 2),
        min(CANVAS_SIZE[1], articulation_bbox[3] + 2),
    )
    return output, articulation_bbox, {
        "donor_resting_ordinal": donor.resting_ordinal,
        "donor_score": round(_donor_score(target_feature, donor), 6),
        "donor_scale": round(scale, 8),
        "destination_x": destination_x,
        "destination_y": destination_y,
        "target_face_feature": {
            "center_x": round(target_feature.center_x, 4),
            "center_y": round(target_feature.center_y, 4),
            "width": target_feature.width,
            "height": target_feature.height,
            "direction": round(target_feature.direction, 4),
        },
    }


def _slug(pose_id: str) -> str:
    return pose_id.split(".", 3)[-1]


def rebuild_legacy_pairs(
    base_index_path: Path,
    rebuild_plan_path: Path,
    stage_plan_path: Path,
    stage_alpha_root: Path,
    output_root: Path,
) -> dict[str, object]:
    library = HDPoseLibrary(base_index_path)
    if library.canvas_size != CANVAS_SIZE:
        raise ValueError("Kingfisher legacy library must use 960 x 540")
    base_pose_ids = list(library.index["pose_ids"])[:LEGACY_POSE_COUNT]
    if len(base_pose_ids) != LEGACY_POSE_COUNT:
        raise ValueError("Kingfisher legacy library must contain 66 poses")
    plan = json.loads(rebuild_plan_path.read_text(encoding="utf-8"))
    authored_speaking = {
        int(value) for value in plan["authored_speaking_ordinals"]
    }
    occluded = {int(value) for value in plan["mouth_occluded_ordinals"]}
    body_core_overrides = {
        int(key): int(value)
        for key, value in plan["source_body_core_height_overrides"].items()
    }
    donors = _load_stage_donors(stage_plan_path, stage_alpha_root)
    alpha_root = output_root / "alphas"
    audit_root = output_root / "audits"
    pair_records: list[dict[str, object]] = []

    for ordinal, base_pose_id in enumerate(base_pose_ids, start=1):
        speaking_ordinal = SPEAKING_FIRST_ORDINAL + ordinal - 1
        slug = _slug(base_pose_id)
        speaking_pose_id = (
            f"kingfisher.act.{speaking_ordinal:03d}."
            f"{slug}-speaking-beak"
        )
        source = library.load_pose(base_pose_id)
        normalized, registration = _normalize_registration(
            source,
            source_body_core_height=body_core_overrides.get(
                ordinal,
                LEGACY_BODY_CORE_HEIGHT,
            ),
        )
        resting = normalized
        speaking = normalized
        mouth_visibility = "occluded" if ordinal in occluded else "visible"
        synthesis: dict[str, object] = {"method": "occluded_identity_pair"}
        articulation_region = (470, 225, 490, 245)

        if mouth_visibility == "visible":
            target_feature = _face_feature(normalized)
            if target_feature is None:
                raise ValueError(
                    f"legacy Kingfisher ACT{ordinal:03d} has no face feature"
                )
            donor = min(
                donors,
                key=lambda candidate: _donor_score(
                    target_feature,
                    candidate,
                ),
            )
            if ordinal in authored_speaking:
                resting, articulation_region, synthesis = _synthetic_state(
                    normalized,
                    target_feature,
                    donor,
                    speaking=False,
                )
                speaking = normalized
                synthesis["authored_state"] = "speaking"
            else:
                resting = normalized
                speaking, articulation_region, synthesis = _synthetic_state(
                    normalized,
                    target_feature,
                    donor,
                    speaking=True,
                )
                synthesis["authored_state"] = "resting"

        resting_name = (
            f"{ordinal:03d}_ACT{ordinal:03d}_{slug.replace('-', '_')}_"
            "resting_beak_alpha.png"
        )
        speaking_name = (
            f"{speaking_ordinal:03d}_ACT{speaking_ordinal:03d}_"
            f"{slug.replace('-', '_')}_speaking_beak_alpha.png"
        )
        resting_path = alpha_root / resting_name
        speaking_path = alpha_root / speaking_name
        _save_png_atomic(resting, resting_path)
        _save_png_atomic(speaking, speaking_path)

        if mouth_visibility == "visible":
            audit = audit_pair(
                resting_path,
                speaking_path,
                articulation_region=articulation_region,
                maximum_articulation_width=(
                    MAX_LEGACY_ARTICULATION_WIDTH
                ),
                maximum_articulation_height=(
                    MAX_LEGACY_ARTICULATION_HEIGHT
                ),
                maximum_registration_bound_delta=(
                    MAX_LEGACY_REGISTRATION_BOUND_DELTA
                ),
            )
        else:
            identical = (
                _sha256_path(resting_path) == _sha256_path(speaking_path)
            )
            audit = {
                "schema_version": 3,
                "passed": identical,
                "mouth_visibility": "occluded",
                "checks": {
                    "body_locked": identical,
                    "mouth_occlusion_declared": True,
                },
                "resting_sha256": _sha256_path(resting_path),
                "speaking_sha256": _sha256_path(speaking_path),
                "mouth_region": list(articulation_region),
            }
        audit["mouth_visibility"] = mouth_visibility
        audit_path = audit_root / (
            f"{ordinal:03d}_{speaking_ordinal:03d}_pair.json"
        )
        _write_json_atomic(audit_path, audit)
        pair_records.append(
            {
                "body_pose_id": base_pose_id,
                "resting_pose_id": base_pose_id,
                "speaking_pose_id": speaking_pose_id,
                "resting_ordinal": ordinal,
                "speaking_ordinal": speaking_ordinal,
                "mouth_visibility": mouth_visibility,
                "articulation_region": list(articulation_region),
                "resting_path": resting_path.relative_to(output_root).as_posix(),
                "speaking_path": speaking_path.relative_to(
                    output_root
                ).as_posix(),
                "resting_sha256": _sha256_path(resting_path),
                "speaking_sha256": _sha256_path(speaking_path),
                "audit_path": audit_path.relative_to(output_root).as_posix(),
                "audit_sha256": _sha256_path(audit_path),
                "audit_passed": bool(audit["passed"]),
                "registration": registration,
                "synthesis": synthesis,
            }
        )

    manifest = {
        "schema_version": 1,
        "character_id": "kingfisher",
        "rebuild_id": "kingfisher-legacy-speech-pairs-v1",
        "approval_state": "candidate_visual_review",
        "review_projection": True,
        "runtime_admitted": False,
        "canvas": {
            "width": CANVAS_SIZE[0],
            "height": CANVAS_SIZE[1],
            "alpha_mode": "binary_straight",
        },
        "registration_policy": {
            "target_body_core_height": TARGET_BODY_CORE_HEIGHT,
            "target_baseline_y": TARGET_BASELINE_Y,
            "target_center_x": CANVAS_SIZE[0] // 2,
            "maximum_visible_width": MAX_VISIBLE_WIDTH,
        },
        "pair_policy": {
            "body_lock": "exact_outside_articulation_region",
            "visible_pair_count": LEGACY_POSE_COUNT - len(occluded),
            "occluded_pair_count": len(occluded),
        },
        "source": {
            "base_index_path": base_index_path.name,
            "base_index_sha256": _sha256_path(base_index_path),
            "rebuild_plan_path": rebuild_plan_path.name,
            "rebuild_plan_sha256": _sha256_path(rebuild_plan_path),
            "stage_plan_path": stage_plan_path.name,
            "stage_plan_sha256": _sha256_path(stage_plan_path),
        },
        "pair_count": len(pair_records),
        "passed": all(record["audit_passed"] for record in pair_records),
        "pairs": pair_records,
    }
    manifest_path = output_root / "manifest.json"
    _write_json_atomic(manifest_path, manifest)
    return {
        "manifest_path": manifest_path.as_posix(),
        "manifest_sha256": _sha256_path(manifest_path),
        "pair_count": len(pair_records),
        "passed": manifest["passed"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild all 66 legacy Kingfisher poses as registered "
            "resting/speaking pairs."
        )
    )
    parser.add_argument("--base-index", type=Path, required=True)
    parser.add_argument("--rebuild-plan", type=Path, required=True)
    parser.add_argument("--stage-plan", type=Path, required=True)
    parser.add_argument("--stage-alpha-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = rebuild_legacy_pairs(
        args.base_index,
        args.rebuild_plan,
        args.stage_plan,
        args.stage_alpha_root,
        args.output_root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
