from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Dict, Mapping, Optional, Sequence, Tuple


MEDIA_SESSION_SCHEMA_VERSION = 1
MEDIA_SESSION_MAX_BODY_BYTES = 16 * 1024
DEFAULT_CLOCK_FRESHNESS_US = 1_500_000
DEFAULT_SESSION_LEASE_US = 5_000_000
DEFAULT_DEDUP_CAPACITY = 4096
SUPPORTED_RATE_MILLI = (500, 750, 1000, 1250, 1500, 2000)
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

SNAPSHOT_CAUSES = frozenset(
    {
        "initial",
        "mount",
        "loadedmetadata",
        "play",
        "play_intent",
        "playing",
        "pause",
        "waiting",
        "stalled",
        "seeking",
        "seeked",
        "ratechange",
        "durationchange",
        "ended",
        "emptied",
        "error",
        "stop",
        "trackchange",
        "chapterchange",
        "visibilitychange",
        "preferencechange",
        "heartbeat",
        "pagehide",
        "reconnect",
    }
)
PLAYBACK_STATES = frozenset({"empty", "loading", "paused", "playing", "buffering", "seeking", "ended", "stopped", "error"})
MEDIA_KINDS = frozenset({"audiobook", "podcast", "music", "video", "speech", "tts"})
SOURCE_SLOTS = frozenset({"main", "speech"})
SOURCE_KINDS = frozenset(
    {"library", "podcast", "generated", "studio_chapter", "managed_import", "linked_local", "speech", "tts", "speaker"}
)
PERFORMANCE_MODES = frozenset({"narrative", "music", "speech", "none"})
MOTION_PROFILES = frozenset({"full", "reduced", "still"})
KNOWN_CHANNELS = frozenset(
    {
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
    }
)
ACK_DISPOSITIONS = frozenset(
    {"accepted", "duplicate", "stale", "rejected", "resync_required", "controller_conflict", "unavailable"}
)
SCHEDULER_STATES = frozenset(
    {
        "no_session",
        "loading_score",
        "ready",
        "playing",
        "paused",
        "buffering",
        "seeking",
        "clock_uncertain",
        "stopped",
        "ended",
        "scoreless",
        "error",
    }
)


class MediaSessionError(ValueError):
    """Stable error with no caller-provided content in its public message."""

    def __init__(self, code: str, message: str, path: str = "$") -> None:
        super().__init__(message)
        self.code = code
        self.path = path


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_exact_fields(value: Mapping[str, object], required: Sequence[str], path: str) -> None:
    expected = set(required)
    unknown = set(value) - expected
    missing = expected - set(value)
    if unknown:
        raise MediaSessionError("unknown_field", "snapshot contains an unknown field", path)
    if missing:
        raise MediaSessionError("missing_field", "snapshot is missing a required field", path)


def _require_mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise MediaSessionError("invalid_type", "expected an object", path)
    return value  # type: ignore[return-value]


def _require_int(value: object, path: str, minimum: int = 0, maximum: Optional[int] = None) -> int:
    if not _is_int(value) or int(value) < minimum or (maximum is not None and int(value) > maximum):
        raise MediaSessionError("invalid_type", "expected a bounded integer", path)
    return int(value)


def _require_id(value: object, path: str) -> str:
    if not isinstance(value, str) or ID_PATTERN.fullmatch(value) is None:
        raise MediaSessionError("invalid_id", "expected a stable identifier", path)
    return value


def _require_optional_id(value: object, path: str) -> Optional[str]:
    if value is None:
        return None
    return _require_id(value, path)


def _require_pattern(value: object, pattern: re.Pattern[str], path: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise MediaSessionError("invalid_id", "expected a contract identifier", path)
    return value


def _require_sha256(value: object, path: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise MediaSessionError("invalid_hash", "expected a sha256 reference", path)
    return value


def _require_optional_sha256(value: object, path: str) -> Optional[str]:
    if value is None:
        return None
    return _require_sha256(value, path)


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    frozen: Dict[str, object] = {}
    for key, item in value.items():
        if isinstance(item, Mapping):
            frozen[key] = _freeze_mapping(item)  # type: ignore[arg-type]
        elif isinstance(item, (list, tuple)):
            frozen[key] = tuple(item)
        else:
            frozen[key] = item
    return MappingProxyType(frozen)


@dataclass(frozen=True)
class MediaIdentityV1:
    media_id: str
    media_sha256: Optional[str]
    kind: str
    source_slot: str
    source_kind: str
    book_id: Optional[str]
    chapter_id: Optional[str]
    duration_ms: Optional[int]

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "MediaIdentityV1":
        _require_exact_fields(
            value,
            ("media_id", "media_sha256", "kind", "source_slot", "source_kind", "book_id", "chapter_id", "duration_ms"),
            "$.media",
        )
        kind = value.get("kind")
        if kind not in MEDIA_KINDS:
            raise MediaSessionError("invalid_enum", "unsupported media kind", "$.media.kind")
        source_slot = value.get("source_slot")
        if source_slot not in SOURCE_SLOTS:
            raise MediaSessionError("invalid_enum", "unsupported media source slot", "$.media.source_slot")
        if source_slot == "speech" and kind not in {"speech", "tts"}:
            raise MediaSessionError("invalid_enum", "speech slot requires speech or tts kind", "$.media")
        source_kind = value.get("source_kind")
        if source_kind not in SOURCE_KINDS:
            raise MediaSessionError("invalid_enum", "unsupported privacy-safe source kind", "$.media.source_kind")
        media_id = _require_id(value.get("media_id"), "$.media.media_id")
        media_sha256 = _require_optional_sha256(value.get("media_sha256"), "$.media.media_sha256")
        if media_sha256 is not None and media_id != "media:sha256:" + media_sha256.split(":", 1)[1]:
            raise MediaSessionError("hash_mismatch", "media identity does not match its digest", "$.media.media_id")
        duration_value = value.get("duration_ms")
        duration_ms = None if duration_value is None else _require_int(duration_value, "$.media.duration_ms", minimum=1)
        return cls(
            media_id=media_id,
            media_sha256=media_sha256,
            kind=str(kind),
            source_slot=str(source_slot),
            source_kind=str(source_kind),
            book_id=_require_optional_id(value.get("book_id"), "$.media.book_id"),
            chapter_id=_require_optional_id(value.get("chapter_id"), "$.media.chapter_id"),
            duration_ms=duration_ms,
        )

    def to_dict(self) -> Mapping[str, object]:
        return {
            "media_id": self.media_id,
            "media_sha256": self.media_sha256,
            "kind": self.kind,
            "source_slot": self.source_slot,
            "source_kind": self.source_kind,
            "book_id": self.book_id,
            "chapter_id": self.chapter_id,
            "duration_ms": self.duration_ms,
        }


@dataclass(frozen=True)
class PlaybackSnapshotV1:
    state: str
    position_ms: int
    rate_milli: int
    ready_state: int
    seeking: bool

    @classmethod
    def from_mapping(cls, value: Mapping[str, object], duration_ms: Optional[int]) -> "PlaybackSnapshotV1":
        _require_exact_fields(value, ("state", "position_ms", "rate_milli", "ready_state", "seeking"), "$.playback")
        state = value.get("state")
        if state not in PLAYBACK_STATES:
            raise MediaSessionError("invalid_enum", "unsupported playback state", "$.playback.state")
        position = _require_int(value.get("position_ms"), "$.playback.position_ms")
        if duration_ms is not None and position > duration_ms:
            raise MediaSessionError("position_out_of_bounds", "playback position exceeds duration", "$.playback.position_ms")
        rate = _require_int(value.get("rate_milli"), "$.playback.rate_milli", minimum=1)
        if rate not in SUPPORTED_RATE_MILLI:
            raise MediaSessionError("unsupported_rate", "playback rate is not supported", "$.playback.rate_milli")
        seeking = value.get("seeking")
        if not isinstance(seeking, bool):
            raise MediaSessionError("invalid_type", "seeking must be a boolean", "$.playback.seeking")
        return cls(
            state=str(state),
            position_ms=position,
            rate_milli=rate,
            ready_state=_require_int(value.get("ready_state"), "$.playback.ready_state", maximum=4),
            seeking=seeking,
        )

    def to_dict(self) -> Mapping[str, object]:
        return {
            "state": self.state,
            "position_ms": self.position_ms,
            "rate_milli": self.rate_milli,
            "ready_state": self.ready_state,
            "seeking": self.seeking,
        }


@dataclass(frozen=True)
class PerformanceSelectionV1:
    mode: str
    score_id: Optional[str]
    score_revision: Optional[int]
    score_sha256: Optional[str]
    character_id: str
    character_package_sha256: Optional[str]
    intensity_milli: int
    motion_profile: str
    disabled_channels: Tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "PerformanceSelectionV1":
        _require_exact_fields(
            value,
            (
                "character_id",
                "mode",
                "score_id",
                "score_revision",
                "score_sha256",
                "character_package_sha256",
                "intensity_milli",
                "motion_profile",
                "disabled_channels",
            ),
            "$.performance",
        )
        motion_profile = value.get("motion_profile")
        if motion_profile not in MOTION_PROFILES:
            raise MediaSessionError("invalid_enum", "unsupported motion profile", "$.performance.motion_profile")
        disabled_value = value.get("disabled_channels")
        if not isinstance(disabled_value, (list, tuple)):
            raise MediaSessionError("invalid_type", "disabled_channels must be an array", "$.performance.disabled_channels")
        disabled: list[str] = []
        for channel in disabled_value:
            if not isinstance(channel, str) or channel not in KNOWN_CHANNELS:
                raise MediaSessionError("invalid_enum", "unsupported disabled channel", "$.performance.disabled_channels")
            if channel in disabled:
                raise MediaSessionError("invalid_type", "disabled channels must be unique", "$.performance.disabled_channels")
            disabled.append(channel)
        if disabled != sorted(disabled):
            raise MediaSessionError("invalid_type", "disabled channels must be sorted", "$.performance.disabled_channels")
        mode = value.get("mode")
        if mode not in PERFORMANCE_MODES:
            raise MediaSessionError("invalid_enum", "unsupported performance mode", "$.performance.mode")
        score_id = _require_optional_id(value.get("score_id"), "$.performance.score_id")
        revision_value = value.get("score_revision")
        score_revision = None if revision_value is None else _require_int(
            revision_value, "$.performance.score_revision", minimum=1
        )
        score_sha256 = _require_optional_sha256(value.get("score_sha256"), "$.performance.score_sha256")
        score_values = (score_id, score_revision, score_sha256)
        if any(item is None for item in score_values) and any(item is not None for item in score_values):
            raise MediaSessionError("invalid_binding", "score binding must be complete or absent", "$.performance")
        if mode == "none" and any(item is not None for item in score_values):
            raise MediaSessionError("invalid_binding", "none mode cannot bind a score", "$.performance")
        return cls(
            mode=str(mode),
            score_id=score_id,
            score_revision=score_revision,
            score_sha256=score_sha256,
            character_id=_require_id(value.get("character_id"), "$.performance.character_id"),
            character_package_sha256=_require_optional_sha256(
                value.get("character_package_sha256"), "$.performance.character_package_sha256"
            ),
            intensity_milli=_require_int(value.get("intensity_milli"), "$.performance.intensity_milli", maximum=1000),
            motion_profile=str(motion_profile),
            disabled_channels=tuple(disabled),
        )

    def to_dict(self) -> Mapping[str, object]:
        return {
            "mode": self.mode,
            "score_id": self.score_id,
            "score_revision": self.score_revision,
            "score_sha256": self.score_sha256,
            "character_id": self.character_id,
            "character_package_sha256": self.character_package_sha256,
            "intensity_milli": self.intensity_milli,
            "motion_profile": self.motion_profile,
            "disabled_channels": list(self.disabled_channels),
        }


@dataclass(frozen=True)
class MediaSessionSnapshotV1:
    schema_version: int
    message_id: str
    connector_session_id: str
    sequence: int
    cause: str
    sampled_at_monotonic_ms: int
    media_epoch: int
    media: MediaIdentityV1
    playback: PlaybackSnapshotV1
    performance: PerformanceSelectionV1

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "MediaSessionSnapshotV1":
        _require_exact_fields(
            value,
            (
                "schema_version",
                "message_id",
                "connector_session_id",
                "sequence",
                "cause",
                "sampled_at_monotonic_ms",
                "media_epoch",
                "media",
                "playback",
                "performance",
            ),
            "$",
        )
        if value.get("schema_version") != MEDIA_SESSION_SCHEMA_VERSION or isinstance(value.get("schema_version"), bool):
            raise MediaSessionError("schema_version_unsupported", "media session schema must be version 1")
        cause = value.get("cause")
        if cause not in SNAPSHOT_CAUSES:
            raise MediaSessionError("invalid_enum", "unsupported snapshot cause", "$.cause")
        media = MediaIdentityV1.from_mapping(_require_mapping(value.get("media"), "$.media"))
        return cls(
            schema_version=MEDIA_SESSION_SCHEMA_VERSION,
            message_id=_require_pattern(value.get("message_id"), UUID_V4_PATTERN, "$.message_id"),
            connector_session_id=_require_pattern(
                value.get("connector_session_id"), UUID_V4_PATTERN, "$.connector_session_id"
            ),
            sequence=_require_int(value.get("sequence"), "$.sequence"),
            cause=str(cause),
            sampled_at_monotonic_ms=_require_int(
                value.get("sampled_at_monotonic_ms"), "$.sampled_at_monotonic_ms"
            ),
            media_epoch=_require_int(value.get("media_epoch"), "$.media_epoch"),
            media=media,
            playback=PlaybackSnapshotV1.from_mapping(
                _require_mapping(value.get("playback"), "$.playback"), media.duration_ms
            ),
            performance=PerformanceSelectionV1.from_mapping(
                _require_mapping(value.get("performance"), "$.performance")
            ),
        )

    @classmethod
    def from_json(cls, data: bytes) -> "MediaSessionSnapshotV1":
        if len(data) > MEDIA_SESSION_MAX_BODY_BYTES:
            raise MediaSessionError("body_too_large", "snapshot exceeds the 16 KiB limit")
        def reject_duplicates(pairs: Sequence[Tuple[str, object]]) -> Mapping[str, object]:
            result: Dict[str, object] = {}
            for key, item in pairs:
                if key in result:
                    raise MediaSessionError("duplicate_json_key", "duplicate JSON object key")
                result[key] = item
            return result

        try:
            value = json.loads(data.decode("utf-8"), object_pairs_hook=reject_duplicates)
        except MediaSessionError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MediaSessionError("schema_invalid", "snapshot is not valid UTF-8 JSON") from exc
        return cls.from_mapping(_require_mapping(value, "$"))

    def to_dict(self) -> Mapping[str, object]:
        return {
            "schema_version": self.schema_version,
            "message_id": self.message_id,
            "connector_session_id": self.connector_session_id,
            "sequence": self.sequence,
            "cause": self.cause,
            "sampled_at_monotonic_ms": self.sampled_at_monotonic_ms,
            "media_epoch": self.media_epoch,
            "media": self.media.to_dict(),
            "playback": self.playback.to_dict(),
            "performance": self.performance.to_dict(),
        }

    def fingerprint(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class MediaSessionAckV1:
    schema_version: int
    connector_session_id: str
    accepted_sequence: int
    accepted_media_epoch: int
    disposition: str
    wizard_runtime_epoch: str
    resync_required: bool
    scheduler_state: str
    error: Optional[Mapping[str, str]]
    capabilities: Mapping[str, object]

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "MediaSessionAckV1":
        _require_exact_fields(
            value,
            (
                "schema_version",
                "connector_session_id",
                "accepted_sequence",
                "accepted_media_epoch",
                "disposition",
                "wizard_runtime_epoch",
                "resync_required",
                "scheduler_state",
                "error",
                "capabilities",
            ),
            "$",
        )
        if value.get("schema_version") != 1 or isinstance(value.get("schema_version"), bool):
            raise MediaSessionError("schema_version_unsupported", "media session ack schema must be version 1")
        resync_required = value.get("resync_required")
        if not isinstance(resync_required, bool):
            raise MediaSessionError("invalid_type", "resync_required must be a boolean", "$.resync_required")
        error_value = value.get("error")
        error = None if error_value is None else _require_mapping(error_value, "$.error")
        capabilities = _require_mapping(value.get("capabilities"), "$.capabilities")
        _require_exact_fields(
            capabilities,
            ("media_session_schema", "max_snapshot_hz", "supported_rate_milli", "motion_profiles"),
            "$.capabilities",
        )
        if capabilities.get("media_session_schema") != 1:
            raise MediaSessionError("schema_version_unsupported", "capability schema must be version 1")
        rates = capabilities.get("supported_rate_milli")
        if not isinstance(rates, (list, tuple)) or tuple(rates) != SUPPORTED_RATE_MILLI:
            raise MediaSessionError("invalid_enum", "supported rates must match V1", "$.capabilities.supported_rate_milli")
        profiles = capabilities.get("motion_profiles")
        if profiles != ["full", "reduced", "still"] and profiles != ("full", "reduced", "still"):
            raise MediaSessionError("invalid_enum", "motion profiles must match V1", "$.capabilities.motion_profiles")
        disposition = value.get("disposition")
        scheduler_state = value.get("scheduler_state")
        return cls(
            schema_version=1,
            connector_session_id=_require_pattern(
                value.get("connector_session_id"), UUID_V4_PATTERN, "$.connector_session_id"
            ),
            accepted_sequence=_require_int(value.get("accepted_sequence"), "$.accepted_sequence"),
            accepted_media_epoch=_require_int(
                value.get("accepted_media_epoch"), "$.accepted_media_epoch"
            ),
            disposition=str(disposition),
            wizard_runtime_epoch=_require_id(value.get("wizard_runtime_epoch"), "$.wizard_runtime_epoch"),
            resync_required=resync_required,
            scheduler_state=str(scheduler_state),
            error=error,  # type: ignore[arg-type]
            capabilities={
                "media_session_schema": 1,
                "max_snapshot_hz": _require_int(
                    capabilities.get("max_snapshot_hz"), "$.capabilities.max_snapshot_hz", minimum=1, maximum=60
                ),
                "supported_rate_milli": tuple(rates),
                "motion_profiles": tuple(profiles),
            },
        )

    @classmethod
    def from_json(cls, data: bytes) -> "MediaSessionAckV1":
        if len(data) > MEDIA_SESSION_MAX_BODY_BYTES:
            raise MediaSessionError("body_too_large", "ack exceeds the 16 KiB limit")
        try:
            value = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MediaSessionError("schema_invalid", "ack is not valid UTF-8 JSON") from exc
        return cls.from_mapping(_require_mapping(value, "$"))

    def __post_init__(self) -> None:
        if self.disposition not in ACK_DISPOSITIONS:
            raise MediaSessionError("invalid_enum", "unsupported acknowledgement disposition")
        if self.scheduler_state not in SCHEDULER_STATES:
            raise MediaSessionError("invalid_enum", "unsupported scheduler state")
        _require_pattern(self.connector_session_id, UUID_V4_PATTERN, "connector_session_id")
        _require_id(self.wizard_runtime_epoch, "wizard_runtime_epoch")
        if self.error is not None:
            _require_exact_fields(self.error, ("code",), "error")
            code = self.error.get("code")
            if not isinstance(code, str) or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code) is None:
                raise MediaSessionError("invalid_id", "invalid acknowledgement error code", "error.code")
            object.__setattr__(self, "error", _freeze_mapping(self.error))
        object.__setattr__(self, "capabilities", _freeze_mapping(self.capabilities))

    @property
    def error_code(self) -> Optional[str]:
        return None if self.error is None else str(self.error["code"])

    @property
    def media_epoch(self) -> int:
        return self.accepted_media_epoch

    def to_dict(self) -> Mapping[str, object]:
        return {
            "schema_version": self.schema_version,
            "connector_session_id": self.connector_session_id,
            "accepted_sequence": self.accepted_sequence,
            "accepted_media_epoch": self.accepted_media_epoch,
            "disposition": self.disposition,
            "wizard_runtime_epoch": self.wizard_runtime_epoch,
            "resync_required": self.resync_required,
            "scheduler_state": self.scheduler_state,
            "error": None if self.error is None else {"code": self.error["code"]},
            "capabilities": {
                "media_session_schema": self.capabilities["media_session_schema"],
                "max_snapshot_hz": self.capabilities["max_snapshot_hz"],
                "supported_rate_milli": list(self.capabilities["supported_rate_milli"]),
                "motion_profiles": list(self.capabilities["motion_profiles"]),
            },
        }


class MediaClockEstimator:
    """Interpolates only from the newest accepted authoritative snapshot."""

    def __init__(self, freshness_limit_us: int = DEFAULT_CLOCK_FRESHNESS_US) -> None:
        self.freshness_limit_us = _require_int(freshness_limit_us, "freshness_limit_us", minimum=1)
        self._snapshot: Optional[MediaSessionSnapshotV1] = None
        self._receipt_monotonic_us: Optional[int] = None

    @property
    def snapshot(self) -> Optional[MediaSessionSnapshotV1]:
        return self._snapshot

    @property
    def receipt_monotonic_us(self) -> Optional[int]:
        return self._receipt_monotonic_us

    def observe(self, snapshot: MediaSessionSnapshotV1, receipt_monotonic_us: int) -> None:
        receipt = _require_int(receipt_monotonic_us, "receipt_monotonic_us")
        self._snapshot = snapshot
        self._receipt_monotonic_us = receipt

    def age_us(self, now_monotonic_us: int) -> Optional[int]:
        now = _require_int(now_monotonic_us, "now_monotonic_us")
        if self._receipt_monotonic_us is None:
            return None
        if now < self._receipt_monotonic_us:
            raise MediaSessionError("clock_invalid", "monotonic time moved backwards")
        return now - self._receipt_monotonic_us

    def is_fresh(self, now_monotonic_us: int) -> bool:
        age = self.age_us(now_monotonic_us)
        return age is not None and age <= self.freshness_limit_us

    def position_at(self, now_monotonic_us: int) -> Optional[int]:
        if self._snapshot is None:
            return None
        age = self.age_us(now_monotonic_us)
        assert age is not None
        position = self._snapshot.playback.position_ms
        if self._snapshot.playback.state == "playing" and age <= self.freshness_limit_us:
            position += (age * self._snapshot.playback.rate_milli) // 1_000_000
        if self._snapshot.media.duration_ms is not None:
            position = min(self._snapshot.media.duration_ms, position)
        return max(0, position)


@dataclass(frozen=True)
class MediaSessionAcceptance:
    ack: MediaSessionAckV1
    snapshot: Optional[MediaSessionSnapshotV1]
    hard_reconcile: bool
    reconciliation_generation: int
    clock_error_ms: Optional[int]


@dataclass(frozen=True)
class MediaSessionDiagnostics:
    scheduler_state: str
    active_session_suffix: Optional[str]
    active_source_slot: Optional[str]
    accepted_sequence: Optional[int]
    media_epoch: Optional[int]
    reconciliation_generation: int
    snapshot_age_ms: Optional[int]
    estimated_position_ms: Optional[int]
    media_hash_prefix: Optional[str]
    score_hash_prefix: Optional[str]
    last_disposition: Optional[str]
    last_error_code: Optional[str]

    def to_dict(self) -> Mapping[str, object]:
        return {
            "scheduler_state": self.scheduler_state,
            "active_session_suffix": self.active_session_suffix,
            "active_source_slot": self.active_source_slot,
            "accepted_sequence": self.accepted_sequence,
            "media_epoch": self.media_epoch,
            "reconciliation_generation": self.reconciliation_generation,
            "snapshot_age_ms": self.snapshot_age_ms,
            "estimated_position_ms": self.estimated_position_ms,
            "media_hash_prefix": self.media_hash_prefix,
            "score_hash_prefix": self.score_hash_prefix,
            "last_disposition": self.last_disposition,
            "last_error_code": self.last_error_code,
        }


class MediaSessionCoordinator:
    """Single-controller full-state reconciliation outside the command inbox."""

    def __init__(
        self,
        wizard_runtime_epoch: str,
        dedup_capacity: int = DEFAULT_DEDUP_CAPACITY,
        session_lease_us: int = DEFAULT_SESSION_LEASE_US,
    ) -> None:
        self.wizard_runtime_epoch = _require_id(wizard_runtime_epoch, "wizard_runtime_epoch")
        self.dedup_capacity = _require_int(dedup_capacity, "dedup_capacity", minimum=1)
        self.session_lease_us = _require_int(session_lease_us, "session_lease_us", minimum=1)
        self.clock = MediaClockEstimator()
        self._active_session_id: Optional[str] = None
        self._last_snapshot: Optional[MediaSessionSnapshotV1] = None
        self._last_receipt_us: Optional[int] = None
        self._last_accepted_sequence: Optional[int] = None
        self._slot_snapshots: Dict[str, MediaSessionSnapshotV1] = {}
        self._slot_receipts: Dict[str, int] = {}
        self._slot_clocks: Dict[str, MediaClockEstimator] = {}
        self._seen: "OrderedDict[Tuple[str, int], str]" = OrderedDict()
        self._reconciliation_generation = 0
        self._requires_reconnect = False
        self._last_acceptance: Optional[MediaSessionAcceptance] = None

    @property
    def accepted_snapshot(self) -> Optional[MediaSessionSnapshotV1]:
        return self._last_snapshot

    @property
    def reconciliation_generation(self) -> int:
        return self._reconciliation_generation

    @property
    def last_acceptance(self) -> Optional[MediaSessionAcceptance]:
        return self._last_acceptance

    def _scheduler_state(self, snapshot: Optional[MediaSessionSnapshotV1]) -> str:
        if snapshot is None:
            return "no_session"
        return {
            "playing": "playing",
            "paused": "paused",
            "buffering": "buffering",
            "seeking": "seeking",
            "stopped": "stopped",
            "ended": "ended",
            "error": "error",
            "loading": "loading_score",
            "empty": "no_session",
        }[snapshot.playback.state]

    def _ack(
        self,
        snapshot: MediaSessionSnapshotV1,
        disposition: str,
        error_code: Optional[str] = None,
        resync_required: bool = False,
    ) -> MediaSessionAckV1:
        accepted_sequence = self._last_accepted_sequence if self._last_accepted_sequence is not None else snapshot.sequence
        media_epoch = self._last_snapshot.media_epoch if self._last_snapshot is not None else snapshot.media_epoch
        return MediaSessionAckV1(
            schema_version=1,
            connector_session_id=snapshot.connector_session_id,
            accepted_sequence=accepted_sequence,
            accepted_media_epoch=media_epoch,
            disposition=disposition,
            wizard_runtime_epoch=self.wizard_runtime_epoch,
            resync_required=resync_required,
            scheduler_state=self._scheduler_state(self._last_snapshot),
            error=None if error_code is None else {"code": error_code},
            capabilities={
                "media_session_schema": 1,
                "max_snapshot_hz": 8,
                "supported_rate_milli": SUPPORTED_RATE_MILLI,
                "motion_profiles": ("full", "reduced", "still"),
            },
        )

    def _remember(self, snapshot: MediaSessionSnapshotV1) -> None:
        self._seen[(snapshot.connector_session_id, snapshot.sequence)] = snapshot.fingerprint()
        self._seen.move_to_end((snapshot.connector_session_id, snapshot.sequence))
        while len(self._seen) > self.dedup_capacity:
            self._seen.popitem(last=False)

    @staticmethod
    def _speech_owns_performance(snapshot: MediaSessionSnapshotV1) -> bool:
        # Speech owns the performance only while it is audible or actively
        # continuing an already-audible utterance. Startup/loading and paused
        # elements must not strand the runtime on a silent speech clock.
        return snapshot.playback.state in {"playing", "buffering", "seeking"}

    def _select_active_snapshot(
        self, incoming: MediaSessionSnapshotV1
    ) -> Optional[MediaSessionSnapshotV1]:
        # The connector contract carries full-state snapshots, not independent
        # per-element telemetry. A main snapshot received after speech therefore
        # means the connector has already restored main as its active source.
        if incoming.media.source_slot == "main":
            return incoming
        if self._speech_owns_performance(incoming):
            return incoming
        return self._slot_snapshots.get("main")

    def _activate(self, snapshot: Optional[MediaSessionSnapshotV1]) -> None:
        self._last_snapshot = snapshot
        if snapshot is None:
            self.clock = MediaClockEstimator()
            return
        slot = snapshot.media.source_slot
        self.clock = self._slot_clocks[slot]

    def _finish(
        self,
        ack: MediaSessionAckV1,
        snapshot: Optional[MediaSessionSnapshotV1],
        hard_reconcile: bool,
        clock_error_ms: Optional[int],
    ) -> MediaSessionAcceptance:
        acceptance = MediaSessionAcceptance(
            ack=ack,
            snapshot=snapshot,
            hard_reconcile=hard_reconcile,
            reconciliation_generation=self._reconciliation_generation,
            clock_error_ms=clock_error_ms,
        )
        self._last_acceptance = acceptance
        return acceptance

    def accept(self, snapshot: MediaSessionSnapshotV1, receipt_monotonic_us: int) -> MediaSessionAckV1:
        return self.accept_with_result(snapshot, receipt_monotonic_us).ack

    def accept_with_result(
        self, snapshot: MediaSessionSnapshotV1, receipt_monotonic_us: int
    ) -> MediaSessionAcceptance:
        receipt = _require_int(receipt_monotonic_us, "receipt_monotonic_us")
        key = (snapshot.connector_session_id, snapshot.sequence)
        fingerprint = snapshot.fingerprint()
        prior_fingerprint = self._seen.get(key)
        if prior_fingerprint is not None:
            if prior_fingerprint == fingerprint:
                return self._finish(self._ack(snapshot, "duplicate", "duplicate_snapshot"), None, False, None)
            return self._finish(
                self._ack(snapshot, "resync_required", "sequence_payload_conflict", True), None, False, None
            )

        if self._requires_reconnect and snapshot.cause != "reconnect":
            return self._finish(self._ack(snapshot, "resync_required", "resync_required", True), None, False, None)
        if (
            self._requires_reconnect
            and self._last_snapshot is not None
            and snapshot.connector_session_id == self._active_session_id
            and snapshot.media.source_slot != self._last_snapshot.media.source_slot
        ):
            return self._finish(self._ack(snapshot, "resync_required", "active_source_required", True), None, False, None)

        if self._active_session_id is not None and snapshot.connector_session_id != self._active_session_id:
            lease_fresh = self._last_receipt_us is not None and receipt - self._last_receipt_us <= self.session_lease_us
            if lease_fresh:
                return self._finish(self._ack(snapshot, "rejected", "session_conflict"), None, False, None)
            self._slot_snapshots.clear()
            self._slot_receipts.clear()
            self._slot_clocks.clear()
            self._last_snapshot = None
            self._last_accepted_sequence = None
            self.clock = MediaClockEstimator()
        elif self._last_receipt_us is not None and receipt < self._last_receipt_us:
            raise MediaSessionError("clock_invalid", "monotonic receipt time moved backwards")

        previous_active = self._last_snapshot if snapshot.connector_session_id == self._active_session_id else None
        previous_slot = self._slot_snapshots.get(snapshot.media.source_slot)
        if self._last_accepted_sequence is not None and snapshot.connector_session_id == self._active_session_id:
            if snapshot.sequence <= self._last_accepted_sequence:
                self._remember(snapshot)
                return self._finish(self._ack(snapshot, "stale", "stale_sequence"), None, False, None)
        if previous_slot is not None:
            if snapshot.media_epoch < previous_slot.media_epoch:
                self._remember(snapshot)
                return self._finish(self._ack(snapshot, "stale", "stale_media_epoch"), None, False, None)
            identity_changed = (
                snapshot.media.media_id != previous_slot.media.media_id
                or snapshot.media.media_sha256 != previous_slot.media.media_sha256
                or snapshot.performance.score_id != previous_slot.performance.score_id
                or snapshot.performance.score_sha256 != previous_slot.performance.score_sha256
                or snapshot.performance.character_package_sha256 != previous_slot.performance.character_package_sha256
            )
            if identity_changed and snapshot.media_epoch == previous_slot.media_epoch:
                return self._finish(
                    self._ack(snapshot, "resync_required", "reconcile_required", True), None, False, None
                )

        slot_clock = self._slot_clocks.get(snapshot.media.source_slot)
        expected_position = slot_clock.position_at(receipt) if slot_clock is not None else None
        clock_error = (
            snapshot.playback.position_ms - expected_position if expected_position is not None else None
        )

        slot = snapshot.media.source_slot
        if slot_clock is None:
            slot_clock = MediaClockEstimator()
            self._slot_clocks[slot] = slot_clock
        slot_clock.observe(snapshot, receipt)
        self._slot_snapshots[slot] = snapshot
        self._slot_receipts[slot] = receipt
        new_active = self._select_active_snapshot(snapshot)
        active_changed = (
            previous_active is None
            or new_active is None
            or previous_active.media.source_slot != new_active.media.source_slot
            or previous_active.media.media_id != new_active.media.media_id
            or previous_active.media.media_sha256 != new_active.media.media_sha256
            or previous_active.media_epoch != new_active.media_epoch
        )
        updates_active_slot = new_active is snapshot
        hard_reconcile = bool(
            active_changed
            or (
                updates_active_slot
                and (
                    previous_slot is None
                    or snapshot.media_epoch > previous_slot.media_epoch
                    or snapshot.cause
                    in {"seeking", "seeked", "reconnect", "trackchange", "chapterchange", "stop", "emptied", "error"}
                    or (clock_error is not None and abs(clock_error) > 100)
                    or self._requires_reconnect
                )
            )
        )
        if hard_reconcile:
            self._reconciliation_generation += 1

        self._active_session_id = snapshot.connector_session_id
        self._last_receipt_us = receipt
        self._last_accepted_sequence = snapshot.sequence
        self._requires_reconnect = False
        self._remember(snapshot)
        self._activate(new_active)
        ack = self._ack(snapshot, "accepted")
        return self._finish(ack, new_active if (updates_active_slot or active_changed) else None, hard_reconcile, clock_error)

    def release(self, connector_session_id: str) -> bool:
        if connector_session_id != self._active_session_id:
            return False
        self._active_session_id = None
        self._last_snapshot = None
        self._last_receipt_us = None
        self._last_accepted_sequence = None
        self._slot_snapshots.clear()
        self._slot_receipts.clear()
        self._slot_clocks.clear()
        self.clock = MediaClockEstimator()
        return True

    def rotate_runtime_epoch(self, wizard_runtime_epoch: str) -> None:
        self.wizard_runtime_epoch = _require_id(wizard_runtime_epoch, "wizard_runtime_epoch")
        self._requires_reconnect = True
        self._reconciliation_generation += 1

    def diagnostics(self, now_monotonic_us: int) -> MediaSessionDiagnostics:
        age = self.clock.age_us(now_monotonic_us) if self._last_snapshot is not None else None
        state = self._scheduler_state(self._last_snapshot)
        if age is not None and age > self.clock.freshness_limit_us and state == "playing":
            state = "clock_uncertain"
        last_ack = self._last_acceptance.ack if self._last_acceptance is not None else None
        snapshot = self._last_snapshot
        return MediaSessionDiagnostics(
            scheduler_state=state,
            active_session_suffix=self._active_session_id[-8:] if self._active_session_id is not None else None,
            active_source_slot=snapshot.media.source_slot if snapshot is not None else None,
            accepted_sequence=snapshot.sequence if snapshot is not None else None,
            media_epoch=snapshot.media_epoch if snapshot is not None else None,
            reconciliation_generation=self._reconciliation_generation,
            snapshot_age_ms=age // 1000 if age is not None else None,
            estimated_position_ms=self.clock.position_at(now_monotonic_us),
            media_hash_prefix=(
                snapshot.media.media_sha256[:15]
                if snapshot is not None and snapshot.media.media_sha256 is not None
                else None
            ),
            score_hash_prefix=(
                snapshot.performance.score_sha256[:15]
                if snapshot is not None and snapshot.performance.score_sha256 is not None
                else None
            ),
            last_disposition=last_ack.disposition if last_ack is not None else None,
            last_error_code=last_ack.error_code if last_ack is not None else None,
        )
