#!/usr/bin/env python3
"""Build the committed Wizard Joe palette from the canonical reference art."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image

try:
    from .generate_reference_avatar_cells import (
        DEFAULT_INPUT,
        ROOT,
        initial_subject_mask,
    )
except ImportError:
    from generate_reference_avatar_cells import (
        DEFAULT_INPUT,
        ROOT,
        initial_subject_mask,
    )


DEFAULT_OUTPUT = (
    ROOT
    / "assets"
    / "reference"
    / "motion_sources"
    / "canonical_palette_v1.json"
)
REQUIRED_COLORS = (
    (255, 255, 255),
    (18, 20, 18),
)


def build_palette(
    source_path: Path,
    *,
    color_count: int,
    threshold: float,
) -> dict[str, object]:
    if color_count < len(REQUIRED_COLORS) or color_count > 256:
        raise ValueError(
            f"color_count must be between {len(REQUIRED_COLORS)} and 256"
        )
    source_bytes = source_path.read_bytes()
    source = Image.open(source_path).convert("RGB")
    mask = initial_subject_mask(source, threshold)
    pixels = [
        source.getpixel((x, y))
        for y in range(source.height)
        for x in range(source.width)
        if mask.getpixel((x, y))
    ]
    if not pixels:
        raise ValueError("Canonical reference art contains no subject pixels")

    side = math.ceil(math.sqrt(len(pixels)))
    sample = Image.new("RGB", (side, side), pixels[-1])
    sample.putdata(pixels + [pixels[-1]] * (side * side - len(pixels)))
    quantized = sample.quantize(
        colors=color_count,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    raw_palette = quantized.getpalette()
    used_indexes = sorted(set(quantized.getdata()))
    candidates = sorted(
        {
            tuple(raw_palette[index * 3 : index * 3 + 3])
            for index in used_indexes
        }
    )
    colors = list(REQUIRED_COLORS)
    colors.extend(color for color in candidates if color not in colors)
    colors = colors[:color_count]
    if len(colors) != color_count:
        raise ValueError(
            f"Palette build produced {len(colors)} unique colors, expected {color_count}"
        )
    encoded_colors = json.dumps(colors, separators=(",", ":")).encode("utf-8")
    return {
        "schema": "wizardjoe_canonical_palette_v1",
        "schema_version": 1,
        "palette_id": f"wizardjoe_canonical_{color_count}_v1",
        "source": str(source_path.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "subject_threshold": threshold,
        "color_count": color_count,
        "colors_sha256": hashlib.sha256(encoded_colors).hexdigest(),
        "colors": [list(color) for color in colors],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the canonical Wizard Joe runtime palette."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--colors", type=int, default=64)
    parser.add_argument("--threshold", type=float, default=30.0)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    payload = build_palette(
        args.source.resolve(),
        color_count=args.colors,
        threshold=args.threshold,
    )
    serialized = json.dumps(payload, indent=2) + "\n"
    if args.check:
        current = args.output.read_text(encoding="utf-8")
        if current != serialized:
            raise SystemExit(f"{args.output} does not match the canonical palette build")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(
        json.dumps(
            {
                "palette_id": payload["palette_id"],
                "color_count": payload["color_count"],
                "output": str(args.output),
                "checked": args.check,
            }
        )
    )


if __name__ == "__main__":
    main()
