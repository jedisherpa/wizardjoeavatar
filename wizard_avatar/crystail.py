from __future__ import annotations

import math
from typing import Dict, Iterable, Tuple

from .compositor import CellCanvas
from .models import WizardState


CRYSTAIL_CHARACTER_ID = "crystail-v1"
CRYSTAIL_ROOT_ANCHOR = (36, 91)
CRYSTAIL_SCALE_MULTIPLIER = 0.88

PALETTE: Dict[str, Tuple[int, int, int]] = {
    "outline": (5, 65, 29),
    "green_shadow": (5, 91, 31),
    "green": (4, 128, 35),
    "green_light": (12, 158, 45),
    "belly_shadow": (181, 166, 90),
    "belly": (224, 213, 139),
    "eye": (185, 142, 72),
    "pupil": (35, 30, 18),
    "tooth": (245, 235, 194),
    "mouth": (72, 25, 23),
    "tongue": (205, 80, 91),
    "red": (238, 55, 19),
    "orange": (250, 119, 12),
    "yellow": (239, 194, 13),
    "wing_green": (49, 157, 45),
    "cyan": (15, 138, 143),
    "blue": (18, 88, 142),
    "violet": (105, 55, 139),
    "pink": (210, 45, 94),
    "spark": (119, 239, 227),
}

CRYSTAIL_POSE_IDS = (
    "neutral_front", "neutral_three_quarter_left", "neutral_left_profile",
    "neutral_back_three_quarter_left", "neutral_back",
    "neutral_back_three_quarter_right", "neutral_right_profile",
    "neutral_three_quarter_right", "idle_relaxed", "idle_attentive",
    "idle_speaking", "idle_listening", "walk_contact_left", "walk_passing_left",
    "walk_contact_right", "walk_passing_right", "run_reach", "run_drive",
    "turn_left", "turn_right", "crouch", "jump_anticipation", "jump_airborne",
    "fall", "land", "hover_up", "hover_down", "bank_left", "bank_right",
    "glide", "takeoff", "touchdown", "gesture_explain", "gesture_point",
    "gesture_present", "gesture_think", "gesture_react", "gesture_celebrate",
    "gesture_containment", "magic_cast", "listen_compassionate",
) + tuple(
    "expression_{}".format(name)
    for name in (
        "neutral", "calm", "joy", "amusement", "excitement", "curiosity",
        "confidence", "compassion", "surprise", "confusion", "skepticism",
        "concern", "sadness", "shame", "embarrassment", "fear", "anxiety",
        "anger", "frustration", "determination", "fatigue", "contemplation",
    )
)

FACING_POSES = {
    "south": "neutral_front",
    "southwest": "neutral_three_quarter_left",
    "west": "neutral_left_profile",
    "northwest": "neutral_back_three_quarter_left",
    "north": "neutral_back",
    "northeast": "neutral_back_three_quarter_right",
    "east": "neutral_right_profile",
    "southeast": "neutral_three_quarter_right",
}


def resolve_crystail_pose_id(state: WizardState) -> str:
    if state.pose_override_id in CRYSTAIL_POSE_IDS:
        return str(state.pose_override_id)
    if state.speech_id is not None or state.action == "speaking":
        speech_poses = (
            "expression_calm", "expression_joy", "expression_amusement",
            "expression_excitement", "expression_surprise", "expression_confusion",
        )
        return speech_poses[int(state.time_seconds * 10) % len(speech_poses)]
    action_poses = {
        "speaking": "idle_speaking",
        "explaining": "gesture_explain",
        "pointing": "gesture_point",
        "thinking": "gesture_think",
        "reaction": "gesture_react",
        "magic_cast": "magic_cast",
        "celebrating": "gesture_celebrate",
        "containment": "gesture_containment",
    }
    if state.action in action_poses:
        return action_poses[state.action]
    expression_aliases = {
        "happy": "joy", "amused": "amusement", "surprised": "surprise",
        "worried": "concern", "confident": "confidence", "skeptical": "skepticism",
        "thinking": "contemplation", "focused": "determination", "explaining": "curiosity",
    }
    expression = expression_aliases.get(state.expression, state.expression)
    expression_pose = "expression_{}".format(expression)
    if expression != "neutral" and expression_pose in CRYSTAIL_POSE_IDS:
        return expression_pose
    if state.airborne:
        if state.mobility_mode == "takeoff":
            return "takeoff"
        if state.mobility_mode == "landing":
            return "touchdown"
        if state.velocity["x"] < -0.25:
            return "bank_left"
        if state.velocity["x"] > 0.25:
            return "bank_right"
        return "hover_up" if math.sin(state.time_seconds * math.tau * 1.8) >= 0 else "hover_down"
    if state.locomotion == "walking":
        phase = state.walk_phase % 1.0
        return ("walk_contact_left", "walk_passing_left", "walk_contact_right", "walk_passing_right")[
            min(3, int(phase * 4))
        ]
    return FACING_POSES.get(state.facing, "neutral_front")


def render_crystail_local(state: WizardState, pose_id: str | None = None) -> CellCanvas:
    pose_id = pose_id or resolve_crystail_pose_id(state)
    canvas = CellCanvas(72, 96)
    phase = state.walk_phase * math.tau
    airborne = state.airborne or pose_id in {"jump_airborne", "fall", "hover_up", "hover_down", "bank_left", "bank_right", "glide", "takeoff"}
    walking = state.locomotion == "walking" or pose_id.startswith("walk_") or pose_id.startswith("run_")
    performance = state.action in {"speaking", "explaining", "pointing", "reaction", "magic_cast", "celebrating", "containment"}
    bob = round(math.sin(phase * 2.0) * 1.0) if walking else round(math.sin(state.time_seconds * math.tau * 0.7) * 0.5)
    if airborne:
        bob += round(math.sin(state.time_seconds * math.tau * 1.8))
    hip_sway = round(math.sin(phase) * 1.2) if walking else round(math.sin(state.time_seconds * 2.1) * 0.5)
    talk_sway = round(math.sin(state.time_seconds * 4.0)) if performance else 0
    cx = 36 + hip_sway
    root_y = CRYSTAIL_ROOT_ANCHOR[1] + bob
    back_view = state.facing in {"north", "northwest", "northeast"} or "back" in pose_id
    profile = state.facing in {"east", "west"} or "profile" in pose_id
    looking_left = state.facing in {"west", "southwest", "northwest"} or "left" in pose_id

    _draw_tail(canvas, cx, root_y, looking_left, phase, walking)
    _draw_wings(canvas, cx, root_y, state, pose_id, airborne, back_view)
    _draw_legs(canvas, cx, root_y, phase, walking, airborne, pose_id)
    _draw_body(canvas, cx, root_y, back_view)
    _draw_arms(canvas, cx, root_y, state, pose_id, talk_sway, looking_left)
    _draw_head(canvas, cx, root_y, state, profile, looking_left, back_view, talk_sway)
    _draw_effects(canvas, cx, root_y, state, pose_id)
    return canvas


def _fill(canvas: CellCanvas, x0: int, y0: int, x1: int, y1: int, color: str, layer: str) -> None:
    canvas.rect(x0, y0, x1, y1, "#", PALETTE[color], layer)


def _draw_tail(canvas: CellCanvas, cx: int, root_y: int, left: bool, phase: float, moving: bool) -> None:
    direction = -1 if left else 1
    wave = round(math.sin(phase + 0.8) * 2) if moving else 0
    points = [(cx, root_y - 23), (cx + direction * 12, root_y - 17), (cx + direction * 22, root_y - 12 + wave), (cx + direction * 15, root_y - 8), (cx + direction * 5, root_y - 12)]
    canvas.polygon(points, "#", PALETTE["outline"], "crystail_tail_outline")
    inner = [(x - direction, y - 1) for x, y in points[:-1]] + [(cx + direction * 4, root_y - 13)]
    canvas.polygon(inner, "#", PALETTE["green_shadow"], "crystail_tail")


def _draw_wings(canvas: CellCanvas, cx: int, root_y: int, state: WizardState, pose_id: str, airborne: bool, back_view: bool) -> None:
    flap = math.sin(state.time_seconds * math.tau * 1.8)
    extended = airborne or pose_id in {"gesture_celebrate", "magic_cast", "gesture_react"}
    lift = round(flap * 7) if airborne else (-5 if pose_id == "gesture_celebrate" else 0)
    span = 29 if extended else 23
    top = root_y - (62 if extended else 51) + lift
    bottom = root_y - (25 if extended else 28)
    for side in (-1, 1):
        inner_x = cx + side * 8
        outer_x = cx + side * span
        poly = [(inner_x, root_y - 44), (cx + side * 14, top), (outer_x, top + 8), (outer_x, bottom), (cx + side * 12, root_y - 31)]
        canvas.polygon(poly, "#", PALETTE["outline"], "crystail_wing_outline")
        band_colors = ("red", "orange", "yellow", "wing_green", "cyan", "blue", "violet", "pink")
        y0 = top + 3
        height = max(16, bottom - y0)
        for index, color in enumerate(band_colors):
            x_outer = outer_x - side * 2
            x_inner = inner_x + side * 2
            by0 = y0 + round(index * height / len(band_colors))
            by1 = y0 + round((index + 1) * height / len(band_colors))
            points = [(x_inner, max(by0, root_y - 43)), (x_outer, by0), (x_outer, by1), (x_inner, min(by1, root_y - 30))]
            canvas.polygon(points, "#", PALETTE[color], f"crystail_wing_{color}")
            canvas.set(x_outer, by0, "#", PALETTE[color], f"crystail_wing_{color}")
    if back_view:
        _fill(canvas, cx - 7, root_y - 48, cx + 7, root_y - 25, "green_shadow", "crystail_back")


def _draw_legs(canvas: CellCanvas, cx: int, root_y: int, phase: float, moving: bool, airborne: bool, pose_id: str) -> None:
    stride = round(math.sin(phase) * 4) if moving else 0
    crouch = 5 if pose_id in {"crouch", "jump_anticipation", "touchdown", "land"} else 0
    tuck = 7 if airborne else 0
    for side in (-1, 1):
        leg_x = cx + side * 7 + side * stride
        leg_y = root_y - 22 + crouch
        foot_y = root_y - tuck
        _fill(canvas, leg_x - 4, leg_y, leg_x + 3, foot_y - 3, "green_shadow", "crystail_leg")
        toe_x = leg_x + side * 2
        _fill(canvas, toe_x - 5, foot_y - 4, toe_x + 5, foot_y, "green", "crystail_foot")
        _fill(canvas, toe_x - 5, foot_y - 2, toe_x - 3, foot_y + 1, "outline", "crystail_toe")
        _fill(canvas, toe_x + 2, foot_y - 2, toe_x + 4, foot_y + 1, "outline", "crystail_toe")


def _draw_body(canvas: CellCanvas, cx: int, root_y: int, back_view: bool) -> None:
    canvas.polygon([(cx - 13, root_y - 47), (cx + 12, root_y - 47), (cx + 15, root_y - 20), (cx + 9, root_y - 12), (cx - 10, root_y - 12), (cx - 15, root_y - 22)], "#", PALETTE["outline"], "crystail_body_outline")
    canvas.polygon([(cx - 11, root_y - 45), (cx + 10, root_y - 45), (cx + 12, root_y - 22), (cx + 7, root_y - 15), (cx - 8, root_y - 15), (cx - 12, root_y - 23)], "#", PALETTE["green"], "crystail_body")
    if not back_view:
        _fill(canvas, cx - 5, root_y - 43, cx + 5, root_y - 17, "belly_shadow", "crystail_belly_shadow")
        for y in range(root_y - 42, root_y - 17, 5):
            _fill(canvas, cx - 4, y, cx + 4, min(root_y - 18, y + 3), "belly", "crystail_belly_plate")


def _draw_arms(canvas: CellCanvas, cx: int, root_y: int, state: WizardState, pose_id: str, sway: int, leftward: bool) -> None:
    presenting = pose_id in {"gesture_explain", "gesture_present", "idle_speaking"} or state.action in {"speaking", "explaining"}
    pointing = pose_id == "gesture_point" or state.action == "pointing"
    contained = pose_id == "gesture_containment" or state.action == "containment"
    for side in (-1, 1):
        shoulder = (cx + side * 11, root_y - 42)
        if contained:
            hand = (cx + side * 4, root_y - 28 + side)
        elif pointing and side == ( -1 if leftward else 1):
            hand = (cx + side * 25, root_y - 45)
        elif presenting:
            hand = (cx + side * (19 + sway), root_y - 36 - side * sway)
        elif pose_id in {"gesture_celebrate", "magic_cast"}:
            hand = (cx + side * 18, root_y - 56)
        elif pose_id in {"gesture_think"} and side == 1:
            hand = (cx + 10, root_y - 55)
        else:
            hand = (cx + side * 15, root_y - 27)
        canvas.line(shoulder[0], shoulder[1], hand[0], hand[1], "#", PALETTE["outline"], "crystail_arm_outline", thickness=4)
        canvas.line(shoulder[0], shoulder[1], hand[0], hand[1], "#", PALETTE["green"], "crystail_arm", thickness=2)
        _fill(canvas, hand[0] - 3, hand[1] - 2, hand[0] + 3, hand[1] + 2, "green_light", "crystail_hand")
        # Canonical three-digit hand: two outer digits plus the inner opposable block.
        _fill(canvas, hand[0] + side * 2, hand[1] - 3, hand[0] + side * 4, hand[1] - 2, "green_light", "crystail_digit")
        _fill(canvas, hand[0] + side * 2, hand[1] + 2, hand[0] + side * 4, hand[1] + 3, "green_light", "crystail_digit")
        _fill(canvas, hand[0] - side * 3, hand[1], hand[0] - side, hand[1] + 2, "green_shadow", "crystail_opposable_digit")


def _draw_head(canvas: CellCanvas, cx: int, root_y: int, state: WizardState, profile: bool, leftward: bool, back_view: bool, sway: int) -> None:
    head_x = cx + sway
    head_y = root_y - 65
    _fill(canvas, head_x - 7, head_y + 8, head_x + 7, root_y - 42, "outline", "crystail_neck_outline")
    _fill(canvas, head_x - 5, head_y + 8, head_x + 5, root_y - 42, "green_shadow", "crystail_neck")
    if not back_view:
        for y in range(head_y + 10, root_y - 42, 4):
            _fill(canvas, head_x - 3, y, head_x + 3, min(root_y - 43, y + 2), "belly", "crystail_throat_plate")
    _fill(canvas, head_x - 10, head_y - 8, head_x + 11, head_y + 12, "outline", "crystail_head_outline")
    _fill(canvas, head_x - 8, head_y - 6, head_x + 9, head_y + 10, "green", "crystail_head")
    # Stepped antler-like horns are an immutable silhouette feature.
    for side in (-1, 1):
        hx = head_x + side * 6
        _fill(canvas, hx - 2, head_y - 13, hx + 2, head_y - 7, "green_shadow", "crystail_horn")
        _fill(canvas, hx + side * 2, head_y - 18, hx + side * 5, head_y - 12, "green", "crystail_horn")
        _fill(canvas, hx + side * 5, head_y - 22, hx + side * 8, head_y - 17, "green_shadow", "crystail_horn_tip")
    if back_view:
        return
    muzzle_side = -1 if leftward else 1
    muzzle_x = head_x + (muzzle_side * 7 if profile else 1)
    _fill(canvas, muzzle_x - 7, head_y + 4, muzzle_x + 12, head_y + 13, "outline", "crystail_muzzle_outline")
    _fill(canvas, muzzle_x - 5, head_y + 4, muzzle_x + 10, head_y + 10, "green_light", "crystail_muzzle")
    expression = state.expression
    blink = state.blink_phase > 0.955
    eye_y = head_y - 1
    eye_offsets: Iterable[int] = ((-5, 5) if not profile else ((4,) if not leftward else (-4,)))
    for eye_offset in eye_offsets:
        ex = head_x + eye_offset
        if blink or expression in {"amused", "shame", "embarrassment", "fatigue"}:
            _fill(canvas, ex - 2, eye_y, ex + 2, eye_y + 1, "pupil", "crystail_eye_blink")
        else:
            eye_height = 5 if expression in {"surprised", "excitement", "fear", "anxiety"} else 3
            _fill(canvas, ex - 2, eye_y - eye_height // 2, ex + 2, eye_y + eye_height // 2, "eye", "crystail_eye")
            _fill(canvas, ex, eye_y, ex + (1 if not leftward else -1), eye_y + 1, "pupil", "crystail_pupil")
        brow_delta = -2 if expression in {"anger", "frustration", "determination", "focused"} else (-4 if expression in {"surprised", "excitement"} else -3)
        canvas.line(ex - 3, eye_y + brow_delta, ex + 3, eye_y + brow_delta + (1 if expression in {"skeptical", "curiosity"} and eye_offset > 0 else 0), "#", PALETTE["outline"], "crystail_brow")
    _draw_mouth(canvas, muzzle_x, head_y, state)


def _draw_mouth(canvas: CellCanvas, muzzle_x: int, head_y: int, state: WizardState) -> None:
    shape = state.mouth
    if state.speech_id is not None or state.action == "speaking":
        speech_cycle = ("closed", "slightly_open", "wide_vowel", "open_vowel", "rounded_vowel", "teeth_consonant", "tongue_consonant", "smile_speaking")
        shape = speech_cycle[int(state.time_seconds * 12) % len(speech_cycle)]
    aliases = {"open_small": "slightly_open", "open_medium": "open_vowel", "open_wide": "wide_vowel", "rounded": "rounded_vowel", "smile": "smile_speaking", "frown": "frown_speaking"}
    shape = aliases.get(shape, shape)
    y = head_y + 8
    if shape == "closed":
        _fill(canvas, muzzle_x - 3, y, muzzle_x + 5, y, "mouth", "crystail_mouth")
        for tx in (-3, 0, 3, 6):
            _fill(canvas, muzzle_x + tx, y + 1, muzzle_x + tx + 1, y + 2, "tooth", "crystail_tooth")
        return
    width = 4 if shape in {"slightly_open", "rounded_vowel", "lower_lip_consonant"} else 7
    height = 2 if shape in {"slightly_open", "teeth_consonant", "tongue_consonant"} else 4
    _fill(canvas, muzzle_x - width // 2, y - 1, muzzle_x + width, y + height, "mouth", "crystail_mouth")
    if shape in {"teeth_consonant", "wide_vowel", "smile_speaking"}:
        _fill(canvas, muzzle_x - width // 2 + 1, y - 1, muzzle_x + width - 1, y, "tooth", "crystail_teeth")
    if shape in {"tongue_consonant", "open_vowel", "speech_emphasis"}:
        _fill(canvas, muzzle_x, y + height - 1, muzzle_x + 3, y + height, "tongue", "crystail_tongue")
    # Four canonical upper teeth remain readable outside the mouth cavity.
    for tx in (-3, 0, 3, 6):
        _fill(canvas, muzzle_x + tx, y + 1, muzzle_x + tx + 1, y + 3, "tooth", "crystail_tooth")


def _draw_effects(canvas: CellCanvas, cx: int, root_y: int, state: WizardState, pose_id: str) -> None:
    if pose_id == "magic_cast" or state.action == "magic_cast":
        angle = state.time_seconds * math.tau * 1.4
        for index in range(12):
            x = round(cx + math.cos(angle + index * math.tau / 12) * 27)
            y = round(root_y - 52 + math.sin(angle + index * math.tau / 12) * 12)
            _fill(canvas, x, y, x + (index % 2), y + (index % 2), "spark", "crystail_magic")
    if pose_id == "gesture_containment" or state.action == "containment":
        # A soft visual boundary and closed posture settle her without changing identity.
        for x in range(cx - 17, cx + 18, 3):
            canvas.set(x, root_y - 52, "#", PALETTE["cyan"], "crystail_containment")
            canvas.set(x, root_y - 12, "#", PALETTE["cyan"], "crystail_containment")


def state_for_pose(pose_id: str) -> WizardState:
    state = WizardState(character_id=CRYSTAIL_CHARACTER_ID)
    state.pose_override_id = pose_id
    facing_by_pose = {value: key for key, value in FACING_POSES.items()}
    state.facing = facing_by_pose.get(pose_id, "south")
    if pose_id.startswith("walk_") or pose_id.startswith("run_"):
        state.locomotion = "walking"
        phases = {"walk_contact_left": 0.0, "walk_passing_left": 0.25, "walk_contact_right": 0.5, "walk_passing_right": 0.75, "run_reach": 0.12, "run_drive": 0.62}
        state.walk_phase = phases[pose_id]
    if pose_id in {"hover_up", "hover_down", "bank_left", "bank_right", "glide", "takeoff", "touchdown", "jump_airborne", "fall"}:
        state.airborne = pose_id != "touchdown"
        state.mobility_mode = "takeoff" if pose_id == "takeoff" else ("landing" if pose_id == "touchdown" else "hover")
    action_by_pose = {
        "idle_speaking": "speaking", "gesture_explain": "explaining", "gesture_point": "pointing",
        "gesture_think": "thinking", "gesture_react": "reaction", "magic_cast": "magic_cast",
        "gesture_celebrate": "celebrating", "gesture_containment": "containment",
    }
    state.action = action_by_pose.get(pose_id, "idle")
    state.time_seconds = 0.3 if pose_id == "hover_up" else 0.0
    return state


__all__ = [
    "CRYSTAIL_CHARACTER_ID", "CRYSTAIL_POSE_IDS", "CRYSTAIL_ROOT_ANCHOR",
    "CRYSTAIL_SCALE_MULTIPLIER", "FACING_POSES", "PALETTE", "render_crystail_local",
    "resolve_crystail_pose_id", "state_for_pose",
]
