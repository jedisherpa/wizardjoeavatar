"""Fail-closed release approval for one Character Director turn."""

from __future__ import annotations

import json
import re
import threading
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Deque, Dict, Optional, Sequence, Tuple, Union

from .artifact_hashing import MAX_SAFE_INTEGER, canonical_json_v1, sha256_ref


GOVERNED_PERFORMANCE_SCHEMA_VERSION = 1
GOVERNED_PERFORMANCE_MAX_BODY_BYTES = 16 * 1024
GOVERNED_PERFORMANCE_MAX_LIFETIME_MS = 5 * 60 * 1000

ALLOWED_SINKS = frozenset({"animation", "speech", "text"})
SPEECH_MEDIA_KINDS = frozenset({"media", "none", "speech"})

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_PRIVATE_KEY_FRAGMENTS = (
    "audio_bytes",
    "content_body",
    "message_body",
    "payload",
    "prompt",
    "raw",
    "reply_text",
    "response_text",
    "snippet",
    "transcript",
)
_KNOWN_FIELDS = frozenset(
    {
        "allowed_sinks",
        "approval_id",
        "approval_sha256",
        "character_id",
        "expires_at_ms",
        "identity",
        "issued_at_ms",
        "kind",
        "package_digest",
        "performance_context_sha256",
        "reconciliation_generation",
        "reply_sha256",
        "revocation_generation",
        "schema_version",
        "sha256",
        "speech_media",
        "turn_id",
    }
)


class GovernedPerformanceError(ValueError):
    """Stable, path-addressed rejection without caller-provided content."""

    def __init__(self, code: str, message: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        self.message = message
        super().__init__("{} at {}: {}".format(code, path, message))


def _error(code: str, message: str, path: str = "$") -> GovernedPerformanceError:
    return GovernedPerformanceError(code, message, path)


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _error("invalid_type", "expected an object", path)
    return value


def _exact(value: Mapping[str, object], fields: Sequence[str], path: str) -> None:
    expected = set(fields)
    if expected - set(value):
        raise _error("missing_field", "object is missing required fields", path)
    if set(value) - expected:
        raise _error("unknown_field", "object contains unknown fields", path)


def _child_path(path: str, key: object) -> str:
    if type(key) is str and key in _KNOWN_FIELDS:
        return "{}.{}".format(path, key)
    return "{}.*".format(path)


def _check_json_value(value: object, path: str = "$") -> None:
    if value is None or type(value) in (str, bool):
        if type(value) is str:
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise _error("invalid_type", "text is not valid UTF-8", path) from exc
        return
    if type(value) is int:
        if value < 0 or value > MAX_SAFE_INTEGER:
            raise _error("invalid_type", "expected a non-negative safe integer", path)
        return
    if isinstance(value, float):
        raise _error(
            "non_integer_identity_value",
            "floating-point values are forbidden",
            path,
        )
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is not str:
                raise _error("invalid_type", "object keys must be strings", path)
            _check_json_value(item, _child_path(path, key))
        return
    if type(value) in (list, tuple):
        for index, item in enumerate(value):
            _check_json_value(item, "{}[{}]".format(path, index))
        return
    raise _error("invalid_type", "unsupported value type", path)


def _reject_private_content(value: object, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(fragment in normalized for fragment in _PRIVATE_KEY_FRAGMENTS):
                raise _error(
                    "private_content",
                    "approval contains a forbidden private-content field",
                    path,
                )
            _reject_private_content(item, _child_path(path, key))
    elif type(value) in (list, tuple):
        for index, item in enumerate(value):
            _reject_private_content(item, "{}[{}]".format(path, index))


def _integer(value: object, path: str) -> int:
    if type(value) is not int or value < 0 or value > MAX_SAFE_INTEGER:
        raise _error("invalid_type", "expected a non-negative safe integer", path)
    return value


def _identifier(value: object, path: str) -> str:
    if type(value) is not str or _ID_PATTERN.fullmatch(value) is None:
        raise _error("invalid_id", "expected a stable content-free identifier", path)
    return value


def _optional_identifier(value: object, path: str) -> Optional[str]:
    return None if value is None else _identifier(value, path)


def _hash(value: object, path: str) -> str:
    if type(value) is not str or _SHA256_PATTERN.fullmatch(value) is None:
        raise _error("invalid_hash", "expected an algorithm-qualified SHA-256", path)
    return value


def _optional_hash(value: object, path: str) -> Optional[str]:
    return None if value is None else _hash(value, path)


def _parse_json(source: Union[str, bytes]) -> Mapping[str, object]:
    if type(source) is bytes:
        if len(source) > GOVERNED_PERFORMANCE_MAX_BODY_BYTES:
            raise _error("body_too_large", "approval exceeds the size limit")
        try:
            text = source.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _error("invalid_json", "approval is not valid UTF-8 JSON") from exc
    elif type(source) is str:
        try:
            size = len(source.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise _error("invalid_json", "approval is not valid UTF-8 JSON") from exc
        if size > GOVERNED_PERFORMANCE_MAX_BODY_BYTES:
            raise _error("body_too_large", "approval exceeds the size limit")
        text = source
    else:
        raise _error("invalid_type", "source must be JSON text or bytes")

    def reject_duplicates(pairs: Sequence[Tuple[str, object]]) -> Dict[str, object]:
        result: Dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                raise _error("duplicate_json_key", "duplicate JSON object key")
            result[key] = item
        return result

    def reject_float(_value: str) -> object:
        raise _error(
            "non_integer_identity_value",
            "floating-point values are forbidden",
        )

    try:
        parsed = json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_float=reject_float,
            parse_constant=reject_float,
        )
    except GovernedPerformanceError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise _error("invalid_json", "approval is not valid JSON") from exc
    return _mapping(parsed, "$")


@dataclass(frozen=True)
class SpeechMediaBindingV1:
    """Content-free identity of speech bytes or an existing media object."""

    kind: str
    identity: Optional[str]
    sha256: Optional[str]

    @classmethod
    def from_mapping(cls, raw: object) -> "SpeechMediaBindingV1":
        value = _mapping(raw, "$.speech_media")
        _exact(value, ("kind", "identity", "sha256"), "$.speech_media")
        kind = value["kind"]
        if type(kind) is not str or kind not in SPEECH_MEDIA_KINDS:
            raise _error("invalid_speech_media", "unsupported speech/media kind", "$.speech_media.kind")
        binding = cls(
            kind,
            _optional_identifier(value["identity"], "$.speech_media.identity"),
            _optional_hash(value["sha256"], "$.speech_media.sha256"),
        )
        if binding.kind == "none" and (binding.identity is not None or binding.sha256 is not None):
            raise _error(
                "invalid_speech_media",
                "none binding cannot carry speech/media identity",
                "$.speech_media",
            )
        if binding.kind != "none" and binding.identity is None and binding.sha256 is None:
            raise _error(
                "missing_speech_media_binding",
                "speech/media binding requires a digest or identity",
                "$.speech_media",
            )
        return binding

    def to_dict(self) -> Dict[str, object]:
        return {"kind": self.kind, "identity": self.identity, "sha256": self.sha256}


@dataclass(frozen=True)
class GovernedPerformanceApprovalV1:
    """Hash-sealed authority to release one turn to named presentation sinks."""

    schema_version: int
    approval_id: str
    turn_id: str
    reply_sha256: str
    speech_media: SpeechMediaBindingV1
    performance_context_sha256: str
    character_id: str
    package_digest: str
    allowed_sinks: Tuple[str, ...]
    issued_at_ms: int
    expires_at_ms: int
    revocation_generation: int
    reconciliation_generation: int
    approval_sha256: str

    _CONTENT_FIELDS = (
        "schema_version",
        "approval_id",
        "turn_id",
        "reply_sha256",
        "speech_media",
        "performance_context_sha256",
        "character_id",
        "package_digest",
        "allowed_sinks",
        "issued_at_ms",
        "expires_at_ms",
        "revocation_generation",
        "reconciliation_generation",
    )

    @classmethod
    def build(cls, raw: Mapping[str, object]) -> "GovernedPerformanceApprovalV1":
        value = _mapping(raw, "$")
        _reject_private_content(value)
        _check_json_value(value)
        _exact(value, cls._CONTENT_FIELDS, "$")
        payload = {field: value[field] for field in cls._CONTENT_FIELDS}
        payload["approval_sha256"] = sha256_ref(canonical_json_v1(payload))
        return cls.from_mapping(payload)

    @classmethod
    def from_json(cls, source: Union[str, bytes]) -> "GovernedPerformanceApprovalV1":
        return cls.from_mapping(_parse_json(source))

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "GovernedPerformanceApprovalV1":
        value = _mapping(raw, "$")
        _reject_private_content(value)
        _check_json_value(value)
        _exact(value, cls._CONTENT_FIELDS + ("approval_sha256",), "$")

        version = value["schema_version"]
        if type(version) is not int:
            raise _error("invalid_type", "schema version must be an integer", "$.schema_version")
        if version != GOVERNED_PERFORMANCE_SCHEMA_VERSION:
            raise _error(
                "schema_version_unsupported",
                "governed performance approval must be version 1",
                "$.schema_version",
            )

        sinks_raw = value["allowed_sinks"]
        if type(sinks_raw) not in (list, tuple):
            raise _error("invalid_type", "allowed sinks must be an array", "$.allowed_sinks")
        sinks = tuple(sinks_raw)
        if not sinks:
            raise _error("missing_sink", "approval must name at least one sink", "$.allowed_sinks")
        if any(type(sink) is not str or sink not in ALLOWED_SINKS for sink in sinks):
            raise _error("invalid_sink", "approval contains an unsupported sink", "$.allowed_sinks")
        if list(sinks) != sorted(sinks) or len(sinks) != len(set(sinks)):
            raise _error("invalid_order", "allowed sinks must be sorted and unique", "$.allowed_sinks")

        approval = cls(
            GOVERNED_PERFORMANCE_SCHEMA_VERSION,
            _identifier(value["approval_id"], "$.approval_id"),
            _identifier(value["turn_id"], "$.turn_id"),
            _hash(value["reply_sha256"], "$.reply_sha256"),
            SpeechMediaBindingV1.from_mapping(value["speech_media"]),
            _hash(value["performance_context_sha256"], "$.performance_context_sha256"),
            _identifier(value["character_id"], "$.character_id"),
            _hash(value["package_digest"], "$.package_digest"),
            sinks,
            _integer(value["issued_at_ms"], "$.issued_at_ms"),
            _integer(value["expires_at_ms"], "$.expires_at_ms"),
            _integer(value["revocation_generation"], "$.revocation_generation"),
            _integer(value["reconciliation_generation"], "$.reconciliation_generation"),
            _hash(value["approval_sha256"], "$.approval_sha256"),
        )
        approval._validate_semantics()
        if approval.approval_sha256 != approval.computed_approval_sha256():
            raise _error("hash_mismatch", "approval hash does not match canonical content", "$.approval_sha256")
        return approval

    def _validate_semantics(self) -> None:
        if self.expires_at_ms <= self.issued_at_ms:
            raise _error("invalid_time_window", "expiry must follow issuance", "$.expires_at_ms")
        if self.expires_at_ms - self.issued_at_ms > GOVERNED_PERFORMANCE_MAX_LIFETIME_MS:
            raise _error(
                "approval_lifetime_exceeded",
                "approval lifetime exceeds the V1 bound",
                "$.expires_at_ms",
            )
        if "speech" in self.allowed_sinks and self.speech_media.kind == "none":
            raise _error(
                "missing_speech_media_binding",
                "speech sink requires a speech/media binding",
                "$.speech_media",
            )

    def content_dict(self) -> Dict[str, object]:
        value = self.to_dict()
        value.pop("approval_sha256")
        return value

    def computed_approval_sha256(self) -> str:
        return sha256_ref(canonical_json_v1(self.content_dict()))

    def canonical_json(self) -> bytes:
        return canonical_json_v1(self.to_dict())

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "approval_id": self.approval_id,
            "turn_id": self.turn_id,
            "reply_sha256": self.reply_sha256,
            "speech_media": self.speech_media.to_dict(),
            "performance_context_sha256": self.performance_context_sha256,
            "character_id": self.character_id,
            "package_digest": self.package_digest,
            "allowed_sinks": list(self.allowed_sinks),
            "issued_at_ms": self.issued_at_ms,
            "expires_at_ms": self.expires_at_ms,
            "revocation_generation": self.revocation_generation,
            "reconciliation_generation": self.reconciliation_generation,
            "approval_sha256": self.approval_sha256,
        }


@dataclass(frozen=True)
class GovernedPerformanceBindingsV1:
    """Authority-bearing values observed immediately before release."""

    turn_id: str
    reply_sha256: str
    speech_media: SpeechMediaBindingV1
    performance_context_sha256: str
    character_id: str
    package_digest: str
    revocation_generation: int
    reconciliation_generation: int

    @classmethod
    def from_approval(
        cls, approval: GovernedPerformanceApprovalV1
    ) -> "GovernedPerformanceBindingsV1":
        return cls(
            approval.turn_id,
            approval.reply_sha256,
            approval.speech_media,
            approval.performance_context_sha256,
            approval.character_id,
            approval.package_digest,
            approval.revocation_generation,
            approval.reconciliation_generation,
        )


@dataclass(frozen=True)
class GovernedPerformanceEventV1:
    sequence: int
    outcome: str
    code: str
    approval_sha256: Optional[str]
    sink: Optional[str]
    observed_at_ms: int


@dataclass(frozen=True)
class GovernedReleaseV1:
    approval_id: str
    approval_sha256: str
    turn_id: str
    sink: str


@dataclass
class _ReplayRecord:
    approval_sha256: str
    expires_at_ms: int
    consumed_sinks: set


class GovernedPerformanceGate:
    """Atomically validate and consume each approved sink at most once.

    Replay records remain until their approval expires. If the bounded replay
    table fills before entries expire, new approvals fail closed.
    """

    def __init__(self, max_replay_approvals: int = 1024, max_events: int = 256) -> None:
        for name, value in (
            ("max_replay_approvals", max_replay_approvals),
            ("max_events", max_events),
        ):
            if type(value) is not int or value <= 0:
                raise ValueError("{} must be a positive integer".format(name))
        self.max_replay_approvals = max_replay_approvals
        self.max_events = max_events
        self._replay: Dict[str, _ReplayRecord] = {}
        self._events: Deque[GovernedPerformanceEventV1] = deque(maxlen=max_events)
        self._event_sequence = 0
        self._evicted_event_count = 0
        self._lock = threading.Lock()

    def authorize(
        self,
        approval: GovernedPerformanceApprovalV1,
        sink: object,
        current: GovernedPerformanceBindingsV1,
        now_ms: object,
    ) -> GovernedReleaseV1:
        """Return content-free release authority or raise a stable rejection."""

        with self._lock:
            approval_hash = None
            if (
                isinstance(approval, GovernedPerformanceApprovalV1)
                and type(approval.approval_sha256) is str
                and _SHA256_PATTERN.fullmatch(approval.approval_sha256) is not None
            ):
                approval_hash = approval.approval_sha256
            event_sink = sink if type(sink) is str and sink in ALLOWED_SINKS else None
            observed_at = now_ms if type(now_ms) is int and now_ms >= 0 else 0
            try:
                result = self._authorize_locked(approval, sink, current, now_ms)
            except GovernedPerformanceError as exc:
                self._record_event("denied", exc.code, approval_hash, event_sink, observed_at)
                raise
            self._record_event("allowed", "release_allowed", approval_hash, result.sink, observed_at)
            return result

    def authorize_many(
        self,
        approval: GovernedPerformanceApprovalV1,
        sinks: Sequence[str],
        current: GovernedPerformanceBindingsV1,
        now_ms: object,
    ) -> Tuple[GovernedReleaseV1, ...]:
        """Atomically consume a sorted, unique set of approved sinks."""

        with self._lock:
            approval_hash = (
                approval.approval_sha256
                if isinstance(approval, GovernedPerformanceApprovalV1)
                else None
            )
            observed_at = now_ms if type(now_ms) is int and now_ms >= 0 else 0
            try:
                if type(sinks) not in (list, tuple) or not sinks:
                    raise _error("missing_sink", "at least one release sink is required", "$.sinks")
                requested = tuple(sinks)
                if requested != tuple(sorted(set(requested))):
                    raise _error(
                        "invalid_order",
                        "release sinks must be sorted and unique",
                        "$.sinks",
                    )
                if any(type(sink) is not str or sink not in ALLOWED_SINKS for sink in requested):
                    raise _error("invalid_sink", "release sink is unsupported", "$.sinks")

                validated = GovernedPerformanceApprovalV1.from_mapping(approval.to_dict())
                now = _integer(now_ms, "$.now_ms")
                if now < validated.issued_at_ms:
                    raise _error(
                        "approval_not_yet_valid",
                        "approval issuance is in the future",
                        "$.issued_at_ms",
                    )
                if now >= validated.expires_at_ms:
                    raise _error("approval_expired", "approval has expired", "$.expires_at_ms")
                missing = [sink for sink in requested if sink not in validated.allowed_sinks]
                if missing:
                    raise _error(
                        "sink_not_approved",
                        "release sink is not approved",
                        "$.sinks",
                    )
                self._validate_bindings(validated, current)
                self._prune_expired(now)
                record = self._replay.get(validated.approval_id)
                if record is None:
                    if len(self._replay) >= self.max_replay_approvals:
                        raise _error(
                            "replay_capacity_exceeded",
                            "replay protection capacity is exhausted",
                        )
                else:
                    if record.approval_sha256 != validated.approval_sha256:
                        raise _error(
                            "replay_conflict",
                            "approval identifier was already bound to other authority",
                        )
                    if any(sink in record.consumed_sinks for sink in requested):
                        raise _error(
                            "replay_detected",
                            "approved sink was already consumed",
                            "$.sinks",
                        )

                if record is None:
                    record = _ReplayRecord(
                        validated.approval_sha256,
                        validated.expires_at_ms,
                        set(),
                    )
                    self._replay[validated.approval_id] = record
                record.consumed_sinks.update(requested)
                releases = tuple(
                    GovernedReleaseV1(
                        validated.approval_id,
                        validated.approval_sha256,
                        validated.turn_id,
                        sink,
                    )
                    for sink in requested
                )
            except GovernedPerformanceError as exc:
                self._record_event("denied", exc.code, approval_hash, None, observed_at)
                raise
            for release in releases:
                self._record_event(
                    "allowed",
                    "release_allowed",
                    release.approval_sha256,
                    release.sink,
                    observed_at,
                )
            return releases

    def _authorize_locked(
        self,
        approval: GovernedPerformanceApprovalV1,
        sink: object,
        current: GovernedPerformanceBindingsV1,
        now_ms: object,
    ) -> GovernedReleaseV1:
        if not isinstance(approval, GovernedPerformanceApprovalV1):
            raise _error("invalid_type", "approval must be a validated V1 envelope")
        if not isinstance(current, GovernedPerformanceBindingsV1):
            raise _error("invalid_type", "current bindings must be GovernedPerformanceBindingsV1")
        approval = GovernedPerformanceApprovalV1.from_mapping(approval.to_dict())
        now = _integer(now_ms, "$.now_ms")
        if sink is None:
            raise _error("missing_sink", "release sink is required", "$.sink")
        if type(sink) is not str or sink not in ALLOWED_SINKS:
            raise _error("invalid_sink", "release sink is unsupported", "$.sink")
        if sink not in approval.allowed_sinks:
            raise _error("sink_not_approved", "release sink is not approved", "$.sink")
        if now < approval.issued_at_ms:
            raise _error("approval_not_yet_valid", "approval issuance is in the future", "$.issued_at_ms")
        if now >= approval.expires_at_ms:
            raise _error("approval_expired", "approval has expired", "$.expires_at_ms")

        self._validate_bindings(approval, current)
        self._prune_expired(now)
        record = self._replay.get(approval.approval_id)
        if record is None:
            if len(self._replay) >= self.max_replay_approvals:
                raise _error("replay_capacity_exceeded", "replay protection capacity is exhausted")
            record = _ReplayRecord(approval.approval_sha256, approval.expires_at_ms, set())
            self._replay[approval.approval_id] = record
        elif record.approval_sha256 != approval.approval_sha256:
            raise _error("replay_conflict", "approval identifier was already bound to other authority")
        if sink in record.consumed_sinks:
            raise _error("replay_detected", "approved sink was already consumed", "$.sink")
        record.consumed_sinks.add(sink)
        return GovernedReleaseV1(
            approval.approval_id,
            approval.approval_sha256,
            approval.turn_id,
            sink,
        )

    @staticmethod
    def _validate_bindings(
        approval: GovernedPerformanceApprovalV1,
        current: GovernedPerformanceBindingsV1,
    ) -> None:
        checks = (
            ("turn_id", "turn_mismatch", "$.turn_id"),
            ("reply_sha256", "content_mismatch", "$.reply_sha256"),
            ("speech_media", "speech_media_mismatch", "$.speech_media"),
            ("performance_context_sha256", "context_mismatch", "$.performance_context_sha256"),
            ("character_id", "character_mismatch", "$.character_id"),
            ("package_digest", "package_mismatch", "$.package_digest"),
            (
                "reconciliation_generation",
                "reconciliation_generation_mismatch",
                "$.reconciliation_generation",
            ),
        )
        for field, code, path in checks:
            actual = getattr(approval, field)
            expected = getattr(current, field)
            if type(actual) is not type(expected) or actual != expected:
                raise _error(code, "active release binding no longer matches approval", path)

        current_revocation = _integer(current.revocation_generation, "$.revocation_generation")
        if current_revocation > approval.revocation_generation:
            raise _error("approval_revoked", "approval revocation generation is stale", "$.revocation_generation")
        if current_revocation < approval.revocation_generation:
            raise _error(
                "revocation_generation_mismatch",
                "approval revocation generation is not current",
                "$.revocation_generation",
            )

    def _prune_expired(self, now_ms: int) -> None:
        expired = [
            approval_id
            for approval_id, record in self._replay.items()
            if record.expires_at_ms <= now_ms
        ]
        for approval_id in expired:
            del self._replay[approval_id]

    def _record_event(
        self,
        outcome: str,
        code: str,
        approval_sha256: Optional[str],
        sink: Optional[str],
        observed_at_ms: int,
    ) -> None:
        if len(self._events) == self.max_events:
            self._evicted_event_count += 1
        self._events.append(
            GovernedPerformanceEventV1(
                self._event_sequence,
                outcome,
                code,
                approval_sha256,
                sink,
                observed_at_ms,
            )
        )
        self._event_sequence += 1

    @property
    def events(self) -> Tuple[GovernedPerformanceEventV1, ...]:
        with self._lock:
            return tuple(self._events)

    @property
    def replay_approval_count(self) -> int:
        with self._lock:
            return len(self._replay)

    @property
    def total_event_count(self) -> int:
        with self._lock:
            return self._event_sequence

    @property
    def evicted_event_count(self) -> int:
        with self._lock:
            return self._evicted_event_count


def validate_governed_performance_approval(
    value: Union[Mapping[str, object], str, bytes]
) -> GovernedPerformanceApprovalV1:
    """Validate a mapping or JSON boundary and return the immutable V1 value."""

    if type(value) in (str, bytes):
        return GovernedPerformanceApprovalV1.from_json(value)
    return GovernedPerformanceApprovalV1.from_mapping(value)


__all__ = [
    "ALLOWED_SINKS",
    "GOVERNED_PERFORMANCE_MAX_BODY_BYTES",
    "GOVERNED_PERFORMANCE_MAX_LIFETIME_MS",
    "GOVERNED_PERFORMANCE_SCHEMA_VERSION",
    "GovernedPerformanceApprovalV1",
    "GovernedPerformanceBindingsV1",
    "GovernedPerformanceError",
    "GovernedPerformanceEventV1",
    "GovernedPerformanceGate",
    "GovernedReleaseV1",
    "SpeechMediaBindingV1",
    "validate_governed_performance_approval",
]
