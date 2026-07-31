#!/usr/bin/env python3
"""Stabilize a Kingfisher speech pose against its resting body frame."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

CANVAS_SIZE = (960, 540)
DEFAULT_ARTICULATION_REGION = (420, 200, 540, 320)
MAX_ARTICULATION_WIDTH = 140
MAX_ARTICULATION_HEIGHT = 130


def validate_articulation_region(
    region: tuple[int, int, int, int],
    *,
    maximum_width: int = MAX_ARTICULATION_WIDTH,
    maximum_height: int = MAX_ARTICULATION_HEIGHT,
) -> tuple[int, int, int, int]:
    if len(region) != 4 or any(type(value) is not int for value in region):
        raise ValueError("articulation region must contain four integers")
    x0, y0, x1, y1 = region
    if x0 < 0 or y0 < 0 or x1 > CANVAS_SIZE[0] or y1 > CANVAS_SIZE[1]:
        raise ValueError("articulation region must remain inside the canvas")
    if x1 <= x0 or y1 <= y0:
        raise ValueError("articulation region must have positive area")
    if x1 - x0 > maximum_width:
        raise ValueError("articulation region is too wide")
    if y1 - y0 > maximum_height:
        raise ValueError("articulation region is too tall")
    return region


def _articulation_mask(
    region: tuple[int, int, int, int],
) -> Image.Image:
    x0, y0, x1, y1 = region
    width = x1 - x0
    height = y1 - y0
    inset = min(5, max(2, min(width, height) // 16))
    radius = min(14, max(6, min(width, height) // 8))
    crop = Image.new("L", (width, height), 0)
    ImageDraw.Draw(crop).rounded_rectangle(
        (inset, inset, width - inset - 1, height - inset - 1),
        radius=radius,
        fill=255,
    )
    crop = crop.filter(ImageFilter.GaussianBlur(radius=2))
    mask = Image.new("L", CANVAS_SIZE, 0)
    mask.paste(crop, (x0, y0))
    return mask


def stabilize_pair(
    resting_path: Path,
    speaking_candidate_path: Path,
    output_path: Path,
    *,
    articulation_region: tuple[int, int, int, int] = (
        DEFAULT_ARTICULATION_REGION
    ),
) -> None:
    articulation_region = validate_articulation_region(articulation_region)
    resting = Image.open(resting_path).convert("RGBA")
    speaking = Image.open(speaking_candidate_path).convert("RGBA")
    if resting.size != CANVAS_SIZE or speaking.size != CANVAS_SIZE:
        raise ValueError("Kingfisher stage pair must use the 960 x 540 canvas")
    stabilized = Image.composite(
        speaking,
        resting,
        _articulation_mask(articulation_region),
    )
    alpha = stabilized.getchannel("A").point(
        lambda value: 255 if value >= 128 else 0
    )
    stabilized.putalpha(alpha)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(
        f".{output_path.name}.{os.getpid()}.tmp"
    )
    try:
        stabilized.save(temporary, format="PNG", optimize=True)
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stabilize a Kingfisher speaking frame."
    )
    parser.add_argument("resting", type=Path)
    parser.add_argument("speaking_candidate", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--articulation-region",
        type=int,
        nargs=4,
        metavar=("X0", "Y0", "X1", "Y1"),
        default=DEFAULT_ARTICULATION_REGION,
    )
    args = parser.parse_args()
    stabilize_pair(
        args.resting,
        args.speaking_candidate,
        args.output,
        articulation_region=tuple(args.articulation_region),
    )


if __name__ == "__main__":
    main()
