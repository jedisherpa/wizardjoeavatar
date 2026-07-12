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
}


def validate_mouth_shape(shape: str) -> None:
    if shape not in MOUTH_SHAPES:
        raise ValueError(f"Unsupported mouth shape: {shape}")


def fallback_speech_shape(elapsed_seconds: float) -> str:
    cycle = ["open_small", "open_medium", "rounded", "open_small", "closed"]
    return cycle[int(elapsed_seconds * 10) % len(cycle)]
