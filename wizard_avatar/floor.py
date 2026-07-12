from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Tuple

from .compositor import CellCanvas
from .geometry import clamp, lerp_rgb
from .glyphs import glyph
from .models import Cell
from .palette import ENV_RGB


def _floor_color(base: Tuple[int, int, int], fade: float) -> Tuple[int, int, int]:
    return lerp_rgb(base, ENV_RGB["background"], fade)


@lru_cache(maxsize=8)
def build_background(cols: int, rows: int) -> CellCanvas:
    background = Cell(glyph("empty"), ENV_RGB["background"], "background")
    canvas = CellCanvas(cols, rows, background)
    horizon = round(rows * 0.56)
    near = round(rows * 0.95)
    for y in range(horizon, min(rows, near + 1)):
        depth = (y - horizon) / max(near - horizon, 1)
        fade = 1.0 - clamp(depth, 0.0, 1.0)
        tile_h = max(1, round(1 + depth * 5))
        tile_w = max(5, round(8 + depth * 16))
        perspective_shift = round((0.5 - depth) * 4)
        for x in range(cols):
            rel_x = x - cols // 2 + perspective_shift
            tile_x = rel_x // tile_w
            tile_z = (y - horizon) // tile_h
            is_grid = rel_x % tile_w == 0 or (y - horizon) % tile_h == 0
            base = ENV_RGB["floor_grid"] if is_grid else (
                ENV_RGB["floor_light"] if (tile_x + tile_z) % 2 == 0 else ENV_RGB["floor_alternate"]
            )
            color = _floor_color(base, fade * 0.96)
            mark = glyph("highlight") if is_grid else glyph("empty")
            if not is_grid and depth > 0.45 and (x + y) % 9 == 0:
                mark = glyph("highlight")
            canvas.set(x, y, mark, color, "floor")
    return canvas


def background_hash(cols: int, rows: int) -> str:
    return hashlib.sha256(build_background(cols, rows).to_frame_bytes()).hexdigest()
