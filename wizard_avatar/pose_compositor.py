from __future__ import annotations

import math
from typing import Optional, Tuple

from .compositor import CellCanvas


def copy_pose_canvas(canvas: CellCanvas) -> CellCanvas:
    return canvas.copy()


def clear_authored_staff(
    canvas: CellCanvas,
    staff_tip: tuple[int, int],
    staff_hand: tuple[int, int],
    root_anchor: tuple[int, int] | None = None,
) -> int:
    """Remove the authored staff using its manifest-required anchor geometry.

    Reference poses are atomic pixel graphs, so the staff is not a PNG layer.
    The graph does provide stable tip/hand anchors.  We use those anchors plus
    a deliberately narrow material test, preserving skin and robe pixels where
    the prop crosses the body.  Ambiguous pixels remain character pixels; an
    effect-bearing atomic pose is handled separately by a neutral fallback.
    """

    candidates = [(staff_tip, staff_hand)]
    if root_anchor is not None:
        root_x = root_anchor[0]
        mirrored = (
            (2 * root_x - staff_tip[0], staff_tip[1]),
            (2 * root_x - staff_hand[0], staff_hand[1]),
        )
        if mirrored != candidates[0]:
            candidates.append(mirrored)
    masks = [
        _staff_mask(canvas, tip, hand)
        for tip, hand in candidates
    ]
    selected = max(masks, key=lambda points: (len(points), tuple(points)))
    for x, y in selected:
        canvas.clear_cell(x, y)
    return len(selected)


def touch_up_staff_occlusion(
    canvas: CellCanvas,
    original: CellCanvas,
    root_anchor: tuple[int, int],
    staff_tip: tuple[int, int],
    staff_hand: tuple[int, int],
) -> None:
    """Reconstruct flattened pixels that were hidden behind the staff.

    The permission fallback uses the bilateral neutral pose. Mirroring only the
    outer prop side below the hat replaces the occluded arm, hand, and wing
    with complete pixel runs while preserving the authored face and hat.
    """

    if canvas.width != original.width or canvas.height != original.height:
        raise ValueError("touch-up canvases must have matching dimensions")
    root_x, _root_y = root_anchor
    candidates = [(staff_tip, staff_hand)]
    mirrored = (
        (2 * root_x - staff_tip[0], staff_tip[1]),
        (2 * root_x - staff_hand[0], staff_hand[1]),
    )
    if mirrored != candidates[0]:
        candidates.append(mirrored)
    staff_tip, staff_hand = max(
        candidates,
        key=lambda anchors: (
            len(_staff_mask(original, anchors[0], anchors[1])),
            anchors,
        ),
    )
    staff_x = (staff_tip[0] + staff_hand[0]) / 2.0
    prop_side = 1 if staff_x >= root_x else -1
    body_start_y = max(
        0,
        min(staff_tip[1], staff_hand[1])
        + round(abs(staff_hand[1] - staff_tip[1]) * 0.34),
    )
    for y in range(body_start_y, canvas.height):
        for distance in range(8, canvas.width):
            target_x = root_x + prop_side * distance
            source_x = root_x - prop_side * distance
            if canvas.in_bounds(target_x, y) and original.in_bounds(source_x, y):
                canvas.cells[y][target_x] = original.get(source_x, y)


def _staff_mask(
    canvas: CellCanvas,
    staff_tip: tuple[int, int],
    staff_hand: tuple[int, int],
) -> list[tuple[int, int]]:
    tip_x, tip_y = staff_tip
    hand_x, hand_y = staff_hand
    delta_x = hand_x - tip_x
    delta_y = hand_y - tip_y
    length_squared = delta_x * delta_x + delta_y * delta_y
    if length_squared == 0:
        return []
    length = math.sqrt(length_squared)
    selected = []
    for y in range(canvas.height):
        for x in range(canvas.width):
            cell = canvas.get(x, y)
            if cell is None or not _staff_material(cell.rgb):
                continue
            along = ((x - tip_x) * delta_x + (y - tip_y) * delta_y) / length_squared
            distance = abs((x - tip_x) * delta_y - (y - tip_y) * delta_x) / length
            near_shaft = -0.20 <= along <= 2.35 and distance <= 3.25
            near_crook = math.hypot(x - tip_x, y - tip_y) <= 10.0
            if near_shaft or near_crook:
                selected.append((x, y))
    return selected


def _staff_material(rgb: tuple[int, int, int]) -> bool:
    red, green, blue = rgb
    brown = (
        red >= 45
        and red >= green * 1.12
        and green >= blue * 0.90
        and blue <= 135
    )
    neutral_wrap = (
        red >= 105
        and green >= 90
        and blue >= 65
        and max(rgb) - min(rgb) <= 78
    )
    return brown or neutral_wrap


def blit_pose_scaled(
    stage: CellCanvas,
    local: CellCanvas,
    root_local: tuple[int, int],
    root_screen: tuple[float, float],
    scale: float,
    horizontal_scale: float = 1.0,
) -> Optional[Tuple[int, int, int, int]]:
    scale_x = max(0.001, scale * horizontal_scale)
    scale_y = max(0.001, scale)
    dest_width = max(1, round(local.width * scale_x))
    dest_height = max(1, round(local.height * scale_y))
    origin_x = round(root_screen[0] - root_local[0] * scale_x)
    origin_y = round(root_screen[1] - root_local[1] * scale_y)
    occupied: Optional[Tuple[int, int, int, int]] = None

    for dy in range(dest_height):
        sy = min(local.height - 1, int(dy / scale_y))
        for dx in range(dest_width):
            sx = min(local.width - 1, int(dx / scale_x))
            cell = local.get(sx, sy)
            if cell is not None:
                stage_x = origin_x + dx
                stage_y = origin_y + dy
                if occupied is None:
                    occupied = (stage_x, stage_x, stage_y, stage_y)
                else:
                    occupied = (
                        min(occupied[0], stage_x),
                        max(occupied[1], stage_x),
                        min(occupied[2], stage_y),
                        max(occupied[3], stage_y),
                    )
                if stage.in_bounds(stage_x, stage_y):
                    stage.cells[stage_y][stage_x] = cell
    return occupied


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
