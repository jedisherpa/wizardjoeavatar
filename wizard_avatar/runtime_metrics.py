from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, Mapping, Optional


MAX_SEQUENCE = (1 << 53) - 1
MAX_EPOCH_LENGTH = 128
MAX_REASON_LENGTH = 64


def _require_epoch(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_EPOCH_LENGTH:
        raise ValueError(
            "runtime_epoch must be a non-empty string <= {} characters".format(
                MAX_EPOCH_LENGTH
            )
        )
    return value


def _require_sequence(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("sequence must be a non-negative integer")
    if value > MAX_SEQUENCE:
        raise ValueError("sequence exceeds the JSON safe integer range")
    return value


@dataclass(frozen=True)
class SequenceObservation:
    disposition: str
    runtime_epoch: str
    received_sequence: int
    expected_sequence: int
    next_expected_sequence: int
    missing_count: int = 0
    resync_required: bool = False
    previous_runtime_epoch: Optional[str] = None

    @property
    def accepted(self) -> bool:
        return self.disposition in {"accepted", "epoch_changed"}

    def to_dict(self) -> Dict[str, object]:
        return {
            "disposition": self.disposition,
            "runtime_epoch": self.runtime_epoch,
            "received_sequence": self.received_sequence,
            "expected_sequence": self.expected_sequence,
            "next_expected_sequence": self.next_expected_sequence,
            "missing_count": self.missing_count,
            "resync_required": self.resync_required,
            "previous_runtime_epoch": self.previous_runtime_epoch,
        }


@dataclass(frozen=True)
class RuntimeMetricsSnapshot:
    runtime_epoch: str
    next_outgoing_sequence: int
    next_expected_sequence: int
    messages_sent: int
    messages_received: int
    sequence_gaps: int
    missing_messages: int
    stale_messages: int
    epoch_changes: int
    resync_count: int
    resync_reasons: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "resync_reasons", MappingProxyType(dict(self.resync_reasons)))

    def to_dict(self) -> Dict[str, object]:
        return {
            "runtime_epoch": self.runtime_epoch,
            "next_outgoing_sequence": self.next_outgoing_sequence,
            "next_expected_sequence": self.next_expected_sequence,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "sequence_gaps": self.sequence_gaps,
            "missing_messages": self.missing_messages,
            "stale_messages": self.stale_messages,
            "epoch_changes": self.epoch_changes,
            "resync_count": self.resync_count,
            "resync_reasons": dict(self.resync_reasons),
        }


class RuntimeMetrics:
    """Track one ordered transport stream across runtime epoch changes."""

    def __init__(self, runtime_epoch: str) -> None:
        self.runtime_epoch = _require_epoch(runtime_epoch)
        self._next_outgoing_sequence = 0
        self._next_expected_sequence = 0
        self._messages_sent = 0
        self._messages_received = 0
        self._sequence_gaps = 0
        self._missing_messages = 0
        self._stale_messages = 0
        self._epoch_changes = 0
        self._resync_count = 0
        self._resync_reasons: Counter[str] = Counter()

    def next_sequence(self) -> int:
        if self._next_outgoing_sequence > MAX_SEQUENCE:
            raise OverflowError("transport sequence exhausted")
        sequence = self._next_outgoing_sequence
        self._next_outgoing_sequence += 1
        self._messages_sent += 1
        return sequence

    def begin_epoch(self, runtime_epoch: str) -> None:
        next_epoch = _require_epoch(runtime_epoch)
        if next_epoch == self.runtime_epoch:
            return
        self.runtime_epoch = next_epoch
        self._next_outgoing_sequence = 0
        self._next_expected_sequence = 0
        self._epoch_changes += 1

    def observe_sequence(self, runtime_epoch: str, sequence: int) -> SequenceObservation:
        observed_epoch = _require_epoch(runtime_epoch)
        observed_sequence = _require_sequence(sequence)
        self._messages_received += 1

        if observed_epoch != self.runtime_epoch:
            previous_epoch = self.runtime_epoch
            self.begin_epoch(observed_epoch)
            self._next_expected_sequence = observed_sequence + 1
            return SequenceObservation(
                disposition="epoch_changed",
                runtime_epoch=observed_epoch,
                received_sequence=observed_sequence,
                expected_sequence=0,
                next_expected_sequence=self._next_expected_sequence,
                resync_required=True,
                previous_runtime_epoch=previous_epoch,
            )

        expected = self._next_expected_sequence
        if observed_sequence < expected:
            self._stale_messages += 1
            return SequenceObservation(
                disposition="stale",
                runtime_epoch=observed_epoch,
                received_sequence=observed_sequence,
                expected_sequence=expected,
                next_expected_sequence=expected,
            )
        if observed_sequence > expected:
            missing = observed_sequence - expected
            self._sequence_gaps += 1
            self._missing_messages += missing
            self._next_expected_sequence = observed_sequence + 1
            return SequenceObservation(
                disposition="gap",
                runtime_epoch=observed_epoch,
                received_sequence=observed_sequence,
                expected_sequence=expected,
                next_expected_sequence=self._next_expected_sequence,
                missing_count=missing,
                resync_required=True,
            )

        self._next_expected_sequence += 1
        return SequenceObservation(
            disposition="accepted",
            runtime_epoch=observed_epoch,
            received_sequence=observed_sequence,
            expected_sequence=expected,
            next_expected_sequence=self._next_expected_sequence,
        )

    def record_resync(self, reason: str = "explicit") -> None:
        if not isinstance(reason, str) or not reason or len(reason) > MAX_REASON_LENGTH:
            raise ValueError(
                "resync reason must be a non-empty string <= {} characters".format(
                    MAX_REASON_LENGTH
                )
            )
        self._resync_count += 1
        self._resync_reasons[reason] += 1

    def snapshot(self) -> RuntimeMetricsSnapshot:
        return RuntimeMetricsSnapshot(
            runtime_epoch=self.runtime_epoch,
            next_outgoing_sequence=self._next_outgoing_sequence,
            next_expected_sequence=self._next_expected_sequence,
            messages_sent=self._messages_sent,
            messages_received=self._messages_received,
            sequence_gaps=self._sequence_gaps,
            missing_messages=self._missing_messages,
            stale_messages=self._stale_messages,
            epoch_changes=self._epoch_changes,
            resync_count=self._resync_count,
            resync_reasons=self._resync_reasons,
        )


RuntimeTransportMetrics = RuntimeMetrics


__all__ = [
    "RuntimeMetrics",
    "RuntimeMetricsSnapshot",
    "RuntimeTransportMetrics",
    "SequenceObservation",
]
