from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional, Set

from .models import WizardState
from .reference_avatar import reference_pose_ids
from .animation_graph import load_reference_animation_graph_v2


ANIMATION_GRAPH_PATH = Path(__file__).with_name("definitions") / "reference_avatar_animation_graph.json"

FRONT_IDLE_POSE = "front_idle"
BACK_IDLE_POSE = "back_idle"
PROFILE_LEFT_POSE = "profile_left"
PROFILE_RIGHT_POSE = "profile_right"
WALK_FRONT_LEFT_POSE = "walk_front_left"
WALK_FRONT_RIGHT_POSE = "walk_front_right"
BACK_LEFT_POSE = "back_left"
BACK_RIGHT_POSE = "back_right"
EXPLAINING_POSE = "explaining"
MAGIC_CAST_POSE = "magic_cast"
DASH_POSE = "run_front_airborne_reach"


@dataclass(frozen=True)
class PoseSample:
    pose_id: str
    contact: str = "unknown"
    clip_id: str = ""
    phase: float = 0.0


@lru_cache(maxsize=1)
def load_reference_animation_graph() -> dict[str, Any]:
    with open(ANIMATION_GRAPH_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def select_reference_pose_id(
    state: WizardState,
    available_pose_ids: Optional[Iterable[str]] = None,
) -> str:
    return select_reference_pose_sample(state, available_pose_ids).pose_id


def select_reference_pose_sample(
    state: WizardState,
    available_pose_ids: Optional[Iterable[str]] = None,
) -> PoseSample:
    available = set(available_pose_ids if available_pose_ids is not None else reference_pose_ids())
    if not available:
        raise ValueError("No reference poses are available")
    if state.pose_override_id is not None:
        pose_id = _first_available(
            state.pose_override_id,
            (_idle_pose_id(state.facing), FRONT_IDLE_POSE),
            available,
        )
        return PoseSample(pose_id=pose_id, contact="showcase", clip_id="pose_showcase")

    if state.airborne or state.mobility_mode in {"takeoff", "hover", "flight_travel", "landing"}:
        sample = _select_flight_sample(state)
        pose_id = _first_available(sample.pose_id, ("fly_front_hover_neutral", FRONT_IDLE_POSE), available)
        return PoseSample(
            pose_id=pose_id,
            contact=sample.contact,
            clip_id=sample.clip_id,
            phase=sample.phase,
        )

    try:
        graph = load_reference_animation_graph()
        sample = _select_graph_sample(state, graph)
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        requested = _select_requested_pose_id(state)
        pose_id = _first_available(requested, _fallbacks_for(requested, state), available)
        return PoseSample(pose_id=pose_id, phase=state.walk_phase % 1.0)

    pose_id = _first_available(sample.pose_id, _fallbacks_for(sample.pose_id, state), available)
    if pose_id == sample.pose_id:
        return sample
    return PoseSample(pose_id=pose_id, contact=sample.contact, clip_id=sample.clip_id, phase=sample.phase)


def _select_graph_sample(state: WizardState, graph: dict[str, Any]) -> PoseSample:
    if _is_casting(state):
        return PoseSample(
            pose_id=_graph_action_pose(graph, MAGIC_CAST_POSE),
            contact="both",
            phase=state.walk_phase % 1.0,
        )
    if state.locomotion == "walking":
        return _graph_walking_sample(graph, state.facing, state.walk_phase)
    action_key = _graph_action_key(state, graph)
    if action_key is not None:
        return PoseSample(
            pose_id=_graph_action_pose(graph, action_key),
            contact="both",
            phase=state.walk_phase % 1.0,
        )
    return PoseSample(
        pose_id=str(graph.get("idle_by_facing", {}).get(state.facing, graph["default_pose_id"])),
        contact="both",
        phase=state.walk_phase % 1.0,
    )


def _select_flight_sample(state: WizardState) -> PoseSample:
    graph = load_reference_animation_graph_v2()
    if state.action == "magic_cast":
        node_id = "air_staff"
    elif state.action == "reaction":
        node_id = "air_reaction_node"
    elif state.mobility_mode == "takeoff":
        node_id = "takeoff"
    elif state.mobility_mode == "landing":
        node_id = "landing"
    else:
        speed = (state.velocity["x"] ** 2 + state.velocity["z"] ** 2) ** 0.5
        if speed <= 0.08:
            node_id = "hover"
        elif state.velocity["x"] < -0.25:
            node_id = "flight_bank_left"
        elif state.velocity["x"] > 0.25:
            node_id = "flight_bank_right"
        else:
            node_id = "glide"
    node = graph.nodes[node_id]
    if state.animation_clip_id != node.clip_id:
        state.animation_clip_id = node.clip_id
        state.animation_clip_tick = 0
    state.animation_node_id = node_id
    evaluation = graph.evaluate_clip(node.clip_id, state.animation_clip_tick)
    state.mobility_mode = state.mobility_mode or node.mobility_modes[0]
    return PoseSample(
        pose_id=evaluation.pose_id,
        contact=evaluation.support_contact,
        clip_id=node.clip_id,
        phase=evaluation.clip_phase,
    )


def _graph_action_key(state: WizardState, graph: dict[str, Any]) -> Optional[str]:
    if state.action != "speaking" and state.action in graph.get("action_pose_overrides", {}):
        return state.action
    if state.action in {"pointing", "reaction"}:
        return state.action
    if _is_explaining_without_speech(state):
        return EXPLAINING_POSE
    return None


def _graph_action_pose(graph: dict[str, Any], action_key: str) -> str:
    return str(graph.get("action_pose_overrides", {}).get(action_key, graph["default_pose_id"]))


def _graph_walking_sample(graph: dict[str, Any], facing: str, walk_phase: float) -> PoseSample:
    clips = graph.get("walking_clips", {})
    clip = clips.get(facing) or clips.get("south")
    if not clip:
        return PoseSample(
            pose_id=str(graph.get("idle_by_facing", {}).get(facing, graph["default_pose_id"])),
            contact="both",
            phase=walk_phase % 1.0,
        )
    samples = list(clip.get("samples", []))
    if not samples:
        return PoseSample(pose_id=str(graph["default_pose_id"]), contact="both", phase=walk_phase % 1.0)
    normalized = walk_phase % 1.0
    selected = samples[0]
    for sample in samples:
        if float(sample.get("phase", 0.0)) <= normalized + 1e-9:
            selected = sample
    return PoseSample(
        pose_id=str(selected["pose_id"]),
        contact=str(selected.get("contact", "unknown")),
        clip_id=str(clip.get("clip_id", "")),
        phase=float(selected.get("phase", 0.0)),
    )


def _select_requested_pose_id(state: WizardState) -> str:
    if _is_casting(state):
        return MAGIC_CAST_POSE
    if _is_explaining_without_speech(state):
        return EXPLAINING_POSE
    if state.locomotion == "walking":
        return _walking_pose_id(state)
    return _idle_pose_id(state.facing)


def _is_casting(state: WizardState) -> bool:
    return (
        state.staff_state == "cast"
        or state.upper_body_action == "cast"
        or state.action == "magic_cast"
    )


def _is_explaining_without_speech(state: WizardState) -> bool:
    if state.action == "speaking" or state.speech_id is not None:
        return False
    return state.upper_body_action == "explain" or state.action == "explaining"


def _walking_pose_id(state: WizardState) -> str:
    facing = state.facing
    if facing in {"south", "southwest", "southeast"}:
        return _front_walk_pose_id(state.walk_phase)
    if facing in {"north", "northwest", "northeast"}:
        return _back_walk_pose_id(state.walk_phase, facing)
    return _idle_pose_id(facing)


def _front_walk_pose_id(walk_phase: float) -> str:
    phase = walk_phase % 1.0
    return WALK_FRONT_LEFT_POSE if phase < 0.5 else WALK_FRONT_RIGHT_POSE


def _back_walk_pose_id(walk_phase: float, facing: str) -> str:
    phase = walk_phase % 1.0
    if facing == "northwest":
        return BACK_LEFT_POSE
    if facing == "northeast":
        return BACK_RIGHT_POSE
    if phase < 1.0 / 3.0:
        return BACK_LEFT_POSE
    if phase < 2.0 / 3.0:
        return BACK_IDLE_POSE
    return BACK_RIGHT_POSE


def _idle_pose_id(facing: str) -> str:
    if facing == "north":
        return BACK_IDLE_POSE
    if facing == "west":
        return PROFILE_LEFT_POSE
    if facing == "east":
        return PROFILE_RIGHT_POSE
    if facing == "northwest":
        return BACK_LEFT_POSE
    if facing == "northeast":
        return BACK_RIGHT_POSE
    return FRONT_IDLE_POSE


def _fallbacks_for(requested: str, state: WizardState) -> tuple[str, ...]:
    facing_fallback = _idle_pose_id(state.facing)
    if requested == MAGIC_CAST_POSE:
        return (EXPLAINING_POSE, facing_fallback, FRONT_IDLE_POSE)
    if requested == EXPLAINING_POSE:
        return (facing_fallback, FRONT_IDLE_POSE)
    if requested in {WALK_FRONT_LEFT_POSE, WALK_FRONT_RIGHT_POSE}:
        other_walk = (
            WALK_FRONT_RIGHT_POSE
            if requested == WALK_FRONT_LEFT_POSE
            else WALK_FRONT_LEFT_POSE
        )
        return (other_walk, FRONT_IDLE_POSE)
    if requested in {BACK_LEFT_POSE, BACK_RIGHT_POSE, BACK_IDLE_POSE}:
        return (BACK_IDLE_POSE, BACK_LEFT_POSE, BACK_RIGHT_POSE, FRONT_IDLE_POSE)
    if requested in {PROFILE_LEFT_POSE, PROFILE_RIGHT_POSE}:
        return (FRONT_IDLE_POSE,)
    return (FRONT_IDLE_POSE,)


def _first_available(requested: str, fallbacks: tuple[str, ...], available: Set[str]) -> str:
    for pose_id in (requested, *fallbacks):
        if pose_id in available:
            return pose_id
    return sorted(available)[0]
