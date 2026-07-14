from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from .controller import WizardAvatarController
from .media_session import MediaSessionAckV1, MediaSessionCoordinator, MediaSessionSnapshotV1
from .models import ACTIONS, DIRECTIONS, EXPRESSIONS, MOUTH_SHAPES
from .performance_scheduler import PerformanceScheduler, ResolvedPerformanceState


_MOUTH_MAP = {
    "rest": "closed",
    "silence": "closed",
    "closed": "closed",
    "open": "open_medium",
    "wide": "open_wide",
    "open_small": "open_small",
    "open_medium": "open_medium",
    "open_wide": "open_wide",
    "rounded": "rounded",
    "smile": "smile",
    "frown": "frown",
}

_PERFORMANCE_ACTIONS = frozenset(
    {"speaking", "explaining", "flourish", "staff_spin", "celebrate", "reaction"}
)


@dataclass(frozen=True)
class PerformanceApplicationResult:
    active: bool
    source_slot: Optional[str]
    media_time_ms: Optional[int]
    action: Optional[str]
    mouth: Optional[str]
    resolution_hash: Optional[str]

    def to_dict(self) -> Mapping[str, object]:
        return {
            "active": self.active,
            "source_slot": self.source_slot,
            "media_time_ms": self.media_time_ms,
            "action": self.action,
            "mouth": self.mouth,
            "resolution_hash": self.resolution_hash,
        }


class PerformanceApplication:
    """Apply deterministic media-time performance without owning playback."""

    def __init__(self, runtime_epoch: str) -> None:
        self.scheduler = PerformanceScheduler(
            coordinator=MediaSessionCoordinator(runtime_epoch)
        )
        self._last_applied_action: Optional[str] = None
        self._last_applied_pose: Optional[str] = None
        self._last_result = PerformanceApplicationResult(False, None, None, None, None, None)

    def accept_snapshot(
        self,
        snapshot: MediaSessionSnapshotV1,
        receipt_monotonic_us: int,
    ) -> MediaSessionAckV1:
        return self.scheduler.accept_snapshot(snapshot, receipt_monotonic_us)

    def apply(
        self,
        controller: WizardAvatarController,
        now_monotonic_us: int,
    ) -> PerformanceApplicationResult:
        snapshot = self.scheduler.coordinator.accepted_snapshot
        if snapshot is None or not self._is_live(snapshot, now_monotonic_us):
            self._release_owned_state(controller)
            self._last_result = PerformanceApplicationResult(False, None, None, None, None, None)
            return self._last_result

        resolved = self.scheduler.current_state(now_monotonic_us)
        state = controller.state
        mouth = _MOUTH_MAP.get(resolved.mouth_shape, "closed")
        if mouth not in MOUTH_SHAPES:
            mouth = "closed"
        state.mouth = mouth

        if resolved.speaking:
            state.expression = "explaining"
        elif snapshot.performance.mode == "music" and resolved.expression == "neutral":
            state.expression = "happy"
        elif resolved.expression in EXPRESSIONS:
            state.expression = resolved.expression

        self._release_scripted_locomotion(controller)
        body_allowed = self._body_available(controller)
        action: Optional[str] = None
        if body_allowed:
            action = self._resolve_action(snapshot, resolved)
            if action is not None and action in ACTIONS:
                controller._set_action(action, 0)
                self._last_applied_action = action
            if resolved.pose_id and resolved.pose_id in controller.available_pose_ids:
                state.pose_override_id = resolved.pose_id
                state.pose_override_until = 0.0
                self._last_applied_pose = resolved.pose_id
            if resolved.facing in DIRECTIONS:
                state.facing = resolved.facing
            if resolved.clip_id:
                state.animation_clip_id = resolved.clip_id
                state.animation_clip_tick = resolved.clip_elapsed_ticks
            if resolved.node_id:
                state.animation_node_id = resolved.node_id

        self._last_result = PerformanceApplicationResult(
            active=True,
            source_slot=snapshot.media.source_slot,
            media_time_ms=resolved.media_time_ms,
            action=action,
            mouth=mouth,
            resolution_hash=resolved.resolution_hash,
        )
        return self._last_result

    def diagnostics(self, now_monotonic_us: int) -> Mapping[str, object]:
        return {
            "application": self._last_result.to_dict(),
            "session": self.scheduler.coordinator.diagnostics(now_monotonic_us).to_dict(),
            "scheduler": self.scheduler.diagnostics(now_monotonic_us).to_dict(),
        }

    def _is_live(self, snapshot: MediaSessionSnapshotV1, now_monotonic_us: int) -> bool:
        if snapshot.playback.state != "playing":
            return False
        age = self.scheduler.coordinator.clock.age_us(now_monotonic_us)
        return age is not None and age <= self.scheduler.coordinator.clock.freshness_limit_us

    def _body_available(self, controller: WizardAvatarController) -> bool:
        state = controller.state
        if controller.control_arbiter.active_lease is not None:
            return False
        if state.action in _PERFORMANCE_ACTIONS or state.action == "idle":
            return True
        return bool(state.action_until and state.time_seconds >= state.action_until)

    @staticmethod
    def _release_scripted_locomotion(controller: WizardAvatarController) -> None:
        """Let live media own the body without overriding a human control lease."""
        if controller.control_arbiter.active_lease is not None:
            return
        state = controller.state
        movement = controller.locomotion.movement
        scripted = (
            controller.locomotion.path.active
            or movement.target_x is not None
            or movement.target_z is not None
            or state.locomotion == "walking"
            or state.action == "walking"
        )
        if not scripted:
            return
        controller.locomotion.stop()
        controller.locomotion.sync_to_state(state)
        if state.action == "walking":
            controller._set_action("idle", 0)

    @staticmethod
    def _resolve_action(
        snapshot: MediaSessionSnapshotV1,
        resolved: ResolvedPerformanceState,
    ) -> Optional[str]:
        for value in resolved.track_values.values():
            candidate = value.get("action")
            if isinstance(candidate, str) and candidate in ACTIONS:
                return candidate
        if resolved.speaking or snapshot.performance.mode in {"narrative", "speech"}:
            return "speaking" if (resolved.media_time_ms // 1200) % 2 == 0 else "explaining"
        if snapshot.performance.mode == "music":
            return ("flourish", "staff_spin", "celebrate", "reaction")[(resolved.media_time_ms // 500) % 4]
        return None

    def _release_owned_state(self, controller: WizardAvatarController) -> None:
        state = controller.state
        if self._last_applied_action is not None and state.action == self._last_applied_action:
            controller._set_action("idle", 0)
        if self._last_applied_pose is not None and state.pose_override_id == self._last_applied_pose:
            state.pose_override_id = None
        if self._last_result.active:
            state.mouth = "closed"
        self._last_applied_action = None
        self._last_applied_pose = None
