#!/usr/bin/env python3
"""Render deterministic visual-audit sheets from direct colored-node graphs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent


def _read_graphs(definitions: Path, prefix: str) -> list[dict[str, Any]]:
    references = json.loads(
        (definitions / f"{prefix}_pixel_graphs.json").read_text(encoding="utf-8")
    )["graphs"]
    poses = json.loads(
        (definitions / f"{prefix}_pose_cells.json").read_text(encoding="utf-8")
    )["poses"]
    graphs = [
        {"id": graph["id"], "nodes": graph["nodes"]}
        for graph in references
    ]
    graphs.extend(
        {"id": pose["id"], "nodes": pose["cells"]}
        for pose in poses
    )
    if len(graphs) != 124:
        raise ValueError(f"expected exactly 124 graphs, found {len(graphs)}")
    return graphs


def _isolated_sheet(graphs: list[dict[str, Any]], cols: int, rows: int) -> Image.Image:
    tile_w, tile_h, gutter = cols * 2, rows * 2, 2
    sheet = Image.new("RGBA", (12 * (tile_w + gutter), 11 * (tile_h + gutter)), (0, 0, 0, 0))
    for index, graph in enumerate(graphs):
        tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(tile)
        for node in graph["nodes"]:
            x, y = int(node["x"]), int(node["y"])
            rgb = tuple(int(channel) for channel in node["rgb"])
            draw.rectangle((x * 2, y * 2, x * 2 + 1, y * 2 + 1), fill=rgb + (255,))
        x = (index % 12) * (tile_w + gutter)
        y = (index // 12) * (tile_h + gutter)
        sheet.alpha_composite(tile, (x, y))
    return sheet


def _projected_sheet(graphs: list[dict[str, Any]], cols: int, rows: int) -> Image.Image:
    tile_w, tile_h, scale, gutter = cols, rows, 2, 2
    background = (21, 29, 33, 255)
    sheet = Image.new(
        "RGBA",
        (12 * (tile_w * scale + gutter), 11 * (tile_h * scale + gutter)),
        background,
    )
    for index, graph in enumerate(graphs):
        tile = Image.new("RGBA", (tile_w * scale, tile_h * scale), background)
        draw = ImageDraw.Draw(tile)
        for node in graph["nodes"]:
            x, y = int(node["x"]), int(node["y"])
            rgb = tuple(int(channel) for channel in node["rgb"])
            draw.rectangle(
                (x * scale, y * scale, x * scale + scale - 1, y * scale + scale - 1),
                fill=rgb + (255,),
            )
        x = (index % 12) * (tile_w * scale + gutter)
        y = (index // 12) * (tile_h * scale + gutter)
        sheet.alpha_composite(tile, (x, y))
    return sheet


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", help="definition filename prefix, such as rohan_slate")
    parser.add_argument("evidence_dir", type=Path)
    args = parser.parse_args()
    definitions = ROOT / "wizard_avatar" / "definitions"
    graphs = _read_graphs(definitions, args.prefix)
    pose_payload = json.loads(
        (definitions / f"{args.prefix}_pose_cells.json").read_text(encoding="utf-8")
    )
    cols = int(pose_payload["canonical"]["cols"])
    rows = int(pose_payload["canonical"]["rows"])
    output_dir = args.evidence_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    isolated_path = output_dir / "124-isolated-transparent-graphs.png"
    projected_path = output_dir / "124-projected-canvas-graphs.png"
    _isolated_sheet(graphs, cols, rows).save(isolated_path)
    _projected_sheet(graphs, cols, rows).save(projected_path)
    hashes = {
        "schema_version": 1,
        "graph_count": len(graphs),
        "graph_order": [graph["id"] for graph in graphs],
        "isolated_contact_sheet": {
            "file": isolated_path.name,
            "sha256": _sha256(isolated_path),
        },
        "projected_contact_sheet": {
            "file": projected_path.name,
            "sha256": _sha256(projected_path),
        },
    }
    (output_dir / "CONTACT_SHEET_HASHES.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Rendered {len(graphs)} isolated and projected graphs into {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
