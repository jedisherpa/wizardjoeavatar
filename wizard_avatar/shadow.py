from __future__ import annotations

from .compositor import CellCanvas
from .glyphs import glyph
from .palette import ENV_RGB


def draw_contact_shadow(
    canvas: CellCanvas,
    root_x: float,
    root_y: float,
    scale: float,
    lifted: bool = False,
) -> None:
    width = max(4, round(11 * scale * (0.78 if lifted else 1.0)))
    height = max(1, round(2.2 * scale))
    cx = round(root_x)
    cy = round(root_y + max(1, scale))
    color = ENV_RGB["contact_shadow"]
    for y in range(cy - height, cy + height + 1):
        for x in range(cx - width, cx + width + 1):
            nx = (x - cx) / max(width, 1)
            ny = (y - cy) / max(height, 1)
            if nx * nx + ny * ny <= 1.0:
                canvas.set(x, y, glyph("highlight"), color, "contact_shadow")
