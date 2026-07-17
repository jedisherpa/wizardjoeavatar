"""Immutable, content-free Character Director performance context contract."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, Optional, Sequence, Tuple, Union

from .artifact_hashing import MAX_SAFE_INTEGER, canonical_json_v1, sha256_ref


PERFORMANCE_CONTEXT_SCHEMA_VERSION = 1
PERFORMANCE_CONTEXT_MAX_BODY_BYTES = 64 * 1024

ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")

SOURCE_SLOTS = frozenset({"main", "speech"})
PLAYBACK_STATES = frozenset(
    {"empty", "loading", "paused", "playing", "buffering", "seeking", "ended", "stopped", "error"}
)
FRESHNESS_STATES = frozenset({"fresh", "stale", "uncertain"})
HARD_RECONCILE_REASONS = frozenset(
    {
        "none",
        "initial",
        "reconnect",
        "source_changed",
        "speech_preempted_main",
        "speech_restored_main",
        "seek",
        "track_changed",
        "runtime_epoch_changed",
        "controller_takeover",
        "resync",
    }
)
SEMANTIC_INTENTS = frozenset(
    {
        "none",
        "no_decision",
        "neutral",
        "characterful_neutral",
        "listen",
        "think",
        "speak",
        "explain",
        "review",
        "clarify",
        "wait",
        "recall",
        "reference",
        "topic_reset",
        "degraded",
        "greet",
        "acknowledge",
        "celebrate",
        "caution",
        "empathize",
        "reassure",
        "question",
        "direct",
        "present",
        "transition",
        "permission_posture",
        "interrupt",
        "settle",
        "external_action",
    }
)
TONES = frozenset({"neutral", "warm", "playful", "focused", "measured", "direct", "reflective", "serious"})
SENSITIVITIES = frozenset({"ordinary", "sensitive", "high_stakes", "restricted"})
URGENCIES = frozenset({"low", "normal", "high", "critical"})
RELATIONAL_STANCES = frozenset({"neutral", "collaborative", "supportive", "instructive", "deferential", "firm"})
PIPELINE_STAGES = frozenset(
    {
        "none",
        "queued",
        "understanding",
        "reading_you",
        "listening",
        "drafting",
        "checking_safety",
        "auditing",
        "deciding",
        "reviewing",
        "ready",
        "speaking",
        "needs_clarification",
        "waiting_approval",
        "recalling",
        "referencing",
        "degraded",
    }
)
PIPELINE_STATUSES = frozenset({"none", "started", "active", "completed", "cancelled", "failed"})
NEXT_EVENTS = frozenset(
    {
        "stage_changed",
        "terminal_posture",
        "response_released",
        "speech_started",
        "speech_ended",
        "approval_changed",
        "cancellation_confirmed",
    }
)
CANCELLATION_POSTURES = frozenset({"not_requested", "output_stopped", "requested", "confirmed", "failed"})
ERROR_POSTURES = frozenset({"none", "degraded", "recoverable", "terminal"})
READINESS_STATES = frozenset({"not_requested", "pending", "ready", "unavailable", "failed"})
PRESENTATION_STATES = frozenset({"unapproved", "approved_for_presentation", "denied"})
PENDING_ACTION_POSTURES = frozenset({"none", "not_required", "pending", "approved", "denied", "stale", "failed"})
FACINGS = frozenset({"north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"})
PERFORMANCE_DISPOSITIONS = frozenset({"completed", "cancelled", "interrupted", "failed", "suppressed", "fallback"})
ORIENTATIONS = frozenset({"portrait", "landscape", "square"})
MEMORY_SCOPES = frozenset({"none", "turn", "session", "linked_surface"})
EXTERNAL_ACTION_POSTURES = frozenset({"not_requested", "pending", "allowed", "denied", "revoked", "expired"})
NOTIFICATION_SCOPES = frozenset({"none", "current_surface", "linked_surfaces"})
LINKED_SURFACE_STATES = frozenset({"unlinked", "link_pending", "linked", "revoked", "stale"})
MOTION_PROFILES = frozenset({"full", "reduced", "still"})
CAPTION_MODES = frozenset({"off", "auto", "on"})
PROGRESSIVE_REVEAL_PREFERENCES = frozenset({"disabled", "enabled", "system"})
VOICE_PREFERENCES = frozenset({"silent", "synchronized", "system"})
MANUAL_OVERRIDE_STATES = frozenset({"inactive", "active", "releasing"})
CHANNEL_OWNERS = frozenset({"performance", "user", "system"})
KNOWN_CHANNELS = frozenset(
    {
        "body_base",
        "upper_body",
        "locomotion",
        "dance",
        "flight",
        "camera_motion",
        "simulated_depth",
        "whole_body_pulse",
        "scene_flash",
        "face",
        "eyes",
        "mouth",
        "gaze",
        "blink",
        "speech",
        "gesture",
        "effects",
        "props",
        "world_state",
        "text_reveal",
        "stage",
        "position",
        "facing",
        "breathing",
        "permission_posture",
        "interruption",
        "manual_override",
        "whole_pose",
    }
)

_FORBIDDEN_KEY_FRAGMENTS = (
    "prompt",
    "reply",
    "transcript",
    "message_body",
    "content",
    "snippet",
    "raw_text",
    "memory_body",
    "backstory_body",
    "retrieved_text",
    "embedding",
    "vector",
    "url",
    "path",
    "token",
    "secret",
    "bearer",
    "credential",
    "receipt",
    "authority",
    "provider",
    "model_name",
    "payload",
)

_FORBIDDEN_VALUE_PATTERNS = (
    re.compile(r"(?i)^bearer\s"),
    re.compile(r"(?i)^basic\s"),
    re.compile(r"(?i)^(?:sk|xox[baprs]|gh[opusr])[-_]"),
    re.compile(r"(?i)^-----BEGIN\s"),
    re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://"),
    re.compile(r"^(?:/|~/|[A-Za-z]:[\\/])"),
    re.compile(r"[\r\n\t]"),
)


class PerformanceContextError(ValueError):
    """Stable, path-addressed failure with no caller-provided content."""

    def __init__(self, code: str, message: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        super().__init__(message)


def _is_int(value: object) -> bool:
    return type(value) is int


def _check_json_value(value: object, path: str = "$") -> None:
    if value is None or type(value) in (str, bool):
        if type(value) is str:
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise PerformanceContextError("invalid_type", "text is not valid UTF-8", path) from exc
        return
    if type(value) is int:
        if abs(value) > MAX_SAFE_INTEGER:
            raise PerformanceContextError("invalid_type", "integer exceeds the canonical range", path)
        return
    if isinstance(value, float):
        raise PerformanceContextError(
            "non_integer_identity_value",
            "performance context cannot contain floating-point values",
            path,
        )
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is not str:
                raise PerformanceContextError("invalid_type", "object keys must be strings", path)
            _check_json_value(item, "{}.{}".format(path, key))
        return
    if type(value) in (list, tuple):
        for index, item in enumerate(value):
            _check_json_value(item, "{}[{}]".format(path, index))
        return
    raise PerformanceContextError("invalid_type", "unsupported context value", path)


def _reject_private_content(value: object, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(fragment in normalized for fragment in _FORBIDDEN_KEY_FRAGMENTS):
                raise PerformanceContextError(
                    "private_content",
                    "performance context contains a forbidden private field",
                    "{}.{}".format(path, key),
                )
            _reject_private_content(item, "{}.{}".format(path, key))
    elif type(value) in (list, tuple):
        for index, item in enumerate(value):
            _reject_private_content(item, "{}[{}]".format(path, index))
    elif type(value) is str and any(pattern.search(value) for pattern in _FORBIDDEN_VALUE_PATTERNS):
        raise PerformanceContextError(
            "private_content",
            "performance context contains a forbidden private value",
            path,
        )


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PerformanceContextError("invalid_type", "expected an object", path)
    return value


def _exact(value: Mapping[str, object], fields: Sequence[str], path: str) -> None:
    expected = set(fields)
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing:
        raise PerformanceContextError("missing_field", "object is missing required fields", path)
    if unknown:
        raise PerformanceContextError("unknown_field", "object contains unknown fields", path)


def _integer(value: object, path: str, minimum: int = 0, maximum: int = MAX_SAFE_INTEGER) -> int:
    if not _is_int(value) or not minimum <= value <= maximum:
        raise PerformanceContextError("invalid_type", "expected a bounded integer", path)
    return value


def _id(value: object, path: str) -> str:
    if type(value) is not str or ID_PATTERN.fullmatch(value) is None:
        raise PerformanceContextError("invalid_id", "expected a stable content-free identifier", path)
    return value


def _optional_id(value: object, path: str) -> Optional[str]:
    return None if value is None else _id(value, path)


def _uuid(value: object, path: str) -> str:
    if type(value) is not str or UUID_V4_PATTERN.fullmatch(value) is None:
        raise PerformanceContextError("invalid_id", "expected a canonical UUIDv4", path)
    return value


def _hash(value: object, path: str) -> str:
    if type(value) is not str or SHA256_PATTERN.fullmatch(value) is None:
        raise PerformanceContextError("invalid_hash", "expected a SHA-256 reference", path)
    return value


def _optional_hash(value: object, path: str) -> Optional[str]:
    return None if value is None else _hash(value, path)


def _enum(value: object, allowed: frozenset[str], path: str) -> str:
    if type(value) is not str or value not in allowed:
        raise PerformanceContextError("invalid_enum", "value is not in the allowed set", path)
    return value


def _optional_enum(value: object, allowed: frozenset[str], path: str) -> Optional[str]:
    return None if value is None else _enum(value, allowed, path)


def _sorted_unique_ids(value: object, path: str, allowed: Optional[frozenset[str]] = None) -> Tuple[str, ...]:
    if type(value) not in (list, tuple):
        raise PerformanceContextError("invalid_type", "expected an array", path)
    result = tuple(_id(item, "{}[{}]".format(path, index)) for index, item in enumerate(value))
    if allowed is not None and any(item not in allowed for item in result):
        raise PerformanceContextError("invalid_enum", "array contains an unsupported value", path)
    if list(result) != sorted(result) or len(result) != len(set(result)):
        raise PerformanceContextError("invalid_order", "set-like values must be sorted and unique", path)
    return result


def _parse_json(source: Union[str, bytes]) -> Mapping[str, object]:
    if type(source) is bytes:
        if len(source) > PERFORMANCE_CONTEXT_MAX_BODY_BYTES:
            raise PerformanceContextError("body_too_large", "context exceeds the size limit")
        try:
            text = source.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PerformanceContextError("invalid_json", "context is not valid UTF-8 JSON") from exc
    elif type(source) is str:
        if len(source.encode("utf-8")) > PERFORMANCE_CONTEXT_MAX_BODY_BYTES:
            raise PerformanceContextError("body_too_large", "context exceeds the size limit")
        text = source
    else:
        raise PerformanceContextError("invalid_type", "source must be JSON text or bytes")

    def reject_duplicates(pairs: Sequence[Tuple[str, object]]) -> Dict[str, object]:
        result: Dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                raise PerformanceContextError("duplicate_json_key", "duplicate JSON object key")
            result[key] = item
        return result

    def reject_float(_value: str) -> object:
        raise PerformanceContextError(
            "non_integer_identity_value",
            "performance context cannot contain floating-point values",
        )

    try:
        parsed = json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_float=reject_float,
            parse_constant=reject_float,
        )
    except PerformanceContextError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise PerformanceContextError("invalid_json", "context is not valid JSON") from exc
    return _mapping(parsed, "$")


@dataclass(frozen=True)
class RuntimeContextV1:
    wizard_runtime_epoch: str
    simulation_tick: int
    reconciliation_generation: int
    created_at_monotonic_ms: int

    @classmethod
    def from_mapping(cls, raw: object) -> "RuntimeContextV1":
        value = _mapping(raw, "$.runtime")
        _exact(value, ("wizard_runtime_epoch", "simulation_tick", "reconciliation_generation", "created_at_monotonic_ms"), "$.runtime")
        return cls(
            _id(value["wizard_runtime_epoch"], "$.runtime.wizard_runtime_epoch"),
            _integer(value["simulation_tick"], "$.runtime.simulation_tick"),
            _integer(value["reconciliation_generation"], "$.runtime.reconciliation_generation"),
            _integer(value["created_at_monotonic_ms"], "$.runtime.created_at_monotonic_ms"),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "wizard_runtime_epoch": self.wizard_runtime_epoch,
            "simulation_tick": self.simulation_tick,
            "reconciliation_generation": self.reconciliation_generation,
            "created_at_monotonic_ms": self.created_at_monotonic_ms,
        }


@dataclass(frozen=True)
class SourceContextV1:
    connector_session_id: str
    snapshot_event_id: str
    accepted_sequence: int
    media_epoch: int
    media_id: str
    media_sha256: Optional[str]
    source_slot: str
    source_epoch: str
    turn_id: Optional[str]
    utterance_id: Optional[str]

    @classmethod
    def from_mapping(cls, raw: object) -> "SourceContextV1":
        value = _mapping(raw, "$.source")
        fields = (
            "connector_session_id",
            "snapshot_event_id",
            "accepted_sequence",
            "media_epoch",
            "media_id",
            "media_sha256",
            "source_slot",
            "source_epoch",
            "turn_id",
            "utterance_id",
        )
        _exact(value, fields, "$.source")
        media_id = _id(value["media_id"], "$.source.media_id")
        media_sha256 = _optional_hash(value["media_sha256"], "$.source.media_sha256")
        if media_sha256 is not None:
            expected_media_id = "media:sha256:" + media_sha256.split(":", 1)[1]
            if media_id != expected_media_id:
                raise PerformanceContextError(
                    "hash_mismatch",
                    "media identity does not match its digest",
                    "$.source.media_id",
                )
        return cls(
            _uuid(value["connector_session_id"], "$.source.connector_session_id"),
            _id(value["snapshot_event_id"], "$.source.snapshot_event_id"),
            _integer(value["accepted_sequence"], "$.source.accepted_sequence"),
            _integer(value["media_epoch"], "$.source.media_epoch"),
            media_id,
            media_sha256,
            _enum(value["source_slot"], SOURCE_SLOTS, "$.source.source_slot"),
            _id(value["source_epoch"], "$.source.source_epoch"),
            _optional_id(value["turn_id"], "$.source.turn_id"),
            _optional_id(value["utterance_id"], "$.source.utterance_id"),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "connector_session_id": self.connector_session_id,
            "snapshot_event_id": self.snapshot_event_id,
            "accepted_sequence": self.accepted_sequence,
            "media_epoch": self.media_epoch,
            "media_id": self.media_id,
            "media_sha256": self.media_sha256,
            "source_slot": self.source_slot,
            "source_epoch": self.source_epoch,
            "turn_id": self.turn_id,
            "utterance_id": self.utterance_id,
        }


@dataclass(frozen=True)
class ClockContextV1:
    authoritative_media_position_ms: int
    playback_state: str
    rate_milli: int
    snapshot_age_ms: int
    freshness: str
    hard_reconcile_reason: str

    @classmethod
    def from_mapping(cls, raw: object) -> "ClockContextV1":
        value = _mapping(raw, "$.clock")
        fields = ("authoritative_media_position_ms", "playback_state", "rate_milli", "snapshot_age_ms", "freshness", "hard_reconcile_reason")
        _exact(value, fields, "$.clock")
        return cls(
            _integer(value["authoritative_media_position_ms"], "$.clock.authoritative_media_position_ms"),
            _enum(value["playback_state"], PLAYBACK_STATES, "$.clock.playback_state"),
            _integer(value["rate_milli"], "$.clock.rate_milli", 1, 8_000),
            _integer(value["snapshot_age_ms"], "$.clock.snapshot_age_ms"),
            _enum(value["freshness"], FRESHNESS_STATES, "$.clock.freshness"),
            _enum(value["hard_reconcile_reason"], HARD_RECONCILE_REASONS, "$.clock.hard_reconcile_reason"),
        )

    def to_dict(self) -> Dict[str, object]:
        return dict(vars(self))


@dataclass(frozen=True)
class ConversationContextV1:
    intent: str
    tone: str
    sensitivity: str
    urgency: str
    humor_band: int
    uncertainty_band: int
    relational_stance: str
    response_artifact_id: Optional[str]

    @classmethod
    def from_mapping(cls, raw: object) -> "ConversationContextV1":
        value = _mapping(raw, "$.conversation")
        fields = ("intent", "tone", "sensitivity", "urgency", "humor_band", "uncertainty_band", "relational_stance", "response_artifact_id")
        _exact(value, fields, "$.conversation")
        return cls(
            _enum(value["intent"], SEMANTIC_INTENTS, "$.conversation.intent"),
            _enum(value["tone"], TONES, "$.conversation.tone"),
            _enum(value["sensitivity"], SENSITIVITIES, "$.conversation.sensitivity"),
            _enum(value["urgency"], URGENCIES, "$.conversation.urgency"),
            _integer(value["humor_band"], "$.conversation.humor_band", 0, 1_000),
            _integer(value["uncertainty_band"], "$.conversation.uncertainty_band", 0, 1_000),
            _enum(value["relational_stance"], RELATIONAL_STANCES, "$.conversation.relational_stance"),
            _optional_id(value["response_artifact_id"], "$.conversation.response_artifact_id"),
        )

    def to_dict(self) -> Dict[str, object]:
        return dict(vars(self))


@dataclass(frozen=True)
class PipelineContextV1:
    observed_stage: str
    mapped_status: str
    stage_started_at_monotonic_ms: int
    expected_next_event: Optional[str]
    cancellation_posture: str
    error_posture: str
    tts_readiness: str
    alignment_readiness: str

    @classmethod
    def from_mapping(cls, raw: object) -> "PipelineContextV1":
        value = _mapping(raw, "$.pipeline")
        fields = ("observed_stage", "mapped_status", "stage_started_at_monotonic_ms", "expected_next_event", "cancellation_posture", "error_posture", "tts_readiness", "alignment_readiness")
        _exact(value, fields, "$.pipeline")
        return cls(
            _enum(value["observed_stage"], PIPELINE_STAGES, "$.pipeline.observed_stage"),
            _enum(value["mapped_status"], PIPELINE_STATUSES, "$.pipeline.mapped_status"),
            _integer(value["stage_started_at_monotonic_ms"], "$.pipeline.stage_started_at_monotonic_ms"),
            _optional_enum(value["expected_next_event"], NEXT_EVENTS, "$.pipeline.expected_next_event"),
            _enum(value["cancellation_posture"], CANCELLATION_POSTURES, "$.pipeline.cancellation_posture"),
            _enum(value["error_posture"], ERROR_POSTURES, "$.pipeline.error_posture"),
            _enum(value["tts_readiness"], READINESS_STATES, "$.pipeline.tts_readiness"),
            _enum(value["alignment_readiness"], READINESS_STATES, "$.pipeline.alignment_readiness"),
        )

    def to_dict(self) -> Dict[str, object]:
        return dict(vars(self))


@dataclass(frozen=True)
class ApprovalContextV1:
    presentation_state: str
    presentation_artifact_sha256: Optional[str]
    pending_action_posture: str

    @classmethod
    def from_mapping(cls, raw: object) -> "ApprovalContextV1":
        value = _mapping(raw, "$.approval")
        fields = ("presentation_state", "presentation_artifact_sha256", "pending_action_posture")
        _exact(value, fields, "$.approval")
        state = _enum(value["presentation_state"], PRESENTATION_STATES, "$.approval.presentation_state")
        digest = _optional_hash(value["presentation_artifact_sha256"], "$.approval.presentation_artifact_sha256")
        if state == "approved_for_presentation" and digest is None:
            raise PerformanceContextError("missing_binding", "approved presentation requires an artifact digest", "$.approval.presentation_artifact_sha256")
        if state != "approved_for_presentation" and digest is not None:
            raise PerformanceContextError("invalid_binding", "unapproved presentation cannot bind an artifact digest", "$.approval.presentation_artifact_sha256")
        return cls(state, digest, _enum(value["pending_action_posture"], PENDING_ACTION_POSTURES, "$.approval.pending_action_posture"))

    def to_dict(self) -> Dict[str, object]:
        return dict(vars(self))


def _position(value: object, path: str) -> Mapping[str, int]:
    raw = _mapping(value, path)
    _exact(raw, ("x", "y", "z"), path)
    return MappingProxyType(
        {
            "x": _integer(raw["x"], path + ".x", -MAX_SAFE_INTEGER, MAX_SAFE_INTEGER),
            "y": _integer(raw["y"], path + ".y", -MAX_SAFE_INTEGER, MAX_SAFE_INTEGER),
            "z": _integer(raw["z"], path + ".z", -MAX_SAFE_INTEGER, MAX_SAFE_INTEGER),
        }
    )


@dataclass(frozen=True)
class RecentPerformanceV1:
    performance_id: str
    intent: str
    disposition: str

    @classmethod
    def from_mapping(cls, raw: object, path: str) -> "RecentPerformanceV1":
        value = _mapping(raw, path)
        _exact(value, ("performance_id", "intent", "disposition"), path)
        return cls(
            _id(value["performance_id"], path + ".performance_id"),
            _enum(value["intent"], SEMANTIC_INTENTS, path + ".intent"),
            _enum(value["disposition"], PERFORMANCE_DISPOSITIONS, path + ".disposition"),
        )

    def to_dict(self) -> Dict[str, object]:
        return dict(vars(self))


@dataclass(frozen=True)
class CharacterContextV1:
    character_id: str
    package_digest: str
    manifest_digest: str
    runtime_api_version: int
    current_pose_id: str
    current_action_id: str
    position_milli: Mapping[str, int]
    facing: str
    gaze: str
    expression: str
    world_state: str
    recent_performance: Tuple[RecentPerformanceV1, ...]

    @classmethod
    def from_mapping(cls, raw: object) -> "CharacterContextV1":
        value = _mapping(raw, "$.character")
        fields = ("character_id", "package_digest", "manifest_digest", "runtime_api_version", "current_pose_id", "current_action_id", "position_milli", "facing", "gaze", "expression", "world_state", "recent_performance")
        _exact(value, fields, "$.character")
        recent_raw = value["recent_performance"]
        if type(recent_raw) not in (list, tuple) or len(recent_raw) > 16:
            raise PerformanceContextError("invalid_type", "recent performance must be a bounded array", "$.character.recent_performance")
        recent = tuple(RecentPerformanceV1.from_mapping(item, "$.character.recent_performance[{}]".format(index)) for index, item in enumerate(recent_raw))
        ids = [item.performance_id for item in recent]
        if len(ids) != len(set(ids)):
            raise PerformanceContextError("duplicate_id", "recent performance identifiers must be unique", "$.character.recent_performance")
        return cls(
            _id(value["character_id"], "$.character.character_id"),
            _hash(value["package_digest"], "$.character.package_digest"),
            _hash(value["manifest_digest"], "$.character.manifest_digest"),
            _integer(value["runtime_api_version"], "$.character.runtime_api_version", 1),
            _id(value["current_pose_id"], "$.character.current_pose_id"),
            _id(value["current_action_id"], "$.character.current_action_id"),
            _position(value["position_milli"], "$.character.position_milli"),
            _enum(value["facing"], FACINGS, "$.character.facing"),
            _id(value["gaze"], "$.character.gaze"),
            _id(value["expression"], "$.character.expression"),
            _id(value["world_state"], "$.character.world_state"),
            recent,
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "character_id": self.character_id,
            "package_digest": self.package_digest,
            "manifest_digest": self.manifest_digest,
            "runtime_api_version": self.runtime_api_version,
            "current_pose_id": self.current_pose_id,
            "current_action_id": self.current_action_id,
            "position_milli": dict(self.position_milli),
            "facing": self.facing,
            "gaze": self.gaze,
            "expression": self.expression,
            "world_state": self.world_state,
            "recent_performance": [item.to_dict() for item in self.recent_performance],
        }


def _box(value: object, path: str, maximum: int) -> Mapping[str, int]:
    raw = _mapping(value, path)
    _exact(raw, ("x", "y", "width", "height"), path)
    result = {
        "x": _integer(raw["x"], path + ".x", 0, maximum),
        "y": _integer(raw["y"], path + ".y", 0, maximum),
        "width": _integer(raw["width"], path + ".width", 0, maximum),
        "height": _integer(raw["height"], path + ".height", 0, maximum),
    }
    if result["x"] + result["width"] > maximum or result["y"] + result["height"] > maximum:
        raise PerformanceContextError("range_invalid", "box exceeds normalized bounds", path)
    return MappingProxyType(result)


def _insets(value: object, path: str) -> Mapping[str, int]:
    raw = _mapping(value, path)
    _exact(raw, ("top", "right", "bottom", "left"), path)
    return MappingProxyType({key: _integer(raw[key], path + "." + key) for key in ("top", "right", "bottom", "left")})


@dataclass(frozen=True)
class DisplayContextV1:
    width_px: int
    height_px: int
    scale_factor_milli: int
    orientation: str
    safe_area_px: Mapping[str, int]
    caption_area_milli: Mapping[str, int]
    stage_bounds_milli: Mapping[str, int]

    @classmethod
    def from_mapping(cls, raw: object) -> "DisplayContextV1":
        value = _mapping(raw, "$.display")
        fields = ("width_px", "height_px", "scale_factor_milli", "orientation", "safe_area_px", "caption_area_milli", "stage_bounds_milli")
        _exact(value, fields, "$.display")
        width = _integer(value["width_px"], "$.display.width_px", 1)
        height = _integer(value["height_px"], "$.display.height_px", 1)
        safe = _insets(value["safe_area_px"], "$.display.safe_area_px")
        if safe["left"] + safe["right"] >= width or safe["top"] + safe["bottom"] >= height:
            raise PerformanceContextError("range_invalid", "safe area leaves no display region", "$.display.safe_area_px")
        return cls(
            width,
            height,
            _integer(value["scale_factor_milli"], "$.display.scale_factor_milli", 1, 16_000),
            _enum(value["orientation"], ORIENTATIONS, "$.display.orientation"),
            safe,
            _box(value["caption_area_milli"], "$.display.caption_area_milli", 1_000),
            _box(value["stage_bounds_milli"], "$.display.stage_bounds_milli", 1_000),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "width_px": self.width_px,
            "height_px": self.height_px,
            "scale_factor_milli": self.scale_factor_milli,
            "orientation": self.orientation,
            "safe_area_px": dict(self.safe_area_px),
            "caption_area_milli": dict(self.caption_area_milli),
            "stage_bounds_milli": dict(self.stage_bounds_milli),
        }


@dataclass(frozen=True)
class GovernanceContextV1:
    allowed_semantic_actions: Tuple[str, ...]
    denied_semantic_actions: Tuple[str, ...]
    pending_approval_references: Tuple[str, ...]
    memory_scope: str
    external_action_posture: str
    notification_scope: str
    linked_surface_state: str

    @classmethod
    def from_mapping(cls, raw: object) -> "GovernanceContextV1":
        value = _mapping(raw, "$.governance")
        fields = ("allowed_semantic_actions", "denied_semantic_actions", "pending_approval_references", "memory_scope", "external_action_posture", "notification_scope", "linked_surface_state")
        _exact(value, fields, "$.governance")
        allowed = _sorted_unique_ids(value["allowed_semantic_actions"], "$.governance.allowed_semantic_actions", SEMANTIC_INTENTS)
        denied = _sorted_unique_ids(value["denied_semantic_actions"], "$.governance.denied_semantic_actions", SEMANTIC_INTENTS)
        if set(allowed) & set(denied):
            raise PerformanceContextError("invalid_binding", "an action cannot be both allowed and denied", "$.governance")
        return cls(
            allowed,
            denied,
            _sorted_unique_ids(value["pending_approval_references"], "$.governance.pending_approval_references"),
            _enum(value["memory_scope"], MEMORY_SCOPES, "$.governance.memory_scope"),
            _enum(value["external_action_posture"], EXTERNAL_ACTION_POSTURES, "$.governance.external_action_posture"),
            _enum(value["notification_scope"], NOTIFICATION_SCOPES, "$.governance.notification_scope"),
            _enum(value["linked_surface_state"], LINKED_SURFACE_STATES, "$.governance.linked_surface_state"),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "allowed_semantic_actions": list(self.allowed_semantic_actions),
            "denied_semantic_actions": list(self.denied_semantic_actions),
            "pending_approval_references": list(self.pending_approval_references),
            "memory_scope": self.memory_scope,
            "external_action_posture": self.external_action_posture,
            "notification_scope": self.notification_scope,
            "linked_surface_state": self.linked_surface_state,
        }


@dataclass(frozen=True)
class PreferencesContextV1:
    motion_profile: str
    intensity_band: int
    disabled_channels: Tuple[str, ...]
    caption_mode: str
    progressive_reveal_preference: str
    voice_preference: str

    @classmethod
    def from_mapping(cls, raw: object) -> "PreferencesContextV1":
        value = _mapping(raw, "$.preferences")
        fields = ("motion_profile", "intensity_band", "disabled_channels", "caption_mode", "progressive_reveal_preference", "voice_preference")
        _exact(value, fields, "$.preferences")
        return cls(
            _enum(value["motion_profile"], MOTION_PROFILES, "$.preferences.motion_profile"),
            _integer(value["intensity_band"], "$.preferences.intensity_band", 0, 1_000),
            _sorted_unique_ids(value["disabled_channels"], "$.preferences.disabled_channels", KNOWN_CHANNELS),
            _enum(value["caption_mode"], CAPTION_MODES, "$.preferences.caption_mode"),
            _enum(value["progressive_reveal_preference"], PROGRESSIVE_REVEAL_PREFERENCES, "$.preferences.progressive_reveal_preference"),
            _enum(value["voice_preference"], VOICE_PREFERENCES, "$.preferences.voice_preference"),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "motion_profile": self.motion_profile,
            "intensity_band": self.intensity_band,
            "disabled_channels": list(self.disabled_channels),
            "caption_mode": self.caption_mode,
            "progressive_reveal_preference": self.progressive_reveal_preference,
            "voice_preference": self.voice_preference,
        }


@dataclass(frozen=True)
class ChannelClaimV1:
    channel: str
    owner: str
    lease_id: str
    expires_at_monotonic_ms: int

    @classmethod
    def from_mapping(cls, raw: object, path: str) -> "ChannelClaimV1":
        value = _mapping(raw, path)
        _exact(value, ("channel", "owner", "lease_id", "expires_at_monotonic_ms"), path)
        return cls(
            _enum(value["channel"], KNOWN_CHANNELS, path + ".channel"),
            _enum(value["owner"], CHANNEL_OWNERS, path + ".owner"),
            _id(value["lease_id"], path + ".lease_id"),
            _integer(value["expires_at_monotonic_ms"], path + ".expires_at_monotonic_ms"),
        )

    def to_dict(self) -> Dict[str, object]:
        return dict(vars(self))


@dataclass(frozen=True)
class ControlContextV1:
    user_locomotion_lease_id: Optional[str]
    user_locomotion_lease_expires_at_monotonic_ms: Optional[int]
    manual_override_state: str
    channel_claims: Tuple[ChannelClaimV1, ...]
    cancellation_generation: int

    @classmethod
    def from_mapping(cls, raw: object) -> "ControlContextV1":
        value = _mapping(raw, "$.control")
        fields = ("user_locomotion_lease_id", "user_locomotion_lease_expires_at_monotonic_ms", "manual_override_state", "channel_claims", "cancellation_generation")
        _exact(value, fields, "$.control")
        lease_id = _optional_id(value["user_locomotion_lease_id"], "$.control.user_locomotion_lease_id")
        expiry_raw = value["user_locomotion_lease_expires_at_monotonic_ms"]
        expiry = None if expiry_raw is None else _integer(expiry_raw, "$.control.user_locomotion_lease_expires_at_monotonic_ms")
        if (lease_id is None) != (expiry is None):
            raise PerformanceContextError("invalid_binding", "locomotion lease identity and expiry must be paired", "$.control")
        claims_raw = value["channel_claims"]
        if type(claims_raw) not in (list, tuple) or len(claims_raw) > 64:
            raise PerformanceContextError("invalid_type", "channel claims must be a bounded array", "$.control.channel_claims")
        claims = tuple(ChannelClaimV1.from_mapping(item, "$.control.channel_claims[{}]".format(index)) for index, item in enumerate(claims_raw))
        keys = [(claim.channel, claim.owner, claim.lease_id) for claim in claims]
        if keys != sorted(keys) or len({claim.channel for claim in claims}) != len(claims):
            raise PerformanceContextError("invalid_order", "channel claims must be sorted with one claim per channel", "$.control.channel_claims")
        return cls(
            lease_id,
            expiry,
            _enum(value["manual_override_state"], MANUAL_OVERRIDE_STATES, "$.control.manual_override_state"),
            claims,
            _integer(value["cancellation_generation"], "$.control.cancellation_generation"),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "user_locomotion_lease_id": self.user_locomotion_lease_id,
            "user_locomotion_lease_expires_at_monotonic_ms": self.user_locomotion_lease_expires_at_monotonic_ms,
            "manual_override_state": self.manual_override_state,
            "channel_claims": [item.to_dict() for item in self.channel_claims],
            "cancellation_generation": self.cancellation_generation,
        }


@dataclass(frozen=True)
class SourceCommitV1:
    component: str
    commit: str

    @classmethod
    def from_mapping(cls, raw: object, path: str) -> "SourceCommitV1":
        value = _mapping(raw, path)
        _exact(value, ("component", "commit"), path)
        commit = value["commit"]
        if type(commit) is not str or GIT_COMMIT_PATTERN.fullmatch(commit) is None:
            raise PerformanceContextError("invalid_id", "expected a full lowercase Git commit", path + ".commit")
        return cls(_id(value["component"], path + ".component"), commit)

    def to_dict(self) -> Dict[str, object]:
        return dict(vars(self))


@dataclass(frozen=True)
class SchemaVersionV1:
    schema_id: str
    version: int

    @classmethod
    def from_mapping(cls, raw: object, path: str) -> "SchemaVersionV1":
        value = _mapping(raw, path)
        _exact(value, ("schema_id", "version"), path)
        return cls(_id(value["schema_id"], path + ".schema_id"), _integer(value["version"], path + ".version", 1))

    def to_dict(self) -> Dict[str, object]:
        return dict(vars(self))


@dataclass(frozen=True)
class ScoreBindingV1:
    score_id: Optional[str]
    score_revision: Optional[int]
    score_sha256: Optional[str]

    @classmethod
    def from_mapping(cls, raw: object) -> "ScoreBindingV1":
        value = _mapping(raw, "$.evidence.score_binding")
        _exact(value, ("score_id", "score_revision", "score_sha256"), "$.evidence.score_binding")
        score_id = _optional_id(value["score_id"], "$.evidence.score_binding.score_id")
        revision_raw = value["score_revision"]
        revision = None if revision_raw is None else _integer(revision_raw, "$.evidence.score_binding.score_revision", 1)
        digest = _optional_hash(value["score_sha256"], "$.evidence.score_binding.score_sha256")
        if not ((score_id is None and revision is None and digest is None) or (score_id is not None and revision is not None and digest is not None)):
            raise PerformanceContextError("invalid_binding", "score binding must be complete or empty", "$.evidence.score_binding")
        return cls(score_id, revision, digest)

    def to_dict(self) -> Dict[str, object]:
        return dict(vars(self))


@dataclass(frozen=True)
class EvidenceContextV1:
    ordered_fingerprints: Tuple[str, ...]
    source_commits: Tuple[SourceCommitV1, ...]
    schema_versions: Tuple[SchemaVersionV1, ...]
    score_binding: ScoreBindingV1
    package_digest: str

    @classmethod
    def from_mapping(cls, raw: object) -> "EvidenceContextV1":
        value = _mapping(raw, "$.evidence")
        fields = ("ordered_fingerprints", "source_commits", "schema_versions", "score_binding", "package_digest")
        _exact(value, fields, "$.evidence")
        fingerprint_raw = value["ordered_fingerprints"]
        if type(fingerprint_raw) not in (list, tuple) or len(fingerprint_raw) > 256:
            raise PerformanceContextError("invalid_type", "evidence fingerprints must be a bounded array", "$.evidence.ordered_fingerprints")
        fingerprints = tuple(_hash(item, "$.evidence.ordered_fingerprints[{}]".format(index)) for index, item in enumerate(fingerprint_raw))
        if len(fingerprints) != len(set(fingerprints)):
            raise PerformanceContextError("duplicate_id", "evidence fingerprints must be unique", "$.evidence.ordered_fingerprints")

        commits_raw = value["source_commits"]
        if type(commits_raw) not in (list, tuple) or len(commits_raw) > 32:
            raise PerformanceContextError("invalid_type", "source commits must be a bounded array", "$.evidence.source_commits")
        commits = tuple(SourceCommitV1.from_mapping(item, "$.evidence.source_commits[{}]".format(index)) for index, item in enumerate(commits_raw))
        if [item.component for item in commits] != sorted(item.component for item in commits) or len({item.component for item in commits}) != len(commits):
            raise PerformanceContextError("invalid_order", "source commits must be sorted and unique by component", "$.evidence.source_commits")

        versions_raw = value["schema_versions"]
        if type(versions_raw) not in (list, tuple) or len(versions_raw) > 64:
            raise PerformanceContextError("invalid_type", "schema versions must be a bounded array", "$.evidence.schema_versions")
        versions = tuple(SchemaVersionV1.from_mapping(item, "$.evidence.schema_versions[{}]".format(index)) for index, item in enumerate(versions_raw))
        if [item.schema_id for item in versions] != sorted(item.schema_id for item in versions) or len({item.schema_id for item in versions}) != len(versions):
            raise PerformanceContextError("invalid_order", "schema versions must be sorted and unique by schema ID", "$.evidence.schema_versions")
        return cls(
            fingerprints,
            commits,
            versions,
            ScoreBindingV1.from_mapping(value["score_binding"]),
            _hash(value["package_digest"], "$.evidence.package_digest"),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "ordered_fingerprints": list(self.ordered_fingerprints),
            "source_commits": [item.to_dict() for item in self.source_commits],
            "schema_versions": [item.to_dict() for item in self.schema_versions],
            "score_binding": self.score_binding.to_dict(),
            "package_digest": self.package_digest,
        }


@dataclass(frozen=True)
class PerformanceContextV1:
    schema_version: int
    runtime: RuntimeContextV1
    source: SourceContextV1
    clock: ClockContextV1
    conversation: ConversationContextV1
    pipeline: PipelineContextV1
    approval: ApprovalContextV1
    character: CharacterContextV1
    display: DisplayContextV1
    governance: GovernanceContextV1
    preferences: PreferencesContextV1
    control: ControlContextV1
    evidence: EvidenceContextV1
    context_sha256: str

    @classmethod
    def build(cls, value: Mapping[str, object]) -> "PerformanceContextV1":
        """Validate and hash an unhashed context mapping."""

        _reject_private_content(value)
        _check_json_value(value)
        fields = (
            "schema_version",
            "runtime",
            "source",
            "clock",
            "conversation",
            "pipeline",
            "approval",
            "character",
            "display",
            "governance",
            "preferences",
            "control",
            "evidence",
        )
        _exact(value, fields, "$")
        payload = {key: value[key] for key in fields}
        payload["context_sha256"] = sha256_ref(canonical_json_v1(payload))
        return cls.from_mapping(payload)

    @classmethod
    def from_json(cls, source: Union[str, bytes]) -> "PerformanceContextV1":
        return cls.from_mapping(_parse_json(source))

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "PerformanceContextV1":
        value = _mapping(raw, "$")
        _reject_private_content(value)
        _check_json_value(value)
        fields = (
            "schema_version",
            "runtime",
            "source",
            "clock",
            "conversation",
            "pipeline",
            "approval",
            "character",
            "display",
            "governance",
            "preferences",
            "control",
            "evidence",
            "context_sha256",
        )
        _exact(value, fields, "$")
        if type(value["schema_version"]) is not int:
            raise PerformanceContextError("invalid_type", "schema version must be an integer", "$.schema_version")
        if value["schema_version"] != PERFORMANCE_CONTEXT_SCHEMA_VERSION:
            raise PerformanceContextError("schema_version_unsupported", "performance context schema must be version 1", "$.schema_version")
        context = cls(
            PERFORMANCE_CONTEXT_SCHEMA_VERSION,
            RuntimeContextV1.from_mapping(value["runtime"]),
            SourceContextV1.from_mapping(value["source"]),
            ClockContextV1.from_mapping(value["clock"]),
            ConversationContextV1.from_mapping(value["conversation"]),
            PipelineContextV1.from_mapping(value["pipeline"]),
            ApprovalContextV1.from_mapping(value["approval"]),
            CharacterContextV1.from_mapping(value["character"]),
            DisplayContextV1.from_mapping(value["display"]),
            GovernanceContextV1.from_mapping(value["governance"]),
            PreferencesContextV1.from_mapping(value["preferences"]),
            ControlContextV1.from_mapping(value["control"]),
            EvidenceContextV1.from_mapping(value["evidence"]),
            _hash(value["context_sha256"], "$.context_sha256"),
        )
        if context.evidence.package_digest != context.character.package_digest:
            raise PerformanceContextError("invalid_binding", "evidence package does not match character package", "$.evidence.package_digest")
        if context.context_sha256 != context.content_sha256():
            raise PerformanceContextError("hash_mismatch", "context SHA-256 does not match canonical content", "$.context_sha256")
        return context

    def content_dict(self) -> Dict[str, object]:
        value = self.to_dict()
        value.pop("context_sha256")
        return value

    def content_sha256(self) -> str:
        return sha256_ref(canonical_json_v1(self.content_dict()))

    def canonical_json(self) -> bytes:
        return canonical_json_v1(self.to_dict())

    def validate_binding(self, current: "PerformanceContextBindingsV1") -> None:
        """Reject a compiler result after any authority-bearing binding changes."""

        validate_performance_context_bindings(self, current)

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "runtime": self.runtime.to_dict(),
            "source": self.source.to_dict(),
            "clock": self.clock.to_dict(),
            "conversation": self.conversation.to_dict(),
            "pipeline": self.pipeline.to_dict(),
            "approval": self.approval.to_dict(),
            "character": self.character.to_dict(),
            "display": self.display.to_dict(),
            "governance": self.governance.to_dict(),
            "preferences": self.preferences.to_dict(),
            "control": self.control.to_dict(),
            "evidence": self.evidence.to_dict(),
            "context_sha256": self.context_sha256,
        }


@dataclass(frozen=True)
class PerformanceContextBindingsV1:
    """Bindings that must still match immediately before result application."""

    context_sha256: str
    wizard_runtime_epoch: str
    connector_session_id: str
    accepted_sequence: int
    media_epoch: int
    media_id: str
    media_sha256: Optional[str]
    source_slot: str
    source_epoch: str
    turn_id: Optional[str]
    utterance_id: Optional[str]
    character_id: str
    package_digest: str
    reconciliation_generation: int
    score_sha256: Optional[str]
    cancellation_generation: int

    @classmethod
    def from_context(cls, context: PerformanceContextV1) -> "PerformanceContextBindingsV1":
        return cls(
            context.context_sha256,
            context.runtime.wizard_runtime_epoch,
            context.source.connector_session_id,
            context.source.accepted_sequence,
            context.source.media_epoch,
            context.source.media_id,
            context.source.media_sha256,
            context.source.source_slot,
            context.source.source_epoch,
            context.source.turn_id,
            context.source.utterance_id,
            context.character.character_id,
            context.character.package_digest,
            context.runtime.reconciliation_generation,
            context.evidence.score_binding.score_sha256,
            context.control.cancellation_generation,
        )

    def to_dict(self) -> Dict[str, object]:
        return dict(vars(self))


def validate_performance_context_bindings(
    context: PerformanceContextV1,
    expected: PerformanceContextBindingsV1,
) -> None:
    """Raise ``stale_binding`` when accepted authority has moved on."""

    actual = PerformanceContextBindingsV1.from_context(context).to_dict()
    for field, expected_value in expected.to_dict().items():
        if type(actual[field]) is not type(expected_value) or actual[field] != expected_value:
            raise PerformanceContextError(
                "stale_binding",
                "performance context binding no longer matches active authority",
                "$.{}".format(field),
            )


__all__ = [
    "PERFORMANCE_CONTEXT_SCHEMA_VERSION",
    "PerformanceContextBindingsV1",
    "PerformanceContextError",
    "PerformanceContextV1",
    "validate_performance_context_bindings",
]
