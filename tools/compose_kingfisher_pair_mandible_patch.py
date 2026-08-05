#!/usr/bin/env python3
"""Build one body-locked Kingfisher speaking mate from a matched render."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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


def beak_anatomy_metrics(
    *,
    hinge: tuple[int, int],
    hinge_radius: int,
    upper_beak_polygon: list[tuple[int, int]],
    mandible_polygon: list[tuple[int, int]],
    cavity_polygon: list[tuple[int, int]],
) -> dict[str, object]:
    """Measure whether a lower beak is anchored to its canonical upper beak."""

    def anchor_distance(polygon: list[tuple[int, int]]) -> float:
        distances: list[float] = []
        for start, end in zip(polygon, polygon[1:] + polygon[:1]):
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            if dx == 0 and dy == 0:
                distances.append(
                    math.hypot(hinge[0] - start[0], hinge[1] - start[1])
                )
                continue
            projection = (
                (hinge[0] - start[0]) * dx
                + (hinge[1] - start[1]) * dy
            ) / (dx * dx + dy * dy)
            projection = min(1.0, max(0.0, projection))
            closest_x = start[0] + projection * dx
            closest_y = start[1] + projection * dy
            distances.append(
                math.hypot(hinge[0] - closest_x, hinge[1] - closest_y)
            )
        return min(distances)

    def bounds(polygon: list[tuple[int, int]]) -> tuple[int, int, int, int]:
        xs = [point[0] for point in polygon]
        ys = [point[1] for point in polygon]
        return min(xs), min(ys), max(xs), max(ys)

    upper_bounds = bounds(upper_beak_polygon)
    mandible_bounds = bounds(mandible_polygon)
    upper_left_reach = hinge[0] - upper_bounds[0]
    upper_right_reach = upper_bounds[2] - hinge[0]
    dominant_reach = max(upper_left_reach, upper_right_reach)
    opposite_reach = min(upper_left_reach, upper_right_reach)
    directional = dominant_reach >= max(12, opposite_reach * 1.8)

    checks = {
        "upper_beak_anchored": (
            anchor_distance(upper_beak_polygon) <= hinge_radius + 4
        ),
        "mandible_anchored": (
            anchor_distance(mandible_polygon) <= hinge_radius + 4
        ),
        "cavity_anchored": (
            anchor_distance(cavity_polygon) <= max(24, hinge_radius + 6)
        ),
    }
    metrics: dict[str, object] = {
        "schema_version": 1,
        "mode": "directional" if directional else "frontal",
        "upper_anchor_distance": round(
            anchor_distance(upper_beak_polygon), 3
        ),
        "mandible_anchor_distance": round(
            anchor_distance(mandible_polygon), 3
        ),
        "cavity_anchor_distance": round(
            anchor_distance(cavity_polygon), 3
        ),
    }

    if directional:
        direction = 1 if upper_right_reach > upper_left_reach else -1

        def reach(polygon: list[tuple[int, int]], sign: int) -> int:
            return max(sign * (point[0] - hinge[0]) for point in polygon)

        mandible_forward_reach = reach(mandible_polygon, direction)
        mandible_reverse_reach = reach(mandible_polygon, -direction)
        upper_forward_reach = reach(upper_beak_polygon, direction)
        upper_tip_points = [
            point
            for point in upper_beak_polygon
            if direction * (point[0] - hinge[0]) >= upper_forward_reach - 2
        ]
        mandible_tip_points = [
            point
            for point in mandible_polygon
            if direction * (point[0] - hinge[0]) >= mandible_forward_reach - 2
        ]
        upper_tip_y = sum(point[1] for point in upper_tip_points) / len(
            upper_tip_points
        )
        mandible_tip_y = sum(point[1] for point in mandible_tip_points) / len(
            mandible_tip_points
        )
        length_ratio = mandible_forward_reach / max(1, upper_forward_reach)
        tip_offset_ratio = abs(mandible_tip_y - upper_tip_y) / max(
            1, upper_forward_reach
        )
        checks.update(
            {
                "same_longitudinal_direction": (
                    mandible_forward_reach > mandible_reverse_reach
                ),
                "plausible_mandible_length": 0.5 <= length_ratio <= 1.25,
                "bounded_tip_offset": tip_offset_ratio <= 0.6,
            }
        )
        metrics.update(
            {
                "direction": "right" if direction == 1 else "left",
                "upper_forward_reach": upper_forward_reach,
                "mandible_forward_reach": mandible_forward_reach,
                "mandible_reverse_reach": mandible_reverse_reach,
                "mandible_length_ratio": round(length_ratio, 4),
                "tip_offset_ratio": round(tip_offset_ratio, 4),
            }
        )
    else:
        upper_width = upper_bounds[2] - upper_bounds[0]
        mandible_width = mandible_bounds[2] - mandible_bounds[0]
        upper_center_x = (upper_bounds[0] + upper_bounds[2]) / 2
        mandible_center_x = (mandible_bounds[0] + mandible_bounds[2]) / 2
        center_offset_ratio = abs(mandible_center_x - upper_center_x) / max(
            1, upper_width
        )
        width_ratio = mandible_width / max(1, upper_width)
        checks.update(
            {
                "centered_frontal_mandible": center_offset_ratio <= 0.25,
                "plausible_frontal_width": 0.5 <= width_ratio <= 1.5,
                "mandible_below_upper_beak": (
                    mandible_bounds[3] >= upper_bounds[3]
                ),
            }
        )
        metrics.update(
            {
                "center_offset_ratio": round(center_offset_ratio, 4),
                "mandible_width_ratio": round(width_ratio, 4),
            }
        )

    metrics["checks"] = checks
    metrics["passed"] = all(checks.values())
    return metrics


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


def _source_color_mask(
    image: Image.Image,
    *,
    mode: str,
    light_threshold: int,
    neutral_chroma_threshold: int,
) -> Image.Image:
    """Return donor pixels eligible for a compact mouth-only transfer."""
    alpha = image.getchannel("A")
    if mode == "opaque":
        return alpha
    if mode != "exclude_light_neutral":
        raise ValueError("unsupported source mask mode")

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


def _replace_warm_oral_pixels(
    image: Image.Image,
    replacement: tuple[int, int, int, int] | None,
    region_mask: Image.Image | None = None,
) -> Image.Image:
    """Neutralize donor tongue/palate colors without touching orange plumage."""
    if replacement is None:
        return image
    output = image.copy()
    region = (
        list(region_mask.getdata())
        if region_mask is not None
        else [0] * (image.width * image.height)
    )
    output.putdata(
        [
            replacement
            if (
                a
                and (
                    (
                        inside
                        and r >= 40
                        and r >= g + 15
                        and r >= b + 15
                    )
                    or (
                        not inside
                        and r >= 64
                        and r >= g + 30
                        and r >= b + 30
                        and b >= round(g * 0.75)
                    )
                )
            )
            else (r, g, b, a)
            for (r, g, b, a), inside in zip(image.getdata(), region)
        ]
    )
    return output


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
    source_mask_mode: str = "opaque",
    source_light_threshold: int = 180,
    source_neutral_chroma_threshold: int = 36,
    oral_warm_replacement: tuple[int, int, int, int] | None = None,
    oral_warm_replacement_polygon: list[tuple[int, int]] | None = None,
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
    if source_mask_mode not in {"opaque", "exclude_light_neutral"}:
        raise ValueError(
            "source mask mode must be opaque or exclude_light_neutral"
        )
    if not 0 <= source_light_threshold <= 255:
        raise ValueError("source light threshold must be in [0, 255]")
    if not 0 <= source_neutral_chroma_threshold <= 255:
        raise ValueError(
            "source neutral chroma threshold must be in [0, 255]"
        )
    if oral_warm_replacement is not None and any(
        not 0 <= value <= 255 for value in oral_warm_replacement
    ):
        raise ValueError("oral warm replacement channels must be in [0, 255]")
    if oral_warm_replacement_polygon is not None:
        if len(oral_warm_replacement_polygon) < 3:
            raise ValueError(
                "oral_warm_replacement_polygon requires at least three points"
            )
        if any(
            x < 0 or y < 0 or x >= CANVAS_SIZE[0] or y >= CANVAS_SIZE[1]
            for x, y in oral_warm_replacement_polygon
        ):
            raise ValueError(
                "oral_warm_replacement_polygon must remain inside the canvas"
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
    oral_replacement_mask = (
        _polygon_mask(CANVAS_SIZE, oral_warm_replacement_polygon)
        if oral_warm_replacement_polygon is not None
        else None
    )
    aligned = _replace_warm_oral_pixels(
        aligned,
        oral_warm_replacement,
        oral_replacement_mask,
    )

    source_color_mask = _source_color_mask(
        aligned,
        mode=source_mask_mode,
        light_threshold=source_light_threshold,
        neutral_chroma_threshold=source_neutral_chroma_threshold,
    )
    mandible_mask = _polygon_mask(CANVAS_SIZE, mandible_polygon)
    source_alpha = ImageChops.multiply(
        source_color_mask,
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

    anatomy = beak_anatomy_metrics(
        hinge=hinge,
        hinge_radius=hinge_radius,
        upper_beak_polygon=upper_beak_polygon,
        mandible_polygon=mandible_polygon,
        cavity_polygon=cavity_polygon,
    )
    if anatomy["passed"] is not True:
        failed = [
            name
            for name, passed in anatomy["checks"].items()
            if passed is not True
        ]
        raise ValueError(
            "beak anatomy is misaligned: " + ", ".join(failed)
        )

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
            source_color_mask,
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
        "source_mask": {
            "mode": source_mask_mode,
            "light_threshold": source_light_threshold,
            "neutral_chroma_threshold": source_neutral_chroma_threshold,
        },
        "oral_warm_replacement_rgba": (
            list(oral_warm_replacement)
            if oral_warm_replacement is not None
            else None
        ),
        "oral_warm_replacement_polygon": (
            [list(point) for point in oral_warm_replacement_polygon]
            if oral_warm_replacement_polygon is not None
            else None
        ),
        "mandible_bbox": list(mandible_bbox),
        "mandible_opaque_pixels": total_pixels,
        "mandible_largest_component_pixels": largest_component,
        "mandible_connected_ratio": round(connected_ratio, 6),
        "changed_bbox": list(changed_bbox),
        "outside_articulation_change": False,
        "upper_beak_policy": "immutable_source_pixels",
        "beak_anatomy": anatomy,
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
    parser.add_argument(
        "--source-mask-mode",
        choices=("opaque", "exclude_light_neutral"),
        default="opaque",
    )
    parser.add_argument("--source-light-threshold", type=int, default=180)
    parser.add_argument(
        "--source-neutral-chroma-threshold",
        type=int,
        default=36,
    )
    parser.add_argument(
        "--oral-warm-replacement",
        nargs=4,
        type=int,
        metavar=("R", "G", "B", "A"),
    )
    parser.add_argument(
        "--oral-warm-replacement-polygon",
        nargs="+",
        type=int,
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
        source_mask_mode=args.source_mask_mode,
        source_light_threshold=args.source_light_threshold,
        source_neutral_chroma_threshold=(
            args.source_neutral_chroma_threshold
        ),
        oral_warm_replacement=(
            tuple(args.oral_warm_replacement)
            if args.oral_warm_replacement is not None
            else None
        ),
        oral_warm_replacement_polygon=(
            _points(
                args.oral_warm_replacement_polygon,
                name="oral_warm_replacement_polygon",
            )
            if args.oral_warm_replacement_polygon
            else None
        ),
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
