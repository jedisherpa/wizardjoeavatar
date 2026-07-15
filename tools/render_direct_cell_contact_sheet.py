#!/usr/bin/env python3
"""Render a human-review contact sheet from direct colored-node JSON assets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent


def load_graphs(prefix: str) -> list[dict[str, Any]]:
    definitions = ROOT / "wizard_avatar" / "definitions"
    references = json.loads(
        (definitions / f"{prefix}_pixel_graphs.json").read_text(encoding="utf-8")
    )["graphs"]
    poses = json.loads(
        (definitions / f"{prefix}_pose_cells.json").read_text(encoding="utf-8")
    )["poses"]
    graphs = [
        {"id": graph["id"], "nodes": graph["nodes"]} for graph in references
    ]
    graphs.extend({"id": pose["id"], "nodes": pose["cells"]} for pose in poses)
    return graphs


def render(prefix: str, output: Path, columns: int = 10) -> None:
    graphs = load_graphs(prefix)
    if len(graphs) != 124:
        raise ValueError(f"expected exactly 124 graphs, found {len(graphs)}")
    tile_width, tile_height = 148, 150
    rows = (len(graphs) + columns - 1) // columns
    image = Image.new("RGB", (tile_width * columns, tile_height * rows), (28, 31, 36))
    draw = ImageDraw.Draw(image)
    for ordinal, graph in enumerate(graphs, start=1):
        column = (ordinal - 1) % columns
        row = (ordinal - 1) // columns
        left, top = column * tile_width, row * tile_height
        draw.rectangle(
            (left, top, left + tile_width - 1, top + tile_height - 1),
            outline=(62, 67, 75),
        )
        nodes = graph["nodes"]
        xs = [int(node["x"]) for node in nodes]
        ys = [int(node["y"]) for node in nodes]
        width, height = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        scale = min(1.55, 116 / width, 116 / height)
        x_offset = left + (tile_width - width * scale) / 2 - min(xs) * scale
        y_offset = top + 4 - min(ys) * scale
        for node in nodes:
            x = x_offset + int(node["x"]) * scale
            y = y_offset + int(node["y"]) * scale
            rgb = tuple(int(value) for value in node["rgb"])
            draw.rectangle((x, y, x + scale, y + scale), fill=rgb)
        label = f"{ordinal:03d} {graph['id']}"
        draw.text((left + 3, top + tile_height - 17), label[:22], fill=(235, 238, 242))
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(args.prefix, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
