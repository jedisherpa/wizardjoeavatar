from __future__ import annotations

from .compositor import CellCanvas


def copy_pose_canvas(canvas: CellCanvas) -> CellCanvas:
    return canvas.copy()


def blit_pose_scaled(
    stage: CellCanvas,
    local: CellCanvas,
    root_local: tuple[int, int],
    root_screen: tuple[float, float],
    scale: float,
    horizontal_scale: float = 1.0,
) -> None:
    scale_x = max(0.001, scale * horizontal_scale)
    scale_y = max(0.001, scale)
    dest_width = max(1, round(local.width * scale_x))
    dest_height = max(1, round(local.height * scale_y))
    origin_x = round(root_screen[0] - root_local[0] * scale_x)
    origin_y = round(root_screen[1] - root_local[1] * scale_y)

    for dy in range(dest_height):
        sy = min(local.height - 1, int(dy / scale_y))
        for dx in range(dest_width):
            sx = min(local.width - 1, int(dx / scale_x))
            cell = local.get(sx, sy)
            if cell is not None:
                stage_x = origin_x + dx
                stage_y = origin_y + dy
                if stage.in_bounds(stage_x, stage_y):
                    stage.cells[stage_y][stage_x] = cell


def composite_crisp_transition(
    from_canvas: CellCanvas,
    to_canvas: CellCanvas,
    progress: float,
) -> CellCanvas:
    if progress <= 0.0:
        return from_canvas.copy()
    if progress >= 1.0:
        return to_canvas.copy()

    width = max(from_canvas.width, to_canvas.width)
    height = max(from_canvas.height, to_canvas.height)
    out = CellCanvas(width, height)
    for y in range(height):
        for x in range(width):
            from_cell = from_canvas.get(x, y)
            to_cell = to_canvas.get(x, y)
            if from_cell == to_cell:
                out.cells[y][x] = from_cell
            elif _cell_threshold(x, y) < progress:
                out.cells[y][x] = to_cell
            else:
                out.cells[y][x] = from_cell
    return out


def composite_anchor_transition(
    from_canvas: CellCanvas,
    to_canvas: CellCanvas,
    from_root: tuple[int, int],
    to_root: tuple[int, int],
    progress: float,
) -> tuple[CellCanvas, tuple[int, int]]:
    root_x = max(from_root[0], to_root[0])
    root_y = max(from_root[1], to_root[1])
    from_offset = (root_x - from_root[0], root_y - from_root[1])
    to_offset = (root_x - to_root[0], root_y - to_root[1])
    width = max(from_offset[0] + from_canvas.width, to_offset[0] + to_canvas.width)
    height = max(from_offset[1] + from_canvas.height, to_offset[1] + to_canvas.height)

    if progress <= 0.0:
        out = CellCanvas(width, height)
        _blit_unscaled(out, from_canvas, from_offset)
        return out, (root_x, root_y)
    if progress >= 1.0:
        out = CellCanvas(width, height)
        _blit_unscaled(out, to_canvas, to_offset)
        return out, (root_x, root_y)

    out = CellCanvas(width, height)
    for y in range(height):
        from_y = y - from_offset[1]
        to_y = y - to_offset[1]
        for x in range(width):
            from_x = x - from_offset[0]
            to_x = x - to_offset[0]
            from_cell = from_canvas.get(from_x, from_y)
            to_cell = to_canvas.get(to_x, to_y)
            if from_cell == to_cell:
                out.cells[y][x] = from_cell
            elif _cell_threshold(x - root_x, y - root_y) < progress:
                out.cells[y][x] = to_cell
            else:
                out.cells[y][x] = from_cell
    return out, (root_x, root_y)


def translate_anchor(
    anchor: tuple[int, int],
    source_root: tuple[int, int],
    target_root: tuple[int, int],
) -> tuple[int, int]:
    return target_root[0] + anchor[0] - source_root[0], target_root[1] + anchor[1] - source_root[1]


def _blit_unscaled(
    target: CellCanvas,
    source: CellCanvas,
    offset: tuple[int, int],
) -> None:
    for y in range(source.height):
        for x in range(source.width):
            cell = source.get(x, y)
            if cell is not None:
                target.cells[y + offset[1]][x + offset[0]] = cell


def _cell_threshold(x: int, y: int) -> float:
    value = (x * 73856093) ^ (y * 19349663) ^ 0x9E3779B9
    value = (value ^ (value >> 13)) * 1274126177
    return ((value & 0xFFFF) + 0.5) / 65536.0
