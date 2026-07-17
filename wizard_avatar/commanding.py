from __future__ import annotations

import heapq
import math
from collections import OrderedDict
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple


COMMAND_SCHEMA_VERSION = 1
DEFAULT_INBOX_CAPACITY = 1024
DEFAULT_DEDUP_CAPACITY = 4096
DEFAULT_SOURCE_WATERMARK_CAPACITY = 4096
DEFAULT_RETIRED_SOURCE_EPOCH_CAPACITY = 16384
MAX_FUTURE_TICKS = 120
TICK_RATE = 60

SOURCE_KINDS = frozenset(
    {
        "keyboard",
        "gamepad",
        "remote",
        "demo",
        "api",
        "system",
        "visual_signal",
        "legacy_adapter",
    }
)
PRIORITY_CLASSES = frozenset({"user", "system", "demo", "visual_signal"})
COMMAND_KINDS = frozenset(
    {
        "control_intent",
        "action",
        "path",
        "move",
        "move_to",
        "circle",
        "figure_eight",
        "face",
        "gaze",
        "expression",
        "speak",
        "stop",
        "reset",
        "diagnostic_pose",
        "visual_signal",
    }
)
ACK_DISPOSITIONS = frozenset(
    {
        "accepted",
        "applied",
        "rejected",
        "duplicate",
        "expired",
        "unauthorized",
        "stale",
    }
)

_PRIORITY_BY_CLASS = {
    "system": 100,
    "user": 60,
    "demo": 40,
    "visual_signal": 20,
}


class CommandValidationError(ValueError):
    """Raised when a command does not satisfy the frozen CAP-100 contract."""


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_int(name: str, value: object, minimum: Optional[int] = None) -> int:
    if not _is_int(value):
        raise CommandValidationError("{} must be an integer".format(name))
    result = int(value)
    if minimum is not None and result < minimum:
        raise CommandValidationError("{} must be >= {}".format(name, minimum))
    return result


def _require_text(name: str, value: object, maximum: int = 128) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise CommandValidationError("{} must be a non-empty string <= {} characters".format(name, maximum))
    return value


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        frozen: Dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CommandValidationError("payload keys must be strings")
            frozen[key] = _freeze(item)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise CommandValidationError("unsupported payload value type: {}".format(type(value).__name__))


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return sorted((_thaw(item) for item in value), key=repr)
    return value


@dataclass(frozen=True)
class CommandEnvelopeV1:
    schema_version: int
    command_id: str
    source_id: str
    source_kind: str
    source_sequence: int
    source_epoch: str
    kind: str
    payload: Mapping[str, object] = field(default_factory=dict)
    issued_at_ms: Optional[float] = None
    issued_tick: Optional[int] = None
    ttl_ms: Optional[int] = None
    lease_id: Optional[str] = None
    duration_ticks: Optional[int] = None
    priority_class: str = "user"

    def __post_init__(self) -> None:
        if self.schema_version != COMMAND_SCHEMA_VERSION or isinstance(self.schema_version, bool):
            raise CommandValidationError("schema_version must be exactly 1")
        _require_text("command_id", self.command_id)
        _require_text("source_id", self.source_id)
        _require_text("source_epoch", self.source_epoch)
        _require_int("source_sequence", self.source_sequence, 0)
        if self.source_kind not in SOURCE_KINDS:
            raise CommandValidationError("unsupported source_kind: {}".format(self.source_kind))
        if self.kind not in COMMAND_KINDS:
            raise CommandValidationError("unsupported command kind: {}".format(self.kind))
        if self.priority_class not in PRIORITY_CLASSES:
            raise CommandValidationError("unsupported priority_class: {}".format(self.priority_class))
        if not isinstance(self.payload, Mapping):
            raise CommandValidationError("payload must be an object")
        object.__setattr__(self, "payload", _freeze(self.payload))
        if self.issued_at_ms is not None:
            if isinstance(self.issued_at_ms, bool) or not isinstance(self.issued_at_ms, (int, float)):
                raise CommandValidationError("issued_at_ms must be a finite number or null")
            if not math.isfinite(float(self.issued_at_ms)):
                raise CommandValidationError("issued_at_ms must be finite")
            object.__setattr__(self, "issued_at_ms", float(self.issued_at_ms))
        if self.issued_tick is not None:
            _require_int("issued_tick", self.issued_tick, 0)
        if self.ttl_ms is not None:
            _require_int("ttl_ms", self.ttl_ms, 0)
        if self.kind == "control_intent":
            if self.ttl_ms is None or not 50 <= self.ttl_ms <= 1000:
                raise CommandValidationError("control_intent ttl_ms must be in [50, 1000]")
            if not self.lease_id:
                raise CommandValidationError("control_intent requires lease_id")
        if self.lease_id is not None:
            _require_text("lease_id", self.lease_id)
        if self.duration_ticks is not None:
            _require_int("duration_ticks", self.duration_ticks, 1)

    @property
    def sequence(self) -> int:
        """Compatibility alias used by the earlier workflow report."""

        return self.source_sequence

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "CommandEnvelopeV1":
        if not isinstance(value, Mapping):
            raise CommandValidationError("command envelope must be an object")
        allowed = {
            "schema_version",
            "command_id",
            "source_id",
            "source_kind",
            "source_sequence",
            "sequence",
            "source_epoch",
            "kind",
            "payload",
            "issued_at_ms",
            "issued_tick",
            "ttl_ms",
            "lease_id",
            "duration_ticks",
            "priority_class",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise CommandValidationError("unknown command fields: {}".format(", ".join(unknown)))
        if "source_sequence" in value and "sequence" in value:
            raise CommandValidationError("use source_sequence, not both source_sequence and sequence")
        required = {"schema_version", "command_id", "source_id", "source_kind", "source_epoch", "kind"}
        missing = sorted(required - set(value))
        if "source_sequence" not in value and "sequence" not in value:
            missing.append("source_sequence")
        if missing:
            raise CommandValidationError("missing command fields: {}".format(", ".join(missing)))
        return cls(
            schema_version=value["schema_version"],  # type: ignore[arg-type]
            command_id=value["command_id"],  # type: ignore[arg-type]
            source_id=value["source_id"],  # type: ignore[arg-type]
            source_kind=value["source_kind"],  # type: ignore[arg-type]
            source_sequence=value.get("source_sequence", value.get("sequence")),  # type: ignore[arg-type]
            source_epoch=value["source_epoch"],  # type: ignore[arg-type]
            kind=value["kind"],  # type: ignore[arg-type]
            payload=value.get("payload", {}),  # type: ignore[arg-type]
            issued_at_ms=value.get("issued_at_ms"),  # type: ignore[arg-type]
            issued_tick=value.get("issued_tick"),  # type: ignore[arg-type]
            ttl_ms=value.get("ttl_ms"),  # type: ignore[arg-type]
            lease_id=value.get("lease_id"),  # type: ignore[arg-type]
            duration_ticks=value.get("duration_ticks"),  # type: ignore[arg-type]
            priority_class=value.get("priority_class", "user"),  # type: ignore[arg-type]
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "command_id": self.command_id,
            "source_id": self.source_id,
            "source_kind": self.source_kind,
            "source_sequence": self.source_sequence,
            "source_epoch": self.source_epoch,
            "kind": self.kind,
            "payload": _thaw(self.payload),
            "issued_at_ms": self.issued_at_ms,
            "issued_tick": self.issued_tick,
            "ttl_ms": self.ttl_ms,
            "lease_id": self.lease_id,
            "duration_ticks": self.duration_ticks,
            "priority_class": self.priority_class,
        }


@dataclass(frozen=True)
class QueuedCommand:
    envelope: CommandEnvelopeV1
    received_order: int
    accepted_tick: int
    apply_tick: int
    priority: int


@dataclass(frozen=True)
class CommandAckV1:
    schema_version: int
    command_id: str
    source_id: str
    source_sequence: int
    disposition: str
    accepted_tick: Optional[int]
    apply_tick: Optional[int]
    state_revision: int
    runtime_epoch: str
    error_code: Optional[str] = None
    message: str = "ok"
    lease_id: Optional[str] = None
    lease_generation: Optional[int] = None

    def __post_init__(self) -> None:
        if self.schema_version != COMMAND_SCHEMA_VERSION:
            raise CommandValidationError("ack schema_version must be exactly 1")
        if self.disposition not in ACK_DISPOSITIONS:
            raise CommandValidationError("unsupported ack disposition: {}".format(self.disposition))

    @property
    def sequence(self) -> int:
        return self.source_sequence

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "command_id": self.command_id,
            "source_id": self.source_id,
            "source_sequence": self.source_sequence,
            "disposition": self.disposition,
            "accepted_tick": self.accepted_tick,
            "apply_tick": self.apply_tick,
            "state_revision": self.state_revision,
            "runtime_epoch": self.runtime_epoch,
            "error_code": self.error_code,
            "message": self.message,
            "lease_id": self.lease_id,
            "lease_generation": self.lease_generation,
        }


def command_priority(envelope: CommandEnvelopeV1) -> int:
    if envelope.kind in {"stop", "reset"} or envelope.source_kind == "system":
        return 100
    if envelope.kind == "action" and envelope.priority_class == "user":
        return 80
    return _PRIORITY_BY_CLASS[envelope.priority_class]


class OrderedCommandInbox:
    """Bounded, deterministic, idempotent command scheduling for one runtime epoch."""

    def __init__(
        self,
        runtime_epoch: str,
        capacity: int = DEFAULT_INBOX_CAPACITY,
        dedup_capacity: int = DEFAULT_DEDUP_CAPACITY,
        source_watermark_capacity: int = DEFAULT_SOURCE_WATERMARK_CAPACITY,
        retired_source_epoch_capacity: int = DEFAULT_RETIRED_SOURCE_EPOCH_CAPACITY,
    ) -> None:
        _require_text("runtime_epoch", runtime_epoch)
        if not _is_int(capacity) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if not _is_int(dedup_capacity) or dedup_capacity < capacity:
            raise ValueError("dedup_capacity must be an integer >= capacity")
        if not _is_int(source_watermark_capacity) or source_watermark_capacity <= 0:
            raise ValueError("source_watermark_capacity must be a positive integer")
        if not _is_int(retired_source_epoch_capacity) or retired_source_epoch_capacity <= 0:
            raise ValueError("retired_source_epoch_capacity must be a positive integer")
        self.runtime_epoch = runtime_epoch
        self.capacity = capacity
        self.dedup_capacity = dedup_capacity
        self.source_watermark_capacity = source_watermark_capacity
        self.retired_source_epoch_capacity = retired_source_epoch_capacity
        self._heap: list[Tuple[int, int, int, QueuedCommand]] = []
        self._received_order = 0
        self._source_watermarks: "OrderedDict[Tuple[str, str], int]" = OrderedDict()
        self._active_source_epochs: Dict[str, str] = {}
        self._retired_source_epochs: set[Tuple[str, str]] = set()
        self._total_source_epoch_count = 0
        self._source_watermark_eviction_count = 0
        self._source_watermark_capacity_rejection_count = 0
        self._acks: "OrderedDict[str, CommandAckV1]" = OrderedDict()
        self._pending_ids: set[str] = set()

    def submit(
        self,
        envelope: CommandEnvelopeV1,
        current_tick: int,
        state_revision: int,
        apply_tick: Optional[int] = None,
    ) -> CommandAckV1:
        _require_int("current_tick", current_tick, 0)
        _require_int("state_revision", state_revision, 0)
        prior = self._acks.get(envelope.command_id)
        if prior is not None:
            self._acks.move_to_end(envelope.command_id)
            return replace(
                prior,
                disposition="duplicate",
                error_code="duplicate_command",
                message="command_id was already observed in this runtime epoch",
            )

        key = (envelope.source_id, envelope.source_epoch)
        if key in self._retired_source_epochs:
            return self._remember(
                self._reject(
                    envelope,
                    state_revision,
                    "stale",
                    "retired_source_epoch",
                    "source epoch was retired; use a fresh source_epoch",
                )
            )

        active_epoch = self._active_source_epochs.get(envelope.source_id)
        if active_epoch is not None and active_epoch != envelope.source_epoch and key in self._source_watermarks:
            return self._remember(
                self._reject(
                    envelope,
                    state_revision,
                    "stale",
                    "retired_source_epoch",
                    "source epoch is no longer active; use a fresh source_epoch",
                )
            )

        watermark = self._source_watermarks.get(key)
        if watermark is not None and envelope.source_sequence <= watermark:
            return self._remember(
                self._reject(envelope, state_revision, "stale", "stale_sequence", "source_sequence must increase")
            )

        if self._is_expired(envelope, current_tick):
            return self._remember(
                self._reject(envelope, state_revision, "expired", "command_expired", "command TTL elapsed")
            )

        target_tick = current_tick + 1 if apply_tick is None else apply_tick
        if not _is_int(target_tick) or target_tick < current_tick + 1:
            return self._remember(
                self._reject(envelope, state_revision, "rejected", "invalid_apply_tick", "apply_tick is in the past")
            )
        if target_tick > current_tick + MAX_FUTURE_TICKS:
            return self._remember(
                self._reject(envelope, state_revision, "rejected", "apply_tick_too_far", "apply_tick exceeds horizon")
            )
        if len(self._heap) >= self.capacity:
            return self._remember(
                self._reject(envelope, state_revision, "rejected", "queue_full", "command inbox is full")
            )
        if not self._reserve_source_watermark(key):
            self._source_watermark_capacity_rejection_count += 1
            return self._remember(
                self._reject(
                    envelope,
                    state_revision,
                    "rejected",
                    "source_watermark_capacity",
                    "source watermark retention is full; use an existing active source or restart the runtime",
                )
            )

        self._received_order += 1
        priority = command_priority(envelope)
        queued = QueuedCommand(
            envelope=envelope,
            received_order=self._received_order,
            accepted_tick=current_tick,
            apply_tick=target_tick,
            priority=priority,
        )
        # Higher numeric priority applies first at the same tick.
        heapq.heappush(self._heap, (target_tick, -priority, queued.received_order, queued))
        self._pending_ids.add(envelope.command_id)
        is_new_source_epoch = key not in self._source_watermarks
        self._source_watermarks[key] = envelope.source_sequence
        self._source_watermarks.move_to_end(key)
        self._active_source_epochs[envelope.source_id] = envelope.source_epoch
        if is_new_source_epoch:
            self._total_source_epoch_count += 1
        ack = CommandAckV1(
            schema_version=COMMAND_SCHEMA_VERSION,
            command_id=envelope.command_id,
            source_id=envelope.source_id,
            source_sequence=envelope.source_sequence,
            disposition="accepted",
            accepted_tick=current_tick,
            apply_tick=target_tick,
            state_revision=state_revision,
            runtime_epoch=self.runtime_epoch,
            lease_id=envelope.lease_id,
        )
        return self._remember(ack)

    def pop_due(self, simulation_tick: int) -> Tuple[QueuedCommand, ...]:
        _require_int("simulation_tick", simulation_tick, 0)
        due = []
        while self._heap and self._heap[0][0] <= simulation_tick:
            _, _, _, queued = heapq.heappop(self._heap)
            self._pending_ids.discard(queued.envelope.command_id)
            due.append(queued)
        return tuple(due)

    def mark_applied(self, command_id: str, state_revision: int, message: str = "applied") -> CommandAckV1:
        prior = self._acks.get(command_id)
        if prior is None:
            raise KeyError(command_id)
        if prior.disposition not in {"accepted", "applied"}:
            raise ValueError("cannot apply command with disposition {}".format(prior.disposition))
        ack = replace(
            prior,
            disposition="applied",
            state_revision=state_revision,
            error_code=None,
            message=message,
        )
        self._acks[command_id] = ack
        self._acks.move_to_end(command_id)
        return ack

    def mark_rejected(
        self,
        command_id: str,
        state_revision: int,
        error_code: str,
        message: str,
    ) -> CommandAckV1:
        prior = self._acks.get(command_id)
        if prior is None:
            raise KeyError(command_id)
        if prior.disposition != "accepted":
            raise ValueError("cannot reject command with disposition {}".format(prior.disposition))
        ack = replace(
            prior,
            disposition="rejected",
            state_revision=state_revision,
            error_code=error_code,
            message=message,
        )
        self._acks[command_id] = ack
        self._acks.move_to_end(command_id)
        return ack

    def ack_for(self, command_id: str) -> Optional[CommandAckV1]:
        return self._acks.get(command_id)

    @property
    def pending_count(self) -> int:
        return len(self._heap)

    @property
    def received_order(self) -> int:
        return self._received_order

    def source_watermark(self, source_id: str, source_epoch: str) -> Optional[int]:
        return self._source_watermarks.get((source_id, source_epoch))

    @property
    def source_watermark_count(self) -> int:
        return len(self._source_watermarks)

    @property
    def total_source_epoch_count(self) -> int:
        return self._total_source_epoch_count

    @property
    def source_watermark_eviction_count(self) -> int:
        return self._source_watermark_eviction_count

    @property
    def source_watermark_capacity_rejection_count(self) -> int:
        return self._source_watermark_capacity_rejection_count

    @property
    def source_retention_diagnostics(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "source_watermark_capacity": self.source_watermark_capacity,
                "source_watermark_count": self.source_watermark_count,
                "total_source_epoch_count": self.total_source_epoch_count,
                "source_watermark_eviction_count": self.source_watermark_eviction_count,
                "source_watermark_capacity_rejection_count": self.source_watermark_capacity_rejection_count,
                "retired_source_epoch_capacity": self.retired_source_epoch_capacity,
                "retired_source_epoch_count": len(self._retired_source_epochs),
            }
        )

    def pending(self) -> Tuple[QueuedCommand, ...]:
        return tuple(item[3] for item in sorted(self._heap))

    def discard_pending(self, kinds: Optional[Iterable[str]] = None) -> Tuple[QueuedCommand, ...]:
        kind_set = None if kinds is None else frozenset(kinds)
        kept = []
        removed = []
        for item in self._heap:
            queued = item[3]
            if kind_set is None or queued.envelope.kind in kind_set:
                removed.append(queued)
                self._pending_ids.discard(queued.envelope.command_id)
            else:
                kept.append(item)
        self._heap = kept
        heapq.heapify(self._heap)
        return tuple(sorted(removed, key=lambda item: (item.apply_tick, -item.priority, item.received_order)))

    def _is_expired(self, envelope: CommandEnvelopeV1, current_tick: int) -> bool:
        if envelope.ttl_ms is None or envelope.issued_tick is None:
            return False
        ttl_ticks = int(math.ceil(envelope.ttl_ms * TICK_RATE / 1000.0))
        return current_tick > envelope.issued_tick + ttl_ticks

    def _reserve_source_watermark(self, incoming_key: Tuple[str, str]) -> bool:
        if incoming_key in self._source_watermarks:
            return True
        if len(self._source_watermarks) < self.source_watermark_capacity:
            return True
        if len(self._retired_source_epochs) >= self.retired_source_epoch_capacity:
            return False

        pending_keys = {
            (item[3].envelope.source_id, item[3].envelope.source_epoch)
            for item in self._heap
        }
        incoming_source_id = incoming_key[0]
        for candidate in tuple(self._source_watermarks):
            active_epoch = self._active_source_epochs.get(candidate[0])
            is_active = active_epoch == candidate[1]
            is_atomic_epoch_replacement = candidate[0] == incoming_source_id
            if candidate in pending_keys or (is_active and not is_atomic_epoch_replacement):
                continue
            del self._source_watermarks[candidate]
            self._retired_source_epochs.add(candidate)
            self._source_watermark_eviction_count += 1
            return True
        return False

    def _reject(
        self,
        envelope: CommandEnvelopeV1,
        state_revision: int,
        disposition: str,
        error_code: str,
        message: str,
    ) -> CommandAckV1:
        return CommandAckV1(
            schema_version=COMMAND_SCHEMA_VERSION,
            command_id=envelope.command_id,
            source_id=envelope.source_id,
            source_sequence=envelope.source_sequence,
            disposition=disposition,
            accepted_tick=None,
            apply_tick=None,
            state_revision=state_revision,
            runtime_epoch=self.runtime_epoch,
            error_code=error_code,
            message=message,
            lease_id=envelope.lease_id,
        )

    def _remember(self, ack: CommandAckV1) -> CommandAckV1:
        self._acks[ack.command_id] = ack
        self._acks.move_to_end(ack.command_id)
        self._trim_dedup_cache()
        return ack

    def _trim_dedup_cache(self) -> None:
        while len(self._acks) > self.dedup_capacity:
            removed = False
            for command_id in tuple(self._acks):
                if command_id not in self._pending_ids:
                    del self._acks[command_id]
                    removed = True
                    break
            if not removed:
                return


__all__ = [
    "ACK_DISPOSITIONS",
    "COMMAND_KINDS",
    "COMMAND_SCHEMA_VERSION",
    "DEFAULT_RETIRED_SOURCE_EPOCH_CAPACITY",
    "DEFAULT_SOURCE_WATERMARK_CAPACITY",
    "CommandAckV1",
    "CommandEnvelopeV1",
    "CommandValidationError",
    "OrderedCommandInbox",
    "QueuedCommand",
    "command_priority",
]
