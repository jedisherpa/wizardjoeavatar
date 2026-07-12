from __future__ import annotations

import math
from typing import Dict, Tuple

from .anchors import anchors_for_view


def walking_offsets(walk_phase: float, active: bool) -> Dict[str, Tuple[int, int]]:
    if not active:
        return {
            "left_boot": (0, 0),
            "right_boot": (0, 0),
            "left_arm": (0, 0),
            "right_arm": (0, 0),
            "body": (0, 0),
            "hat": (0, 0),
            "beard": (0, 0),
            "staff": (0, 0),
        }
    theta = walk_phase * math.tau
    swing = math.sin(theta)
    opposite = math.sin(theta + math.pi)
    lift_left = -1 if swing > 0.35 else 0
    lift_right = -1 if opposite > 0.35 else 0
    body_bob = -1 if abs(swing) > 0.72 else 0
    return {
        "left_boot": (round(-swing * 2), lift_left),
        "right_boot": (round(opposite * 2), lift_right),
        "left_arm": (round(opposite * 2), 0),
        "right_arm": (round(swing * 2), 0),
        "body": (0, body_bob),
        "hat": (round(-swing * 0.6), body_bob),
        "beard": (round(-swing * 0.45), 0),
        "staff": (round(-swing * 0.55), 0),
    }


def action_wrist_targets(action: str, anchors: Dict[str, Tuple[int, int]]) -> Dict[str, Tuple[int, int]]:
    targets = {
        "left_wrist": anchors["left_wrist"],
        "right_wrist": anchors["right_wrist"],
        "staff_hand": anchors["staff_hand"],
    }
    if action in {"explaining", "speaking"}:
        targets["right_wrist"] = (24, 35)
    elif action == "thinking":
        targets["right_wrist"] = (19, 27)
    elif action == "pointing":
        targets["right_wrist"] = (31, 30)
    elif action == "magic_cast":
        targets["staff_hand"] = (9, 31)
        targets["left_wrist"] = (9, 31)
    elif action == "reaction":
        targets["left_wrist"] = (4, 35)
        targets["right_wrist"] = (30, 35)
    return targets


def skeleton_for(body_width: float, face_shift: int, walk_phase: float, walking: bool, action: str):
    anchors = anchors_for_view(body_width, face_shift)
    offsets = walking_offsets(walk_phase, walking)
    targets = action_wrist_targets(action, anchors)
    return anchors, offsets, targets
