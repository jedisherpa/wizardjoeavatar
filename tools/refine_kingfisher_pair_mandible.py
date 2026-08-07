#!/usr/bin/env python3
"""Refine one Kingfisher open-beak mate without redrawing its body."""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import math
import os
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.compose_kingfisher_pair_mandible_patch import beak_anatomy_metrics


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt_path(path: Path) -> str:
    return (
        path.relative_to(ROOT).as_posix()
        if path.is_relative_to(ROOT)
        else path.as_posix()
    )


def _points(values: list[int], *, name: str) -> list[tuple[int, int]]:
    if len(values) < 6 or len(values) % 2:
        raise ValueError(f"{name} must contain at least three x/y points")
    return list(zip(values[0::2], values[1::2]))


def _polygon_mask(
    size: tuple[int, int], polygon: list[tuple[int, int]]
) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    return mask


def _binary_alpha(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    rgba.putalpha(
        rgba.getchannel("A").point(lambda value: 255 if value >= 16 else 0)
    )
    return rgba


def _component_stats(mask: Image.Image) -> tuple[int, int]:
    pixels = mask.load()
    width, height = mask.size
    remaining = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if pixels[x, y]
    }
    component_sizes: list[int] = []
    while remaining:
        seed = remaining.pop()
        size = 1
        queue = deque([seed])
        while queue:
            x, y = queue.popleft()
            for neighbor in (
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1),
            ):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
                    size += 1
        component_sizes.append(size)
    total = sum(component_sizes)
    return total, max(component_sizes, default=0)


def _exclude_light_neutral(
    image: Image.Image,
    *,
    light_threshold: int,
    neutral_chroma_threshold: int,
) -> Image.Image:
    eligible = Image.new("L", image.size, 0)
    eligible.putdata(
        [
            a
            if not (
                max(r, g, b) >= light_threshold
                and max(r, g, b) - min(r, g, b)
                <= neutral_chroma_threshold
            )
            else 0
            for r, g, b, a in image.getdata()
        ]
    )
    return eligible


def _write_png_atomic(path: Path, image: Image.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        image.save(temporary, format="PNG", optimize=True)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _rotate_point(
    point: tuple[int, int],
    hinge: tuple[int, int],
    degrees: float,
) -> tuple[int, int]:
    radians = math.radians(degrees)
    cosine = math.cos(radians)
    sine = math.sin(radians)
    dx = point[0] - hinge[0]
    dy = point[1] - hinge[1]
    return (
        round(hinge[0] + cosine * dx + sine * dy),
        round(hinge[1] - sine * dx + cosine * dy),
    )


def refine_pair_mandible(
    resting_path: Path,
    speaking_donor_path: Path,
    output_path: Path,
    receipt_path: Path,
    *,
    mandible_polygon: list[tuple[int, int]],
    cavity_polygon: list[tuple[int, int]],
    upper_beak_polygon: list[tuple[int, int]],
    hinge: tuple[int, int],
    rotation_degrees: float,
    cavity_fill: tuple[int, int, int, int] = (28, 13, 16, 255),
    light_threshold: int = 180,
    neutral_chroma_threshold: int = 36,
    hinge_radius: int = 8,
    minimum_mandible_height: int = 8,
    minimum_connected_ratio: float = 0.8,
) -> dict[str, object]:
    resting_path = resting_path.resolve()
    speaking_donor_path = speaking_donor_path.resolve()
    output_path = output_path.resolve()
    receipt_path = receipt_path.resolve()
    with Image.open(resting_path) as loaded:
        resting = loaded.convert("RGBA")
    with Image.open(speaking_donor_path) as loaded:
        donor = loaded.convert("RGBA")
    if resting.size != donor.size:
        raise ValueError("resting and donor frames must share a canvas")
    width, height = resting.size
    for name, polygon in (
        ("mandible_polygon", mandible_polygon),
        ("cavity_polygon", cavity_polygon),
        ("upper_beak_polygon", upper_beak_polygon),
    ):
        if any(not (0 <= x < width and 0 <= y < height) for x, y in polygon):
            raise ValueError(f"{name} must remain inside the canvas")
    if not (0 <= hinge[0] < width and 0 <= hinge[1] < height):
        raise ValueError("hinge must remain inside the canvas")

    mandible_mask = ImageChops.multiply(
        _polygon_mask(resting.size, mandible_polygon),
        _exclude_light_neutral(
            donor,
            light_threshold=light_threshold,
            neutral_chroma_threshold=neutral_chroma_threshold,
        ),
    )
    mandible = Image.new("RGBA", resting.size, (0, 0, 0, 0))
    mandible.paste(donor, mask=mandible_mask)
    rotated_mandible = _binary_alpha(
        mandible.rotate(
            rotation_degrees,
            resample=Image.Resampling.BICUBIC,
            center=hinge,
            expand=False,
        )
    )
    rotated_polygon = [
        _rotate_point(point, hinge, rotation_degrees)
        for point in mandible_polygon
    ]
    rotated_mask = rotated_mandible.getchannel("A")
    mandible_bbox = rotated_mask.getbbox()
    if mandible_bbox is None:
        raise ValueError("rotated mandible contains no visible pixels")
    if mandible_bbox[3] - mandible_bbox[1] < minimum_mandible_height:
        raise ValueError("rotated mandible is too thin")
    mandible_pixels, largest_component = _component_stats(rotated_mask)
    connected_ratio = (
        largest_component / mandible_pixels if mandible_pixels else 0.0
    )
    if connected_ratio < minimum_connected_ratio:
        raise ValueError("rotated mandible contains detached geometry")

    output = resting.copy()
    output.paste(
        Image.new("RGBA", resting.size, cavity_fill),
        mask=_polygon_mask(resting.size, cavity_polygon),
    )
    output.alpha_composite(rotated_mandible)
    upper_mask = _polygon_mask(resting.size, upper_beak_polygon)
    output = Image.composite(resting, output, upper_mask)
    output = _binary_alpha(output)

    difference = ImageChops.difference(resting, output)
    changed_mask = difference.getchannel("A")
    for channel in difference.convert("RGB").split():
        changed_mask = ImageChops.lighter(changed_mask, channel)
    changed_mask = changed_mask.point(lambda value: 255 if value else 0)
    changed_bbox = changed_mask.getbbox()
    if changed_bbox is None:
        raise ValueError("mandible refinement produced no visible change")
    allowed_mask = ImageChops.lighter(
        ImageChops.lighter(
            rotated_mask,
            _polygon_mask(resting.size, cavity_polygon),
        ),
        upper_mask,
    )
    if ImageChops.multiply(
        changed_mask, ImageChops.invert(allowed_mask)
    ).getbbox() is not None:
        raise ValueError("mandible refinement changed pixels outside the mouth")

    hinge_window = rotated_mandible.crop(
        (
            max(0, hinge[0] - hinge_radius),
            max(0, hinge[1] - hinge_radius),
            min(width, hinge[0] + hinge_radius + 1),
            min(height, hinge[1] + hinge_radius + 1),
        )
    )
    if hinge_window.getchannel("A").getbbox() is None:
        raise ValueError("rotated mandible is disconnected from the hinge")

    anatomy = beak_anatomy_metrics(
        hinge=hinge,
        hinge_radius=hinge_radius,
        upper_beak_polygon=upper_beak_polygon,
        mandible_polygon=rotated_polygon,
        cavity_polygon=cavity_polygon,
        direction_vector=None,
    )
    if anatomy["passed"] is not True:
        raise ValueError("refined beak anatomy is misaligned")

    _write_png_atomic(output_path, output)
    receipt = {
        "schema_version": 1,
        "method": "pair_specific_connected_mandible_patch_v1",
        "approval_state": "candidate_visual_review",
        "runtime_admitted": False,
        "resting_path": _receipt_path(resting_path),
        "resting_sha256": _sha256(resting_path),
        "speaking_donor_path": _receipt_path(speaking_donor_path),
        "speaking_donor_sha256": _sha256(speaking_donor_path),
        "speaking_path": _receipt_path(output_path),
        "speaking_sha256": _sha256(output_path),
        "canvas": [width, height],
        "hinge": list(hinge),
        "rotation_degrees": rotation_degrees,
        "source_mandible_polygon": [
            list(point) for point in mandible_polygon
        ],
        "mandible_polygon": [
            list(point) for point in rotated_polygon
        ],
        "cavity_polygon": [list(point) for point in cavity_polygon],
        "cavity_fill_rgba": list(cavity_fill),
        "source_mask": {
            "mode": "exclude_light_neutral",
            "light_threshold": light_threshold,
            "neutral_chroma_threshold": neutral_chroma_threshold,
        },
        "upper_beak_polygon": [list(point) for point in upper_beak_polygon],
        "anatomy_upper_beak_polygon": [
            list(point) for point in upper_beak_polygon
        ],
        "anatomy_hinge": list(hinge),
        "anatomy_hinge_radius": hinge_radius,
        "anatomy_direction_vector": None,
        "hinge_radius": hinge_radius,
        "minimum_mandible_height": minimum_mandible_height,
        "minimum_connected_ratio": minimum_connected_ratio,
        "mandible_bbox": list(mandible_bbox),
        "mandible_opaque_pixels": mandible_pixels,
        "mandible_largest_component_pixels": largest_component,
        "mandible_connected_ratio": round(connected_ratio, 6),
        "upper_beak_policy": "immutable_source_pixels",
        "changed_bbox": list(changed_bbox),
        "outside_mouth_change": False,
        "outside_articulation_change": False,
        "beak_anatomy": anatomy,
    }
    _write_json_atomic(receipt_path, receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resting", type=Path, required=True)
    parser.add_argument("--speaking-donor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--mandible-polygon", nargs="+", type=int, required=True)
    parser.add_argument("--cavity-polygon", nargs="+", type=int, required=True)
    parser.add_argument("--upper-beak-polygon", nargs="+", type=int, required=True)
    parser.add_argument("--hinge", nargs=2, type=int, required=True)
    parser.add_argument("--rotation-degrees", type=float, required=True)
    parser.add_argument("--hinge-radius", type=int, default=8)
    parser.add_argument("--minimum-mandible-height", type=int, default=8)
    parser.add_argument("--minimum-connected-ratio", type=float, default=0.8)
    parser.add_argument("--cavity-fill", nargs=4, type=int, default=(28, 13, 16, 255))
    parser.add_argument("--light-threshold", type=int, default=180)
    parser.add_argument("--neutral-chroma-threshold", type=int, default=36)
    args = parser.parse_args()
    receipt = refine_pair_mandible(
        args.resting,
        args.speaking_donor,
        args.output,
        args.receipt,
        mandible_polygon=_points(args.mandible_polygon, name="mandible_polygon"),
        cavity_polygon=_points(args.cavity_polygon, name="cavity_polygon"),
        upper_beak_polygon=_points(
            args.upper_beak_polygon,
            name="upper_beak_polygon",
        ),
        hinge=(args.hinge[0], args.hinge[1]),
        rotation_degrees=args.rotation_degrees,
        hinge_radius=args.hinge_radius,
        minimum_mandible_height=args.minimum_mandible_height,
        minimum_connected_ratio=args.minimum_connected_ratio,
        cavity_fill=tuple(args.cavity_fill),
        light_threshold=args.light_threshold,
        neutral_chroma_threshold=args.neutral_chroma_threshold,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
