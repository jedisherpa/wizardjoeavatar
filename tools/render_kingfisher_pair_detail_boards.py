#!/usr/bin/env python3
"""Render close-up closed/open Kingfisher beak pairs from compiled review pixels."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import HDPoseLibrary  # noqa: E402


def render_detail_boards(
    index_path: Path,
    ledger_path: Path,
    output_root: Path,
    *,
    pairs_per_page: int = 6,
    crop_padding: int = 24,
    detail_size: tuple[int, int] = (420, 240),
) -> list[Path]:
    library = HDPoseLibrary(index_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    pairs = list(ledger["pairs"])
    output_root.mkdir(parents=True, exist_ok=True)
    page_paths = []
    for page_index in range(math.ceil(len(pairs) / pairs_per_page)):
        page_pairs = pairs[
            page_index * pairs_per_page:(page_index + 1) * pairs_per_page
        ]
        label_height = 34
        gap = 14
        tile_width, tile_height = detail_size
        page = Image.new(
            "RGB",
            (
                gap + 2 * (tile_width + gap),
                gap + len(page_pairs) * (tile_height + label_height + gap),
            ),
            (238, 238, 235),
        )
        draw = ImageDraw.Draw(page)
        for row, pair in enumerate(page_pairs):
            receipt_path = ledger_path.parent / pair["receipt_path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if "articulation_bbox" in receipt:
                x0, y0, x1, y1 = receipt["articulation_bbox"]
            else:
                resting_frame = library.load_pose(pair["resting_pose_id"])
                alpha_bbox = resting_frame.getchannel("A").getbbox()
                if alpha_bbox is None:
                    raise ValueError(
                        f"empty resting frame: {pair['resting_pose_id']}"
                    )
                body_height = alpha_bbox[3] - alpha_bbox[1]
                x0, y0, x1, y1 = (
                    alpha_bbox[0],
                    alpha_bbox[1],
                    alpha_bbox[2],
                    alpha_bbox[1] + max(1, body_height // 2),
                )
            crop_box = (
                max(0, x0 - crop_padding),
                max(0, y0 - crop_padding),
                min(library.canvas_size[0], x1 + crop_padding),
                min(library.canvas_size[1], y1 + crop_padding),
            )
            for column, pose_id in enumerate(
                (pair["resting_pose_id"], pair["speaking_pose_id"])
            ):
                left = gap + column * (tile_width + gap)
                top = gap + row * (tile_height + label_height + gap)
                crop = library.load_pose(pose_id).crop(crop_box)
                crop.thumbnail(detail_size, Image.Resampling.NEAREST)
                background = Image.new(
                    "RGBA",
                    detail_size,
                    (255, 255, 255, 255),
                )
                background.alpha_composite(
                    crop,
                    (
                        (tile_width - crop.width) // 2,
                        (tile_height - crop.height) // 2,
                    ),
                )
                page.paste(background.convert("RGB"), (left, top))
                state = "CLOSED" if column == 0 else "OPEN"
                draw.text(
                    (left, top + tile_height + 8),
                    f"{int(pair['ordinal']):03d} {pair['slug']} · {state}",
                    fill=(18, 18, 18),
                )
        page_path = output_root / f"pair-detail-page-{page_index + 1:02d}.png"
        page.save(page_path)
        page_paths.append(page_path)
    return page_paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--pairs-per-page", type=int, default=6)
    parser.add_argument("--crop-padding", type=int, default=24)
    args = parser.parse_args()
    pages = render_detail_boards(
        args.index,
        args.ledger,
        args.output_root,
        pairs_per_page=max(1, args.pairs_per_page),
        crop_padding=max(0, args.crop_padding),
    )
    print(json.dumps([path.as_posix() for path in pages], indent=2))


if __name__ == "__main__":
    main()
