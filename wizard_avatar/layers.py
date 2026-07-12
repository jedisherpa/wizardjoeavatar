from __future__ import annotations

import math
from typing import Any, Dict, Iterable, Sequence, Tuple

from .blink import blink_state
from .compositor import CellCanvas
from .expressions import get_expression
from .glyphs import glyph
from .models import WizardState
from .mouth import MOUTH_CELLS, fallback_speech_shape
from .palette import RGB
from .skeleton import skeleton_for
from .views import get_view


LOCAL_WIDTH = 34
LOCAL_HEIGHT = 52
ROOT_ANCHOR = (17, 51)


LAYER_ORDER = [
    "rear_staff",
    "rear_arm",
    "rear_robe",
    "boots",
    "robe_base",
    "inner_magenta_robe",
    "gold_trim",
    "belt_and_buckle",
    "front_arm",
    "hand",
    "neck",
    "head",
    "ears",
    "beard",
    "mouth",
    "nose",
    "eyes",
    "eyebrows",
    "hat_brim",
    "hat_crown",
    "hat_stars",
    "front_staff",
    "cyan_orb",
    "magic_effects",
]


def _xf(x: int, body_width: float, face_shift: int) -> int:
    return round(17 + (x - 17) * body_width + face_shift * 0.35)


def _points(points: Iterable[Tuple[int, int]], body_width: float, face_shift: int, y_offset: int = 0):
    return [(_xf(x, body_width, face_shift), y + y_offset) for x, y in points]


def _draw_outline_polygon(canvas: CellCanvas, points, fill_glyph, fill_rgb, layer_id):
    canvas.polygon(points, glyph("outline"), RGB["outline"], layer_id + "_outline")
    inner = [(x, y + 1) for x, y in points]
    canvas.polygon(inner, fill_glyph, fill_rgb, layer_id)


def _draw_staff(canvas: CellCanvas, hand: Tuple[int, int], state: WizardState, layer_id: str) -> None:
    x, y = hand
    cast = state.action == "magic_cast"
    top = (x - 5, 5 if cast else 8)
    grip = (x, y)
    bottom = (x - 3, 50)
    if cast:
        bottom = (x - 2, 38)
        grip = (x - 1, y - 4)
    canvas.line(bottom[0], bottom[1], grip[0], grip[1], glyph("solid_fill"), RGB["brown_dark"], layer_id, 1)
    canvas.line(grip[0], grip[1], top[0], top[1], glyph("solid_fill"), RGB["brown"], layer_id, 1)
    canvas.line(bottom[0] + 1, bottom[1], grip[0] + 1, grip[1], glyph("soft_fill"), RGB["brown"], layer_id, 1)
    canvas.set(grip[0], grip[1], glyph("skin_fill"), RGB["skin_light"], "hand")
    curl = [
        (top[0], top[1]),
        (top[0] + 1, top[1] - 3),
        (top[0] + 5, top[1] - 3),
        (top[0] + 7, top[1]),
        (top[0] + 5, top[1] + 3),
        (top[0] + 3, top[1] + 2),
    ]
    for a, b in zip(curl, curl[1:]):
        canvas.line(a[0], a[1], b[0], b[1], glyph("outline"), RGB["brown_dark"], layer_id, 1)
    orb = (top[0] + 4, top[1])
    canvas.ellipse(orb[0], orb[1], 2 if not cast else 3, 1 if not cast else 2, glyph("spark"), RGB["cyan_magic"], "cyan_orb")
    canvas.set(orb[0], orb[1], "O", RGB["cyan_magic"], "cyan_orb")


def _draw_magic(canvas: CellCanvas, state: WizardState, hand: Tuple[int, int]) -> None:
    if state.action != "magic_cast":
        return
    phase = (state.time_seconds * 6.0) % 1.0
    radius = 3 + round(phase * 5)
    cx, cy = hand[0] + 2, hand[1] - 25
    for i in range(12):
        angle = i * math.tau / 12.0 + phase * math.tau
        x = round(cx + math.cos(angle) * radius)
        y = round(cy + math.sin(angle) * radius * 0.55)
        mark = "*" if i % 3 == 0 else ("+" if i % 3 == 1 else ".")
        canvas.set(x, y, mark, RGB["cyan_magic"], "magic_effects")


def _draw_boots(canvas: CellCanvas, offsets: Dict[str, Tuple[int, int]], body_width: float, face_shift: int) -> None:
    lx, ly = offsets["left_boot"]
    rx, ry = offsets["right_boot"]
    canvas.rect(_xf(7, body_width, face_shift) + lx, 48 + ly, _xf(15, body_width, face_shift) + lx, 51 + ly, glyph("solid_fill"), RGB["brown_dark"], "boots")
    canvas.rect(_xf(19, body_width, face_shift) + rx, 48 + ry, _xf(27, body_width, face_shift) + rx, 51 + ry, glyph("solid_fill"), RGB["brown"], "boots")
    canvas.line(_xf(6, body_width, face_shift) + lx, 51 + ly, _xf(15, body_width, face_shift) + lx, 51 + ly, glyph("outline"), RGB["outline"], "boots")
    canvas.line(_xf(19, body_width, face_shift) + rx, 51 + ry, _xf(28, body_width, face_shift) + rx, 51 + ry, glyph("outline"), RGB["outline"], "boots")
    canvas.line(_xf(7, body_width, face_shift) + lx, 47 + ly, _xf(16, body_width, face_shift) + lx, 47 + ly, glyph("outline"), RGB["outline"], "boots")
    canvas.line(_xf(18, body_width, face_shift) + rx, 47 + ry, _xf(27, body_width, face_shift) + rx, 47 + ry, glyph("outline"), RGB["outline"], "boots")


def _draw_robe(canvas: CellCanvas, view: Dict[str, Any], offsets: Dict[str, Tuple[int, int]]) -> None:
    bw = float(view["body_width"])
    fs = int(view["face_shift"])
    by = offsets["body"][1]
    robe = _points([(8, 28), (26, 28), (31, 47), (3, 47)], bw, fs, by)
    _draw_outline_polygon(canvas, robe, glyph("cloth_fill"), RGB["blue_mid"], "robe_base")
    canvas.polygon(_points([(9, 30), (25, 30), (29, 46), (5, 46)], bw, fs, by), glyph("cloth_fill"), RGB["blue_dark"], "rear_robe")
    canvas.line(_xf(9, bw, fs), 29 + by, _xf(5, bw, fs), 45 + by, glyph("highlight"), RGB["blue_light"], "robe_highlight")
    canvas.line(_xf(25, bw, fs), 29 + by, _xf(29, bw, fs), 45 + by, glyph("highlight"), RGB["blue_light"], "robe_highlight")
    if view.get("robe_opening", 1.0) > 0:
        opening_half = max(1, round(4 * float(view["robe_opening"])))
        canvas.polygon(
            [(_xf(17 - opening_half, bw, fs), 30 + by), (_xf(17 + opening_half, bw, fs), 30 + by), (_xf(20, bw, fs), 47 + by), (_xf(14, bw, fs), 47 + by)],
            glyph("cloth_fill"),
            RGB["magenta"],
            "inner_magenta_robe",
        )
        canvas.line(_xf(14, bw, fs), 30 + by, _xf(15, bw, fs), 47 + by, glyph("trim"), RGB["gold"], "gold_trim")
        canvas.line(_xf(20, bw, fs), 30 + by, _xf(19, bw, fs), 47 + by, glyph("trim"), RGB["gold"], "gold_trim")
    canvas.line(_xf(6, bw, fs), 36 + by, _xf(28, bw, fs), 36 + by, glyph("belt"), RGB["gold"], "belt_and_buckle", 1)
    canvas.rect(_xf(16, bw, fs), 34 + by, _xf(18, bw, fs), 36 + by, glyph("solid_fill"), RGB["gold_light"], "belt_and_buckle")


def _draw_arms(canvas: CellCanvas, anchors, targets, offsets, action: str, view: Dict[str, Any]) -> None:
    bw = float(view["body_width"])
    fs = int(view["face_shift"])
    left_s = anchors["left_shoulder"]
    right_s = anchors["right_shoulder"]
    left_w = targets["left_wrist"]
    right_w = targets["right_wrist"]
    la = offsets["left_arm"]
    ra = offsets["right_arm"]
    canvas.line(left_s[0], left_s[1], left_w[0] + la[0], left_w[1] + la[1], glyph("cloth_fill"), RGB["blue_dark"], "front_arm", 2)
    canvas.line(right_s[0], right_s[1], right_w[0] + ra[0], right_w[1] + ra[1], glyph("cloth_fill"), RGB["blue_light"], "front_arm", 2)
    canvas.line(left_s[0], left_s[1], left_w[0] + la[0], left_w[1] + la[1], glyph("outline"), RGB["outline"], "arm_outline", 1)
    canvas.line(right_s[0], right_s[1], right_w[0] + ra[0], right_w[1] + ra[1], glyph("outline"), RGB["outline"], "arm_outline", 1)
    canvas.ellipse(left_w[0] + la[0], left_w[1] + la[1], 1, 1, glyph("skin_fill"), RGB["skin_light"], "hand")
    canvas.ellipse(right_w[0] + ra[0], right_w[1] + ra[1], 1, 1, glyph("skin_fill"), RGB["skin_light"], "hand")


def _draw_head_and_face(canvas: CellCanvas, state: WizardState, view: Dict[str, Any], offsets: Dict[str, Tuple[int, int]]) -> None:
    bw = float(view["body_width"])
    fs = int(view["face_shift"])
    by = offsets["body"][1]
    back = bool(view.get("back"))
    profile = bool(view.get("profile"))
    face_center_x = _xf(17, bw, fs)
    if not back:
        canvas.ellipse(face_center_x, 18 + by, max(5, round(7 * bw)), 6, glyph("outline"), RGB["outline"], "head_outline")
        canvas.ellipse(face_center_x, 18 + by, max(4, round(6 * bw)), 5, glyph("skin_fill"), RGB["skin_mid"], "head")
        canvas.ellipse(face_center_x, 17 + by, max(2, round(4 * bw)), 4, glyph("skin_fill"), RGB["skin_light"], "head")
        canvas.ellipse(_xf(9, bw, fs), 18 + by, 1, 2, glyph("skin_fill"), RGB["skin_dark"], "ears")
        canvas.ellipse(_xf(25, bw, fs), 18 + by, 1, 2, glyph("skin_fill"), RGB["skin_dark"], "ears")
        canvas.set(face_center_x, 20 + by, glyph("skin_fill"), RGB["skin_dark"], "nose")
        canvas.set(face_center_x, 21 + by, ".", RGB["skin_dark"], "nose")
    else:
        canvas.ellipse(face_center_x, 18 + by, max(4, round(7 * bw)), 6, glyph("soft_fill"), RGB["blue_dark"], "head")
        canvas.rect(_xf(11, bw, fs), 20 + by, _xf(23, bw, fs), 28 + by, glyph("beard_fill"), RGB["beard_mid"], "beard")

    if float(view.get("beard_visibility", 1.0)) > 0.0:
        beard_width = max(4, round(8 * bw * float(view.get("beard_visibility", 1.0))))
        beard = [
            (face_center_x - beard_width, 22 + by),
            (face_center_x + beard_width, 22 + by),
            (face_center_x + max(2, round(beard_width * 0.85)), 27 + by),
            (face_center_x + max(1, round(beard_width * 0.45)), 33 + by),
            (face_center_x, 36 + by),
            (face_center_x - max(2, round(beard_width * 0.75)), 31 + by),
        ]
        canvas.polygon(beard, glyph("beard_fill"), RGB["beard_dark"], "beard")
        canvas.polygon([(x, y + 1) for x, y in beard[1:-1]], glyph("beard_fill"), RGB["beard_mid"], "beard")
        canvas.line(face_center_x - 5, 23 + by, face_center_x - 1, 24 + by, glyph("beard_fill"), RGB["beard_light"], "moustache")
        canvas.line(face_center_x + 1, 24 + by, face_center_x + 5, 23 + by, glyph("beard_fill"), RGB["beard_light"], "moustache")
        canvas.line(face_center_x - 1, 23 + by, face_center_x - 2, 33 + by, glyph("highlight"), RGB["beard_light"], "beard")
        canvas.line(face_center_x + 2, 23 + by, face_center_x + 1, 32 + by, glyph("highlight"), RGB["beard_light"], "beard")

    if not back:
        _draw_expression_overlay(canvas, state, view, face_center_x, by, profile)


def _draw_expression_overlay(canvas: CellCanvas, state: WizardState, view: Dict[str, Any], cx: int, yoff: int, profile: bool) -> None:
    expr = get_expression(state.expression)
    blink = blink_state(state.time_seconds)
    eye_y = 18 + yoff
    brow_y = 16 + yoff
    left_eye = cx - (3 if not profile else 1)
    right_eye = cx + 4
    if profile:
        right_eye = left_eye
    eye_color = RGB["outline"]
    if blink == "closed":
        eye_glyph = "-"
    elif blink == "half_closed":
        eye_glyph = ":"
    else:
        eye_glyph = glyph("eye")
    if expr.get("eyes") == "wide":
        eye_glyph = "O" if blink == "open" else eye_glyph
    if expr.get("eyes") == "squint" and blink == "open":
        eye_glyph = "-"
    canvas.set(left_eye - 1, eye_y, ".", RGB["skin_dark"], "eye_socket")
    canvas.set(left_eye, eye_y, eye_glyph, eye_color, "eyes")
    if not profile:
        canvas.set(right_eye - 1, eye_y, ".", RGB["skin_dark"], "eye_socket")
        canvas.set(right_eye, eye_y, eye_glyph, eye_color, "eyes")

    def draw_brow(kind: str, x: int, mirrored: bool = False) -> None:
        if kind in {"up", "soft_up"}:
            cells = [(-1, 0, "/"), (0, -1, "-"), (1, -1, "-")]
        elif kind == "down":
            cells = [(-1, 1, "-"), (0, 0, "-"), (1, 0, "\\")]
        elif kind == "pinched":
            cells = [(-1, 0, "\\"), (0, 0, "-"), (1, 1, "/")]
        elif kind == "tilt":
            cells = [(-1, 1, "-"), (0, 0, "-"), (1, -1, "-")]
        else:
            cells = [(-1, 0, "-"), (0, 0, "-"), (1, 0, "-")]
        for dx, dy, mark in cells:
            mdx = -dx if mirrored else dx
            canvas.set(x + mdx, brow_y + dy, mark, RGB["outline"], "eyebrows")

    draw_brow(str(expr.get("brow_left", "level")), left_eye)
    if not profile:
        draw_brow(str(expr.get("brow_right", "level")), right_eye, True)

    mouth_shape = state.mouth
    if state.speech_id is None and mouth_shape == "closed":
        mouth_shape = str(expr.get("mouth", "closed"))
    if state.speech_id is not None:
        mouth_shape = fallback_speech_shape(max(0.0, state.speech_until - state.time_seconds))
    for mx, my, mark in MOUTH_CELLS[mouth_shape]:
        x = cx + (mx - 17)
        if profile and mx > 17:
            continue
        canvas.set(x, my + yoff, mark, RGB["outline"], "mouth")


def _draw_hat(canvas: CellCanvas, state: WizardState, view: Dict[str, Any], offsets: Dict[str, Tuple[int, int]]) -> None:
    bw = float(view["body_width"])
    fs = int(view["face_shift"])
    hat_y = offsets["hat"][1]
    hat_x = offsets["hat"][0]
    crown = _points([(8, 10), (9, 5), (13, 2), (17, 0), (22, 2), (27, 6), (25, 10)], bw, fs, hat_y)
    crown = [(x + hat_x, y) for x, y in crown]
    canvas.polygon(crown, glyph("cloth_fill"), RGB["blue_dark"], "hat_crown")
    inner = _points([(10, 10), (11, 6), (14, 3), (17, 1), (21, 3), (25, 7), (23, 10)], bw, fs, hat_y)
    inner = [(x + hat_x, y) for x, y in inner]
    canvas.polygon(inner, glyph("cloth_fill"), RGB["blue_mid"], "hat_crown")
    tip = _points([(23, 3), (28, 5), (27, 8), (24, 7)], bw, fs, hat_y)
    tip = [(x + hat_x, y) for x, y in tip]
    canvas.polygon(tip, glyph("cloth_fill"), RGB["blue_light"], "hat_tip")
    canvas.line(_xf(4, bw, fs) + hat_x, 11 + hat_y, _xf(30, bw, fs) + hat_x, 11 + hat_y, glyph("solid_fill"), RGB["gold"], "hat_brim", 2)
    canvas.line(_xf(6, bw, fs) + hat_x, 13 + hat_y, _xf(28, bw, fs) + hat_x, 13 + hat_y, glyph("trim"), RGB["gold_light"], "hat_brim", 1)
    canvas.line(_xf(6, bw, fs) + hat_x, 10 + hat_y, _xf(27, bw, fs) + hat_x, 10 + hat_y, glyph("outline"), RGB["outline"], "hat_outline", 1)
    stars = [(14, 5), (19, 4), (23, 8), (12, 9), (20, 7)]
    for sx, sy in stars:
        canvas.set(_xf(sx, bw, fs) + hat_x, sy + hat_y, glyph("spark"), RGB["gold_light"], "hat_stars")
        if sx == 19:
            canvas.set(_xf(sx + 1, bw, fs) + hat_x, sy + 1 + hat_y, glyph("spark"), RGB["gold"], "hat_stars")


def render_wizard_local(state: WizardState) -> CellCanvas:
    view = get_view(state.facing)
    walking = state.locomotion == "walking"
    anchors, offsets, targets = skeleton_for(
        float(view["body_width"]),
        int(view["face_shift"]),
        state.walk_phase,
        walking,
        state.action,
    )
    canvas = CellCanvas(LOCAL_WIDTH, LOCAL_HEIGHT)

    staff_hand = targets["staff_hand"]
    if view.get("staff_side") == "viewer_right":
        staff_hand = (27, staff_hand[1])
    staff_hand = (staff_hand[0] + offsets["staff"][0], staff_hand[1] + offsets["staff"][1])

    if view.get("staff_order") == "rear":
        _draw_staff(canvas, staff_hand, state, "rear_staff")
    _draw_boots(canvas, offsets, float(view["body_width"]), int(view["face_shift"]))
    _draw_robe(canvas, view, offsets)
    _draw_arms(canvas, anchors, targets, offsets, state.action, view)
    _draw_head_and_face(canvas, state, view, offsets)
    _draw_hat(canvas, state, view, offsets)
    if view.get("staff_order") != "rear":
        _draw_staff(canvas, staff_hand, state, "front_staff")
    _draw_magic(canvas, state, staff_hand)
    return canvas
