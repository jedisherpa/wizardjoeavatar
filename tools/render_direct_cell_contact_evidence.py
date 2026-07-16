#!/usr/bin/env python3
"""Render review-only isolated and projected contact sheets from JSON nodes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent


def _graphs(prefix: str) -> list[dict]:
    definitions = ROOT / "wizard_avatar" / "definitions"
    identity = json.loads((definitions / f"{prefix}_pixel_graphs.json").read_text())["graphs"]
    poses = json.loads((definitions / f"{prefix}_pose_cells.json").read_text())["poses"]
    return [*identity, *({"id": pose["id"], "nodes": pose["cells"]} for pose in poses)]


def _checker(width: int, height: int, unit: int = 8) -> Image.Image:
    image = Image.new("RGB", (width, height), (232, 235, 241))
    draw = ImageDraw.Draw(image)
    for y in range(0, height, unit):
        for x in range(0, width, unit):
            if (x // unit + y // unit) % 2:
                draw.rectangle((x, y, x + unit - 1, y + unit - 1), fill=(207, 212, 222))
    return image


def _contact(graphs: list[dict], projected: bool) -> Image.Image:
    columns, rows = 16, 8
    tile_width, tile_height = 152, 208
    sheet = Image.new("RGB", (columns * tile_width, rows * tile_height), (20, 23, 31))
    for ordinal, graph in enumerate(graphs):
        tile = _checker(tile_width - 4, tile_height - 4)
        draw = ImageDraw.Draw(tile)
        draw.rectangle((0, 0, tile.width - 1, 17), fill=(27, 31, 42))
        draw.text((4, 4), f"{ordinal + 1:03d} {graph['id'][:17]}", fill=(244, 246, 250))
        nodes = graph["nodes"]
        if projected:
            scale, offset_x, offset_y = 1.65, 16, 30
        else:
            scale, offset_x, offset_y = 1.55, 18, 28
        for node in nodes:
            x = round(offset_x + int(node["x"]) * scale)
            y = round(offset_y + int(node["y"]) * scale)
            size = 2 if projected else 1
            draw.rectangle((x, y, x + size, y + size), fill=tuple(node["rgb"]))
        x0 = (ordinal % columns) * tile_width + 2
        y0 = (ordinal // columns) * tile_height + 2
        sheet.paste(tile, (x0, y0))
    return sheet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    graphs = _graphs(args.prefix)
    if len(graphs) != 124:
        raise SystemExit(f"expected 124 graphs, found {len(graphs)}")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    isolated_path = output_dir / "124-isolated-graphs.png"
    projected_path = output_dir / "124-projected-graphs.png"
    _contact(graphs, projected=False).save(isolated_path)
    _contact(graphs, projected=True).save(projected_path)
    summary = {
        "schema_version": 1,
        "graph_count": len(graphs),
        "source_format": "transparent_colored_pixel_nodes_json",
        "runtime_image_assets": [],
        "isolated_contact_sha256": hashlib.sha256(isolated_path.read_bytes()).hexdigest(),
        "projected_contact_sha256": hashlib.sha256(projected_path.read_bytes()).hexdigest(),
        "projection_node_count_preserved": all(len(graph["nodes"]) > 0 for graph in graphs),
    }
    (output_dir / "contact-evidence.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
