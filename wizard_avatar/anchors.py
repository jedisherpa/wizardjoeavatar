from __future__ import annotations

from typing import Dict, Tuple


ANCHORS_FRONT: Dict[str, Tuple[int, int]] = {
    "root": (17, 51),
    "pelvis": (17, 39),
    "chest": (17, 30),
    "neck": (17, 26),
    "head": (17, 18),
    "left_shoulder": (8, 30),
    "left_elbow": (6, 35),
    "left_wrist": (7, 40),
    "right_shoulder": (26, 30),
    "right_elbow": (28, 35),
    "right_wrist": (27, 40),
    "left_hip": (13, 41),
    "left_knee": (12, 46),
    "left_ankle": (12, 49),
    "right_hip": (21, 41),
    "right_knee": (22, 46),
    "right_ankle": (22, 49),
    "staff_hand": (7, 37),
    "staff_top": (5, 8),
}


def anchors_for_view(body_width: float = 1.0, face_shift: int = 0) -> Dict[str, Tuple[int, int]]:
    def transform(point: Tuple[int, int]) -> Tuple[int, int]:
        x, y = point
        return (round(17 + (x - 17) * body_width + face_shift * 0.35), y)

    return {name: transform(point) for name, point in ANCHORS_FRONT.items()}
