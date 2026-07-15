from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Optional, Sequence, Tuple

from .models import WizardState


@dataclass(frozen=True)
class DirectCellRuntimeProfile:
    character_id: str
    scale_multiplier: float
    default_pose_id: str
    facing_poses: Mapping[str, str]
    action_poses: Mapping[str, str]
    expression_aliases: Mapping[str, str]
    walking_cycle: Tuple[str, ...]
    running_cycle: Tuple[str, ...]
    airborne_poses: Mapping[str, str]
    speech_poses: Tuple[str, ...]
    blink_poses: Mapping[str, str]


@lru_cache(maxsize=None)
def load_direct_cell_runtime_profile(path: Path) -> DirectCellRuntimeProfile:
    profile_path = Path(path).resolve()
    raw = json.loads(profile_path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError("direct-cell runtime profile schema_version must be 1")
    return DirectCellRuntimeProfile(
        character_id=_required_text(raw, "character_id"),
        scale_multiplier=float(raw.get("scale_multiplier", 0.88)),
        default_pose_id=_required_text(raw, "default_pose_id"),
        facing_poses=_text_map(raw.get("facing_poses", {}), "facing_poses"),
        action_poses=_text_map(raw.get("action_poses", {}), "action_poses"),
        expression_aliases=_text_map(raw.get("expression_aliases", {}), "expression_aliases"),
        walking_cycle=_text_tuple(raw.get("walking_cycle", ()), "walking_cycle"),
        running_cycle=_text_tuple(raw.get("running_cycle", ()), "running_cycle"),
        airborne_poses=_text_map(raw.get("airborne_poses", {}), "airborne_poses"),
        speech_poses=_text_tuple(raw.get("speech_poses", ()), "speech_poses"),
        blink_poses=_text_map(raw.get("blink_poses", {}), "blink_poses"),
    )


def validate_direct_cell_runtime_profile(
    profile: DirectCellRuntimeProfile,
    available_pose_ids: Sequence[str],
) -> None:
    available = set(available_pose_ids)
    referenced = {
        profile.default_pose_id,
        *profile.facing_poses.values(),
        *profile.action_poses.values(),
        *profile.walking_cycle,
        *profile.running_cycle,
        *profile.airborne_poses.values(),
        *profile.speech_poses,
        *profile.blink_poses.values(),
    }
    missing = sorted(referenced - available)
    if missing:
        raise ValueError("runtime profile references unknown poses: {}".format(", ".join(missing)))
    if not (0.1 <= profile.scale_multiplier <= 4.0):
        raise ValueError("runtime profile scale_multiplier is outside the safe range")


def resolve_direct_cell_pose_id(
    state: WizardState,
    profile: DirectCellRuntimeProfile,
    available_pose_ids: Sequence[str],
) -> str:
    available = set(available_pose_ids)
    if state.pose_override_id in available:
        return str(state.pose_override_id)

    action_pose = profile.action_poses.get(state.action)
    if action_pose in available:
        return str(action_pose)

    expression = profile.expression_aliases.get(state.expression, state.expression)
    expression_pose = "expression_{}".format(expression)
    if expression != "neutral" and expression_pose in available:
        return expression_pose

    if state.airborne or state.mobility_mode in {"takeoff", "hover", "flight_travel", "landing"}:
        airborne_key = _airborne_key(state)
        airborne_pose = profile.airborne_poses.get(airborne_key)
        if airborne_pose in available:
            return str(airborne_pose)

    cycle = profile.running_cycle if state.action == "dash" else profile.walking_cycle
    if state.locomotion == "walking" and cycle:
        pose = _sample(cycle, (state.walk_phase % 1.0) * len(cycle))
        if pose in available:
            return pose

    facing_pose = profile.facing_poses.get(state.facing)
    if facing_pose in available:
        return str(facing_pose)
    if profile.default_pose_id in available:
        return profile.default_pose_id
    return sorted(available)[0]


def resolve_direct_cell_speech_pose_id(
    state: WizardState,
    profile: DirectCellRuntimeProfile,
    available_pose_ids: Sequence[str],
) -> Optional[str]:
    """Return the authored mouth donor while preserving the base body pose."""
    if state.speech_id is None and state.action != "speaking":
        return None
    pose = _sample(profile.speech_poses, state.time_seconds * 8.0)
    return pose if pose in set(available_pose_ids) else None


def resolve_direct_cell_blink_pose_id(
    state: WizardState,
    profile: DirectCellRuntimeProfile,
    available_pose_ids: Sequence[str],
) -> Optional[str]:
    """Return a blink face donor from the deterministic simulation phase."""
    phase = state.blink_phase % 1.0
    if phase < 0.955 or phase >= 0.998:
        blink_key = "open"
    elif phase < 0.970:
        blink_key = "half_closed"
    elif phase < 0.985:
        blink_key = "closed"
    else:
        blink_key = "half_closed"
    pose = profile.blink_poses.get(blink_key)
    return pose if pose in set(available_pose_ids) else None


def _airborne_key(state: WizardState) -> str:
    if state.mobility_mode == "takeoff":
        return "takeoff"
    if state.mobility_mode == "landing":
        return "landing"
    if state.velocity["x"] < -0.25:
        return "bank_left"
    if state.velocity["x"] > 0.25:
        return "bank_right"
    if state.velocity["z"] < -0.25:
        return "travel_away"
    if state.velocity["z"] > 0.25:
        return "travel_toward"
    return "hover"


def _sample(values: Sequence[str], position: float) -> Optional[str]:
    if not values:
        return None
    return values[int(position) % len(values)]


def _required_text(raw: Mapping[str, object], name: str) -> str:
    value = raw.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError("{} must be non-empty text".format(name))
    return value


def _text_map(value: object, name: str) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("{} must be an object".format(name))
    result = {str(key): str(item) for key, item in value.items()}
    if any(not key or not item for key, item in result.items()):
        raise ValueError("{} must contain non-empty text".format(name))
    return result


def _text_tuple(value: object, name: str) -> Tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("{} must be an array".format(name))
    result = tuple(str(item) for item in value)
    if any(not item for item in result):
        raise ValueError("{} must contain non-empty text".format(name))
    return result


__all__ = [
    "DirectCellRuntimeProfile",
    "load_direct_cell_runtime_profile",
    "resolve_direct_cell_blink_pose_id",
    "resolve_direct_cell_pose_id",
    "resolve_direct_cell_speech_pose_id",
    "validate_direct_cell_runtime_profile",
]
