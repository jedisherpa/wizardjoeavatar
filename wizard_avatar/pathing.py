from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

from .geometry import distance
from .projection import WORLD_X_MAX, WORLD_X_MIN, WORLD_Z_FAR, WORLD_Z_NEAR


Point = Tuple[float, float]


def validate_world_point(x: float, z: float) -> None:
    if not (WORLD_X_MIN <= x <= WORLD_X_MAX and WORLD_Z_NEAR <= z <= WORLD_Z_FAR):
        raise ValueError(f"Point out of world bounds: ({x}, {z})")


def validate_path(points: Sequence[Point], max_points: int = 128) -> List[Point]:
    if not points:
        raise ValueError("Path must contain at least one point")
    if len(points) > max_points:
        raise ValueError(f"Path has too many points: {len(points)} > {max_points}")
    out: List[Point] = []
    for x, z in points:
        validate_world_point(float(x), float(z))
        out.append((float(x), float(z)))
    return out


def circle_points(
    center_x: float,
    center_z: float,
    radius: float,
    clockwise: bool,
    steps: int = 48,
) -> List[Point]:
    if radius <= 0:
        raise ValueError("Circle radius must be positive")
    points = []
    sign = -1.0 if clockwise else 1.0
    for i in range(steps + 1):
        theta = sign * math.tau * (i / steps)
        x = center_x + radius * math.cos(theta)
        z = center_z + radius * math.sin(theta)
        validate_world_point(x, z)
        points.append((x, z))
    return points


def figure_eight_points(center_x: float = 0.0, center_z: float = 5.0, radius: float = 1.4, steps: int = 96) -> List[Point]:
    points = []
    for i in range(steps + 1):
        t = math.tau * (i / steps)
        x = center_x + radius * math.sin(t)
        z = center_z + radius * math.sin(t) * math.cos(t)
        validate_world_point(x, z)
        points.append((x, z))
    return points


def path_length(points: Sequence[Point]) -> float:
    return sum(distance(a, b) for a, b in zip(points, points[1:]))
