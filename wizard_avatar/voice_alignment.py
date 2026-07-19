"""Immutable voice alignment and approved-text reveal primitive.

This module deliberately owns no clock and performs no I/O. Callers supply an
absolute position from the audible media source and receive a complete result
that can be reconstructed identically after a seek.
"""

from __future__ import annotations

import bisect
import json
import re
from dataclasses import dataclass
from typing import Dict, Mapping, Sequence, Tuple, Type, TypeVar

from .artifact_hashing import MAX_SAFE_INTEGER, canonical_json_v1, sha256_ref
from .models import MOUTH_SHAPES


VOICE_ALIGNMENT_SCHEMA_VERSION = 1
VOICE_ALIGNMENT_MAX_BODY_BYTES = 256 * 1024
VOICE_PRESENTATION_MAX_DURATION_MS = 60 * 60 * 1000

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_PHONEME_CLASSES = frozenset(
    {"rest", "mbp", "fv", "th", "dtln", "kg", "chsh", "sz", "r", "a", "e", "i", "o", "u"}
)
_PHONEME_MOUTHS = {
    "rest": "closed",
    "mbp": "closed",
    "fv": "open_small",
    "th": "open_small",
    "dtln": "open_small",
    "sz": "open_small",
    "kg": "open_medium",
    "chsh": "open_medium",
    "a": "open_wide",
    "r": "rounded",
    "o": "rounded",
    "u": "rounded",
    "e": "smile",
    "i": "smile",
}
_FALLBACK_MOUTHS = (
    "open_small",
    "open_medium",
    "rounded",
    "open_medium",
    "open_wide",
    "open_small",
)
_FALLBACK_STEP_MS = 90
_PRESENTATION_FPS = 24
_PRESENTATION_BEAT_FRAMES = 5
_PRESENTATION_COARTICULATION_FRAMES = 4
_PRESENTATION_FALLBACK_CLOSURE_CADENCE = 12
_PRESENTATION_FALLBACK_CLOSURE_BEATS = 3
_MOUTH_APERTURE = {
    "closed": 0,
    "open_small": 1,
    "rounded": 1,
    "smile": 1,
    "frown": 1,
    "open_medium": 2,
    "open_wide": 3,
}
_APERTURE_BRIDGE = {
    0: "closed",
    1: "open_small",
    2: "open_medium",
    3: "open_wide",
}


class VoiceAlignmentError(ValueError):
    """Stable validation error for the V1 voice alignment boundary."""

    def __init__(self, code: str, path: str, message: str) -> None:
        super().__init__("{}: {}".format(path, message))
        self.code = code
        self.path = path


def _error(code: str, path: str, message: str) -> VoiceAlignmentError:
    return VoiceAlignmentError(code, path, message)


def _closed(mapping: Mapping[str, object], fields: Sequence[str], path: str) -> None:
    expected = set(fields)
    actual = set(mapping)
    missing = expected - actual
    if missing:
        raise _error("missing_field", path, "required field is missing")
    if actual - expected:
        raise _error("unknown_field", path, "object contains an unknown field")


def _integer(value: object, path: str, minimum: int = 0) -> int:
    if type(value) is not int:
        raise _error("invalid_type", path, "must be an integer")
    if value < minimum or value > MAX_SAFE_INTEGER:
        raise _error("range_invalid", path, "integer is outside the accepted range")
    return value


def _identifier(value: object, path: str, prefix: str = "") -> str:
    if type(value) is not str or not _ID_PATTERN.fullmatch(value):
        raise _error("identity_invalid", path, "must be a valid identifier")
    if prefix and not value.startswith(prefix):
        raise _error("identity_invalid", path, "identifier has the wrong namespace")
    return value


def _sha256(value: object, path: str) -> str:
    if type(value) is not str or not _SHA256_PATTERN.fullmatch(value):
        raise _error("hash_invalid", path, "must be a lowercase SHA-256 reference")
    return value


@dataclass(frozen=True)
class TextTimingSpanV1:
    """A content-free word or character range on the approved response."""

    start_ms: int
    end_ms: int
    start_char: int
    end_char: int

    def __post_init__(self) -> None:
        _integer(self.start_ms, "$.start_ms")
        _integer(self.end_ms, "$.end_ms")
        _integer(self.start_char, "$.start_char")
        _integer(self.end_char, "$.end_char")
        if self.start_ms >= self.end_ms:
            raise _error("range_invalid", "$.end_ms", "timing span must have positive duration")
        if self.start_char >= self.end_char:
            raise _error("range_invalid", "$.end_char", "text span must contain at least one character")

    @classmethod
    def from_mapping(cls, value: object, path: str = "$") -> "TextTimingSpanV1":
        if not isinstance(value, Mapping):
            raise _error("invalid_type", path, "must be an object")
        fields = ("start_ms", "end_ms", "start_char", "end_char")
        _closed(value, fields, path)
        return cls(
            start_ms=_integer(value["start_ms"], path + ".start_ms"),
            end_ms=_integer(value["end_ms"], path + ".end_ms"),
            start_char=_integer(value["start_char"], path + ".start_char"),
            end_char=_integer(value["end_char"], path + ".end_char"),
        )

    def to_dict(self) -> Dict[str, int]:
        return {
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "start_char": self.start_char,
            "end_char": self.end_char,
        }


@dataclass(frozen=True)
class PhonemeTimingSpanV1:
    """A semantic phoneme-class interval; it never carries source text."""

    start_ms: int
    end_ms: int
    phoneme_class: str

    def __post_init__(self) -> None:
        _integer(self.start_ms, "$.start_ms")
        _integer(self.end_ms, "$.end_ms")
        if self.start_ms >= self.end_ms:
            raise _error("range_invalid", "$.end_ms", "timing span must have positive duration")
        if self.phoneme_class not in _PHONEME_CLASSES:
            raise _error("phoneme_unknown", "$.phoneme_class", "phoneme class is not supported by V1")

    @classmethod
    def from_mapping(cls, value: object, path: str = "$") -> "PhonemeTimingSpanV1":
        if not isinstance(value, Mapping):
            raise _error("invalid_type", path, "must be an object")
        fields = ("start_ms", "end_ms", "phoneme_class")
        _closed(value, fields, path)
        phoneme_class = value["phoneme_class"]
        if type(phoneme_class) is not str:
            raise _error("invalid_type", path + ".phoneme_class", "must be a string")
        return cls(
            start_ms=_integer(value["start_ms"], path + ".start_ms"),
            end_ms=_integer(value["end_ms"], path + ".end_ms"),
            phoneme_class=phoneme_class,
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "phoneme_class": self.phoneme_class,
        }


_SpanT = TypeVar("_SpanT", TextTimingSpanV1, PhonemeTimingSpanV1)


def _span_tuple(
    value: object,
    path: str,
    span_type: Type[_SpanT],
) -> Tuple[_SpanT, ...]:
    if type(value) is not list and type(value) is not tuple:
        raise _error("invalid_type", path, "must be an array")
    return tuple(
        span_type.from_mapping(item, "{}[{}]".format(path, index))
        if isinstance(item, Mapping)
        else _invalid_span(item, "{}[{}]".format(path, index))
        for index, item in enumerate(value)
    )


def _invalid_span(_value: object, path: str) -> _SpanT:
    raise _error("invalid_type", path, "must be an object")


def _validate_time_track(spans: Sequence[object], duration_ms: int, path: str) -> None:
    previous_end = 0
    for index, span in enumerate(spans):
        start_ms = span.start_ms  # type: ignore[attr-defined]
        end_ms = span.end_ms  # type: ignore[attr-defined]
        item_path = "{}[{}]".format(path, index)
        if end_ms > duration_ms:
            raise _error("timing_out_of_range", item_path, "timing exceeds media duration")
        if index and start_ms < previous_end:
            raise _error("timing_overlap", item_path, "timing spans overlap or are out of order")
        previous_end = end_ms


def _validate_text_track(
    spans: Sequence[TextTimingSpanV1],
    approved_text_length: int,
    path: str,
) -> None:
    previous_end = 0
    for index, span in enumerate(spans):
        item_path = "{}[{}]".format(path, index)
        if span.end_char > approved_text_length:
            raise _error("text_out_of_range", item_path, "text range exceeds approved text length")
        if index and span.start_char < previous_end:
            raise _error("text_overlap", item_path, "text ranges overlap or are out of order")
        previous_end = span.end_char


@dataclass(frozen=True)
class VoiceAlignmentDiagnosticsV1:
    alignment_sha256: str
    approved_content_sha256: str
    media_sha256: str
    speech_identity_sha256: str
    duration_ms: int
    approved_text_length: int
    word_span_count: int
    character_span_count: int
    phoneme_span_count: int
    first_timed_ms: int
    last_timed_ms: int
    mouth_policy: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "alignment_sha256": self.alignment_sha256,
            "approved_content_sha256": self.approved_content_sha256,
            "media_sha256": self.media_sha256,
            "speech_identity_sha256": self.speech_identity_sha256,
            "duration_ms": self.duration_ms,
            "approved_text_length": self.approved_text_length,
            "word_span_count": self.word_span_count,
            "character_span_count": self.character_span_count,
            "phoneme_span_count": self.phoneme_span_count,
            "first_timed_ms": self.first_timed_ms,
            "last_timed_ms": self.last_timed_ms,
            "mouth_policy": self.mouth_policy,
        }


@dataclass(frozen=True)
class VoiceAlignmentEvaluationV1:
    media_time_ms: int
    reveal_boundary: int
    mouth_shape: str
    speaking: bool
    terminal: bool
    mouth_policy: str

    def __post_init__(self) -> None:
        if self.mouth_shape not in MOUTH_SHAPES:
            raise ValueError("mouth_shape is not supported by the avatar")

    def to_dict(self) -> Dict[str, object]:
        return {
            "media_time_ms": self.media_time_ms,
            "reveal_boundary": self.reveal_boundary,
            "mouth_shape": self.mouth_shape,
            "speaking": self.speaking,
            "terminal": self.terminal,
            "mouth_policy": self.mouth_policy,
        }


@dataclass(frozen=True)
class VoicePresentationTrackV1:
    """Immutable, seek-stable mouth presentation compiled off the frame loop."""

    duration_ms: int
    fps: int
    mouth_shapes: Tuple[str, ...]
    speaking_frames: Tuple[bool, ...]

    def __post_init__(self) -> None:
        if (
            type(self.duration_ms) is not int
            or type(self.fps) is not int
            or self.duration_ms <= 0
            or self.fps <= 0
        ):
            raise ValueError("voice presentation timing must be positive")
        if (
            type(self.mouth_shapes) is not tuple
            or type(self.speaking_frames) is not tuple
            or not self.mouth_shapes
            or len(self.mouth_shapes) != len(self.speaking_frames)
        ):
            raise ValueError("voice presentation tracks must be nonempty and paired")
        if any(shape not in MOUTH_SHAPES for shape in self.mouth_shapes):
            raise ValueError("voice presentation contains an unsupported mouth shape")
        if any(type(active) is not bool for active in self.speaking_frames):
            raise ValueError("voice presentation speaking values must be booleans")

    def evaluate(self, media_time_ms: int) -> Tuple[str, bool]:
        requested = _integer(media_time_ms, "$.media_time_ms")
        if requested >= self.duration_ms:
            return "closed", False
        index = min(
            len(self.mouth_shapes) - 1,
            (requested * self.fps) // 1000,
        )
        return self.mouth_shapes[index], self.speaking_frames[index]


@dataclass(frozen=True)
class VoiceAlignmentV1:
    schema_version: int
    alignment_id: str
    approved_content_sha256: str
    approved_text_length: int
    media_id: str
    media_sha256: str
    speech_id: str
    voice_id: str
    duration_ms: int
    word_spans: Tuple[TextTimingSpanV1, ...]
    character_spans: Tuple[TextTimingSpanV1, ...]
    phoneme_spans: Tuple[PhonemeTimingSpanV1, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != VOICE_ALIGNMENT_SCHEMA_VERSION:
            raise _error("schema_version_unsupported", "$.schema_version", "must equal 1")
        _identifier(self.alignment_id, "$.alignment_id", "alignment:")
        _sha256(self.approved_content_sha256, "$.approved_content_sha256")
        _integer(self.approved_text_length, "$.approved_text_length")
        _identifier(self.media_id, "$.media_id", "media:")
        _sha256(self.media_sha256, "$.media_sha256")
        if self.media_id.startswith("media:sha256:") and self.media_id != "media:" + self.media_sha256:
            raise _error("media_hash_mismatch", "$.media_id", "media ID does not match media digest")
        _identifier(self.speech_id, "$.speech_id", "speech:")
        _identifier(self.voice_id, "$.voice_id")
        _integer(self.duration_ms, "$.duration_ms", 1)
        if type(self.word_spans) is not tuple or not all(isinstance(item, TextTimingSpanV1) for item in self.word_spans):
            raise _error("invalid_type", "$.word_spans", "must be an immutable text-span tuple")
        if type(self.character_spans) is not tuple or not all(isinstance(item, TextTimingSpanV1) for item in self.character_spans):
            raise _error("invalid_type", "$.character_spans", "must be an immutable text-span tuple")
        if type(self.phoneme_spans) is not tuple or not all(isinstance(item, PhonemeTimingSpanV1) for item in self.phoneme_spans):
            raise _error("invalid_type", "$.phoneme_spans", "must be an immutable phoneme-span tuple")
        if self.word_spans and self.character_spans:
            raise _error("reveal_track_ambiguous", "$", "word and character reveal tracks are mutually exclusive")
        if self.approved_text_length and not (self.word_spans or self.character_spans):
            raise _error("reveal_track_missing", "$", "nonempty approved text requires a reveal track")
        if not self.approved_text_length and (self.word_spans or self.character_spans):
            raise _error("text_out_of_range", "$", "empty approved text cannot have reveal spans")
        _validate_time_track(self.word_spans, self.duration_ms, "$.word_spans")
        _validate_time_track(self.character_spans, self.duration_ms, "$.character_spans")
        _validate_time_track(self.phoneme_spans, self.duration_ms, "$.phoneme_spans")
        _validate_text_track(self.word_spans, self.approved_text_length, "$.word_spans")
        _validate_text_track(self.character_spans, self.approved_text_length, "$.character_spans")

    @classmethod
    def from_mapping(cls, value: object) -> "VoiceAlignmentV1":
        if not isinstance(value, Mapping):
            raise _error("invalid_type", "$", "voice alignment must be an object")
        fields = (
            "schema_version",
            "alignment_id",
            "approved_content_sha256",
            "approved_text_length",
            "media_id",
            "media_sha256",
            "speech_id",
            "voice_id",
            "duration_ms",
            "word_spans",
            "character_spans",
            "phoneme_spans",
        )
        _closed(value, fields, "$")
        return cls(
            schema_version=value["schema_version"],  # type: ignore[arg-type]
            alignment_id=value["alignment_id"],  # type: ignore[arg-type]
            approved_content_sha256=value["approved_content_sha256"],  # type: ignore[arg-type]
            approved_text_length=value["approved_text_length"],  # type: ignore[arg-type]
            media_id=value["media_id"],  # type: ignore[arg-type]
            media_sha256=value["media_sha256"],  # type: ignore[arg-type]
            speech_id=value["speech_id"],  # type: ignore[arg-type]
            voice_id=value["voice_id"],  # type: ignore[arg-type]
            duration_ms=value["duration_ms"],  # type: ignore[arg-type]
            word_spans=_span_tuple(value["word_spans"], "$.word_spans", TextTimingSpanV1),
            character_spans=_span_tuple(value["character_spans"], "$.character_spans", TextTimingSpanV1),
            phoneme_spans=_span_tuple(value["phoneme_spans"], "$.phoneme_spans", PhonemeTimingSpanV1),
        )

    @classmethod
    def from_json(cls, payload: bytes) -> "VoiceAlignmentV1":
        if type(payload) is not bytes:
            raise _error("invalid_type", "$", "JSON payload must be bytes")
        if len(payload) > VOICE_ALIGNMENT_MAX_BODY_BYTES:
            raise _error("payload_too_large", "$", "JSON payload exceeds the V1 limit")

        def reject_duplicates(pairs: Sequence[Tuple[str, object]]) -> Dict[str, object]:
            result: Dict[str, object] = {}
            for key, item in pairs:
                if key in result:
                    raise _error("duplicate_json_key", "$", "JSON object contains a duplicate key")
                result[key] = item
            return result

        try:
            value = json.loads(payload.decode("utf-8"), object_pairs_hook=reject_duplicates)
        except VoiceAlignmentError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("json_invalid", "$", "payload is not valid UTF-8 JSON") from exc
        return cls.from_mapping(value)

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "alignment_id": self.alignment_id,
            "approved_content_sha256": self.approved_content_sha256,
            "approved_text_length": self.approved_text_length,
            "media_id": self.media_id,
            "media_sha256": self.media_sha256,
            "speech_id": self.speech_id,
            "voice_id": self.voice_id,
            "duration_ms": self.duration_ms,
            "word_spans": [span.to_dict() for span in self.word_spans],
            "character_spans": [span.to_dict() for span in self.character_spans],
            "phoneme_spans": [span.to_dict() for span in self.phoneme_spans],
        }

    def canonical_json(self) -> bytes:
        return canonical_json_v1(self.to_dict())

    @property
    def alignment_sha256(self) -> str:
        return sha256_ref(self.canonical_json())

    def evaluate(self, media_time_ms: int) -> VoiceAlignmentEvaluationV1:
        return evaluate_voice_alignment(self, media_time_ms)

    def diagnostics(self) -> VoiceAlignmentDiagnosticsV1:
        all_spans = self.word_spans + self.character_spans + self.phoneme_spans
        first_timed_ms = min((span.start_ms for span in all_spans), default=0)
        last_timed_ms = max((span.end_ms for span in all_spans), default=0)
        return VoiceAlignmentDiagnosticsV1(
            alignment_sha256=self.alignment_sha256,
            approved_content_sha256=self.approved_content_sha256,
            media_sha256=self.media_sha256,
            speech_identity_sha256=sha256_ref(
                canonical_json_v1(
                    {"speech_id": self.speech_id, "voice_id": self.voice_id}
                )
            ),
            duration_ms=self.duration_ms,
            approved_text_length=self.approved_text_length,
            word_span_count=len(self.word_spans),
            character_span_count=len(self.character_spans),
            phoneme_span_count=len(self.phoneme_spans),
            first_timed_ms=first_timed_ms,
            last_timed_ms=last_timed_ms,
            mouth_policy="phoneme_v1" if self.phoneme_spans else "absolute_duration_fallback_v1",
        )


def _active_span(spans: Sequence[_SpanT], media_time_ms: int) -> object:
    if not spans:
        return None
    starts = tuple(span.start_ms for span in spans)
    index = bisect.bisect_right(starts, media_time_ms) - 1
    if index >= 0 and media_time_ms < spans[index].end_ms:
        return spans[index]
    return None


def _reveal_boundary(alignment: VoiceAlignmentV1, media_time_ms: int) -> int:
    if media_time_ms >= alignment.duration_ms:
        return alignment.approved_text_length
    spans = alignment.word_spans or alignment.character_spans
    starts = tuple(span.start_ms for span in spans)
    index = bisect.bisect_right(starts, media_time_ms) - 1
    return spans[index].end_char if index >= 0 else 0


def _presentation_speech_intervals(
    alignment: VoiceAlignmentV1,
    fps: int,
) -> Tuple[Tuple[int, int], ...]:
    if alignment.phoneme_spans:
        source = (
            (span.start_ms, span.end_ms)
            for span in alignment.phoneme_spans
            if span.phoneme_class != "rest"
        )
    else:
        source = (
            (span.start_ms, span.end_ms)
            for span in (alignment.word_spans or alignment.character_spans)
        )
    merged = []
    for start_ms, end_ms in source:
        if (
            merged
            and (start_ms - merged[-1][1]) * fps
            <= _PRESENTATION_COARTICULATION_FRAMES * 1000
        ):
            merged[-1] = (merged[-1][0], end_ms)
        else:
            merged.append((start_ms, end_ms))
    return tuple(merged)


def _apply_presentation_envelope(
    alignment: VoiceAlignmentV1,
    shapes: Sequence[str],
    speaking: Sequence[bool],
    fps: int,
) -> Tuple[Tuple[str, ...], Tuple[bool, ...]]:
    intervals = _presentation_speech_intervals(alignment, fps)
    result_shapes = ["closed"] * len(shapes)
    result_speaking = [False] * len(shapes)
    interval_index = 0
    for frame_index, sampled_shape in enumerate(shapes):
        frame_start = frame_index * 1000
        frame_end = (frame_index + 1) * 1000
        while (
            interval_index < len(intervals)
            and intervals[interval_index][1] * fps < frame_end
        ):
            interval_index += 1
        if interval_index >= len(intervals):
            break
        start_ms, end_ms = intervals[interval_index]
        if frame_start >= start_ms * fps and frame_end <= end_ms * fps:
            result_shapes[frame_index] = (
                sampled_shape if speaking[frame_index] else "open_small"
            )
            result_speaking[frame_index] = True
    return tuple(result_shapes), tuple(result_speaking)


def _representative_beat_shape(
    shapes: Sequence[str],
    speaking: Sequence[bool],
) -> Tuple[str, bool]:
    if not speaking or not all(speaking):
        return "closed", False
    voiced_indices = list(range(len(speaking)))
    midpoint = (len(shapes) - 1) / 2.0
    selected_index = min(
        voiced_indices,
        key=lambda index: (abs(index - midpoint), -index),
    )
    return shapes[selected_index], True


def _bridge_aperture(previous: str, target: str) -> str:
    previous_rank = _MOUTH_APERTURE[previous]
    target_rank = _MOUTH_APERTURE[target]
    if abs(target_rank - previous_rank) <= 1:
        return target
    direction = 1 if target_rank > previous_rank else -1
    return _APERTURE_BRIDGE[previous_rank + direction]


def _presentation_hold_widths(frame_count: int) -> Tuple[int, ...]:
    if frame_count < 2:
        return ()
    if frame_count <= 7:
        return (frame_count,)
    hold_count = max(1, (frame_count + _PRESENTATION_BEAT_FRAMES // 2) // _PRESENTATION_BEAT_FRAMES)
    while hold_count > 1 and frame_count // hold_count < 4:
        hold_count -= 1
    width, wider_count = divmod(frame_count, hold_count)
    return (width + 1,) * wider_count + (width,) * (hold_count - wider_count)


def _sample_raw_presentation(
    alignment: VoiceAlignmentV1,
    frame_count: int,
    fps: int,
) -> Tuple[Tuple[str, ...], Tuple[bool, ...]]:
    """Sample a monotonic alignment in O(frames + spans) time."""

    shapes = []
    speaking = []
    if alignment.phoneme_spans:
        spans = alignment.phoneme_spans
        span_index = 0
        for frame_index in range(frame_count):
            sample_ms = min(
                alignment.duration_ms - 1,
                (frame_index * 1000 + 500) // fps,
            )
            while span_index < len(spans) and spans[span_index].end_ms <= sample_ms:
                span_index += 1
            active = (
                spans[span_index]
                if span_index < len(spans)
                and spans[span_index].start_ms <= sample_ms < spans[span_index].end_ms
                else None
            )
            if active is None or active.phoneme_class == "rest":
                shapes.append("closed")
                speaking.append(False)
            else:
                shapes.append(_PHONEME_MOUTHS[active.phoneme_class])
                speaking.append(True)
        return tuple(shapes), tuple(speaking)

    spans = alignment.word_spans or alignment.character_spans
    span_index = 0
    fallback_seed = int(alignment.alignment_sha256[7:15], 16)
    for frame_index in range(frame_count):
        sample_ms = min(
            alignment.duration_ms - 1,
            (frame_index * 1000 + 500) // fps,
        )
        while span_index < len(spans) and spans[span_index].end_ms <= sample_ms:
            span_index += 1
        active = (
            span_index < len(spans)
            and spans[span_index].start_ms <= sample_ms < spans[span_index].end_ms
        )
        if not active:
            shapes.append("closed")
            speaking.append(False)
            continue
        phase = (sample_ms + fallback_seed) // _FALLBACK_STEP_MS
        shapes.append(_FALLBACK_MOUTHS[phase % len(_FALLBACK_MOUTHS)])
        speaking.append(True)
    return tuple(shapes), tuple(speaking)


def compile_voice_presentation(
    alignment: VoiceAlignmentV1,
    fps: int = _PRESENTATION_FPS,
) -> VoicePresentationTrackV1:
    """Compile raw alignment into readable beats without changing its authority."""

    if not isinstance(alignment, VoiceAlignmentV1):
        raise TypeError("alignment must be a VoiceAlignmentV1")
    if type(fps) is not int or fps <= 0:
        raise ValueError("fps must be a positive integer")
    if alignment.duration_ms > VOICE_PRESENTATION_MAX_DURATION_MS:
        raise _error(
            "presentation_duration_unsupported",
            "$.duration_ms",
            "presentation duration exceeds the one-hour chunk boundary",
        )
    frame_count = max(1, (alignment.duration_ms * fps + 999) // 1000)
    sampled_shapes, sampled_speaking = _sample_raw_presentation(
        alignment,
        frame_count,
        fps,
    )
    shapes, speaking = _apply_presentation_envelope(
        alignment,
        sampled_shapes,
        sampled_speaking,
        fps,
    )
    presented_shapes = ["closed"] * frame_count
    presented_speaking = [False] * frame_count
    island_start = 0
    while island_start < frame_count:
        if not speaking[island_start]:
            island_start += 1
            continue
        island_end = island_start + 1
        while island_end < frame_count and speaking[island_end]:
            island_end += 1
        hold_widths = _presentation_hold_widths(island_end - island_start)
        targets = []
        cursor = island_start
        for width in hold_widths:
            target, _active = _representative_beat_shape(
                shapes[cursor : cursor + width],
                speaking[cursor : cursor + width],
            )
            targets.append(target)
            cursor += width

        previous = "closed"
        cursor = island_start
        for hold_index, (target, width) in enumerate(zip(targets, hold_widths)):
            maximum_rank = min(3, len(targets) - hold_index)
            fallback_closure_phase = (
                hold_index % _PRESENTATION_FALLBACK_CLOSURE_CADENCE
            )
            fallback_closing = (
                not alignment.phoneme_spans
                and len(targets) >= _PRESENTATION_FALLBACK_CLOSURE_CADENCE
                and fallback_closure_phase
                >= _PRESENTATION_FALLBACK_CLOSURE_CADENCE
                - _PRESENTATION_FALLBACK_CLOSURE_BEATS
            )
            desired = "closed" if fallback_closing else target
            if _MOUTH_APERTURE[desired] > maximum_rank:
                desired = _APERTURE_BRIDGE[maximum_rank]
            presented = _bridge_aperture(previous, desired)
            presented_shapes[cursor : cursor + width] = [presented] * width
            presented_speaking[cursor : cursor + width] = [True] * width
            previous = presented
            cursor += width
        island_start = island_end

    return VoicePresentationTrackV1(
        duration_ms=alignment.duration_ms,
        fps=fps,
        mouth_shapes=tuple(presented_shapes),
        speaking_frames=tuple(presented_speaking),
    )


def evaluate_voice_alignment(
    alignment: VoiceAlignmentV1,
    media_time_ms: int,
) -> VoiceAlignmentEvaluationV1:
    """Evaluate reveal and mouth state from one authoritative media timestamp."""

    if not isinstance(alignment, VoiceAlignmentV1):
        raise TypeError("alignment must be a VoiceAlignmentV1")
    requested_time_ms = _integer(media_time_ms, "$.media_time_ms")
    resolved_time_ms = min(requested_time_ms, alignment.duration_ms)
    terminal = requested_time_ms >= alignment.duration_ms
    reveal_boundary = _reveal_boundary(alignment, resolved_time_ms)

    if terminal:
        mouth_shape = "closed"
        speaking = False
        mouth_policy = "ended"
    elif alignment.phoneme_spans:
        phoneme = _active_span(alignment.phoneme_spans, resolved_time_ms)
        if phoneme is None:
            mouth_shape = "closed"
            speaking = False
            mouth_policy = "silence"
        else:
            mouth_shape = _PHONEME_MOUTHS[phoneme.phoneme_class]  # type: ignore[attr-defined]
            speaking = phoneme.phoneme_class != "rest"  # type: ignore[attr-defined]
            mouth_policy = "phoneme_v1" if speaking else "silence"
    else:
        reveal_spans = alignment.word_spans or alignment.character_spans
        active = _active_span(reveal_spans, resolved_time_ms)
        if active is None:
            mouth_shape = "closed"
            speaking = False
            mouth_policy = "silence"
        else:
            seed = int(alignment.alignment_sha256[7:15], 16)
            phase = (resolved_time_ms + seed) // _FALLBACK_STEP_MS
            mouth_shape = _FALLBACK_MOUTHS[phase % len(_FALLBACK_MOUTHS)]
            speaking = True
            mouth_policy = "absolute_duration_fallback_v1"

    return VoiceAlignmentEvaluationV1(
        media_time_ms=resolved_time_ms,
        reveal_boundary=reveal_boundary,
        mouth_shape=mouth_shape,
        speaking=speaking,
        terminal=terminal,
        mouth_policy=mouth_policy,
    )


__all__ = [
    "VOICE_ALIGNMENT_SCHEMA_VERSION",
    "VOICE_PRESENTATION_MAX_DURATION_MS",
    "PhonemeTimingSpanV1",
    "TextTimingSpanV1",
    "VoiceAlignmentDiagnosticsV1",
    "VoiceAlignmentError",
    "VoiceAlignmentEvaluationV1",
    "VoiceAlignmentV1",
    "VoicePresentationTrackV1",
    "compile_voice_presentation",
    "evaluate_voice_alignment",
]
