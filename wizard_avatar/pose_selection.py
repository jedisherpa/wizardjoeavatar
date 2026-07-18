from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Optional, Set

from .animation_graph import (
    ANIMATION_GRAPH_V2_PATH,
    AnimationGraph,
    AnimationGraphValidationError,
    ClipDefinition,
    ClipEvaluation,
    TransitionDefinition,
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
GROUND_STOP_LEFT_NODE = "ground_stop_left"
GROUND_STOP_RIGHT_NODE = "ground_stop_right"
GROUND_STOP_NODES = frozenset({GROUND_STOP_LEFT_NODE, GROUND_STOP_RIGHT_NODE})


@dataclass(frozen=True)
class PoseSample:
    pose_id: str
    contact: str = "unknown"
    clip_id: str = ""
    phase: float = 0.0
    planted_anchor: Optional[str] = None
    active_markers: tuple[str, ...] = ()
    sample_index: int = 0
    sample_frame: int = 0
    authored_frame: int = 0
    phase_numerator: int = 0
    phase_denominator: int = 1
    root_policy: str = "fixed"


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
    return PoseSample(
        pose_id=pose_id,
        contact=sample.contact,
        clip_id=sample.clip_id,
        phase=sample.phase,
        planted_anchor=sample.planted_anchor,
        active_markers=sample.active_markers,
        sample_index=sample.sample_index,
        sample_frame=sample.sample_frame,
        authored_frame=sample.authored_frame,
        phase_numerator=sample.phase_numerator,
        phase_denominator=sample.phase_denominator,
        root_policy=sample.root_policy,
    )


def presentation_pose_for_facing(
    pose_id: str,
    animation_clip_id: str,
    presented_facing: str,
    available_pose_ids: Optional[Iterable[str]] = None,
) -> str:
    """Choose an authored idle view without advancing animation state."""

    candidate = pose_id
    if animation_clip_id in {"idle_front", "idle_back", "idle_left", "idle_right"}:
        if presented_facing in {"north", "northwest", "northeast"}:
            candidate = BACK_IDLE_POSE
        elif presented_facing == "west":
            candidate = PROFILE_LEFT_POSE
        elif presented_facing == "east":
            candidate = PROFILE_RIGHT_POSE
        else:
            candidate = FRONT_IDLE_POSE
    if available_pose_ids is not None and candidate not in set(available_pose_ids):
        return pose_id
    return candidate


def _select_graph_v2_sample(state: WizardState, graph: AnimationGraph) -> PoseSample:
    desired_node_id = _select_node_id(state, graph)
    desired_node = graph.nodes[desired_node_id]
    if state.animation_node_id not in graph.nodes or state.animation_clip_id not in graph.clips:
        return _commit_target(state, graph, desired_node_id, desired_node.clip_id, 0)

    if state.animation_transition_phase != "stable":
        return _advance_pending_transition(state, graph, desired_node_id)

    if (
        state.animation_node_id != desired_node_id
        or state.animation_clip_id != desired_node.clip_id
    ):
        return _request_transition(state, graph, desired_node_id)

    return _sample_active_clip(state, graph)


def _request_transition(
    state: WizardState,
    graph: AnimationGraph,
    target_node_id: str,
) -> PoseSample:
    target = graph.nodes[target_node_id]
    source_evaluation = _presented_clip_evaluation(state, graph)
    transition = graph.select_transition(state.animation_node_id, target_node_id)
    if transition is None or source_evaluation is None:
        return _commit_target(state, graph, target_node_id, target.clip_id, 0)

    _set_pending_transition(state, transition, target.clip_id)
    if _transition_gate_is_open(state, graph, transition, source_evaluation):
        return _begin_transition_handoff(
            state,
            graph,
            transition,
            source_evaluation,
        )
    return _pose_sample(source_evaluation, state.animation_clip_id, graph)


def _advance_pending_transition(
    state: WizardState,
    graph: AnimationGraph,
    desired_node_id: str,
) -> PoseSample:
    target_node_id = state.animation_transition_target_node_id
    if desired_node_id == state.animation_node_id:
        _clear_transition(state)
        return _sample_active_clip(state, graph)
    if target_node_id != desired_node_id:
        _clear_transition(state)
        return _request_transition(state, graph, desired_node_id)

    transition = graph.select_transition(state.animation_node_id, target_node_id)
    if state.animation_transition_phase == "wait_gate":
        _advance_stopped_contact_settle(state, graph)
    source_evaluation = _presented_clip_evaluation(state, graph)
    if transition is None or source_evaluation is None:
        target = graph.nodes[desired_node_id]
        return _commit_target(state, graph, desired_node_id, target.clip_id, 0)

    if state.animation_transition_phase == "wait_gate":
        if _transition_gate_is_open(state, graph, transition, source_evaluation):
            return _begin_transition_handoff(
                state,
                graph,
                transition,
                source_evaluation,
            )
        return _pose_sample(source_evaluation, state.animation_clip_id, graph)

    if state.animation_transition_phase == "handoff":
        if state.simulation_tick >= state.animation_transition_commit_tick:
            return _commit_target(
                state,
                graph,
                target_node_id,
                state.animation_transition_target_clip_id or graph.nodes[target_node_id].clip_id,
                state.animation_transition_entry_tick,
            )
        duration = max(
            1,
            state.animation_transition_commit_tick
            - state.animation_transition_started_tick,
        )
        state.pose_transition_progress = min(
            1.0,
            max(
                0.0,
                (state.simulation_tick - state.animation_transition_started_tick)
                / duration,
            ),
        )
        return PoseSample(
            pose_id=state.animation_transition_source_pose_id or source_evaluation.pose_id,
            contact=state.animation_transition_source_contact,
            clip_id=state.animation_clip_id,
            phase=source_evaluation.clip_phase,
            planted_anchor=source_evaluation.planted_anchor,
            active_markers=source_evaluation.active_markers,
            sample_index=source_evaluation.sample_index,
            sample_frame=source_evaluation.sample_frame,
            authored_frame=source_evaluation.authored_frame,
            phase_numerator=source_evaluation.clip_phase_numerator,
            phase_denominator=source_evaluation.clip_phase_denominator,
            root_policy=graph.clips[state.animation_clip_id].root_policy,
        )

    _clear_transition(state)
    return _sample_active_clip(state, graph)


def _advance_stopped_contact_settle(
    state: WizardState,
    graph: AnimationGraph,
) -> None:
    clip = graph.clips[state.animation_clip_id]
    if state.locomotion != "idle" or clip.phase_source != "ground_distance":
        return
    authored_frame_step = graph.authored_fps / graph.simulation_hz
    state.animation_phase_offset = (
        state.animation_phase_offset + authored_frame_step / clip.total_frames
    ) % 1.0


def _set_pending_transition(
    state: WizardState,
    transition: TransitionDefinition,
    target_clip_id: str,
) -> None:
    state.animation_transition_id = transition.transition_id
    state.animation_transition_phase = "wait_gate"
    state.animation_transition_target_node_id = transition.target_node_id
    state.animation_transition_target_clip_id = target_clip_id
    state.animation_transition_entry_tick = 0
    state.animation_transition_started_tick = state.simulation_tick
    state.animation_transition_commit_tick = 0
    state.animation_transition_source_pose_id = None
    state.animation_transition_source_contact = "unknown"
    state.pose_transition_progress = 0.0


def _begin_transition_handoff(
    state: WizardState,
    graph: AnimationGraph,
    transition: TransitionDefinition,
    source_evaluation: ClipEvaluation,
) -> PoseSample:
    target_clip_id = state.animation_transition_target_clip_id
    target_node_id = state.animation_transition_target_node_id
    if target_clip_id is None or target_node_id is None:
        raise ValueError("pending transition is missing its target")
    entry_tick = _transition_entry_tick(
        graph,
        target_clip_id,
        transition,
        source_evaluation,
    )
    duration_ticks = _transition_duration_ticks(graph, transition)
    state.animation_transition_entry_tick = entry_tick
    state.animation_transition_source_pose_id = source_evaluation.pose_id
    state.animation_transition_source_contact = source_evaluation.support_contact
    state.animation_transition_started_tick = state.simulation_tick
    if duration_ticks <= 0:
        return _commit_target(
            state,
            graph,
            target_node_id,
            target_clip_id,
            entry_tick,
        )
    state.animation_transition_phase = "handoff"
    state.animation_transition_commit_tick = state.simulation_tick + duration_ticks
    state.pose_transition_progress = 0.0
    return _pose_sample(source_evaluation, state.animation_clip_id, graph)


def _transition_duration_ticks(
    graph: AnimationGraph,
    transition: TransitionDefinition,
) -> int:
    recipe = graph.transition_recipes[transition.transition_recipe_id]
    recipe_ticks = _authored_frame_to_tick(
        recipe.duration_frames,
        graph.authored_fps,
        graph.simulation_hz,
    )
    return max(transition.duration_ticks, recipe_ticks)


def _transition_gate_is_open(
    state: WizardState,
    graph: AnimationGraph,
    transition: TransitionDefinition,
    evaluation: ClipEvaluation,
) -> bool:
    clip = graph.clips[state.animation_clip_id]
    if state.animation_clip_tick < clip.minimum_hold_ticks:
        return False
    markers = set(evaluation.active_markers)
    reached = lambda marker: _clip_marker_reached(
        graph,
        clip,
        state.animation_clip_tick,
        marker,
    )

    if clip.interrupt_policy == "uninterruptible":
        if clip.loop_mode == "loop" or evaluation.authored_frame < clip.total_frames - 1:
            return False
    elif clip.interrupt_policy == "after_commit":
        if not any(
            reached(marker)
            for marker in ("action_commit", "action_effect", "action_recoverable", "takeoff_commit")
        ):
            return False
    elif clip.interrupt_policy == "at_marker" and transition.timing_mode == "marker":
        if not markers and not any(reached(marker) for marker in clip.exit_markers):
            return False

    window = transition.interrupt_window
    if window == "contact_marker":
        if not _at_contact_boundary(evaluation):
            return False
    elif window == "action_recoverable":
        if "action_recoverable" not in markers and not reached("action_recoverable"):
            return False
    elif window == "before_takeoff_commit":
        if reached("takeoff_commit"):
            return False
    elif window == "airborne":
        if "airborne" not in markers and not reached("airborne"):
            return False
    elif window == "landing_settled":
        if "landing_settled" not in markers and not reached("landing_settled"):
            return False

    if transition.timing_mode == "marker":
        marker_names = set(clip.exit_markers)
        if window not in {"immediate", "action_recoverable", "airborne", "landing_settled"}:
            marker_names.add(window)
        return bool(markers.intersection(marker_names)) or any(
            reached(marker) for marker in marker_names
        )
    if transition.timing_mode == "contact":
        return evaluation.support_contact != "none" and (
            window == "immediate" or _at_contact_boundary(evaluation)
        )
    return True


def _at_contact_boundary(evaluation: ClipEvaluation) -> bool:
    return evaluation.support_contact != "none" and any(
        marker.endswith("contact") for marker in evaluation.active_markers
    )


def _clip_marker_reached(
    graph: AnimationGraph,
    clip: ClipDefinition,
    elapsed_ticks: int,
    marker_id: str,
) -> bool:
    if clip.loop_mode == "loop":
        return False
    authored_frame = (elapsed_ticks * graph.authored_fps) // graph.simulation_hz
    sample_start = 0
    for sample in clip.samples:
        for marker in sample.markers:
            if marker.marker_id == marker_id and authored_frame >= sample_start + marker.frame_offset:
                return True
        sample_start += sample.duration_frames
    return False


def _commit_target(
    state: WizardState,
    graph: AnimationGraph,
    node_id: str,
    clip_id: str,
    entry_tick: int,
) -> PoseSample:
    state.animation_node_id = node_id
    state.animation_clip_id = clip_id
    state.animation_clip_tick = max(0, entry_tick)
    target_clip = graph.clips[clip_id]
    if target_clip.phase_source == "ground_distance":
        target_phase = graph.evaluate_clip(clip_id, state.animation_clip_tick).clip_phase
        state.animation_phase_offset = (target_phase - state.walk_phase) % 1.0
    else:
        state.animation_phase_offset = 0.0
    state.animation_transition_generation += 1
    _clear_transition(state)
    return _sample_active_clip(state, graph)


def _clear_transition(state: WizardState) -> None:
    state.animation_transition_id = None
    state.animation_transition_phase = "stable"
    state.animation_transition_target_node_id = None
    state.animation_transition_target_clip_id = None
    state.animation_transition_entry_tick = 0
    state.animation_transition_started_tick = state.simulation_tick
    state.animation_transition_commit_tick = state.simulation_tick
    state.animation_transition_source_pose_id = None
    state.animation_transition_source_contact = "unknown"
    state.pose_transition_progress = 1.0


def _sample_active_clip(state: WizardState, graph: AnimationGraph) -> PoseSample:
    evaluation = _evaluate_presented_clip(
        graph,
        state.animation_node_id,
        state.animation_clip_id,
        state.animation_clip_tick,
        state.walk_phase,
        state.animation_phase_offset,
    )
    return _pose_sample(evaluation, state.animation_clip_id, graph)


def _pose_sample(
    evaluation: ClipEvaluation,
    clip_id: str,
    graph: AnimationGraph,
) -> PoseSample:
    return PoseSample(
        pose_id=evaluation.pose_id,
        contact=evaluation.support_contact,
        clip_id=clip_id,
        phase=evaluation.clip_phase,
        planted_anchor=evaluation.planted_anchor,
        active_markers=evaluation.active_markers,
        sample_index=evaluation.sample_index,
        sample_frame=evaluation.sample_frame,
        authored_frame=evaluation.authored_frame,
        phase_numerator=evaluation.clip_phase_numerator,
        phase_denominator=evaluation.clip_phase_denominator,
        root_policy=graph.clips[clip_id].root_policy,
    )


def _presented_clip_evaluation(
    state: WizardState,
    graph: AnimationGraph,
) -> Optional[ClipEvaluation]:
    if state.animation_clip_id not in graph.clips:
        return None
    return _evaluate_presented_clip(
        graph,
        state.animation_node_id,
        state.animation_clip_id,
        state.animation_clip_tick,
        state.walk_phase,
        state.animation_phase_offset,
    )


def _evaluate_presented_clip(
    graph: AnimationGraph,
    node_id: str,
    clip_id: str,
    clip_tick: int,
    walk_phase: float,
    phase_offset: float = 0.0,
) -> ClipEvaluation:
    clip = graph.clips[clip_id]
    if node_id in {"ground_walk", "back_walk"} and clip.phase_source == "ground_distance":
        return graph.evaluate_clip_phase(clip_id, walk_phase + phase_offset)
    return graph.evaluate_clip(clip_id, clip_tick)


def _transition_entry_tick(
    graph: AnimationGraph,
    target_clip_id: str,
    transition: Optional[TransitionDefinition],
    source_evaluation: Optional[ClipEvaluation],
) -> int:
    if transition is None or source_evaluation is None:
        return 0
    source_phase = Fraction(
        source_evaluation.clip_phase_numerator,
        source_evaluation.clip_phase_denominator,
    )
    if transition.phase_policy == "preserve":
        target_frame = int(source_phase * graph.clips[target_clip_id].total_frames)
    elif transition.phase_policy == "nearest_contact":
        source_contact = (
            source_evaluation.support_contact
            if transition.contact_policy == "match"
            else None
        )
        target_frame = _nearest_contact_entry_frame(
            graph.clips[target_clip_id],
            source_contact,
            source_phase,
        )
    else:
        return 0
    return _authored_frame_to_tick(target_frame, graph.authored_fps, graph.simulation_hz)


def _nearest_contact_entry_frame(
    clip: ClipDefinition,
    source_contact: Optional[str],
    source_phase: Fraction,
) -> int:
    sample_frames = []
    frame = 0
    for sample in clip.samples:
        sample_frames.append((frame, sample.support_contact))
        frame += sample.duration_frames
    matching_frames = tuple(
        frame
        for frame, contact in sample_frames
        if contact == source_contact
    )
    candidates = matching_frames or tuple(frame for frame, _ in sample_frames)
    normalized_source_phase = source_phase % 1
    return min(
        candidates,
        key=lambda frame: (
            _circular_phase_distance(
                normalized_source_phase,
                Fraction(frame, clip.total_frames),
            ),
            frame,
        ),
    )


def _circular_phase_distance(first: Fraction, second: Fraction) -> Fraction:
    distance = abs(first - second) % 1
    return min(distance, 1 - distance)


def _authored_frame_to_tick(frame: int, authored_fps: int, simulation_hz: int) -> int:
    return (frame * simulation_hz + authored_fps - 1) // authored_fps


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
    if not airborne and state.animation_node_id == "ground_run" and action != "dash":
        if "run_recovery" in graph.nodes:
            return "run_recovery"
    if not airborne and state.animation_node_id == "run_recovery" and action != "dash":
        return graph.default_node_id
    if action == "dash" and not airborne:
        return _action_node_id(graph, action, "grounded_run") or graph.default_node_id
    action_node = _action_node_id(graph, action, mobility)
    if action_node is not None:
        return action_node
    if airborne:
        return _flight_node_id(state, graph)
    if state.animation_node_id in GROUND_STOP_NODES and state.locomotion == "idle":
        stop_clip = graph.clips.get(state.animation_clip_id)
        if stop_clip is not None and not _clip_marker_reached(
            graph,
            stop_clip,
            state.animation_clip_tick,
            "action_recoverable",
        ):
            return state.animation_node_id
    if state.locomotion == "walking":
        travel_facing = _travel_facing_family(state)
        if travel_facing == "back":
            return _node_for_clip(graph, "walk_back", graph.default_node_id)
        return _node_for_clip(graph, "walk_front", graph.default_node_id)
    if state.animation_node_id == "ground_walk":
        if state.facing == "west" and GROUND_STOP_LEFT_NODE in graph.nodes:
            return GROUND_STOP_LEFT_NODE
        if state.facing == "east" and GROUND_STOP_RIGHT_NODE in graph.nodes:
            return GROUND_STOP_RIGHT_NODE
    fallback_clip = str(
        graph.fallbacks["by_facing"].get(
            state.facing,
            graph.fallbacks["grounded_clip_id"],
        )
    )
    return _node_for_clip(graph, fallback_clip, graph.default_node_id)


def _travel_facing_family(state: WizardState) -> str:
    """Resolve the locomotion clip from travel, not a stepped presentation turn."""

    velocity_x = float(state.velocity.get("x", 0.0))
    velocity_z = float(state.velocity.get("z", 0.0))
    if abs(velocity_x) >= abs(velocity_z) and abs(velocity_x) > 1e-9:
        return "front"
    if abs(velocity_z) > 1e-9:
        return "back" if velocity_z > 0.0 else "front"
    return "back" if state.facing in {"north", "northeast", "northwest"} else "front"


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
    return _front_walk_pose_id(state.walk_phase)


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
