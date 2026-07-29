#!/usr/bin/env python3
"""Audit one resting/speaking Kingfisher stage-pose pair."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.register_kingfisher_stage_pose import portable_receipt_path
from tools.stabilize_kingfisher_stage_pair import (
    DEFAULT_ARTICULATION_REGION,
    validate_articulation_region,
)

CANVAS_SIZE = (960, 540)
# Profile beaks legitimately change more silhouette area than frontal beaks.
# Body stability is enforced independently and exactly outside the articulation
# region, so this threshold only guards against implausibly large head changes.
MINIMUM_SILHOUETTE_IOU = 0.98
MAXIMUM_REGISTRATION_BOUND_DELTA = 2
MAXIMUM_OUTSIDE_MOUTH_MEAN_ABS = 0.0
MINIMUM_MOUTH_MEAN_ABS = 5.0
MAXIMUM_CHANGED_RENDERED_PIXELS = 15000


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _load_rgba_and_sha256(path: Path) -> tuple[Image.Image, str]:
    payload = Path(path).read_bytes()
    with Image.open(io.BytesIO(payload)) as source:
        image = source.convert("RGBA")
    return image, hashlib.sha256(payload).hexdigest()


def _rendered_differences(
    resting: Image.Image,
    speaking: Image.Image,
) -> tuple[Image.Image, Image.Image]:
    background = Image.new("RGBA", resting.size, (0, 0, 0, 255))
    resting_rgb = Image.alpha_composite(background, resting).convert("RGB")
    speaking_rgb = Image.alpha_composite(background, speaking).convert("RGB")
    return (
        ImageChops.difference(resting_rgb, speaking_rgb),
        ImageChops.difference(
            resting.getchannel("A"),
            speaking.getchannel("A"),
        ),
    )


def _mean_abs_rendered_difference(
    rgb_difference: Image.Image,
    alpha_difference: Image.Image,
    region: tuple[int, int, int, int],
) -> float:
    rgb_crop = rgb_difference.crop(region)
    alpha_crop = alpha_difference.crop(region)
    rgb_mean = sum(ImageStat.Stat(rgb_crop).mean) / len(rgb_crop.getbands())
    alpha_mean = ImageStat.Stat(alpha_crop).mean[0]
    return max(rgb_mean, alpha_mean)


def _changed_rendered_pixels(
    rgb_difference: Image.Image,
    alpha_difference: Image.Image,
    region: tuple[int, int, int, int],
) -> int:
    rgb_channels = [
        list(channel.getdata())
        for channel in rgb_difference.crop(region).split()
    ]
    alpha_values = list(alpha_difference.crop(region).getdata())
    return sum(
        1
        for index, alpha_value in enumerate(alpha_values)
        if alpha_value
        or any(channel[index] for channel in rgb_channels)
    )


def audit_pair(
    resting_path: Path,
    speaking_path: Path,
    *,
    articulation_region: tuple[int, int, int, int] = (
        DEFAULT_ARTICULATION_REGION
    ),
) -> dict[str, object]:
    articulation_region = validate_articulation_region(articulation_region)
    resting, resting_sha256 = _load_rgba_and_sha256(resting_path)
    speaking, speaking_sha256 = _load_rgba_and_sha256(speaking_path)
    if resting.size != CANVAS_SIZE or speaking.size != CANVAS_SIZE:
        raise ValueError("Kingfisher stage pair must use the 960 x 540 canvas")

    resting_alpha = resting.getchannel("A")
    speaking_alpha = speaking.getchannel("A")
    resting_bbox = resting_alpha.getbbox()
    speaking_bbox = speaking_alpha.getbbox()
    if resting_bbox is None or speaking_bbox is None:
        raise ValueError("Kingfisher stage pair cannot contain an empty pose")
    registration_bound_delta = max(
        abs(resting_value - speaking_value)
        for resting_value, speaking_value in zip(resting_bbox, speaking_bbox)
    )
    if registration_bound_delta > MAXIMUM_REGISTRATION_BOUND_DELTA:
        raise ValueError("Kingfisher stage pair registration bounds differ")

    resting_pixels = resting_alpha.getdata()
    speaking_pixels = speaking_alpha.getdata()
    intersection = sum(
        1
        for resting_value, speaking_value in zip(
            resting_pixels,
            speaking_pixels,
        )
        if resting_value and speaking_value
    )
    union = sum(
        1
        for resting_value, speaking_value in zip(
            resting_alpha.getdata(),
            speaking_alpha.getdata(),
        )
        if resting_value or speaking_value
    )
    silhouette_iou = intersection / union

    rgb_difference, alpha_difference = _rendered_differences(
        resting,
        speaking,
    )
    mouth_mean_abs = _mean_abs_rendered_difference(
        rgb_difference,
        alpha_difference,
        articulation_region,
    )
    changed_rendered_pixels = _changed_rendered_pixels(
        rgb_difference,
        alpha_difference,
        articulation_region,
    )
    outside_mask = Image.new("L", CANVAS_SIZE, 255)
    outside_mask.paste(0, articulation_region)
    outside_rgb_mean = (
        sum(ImageStat.Stat(rgb_difference, outside_mask).mean) / 3
    )
    outside_alpha_mean = ImageStat.Stat(
        alpha_difference,
        outside_mask,
    ).mean[0]
    outside_mean_abs = max(outside_rgb_mean, outside_alpha_mean)

    checks = {
        "stable_registration_bounds": (
            registration_bound_delta <= MAXIMUM_REGISTRATION_BOUND_DELTA
        ),
        "silhouette_overlap": silhouette_iou >= MINIMUM_SILHOUETTE_IOU,
        "outside_mouth_stability": (
            outside_mean_abs <= MAXIMUM_OUTSIDE_MOUTH_MEAN_ABS
        ),
        "visible_mouth_change": mouth_mean_abs >= MINIMUM_MOUTH_MEAN_ABS,
        "bounded_articulation_change": (
            changed_rendered_pixels <= MAXIMUM_CHANGED_RENDERED_PIXELS
        ),
    }
    return {
        "schema_version": 2,
        "resting_path": portable_receipt_path(resting_path),
        "speaking_path": portable_receipt_path(speaking_path),
        "resting_sha256": resting_sha256,
        "speaking_sha256": speaking_sha256,
        "resting_registration_bbox": list(resting_bbox),
        "speaking_registration_bbox": list(speaking_bbox),
        "registration_bound_delta": registration_bound_delta,
        "silhouette_iou": round(silhouette_iou, 6),
        "outside_mouth_mean_abs": round(outside_mean_abs, 6),
        "mouth_mean_abs": round(mouth_mean_abs, 6),
        "changed_rendered_pixels": changed_rendered_pixels,
        "mouth_region": list(articulation_region),
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit a resting/speaking Kingfisher stage-pose pair."
    )
    parser.add_argument("resting", type=Path)
    parser.add_argument("speaking", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--articulation-region",
        type=int,
        nargs=4,
        metavar=("X0", "Y0", "X1", "Y1"),
        default=DEFAULT_ARTICULATION_REGION,
    )
    args = parser.parse_args()
    report = audit_pair(
        args.resting,
        args.speaking,
        articulation_region=tuple(args.articulation_region),
    )
    if args.output:
        _write_json_atomic(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
