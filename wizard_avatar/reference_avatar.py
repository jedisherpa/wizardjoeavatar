from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Tuple

from .compositor import CellCanvas
from .glyphs import glyph


REFERENCE_CELL_PATH = Path(__file__).with_name("definitions") / "reference_avatar_cells.json"
REFERENCE_LAYER_ID = "reference_voxel_png"
REFERENCE_SCALE_MULTIPLIER = 0.90


@lru_cache(maxsize=1)
def _load_reference_payload() -> dict:
    with open(REFERENCE_CELL_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def reference_avatar_available() -> bool:
    return REFERENCE_CELL_PATH.exists()


def reference_root_anchor() -> Tuple[int, int]:
    payload = _load_reference_payload()
    root = payload["root_anchor"]
    return int(root[0]), int(root[1])


def render_reference_avatar_local() -> CellCanvas:
    payload = _load_reference_payload()
    canvas = CellCanvas(int(payload["cols"]), int(payload["rows"]))
    for cell in payload["cells"]:
        rgb = tuple(int(channel) for channel in cell["rgb"])
        canvas.set(int(cell["x"]), int(cell["y"]), glyph("solid_fill"), rgb, REFERENCE_LAYER_ID)
    return canvas
