from __future__ import annotations

import json
import re
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from types import MappingProxyType
from typing import AbstractSet, Dict, Mapping, Optional, Sequence, Set, Union


PRISM_SIGNAL_SCHEMA_VERSION = 2
PRISM_LEGACY_SIGNAL_SCHEMA_VERSION = 1
PRISM_SANITIZATION_VERSION = 1
VISUAL_ADVISORY_CLASSIFICATION = "visual_advisory_only"
MAX_TTL_MS = 300_000
MAX_FUTURE_SKEW_MS = 5_000
MAX_SEEN_EVENT_IDS = 4_096
MAX_SAFE_INTEGER = 9_007_199_254_740_991
MAX_SIGNAL_JSON_BYTES = 65_536

TERMINAL_STAGE_STATUSES = frozenset({"completed", "cancelled", "failed"})

PRISM_SIGNAL_KINDS = frozenset(
    {
        "stage",
        "terminal_posture",
        "persona_style",
        "recall_summary",
        "retrieval_summary",
        "approval_posture",
        "continuity",
        "topic_shift",
        "health",
    }
)

PROVENANCE_CLASSES = frozenset(
    {
        "runtime_lifecycle",
        "governance_projection",
        "sanitized_aggregate",
        "runtime_health",
        "authored_profile",
    }
)

_STAGES = frozenset(
    {
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

_ENUM_FIELDS = {
    "stage": _STAGES,
    "status": frozenset({"started", "active", "completed", "cancelled", "failed"}),
    "posture": frozenset(
        {"ready", "settled", "needs_clarification", "waiting", "degraded"}
    ),
    "confidence_bucket": frozenset({"unknown", "low", "medium", "high"}),
    "style": frozenset({"warm", "playful", "focused", "measured", "direct", "reflective"}),
    "selected_count_bucket": frozenset({"0", "1", "2_plus"}),
    "result_count_bucket": frozenset({"0", "1", "2_plus"}),
    "approval_state": frozenset(
        {"pending", "approved", "denied", "stale", "failed", "not_required"}
    ),
    "continuity_state": frozenset({"continued", "restored", "reset", "new_topic"}),
    "age_bucket": frozenset({"unknown", "new", "recent", "established"}),
    "cause": frozenset({"explicit", "semantic", "unknown"}),
    "health_state": frozenset({"healthy", "degraded", "unavailable"}),
}

_PAYLOAD_RULES = {
    "stage": ({"stage", "status"}, {"stage", "status"}),
    "terminal_posture": (
        {"posture"},
        {"posture", "confidence_bucket", "serious_mode"},
    ),
    "persona_style": ({"style"}, {"style"}),
    "recall_summary": (
        {"selected_count_bucket"},
        {
            "selected_count_bucket",
            "selected_count",
            "memory_selected",
            "backstory_selected",
            "degraded",
        },
    ),
    "retrieval_summary": (
        {"result_count_bucket"},
        {"result_count_bucket", "result_count", "occurred", "degraded"},
    ),
    "approval_posture": ({"approval_state"}, {"approval_state"}),
    "continuity": (
        {"continuity_state"},
        {
            "continuity_state",
            "age_bucket",
            "present",
            "ledger_valid",
            "pending_approval_count",
            "recent_turns_count",
        },
    ),
    "topic_shift": ({"changed", "cause"}, {"changed", "cause"}),
    "health": (
        {"health_state"},
        {"health_state", "audit_healthy", "signal_age_ms"},
    ),
}

_BOOLEAN_FIELDS = frozenset(
    {
        "serious_mode",
        "memory_selected",
        "backstory_selected",
        "degraded",
        "occurred",
        "present",
        "ledger_valid",
        "changed",
        "audit_healthy",
    }
)

_COUNTER_MAXIMUMS = {
    "selected_count": 1_000,
    "result_count": 10_000,
    "pending_approval_count": 1_000,
    "recent_turns_count": 1_000_000,
    "signal_age_ms": MAX_TTL_MS,
}

_V1_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "event_id",
        "source_epoch",
        "source_sequence",
        "emitted_at_ms",
        "ttl_ms",
        "kind",
        "classification",
        "provenance_class",
        "sanitization_version",
        "payload",
    }
)

_V2_REQUIRED_TOP_LEVEL_FIELDS = _V1_TOP_LEVEL_FIELDS | {"turn_id"}
_V2_TOP_LEVEL_FIELDS = _V2_REQUIRED_TOP_LEVEL_FIELDS | {"utterance_id"}

_FORBIDDEN_KEY_FRAGMENTS = (
    "prompt",
    "reply",
    "message",
    "content",
    "snippet",
    "memory_body",
    "backstory_body",
    "retrieved_text",
    "embedding",
    "vector",
    "source_id",
    "user_id",
    "rationale",
    "approval_payload",
    "provider",
    "model",
    "route",
    "path",
    "hash",
    "secret",
    "authority",
    "command",
    "execute",
    "locomotion",
    "movement",
    "position",
    "velocity",
    "destination",
    "world_target",
)

_OPAQUE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
_OPAQUE_CONTEXT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class PrismSignalValidationError(ValueError):
    """Raised when a Prism visual advisory fails closed validation."""


JsonInput = Union[str, bytes, bytearray]


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_int(name: str, value: object, minimum: int, maximum: int) -> int:
    if not _is_int(value):
        raise PrismSignalValidationError("{} must be an integer".format(name))
    result = int(value)
    if not minimum <= result <= maximum:
        raise PrismSignalValidationError(
            "{} must be in [{}, {}]".format(name, minimum, maximum)
        )
    return result


def _require_exact_enum(
    name: str, value: object, allowed: AbstractSet[str]
) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise PrismSignalValidationError("unsupported {}: {!r}".format(name, value))
    return value


def _reject_duplicate_pairs(pairs: Sequence[object]) -> Dict[str, object]:
    value: Dict[str, object] = {}
    for pair in pairs:
        key, item = pair  # type: ignore[misc]
        if key in value:
            raise PrismSignalValidationError(
                "duplicate JSON object field: {}".format(key)
            )
        value[key] = item
    return value


def _reject_json_float(_value: str) -> object:
    raise PrismSignalValidationError("floating-point JSON numbers are not allowed")


def _reject_json_constant(value: str) -> object:
    raise PrismSignalValidationError(
        "non-finite JSON constant is not allowed: {}".format(value)
    )


def _load_exact_json(value: JsonInput) -> Mapping[str, object]:
    if not isinstance(value, (str, bytes, bytearray)):
        raise PrismSignalValidationError("Prism signal JSON must be text or bytes")
    byte_length = len(value.encode("utf-8")) if isinstance(value, str) else len(value)
    if byte_length > MAX_SIGNAL_JSON_BYTES:
        raise PrismSignalValidationError("Prism signal JSON exceeds the size limit")
    try:
        decoded = json.loads(
            value,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_float=_reject_json_float,
            parse_constant=_reject_json_constant,
        )
    except PrismSignalValidationError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as error:
        raise PrismSignalValidationError("invalid Prism signal JSON") from error
    if not isinstance(decoded, Mapping):
        raise PrismSignalValidationError("Prism signal JSON must contain one object")
    return decoded


def _reject_forbidden_keys(value: Mapping[str, object], path: str = "$") -> None:
    for key, item in value.items():
        if not isinstance(key, str):
            raise PrismSignalValidationError("{} keys must be strings".format(path))
        normalized = key.lower().replace("-", "_")
        if any(fragment in normalized for fragment in _FORBIDDEN_KEY_FRAGMENTS):
            raise PrismSignalValidationError(
                "forbidden Prism field at {}.{}".format(path, key)
            )
        if isinstance(item, Mapping):
            _reject_forbidden_keys(item, "{}.{}".format(path, key))
        elif isinstance(item, (list, tuple, set, frozenset)):
            raise PrismSignalValidationError(
                "collections are not allowed at {}.{}".format(path, key)
            )


def _validate_event_id(value: object) -> str:
    if not isinstance(value, str):
        raise PrismSignalValidationError("event_id must be a canonical UUID")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise PrismSignalValidationError("event_id must be a canonical UUID")
    if str(parsed) != value:
        raise PrismSignalValidationError("event_id must be a canonical lowercase UUID")
    if parsed.version not in (1, 2, 3, 4, 5) or parsed.variant != uuid.RFC_4122:
        raise PrismSignalValidationError("event_id must be an RFC 4122 UUID")
    return value


def _validate_epoch(value: object) -> str:
    if not isinstance(value, str) or _OPAQUE_TOKEN.fullmatch(value) is None:
        raise PrismSignalValidationError("source_epoch must be an opaque ASCII token")
    return value


def _validate_context_id(name: str, value: object) -> str:
    if not isinstance(value, str) or _OPAQUE_CONTEXT_ID.fullmatch(value) is None:
        raise PrismSignalValidationError(
            "{} must be an opaque ASCII token of at most 128 bytes".format(name)
        )
    return value


def _validate_payload(kind: str, value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PrismSignalValidationError("payload must be an object")
    _reject_forbidden_keys(value, "$.payload")
    required, allowed = _PAYLOAD_RULES[kind]
    keys = set(value)
    unknown = sorted(keys - allowed)
    missing = sorted(required - keys)
    if unknown:
        raise PrismSignalValidationError(
            "unknown {} payload fields: {}".format(kind, ", ".join(unknown))
        )
    if missing:
        raise PrismSignalValidationError(
            "missing {} payload fields: {}".format(kind, ", ".join(missing))
        )

    validated: Dict[str, object] = {}
    for key, item in value.items():
        if key in _ENUM_FIELDS:
            validated[key] = _require_exact_enum(key, item, _ENUM_FIELDS[key])
        elif key in _BOOLEAN_FIELDS:
            if not isinstance(item, bool):
                raise PrismSignalValidationError("payload.{} must be boolean".format(key))
            validated[key] = item
        elif key in _COUNTER_MAXIMUMS:
            validated[key] = _require_int(
                "payload.{}".format(key), item, 0, _COUNTER_MAXIMUMS[key]
            )
        else:
            raise PrismSignalValidationError("unsupported payload field: {}".format(key))

    for count_name, bucket_name in (
        ("selected_count", "selected_count_bucket"),
        ("result_count", "result_count_bucket"),
    ):
        if count_name not in validated:
            continue
        count = int(validated[count_name])
        expected_bucket = "0" if count == 0 else "1" if count == 1 else "2_plus"
        if validated.get(bucket_name) != expected_bucket:
            raise PrismSignalValidationError(
                "payload.{} contradicts payload.{}".format(bucket_name, count_name)
            )
    return MappingProxyType(validated)


@dataclass(frozen=True)
class PrismAnimationSignalV1:
    """Legacy content-free advice without turn correlation."""

    schema_version: int
    event_id: str
    source_epoch: str
    source_sequence: int
    emitted_at_ms: int
    ttl_ms: int
    kind: str
    classification: str
    provenance_class: str
    sanitization_version: int
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        self._validate_common(PRISM_LEGACY_SIGNAL_SCHEMA_VERSION)

    def _validate_common(self, expected_schema_version: int) -> None:
        _require_int(
            "schema_version",
            self.schema_version,
            expected_schema_version,
            expected_schema_version,
        )
        _validate_event_id(self.event_id)
        _validate_epoch(self.source_epoch)
        _require_int("source_sequence", self.source_sequence, 0, MAX_SAFE_INTEGER)
        _require_int("emitted_at_ms", self.emitted_at_ms, 0, MAX_SAFE_INTEGER)
        _require_int("ttl_ms", self.ttl_ms, 1, MAX_TTL_MS)
        if self.emitted_at_ms + self.ttl_ms > MAX_SAFE_INTEGER:
            raise PrismSignalValidationError(
                "emitted_at_ms plus ttl_ms exceeds the safe integer bound"
            )
        _require_exact_enum("kind", self.kind, PRISM_SIGNAL_KINDS)
        if self.classification != VISUAL_ADVISORY_CLASSIFICATION:
            raise PrismSignalValidationError(
                "classification must be visual_advisory_only"
            )
        _require_exact_enum(
            "provenance_class", self.provenance_class, PROVENANCE_CLASSES
        )
        _require_int("sanitization_version", self.sanitization_version, 1, 1)
        object.__setattr__(self, "payload", _validate_payload(self.kind, self.payload))

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "PrismAnimationSignalV1":
        if not isinstance(value, Mapping):
            raise PrismSignalValidationError("Prism signal must be an object")
        _reject_forbidden_keys(value)
        keys = set(value)
        unknown = sorted(keys - _V1_TOP_LEVEL_FIELDS)
        missing = sorted(_V1_TOP_LEVEL_FIELDS - keys)
        if unknown:
            raise PrismSignalValidationError(
                "unknown Prism signal fields: {}".format(", ".join(unknown))
            )
        if missing:
            raise PrismSignalValidationError(
                "missing Prism signal fields: {}".format(", ".join(missing))
            )
        return cls(
            schema_version=value["schema_version"],  # type: ignore[arg-type]
            event_id=value["event_id"],  # type: ignore[arg-type]
            source_epoch=value["source_epoch"],  # type: ignore[arg-type]
            source_sequence=value["source_sequence"],  # type: ignore[arg-type]
            emitted_at_ms=value["emitted_at_ms"],  # type: ignore[arg-type]
            ttl_ms=value["ttl_ms"],  # type: ignore[arg-type]
            kind=value["kind"],  # type: ignore[arg-type]
            classification=value["classification"],  # type: ignore[arg-type]
            provenance_class=value["provenance_class"],  # type: ignore[arg-type]
            sanitization_version=value["sanitization_version"],  # type: ignore[arg-type]
            payload=value["payload"],  # type: ignore[arg-type]
        )

    @classmethod
    def from_json(cls, value: JsonInput) -> "PrismAnimationSignalV1":
        return cls.from_mapping(_load_exact_json(value))

    @property
    def producer_epoch(self) -> str:
        return self.source_epoch

    @property
    def sequence(self) -> int:
        return self.source_sequence

    @property
    def issued_at_ms(self) -> int:
        return self.emitted_at_ms

    @property
    def expires_at_ms(self) -> int:
        return self.emitted_at_ms + self.ttl_ms

    def is_expired(self, now_ms: int) -> bool:
        checked_now = _require_int("now_ms", now_ms, 0, MAX_SAFE_INTEGER)
        return checked_now >= self.expires_at_ms

    @property
    def terminal_stage_status(self) -> Optional[str]:
        if self.kind != "stage":
            return None
        status = self.payload.get("status")
        return str(status) if status in TERMINAL_STAGE_STATUSES else None

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "source_epoch": self.source_epoch,
            "source_sequence": self.source_sequence,
            "emitted_at_ms": self.emitted_at_ms,
            "ttl_ms": self.ttl_ms,
            "kind": self.kind,
            "classification": self.classification,
            "provenance_class": self.provenance_class,
            "sanitization_version": self.sanitization_version,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class PrismAnimationSignalV2(PrismAnimationSignalV1):
    """Turn-correlated, content-free visual advice for governed conversation."""

    turn_id: str
    utterance_id: Optional[str] = None

    def __post_init__(self) -> None:
        self._validate_common(PRISM_SIGNAL_SCHEMA_VERSION)
        _validate_context_id("turn_id", self.turn_id)
        if self.utterance_id is not None:
            _validate_context_id("utterance_id", self.utterance_id)

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "PrismAnimationSignalV2":
        if not isinstance(value, Mapping):
            raise PrismSignalValidationError("Prism signal must be an object")
        _reject_forbidden_keys(value)
        keys = set(value)
        unknown = sorted(keys - _V2_TOP_LEVEL_FIELDS)
        missing = sorted(_V2_REQUIRED_TOP_LEVEL_FIELDS - keys)
        if unknown:
            raise PrismSignalValidationError(
                "unknown Prism signal fields: {}".format(", ".join(unknown))
            )
        if missing:
            raise PrismSignalValidationError(
                "missing Prism signal fields: {}".format(", ".join(missing))
            )
        return cls(
            schema_version=value["schema_version"],  # type: ignore[arg-type]
            event_id=value["event_id"],  # type: ignore[arg-type]
            source_epoch=value["source_epoch"],  # type: ignore[arg-type]
            source_sequence=value["source_sequence"],  # type: ignore[arg-type]
            emitted_at_ms=value["emitted_at_ms"],  # type: ignore[arg-type]
            ttl_ms=value["ttl_ms"],  # type: ignore[arg-type]
            kind=value["kind"],  # type: ignore[arg-type]
            classification=value["classification"],  # type: ignore[arg-type]
            provenance_class=value["provenance_class"],  # type: ignore[arg-type]
            sanitization_version=value["sanitization_version"],  # type: ignore[arg-type]
            payload=value["payload"],  # type: ignore[arg-type]
            turn_id=value["turn_id"],  # type: ignore[arg-type]
            utterance_id=value.get("utterance_id"),  # type: ignore[arg-type]
        )

    @classmethod
    def from_json(cls, value: JsonInput) -> "PrismAnimationSignalV2":
        return cls.from_mapping(_load_exact_json(value))

    def to_dict(self) -> Dict[str, object]:
        value = super().to_dict()
        value["turn_id"] = self.turn_id
        if self.utterance_id is not None:
            value["utterance_id"] = self.utterance_id
        return value


PrismAnimationSignal = Union[PrismAnimationSignalV1, PrismAnimationSignalV2]


def _signal_from_mapping(value: Mapping[str, object]) -> PrismAnimationSignal:
    version = value.get("schema_version") if isinstance(value, Mapping) else None
    if version == PRISM_LEGACY_SIGNAL_SCHEMA_VERSION and not isinstance(version, bool):
        return PrismAnimationSignalV1.from_mapping(value)
    if version == PRISM_SIGNAL_SCHEMA_VERSION and not isinstance(version, bool):
        return PrismAnimationSignalV2.from_mapping(value)
    raise PrismSignalValidationError("unsupported Prism signal schema_version")


def _signal_from_json(value: JsonInput) -> PrismAnimationSignal:
    return _signal_from_mapping(_load_exact_json(value))


def parse_prism_signal_json(value: JsonInput) -> PrismAnimationSignal:
    """Decode one exact V1 or V2 advisory without mutating replay state."""

    return _signal_from_json(value)


class PrismSignalParser:
    """Stateful local validator for freshness, deduplication, and source order.

    The parser deliberately has no URL, socket, stream, callback, command, or
    movement API. A caller may submit already-received mappings and consume the
    resulting visual advisory value.
    """

    def __init__(
        self,
        *,
        max_future_skew_ms: int = MAX_FUTURE_SKEW_MS,
        dedup_capacity: int = MAX_SEEN_EVENT_IDS,
    ) -> None:
        self._max_future_skew_ms = _require_int(
            "max_future_skew_ms", max_future_skew_ms, 0, MAX_TTL_MS
        )
        self._dedup_capacity = _require_int(
            "dedup_capacity", dedup_capacity, 1, 1_000_000
        )
        self._active_epoch: Optional[str] = None
        self._retired_epochs: Set[str] = set()
        self._last_sequences: Dict[str, int] = {}
        self._seen_event_ids: "OrderedDict[str, None]" = OrderedDict()

    @property
    def active_epoch(self) -> Optional[str]:
        return self._active_epoch

    def last_sequence(self, source_epoch: Optional[str] = None) -> Optional[int]:
        epoch = self._active_epoch if source_epoch is None else source_epoch
        if epoch is None:
            return None
        return self._last_sequences.get(epoch)

    def parse(
        self,
        value: Mapping[str, object],
        *,
        now_ms: Optional[int] = None,
    ) -> PrismAnimationSignal:
        return self._accept(_signal_from_mapping(value), now_ms=now_ms)

    def parse_json(
        self,
        value: JsonInput,
        *,
        now_ms: Optional[int] = None,
    ) -> PrismAnimationSignal:
        return self._accept(_signal_from_json(value), now_ms=now_ms)

    def _accept(
        self,
        signal: PrismAnimationSignal,
        *,
        now_ms: Optional[int],
    ) -> PrismAnimationSignal:
        checked_now = (
            int(time.time() * 1000)
            if now_ms is None
            else _require_int("now_ms", now_ms, 0, MAX_SAFE_INTEGER)
        )
        if signal.emitted_at_ms > checked_now + self._max_future_skew_ms:
            raise PrismSignalValidationError("Prism signal is issued too far in the future")
        if signal.is_expired(checked_now):
            raise PrismSignalValidationError("Prism signal TTL has expired")
        if signal.event_id in self._seen_event_ids:
            raise PrismSignalValidationError("duplicate Prism event_id")
        if signal.source_epoch in self._retired_epochs:
            raise PrismSignalValidationError("Prism source_epoch has been retired")

        last_sequence = self._last_sequences.get(signal.source_epoch)
        if last_sequence is not None and signal.source_sequence <= last_sequence:
            raise PrismSignalValidationError(
                "source_sequence must increase monotonically within source_epoch"
            )

        if self._active_epoch is not None and signal.source_epoch != self._active_epoch:
            self._retired_epochs.add(self._active_epoch)
        self._active_epoch = signal.source_epoch
        self._last_sequences[signal.source_epoch] = signal.source_sequence
        self._seen_event_ids[signal.event_id] = None
        while len(self._seen_event_ids) > self._dedup_capacity:
            self._seen_event_ids.popitem(last=False)
        return signal


@dataclass(frozen=True)
class PrismAdvisoryTransition:
    """Observable result of one content-free advisory state transition."""

    disposition: str
    accepted_signal: Optional[PrismAnimationSignal]
    active_signal: Optional[PrismAnimationSignal]
    released: bool
    release_reason: Optional[str]


class PrismAdvisoryStateMachine:
    """Own one advisory lifetime and fail closed on ambiguous correlation."""

    def __init__(self, parser: Optional[PrismSignalParser] = None) -> None:
        self._parser = parser if parser is not None else PrismSignalParser()
        self._active_signal: Optional[PrismAnimationSignal] = None

    @property
    def active_signal(self) -> Optional[PrismAnimationSignal]:
        return self._active_signal

    def accept(
        self,
        value: Mapping[str, object],
        *,
        now_ms: Optional[int] = None,
    ) -> PrismAdvisoryTransition:
        return self._apply(self._parser.parse(value, now_ms=now_ms))

    def accept_json(
        self,
        value: JsonInput,
        *,
        now_ms: Optional[int] = None,
    ) -> PrismAdvisoryTransition:
        return self._apply(self._parser.parse_json(value, now_ms=now_ms))

    def advance(self, *, now_ms: int) -> PrismAdvisoryTransition:
        checked_now = _require_int("now_ms", now_ms, 0, MAX_SAFE_INTEGER)
        active = self._active_signal
        if active is not None and active.is_expired(checked_now):
            self._active_signal = None
            return PrismAdvisoryTransition(
                "released", None, None, True, "expired"
            )
        return PrismAdvisoryTransition(
            "retained" if active is not None else "inactive",
            None,
            active,
            False,
            None,
        )

    def _apply(self, signal: PrismAnimationSignal) -> PrismAdvisoryTransition:
        terminal_status = signal.terminal_stage_status
        if terminal_status is not None:
            correlation_failure = self._terminal_correlation_failure(signal)
            if correlation_failure is not None:
                return PrismAdvisoryTransition(
                    "terminal_ignored",
                    signal,
                    self._active_signal,
                    False,
                    correlation_failure,
                )
            released = self._active_signal is not None
            self._active_signal = None
            return PrismAdvisoryTransition(
                "released" if released else "terminal",
                signal,
                None,
                released,
                terminal_status,
            )

        disposition = "replaced" if self._active_signal is not None else "activated"
        self._active_signal = signal
        return PrismAdvisoryTransition(
            disposition, signal, signal, False, None
        )

    def _terminal_correlation_failure(
        self, terminal: PrismAnimationSignal
    ) -> Optional[str]:
        active = self._active_signal
        if active is None:
            return None
        active_v2 = isinstance(active, PrismAnimationSignalV2)
        terminal_v2 = isinstance(terminal, PrismAnimationSignalV2)
        if not active_v2 and not terminal_v2:
            return None
        if not active_v2 or not terminal_v2:
            return "turn_unbound"
        if active.turn_id != terminal.turn_id:
            return "turn_mismatch"
        if (
            active.utterance_id is not None
            and terminal.utterance_id is not None
            and active.utterance_id != terminal.utterance_id
        ):
            return "utterance_mismatch"
        return None


class PrismSignalAdapter(PrismSignalParser):
    """Compatibility name for the validation-only, network-free adapter."""


PrismAnimationSignalParser = PrismSignalParser
