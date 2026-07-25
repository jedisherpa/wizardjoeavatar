"""Deterministic score preparation for one governed live-speech turn."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .artifact_hashing import canonical_json_v1, sha256_ref
from .direction_compiler import (
    DirectionCompileError,
    HighLevelDirectionRequestV1,
    compile_high_level_direction,
)
from .performance_context import PerformanceContextV1
from .performance_score import (
    CompiledScoreLoader,
    CompiledScoreRepository,
    ScoreValidationError,
)


class LiveSpeechScoreError(ValueError):
    """Content-free live-score preparation failure."""

    def __init__(self, code: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        super().__init__(code)


@dataclass(frozen=True)
class LiveSpeechScoreBindingV1:
    schema_version: int
    score_id: str
    score_revision: int
    score_sha256: str
    compiled_from_context_sha256: str
    character_id: str
    package_digest: str
    media_id: str
    media_sha256: str

    def to_dict(self) -> Mapping[str, object]:
        return {
            "schema_version": self.schema_version,
            "score_id": self.score_id,
            "score_revision": self.score_revision,
            "score_sha256": self.score_sha256,
            "compiled_from_context_sha256": self.compiled_from_context_sha256,
            "character_id": self.character_id,
            "package_digest": self.package_digest,
            "media_id": self.media_id,
            "media_sha256": self.media_sha256,
        }


@dataclass(frozen=True)
class PreparedLiveSpeechScoreV1:
    schema_version: int
    preliminary_context: PerformanceContextV1
    score_binding: LiveSpeechScoreBindingV1

    def to_dict(self) -> Mapping[str, object]:
        return {
            "schema_version": self.schema_version,
            "preliminary_context": self.preliminary_context.to_dict(),
            "score_binding": self.score_binding.to_dict(),
        }


def compile_live_speech_score(
    context: PerformanceContextV1,
    *,
    duration_ms: int,
    capability_manifest: Mapping[str, object],
    repository: CompiledScoreRepository,
) -> PreparedLiveSpeechScoreV1:
    """Compile and atomically publish a content-free speech performance score."""

    if context.conversation.intent != "speak":
        raise LiveSpeechScoreError(
            "live_score_intent_unsupported",
            "$.performance_context.conversation.intent",
        )
    if (
        context.evidence.score_binding.score_id is not None
        or context.evidence.score_binding.score_revision is not None
        or context.evidence.score_binding.score_sha256 is not None
    ):
        raise LiveSpeechScoreError(
            "live_score_already_bound",
            "$.performance_context.evidence.score_binding",
        )
    if type(duration_ms) is not int or duration_ms <= 0:
        raise LiveSpeechScoreError("media_duration_not_ready", "$.media.duration_ms")

    identity_payload = {
        "character_id": context.character.character_id,
        "context_sha256": context.context_sha256,
        "duration_ms": duration_ms,
        "media_id": context.source.media_id,
        "media_sha256": context.source.media_sha256,
        "package_digest": context.character.package_digest,
    }
    identity = sha256_ref(canonical_json_v1(identity_payload)).split(":", 1)[1]
    try:
        request = HighLevelDirectionRequestV1.from_mapping(
            {
                "schema_version": 1,
                "direction_id": "direction:speech:" + identity[:24],
                "direction_text": "speaks",
                "context_sha256": context.context_sha256,
                "intent": "speak",
                "duration_ms": duration_ms,
                "media_id": context.source.media_id,
                "media_sha256": context.source.media_sha256,
                "seed": int(identity[:13], 16),
            }
        )
        compilation = compile_high_level_direction(
            request,
            context,
            capability_manifest,
        )
        score = CompiledScoreLoader().from_mapping(compilation.compiled_score)
        publication = repository.publish(score)
    except DirectionCompileError as exc:
        raise LiveSpeechScoreError(exc.code, "$.performance_context") from exc
    except ScoreValidationError as exc:
        raise LiveSpeechScoreError(exc.code, exc.path) from exc

    binding = LiveSpeechScoreBindingV1(
        schema_version=1,
        score_id=publication.compiled_score_id,
        score_revision=publication.revision,
        score_sha256=publication.score_sha256,
        compiled_from_context_sha256=context.context_sha256,
        character_id=context.character.character_id,
        package_digest=context.character.package_digest,
        media_id=context.source.media_id,
        media_sha256=context.source.media_sha256,
    )
    return PreparedLiveSpeechScoreV1(1, context, binding)


__all__ = [
    "LiveSpeechScoreBindingV1",
    "LiveSpeechScoreError",
    "PreparedLiveSpeechScoreV1",
    "compile_live_speech_score",
]
