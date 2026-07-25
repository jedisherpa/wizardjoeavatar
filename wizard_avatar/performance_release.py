"""Governed text, speech, and animation release on the accepted media clock."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

from .artifact_hashing import MAX_SAFE_INTEGER, sha256_ref
from .governed_performance import (
    GovernedPerformanceApprovalV1,
    GovernedPerformanceBindingsV1,
    GovernedPerformanceError,
    GovernedPerformanceGate,
)
from .media_session import MediaSessionSnapshotV1
from .performance_context import (
    PERFORMANCE_CONTEXT_MAX_BODY_BYTES,
    RELATIONAL_STANCES,
    SENSITIVITIES,
    SEMANTIC_INTENTS,
    TONES,
    URGENCIES,
    PerformanceContextV1,
)
from .voice_alignment import (
    VOICE_PRESENTATION_MAX_DURATION_MS,
    VoiceAlignmentEvaluationV1,
    VoiceAlignmentV1,
    VoicePresentationTrackV1,
    compile_voice_presentation,
)


GOVERNED_SPEECH_SCHEMA_VERSION = 1
GOVERNED_SPEECH_MAX_BODY_BYTES = PERFORMANCE_CONTEXT_MAX_BODY_BYTES
GOVERNED_SPEECH_MAX_TEXT_CHARS = 32_768

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_DISPLAY_PROFILES = frozenset({"desktop", "mobile"})
_PENDING_ACTION_POSTURES = frozenset(
    {"none", "not_required", "pending", "approved", "denied", "stale", "failed"}
)
_REQUIRED_SINKS = ("animation", "speech", "text")
_CANONICAL_PERSONA_CHARACTER_BINDINGS = {
    "serena-quill": (
        "serena-quill-v1",
        "sha256:30b5540c8d13cf579776961ce1b31839513a4e184355ec7a35cd16b4a98bc4e5",
    ),
}


class GovernedSpeechError(ValueError):
    """Stable release failure that never includes approved text."""

    def __init__(self, code: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        super().__init__(code)


def _error(code: str, path: str = "$") -> GovernedSpeechError:
    return GovernedSpeechError(code, path)


def _exact(value: Mapping[str, object], fields: Sequence[str], path: str) -> None:
    expected = set(fields)
    actual = set(value)
    if actual != expected:
        raise _error("schema_invalid", path)


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _error("invalid_type", path)
    return value


def _id(value: object, path: str) -> str:
    if type(value) is not str or _ID_PATTERN.fullmatch(value) is None:
        raise _error("invalid_id", path)
    return value


def _sha256(value: object, path: str) -> str:
    if type(value) is not str or _SHA256_PATTERN.fullmatch(value) is None:
        raise _error("invalid_hash", path)
    return value


def _enum(value: object, allowed: frozenset[str], path: str) -> str:
    if type(value) is not str or value not in allowed:
        raise _error("invalid_enum", path)
    return value


def _integer(value: object, path: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > MAX_SAFE_INTEGER:
        raise _error("invalid_integer", path)
    return value


def _parse_json(payload: bytes, maximum: int) -> Mapping[str, object]:
    if type(payload) is not bytes:
        raise _error("invalid_type")
    if len(payload) > maximum:
        raise _error("payload_too_large")

    def reject_duplicates(pairs: Sequence[Tuple[str, object]]) -> Dict[str, object]:
        result: Dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise _error("duplicate_json_key")
            result[key] = value
        return result

    def reject_non_integer(_value: str) -> object:
        raise _error("non_integer_number")

    try:
        decoded = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_float=reject_non_integer,
            parse_constant=reject_non_integer,
        )
    except GovernedSpeechError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("json_invalid") from exc
    return _mapping(decoded, "$")


@dataclass(frozen=True)
class PerformanceContextRequestV1:
    """Content-free semantic input for a runtime-bound context capture."""

    schema_version: int
    turn_id: str
    utterance_id: str
    media_id: str
    reply_sha256: str
    intent: str
    tone: str
    sensitivity: str
    urgency: str
    relational_stance: str
    pending_action_posture: str
    display_profile: str

    @classmethod
    def from_mapping(cls, raw: object) -> "PerformanceContextRequestV1":
        value = _mapping(raw, "$")
        fields = (
            "schema_version",
            "turn_id",
            "utterance_id",
            "media_id",
            "reply_sha256",
            "intent",
            "tone",
            "sensitivity",
            "urgency",
            "relational_stance",
            "pending_action_posture",
            "display_profile",
        )
        _exact(value, fields, "$")
        if value["schema_version"] != GOVERNED_SPEECH_SCHEMA_VERSION:
            raise _error("schema_version_unsupported", "$.schema_version")
        return cls(
            GOVERNED_SPEECH_SCHEMA_VERSION,
            _id(value["turn_id"], "$.turn_id"),
            _id(value["utterance_id"], "$.utterance_id"),
            _id(value["media_id"], "$.media_id"),
            _sha256(value["reply_sha256"], "$.reply_sha256"),
            _enum(value["intent"], SEMANTIC_INTENTS, "$.intent"),
            _enum(value["tone"], TONES, "$.tone"),
            _enum(value["sensitivity"], SENSITIVITIES, "$.sensitivity"),
            _enum(value["urgency"], URGENCIES, "$.urgency"),
            _enum(
                value["relational_stance"],
                RELATIONAL_STANCES,
                "$.relational_stance",
            ),
            _enum(
                value["pending_action_posture"],
                _PENDING_ACTION_POSTURES,
                "$.pending_action_posture",
            ),
            _enum(value["display_profile"], _DISPLAY_PROFILES, "$.display_profile"),
        )

    @classmethod
    def from_json(cls, payload: bytes) -> "PerformanceContextRequestV1":
        return cls.from_mapping(_parse_json(payload, 16 * 1024))


@dataclass(frozen=True)
class GovernedSpeechRegistrationV1:
    schema_version: int
    approved_text: str
    approval: GovernedPerformanceApprovalV1
    performance_context: PerformanceContextV1
    alignment: VoiceAlignmentV1

    @classmethod
    def from_mapping(cls, raw: object) -> "GovernedSpeechRegistrationV1":
        value = _mapping(raw, "$")
        fields = (
            "schema_version",
            "approved_text",
            "approval",
            "performance_context",
            "alignment",
        )
        _exact(value, fields, "$")
        if value["schema_version"] != GOVERNED_SPEECH_SCHEMA_VERSION:
            raise _error("schema_version_unsupported", "$.schema_version")
        text = value["approved_text"]
        if type(text) is not str or len(text) > GOVERNED_SPEECH_MAX_TEXT_CHARS:
            raise _error("approved_text_invalid", "$.approved_text")
        try:
            text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _error("approved_text_invalid", "$.approved_text") from exc
        try:
            approval = GovernedPerformanceApprovalV1.from_mapping(
                _mapping(value["approval"], "$.approval")
            )
            context = PerformanceContextV1.from_mapping(
                _mapping(value["performance_context"], "$.performance_context")
            )
            alignment = VoiceAlignmentV1.from_mapping(
                _mapping(value["alignment"], "$.alignment")
            )
        except (GovernedPerformanceError, ValueError) as exc:
            code = getattr(exc, "code", "nested_contract_invalid")
            path = getattr(exc, "path", "$")
            raise _error(str(code), str(path)) from exc
        return cls(GOVERNED_SPEECH_SCHEMA_VERSION, text, approval, context, alignment)

    @classmethod
    def from_json(cls, payload: bytes) -> "GovernedSpeechRegistrationV1":
        return cls.from_mapping(_parse_json(payload, GOVERNED_SPEECH_MAX_BODY_BYTES))

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "approved_text": self.approved_text,
            "approval": self.approval.to_dict(),
            "performance_context": self.performance_context.to_dict(),
            "alignment": self.alignment.to_dict(),
        }


@dataclass(frozen=True)
class GovernedSpeechRevocationV1:
    schema_version: int
    approval_id: str
    revocation_generation: int

    @classmethod
    def from_mapping(cls, raw: object) -> "GovernedSpeechRevocationV1":
        value = _mapping(raw, "$")
        _exact(
            value,
            ("schema_version", "approval_id", "revocation_generation"),
            "$",
        )
        if value["schema_version"] != GOVERNED_SPEECH_SCHEMA_VERSION:
            raise _error("schema_version_unsupported", "$.schema_version")
        return cls(
            GOVERNED_SPEECH_SCHEMA_VERSION,
            _id(value["approval_id"], "$.approval_id"),
            _integer(value["revocation_generation"], "$.revocation_generation", 1),
        )

    @classmethod
    def from_json(cls, payload: bytes) -> "GovernedSpeechRevocationV1":
        return cls.from_mapping(_parse_json(payload, 4 * 1024))


@dataclass(frozen=True)
class GovernedSpeechEvaluationV1:
    approved_text: str
    mouth: VoiceAlignmentEvaluationV1
    turn_id: str
    speech_id: str


@dataclass(frozen=True)
class _ActiveGovernedSpeech:
    approved_text: str
    approval: GovernedPerformanceApprovalV1
    context: PerformanceContextV1
    alignment: VoiceAlignmentV1
    presentation: VoicePresentationTrackV1
    expires_at_monotonic_us: int
    reconciliation_generation: int


class GovernedSpeechRuntime:
    """Bounded in-memory release authority evaluated by PerformanceApplication."""

    def __init__(self, gate: Optional[GovernedPerformanceGate] = None) -> None:
        self.gate = gate or GovernedPerformanceGate()
        self._active: Optional[_ActiveGovernedSpeech] = None
        self._revocation_generation = 0
        self._last_code = "no_release"

    @property
    def revocation_generation(self) -> int:
        return self._revocation_generation

    def register(
        self,
        registration: GovernedSpeechRegistrationV1,
        snapshot: MediaSessionSnapshotV1,
        *,
        runtime_epoch: str,
        character_id: str,
        package_digest: str,
        reconciliation_generation: int,
        now_wall_ms: int,
        now_monotonic_us: int,
        allow_scoreless: bool = False,
    ) -> None:
        if sha256_ref(registration.approved_text.encode("utf-8")) != registration.approval.reply_sha256:
            raise _error("content_mismatch", "$.approved_text")
        context = registration.performance_context
        alignment = registration.alignment
        approval = registration.approval
        if approval.performance_context_sha256 != context.context_sha256:
            raise _error("context_mismatch", "$.approval.performance_context_sha256")
        if context.approval.presentation_state != "approved_for_presentation":
            raise _error("presentation_not_approved", "$.performance_context.approval")
        if context.approval.presentation_artifact_sha256 != approval.reply_sha256:
            raise _error("content_mismatch", "$.performance_context.approval")
        if context.runtime.wizard_runtime_epoch != runtime_epoch:
            raise _error("runtime_epoch_mismatch", "$.performance_context.runtime")
        if context.runtime.reconciliation_generation != reconciliation_generation:
            raise _error("reconciliation_generation_mismatch", "$.performance_context.runtime")
        if context.source.connector_session_id != snapshot.connector_session_id:
            raise _error("connector_session_mismatch", "$.performance_context.source")
        if context.source.accepted_sequence != snapshot.sequence:
            raise _error("sequence_mismatch", "$.performance_context.source")
        if context.source.media_epoch != snapshot.media_epoch:
            raise _error("media_epoch_mismatch", "$.performance_context.source")
        if context.source.media_id != snapshot.media.media_id:
            raise _error("media_mismatch", "$.performance_context.source")
        if context.source.media_sha256 != snapshot.media.media_sha256:
            raise _error("media_mismatch", "$.performance_context.source")
        context_score = context.evidence.score_binding
        snapshot_score = snapshot.performance
        context_scoreless = context_score.score_id is None
        snapshot_scoreless = snapshot_score.score_id is None
        if context_scoreless or snapshot_scoreless:
            if (
                not allow_scoreless
                or not context_scoreless
                or not snapshot_scoreless
            ):
                raise _error(
                    "score_binding_required",
                    "$.performance_context.evidence.score_binding",
                )
        elif (
            context_score.score_id != snapshot_score.score_id
            or context_score.score_revision != snapshot_score.score_revision
            or context_score.score_sha256 != snapshot_score.score_sha256
        ):
            raise _error(
                "score_binding_mismatch",
                "$.performance_context.evidence.score_binding",
            )
        if context.source.source_slot != "speech" or snapshot.media.source_slot != "speech":
            raise _error("source_slot_mismatch", "$.performance_context.source")
        if context.source.turn_id != approval.turn_id:
            raise _error("turn_mismatch", "$.performance_context.source.turn_id")
        if context.character.character_id != character_id or approval.character_id != character_id:
            raise _error("character_mismatch", "$.performance_context.character")
        if context.character.package_digest != package_digest or approval.package_digest != package_digest:
            raise _error("package_mismatch", "$.performance_context.character")
        if alignment.approved_content_sha256 != approval.reply_sha256:
            raise _error("content_mismatch", "$.alignment.approved_content_sha256")
        if character_id != "wizard-joe" and approval.persona_id is None:
            raise _error("missing_persona_identity", "$.approval.persona_id")
        if character_id != "wizard-joe" and approval.voice_id is None:
            raise _error("missing_voice_identity", "$.approval.voice_id")
        if approval.voice_id is not None and approval.voice_id != alignment.voice_id:
            raise _error("voice_mismatch", "$.approval.voice_id")
        canonical_binding = (
            None
            if approval.persona_id is None
            else _CANONICAL_PERSONA_CHARACTER_BINDINGS.get(approval.persona_id)
        )
        canonical_persona_for_character = next(
            (
                persona_id
                for persona_id, (bound_character_id, _bound_package_digest)
                in _CANONICAL_PERSONA_CHARACTER_BINDINGS.items()
                if bound_character_id == character_id
            ),
            None,
        )
        if (
            canonical_binding is not None
            and canonical_binding != (character_id, package_digest)
        ) or (
            canonical_persona_for_character is not None
            and approval.persona_id != canonical_persona_for_character
        ):
            raise _error(
                "persona_character_binding_mismatch",
                "$.approval.persona_id",
            )
        if alignment.approved_text_length != len(registration.approved_text):
            raise _error("text_length_mismatch", "$.alignment.approved_text_length")
        if alignment.media_id != snapshot.media.media_id or alignment.media_sha256 != snapshot.media.media_sha256:
            raise _error("media_mismatch", "$.alignment")
        if snapshot.media.duration_ms is not None and alignment.duration_ms != snapshot.media.duration_ms:
            raise _error("duration_mismatch", "$.alignment.duration_ms")
        if alignment.duration_ms > VOICE_PRESENTATION_MAX_DURATION_MS:
            raise _error("presentation_duration_unsupported", "$.alignment.duration_ms")
        if approval.speech_media.kind == "media":
            expected_identity = alignment.media_id
        elif approval.speech_media.kind == "speech":
            expected_identity = alignment.speech_id
        else:
            raise _error("missing_speech_media_binding", "$.approval.speech_media")
        if approval.speech_media.identity != expected_identity:
            raise _error("speech_media_mismatch", "$.approval.speech_media.identity")
        if approval.speech_media.sha256 != alignment.media_sha256:
            raise _error("speech_media_mismatch", "$.approval.speech_media.sha256")
        current = GovernedPerformanceBindingsV1(
            turn_id=context.source.turn_id,
            reply_sha256=sha256_ref(registration.approved_text.encode("utf-8")),
            speech_media=approval.speech_media,
            performance_context_sha256=context.context_sha256,
            character_id=character_id,
            package_digest=package_digest,
            revocation_generation=self._revocation_generation,
            reconciliation_generation=reconciliation_generation,
        )
        try:
            self.gate.authorize_many(approval, _REQUIRED_SINKS, current, now_wall_ms)
        except GovernedPerformanceError as exc:
            raise _error(exc.code, exc.path) from exc
        presentation = compile_voice_presentation(alignment)
        remaining_ms = approval.expires_at_ms - now_wall_ms
        self._active = _ActiveGovernedSpeech(
            registration.approved_text,
            approval,
            context,
            alignment,
            presentation,
            now_monotonic_us + remaining_ms * 1000,
            reconciliation_generation,
        )
        self._last_code = "release_active"

    def reconcile(
        self,
        snapshot: MediaSessionSnapshotV1,
        reconciliation_generation: int,
        *,
        hard_reconcile: bool,
        clock_error_ms: Optional[int],
    ) -> None:
        active = self._active
        if active is None or reconciliation_generation == active.reconciliation_generation:
            return
        context = active.context
        same_binding = (
            snapshot.connector_session_id == context.source.connector_session_id
            and snapshot.media_epoch == context.source.media_epoch
            and snapshot.media.media_id == context.source.media_id
            and snapshot.media.media_sha256 == context.source.media_sha256
            and snapshot.media.source_slot == "speech"
        )
        bounded_clock_transition = (
            snapshot.cause in {"play", "playing", "pause", "waiting", "stalled"}
            and (clock_error_ms is None or abs(clock_error_ms) <= 100)
        )
        explicit_timeline_transition = snapshot.cause in {
            "ratechange",
            "seeked",
            "seeking",
        }
        lifecycle_transition = same_binding and (
            bounded_clock_transition or explicit_timeline_transition
        )
        if reconciliation_generation < active.reconciliation_generation or (
            hard_reconcile and not lifecycle_transition
        ):
            self.clear("reconciliation_changed")
            return
        if not same_binding:
            self.clear("binding_changed")
            return
        self._active = _ActiveGovernedSpeech(
            active.approved_text,
            active.approval,
            active.context,
            active.alignment,
            active.presentation,
            active.expires_at_monotonic_us,
            reconciliation_generation,
        )

    def evaluate(
        self,
        snapshot: MediaSessionSnapshotV1,
        media_time_ms: int,
        now_monotonic_us: int,
        reconciliation_generation: int,
    ) -> Optional[GovernedSpeechEvaluationV1]:
        active = self._active
        if active is None:
            return None
        if now_monotonic_us >= active.expires_at_monotonic_us:
            self.clear("approval_expired")
            return None
        context = active.context
        if (
            reconciliation_generation != active.reconciliation_generation
            or snapshot.connector_session_id != context.source.connector_session_id
            or snapshot.media_epoch != context.source.media_epoch
            or snapshot.media.media_id != context.source.media_id
            or snapshot.media.media_sha256 != context.source.media_sha256
            or snapshot.media.source_slot != "speech"
        ):
            self.clear("binding_changed")
            return None
        aligned = active.alignment.evaluate(media_time_ms)
        mouth_shape, speaking = active.presentation.evaluate(media_time_ms)
        mouth = VoiceAlignmentEvaluationV1(
            media_time_ms=aligned.media_time_ms,
            reveal_boundary=aligned.reveal_boundary,
            mouth_shape=mouth_shape,
            speaking=speaking,
            terminal=aligned.terminal,
            mouth_policy=(
                "ended" if aligned.terminal else "presentation_stabilized_v1"
            ),
        )
        return GovernedSpeechEvaluationV1(
            approved_text=active.approved_text[: mouth.reveal_boundary],
            mouth=mouth,
            turn_id=active.approval.turn_id,
            speech_id=active.alignment.speech_id,
        )

    def interrupt(self, expected_speech_id: Optional[str] = None) -> bool:
        active = self._active
        if active is None:
            return False
        if (
            expected_speech_id is not None
            and str(expected_speech_id) != active.alignment.speech_id
        ):
            return False
        self.clear("speech_interrupted")
        return True

    def revoke(self, generation: int) -> None:
        generation = _integer(generation, "$.revocation_generation")
        if generation <= self._revocation_generation:
            raise _error("revocation_generation_stale", "$.revocation_generation")
        self._revocation_generation = generation
        self.clear("approval_revoked")

    def clear(self, code: str = "released") -> None:
        self._active = None
        self._last_code = _id(code, "$.code")

    def diagnostics(self) -> Mapping[str, object]:
        active = self._active
        return {
            "active": active is not None,
            "status": self._last_code,
            "approval_id": (
                None if active is None else active.approval.approval_id
            ),
            "approval_sha256": (
                None if active is None else active.approval.approval_sha256
            ),
            "approval_hash_prefix": (
                None if active is None else active.approval.approval_sha256[7:19]
            ),
            "alignment_sha256": (
                None if active is None else active.alignment.alignment_sha256
            ),
            "alignment_hash_prefix": (
                None if active is None else active.alignment.alignment_sha256[7:19]
            ),
            "mouth_presentation_policy": (
                None if active is None else "presentation_stabilized_v1"
            ),
            "turn_id": (
                None if active is None else active.approval.turn_id
            ),
            "turn_sha256": (
                None
                if active is None
                else sha256_ref(active.approval.turn_id.encode("utf-8"))
            ),
            "turn_hash_prefix": (
                None
                if active is None
                else sha256_ref(active.approval.turn_id.encode("utf-8"))[7:19]
            ),
            "speech_id": (
                None if active is None else active.alignment.speech_id
            ),
            "character_id": (
                None if active is None else active.context.character.character_id
            ),
            "package_digest": (
                None if active is None else active.context.character.package_digest
            ),
            "media_id": (
                None if active is None else active.alignment.media_id
            ),
            "media_sha256": (
                None if active is None else active.alignment.media_sha256
            ),
            "reconciliation_generation": (
                None
                if active is None
                else active.reconciliation_generation
            ),
            "revocation_generation": self._revocation_generation,
            "replay_approval_count": self.gate.replay_approval_count,
        }


__all__ = [
    "GOVERNED_SPEECH_MAX_BODY_BYTES",
    "GOVERNED_SPEECH_SCHEMA_VERSION",
    "GovernedSpeechError",
    "GovernedSpeechEvaluationV1",
    "GovernedSpeechRegistrationV1",
    "GovernedSpeechRevocationV1",
    "GovernedSpeechRuntime",
    "PerformanceContextRequestV1",
]
