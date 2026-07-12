from __future__ import annotations

from typing import Tuple

from .geometry import clamp, quantize_scale


WORLD_X_MIN = -5.0
WORLD_X_MAX = 5.0
WORLD_Z_NEAR = 1.5
WORLD_Z_FAR = 10.0


def project_world_to_screen(
    x: float,
    z: float,
    width: int,
    height: int,
) -> Tuple[float, float, float]:
    horizon_y = height * 0.56
    near_y = height * 0.95

    depth = (WORLD_Z_FAR - z) / (WORLD_Z_FAR - WORLD_Z_NEAR)
    depth = clamp(depth, 0.0, 1.0)

    scale = 0.70 + depth * 0.85

    screen_x = width * 0.5 + x * width * 0.075 * scale
    screen_y = horizon_y + depth * (near_y - horizon_y)

    return screen_x, screen_y, scale


def project_quantized(
    x: float,
    z: float,
    width: int,
    height: int,
) -> Tuple[float, float, float]:
    sx, sy, scale = project_world_to_screen(x, z, width, height)
    return sx, sy, quantize_scale(scale)
