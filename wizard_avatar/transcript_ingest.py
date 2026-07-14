from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union


TRANSCRIPT_SCHEMA_VERSION = 1
TRANSCRIPT_NORMALIZER_VERSION = "transcript-normalizer-v1"
SUPPORTED_SOURCE_KINDS = frozenset(
    {"provided", "provider_tts", "local_asr", "human_corrected"}
)
SUPPORTED_FORMATS = frozenset({"text", "webvtt", "srt"})

_MEDIA_ID = re.compile(r"^media:sha256:[0-9a-f]{64}$")
_LANGUAGE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
_TIMING_LINE = re.compile(
    r"^(?P<start>(?:\d{1,3}:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*"
    r"(?P<end>(?:\d{1,3}:)?\d{2}:\d{2}[.,]\d{3})(?:\s+.*)?$"
)
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SSML_TAG = re.compile(
    r"</?(?:speak|break|prosody|phoneme|say-as|voice|p|s|sub|emphasis|audio|mark)\b",
    re.IGNORECASE,
)


class TranscriptIngestError(ValueError):
    """A stable, local transcript-ingestion failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CaptionCue:
    cue_id: str
    block_id: str
    start_ms: int
    end_ms: int
    display_text: str
    spoken_normalized_text: str

    def to_mapping(self) -> Dict[str, object]:
        return {
            "cue_id": self.cue_id,
            "block_id": self.block_id,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "display_text": self.display_text,
            "spoken_normalized_text": self.spoken_normalized_text,
        }


@dataclass(frozen=True)
class TranscriptBlock:
    block_id: str
    chapter_id: str
    order: int
    kind: str
    display_text: str
    spoken_normalized_text: str

    def to_mapping(self) -> Dict[str, object]:
        return {
            "block_id": self.block_id,
            "chapter_id": self.chapter_id,
            "order": self.order,
            "kind": self.kind,
            "display_text": self.display_text,
            "spoken_normalized_text": self.spoken_normalized_text,
        }


@dataclass(frozen=True)
class TranscriptChapter:
    chapter_id: str
    order: int
    title: Optional[str]
    block_ids: Tuple[str, ...]

    def to_mapping(self) -> Dict[str, object]:
        return {
            "chapter_id": self.chapter_id,
            "order": self.order,
            "title": self.title,
            "block_ids": list(self.block_ids),
        }


@dataclass(frozen=True)
class TranscriptDocument:
    transcript_id: str
    media_id: str
    source_sha256: str
    display_sha256: str
    spoken_normalized_sha256: str
    revision: int
    language: str
    source_kind: str
    chapters: Tuple[TranscriptChapter, ...]
    blocks: Tuple[TranscriptBlock, ...]
    importer_id: str
    normalizer_version: str
    parent_transcript_id: Optional[str]

    def to_mapping(self) -> Dict[str, object]:
        return {
            "schema_version": TRANSCRIPT_SCHEMA_VERSION,
            "transcript_id": self.transcript_id,
            "media_id": self.media_id,
            "source_sha256": self.source_sha256,
            "display_sha256": self.display_sha256,
            "spoken_normalized_sha256": self.spoken_normalized_sha256,
            "revision": self.revision,
            "language": self.language,
            "source_kind": self.source_kind,
            "chapters": [chapter.to_mapping() for chapter in self.chapters],
            "blocks": [block.to_mapping() for block in self.blocks],
            "provenance": {
                "importer_id": self.importer_id,
                "normalizer_version": self.normalizer_version,
                "parent_transcript_id": self.parent_transcript_id,
            },
        }


@dataclass(frozen=True)
class TranscriptIngestResult:
    transcript: TranscriptDocument
    caption_cues: Tuple[CaptionCue, ...]


class _CaptionMarkupStripper(HTMLParser):
    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.parts = []  # type: list[str]

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(
        self, tag: str, attrs: Sequence[Tuple[str, Optional[str]]]
    ) -> None:
        if tag.lower() == "br":
            self.parts.append("\n")

    def text(self) -> str:
        return "".join(self.parts)


def normalize_display_text(value: str) -> str:
    """Normalize display text without applying speech-specific rewriting."""

    if not isinstance(value, str):
        raise TranscriptIngestError("invalid_type", "transcript text must be a string")
    _reject_invalid_unicode(value)
    normalized = unicodedata.normalize("NFC", value.lstrip("\ufeff"))
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    if _CONTROL_CHARACTERS.search(normalized):
        raise TranscriptIngestError(
            "invalid_text_control", "transcript text contains a control character"
        )
    lines = [re.sub(r"[\t \f\v]+", " ", line).strip() for line in normalized.split("\n")]
    result = []  # type: list[str]
    previous_blank = False
    for line in lines:
        if line:
            result.append(line)
            previous_blank = False
        elif result and not previous_blank:
            result.append("")
            previous_blank = True
    while result and not result[-1]:
        result.pop()
    return "\n".join(result)


def normalize_spoken_text(value: str) -> str:
    """Create a stable, punctuation-light form for timing/cache identity."""

    display = normalize_display_text(value)
    folded = unicodedata.normalize("NFKC", display).casefold()
    characters = []  # type: list[str]
    for index, character in enumerate(folded):
        category = unicodedata.category(character)
        if category[0] in {"L", "N", "M"}:
            characters.append(character)
            continue
        if character in {"'", "\u2019"}:
            before = folded[index - 1] if index else ""
            after = folded[index + 1] if index + 1 < len(folded) else ""
            if before.isalnum() and after.isalnum():
                characters.append("'")
                continue
        characters.append(" ")
    return " ".join("".join(characters).split())


def parse_caption_text(value: str, caption_format: str) -> Tuple[CaptionCue, ...]:
    """Parse WebVTT or SRT into strict, monotonically ordered local cues."""

    normalized_format = _normalize_format(caption_format)
    if normalized_format not in {"webvtt", "srt"}:
        raise TranscriptIngestError(
            "invalid_caption_format", "caption format must be webvtt or srt"
        )
    display = normalize_display_text(value)
    lines = display.split("\n")
    if normalized_format == "webvtt":
        if not lines or not lines[0].startswith("WEBVTT"):
            raise TranscriptIngestError("caption_header_missing", "WebVTT header is missing")
        lines = lines[1:]

    groups = _split_nonempty_groups(lines)
    cues = []  # type: list[CaptionCue]
    previous_start = -1
    for group in groups:
        if normalized_format == "webvtt" and group[0].startswith(("NOTE", "STYLE", "REGION")):
            continue
        timing_index = next(
            (index for index, line in enumerate(group[:2]) if "-->" in line), None
        )
        if timing_index is None:
            raise TranscriptIngestError(
                "caption_timing_missing", "caption block has no timing line"
            )
        match = _TIMING_LINE.match(group[timing_index])
        if match is None:
            raise TranscriptIngestError(
                "caption_timing_invalid", "caption timing line is invalid"
            )
        start_ms = _timestamp_ms(match.group("start"))
        end_ms = _timestamp_ms(match.group("end"))
        if end_ms <= start_ms:
            raise TranscriptIngestError(
                "caption_range_invalid", "caption end must be after its start"
            )
        if start_ms < previous_start:
            raise TranscriptIngestError(
                "caption_order_invalid", "caption starts must be monotonic"
            )
        previous_start = start_ms
        raw_identifier = group[0] if timing_index == 1 else ""
        cue_index = len(cues) + 1
        cue_id = _safe_cue_id(raw_identifier, cue_index)
        block_id = "b-{:04d}".format(cue_index)
        payload = "\n".join(group[timing_index + 1 :])
        caption_text = _strip_caption_markup(payload)
        if not caption_text:
            raise TranscriptIngestError("caption_text_missing", "caption text is empty")
        cues.append(
            CaptionCue(
                cue_id=cue_id,
                block_id=block_id,
                start_ms=start_ms,
                end_ms=end_ms,
                display_text=caption_text,
                spoken_normalized_text=normalize_spoken_text(caption_text),
            )
        )
    if not cues:
        raise TranscriptIngestError("transcript_empty", "caption document has no cues")
    return tuple(cues)


def ingest_transcript(
    source: Union[str, bytes],
    *,
    media_id: str,
    transcript_format: str = "text",
    source_kind: str = "provided",
    language: str = "en",
    revision: int = 1,
    chapter_id: str = "ch-001",
    chapter_title: Optional[str] = None,
    parent_transcript_id: Optional[str] = None,
) -> TranscriptIngestResult:
    """Ingest local text/captions into a canonical immutable transcript revision."""

    _validate_common(media_id, source_kind, language, revision, chapter_id)
    source_bytes = _source_bytes(source)
    try:
        source_text = source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise TranscriptIngestError(
            "transcript_encoding_invalid", "transcript source must be UTF-8"
        ) from exc
    normalized_format = _normalize_format(transcript_format)
    caption_cues = ()  # type: Tuple[CaptionCue, ...]
    if normalized_format == "text":
        display = normalize_display_text(_strip_synthesis_markup(source_text))
        paragraphs = tuple(part for part in re.split(r"\n\s*\n", display) if part)
        if not paragraphs:
            raise TranscriptIngestError("transcript_empty", "transcript has no text")
    else:
        caption_cues = parse_caption_text(source_text, normalized_format)
        paragraphs = tuple(cue.display_text for cue in caption_cues)

    blocks = tuple(
        TranscriptBlock(
            block_id="b-{:04d}".format(index),
            chapter_id=chapter_id,
            order=index - 1,
            kind=_block_kind(paragraph),
            display_text=paragraph,
            spoken_normalized_text=normalize_spoken_text(paragraph),
        )
        for index, paragraph in enumerate(paragraphs, 1)
    )
    chapters = (
        TranscriptChapter(
            chapter_id=chapter_id,
            order=0,
            title=normalize_display_text(chapter_title) if chapter_title else None,
            block_ids=tuple(block.block_id for block in blocks),
        ),
    )
    document = _build_document(
        media_id=media_id,
        source_sha256=_sha256_ref(source_bytes),
        revision=revision,
        language=language,
        source_kind=source_kind,
        chapters=chapters,
        blocks=blocks,
        importer_id="{}-{}-v1".format(source_kind, normalized_format),
        parent_transcript_id=parent_transcript_id,
    )
    return TranscriptIngestResult(transcript=document, caption_cues=caption_cues)


def import_transcript(
    source: Union[str, bytes],
    **kwargs: object,
) -> TranscriptDocument:
    """Compatibility entry point returning only the portable transcript artifact."""

    return ingest_transcript(source, **kwargs).transcript


def revise_transcript(
    parent: TranscriptDocument,
    replacements: Mapping[str, str],
) -> TranscriptDocument:
    """Create a human-corrected immutable revision with stable block IDs."""

    if not replacements:
        raise TranscriptIngestError("revision_empty", "revision has no replacements")
    known = {block.block_id for block in parent.blocks}
    unknown = sorted(set(replacements) - known)
    if unknown:
        raise TranscriptIngestError(
            "block_unknown", "revision names unknown blocks: {}".format(unknown)
        )
    blocks = []  # type: list[TranscriptBlock]
    for block in parent.blocks:
        display_text = (
            normalize_display_text(replacements[block.block_id])
            if block.block_id in replacements
            else block.display_text
        )
        if not display_text:
            raise TranscriptIngestError("block_empty", "revised block may not be empty")
        blocks.append(
            TranscriptBlock(
                block_id=block.block_id,
                chapter_id=block.chapter_id,
                order=block.order,
                kind=block.kind,
                display_text=display_text,
                spoken_normalized_text=normalize_spoken_text(display_text),
            )
        )
    corrected_source = _canonical_json(
        {"blocks": [block.to_mapping() for block in blocks]}
    )
    return _build_document(
        media_id=parent.media_id,
        source_sha256=_sha256_ref(corrected_source),
        revision=parent.revision + 1,
        language=parent.language,
        source_kind="human_corrected",
        chapters=parent.chapters,
        blocks=tuple(blocks),
        importer_id="human-correction-v1",
        parent_transcript_id=parent.transcript_id,
    )


def _build_document(
    *,
    media_id: str,
    source_sha256: str,
    revision: int,
    language: str,
    source_kind: str,
    chapters: Tuple[TranscriptChapter, ...],
    blocks: Tuple[TranscriptBlock, ...],
    importer_id: str,
    parent_transcript_id: Optional[str],
) -> TranscriptDocument:
    display_bytes = "\n\n".join(block.display_text for block in blocks).encode("utf-8")
    spoken_bytes = "\n".join(
        block.spoken_normalized_text for block in blocks
    ).encode("utf-8")
    identity = {
        "schema_version": TRANSCRIPT_SCHEMA_VERSION,
        "media_id": media_id,
        "source_sha256": source_sha256,
        "display_sha256": _sha256_ref(display_bytes),
        "spoken_normalized_sha256": _sha256_ref(spoken_bytes),
        "revision": revision,
        "language": language,
        "source_kind": source_kind,
        "chapters": [chapter.to_mapping() for chapter in chapters],
        "blocks": [block.to_mapping() for block in blocks],
        "provenance": {
            "importer_id": importer_id,
            "normalizer_version": TRANSCRIPT_NORMALIZER_VERSION,
            "parent_transcript_id": parent_transcript_id,
        },
    }
    digest = hashlib.sha256(_canonical_json(identity)).hexdigest()
    return TranscriptDocument(
        transcript_id="transcript:{}".format(digest[:24]),
        media_id=media_id,
        source_sha256=source_sha256,
        display_sha256=str(identity["display_sha256"]),
        spoken_normalized_sha256=str(identity["spoken_normalized_sha256"]),
        revision=revision,
        language=language,
        source_kind=source_kind,
        chapters=chapters,
        blocks=blocks,
        importer_id=importer_id,
        normalizer_version=TRANSCRIPT_NORMALIZER_VERSION,
        parent_transcript_id=parent_transcript_id,
    )


def _validate_common(
    media_id: str,
    source_kind: str,
    language: str,
    revision: int,
    chapter_id: str,
) -> None:
    if not isinstance(media_id, str) or _MEDIA_ID.fullmatch(media_id) is None:
        raise TranscriptIngestError("invalid_media_id", "media_id is invalid")
    if source_kind not in SUPPORTED_SOURCE_KINDS:
        raise TranscriptIngestError("invalid_source_kind", "source_kind is unsupported")
    if not isinstance(language, str) or _LANGUAGE.fullmatch(language) is None:
        raise TranscriptIngestError("invalid_language", "language tag is invalid")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise TranscriptIngestError("invalid_revision", "revision must be positive")
    if not isinstance(chapter_id, str) or not re.fullmatch(
        r"[a-z0-9][a-z0-9._:-]{0,127}", chapter_id
    ):
        raise TranscriptIngestError("invalid_chapter_id", "chapter_id is invalid")


def _source_bytes(source: Union[str, bytes]) -> bytes:
    if isinstance(source, bytes):
        return source
    if isinstance(source, str):
        return source.encode("utf-8")
    raise TranscriptIngestError("invalid_type", "transcript source must be text or bytes")


def _normalize_format(value: str) -> str:
    aliases = {"vtt": "webvtt", "plain": "text", "txt": "text"}
    normalized = aliases.get(str(value).lower(), str(value).lower())
    if normalized not in SUPPORTED_FORMATS:
        raise TranscriptIngestError(
            "transcript_format_unsupported", "transcript format is unsupported"
        )
    return normalized


def _split_nonempty_groups(lines: Iterable[str]) -> Tuple[Tuple[str, ...], ...]:
    groups = []  # type: list[Tuple[str, ...]]
    current = []  # type: list[str]
    for line in lines:
        if line:
            current.append(line)
        elif current:
            groups.append(tuple(current))
            current = []
    if current:
        groups.append(tuple(current))
    return tuple(groups)


def _timestamp_ms(value: str) -> int:
    normalized = value.replace(",", ".")
    fields = normalized.split(":")
    if len(fields) == 2:
        hours = 0
        minutes_text, seconds_text = fields
    elif len(fields) == 3:
        hours_text, minutes_text, seconds_text = fields
        hours = int(hours_text)
    else:
        raise TranscriptIngestError("caption_timing_invalid", "timestamp is invalid")
    seconds, milliseconds = seconds_text.split(".")
    minutes = int(minutes_text)
    seconds_value = int(seconds)
    if minutes > 59 or seconds_value > 59:
        raise TranscriptIngestError("caption_timing_invalid", "timestamp is invalid")
    return ((hours * 60 + minutes) * 60 + seconds_value) * 1000 + int(milliseconds)


def _safe_cue_id(value: str, index: int) -> str:
    candidate = re.sub(r"[^a-z0-9._:-]+", "-", value.strip().casefold()).strip("-.")
    if candidate and re.fullmatch(r"[a-z0-9][a-z0-9._:-]{0,127}", candidate):
        return candidate
    return "cue-{:04d}".format(index)


def _block_kind(display_text: str) -> str:
    stripped = display_text.strip()
    if stripped.startswith(('"', "'", "\u2018", "\u201c")):
        return "dialogue"
    return "paragraph"


def _strip_caption_markup(value: str) -> str:
    stripper = _CaptionMarkupStripper()
    try:
        stripper.feed(value)
        stripper.close()
    except (ValueError, AssertionError) as exc:
        raise TranscriptIngestError("caption_markup_invalid", "caption markup is invalid") from exc
    return normalize_display_text(html.unescape(stripper.text()))


def _strip_synthesis_markup(value: str) -> str:
    if _SSML_TAG.search(value) is None:
        return value
    return _strip_caption_markup(value)


def _reject_invalid_unicode(value: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise TranscriptIngestError("invalid_unicode", "text contains a lone surrogate")


def _sha256_ref(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


__all__ = [
    "CaptionCue",
    "SUPPORTED_FORMATS",
    "SUPPORTED_SOURCE_KINDS",
    "TRANSCRIPT_NORMALIZER_VERSION",
    "TranscriptBlock",
    "TranscriptChapter",
    "TranscriptDocument",
    "TranscriptIngestError",
    "TranscriptIngestResult",
    "import_transcript",
    "ingest_transcript",
    "normalize_display_text",
    "normalize_spoken_text",
    "parse_caption_text",
    "revise_transcript",
]
