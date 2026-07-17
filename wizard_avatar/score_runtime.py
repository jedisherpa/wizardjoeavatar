from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Dict, Mapping, Optional

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
SCORELESS_V1 = "scoreless_v1"


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

    def to_dict(self, cache_entries: int) -> Mapping[str, object]:
        return {
            "ready": self.ready,
            "code": self.code,
            "binding_id": self.binding_id,
            "cache_entries": cache_entries,
        }


class ScoreRuntime:
    """Prepare immutable scores off-loop, then resolve exact bindings from memory."""

    def __init__(self, repository: CompiledScoreRepository) -> None:
        if not isinstance(repository, CompiledScoreRepository):
            raise TypeError("repository must be a CompiledScoreRepository")
        self.repository = repository
        self._lock = threading.RLock()
        self._scores: Dict[ScoreRuntimeBinding, CompiledPerformanceScore] = {}
        self._results: Dict[ScoreRuntimeBinding, ScorePreparationResult] = {}

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

        result = ScorePreparationResult(
            ready=True,
            code=SCORE_READY,
            binding_id=binding.diagnostic_id,
            score=score,
        )
        with self._lock:
            self._scores[binding] = score
            self._results[binding] = result
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
            return self._scores.get(binding)

    def result_for(self, snapshot: MediaSessionSnapshotV1) -> ScorePreparationResult:
        binding = ScoreRuntimeBinding.from_snapshot(snapshot)
        if binding is None:
            return ScorePreparationResult(False, SCORELESS_V1, None, None)
        with self._lock:
            result = self._results.get(binding)
        if result is not None:
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
            cache_entries = len(self._scores)
        return self.result_for(snapshot).to_dict(cache_entries)

    def _record(self, binding: ScoreRuntimeBinding, code: str) -> ScorePreparationResult:
        result = ScorePreparationResult(
            ready=False,
            code=code,
            binding_id=binding.diagnostic_id,
            score=None,
        )
        with self._lock:
            self._scores.pop(binding, None)
            self._results[binding] = result
        return result

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
