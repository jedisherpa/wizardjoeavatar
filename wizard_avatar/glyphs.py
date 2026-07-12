from __future__ import annotations

from types import MappingProxyType


GLYPHS = MappingProxyType(
    {
        "empty": " ",
        "highlight": ".",
        "soft_fill": ":",
        "cloth_fill": "+",
        "skin_fill": "o",
        "beard_fill": "%",
        "solid_fill": "#",
        "outline": "@",
        "spark": "*",
        "eye": "O",
        "belt": "=",
        "trim": "-",
    }
)

PRIMARY_GLYPHS = tuple(" .:-=+*oO#%@")


def glyph(role: str) -> str:
    try:
        return GLYPHS[role]
    except KeyError as exc:
        raise KeyError(f"Unknown glyph role: {role}") from exc
