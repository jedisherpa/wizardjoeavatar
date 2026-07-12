from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

from .geometry import bresenham_line, ellipse_points, point_in_polygon, polygon_bounds
from .models import Cell


class CellCanvas:
    def __init__(
        self,
        width: int,
        height: int,
        fill: Optional[Cell] = None,
    ) -> None:
        self.width = width
        self.height = height
        self.cells: List[List[Optional[Cell]]] = [
            [fill for _ in range(width)] for _ in range(height)
        ]

    def copy(self) -> "CellCanvas":
        other = CellCanvas(self.width, self.height)
        other.cells = [row[:] for row in self.cells]
        return other

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x: int, y: int) -> Optional[Cell]:
        if not self.in_bounds(x, y):
            return None
        return self.cells[y][x]

    def set(self, x: int, y: int, glyph: str, rgb: Tuple[int, int, int], layer_id: str = "") -> None:
        if self.in_bounds(x, y):
            self.cells[y][x] = Cell(glyph[0], rgb, layer_id)

    def clear_cell(self, x: int, y: int) -> None:
        if self.in_bounds(x, y):
            self.cells[y][x] = None

    def rect(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        glyph: str,
        rgb: Tuple[int, int, int],
        layer_id: str = "",
    ) -> None:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                self.set(x, y, glyph, rgb, layer_id)

    def line(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        glyph: str,
        rgb: Tuple[int, int, int],
        layer_id: str = "",
        thickness: int = 1,
    ) -> None:
        radius = max(0, thickness - 1)
        for x, y in bresenham_line(x0, y0, x1, y1):
            for oy in range(-radius, radius + 1):
                for ox in range(-radius, radius + 1):
                    if abs(ox) + abs(oy) <= radius:
                        self.set(x + ox, y + oy, glyph, rgb, layer_id)

    def polygon(
        self,
        points: Sequence[Tuple[int, int]],
        glyph: str,
        rgb: Tuple[int, int, int],
        layer_id: str = "",
    ) -> None:
        if not points:
            return
        min_x, min_y, max_x, max_y = polygon_bounds(points)
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                if point_in_polygon(x + 0.5, y + 0.5, points):
                    self.set(x, y, glyph, rgb, layer_id)

    def ellipse(
        self,
        cx: int,
        cy: int,
        rx: int,
        ry: int,
        glyph: str,
        rgb: Tuple[int, int, int],
        layer_id: str = "",
    ) -> None:
        for x, y in ellipse_points(cx, cy, rx, ry):
            self.set(x, y, glyph, rgb, layer_id)

    def overlay(self, other: "CellCanvas", offset_x: int = 0, offset_y: int = 0) -> None:
        for y in range(other.height):
            for x in range(other.width):
                cell = other.cells[y][x]
                if cell is not None:
                    self.cells[y + offset_y][x + offset_x] = cell

    def to_frame_bytes(self, fallback: Optional[Cell] = None) -> bytes:
        out = bytearray(self.width * self.height * 4)
        cursor = 0
        for row in self.cells:
            for cell in row:
                value = cell or fallback
                if value is None:
                    out[cursor : cursor + 4] = b" \xff\xff\xff"
                else:
                    out[cursor] = ord(value.glyph[0])
                    out[cursor + 1] = value.rgb[0]
                    out[cursor + 2] = value.rgb[1]
                    out[cursor + 3] = value.rgb[2]
                cursor += 4
        return bytes(out)


def blit_scaled(
    stage: CellCanvas,
    local: CellCanvas,
    root_local: Tuple[int, int],
    root_screen: Tuple[float, float],
    scale: float,
) -> None:
    dest_width = max(1, round(local.width * scale))
    dest_height = max(1, round(local.height * scale))
    origin_x = round(root_screen[0] - root_local[0] * scale)
    origin_y = round(root_screen[1] - root_local[1] * scale)

    for dy in range(dest_height):
        sy = min(local.height - 1, int(dy / max(scale, 0.001)))
        for dx in range(dest_width):
            sx = min(local.width - 1, int(dx / max(scale, 0.001)))
            cell = local.get(sx, sy)
            if cell is not None:
                stage_x = origin_x + dx
                stage_y = origin_y + dy
                if stage.in_bounds(stage_x, stage_y):
                    stage.cells[stage_y][stage_x] = cell
