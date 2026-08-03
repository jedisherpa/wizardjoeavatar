#!/usr/bin/env python3
"""Build one body-locked Kingfisher speaking mate from a matched render."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.compose_kingfisher_pair_render import (
    CANVAS_SIZE,
    _binary_alpha,
    load_render_alpha,
)


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
        image.save(temporary, format="PNG", optimize=True)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _polygon_mask(
    size: tuple[int, int],
    polygon: list[tuple[int, int]],
) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    return mask


def _component_stats(mask: Image.Image) -> tuple[int, int, list[set[tuple[int, int]]]]:
    pixels = mask.load()
    width, height = mask.size
    remaining = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if pixels[x, y]
    }
    components: list[set[tuple[int, int]]] = []
    while remaining:
        seed = remaining.pop()
        component = {seed}
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
                    component.add(neighbor)
                    queue.append(neighbor)
        components.append(component)
    components.sort(key=len, reverse=True)
    total = sum(len(component) for component in components)
    largest = len(components[0]) if components else 0
    return total, largest, components


def compose_mandible_patch(
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
    rotation_degrees: float = 0.0,
    rotation_center: tuple[int, int] | None = None,
    mandible_polygon: list[tuple[int, int]],
    cavity_polygon: list[tuple[int, int]],
    upper_beak_polygon: list[tuple[int, int]],
    hinge: tuple[int, int],
    residual_clear_polygon: list[tuple[int, int]] | None = None,
    hinge_radius: int = 6,
    minimum_mandible_height: int = 8,
    minimum_connected_ratio: float = 0.9,
    cavity_fill: tuple[int, int, int, int] = (10, 13, 16, 255),
    cavity_source: str = "solid",
) -> dict[str, object]:
    """Composite only a matched lower mandible onto an immutable body."""
    with Image.open(resting_path) as loaded:
        resting = loaded.convert("RGBA")
    if resting.size != CANVAS_SIZE:
        raise ValueError("canonical Kingfisher frame must use 960 x 540")
    if scale <= 0:
        raise ValueError("render alignment scale must be positive")
    effective_scale_x = scale if scale_x is None else scale_x
    effective_scale_y = scale if scale_y is None else scale_y
    if effective_scale_x <= 0 or effective_scale_y <= 0:
        raise ValueError("render alignment scales must be positive")
    for name, polygon in (
        ("mandible_polygon", mandible_polygon),
        ("cavity_polygon", cavity_polygon),
        ("upper_beak_polygon", upper_beak_polygon),
    ):
        if len(polygon) < 3:
            raise ValueError(f"{name} requires at least three points")
        if any(
            x < 0 or y < 0 or x >= CANVAS_SIZE[0] or y >= CANVAS_SIZE[1]
            for x, y in polygon
        ):
            raise ValueError(f"{name} must remain inside the canvas")
    if residual_clear_polygon is not None:
        if len(residual_clear_polygon) < 3:
            raise ValueError(
                "residual_clear_polygon requires at least three points"
            )
        if any(
            x < 0 or y < 0 or x >= CANVAS_SIZE[0] or y >= CANVAS_SIZE[1]
            for x, y in residual_clear_polygon
        ):
            raise ValueError(
                "residual_clear_polygon must remain inside the canvas"
            )
    if not (
        0 <= hinge[0] < CANVAS_SIZE[0]
        and 0 <= hinge[1] < CANVAS_SIZE[1]
    ):
        raise ValueError("hinge must remain inside the canvas")
    if hinge_radius < 1:
        raise ValueError("hinge radius must be positive")
    if minimum_mandible_height < 1:
        raise ValueError("minimum mandible height must be positive")
    if not 0 < minimum_connected_ratio <= 1:
        raise ValueError("minimum connected ratio must be in (0, 1]")
    if cavity_source not in {
        "solid",
        "solid_overlay",
        "solid_generated_overlay",
        "generated",
        "generated_overlay",
    }:
        raise ValueError(
            "cavity source must be solid, solid_overlay, "
            "solid_generated_overlay, generated, or generated_overlay"
        )

    generated = load_render_alpha(generated_path)
    target_size = (
        max(1, round(generated.width * effective_scale_x)),
        max(1, round(generated.height * effective_scale_y)),
    )
    generated = _binary_alpha(
        generated.resize(target_size, Image.Resampling.LANCZOS)
    )
    aligned = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    aligned.alpha_composite(generated, (translate_x, translate_y))
    effective_rotation_center = rotation_center or hinge
    if not (
        0 <= effective_rotation_center[0] < CANVAS_SIZE[0]
        and 0 <= effective_rotation_center[1] < CANVAS_SIZE[1]
    ):
        raise ValueError("rotation center must remain inside the canvas")
    if rotation_degrees:
        aligned = _binary_alpha(
            aligned.rotate(
                rotation_degrees,
                resample=Image.Resampling.BICUBIC,
                center=effective_rotation_center,
            )
        )

    mandible_mask = _polygon_mask(CANVAS_SIZE, mandible_polygon)
    source_alpha = ImageChops.multiply(
        aligned.getchannel("A"),
        mandible_mask,
    )
    mandible_bbox = source_alpha.getbbox()
    if mandible_bbox is None:
        raise ValueError("declared mandible polygon contains no source pixels")
    if mandible_bbox[3] - mandible_bbox[1] < minimum_mandible_height:
        raise ValueError("source mandible is too thin")

    total_pixels, largest_component, components = _component_stats(source_alpha)
    connected_ratio = (
        largest_component / total_pixels if total_pixels else 0.0
    )
    if connected_ratio < minimum_connected_ratio:
        raise ValueError("source mandible contains detached geometry")
    hinge_pixels = {
        (x, y)
        for x in range(
            max(0, hinge[0] - hinge_radius),
            min(CANVAS_SIZE[0], hinge[0] + hinge_radius + 1),
        )
        for y in range(
            max(0, hinge[1] - hinge_radius),
            min(CANVAS_SIZE[1], hinge[1] + hinge_radius + 1),
        )
        if (x - hinge[0]) ** 2 + (y - hinge[1]) ** 2
        <= hinge_radius**2
    }
    if not components or not components[0].intersection(hinge_pixels):
        raise ValueError("source mandible does not connect to the hinge")

    mandible_patch = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    mandible_patch.paste(aligned, mask=source_alpha)
    output = resting.copy()
    residual_clear_mask = Image.new("L", CANVAS_SIZE, 0)
    if residual_clear_polygon is not None:
        residual_clear_mask = _polygon_mask(
            CANVAS_SIZE,
            residual_clear_polygon,
        )
        output.paste(
            Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0)),
            mask=residual_clear_mask,
        )
    output.alpha_composite(mandible_patch)
    # The generated render is only a lower-mandible donor. Paint the neutral
    # cavity after it so donor tongues, teeth, highlights, or throat pixels
    # cannot leak back into the admitted speaking frame.
    cavity_mask = _polygon_mask(CANVAS_SIZE, cavity_polygon)
    if cavity_source == "solid":
        output.paste(
            Image.new("RGBA", CANVAS_SIZE, cavity_fill),
            mask=cavity_mask,
        )

    upper_beak_mask = _polygon_mask(CANVAS_SIZE, upper_beak_polygon)
    output = Image.composite(resting, output, upper_beak_mask)
    if cavity_source in {"solid_overlay", "solid_generated_overlay"}:
        output.paste(
            Image.new("RGBA", CANVAS_SIZE, cavity_fill),
            mask=cavity_mask,
        )
    if cavity_source in {"generated_overlay", "solid_generated_overlay"}:
        cavity_alpha = ImageChops.multiply(
            aligned.getchannel("A"),
            cavity_mask,
        )
        output.paste(aligned, mask=cavity_alpha)
    output = _binary_alpha(output)

    allowed_mask = ImageChops.lighter(
        ImageChops.lighter(
            ImageChops.lighter(mandible_mask, cavity_mask),
            upper_beak_mask,
        ),
        residual_clear_mask,
    )
    difference = ImageChops.difference(resting, output)
    changed_mask = difference.getchannel("A")
    for channel in difference.convert("RGB").split():
        changed_mask = ImageChops.lighter(changed_mask, channel)
    changed_mask = changed_mask.point(lambda value: 255 if value else 0)
    changed_bbox = changed_mask.getbbox()
    if changed_bbox is None:
        raise ValueError("mandible patch produced no visible change")
    outside_mask = ImageChops.invert(allowed_mask)
    if ImageChops.multiply(changed_mask, outside_mask).getbbox() is not None:
        raise ValueError("mandible patch changed pixels outside its masks")

    _write_png_atomic(output_path, output)
    receipt = {
        "schema_version": 1,
        "method": "pair_specific_connected_mandible_patch_v1",
        "approval_state": "candidate_visual_review",
        "runtime_admitted": False,
        "canvas": list(CANVAS_SIZE),
        "resting_path": resting_path.as_posix(),
        "resting_sha256": _sha256(resting_path),
        "generated_render_path": generated_path.as_posix(),
        "generated_render_sha256": _sha256(generated_path),
        "speaking_path": output_path.as_posix(),
        "speaking_sha256": _sha256(output_path),
        "alignment": {
            "scale": scale,
            "scale_x": effective_scale_x,
            "scale_y": effective_scale_y,
            "translate_x": translate_x,
            "translate_y": translate_y,
            "rotation_degrees": rotation_degrees,
            "rotation_center": list(effective_rotation_center),
            "interpolation": "lanczos_rgb_binary_alpha",
        },
        "mandible_polygon": [list(point) for point in mandible_polygon],
        "cavity_polygon": [list(point) for point in cavity_polygon],
        "upper_beak_polygon": [
            list(point) for point in upper_beak_polygon
        ],
        "residual_clear_polygon": (
            [list(point) for point in residual_clear_polygon]
            if residual_clear_polygon is not None
            else None
        ),
        "hinge": list(hinge),
        "hinge_radius": hinge_radius,
        "minimum_mandible_height": minimum_mandible_height,
        "minimum_connected_ratio": minimum_connected_ratio,
        "cavity_source": cavity_source,
        "cavity_fill_rgba": (
            list(cavity_fill)
            if cavity_source
            in {"solid", "solid_overlay", "solid_generated_overlay"}
            else None
        ),
        "mandible_bbox": list(mandible_bbox),
        "mandible_opaque_pixels": total_pixels,
        "mandible_largest_component_pixels": largest_component,
        "mandible_connected_ratio": round(connected_ratio, 6),
        "changed_bbox": list(changed_bbox),
        "outside_articulation_change": False,
        "upper_beak_policy": "immutable_source_pixels",
    }
    _write_json_atomic(receipt_path, receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create one Kingfisher speaking mate from a matched lower-"
            "mandible render while preserving the canonical body and upper beak."
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
    parser.add_argument("--rotation-degrees", type=float, default=0.0)
    parser.add_argument("--rotation-center", nargs=2, type=int)
    parser.add_argument("--mandible-polygon", nargs="+", type=int, required=True)
    parser.add_argument("--cavity-polygon", nargs="+", type=int, required=True)
    parser.add_argument("--upper-beak-polygon", nargs="+", type=int, required=True)
    parser.add_argument("--residual-clear-polygon", nargs="+", type=int)
    parser.add_argument("--hinge", nargs=2, type=int, required=True)
    parser.add_argument("--hinge-radius", type=int, default=6)
    parser.add_argument("--minimum-mandible-height", type=int, default=8)
    parser.add_argument("--minimum-connected-ratio", type=float, default=0.9)
    parser.add_argument(
        "--cavity-fill",
        nargs=4,
        type=int,
        metavar=("R", "G", "B", "A"),
        default=(10, 13, 16, 255),
    )
    parser.add_argument(
        "--cavity-source",
        choices=(
            "solid",
            "solid_overlay",
            "solid_generated_overlay",
            "generated",
            "generated_overlay",
        ),
        default="solid",
    )
    args = parser.parse_args()
    receipt = compose_mandible_patch(
        args.resting,
        args.generated,
        args.output,
        args.receipt,
        scale=args.scale,
        scale_x=args.scale_x,
        scale_y=args.scale_y,
        translate_x=args.translate_x,
        translate_y=args.translate_y,
        rotation_degrees=args.rotation_degrees,
        rotation_center=(
            (args.rotation_center[0], args.rotation_center[1])
            if args.rotation_center
            else None
        ),
        mandible_polygon=_points(
            args.mandible_polygon,
            name="mandible_polygon",
        ),
        cavity_polygon=_points(
            args.cavity_polygon,
            name="cavity_polygon",
        ),
        upper_beak_polygon=_points(
            args.upper_beak_polygon,
            name="upper_beak_polygon",
        ),
        residual_clear_polygon=(
            _points(
                args.residual_clear_polygon,
                name="residual_clear_polygon",
            )
            if args.residual_clear_polygon
            else None
        ),
        hinge=(args.hinge[0], args.hinge[1]),
        hinge_radius=args.hinge_radius,
        minimum_mandible_height=args.minimum_mandible_height,
        minimum_connected_ratio=args.minimum_connected_ratio,
        cavity_fill=tuple(args.cavity_fill),
        cavity_source=args.cavity_source,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
