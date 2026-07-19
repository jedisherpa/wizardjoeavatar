#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from generate_reference_avatar_cells import ROOT, generate

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.compositor import CellCanvas
from wizard_avatar.glyphs import glyph
from wizard_avatar.pose_compositor import (
    author_cast_staff_graph,
    composite_anchor_transition,
)


DEFAULT_MANIFEST = ROOT / "assets" / "reference" / "motion_sources" / "manifest.json"
DEFAULT_OUTPUT = ROOT / "wizard_avatar" / "definitions" / "reference_avatar_pose_cells.json"
REQUIRED_ANCHORS = (
    "root",
    "mouth",
    "left_eye",
    "right_eye",
    "left_foot",
    "right_foot",
    "left_hand",
    "right_hand",
    "staff_hand",
    "staff_tip",
)


def stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def point_from(value: object, *, field_name: str) -> list[int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{field_name} must be a two-item coordinate list")
    return [int(value[0]), int(value[1])]


def resolve_anchors(
    manifest: dict[str, Any],
    pose: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, list[int]]:
    root = point_from(payload["root_anchor"], field_name=f"{pose['id']}.root_anchor")
    offsets = dict(manifest.get("default_anchor_offsets", {}))
    offsets.update(pose.get("anchor_offsets", {}))
    offsets.update(pose.get("anchors", {}))

    anchors: dict[str, list[int]] = {"root": root}
    for name, offset in offsets.items():
        offset_point = point_from(offset, field_name=f"{pose['id']}.anchors.{name}")
        anchors[name] = [root[0] + offset_point[0], root[1] + offset_point[1]]
    anchors["root"] = root

    missing = [name for name in REQUIRED_ANCHORS if name not in anchors]
    if missing:
        raise ValueError(f"{pose['id']} missing required anchors: {', '.join(missing)}")
    return {name: anchors[name] for name in sorted(anchors)}


def palette_summary(poses: list[dict[str, Any]], palette_id: str) -> dict[str, Any]:
    colors = sorted(
        {
            tuple(int(channel) for channel in cell["rgb"])
            for pose in poses
            for cell in pose["cells"]
        }
    )
    encoded = json.dumps(colors, separators=(",", ":")).encode("utf-8")
    return {
        "id": palette_id,
        "hash": f"sha256:{hashlib.sha256(encoded).hexdigest()}",
        "unique_color_count": len(colors),
    }


def canonical_config(
    manifest: dict[str, Any],
    raw_payloads: list[dict[str, Any]],
    rows: int,
) -> dict[str, Any]:
    requested = dict(manifest.get("canonical", {}))
    canonical_rows = int(requested.get("rows", rows))
    baseline_y = int(requested.get("baseline_y", canonical_rows - 1))
    cols = int(requested.get("cols", max(int(payload["cols"]) for payload in raw_payloads)))
    root_anchor = requested.get("root_anchor", [cols // 2, baseline_y])
    root = point_from(root_anchor, field_name="canonical.root_anchor")
    if root[0] < 0 or root[0] >= cols:
        raise ValueError("canonical.root_anchor x is outside canonical cols")
    if root[1] < 0 or root[1] >= canonical_rows:
        raise ValueError("canonical.root_anchor y is outside canonical rows")
    return {
        **requested,
        "rows": canonical_rows,
        "cols": cols,
        "baseline_y": baseline_y,
        "root_anchor": root,
        "root_anchor_strategy": requested.get("root_anchor_strategy", "fixed_canonical_root_v1"),
        "crop_strategy": requested.get(
            "crop_strategy",
            "per_pose_subject_crop_then_canonical_canvas_v1",
        ),
    }


def normalize_payload_to_canonical(
    pose: dict[str, Any],
    payload: dict[str, Any],
    canonical: dict[str, Any],
) -> dict[str, Any]:
    root = point_from(payload["root_anchor"], field_name=f"{pose['id']}.root_anchor")
    canonical_root = point_from(canonical["root_anchor"], field_name="canonical.root_anchor")
    dx = canonical_root[0] - root[0]
    dy = canonical_root[1] - root[1]
    cols = int(canonical["cols"])
    rows = int(canonical["rows"])
    normalized_cells = []
    for cell in payload["cells"]:
        x = int(cell["x"]) + dx
        y = int(cell["y"]) + dy
        if not (0 <= x < cols and 0 <= y < rows):
            raise ValueError(
                f"{pose['id']} cell shifted outside canonical canvas: "
                f"({cell['x']}, {cell['y']}) -> ({x}, {y})"
            )
        normalized_cells.append({**cell, "x": x, "y": y})
    return {
        **payload,
        "cols": cols,
        "rows": rows,
        "root_anchor": canonical_root,
        "canonical_shift": [dx, dy],
        "cells": normalized_cells,
    }


def payload_canvas(payload: dict[str, Any]) -> CellCanvas:
    canvas = CellCanvas(int(payload["cols"]), int(payload["rows"]))
    for cell in payload["cells"]:
        canvas.set(
            int(cell["x"]),
            int(cell["y"]),
            glyph("solid_fill"),
            tuple(int(channel) for channel in cell["rgb"]),
            str(cell.get("region", "")),
        )
    return canvas


def canvas_cells(canvas: CellCanvas) -> list[dict[str, Any]]:
    cells = []
    for y, row in enumerate(canvas.cells):
        for x, cell in enumerate(row):
            if cell is None:
                continue
            payload = {"x": x, "y": y, "rgb": list(cell.rgb)}
            if cell.layer_id:
                payload["region"] = cell.layer_id
            cells.append(payload)
    return cells


def derive_blend_payload(
    pose: dict[str, Any],
    normalized_payloads: dict[str, dict[str, Any]],
    canonical: dict[str, Any],
    colors: int,
    coverage_threshold: int,
) -> dict[str, Any]:
    blend = pose.get("derived_blend")
    if not isinstance(blend, dict):
        raise ValueError(f"{pose['id']}.derived_blend must be an object")
    from_pose_id = str(blend.get("from_pose_id", ""))
    to_pose_id = str(blend.get("to_pose_id", ""))
    if from_pose_id == to_pose_id:
        raise ValueError(f"{pose['id']} blend endpoints must be different")
    try:
        from_payload = normalized_payloads[from_pose_id]
        to_payload = normalized_payloads[to_pose_id]
    except KeyError as error:
        raise ValueError(
            f"{pose['id']} blend endpoint {error.args[0]!r} is not an authored pose"
        ) from error
    progress = float(blend.get("progress", 0.5))
    if not 0.0 < progress < 1.0:
        raise ValueError(f"{pose['id']}.derived_blend.progress must be between 0 and 1")

    canvas, root = composite_anchor_transition(
        payload_canvas(from_payload),
        payload_canvas(to_payload),
        tuple(from_payload["root_anchor"]),
        tuple(to_payload["root_anchor"]),
        progress,
    )
    expected_size = (int(canonical["cols"]), int(canonical["rows"]))
    if (canvas.width, canvas.height) != expected_size or root != tuple(canonical["root_anchor"]):
        raise ValueError(f"{pose['id']} blend escaped the canonical canvas or root")
    target_atomic_x_min = blend.get("target_atomic_x_min")
    if target_atomic_x_min is not None:
        target_atomic_x_min = int(target_atomic_x_min)
        if not 0 <= target_atomic_x_min < canvas.width:
            raise ValueError(f"{pose['id']}.target_atomic_x_min is outside the canvas")
        target_canvas = payload_canvas(to_payload)
        for y in range(canvas.height):
            for x in range(target_atomic_x_min, canvas.width):
                canvas.cells[y][x] = target_canvas.get(x, y)
    return {
        "source": f"derived:{from_pose_id}+{to_pose_id}@{progress:g}",
        "source_size": list(expected_size),
        "source_crop": [0, 0, expected_size[0], expected_size[1]],
        "canonical_shift": [0, 0],
        "generation_rows": int(canonical["rows"]),
        "cols": canvas.width,
        "rows": canvas.height,
        "root_anchor": list(root),
        "quantized_colors": colors,
        "coverage_threshold": coverage_threshold,
        "cells": canvas_cells(canvas),
    }


def derive_cast_rig_payload(
    pose: dict[str, Any],
    normalized_payloads: dict[str, dict[str, Any]],
    canonical: dict[str, Any],
    colors: int,
    coverage_threshold: int,
) -> dict[str, Any]:
    rig = pose.get("derived_cast_rig")
    if not isinstance(rig, dict):
        raise ValueError(f"{pose['id']}.derived_cast_rig must be an object")
    base_pose_id = str(rig.get("base_pose_id", ""))
    try:
        base_payload = normalized_payloads[base_pose_id]
    except KeyError as error:
        raise ValueError(
            f"{pose['id']} cast rig base {base_pose_id!r} is not an authored pose"
        ) from error

    root = point_from(base_payload["root_anchor"], field_name=f"{pose['id']}.root")

    def absolute_offset(field_name: str) -> tuple[int, int]:
        offset = point_from(rig[field_name], field_name=f"{pose['id']}.{field_name}")
        return root[0] + offset[0], root[1] + offset[1]

    source_tip = absolute_offset("source_staff_tip_offset")
    source_hand = absolute_offset("source_staff_hand_offset")
    target_tip = absolute_offset("target_staff_tip_offset")
    target_hand = absolute_offset("target_staff_hand_offset")
    canvas = payload_canvas(base_payload)
    author_cast_staff_graph(
        canvas,
        source_staff_tip=source_tip,
        source_staff_hand=source_hand,
        root_anchor=tuple(root),
        target_staff_tip=target_tip,
        target_staff_hand=target_hand,
    )
    return {
        "source": (
            f"derived_cast_rig:{base_pose_id}:"
            f"hand={target_hand[0]},{target_hand[1]}:"
            f"tip={target_tip[0]},{target_tip[1]}"
        ),
        "source_size": [int(canonical["cols"]), int(canonical["rows"])],
        "source_crop": [0, 0, int(canonical["cols"]), int(canonical["rows"])],
        "canonical_shift": [0, 0],
        "generation_rows": int(canonical["rows"]),
        "cols": canvas.width,
        "rows": canvas.height,
        "root_anchor": root,
        "quantized_colors": colors,
        "coverage_threshold": coverage_threshold,
        "cells": canvas_cells(canvas),
    }


def generate_pose_library(
    manifest_path: Path,
    output_path: Path,
    rows: int,
    margin: int,
    threshold: float,
    coverage_threshold: int,
    colors: int,
    write_output: bool = True,
    reuse_authored_library_path: Path | None = None,
) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_dir = manifest_path.parent
    requested_cols = int(manifest.get("canonical", {}).get("cols", 0))
    reused_authored: dict[str, dict[str, Any]] = {}
    if reuse_authored_library_path is not None:
        reuse_path = reuse_authored_library_path.resolve()
        reused_library = json.loads(reuse_path.read_text(encoding="utf-8"))
        reused_authored = {
            str(existing["id"]): existing
            for existing in reused_library.get("poses", [])
            if isinstance(existing, dict) and "id" in existing
        }
        if not reused_authored:
            raise ValueError(f"No reusable authored poses found in {reuse_path}")

    raw_entries = []
    authored_poses = [
        pose
        for pose in manifest["poses"]
        if "derived_blend" not in pose and "derived_cast_rig" not in pose
    ]
    for pose in authored_poses:
        if reused_authored:
            try:
                existing = reused_authored[pose["id"]]
            except KeyError as error:
                raise ValueError(
                    f"Reusable library is missing authored pose {pose['id']!r}"
                ) from error
            payload = {
                "source": existing["source"],
                "source_size": existing["source_size"],
                "source_crop": existing["source_crop"],
                "cols": existing["cols"],
                "rows": existing["rows"],
                "root_anchor": existing["root_anchor"],
                "quantized_colors": existing.get("quantized_colors", colors),
                "coverage_threshold": existing.get(
                    "coverage_threshold",
                    coverage_threshold,
                ),
                "cells": existing["cells"],
            }
            generation_rows = int(existing.get("generation_rows", rows))
            raw_entries.append((pose, payload, generation_rows))
            continue
        source_path_value = pose.get("source_path")
        if source_path_value is None:
            source_path = source_dir / pose["source"]
        else:
            source_path = Path(source_path_value)
            if not source_path.is_absolute():
                source_path = ROOT / source_path
        temp_output = output_path.parent / f".{pose['id']}.tmp.json"
        generation_rows = int(pose.get("generation_rows", rows))
        payload = generate(
            source_path,
            temp_output,
            rows=generation_rows,
            margin=margin,
            threshold=threshold,
            coverage_threshold=coverage_threshold,
            colors=colors,
        )
        while requested_cols and int(payload["cols"]) > requested_cols:
            fitted_rows = max(
                1,
                generation_rows * requested_cols // int(payload["cols"]),
            )
            if fitted_rows >= generation_rows:
                fitted_rows = generation_rows - 1
            if fitted_rows < 1:
                raise ValueError(f"{pose['id']} cannot fit the canonical width")
            generation_rows = fitted_rows
            payload = generate(
                source_path,
                temp_output,
                rows=generation_rows,
                margin=margin,
                threshold=threshold,
                coverage_threshold=coverage_threshold,
                colors=colors,
            )
        temp_output.unlink(missing_ok=True)
        raw_entries.append((pose, payload, generation_rows))

    canonical = canonical_config(manifest, [payload for _, payload, _ in raw_entries], rows)
    normalized_payloads = {
        pose["id"]: normalize_payload_to_canonical(pose, raw_payload, canonical)
        for pose, raw_payload, _generation_rows in raw_entries
    }
    generation_rows_by_id = {
        pose["id"]: generation_rows
        for pose, _raw_payload, generation_rows in raw_entries
    }
    poses = []
    for pose in manifest["poses"]:
        if "derived_blend" in pose:
            payload = derive_blend_payload(
                pose,
                normalized_payloads,
                canonical,
                colors,
                coverage_threshold,
            )
            generation_rows = int(payload["generation_rows"])
        elif "derived_cast_rig" in pose:
            payload = derive_cast_rig_payload(
                pose,
                normalized_payloads,
                canonical,
                colors,
                coverage_threshold,
            )
            generation_rows = int(payload["generation_rows"])
        else:
            payload = normalized_payloads[pose["id"]]
            generation_rows = generation_rows_by_id[pose["id"]]
        poses.append(
            {
                "id": pose["id"],
                "description": pose.get("description", ""),
                "source": payload["source"],
                "source_size": payload["source_size"],
                "source_crop": payload["source_crop"],
                "canonical_shift": payload["canonical_shift"],
                "generation_rows": generation_rows,
                "cols": payload["cols"],
                "rows": payload["rows"],
                "root_anchor": payload["root_anchor"],
                **(
                    {
                        "presentation_scale": point_from(
                            pose["presentation_scale"],
                            field_name=f"{pose['id']}.presentation_scale",
                        )
                    }
                    if "presentation_scale" in pose
                    else {}
                ),
                "facing": pose.get("facing", "south"),
                "locomotion": pose.get("locomotion", "idle"),
                "actions": list(pose.get("actions", [])),
                "phase": pose.get("phase"),
                "tags": list(pose.get("tags", [])),
                "anchor_space": "local_cells",
                "anchors": resolve_anchors(manifest, pose, payload),
                "quantized_colors": payload["quantized_colors"],
                "coverage_threshold": payload["coverage_threshold"],
                "cells": payload["cells"],
            }
        )

    library = {
        "schema_version": 2,
        "version": manifest.get("version", 1),
        "asset_set_id": manifest.get("asset_set_id", "wizardjoe-reference-motion-v1"),
        "source_manifest": str(manifest_path.relative_to(ROOT)),
        "canonical": canonical,
        "palette": palette_summary(
            poses,
            manifest.get("palette_id", f"per_pose_quantized_{colors}"),
        ),
        "rows": rows,
        "margin": margin,
        "threshold": threshold,
        "coverage_threshold": coverage_threshold,
        "quantized_colors": colors,
        "poses": poses,
    }
    if write_output:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(stable_json(library), encoding="utf-8")
    return library


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert reference pose PNGs into a square-cell pose library.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rows", type=int, default=96)
    parser.add_argument("--margin", type=int, default=18)
    parser.add_argument("--threshold", type=float, default=30.0)
    parser.add_argument("--coverage-threshold", type=int, default=24)
    parser.add_argument("--colors", type=int, default=64)
    parser.add_argument(
        "--check-deterministic",
        action="store_true",
        help="Generate the pose library twice and fail if the serialized payload differs.",
    )
    parser.add_argument(
        "--reuse-authored-library",
        nargs="?",
        const=DEFAULT_OUTPUT,
        type=Path,
        help=(
            "Reuse authored pose cells from an existing audited library while "
            "rebuilding derived graphs; defaults to the output library"
        ),
    )
    args = parser.parse_args()
    library = generate_pose_library(
        args.manifest,
        args.output,
        rows=args.rows,
        margin=args.margin,
        threshold=args.threshold,
        coverage_threshold=args.coverage_threshold,
        colors=args.colors,
        reuse_authored_library_path=args.reuse_authored_library,
    )
    deterministic_sha256 = hashlib.sha256(stable_json(library).encode("utf-8")).hexdigest()
    if args.check_deterministic:
        second = generate_pose_library(
            args.manifest,
            args.output,
            rows=args.rows,
            margin=args.margin,
            threshold=args.threshold,
            coverage_threshold=args.coverage_threshold,
            colors=args.colors,
            write_output=False,
            reuse_authored_library_path=args.reuse_authored_library,
        )
        second_sha256 = hashlib.sha256(stable_json(second).encode("utf-8")).hexdigest()
        if second_sha256 != deterministic_sha256:
            raise SystemExit(
                "Reference pose generation is not deterministic: "
                f"{deterministic_sha256} != {second_sha256}"
            )
    try:
        output_label = str(args.output.resolve().relative_to(ROOT))
    except ValueError:
        output_label = str(args.output.resolve())
    print(
        json.dumps(
            {
                "source_manifest": library["source_manifest"],
                "output": output_label,
                "schema_version": library["schema_version"],
                "asset_set_id": library["asset_set_id"],
                "sha256": deterministic_sha256,
                "poses": [
                    {
                        "id": pose["id"],
                        "facing": pose["facing"],
                        "locomotion": pose["locomotion"],
                        "cols": pose["cols"],
                        "rows": pose["rows"],
                        "cells": len(pose["cells"]),
                    }
                    for pose in library["poses"]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
