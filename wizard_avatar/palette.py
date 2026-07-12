from __future__ import annotations

from types import MappingProxyType
from typing import Dict, Tuple


PALETTE_VERSION = "wizard-joe-v1"

PALETTE: Dict[str, str] = {
    "outline": "#17191C",
    "shadow_gray": "#363A3E",
    "beard_dark": "#6E7377",
    "beard_mid": "#BFC3C7",
    "beard_light": "#F4F4F1",
    "skin_dark": "#9B5428",
    "skin_mid": "#C7783E",
    "skin_light": "#E9AA71",
    "brown_dark": "#4C2912",
    "brown": "#874719",
    "blue_dark": "#082D59",
    "blue_mid": "#0E4C89",
    "blue_light": "#176DB5",
    "gold": "#EFA000",
    "gold_light": "#FFD247",
    "magenta": "#C51E72",
    "cyan_magic": "#26D7E8",
}

ENVIRONMENT = {
    "background": "#FFFFFF",
    "floor_light": "#FCFCFB",
    "floor_alternate": "#F5F5F3",
    "floor_grid": "#ECECEA",
    "contact_shadow": "#E8E8E5",
}

IMMUTABLE_PALETTE = MappingProxyType(PALETTE)
IMMUTABLE_ENVIRONMENT = MappingProxyType(ENVIRONMENT)


def hex_to_rgb(value: str) -> Tuple[int, int, int]:
    value = value.strip()
    if value.startswith("#"):
        value = value[1:]
    if len(value) != 6:
        raise ValueError(f"Expected 6 hex digits, got {value!r}")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


RGB = MappingProxyType({name: hex_to_rgb(value) for name, value in PALETTE.items()})
ENV_RGB = MappingProxyType({name: hex_to_rgb(value) for name, value in ENVIRONMENT.items()})
