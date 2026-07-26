#!/usr/bin/env python3
"""Deterministically remove a flat chroma key from JoeVille source art."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import median
from typing import Any

from PIL import Image, ImageFilter


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sample_border_key(image: Image.Image) -> tuple[int, int, int]:
    width, height = image.size
    band = max(1, min(width, height, 6))
    step = max(1, min(width, height) // 256)
    samples: list[tuple[int, int, int]] = []
    pixels = image.load()
    for x in range(0, width, step):
        for y in range(band):
            samples.append(tuple(pixels[x, y][:3]))
            samples.append(tuple(pixels[x, height - 1 - y][:3]))
    for y in range(0, height, step):
        for x in range(band):
            samples.append(tuple(pixels[x, y][:3]))
            samples.append(tuple(pixels[width - 1 - x, y][:3]))
    return tuple(
        int(round(median(sample[channel] for sample in samples)))
        for channel in range(3)
    )


def extract_alpha(
    *,
    source_path: Path,
    destination_path: Path,
    tolerance: int = 110,
    edge_contract: int = 1,
    canvas_size: tuple[int, int] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    if not 0 <= tolerance <= 255:
        raise ValueError("tolerance must be between 0 and 255")
    if not 0 <= edge_contract <= 16:
        raise ValueError("edge_contract must be between 0 and 16")
    if destination_path.exists() and not force:
        raise ValueError("destination exists; pass force=True to replace it")

    with Image.open(source_path) as source:
        image = source.convert("RGBA")
    key = _sample_border_key(image)
    source_canvas_size = image.size
    normalization_scale = 1.0
    normalization_offset = (0, 0)
    if canvas_size is not None and image.size != canvas_size:
        normalization_scale = min(
            canvas_size[0] / image.width,
            canvas_size[1] / image.height,
        )
        normalized_size = (
            max(1, math.floor(image.width * normalization_scale)),
            max(1, math.floor(image.height * normalization_scale)),
        )
        resized = image.convert("RGBa").resize(
            normalized_size,
            resample=Image.Resampling.LANCZOS,
        ).convert("RGBA")
        normalization_offset = (
            (canvas_size[0] - normalized_size[0]) // 2,
            (canvas_size[1] - normalized_size[1]) // 2,
        )
        normalized = Image.new("RGBA", canvas_size, (*key, 255))
        normalized.alpha_composite(resized, normalization_offset)
        image = normalized
    pixels = image.load()
    transparent = 0
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, source_alpha = pixels[x, y]
            distance = max(
                abs(red - key[0]),
                abs(green - key[1]),
                abs(blue - key[2]),
            )
            alpha = 0 if distance <= tolerance else source_alpha
            if alpha == 0:
                pixels[x, y] = (0, 0, 0, 0)
                transparent += 1
            else:
                pixels[x, y] = (red, green, blue, alpha)

    alpha = image.getchannel("A")
    for _ in range(edge_contract):
        alpha = alpha.filter(ImageFilter.MinFilter(3))
    image.putalpha(alpha)
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            if pixels[x, y][3] == 0:
                pixels[x, y] = (0, 0, 0, 0)
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("chroma extraction removed the complete silhouette")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination_path.with_name(
        f".{destination_path.name}.{os.getpid()}.tmp"
    )
    image.save(temporary, format="PNG", optimize=True)
    temporary.replace(destination_path)
    return {
        "schema_version": 1,
        "source_path": str(source_path.resolve()),
        "source_sha256": _sha256(source_path),
        "destination_path": str(destination_path.resolve()),
        "destination_sha256": _sha256(destination_path),
        "destination_rgba_sha256": hashlib.sha256(
            image.tobytes()
        ).hexdigest(),
        "key_color": list(key),
        "tolerance": tolerance,
        "edge_contract": edge_contract,
        "source_canvas_size": list(source_canvas_size),
        "canvas_size": list(image.size),
        "canvas_normalized": source_canvas_size != image.size,
        "normalization_scale": normalization_scale,
        "normalization_offset": list(normalization_offset),
        "silhouette_bbox": list(bbox),
        "transparent_pixels_before_contract": transparent,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--tolerance", type=int, default=110)
    parser.add_argument("--edge-contract", type=int, default=1)
    parser.add_argument("--canvas-size", type=int, default=1254)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--receipt", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    receipt = extract_alpha(
        source_path=args.source.resolve(),
        destination_path=args.destination.resolve(),
        tolerance=args.tolerance,
        edge_contract=args.edge_contract,
        canvas_size=(args.canvas_size, args.canvas_size),
        force=args.force,
    )
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt is not None:
        receipt_path = args.receipt.resolve()
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(payload, encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
