#!/usr/bin/env python3
"""Create one Kingfisher open-beak mate by rotating its original lower mandible."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _points(values: list[int], *, name: str) -> list[tuple[int, int]]:
    if len(values) < 6 or len(values) % 2:
        raise ValueError(f"{name} must contain at least three x/y points")
    return list(zip(values[0::2], values[1::2]))


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


def _write_png_atomic(path: Path, image: Image.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        image.save(temporary, format="PNG")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _binary_alpha(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A").point(lambda value: 255 if value >= 16 else 0)
    rgba.putalpha(alpha)
    return rgba


def articulate_lower_mandible(
    resting_path: Path,
    output_path: Path,
    receipt_path: Path,
    *,
    mandible_polygon: list[tuple[int, int]],
    cavity_polygon: list[tuple[int, int]],
    hinge: tuple[int, int],
    rotation_degrees: float,
    cavity_fill: tuple[int, int, int, int] = (12, 9, 12, 255),
    tongue_polygon: list[tuple[int, int]] | None = None,
    tongue_fill: tuple[int, int, int, int] = (116, 42, 42, 255),
) -> dict[str, object]:
    resting_path = resting_path.resolve()
    output_path = output_path.resolve()
    receipt_path = receipt_path.resolve()
    with Image.open(resting_path) as loaded:
        resting = loaded.convert("RGBA")
    width, height = resting.size
    for name, polygon in (
        ("mandible_polygon", mandible_polygon),
        ("cavity_polygon", cavity_polygon),
    ):
        if any(not (0 <= x < width and 0 <= y < height) for x, y in polygon):
            raise ValueError(f"{name} must remain inside the canvas")
    if not (0 <= hinge[0] < width and 0 <= hinge[1] < height):
        raise ValueError("hinge must remain inside the canvas")

    mandible_mask = Image.new("L", resting.size, 0)
    ImageDraw.Draw(mandible_mask).polygon(mandible_polygon, fill=255)
    mandible = Image.new("RGBA", resting.size, (0, 0, 0, 0))
    mandible.paste(resting, mask=mandible_mask)
    rotated = mandible.rotate(
        rotation_degrees,
        resample=Image.Resampling.BICUBIC,
        center=hinge,
        expand=False,
    )
    rotated = _binary_alpha(rotated)

    output = resting.copy()
    draw = ImageDraw.Draw(output)
    draw.polygon(cavity_polygon, fill=cavity_fill)
    if tongue_polygon:
        if any(
            not (0 <= x < width and 0 <= y < height)
            for x, y in tongue_polygon
        ):
            raise ValueError("tongue_polygon must remain inside the canvas")
        draw.polygon(tongue_polygon, fill=tongue_fill)
    output.alpha_composite(rotated)
    output = _binary_alpha(output)

    changed = ImageChops.difference(resting, output)
    changed_bbox = changed.convert("RGB").getbbox()
    if changed_bbox is None:
        raise ValueError("mandible articulation produced no visible change")
    changed_pixels = sum(
        pixel != (0, 0, 0, 0)
        for pixel in changed.getdata()
    )
    if changed_pixels <= 0:
        raise ValueError("mandible articulation produced no changed pixels")

    _write_png_atomic(output_path, output)
    receipt = {
        "schema_version": 1,
        "method": "rotate_original_lower_mandible_about_declared_hinge_v1",
        "approval_state": "candidate_visual_review",
        "runtime_admitted": False,
        "resting_path": resting_path.as_posix(),
        "resting_sha256": _sha256(resting_path),
        "speaking_path": output_path.as_posix(),
        "speaking_sha256": _sha256(output_path),
        "canvas": [width, height],
        "mandible_polygon": [list(point) for point in mandible_polygon],
        "cavity_polygon": [list(point) for point in cavity_polygon],
        "hinge": list(hinge),
        "rotation_degrees": rotation_degrees,
        "cavity_fill_rgba": list(cavity_fill),
        "tongue_polygon": (
            [list(point) for point in tongue_polygon]
            if tongue_polygon
            else None
        ),
        "tongue_fill_rgba": list(tongue_fill) if tongue_polygon else None,
        "changed_bbox": list(changed_bbox),
        "changed_pixels": changed_pixels,
        "upper_beak_policy": "immutable_source_pixels",
    }
    _write_json_atomic(receipt_path, receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resting", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--mandible-polygon", nargs="+", type=int, required=True)
    parser.add_argument("--cavity-polygon", nargs="+", type=int, required=True)
    parser.add_argument("--hinge", nargs=2, type=int, required=True)
    parser.add_argument("--rotation-degrees", type=float, required=True)
    parser.add_argument("--tongue-polygon", nargs="+", type=int)
    args = parser.parse_args()
    receipt = articulate_lower_mandible(
        args.resting,
        args.output,
        args.receipt,
        mandible_polygon=_points(
            args.mandible_polygon,
            name="mandible_polygon",
        ),
        cavity_polygon=_points(
            args.cavity_polygon,
            name="cavity_polygon",
        ),
        hinge=(args.hinge[0], args.hinge[1]),
        rotation_degrees=args.rotation_degrees,
        tongue_polygon=(
            _points(args.tongue_polygon, name="tongue_polygon")
            if args.tongue_polygon
            else None
        ),
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
