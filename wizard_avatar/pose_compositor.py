from __future__ import annotations

import math
from typing import Optional, Sequence, Tuple

from .compositor import CellCanvas
from .models import Cell


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

    resolved_tip, resolved_hand = resolve_authored_staff_anchors(
        canvas,
        staff_tip,
        staff_hand,
        root_anchor,
    )
    selected = _staff_mask(canvas, resolved_tip, resolved_hand)
    for x, y in selected:
        canvas.clear_cell(x, y)
    return len(selected)


def resolve_authored_staff_anchors(
    canvas: CellCanvas,
    staff_tip: tuple[int, int],
    staff_hand: tuple[int, int],
    root_anchor: tuple[int, int] | None = None,
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Resolve legacy mirrored staff anchors against the authored pixels."""

    candidates = [(staff_tip, staff_hand)]
    if root_anchor is not None:
        root_x = root_anchor[0]
        mirrored = (
            (2 * root_x - staff_tip[0], staff_tip[1]),
            (2 * root_x - staff_hand[0], staff_hand[1]),
        )
        if mirrored != candidates[0]:
            candidates.append(mirrored)
    return max(
        candidates,
        key=lambda anchors: (
            len(_staff_mask(canvas, anchors[0], anchors[1])),
            anchors,
        ),
    )


def authored_staff_cells(
    canvas: CellCanvas,
    staff_tip: tuple[int, int],
    staff_hand: tuple[int, int],
    root_anchor: tuple[int, int] | None = None,
) -> dict[tuple[int, int], Cell]:
    """Return the complete authored staff raster keyed by local cell."""

    tagged = {
        (x, y): cell
        for y, row in enumerate(canvas.cells)
        for x, cell in enumerate(row)
        if cell is not None and cell.layer_id == "cast_staff_rigid"
    }
    if tagged:
        return tagged
    resolved_tip, resolved_hand = resolve_authored_staff_anchors(
        canvas,
        staff_tip,
        staff_hand,
        root_anchor,
    )
    result = {}
    for point in _staff_mask(canvas, resolved_tip, resolved_hand):
        cell = canvas.get(*point)
        if cell is not None:
            result[point] = cell
    return result


def author_cast_staff_graph(
    canvas: CellCanvas,
    *,
    source_staff_tip: tuple[int, int],
    source_staff_hand: tuple[int, int],
    root_anchor: tuple[int, int],
    target_staff_tip: tuple[int, int],
    target_staff_hand: tuple[int, int],
) -> None:
    """Rotate the authored neutral staff as one complete pixel appendage.

    The character body remains an atomic source graph. The staff's original
    shaft, hook, width, palette, and length are rigidly transformed around a
    fixed authored grip. The result is baked into the pose library by the
    offline generator; this function is not a runtime render path.
    """

    original = canvas.copy()
    resolved_tip, resolved_hand = resolve_authored_staff_anchors(
        original,
        source_staff_tip,
        source_staff_hand,
        root_anchor,
    )
    staff_cells = authored_staff_cells(original, resolved_tip, resolved_hand)
    if not staff_cells:
        raise ValueError("authored staff mask is empty")
    for x, y in staff_cells:
        canvas.clear_cell(x, y)

    source_axis_x = resolved_tip[0] - resolved_hand[0]
    source_axis_y = resolved_tip[1] - resolved_hand[1]
    target_axis_x = target_staff_tip[0] - target_staff_hand[0]
    target_axis_y = target_staff_tip[1] - target_staff_hand[1]
    source_length = math.hypot(source_axis_x, source_axis_y)
    target_length = math.hypot(target_axis_x, target_axis_y)
    if source_length < 1.0 or target_length < 1.0:
        raise ValueError("cast staff tip and hand must be distinct")
    source_unit = (source_axis_x / source_length, source_axis_y / source_length)
    target_unit = (target_axis_x / target_length, target_axis_y / target_length)
    cosine = source_unit[0] * target_unit[0] + source_unit[1] * target_unit[1]
    sine = source_unit[0] * target_unit[1] - source_unit[1] * target_unit[0]

    # Inverse nearest-cell sampling preserves a solid square-cell graph while
    # retaining the exact source material at every destination cell.
    for y in range(canvas.height):
        for x in range(canvas.width):
            target_dx = x - target_staff_hand[0]
            target_dy = y - target_staff_hand[1]
            source_dx = cosine * target_dx + sine * target_dy
            source_dy = -sine * target_dx + cosine * target_dy
            source_point = (
                round(resolved_hand[0] + source_dx),
                round(resolved_hand[1] + source_dy),
            )
            source_cell = staff_cells.get(source_point)
            if source_cell is not None:
                canvas.cells[y][x] = Cell(
                    source_cell.glyph,
                    source_cell.rgb,
                    "cast_staff_rigid",
                )

    # Restore the authored skin pixels over the shaft so the grip remains
    # unambiguous and the staff cannot paint across the hand.
    hand_x, hand_y = target_staff_hand
    for y in range(hand_y - 5, hand_y + 6):
        for x in range(hand_x - 5, hand_x + 6):
            cell = original.get(x, y)
            if cell is not None and _skin_material(cell.rgb):
                canvas.cells[y][x] = cell


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


def _skin_material(rgb: tuple[int, int, int]) -> bool:
    red, green, blue = rgb
    return red >= 145 and red > green * 1.08 and green > blue * 1.05


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


def composite_landmark_warp_transition(
    from_canvas: CellCanvas,
    to_canvas: CellCanvas,
    control_pairs: Sequence[tuple[tuple[int, int], tuple[int, int]]],
    progress: float,
) -> CellCanvas:
    """Bake a deterministic, nearest-cell landmark warp between atomic poses.

    This is an offline authoring primitive. It moves each endpoint graph toward
    interpolated anatomical landmarks. Each intermediate uses one complete
    endpoint graph, switching texture authority once at the motion midpoint;
    this avoids color-confetti dissolves. The visualizer still receives one
    complete colored-cell graph per frame, with no runtime interpolation.
    """

    if (from_canvas.width, from_canvas.height) != (to_canvas.width, to_canvas.height):
        raise ValueError("landmark-warp canvases must have matching dimensions")
    if not control_pairs:
        raise ValueError("landmark warp requires at least one control pair")
    if progress <= 0.0:
        return from_canvas.copy()
    if progress >= 1.0:
        return to_canvas.copy()

    controls = tuple(
        (
            (float(source[0]), float(source[1])),
            (float(target[0]), float(target[1])),
        )
        for source, target in control_pairs
    )
    out = CellCanvas(from_canvas.width, from_canvas.height)
    for y in range(out.height):
        for x in range(out.width):
            endpoint = "source" if progress <= 0.5 else "target"
            sample_x, sample_y = _inverse_landmark_sample(
                float(x),
                float(y),
                controls,
                progress,
                endpoint=endpoint,
            )
            canvas = from_canvas if endpoint == "source" else to_canvas
            out.cells[y][x] = canvas.get(round(sample_x), round(sample_y))
    return out


def composite_landmark_splat_transition(
    from_canvas: CellCanvas,
    to_canvas: CellCanvas,
    control_pairs: Sequence[tuple[tuple[int, int], tuple[int, int]]],
    progress: float,
) -> CellCanvas:
    """Bake a topology-preserving landmark transition from intact pixel cells.

    Inverse sampling can stretch a bent limb into a hollow ribbon when a
    flattened pose moves a long distance. This authoring primitive instead
    carries every occupied endpoint cell forward toward the interpolated rig.
    It switches endpoint authority once, at the midpoint, and repairs only
    enclosed one-cell raster gaps. Colors are never averaged and the result is
    still one complete atomic pixel graph for the runtime projector.
    """

    if (from_canvas.width, from_canvas.height) != (to_canvas.width, to_canvas.height):
        raise ValueError("landmark-splat canvases must have matching dimensions")
    if not control_pairs:
        raise ValueError("landmark splat requires at least one control pair")
    if progress <= 0.0:
        return from_canvas.copy()
    if progress >= 1.0:
        return to_canvas.copy()

    controls = tuple(
        (
            (float(source[0]), float(source[1])),
            (float(target[0]), float(target[1])),
        )
        for source, target in control_pairs
    )
    endpoint = "source" if progress < 0.5 else "target"
    canvas = from_canvas if endpoint == "source" else to_canvas
    out = CellCanvas(canvas.width, canvas.height)
    priorities: dict[tuple[int, int], tuple[float, int, int]] = {}
    for y, row in enumerate(canvas.cells):
        for x, cell in enumerate(row):
            if cell is None:
                continue
            destination_x, destination_y = _forward_landmark_destination(
                float(x),
                float(y),
                controls,
                progress,
                endpoint=endpoint,
            )
            # Python's bankers rounding collapses adjacent cells at exact
            # half-cell translations. Pixel authoring needs stable half-up
            # quantization so a rigid row remains a rigid row.
            target_x = math.floor(destination_x + 0.5)
            target_y = math.floor(destination_y + 0.5)
            if not (0 <= target_x < out.width and 0 <= target_y < out.height):
                continue
            priority = (
                (destination_x - target_x) ** 2 + (destination_y - target_y) ** 2,
                y,
                x,
            )
            key = (target_x, target_y)
            if key not in priorities or priority < priorities[key]:
                priorities[key] = priority
                out.cells[target_y][target_x] = cell

    _repair_enclosed_splat_gaps(out)
    return out


def composite_localized_landmark_transition(
    from_canvas: CellCanvas,
    to_canvas: CellCanvas,
    source_chain: tuple[tuple[int, int], tuple[int, int]],
    target_chain: tuple[tuple[int, int], tuple[int, int]],
    progress: float,
    *,
    radius: float,
    hand_radius: float,
    repair_axis_x: int,
) -> CellCanvas:
    """Bake one articulated appendage over an otherwise stable source pose.

    Reference poses are flattened pixel graphs, not layered sprites. A global
    landmark warp therefore changes the face, body, wings, and prop when only
    one arm is meant to act. This offline authoring primitive isolates cells
    near a hand-to-joint chain, removes that appendage from the source graph,
    and rigidly carries one complete endpoint raster to the interpolated chain.
    The resulting frame remains a single atomic colored-cell graph.
    """

    if (from_canvas.width, from_canvas.height) != (to_canvas.width, to_canvas.height):
        raise ValueError("localized-warp canvases must have matching dimensions")
    if radius <= 0.0:
        raise ValueError("localized warp radius must be positive")
    if progress <= 0.0:
        return from_canvas.copy()

    progress = min(1.0, progress)
    source_hand, source_joint = source_chain
    target_hand, target_joint = target_chain
    middle_chain = (
        _interpolate_point(source_hand, target_hand, progress),
        _interpolate_point(source_joint, target_joint, progress),
    )
    endpoint_canvas = to_canvas
    endpoint_chain = target_chain

    out = from_canvas.copy()
    for y in range(out.height):
        for x in range(out.width):
            source_cell = from_canvas.get(x, y)
            if (
                source_cell is not None
                and _skin_material(source_cell.rgb)
                and _distance_to_segment((x, y), source_hand, source_joint) <= radius
            ):
                out.cells[y][x] = _gesture_backfill(
                    from_canvas,
                    x,
                    y,
                    repair_axis_x,
                )

    bounds_radius = max(radius, hand_radius)
    min_x = max(0, math.floor(min(middle_chain[0][0], middle_chain[1][0]) - bounds_radius - 1))
    max_x = min(out.width - 1, math.ceil(max(middle_chain[0][0], middle_chain[1][0]) + bounds_radius + 1))
    min_y = max(0, math.floor(min(middle_chain[0][1], middle_chain[1][1]) - bounds_radius - 1))
    max_y = min(out.height - 1, math.ceil(max(middle_chain[0][1], middle_chain[1][1]) + bounds_radius + 1))
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            sample_x, sample_y = _map_between_segment_frames(
                (float(x), float(y)),
                middle_chain,
                endpoint_chain,
            )
            if not _in_articulated_region(
                (sample_x, sample_y),
                endpoint_chain[0],
                endpoint_chain[1],
                radius,
                hand_radius,
            ):
                continue
            sample_cell_x = round(sample_x)
            sample_cell_y = round(sample_y)
            cell = endpoint_canvas.get(sample_cell_x, sample_cell_y)
            if cell is not None and _gesture_cell(
                endpoint_canvas,
                sample_cell_x,
                sample_cell_y,
            ):
                out.cells[y][x] = cell
    return out


def _interpolate_point(
    source: tuple[int, int],
    target: tuple[int, int],
    progress: float,
) -> tuple[float, float]:
    return (
        source[0] + (target[0] - source[0]) * progress,
        source[1] + (target[1] - source[1]) * progress,
    )


def _map_between_segment_frames(
    point: tuple[float, float],
    from_chain: tuple[tuple[float, float], tuple[float, float]],
    to_chain: tuple[tuple[int, int], tuple[int, int]],
) -> tuple[float, float]:
    from_hand, from_joint = from_chain
    to_hand, to_joint = to_chain
    from_dx = from_joint[0] - from_hand[0]
    from_dy = from_joint[1] - from_hand[1]
    to_dx = to_joint[0] - to_hand[0]
    to_dy = to_joint[1] - to_hand[1]
    from_length = math.hypot(from_dx, from_dy)
    to_length = math.hypot(to_dx, to_dy)
    if from_length < 1.0 or to_length < 1.0:
        raise ValueError("localized warp chains must have distinct endpoints")
    along = (
        (point[0] - from_hand[0]) * from_dx
        + (point[1] - from_hand[1]) * from_dy
    ) / (from_length * from_length)
    perpendicular = (
        -(point[0] - from_hand[0]) * from_dy
        + (point[1] - from_hand[1]) * from_dx
    ) / from_length
    to_unit_perpendicular = (-to_dy / to_length, to_dx / to_length)
    return (
        to_hand[0] + along * to_dx + perpendicular * to_unit_perpendicular[0],
        to_hand[1] + along * to_dy + perpendicular * to_unit_perpendicular[1],
    )


def _distance_to_segment(
    point: tuple[float, float],
    start: tuple[float, float] | tuple[int, int],
    end: tuple[float, float] | tuple[int, int],
) -> float:
    delta_x = end[0] - start[0]
    delta_y = end[1] - start[1]
    length_squared = delta_x * delta_x + delta_y * delta_y
    if length_squared <= 0.0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    along = max(
        0.0,
        min(
            1.0,
            ((point[0] - start[0]) * delta_x + (point[1] - start[1]) * delta_y)
            / length_squared,
        ),
    )
    nearest_x = start[0] + along * delta_x
    nearest_y = start[1] + along * delta_y
    return math.hypot(point[0] - nearest_x, point[1] - nearest_y)


def _in_articulated_region(
    point: tuple[float, float],
    hand: tuple[int, int],
    joint: tuple[int, int],
    radius: float,
    hand_radius: float,
) -> bool:
    if _distance_to_segment(point, hand, joint) <= radius:
        return True
    hand_dx = point[0] - hand[0]
    hand_dy = point[1] - hand[1]
    joint_dx = joint[0] - hand[0]
    joint_dy = joint[1] - hand[1]
    points_away_from_joint = hand_dx * joint_dx + hand_dy * joint_dy <= 0.0
    return points_away_from_joint and math.hypot(hand_dx, hand_dy) <= hand_radius


def _gesture_primary_material(rgb: tuple[int, int, int]) -> bool:
    red, green, blue = rgb
    skin = red >= 140 and red > green * 1.06 and green > blue * 1.02
    robe = blue >= 90 and blue > red * 1.05 and blue >= green * 0.88
    return skin or robe


def _gesture_cell(canvas: CellCanvas, x: int, y: int) -> bool:
    cell = canvas.get(x, y)
    if cell is None:
        return False
    if _gesture_primary_material(cell.rgb):
        return True
    if max(cell.rgb) > 105:
        return False
    return any(
        neighbor is not None and _gesture_primary_material(neighbor.rgb)
        for neighbor_y in range(y - 1, y + 2)
        for neighbor_x in range(x - 1, x + 2)
        if (neighbor_x, neighbor_y) != (x, y)
        for neighbor in (canvas.get(neighbor_x, neighbor_y),)
    )


def _gesture_backfill(
    canvas: CellCanvas,
    x: int,
    y: int,
    repair_axis_x: int,
) -> Cell | None:
    mirrored = canvas.get(2 * repair_axis_x - x, y)
    if mirrored is not None and not _skin_material(mirrored.rgb):
        return mirrored
    for radius in range(1, 6):
        candidates = (
            (x - radius, y),
            (x + radius, y),
            (x, y - radius),
            (x, y + radius),
        )
        for candidate_x, candidate_y in candidates:
            candidate = canvas.get(candidate_x, candidate_y)
            if candidate is not None and not _skin_material(candidate.rgb):
                return candidate
    return None


def _inverse_landmark_sample(
    x: float,
    y: float,
    controls: Sequence[tuple[tuple[float, float], tuple[float, float]]],
    progress: float,
    *,
    endpoint: str,
) -> tuple[float, float]:
    weighted_dx = 0.0
    weighted_dy = 0.0
    total_weight = 0.0
    for source, target in controls:
        middle_x = source[0] + (target[0] - source[0]) * progress
        middle_y = source[1] + (target[1] - source[1]) * progress
        distance_squared = (x - middle_x) ** 2 + (y - middle_y) ** 2
        weight = 1.0 / (distance_squared + 4.0)
        endpoint_point = source if endpoint == "source" else target
        weighted_dx += (endpoint_point[0] - middle_x) * weight
        weighted_dy += (endpoint_point[1] - middle_y) * weight
        total_weight += weight
    return (
        x + weighted_dx / total_weight,
        y + weighted_dy / total_weight,
    )


def _forward_landmark_destination(
    x: float,
    y: float,
    controls: Sequence[tuple[tuple[float, float], tuple[float, float]]],
    progress: float,
    *,
    endpoint: str,
) -> tuple[float, float]:
    weighted_dx = 0.0
    weighted_dy = 0.0
    total_weight = 0.0
    for source, target in controls:
        endpoint_point = source if endpoint == "source" else target
        middle_x = source[0] + (target[0] - source[0]) * progress
        middle_y = source[1] + (target[1] - source[1]) * progress
        distance_squared = (x - endpoint_point[0]) ** 2 + (y - endpoint_point[1]) ** 2
        weight = 1.0 / (distance_squared + 4.0)
        weighted_dx += (middle_x - endpoint_point[0]) * weight
        weighted_dy += (middle_y - endpoint_point[1]) * weight
        total_weight += weight
    return x + weighted_dx / total_weight, y + weighted_dy / total_weight


def _repair_enclosed_splat_gaps(canvas: CellCanvas) -> None:
    repairs: list[tuple[int, int, Cell]] = []
    for y in range(1, canvas.height - 1):
        for x in range(1, canvas.width - 1):
            if canvas.get(x, y) is not None:
                continue
            cardinal = (
                canvas.get(x - 1, y),
                canvas.get(x + 1, y),
                canvas.get(x, y - 1),
                canvas.get(x, y + 1),
            )
            if sum(cell is not None for cell in cardinal) < 3:
                continue
            neighbors = [
                cell
                for neighbor_y in range(y - 1, y + 2)
                for neighbor_x in range(x - 1, x + 2)
                for cell in (canvas.get(neighbor_x, neighbor_y),)
                if cell is not None
            ]
            if len(neighbors) < 6:
                continue
            chosen = max(
                neighbors,
                key=lambda cell: (
                    sum(candidate.rgb == cell.rgb for candidate in neighbors),
                    cell.rgb,
                    cell.layer_id,
                ),
            )
            repairs.append((x, y, chosen))
    for x, y, cell in repairs:
        canvas.cells[y][x] = cell


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
