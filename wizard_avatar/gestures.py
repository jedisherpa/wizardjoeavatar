from __future__ import annotations

from .models import ACTIONS


ACTION_TO_CHANNELS = {
    "idle": ("none", "held"),
    "speaking": ("explain", "held"),
    "explaining": ("explain", "held"),
    "walking": ("none", "held"),
    "dash": ("none", "held"),
    "thinking": ("think", "held"),
    "pointing": ("point", "point"),
    "magic_cast": ("cast", "cast"),
    "reaction": ("react", "held"),
    "celebrating": ("react", "held"),
    "containment": ("think", "rest"),
}


def validate_action(action: str) -> None:
    if action not in ACTIONS:
        raise ValueError(f"Unsupported action: {action}")


def channels_for_action(action: str):
    validate_action(action)
    return ACTION_TO_CHANNELS[action]
