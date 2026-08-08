"""Deterministic score preparation for one governed live-speech turn."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Tuple

from .artifact_hashing import canonical_json_v1, sha256_ref
from .character_choreography import (
    CharacterChoreographyDictionaryV1,
    ChoreographyIntentBindingV1,
    load_character_choreography_dictionary,
)
from .performance_compiler import (
    PerformanceCompileError,
    compile_character_bound_performance,
)
from .performance_context import PerformanceContextV1
from .performance_score import (
    CompiledPerformanceScore,
    CompiledScoreLoader,
    CompiledScoreRepository,
    ScoreValidationError,
)


_LIVE_SPEECH_CHOREOGRAPHY_POLICY_VERSION = "live-speech-choreography-v1"
_WIZARD_JOE_DICTIONARY_PATH = (
    Path(__file__).resolve().parent
    / "definitions"
    / "wizard_joe_choreography_dictionary_v1.json"
)
_INTERRUPT_POLICY = {
    "immediate": "immediate",
    "phrase_boundary": "at_phase_boundary",
    "commit_then_recover": "after_hold",
}


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
    prepared_from_context_sha256: str
    compiled_from_context_sha256: str
    character_id: str
    package_digest: str
    media_id: str
    media_sha256: str
    choreography_dictionary_id: str
    choreography_policy_sha256: str

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
            "choreography_dictionary_id": self.choreography_dictionary_id,
            "choreography_policy_sha256": self.choreography_policy_sha256,
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


@dataclass(frozen=True)
class CompiledLiveSpeechScoreV1:
    """Unpublished deterministic score candidate and its two context bindings."""

    preliminary_context: PerformanceContextV1
    compiler_context_sha256: str
    score: CompiledPerformanceScore
    choreography_dictionary_id: str
    choreography_policy_sha256: str


def compile_live_speech_score(
    context: PerformanceContextV1,
    *,
    duration_ms: int,
    capability_manifest: Mapping[str, object],
    choreography_dictionary: Optional[
        CharacterChoreographyDictionaryV1
    ] = None,
) -> CompiledLiveSpeechScoreV1:
    """Compile an exact dictionary-bound speech score without repository mutation."""

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

    dictionary, speak_binding = _resolve_speak_binding(
        context,
        choreography_dictionary,
        duration_ms=duration_ms,
    )
    capability_id, clip_id = _resolve_speech_capability(
        speak_binding,
        capability_manifest,
    )
    policy_sha256 = _choreography_policy_sha256(dictionary)
    identity_payload = {
        "character_id": context.character.character_id,
        "choreography_dictionary_id": dictionary.dictionary_id,
        "choreography_policy_sha256": policy_sha256,
        "choreography_policy_version": _LIVE_SPEECH_CHOREOGRAPHY_POLICY_VERSION,
        "clip_id": clip_id,
        "context_sha256": context.context_sha256,
        "duration_ms": duration_ms,
        "media_id": context.source.media_id,
        "media_sha256": context.source.media_sha256,
        "package_digest": context.character.package_digest,
    }
    identity = sha256_ref(canonical_json_v1(identity_payload)).split(":", 1)[1]
    portable_score = _build_live_speech_score(
        context,
        duration_ms=duration_ms,
        identity=identity,
        dictionary=dictionary,
        speak_binding=speak_binding,
        capability_id=capability_id,
        clip_id=clip_id,
        policy_sha256=policy_sha256,
    )
    compiler_context = _bind_compiler_context(context, portable_score)
    try:
        compiled_mapping = compile_character_bound_performance(
            compiler_context,
            portable_score,
            capability_manifest,
        )
        score = CompiledScoreLoader().from_mapping(compiled_mapping)
    except PerformanceCompileError as exc:
        raise LiveSpeechScoreError(exc.code, "$.performance_context") from exc
    except ScoreValidationError as exc:
        raise LiveSpeechScoreError(exc.code, exc.path) from exc

    return CompiledLiveSpeechScoreV1(
        preliminary_context=context,
        compiler_context_sha256=compiler_context.context_sha256,
        score=score,
        choreography_dictionary_id=dictionary.dictionary_id,
        choreography_policy_sha256=policy_sha256,
    )


def _resolve_speak_binding(
    context: PerformanceContextV1,
    dictionary: Optional[CharacterChoreographyDictionaryV1],
    *,
    duration_ms: int,
) -> Tuple[CharacterChoreographyDictionaryV1, ChoreographyIntentBindingV1]:
    if dictionary is None:
        if context.character.character_id != "wizard-joe-v1":
            raise LiveSpeechScoreError(
                "live_score_choreography_dictionary_not_ready",
                "$.character.choreography_dictionary",
            )
        dictionary = load_character_choreography_dictionary(
            _WIZARD_JOE_DICTIONARY_PATH,
            character_id=context.character.character_id,
        )
    if not isinstance(dictionary, CharacterChoreographyDictionaryV1):
        raise LiveSpeechScoreError(
            "live_score_choreography_dictionary_invalid",
            "$.character.choreography_dictionary",
        )
    if dictionary.character_id != context.character.character_id:
        raise LiveSpeechScoreError(
            "live_score_choreography_character_mismatch",
            "$.character.choreography_dictionary.character_id",
        )
    if dictionary.instructions.speech_motion_policy == "unsupported":
        raise LiveSpeechScoreError(
            "live_score_speech_motion_unsupported",
            "$.character.choreography_dictionary.instructions.speech_motion_policy",
        )
    binding = dictionary.intent_bindings.get("speak")
    if binding is None:
        raise LiveSpeechScoreError(
            "live_score_speak_binding_missing",
            "$.character.choreography_dictionary.intent_bindings.speak",
        )
    if not binding.speech_compatible:
        raise LiveSpeechScoreError(
            "live_score_speak_binding_speech_incompatible",
            "$.character.choreography_dictionary.intent_bindings.speak.speech_compatible",
        )
    if duration_ms < binding.minimum_hold_ms:
        raise LiveSpeechScoreError(
            "live_score_duration_below_speak_minimum_hold",
            "$.media.duration_ms",
        )
    if not binding.clip_ids:
        raise LiveSpeechScoreError(
            "live_score_speak_clip_missing",
            "$.character.choreography_dictionary.intent_bindings.speak.clip_ids",
        )
    return dictionary, binding


def _resolve_speech_capability(
    binding: ChoreographyIntentBindingV1,
    capability_manifest: Mapping[str, object],
) -> Tuple[str, str]:
    clip_id = binding.clip_ids[0]
    capability_id = clip_id if clip_id.startswith("clip:") else "clip:" + clip_id
    raw_capabilities = capability_manifest.get("capabilities")
    if not isinstance(raw_capabilities, (list, tuple)):
        raise LiveSpeechScoreError(
            "live_score_capability_manifest_invalid",
            "$.capability_manifest.capabilities",
        )
    matching = [
        item
        for item in raw_capabilities
        if isinstance(item, Mapping) and item.get("capability_id") == capability_id
    ]
    if len(matching) != 1:
        raise LiveSpeechScoreError(
            "live_score_speak_capability_not_admitted",
            "$.capability_manifest.capabilities",
        )
    capability = matching[0]
    compatibility = capability.get("compatibility")
    if not isinstance(compatibility, Mapping):
        raise LiveSpeechScoreError(
            "live_score_speak_capability_compatibility_missing",
            "$.capability_manifest.capabilities.compatibility",
        )
    if compatibility.get("speech") != "compatible":
        raise LiveSpeechScoreError(
            "live_score_speak_capability_speech_incompatible",
            "$.capability_manifest.capabilities.compatibility.speech",
        )
    mapping = capability.get("mapping")
    mapped_clips = mapping.get("clip_ids") if isinstance(mapping, Mapping) else None
    canonical_clip_id = clip_id.split(":", 1)[1] if clip_id.startswith("clip:") else clip_id
    if not isinstance(mapped_clips, (list, tuple)) or canonical_clip_id not in mapped_clips:
        raise LiveSpeechScoreError(
            "live_score_speak_capability_mapping_mismatch",
            "$.capability_manifest.capabilities.mapping.clip_ids",
        )
    return capability_id, canonical_clip_id


def _choreography_policy_sha256(
    dictionary: CharacterChoreographyDictionaryV1,
) -> str:
    instructions = dictionary.instructions
    payload = {
        "policy_version": _LIVE_SPEECH_CHOREOGRAPHY_POLICY_VERSION,
        "dictionary": {
            "schema_version": dictionary.schema_version,
            "dictionary_id": dictionary.dictionary_id,
            "character_id": dictionary.character_id,
            "library_class": dictionary.library_class,
            "instructions": {
                "selection_unit": instructions.selection_unit,
                "transition_policy": instructions.transition_policy,
                "speech_motion_policy": instructions.speech_motion_policy,
                "locomotion_speech_policy": instructions.locomotion_speech_policy,
                "unsupported_intent_policy": instructions.unsupported_intent_policy,
                "repetition_window_ms": instructions.repetition_window_ms,
                "minimum_stillness_ms": instructions.minimum_stillness_ms,
                "maximum_gestures_per_phrase": instructions.maximum_gestures_per_phrase,
            },
            "intent_bindings": {
                intent_id: {
                    "roles": list(binding.roles),
                    "pose_ids": list(binding.pose_ids),
                    "action_ids": list(binding.action_ids),
                    "clip_ids": list(binding.clip_ids),
                    "speech_compatible": binding.speech_compatible,
                    "interrupt_policy": binding.interrupt_policy,
                    "minimum_hold_ms": binding.minimum_hold_ms,
                    "recovery_intent": binding.recovery_intent,
                }
                for intent_id, binding in sorted(dictionary.intent_bindings.items())
            },
        },
    }
    return sha256_ref(canonical_json_v1(payload))


def _build_live_speech_score(
    context: PerformanceContextV1,
    *,
    duration_ms: int,
    identity: str,
    dictionary: CharacterChoreographyDictionaryV1,
    speak_binding: ChoreographyIntentBindingV1,
    capability_id: str,
    clip_id: str,
    policy_sha256: str,
) -> Mapping[str, object]:
    report_sha256 = sha256_ref(
        canonical_json_v1(
            {
                "decision": "accepted",
                "dictionary_id": dictionary.dictionary_id,
                "intent": "speak",
                "capability_id": capability_id,
                "clip_id": clip_id,
                "speech_compatible": True,
                "minimum_hold_ms": speak_binding.minimum_hold_ms,
            }
        )
    )
    return {
        "schema_version": 1,
        "score_id": "performance:live-speech:" + identity[:24],
        "revision": 1,
        "status": "accepted",
        "mode": "directed",
        "media": {
            "media_id": context.source.media_id,
            "media_sha256": context.source.media_sha256,
            "duration_ms": duration_ms,
        },
        "analysis_ref": {
            "kind": "direction",
            "artifact_id": "direction:live-speech:" + identity[:24],
            "artifact_sha256": policy_sha256,
        },
        "tracks": [
            {
                "track_id": "live-speech-body",
                "kind": "body_base",
                "exclusive": True,
                "max_active": 1,
                "gap_policy": "characterful_neutral",
                "cues": [
                    {
                        "cue_id": "live-speech:" + identity[:24],
                        "start_ms": 0,
                        "end_ms": duration_ms,
                        "intent": "speak",
                        "source_ids": [dictionary.dictionary_id],
                        "priority": 60,
                        "amplitude_milli": 0,
                        "capability_requirements": [capability_id],
                        "fallback_intents": [capability_id],
                        "interrupt_policy": _INTERRUPT_POLICY[
                            speak_binding.interrupt_policy
                        ],
                        "cooldown_class": "live-speech-baseline",
                        "motif_id": None,
                        "confidence": {
                            "alignment_milli": 1000,
                            "evidence_milli": 1000,
                            "planner_milli": 1000,
                        },
                        "manual": {"locked": False, "disabled": False},
                    }
                ],
            }
        ],
        "provenance": {
            "pipeline_version": _LIVE_SPEECH_CHOREOGRAPHY_POLICY_VERSION,
            "prompt_bundle_sha256": None,
            "provider_run_sha256": None,
            "seed": int(identity[:13], 16),
            "parent_score_sha256": None,
            "edit_set_sha256": None,
        },
        "validation": {
            "policy_sha256": policy_sha256,
            "report_sha256": report_sha256,
            "decision": "accepted",
        },
    }


def _bind_compiler_context(
    context: PerformanceContextV1,
    score: Mapping[str, object],
) -> PerformanceContextV1:
    raw = context.content_dict()
    raw["evidence"]["score_binding"] = {  # type: ignore[index]
        "score_id": score["score_id"],
        "score_revision": score["revision"],
        "score_sha256": sha256_ref(canonical_json_v1(score)),
    }
    return PerformanceContextV1.build(raw)


def publish_live_speech_score(
    compiled: CompiledLiveSpeechScoreV1,
    *,
    repository: CompiledScoreRepository,
) -> PreparedLiveSpeechScoreV1:
    """Atomically publish a previously compiled and revalidated candidate."""

    if not isinstance(compiled, CompiledLiveSpeechScoreV1):
        raise TypeError("compiled must be a CompiledLiveSpeechScoreV1")
    try:
        publication = repository.publish(compiled.score)
    except ScoreValidationError as exc:
        raise LiveSpeechScoreError(exc.code, exc.path) from exc

    context = compiled.preliminary_context
    binding = LiveSpeechScoreBindingV1(
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
        choreography_dictionary_id=compiled.choreography_dictionary_id,
        choreography_policy_sha256=compiled.choreography_policy_sha256,
    )
    return PreparedLiveSpeechScoreV1(1, context, binding)


__all__ = [
    "CompiledLiveSpeechScoreV1",
    "LiveSpeechScoreBindingV1",
    "LiveSpeechScoreError",
    "PreparedLiveSpeechScoreV1",
    "compile_live_speech_score",
    "publish_live_speech_score",
]
