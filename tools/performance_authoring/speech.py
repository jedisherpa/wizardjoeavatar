"""Content-free fallback authoring for generated TTS and speaker audio."""

from wizard_avatar.performance_compiler import (
    PerformanceSourceSelection,
    SpeechFallbackProfile,
    SpeechFallbackState,
    build_speech_fallback_profile,
    evaluate_speech_fallback,
    select_performance_source,
)

__all__ = [
    "PerformanceSourceSelection",
    "SpeechFallbackProfile",
    "SpeechFallbackState",
    "build_speech_fallback_profile",
    "evaluate_speech_fallback",
    "select_performance_source",
]
