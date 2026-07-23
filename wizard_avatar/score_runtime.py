from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

from .media_session import MediaSessionSnapshotV1
from .performance_score import (
    CompiledPerformanceScore,
    CompiledScoreRepository,
    ScoreValidationError,
)


SCORE_READY = "score_ready"
SCORE_NOT_READY = "score_not_ready"
SCORE_MISMATCH = "score_mismatch"
SCORE_CORRUPT = "score_corrupt"
SCORE_ADMISSION_MISMATCH = "score_admission_mismatch"
SCORELESS_V1 = "scoreless_v1"
DEFAULT_SCORE_RUNTIME_CAPACITY = 256


@dataclass(frozen=True)
class ScoreRuntimeBinding:
    score_id: str
    score_revision: int
    score_sha256: str
    package_sha256: Optional[str]
    character_id: str
    media_id: str
    media_sha256: Optional[str]
    duration_ms: Optional[int]

    @classmethod
    def from_snapshot(
        cls,
        snapshot: MediaSessionSnapshotV1,
    ) -> Optional["ScoreRuntimeBinding"]:
        selection = snapshot.performance
        if selection.score_id is None:
            return None
        assert selection.score_revision is not None
        assert selection.score_sha256 is not None
        return cls(
            score_id=selection.score_id,
            score_revision=selection.score_revision,
            score_sha256=selection.score_sha256,
            package_sha256=selection.character_package_sha256,
            character_id=selection.character_id,
            media_id=snapshot.media.media_id,
            media_sha256=snapshot.media.media_sha256,
            duration_ms=snapshot.media.duration_ms,
        )

    @property
    def diagnostic_id(self) -> str:
        value = {
            "character_id": self.character_id,
            "duration_ms": self.duration_ms,
            "media_id": self.media_id,
            "media_sha256": self.media_sha256,
            "package_sha256": self.package_sha256,
            "score_id": self.score_id,
            "score_revision": self.score_revision,
            "score_sha256": self.score_sha256,
        }
        encoded = json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ScorePreparationResult:
    ready: bool
    code: str
    binding_id: Optional[str]
    score: Optional[CompiledPerformanceScore]

    def to_dict(
        self,
        cache_entries: int,
        result_entries: int,
        evictions: int,
        capacity: int,
    ) -> Mapping[str, object]:
        return {
            "ready": self.ready,
            "code": self.code,
            "binding_id": self.binding_id,
            "cache_entries": cache_entries,
            "result_entries": result_entries,
            "evictions": evictions,
            "capacity": capacity,
        }


class ScoreRuntime:
    """Prepare immutable scores off-loop, then resolve exact bindings from memory."""

    def __init__(
        self,
        repository: CompiledScoreRepository,
        capacity: int = DEFAULT_SCORE_RUNTIME_CAPACITY,
        *,
        package_digest: Optional[str] = None,
        manifest_digest: Optional[str] = None,
        pose_library_digest: Optional[str] = None,
        graph_digest: Optional[str] = None,
        admitted_pose_ids: Optional[Iterable[str]] = None,
        admitted_clip_ids: Optional[Iterable[str]] = None,
        admitted_node_ids: Optional[Iterable[str]] = None,
    ) -> None:
        if not isinstance(repository, CompiledScoreRepository):
            raise TypeError("repository must be a CompiledScoreRepository")
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self.repository = repository
        self.capacity = capacity
        self.package_digest = _optional_digest(package_digest, "package_digest")
        self.manifest_digest = _optional_digest(manifest_digest, "manifest_digest")
        self.pose_library_digest = _optional_digest(
            pose_library_digest, "pose_library_digest"
        )
        self.graph_digest = _optional_digest(graph_digest, "graph_digest")
        self.admitted_pose_ids = _optional_id_set(
            admitted_pose_ids, "admitted_pose_ids"
        )
        self.admitted_clip_ids = _optional_id_set(
            admitted_clip_ids, "admitted_clip_ids"
        )
        self.admitted_node_ids = _optional_id_set(
            admitted_node_ids, "admitted_node_ids"
        )
        self._lock = threading.RLock()
        self._scores: OrderedDict[
            ScoreRuntimeBinding, CompiledPerformanceScore
        ] = OrderedDict()
        self._results: OrderedDict[
            ScoreRuntimeBinding, ScorePreparationResult
        ] = OrderedDict()
        self._evictions = 0

    def prepare_snapshot(self, snapshot: MediaSessionSnapshotV1) -> ScorePreparationResult:
        """Load and validate one score binding; callers must run this off the event loop."""

        binding = ScoreRuntimeBinding.from_snapshot(snapshot)
        if binding is None:
            return ScorePreparationResult(
                ready=False,
                code=SCORELESS_V1,
                binding_id=None,
                score=None,
            )

        with self._lock:
            cached = self._scores.get(binding)
            if cached is not None:
                self._touch(binding)
                return self._results[binding]

        if binding.media_sha256 is None:
            return self._record(binding, SCORE_NOT_READY)

        try:
            score = self.repository.load_current(binding.media_sha256)
        except ScoreValidationError as exc:
            code = SCORE_NOT_READY if exc.code == SCORE_NOT_READY else SCORE_CORRUPT
            return self._record(binding, code)
        except OSError:
            return self._record(binding, SCORE_CORRUPT)

        if not self._matches(score, binding):
            return self._record(binding, SCORE_MISMATCH)
        if not self._is_admitted(score):
            return self._record(binding, SCORE_ADMISSION_MISMATCH)

        result = ScorePreparationResult(
            ready=True,
            code=SCORE_READY,
            binding_id=binding.diagnostic_id,
            score=score,
        )
        with self._lock:
            self._store(binding, result)
        return result

    def resolve(
        self,
        snapshot: MediaSessionSnapshotV1,
    ) -> Optional[CompiledPerformanceScore]:
        """Resolve an exact score binding from memory without repository access."""

        binding = ScoreRuntimeBinding.from_snapshot(snapshot)
        if binding is None:
            return None
        with self._lock:
            score = self._scores.get(binding)
            if score is not None:
                self._touch(binding)
            return score

    def result_for(self, snapshot: MediaSessionSnapshotV1) -> ScorePreparationResult:
        binding = ScoreRuntimeBinding.from_snapshot(snapshot)
        if binding is None:
            return ScorePreparationResult(False, SCORELESS_V1, None, None)
        with self._lock:
            result = self._results.get(binding)
            if result is not None:
                self._touch(binding)
                return result
        return ScorePreparationResult(
            ready=False,
            code=SCORE_NOT_READY,
            binding_id=binding.diagnostic_id,
            score=None,
        )

    def diagnostics_for(self, snapshot: MediaSessionSnapshotV1) -> ScorePreparationResult:
        return self.result_for(snapshot)

    def diagnostics_mapping(self, snapshot: MediaSessionSnapshotV1) -> Mapping[str, object]:
        with self._lock:
            result = self._result_for_locked(snapshot)
            cache_entries = len(self._scores)
            result_entries = len(self._results)
            evictions = self._evictions
        return result.to_dict(
            cache_entries,
            result_entries,
            evictions,
            self.capacity,
        )

    def _record(self, binding: ScoreRuntimeBinding, code: str) -> ScorePreparationResult:
        result = ScorePreparationResult(
            ready=False,
            code=code,
            binding_id=binding.diagnostic_id,
            score=None,
        )
        with self._lock:
            self._store(binding, result)
        return result

    def _store(
        self,
        binding: ScoreRuntimeBinding,
        result: ScorePreparationResult,
    ) -> None:
        self._results.pop(binding, None)
        self._scores.pop(binding, None)
        self._results[binding] = result
        if result.score is not None:
            self._scores[binding] = result.score
        while len(self._results) > self.capacity:
            evicted_binding, _ = self._results.popitem(last=False)
            self._scores.pop(evicted_binding, None)
            self._evictions += 1

    def _touch(self, binding: ScoreRuntimeBinding) -> None:
        self._results.move_to_end(binding)
        if binding in self._scores:
            self._scores.move_to_end(binding)

    def _result_for_locked(
        self,
        snapshot: MediaSessionSnapshotV1,
    ) -> ScorePreparationResult:
        binding = ScoreRuntimeBinding.from_snapshot(snapshot)
        if binding is None:
            return ScorePreparationResult(False, SCORELESS_V1, None, None)
        result = self._results.get(binding)
        if result is not None:
            self._touch(binding)
            return result
        return ScorePreparationResult(
            ready=False,
            code=SCORE_NOT_READY,
            binding_id=binding.diagnostic_id,
            score=None,
        )

    def _is_admitted(self, score: CompiledPerformanceScore) -> bool:
        character = score.document.get("character")
        if not isinstance(character, Mapping):
            return False
        if (
            character.get("character_id") != score.character_id
            or character.get("package_digest") != score.package_digest
        ):
            return False
        if (
            self.package_digest is not None
            and score.package_digest != self.package_digest
        ):
            return False
        if (
            self.pose_library_digest is not None
            and character.get("pose_library_digest") != self.pose_library_digest
        ):
            return False
        if (
            self.graph_digest is not None
            and character.get("graph_digest") != self.graph_digest
        ):
            return False
        if self.manifest_digest is not None:
            document_manifest = character.get(
                "manifest_digest",
                score.document.get("manifest_digest"),
            )
            if document_manifest != self.manifest_digest:
                return False
        return (
            self._references_admitted(
                score, "pose_id", self.admitted_pose_ids
            )
            and self._references_admitted(
                score, "clip_id", self.admitted_clip_ids
            )
            and self._references_admitted(
                score, "node_id", self.admitted_node_ids
            )
        )

    @staticmethod
    def _references_admitted(
        score: CompiledPerformanceScore,
        field: str,
        admitted_ids: Optional[frozenset[str]],
    ) -> bool:
        if admitted_ids is None:
            return True
        for track in score.tracks:
            for cue in track.index.cues:
                value = cue.get(field)
                if value in (None, ""):
                    continue
                if not isinstance(value, str) or value not in admitted_ids:
                    return False
        return True

    @staticmethod
    def _matches(score: CompiledPerformanceScore, binding: ScoreRuntimeBinding) -> bool:
        return (
            score.compiled_score_id == binding.score_id
            and score.revision == binding.score_revision
            and score.artifact_sha256 == binding.score_sha256
            and score.package_digest == binding.package_sha256
            and score.character_id == binding.character_id
            and score.media_id == binding.media_id
            and score.media_sha256 == binding.media_sha256
            and score.duration_ms == binding.duration_ms
        )


def _optional_digest(value: Optional[str], name: str) -> Optional[str]:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(character not in "0123456789abcdef" for character in value[7:])
    ):
        raise ValueError(f"{name} must be a sha256 reference")
    return value


def _optional_id_set(
    values: Optional[Iterable[str]],
    name: str,
) -> Optional[frozenset[str]]:
    if values is None:
        return None
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be an iterable of identifiers")
    frozen = frozenset(values)
    if any(not isinstance(value, str) or not value for value in frozen):
        raise ValueError(f"{name} must contain non-empty string identifiers")
    return frozen
