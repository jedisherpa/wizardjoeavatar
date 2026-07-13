from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Tuple

from .commanding import CommandEnvelopeV1, CommandValidationError, command_priority


CONTROL_SCHEMA_VERSION = 1
LEASE_TIMEOUT_MS = 250
TICK_RATE = 60

SPEED_MODES = frozenset({"walk", "run"})
MOBILITY_REQUESTS = frozenset({"keep", "takeoff", "land"})

_EXPECTED_PRIORITY_CLASS = {
    "keyboard": "user",
    "gamepad": "user",
    "remote": "user",
    "api": "user",
    "legacy_adapter": "user",
    "demo": "demo",
    "visual_signal": "visual_signal",
    "system": "system",
}


class ControlValidationError(ValueError):
    """Raised when a continuous control intent is malformed."""


def _number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ControlValidationError("{} must be a finite number".format(name))
    result = float(value)
    if not math.isfinite(result):
        raise ControlValidationError("{} must be finite".format(name))
    return result


def _unit_axis(name: str, value: object) -> float:
    result = _number(name, value)
    if not -1.0 <= result <= 1.0:
        raise ControlValidationError("{} must be in [-1.0, 1.0]".format(name))
    return result


@dataclass(frozen=True)
class ControlIntentV1:
    move_x: float = 0.0
    move_z: float = 0.0
    ascend: float = 0.0
    face_x: Optional[float] = None
    face_z: Optional[float] = None
    speed_mode: str = "walk"
    mobility_request: str = "keep"
    held_actions: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        move_x = _unit_axis("move_x", self.move_x)
        move_z = _unit_axis("move_z", self.move_z)
        magnitude = math.hypot(move_x, move_z)
        if magnitude > 1.0:
            move_x /= magnitude
            move_z /= magnitude
        object.__setattr__(self, "move_x", move_x)
        object.__setattr__(self, "move_z", move_z)
        object.__setattr__(self, "ascend", _unit_axis("ascend", self.ascend))

        if (self.face_x is None) != (self.face_z is None):
            raise ControlValidationError("face_x and face_z must both be set or both be null")
        if self.face_x is not None and self.face_z is not None:
            face_x = _unit_axis("face_x", self.face_x)
            face_z = _unit_axis("face_z", self.face_z)
            face_magnitude = math.hypot(face_x, face_z)
            if face_magnitude == 0.0:
                raise ControlValidationError("facing vector must not be zero")
            if face_magnitude > 1.0:
                face_x /= face_magnitude
                face_z /= face_magnitude
            object.__setattr__(self, "face_x", face_x)
            object.__setattr__(self, "face_z", face_z)

        if self.speed_mode not in SPEED_MODES:
            raise ControlValidationError("unsupported speed_mode: {}".format(self.speed_mode))
        if self.mobility_request not in MOBILITY_REQUESTS:
            raise ControlValidationError("unsupported mobility_request: {}".format(self.mobility_request))
        if not isinstance(self.held_actions, tuple):
            object.__setattr__(self, "held_actions", tuple(self.held_actions))
        for action in self.held_actions:
            if not isinstance(action, str) or not action:
                raise ControlValidationError("held_actions must contain non-empty strings")
        if len(set(self.held_actions)) != len(self.held_actions):
            raise ControlValidationError("held_actions must not contain duplicates")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "ControlIntentV1":
        if not isinstance(value, Mapping):
            raise ControlValidationError("control intent must be an object")
        allowed = {
            "move_x",
            "move_z",
            "ascend",
            "face_x",
            "face_z",
            "speed_mode",
            "mobility_request",
            "held_actions",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ControlValidationError("unknown control fields: {}".format(", ".join(unknown)))
        held_actions = value.get("held_actions", ())
        if not isinstance(held_actions, (list, tuple)):
            raise ControlValidationError("held_actions must be an array")
        return cls(
            move_x=value.get("move_x", 0.0),  # type: ignore[arg-type]
            move_z=value.get("move_z", 0.0),  # type: ignore[arg-type]
            ascend=value.get("ascend", 0.0),  # type: ignore[arg-type]
            face_x=value.get("face_x"),  # type: ignore[arg-type]
            face_z=value.get("face_z"),  # type: ignore[arg-type]
            speed_mode=value.get("speed_mode", "walk"),  # type: ignore[arg-type]
            mobility_request=value.get("mobility_request", "keep"),  # type: ignore[arg-type]
            held_actions=tuple(held_actions),
        )

    @classmethod
    def neutral(cls) -> "ControlIntentV1":
        return cls()

    @property
    def planar_magnitude(self) -> float:
        return math.hypot(self.move_x, self.move_z)

    @property
    def is_neutral(self) -> bool:
        return (
            self.move_x == 0.0
            and self.move_z == 0.0
            and self.ascend == 0.0
            and self.face_x is None
            and self.face_z is None
            and self.mobility_request == "keep"
            and not self.held_actions
        )

    @property
    def run(self) -> bool:
        return self.speed_mode == "run"

    def to_dict(self) -> Dict[str, object]:
        return {
            "move_x": self.move_x,
            "move_z": self.move_z,
            "ascend": self.ascend,
            "face_x": self.face_x,
            "face_z": self.face_z,
            "speed_mode": self.speed_mode,
            "mobility_request": self.mobility_request,
            "held_actions": list(self.held_actions),
        }


@dataclass(frozen=True)
class ControllerLease:
    source_id: str
    source_kind: str
    source_epoch: str
    lease_id: str
    generation: int
    priority: int
    last_sequence: int
    accepted_tick: int
    expires_tick: int
    intent: ControlIntentV1
    expires_monotonic_ns: Optional[int] = None


ControlLease = ControllerLease


@dataclass(frozen=True)
class ArbitrationDecision:
    accepted: bool
    disposition: str
    reason: str
    active_lease: Optional[ControllerLease]
    previous_lease: Optional[ControllerLease]
    released: bool = False
    preempted: bool = False


class ControlArbiter:
    """Deterministic single-owner arbitration for continuous mobility intent."""

    def __init__(self, lease_timeout_ms: int = LEASE_TIMEOUT_MS) -> None:
        if isinstance(lease_timeout_ms, bool) or not isinstance(lease_timeout_ms, int):
            raise ValueError("lease_timeout_ms must be an integer")
        if not 50 <= lease_timeout_ms <= 1000:
            raise ValueError("lease_timeout_ms must be in [50, 1000]")
        self.lease_timeout_ms = lease_timeout_ms
        self._active: Optional[ControllerLease] = None
        self._generation = 0
        self._last_sequences: Dict[Tuple[str, str], int] = {}
        self._active_epoch_by_source: Dict[str, str] = {}
        self._retired_epochs: set[Tuple[str, str]] = set()

    @property
    def active_lease(self) -> Optional[ControllerLease]:
        return self._active

    def submit(
        self,
        envelope: CommandEnvelopeV1,
        intent: ControlIntentV1,
        accepted_tick: int,
        accepted_monotonic_ns: Optional[int] = None,
    ) -> ArbitrationDecision:
        if envelope.kind != "control_intent":
            raise ControlValidationError("control arbiter accepts only control_intent commands")
        if envelope.ttl_ms is None or envelope.lease_id is None:
            raise ControlValidationError("control_intent requires ttl_ms and lease_id")
        if isinstance(accepted_tick, bool) or not isinstance(accepted_tick, int) or accepted_tick < 0:
            raise ControlValidationError("accepted_tick must be a non-negative integer")
        if accepted_monotonic_ns is not None and (
            isinstance(accepted_monotonic_ns, bool)
            or not isinstance(accepted_monotonic_ns, int)
            or accepted_monotonic_ns < 0
        ):
            raise ControlValidationError("accepted_monotonic_ns must be a non-negative integer")

        expected_class = _EXPECTED_PRIORITY_CLASS[envelope.source_kind]
        if envelope.priority_class != expected_class:
            return self._reject("unauthorized", "source_kind cannot claim priority_class")

        key = (envelope.source_id, envelope.source_epoch)
        if key in self._retired_epochs:
            return self._reject("stale", "source epoch was retired")
        last_sequence = self._last_sequences.get(key)
        if last_sequence is not None and envelope.source_sequence <= last_sequence:
            return self._reject("stale", "source_sequence must increase")

        active_epoch = self._active_epoch_by_source.get(envelope.source_id)
        epoch_reconnect = active_epoch is not None and active_epoch != envelope.source_epoch
        active = self._active

        if intent.is_neutral:
            self._record_sequence(envelope)
            if active is not None and self._owns(active, envelope, permit_epoch_reconnect=epoch_reconnect):
                previous = active
                self._active = None
                self._activate_epoch(envelope)
                return ArbitrationDecision(True, "released", "neutral intent", None, previous, released=True)
            self._activate_epoch(envelope)
            return ArbitrationDecision(True, "released", "neutral intent with no owned lease", active, active, released=True)

        priority = command_priority(envelope)
        if active is not None:
            same_lease = self._same_lease(active, envelope)
            reconnecting_owner = active.source_id == envelope.source_id and epoch_reconnect
            if not same_lease and not reconnecting_owner and priority <= active.priority:
                return self._reject("unauthorized", "active lease has equal or higher priority")

        previous = active
        preempted = previous is not None and not self._same_lease(previous, envelope)
        self._record_sequence(envelope)
        self._activate_epoch(envelope)
        self._generation += 1
        ttl_ms = min(envelope.ttl_ms, self.lease_timeout_ms)
        ttl_ticks = max(1, int(math.ceil(ttl_ms * TICK_RATE / 1000.0)))
        expires_monotonic_ns = None
        if accepted_monotonic_ns is not None:
            expires_monotonic_ns = accepted_monotonic_ns + ttl_ms * 1_000_000
        self._active = ControllerLease(
            source_id=envelope.source_id,
            source_kind=envelope.source_kind,
            source_epoch=envelope.source_epoch,
            lease_id=envelope.lease_id,
            generation=self._generation,
            priority=priority,
            last_sequence=envelope.source_sequence,
            accepted_tick=accepted_tick,
            expires_tick=accepted_tick + ttl_ticks,
            intent=intent,
            expires_monotonic_ns=expires_monotonic_ns,
        )
        return ArbitrationDecision(
            accepted=True,
            disposition="accepted",
            reason="lease refreshed" if not preempted and previous is not None else "lease acquired",
            active_lease=self._active,
            previous_lease=previous,
            preempted=preempted,
        )

    def expire(
        self,
        current_tick: int,
        monotonic_ns: Optional[int] = None,
    ) -> ArbitrationDecision:
        active = self._active
        if active is None:
            return ArbitrationDecision(False, "unchanged", "no active lease", None, None)
        tick_expired = current_tick >= active.expires_tick
        wall_expired = (
            monotonic_ns is not None
            and active.expires_monotonic_ns is not None
            and monotonic_ns >= active.expires_monotonic_ns
        )
        if not tick_expired and not wall_expired:
            return ArbitrationDecision(False, "unchanged", "lease remains active", active, active)
        self._active = None
        return ArbitrationDecision(True, "expired", "lease TTL elapsed", None, active, released=True)

    def disconnect(self, source_id: str, source_epoch: str) -> ArbitrationDecision:
        active = self._active
        if active is None or active.source_id != source_id or active.source_epoch != source_epoch:
            return ArbitrationDecision(False, "unchanged", "disconnect did not own lease", active, active)
        self._active = None
        return ArbitrationDecision(True, "released", "controller disconnected", None, active, released=True)

    def clear(self, reason: str = "system reset") -> ArbitrationDecision:
        active = self._active
        self._active = None
        return ArbitrationDecision(active is not None, "released", reason, None, active, released=active is not None)

    def last_sequence(self, source_id: str, source_epoch: str) -> Optional[int]:
        return self._last_sequences.get((source_id, source_epoch))

    def _reject(self, disposition: str, reason: str) -> ArbitrationDecision:
        return ArbitrationDecision(False, disposition, reason, self._active, self._active)

    def _record_sequence(self, envelope: CommandEnvelopeV1) -> None:
        self._last_sequences[(envelope.source_id, envelope.source_epoch)] = envelope.source_sequence

    def _activate_epoch(self, envelope: CommandEnvelopeV1) -> None:
        prior = self._active_epoch_by_source.get(envelope.source_id)
        if prior is not None and prior != envelope.source_epoch:
            self._retired_epochs.add((envelope.source_id, prior))
        self._active_epoch_by_source[envelope.source_id] = envelope.source_epoch

    @staticmethod
    def _same_lease(active: ControllerLease, envelope: CommandEnvelopeV1) -> bool:
        return (
            active.source_id == envelope.source_id
            and active.source_epoch == envelope.source_epoch
            and active.lease_id == envelope.lease_id
        )

    @staticmethod
    def _owns(
        active: ControllerLease,
        envelope: CommandEnvelopeV1,
        permit_epoch_reconnect: bool,
    ) -> bool:
        return ControlArbiter._same_lease(active, envelope) or (
            permit_epoch_reconnect and active.source_id == envelope.source_id
        )


def intent_from_envelope(envelope: CommandEnvelopeV1) -> ControlIntentV1:
    if envelope.kind != "control_intent":
        raise CommandValidationError("envelope kind must be control_intent")
    return ControlIntentV1.from_mapping(envelope.payload)


__all__ = [
    "ArbitrationDecision",
    "CONTROL_SCHEMA_VERSION",
    "ControlArbiter",
    "ControlIntentV1",
    "ControlLease",
    "ControlValidationError",
    "ControllerLease",
    "LEASE_TIMEOUT_MS",
    "intent_from_envelope",
]
