"""Deterministic controlled-language direction compiler for Character Director."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .artifact_hashing import canonical_json_v1, sha256_ref
from .performance_compiler import (
    compile_character_bound_performance,
)
from .performance_context import PerformanceContextV1
from .schema_validation import ContractValidationError, SchemaRegistry


DIRECTION_COMPILER_VERSION = "controlled-direction-compiler-v1"
_PRIVATE_VALUE_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+\S"),
    re.compile(r"(?i)\bbasic\s+\S"),
    re.compile(r"(?i)\b(?:sk|xox[baprs]|gh[opusr])[-_][a-z0-9]"),
    re.compile(r"(?i)-----BEGIN\s"),
)
_CHARACTER_PREFIX = re.compile(r"^(?:wizard joe|joe)\s+")
_LEADING_JOINER = re.compile(r"^(?:and|then)\s+")
_ENTER = re.compile(
    r"^(?:enters?|walks?|moves?)(?:\s+in)?"
    r"(?:\s+from\s+(?P<source>stage-left rear|stage-right rear|stage-left|stage-right|center stage|center))?"
    r"(?:\s+(?:toward|to)\s+(?P<destination>stage-left|stage-right|center stage|center))?"
    r"(?:\s+over\s+(?P<seconds>one|two|three|four|five)\s+seconds?)?$"
)
_CIRCLE = re.compile(
    r"^circles?(?:\s+(?:toward|to|around))?\s+(?P<destination>center stage|center)$"
)
_TELL = re.compile(
    r"^(?:speaks?|explains?|tells?)(?:\s+(?:the\s+)?user)?(?:\s+something(?:\s+important)?)?$"
)
_SECONDS = {"one": 1000, "two": 2000, "three": 3000, "four": 4000, "five": 5000}


class DirectionCompileError(ValueError):
    """A stable, content-free failure from high-level direction compilation."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _hash(value: object) -> str:
    return sha256_ref(canonical_json_v1(value))


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class HighLevelDirectionRequestV1:
    schema_version: int
    direction_id: str
    direction_text: str
    context_sha256: str
    intent: str
    duration_ms: int
    media_id: str
    media_sha256: str
    seed: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "HighLevelDirectionRequestV1":
        try:
            SchemaRegistry().validate("HighLevelDirectionRequestV1", value)
        except ContractValidationError as exc:
            raise DirectionCompileError(exc.code, "direction request is invalid") from exc
        text = str(value["direction_text"])
        if any(pattern.search(text) is not None for pattern in _PRIVATE_VALUE_PATTERNS):
            raise DirectionCompileError("private_content", "direction request contains private content")
        media_sha256 = str(value["media_sha256"])
        if value["media_id"] != "media:sha256:" + media_sha256.split(":", 1)[1]:
            raise DirectionCompileError("hash_mismatch", "direction media identity is invalid")
        return cls(
            schema_version=1,
            direction_id=str(value["direction_id"]),
            direction_text=text,
            context_sha256=str(value["context_sha256"]),
            intent=str(value["intent"]),
            duration_ms=int(value["duration_ms"]),
            media_id=str(value["media_id"]),
            media_sha256=media_sha256,
            seed=int(value["seed"]),
        )

    def to_mapping(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "direction_id": self.direction_id,
            "direction_text": self.direction_text,
            "context_sha256": self.context_sha256,
            "intent": self.intent,
            "duration_ms": self.duration_ms,
            "media_id": self.media_id,
            "media_sha256": self.media_sha256,
            "seed": self.seed,
        }


@dataclass(frozen=True)
class DirectionPlanFallbackV1:
    step_id: str
    requested_shape: str
    selected_shape: str
    reason_code: str

    def to_mapping(self) -> Dict[str, str]:
        return {
            "step_id": self.step_id,
            "requested_shape": self.requested_shape,
            "selected_shape": self.selected_shape,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class DirectionPlanStepV1:
    step_id: str
    intent: str
    track_kind: str
    capability_requirement: str
    start_ms: int
    end_ms: int
    weight_ms: int
    execution: Mapping[str, object]

    def to_mapping(self) -> Dict[str, object]:
        return {
            "step_id": self.step_id,
            "intent": self.intent,
            "track_kind": self.track_kind,
            "capability_requirement": self.capability_requirement,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "weight_ms": self.weight_ms,
            "execution": _thaw(self.execution),
        }


@dataclass(frozen=True)
class DirectionPerformancePlanV1:
    schema_version: int
    plan_id: str
    direction_sha256: str
    compiler_version: str
    steps: Tuple[DirectionPlanStepV1, ...]
    fallbacks: Tuple[DirectionPlanFallbackV1, ...]
    plan_sha256: str

    def to_mapping(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "direction_sha256": self.direction_sha256,
            "compiler_version": self.compiler_version,
            "steps": [step.to_mapping() for step in self.steps],
            "fallbacks": [item.to_mapping() for item in self.fallbacks],
            "plan_sha256": self.plan_sha256,
        }


@dataclass(frozen=True)
class DirectedPerformanceCompilation:
    plan: DirectionPerformancePlanV1
    portable_score: Mapping[str, object]
    bound_context: PerformanceContextV1
    compiled_score: Mapping[str, object]


@dataclass(frozen=True)
class _StepSpec:
    intent: str
    track_kind: str
    capability_requirement: str
    weight_ms: int
    execution: Mapping[str, object]
    requested_shape: Optional[str] = None
    selected_shape: Optional[str] = None
    fallback_reason: Optional[str] = None


def compile_high_level_direction(
    request: HighLevelDirectionRequestV1,
    context: PerformanceContextV1,
    capability_manifest: Mapping[str, object],
) -> DirectedPerformanceCompilation:
    """Compile controlled natural-language direction through the existing score runtime."""

    if not isinstance(request, HighLevelDirectionRequestV1):
        raise DirectionCompileError("direction_invalid", "direction request has the wrong type")
    if not isinstance(context, PerformanceContextV1):
        raise DirectionCompileError("context_invalid", "performance context has the wrong type")
    if request.context_sha256 != context.context_sha256:
        raise DirectionCompileError("stale_binding", "direction context binding is stale")
    if request.intent in context.governance.denied_semantic_actions:
        raise DirectionCompileError("direction_not_authorized", "direction intent is denied")
    if request.intent not in context.governance.allowed_semantic_actions:
        raise DirectionCompileError("direction_not_authorized", "direction intent is not allowed")
    if context.approval.presentation_state != "approved_for_presentation":
        raise DirectionCompileError("presentation_not_approved", "direction presentation is not approved")

    direction_sha256 = _hash(request.to_mapping())
    specs = _parse_direction(request.direction_text, context)
    if any(spec.intent == "celebrate" for spec in specs) and request.intent != "celebrate":
        raise DirectionCompileError(
            "direction_intent_mismatch",
            "direction behavior does not match its governed intent",
        )
    steps, fallbacks = _schedule_specs(specs, request.duration_ms, direction_sha256)
    plan = _build_plan(direction_sha256, steps, fallbacks)
    portable_score = _build_portable_score(request, plan)
    bound_context = _bind_context(context, request, portable_score)
    compiled_score = compile_character_bound_performance(
        bound_context,
        portable_score,
        capability_manifest,
    )
    return DirectedPerformanceCompilation(
        plan=plan,
        portable_score=copy.deepcopy(portable_score),
        bound_context=bound_context,
        compiled_score=copy.deepcopy(compiled_score),
    )


def _normalize_clauses(text: str) -> Tuple[str, ...]:
    normalized = text.lower().replace("\u2019", "'")
    normalized = re.sub(r"\bthen\b", ",", normalized)
    clauses = []
    for raw in re.split(r"[,;]+", normalized):
        clause = raw.strip().rstrip(".!?")
        clause = _LEADING_JOINER.sub("", clause)
        clause = _CHARACTER_PREFIX.sub("", clause)
        if clause:
            clauses.append(re.sub(r"\s+", " ", clause))
    return tuple(clauses)


def _parse_direction(text: str, context: PerformanceContextV1) -> Tuple[_StepSpec, ...]:
    clauses = _normalize_clauses(text)
    if not clauses or len(clauses) > 32:
        raise DirectionCompileError("direction_invalid", "direction requires one to 32 clauses")
    anchors = _stage_anchors(context)
    current_position = anchors["current"]
    specs: List[_StepSpec] = []
    for clause in clauses:
        clause_specs, current_position = _parse_clause(clause, anchors, current_position)
        if not clause_specs:
            raise DirectionCompileError(
                "direction_unsupported",
                "direction contains an unsupported clause",
            )
        specs.extend(clause_specs)
    if not specs:
        raise DirectionCompileError("direction_unsupported", "direction has no supported behavior")
    return tuple(specs)


def _parse_clause(
    clause: str,
    anchors: Mapping[str, Tuple[int, int]],
    current_position: Tuple[int, int],
) -> Tuple[Tuple[_StepSpec, ...], Tuple[int, int]]:
    delighted = "with delighted surprise" in clause
    if delighted:
        clause = re.sub(r"\s+with delighted surprise", "", clause).strip()

    enter = _ENTER.fullmatch(clause)
    if enter is not None:
        source_name = enter.group("source") or "stage-left rear"
        destination_name = enter.group("destination")
        source = _anchor(source_name, anchors)
        destination = (
            _anchor(destination_name, anchors)
            if destination_name is not None
            else _interpolate(source, anchors["center"], 450)
        )
        weight = _SECONDS.get(enter.group("seconds") or "", 1400)
        result: List[_StepSpec] = []
        if delighted:
            result.append(
                _StepSpec(
                    "greet",
                    "face",
                    "face.surprised",
                    500,
                    MappingProxyType({"expression": "surprised"}),
                )
            )
        result.append(_stage_step(source, destination, weight))
        return tuple(result), destination

    circle = _CIRCLE.fullmatch(clause)
    if circle is not None:
        destination = _anchor(circle.group("destination"), anchors)
        return (
            (
                _StepSpec(
                    "transition",
                    "stage",
                    "locomotion.stage_walk",
                    1800,
                    _trajectory(current_position, destination),
                    requested_shape="circle_path",
                    selected_shape="linear_stage_trajectory",
                    fallback_reason="circle_to_linear_stage_fallback",
                ),
            ),
            destination,
        )

    if clause in {"stops", "stop", "plants", "plants the feet"}:
        return (
            (_StepSpec("settle", "body_base", "body.settle_grounded", 500, MappingProxyType({})),),
            current_position,
        )
    if clause in {"turns toward the viewer", "turn toward the viewer", "faces the viewer"}:
        return (
            (
                _StepSpec(
                    "transition",
                    "body_base",
                    "body.viewer_turn",
                    700,
                    MappingProxyType({"facing": "south"}),
                ),
            ),
            current_position,
        )
    if clause in {
        "transition to warm seriousness",
        "transitions to warm seriousness",
        "becomes warmly serious",
        "warm seriousness",
    }:
        return (
            (
                _StepSpec(
                    "explain",
                    "face",
                    "face.focused",
                    800,
                    MappingProxyType({"expression": "focused"}),
                ),
            ),
            current_position,
        )
    if clause in {"raises the right hand", "raise the right hand", "raises a hand"}:
        return (
            (_StepSpec("explain", "body_base", "gesture.point", 900, MappingProxyType({})),),
            current_position,
        )
    if re.fullmatch(r"holds?(?: for)? one second", clause):
        return (
            (_StepSpec("explain", "body_base", "gesture.point", 1000, MappingProxyType({})),),
            current_position,
        )
    if clause in {"leans closer", "leans toward the viewer", "leans in"}:
        return (
            (_StepSpec("explain", "body_base", "gesture.point", 700, MappingProxyType({})),),
            current_position,
        )
    if _TELL.fullmatch(clause) is not None:
        return (
            (_StepSpec("explain", "body_base", "body.explain", 1900, MappingProxyType({})),),
            current_position,
        )
    if clause in {"celebrates", "celebrate", "celebrates warmly"}:
        return (
            (_StepSpec("celebrate", "body_base", "body.celebrate_grounded", 1400, MappingProxyType({})),),
            current_position,
        )
    return (), current_position


def _stage_anchors(context: PerformanceContextV1) -> Dict[str, Tuple[int, int]]:
    bounds = context.display.stage_bounds_milli
    x = int(bounds["x"])
    y = int(bounds["y"])
    width = int(bounds["width"])
    height = int(bounds["height"])
    left = x + width // 10
    right = x + (width * 9) // 10
    center_x = x + width // 2
    rear = y + height // 7
    middle = y + (height * 4) // 7
    current = (
        min(1000, max(0, int(context.character.position_milli["x"]))),
        min(1000, max(0, int(context.character.position_milli["z"]))),
    )
    return {
        "stage-left rear": (left, rear),
        "stage-right rear": (right, rear),
        "stage-left": (left, middle),
        "stage-right": (right, middle),
        "center stage": (center_x, middle),
        "center": (center_x, middle),
        "current": current,
    }


def _anchor(name: str, anchors: Mapping[str, Tuple[int, int]]) -> Tuple[int, int]:
    return anchors[name]


def _interpolate(
    source: Tuple[int, int], destination: Tuple[int, int], amount_milli: int
) -> Tuple[int, int]:
    return (
        source[0] + ((destination[0] - source[0]) * amount_milli) // 1000,
        source[1] + ((destination[1] - source[1]) * amount_milli) // 1000,
    )


def _trajectory(
    source: Tuple[int, int], destination: Tuple[int, int]
) -> Mapping[str, object]:
    return MappingProxyType(
        {
            "trajectory": MappingProxyType(
                {
                    "source_position_milli": source,
                    "destination_position_milli": destination,
                    "easing_id": "smoothstep_v1",
                }
            ),
            "facing": "south",
        }
    )


def _stage_step(
    source: Tuple[int, int], destination: Tuple[int, int], weight_ms: int
) -> _StepSpec:
    return _StepSpec(
        "transition",
        "stage",
        "locomotion.stage_walk",
        weight_ms,
        _trajectory(source, destination),
    )


def _schedule_specs(
    specs: Sequence[_StepSpec], duration_ms: int, direction_sha256: str
) -> Tuple[Tuple[DirectionPlanStepV1, ...], Tuple[DirectionPlanFallbackV1, ...]]:
    total_weight = sum(item.weight_ms for item in specs)
    if total_weight <= 0 or duration_ms < len(specs):
        raise DirectionCompileError("duration_too_short", "direction duration is too short")
    cursor = 0
    steps: List[DirectionPlanStepV1] = []
    fallbacks: List[DirectionPlanFallbackV1] = []
    token = direction_sha256.split(":", 1)[1][:16]
    for index, spec in enumerate(specs):
        remaining_steps = len(specs) - index - 1
        if index == len(specs) - 1:
            end_ms = duration_ms
        else:
            scaled = max(1, (duration_ms * spec.weight_ms) // total_weight)
            end_ms = min(duration_ms - remaining_steps, cursor + scaled)
        step_id = "directed:{}:step:{:03d}".format(token, index + 1)
        step = DirectionPlanStepV1(
            step_id=step_id,
            intent=spec.intent,
            track_kind=spec.track_kind,
            capability_requirement=spec.capability_requirement,
            start_ms=cursor,
            end_ms=end_ms,
            weight_ms=spec.weight_ms,
            execution=spec.execution,
        )
        steps.append(step)
        if spec.fallback_reason is not None:
            fallbacks.append(
                DirectionPlanFallbackV1(
                    step_id=step_id,
                    requested_shape=spec.requested_shape or "unsupported",
                    selected_shape=spec.selected_shape or "clear",
                    reason_code=spec.fallback_reason,
                )
            )
        cursor = end_ms
    return tuple(steps), tuple(fallbacks)


def _build_plan(
    direction_sha256: str,
    steps: Tuple[DirectionPlanStepV1, ...],
    fallbacks: Tuple[DirectionPlanFallbackV1, ...],
) -> DirectionPerformancePlanV1:
    body = {
        "schema_version": 1,
        "direction_sha256": direction_sha256,
        "compiler_version": DIRECTION_COMPILER_VERSION,
        "steps": [step.to_mapping() for step in steps],
        "fallbacks": [item.to_mapping() for item in fallbacks],
    }
    digest = _hash(body)
    plan_id = "direction-plan:" + digest.split(":", 1)[1][:24]
    plan_body = {"plan_id": plan_id, **body}
    plan_sha256 = _hash(plan_body)
    return DirectionPerformancePlanV1(
        schema_version=1,
        plan_id=plan_id,
        direction_sha256=direction_sha256,
        compiler_version=DIRECTION_COMPILER_VERSION,
        steps=steps,
        fallbacks=fallbacks,
        plan_sha256=plan_sha256,
    )


def _build_portable_score(
    request: HighLevelDirectionRequestV1,
    plan: DirectionPerformancePlanV1,
) -> Dict[str, object]:
    track_order = (
        "narrative_state",
        "stage",
        "locomotion",
        "body_base",
        "transition",
        "gesture",
        "face",
        "gaze",
        "speech",
        "blink",
        "dance",
        "effects",
        "manual_override",
    )
    tracks = []
    for track_kind in track_order:
        matching = [step for step in plan.steps if step.track_kind == track_kind]
        if not matching:
            continue
        cues = []
        for step in matching:
            cue: Dict[str, object] = {
                "cue_id": step.step_id,
                "start_ms": step.start_ms,
                "end_ms": step.end_ms,
                "intent": step.intent,
                "source_ids": [plan.plan_id],
                "priority": 60,
                "amplitude_milli": 500,
                "capability_requirements": [step.capability_requirement],
                "fallback_intents": ["body.characterful_neutral", "still"],
                "interrupt_policy": "at_phase_boundary",
                "cooldown_class": "directed_ordinary",
                "motif_id": None,
                "confidence": {
                    "alignment_milli": 1000,
                    "evidence_milli": 1000,
                    "planner_milli": 1000,
                },
                "manual": {"locked": False, "disabled": False},
            }
            if step.execution:
                cue["execution"] = _thaw(step.execution)
            cues.append(cue)
        tracks.append(
            {
                "track_id": "directed-" + track_kind.replace("_", "-"),
                "kind": track_kind,
                "exclusive": True,
                "max_active": 1,
                "gap_policy": "characterful_neutral" if track_kind == "body_base" else "clear",
                "cues": cues,
            }
        )

    analysis_id = "direction:" + plan.direction_sha256.split(":", 1)[1][:24]
    body: Dict[str, object] = {
        "schema_version": 1,
        "revision": 1,
        "status": "accepted",
        "mode": "directed",
        "media": {
            "media_id": request.media_id,
            "media_sha256": request.media_sha256,
            "duration_ms": request.duration_ms,
        },
        "analysis_ref": {
            "kind": "direction",
            "artifact_id": analysis_id,
            "artifact_sha256": plan.plan_sha256,
        },
        "tracks": tracks,
        "provenance": {
            "pipeline_version": DIRECTION_COMPILER_VERSION,
            "prompt_bundle_sha256": None,
            "provider_run_sha256": None,
            "seed": request.seed,
            "parent_score_sha256": None,
            "edit_set_sha256": None,
        },
        "validation": {
            "policy_sha256": _hash(
                {
                    "compiler_version": DIRECTION_COMPILER_VERSION,
                    "controlled_language": True,
                    "model_calls": False,
                    "manifest_binding_required": True,
                }
            ),
            "report_sha256": _hash(
                {
                    "decision": "accepted",
                    "plan_sha256": plan.plan_sha256,
                    "step_count": len(plan.steps),
                    "fallbacks": [item.to_mapping() for item in plan.fallbacks],
                }
            ),
            "decision": "accepted",
        },
    }
    score_identity = _hash(body).split(":", 1)[1][:24]
    return {"score_id": "performance:directed:" + score_identity, **body}


def _bind_context(
    context: PerformanceContextV1,
    request: HighLevelDirectionRequestV1,
    score: Mapping[str, object],
) -> PerformanceContextV1:
    raw = context.content_dict()
    raw["source"]["media_id"] = request.media_id  # type: ignore[index]
    raw["source"]["media_sha256"] = request.media_sha256  # type: ignore[index]
    raw["clock"]["authoritative_media_position_ms"] = 0  # type: ignore[index]
    raw["conversation"]["intent"] = request.intent  # type: ignore[index]
    raw["evidence"]["score_binding"] = {  # type: ignore[index]
        "score_id": score["score_id"],
        "score_revision": score["revision"],
        "score_sha256": _hash(score),
    }
    return PerformanceContextV1.build(raw)


__all__ = [
    "DIRECTION_COMPILER_VERSION",
    "DirectionCompileError",
    "HighLevelDirectionRequestV1",
    "DirectionPlanFallbackV1",
    "DirectionPlanStepV1",
    "DirectionPerformancePlanV1",
    "DirectedPerformanceCompilation",
    "compile_high_level_direction",
]
