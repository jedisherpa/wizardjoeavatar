#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_wizard_joe_performance_geometry import projected_pose_sequence
from wizard_avatar.hd_pose_artifact import HDPoseLibrary


DEFAULT_MANIFEST = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "wizard-joe"
    / "audio-performances-v1"
    / "manifest.json"
)
DEFAULT_LIBRARY_INDEX = (
    ROOT / "assets" / "reference" / "hd_canonical" / "compiled" / "library-index.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def render_clip(
    clip: dict[str, Any],
    library: HDPoseLibrary,
    output_path: Path,
    *,
    tile_size: int,
    columns: int,
) -> None:
    performance = {
        **clip["performance"],
        "_duration_ms": int(clip["audio"]["duration_ms"]),
    }
    pose_ids = projected_pose_sequence(performance)
    columns = max(1, columns)
    rows = math.ceil(len(pose_ids) / columns)
    label_height = 58
    header_height = 72
    gap = 16
    width = gap + columns * (tile_size + gap)
    height = header_height + gap + rows * (tile_size + label_height + gap)
    sheet = Image.new("RGB", (width, height), (238, 239, 237))
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (gap, 18),
        f"{clip['clip_id']} - projected full-frame sequence",
        fill=(20, 20, 20),
    )
    for index, pose_id in enumerate(pose_ids):
        column = index % columns
        row = index // columns
        left = gap + column * (tile_size + gap)
        top = header_height + gap + row * (tile_size + label_height + gap)
        frame = library.load_pose(pose_id)
        frame.thumbnail((tile_size, tile_size), Image.Resampling.LANCZOS)
        background = Image.new("RGBA", (tile_size, tile_size), (255, 255, 255, 255))
        background.alpha_composite(
            frame,
            ((tile_size - frame.width) // 2, (tile_size - frame.height) // 2),
        )
        sheet.paste(background.convert("RGB"), (left, top))
        draw.text(
            (left, top + tile_size + 8),
            f"{index + 1:02d}  {pose_id}",
            fill=(22, 22, 22),
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render large Wizard Joe performance pose review sheets."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--library-index", type=Path, default=DEFAULT_LIBRARY_INDEX)
    parser.add_argument("--clip-id", action="append", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tile-size", type=int, default=560)
    parser.add_argument("--columns", type=int, default=2)
    args = parser.parse_args()

    manifest = _read_json(args.manifest.resolve())
    clips = {clip["clip_id"]: clip for clip in manifest["clips"]}
    if args.all:
        args.clip_id = list(clips)
    if not args.clip_id:
        parser.error("provide at least one --clip-id or use --all")
    unknown = sorted(set(args.clip_id) - set(clips))
    if unknown:
        raise SystemExit(f"Unknown clip ids: {', '.join(unknown)}")
    library = HDPoseLibrary(args.library_index.resolve())
    for clip_id in args.clip_id:
        output_path = args.output_dir / f"{clip_id}.png"
        render_clip(
            clips[clip_id],
            library,
            output_path,
            tile_size=args.tile_size,
            columns=args.columns,
        )
        print(output_path.resolve())


if __name__ == "__main__":
    main()
