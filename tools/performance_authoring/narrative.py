from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Optional, Sequence

from wizard_avatar.performance_compiler import (
    BaselineCompilation,
    NARRATIVE_PIPELINE_VERSION,
    NarrativeTimingSpan,
    canonical_artifact_bytes,
    compile_baseline_performance,
)
from wizard_avatar.transcript_ingest import TranscriptDocument

from .cache import CacheKey, canonical_identity_bytes, narrative_cache_key


@dataclass(frozen=True)
class PlannerCapability:
    planner: str
    available: bool
    local_only: bool
    reason_code: Optional[str]

    def to_mapping(self) -> Dict[str, object]:
        return {
            "planner": self.planner,
            "available": self.available,
            "local_only": self.local_only,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class NarrativeAuthoringResult:
    compilation: BaselineCompilation
    cache_key: CacheKey
    planner: PlannerCapability


def deterministic_planner_capability() -> PlannerCapability:
    return PlannerCapability(
        planner=NARRATIVE_PIPELINE_VERSION,
        available=True,
        local_only=True,
        reason_code=None,
    )


def structured_planner_capability() -> PlannerCapability:
    return PlannerCapability(
        planner="structured-planner",
        available=False,
        local_only=True,
        reason_code="optional_planner_not_configured",
    )


def build_narrative_baseline(
    transcript: TranscriptDocument,
    *,
    duration_ms: int,
    alignment_id: str,
    alignment_sha256: str,
    media_sha256: str,
    timing_spans: Sequence[NarrativeTimingSpan] = (),
    seed: int = 0,
) -> NarrativeAuthoringResult:
    transcript_sha256 = "sha256:" + hashlib.sha256(
        canonical_artifact_bytes(transcript.to_mapping())
    ).hexdigest()
    policy_sha256 = "sha256:" + hashlib.sha256(
        canonical_identity_bytes(
            {
                "pipeline": NARRATIVE_PIPELINE_VERSION,
                "content_free": True,
                "network": "forbidden",
                "fallback": "neutral_first",
            }
        )
    ).hexdigest()
    key = narrative_cache_key(
        transcript_sha256=transcript_sha256,
        alignment_sha256=alignment_sha256,
        pipeline_version=NARRATIVE_PIPELINE_VERSION,
        policy_sha256=policy_sha256,
        seed=seed,
    )
    compilation = compile_baseline_performance(
        transcript,
        duration_ms=duration_ms,
        alignment_id=alignment_id,
        media_sha256=media_sha256,
        timing_spans=timing_spans,
        seed=seed,
    )
    return NarrativeAuthoringResult(
        compilation=compilation,
        cache_key=key,
        planner=deterministic_planner_capability(),
    )


__all__ = [
    "NarrativeAuthoringResult",
    "PlannerCapability",
    "build_narrative_baseline",
    "deterministic_planner_capability",
    "structured_planner_capability",
]
