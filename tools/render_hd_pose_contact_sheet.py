#!/usr/bin/env python3
"""Render selected compiled HD pixel poses for visual review."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import HDPoseLibrary


DEFAULT_INDEX = (
    ROOT / "assets" / "reference" / "hd_canonical" / "compiled" / "library-index.json"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pose-prefix", action="append", default=[])
    parser.add_argument("--start", type=int)
    parser.add_argument("--end", type=int)
    parser.add_argument("--columns", type=int, default=5)
    parser.add_argument("--thumbnail", type=int, default=300)
    args = parser.parse_args()

    library = HDPoseLibrary(args.index)
    selected = []
    for pose_id in library.pose_ids:
        number = int(pose_id.split("_", 1)[0]) if pose_id[:3].isdigit() else None
        in_range = (
            args.start is not None
            and args.end is not None
            and number is not None
            and args.start <= number <= args.end
        )
        matches_prefix = any(
            pose_id.startswith(prefix) for prefix in args.pose_prefix
        )
        if in_range or matches_prefix:
            selected.append(pose_id)
    if not selected:
        raise SystemExit("No HD poses matched the requested selection")

    columns = max(1, args.columns)
    rows = math.ceil(len(selected) / columns)
    label_height = 34
    gap = 12
    tile = args.thumbnail
    sheet = Image.new(
        "RGB",
        (
            gap + columns * (tile + gap),
            gap + rows * (tile + label_height + gap),
        ),
        (242, 242, 240),
    )
    draw = ImageDraw.Draw(sheet)
    for index, pose_id in enumerate(selected):
        column = index % columns
        row = index // columns
        left = gap + column * (tile + gap)
        top = gap + row * (tile + label_height + gap)
        frame = library.load_pose(pose_id)
        frame.thumbnail((tile, tile), Image.Resampling.LANCZOS)
        background = Image.new("RGBA", (tile, tile), (255, 255, 255, 255))
        background.alpha_composite(
            frame,
            ((tile - frame.width) // 2, (tile - frame.height) // 2),
        )
        sheet.paste(background.convert("RGB"), (left, top))
        draw.text((left, top + tile + 8), pose_id, fill=(18, 18, 18))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    print(f"Rendered {len(selected)} HD poses to {args.output}")


if __name__ == "__main__":
    main()
