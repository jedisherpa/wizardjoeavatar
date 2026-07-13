from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from .models import DIRECTIONS


DEFINITION_DIR = Path(__file__).with_name("definitions")

VIEW_FILES = {
    "south": "front.json",
    "southwest": "front_left.json",
    "west": "left.json",
    "northwest": "back_left.json",
    "north": "back.json",
    "northeast": "back_right.json",
    "east": "right.json",
    "southeast": "front_right.json",
}


@lru_cache(maxsize=16)
def get_view(direction: str) -> Dict[str, Any]:
    if direction not in VIEW_FILES:
        raise ValueError(f"Unsupported direction: {direction}")
    with open(DEFINITION_DIR / VIEW_FILES[direction], "r", encoding="utf-8") as handle:
        return json.load(handle)


def all_views() -> Dict[str, Dict[str, Any]]:
    return {direction: get_view(direction) for direction in DIRECTIONS}


def resolve_direction_from_velocity(
    vx: float,
    vz: float,
    previous: str = "south",
    hysteresis_degrees: float = 8.0,
) -> str:
    speed = math.hypot(vx, vz)
    if speed < 0.005:
        return previous
    angle = math.degrees(math.atan2(vx, -vz))
    sectors = [
        ("south", 0.0),
        ("southeast", 45.0),
        ("east", 90.0),
        ("northeast", 135.0),
        ("north", 180.0),
        ("northwest", -135.0),
        ("west", -90.0),
        ("southwest", -45.0),
    ]

    def angular_delta(a: float, b: float) -> float:
        return abs((a - b + 180.0) % 360.0 - 180.0)

    current_center = next((center for name, center in sectors if name == previous), None)
    if current_center is not None and angular_delta(angle, current_center) <= 22.5 + hysteresis_degrees:
        return previous
    return min(sectors, key=lambda item: angular_delta(angle, item[1]))[0]


def rotate_direction(direction: str, steps: int) -> str:
    order = ["south", "southwest", "west", "northwest", "north", "northeast", "east", "southeast"]
    idx = order.index(direction)
    return order[(idx + steps) % len(order)]


def step_direction_towards(current: str, target: str) -> str:
    order = ["south", "southwest", "west", "northwest", "north", "northeast", "east", "southeast"]
    if current not in order or target not in order:
        return target
    current_idx = order.index(current)
    target_idx = order.index(target)
    clockwise = (target_idx - current_idx) % len(order)
    counter_clockwise = (current_idx - target_idx) % len(order)
    if clockwise == 0:
        return current
    if clockwise <= counter_clockwise:
        return order[(current_idx + 1) % len(order)]
    return order[(current_idx - 1) % len(order)]
