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
    "turn_left": ("none", "held"),
    "turn_right": ("none", "held"),
    "crouch": ("none", "held"),
    "jump": ("none", "held"),
    "fall": ("react", "held"),
    "land": ("none", "held"),
    "listening": ("none", "held"),
    "journal_hold": ("none", "rest"),
    "journal_write": ("none", "rest"),
    "journal_page_turn": ("none", "rest"),
    "sword_upright": ("none", "held"),
    "sword_guard_low": ("none", "held"),
    "parchment_read": ("think", "rest"),
    "policy_present": ("explain", "rest"),
    "decision_rights": ("point", "held"),
    "tradeoff_compare": ("explain", "rest"),
    "risk_review": ("point", "rest"),
    "incentive_analysis": ("think", "rest"),
    "guarded_approval": ("none", "held"),
}


def validate_action(action: str) -> None:
    if action not in ACTIONS:
        raise ValueError(f"Unsupported action: {action}")


def channels_for_action(action: str):
    validate_action(action)
    return ACTION_TO_CHANNELS[action]
