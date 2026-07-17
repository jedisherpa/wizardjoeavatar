from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, Tuple

from .character_capabilities import (
    CharacterCapabilityManifestValidationError,
    validate_character_capability_manifest,
)
from .performance_context import PerformanceContextV1
from .performance_scheduler import (
    REDUCED_PROHIBITED_CHANNELS,
    REDUCED_PROHIBITED_TRACKS,
    STILL_ALLOWED_CHANNELS,
    TRACK_DEFAULT_CHANNEL,
)
from .transcript_ingest import CaptionCue, TranscriptDocument


NARRATIVE_PIPELINE_VERSION = "deterministic-narrative-baseline-v1"
PERFORMANCE_ASSEMBLY_VERSION = "deterministic-performance-assembly-v1"
CHARACTER_BINDING_POLICY_VERSION = "deterministic-character-binding-v1"
COMPILED_RUNTIME_API_VERSION = 2

_PRIVATE_VALUE_PATTERNS = (
    re.compile(r"(?i)^bearer\\s"),
    re.compile(r"(?i)^basic\\s"),
    re.compile(r"(?i)^(?:sk|xox[baprs]|gh[opusr])[-_]"),
    re.compile(r"(?i)^-----BEGIN\\s"),
)


class PerformanceCompileError(ValueError):
    """A stable failure from the deterministic authoring compiler."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class NarrativeTimingSpan:
    block_id: str
    start_ms: int
    end_ms: int
    source: str = "supplied_caption"


@dataclass(frozen=True)
class BaselineCompilation:
    narrative_score: Mapping[str, object]
    performance_score: Mapping[str, object]


@dataclass(frozen=True)
class SpeechFallbackProfile:
    profile_id: str
    media_id: str
    media_sha256: str
    duration_ms: int
    cycle_offset_ms: int
    degraded_reason: str = "duration_only_speech"

    def to_mapping(self) -> Dict[str, object]:
        return {
            "schema_version": 1,
            "profile_id": self.profile_id,
            "media_id": self.media_id,
            "media_sha256": self.media_sha256,
            "duration_ms": self.duration_ms,
            "policy": "sparse-duration-only-speech-v1",
            "cycle_offset_ms": self.cycle_offset_ms,
            "body_intent": "characterful_neutral",
            "expression": "attentive",
            "gaze_target": "direct_viewer",
            "degraded_reason": self.degraded_reason,
        }


@dataclass(frozen=True)
class SpeechFallbackState:
    media_time_ms: int
    terminal: bool
    speaking: bool
    body_intent: str
    expression: str
    gaze_target: str
    mouth_shape: str
    face_energy_milli: int
    degraded_reason: str
    resolution_hash: str


@dataclass(frozen=True)
class PerformanceSourceSelection:
    source: str
    aligned_score: Optional[Mapping[str, object]]
    speech_fallback: Optional[SpeechFallbackProfile]
    degraded_reason: Optional[str]


@dataclass(frozen=True)
class _CapabilityResolution:
    capability: Optional[Mapping[str, object]]
    selected_intent: str
    path: Tuple[str, ...]
    reason_code: Optional[str] = None
    review_required: bool = False


def timing_spans_from_captions(
    cues: Sequence[CaptionCue],
) -> Tuple[NarrativeTimingSpan, ...]:
    return tuple(
        NarrativeTimingSpan(
            block_id=cue.block_id,
            start_ms=cue.start_ms,
            end_ms=cue.end_ms,
            source="supplied_caption",
        )
        for cue in cues
    )


def build_speech_fallback_profile(
    *,
    media_id: str,
    media_sha256: str,
    duration_ms: int,
) -> SpeechFallbackProfile:
    """Build a content-free fallback for generated TTS or other speech audio."""

    if not isinstance(media_id, str) or not media_id.startswith("media:sha256:"):
        raise PerformanceCompileError("media_id_invalid", "media_id is invalid")
    _require_sha256_ref("media_sha256", media_sha256)
    _require_positive_int("duration_ms", duration_ms)
    identity = {
        "policy": "sparse-duration-only-speech-v1",
        "media_id": media_id,
        "media_sha256": media_sha256,
        "duration_ms": duration_ms,
    }
    digest = _identity_hash(identity).split(":", 1)[1]
    return SpeechFallbackProfile(
        profile_id="speech-fallback:{}".format(digest[:24]),
        media_id=media_id,
        media_sha256=media_sha256,
        duration_ms=duration_ms,
        cycle_offset_ms=int(digest[:8], 16) % 900,
    )


def evaluate_speech_fallback(
    profile: SpeechFallbackProfile,
    media_time_ms: int,
) -> SpeechFallbackState:
    """Resolve fallback face/mouth state directly from authoritative media time."""

    _require_nonnegative_int("media_time_ms", media_time_ms)
    clamped_time = min(media_time_ms, profile.duration_ms)
    terminal = clamped_time >= profile.duration_ms
    if terminal:
        mouth_shape = "rest"
        speaking = False
        face_energy_milli = 0
    else:
        phase = (clamped_time + profile.cycle_offset_ms) % 900
        mouth_shape = _duration_only_mouth_shape(phase)
        speaking = True
        face_energy_milli = 160 if mouth_shape == "rest" else 220
    identity = {
        "profile_id": profile.profile_id,
        "media_time_ms": clamped_time,
        "terminal": terminal,
        "speaking": speaking,
        "body_intent": "characterful_neutral",
        "expression": "attentive",
        "gaze_target": "direct_viewer",
        "mouth_shape": mouth_shape,
        "face_energy_milli": face_energy_milli,
        "degraded_reason": profile.degraded_reason,
    }
    return SpeechFallbackState(
        media_time_ms=clamped_time,
        terminal=terminal,
        speaking=speaking,
        body_intent="characterful_neutral",
        expression="attentive",
        gaze_target="direct_viewer",
        mouth_shape=mouth_shape,
        face_energy_milli=face_energy_milli,
        degraded_reason=profile.degraded_reason,
        resolution_hash=_identity_hash(identity),
    )


def select_performance_source(
    aligned_score: Optional[Mapping[str, object]],
    *,
    media_id: str,
    media_sha256: str,
    duration_ms: int,
) -> PerformanceSourceSelection:
    """Prefer a matching accepted aligned score, otherwise choose explicit fallback."""

    if aligned_score is not None:
        status = aligned_score.get("status")
        media = aligned_score.get("media")
        if status != "accepted" or not isinstance(media, Mapping):
            raise PerformanceCompileError(
                "artifact_not_accepted", "aligned performance score is not accepted"
            )
        if (
            media.get("media_id") != media_id
            or media.get("media_sha256") != media_sha256
            or media.get("duration_ms") != duration_ms
        ):
            raise PerformanceCompileError(
                "score_mismatch", "aligned performance score does not match media"
            )
        return PerformanceSourceSelection(
            source="aligned_score",
            aligned_score=aligned_score,
            speech_fallback=None,
            degraded_reason=None,
        )
    fallback = build_speech_fallback_profile(
        media_id=media_id,
        media_sha256=media_sha256,
        duration_ms=duration_ms,
    )
    return PerformanceSourceSelection(
        source="speech_fallback",
        aligned_score=None,
        speech_fallback=fallback,
        degraded_reason=fallback.degraded_reason,
    )


def compile_narrative_baseline(
    transcript: TranscriptDocument,
    *,
    duration_ms: int,
    alignment_id: str,
    timing_spans: Sequence[NarrativeTimingSpan] = (),
) -> Dict[str, object]:
    """Build sparse, content-free narrative direction without a model call."""

    _require_positive_int("duration_ms", duration_ms)
    if not isinstance(alignment_id, str) or not alignment_id.startswith("alignment:"):
        raise PerformanceCompileError(
            "alignment_id_invalid", "alignment_id must use the alignment namespace"
        )
    if not transcript.blocks:
        raise PerformanceCompileError("transcript_empty", "transcript has no blocks")
    spans, timing_source = _resolve_spans(transcript, duration_ms, timing_spans)
    chapter_by_block = {
        block_id: chapter.chapter_id
        for chapter in transcript.chapters
        for block_id in chapter.block_ids
    }
    blocks_by_id = {block.block_id: block for block in transcript.blocks}
    chapter_counts = {
        chapter.chapter_id: len(chapter.block_ids) for chapter in transcript.chapters
    }
    chapter_seen = {chapter.chapter_id: 0 for chapter in transcript.chapters}
    beats = []  # type: list[Dict[str, object]]
    for index, span in enumerate(spans):
        block = blocks_by_id[span.block_id]
        chapter_id = chapter_by_block[span.block_id]
        chapter_index = chapter_seen[chapter_id]
        chapter_seen[chapter_id] += 1
        chapter_count = chapter_counts[chapter_id]
        performer_mode = _performer_mode(block.display_text)
        beat_function = _beat_function(
            block.display_text,
            chapter_index=chapter_index,
            chapter_count=chapter_count,
        )
        word_count = len(block.spoken_normalized_text.split())
        span_duration = span.end_ms - span.start_ms
        density_milli = min(1000, (word_count * 60_000) // max(span_duration, 1))
        chapter_phase = _chapter_phase(chapter_index, chapter_count)
        gesture_intent = _safe_gesture_intent(beat_function, density_milli)
        beats.append(
            {
                "beat_id": "beat-{:04d}".format(index + 1),
                "chapter_id": chapter_id,
                "scene_id": "{}.scene-001".format(chapter_id),
                "source_span_ids": [span.block_id],
                "start_ms": span.start_ms,
                "apex_ms": span.start_ms + span_duration // 2,
                "end_ms": span.end_ms,
                "performer_mode": performer_mode,
                "beat_function": beat_function,
                "chapter_phase": chapter_phase,
                "tension_milli": 250,
                "valence_milli": 0,
                "activation_milli": 260 if beat_function == "question" else 220,
                "intimacy_milli": 300,
                "information_density_milli": density_milli,
                "stillness_target": "held" if density_milli >= 650 else "settled",
                "gesture_intent": gesture_intent,
                "visual_salience": "low" if gesture_intent != "none" else "none",
                "spoiler_sensitive": beat_function in {"reveal", "reverse"},
                "confidence_milli": 800 if timing_source != "fallback" else 300,
                "review_status": "accepted",
            }
        )

    chapter_envelopes = []  # type: list[Dict[str, object]]
    for chapter in transcript.chapters:
        chapter_spans = [
            span for span in spans if span.block_id in set(chapter.block_ids)
        ]
        chapter_envelopes.append(
            {
                "chapter_id": chapter.chapter_id,
                "start_ms": min(span.start_ms for span in chapter_spans),
                "end_ms": max(span.end_ms for span in chapter_spans),
                "entry_energy_milli": 250,
                "apex_energy_milli": 350,
                "exit_energy_milli": 250,
            }
        )

    pipeline_identity = {
        "pipeline_version": NARRATIVE_PIPELINE_VERSION,
        "transcript_id": transcript.transcript_id,
        "transcript_revision": transcript.revision,
        "alignment_id": alignment_id,
        "duration_ms": duration_ms,
        "timing_source": timing_source,
        "spans": [
            {
                "block_id": span.block_id,
                "start_ms": span.start_ms,
                "end_ms": span.end_ms,
                "source": span.source,
            }
            for span in spans
        ],
    }
    body = {
        "schema_version": 1,
        "media_id": transcript.media_id,
        "transcript_id": transcript.transcript_id,
        "alignment_id": alignment_id,
        "duration_ms": duration_ms,
        "book_profile": {
            "genre_family": "unknown",
            "narration_form": "mixed",
            "pov_system": "unknown",
            "narrator_role": "storyteller",
            "baseline_distance": "middle",
            "baseline_energy_milli": 300,
            "performance_ceiling_milli": 600,
        },
        "chapter_envelopes": chapter_envelopes,
        "beats": beats,
        "provenance": {
            "pipeline_hash": _identity_hash(pipeline_identity),
            "validation_hash": _identity_hash(
                {
                    "validator": "content-free-narrative-validator-v1",
                    "beat_count": len(beats),
                    "timing_source": timing_source,
                }
            ),
        },
    }
    body["narrative_score_id"] = "narrative:{}".format(
        _identity_hash(body).split(":", 1)[1][:24]
    )
    return _ordered_narrative_score(body)


def assemble_performance_score(
    narrative_score: Mapping[str, object],
    *,
    media_sha256: str,
    seed: int = 0,
) -> Dict[str, object]:
    """Assemble a portable neutral-first score; no character IDs are selected."""

    _require_sha256_ref("media_sha256", media_sha256)
    _require_nonnegative_int("seed", seed)
    duration_ms = narrative_score.get("duration_ms")
    _require_positive_int("duration_ms", duration_ms)
    media_id = narrative_score.get("media_id")
    narrative_score_id = narrative_score.get("narrative_score_id")
    beats = narrative_score.get("beats")
    if not isinstance(media_id, str) or not media_id.startswith("media:sha256:"):
        raise PerformanceCompileError("media_id_invalid", "narrative media_id is invalid")
    if not isinstance(narrative_score_id, str) or not narrative_score_id.startswith(
        "narrative:"
    ):
        raise PerformanceCompileError(
            "narrative_score_id_invalid", "narrative score identity is invalid"
        )
    if not isinstance(beats, list):
        raise PerformanceCompileError("beats_invalid", "narrative beats must be an array")

    narrative_cues = []  # type: list[Dict[str, object]]
    for beat in beats:
        if not isinstance(beat, Mapping):
            raise PerformanceCompileError("beat_invalid", "narrative beat must be an object")
        beat_id = beat.get("beat_id")
        start_ms = beat.get("start_ms")
        end_ms = beat.get("end_ms")
        performer_mode = beat.get("performer_mode")
        beat_function = beat.get("beat_function")
        if not all(isinstance(value, str) for value in (beat_id, performer_mode, beat_function)):
            raise PerformanceCompileError("beat_invalid", "narrative beat fields are invalid")
        _require_range(start_ms, end_ms, duration_ms)
        narrative_cues.append(
            {
                "cue_id": "{}.narrative".format(beat_id),
                "start_ms": start_ms,
                "end_ms": end_ms,
                "intent": "narrative.{}.{}".format(performer_mode, beat_function),
                "source_ids": [beat_id],
                "priority": 10,
                "amplitude_milli": 0,
                "capability_requirements": [],
                "fallback_intents": ["still"],
                "interrupt_policy": "immediate",
                "cooldown_class": "narrative_state",
                "motif_id": None,
                "confidence": {
                    "alignment_milli": beat.get("confidence_milli", 0),
                    "evidence_milli": beat.get("confidence_milli", 0),
                    "planner_milli": 1000,
                },
                "manual": {"locked": False, "disabled": False},
            }
        )

    body_cue = {
        "cue_id": "baseline.body.characterful-neutral",
        "start_ms": 0,
        "end_ms": duration_ms,
        "intent": "characterful_neutral",
        "source_ids": [],
        "priority": 20,
        "amplitude_milli": 250,
        "capability_requirements": ["body.characterful_neutral"],
        "fallback_intents": ["still"],
        "interrupt_policy": "at_phase_boundary",
        "cooldown_class": "baseline",
        "motif_id": None,
        "confidence": {
            "alignment_milli": 1000,
            "evidence_milli": 1000,
            "planner_milli": 1000,
        },
        "manual": {"locked": False, "disabled": False},
    }
    analysis_hash = _identity_hash(narrative_score)
    body = {
        "schema_version": 1,
        "revision": 1,
        "status": "accepted",
        "mode": "audiobook",
        "media": {
            "media_id": media_id,
            "media_sha256": media_sha256,
            "duration_ms": duration_ms,
        },
        "analysis_ref": {
            "kind": "narrative",
            "artifact_id": narrative_score_id,
            "artifact_sha256": analysis_hash,
        },
        "tracks": [
            {
                "track_id": "narrative-state",
                "kind": "narrative_state",
                "exclusive": True,
                "max_active": 1,
                "gap_policy": "hold",
                "cues": narrative_cues,
            },
            {
                "track_id": "body-base",
                "kind": "body_base",
                "exclusive": True,
                "max_active": 1,
                "gap_policy": "characterful_neutral",
                "cues": [body_cue],
            },
        ],
        "provenance": {
            "pipeline_version": PERFORMANCE_ASSEMBLY_VERSION,
            "prompt_bundle_sha256": None,
            "provider_run_sha256": None,
            "seed": seed,
            "parent_score_sha256": None,
            "edit_set_sha256": None,
        },
        "validation": {
            "policy_sha256": _identity_hash(
                {
                    "policy": PERFORMANCE_ASSEMBLY_VERSION,
                    "neutral_first": True,
                    "model_calls": False,
                }
            ),
            "report_sha256": _identity_hash(
                {
                    "decision": "accepted",
                    "narrative_cue_count": len(narrative_cues),
                    "body_cue_count": 1,
                }
            ),
            "decision": "accepted",
        },
    }
    body["score_id"] = "performance:{}".format(
        _identity_hash(body).split(":", 1)[1][:24]
    )
    return _ordered_performance_score(body)


def compile_baseline_performance(
    transcript: TranscriptDocument,
    *,
    duration_ms: int,
    alignment_id: str,
    media_sha256: str,
    timing_spans: Sequence[NarrativeTimingSpan] = (),
    seed: int = 0,
) -> BaselineCompilation:
    narrative = compile_narrative_baseline(
        transcript,
        duration_ms=duration_ms,
        alignment_id=alignment_id,
        timing_spans=timing_spans,
    )
    performance = assemble_performance_score(
        narrative,
        media_sha256=media_sha256,
        seed=seed,
    )
    return BaselineCompilation(
        narrative_score=narrative,
        performance_score=performance,
    )


def compile_character_bound_performance(
    context: PerformanceContextV1,
    performance_score: Mapping[str, object],
    capability_manifest: Mapping[str, object],
) -> Dict[str, object]:
    """Bind a portable score to one validated character without runtime guessing."""

    if not isinstance(context, PerformanceContextV1):
        raise PerformanceCompileError("context_invalid", "context must be PerformanceContextV1")
    if not isinstance(performance_score, Mapping):
        raise PerformanceCompileError("score_invalid", "performance score must be an object")
    if not isinstance(capability_manifest, Mapping):
        raise PerformanceCompileError("manifest_invalid", "capability manifest must be an object")

    _reject_private_values(performance_score)
    _reject_private_values(capability_manifest)

    from .schema_validation import SchemaRegistry

    registry = SchemaRegistry()
    try:
        registry.validate("PerformanceScoreV1", performance_score)
        validate_character_capability_manifest(capability_manifest)
    except CharacterCapabilityManifestValidationError as exc:
        raise PerformanceCompileError(exc.code, "character capability manifest is invalid") from exc
    except ValueError as exc:
        raise PerformanceCompileError(
            getattr(exc, "code", "score_invalid"),
            "portable performance score is invalid",
        ) from exc

    if performance_score.get("status") != "accepted":
        raise PerformanceCompileError("artifact_not_accepted", "performance score is not accepted")

    score_sha256 = _identity_hash(performance_score)
    _validate_character_binding(context, performance_score, capability_manifest, score_sha256)

    media = _mapping_value(performance_score.get("media"), "score media")
    manifest_character = _mapping_value(capability_manifest.get("character"), "manifest character")
    sources = _mapping_value(capability_manifest.get("sources"), "manifest sources")
    manifest_sha256 = _string_value(capability_manifest.get("manifest_sha256"), "manifest SHA-256")
    mapping_policy_identity = {
        "policy_version": CHARACTER_BINDING_POLICY_VERSION,
        "context_sha256": context.context_sha256,
        "wizard_runtime_epoch": context.runtime.wizard_runtime_epoch,
        "reconciliation_generation": context.runtime.reconciliation_generation,
        "connector_session_id": context.source.connector_session_id,
        "accepted_sequence": context.source.accepted_sequence,
        "media_epoch": context.source.media_epoch,
        "source_epoch": context.source.source_epoch,
        "turn_id": context.source.turn_id,
        "performance_score_id": performance_score["score_id"],
        "performance_score_revision": performance_score["revision"],
        "performance_score_sha256": score_sha256,
        "media_id": media["media_id"],
        "media_sha256": media["media_sha256"],
        "media_duration_ms": media["duration_ms"],
        "character_id": manifest_character["character_id"],
        "package_sha256": sources["package_sha256"],
        "manifest_sha256": manifest_sha256,
        "pose_library_sha256": sources["pose_library_sha256"],
        "animation_graph_sha256": sources["animation_graph_sha256"],
        "motion_profile": context.preferences.motion_profile,
        "disabled_channels": list(context.preferences.disabled_channels),
        "model_calls": False,
        "live_io": False,
    }
    mapping_policy_sha256 = _identity_hash(mapping_policy_identity)

    capabilities = tuple(
        _mapping_value(item, "manifest capability")
        for item in _sequence_value(capability_manifest.get("capabilities"), "manifest capabilities")
    )
    poses = tuple(
        _mapping_value(item, "manifest pose")
        for item in _sequence_value(capability_manifest.get("poses"), "manifest poses")
    )
    capabilities_by_id = {
        _string_value(item.get("capability_id"), "capability ID"): item
        for item in capabilities
    }
    poses_by_id = {
        _string_value(item.get("pose_id"), "pose ID"): item
        for item in poses
    }

    compiled_tracks = []  # type: list[Dict[str, object]]
    fallback_records = []  # type: list[Dict[str, object]]
    for track_value in _sequence_value(performance_score.get("tracks"), "score tracks"):
        track = _mapping_value(track_value, "score track")
        track_kind = _string_value(track.get("kind"), "track kind")
        compiled_cues = []  # type: list[Dict[str, object]]
        for cue_value in _sequence_value(track.get("cues"), "score cues"):
            cue = _mapping_value(cue_value, "score cue")
            resolution = _resolve_capability(
                cue,
                capability_manifest,
                capabilities_by_id,
                poses_by_id,
            )
            if resolution.capability is None:
                fallback_records.append(
                    _fallback_record(
                        cue,
                        resolution.selected_intent,
                        None,
                        resolution.path,
                        resolution.reason_code or "clear_fallback",
                        context.character.package_digest,
                        resolution.review_required,
                    )
                )
                continue
            resolution = _apply_accessibility_fallback(
                resolution,
                context.preferences.motion_profile,
                capabilities_by_id,
            )
            projected_channels, projection_reasons = _project_capability_channels(
                resolution.capability,
                track_kind,
                context.preferences.motion_profile,
                context.preferences.disabled_channels,
            )

            if resolution.reason_code is not None:
                fallback_records.append(
                    _fallback_record(
                        cue,
                        resolution.selected_intent,
                        resolution.capability,
                        resolution.path,
                        resolution.reason_code,
                        context.character.package_digest,
                        resolution.review_required,
                    )
                )
            for reason_code in projection_reasons:
                fallback_records.append(
                    _fallback_record(
                        cue,
                        resolution.selected_intent,
                        resolution.capability,
                        _unique_path(resolution.path + ("projection:" + context.preferences.motion_profile,)),
                        reason_code,
                        context.character.package_digest,
                        False,
                    )
                )

            if not projected_channels:
                fallback_records.append(
                    _fallback_record(
                        cue,
                        "clear",
                        None,
                        _unique_path(resolution.path + ("clear",)),
                        "motion_profile_suppressed",
                        context.character.package_digest,
                        False,
                    )
                )
                continue

            compiled_cues.append(
                _compile_bound_cue(
                    cue,
                    resolution,
                    projected_channels,
                    mapping_policy_sha256,
                    context,
                )
            )

        compiled_tracks.append(
            {
                "track_id": track["track_id"],
                "kind": track_kind,
                "exclusive": track["exclusive"],
                "max_active": track["max_active"],
                "gap_policy": track["gap_policy"],
                "cues": compiled_cues,
            }
        )

    fallback_records.sort(
        key=lambda item: (
            int(item["media_time_ms"]),
            str(item["cue_id"]),
            str(item["reason_code"]),
            str(item["selected_mapping_id"]),
        )
    )
    checkpoints = [_time_zero_checkpoint(compiled_tracks)]
    report_sha256 = _identity_hash(
        {
            "policy_sha256": mapping_policy_sha256,
            "context_sha256": context.context_sha256,
            "manifest_sha256": manifest_sha256,
            "package_sha256": context.character.package_digest,
            "media_sha256": media["media_sha256"],
            "performance_score_sha256": score_sha256,
            "reconciliation_generation": context.runtime.reconciliation_generation,
            "cue_resolution_hashes": [
                cue["resolution_hash"]
                for track in compiled_tracks
                for cue in track["cues"]  # type: ignore[index]
            ],
            "fallback_records": fallback_records,
        }
    )
    body = {
        "schema_version": 1,
        "performance_score_sha256": score_sha256,
        "media": copy.deepcopy(media),
        "character": {
            "character_id": manifest_character["character_id"],
            "package_version": "{}.0.0".format(capability_manifest["schema_version"]),
            "package_digest": sources["package_sha256"],
            "pose_library_digest": sources["pose_library_sha256"],
            "graph_digest": sources["animation_graph_sha256"],
        },
        "mapping_policy_sha256": mapping_policy_sha256,
        "runtime_api_version": COMPILED_RUNTIME_API_VERSION,
        "tracks": compiled_tracks,
        "checkpoints": checkpoints,
        "fallback_records": fallback_records,
        "validation": {"decision": "accepted", "report_sha256": report_sha256},
    }
    body["compiled_score_id"] = "compiled:{}".format(
        _identity_hash(body).split(":", 1)[1][:24]
    )
    ordered = {
        "schema_version": body["schema_version"],
        "compiled_score_id": body["compiled_score_id"],
        "performance_score_sha256": body["performance_score_sha256"],
        "media": body["media"],
        "character": body["character"],
        "mapping_policy_sha256": body["mapping_policy_sha256"],
        "runtime_api_version": body["runtime_api_version"],
        "tracks": body["tracks"],
        "checkpoints": body["checkpoints"],
        "fallback_records": body["fallback_records"],
        "validation": body["validation"],
    }
    try:
        registry.validate("CompiledPerformanceScoreV1", ordered)
    except ValueError as exc:
        raise PerformanceCompileError(
            getattr(exc, "code", "compiled_score_invalid"),
            "compiled performance score is invalid",
        ) from exc
    return ordered


compile_character_bound_score = compile_character_bound_performance


def _validate_character_binding(
    context: PerformanceContextV1,
    score: Mapping[str, object],
    manifest: Mapping[str, object],
    score_sha256: str,
) -> None:
    character = _mapping_value(manifest.get("character"), "manifest character")
    sources = _mapping_value(manifest.get("sources"), "manifest sources")
    expected = {
        "character_id": character.get("character_id"),
        "package_digest": sources.get("package_sha256"),
        "manifest_digest": manifest.get("manifest_sha256"),
    }
    actual = {
        "character_id": context.character.character_id,
        "package_digest": context.character.package_digest,
        "manifest_digest": context.character.manifest_digest,
    }
    for field in ("character_id", "package_digest", "manifest_digest"):
        if actual[field] != expected[field]:
            raise PerformanceCompileError(
                "stale_binding",
                "performance context does not match the selected character manifest",
            )

    binding = context.evidence.score_binding
    if binding.score_id is None:
        raise PerformanceCompileError("score_binding_missing", "context has no portable score binding")
    if (
        binding.score_id != score.get("score_id")
        or binding.score_revision != score.get("revision")
        or binding.score_sha256 != score_sha256
    ):
        raise PerformanceCompileError("stale_binding", "context score binding does not match input score")


def _resolve_capability(
    cue: Mapping[str, object],
    manifest: Mapping[str, object],
    capabilities_by_id: Mapping[str, Mapping[str, object]],
    poses_by_id: Mapping[str, Mapping[str, object]],
) -> _CapabilityResolution:
    intent = _string_value(cue.get("intent"), "cue intent")
    _reject_renderer_intent(intent, capabilities_by_id, poses_by_id)
    requirements = tuple(
        _string_value(item, "capability requirement")
        for item in _sequence_value(cue.get("capability_requirements"), "capability requirements")
    )
    fallbacks = tuple(
        _string_value(item, "fallback intent")
        for item in _sequence_value(cue.get("fallback_intents"), "fallback intents")
    )
    attempted = []  # type: list[str]
    terminal_reason = "characterful_neutral_fallback"
    requests = requirements + (intent,) + fallbacks
    for request_index, requested in enumerate(requests):
        if requested not in attempted:
            attempted.append(requested)
        direct = capabilities_by_id.get(requested)
        if direct is not None:
            if direct.get("admission") == "unsupported":
                declared = _declared_fallback_resolution(
                    direct,
                    requested,
                    tuple(attempted),
                    capabilities_by_id,
                )
                if declared is not None:
                    return declared
                terminal_reason = "declared_fallback_unavailable"
                continue
            return _CapabilityResolution(
                direct,
                intent,
                _unique_path(tuple(attempted) + (requested,)),
                None if request_index == 0 else "semantic_fallback",
            )

        pose_id = requested.removeprefix("pose:")
        pose = poses_by_id.get(pose_id)
        if pose is not None:
            if pose.get("admission") != "graph_admitted":
                raise PerformanceCompileError(
                    "pose_not_admitted",
                    "diagnostic-only pose cannot be selected by the compiler",
                )
            pose_capabilities = sorted(
                (
                    capability
                    for capability in capabilities_by_id.values()
                    if capability.get("admission") != "unsupported"
                    and pose_id in _mapping_sequence(capability, "mapping", "pose_ids")
                ),
                key=lambda item: str(item.get("capability_id")),
            )
            if not pose_capabilities:
                raise PerformanceCompileError(
                    "pose_capability_unknown",
                    "admitted pose has no admitted capability mapping",
                )
            capability = pose_capabilities[0]
            capability_id = _string_value(capability.get("capability_id"), "capability ID")
            return _CapabilityResolution(
                capability,
                intent,
                _unique_path(tuple(attempted) + (capability_id,)),
                None if request_index == 0 else "semantic_fallback",
            )

        if requested.startswith(("clip:", "expression:", "mouth:", "ownership:", "unsupported:")):
            raise PerformanceCompileError("capability_unknown", "requested capability ID is absent")

        matches = _semantic_capability_matches(requested, manifest, capabilities_by_id)
        if matches:
            capability = matches[0]
            capability_id = _string_value(capability.get("capability_id"), "capability ID")
            return _CapabilityResolution(
                capability,
                intent,
                _unique_path(tuple(attempted) + (capability_id,)),
                None if request_index == 0 else "semantic_fallback",
            )

    neutral = _neutral_capability(manifest, capabilities_by_id)
    if neutral is None:
        return _CapabilityResolution(
            None,
            "clear",
            _unique_path(tuple(attempted) + ("clear",)),
            "clear_fallback",
            True,
        )
    neutral_id = _string_value(neutral.get("capability_id"), "neutral capability ID")
    return _CapabilityResolution(
        neutral,
        "characterful_neutral",
        _unique_path(tuple(attempted) + (neutral_id,)),
        terminal_reason,
        True,
    )


def _declared_fallback_resolution(
    capability: Mapping[str, object],
    requested: str,
    attempted: Tuple[str, ...],
    capabilities_by_id: Mapping[str, Mapping[str, object]],
) -> Optional[_CapabilityResolution]:
    fallback = _mapping_value(capability.get("fallback"), "capability fallback")
    fallback_id = fallback.get("capability_id")
    selected = capabilities_by_id.get(str(fallback_id)) if fallback_id is not None else None
    if selected is None or selected.get("admission") == "unsupported":
        return None
    selected_id = _string_value(selected.get("capability_id"), "fallback capability ID")
    selected_intent = fallback.get("intent")
    return _CapabilityResolution(
        selected,
        str(selected_intent) if isinstance(selected_intent, str) else "characterful_neutral",
        _unique_path(attempted + (requested, selected_id)),
        str(fallback.get("reason_code") or "capability_not_admitted"),
        True,
    )


def _semantic_capability_matches(
    requested: str,
    manifest: Mapping[str, object],
    capabilities_by_id: Mapping[str, Mapping[str, object]],
) -> Tuple[Mapping[str, object], ...]:
    variants = _semantic_variants(requested)
    if "characterful_neutral" in variants or "still" in variants or "clear" in variants:
        neutral = _neutral_capability(manifest, capabilities_by_id)
        return () if neutral is None else (neutral,)
    matches = []  # type: list[Mapping[str, object]]
    for capability in capabilities_by_id.values():
        if capability.get("admission") == "unsupported":
            continue
        mapping = _mapping_value(capability.get("mapping"), "capability mapping")
        searchable = {
            str(capability.get("semantic_meaning", "")),
            str(capability.get("capability_id", "")).split(":", 1)[-1],
        }
        for field in (
            "action_ids",
            "expression_ids",
            "mouth_ids",
            "gaze_ids",
            "locomotion_ids",
            "flight_ids",
            "effect_ids",
            "prop_ids",
        ):
            searchable.update(str(item) for item in _sequence_value(mapping.get(field), field))
        if variants.intersection(searchable):
            matches.append(capability)
    return tuple(sorted(matches, key=lambda item: str(item.get("capability_id"))))


def _semantic_variants(value: str) -> frozenset[str]:
    leaf = value.rsplit(".", 1)[-1].rsplit(":", 1)[-1]
    variants = {value, leaf}
    aliases = {
        "explain": ("explaining", "speech"),
        "explain_light": ("explain", "explaining", "speech"),
        "explain_broad": ("explain", "explaining", "speech"),
        "speak": ("speaking", "speech"),
        "greet": ("greeting",),
        "celebration": ("celebrate",),
        "celebrate_grounded": ("celebrate_front",),
        "stage_walk": ("walk_front",),
        "viewer_turn": ("turn_views",),
        "settle_grounded": ("idle_front",),
        "point": ("point_front",),
    }
    variants.update(aliases.get(leaf, ()))
    return frozenset(variants)


def _neutral_capability(
    manifest: Mapping[str, object],
    capabilities_by_id: Mapping[str, Mapping[str, object]],
) -> Optional[Mapping[str, object]]:
    character = _mapping_value(manifest.get("character"), "manifest character")
    default_pose = character.get("default_pose_id")
    candidates = sorted(
        (
            capability
            for capability in capabilities_by_id.values()
            if capability.get("admission") != "unsupported"
            and default_pose in _mapping_sequence(capability, "mapping", "pose_ids")
        ),
        key=lambda item: str(item.get("capability_id")),
    )
    if candidates:
        return candidates[0]
    for capability_id in ("clip:idle_front", "expression:neutral", "mouth:closed"):
        capability = capabilities_by_id.get(capability_id)
        if capability is not None and capability.get("admission") != "unsupported":
            return capability
    return None


def _apply_accessibility_fallback(
    resolution: _CapabilityResolution,
    motion_profile: str,
    capabilities_by_id: Mapping[str, Mapping[str, object]],
) -> _CapabilityResolution:
    accessibility = _mapping_value(resolution.capability.get("accessibility"), "capability accessibility")
    behavior = accessibility.get(motion_profile)
    if behavior in {"admitted", "admitted_by_scheduler_projection"}:
        return resolution
    if behavior in {"fallback_characterful_neutral", "unsupported"}:
        fallback = _mapping_value(resolution.capability.get("fallback"), "capability fallback")
        fallback_id = fallback.get("capability_id")
        selected = capabilities_by_id.get(str(fallback_id)) if fallback_id is not None else None
        if selected is None or selected.get("admission") == "unsupported":
            raise PerformanceCompileError(
                "motion_profile_unsupported",
                "capability has no admitted accessibility fallback",
            )
        selected_id = _string_value(selected.get("capability_id"), "fallback capability ID")
        return _CapabilityResolution(
            selected,
            str(fallback.get("intent") or "characterful_neutral"),
            _unique_path(resolution.path + (selected_id,)),
            "motion_profile_fallback",
            resolution.review_required,
        )
    raise PerformanceCompileError(
        "motion_profile_unsupported",
        "capability declares an unknown accessibility behavior",
    )


def _project_capability_channels(
    capability: Mapping[str, object],
    track_kind: str,
    motion_profile: str,
    disabled_channels: Sequence[str],
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    mapping = _mapping_value(capability.get("mapping"), "capability mapping")
    channels = tuple(sorted(str(item) for item in _sequence_value(mapping.get("channels"), "mapping channels")))
    locomotion_ids = _sequence_value(mapping.get("locomotion_ids"), "mapping locomotion IDs")
    if track_kind in {"stage", "locomotion"} and locomotion_ids:
        channels = tuple(sorted(set(channels) | {TRACK_DEFAULT_CHANNEL[track_kind]}))
    disabled = set(disabled_channels)
    if "body_base" in disabled:
        disabled.add("body")
    if "body" in disabled:
        disabled.add("body_base")
    projected = tuple(channel for channel in channels if channel not in disabled)
    reasons = []  # type: list[str]
    if len(projected) != len(channels):
        reasons.append("channel_disabled")
    before_motion = projected
    if motion_profile == "reduced":
        projected = tuple(channel for channel in projected if channel not in REDUCED_PROHIBITED_CHANNELS)
        if track_kind in REDUCED_PROHIBITED_TRACKS:
            projected = ()
    elif motion_profile == "still":
        projected = tuple(channel for channel in projected if channel in STILL_ALLOWED_CHANNELS)
    if projected != before_motion:
        reasons.append("motion_profile_projection")
    return projected, tuple(reasons)


def _compile_bound_cue(
    cue: Mapping[str, object],
    resolution: _CapabilityResolution,
    projected_channels: Sequence[str],
    mapping_policy_sha256: str,
    context: PerformanceContextV1,
) -> Dict[str, object]:
    compiled = {
        key: copy.deepcopy(cue[key])
        for key in (
            "cue_id",
            "start_ms",
            "end_ms",
            "intent",
            "source_ids",
            "priority",
            "amplitude_milli",
            "capability_requirements",
            "fallback_intents",
            "interrupt_policy",
            "cooldown_class",
            "motif_id",
            "confidence",
            "manual",
        )
    }
    if cue.get("phase_ranges"):
        compiled["phase_ranges"] = copy.deepcopy(cue["phase_ranges"])
    if cue.get("execution"):
        compiled["execution"] = copy.deepcopy(cue["execution"])
    capability = resolution.capability
    capability_id = _string_value(capability.get("capability_id"), "capability ID")
    mapping = _mapping_value(capability.get("mapping"), "capability mapping")
    clip_ids = _sequence_value(mapping.get("clip_ids"), "mapping clip IDs")
    node_ids = _sequence_value(mapping.get("node_ids"), "mapping node IDs")
    pose_ids = _sequence_value(mapping.get("pose_ids"), "mapping pose IDs")
    timing = _mapping_value(capability.get("timing"), "capability timing")
    transitions = _mapping_value(capability.get("transitions"), "capability transitions")
    budget = _mapping_value(capability.get("budget"), "capability budget")
    compiled.update(
        {
            "mapping_id": capability_id,
            "clip_id": str(clip_ids[0]) if clip_ids else None,
            "node_id": str(node_ids[0]) if node_ids else None,
            "phase_marker_map": _phase_marker_map(transitions),
            "owned_channels": sorted(set(projected_channels)),
            "resolved_fallback_path": list(_unique_path(resolution.path)),
            "preload_asset_ids": (
                sorted({str(item) for item in tuple(clip_ids) + tuple(pose_ids)})
                if budget.get("preload_required") is True
                else []
            ),
        }
    )
    compiled["resolution_hash"] = _identity_hash(
        {
            "cue": compiled,
            "mapping_policy_sha256": mapping_policy_sha256,
            "context_sha256": context.context_sha256,
            "reconciliation_generation": context.runtime.reconciliation_generation,
            "capability_timing": timing,
            "capability_transitions": transitions,
        }
    )
    return compiled


def _phase_marker_map(transitions: Mapping[str, object]) -> Dict[str, Optional[str]]:
    entry = _sequence_value(transitions.get("entry_markers"), "entry markers")
    commit = _sequence_value(transitions.get("commit_markers"), "commit markers")
    recovery = _sequence_value(transitions.get("recovery_markers"), "recovery markers")
    exit_markers = _sequence_value(transitions.get("exit_markers"), "exit markers")
    return {
        "anticipation": str(entry[0]) if entry else None,
        "stroke": str(commit[0]) if commit else None,
        "hold": None,
        "release": str(recovery[0]) if recovery else (str(exit_markers[0]) if exit_markers else None),
        "settle": str(exit_markers[0]) if exit_markers else None,
    }


def _fallback_record(
    cue: Mapping[str, object],
    selected_intent: str,
    capability: Optional[Mapping[str, object]],
    path: Sequence[str],
    reason_code: str,
    package_digest: str,
    review_required: bool,
) -> Dict[str, object]:
    capability_id = (
        _string_value(capability.get("capability_id"), "capability ID")
        if capability is not None
        else None
    )
    identity = {
        "cue_id": cue["cue_id"],
        "requested_intent": cue["intent"],
        "selected_intent": selected_intent,
        "selected_mapping_id": capability_id,
        "fallback_path": list(_unique_path(tuple(str(item) for item in path))),
        "reason_code": reason_code,
        "package_digest": package_digest,
        "media_time_ms": cue["start_ms"],
        "severity": "warning" if review_required else "info",
        "review_required": review_required,
    }
    return {
        "fallback_id": "fallback:{}".format(_identity_hash(identity).split(":", 1)[1][:24]),
        **identity,
    }


def _time_zero_checkpoint(tracks: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    active = []  # type: list[Tuple[str, str, str]]
    for track in tracks:
        track_kind = str(track["kind"])
        for cue_value in track["cues"]:  # type: ignore[index]
            cue = _mapping_value(cue_value, "compiled cue")
            if int(cue["start_ms"]) <= 0 < int(cue["end_ms"]):
                active.append((str(cue["cue_id"]), track_kind, str(cue["intent"])))

    def intent_for(kind: str) -> Optional[str]:
        return next((intent for _cue_id, track_kind, intent in active if track_kind == kind), None)

    return {
        "checkpoint_id": "checkpoint:time-zero",
        "media_time_ms": 0,
        "reason": "time_zero",
        "state": {
            "active_cue_ids": sorted(cue_id for cue_id, _kind, _intent in active),
            "chapter_id": None,
            "scene_id": None,
            "setup_id": None,
            "stage_intent": intent_for("stage"),
            "body_intent": intent_for("body_base"),
            "face_intent": intent_for("face"),
            "gaze_intent": intent_for("gaze"),
            "speech_intent": intent_for("speech"),
        },
    }


def _mapping_sequence(value: Mapping[str, object], parent: str, field: str) -> Tuple[object, ...]:
    mapping = _mapping_value(value.get(parent), parent)
    return _sequence_value(mapping.get(field), field)


def _mapping_value(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PerformanceCompileError("invalid_type", "{} must be an object".format(name))
    return value


def _sequence_value(value: object, name: str) -> Tuple[object, ...]:
    if not isinstance(value, (list, tuple)):
        raise PerformanceCompileError("invalid_type", "{} must be an array".format(name))
    return tuple(value)


def _string_value(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise PerformanceCompileError("invalid_type", "{} must be a non-empty string".format(name))
    return value


def _unique_path(path: Sequence[str]) -> Tuple[str, ...]:
    seen = set()
    return tuple(item for item in path if item and not (item in seen or seen.add(item)))


def _reject_renderer_intent(
    intent: str,
    capabilities_by_id: Mapping[str, Mapping[str, object]],
    poses_by_id: Mapping[str, Mapping[str, object]],
) -> None:
    raw_clip_ids = {
        str(clip_id)
        for capability in capabilities_by_id.values()
        for clip_id in _mapping_sequence(capability, "mapping", "clip_ids")
    }
    if (
        intent.startswith(("pose:", "clip:"))
        or intent in poses_by_id
        or intent in raw_clip_ids
    ):
        raise PerformanceCompileError(
            "raw_renderer_intent",
            "semantic intent cannot contain a renderer pose or clip identifier",
        )


def _reject_private_values(value: object) -> None:
    if isinstance(value, Mapping):
        for item in value.values():
            _reject_private_values(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _reject_private_values(item)
        return
    if isinstance(value, str) and any(pattern.search(value) for pattern in _PRIVATE_VALUE_PATTERNS):
        raise PerformanceCompileError(
            "private_content",
            "compiler input contains a forbidden private value",
        )


def canonical_artifact_bytes(value: Mapping[str, object]) -> bytes:
    """Serialize baseline artifacts deterministically for publication/tests."""

    _reject_noncanonical_values(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _resolve_spans(
    transcript: TranscriptDocument,
    duration_ms: int,
    timing_spans: Sequence[NarrativeTimingSpan],
) -> Tuple[Tuple[NarrativeTimingSpan, ...], str]:
    block_ids = [block.block_id for block in transcript.blocks]
    if timing_spans:
        spans_by_id = {span.block_id: span for span in timing_spans}
        if len(spans_by_id) != len(timing_spans) or set(spans_by_id) != set(block_ids):
            raise PerformanceCompileError(
                "timing_span_mismatch", "timing spans must cover every block exactly once"
            )
        ordered = tuple(spans_by_id[block_id] for block_id in block_ids)
        previous_start = -1
        previous_end = -1
        for span in ordered:
            _require_range(span.start_ms, span.end_ms, duration_ms)
            if span.start_ms < previous_start:
                raise PerformanceCompileError(
                    "timing_span_order", "timing spans must be monotonic"
                )
            if span.start_ms < previous_end:
                raise PerformanceCompileError(
                    "timing_span_overlap", "timing spans may not overlap"
                )
            previous_start = span.start_ms
            previous_end = span.end_ms
        sources = {span.source for span in ordered}
        return ordered, sources.pop() if len(sources) == 1 else "mixed"

    weights = [max(1, len(block.spoken_normalized_text.split())) for block in transcript.blocks]
    total_weight = sum(weights)
    if duration_ms < len(weights):
        raise PerformanceCompileError(
            "duration_too_short", "media duration cannot assign a non-empty block range"
        )
    boundaries = [0]
    cumulative = 0
    for weight in weights[:-1]:
        cumulative += weight
        boundaries.append((duration_ms * cumulative) // total_weight)
    boundaries.append(duration_ms)
    spans = tuple(
        NarrativeTimingSpan(
            block_id=block_id,
            start_ms=boundaries[index],
            end_ms=boundaries[index + 1],
            source="fallback",
        )
        for index, block_id in enumerate(block_ids)
    )
    return spans, "fallback"


def _performer_mode(display_text: str) -> str:
    stripped = display_text.strip()
    quote_count = sum(stripped.count(mark) for mark in ('"', "\u201c", "\u201d"))
    if quote_count >= 2 or (stripped.startswith(("'", "\u2018")) and stripped.endswith(("'", "\u2019"))):
        return "dialogue"
    return "narration"


def _beat_function(display_text: str, *, chapter_index: int, chapter_count: int) -> str:
    stripped = display_text.rstrip()
    if chapter_index == 0:
        return "orient"
    if chapter_index == chapter_count - 1:
        return "conclude"
    if stripped.endswith("?"):
        return "question"
    if stripped.endswith("!"):
        return "escalate"
    return "propose"


def _chapter_phase(index: int, count: int) -> str:
    if index == 0:
        return "entry"
    if index == count - 1:
        return "landing"
    progress_milli = (index * 1000) // max(1, count - 1)
    if progress_milli < 600:
        return "development"
    if progress_milli < 800:
        return "turn"
    return "release"


def _safe_gesture_intent(beat_function: str, density_milli: int) -> str:
    if density_milli >= 650:
        return "none"
    if beat_function == "question":
        return "question"
    if beat_function == "orient":
        return "orient"
    return "none"


def _duration_only_mouth_shape(phase_ms: int) -> str:
    boundaries = (
        (120, "rest"),
        (310, "open"),
        (440, "wide"),
        (650, "open"),
        (740, "rest"),
        (900, "rounded"),
    )
    for boundary, shape in boundaries:
        if phase_ms < boundary:
            return shape
    return "rest"


def _require_range(start_ms: object, end_ms: object, duration_ms: int) -> None:
    _require_nonnegative_int("start_ms", start_ms)
    _require_positive_int("end_ms", end_ms)
    if int(start_ms) >= int(end_ms) or int(end_ms) > duration_ms:
        raise PerformanceCompileError("range_invalid", "time range is outside media")


def _require_positive_int(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise PerformanceCompileError("invalid_type", "{} must be a positive integer".format(name))


def _require_nonnegative_int(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise PerformanceCompileError(
            "invalid_type", "{} must be a non-negative integer".format(name)
        )


def _require_sha256_ref(name: str, value: object) -> None:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise PerformanceCompileError("invalid_hash", "{} is not a SHA-256 reference".format(name))
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise PerformanceCompileError(
            "invalid_hash", "{} is not a SHA-256 reference".format(name)
        ) from exc


def _identity_hash(value: Mapping[str, object]) -> str:
    return "sha256:" + hashlib.sha256(canonical_artifact_bytes(value)).hexdigest()


def _reject_noncanonical_values(value: object) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, list) or isinstance(value, tuple):
        for item in value:
            _reject_noncanonical_values(item)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise PerformanceCompileError(
                    "noncanonical_value", "artifact keys must be strings"
                )
            _reject_noncanonical_values(item)
        return
    raise PerformanceCompileError(
        "noncanonical_value", "artifact identities may not contain floats or binary values"
    )


def _ordered_narrative_score(value: Mapping[str, object]) -> Dict[str, object]:
    return {
        "schema_version": value["schema_version"],
        "narrative_score_id": value["narrative_score_id"],
        "media_id": value["media_id"],
        "transcript_id": value["transcript_id"],
        "alignment_id": value["alignment_id"],
        "duration_ms": value["duration_ms"],
        "book_profile": value["book_profile"],
        "chapter_envelopes": value["chapter_envelopes"],
        "beats": value["beats"],
        "provenance": value["provenance"],
    }


def _ordered_performance_score(value: Mapping[str, object]) -> Dict[str, object]:
    return {
        "schema_version": value["schema_version"],
        "score_id": value["score_id"],
        "revision": value["revision"],
        "status": value["status"],
        "mode": value["mode"],
        "media": value["media"],
        "analysis_ref": value["analysis_ref"],
        "tracks": value["tracks"],
        "provenance": value["provenance"],
        "validation": value["validation"],
    }


__all__ = [
    "BaselineCompilation",
    "CHARACTER_BINDING_POLICY_VERSION",
    "NARRATIVE_PIPELINE_VERSION",
    "NarrativeTimingSpan",
    "PERFORMANCE_ASSEMBLY_VERSION",
    "PerformanceCompileError",
    "PerformanceSourceSelection",
    "SpeechFallbackProfile",
    "SpeechFallbackState",
    "assemble_performance_score",
    "build_speech_fallback_profile",
    "canonical_artifact_bytes",
    "compile_baseline_performance",
    "compile_character_bound_performance",
    "compile_character_bound_score",
    "compile_narrative_baseline",
    "evaluate_speech_fallback",
    "select_performance_source",
    "timing_spans_from_captions",
]
