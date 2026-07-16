#!/usr/bin/env python3
"""Render a 124-up worksheet isolation audit without creating runtime art."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from generate_voxel_persona_character import (  # noqa: E402
    _cells_for_pose,
    load_profile,
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_contact_sheet(
    items: Sequence[tuple[str, Sequence[Mapping[str, Any]]]],
    destination: Path,
) -> None:
    columns = 10
    tile_width, tile_height = 154, 206
    canvas = Image.new(
        "RGB",
        (columns * tile_width, ((len(items) + columns - 1) // columns) * tile_height),
        (25, 31, 44),
    )
    draw = ImageDraw.Draw(canvas)
    for ordinal, (graph_id, cells) in enumerate(items):
        tile_x = (ordinal % columns) * tile_width
        tile_y = (ordinal // columns) * tile_height
        draw.rectangle(
            (tile_x + 3, tile_y + 3, tile_x + tile_width - 4, tile_y + tile_height - 4),
            fill=(238, 247, 251),
            outline=(95, 111, 132),
        )
        scale = 2
        origin_x, origin_y = tile_x + 5, tile_y + 5
        for cell in cells:
            x = origin_x + int(cell["x"]) * scale
            y = origin_y + int(cell["y"]) * scale
            rgb = tuple(int(channel) for channel in cell["rgb"])
            draw.rectangle((x, y, x + scale - 1, y + scale - 1), fill=rgb)
        label = "{:03d} {}".format(ordinal + 1, graph_id[:19])
        draw.text((tile_x + 6, tile_y + 196), label, fill=(232, 238, 248))
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    parser.add_argument("evidence_dir", type=Path)
    args = parser.parse_args()
    profile = load_profile(args.profile)
    prefix = str(profile["output_prefix"])
    pose_payload = json.loads(
        (ROOT / "wizard_avatar" / "definitions" / f"{prefix}_pose_cells.json").read_text()
    )
    graph_payload = json.loads(
        (ROOT / "wizard_avatar" / "definitions" / f"{prefix}_pixel_graphs.json").read_text()
    )
    stored = {
        str(item["id"]): item["nodes"] for item in graph_payload["graphs"]
    }
    stored.update({str(item["id"]): item["cells"] for item in pose_payload["poses"]})
    raw_items = [*profile.get("reference_cells", ()), *profile["poses"]]
    isolated: list[tuple[str, Sequence[Mapping[str, Any]]]] = []
    projected: list[tuple[str, Sequence[Mapping[str, Any]]]] = []
    comparisons = []
    for raw in raw_items:
        graph_id = str(raw["id"])
        source_cells = _cells_for_pose(profile, raw)
        graph_cells = stored[graph_id]
        isolated.append((graph_id, source_cells))
        projected.append((graph_id, graph_cells))
        comparisons.append(
            {
                "graph_id": graph_id,
                "isolated_node_count": len(source_cells),
                "projected_node_count": len(graph_cells),
                "different_nodes": 0 if source_cells == graph_cells else 1,
                "status": "passed" if source_cells == graph_cells else "failed",
            }
        )
    if len(isolated) != 124 or any(item["status"] != "passed" for item in comparisons):
        raise SystemExit("124-cell isolation/projector equality gate failed")
    evidence_dir = args.evidence_dir.resolve()
    slug = str(profile["character_id"]).removesuffix("-v1")
    isolated_path = evidence_dir / f"{slug}-124-isolated-silhouettes.png"
    projected_path = evidence_dir / f"{slug}-124-pixel-graph-renders.png"
    _render_contact_sheet(isolated, isolated_path)
    _render_contact_sheet(projected, projected_path)
    summary = {
        "schema_version": 1,
        "character_id": profile["character_id"],
        "cell_count": len(comparisons),
        "failed_count": sum(item["status"] != "passed" for item in comparisons),
        "isolated_contact_sheet": str(isolated_path.relative_to(ROOT)),
        "isolated_contact_sheet_sha256": _hash(isolated_path),
        "projected_contact_sheet": str(projected_path.relative_to(ROOT)),
        "projected_contact_sheet_sha256": _hash(projected_path),
        "comparisons": comparisons,
    }
    summary_path = evidence_dir / f"{slug}-124-visual-audit.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "comparisons"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
