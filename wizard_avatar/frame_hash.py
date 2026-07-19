from __future__ import annotations

from functools import lru_cache


FNV1A_32_OFFSET = 0x811C9DC5
FNV1A_32_PRIME = 0x01000193


@lru_cache(maxsize=64)
def frame_hash(frame: bytes) -> str:
    """Return the protocol FNV digest, reusing repeated presentation frames.

    Held animation cels are intentionally common. The bytes key preserves the
    exact protocol result while avoiding another Python byte loop for an
    identical frame.
    """

    value = FNV1A_32_OFFSET
    for byte in frame:
        value ^= byte
        value = (value * FNV1A_32_PRIME) & 0xFFFFFFFF
    return f"fnv1a32:{value:08x}"
