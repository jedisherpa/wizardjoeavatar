from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, replace
import time
from typing import Iterable, Mapping, Optional

from .animation_graph import AnimationGraph, load_reference_animation_graph_v2
from .artifact_hashing import canonical_json_v1, sha256_ref
from .character_choreography import (
    CharacterChoreographyDictionaryV1,
    ChoreographyIntentBindingV1,
)
from .character_registry import CharacterRegistry
from .character_runtime_profile import CharacterRuntimeProfile
from .controller import WizardAvatarController
from .expressions import expression_mouth
from .live_speech_score import (
    CompiledLiveSpeechScoreV1,
    LiveSpeechScoreError,
    PreparedLiveSpeechScoreV1,
    compile_live_speech_score,
    publish_live_speech_score,
)
from .media_session import (
    MediaSessionAck,
    MediaSessionAdmissionV1,
    MediaSessionCoordinator,
    MediaSessionSnapshot,
    MediaSessionSnapshotV1,
    MediaSessionSnapshotV2,
)
from .models import ACTIONS, DIRECTIONS, EXPRESSIONS, MOUTH_SHAPES
from .performance_context import PerformanceContextV1
from .directed_performance import (
    CompiledDirectedPerformanceV1,
    DirectedPerformanceError,
    DirectedPerformancePreparationV1,
    PreparedDirectedPerformanceV1,
    compile_directed_performance,
    publish_directed_performance,
)
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
from .performance_score import CompiledScoreRepository, ScoreValidationError
from .permission_world import (
    CapabilityPermissionV1,
    PermissionWorldCapabilityIndexV1,
    PermissionWorldRenderPolicyV1,
    PermissionWorldRuntime,
    PermissionWorldStateV1,
)
from .projection import WORLD_X_MAX, WORLD_X_MIN, WORLD_Z_FAR, WORLD_Z_NEAR
from .score_runtime import (
    SCORE_ADMISSION_MISMATCH,
    SCORE_CORRUPT,
    SCORE_MISMATCH,
    SCORE_NOT_READY,
    SCORELESS_V1,
    ScorePreparationResult,
    ScoreRuntime,
)


_UNBOUND_DIGEST = "sha256:" + "0" * 64
_LIVE_SCORE_PREPARATION_CAPACITY = 256
_LIVE_SCORE_PREPARATION_TTL_US = 30_000_000
_LIVE_SCORE_RETENTION_LIMIT = 2_048


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
_LEGACY_MEDIA_V1_CHARACTER_ID = "wizard-joe-v1"
_LEGACY_MEDIA_V1_PACKAGE_DIGEST = (
    "sha256:e35d9fee572e8f984a25a3776e2be51e1920b2a09f568170f12ccd3f0851b387"
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


@dataclass(frozen=True)
class _LiveScorePreparationGrant:
    prepared: PreparedLiveSpeechScoreV1
    expires_at_monotonic_us: int


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
        animation_graph: Optional[AnimationGraph] = None,
        runtime_profile: Optional[CharacterRuntimeProfile] = None,
        choreography_dictionary: Optional[
            CharacterChoreographyDictionaryV1
        ] = None,
        pose_library_digest: Optional[str] = None,
        graph_digest: Optional[str] = None,
        admitted_pose_ids: Optional[Iterable[str]] = None,
        admitted_clip_ids: Optional[Iterable[str]] = None,
        admitted_node_ids: Optional[Iterable[str]] = None,
        allow_scoreless_governed_speech: bool = False,
        character_registry: Optional[CharacterRegistry] = None,
    ) -> None:
        self.runtime_epoch = runtime_epoch
        self.character_id = character_id
        self.package_digest = package_digest
        self.manifest_digest = manifest_digest
        character_admission = (
            None
            if character_registry is None
            else character_registry.resolve_admission(
                character_id,
                package_digest,
            )
        )
        self.character_admission = character_admission
        self.persona_id = (
            None if character_admission is None else character_admission.persona_id
        )
        self.admission_sha256 = (
            None
            if character_admission is None
            else character_admission.admission_sha256
        )
        self.runtime_admitted = character_admission is not None
        character_manifest = (
            capability_manifest.get("character")
            if isinstance(capability_manifest, Mapping)
            else None
        )
        package_schema_version = (
            character_manifest.get("package_schema_version")
            if isinstance(character_manifest, Mapping)
            else None
        )
        self.package_schema_version = (
            package_schema_version
            if type(package_schema_version) is int and package_schema_version > 0
            else None
        )
        self.score_repository = score_repository
        self.capability_manifest = capability_manifest
        self.allow_scoreless_governed_speech = bool(
            allow_scoreless_governed_speech
        )
        identity_bound = package_digest != _UNBOUND_DIGEST
        self.score_runtime = (
            ScoreRuntime(
                score_repository,
                character_id=character_id if identity_bound else None,
                package_digest=(
                    package_digest if identity_bound else None
                ),
                pose_library_digest=pose_library_digest,
                graph_digest=graph_digest,
                admitted_pose_ids=admitted_pose_ids,
                admitted_clip_ids=admitted_clip_ids,
                admitted_node_ids=admitted_node_ids,
            )
            if score_repository is not None
            else None
        )
        media_runtime_admission = (
            None
            if character_admission is None
            else MediaSessionAdmissionV1(
                schema_version=character_admission.schema_version,
                persona_id=character_admission.persona_id,
                character_id=character_admission.character_id,
                package_digest=character_admission.package_sha256,
                admission_sha256=character_admission.admission_sha256,
            )
        )
        self.scheduler = PerformanceScheduler(
            coordinator=MediaSessionCoordinator(
                runtime_epoch,
                runtime_admission=media_runtime_admission,
            ),
            score_resolver=(
                self.score_runtime.resolve if self.score_runtime is not None else None
            ),
        )
        self.animation_graph = (
            animation_graph
            if animation_graph is not None
            else load_reference_animation_graph_v2()
        )
        self.runtime_profile = runtime_profile
        self.choreography_dictionary = choreography_dictionary
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
        self._live_score_preparations: OrderedDict[
            tuple[str, int, str], _LiveScorePreparationGrant
        ] = OrderedDict()

    def _require_runtime_admission(self) -> None:
        if (
            not self.runtime_admitted
            or self.character_admission is None
            or self.persona_id is None
            or self.admission_sha256 is None
        ):
            raise GovernedSpeechError(
                "character_not_runtime_admitted",
                "$.performance_context.character",
            )

    def performance_binding(self) -> Mapping[str, object]:
        self._require_runtime_admission()
        admission = self.character_admission
        if admission is None:
            raise GovernedSpeechError("character_not_runtime_admitted")
        content = {
            "schema_version": 2,
            "wizard_runtime_epoch": self.runtime_epoch,
            "admission": dict(admission.content_dict()),
            "admission_sha256": admission.admission_sha256,
            "reconciliation_generation": (
                self.scheduler.coordinator.reconciliation_generation
            ),
            "revocation_generation": self.governed_speech.revocation_generation,
        }
        return {
            **content,
            "binding_sha256": sha256_ref(canonical_json_v1(content)),
        }

    def supports_action(self, action: str) -> bool:
        if self.runtime_profile is None:
            return action in ACTIONS
        if action == "walking":
            return bool(self.runtime_profile.locomotion_cycles.get("walk", ()))
        return action in {"idle", "speaking"} or action in self.runtime_profile.action_poses

    def choreography_binding(
        self,
        intent_id: str,
        *,
        allow_fallback: bool = True,
    ) -> Optional[ChoreographyIntentBindingV1]:
        if self.choreography_dictionary is None:
            return None
        if not allow_fallback:
            return self.choreography_dictionary.intent_bindings.get(intent_id)
        return self.choreography_dictionary.binding_for_intent(intent_id)

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
        snapshot: MediaSessionSnapshot,
        receipt_monotonic_us: int,
    ) -> MediaSessionAck:
        identity_error = self._snapshot_identity_error(snapshot)
        if identity_error is not None:
            return self.scheduler.coordinator.reject_without_mutation(
                snapshot,
                identity_error,
            )
        ack = self.scheduler.accept_snapshot(snapshot, receipt_monotonic_us)
        acceptance = self.scheduler.coordinator.last_acceptance
        if (
            acceptance is not None
            and acceptance.snapshot is snapshot
            and ack.disposition == "accepted"
        ):
            self._reconcile_live_score_preparations(
                snapshot,
                receipt_monotonic_us,
            )
            self.governed_speech.reconcile(
                snapshot,
                acceptance.reconciliation_generation,
                hard_reconcile=acceptance.hard_reconcile,
                clock_error_ms=acceptance.clock_error_ms,
            )
        if self.score_runtime is None or ack.scheduler_state != "error":
            return ack
        runtime_code = self.score_runtime.result_for(snapshot).code
        if runtime_code not in {SCORE_NOT_READY, SCORE_MISMATCH, SCORE_CORRUPT}:
            return ack
        return replace(ack, error={"code": runtime_code})

    def prepare_snapshot(
        self,
        snapshot: MediaSessionSnapshot,
    ) -> ScorePreparationResult:
        """Prepare a bound score; call this through ``asyncio.to_thread``."""

        if self._snapshot_identity_error(snapshot) is not None:
            return ScorePreparationResult(
                ready=False,
                code=SCORE_ADMISSION_MISMATCH,
                binding_id=None,
                score=None,
            )
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

    def _snapshot_identity_error(
        self,
        snapshot: MediaSessionSnapshot,
    ) -> Optional[str]:
        if self.package_digest == _UNBOUND_DIGEST:
            return None
        if not self.runtime_admitted or self.character_admission is None:
            return "character_not_runtime_admitted"
        if isinstance(snapshot, MediaSessionSnapshotV1):
            if (
                snapshot.performance.character_id
                != _LEGACY_MEDIA_V1_CHARACTER_ID
                or snapshot.performance.character_package_sha256
                != _LEGACY_MEDIA_V1_PACKAGE_DIGEST
                or self.character_id != _LEGACY_MEDIA_V1_CHARACTER_ID
                or self.package_digest != _LEGACY_MEDIA_V1_PACKAGE_DIGEST
            ):
                return "legacy_schema_not_allowed"
            return None
        if not isinstance(snapshot, MediaSessionSnapshotV2):
            return "schema_version_unsupported"
        if snapshot.performance.persona_id != self.persona_id:
            return "persona_mismatch"
        if snapshot.performance.character_id != self.character_id:
            return "character_mismatch"
        if snapshot.performance.character_package_sha256 != self.package_digest:
            return "package_mismatch"
        if snapshot.performance.admission_sha256 != self.admission_sha256:
            return "admission_mismatch"
        return None

    def capture_performance_context(
        self,
        request: PerformanceContextRequestV1,
        controller: WizardAvatarController,
        now_monotonic_us: int,
        *,
        source_slot: str = "speech",
    ) -> PerformanceContextV1:
        """Freeze a content-free context against one authoritative media source."""

        self._require_runtime_admission()
        if source_slot not in {"main", "speech"}:
            raise GovernedSpeechError("source_slot_mismatch", "$.source_slot")
        snapshot = self.scheduler.coordinator.snapshot_for_slot(source_slot)
        receipt_us = self.scheduler.coordinator.receipt_for_slot(source_slot)
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
                "expected_next_event": (
                    "speech_started"
                    if source_slot == "speech"
                    else "terminal_posture"
                ),
                "cancellation_posture": "not_requested",
                "error_posture": "none",
                "tts_readiness": (
                    "ready" if source_slot == "speech" else "not_requested"
                ),
                "alignment_readiness": (
                    "ready" if source_slot == "speech" else "not_requested"
                ),
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

    def compile_directed_performance(
        self,
        preparation: DirectedPerformancePreparationV1,
        context: PerformanceContextV1,
    ) -> CompiledDirectedPerformanceV1:
        """Compile a governed direction off the event loop."""

        self._require_runtime_admission()
        if self.score_repository is None:
            raise DirectedPerformanceError("score_repository_not_ready")
        if self.capability_manifest is None:
            raise DirectedPerformanceError("capability_manifest_not_ready")
        return compile_directed_performance(
            preparation,
            context,
            capability_manifest=self.capability_manifest,
        )

    def publish_directed_performance(
        self,
        compiled: CompiledDirectedPerformanceV1,
    ) -> PreparedDirectedPerformanceV1:
        """Publish a revalidated direction through the existing score repository."""

        self._require_runtime_admission()
        if self.score_repository is None:
            raise DirectedPerformanceError("score_repository_not_ready")
        return publish_directed_performance(
            compiled,
            repository=self.score_repository,
        )

    def compile_live_speech_score(
        self,
        context: PerformanceContextV1,
        *,
        duration_ms: int,
    ) -> CompiledLiveSpeechScoreV1:
        """Compile an unpublished preliminary-context score off the event loop."""

        self._require_runtime_admission()
        if self.score_runtime is None:
            raise GovernedSpeechError("score_repository_not_ready")
        if self.capability_manifest is None:
            raise GovernedSpeechError("capability_manifest_not_ready")
        try:
            return compile_live_speech_score(
                context,
                duration_ms=duration_ms,
                capability_manifest=self.capability_manifest,
            )
        except LiveSpeechScoreError as exc:
            raise GovernedSpeechError(exc.code, exc.path) from exc

    def publish_live_speech_score(
        self,
        compiled: CompiledLiveSpeechScoreV1,
    ) -> PreparedLiveSpeechScoreV1:
        self._require_runtime_admission()
        if self.score_repository is None:
            raise GovernedSpeechError("score_repository_not_ready")
        try:
            protected_bindings = [
                (
                    grant.prepared.score_binding.media_sha256,
                    grant.prepared.score_binding.score_id,
                    grant.prepared.score_binding.score_revision,
                    grant.prepared.score_binding.score_sha256,
                )
                for grant in self._live_score_preparations.values()
            ]
            speech_snapshot = self.scheduler.coordinator.snapshot_for_slot("speech")
            if (
                speech_snapshot is not None
                and speech_snapshot.media.media_sha256 is not None
                and speech_snapshot.performance.score_id is not None
                and speech_snapshot.performance.score_revision is not None
                and speech_snapshot.performance.score_sha256 is not None
            ):
                protected_bindings.append(
                    (
                        speech_snapshot.media.media_sha256,
                        speech_snapshot.performance.score_id,
                        speech_snapshot.performance.score_revision,
                        speech_snapshot.performance.score_sha256,
                    )
                )
            self.score_repository.prune_live_generations(
                protected_bindings=protected_bindings,
                max_generations=_LIVE_SCORE_RETENTION_LIMIT - 1,
            )
            prepared = publish_live_speech_score(
                compiled,
                repository=self.score_repository,
            )
        except (LiveSpeechScoreError, ScoreValidationError) as exc:
            raise GovernedSpeechError(exc.code, exc.path) from exc
        binding = prepared.score_binding
        key = (binding.score_id, binding.score_revision, binding.score_sha256)
        self._live_score_preparations[key] = _LiveScorePreparationGrant(
            prepared=prepared,
            expires_at_monotonic_us=(
                time.perf_counter_ns() // 1000 + _LIVE_SCORE_PREPARATION_TTL_US
            ),
        )
        self._live_score_preparations.move_to_end(key)
        while len(self._live_score_preparations) > _LIVE_SCORE_PREPARATION_CAPACITY:
            self._live_score_preparations.popitem(last=False)
        return prepared

    def _reconcile_live_score_preparations(
        self,
        snapshot: MediaSessionSnapshot,
        now_monotonic_us: int,
    ) -> None:
        for key, grant in tuple(self._live_score_preparations.items()):
            preliminary = grant.prepared.preliminary_context
            binding = grant.prepared.score_binding
            expired = now_monotonic_us > grant.expires_at_monotonic_us
            superseded = (
                snapshot.media.source_slot == "speech"
                and not (
                    snapshot.connector_session_id
                    == preliminary.source.connector_session_id
                    and snapshot.sequence
                    == preliminary.source.accepted_sequence + 1
                    and snapshot.media_epoch == preliminary.source.media_epoch + 1
                    and snapshot.media.media_id == binding.media_id
                    and snapshot.media.media_sha256 == binding.media_sha256
                    and snapshot.performance.score_id == binding.score_id
                    and snapshot.performance.score_revision
                    == binding.score_revision
                    and snapshot.performance.score_sha256
                    == binding.score_sha256
                )
            )
            if expired or superseded:
                self._live_score_preparations.pop(key, None)

    @staticmethod
    def _validate_live_score_preparation(
        grant: _LiveScorePreparationGrant,
        registration: GovernedSpeechRegistrationV1,
        snapshot: MediaSessionSnapshot,
    ) -> None:
        prepared = grant.prepared
        preliminary = prepared.preliminary_context
        final = registration.performance_context
        approval = registration.approval
        binding = prepared.score_binding
        source_matches = (
            preliminary.source.connector_session_id
            == final.source.connector_session_id
            == snapshot.connector_session_id
            and preliminary.source.media_id
            == final.source.media_id
            == snapshot.media.media_id
            and preliminary.source.media_sha256
            == final.source.media_sha256
            == snapshot.media.media_sha256
            and preliminary.source.source_slot
            == final.source.source_slot
            == snapshot.media.source_slot
            and preliminary.source.turn_id == final.source.turn_id
            and preliminary.source.utterance_id == final.source.utterance_id
            and final.source.accepted_sequence
            == preliminary.source.accepted_sequence + 1
            and final.source.media_epoch == preliminary.source.media_epoch + 1
        )
        identity_matches = (
            preliminary.runtime.wizard_runtime_epoch
            == final.runtime.wizard_runtime_epoch
            and preliminary.character.character_id
            == final.character.character_id
            == binding.character_id
            and preliminary.character.package_digest
            == final.character.package_digest
            == binding.package_digest
            and preliminary.approval.presentation_artifact_sha256
            == final.approval.presentation_artifact_sha256
            == approval.reply_sha256
            and binding.prepared_from_context_sha256
            == preliminary.context_sha256
        )
        if not source_matches or not identity_matches:
            raise GovernedSpeechError(
                "score_preparation_mismatch",
                "$.performance_context.evidence.score_binding",
            )

    def register_governed_speech(
        self,
        registration: GovernedSpeechRegistrationV1,
        *,
        now_wall_ms: int,
        now_monotonic_us: int,
    ) -> Mapping[str, object]:
        self._require_runtime_admission()
        snapshot = self.scheduler.coordinator.snapshot_for_slot("speech")
        if snapshot is None:
            raise GovernedSpeechError("media_session_not_ready")
        score_binding = {
            "score_id": snapshot.performance.score_id,
            "score_revision": snapshot.performance.score_revision,
            "score_sha256": snapshot.performance.score_sha256,
        }
        if all(value is None for value in score_binding.values()):
            if not self.allow_scoreless_governed_speech:
                raise GovernedSpeechError(
                    "score_binding_required",
                    "$.performance_context.evidence.score_binding",
                )
        else:
            if self.score_runtime is None:
                raise GovernedSpeechError("score_repository_not_ready")
            prepared = self.score_runtime.result_for(snapshot)
            score = prepared.score
            if not prepared.ready or score is None:
                raise GovernedSpeechError(
                    "score_not_ready",
                    "$.performance_context.evidence.score_binding",
                )
            if (
                score.compiled_score_id != score_binding["score_id"]
                or score.revision != score_binding["score_revision"]
                or score.artifact_sha256 != score_binding["score_sha256"]
            ):
                raise GovernedSpeechError(
                    "score_binding_mismatch",
                    "$.performance_context.evidence.score_binding",
                )
            key = (
                score.compiled_score_id,
                score.revision,
                score.artifact_sha256,
            )
            live_preparation = self._live_score_preparations.get(key)
            if live_preparation is None:
                raise GovernedSpeechError(
                    "score_preparation_required",
                    "$.performance_context.evidence.score_binding",
                )
            if now_monotonic_us > live_preparation.expires_at_monotonic_us:
                self._live_score_preparations.pop(key, None)
                raise GovernedSpeechError(
                    "score_preparation_expired",
                    "$.performance_context.evidence.score_binding",
                )
            self._validate_live_score_preparation(
                live_preparation,
                registration,
                snapshot,
            )
        self.governed_speech.register(
            registration,
            snapshot,
            runtime_epoch=self.runtime_epoch,
            character_id=self.character_id,
            package_digest=self.package_digest,
            persona_id=self.persona_id,
            admission_sha256=self.admission_sha256,
            runtime_admitted=self.runtime_admitted,
            reconciliation_generation=self.scheduler.coordinator.reconciliation_generation,
            now_wall_ms=now_wall_ms,
            now_monotonic_us=now_monotonic_us,
            allow_scoreless=self.allow_scoreless_governed_speech,
        )
        if not all(value is None for value in score_binding.values()):
            self._live_score_preparations.pop(key, None)
        return score_binding

    def revoke_governed_speech(
        self,
        generation: int,
        controller: WizardAvatarController,
    ) -> None:
        self.governed_speech.revoke(generation)
        self._live_score_preparations.clear()
        self._release_owned_state(controller)
        self._orient_toward_viewer_after_interruption(controller)

    def interrupt_governed_speech(
        self,
        expected_speech_id: Optional[str],
        controller: WizardAvatarController,
    ) -> bool:
        interrupted = self.governed_speech.interrupt(expected_speech_id)
        if interrupted:
            self._release_owned_state(controller)
        return interrupted

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
        whole_pose_speech = bool(
            governed is not None
            and speaking
            and self.runtime_profile is not None
            and self.runtime_profile.speech_pose_map
        )
        self._application_suppressions = self._apply_stage_and_gaze(
            controller,
            resolved,
            body_allowed=body_allowed,
            gaze_allowed=speech_authorized,
        )
        action: Optional[str] = None
        if body_allowed:
            self._suspend_prism_channels(controller, ("action",))
            if whole_pose_speech:
                self._release_body_projection(controller)
                self._application_suppressions += (
                    {
                        "channel": "body",
                        "reason_code": "whole_pose_speech_authority",
                    },
                )
            elif resolved.motion_profile is AccessibilityMotionProfile.FULL:
                action = self._resolve_action(
                    snapshot,
                    resolved,
                    speaking,
                    controller,
                )
                if action is not None and controller.supports_action(action):
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

    def _is_live(self, snapshot: MediaSessionSnapshot, now_monotonic_us: int) -> bool:
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

    def _resolve_action(
        self,
        snapshot: MediaSessionSnapshot,
        resolved: ResolvedPerformanceState,
        speaking: bool,
        controller: Optional[WizardAvatarController] = None,
    ) -> Optional[str]:
        supports_action = (
            controller.supports_action
            if controller is not None
            else self.supports_action
        )
        if resolved.motion_profile is not AccessibilityMotionProfile.FULL:
            return None
        for value in resolved.track_values.values():
            candidate = value.get("action")
            if isinstance(candidate, str) and supports_action(candidate):
                return candidate
        node = self.animation_graph.nodes.get(resolved.node_id)
        if node is not None:
            for candidate in node.actions:
                if supports_action(candidate):
                    return candidate
        if resolved.owned_channels & {"locomotion", "stage", "position"}:
            return "walking" if supports_action("walking") else None
        if speaking:
            # Scoreless speech owns the face, not a repeating whole-body pose.
            # Authored gesture tracks above may still request a motivated accent.
            if (
                self.choreography_dictionary is not None
                and self.choreography_dictionary.instructions.speech_motion_policy
                == "unsupported"
            ):
                return None
            binding = self.choreography_binding(
                "speak",
                allow_fallback=False,
            )
            if binding is not None:
                for action in binding.action_ids:
                    if supports_action(action):
                        return action
                return None
            return "speaking"
        if snapshot.performance.mode == "music":
            binding = self.choreography_binding(
                "music",
                allow_fallback=False,
            )
            if binding is not None:
                candidates = tuple(
                    action
                    for action in binding.action_ids
                    if supports_action(action)
                )
                if candidates:
                    return candidates[
                        (resolved.media_time_ms // 500) % len(candidates)
                    ]
                return None
            candidates = tuple(
                action
                for action in ("flourish", "staff_spin", "celebrate", "reaction")
                if supports_action(action)
            )
            if candidates:
                return candidates[(resolved.media_time_ms // 500) % len(candidates)]
        return None

    def _release_body_projection(self, controller: WizardAvatarController) -> None:
        state = controller.state
        if (
            self._last_applied_action is not None
            and state.action == self._last_applied_action
        ) or state.action in _PERFORMANCE_ACTIONS:
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
