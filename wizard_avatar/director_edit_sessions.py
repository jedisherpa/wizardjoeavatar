"""Bounded content-safe custody for iterative Character Director score edits."""

from __future__ import annotations

import copy
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Mapping

from .artifact_hashing import canonical_json_v1, sha256_ref
from .performance_context import PerformanceContextV1
from .score_edit_application import score_edit_target_sha256


DIRECTOR_EDIT_SESSION_CAPACITY = 32
DIRECTOR_EDIT_SESSION_TTL_US = 15 * 60 * 1_000_000
SAFE_EDIT_TYPES = (
    "timing_offset_ms",
    "duration_ms",
    "intensity_milli",
    "disabled",
    "semantic_clip_id",
    "semantic_pose_id",
    "semantic_action_id",
    "semantic_expression_id",
    "semantic_gaze_id",
)


class DirectorEditSessionError(ValueError):
    def __init__(self, code: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        super().__init__(code)


@dataclass(frozen=True)
class DirectorEditSessionV1:
    session_id: str
    source_slot: str
    media_id: str
    media_sha256: str
    snapshot_fingerprint: str
    portable_score: Mapping[str, object]
    compiler_context: PerformanceContextV1
    expires_at_monotonic_us: int

    @property
    def base_score_sha256(self) -> str:
        return sha256_ref(canonical_json_v1(self.portable_score))

    def safe_inspection(self, now_monotonic_us: int) -> Mapping[str, object]:
        cues = []
        tracks = self.portable_score.get("tracks")
        if not isinstance(tracks, list):
            raise DirectorEditSessionError("score_invalid", "$.tracks")
        for track in tracks:
            if not isinstance(track, Mapping):
                raise DirectorEditSessionError("score_invalid", "$.tracks")
            track_cues = track.get("cues")
            if not isinstance(track_cues, list):
                raise DirectorEditSessionError("score_invalid", "$.tracks.cues")
            for cue in track_cues:
                if not isinstance(cue, Mapping):
                    raise DirectorEditSessionError("score_invalid", "$.tracks.cues")
                cue_id = cue.get("cue_id")
                manual = cue.get("manual")
                if not isinstance(cue_id, str) or not isinstance(manual, Mapping):
                    raise DirectorEditSessionError("score_invalid", "$.tracks.cues")
                cues.append(
                    {
                        "cue_id": cue_id,
                        "track_kind": track.get("kind"),
                        "intent": cue.get("intent"),
                        "start_ms": cue.get("start_ms"),
                        "end_ms": cue.get("end_ms"),
                        "intensity_milli": cue.get("amplitude_milli"),
                        "locked": manual.get("locked"),
                        "disabled": manual.get("disabled"),
                        "edit_preconditions": {
                            edit_type: score_edit_target_sha256(
                                self.portable_score,
                                cue_id,
                                edit_type,
                            )
                            for edit_type in SAFE_EDIT_TYPES
                        },
                    }
                )
        remaining_us = max(0, self.expires_at_monotonic_us - now_monotonic_us)
        return {
            "schema_version": 1,
            "edit_session_id": self.session_id,
            "expires_in_ms": remaining_us // 1000,
            "base_score_sha256": self.base_score_sha256,
            "score_id": self.portable_score.get("score_id"),
            "score_revision": self.portable_score.get("revision"),
            "character_id": self.compiler_context.character.character_id,
            "package_digest": self.compiler_context.character.package_digest,
            "media_id": self.media_id,
            "media_sha256": self.media_sha256,
            "cues": cues,
        }


class DirectorEditSessionStore:
    def __init__(
        self,
        *,
        capacity: int = DIRECTOR_EDIT_SESSION_CAPACITY,
        ttl_us: int = DIRECTOR_EDIT_SESSION_TTL_US,
    ) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        if isinstance(ttl_us, bool) or not isinstance(ttl_us, int) or ttl_us < 1:
            raise ValueError("ttl_us must be a positive integer")
        self.capacity = capacity
        self.ttl_us = ttl_us
        self._sessions: "OrderedDict[str, DirectorEditSessionV1]" = OrderedDict()

    def create(
        self,
        *,
        source_slot: str,
        media_id: str,
        media_sha256: str,
        snapshot_fingerprint: str,
        portable_score: Mapping[str, object],
        compiler_context: PerformanceContextV1,
        now_monotonic_us: int,
    ) -> DirectorEditSessionV1:
        self.prune(now_monotonic_us)
        session = DirectorEditSessionV1(
            session_id="edit-session:" + uuid.uuid4().hex,
            source_slot=source_slot,
            media_id=media_id,
            media_sha256=media_sha256,
            snapshot_fingerprint=snapshot_fingerprint,
            portable_score=copy.deepcopy(dict(portable_score)),
            compiler_context=compiler_context,
            expires_at_monotonic_us=now_monotonic_us + self.ttl_us,
        )
        self._sessions[session.session_id] = session
        while len(self._sessions) > self.capacity:
            self._sessions.popitem(last=False)
        return session

    def replace_score(
        self,
        session_id: str,
        *,
        portable_score: Mapping[str, object],
        compiler_context: PerformanceContextV1,
        now_monotonic_us: int,
    ) -> DirectorEditSessionV1:
        current = self.require(session_id, now_monotonic_us)
        replacement = DirectorEditSessionV1(
            session_id=current.session_id,
            source_slot=current.source_slot,
            media_id=current.media_id,
            media_sha256=current.media_sha256,
            snapshot_fingerprint=current.snapshot_fingerprint,
            portable_score=copy.deepcopy(dict(portable_score)),
            compiler_context=compiler_context,
            expires_at_monotonic_us=now_monotonic_us + self.ttl_us,
        )
        self._sessions[session_id] = replacement
        self._sessions.move_to_end(session_id)
        return replacement

    def require(
        self,
        session_id: str,
        now_monotonic_us: int,
    ) -> DirectorEditSessionV1:
        self.prune(now_monotonic_us)
        session = self._sessions.get(session_id)
        if session is None:
            raise DirectorEditSessionError("edit_session_not_found")
        self._sessions.move_to_end(session_id)
        return session

    def discard(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def prune(self, now_monotonic_us: int) -> int:
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if session.expires_at_monotonic_us <= now_monotonic_us
        ]
        for session_id in expired:
            del self._sessions[session_id]
        return len(expired)

    def __len__(self) -> int:
        return len(self._sessions)


__all__ = [
    "DIRECTOR_EDIT_SESSION_CAPACITY",
    "DIRECTOR_EDIT_SESSION_TTL_US",
    "DirectorEditSessionError",
    "DirectorEditSessionStore",
    "DirectorEditSessionV1",
    "SAFE_EDIT_TYPES",
]
