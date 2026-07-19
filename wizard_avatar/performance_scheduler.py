from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from enum import Enum
from types import MappingProxyType
from typing import Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from .media_session import (
    MediaSessionAckV1,
    MediaSessionAcceptance,
    MediaSessionCoordinator,
    MediaSessionSnapshotV1,
)
from .performance_score import CompiledPerformanceScore, PerformanceTrack, ScoreCue


TICK_RATE = 60


class AccessibilityMotionProfile(str, Enum):
    FULL = "full"
    REDUCED = "reduced"
    STILL = "still"
    SYSTEM = "system"


class SchedulerState(str, Enum):
    NO_SESSION = "no_session"
    LOADING_SCORE = "loading_score"
    READY = "ready"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    SEEKING = "seeking"
    CLOCK_UNCERTAIN = "clock_uncertain"
    STOPPED = "stopped"
    ENDED = "ended"
    SCORELESS = "scoreless"
    ERROR = "error"


REDUCED_PROHIBITED_CHANNELS = frozenset(
    {
        "locomotion",
        "stage",
        "position",
        "dance",
        "flight",
        "camera",
        "camera_motion",
        "simulated_depth",
        "whole_body_pulse",
        "scene_flash",
    }
)
REDUCED_PROHIBITED_TRACKS = frozenset({"locomotion", "stage", "dance"})
STILL_ALLOWED_CHANNELS = frozenset({"speech", "mouth", "face", "eyes", "gaze", "blink"})
TRACK_DEFAULT_CHANNEL = {
    "narrative_state": "narrative_state",
    "body_base": "body",
    "locomotion": "locomotion",
    "stage": "stage",
    "gesture": "gesture",
    "face": "face",
    "gaze": "gaze",
    "speech": "speech",
    "blink": "blink",
    "dance": "dance",
    "effects": "effects",
    "transition": "body",
    "manual_override": "manual_override",
}


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return sorted((_thaw(item) for item in value), key=repr)
    if isinstance(value, Enum):
        return value.value
    return value


def _state_hash(value: Mapping[str, object]) -> str:
    data = json.dumps(
        _thaw(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _cue_value(cue: ScoreCue, key: str, default: object = None) -> object:
    if key in cue.data:
        return cue.data[key]
    execution = cue.data.get("execution")
    if isinstance(execution, Mapping) and key in execution:
        return execution[key]
    return default


def _string_value(cue: Optional[ScoreCue], key: str, default: str) -> str:
    if cue is None:
        return default
    value = _cue_value(cue, key, default)
    return value if isinstance(value, str) else default


@dataclass(frozen=True)
class SchedulerSuppressionRecord:
    reason_code: str
    winning_owner: str
    losing_owner: str
    cue_id: str

    def to_dict(self) -> Mapping[str, object]:
        return {
            "reason_code": self.reason_code,
            "winning_owner": self.winning_owner,
            "losing_owner": self.losing_owner,
            "cue_id": self.cue_id,
        }


@dataclass(frozen=True)
class ResolvedPerformanceState:
    media_time_ms: int
    score_id: Optional[str]
    score_sha256: Optional[str]
    motion_profile: AccessibilityMotionProfile
    intensity_milli: int
    score_cue_ids: Tuple[str, ...]
    cue_phases: Mapping[str, str]
    track_values: Mapping[str, Mapping[str, object]]
    channel_owners: Mapping[str, str]
    body_mapping_id: str
    clip_id: str
    node_id: str
    clip_elapsed_ticks: int
    pose_id: str
    world_position_milli: Tuple[int, int]
    facing: str
    expression: str
    gaze_target: str
    mouth_shape: str
    speaking: bool
    owned_channels: frozenset[str]
    suppressed_requests: Tuple[SchedulerSuppressionRecord, ...]
    fallback_records: Tuple[Mapping[str, object], ...]
    resolution_hash: str

    def to_dict(self) -> Mapping[str, object]:
        return {
            "media_time_ms": self.media_time_ms,
            "score_id": self.score_id,
            "score_sha256": self.score_sha256,
            "motion_profile": self.motion_profile.value,
            "intensity_milli": self.intensity_milli,
            "score_cue_ids": list(self.score_cue_ids),
            "cue_phases": dict(self.cue_phases),
            "track_values": _thaw(self.track_values),
            "channel_owners": dict(self.channel_owners),
            "body_mapping_id": self.body_mapping_id,
            "clip_id": self.clip_id,
            "node_id": self.node_id,
            "clip_elapsed_ticks": self.clip_elapsed_ticks,
            "pose_id": self.pose_id,
            "world_position_milli": list(self.world_position_milli),
            "facing": self.facing,
            "expression": self.expression,
            "gaze_target": self.gaze_target,
            "mouth_shape": self.mouth_shape,
            "speaking": self.speaking,
            "owned_channels": sorted(self.owned_channels),
            "suppressed_requests": [record.to_dict() for record in self.suppressed_requests],
            "fallback_records": [_thaw(record) for record in self.fallback_records],
            "resolution_hash": self.resolution_hash,
        }


@dataclass(frozen=True)
class SchedulerDiagnostics:
    scheduler_state: SchedulerState
    media_time_ms: Optional[int]
    snapshot_age_ms: Optional[int]
    reconciliation_generation: int
    hard_reconcile_count: int
    score_id: Optional[str]
    score_hash_prefix: Optional[str]
    package_hash_prefix: Optional[str]
    active_cue_ids: Tuple[str, ...]
    phrase_phases: Mapping[str, str]
    motion_profile: Optional[str]
    fallback_count: int
    suppression_count: int
    last_ack_disposition: Optional[str]
    last_error_code: Optional[str]

    def to_dict(self) -> Mapping[str, object]:
        return {
            "scheduler_state": self.scheduler_state.value,
            "media_time_ms": self.media_time_ms,
            "snapshot_age_ms": self.snapshot_age_ms,
            "reconciliation_generation": self.reconciliation_generation,
            "hard_reconcile_count": self.hard_reconcile_count,
            "score_id": self.score_id,
            "score_hash_prefix": self.score_hash_prefix,
            "package_hash_prefix": self.package_hash_prefix,
            "active_cue_ids": list(self.active_cue_ids),
            "phrase_phases": dict(self.phrase_phases),
            "motion_profile": self.motion_profile,
            "fallback_count": self.fallback_count,
            "suppression_count": self.suppression_count,
            "last_ack_disposition": self.last_ack_disposition,
            "last_error_code": self.last_error_code,
        }


ScoreResolver = Callable[[MediaSessionSnapshotV1], Optional[CompiledPerformanceScore]]


def _normalize_profile(
    profile: object, system_profile: AccessibilityMotionProfile
) -> AccessibilityMotionProfile:
    if isinstance(profile, AccessibilityMotionProfile):
        parsed = profile
    else:
        try:
            parsed = AccessibilityMotionProfile(str(profile))
        except ValueError as exc:
            raise ValueError("unsupported accessibility motion profile") from exc
    return system_profile if parsed is AccessibilityMotionProfile.SYSTEM else parsed


def _cue_channels(track: PerformanceTrack, cue: ScoreCue) -> Tuple[str, ...]:
    if cue.owned_channels:
        return cue.owned_channels
    return (TRACK_DEFAULT_CHANNEL.get(track.kind, track.kind),)


def _channels_after_projection(
    channels: Sequence[str], profile: AccessibilityMotionProfile, disabled_channels: frozenset[str]
) -> Tuple[str, ...]:
    projected = [channel for channel in channels if channel not in disabled_channels]
    if profile is AccessibilityMotionProfile.REDUCED:
        projected = [channel for channel in projected if channel not in REDUCED_PROHIBITED_CHANNELS]
    elif profile is AccessibilityMotionProfile.STILL:
        projected = [channel for channel in projected if channel in STILL_ALLOWED_CHANNELS]
    return tuple(projected)


def _ease_milli(u_milli: int, easing_id: str) -> int:
    u = min(1000, max(0, u_milli))
    if easing_id in {"linear", "linear_v1"}:
        return u
    if easing_id in {"smoothstep", "smoothstep_v1", "ease_in_out_v1"}:
        return (3 * u * u * 1000 - 2 * u * u * u) // 1_000_000
    return u


def _pair(value: object) -> Optional[Tuple[int, int]]:
    if (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and isinstance(value[0], int)
        and not isinstance(value[0], bool)
        and isinstance(value[1], int)
        and not isinstance(value[1], bool)
    ):
        return (int(value[0]), int(value[1]))
    return None


def _stage_position(cue: Optional[ScoreCue], media_time_ms: int) -> Tuple[int, int]:
    if cue is None:
        return (0, 0)
    trajectory = _cue_value(cue, "trajectory", {})
    source = _pair(_cue_value(cue, "source_position_milli"))
    destination = _pair(_cue_value(cue, "destination_position_milli"))
    easing_id = _string_value(cue, "easing_id", "linear_v1")
    if isinstance(trajectory, Mapping):
        source = _pair(trajectory.get("source_position_milli")) or source
        destination = _pair(trajectory.get("destination_position_milli")) or destination
        raw_easing = trajectory.get("easing_id")
        if isinstance(raw_easing, str):
            easing_id = raw_easing
    direct = _pair(_cue_value(cue, "world_position_milli"))
    if source is None or destination is None:
        return direct or destination or source or (0, 0)
    duration = cue.end_ms - cue.start_ms
    elapsed = min(duration, max(0, media_time_ms - cue.start_ms))
    eased = _ease_milli((elapsed * 1000) // duration, easing_id)
    return (
        source[0] + ((destination[0] - source[0]) * eased) // 1000,
        source[1] + ((destination[1] - source[1]) * eased) // 1000,
    )


class PerformanceScheduler:
    """Pure score evaluator plus a thin accepted-snapshot orchestration seam."""

    def __init__(
        self,
        score: Optional[CompiledPerformanceScore] = None,
        coordinator: Optional[MediaSessionCoordinator] = None,
        score_resolver: Optional[ScoreResolver] = None,
        system_profile: AccessibilityMotionProfile = AccessibilityMotionProfile.FULL,
    ) -> None:
        if system_profile not in {AccessibilityMotionProfile.FULL, AccessibilityMotionProfile.REDUCED, AccessibilityMotionProfile.STILL}:
            raise ValueError("system_profile must resolve to full, reduced, or still")
        self._score = score
        self.coordinator = coordinator or MediaSessionCoordinator("wizard:performance-runtime")
        self._score_resolver = score_resolver
        self._system_profile = system_profile
        self._scheduler_state = SchedulerState.READY if score is not None else SchedulerState.NO_SESSION
        self._last_resolved: Optional[ResolvedPerformanceState] = None
        self._last_ack: Optional[MediaSessionAckV1] = None
        self._last_error_code: Optional[str] = None
        self._hard_reconcile_count = 0
        self._score_binding_valid = score is not None
        self._scoreless_active = False

    @property
    def score(self) -> Optional[CompiledPerformanceScore]:
        return self._score

    @property
    def scheduler_state(self) -> SchedulerState:
        return self._scheduler_state

    def set_score(self, score: Optional[CompiledPerformanceScore]) -> None:
        self._score = score
        self._score_binding_valid = score is not None
        self._scoreless_active = False
        self._last_resolved = None
        self._scheduler_state = SchedulerState.READY if score is not None else SchedulerState.LOADING_SCORE

    @staticmethod
    def _score_matches(score: CompiledPerformanceScore, snapshot: MediaSessionSnapshotV1) -> bool:
        selection = snapshot.performance
        return (
            selection.score_id is not None
            and score.compiled_score_id == selection.score_id
            and score.artifact_sha256 == selection.score_sha256
            and score.character_id == selection.character_id
            and (
                selection.character_package_sha256 is None
                or score.package_digest == selection.character_package_sha256
            )
            and (score.media_id is None or score.media_id == snapshot.media.media_id)
            and (score.media_sha256 is None or score.media_sha256 == snapshot.media.media_sha256)
            and (
                score.duration_ms == 0
                or snapshot.media.duration_ms is None
                or score.duration_ms == snapshot.media.duration_ms
            )
        )

    def accept_snapshot(self, snapshot: MediaSessionSnapshotV1, receipt_monotonic_us: int) -> MediaSessionAckV1:
        acceptance = self.coordinator.accept_with_result(snapshot, receipt_monotonic_us)
        ack = acceptance.ack
        if ack.disposition != "accepted":
            self._last_ack = ack
            self._last_error_code = ack.error_code
            return ack

        active_snapshot = acceptance.snapshot
        if active_snapshot is None:
            self._last_ack = ack
            return ack

        if acceptance.hard_reconcile:
            self._hard_reconcile_count += 1
            self._last_resolved = None

        if active_snapshot.performance.score_id is None:
            self._score = None
            self._score_binding_valid = False
            self._scoreless_active = active_snapshot.performance.mode != "none"
            self._scheduler_state = (
                SchedulerState.SCORELESS if self._scoreless_active else self._state_for_snapshot(active_snapshot)
            )
            self._last_error_code = None
            ack = replace(ack, scheduler_state=self._scheduler_state.value, error=None)
            self._last_ack = ack
            self._last_resolved = self._scoreless_state(
                active_snapshot.playback.position_ms,
                active_snapshot,
            )
            return ack

        score = self._score
        had_loaded_score = score is not None
        if score is None or not self._score_matches(score, active_snapshot):
            score = self._score_resolver(active_snapshot) if self._score_resolver is not None else None
            if score is not None and self._score_matches(score, active_snapshot):
                self._score = score
                self._score_binding_valid = True
            else:
                self._scheduler_state = SchedulerState.ERROR
                self._score_binding_valid = False
                self._scoreless_active = False
                self._last_error_code = "score_mismatch" if had_loaded_score or score is not None else "score_not_ready"
                ack = replace(ack, scheduler_state="error", error={"code": self._last_error_code})
                self._last_ack = ack
                return ack

        self._scheduler_state = self._state_for_snapshot(active_snapshot)
        self._score_binding_valid = True
        self._scoreless_active = False
        self._last_error_code = None
        ack = replace(ack, scheduler_state=self._scheduler_state.value)
        self._last_ack = ack
        self._last_resolved = self.evaluate(
            active_snapshot.playback.position_ms,
            motion_profile=active_snapshot.performance.motion_profile,
            disabled_channels=active_snapshot.performance.disabled_channels,
            intensity_milli=active_snapshot.performance.intensity_milli,
        )
        return ack

    @staticmethod
    def _state_for_snapshot(snapshot: MediaSessionSnapshotV1) -> SchedulerState:
        return {
            "empty": SchedulerState.NO_SESSION,
            "loading": SchedulerState.LOADING_SCORE,
            "paused": SchedulerState.PAUSED,
            "playing": SchedulerState.PLAYING,
            "buffering": SchedulerState.BUFFERING,
            "seeking": SchedulerState.SEEKING,
            "ended": SchedulerState.ENDED,
            "stopped": SchedulerState.STOPPED,
            "error": SchedulerState.ERROR,
        }[snapshot.playback.state]

    def _neutral_state(
        self,
        media_time_ms: int,
        profile: AccessibilityMotionProfile,
        intensity_milli: int,
    ) -> ResolvedPerformanceState:
        score_id = self._score.compiled_score_id if self._score is not None else None
        score_sha = self._score.artifact_sha256 if self._score is not None else None
        identity: Mapping[str, object] = {
            "media_time_ms": media_time_ms,
            "score_id": score_id,
            "score_sha256": score_sha,
            "motion_profile": profile.value,
            "intensity_milli": intensity_milli,
            "score_cue_ids": [],
            "cue_phases": {},
            "track_values": {},
            "channel_owners": {},
            "body_mapping_id": "body.characterful_neutral",
            "clip_id": "",
            "node_id": "",
            "clip_elapsed_ticks": 0,
            "pose_id": "",
            "world_position_milli": [0, 0],
            "facing": "south",
            "expression": "neutral",
            "gaze_target": "forward",
            "mouth_shape": "rest",
            "speaking": False,
            "owned_channels": [],
            "suppressed_requests": [],
            "fallback_records": [],
        }
        return ResolvedPerformanceState(
            media_time_ms=media_time_ms,
            score_id=score_id,
            score_sha256=score_sha,
            motion_profile=profile,
            intensity_milli=intensity_milli,
            score_cue_ids=(),
            cue_phases=MappingProxyType({}),
            track_values=MappingProxyType({}),
            channel_owners=MappingProxyType({}),
            body_mapping_id="body.characterful_neutral",
            clip_id="",
            node_id="",
            clip_elapsed_ticks=0,
            pose_id="",
            world_position_milli=(0, 0),
            facing="south",
            expression="neutral",
            gaze_target="forward",
            mouth_shape="rest",
            speaking=False,
            owned_channels=frozenset(),
            suppressed_requests=(),
            fallback_records=(),
            resolution_hash=_state_hash(identity),
        )

    def _scoreless_state(
        self,
        media_time_ms: int,
        snapshot: MediaSessionSnapshotV1,
    ) -> ResolvedPerformanceState:
        profile = _normalize_profile(snapshot.performance.motion_profile, self._system_profile)
        intensity_milli = snapshot.performance.intensity_milli
        disabled = frozenset(snapshot.performance.disabled_channels)
        mode = snapshot.performance.mode
        duration_ms = snapshot.media.duration_ms
        active = duration_ms is None or media_time_ms < duration_ms
        terminal = snapshot.playback.state in {"empty", "ended", "stopped", "error"}

        body_mapping_id = "body.characterful_neutral"
        mouth_shape = "rest"
        speaking = False
        owned_channels: set[str] = set()
        channel_owners: Dict[str, str] = {}
        track_values: Dict[str, Mapping[str, object]] = {}

        if mode in {"narrative", "speech"} and active and not terminal:
            speaking = True
            if "mouth" not in disabled:
                mouth_shape = ("closed", "open", "wide", "open")[(media_time_ms // 120) % 4]
                owned_channels.update({"mouth", "speech"})
            track_values["scoreless_speech"] = MappingProxyType(
                {
                    "fallback": "duration_only_speech",
                    "phase": (media_time_ms // 120) % 4,
                    "effective_amplitude_milli": (400 * intensity_milli) // 1000,
                }
            )
        elif mode == "music" and active and not terminal:
            groove_phase = (media_time_ms // 500) % 4
            if profile is not AccessibilityMotionProfile.STILL and "upper_body" not in disabled:
                body_mapping_id = "body.music_groove_restrained.{}".format(groove_phase)
                owned_channels.add("gesture")
            track_values["scoreless_music"] = MappingProxyType(
                {
                    "fallback": "time_based_groove",
                    "phase": groove_phase,
                    "effective_amplitude_milli": (350 * intensity_milli) // 1000,
                }
            )

        for channel in sorted(owned_channels):
            channel_owners[channel] = "scoreless:" + mode
        fallback_records: Tuple[Mapping[str, object], ...] = ()
        if mode != "none":
            fallback_records = (
                MappingProxyType(
                    {
                        "fallback_id": "scoreless-v1",
                        "reason_code": "score_absent",
                        "mode": mode,
                    }
                ),
            )
        identity: Mapping[str, object] = {
            "media_time_ms": media_time_ms,
            "score_id": None,
            "score_sha256": None,
            "motion_profile": profile.value,
            "intensity_milli": intensity_milli,
            "score_cue_ids": [],
            "cue_phases": {},
            "track_values": track_values,
            "channel_owners": channel_owners,
            "body_mapping_id": body_mapping_id,
            "clip_id": "",
            "node_id": "",
            "clip_elapsed_ticks": 0,
            "pose_id": "",
            "world_position_milli": [0, 0],
            "facing": "south",
            "expression": "neutral",
            "gaze_target": "forward",
            "mouth_shape": mouth_shape,
            "speaking": speaking,
            "owned_channels": sorted(owned_channels),
            "suppressed_requests": [],
            "fallback_records": fallback_records,
        }
        return ResolvedPerformanceState(
            media_time_ms=media_time_ms,
            score_id=None,
            score_sha256=None,
            motion_profile=profile,
            intensity_milli=intensity_milli,
            score_cue_ids=(),
            cue_phases=MappingProxyType({}),
            track_values=MappingProxyType(track_values),
            channel_owners=MappingProxyType(channel_owners),
            body_mapping_id=body_mapping_id,
            clip_id="",
            node_id="",
            clip_elapsed_ticks=0,
            pose_id="",
            world_position_milli=(0, 0),
            facing="south",
            expression="neutral",
            gaze_target="forward",
            mouth_shape=mouth_shape,
            speaking=speaking,
            owned_channels=frozenset(owned_channels),
            suppressed_requests=(),
            fallback_records=fallback_records,
            resolution_hash=_state_hash(identity),
        )

    def evaluate(
        self,
        media_time_ms: int,
        motion_profile: object = AccessibilityMotionProfile.FULL,
        disabled_channels: Iterable[str] = (),
        intensity_milli: int = 1000,
    ) -> ResolvedPerformanceState:
        if not isinstance(media_time_ms, int) or isinstance(media_time_ms, bool) or media_time_ms < 0:
            raise ValueError("media_time_ms must be a non-negative integer")
        if not isinstance(intensity_milli, int) or isinstance(intensity_milli, bool) or not 0 <= intensity_milli <= 1000:
            raise ValueError("intensity_milli must be in [0, 1000]")
        profile = _normalize_profile(motion_profile, self._system_profile)
        disabled = frozenset(disabled_channels)
        score = self._score
        if score is None or (score.duration_ms and media_time_ms >= score.duration_ms):
            return self._neutral_state(media_time_ms, profile, intensity_milli)

        requests: list[Tuple[PerformanceTrack, ScoreCue, bool]] = []
        track_values: Dict[str, Mapping[str, object]] = {}
        phases: Dict[str, str] = {}
        suppressions: list[SchedulerSuppressionRecord] = []
        fallbacks: list[Mapping[str, object]] = []

        for track in score.tracks:
            active = track.index.query(media_time_ms)
            held = False
            if not active and track.gap_policy == "hold":
                previous = track.index.previous(media_time_ms)
                active = (previous,) if previous is not None else ()
                held = bool(active)
            for cue in active:
                channels = _cue_channels(track, cue)
                projected = _channels_after_projection(channels, profile, disabled)
                if profile is AccessibilityMotionProfile.REDUCED and track.kind in REDUCED_PROHIBITED_TRACKS:
                    projected = ()
                for channel in sorted(disabled.intersection(channels)):
                    suppressions.append(
                        SchedulerSuppressionRecord(
                            reason_code="channel_disabled",
                            winning_owner="accessibility:disabled:" + channel,
                            losing_owner=track.track_id,
                            cue_id=cue.cue_id,
                        )
                    )
                if not projected:
                    suppressions.append(
                        SchedulerSuppressionRecord(
                            reason_code="accessibility_projection",
                            winning_owner="accessibility:" + profile.value,
                            losing_owner=track.track_id,
                            cue_id=cue.cue_id,
                        )
                    )
                    continue
                requests.append((track, cue, held))
                phases[cue.cue_id] = "hold" if held else (cue.phase_at(media_time_ms) or "active")
                resolved_value = dict(cue.to_dict())
                resolved_value["active_channels"] = list(projected)
                resolved_value["phrase_phase"] = phases[cue.cue_id]
                resolved_value["effective_amplitude_milli"] = (
                    int(resolved_value.get("amplitude_milli", 1000)) * intensity_milli
                ) // 1000
                track_values[track.track_id] = _freeze(resolved_value)  # type: ignore[assignment]
                cue_fallbacks = _cue_value(cue, "fallback_records", ())
                if isinstance(cue_fallbacks, (list, tuple)):
                    for fallback in cue_fallbacks:
                        if isinstance(fallback, Mapping):
                            fallbacks.append(_freeze(fallback))  # type: ignore[arg-type]

        track_rank = {track.track_id: index for index, track in enumerate(score.tracks)}
        requests.sort(key=lambda item: (-item[1].priority, track_rank[item[0].track_id], item[1].start_ms, item[1].cue_id))
        channel_owners: Dict[str, str] = {}
        winner_cues: Dict[str, ScoreCue] = {}
        for track, cue, _held in requests:
            projected = _channels_after_projection(_cue_channels(track, cue), profile, disabled)
            for channel in projected:
                winner = channel_owners.get(channel)
                if winner is None:
                    channel_owners[channel] = track.track_id
                    winner_cues[channel] = cue
                elif winner != track.track_id:
                    suppressions.append(
                        SchedulerSuppressionRecord(
                            reason_code="channel_owned",
                            winning_owner=winner,
                            losing_owner=track.track_id,
                            cue_id=cue.cue_id,
                        )
                    )

        body_cue = next(
            (winner_cues[channel] for channel in ("body", "body_base", "gesture") if channel in winner_cues),
            None,
        )
        stage_cue = next(
            (winner_cues[channel] for channel in ("stage", "locomotion") if channel in winner_cues),
            None,
        )
        face_cue = winner_cues.get("face")
        gaze_cue = winner_cues.get("gaze") or winner_cues.get("eyes")
        speech_cue = winner_cues.get("speech")
        mouth_cue = winner_cues.get("mouth")
        if profile is AccessibilityMotionProfile.STILL:
            body_cue = None
            stage_cue = None

        phrase_origin = 0
        if body_cue is not None:
            raw_origin = _cue_value(body_cue, "phrase_phase_origin_ms", body_cue.start_ms)
            phrase_origin = raw_origin if isinstance(raw_origin, int) and not isinstance(raw_origin, bool) else body_cue.start_ms
        clip_media_time = media_time_ms
        if body_cue is not None and phases.get(body_cue.cue_id) == "hold":
            clip_media_time = min(media_time_ms, body_cue.end_ms - 1)
        clip_ticks = max(0, ((clip_media_time - phrase_origin) * TICK_RATE) // 1000) if body_cue is not None else 0
        mouth_shape = _string_value(mouth_cue, "mouth_shape", "rest")
        speaking_value = _cue_value(speech_cue, "speaking", speech_cue is not None and mouth_shape not in {"rest", "closed", "silence"}) if speech_cue is not None else False
        speaking = bool(speaking_value)

        cue_ids = tuple(sorted({cue.cue_id for _track, cue, _held in requests if cue.cue_id in phases}))
        body_mapping = _string_value(body_cue, "mapping_id", "body.characterful_neutral")
        if profile is AccessibilityMotionProfile.STILL:
            body_mapping = "body.characterful_neutral"
        position = _stage_position(stage_cue, media_time_ms)
        identity: Mapping[str, object] = {
            "media_time_ms": media_time_ms,
            "score_id": score.compiled_score_id,
            "score_sha256": score.artifact_sha256,
            "motion_profile": profile.value,
            "intensity_milli": intensity_milli,
            "score_cue_ids": list(cue_ids),
            "cue_phases": phases,
            "track_values": track_values,
            "channel_owners": channel_owners,
            "body_mapping_id": body_mapping,
            "clip_id": _string_value(body_cue, "clip_id", ""),
            "node_id": _string_value(body_cue, "node_id", ""),
            "clip_elapsed_ticks": clip_ticks,
            "pose_id": _string_value(body_cue, "pose_id", ""),
            "world_position_milli": list(position),
            "facing": _string_value(stage_cue or body_cue, "facing", "south"),
            "expression": _string_value(face_cue, "expression", "neutral"),
            "gaze_target": _string_value(gaze_cue, "gaze_target", "forward"),
            "mouth_shape": mouth_shape,
            "speaking": speaking,
            "owned_channels": sorted(channel_owners),
            "suppressed_requests": [record.to_dict() for record in suppressions],
            "fallback_records": fallbacks,
        }
        return ResolvedPerformanceState(
            media_time_ms=media_time_ms,
            score_id=score.compiled_score_id,
            score_sha256=score.artifact_sha256,
            motion_profile=profile,
            intensity_milli=intensity_milli,
            score_cue_ids=cue_ids,
            cue_phases=_freeze(phases),  # type: ignore[arg-type]
            track_values=_freeze(track_values),  # type: ignore[arg-type]
            channel_owners=_freeze(channel_owners),  # type: ignore[arg-type]
            body_mapping_id=body_mapping,
            clip_id=_string_value(body_cue, "clip_id", ""),
            node_id=_string_value(body_cue, "node_id", ""),
            clip_elapsed_ticks=clip_ticks,
            pose_id=_string_value(body_cue, "pose_id", ""),
            world_position_milli=position,
            facing=_string_value(stage_cue or body_cue, "facing", "south"),
            expression=_string_value(face_cue, "expression", "neutral"),
            gaze_target=_string_value(gaze_cue, "gaze_target", "forward"),
            mouth_shape=mouth_shape,
            speaking=speaking,
            owned_channels=frozenset(channel_owners),
            suppressed_requests=tuple(suppressions),
            fallback_records=tuple(fallbacks),
            resolution_hash=_state_hash(identity),
        )

    state_at_media_time = evaluate

    def current_state(self, now_monotonic_us: int) -> ResolvedPerformanceState:
        snapshot = self.coordinator.accepted_snapshot
        if snapshot is None:
            self._scheduler_state = SchedulerState.NO_SESSION
            return self._neutral_state(0, AccessibilityMotionProfile.FULL, 1000)
        if self._scoreless_active:
            media_time = self.coordinator.clock.position_at(now_monotonic_us)
            assert media_time is not None
            self._scheduler_state = SchedulerState.SCORELESS
            resolved = self._scoreless_state(media_time, snapshot)
            self._last_resolved = resolved
            return resolved
        if not self._score_binding_valid:
            media_time = self.coordinator.clock.position_at(now_monotonic_us)
            assert media_time is not None
            self._scheduler_state = SchedulerState.ERROR
            return self._neutral_state(
                media_time,
                _normalize_profile(snapshot.performance.motion_profile, self._system_profile),
                snapshot.performance.intensity_milli,
            )
        age = self.coordinator.clock.age_us(now_monotonic_us)
        assert age is not None
        if snapshot.playback.state == "playing" and age > self.coordinator.clock.freshness_limit_us:
            self._scheduler_state = SchedulerState.CLOCK_UNCERTAIN
            if self._last_resolved is not None:
                return self._last_resolved
        media_time = self.coordinator.clock.position_at(now_monotonic_us)
        assert media_time is not None
        self._scheduler_state = self._state_for_snapshot(snapshot)
        resolved = self.evaluate(
            media_time,
            motion_profile=snapshot.performance.motion_profile,
            disabled_channels=snapshot.performance.disabled_channels,
            intensity_milli=snapshot.performance.intensity_milli,
        )
        self._last_resolved = resolved
        return resolved

    def diagnostics(self, now_monotonic_us: int) -> SchedulerDiagnostics:
        session = self.coordinator.diagnostics(now_monotonic_us)
        resolved = self._last_resolved
        snapshot = self.coordinator.accepted_snapshot
        return SchedulerDiagnostics(
            scheduler_state=self._scheduler_state,
            media_time_ms=resolved.media_time_ms if resolved is not None else session.estimated_position_ms,
            snapshot_age_ms=session.snapshot_age_ms,
            reconciliation_generation=session.reconciliation_generation,
            hard_reconcile_count=self._hard_reconcile_count,
            score_id=self._score.compiled_score_id if self._score is not None else None,
            score_hash_prefix=self._score.artifact_sha256[:15] if self._score is not None else None,
            package_hash_prefix=(
                snapshot.performance.character_package_sha256[:15]
                if snapshot is not None and snapshot.performance.character_package_sha256 is not None
                else None
            ),
            active_cue_ids=resolved.score_cue_ids if resolved is not None else (),
            phrase_phases=resolved.cue_phases if resolved is not None else MappingProxyType({}),
            motion_profile=resolved.motion_profile.value if resolved is not None else None,
            fallback_count=len(resolved.fallback_records) if resolved is not None else 0,
            suppression_count=len(resolved.suppressed_requests) if resolved is not None else 0,
            last_ack_disposition=self._last_ack.disposition if self._last_ack is not None else None,
            last_error_code=self._last_error_code,
        )
