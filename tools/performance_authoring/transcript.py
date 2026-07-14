from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from wizard_avatar.transcript_ingest import (
    TranscriptDocument,
    TranscriptIngestResult,
    ingest_transcript,
    normalize_display_text,
    normalize_spoken_text,
    revise_transcript,
)

from .media import require_local_input


@dataclass(frozen=True)
class OptionalSpeechCapability:
    capability: str
    available: bool
    adapter: Optional[str]
    reason_code: Optional[str]

    def to_mapping(self) -> Dict[str, object]:
        return {
            "capability": self.capability,
            "available": self.available,
            "adapter": self.adapter,
            "reason_code": self.reason_code,
        }


def import_transcript(
    source: Union[str, Path],
    *,
    media_id: str,
    transcript_format: Optional[str] = None,
    source_kind: str = "provided",
    language: str = "en",
    revision: int = 1,
    chapter_id: str = "ch-001",
    chapter_title: Optional[str] = None,
) -> TranscriptIngestResult:
    source_path = require_local_input(source)
    selected_format = transcript_format or _format_from_suffix(source_path.suffix)
    return ingest_transcript(
        source_path.read_bytes(),
        media_id=media_id,
        transcript_format=selected_format,
        source_kind=source_kind,
        language=language,
        revision=revision,
        chapter_id=chapter_id,
        chapter_title=chapter_title,
    )


def optional_speech_capabilities() -> Tuple[OptionalSpeechCapability, ...]:
    """Report adapters only when code and separately staged model assets exist."""

    return (
        _python_adapter_capability("local_asr", "faster_whisper"),
        _python_adapter_capability("forced_alignment", "whisperx"),
    )


def _python_adapter_capability(capability: str, module: str) -> OptionalSpeechCapability:
    if importlib.util.find_spec(module) is None:
        return OptionalSpeechCapability(
            capability=capability,
            available=False,
            adapter=module,
            reason_code="adapter_not_installed",
        )
    return OptionalSpeechCapability(
        capability=capability,
        available=False,
        adapter=module,
        reason_code="model_assets_not_configured",
    )


def _format_from_suffix(suffix: str) -> str:
    formats = {".txt": "text", ".vtt": "webvtt", ".srt": "srt"}
    try:
        return formats[suffix.lower()]
    except KeyError as exc:
        raise ValueError("transcript format is required for this file suffix") from exc


__all__ = [
    "OptionalSpeechCapability",
    "TranscriptDocument",
    "import_transcript",
    "normalize_display_text",
    "normalize_spoken_text",
    "optional_speech_capabilities",
    "revise_transcript",
]
