from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .models import DIRECTIONS


EYE_AIM_LEFT = -1
EYE_AIM_CENTER = 0
EYE_AIM_RIGHT = 1
SECTOR_STEP_TICKS = 3
SETTLE_TICKS = 6
_LEAD_TICKS_BY_DISTANCE = (0, 3, 4, 6, 8)


@dataclass(frozen=True)
class HeadEyeState:
    """Replayable presentation state expressed only in simulation ticks."""

    origin_facing: str
    presented_facing: str
    target_facing: str
    turn_direction: int = 0
    sector_distance: int = 0
    requested_tick: int = 0
    head_start_tick: int = 0
    head_complete_tick: int = 0
    settle_until_tick: int = 0

    @classmethod
    def steady(cls, facing: str = "south", simulation_tick: int = 0) -> "HeadEyeState":
        _validate_facing(facing)
        _validate_tick(simulation_tick)
        return cls(
            origin_facing=facing,
            presented_facing=facing,
            target_facing=facing,
            requested_tick=simulation_tick,
            head_start_tick=simulation_tick,
            head_complete_tick=simulation_tick,
            settle_until_tick=simulation_tick,
        )


@dataclass(frozen=True)
class HeadEyePresentation:
    """Facing and effective horizontal gaze for one simulation snapshot."""

    presented_facing: str
    gaze_aim: int
    automatic_gaze_aim: int
    gaze_authoritative: bool
    phase: str


def advance_head_eye(
    state: HeadEyeState,
    authoritative_facing: str,
    simulation_tick: int,
    gaze_authoritative: bool = False,
    gaze_aim: int = EYE_AIM_CENTER,
    facing_changed_tick: Optional[int] = None,
) -> Tuple[HeadEyeState, HeadEyePresentation]:
    """Sample deterministic head-eye acting at an authoritative simulation tick.

    The eyes lead a requested turn, then the head traverses adjacent authored
    views at a fixed tick cadence. Repeated calls at the same tick are
    idempotent, so retries and discarded render candidates cannot accelerate
    the performance.
    """

    if not isinstance(state, HeadEyeState):
        raise TypeError("state must be a HeadEyeState")
    _validate_state(state)
    _validate_facing(authoritative_facing)
    _validate_tick(simulation_tick)
    requested_tick = (
        simulation_tick if facing_changed_tick is None else facing_changed_tick
    )
    _validate_tick(requested_tick)
    if requested_tick > simulation_tick:
        raise ValueError("facing_changed_tick cannot exceed simulation_tick")
    if not isinstance(gaze_authoritative, bool):
        raise TypeError("gaze_authoritative must be a bool")
    _validate_gaze_aim(gaze_aim)

    if authoritative_facing != state.target_facing:
        facing_at_request = _presented_facing_at(state, requested_tick)
        state = _begin_turn(facing_at_request, authoritative_facing, requested_tick)

    sampled_facing = _presented_facing_at(state, simulation_tick)
    phase = _phase_at(state, simulation_tick)
    if phase == "steady":
        next_state = HeadEyeState.steady(state.target_facing, simulation_tick)
        automatic_aim = EYE_AIM_CENTER
    else:
        next_state = HeadEyeState(
            origin_facing=state.origin_facing,
            presented_facing=sampled_facing,
            target_facing=state.target_facing,
            turn_direction=state.turn_direction,
            sector_distance=state.sector_distance,
            requested_tick=state.requested_tick,
            head_start_tick=state.head_start_tick,
            head_complete_tick=state.head_complete_tick,
            settle_until_tick=state.settle_until_tick,
        )
        automatic_aim = (
            EYE_AIM_LEFT if state.turn_direction > 0 else EYE_AIM_RIGHT
        )

    effective_aim = gaze_aim if gaze_authoritative else automatic_aim
    return next_state, HeadEyePresentation(
        presented_facing=sampled_facing,
        gaze_aim=effective_aim,
        automatic_gaze_aim=automatic_aim,
        gaze_authoritative=gaze_authoritative,
        phase=phase,
    )


class HeadEyeCoordinator:
    """Small owner adapter; production snapshots store :class:`HeadEyeState`."""

    def __init__(self, initial_facing: str = "south", simulation_tick: int = 0) -> None:
        self._initial_facing = initial_facing
        self._state = HeadEyeState.steady(initial_facing, simulation_tick)

    @property
    def state(self) -> HeadEyeState:
        return self._state

    def advance(
        self,
        authoritative_facing: str,
        simulation_tick: int,
        gaze_authoritative: bool = False,
        gaze_aim: int = EYE_AIM_CENTER,
        facing_changed_tick: Optional[int] = None,
    ) -> HeadEyePresentation:
        self._state, presentation = advance_head_eye(
            self._state,
            authoritative_facing,
            simulation_tick,
            gaze_authoritative,
            gaze_aim,
            facing_changed_tick,
        )
        return presentation

    def reset(
        self,
        facing: Optional[str] = None,
        simulation_tick: int = 0,
    ) -> HeadEyePresentation:
        reset_facing = self._initial_facing if facing is None else facing
        self._state = HeadEyeState.steady(reset_facing, simulation_tick)
        return _steady_presentation(reset_facing)


def _begin_turn(current: str, target: str, tick: int) -> HeadEyeState:
    direction, distance = _shortest_turn(current, target)
    if distance == 0:
        return HeadEyeState.steady(target, tick)
    head_start = tick + _LEAD_TICKS_BY_DISTANCE[distance]
    head_complete = head_start + (distance - 1) * SECTOR_STEP_TICKS
    return HeadEyeState(
        origin_facing=current,
        presented_facing=current,
        target_facing=target,
        turn_direction=direction,
        sector_distance=distance,
        requested_tick=tick,
        head_start_tick=head_start,
        head_complete_tick=head_complete,
        settle_until_tick=head_complete + SETTLE_TICKS,
    )


def _presented_facing_at(state: HeadEyeState, tick: int) -> str:
    if state.sector_distance == 0:
        return state.target_facing
    if tick < state.head_start_tick:
        return state.origin_facing
    completed_steps = min(
        state.sector_distance,
        1 + (tick - state.head_start_tick) // SECTOR_STEP_TICKS,
    )
    index = DIRECTIONS.index(state.origin_facing)
    return DIRECTIONS[(index + state.turn_direction * completed_steps) % len(DIRECTIONS)]


def _phase_at(state: HeadEyeState, tick: int) -> str:
    if state.sector_distance == 0 or tick >= state.settle_until_tick:
        return "steady"
    if tick < state.head_start_tick:
        return "leading"
    if tick <= state.head_complete_tick:
        return "turning"
    return "settling"


def _shortest_turn(current: str, target: str) -> Tuple[int, int]:
    current_index = DIRECTIONS.index(current)
    target_index = DIRECTIONS.index(target)
    positive = (target_index - current_index) % len(DIRECTIONS)
    negative_distance = (current_index - target_index) % len(DIRECTIONS)
    # Exact 180-degree ties use canonical positive order for replay stability.
    if positive <= negative_distance:
        return (1 if positive else 0), positive
    return -1, negative_distance


def _steady_presentation(facing: str) -> HeadEyePresentation:
    return HeadEyePresentation(
        presented_facing=facing,
        gaze_aim=EYE_AIM_CENTER,
        automatic_gaze_aim=EYE_AIM_CENTER,
        gaze_authoritative=False,
        phase="steady",
    )


def _validate_state(state: HeadEyeState) -> None:
    for facing in (state.origin_facing, state.presented_facing, state.target_facing):
        _validate_facing(facing)
    if state.turn_direction not in {-1, 0, 1}:
        raise ValueError("turn_direction must be -1, 0, or 1")
    if not 0 <= state.sector_distance <= len(DIRECTIONS) // 2:
        raise ValueError("sector_distance is outside the canonical turn bound")
    for tick in (
        state.requested_tick,
        state.head_start_tick,
        state.head_complete_tick,
        state.settle_until_tick,
    ):
        _validate_tick(tick)
    if not (
        state.requested_tick
        <= state.head_start_tick
        <= state.head_complete_tick
        <= state.settle_until_tick
    ):
        raise ValueError("head-eye tick boundaries must be monotonic")
    if (state.sector_distance == 0) != (state.turn_direction == 0):
        raise ValueError("steady and turning state fields disagree")


def _validate_facing(facing: str) -> None:
    if facing not in DIRECTIONS:
        raise ValueError("facing must be one of DIRECTIONS")


def _validate_tick(tick: int) -> None:
    if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
        raise ValueError("simulation_tick must be a nonnegative integer")


def _validate_gaze_aim(gaze_aim: int) -> None:
    if isinstance(gaze_aim, bool) or gaze_aim not in {
        EYE_AIM_LEFT,
        EYE_AIM_CENTER,
        EYE_AIM_RIGHT,
    }:
        raise ValueError("gaze_aim must be -1, 0, or 1")


__all__ = [
    "EYE_AIM_LEFT",
    "EYE_AIM_CENTER",
    "EYE_AIM_RIGHT",
    "SECTOR_STEP_TICKS",
    "SETTLE_TICKS",
    "HeadEyeCoordinator",
    "HeadEyePresentation",
    "HeadEyeState",
    "advance_head_eye",
]
