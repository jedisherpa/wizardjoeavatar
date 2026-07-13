from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from typing import Optional, Tuple


TAG_RAW = 0
TAG_ZLIB = 1
TAG_DELTA = 2
TAG_RLE_FULL = 3
KEYFRAME_INTERVAL = 48
CELL_BYTES = 4


@dataclass
class EncodedFrame:
    message: bytes
    shown_frame: bytes
    tag: int
    changed_cells: int
    encoded_size: int
    raw_size: int
    is_keyframe: bool


def _rle_encode(frame: bytes, cell_bytes: int = CELL_BYTES) -> bytes:
    if not frame:
        return b""
    out = bytearray()
    prev = frame[0:cell_bytes]
    count = 0
    for i in range(0, len(frame), cell_bytes):
        cell = frame[i : i + cell_bytes]
        if cell == prev and count < 65535:
            count += 1
            continue
        out.extend(struct.pack("<H", count))
        out.extend(prev)
        prev = cell
        count = 1
    out.extend(struct.pack("<H", count))
    out.extend(prev)
    return bytes(out)


def _full_frame(frame: bytes, frame_index: int, cell_bytes: int = CELL_BYTES) -> EncodedFrame:
    z_raw = zlib.compress(frame, 3)
    z_rle = zlib.compress(_rle_encode(frame, cell_bytes), 3)
    candidates = [
        (TAG_RAW, frame),
        (TAG_ZLIB, z_raw),
        (TAG_RLE_FULL, z_rle),
    ]
    tag, payload = min(candidates, key=lambda item: len(item[1]))
    message = struct.pack(">IB", frame_index, tag) + payload
    return EncodedFrame(message, frame, tag, len(frame) // cell_bytes, len(message), len(frame), True)


def encode_keyframe(frame: bytes, frame_index: int, cell_bytes: int = CELL_BYTES) -> EncodedFrame:
    return _full_frame(frame, frame_index, cell_bytes)


def encode_frame(
    frame: bytes,
    prev: Optional[bytes],
    frame_index: int,
    cell_bytes: int = CELL_BYTES,
) -> EncodedFrame:
    keyframe = prev is None or len(prev) != len(frame) or frame_index % KEYFRAME_INTERVAL == 0
    if keyframe:
        return _full_frame(frame, frame_index, cell_bytes)

    changed_indices = []
    changed_values = bytearray()
    for cell_index, offset in enumerate(range(0, len(frame), cell_bytes)):
        cell = frame[offset : offset + cell_bytes]
        if cell != prev[offset : offset + cell_bytes]:
            changed_indices.append(cell_index)
            changed_values.extend(cell)

    frac = len(changed_indices) / max(1, len(frame) // cell_bytes)
    candidates = []
    if frac < 0.60:
        body = bytearray()
        for index in changed_indices:
            body.extend(struct.pack("<I", index))
        body.extend(changed_values)
        candidates.append((TAG_DELTA, zlib.compress(bytes(body), 3), _apply_delta(prev, changed_indices, changed_values, cell_bytes)))
    if frac >= 0.10 or not candidates:
        z_raw = zlib.compress(frame, 3)
        z_rle = zlib.compress(_rle_encode(frame, cell_bytes), 3)
        if len(z_rle) < len(z_raw):
            candidates.append((TAG_RLE_FULL, z_rle, frame))
        else:
            candidates.append((TAG_ZLIB, z_raw, frame))
    tag, payload, shown = min(candidates, key=lambda item: len(item[1]))
    if len(frame) < len(payload):
        tag, payload, shown = TAG_RAW, frame, frame
    message = struct.pack(">IB", frame_index, tag) + payload
    return EncodedFrame(message, shown, tag, len(changed_indices), len(message), len(frame), False)


def _apply_delta(prev: bytes, indices, values: bytes, cell_bytes: int) -> bytes:
    out = bytearray(prev)
    cursor = 0
    for index in indices:
        start = index * cell_bytes
        out[start : start + cell_bytes] = values[cursor : cursor + cell_bytes]
        cursor += cell_bytes
    return bytes(out)


def decode_frame(message: bytes, prev: Optional[bytes], cell_bytes: int = CELL_BYTES) -> Tuple[int, bytes]:
    if len(message) < 5:
        raise ValueError("Adaptive message too short")
    frame_index = struct.unpack(">I", message[:4])[0]
    tag = message[4]
    payload = message[5:]
    if tag == TAG_RAW:
        return frame_index, payload
    if tag == TAG_ZLIB:
        return frame_index, zlib.decompress(payload)
    if tag == TAG_RLE_FULL:
        body = zlib.decompress(payload)
        out = bytearray()
        offset = 0
        while offset < len(body):
            count = struct.unpack("<H", body[offset : offset + 2])[0]
            cell = body[offset + 2 : offset + 2 + cell_bytes]
            out.extend(cell * count)
            offset += 2 + cell_bytes
        return frame_index, bytes(out)
    if tag == TAG_DELTA:
        if prev is None:
            raise ValueError("Delta frame cannot decode without previous frame")
        body = zlib.decompress(payload)
        count = len(body) // (4 + cell_bytes)
        indices = [
            struct.unpack("<I", body[i * 4 : i * 4 + 4])[0]
            for i in range(count)
        ]
        values_offset = count * 4
        values = body[values_offset:]
        return frame_index, _apply_delta(prev, indices, values, cell_bytes)
    raise ValueError(f"Unknown adaptive frame tag: {tag}")
