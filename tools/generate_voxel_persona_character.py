#!/usr/bin/env python3
"""Build deterministic direct-cell persona assets from approved worksheets.

The profile is intentionally data-only so every school persona can reuse the
same extraction, bounds validation, hashing, graph, and manifest pipeline.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import numpy as np
from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parent.parent
DEFINITIONS = ROOT / "wizard_avatar" / "definitions"


def canonical_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_text(text: str) -> str:
    return digest_bytes(text.encode("utf-8"))


def load_profile(path: Path) -> dict[str, Any]:
    profile_path = path.resolve()
    raw = json.loads(profile_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("generation profile must use schema_version 1")
    required = {
        "character_id", "display_name", "asset_set_id", "references",
        "canonical", "poses", "animation_graph", "animation_matrix",
        "identity_lock", "attachment_points", "output_prefix",
    }
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError("generation profile is missing: {}".format(", ".join(missing)))
    raw["_profile_path"] = profile_path
    return raw


def _root_path(profile: Mapping[str, Any], value: str) -> Path:
    path = (ROOT / value).resolve()
    if ROOT not in path.parents:
        raise ValueError("profile path escapes repository: {}".format(value))
    return path


def _pose_sheet_name(profile: Mapping[str, Any], pose: Mapping[str, Any]) -> str:
    """Resolve an approved worksheet revision without duplicating pose maps."""
    if "resolved_sheet" in pose:
        return str(pose["resolved_sheet"])
    requested = str(pose["sheet"])
    overrides = profile.get("sheet_revision_overrides", {})
    if not isinstance(overrides, Mapping):
        raise ValueError("sheet_revision_overrides must be an object")
    return str(overrides.get(requested, requested))


def _panel(sheet: Path, columns: int, rows: int, index: int, gutter: int) -> Image.Image:
    image = Image.open(sheet).convert("RGB")
    column = index % columns
    row = index // columns
    if row >= rows:
        raise ValueError("panel index {} is outside {}x{} sheet".format(index, columns, rows))
    left = round(column * image.width / columns) + gutter
    right = round((column + 1) * image.width / columns) - gutter
    top = round(row * image.height / rows) + gutter
    bottom = round((row + 1) * image.height / rows) - gutter
    return image.crop((left, top, right, bottom))


def _subject_rgba(panel: Image.Image, extraction: Mapping[str, Any]) -> Image.Image:
    pixels = np.asarray(panel, dtype=np.uint8)
    sample = max(2, int(extraction.get("corner_sample", 12)))
    corner_pixels = np.concatenate(
        (
            pixels[:sample, :sample].reshape(-1, 3),
            pixels[:sample, -sample:].reshape(-1, 3),
            pixels[-sample:, :sample].reshape(-1, 3),
            pixels[-sample:, -sample:].reshape(-1, 3),
        ),
        axis=0,
    )
    background = np.median(corner_pixels.astype(np.int16), axis=0)
    channels = pixels.astype(np.int16)
    red, green, blue = channels[:, :, 0], channels[:, :, 1], channels[:, :, 2]
    if extraction.get("foreground_mode") == "warm_subject":
        maximum = channels.max(axis=2)
        minimum = channels.min(axis=2)
        chroma = maximum - minimum
        warm = (red > blue + 7) & (red >= green - 18)
        non_blue_color = (chroma > 24) & (blue < maximum)
        dark_detail = (maximum < 112) & (red >= blue - 8)
        mask = warm | non_blue_color | dark_detail
    else:
        delta = channels - background
        distance = np.sqrt(np.sum(delta * delta, axis=2))
        tolerance = float(extraction.get("background_tolerance", 42.0))
        mask = distance > tolerance

    # Close small gaps inside glasses, hair, fingers, and held props without
    # expanding the subject to the panel edge.
    mask_image = Image.fromarray(mask.astype(np.uint8) * 255)
    close_size = int(extraction.get("close_filter", 7))
    if close_size > 1:
        if close_size % 2 == 0:
            close_size += 1
        mask_image = mask_image.filter(ImageFilter.MaxFilter(close_size)).filter(
            ImageFilter.MinFilter(close_size)
        )
    mask = np.asarray(mask_image, dtype=np.uint8) > 0
    if extraction.get("largest_component", True):
        mask = _largest_component(mask)
        detail_radius = int(extraction.get("detail_radius", 5))
        if detail_radius > 0:
            size = detail_radius * 2 + 1
            mask = np.asarray(
                Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(size)),
                dtype=np.uint8,
            ) > 0

    # Ignore background islands touching the panel gutter. Approved sheets are
    # required to keep the complete character separated from the panel edge.
    edge = max(1, int(extraction.get("edge_clear", 2)))
    mask[:edge, :] = False
    mask[-edge:, :] = False
    mask[:, :edge] = False
    mask[:, -edge:] = False
    ys, xs = np.nonzero(mask)
    if not len(xs):
        raise ValueError("worksheet panel contains no extractable subject")
    margin = int(extraction.get("crop_margin", 3))
    x0 = max(0, int(xs.min()) - margin)
    x1 = min(panel.width, int(xs.max()) + margin + 1)
    y0 = max(0, int(ys.min()) - margin)
    y1 = min(panel.height, int(ys.max()) + margin + 1)
    rgba = panel.convert("RGBA")
    rgba.putalpha(Image.fromarray(mask.astype(np.uint8) * 255))
    return rgba.crop((x0, y0, x1, y1))


def _largest_component(mask: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=np.uint8)
    best: list[tuple[int, int]] = []
    for start_y, start_x in zip(*np.nonzero(mask)):
        if visited[start_y, start_x]:
            continue
        visited[start_y, start_x] = 1
        queue = deque([(int(start_y), int(start_x))])
        component: list[tuple[int, int]] = []
        while queue:
            y, x = queue.popleft()
            component.append((y, x))
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = 1
                    queue.append((ny, nx))
        if len(component) > len(best):
            best = component
    result = np.zeros_like(mask, dtype=bool)
    for y, x in best:
        result[y, x] = True
    return result


def _cells_for_pose(profile: Mapping[str, Any], pose: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs = profile["references"]
    canonical = profile["canonical"]
    worksheet_dir = _root_path(profile, str(refs["worksheets_dir"]))
    sheet = worksheet_dir / _pose_sheet_name(profile, pose)
    if not sheet.is_file():
        raise FileNotFoundError(sheet)
    panel = _panel(
        sheet,
        int(pose["columns"]),
        int(pose["rows"]),
        int(pose["index"]),
        int(pose.get("gutter", 3)),
    )
    extraction = dict(profile.get("extraction", {}))
    pose_extraction = pose.get("extraction", {})
    if not isinstance(pose_extraction, Mapping):
        raise ValueError("pose extraction must be an object")
    extraction.update(pose_extraction)
    subject = _subject_rgba(panel, extraction)
    cols, rows = int(canonical["cols"]), int(canonical["rows"])
    inset = canonical["safe_inset"]
    left = int(inset["left"])
    right = int(inset["right"])
    top = int(inset["top"])
    baseline_y = int(canonical["baseline_y"])
    bottom_padding = max(0, rows - 1 - baseline_y)
    max_width = cols - left - right
    max_height = baseline_y - top + 1
    scale = min(max_width / subject.width, max_height / subject.height)
    target_width = max(1, round(subject.width * scale))
    target_height = max(1, round(subject.height * scale))
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    subject = subject.resize((target_width, target_height), resampling)
    origin_x = left + max(0, (max_width - target_width) // 2)
    origin_y = baseline_y - target_height + 1
    data = np.asarray(subject, dtype=np.uint8)
    cells: list[dict[str, Any]] = []
    alpha_threshold = int(extraction.get("alpha_threshold", 42))
    for y in range(target_height):
        for x in range(target_width):
            red, green, blue, alpha = (int(channel) for channel in data[y, x])
            if alpha < alpha_threshold:
                continue
            cells.append({"x": origin_x + x, "y": origin_y + y, "rgb": [red, green, blue]})
    if not cells:
        raise ValueError("pose {} produced no direct cells".format(pose["id"]))
    xs = [cell["x"] for cell in cells]
    ys = [cell["y"] for cell in cells]
    if min(xs) < left or max(xs) >= cols - right or min(ys) < top or max(ys) > baseline_y:
        raise ValueError("pose {} violates canonical safety bounds".format(pose["id"]))
    if bottom_padding < 0:  # pragma: no cover - validated by arithmetic above.
        raise ValueError("invalid canonical baseline")
    return cells


def _anchors_for_pose(
    profile: Mapping[str, Any],
    pose: Mapping[str, Any],
    cells: list[dict[str, Any]],
) -> dict[str, list[int]]:
    """Derive stable pose-local anchors from each normalized silhouette.

    Explicit pose anchors remain authoritative. Otherwise ratios are measured
    against the generated subject bounds, so a crouch, jump, profile, or wide
    gesture does not inherit face and attachment coordinates from neutral.
    """
    canonical = profile["canonical"]
    root = [int(value) for value in canonical["root_anchor"]]
    ratios = profile.get("anchor_ratios", {})
    if not isinstance(ratios, Mapping):
        raise ValueError("anchor_ratios must be an object")
    xs = [int(cell["x"]) for cell in cells]
    ys = [int(cell["y"]) for cell in cells]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    width = max(1, right - left)
    height = max(1, bottom - top)
    anchors: dict[str, list[int]] = {"root": root}
    anchor_presence = profile.get("anchor_presence", {})
    if not isinstance(anchor_presence, Mapping):
        raise ValueError("anchor_presence must be an object")
    pose_id = str(pose["id"])
    for name, point in ratios.items():
        if name in anchor_presence:
            allowed_pose_ids = anchor_presence[name]
            if not isinstance(allowed_pose_ids, (list, tuple)):
                raise ValueError("anchor_presence.{} must be an array".format(name))
            if pose_id not in {str(item) for item in allowed_pose_ids}:
                continue
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("anchor ratio {} must contain x and y".format(name))
        x = round(left + float(point[0]) * width)
        y = round(top + float(point[1]) * height)
        expected = (x, y)
        candidates = cells
        if name in {"left_hand", "right_hand"}:
            candidates = [
                cell for cell in cells
                if top + height * 0.25 <= int(cell["y"]) <= top + height * 0.82
                and _is_skin_cell(cell)
            ] or cells
        elif name in {"left_foot", "right_foot"}:
            center_x = (left + right) / 2
            candidates = [
                cell for cell in cells
                if int(cell["y"]) >= top + height * 0.78
                and (
                    int(cell["x"]) <= center_x
                    if name == "left_foot"
                    else int(cell["x"]) >= center_x
                )
            ] or cells
            lowest = max(int(cell["y"]) for cell in candidates)
            candidates = [cell for cell in candidates if int(cell["y"]) >= lowest - 1]
        elif name in {"mouth", "left_eye", "right_eye"}:
            candidates = [
                cell for cell in cells if int(cell["y"]) <= top + height * 0.38
            ] or cells
        elif name == "journal":
            candidates = [
                cell for cell in cells
                if top + height * 0.32 <= int(cell["y"]) <= top + height * 0.78
                and _is_journal_detail_cell(cell)
            ] or cells
        nearest = min(
            candidates,
            key=lambda cell: (
                abs(int(cell["x"]) - expected[0]) + abs(int(cell["y"]) - expected[1]),
                abs(int(cell["y"]) - expected[1]),
                abs(int(cell["x"]) - expected[0]),
            ),
        )
        anchors[str(name)] = [int(nearest["x"]), int(nearest["y"])]
    explicit = pose.get("anchors", {})
    if not isinstance(explicit, Mapping):
        raise ValueError("pose anchors must be an object")
    anchors.update(
        {
            str(name): [int(point[0]), int(point[1])]
            for name, point in explicit.items()
        }
    )
    return anchors


def _is_skin_cell(cell: Mapping[str, Any]) -> bool:
    red, green, blue = (int(value) for value in cell["rgb"])
    return red >= 135 and red >= green + 12 and green >= blue + 8


def _is_journal_detail_cell(cell: Mapping[str, Any]) -> bool:
    red, green, blue = (int(value) for value in cell["rgb"])
    gold = red >= 135 and green >= 75 and blue <= 85 and red >= green + 35
    leather = red >= 55 and red >= green * 1.25 and green >= blue * 1.2
    return gold or leather


def pose_payload(profile: Mapping[str, Any]) -> dict[str, Any]:
    canonical = profile["canonical"]
    poses = []
    seen: set[str] = set()
    for raw_pose in profile["poses"]:
        pose_id = str(raw_pose["id"])
        if pose_id in seen:
            raise ValueError("duplicate pose id: {}".format(pose_id))
        seen.add(pose_id)
        cells = _cells_for_pose(profile, raw_pose)
        anchors = _anchors_for_pose(profile, raw_pose, cells)
        sheet_name = _pose_sheet_name(profile, raw_pose)
        poses.append(
            {
                "id": pose_id,
                "description": str(raw_pose.get("description", pose_id.replace("_", " "))),
                "source": "{}/{}#panel-{}".format(
                    profile["references"]["worksheets_dir"],
                    sheet_name,
                    raw_pose["index"],
                ),
                "cols": int(canonical["cols"]),
                "rows": int(canonical["rows"]),
                "root_anchor": [int(value) for value in canonical["root_anchor"]],
                "facing": str(raw_pose.get("facing", "south")),
                "graph_kind": str(raw_pose.get("graph_kind", "full_body_graph")),
                "anchors": anchors,
                "cells": cells,
            }
        )
    return {
        "schema_version": 2,
        "version": 1,
        "asset_set_id": profile["asset_set_id"],
        "generation_method": "approved_worksheet_to_direct_square_cells",
        "canonical": canonical,
        "poses": poses,
    }


def extraction_audit_payload(
    profile: Mapping[str, Any],
    pixel_graphs: Mapping[str, Any],
    generated_pose_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the repeatable pre-animation audit for every isolated panel."""
    refs = profile["references"]
    worksheet_dir = _root_path(profile, str(refs["worksheets_dir"]))
    generated_graphs = [
        *pixel_graphs["graphs"],
        *(
            {
                "id": pose["id"],
                "graph_kind": pose["graph_kind"],
                "nodes": pose["cells"],
            }
            for pose in generated_pose_payload["poses"]
        ),
    ]
    source_cells = [*profile.get("reference_cells", ()), *profile["poses"]]
    if len(generated_graphs) != len(source_cells):
        raise ValueError("pixel graph extraction and audit item counts differ")
    items = []
    category_counts: dict[str, int] = {}
    for ordinal, (raw_pose, graph) in enumerate(zip(source_cells, generated_graphs)):
        sheet_name = _pose_sheet_name(profile, raw_pose)
        category = _worksheet_category(sheet_name)
        category_counts[category] = category_counts.get(category, 0) + 1
        cells = graph["nodes"]
        compact_graph = json.dumps(cells, separators=(",", ":"), sort_keys=True)
        xs = [int(cell["x"]) for cell in cells]
        ys = [int(cell["y"]) for cell in cells]
        items.append(
            {
                "ordinal": ordinal,
                "graph_id": graph["id"],
                "category": category,
                "graph_kind": graph["graph_kind"],
                "source_cell": "{}#panel-{}".format(sheet_name, raw_pose["index"]),
                "source_worksheet_sha256": digest_bytes((worksheet_dir / sheet_name).read_bytes()),
                "background_removed": True,
                "isolation_method": "largest_connected_warm_subject_mask",
                "runtime_format": "colored_pixel_nodes_json",
                "runtime_asset": (
                    "{}_pixel_graphs.json#graph={}".format(
                        profile["output_prefix"], graph["id"]
                    )
                    if ordinal < len(profile.get("reference_cells", ()))
                    else "{}_pose_cells.json#pose={}".format(
                        profile["output_prefix"], graph["id"]
                    )
                ),
                "pixel_node_count": len(cells),
                "pixel_graph_sha256": digest_text(compact_graph),
                "bounds": {
                    "left": min(xs),
                    "top": min(ys),
                    "right": max(xs),
                    "bottom": max(ys),
                },
                "audit_status": "passed_before_animation_mapping",
            }
        )
    expected = profile.get("expected_extraction_counts")
    if expected is not None:
        normalized_expected = {str(key): int(value) for key, value in expected.items()}
        if category_counts != normalized_expected:
            raise ValueError(
                "extraction category counts differ: expected={} actual={}".format(
                    normalized_expected, category_counts
                )
            )
    return {
        "schema_version": 1,
        "character_id": profile["character_id"],
        "asset_set_id": profile["asset_set_id"],
        "audit_stage": "background_removal_and_pixel_graph_before_animation_mapping",
        "item_count": len(items),
        "category_counts": category_counts,
        "runtime_image_assets": [],
        "items": items,
    }


def pixel_graph_payload(
    profile: Mapping[str, Any],
    generated_pose_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Store all 124 isolated worksheet cells as transparent color nodes."""
    graphs = []
    seen: set[str] = set()
    for raw_cell in profile.get("reference_cells", ()):
        graph_id = str(raw_cell["id"])
        if graph_id in seen:
            raise ValueError("duplicate pixel graph id: {}".format(graph_id))
        seen.add(graph_id)
        cells = _cells_for_pose(profile, raw_cell)
        graphs.append(
            {
                "id": graph_id,
                "graph_kind": str(raw_cell.get("graph_kind", "reference_graph")),
                "source": "{}/{}#panel-{}".format(
                    profile["references"]["worksheets_dir"],
                    _pose_sheet_name(profile, raw_cell),
                    raw_cell["index"],
                ),
                "cols": int(profile["canonical"]["cols"]),
                "rows": int(profile["canonical"]["rows"]),
                "nodes": cells,
            }
        )
    return {
        "schema_version": 1,
        "character_id": profile["character_id"],
        "asset_set_id": profile["asset_set_id"],
        "encoding": "transparent_colored_pixel_nodes",
        "graph_count": len(graphs),
        "graphs": graphs,
    }


def _worksheet_category(sheet_name: str) -> str:
    categories = {
        "01-": "identity_reference",
        "02-": "turnaround",
        "03-": "neutral",
        "04-": "expression",
        "05-": "viseme_blink",
        "06-": "hand_prop",
        "07-": "motion",
        "08-": "signature",
        "09-": "interaction",
    }
    for prefix, category in categories.items():
        if sheet_name.startswith(prefix):
            return category
    raise ValueError("worksheet is not assigned to an extraction category: {}".format(sheet_name))


def matrix_payload(profile: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    for group, names in profile["animation_matrix"].items():
        for name in names:
            rows.append(
                {
                    "behavior_id": "{}.{}".format(group, name),
                    "group": group,
                    "runtime": "worksheet_pose_plus_semantic_channel",
                    "status": "production",
                    "transition": "anticipate_action_follow_through_recover",
                }
            )
    return {
        "schema_version": 1,
        "character_id": profile["character_id"],
        "row_count": len(rows),
        "rows": rows,
    }


def manifest_payload(
    profile: Mapping[str, Any],
    pose_hash: str,
    graph_hash: str,
    matrix_hash: str,
    extraction_audit_hash: str,
    extraction_item_count: int,
    pixel_graph_hash: str,
) -> dict[str, Any]:
    refs = profile["references"]
    original = _root_path(profile, str(refs["original_reference"]))
    canonical_reference = _root_path(profile, str(refs["canonical_reference"]))
    worksheet_dir = _root_path(profile, str(refs["worksheets_dir"]))
    profile_path = Path(str(profile["_profile_path"]))
    production_worksheets = sorted(
        {
            _pose_sheet_name(profile, pose)
            for pose in [*profile.get("reference_cells", ()), *profile["poses"]]
        }
    )
    return {
        "schema_version": 1,
        "character_id": profile["character_id"],
        "display_name": profile["display_name"],
        "identity_lock": profile["identity_lock"],
        "origin": profile["canonical"],
        "attachment_points": profile["attachment_points"],
        "derivation": {
            "original_reference": refs["original_reference"],
            "canonical_reference": refs["canonical_reference"],
            "approved_worksheets": refs["worksheets_dir"],
            "runtime_art": "deterministic worksheet-derived direct cell library",
            "flattened_runtime_dependency": False,
        },
        "hashes": {
            "generation_profile_sha256": digest_bytes(profile_path.read_bytes()),
            "original_reference_sha256": digest_bytes(original.read_bytes()),
            "canonical_reference_sha256": digest_bytes(canonical_reference.read_bytes()),
            "worksheet_sha256": {
                name: digest_bytes((worksheet_dir / name).read_bytes())
                for name in production_worksheets
            },
            "pose_library_sha256": pose_hash,
            "animation_graph_sha256": graph_hash,
            "animation_matrix_sha256": matrix_hash,
            "extraction_audit_sha256": extraction_audit_hash,
            "extraction_item_count": extraction_item_count,
            "pixel_graph_library_sha256": pixel_graph_hash,
        },
    }


def generated_outputs(profile: Mapping[str, Any]) -> dict[Path, str]:
    poses = pose_payload(profile)
    pose_text = canonical_json(poses)
    pixel_graphs = pixel_graph_payload(profile, poses)
    pixel_graph_text = canonical_json(pixel_graphs)
    extraction_audit_text = canonical_json(
        extraction_audit_payload(profile, pixel_graphs, poses)
    )
    graph_text = canonical_json(profile["animation_graph"])
    matrix_text = canonical_json(matrix_payload(profile))
    prefix = str(profile["output_prefix"])
    return {
        DEFINITIONS / "{}_pose_cells.json".format(prefix): pose_text,
        DEFINITIONS / "{}_animation_graph.json".format(prefix): graph_text,
        DEFINITIONS / "{}_animation_matrix.json".format(prefix): matrix_text,
        DEFINITIONS / "{}_pixel_graphs.json".format(prefix): pixel_graph_text,
        DEFINITIONS / "{}_extraction_audit.json".format(prefix): extraction_audit_text,
        DEFINITIONS / "{}_character_manifest.json".format(prefix): canonical_json(
            manifest_payload(
                profile,
                digest_text(pose_text),
                digest_text(graph_text),
                digest_text(matrix_text),
                digest_text(extraction_audit_text),
                len(pixel_graphs["graphs"]) + len(poses["poses"]),
                digest_text(pixel_graph_text),
            )
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    profile = load_profile(args.profile)
    outputs = generated_outputs(profile)
    if args.check:
        mismatches = [
            str(path)
            for path, content in outputs.items()
            if not path.is_file() or path.read_text(encoding="utf-8") != content
        ]
        if mismatches:
            raise SystemExit("generated persona assets differ: " + ", ".join(mismatches))
        print("{} generated assets are deterministic".format(profile["display_name"]))
        return 0
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
    print("Generated {} assets for {}".format(len(outputs), profile["display_name"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
