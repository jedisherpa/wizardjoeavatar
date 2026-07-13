from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Dict, Generic, Mapping, Optional, Sequence, Tuple, TypeVar

from .commanding import CommandAckV1, CommandEnvelopeV1, OrderedCommandInbox, QueuedCommand


TICK_RATE = 60
TICK_SECONDS = 1.0 / TICK_RATE
ACCUMULATOR_TICK_UNITS = 1_000_000_000
DEFAULT_MAX_CATCH_UP_TICKS = 8

StateT = TypeVar("StateT")
PresentationT = TypeVar("PresentationT")
Reducer = Callable[[StateT, Tuple[QueuedCommand, ...], int, float], StateT]
PresentationFactory = Callable[[StateT, int], PresentationT]


def _canonicalize(value: object) -> object:
    if isinstance(value, Enum):
        return _canonicalize(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _canonicalize(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        entries = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical mappings require string keys")
            entries.append((key, _canonicalize(item)))
        return {key: item for key, item in sorted(entries)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        canonical_items = [_canonicalize(item) for item in value]
        return sorted(canonical_items, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical state cannot contain non-finite floats")
        return {"$float_hex": value.hex()}
    if isinstance(value, bytes):
        return {"$bytes_hex": value.hex()}
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError("unsupported canonical value type: {}".format(type(value).__name__))


def canonical_json_bytes(value: object) -> bytes:
    """Serialize structured state with stable ordering and exact float identity."""

    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def freeze_snapshot_value(value: object) -> object:
    """Create a recursively immutable snapshot without mutating the working state."""

    if isinstance(value, Enum) or value is None or isinstance(value, (str, int, float, bool, bytes)):
        return value
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze_snapshot_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze_snapshot_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze_snapshot_value(item) for item in value)
    if is_dataclass(value) and not isinstance(value, type):
        params = getattr(value, "__dataclass_params__", None)
        values = {item.name: freeze_snapshot_value(getattr(value, item.name)) for item in fields(value)}
        if params is not None and params.frozen:
            return type(value)(**values)
        return MappingProxyType(values)
    return copy.deepcopy(value)


@dataclass(frozen=True)
class RuntimeClock:
    simulation_tick: int = 0
    accumulator_units: int = 0
    dropped_accumulator_units: int = 0
    max_catch_up_ticks: int = DEFAULT_MAX_CATCH_UP_TICKS
    state_revision: int = 0

    @property
    def accumulator_seconds(self) -> float:
        return self.accumulator_units / float(ACCUMULATOR_TICK_UNITS * TICK_RATE)

    @property
    def dropped_simulation_seconds(self) -> float:
        return self.dropped_accumulator_units / float(ACCUMULATOR_TICK_UNITS * TICK_RATE)

    @property
    def dropped_simulation_ns(self) -> int:
        return self.dropped_accumulator_units // TICK_RATE


@dataclass(frozen=True)
class RuntimeSnapshot(Generic[StateT, PresentationT]):
    previous: StateT
    current: StateT
    presentation: Optional[PresentationT]
    simulation_tick: int
    state_revision: int
    state_hash: str


@dataclass(frozen=True)
class RuntimeEvent:
    event_type: str
    simulation_tick: int
    details: Mapping[str, object]


@dataclass(frozen=True)
class RuntimeAdvanceResult(Generic[StateT, PresentationT]):
    snapshot: RuntimeSnapshot[StateT, PresentationT]
    steps: int
    dropped_ticks: int
    elapsed_ns: int
    events: Tuple[RuntimeEvent, ...]


class ReplayLog:
    """Deterministic in-memory NDJSON evidence recorder."""

    def __init__(self, header: Mapping[str, object]) -> None:
        self._records: list[Dict[str, object]] = []
        self._sequence = 0
        self.append("header", 0, header)

    def append(self, record_type: str, simulation_tick: int, payload: Mapping[str, object]) -> None:
        if not record_type:
            raise ValueError("record_type must not be empty")
        if simulation_tick < 0:
            raise ValueError("simulation_tick must be non-negative")
        record = {
            "record_type": record_type,
            "record_sequence": self._sequence,
            "simulation_tick": simulation_tick,
            "payload": _canonicalize(payload),
        }
        self._records.append(record)
        self._sequence += 1

    @property
    def records(self) -> Tuple[Mapping[str, object], ...]:
        return tuple(freeze_snapshot_value(record) for record in self._records)  # type: ignore[return-value]

    def to_ndjson_bytes(self) -> bytes:
        return b"".join(canonical_json_bytes(record) + b"\n" for record in self._records)

    def sha256(self) -> str:
        return hashlib.sha256(self.to_ndjson_bytes()).hexdigest()


class AvatarRuntime(Generic[StateT, PresentationT]):
    """Single-writer, exact-tick semantic runtime independent of rendering."""

    TICK_RATE = TICK_RATE
    TICK_SECONDS = TICK_SECONDS

    def __init__(
        self,
        initial_state: StateT,
        reducer: Reducer[StateT],
        runtime_epoch: str,
        inbox: Optional[OrderedCommandInbox] = None,
        presentation_factory: Optional[PresentationFactory[StateT, PresentationT]] = None,
        max_catch_up_ticks: int = DEFAULT_MAX_CATCH_UP_TICKS,
        replay_log: Optional[ReplayLog] = None,
    ) -> None:
        if not runtime_epoch:
            raise ValueError("runtime_epoch must not be empty")
        if isinstance(max_catch_up_ticks, bool) or not isinstance(max_catch_up_ticks, int):
            raise ValueError("max_catch_up_ticks must be an integer")
        if max_catch_up_ticks <= 0:
            raise ValueError("max_catch_up_ticks must be positive")
        self.runtime_epoch = runtime_epoch
        self.inbox = inbox or OrderedCommandInbox(runtime_epoch)
        if self.inbox.runtime_epoch != runtime_epoch:
            raise ValueError("inbox runtime epoch does not match runtime")
        self._reducer = reducer
        self._presentation_factory = presentation_factory
        self._working_state = copy.deepcopy(initial_state)
        self._simulation_tick = 0
        self._state_revision = 0
        self._accumulator_units = 0
        self._dropped_accumulator_units = 0
        self._max_catch_up_ticks = max_catch_up_ticks
        self._last_monotonic_ns: Optional[int] = None
        self._events: list[RuntimeEvent] = []
        self._replay_log = replay_log
        frozen = freeze_snapshot_value(initial_state)
        presentation = self._build_presentation(initial_state, 0)
        self._snapshot = RuntimeSnapshot(
            previous=frozen,  # type: ignore[arg-type]
            current=frozen,  # type: ignore[arg-type]
            presentation=presentation,
            simulation_tick=0,
            state_revision=0,
            state_hash=canonical_sha256(frozen),
        )

    @property
    def clock(self) -> RuntimeClock:
        return RuntimeClock(
            simulation_tick=self._simulation_tick,
            accumulator_units=self._accumulator_units,
            dropped_accumulator_units=self._dropped_accumulator_units,
            max_catch_up_ticks=self._max_catch_up_ticks,
            state_revision=self._state_revision,
        )

    def enqueue(self, envelope: CommandEnvelopeV1, apply_tick: Optional[int] = None) -> CommandAckV1:
        ack = self.inbox.submit(
            envelope,
            current_tick=self._simulation_tick,
            state_revision=self._state_revision,
            apply_tick=apply_tick,
        )
        if self._replay_log is not None:
            self._replay_log.append(
                "command_ack",
                self._simulation_tick,
                {"command": envelope.to_dict(), "ack": ack.to_dict()},
            )
        return ack

    def step_tick(self) -> RuntimeSnapshot[StateT, PresentationT]:
        target_tick = self._simulation_tick + 1
        due = self.inbox.pop_due(target_tick)
        candidate = copy.deepcopy(self._working_state)
        next_state = self._reducer(candidate, due, target_tick, TICK_SECONDS)
        if next_state is None:
            raise TypeError("runtime reducer must return the next state")

        previous = self._snapshot.current
        self._working_state = next_state
        self._simulation_tick = target_tick
        self._state_revision += 1
        current = freeze_snapshot_value(next_state)
        presentation = self._build_presentation(next_state, target_tick)
        self._snapshot = RuntimeSnapshot(
            previous=previous,
            current=current,  # type: ignore[arg-type]
            presentation=presentation,
            simulation_tick=target_tick,
            state_revision=self._state_revision,
            state_hash=canonical_sha256(current),
        )
        applied_acks = []
        for queued in due:
            applied_acks.append(
                self.inbox.mark_applied(queued.envelope.command_id, self._state_revision).to_dict()
            )
        if self._replay_log is not None:
            self._replay_log.append(
                "tick_state",
                target_tick,
                {
                    "state_revision": self._state_revision,
                    "state_hash": self._snapshot.state_hash,
                    "state": current,
                    "applied_commands": [item.envelope.command_id for item in due],
                    "applied_acks": applied_acks,
                },
            )
        return self._snapshot

    def advance_to(self, monotonic_ns: int) -> RuntimeAdvanceResult[StateT, PresentationT]:
        if isinstance(monotonic_ns, bool) or not isinstance(monotonic_ns, int) or monotonic_ns < 0:
            raise ValueError("monotonic_ns must be a non-negative integer")
        if self._last_monotonic_ns is None:
            self._last_monotonic_ns = monotonic_ns
            return RuntimeAdvanceResult(self._snapshot, 0, 0, 0, ())
        if monotonic_ns < self._last_monotonic_ns:
            raise ValueError("monotonic clock moved backwards")
        elapsed_ns = monotonic_ns - self._last_monotonic_ns
        self._last_monotonic_ns = monotonic_ns
        return self.advance_elapsed_ns(elapsed_ns)

    def advance_elapsed_ns(self, elapsed_ns: int) -> RuntimeAdvanceResult[StateT, PresentationT]:
        if isinstance(elapsed_ns, bool) or not isinstance(elapsed_ns, int) or elapsed_ns < 0:
            raise ValueError("elapsed_ns must be a non-negative integer")
        event_start = len(self._events)
        self._accumulator_units += elapsed_ns * TICK_RATE
        due_ticks = self._accumulator_units // ACCUMULATOR_TICK_UNITS
        steps = min(due_ticks, self._max_catch_up_ticks)
        dropped_ticks = due_ticks - steps
        if due_ticks:
            self._accumulator_units -= due_ticks * ACCUMULATOR_TICK_UNITS
        if dropped_ticks:
            dropped_units = dropped_ticks * ACCUMULATOR_TICK_UNITS
            self._dropped_accumulator_units += dropped_units
            event = RuntimeEvent(
                event_type="runtime.catch_up_dropped",
                simulation_tick=self._simulation_tick,
                details=MappingProxyType(
                    {
                        "dropped_ticks": dropped_ticks,
                        "dropped_simulation_ns": dropped_units // TICK_RATE,
                        "max_catch_up_ticks": self._max_catch_up_ticks,
                    }
                ),
            )
            self._events.append(event)
            if self._replay_log is not None:
                self._replay_log.append(event.event_type, self._simulation_tick, event.details)
        for _ in range(steps):
            self.step_tick()
        new_events = tuple(self._events[event_start:])
        return RuntimeAdvanceResult(
            snapshot=self._snapshot,
            steps=steps,
            dropped_ticks=dropped_ticks,
            elapsed_ns=elapsed_ns,
            events=new_events,
        )

    def current_snapshot(self) -> RuntimeSnapshot[StateT, PresentationT]:
        return self._snapshot

    def drain_events(self) -> Tuple[RuntimeEvent, ...]:
        events = tuple(self._events)
        self._events.clear()
        return events

    def _build_presentation(self, state: StateT, tick: int) -> Optional[PresentationT]:
        if self._presentation_factory is None:
            return None
        presentation = self._presentation_factory(copy.deepcopy(state), tick)
        return freeze_snapshot_value(presentation)  # type: ignore[return-value]


__all__ = [
    "ACCUMULATOR_TICK_UNITS",
    "AvatarRuntime",
    "DEFAULT_MAX_CATCH_UP_TICKS",
    "ReplayLog",
    "RuntimeAdvanceResult",
    "RuntimeClock",
    "RuntimeEvent",
    "RuntimeSnapshot",
    "TICK_RATE",
    "TICK_SECONDS",
    "canonical_json_bytes",
    "canonical_sha256",
    "freeze_snapshot_value",
]
