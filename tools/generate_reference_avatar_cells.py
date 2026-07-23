#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Iterable, Sequence, Tuple

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "assets" / "reference" / "target_voxel_wizard.png"
DEFAULT_OUTPUT = ROOT / "wizard_avatar" / "definitions" / "reference_avatar_cells.json"


def color_distance_from_white(rgb: Tuple[int, int, int]) -> float:
    return ((255 - rgb[0]) ** 2 + (255 - rgb[1]) ** 2 + (255 - rgb[2]) ** 2) ** 0.5


def initial_subject_mask(image: Image.Image, threshold: float) -> Image.Image:
    mask = Image.new("1", image.size, 0)
    src = image.load()
    dst = mask.load()
    for y in range(image.height):
        for x in range(image.width):
            if color_distance_from_white(src[x, y]) >= threshold:
                dst[x, y] = 1
    return mask


def alpha_subject_mask(image: Image.Image, minimum_component_pixels: int = 16) -> Image.Image:
    """Keep authored alpha while removing detached matte debris."""

    alpha = image.getchannel("A")
    binary = alpha.point(lambda value: 1 if value else 0, mode="1")
    src = binary.load()
    visited = Image.new("1", binary.size, 0)
    seen = visited.load()
    kept = Image.new("L", binary.size, 0)
    dst = kept.load()

    for y in range(binary.height):
        for x in range(binary.width):
            if not src[x, y] or seen[x, y]:
                continue
            queue: deque[Tuple[int, int]] = deque([(x, y)])
            seen[x, y] = 1
            component = []
            while queue:
                current_x, current_y = queue.popleft()
                component.append((current_x, current_y))
                for next_x, next_y in (
                    (current_x + 1, current_y),
                    (current_x - 1, current_y),
                    (current_x, current_y + 1),
                    (current_x, current_y - 1),
                ):
                    if (
                        0 <= next_x < binary.width
                        and 0 <= next_y < binary.height
                        and src[next_x, next_y]
                        and not seen[next_x, next_y]
                    ):
                        seen[next_x, next_y] = 1
                        queue.append((next_x, next_y))
            if len(component) < minimum_component_pixels:
                continue
            for component_x, component_y in component:
                dst[component_x, component_y] = alpha.getpixel(
                    (component_x, component_y)
                )
    return kept


def subject_bounds(mask: Image.Image) -> Tuple[int, int, int, int]:
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("Reference image did not contain a detectable subject.")
    left, top, right, bottom = bbox
    return left, top, right - 1, bottom - 1


def expand_bounds(bounds: Tuple[int, int, int, int], size: Tuple[int, int], margin: int) -> Tuple[int, int, int, int]:
    left, top, right, bottom = bounds
    width, height = size
    return (
        max(0, left - margin),
        max(0, top - margin),
        min(width - 1, right + margin),
        min(height - 1, bottom + margin),
    )


def flood_exterior(mask: Image.Image) -> Image.Image:
    width, height = mask.size
    src = mask.load()
    exterior = Image.new("1", mask.size, 0)
    dst = exterior.load()
    queue: deque[Tuple[int, int]] = deque()

    def enqueue(x: int, y: int) -> None:
        if 0 <= x < width and 0 <= y < height and not src[x, y] and not dst[x, y]:
            dst[x, y] = 1
            queue.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)
    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    while queue:
        x, y = queue.popleft()
        enqueue(x + 1, y)
        enqueue(x - 1, y)
        enqueue(x, y + 1)
        enqueue(x, y - 1)
    return exterior


def filled_subject_mask(mask: Image.Image) -> Image.Image:
    exterior = flood_exterior(mask)
    result = Image.new("1", mask.size, 0)
    src = mask.load()
    ext = exterior.load()
    dst = result.load()
    for y in range(mask.height):
        for x in range(mask.width):
            if src[x, y] or not ext[x, y]:
                dst[x, y] = 1
    return result


def iter_cells(image: Image.Image, mask: Image.Image, coverage_threshold: int) -> Iterable[dict]:
    rgb = image.convert("RGB").load()
    alpha = mask.convert("L").load()
    for y in range(image.height):
        for x in range(image.width):
            if alpha[x, y] >= coverage_threshold:
                yield {"x": x, "y": y, "rgb": list(rgb[x, y])}


def palette_image(colors: Sequence[Tuple[int, int, int]]) -> Image.Image:
    if not colors or len(colors) > 256:
        raise ValueError("A canonical palette must contain 1..256 colors")
    flattened = [
        int(channel)
        for color in colors
        for channel in color
    ]
    if any(channel < 0 or channel > 255 for channel in flattened):
        raise ValueError("Canonical palette channels must be in the range 0..255")
    flattened.extend([0] * (768 - len(flattened)))
    image = Image.new("P", (1, 1))
    image.putpalette(flattened)
    return image


def quantize_to_palette(
    image: Image.Image,
    colors: Sequence[Tuple[int, int, int]],
) -> Image.Image:
    return image.convert("RGB").quantize(
        palette=palette_image(colors),
        dither=Image.Dither.NONE,
    ).convert("RGB")


def generate_from_image(
    opened: Image.Image,
    source_label: str,
    output_path: Path,
    rows: int,
    margin: int,
    threshold: float,
    coverage_threshold: int,
    colors: int,
    minimum_alpha_component_pixels: int = 16,
    palette_colors: Sequence[Tuple[int, int, int]] | None = None,
) -> dict:
    rgba_source = opened.convert("RGBA")
    source = rgba_source.convert("RGB")
    alpha_extrema = rgba_source.getchannel("A").getextrema()
    has_authored_alpha = alpha_extrema[0] < 255
    rough_mask = (
        alpha_subject_mask(rgba_source, minimum_alpha_component_pixels)
        if has_authored_alpha
        else initial_subject_mask(source, threshold)
    )
    crop_bounds = expand_bounds(subject_bounds(rough_mask), source.size, margin)
    crop_box = (crop_bounds[0], crop_bounds[1], crop_bounds[2] + 1, crop_bounds[3] + 1)
    cropped = source.crop(crop_box)
    cropped_mask = rough_mask.crop(crop_box)
    solid_mask = (
        cropped_mask
        if has_authored_alpha
        else filled_subject_mask(cropped_mask)
    )

    cols = max(1, round(rows * cropped.width / cropped.height))
    resample = Image.Resampling.BOX
    tile_image = cropped.resize((cols, rows), resample)
    if palette_colors is None:
        tile_image = tile_image.quantize(
            colors=colors,
            method=Image.Quantize.MEDIANCUT,
        ).convert("RGB")
    else:
        tile_image = quantize_to_palette(tile_image, palette_colors)
    tile_mask = solid_mask.resize((cols, rows), resample)

    payload = {
        "source": source_label,
        "source_size": [source.width, source.height],
        "source_crop": [crop_bounds[0], crop_bounds[1], crop_bounds[2], crop_bounds[3]],
        "cols": cols,
        "rows": rows,
        "root_anchor": [cols // 2, rows - 1],
        "quantized_colors": len(palette_colors) if palette_colors is not None else colors,
        "coverage_threshold": coverage_threshold,
        "cells": list(iter_cells(tile_image, tile_mask, coverage_threshold)),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def generate(
    input_path: Path,
    output_path: Path,
    rows: int,
    margin: int,
    threshold: float,
    coverage_threshold: int,
    colors: int,
    minimum_alpha_component_pixels: int = 16,
    palette_colors: Sequence[Tuple[int, int, int]] | None = None,
) -> dict:
    source_label = str(
        input_path.relative_to(ROOT)
        if input_path.is_relative_to(ROOT)
        else input_path
    )
    with Image.open(input_path) as opened:
        return generate_from_image(
            opened,
            source_label,
            output_path,
            rows,
            margin,
            threshold,
            coverage_threshold,
            colors,
            minimum_alpha_component_pixels,
            palette_colors,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a reference PNG to a repeatable square-cell avatar mask.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rows", type=int, default=96)
    parser.add_argument("--margin", type=int, default=18)
    parser.add_argument("--threshold", type=float, default=30.0)
    parser.add_argument("--coverage-threshold", type=int, default=24)
    parser.add_argument("--colors", type=int, default=64)
    parser.add_argument("--minimum-alpha-component-pixels", type=int, default=16)
    parser.add_argument(
        "--palette",
        type=Path,
        help="Optional canonical palette JSON containing a colors array.",
    )
    args = parser.parse_args()
    palette_colors = None
    if args.palette is not None:
        palette_payload = json.loads(args.palette.read_text(encoding="utf-8"))
        palette_colors = tuple(
            tuple(int(channel) for channel in color)
            for color in palette_payload["colors"]
        )
    payload = generate(
        args.input,
        args.output,
        args.rows,
        args.margin,
        args.threshold,
        args.coverage_threshold,
        args.colors,
        args.minimum_alpha_component_pixels,
        palette_colors,
    )
    print(json.dumps({k: payload[k] for k in ["source", "source_crop", "cols", "rows", "root_anchor"]}, indent=2))


if __name__ == "__main__":
    main()
