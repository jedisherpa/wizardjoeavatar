from __future__ import annotations


FNV1A_32_OFFSET = 0x811C9DC5
FNV1A_32_PRIME = 0x01000193


def frame_hash(frame: bytes) -> str:
    value = FNV1A_32_OFFSET
    for byte in frame:
        value ^= byte
        value = (value * FNV1A_32_PRIME) & 0xFFFFFFFF
    return f"fnv1a32:{value:08x}"
