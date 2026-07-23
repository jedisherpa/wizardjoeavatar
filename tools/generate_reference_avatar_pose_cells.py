#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from generate_reference_avatar_cells import ROOT, generate, generate_from_image

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.compositor import CellCanvas
from wizard_avatar.glyphs import glyph
from wizard_avatar.hd_pose_artifact import HDPoseLibrary, sha256_path
from wizard_avatar.motion_manifest import (
    expand_derived_bridge_series,
    hd_source_import_policy,
)
from wizard_avatar.pose_compositor import (
    authored_staff_cells,
    author_cast_staff_graph,
    clear_authored_staff,
    composite_anchor_transition,
    composite_landmark_splat_transition,
    composite_landmark_warp_transition,
    composite_localized_landmark_transition,
    paint_rigid_staff_graph,
    resolve_authored_staff_anchors,
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


def load_canonical_palette(
    manifest: dict[str, Any],
) -> tuple[tuple[int, int, int], ...] | None:
    raw_path = manifest.get("canonical_palette_path")
    if raw_path is None:
        return None
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("canonical_palette_path must be a nonempty string")
    palette_path = Path(raw_path)
    if not palette_path.is_absolute():
        palette_path = ROOT / palette_path
    payload = json.loads(palette_path.read_text(encoding="utf-8"))
    raw_colors = payload.get("colors")
    if not isinstance(raw_colors, list) or not raw_colors:
        raise ValueError(f"{palette_path}: colors must be a nonempty list")
    colors_list: list[tuple[int, int, int]] = []
    for index, color in enumerate(raw_colors):
        if not isinstance(color, list) or len(color) != 3:
            raise ValueError(
                f"{palette_path}.colors[{index}] must contain three channels"
            )
        if any(isinstance(channel, bool) or not isinstance(channel, int) for channel in color):
            raise ValueError(
                f"{palette_path}.colors[{index}] channels must be integers"
            )
        colors_list.append((color[0], color[1], color[2]))
    colors = tuple(colors_list)
    if any(channel < 0 or channel > 255 for color in colors for channel in color):
        raise ValueError(f"{palette_path}: palette channels must be in the range 0..255")
    if len(set(colors)) != len(colors):
        raise ValueError(f"{palette_path}: palette colors must be unique")
    if len(colors) > 256:
        raise ValueError(f"{palette_path}: palette cannot contain more than 256 colors")
    return colors


def load_hd_pose_library(
    manifest: dict[str, Any],
    *,
    required: bool,
) -> HDPoseLibrary | None:
    raw_path = manifest.get("hd_pose_library_path")
    if raw_path is None:
        if required:
            raise ValueError("hd_pose_library_path is required by an authored pose")
        return None
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("hd_pose_library_path must be a nonempty string")
    index_path = Path(raw_path)
    if not index_path.is_absolute():
        index_path = ROOT / index_path
    expected_sha256 = manifest.get("hd_pose_library_sha256")
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise ValueError("hd_pose_library_sha256 must be a SHA-256 hex digest")
    actual_sha256 = sha256_path(index_path)
    if actual_sha256 != expected_sha256:
        raise ValueError("HD pose library index checksum does not match the manifest")
    return HDPoseLibrary(index_path)


def remap_payload_palette(
    payload: dict[str, Any],
    palette_colors: Sequence[tuple[int, int, int]] | None,
) -> dict[str, Any]:
    if palette_colors is None:
        return payload
    palette = tuple(palette_colors)
    nearest_cache: dict[tuple[int, int, int], tuple[int, int, int]] = {}

    def nearest(raw: Sequence[int]) -> tuple[int, int, int]:
        rgb = tuple(int(channel) for channel in raw)
        cached = nearest_cache.get(rgb)
        if cached is not None:
            return cached
        selected = min(
            palette,
            key=lambda candidate: (
                sum(
                    (rgb[channel] - candidate[channel]) ** 2
                    for channel in range(3)
                ),
                candidate,
            ),
        )
        nearest_cache[rgb] = selected
        return selected

    return {
        **payload,
        "quantized_colors": len(palette),
        "cells": [
            {**cell, "rgb": list(nearest(cell["rgb"]))}
            for cell in payload["cells"]
        ],
    }


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
        "canonical_shift": list(payload.get("canonical_shift", [dx, dy])),
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


def derive_translation_payload(
    manifest: dict[str, Any],
    pose: dict[str, Any],
    poses_by_id: dict[str, dict[str, Any]],
    normalized_payloads: dict[str, dict[str, Any]],
    canonical: dict[str, Any],
    colors: int,
    coverage_threshold: int,
) -> dict[str, Any]:
    """Bake a complete source graph at a small root-relative cell offset."""

    translation = pose["derived_translation"]
    source_pose_id = str(translation["source_pose_id"])
    try:
        source = normalized_payloads[source_pose_id]
    except KeyError as error:
        raise ValueError(
            f"{pose['id']} translation source {source_pose_id!r} is not an available earlier pose"
        ) from error
    offset = point_from(
        translation.get("offset", [0, 0]),
        field_name=f"{pose['id']}.derived_translation.offset",
    )
    cols = int(canonical["cols"])
    rows = int(canonical["rows"])
    cells = []
    for cell in source["cells"]:
        x = int(cell["x"]) + offset[0]
        y = int(cell["y"]) + offset[1]
        if not (0 <= x < cols and 0 <= y < rows):
            raise ValueError(
                f"{pose['id']} translated cell leaves the canonical canvas: ({x}, {y})"
            )
        cells.append({**cell, "x": x, "y": y})

    source_anchors = source.get("resolved_anchors") or resolve_anchors(
        manifest,
        poses_by_id[source_pose_id],
        source,
    )
    anchors = {
        name: [int(point[0]) + offset[0], int(point[1]) + offset[1]]
        for name, point in source_anchors.items()
    }
    root = point_from(canonical["root_anchor"], field_name="canonical.root_anchor")
    anchors["root"] = root
    return {
        "source": (
            f"derived_translation:{source_pose_id}@{offset[0]},{offset[1]}"
        ),
        "source_size": [cols, rows],
        "source_crop": [0, 0, cols, rows],
        "canonical_shift": [0, 0],
        "generation_rows": rows,
        "cols": cols,
        "rows": rows,
        "root_anchor": root,
        "resolved_anchors": anchors,
        "quantized_colors": colors,
        "coverage_threshold": coverage_threshold,
        "cells": cells,
    }


def derive_cast_rig_payload(
    manifest: dict[str, Any],
    pose: dict[str, Any],
    poses_by_id: dict[str, dict[str, Any]],
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
    tip_overrides = manifest.get("derived_cast_tip_overrides", {})
    target_tip_offset = tip_overrides.get(pose["id"])
    if target_tip_offset is None:
        target_tip = absolute_offset("target_staff_tip_offset")
    else:
        override = point_from(
            target_tip_offset,
            field_name=f"derived_cast_tip_overrides.{pose['id']}",
        )
        target_tip = root[0] + override[0], root[1] + override[1]
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
    base_anchors = resolve_anchors(manifest, poses_by_id[base_pose_id], base_payload)
    base_anchors["staff_hand"] = [target_hand[0], target_hand[1]]
    base_anchors["staff_tip"] = [target_tip[0], target_tip[1]]
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
        "resolved_anchors": base_anchors,
        "quantized_colors": colors,
        "coverage_threshold": coverage_threshold,
        "cells": canvas_cells(canvas),
    }


def derive_landmark_warp_payload(
    manifest: dict[str, Any],
    pose: dict[str, Any],
    poses_by_id: dict[str, dict[str, Any]],
    normalized_payloads: dict[str, dict[str, Any]],
    canonical: dict[str, Any],
    colors: int,
    coverage_threshold: int,
) -> dict[str, Any]:
    warp = pose.get("derived_landmark_warp")
    if not isinstance(warp, dict):
        raise ValueError(f"{pose['id']}.derived_landmark_warp must be an object")
    from_pose_id = str(warp.get("from_pose_id", ""))
    to_pose_id = str(warp.get("to_pose_id", ""))
    if from_pose_id == to_pose_id:
        raise ValueError(f"{pose['id']} warp endpoints must be different")
    try:
        from_pose = poses_by_id[from_pose_id]
        to_pose = poses_by_id[to_pose_id]
        from_payload = normalized_payloads[from_pose_id]
        to_payload = normalized_payloads[to_pose_id]
    except KeyError as error:
        raise ValueError(
            f"{pose['id']} warp endpoint {error.args[0]!r} is not an available earlier pose"
        ) from error

    progress_milli = int(warp.get("progress_milli", 500))
    if not 0 < progress_milli <= 1000:
        raise ValueError(f"{pose['id']}.derived_landmark_warp.progress_milli must be 1..1000")
    progress = progress_milli / 1000.0
    from_anchors = resolve_anchors(manifest, from_pose, from_payload)
    to_anchors = resolve_anchors(manifest, to_pose, to_payload)
    from_canvas = payload_canvas(from_payload)
    to_canvas = payload_canvas(to_payload)

    def resolve_staff_geometry(
        canvas: CellCanvas,
        anchors: dict[str, list[int]],
        endpoint_pose: dict[str, Any],
    ) -> None:
        if "hd_source" in endpoint_pose.get("tags", []):
            return
        staff_tip, staff_hand = resolve_authored_staff_anchors(
            canvas,
            tuple(anchors["staff_tip"]),
            tuple(anchors["staff_hand"]),
            tuple(anchors["root"]),
        )
        anchors["staff_tip"] = list(staff_tip)
        anchors["staff_hand"] = list(staff_hand)

    resolve_staff_geometry(from_canvas, from_anchors, from_pose)
    resolve_staff_geometry(to_canvas, to_anchors, to_pose)
    staff_transition = warp.get("staff_transition")
    if staff_transition not in {None, "rigid"}:
        raise ValueError(
            f"{pose['id']}.derived_landmark_warp.staff_transition is unsupported"
        )
    rigid_staff_cells = None
    if staff_transition == "rigid":
        rigid_staff_cells = authored_staff_cells(
            from_canvas,
            tuple(from_anchors["staff_tip"]),
            tuple(from_anchors["staff_hand"]),
            None if "hd_source" in from_pose.get("tags", []) else tuple(from_anchors["root"]),
        )
        if not rigid_staff_cells:
            raise ValueError(f"{pose['id']} rigid staff source mask is empty")
        clear_authored_staff(
            from_canvas,
            tuple(from_anchors["staff_tip"]),
            tuple(from_anchors["staff_hand"]),
            None if "hd_source" in from_pose.get("tags", []) else tuple(from_anchors["root"]),
            aggressive=True,
        )
        clear_authored_staff(
            to_canvas,
            tuple(to_anchors["staff_tip"]),
            tuple(to_anchors["staff_hand"]),
            None if "hd_source" in to_pose.get("tags", []) else tuple(to_anchors["root"]),
            aggressive=True,
        )
    lock_anchor = warp.get("lock_anchor")
    prealign_lock_anchor = warp.get("prealign_lock_anchor", True)
    if not isinstance(prealign_lock_anchor, bool):
        raise ValueError(
            f"{pose['id']}.derived_landmark_warp.prealign_lock_anchor "
            "must be a boolean"
        )
    if lock_anchor is not None:
        if not isinstance(lock_anchor, str) or not lock_anchor:
            raise ValueError(f"{pose['id']}.derived_landmark_warp.lock_anchor must be a name")
        if lock_anchor not in from_anchors or lock_anchor not in to_anchors:
            raise ValueError(f"{pose['id']} lock anchor {lock_anchor!r} is missing")
        if prealign_lock_anchor:
            delta_x = from_anchors[lock_anchor][0] - to_anchors[lock_anchor][0]
            delta_y = from_anchors[lock_anchor][1] - to_anchors[lock_anchor][1]
            aligned = CellCanvas(to_canvas.width, to_canvas.height)
            for y in range(to_canvas.height):
                for x in range(to_canvas.width):
                    cell = to_canvas.get(x, y)
                    target_x = x + delta_x
                    target_y = y + delta_y
                    if (
                        cell is not None
                        and 0 <= target_x < aligned.width
                        and 0 <= target_y < aligned.height
                    ):
                        aligned.cells[target_y][target_x] = cell
            to_canvas = aligned
            to_anchors = {
                name: [point[0] + delta_x, point[1] + delta_y]
                for name, point in to_anchors.items()
            }
    requested_names = tuple(
        str(name)
        for name in warp.get(
            "anchor_names",
            REQUIRED_ANCHORS,
        )
    )
    if staff_transition == "rigid":
        requested_names = tuple(
            name for name in requested_names if name != "staff_tip"
        )
    missing = [
        name
        for name in requested_names
        if name not in from_anchors or name not in to_anchors
    ]
    if missing:
        raise ValueError(f"{pose['id']} warp anchors are missing: {', '.join(missing)}")
    control_pairs = tuple(
        (tuple(from_anchors[name]), tuple(to_anchors[name]))
        for name in requested_names
    )
    localized_region = warp.get("localized_region")
    method = str(warp.get("method", "inverse_sample"))
    if localized_region is None:
        if method == "inverse_sample":
            canvas = composite_landmark_warp_transition(
                from_canvas,
                to_canvas,
                control_pairs,
                progress,
            )
        elif method == "topology_splat":
            canvas = composite_landmark_splat_transition(
                from_canvas,
                to_canvas,
                control_pairs,
                progress,
            )
        else:
            raise ValueError(f"{pose['id']}.derived_landmark_warp.method is unsupported")
    else:
        if not isinstance(localized_region, dict):
            raise ValueError(f"{pose['id']}.localized_region must be an object")
        anchor_name = str(localized_region.get("anchor_name", ""))
        if anchor_name not in from_anchors or anchor_name not in to_anchors:
            raise ValueError(f"{pose['id']} localized anchor {anchor_name!r} is missing")
        pivot_offset = point_from(
            localized_region.get("pivot_offset_from_root"),
            field_name=f"{pose['id']}.localized_region.pivot_offset_from_root",
        )
        radius = float(localized_region.get("radius", 0.0))
        hand_radius = float(localized_region.get("hand_radius", radius))
        source_pivot = (
            from_anchors["root"][0] + pivot_offset[0],
            from_anchors["root"][1] + pivot_offset[1],
        )
        target_pivot = (
            to_anchors["root"][0] + pivot_offset[0],
            to_anchors["root"][1] + pivot_offset[1],
        )
        canvas = composite_localized_landmark_transition(
            from_canvas,
            to_canvas,
            (tuple(from_anchors[anchor_name]), source_pivot),
            (tuple(to_anchors[anchor_name]), target_pivot),
            progress,
            radius=radius,
            hand_radius=hand_radius,
            repair_axis_x=from_anchors["root"][0],
        )
    if (
        prealign_lock_anchor
        and lock_anchor in {"left_foot", "right_foot"}
    ):
        foot_x, foot_y = from_anchors[lock_anchor]
        for y in range(max(0, foot_y - 10), min(canvas.height, foot_y + 4)):
            for x in range(max(0, foot_x - 8), min(canvas.width, foot_x + 9)):
                canvas.cells[y][x] = from_canvas.cells[y][x]
    if rigid_staff_cells is not None:
        skin_canvas = canvas.copy()
        target_hand = tuple(
            from_anchors["staff_hand"][axis]
            + (
                (to_anchors["staff_hand"][axis] - from_anchors["staff_hand"][axis])
                * progress_milli
            )
            // 1000
            for axis in (0, 1)
        )
        target_tip = tuple(
            from_anchors["staff_tip"][axis]
            + (
                (to_anchors["staff_tip"][axis] - from_anchors["staff_tip"][axis])
                * progress_milli
            )
            // 1000
            for axis in (0, 1)
        )
        paint_rigid_staff_graph(
            canvas,
            staff_cells=rigid_staff_cells,
            source_staff_tip=tuple(from_anchors["staff_tip"]),
            source_staff_hand=tuple(from_anchors["staff_hand"]),
            target_staff_tip=target_tip,
            target_staff_hand=target_hand,
            skin_canvas=skin_canvas,
        )
    anchors = {
        name: [
            from_anchors[name][axis]
            + ((to_anchors[name][axis] - from_anchors[name][axis]) * progress_milli) // 1000
            for axis in (0, 1)
        ]
        for name in sorted(set(from_anchors) & set(to_anchors))
    }
    if lock_anchor in {"left_foot", "right_foot"}:
        requested_x, requested_y = anchors[lock_anchor]
        occupied = [
            (x, y)
            for y in range(canvas.height)
            for x in range(canvas.width)
            if canvas.get(x, y) is not None
        ]
        anchors[lock_anchor] = list(
            min(
                occupied,
                key=lambda point: (
                    (point[0] - requested_x) ** 2
                    + (point[1] - requested_y) ** 2,
                    abs(point[1] - requested_y),
                    abs(point[0] - requested_x),
                    point[1],
                    point[0],
                ),
            )
        )
    root = point_from(canonical["root_anchor"], field_name="canonical.root_anchor")
    anchors["root"] = root
    return {
        "source": (
            f"derived_landmark_warp:{from_pose_id}+{to_pose_id}@"
            f"{progress_milli}/1000"
            + (f":lock={lock_anchor}" if lock_anchor is not None else "")
            + (":localized" if localized_region is not None else "")
            + (f":method={method}" if method != "inverse_sample" else "")
            + (
                f":staff={staff_transition}"
                if staff_transition is not None
                else ""
            )
        ),
        "source_size": [int(canonical["cols"]), int(canonical["rows"])],
        "source_crop": [0, 0, int(canonical["cols"]), int(canonical["rows"])],
        "canonical_shift": [0, 0],
        "generation_rows": int(canonical["rows"]),
        "cols": canvas.width,
        "rows": canvas.height,
        "root_anchor": root,
        "resolved_anchors": anchors,
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
    manifest = expand_derived_bridge_series(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )
    palette_colors = load_canonical_palette(manifest)
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
        if "derived_blend" not in pose
        and "derived_cast_rig" not in pose
        and "derived_landmark_warp" not in pose
        and "derived_translation" not in pose
    ]
    hd_library = load_hd_pose_library(
        manifest,
        required=any("hd_pose_id" in pose for pose in authored_poses),
    )
    hd_import_policy = (
        hd_source_import_policy(manifest)
        if hd_library is not None
        and any("hd_pose_id" in pose for pose in authored_poses)
        else None
    )
    for pose in authored_poses:
        existing = reused_authored.get(str(pose["id"]))
        if existing is not None:
            payload = {
                "source": existing["source"],
                "source_size": existing["source_size"],
                "source_crop": existing["source_crop"],
                "cols": existing["cols"],
                "rows": existing["rows"],
                "root_anchor": existing["root_anchor"],
                "canonical_shift": existing.get("canonical_shift", [0, 0]),
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
        temp_output = output_path.parent / f".{pose['id']}.tmp.json"
        generation_rows = int(pose.get("generation_rows", rows))

        def generate_authored_payload(authored_rows: int) -> dict[str, Any]:
            common = {
                "rows": authored_rows,
                "margin": margin,
                "threshold": threshold,
                "coverage_threshold": coverage_threshold,
                "colors": colors,
                "minimum_alpha_component_pixels": int(
                    pose.get("minimum_alpha_component_pixels", 16)
                ),
                "palette_colors": palette_colors,
            }
            hd_pose_id = pose.get("hd_pose_id")
            if hd_pose_id is not None:
                if not isinstance(hd_pose_id, str) or not hd_pose_id:
                    raise ValueError(f"{pose['id']}.hd_pose_id must be nonempty")
                if hd_library is None:
                    raise ValueError(f"{pose['id']} requires the HD pose library")
                if hd_import_policy is None:
                    raise ValueError(f"{pose['id']} requires an HD source import policy")
                metadata = hd_library.pose_metadata.get(hd_pose_id)
                if metadata is None:
                    raise ValueError(f"{pose['id']} references an unknown HD pose")
                if (
                    metadata["approval_state"]
                    != hd_import_policy["required_approval_state"]
                ):
                    raise ValueError(
                        f"{pose['id']} references HD art outside the approved "
                        "offline-authoring scope"
                    )
                if (
                    hd_import_policy["native_runtime_admission_required"]
                    and not metadata["runtime_admitted"]
                ):
                    raise ValueError(
                        f"{pose['id']} requires native HD runtime admission"
                    )
                return generate_from_image(
                    hd_library.load_pose(hd_pose_id),
                    f"hd_pose:{hd_pose_id}",
                    temp_output,
                    **common,
                )
            source_path_value = pose.get("source_path")
            if source_path_value is None:
                source_path = source_dir / pose["source"]
            else:
                source_path = Path(source_path_value)
                if not source_path.is_absolute():
                    source_path = ROOT / source_path
            return generate(source_path, temp_output, **common)

        payload = generate_authored_payload(generation_rows)
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
            payload = generate_authored_payload(generation_rows)
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
    poses_by_id = {str(pose["id"]): pose for pose in manifest["poses"]}
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
                manifest,
                pose,
                poses_by_id,
                normalized_payloads,
                canonical,
                colors,
                coverage_threshold,
            )
            generation_rows = int(payload["generation_rows"])
        elif "derived_landmark_warp" in pose:
            payload = derive_landmark_warp_payload(
                manifest,
                pose,
                poses_by_id,
                normalized_payloads,
                canonical,
                colors,
                coverage_threshold,
            )
            generation_rows = int(payload["generation_rows"])
        elif "derived_translation" in pose:
            payload = derive_translation_payload(
                manifest,
                pose,
                poses_by_id,
                normalized_payloads,
                canonical,
                colors,
                coverage_threshold,
            )
            generation_rows = int(payload["generation_rows"])
        else:
            payload = normalized_payloads[pose["id"]]
            generation_rows = generation_rows_by_id[pose["id"]]
        payload = remap_payload_palette(payload, palette_colors)
        # Derived graphs become valid inputs for later derived graphs in the
        # manifest. This preserves a deterministic, acyclic authoring order
        # while keeping every runtime pose as a fully baked pixel graph.
        normalized_payloads[pose["id"]] = payload
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
                "anchors": payload.get("resolved_anchors")
                or resolve_anchors(manifest, pose, payload),
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
        "palette": {
            **palette_summary(
                poses,
                manifest.get("palette_id", f"per_pose_quantized_{colors}"),
            ),
            **(
                {
                    "declared_color_count": len(palette_colors),
                    "source": str(manifest["canonical_palette_path"]),
                }
                if palette_colors is not None
                else {}
            ),
        },
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
