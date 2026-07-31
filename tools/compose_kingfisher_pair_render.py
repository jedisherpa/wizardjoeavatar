#!/usr/bin/env python3
"""Composite one pose-specific speaking render onto its canonical body."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw

CANVAS_SIZE = (960, 540)


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _save_png_atomic(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        image.save(temporary, format="PNG", optimize=True)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def extract_light_background_alpha(image: Image.Image) -> Image.Image:
    """Remove the detected matte only where connected to the boundary."""
    rgb = np.asarray(image.convert("RGB"))
    height, width, _ = rgb.shape
    border = np.concatenate(
        (
            rgb[0, :, :],
            rgb[-1, :, :],
            rgb[:, 0, :],
            rgb[:, -1, :],
        ),
        axis=0,
    )
    background = np.median(border, axis=0)
    chroma_background = (
        background[1] > background[0] + 80
        and background[1] > background[2] + 80
    )
    if chroma_background:
        distance = np.linalg.norm(
            rgb.astype(np.float32) - background,
            axis=2,
        )
        traversable = distance < 150
    else:
        minimum = rgb.min(axis=2)
        maximum = rgb.max(axis=2)
        traversable = (minimum > 220) & ((maximum - minimum) < 28)
    exterior = np.zeros((height, width), dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    def enqueue(y: int, x: int) -> None:
        if traversable[y, x] and not exterior[y, x]:
            exterior[y, x] = True
            queue.append((y, x))

    for x in range(width):
        enqueue(0, x)
        enqueue(height - 1, x)
    for y in range(height):
        enqueue(y, 0)
        enqueue(y, width - 1)
    while queue:
        y, x = queue.popleft()
        for next_y, next_x in (
            (y - 1, x),
            (y + 1, x),
            (y, x - 1),
            (y, x + 1),
        ):
            if (
                0 <= next_y < height
                and 0 <= next_x < width
                and traversable[next_y, next_x]
                and not exterior[next_y, next_x]
            ):
                exterior[next_y, next_x] = True
                queue.append((next_y, next_x))

    alpha = np.where(exterior, 0, 255).astype(np.uint8)
    if chroma_background:
        red = rgb[:, :, 0].astype(np.int16)
        green = rgb[:, :, 1].astype(np.int16)
        blue = rgb[:, :, 2].astype(np.int16)
        chroma_spill = (
            (green > 100)
            & (green > red + 30)
            & (green > blue + 30)
        )
        alpha[chroma_spill] = 0
    rgba = np.dstack((rgb, alpha))
    return Image.fromarray(rgba).convert("RGBA")


def _binary_alpha(image: Image.Image) -> Image.Image:
    output = image.convert("RGBA")
    output.putalpha(
        output.getchannel("A").point(
            lambda value: 255 if value >= 128 else 0
        )
    )
    return output


def compose_pair(
    resting_path: Path,
    generated_path: Path,
    output_path: Path,
    receipt_path: Path,
    *,
    scale: float,
    scale_x: float | None = None,
    scale_y: float | None = None,
    translate_x: int,
    translate_y: int,
    articulation_polygon: list[tuple[int, int]],
    cavity_polygon: list[tuple[int, int]] | None = None,
    cavity_fill_mode: str = "generated_alpha",
    output_role: str = "speaking",
) -> dict[str, object]:
    resting = Image.open(resting_path).convert("RGBA")
    generated_source = Image.open(generated_path).convert("RGB")
    if resting.size != CANVAS_SIZE:
        raise ValueError("canonical Kingfisher frame must use 960 x 540")
    if scale <= 0:
        raise ValueError("render alignment scale must be positive")
    effective_scale_x = scale if scale_x is None else scale_x
    effective_scale_y = scale if scale_y is None else scale_y
    if effective_scale_x <= 0 or effective_scale_y <= 0:
        raise ValueError("render alignment scales must be positive")
    if output_role not in {"speaking", "resting_repair"}:
        raise ValueError("output role must be speaking or resting_repair")
    if cavity_fill_mode not in {"generated_alpha", "opaque_polygon"}:
        raise ValueError(
            "cavity fill mode must be generated_alpha or opaque_polygon"
        )
    if len(articulation_polygon) < 3:
        raise ValueError("articulation polygon requires at least three points")
    if any(
        x < 0 or y < 0 or x >= CANVAS_SIZE[0] or y >= CANVAS_SIZE[1]
        for x, y in articulation_polygon
    ):
        raise ValueError("articulation polygon must remain inside the canvas")
    if cavity_polygon is not None:
        if len(cavity_polygon) < 3:
            raise ValueError("cavity polygon requires at least three points")
        if any(
            x < 0 or y < 0 or x >= CANVAS_SIZE[0] or y >= CANVAS_SIZE[1]
            for x, y in cavity_polygon
        ):
            raise ValueError("cavity polygon must remain inside the canvas")

    generated = extract_light_background_alpha(generated_source)
    target_size = (
        max(1, round(generated.width * effective_scale_x)),
        max(1, round(generated.height * effective_scale_y)),
    )
    generated = generated.resize(target_size, Image.Resampling.LANCZOS)
    generated = _binary_alpha(generated)
    aligned = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    aligned.alpha_composite(generated, (translate_x, translate_y))

    mask = Image.new("L", CANVAS_SIZE, 0)
    ImageDraw.Draw(mask).polygon(articulation_polygon, fill=255)
    if cavity_polygon is not None:
        cavity_mask = Image.new("L", CANVAS_SIZE, 0)
        ImageDraw.Draw(cavity_mask).polygon(cavity_polygon, fill=255)
        cavity_outside = ImageChops.subtract(cavity_mask, mask).getbbox()
        if cavity_outside is not None:
            raise ValueError(
                "cavity polygon must remain inside the articulation polygon"
            )
        cavity_alpha = cavity_mask
        if cavity_fill_mode == "generated_alpha":
            cavity_alpha = ImageChops.multiply(
                cavity_mask,
                aligned.getchannel("A"),
            )
        aligned = Image.composite(
            Image.new("RGBA", CANVAS_SIZE, (10, 13, 16, 255)),
            aligned,
            cavity_alpha,
        )
    output = Image.composite(aligned, resting, mask)
    output = _binary_alpha(output)

    difference = ImageChops.difference(
        resting.convert("RGB"),
        output.convert("RGB"),
    )
    alpha_difference = ImageChops.difference(
        resting.getchannel("A"),
        output.getchannel("A"),
    )
    changed_mask = Image.new("L", CANVAS_SIZE, 0)
    changed_rgb = difference.convert("L").point(
        lambda value: 255 if value else 0
    )
    changed_alpha = alpha_difference.point(
        lambda value: 255 if value else 0
    )
    changed_mask = ImageChops.lighter(changed_rgb, changed_alpha)
    changed_bbox = changed_mask.getbbox()
    polygon_bbox = mask.getbbox()
    if changed_bbox is None or polygon_bbox is None:
        raise ValueError("generated render produced no articulation change")
    outside = Image.new("L", CANVAS_SIZE, 255)
    outside.paste(0, polygon_bbox)
    outside_change = ImageChops.multiply(changed_mask, outside).getbbox()
    if outside_change is not None:
        raise ValueError("generated render changed pixels outside its polygon")

    _save_png_atomic(output, output_path)
    output_path_key = (
        "speaking_path"
        if output_role == "speaking"
        else "repaired_resting_path"
    )
    output_sha_key = (
        "speaking_sha256"
        if output_role == "speaking"
        else "repaired_resting_sha256"
    )
    receipt = {
        "schema_version": 1,
        "method": "pose_specific_render_local_articulation_composite_v1",
        "output_role": output_role,
        "approval_state": "candidate_visual_review",
        "runtime_admitted": False,
        "canvas": list(CANVAS_SIZE),
        "resting_path": resting_path.as_posix(),
        "resting_sha256": _sha256_path(resting_path),
        "generated_render_path": generated_path.as_posix(),
        "generated_render_sha256": _sha256_path(generated_path),
        output_path_key: output_path.as_posix(),
        output_sha_key: _sha256_path(output_path),
        "alignment": {
            "scale": scale,
            "scale_x": effective_scale_x,
            "scale_y": effective_scale_y,
            "translate_x": translate_x,
            "translate_y": translate_y,
            "interpolation": "lanczos_rgb_binary_alpha",
        },
        "articulation_polygon": [
            [x, y] for x, y in articulation_polygon
        ],
        "cavity_polygon": (
            [[x, y] for x, y in cavity_polygon]
            if cavity_polygon is not None
            else None
        ),
        "cavity_fill_rgba": (
            [10, 13, 16, 255]
            if cavity_polygon is not None
            else None
        ),
        "cavity_fill_mode": (
            cavity_fill_mode
            if cavity_polygon is not None
            else None
        ),
        "articulation_bbox": list(polygon_bbox),
        "changed_bbox": list(changed_bbox),
        "outside_articulation_change": False,
    }
    _write_json_atomic(receipt_path, receipt)
    return receipt


def _parse_polygon(values: list[int]) -> list[tuple[int, int]]:
    if len(values) < 6 or len(values) % 2:
        raise argparse.ArgumentTypeError(
            "articulation polygon needs at least three x/y pairs"
        )
    return list(zip(values[::2], values[1::2]))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Composite one pose-specific Kingfisher speaking render "
            "onto an immutable canonical body frame."
        )
    )
    parser.add_argument("--resting", type=Path, required=True)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--scale", type=float, required=True)
    parser.add_argument("--scale-x", type=float)
    parser.add_argument("--scale-y", type=float)
    parser.add_argument("--translate-x", type=int, required=True)
    parser.add_argument("--translate-y", type=int, required=True)
    parser.add_argument(
        "--output-role",
        choices=("speaking", "resting_repair"),
        default="speaking",
    )
    parser.add_argument(
        "--articulation-polygon",
        type=int,
        nargs="+",
        required=True,
    )
    parser.add_argument(
        "--cavity-polygon",
        type=int,
        nargs="+",
    )
    parser.add_argument(
        "--cavity-fill-mode",
        choices=("generated_alpha", "opaque_polygon"),
        default="generated_alpha",
    )
    args = parser.parse_args()
    receipt = compose_pair(
        args.resting,
        args.generated,
        args.output,
        args.receipt,
        scale=args.scale,
        scale_x=args.scale_x,
        scale_y=args.scale_y,
        translate_x=args.translate_x,
        translate_y=args.translate_y,
        articulation_polygon=_parse_polygon(
            args.articulation_polygon
        ),
        cavity_polygon=(
            _parse_polygon(args.cavity_polygon)
            if args.cavity_polygon is not None
            else None
        ),
        cavity_fill_mode=args.cavity_fill_mode,
        output_role=args.output_role,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
