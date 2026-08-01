"""Transactional preparation for governed high-level character direction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .direction_compiler import (
    DirectionCompileError,
    DirectionPerformancePlanV1,
    HighLevelDirectionRequestV1,
    compile_high_level_direction,
)
from .performance_context import PerformanceContextV1
from .performance_release import PerformanceContextRequestV1
from .performance_score import (
    CompiledPerformanceScore,
    CompiledScoreLoader,
    CompiledScoreRepository,
    ScoreValidationError,
)
from .schema_validation import (
    ContractValidationError,
    SchemaRegistry,
    load_and_validate_json,
)


DIRECTED_PERFORMANCE_MAX_BODY_BYTES = 64 * 1024


class DirectedPerformanceError(ValueError):
    """A stable, content-free directed-performance preparation failure."""

    def __init__(self, code: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        super().__init__(code)


@dataclass(frozen=True)
class DirectedPerformancePreparationV1:
    schema_version: int
    source_slot: str
    context_request: PerformanceContextRequestV1
    direction_id: str
    direction_text: str
    intent: str
    duration_ms: int
    media_id: str
    media_sha256: str
    seed: int

    @classmethod
    def _from_validated_mapping(
        cls,
        value: Mapping[str, object],
    ) -> "DirectedPerformancePreparationV1":
        try:
            context_request = PerformanceContextRequestV1.from_mapping(
                value["context_request"]
            )
        except ValueError as exc:
            raise DirectedPerformanceError(
                str(getattr(exc, "code", "schema_invalid")),
                str(getattr(exc, "path", "$")),
            ) from exc
        direction = value["direction"]
        assert isinstance(direction, Mapping)
        return cls(
            schema_version=1,
            source_slot=str(value["source_slot"]),
            context_request=context_request,
            direction_id=str(direction["direction_id"]),
            direction_text=str(direction["direction_text"]),
            intent=str(direction["intent"]),
            duration_ms=int(direction["duration_ms"]),
            media_id=str(direction["media_id"]),
            media_sha256=str(direction["media_sha256"]),
            seed=int(direction["seed"]),
        )

    @classmethod
    def from_mapping(
        cls,
        raw: Mapping[str, object],
    ) -> "DirectedPerformancePreparationV1":
        try:
            value = SchemaRegistry().validate(
                "DirectedPerformancePreparationV1",
                raw,
            )
        except ContractValidationError as exc:
            raise DirectedPerformanceError(exc.code, exc.path) from exc
        return cls._from_validated_mapping(value)

    @classmethod
    def from_json(cls, payload: bytes) -> "DirectedPerformancePreparationV1":
        if len(payload) > DIRECTED_PERFORMANCE_MAX_BODY_BYTES:
            raise DirectedPerformanceError("body_too_large")
        try:
            value = load_and_validate_json(
                payload,
                "DirectedPerformancePreparationV1",
            )
        except ContractValidationError as exc:
            raise DirectedPerformanceError(exc.code, exc.path) from exc
        return cls._from_validated_mapping(value)

    def bind_context(
        self,
        context: PerformanceContextV1,
    ) -> HighLevelDirectionRequestV1:
        try:
            return HighLevelDirectionRequestV1.from_mapping(
                {
                    "schema_version": 1,
                    "direction_id": self.direction_id,
                    "direction_text": self.direction_text,
                    "context_sha256": context.context_sha256,
                    "intent": self.intent,
                    "duration_ms": self.duration_ms,
                    "media_id": self.media_id,
                    "media_sha256": self.media_sha256,
                    "seed": self.seed,
                }
            )
        except DirectionCompileError as exc:
            raise DirectedPerformanceError(exc.code, "$.direction") from exc


@dataclass(frozen=True)
class CompiledDirectedPerformanceV1:
    preparation: DirectedPerformancePreparationV1
    preliminary_context: PerformanceContextV1
    compiler_context: PerformanceContextV1
    compiler_context_sha256: str
    plan: DirectionPerformancePlanV1
    portable_score: Mapping[str, object]
    score: CompiledPerformanceScore


@dataclass(frozen=True)
class DirectedPerformanceScoreBindingV1:
    schema_version: int
    score_id: str
    score_revision: int
    score_sha256: str
    prepared_from_context_sha256: str
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
            "prepared_from_context_sha256": self.prepared_from_context_sha256,
            "compiled_from_context_sha256": self.compiled_from_context_sha256,
            "character_id": self.character_id,
            "package_digest": self.package_digest,
            "media_id": self.media_id,
            "media_sha256": self.media_sha256,
        }


@dataclass(frozen=True)
class PreparedDirectedPerformanceV1:
    schema_version: int
    preliminary_context: PerformanceContextV1
    plan: DirectionPerformancePlanV1
    score_binding: DirectedPerformanceScoreBindingV1

    def to_dict(self) -> Mapping[str, object]:
        return {
            "schema_version": self.schema_version,
            "preliminary_context": self.preliminary_context.to_dict(),
            "plan": self.plan.to_mapping(),
            "score_binding": self.score_binding.to_dict(),
        }


def compile_directed_performance(
    preparation: DirectedPerformancePreparationV1,
    context: PerformanceContextV1,
    *,
    capability_manifest: Mapping[str, object],
) -> CompiledDirectedPerformanceV1:
    """Compile one context-bound candidate without mutating the repository."""

    if context.source.source_slot != preparation.source_slot:
        raise DirectedPerformanceError("source_slot_mismatch", "$.source_slot")
    if (
        context.source.media_id != preparation.media_id
        or context.source.media_sha256 != preparation.media_sha256
    ):
        raise DirectedPerformanceError("media_mismatch", "$.direction.media_id")
    if context.conversation.intent != preparation.intent:
        raise DirectedPerformanceError("direction_intent_mismatch", "$.direction.intent")
    score_binding = context.evidence.score_binding
    if (
        score_binding.score_id is not None
        or score_binding.score_revision is not None
        or score_binding.score_sha256 is not None
    ):
        raise DirectedPerformanceError(
            "directed_score_already_bound",
            "$.preliminary_context.evidence.score_binding",
        )
    try:
        compilation = compile_high_level_direction(
            preparation.bind_context(context),
            context,
            capability_manifest,
        )
        score = CompiledScoreLoader().from_mapping(compilation.compiled_score)
    except DirectionCompileError as exc:
        raise DirectedPerformanceError(exc.code, "$.direction") from exc
    except ScoreValidationError as exc:
        raise DirectedPerformanceError(exc.code, exc.path) from exc
    return CompiledDirectedPerformanceV1(
        preparation=preparation,
        preliminary_context=context,
        compiler_context=compilation.bound_context,
        compiler_context_sha256=compilation.bound_context.context_sha256,
        plan=compilation.plan,
        portable_score=compilation.portable_score,
        score=score,
    )


def publish_directed_performance(
    compiled: CompiledDirectedPerformanceV1,
    *,
    repository: CompiledScoreRepository,
) -> PreparedDirectedPerformanceV1:
    """Atomically publish a previously compiled and revalidated candidate."""

    if not isinstance(compiled, CompiledDirectedPerformanceV1):
        raise TypeError("compiled must be a CompiledDirectedPerformanceV1")
    try:
        publication = repository.publish(compiled.score)
    except ScoreValidationError as exc:
        raise DirectedPerformanceError(exc.code, exc.path) from exc
    context = compiled.preliminary_context
    binding = DirectedPerformanceScoreBindingV1(
        schema_version=1,
        score_id=publication.compiled_score_id,
        score_revision=publication.revision,
        score_sha256=publication.score_sha256,
        prepared_from_context_sha256=context.context_sha256,
        compiled_from_context_sha256=compiled.compiler_context_sha256,
        character_id=context.character.character_id,
        package_digest=context.character.package_digest,
        media_id=context.source.media_id,
        media_sha256=context.source.media_sha256,
    )
    return PreparedDirectedPerformanceV1(
        schema_version=1,
        preliminary_context=context,
        plan=compiled.plan,
        score_binding=binding,
    )


__all__ = [
    "CompiledDirectedPerformanceV1",
    "DIRECTED_PERFORMANCE_MAX_BODY_BYTES",
    "DirectedPerformanceError",
    "DirectedPerformancePreparationV1",
    "DirectedPerformanceScoreBindingV1",
    "PreparedDirectedPerformanceV1",
    "compile_directed_performance",
    "publish_directed_performance",
]
