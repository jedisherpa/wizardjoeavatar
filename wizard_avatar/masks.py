from __future__ import annotations

from typing import Set, Tuple


FACE_MASK: Set[Tuple[int, int]] = {
    (x, y)
    for y in range(15, 25)
    for x in range(10, 25)
}

EYE_MASK: Set[Tuple[int, int]] = {
    (12, 18),
    (13, 18),
    (14, 18),
    (20, 18),
    (21, 18),
    (22, 18),
}

MOUTH_MASK: Set[Tuple[int, int]] = {
    (x, y)
    for y in range(22, 25)
    for x in range(14, 20)
}


def inside_face_mask(x: int, y: int) -> bool:
    return (x, y) in FACE_MASK or (x, y) in MOUTH_MASK
