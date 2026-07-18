from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .models import MOUTH_SHAPES


MOUTH_CELLS: Dict[str, List[Tuple[int, int, str]]] = {
    "closed": [(16, 23, "-"), (17, 23, "-"), (18, 23, "-")],
    "open_small": [(16, 23, "-"), (17, 23, "o"), (18, 23, "-")],
    "open_medium": [(16, 23, "o"), (17, 23, "O"), (18, 23, "o")],
    "open_wide": [(15, 23, "o"), (16, 23, "O"), (17, 23, "O"), (18, 23, "o")],
    "rounded": [(16, 22, "o"), (17, 22, "O"), (18, 22, "o"), (17, 23, "o")],
    "smile": [(15, 23, "."), (16, 24, "-"), (17, 24, "-"), (18, 24, "." )],
    "frown": [(15, 24, "."), (16, 23, "-"), (17, 23, "-"), (18, 23, ".")],
}


def validate_mouth_shape(shape: str) -> None:
    if shape not in MOUTH_SHAPES:
        raise ValueError(f"Unsupported mouth shape: {shape}")


_SPEECH_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?|[^\w\s]", re.ASCII)
_VOWELS = frozenset("aeiouy")
_PAUSE_WEIGHTS = {
    ",": 0.55,
    ";": 0.70,
    ":": 0.70,
    ".": 0.95,
    "!": 0.85,
    "?": 0.90,
    "-": 0.45,
}
_WORD_PATTERNS = (
    ("open_small", "open_medium", "rounded", "open_small"),
    ("open_medium", "open_small", "open_wide", "open_small"),
    ("open_small", "rounded", "open_medium", "open_small"),
    ("open_medium", "open_wide", "open_small", "rounded"),
)


def fallback_speech_shape(
    elapsed_seconds: float,
    duration_seconds: float,
    text: str,
) -> str:
    """Resolve a deterministic, utterance-relative mouth shape.

    This is intentionally a degraded local fallback. Aligned media speech must
    supply its own mouth state and must never call this function.
    """

    duration = max(0.0, float(duration_seconds))
    elapsed = max(0.0, min(float(elapsed_seconds), duration))
    if duration <= 0.0 or elapsed >= max(0.0, duration - min(0.08, duration * 0.12)):
        return "closed"
    if elapsed < min(0.06, duration * 0.08):
        return "open_small"

    tokens = _SPEECH_TOKEN_RE.findall(text or "")
    if not tokens:
        tokens = ["speech"]
    weighted = [(token, _speech_token_weight(token)) for token in tokens]
    total_weight = sum(weight for _token, weight in weighted)
    progress = (elapsed / duration) * total_weight

    cursor = 0.0
    for token, weight in weighted:
        end = cursor + weight
        if progress < end:
            if not token[0].isalnum():
                return "closed"
            local_phase = max(0.0, min(0.999999, (progress - cursor) / weight))
            return _word_mouth_shape(token, local_phase)
        cursor = end
    return "closed"


def _speech_token_weight(token: str) -> float:
    if not token[0].isalnum():
        return _PAUSE_WEIGHTS.get(token, 0.40)
    syllables = 0
    previous_vowel = False
    for character in token.lower():
        vowel = character in _VOWELS
        if vowel and not previous_vowel:
            syllables += 1
        previous_vowel = vowel
    return max(0.85, min(3.2, max(1, syllables) * 0.72 + len(token) * 0.10))


def _word_mouth_shape(token: str, local_phase: float) -> str:
    seed = sum((index + 1) * ord(character) for index, character in enumerate(token.lower()))
    pattern = _WORD_PATTERNS[seed % len(_WORD_PATTERNS)]
    index = min(len(pattern) - 1, int(local_phase * len(pattern)))
    return pattern[index]
