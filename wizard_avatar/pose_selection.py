from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Set

from .animation_graph import (
    ANIMATION_GRAPH_V2_PATH,
    AnimationGraph,
    AnimationGraphValidationError,
    load_animation_graph,
)
from .character_package import animation_graph_path_for
from .models import WizardState
from .reference_avatar import reference_pose_ids

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


def select_reference_pose_id(
    state: WizardState,
    available_pose_ids: Optional[Iterable[str]] = None,
    animation_graph_path: Optional[Path] = None,
) -> str:
    return select_reference_pose_sample(
        state,
        available_pose_ids,
        animation_graph_path,
    ).pose_id


def select_reference_pose_sample(
    state: WizardState,
    available_pose_ids: Optional[Iterable[str]] = None,
    animation_graph_path: Optional[Path] = None,
) -> PoseSample:
    available = set(available_pose_ids if available_pose_ids is not None else reference_pose_ids())
    if not available:
        raise ValueError("No reference poses are available")
    state.reconcile_compatibility_state()
    if state.pose_override_id is not None:
        pose_id = _first_available(
            state.pose_override_id,
            (_idle_pose_id(state.facing), FRONT_IDLE_POSE),
            available,
        )
        return PoseSample(pose_id=pose_id, contact="showcase", clip_id="pose_showcase")

    try:
        graph_path = (
            Path(animation_graph_path)
            if animation_graph_path is not None
            else animation_graph_path_for(state.character_id) or ANIMATION_GRAPH_V2_PATH
        )
        graph = load_animation_graph(graph_path)
        sample = _select_graph_v2_sample(state, graph)
    except (AnimationGraphValidationError, FileNotFoundError, KeyError, OSError, TypeError, ValueError):
        requested = _select_requested_pose_id(state)
        pose_id = _first_available(requested, _fallbacks_for(requested, state), available)
        return PoseSample(pose_id=pose_id, phase=state.walk_phase % 1.0)

    pose_id = _first_available(sample.pose_id, _fallbacks_for(sample.pose_id, state), available)
    if pose_id == sample.pose_id:
        return sample
    return PoseSample(pose_id=pose_id, contact=sample.contact, clip_id=sample.clip_id, phase=sample.phase)


def _select_graph_v2_sample(state: WizardState, graph: AnimationGraph) -> PoseSample:
    node_id = _select_node_id(state, graph)
    node = graph.nodes[node_id]
    if state.animation_node_id != node_id or state.animation_clip_id != node.clip_id:
        transition = graph.select_transition(state.animation_node_id, node_id)
        state.animation_transition_id = (
            transition.transition_id if transition is not None else None
        )
        state.animation_node_id = node_id
        state.animation_clip_id = node.clip_id
        state.animation_clip_tick = 0
    clip = graph.clips[node.clip_id]
    if node_id in {"ground_walk", "back_walk"} and clip.phase_source == "ground_distance":
        evaluation = graph.evaluate_clip_phase(node.clip_id, state.walk_phase)
    else:
        evaluation = graph.evaluate_clip(node.clip_id, state.animation_clip_tick)
    return PoseSample(
        pose_id=evaluation.pose_id,
        contact=evaluation.support_contact,
        clip_id=node.clip_id,
        phase=evaluation.clip_phase,
    )


def _select_node_id(state: WizardState, graph: AnimationGraph) -> str:
    airborne = state.airborne or state.mobility_mode in {
        "takeoff",
        "hover",
        "flight_travel",
        "flight_bank",
        "landing",
    }
    action = _effective_action(state)
    mobility = _graph_mobility(state, airborne)
    if action == "dash" and not airborne:
        return _action_node_id(graph, action, "grounded_run") or graph.default_node_id
    action_node = _action_node_id(graph, action, mobility)
    if action_node is not None:
        return action_node
    if airborne:
        return _flight_node_id(state, graph)
    if state.locomotion == "walking":
        if state.facing in {"north", "northeast", "northwest"}:
            return _node_for_clip(graph, "walk_back", graph.default_node_id)
        if state.facing in {"south", "southeast", "southwest"}:
            return _node_for_clip(graph, "walk_front", graph.default_node_id)
    fallback_clip = str(
        graph.fallbacks["by_facing"].get(
            state.facing,
            graph.fallbacks["grounded_clip_id"],
        )
    )
    return _node_for_clip(graph, fallback_clip, graph.default_node_id)


def _effective_action(state: WizardState) -> Optional[str]:
    if state.action == "speaking":
        return "speaking" if state.speech_id is None else None
    if state.action not in {"idle", "walking", "speaking", "thinking"}:
        return state.action
    if _is_casting(state):
        return "magic_cast"
    if _is_explaining_without_speech(state):
        return "explaining"
    return None


def _graph_mobility(state: WizardState, airborne: bool) -> str:
    if airborne:
        if state.mobility_mode in {"takeoff", "landing", "hover", "flight_travel", "flight_bank"}:
            return state.mobility_mode
        return "hover"
    return "grounded_walk" if state.locomotion == "walking" else "grounded_idle"


def _action_node_id(
    graph: AnimationGraph,
    action: Optional[str],
    mobility: str,
) -> Optional[str]:
    if action is None:
        return None
    matches = [
        node.node_id
        for node in graph.nodes.values()
        if action in node.actions and mobility in node.mobility_modes
    ]
    return matches[0] if matches else None


def _flight_node_id(state: WizardState, graph: AnimationGraph) -> str:
    if state.mobility_mode == "takeoff":
        preferred = "takeoff"
    elif state.mobility_mode == "landing":
        preferred = "landing"
    else:
        speed = (state.velocity["x"] ** 2 + state.velocity["z"] ** 2) ** 0.5
        if speed <= 0.08:
            preferred = "hover"
        elif state.velocity["x"] < -0.25:
            preferred = "flight_bank_left"
        elif state.velocity["x"] > 0.25:
            preferred = "flight_bank_right"
        else:
            preferred = "glide"
    if preferred in graph.nodes:
        return preferred
    return _node_for_clip(graph, str(graph.fallbacks["airborne_clip_id"]), graph.default_node_id)


def _node_for_clip(graph: AnimationGraph, clip_id: str, fallback_node_id: str) -> str:
    for node in graph.nodes.values():
        if node.clip_id == clip_id:
            return node.node_id
    return fallback_node_id


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
