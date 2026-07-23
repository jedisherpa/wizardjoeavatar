#!/usr/bin/env python3
"""Measure and render adjacency continuity for authored animation clips."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.compositor import CellCanvas
from wizard_avatar.pose_compositor import resolve_authored_staff_anchors


DEFAULT_LIBRARY = (
    ROOT / "wizard_avatar" / "definitions" / "reference_avatar_pose_cells.json"
)
DEFAULT_GRAPH = (
    ROOT
    / "wizard_avatar"
    / "definitions"
    / "reference_avatar_animation_graph_v2.json"
)
DEFAULT_CLIPS = (
    "walk_left",
    "walk_right",
    "reverse_east_to_west",
    "stop_left",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def cells_by_position(pose: dict[str, Any]) -> dict[tuple[int, int], tuple[int, int, int]]:
    root_x, root_y = pose["anchors"]["root"]
    return {
        (int(cell["x"]) - root_x, int(cell["y"]) - root_y): tuple(cell["rgb"])
        for cell in pose["cells"]
    }


def iou(left: set[Any], right: set[Any]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def anchor_step(
    left: dict[str, Any],
    right: dict[str, Any],
    anchor_name: str,
) -> int:
    left_root = left["anchors"]["root"]
    right_root = right["anchors"]["root"]
    left_anchor = left["anchors"][anchor_name]
    right_anchor = right["anchors"][anchor_name]
    return max(
        abs(
            (right_anchor[axis] - right_root[axis])
            - (left_anchor[axis] - left_root[axis])
        )
        for axis in (0, 1)
    )


def resolve_staff_anchors(pose: dict[str, Any]) -> dict[str, tuple[int, int]]:
    if "hd_source" in pose.get("tags", []):
        return {
            "staff_tip": tuple(pose["anchors"]["staff_tip"]),
            "staff_hand": tuple(pose["anchors"]["staff_hand"]),
        }
    canvas = CellCanvas(int(pose["cols"]), int(pose["rows"]))
    for cell in pose["cells"]:
        x = int(cell["x"])
        y = int(cell["y"])
        rgb = tuple(cell["rgb"])
        canvas.set(x, y, "#", rgb, "pose")
    staff_tip, staff_hand = resolve_authored_staff_anchors(
        canvas,
        tuple(pose["anchors"]["staff_tip"]),
        tuple(pose["anchors"]["staff_hand"]),
        tuple(pose["anchors"]["root"]),
    )
    return {"staff_tip": staff_tip, "staff_hand": staff_hand}


def analyze_pair(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_cells = cells_by_position(left)
    right_cells = cells_by_position(right)
    left_colored = {(position, rgb) for position, rgb in left_cells.items()}
    right_colored = {(position, rgb) for position, rgb in right_cells.items()}
    left_staff = resolve_staff_anchors(left)
    right_staff = resolve_staff_anchors(right)
    left_root = left["anchors"]["root"]
    right_root = right["anchors"]["root"]

    def resolved_step(anchor_name: str) -> int:
        return max(
            abs(
                (right_staff[anchor_name][axis] - right_root[axis])
                - (left_staff[anchor_name][axis] - left_root[axis])
            )
            for axis in (0, 1)
        )

    return {
        "from_pose_id": left["id"],
        "to_pose_id": right["id"],
        "occupancy_iou": round(iou(set(left_cells), set(right_cells)), 6),
        "color_iou": round(iou(left_colored, right_colored), 6),
        "staff_hand_step": resolved_step("staff_hand"),
        "staff_tip_step": resolved_step("staff_tip"),
    }


def render_pose(pose: dict[str, Any], *, scale: int) -> Image.Image:
    image = Image.new(
        "RGBA",
        (int(pose["cols"]) * scale, int(pose["rows"]) * scale),
        (255, 255, 255, 0),
    )
    draw = ImageDraw.Draw(image)
    for cell in pose["cells"]:
        x = int(cell["x"]) * scale
        y = int(cell["y"]) * scale
        rgb = tuple(cell["rgb"])
        draw.rectangle((x, y, x + scale - 1, y + scale - 1), fill=(*rgb, 255))
    return image


def create_contact_sheet(
    clips: list[dict[str, Any]],
    poses: dict[str, dict[str, Any]],
    output: Path,
    *,
    scale: int,
) -> None:
    label_height = 28
    gap = 12
    max_samples = max(len(clip["pose_ids"]) for clip in clips)
    pose_width = max(int(pose["cols"]) for pose in poses.values()) * scale
    pose_height = max(int(pose["rows"]) for pose in poses.values()) * scale
    row_height = label_height + pose_height + gap
    sheet = Image.new(
        "RGBA",
        (
            gap + max_samples * (pose_width + gap),
            gap + len(clips) * row_height,
        ),
        (244, 244, 242, 255),
    )
    draw = ImageDraw.Draw(sheet)
    for row, clip in enumerate(clips):
        top = gap + row * row_height
        draw.text((gap, top), clip["clip_id"], fill=(20, 20, 20, 255))
        for column, pose_id in enumerate(clip["pose_ids"]):
            left = gap + column * (pose_width + gap)
            pose_image = render_pose(poses[pose_id], scale=scale)
            sheet.alpha_composite(pose_image, (left, top + label_height))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--clips", nargs="+", default=list(DEFAULT_CLIPS))
    parser.add_argument("--contact-sheet", type=Path)
    parser.add_argument("--scale", type=int, default=2)
    args = parser.parse_args()

    library = load_json(args.library)
    graph = load_json(args.graph)
    poses = {pose["id"]: pose for pose in library["poses"]}
    clips = []
    for clip_id in args.clips:
        pose_ids = [
            sample["pose_id"]
            for sample in graph["clips"][clip_id]["samples"]
        ]
        missing = [pose_id for pose_id in pose_ids if pose_id not in poses]
        if missing:
            raise SystemExit(f"{clip_id} references missing poses: {missing}")
        pairs = [
            analyze_pair(poses[left_id], poses[right_id])
            for left_id, right_id in zip(pose_ids, pose_ids[1:])
        ]
        clips.append(
            {
                "clip_id": clip_id,
                "pose_ids": pose_ids,
                "minimum_occupancy_iou": min(
                    pair["occupancy_iou"] for pair in pairs
                ),
                "minimum_color_iou": min(pair["color_iou"] for pair in pairs),
                "maximum_staff_hand_step": max(
                    pair["staff_hand_step"] for pair in pairs
                ),
                "maximum_staff_tip_step": max(
                    pair["staff_tip_step"] for pair in pairs
                ),
                "pairs": pairs,
            }
        )
    if args.contact_sheet is not None:
        create_contact_sheet(
            clips,
            poses,
            args.contact_sheet,
            scale=args.scale,
        )
    print(json.dumps({"clips": clips}, indent=2))


if __name__ == "__main__":
    main()
