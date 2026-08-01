"""Apply immutable director edits and recompile through the normal score path."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Dict, Mapping, MutableMapping, Sequence, Tuple, Union

from .artifact_hashing import canonical_json_v1, sha256_ref
from .performance_compiler import PerformanceCompileError, compile_character_bound_performance
from .performance_context import PerformanceContextError, PerformanceContextV1
from .performance_score import (
    CompiledPerformanceScore,
    CompiledScoreLoader,
    CompiledScoreRepository,
    ScorePublication,
    ScoreValidationError,
)
from .schema_validation import ContractValidationError, SchemaRegistry
from .score_edits import ScoreEditOperationV1, ScoreEditsV1, ScoreEditsValidationError


class ScoreEditApplicationError(ValueError):
    """Stable, path-addressed failure while applying or publishing score edits."""

    def __init__(self, code: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        super().__init__(code)


@dataclass(frozen=True)
class AppliedScoreEditsV1:
    schema_version: int
    base_score_sha256: str
    edit_set_sha256: str
    revised_score_sha256: str
    portable_score: Mapping[str, object]
    bound_context: PerformanceContextV1
    compiled_score: CompiledPerformanceScore

    def to_dict(self) -> Mapping[str, object]:
        return {
            "schema_version": self.schema_version,
            "base_score_sha256": self.base_score_sha256,
            "edit_set_sha256": self.edit_set_sha256,
            "revised_score_sha256": self.revised_score_sha256,
            "compiled_score_id": self.compiled_score.compiled_score_id,
            "compiled_score_revision": self.compiled_score.revision,
            "compiled_score_sha256": self.compiled_score.artifact_sha256,
            "context_sha256": self.bound_context.context_sha256,
        }


@dataclass(frozen=True)
class PublishedScoreEditsV1:
    applied: AppliedScoreEditsV1
    publication: ScorePublication

    def to_dict(self) -> Mapping[str, object]:
        return {
            "schema_version": 1,
            "applied": self.applied.to_dict(),
            "publication": self.publication.to_dict(),
        }


def score_edit_target_value(
    score: Mapping[str, object],
    cue_id: str,
    edit_type: str,
) -> object:
    """Return the canonical precondition value for one editable cue field."""

    cue, _path = _find_cue(score, cue_id)
    if edit_type == "timing_offset_ms":
        return {
            "start_ms": cue["start_ms"],
            "end_ms": cue["end_ms"],
            "phase_ranges": copy.deepcopy(cue.get("phase_ranges")),
        }
    if edit_type == "duration_ms":
        return int(cue["end_ms"]) - int(cue["start_ms"])
    if edit_type == "intensity_milli":
        return cue["amplitude_milli"]
    if edit_type == "disabled":
        manual = _mutable_mapping(cue.get("manual"), "cue manual state")
        return manual["disabled"]
    if edit_type in {"semantic_clip_id", "semantic_pose_id", "semantic_action_id"}:
        return copy.deepcopy(cue["capability_requirements"])
    if edit_type in {"semantic_expression_id", "semantic_gaze_id"}:
        field = "expression" if edit_type == "semantic_expression_id" else "gaze_target"
        execution = cue.get("execution")
        current = execution.get(field) if isinstance(execution, Mapping) else None
        return {
            "capability_requirements": copy.deepcopy(cue["capability_requirements"]),
            field: current,
        }
    raise ScoreEditApplicationError("unsafe_edit_type")


def score_edit_target_sha256(
    score: Mapping[str, object],
    cue_id: str,
    edit_type: str,
) -> str:
    return sha256_ref(canonical_json_v1(score_edit_target_value(score, cue_id, edit_type)))


def apply_score_edits(
    base_score: Mapping[str, object],
    edits: ScoreEditsV1,
    context: PerformanceContextV1,
    *,
    capability_manifest: Mapping[str, object],
) -> AppliedScoreEditsV1:
    """Apply one edit set, revalidate, bind, and character-compile deterministically."""

    if not isinstance(edits, ScoreEditsV1):
        raise TypeError("edits must be a ScoreEditsV1")
    if not isinstance(context, PerformanceContextV1):
        raise TypeError("context must be a PerformanceContextV1")
    portable = copy.deepcopy(dict(base_score))
    registry = SchemaRegistry()
    try:
        registry.validate("PerformanceScoreV1", portable)
    except ContractValidationError as exc:
        raise ScoreEditApplicationError(exc.code, exc.path) from exc
    if portable.get("status") != "accepted":
        raise ScoreEditApplicationError("artifact_not_accepted", "$.status")

    base_sha256 = sha256_ref(canonical_json_v1(portable))
    try:
        edits.validate_binding(
            character_id=context.character.character_id,
            package_digest=context.character.package_digest,
            base_score_sha256=base_sha256,
        )
    except ScoreEditsValidationError as exc:
        raise ScoreEditApplicationError(exc.code, exc.path) from exc
    binding = context.evidence.score_binding
    if binding.score_id is not None and (
        binding.score_id != portable["score_id"]
        or binding.score_revision != portable["revision"]
        or binding.score_sha256 != base_sha256
    ):
        raise ScoreEditApplicationError("stale_context_binding", "$.evidence.score_binding")

    for index, operation in enumerate(edits.operations):
        _apply_operation(portable, operation, index)

    portable["revision"] = int(portable["revision"]) + 1
    provenance = _mutable_mapping(portable.get("provenance"), "score provenance")
    provenance["parent_score_sha256"] = base_sha256
    provenance["edit_set_sha256"] = edits.edit_set_sha256
    validation = _mutable_mapping(portable.get("validation"), "score validation")
    validation["decision"] = "accepted"
    validation["report_sha256"] = sha256_ref(
        canonical_json_v1(
            {
                "decision": "accepted",
                "base_score_sha256": base_sha256,
                "edit_set_sha256": edits.edit_set_sha256,
                "operation_ids": [item.operation_id for item in edits.operations],
                "revised_revision": portable["revision"],
            }
        )
    )
    try:
        registry.validate("PerformanceScoreV1", portable)
    except ContractValidationError as exc:
        raise ScoreEditApplicationError(exc.code, exc.path) from exc
    revised_sha256 = sha256_ref(canonical_json_v1(portable))
    bound_context = _bind_context(context, portable, revised_sha256)
    try:
        compiled_mapping = compile_character_bound_performance(
            bound_context,
            portable,
            capability_manifest,
        )
        compiled_mapping = copy.deepcopy(compiled_mapping)
        compiled_mapping["revision"] = portable["revision"]
        compiled_identity = dict(compiled_mapping)
        compiled_identity.pop("compiled_score_id", None)
        compiled_mapping["compiled_score_id"] = "compiled:" + sha256_ref(
            canonical_json_v1(compiled_identity)
        ).split(":", 1)[1][:24]
        compiled = CompiledScoreLoader().from_mapping(compiled_mapping)
    except PerformanceCompileError as exc:
        raise ScoreEditApplicationError(exc.code) from exc
    except ScoreValidationError as exc:
        raise ScoreEditApplicationError(exc.code, exc.path) from exc
    return AppliedScoreEditsV1(
        schema_version=1,
        base_score_sha256=base_sha256,
        edit_set_sha256=edits.edit_set_sha256,
        revised_score_sha256=revised_sha256,
        portable_score=copy.deepcopy(portable),
        bound_context=bound_context,
        compiled_score=compiled,
    )


def publish_score_edits(
    applied: AppliedScoreEditsV1,
    *,
    repository: CompiledScoreRepository,
) -> PublishedScoreEditsV1:
    """Publish an edited compiled score through the existing atomic repository."""

    if not isinstance(applied, AppliedScoreEditsV1):
        raise TypeError("applied must be an AppliedScoreEditsV1")
    try:
        publication = repository.publish(applied.compiled_score)
    except ScoreValidationError as exc:
        raise ScoreEditApplicationError(exc.code, exc.path) from exc
    return PublishedScoreEditsV1(applied=applied, publication=publication)


def _apply_operation(
    score: MutableMapping[str, object],
    operation: ScoreEditOperationV1,
    index: int,
) -> None:
    cue, cue_path = _find_cue(score, operation.cue_id)
    manual = _mutable_mapping(cue.get("manual"), "cue manual state")
    if manual.get("locked") is True:
        raise ScoreEditApplicationError("cue_locked", cue_path + ".manual.locked")
    actual_sha256 = score_edit_target_sha256(score, operation.cue_id, operation.edit_type)
    if actual_sha256 != operation.expected_value_sha256:
        raise ScoreEditApplicationError(
            "expected_value_mismatch",
            "$.operations[{}].expected_value_sha256".format(index),
        )

    if operation.edit_type == "timing_offset_ms":
        _offset_cue(cue, int(operation.value), score, cue_path)
    elif operation.edit_type == "duration_ms":
        _resize_cue(cue, int(operation.value), score, cue_path)
    elif operation.edit_type == "intensity_milli":
        cue["amplitude_milli"] = int(operation.value)
    elif operation.edit_type == "disabled":
        manual["disabled"] = bool(operation.value)
    else:
        _replace_semantic(cue, operation.edit_type, str(operation.value))


def _offset_cue(
    cue: MutableMapping[str, object],
    offset_ms: int,
    score: Mapping[str, object],
    path: str,
) -> None:
    start_ms = int(cue["start_ms"]) + offset_ms
    end_ms = int(cue["end_ms"]) + offset_ms
    _require_score_range(start_ms, end_ms, score, path)
    cue["start_ms"] = start_ms
    cue["end_ms"] = end_ms
    phases = cue.get("phase_ranges")
    if isinstance(phases, MutableMapping):
        for name, values in tuple(phases.items()):
            phases[name] = [int(values[0]) + offset_ms, int(values[1]) + offset_ms]
    execution = cue.get("execution")
    if isinstance(execution, MutableMapping) and "phrase_phase_origin_ms" in execution:
        execution["phrase_phase_origin_ms"] = int(execution["phrase_phase_origin_ms"]) + offset_ms


def _resize_cue(
    cue: MutableMapping[str, object],
    duration_ms: int,
    score: Mapping[str, object],
    path: str,
) -> None:
    start_ms = int(cue["start_ms"])
    old_end_ms = int(cue["end_ms"])
    old_duration_ms = old_end_ms - start_ms
    end_ms = start_ms + duration_ms
    _require_score_range(start_ms, end_ms, score, path)
    phases = cue.get("phase_ranges")
    if isinstance(phases, MutableMapping):
        names = [name for name in ("anticipation", "stroke", "hold", "release", "settle") if name in phases]
        if duration_ms < len(names):
            raise ScoreEditApplicationError("duration_too_short_for_phases", path + ".phase_ranges")
        cursor = start_ms
        for phase_index, name in enumerate(names):
            old_range = phases[name]
            remaining = len(names) - phase_index - 1
            if remaining == 0:
                boundary = end_ms
            else:
                relative_end = int(old_range[1]) - start_ms
                projected = start_ms + (relative_end * duration_ms) // old_duration_ms
                boundary = max(cursor + 1, min(projected, end_ms - remaining))
            phases[name] = [cursor, boundary]
            cursor = boundary
    execution = cue.get("execution")
    if isinstance(execution, MutableMapping) and "phrase_phase_origin_ms" in execution:
        origin = int(execution["phrase_phase_origin_ms"])
        relative = max(0, min(old_duration_ms, origin - start_ms))
        execution["phrase_phase_origin_ms"] = start_ms + (relative * duration_ms) // old_duration_ms
    cue["end_ms"] = end_ms


def _replace_semantic(
    cue: MutableMapping[str, object],
    edit_type: str,
    semantic_id: str,
) -> None:
    leaf = semantic_id.rsplit(":", 1)[-1]
    if edit_type == "semantic_clip_id":
        cue["capability_requirements"] = ["clip:" + leaf]
    elif edit_type == "semantic_pose_id":
        cue["capability_requirements"] = ["pose:" + leaf]
    elif edit_type == "semantic_action_id":
        cue["capability_requirements"] = [semantic_id]
    elif edit_type in {"semantic_expression_id", "semantic_gaze_id"}:
        prefix = "expression:" if edit_type == "semantic_expression_id" else "gaze:"
        cue["capability_requirements"] = [prefix + leaf]
        execution = cue.setdefault("execution", {})
        execution_mapping = _mutable_mapping(execution, "cue execution")
        field = "expression" if edit_type == "semantic_expression_id" else "gaze_target"
        execution_mapping[field] = semantic_id
    else:
        raise ScoreEditApplicationError("unsafe_edit_type")


def _require_score_range(
    start_ms: int,
    end_ms: int,
    score: Mapping[str, object],
    path: str,
) -> None:
    media = score.get("media")
    if not isinstance(media, Mapping):
        raise ScoreEditApplicationError("score_invalid", "$.media")
    duration_ms = int(media["duration_ms"])
    if start_ms < 0 or end_ms <= start_ms or end_ms > duration_ms:
        raise ScoreEditApplicationError("time_out_of_bounds", path)


def _bind_context(
    context: PerformanceContextV1,
    score: Mapping[str, object],
    score_sha256: str,
) -> PerformanceContextV1:
    raw = context.content_dict()
    evidence = _mutable_mapping(raw.get("evidence"), "context evidence")
    evidence["score_binding"] = {
        "score_id": score["score_id"],
        "score_revision": score["revision"],
        "score_sha256": score_sha256,
    }
    try:
        return PerformanceContextV1.build(raw)
    except PerformanceContextError as exc:
        raise ScoreEditApplicationError(exc.code, exc.path) from exc


def _find_cue(
    score: Mapping[str, object],
    cue_id: str,
) -> Tuple[MutableMapping[str, object], str]:
    found = []
    tracks = score.get("tracks")
    if not isinstance(tracks, Sequence) or isinstance(tracks, (str, bytes)):
        raise ScoreEditApplicationError("score_invalid", "$.tracks")
    for track_index, track in enumerate(tracks):
        if not isinstance(track, Mapping):
            continue
        cues = track.get("cues")
        if not isinstance(cues, Sequence) or isinstance(cues, (str, bytes)):
            continue
        for cue_index, cue in enumerate(cues):
            if isinstance(cue, MutableMapping) and cue.get("cue_id") == cue_id:
                found.append((cue, "$.tracks[{}].cues[{}]".format(track_index, cue_index)))
    if not found:
        raise ScoreEditApplicationError("cue_not_found", "$.operations")
    if len(found) != 1:
        raise ScoreEditApplicationError("duplicate_cue_id", "$.tracks")
    return found[0]


def _mutable_mapping(value: object, name: str) -> MutableMapping[str, object]:
    if not isinstance(value, MutableMapping):
        raise ScoreEditApplicationError("invalid_type", "$." + name.replace(" ", "_"))
    return value


__all__ = [
    "AppliedScoreEditsV1",
    "PublishedScoreEditsV1",
    "ScoreEditApplicationError",
    "apply_score_edits",
    "publish_score_edits",
    "score_edit_target_sha256",
    "score_edit_target_value",
]
