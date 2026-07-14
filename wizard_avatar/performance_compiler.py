from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, Tuple

from .transcript_ingest import CaptionCue, TranscriptDocument


NARRATIVE_PIPELINE_VERSION = "deterministic-narrative-baseline-v1"
PERFORMANCE_ASSEMBLY_VERSION = "deterministic-performance-assembly-v1"


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
    "compile_narrative_baseline",
    "evaluate_speech_fallback",
    "select_performance_source",
    "timing_spans_from_captions",
]
