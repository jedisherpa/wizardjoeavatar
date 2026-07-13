from __future__ import annotations

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
    "slightly_open": [(16, 23, "o"), (17, 23, "o")],
    "wide_vowel": [(15, 23, "O"), (16, 23, "O"), (17, 23, "O"), (18, 23, "O")],
    "open_vowel": [(16, 22, "O"), (17, 22, "O"), (16, 23, "O"), (17, 23, "O")],
    "rounded_vowel": [(16, 22, "o"), (17, 22, "O"), (18, 22, "o"), (17, 23, "o")],
    "teeth_consonant": [(15, 23, "="), (16, 23, "="), (17, 23, "="), (18, 23, "=")],
    "lower_lip_consonant": [(16, 23, "_"), (17, 23, "_")],
    "tongue_consonant": [(16, 22, "="), (17, 22, "="), (17, 23, "~")],
    "smile_speaking": [(15, 23, "/"), (16, 24, "O"), (17, 24, "O"), (18, 23, "\\")],
    "frown_speaking": [(15, 24, "\\"), (16, 23, "O"), (17, 23, "O"), (18, 24, "/")],
    "speech_emphasis": [(15, 22, "O"), (16, 22, "O"), (17, 22, "O"), (18, 22, "O"), (16, 23, "O"), (17, 23, "O")],
    "breath_pause": [(16, 23, "."), (17, 23, ".")],
}


def validate_mouth_shape(shape: str) -> None:
    if shape not in MOUTH_SHAPES:
        raise ValueError(f"Unsupported mouth shape: {shape}")


def fallback_speech_shape(elapsed_seconds: float) -> str:
    cycle = ["open_small", "open_medium", "rounded", "open_small", "closed"]
    return cycle[int(elapsed_seconds * 10) % len(cycle)]
