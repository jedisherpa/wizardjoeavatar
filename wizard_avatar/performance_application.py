from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping, Optional

from .controller import WizardAvatarController
from .expressions import expression_mouth
from .media_session import MediaSessionAckV1, MediaSessionCoordinator, MediaSessionSnapshotV1
from .models import ACTIONS, DIRECTIONS, EXPRESSIONS, MOUTH_SHAPES
from .performance_context import PerformanceContextV1
from .performance_release import (
    GovernedSpeechError,
    GovernedSpeechRegistrationV1,
    GovernedSpeechRuntime,
    PerformanceContextRequestV1,
)
from .performance_scheduler import (
    AccessibilityMotionProfile,
    PerformanceScheduler,
    ResolvedPerformanceState,
    SchedulerState,
)
from .performance_score import CompiledScoreRepository
from .permission_world import (
    CapabilityPermissionV1,
    PermissionWorldCapabilityIndexV1,
    PermissionWorldRenderPolicyV1,
    PermissionWorldRuntime,
    PermissionWorldStateV1,
)
from .projection import WORLD_X_MAX, WORLD_X_MIN, WORLD_Z_FAR, WORLD_Z_NEAR
from .score_runtime import (
    SCORE_CORRUPT,
    SCORE_MISMATCH,
    SCORE_NOT_READY,
    SCORELESS_V1,
    ScorePreparationResult,
    ScoreRuntime,
)


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

    def __init__(
        self,
        runtime_epoch: str,
        score_repository: Optional[CompiledScoreRepository] = None,
        *,
        character_id: str = "wizard-joe",
        package_digest: str = "sha256:" + "0" * 64,
        manifest_digest: str = "sha256:" + "0" * 64,
        capability_manifest: Optional[Mapping[str, object]] = None,
    ) -> None:
        self.runtime_epoch = runtime_epoch
        self.character_id = character_id
        self.package_digest = package_digest
        self.manifest_digest = manifest_digest
        self.score_repository = score_repository
        self.score_runtime = (
            ScoreRuntime(score_repository) if score_repository is not None else None
        )
        self.scheduler = PerformanceScheduler(
            coordinator=MediaSessionCoordinator(runtime_epoch),
            score_resolver=(
                self.score_runtime.resolve if self.score_runtime is not None else None
            ),
        )
        self._last_applied_action: Optional[str] = None
        self._last_applied_pose: Optional[str] = None
        self._last_applied_mouth: Optional[str] = None
        self._last_applied_expression: Optional[str] = None
        self._last_governed_speech_id: Optional[str] = None
        self._last_applied_stage = False
        self._last_applied_gaze = False
        self._application_suppressions = ()
        self._paused = False
        self._last_result = PerformanceApplicationResult(False, None, None, None, None, None)
        self.governed_speech = GovernedSpeechRuntime()
        self.permission_world = PermissionWorldRuntime()
        self.permission_world_simulation = PermissionWorldRuntime()
        self.permission_world_capabilities = (
            PermissionWorldCapabilityIndexV1()
            if capability_manifest is None
            else PermissionWorldCapabilityIndexV1.from_character_manifest(
                capability_manifest
            )
        )
        self._permission_simulation_observed_ms = 0
        self._permission_visual_source_sha256: Optional[str] = None
        self._permission_visual_origin_monotonic_us: Optional[int] = None
        self._permission_visual_receipt_wall_ms: Optional[int] = None

    @property
    def paused(self) -> bool:
        return self._paused

    def set_paused(
        self,
        paused: bool,
        controller: Optional[WizardAvatarController] = None,
    ) -> None:
        self._paused = bool(paused)
        if self._paused and controller is not None:
            self._release_owned_state(controller)

    def accept_snapshot(
        self,
        snapshot: MediaSessionSnapshotV1,
        receipt_monotonic_us: int,
    ) -> MediaSessionAckV1:
        ack = self.scheduler.accept_snapshot(snapshot, receipt_monotonic_us)
        if self.score_runtime is None or ack.scheduler_state != "error":
            return ack
        runtime_code = self.score_runtime.result_for(snapshot).code
        if runtime_code not in {SCORE_NOT_READY, SCORE_MISMATCH, SCORE_CORRUPT}:
            return ack
        return replace(ack, error={"code": runtime_code})

    def prepare_snapshot(
        self,
        snapshot: MediaSessionSnapshotV1,
    ) -> ScorePreparationResult:
        """Prepare a bound score; call this through ``asyncio.to_thread``."""

        if snapshot.performance.score_id is None:
            return ScorePreparationResult(
                ready=False,
                code=SCORELESS_V1,
                binding_id=None,
                score=None,
            )
        if self.score_runtime is None:
            return ScorePreparationResult(
                ready=False,
                code=SCORE_NOT_READY,
                binding_id=None,
                score=None,
            )
        return self.score_runtime.prepare_snapshot(snapshot)

    def capture_performance_context(
        self,
        request: PerformanceContextRequestV1,
        controller: WizardAvatarController,
        now_monotonic_us: int,
    ) -> PerformanceContextV1:
        """Freeze a content-free context against the pending speech source."""

        snapshot = self.scheduler.coordinator.snapshot_for_slot("speech")
        receipt_us = self.scheduler.coordinator.receipt_for_slot("speech")
        if snapshot is None or receipt_us is None:
            raise GovernedSpeechError("media_session_not_ready")
        if snapshot.media.media_id != request.media_id:
            raise GovernedSpeechError("media_mismatch", "$.media_id")
        if snapshot.media.media_sha256 is None:
            raise GovernedSpeechError("media_digest_required", "$.media_id")
        if snapshot.performance.character_id != self.character_id:
            raise GovernedSpeechError("character_mismatch", "$.media_id")
        if snapshot.performance.character_package_sha256 != self.package_digest:
            raise GovernedSpeechError("package_mismatch", "$.media_id")

        state = controller.state
        age_ms = max(0, (now_monotonic_us - receipt_us) // 1000)
        last_acceptance = self.scheduler.coordinator.last_acceptance
        if request.display_profile == "mobile":
            display = {
                "width_px": 390,
                "height_px": 844,
                "scale_factor_milli": 1000,
                "orientation": "portrait",
                "safe_area_px": {"top": 24, "right": 0, "bottom": 24, "left": 0},
                "caption_area_milli": {"x": 40, "y": 735, "width": 920, "height": 225},
                "stage_bounds_milli": {"x": 25, "y": 25, "width": 950, "height": 690},
            }
        else:
            display = {
                "width_px": 1280,
                "height_px": 720,
                "scale_factor_milli": 1000,
                "orientation": "landscape",
                "safe_area_px": {"top": 0, "right": 0, "bottom": 24, "left": 0},
                "caption_area_milli": {"x": 50, "y": 760, "width": 900, "height": 190},
                "stage_bounds_milli": {"x": 40, "y": 30, "width": 920, "height": 700},
            }
        allowed_actions = [] if request.intent == "external_action" else [request.intent]
        payload = {
            "schema_version": 1,
            "runtime": {
                "wizard_runtime_epoch": self.runtime_epoch,
                "simulation_tick": state.simulation_tick,
                "reconciliation_generation": self.scheduler.coordinator.reconciliation_generation,
                "created_at_monotonic_ms": now_monotonic_us // 1000,
            },
            "source": {
                "connector_session_id": snapshot.connector_session_id,
                "snapshot_event_id": snapshot.message_id,
                "accepted_sequence": snapshot.sequence,
                "media_epoch": snapshot.media_epoch,
                "media_id": snapshot.media.media_id,
                "media_sha256": snapshot.media.media_sha256,
                "source_slot": snapshot.media.source_slot,
                "source_epoch": "source:{}:{}:{}".format(
                    snapshot.media.source_slot,
                    snapshot.media_epoch,
                    snapshot.connector_session_id[:8],
                ),
                "turn_id": request.turn_id,
                "utterance_id": request.utterance_id,
            },
            "clock": {
                "authoritative_media_position_ms": snapshot.playback.position_ms,
                "playback_state": snapshot.playback.state,
                "rate_milli": snapshot.playback.rate_milli,
                "snapshot_age_ms": age_ms,
                "freshness": "fresh" if age_ms <= 2_500 else "stale",
                "hard_reconcile_reason": (
                    "resync"
                    if last_acceptance is not None and last_acceptance.hard_reconcile
                    else "none"
                ),
            },
            "conversation": {
                "intent": request.intent,
                "tone": request.tone,
                "sensitivity": request.sensitivity,
                "urgency": request.urgency,
                "humor_band": 0,
                "uncertainty_band": 0,
                "relational_stance": request.relational_stance,
                "response_artifact_id": None,
            },
            "pipeline": {
                "observed_stage": "ready",
                "mapped_status": "completed",
                "stage_started_at_monotonic_ms": now_monotonic_us // 1000,
                "expected_next_event": "speech_started",
                "cancellation_posture": "not_requested",
                "error_posture": "none",
                "tts_readiness": "ready",
                "alignment_readiness": "ready",
            },
            "approval": {
                "presentation_state": "approved_for_presentation",
                "presentation_artifact_sha256": request.reply_sha256,
                "pending_action_posture": request.pending_action_posture,
            },
            "character": {
                "character_id": self.character_id,
                "package_digest": self.package_digest,
                "manifest_digest": self.manifest_digest,
                "runtime_api_version": 1,
                "current_pose_id": state.pose_id,
                "current_action_id": state.action,
                "position_milli": {
                    "x": round(state.world_position["x"] * 1000),
                    "y": round(state.altitude * 1000),
                    "z": round(state.world_position["z"] * 1000),
                },
                "facing": state.facing,
                "gaze": "direct_viewer",
                "expression": state.expression,
                "world_state": "default",
                "recent_performance": [],
            },
            "display": display,
            "governance": {
                "allowed_semantic_actions": sorted(allowed_actions),
                "denied_semantic_actions": ["external_action"],
                "pending_approval_references": [],
                "memory_scope": "session",
                "external_action_posture": "not_requested",
                "notification_scope": "current_surface",
                "linked_surface_state": "unlinked",
            },
            "preferences": {
                "motion_profile": snapshot.performance.motion_profile,
                "intensity_band": snapshot.performance.intensity_milli,
                "disabled_channels": list(snapshot.performance.disabled_channels),
                "caption_mode": "auto",
                "progressive_reveal_preference": "enabled",
                "voice_preference": "synchronized",
            },
            "control": {
                "user_locomotion_lease_id": None,
                "user_locomotion_lease_expires_at_monotonic_ms": None,
                "manual_override_state": (
                    "active" if controller.control_arbiter.active_lease is not None else "inactive"
                ),
                "channel_claims": [],
                "cancellation_generation": state.control_lease_generation,
            },
            "evidence": {
                "ordered_fingerprints": sorted(
                    {request.reply_sha256, "sha256:" + snapshot.fingerprint()}
                ),
                "source_commits": [],
                "schema_versions": [
                    {"schema_id": "governed-performance-approval", "version": 1},
                    {"schema_id": "media-session-snapshot", "version": 1},
                    {"schema_id": "performance-context", "version": 1},
                    {"schema_id": "voice-alignment", "version": 1},
                ],
                "score_binding": {
                    "score_id": snapshot.performance.score_id,
                    "score_revision": snapshot.performance.score_revision,
                    "score_sha256": snapshot.performance.score_sha256,
                },
                "package_digest": self.package_digest,
            },
        }
        return PerformanceContextV1.build(payload)

    def register_governed_speech(
        self,
        registration: GovernedSpeechRegistrationV1,
        *,
        now_wall_ms: int,
        now_monotonic_us: int,
    ) -> None:
        snapshot = self.scheduler.coordinator.snapshot_for_slot("speech")
        if snapshot is None:
            raise GovernedSpeechError("media_session_not_ready")
        self.governed_speech.register(
            registration,
            snapshot,
            runtime_epoch=self.runtime_epoch,
            character_id=self.character_id,
            package_digest=self.package_digest,
            reconciliation_generation=self.scheduler.coordinator.reconciliation_generation,
            now_wall_ms=now_wall_ms,
            now_monotonic_us=now_monotonic_us,
        )

    def revoke_governed_speech(
        self,
        generation: int,
        controller: WizardAvatarController,
    ) -> None:
        self.governed_speech.revoke(generation)
        self._release_owned_state(controller)
        self._orient_toward_viewer_after_interruption(controller)

    def accept_permission_world(
        self,
        state: PermissionWorldStateV1,
        received_at_wall_ms: Optional[int] = None,
    ) -> Mapping[str, object]:
        self.permission_world.accept(state)
        self._permission_visual_source_sha256 = None
        self._permission_visual_origin_monotonic_us = None
        self._permission_visual_receipt_wall_ms = (
            state.observed_at_ms
            if received_at_wall_ms is None
            else max(state.observed_at_ms, int(received_at_wall_ms))
        )
        return self.permission_world.diagnostics()

    def _apply_authoritative_permission_world(
        self,
        controller: WizardAvatarController,
        now_monotonic_us: int,
    ) -> None:
        """Publish one bounded authority snapshot for the pure frame compositor."""

        publish = getattr(controller, "set_permission_world_render_policy", None)
        if not callable(publish):
            return
        state = self.permission_world.current_state
        snapshot = self.scheduler.coordinator.accepted_snapshot
        motion_profile = (
            "full" if snapshot is None else snapshot.performance.motion_profile
        )
        if state is None:
            publish(
                PermissionWorldRenderPolicyV1.build(
                    source_state_sha256=None,
                    evaluated_at_ms=0,
                    motion_profile=motion_profile,
                    managed_world_states=(
                        self.permission_world_capabilities.world_state_ids
                    ),
                    managed_effects=self.permission_world_capabilities.effect_ids,
                    managed_props=self.permission_world_capabilities.prop_ids,
                )
            )
            return

        if self._permission_visual_source_sha256 != state.state_sha256:
            self._permission_visual_source_sha256 = state.state_sha256
            self._permission_visual_origin_monotonic_us = now_monotonic_us
        origin = self._permission_visual_origin_monotonic_us
        if origin is None:
            origin = now_monotonic_us
            self._permission_visual_origin_monotonic_us = origin
        elapsed_ms = max(0, now_monotonic_us - origin) // 1000
        receipt_wall_ms = self._permission_visual_receipt_wall_ms
        if receipt_wall_ms is None:
            receipt_wall_ms = state.observed_at_ms
        evaluated_at_ms = max(state.observed_at_ms, receipt_wall_ms) + elapsed_ms
        projection = self.permission_world.project(
            evaluated_at_ms=evaluated_at_ms,
            motion_profile=motion_profile,
            capability_index=self.permission_world_capabilities,
        )
        publish(
            PermissionWorldRenderPolicyV1.from_projection(projection)
        )

    def permission_world_snapshot(
        self,
        evaluated_at_ms: int,
    ) -> Mapping[str, object]:
        state = self.permission_world.current_state
        snapshot = self.scheduler.coordinator.accepted_snapshot
        motion_profile = (
            "full" if snapshot is None else snapshot.performance.motion_profile
        )
        simulation_state = self.permission_world_simulation.current_state

        def projected(runtime, current):
            if current is None:
                return None
            return runtime.project(
                evaluated_at_ms=max(evaluated_at_ms, current.observed_at_ms),
                motion_profile=motion_profile,
                capability_index=self.permission_world_capabilities,
            ).to_dict()

        projection = projected(self.permission_world, state)
        simulation_projection = projected(
            self.permission_world_simulation,
            simulation_state,
        )

        def runtime_projection(runtime, current, projection_value):
            if current is None or projection_value is None:
                return {
                    "schema_version": 1,
                    "status": "empty",
                    "source_epoch_sha256": None,
                    "source_state_sha256": None,
                    "observed_at_ms": None,
                    "evaluated_at_ms": evaluated_at_ms,
                    "motion_profile": motion_profile,
                    "visible_surfaces": {
                        "world_states": [],
                        "effects": [],
                        "props": [],
                    },
                    "affordances": [],
                    "projection_sha256": None,
                }
            return runtime.project(
                evaluated_at_ms=max(evaluated_at_ms, current.observed_at_ms),
                motion_profile=motion_profile,
                capability_index=self.permission_world_capabilities,
            ).to_runtime_dict()

        return {
            "render_authority": {
                "source": "authoritative",
                "applied_to_projected_frames": True,
                "simulation_can_control_projection": False,
                "active_projection_sha256": (
                    None if projection is None else projection["projection_sha256"]
                ),
            },
            "state": None if state is None else state.to_dict(),
            "projection": projection,
            "runtime": runtime_projection(self.permission_world, state, projection),
            "simulation_state": (
                None if simulation_state is None else simulation_state.to_dict()
            ),
            "simulation_projection": simulation_projection,
            "simulation_runtime": runtime_projection(
                self.permission_world_simulation,
                simulation_state,
                simulation_projection,
            ),
            "simulation_boundary": {
                "source": "director_simulation",
                "label": "SIMULATION",
                "applied_to_projected_frames": False,
            },
            "diagnostics": self.permission_world.diagnostics(),
            "simulation_diagnostics": self.permission_world_simulation.diagnostics(),
        }

    def simulate_permission_world(
        self,
        permission: CapabilityPermissionV1,
        observed_at_ms: int,
    ) -> Mapping[str, object]:
        observed = max(observed_at_ms, self._permission_simulation_observed_ms + 1)
        state = PermissionWorldStateV1.build(
            source_epoch="director-simulation:{}".format(self.runtime_epoch),
            observed_at_ms=observed,
            permissions=(permission,),
        )
        self.permission_world_simulation.accept(state)
        self._permission_simulation_observed_ms = observed
        return self.permission_world_snapshot(observed)

    def clear_permission_world_simulation(self) -> Mapping[str, object]:
        self.permission_world_simulation = PermissionWorldRuntime()
        self._permission_simulation_observed_ms = 0
        return self.permission_world_snapshot(0)

    def apply(
        self,
        controller: WizardAvatarController,
        now_monotonic_us: int,
    ) -> PerformanceApplicationResult:
        self._apply_authoritative_permission_world(controller, now_monotonic_us)
        snapshot = self.scheduler.coordinator.accepted_snapshot
        if self._paused:
            self._release_owned_state(controller)
            self._clear_performance_trace_state(controller)
            self._last_result = PerformanceApplicationResult(False, None, None, None, None, None)
            return self._last_result
        if snapshot is None or not self._is_live(snapshot, now_monotonic_us):
            self._release_owned_state(controller)
            self._clear_performance_trace_state(controller)
            self._last_result = PerformanceApplicationResult(False, None, None, None, None, None)
            return self._last_result
        if (
            snapshot.performance.score_id is not None
            and self.scheduler.scheduler_state is SchedulerState.ERROR
        ):
            self._release_owned_state(controller)
            self._clear_performance_trace_state(controller)
            self._last_result = PerformanceApplicationResult(
                False, None, None, None, None, None
            )
            return self._last_result

        resolved = self.scheduler.current_state(now_monotonic_us)
        state = controller.state
        governed = self.governed_speech.evaluate(
            snapshot,
            resolved.media_time_ms,
            now_monotonic_us,
            self.scheduler.coordinator.reconciliation_generation,
        )
        speech_source = snapshot.media.source_slot == "speech"
        speech_authorized = not speech_source or governed is not None
        self._suspend_prism_channels(controller, ("expression", "mouth"))
        if governed is not None:
            mouth = governed.mouth.mouth_shape
            speaking = governed.mouth.speaking
            state.speech_id = governed.speech_id
            state.speech_text = governed.approved_text
            state.speech_started_at = 0.0
            state.speech_until = 0.0
            state.speech_mouth_authority = "media_alignment"
            self._last_governed_speech_id = governed.speech_id
        elif speech_source:
            mouth = "closed"
            speaking = False
            self._clear_governed_speech_state(state)
        else:
            mouth = _MOUTH_MAP.get(resolved.mouth_shape, "closed")
            speaking = resolved.speaking
            self._clear_governed_speech_state(state)
        if mouth not in MOUTH_SHAPES:
            mouth = "closed"
        state.mouth = mouth
        self._last_applied_mouth = mouth

        if speaking:
            state.expression = "explaining"
            self._last_applied_expression = state.expression
        elif snapshot.performance.mode == "music" and resolved.expression == "neutral":
            state.expression = "happy"
            self._last_applied_expression = state.expression
        elif resolved.expression in EXPRESSIONS:
            state.expression = resolved.expression
            self._last_applied_expression = state.expression

        self._release_scripted_locomotion(controller)
        body_allowed = speech_authorized and self._body_available(controller)
        self._application_suppressions = self._apply_stage_and_gaze(
            controller,
            resolved,
            body_allowed=body_allowed,
            gaze_allowed=speech_authorized,
        )
        action: Optional[str] = None
        if body_allowed:
            self._suspend_prism_channels(controller, ("action",))
            if resolved.motion_profile is AccessibilityMotionProfile.FULL:
                action = self._resolve_action(snapshot, resolved, speaking)
                if action is not None and action in ACTIONS:
                    controller._set_action(action, 0)
                    self._last_applied_action = action
                elif (
                    self._last_applied_action is not None
                    and state.action == self._last_applied_action
                ):
                    controller._set_action("idle", 0)
                    self._last_applied_action = None
                if resolved.pose_id and resolved.pose_id in controller.available_pose_ids:
                    state.pose_override_id = resolved.pose_id
                    state.pose_override_until = 0.0
                    self._last_applied_pose = resolved.pose_id
                elif (
                    self._last_applied_pose is not None
                    and state.pose_override_id == self._last_applied_pose
                ):
                    state.pose_override_id = None
                    state.pose_override_until = 0.0
                    self._last_applied_pose = None
                if resolved.facing in DIRECTIONS:
                    state.set_facing(resolved.facing)
                if resolved.clip_id:
                    state.animation_clip_id = resolved.clip_id
                    state.animation_clip_tick = resolved.clip_elapsed_ticks
                if resolved.node_id:
                    state.animation_node_id = resolved.node_id
            else:
                self._release_body_projection(controller)
                self._application_suppressions += (
                    {
                        "channel": "body",
                        "reason_code": "motion_profile_projection",
                    },
                )

        self._publish_performance_trace_state(controller, resolved)

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
        diagnostics = {
            "reactions_paused": self._paused,
            "application": self._last_result.to_dict(),
            "session": self.scheduler.coordinator.diagnostics(now_monotonic_us).to_dict(),
            "scheduler": self.scheduler.diagnostics(now_monotonic_us).to_dict(),
            "governed_speech": self.governed_speech.diagnostics(),
            "permission_world": self.permission_world.diagnostics(),
            "permission_world_simulation": self.permission_world_simulation.diagnostics(),
            "application_suppressions": list(self._application_suppressions),
        }
        snapshot = self.scheduler.coordinator.accepted_snapshot
        if self.score_runtime is not None and snapshot is not None:
            diagnostics["score_runtime"] = self.score_runtime.diagnostics_mapping(snapshot)
        return diagnostics

    def _is_live(self, snapshot: MediaSessionSnapshotV1, now_monotonic_us: int) -> bool:
        if snapshot.playback.state != "playing":
            return False
        age = self.scheduler.coordinator.clock.age_us(now_monotonic_us)
        return age is not None and age <= self.scheduler.coordinator.clock.freshness_limit_us

    def _body_available(self, controller: WizardAvatarController) -> bool:
        state = controller.state
        if controller.control_arbiter.active_lease is not None:
            return False
        if (
            self._last_applied_action is not None
            and state.action == self._last_applied_action
        ):
            return True
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
        speaking: bool,
    ) -> Optional[str]:
        if resolved.motion_profile is not AccessibilityMotionProfile.FULL:
            return None
        for value in resolved.track_values.values():
            candidate = value.get("action")
            if isinstance(candidate, str) and candidate in ACTIONS:
                return candidate
        if speaking:
            # Scoreless speech owns the face, not a repeating whole-body pose.
            # Authored gesture tracks above may still request a motivated accent.
            return "speaking"
        if snapshot.performance.mode == "music":
            return ("flourish", "staff_spin", "celebrate", "reaction")[(resolved.media_time_ms // 500) % 4]
        return None

    def _release_body_projection(self, controller: WizardAvatarController) -> None:
        state = controller.state
        if state.action in _PERFORMANCE_ACTIONS:
            controller._set_action("idle", 0)
        if self._last_applied_pose is not None and state.pose_override_id == self._last_applied_pose:
            state.pose_override_id = None
            state.pose_override_until = 0.0
        self._last_applied_action = None
        self._last_applied_pose = None

    @staticmethod
    def _clear_performance_trace_state(controller: WizardAvatarController) -> None:
        state = controller.state
        state.performance_motion_profile = "none"
        state.performance_resolution_hash = None
        state.performance_owned_channels = ()
        state.performance_suppression_codes = ()

    def _publish_performance_trace_state(
        self,
        controller: WizardAvatarController,
        resolved: ResolvedPerformanceState,
    ) -> None:
        scheduler_codes = {
            record.reason_code for record in resolved.suppressed_requests
        }
        application_codes = {
            str(record.get("reason_code"))
            for record in self._application_suppressions
            if record.get("reason_code")
        }
        state = controller.state
        state.performance_motion_profile = resolved.motion_profile.value
        state.performance_resolution_hash = resolved.resolution_hash
        state.performance_owned_channels = tuple(sorted(resolved.owned_channels))
        state.performance_suppression_codes = tuple(
            sorted(scheduler_codes | application_codes)
        )

    def _release_owned_state(self, controller: WizardAvatarController) -> None:
        state = controller.state
        self._clear_governed_speech_state(state)
        if (
            self._last_applied_action is not None
            and state.speech_id is None
            and state.action == self._last_applied_action
        ):
            controller._set_action("idle", 0)
        if self._last_applied_pose is not None and state.pose_override_id == self._last_applied_pose:
            state.pose_override_id = None
        if (
            self._last_applied_mouth is not None
            and state.speech_id is None
            and state.mouth == self._last_applied_mouth
        ):
            state.mouth = expression_mouth(state.expression)
        if (
            self._last_applied_expression is not None
            and state.speech_id is None
            and state.expression == self._last_applied_expression
        ):
            state.expression = "neutral"
            state.mouth = expression_mouth(state.expression)
        self._last_applied_action = None
        self._last_applied_pose = None
        self._last_applied_mouth = None
        self._last_applied_expression = None
        if self._last_applied_gaze:
            state.gaze_authoritative = False
            state.gaze_aim = 0
            state.gaze_vertical_aim = 0
        self._last_applied_gaze = False
        self._last_applied_stage = False
        self._application_suppressions = ()
        self._resume_prism_channels(controller, ("action", "expression", "mouth"))

    @staticmethod
    def _orient_toward_viewer_after_interruption(
        controller: WizardAvatarController,
    ) -> None:
        """Recover the performance stance without moving or overriding a human."""
        if controller.control_arbiter.active_lease is not None:
            return
        controller.state.set_facing("south")

    def _clear_governed_speech_state(self, state) -> None:
        if (
            self._last_governed_speech_id is not None
            and state.speech_id == self._last_governed_speech_id
        ):
            state.speech_id = None
            state.speech_text = None
            state.speech_started_at = 0.0
            state.speech_until = 0.0
            state.speech_mouth_authority = "none"
        self._last_governed_speech_id = None

    def _apply_stage_and_gaze(
        self,
        controller: WizardAvatarController,
        resolved: ResolvedPerformanceState,
        *,
        body_allowed: bool,
        gaze_allowed: bool,
    ):
        state = controller.state
        suppressions = []
        stage_owned = bool(
            resolved.owned_channels & {"stage", "locomotion", "position"}
        )
        if stage_owned:
            if not body_allowed:
                reason = (
                    "user_control_lease"
                    if controller.control_arbiter.active_lease is not None
                    else "body_authority_unavailable"
                )
                suppressions.append({"channel": "stage", "reason_code": reason})
            else:
                x_milli, depth_milli = resolved.world_position_milli
                if not (0 <= x_milli <= 1000 and 0 <= depth_milli <= 1000):
                    suppressions.append(
                        {"channel": "stage", "reason_code": "stage_position_out_of_range"}
                    )
                else:
                    x = WORLD_X_MIN + (WORLD_X_MAX - WORLD_X_MIN) * x_milli / 1000.0
                    z = WORLD_Z_FAR - (WORLD_Z_FAR - WORLD_Z_NEAR) * depth_milli / 1000.0
                    controller.locomotion.stop()
                    controller.locomotion.movement.position_x = x
                    controller.locomotion.movement.position_z = z
                    controller.locomotion.sync_to_state(state)
                    self._last_applied_stage = True

        gaze_owned = bool(resolved.owned_channels & {"gaze", "eyes"})
        if gaze_owned:
            if not gaze_allowed:
                suppressions.append(
                    {"channel": "gaze", "reason_code": "presentation_not_approved"}
                )
            elif state.gaze_authoritative and not self._last_applied_gaze:
                suppressions.append(
                    {"channel": "gaze", "reason_code": "manual_gaze_override"}
                )
            else:
                gaze = resolved.gaze_target.lower()
                if gaze.startswith("semantic:gaze:"):
                    gaze = gaze.split(":", 2)[2]
                if gaze in {"forward", "center", "direct", "direct_viewer", "viewer"}:
                    aim = 0
                elif gaze in {"left", "viewer_left", "screen_left"}:
                    aim = -1
                elif gaze in {"right", "viewer_right", "screen_right"}:
                    aim = 1
                else:
                    aim = None
                if aim is None:
                    suppressions.append(
                        {"channel": "gaze", "reason_code": "gaze_target_unsupported"}
                    )
                else:
                    state.gaze_aim = aim
                    state.gaze_vertical_aim = 0
                    state.gaze_authoritative = True
                    self._last_applied_gaze = True
        elif self._last_applied_gaze:
            state.gaze_authoritative = False
            state.gaze_aim = 0
            state.gaze_vertical_aim = 0
            self._last_applied_gaze = False
        return tuple(suppressions)

    @staticmethod
    def _suspend_prism_channels(controller, channels) -> None:
        suspend = getattr(controller, "suspend_prism_channels", None)
        if suspend is not None:
            suspend(channels, owner="performance")

    @staticmethod
    def _resume_prism_channels(controller, channels) -> None:
        resume = getattr(controller, "resume_prism_channels", None)
        if resume is not None:
            resume(channels, owner="performance")
