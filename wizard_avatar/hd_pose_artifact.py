from __future__ import annotations

import hashlib
import json
import struct
import threading
import zlib
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Mapping

from PIL import Image

MAGIC = b"WJPOSE2\0"
RECORD_STRUCT = struct.Struct("<HII")
U32 = struct.Struct("<I")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class PoseRecord:
    pose_id: str
    payload_offset: int
    compressed_size: int
    raw_size: int


def write_pose_artifact(
    destination: Path,
    poses: Mapping[str, Image.Image],
    *,
    profile: Mapping[str, object],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    if not poses:
        raise ValueError("HD pose artifact requires at least one pose")
    ordered = sorted(poses.items())
    width = int(profile["canvas_width"])
    height = int(profile["canvas_height"])
    header = {
        "schema_version": 1,
        "payload_encoding": "rgba8-zlib",
        "profile": dict(profile),
        "provenance": dict(provenance),
        "pose_ids": [pose_id for pose_id, _ in ordered],
    }
    header_bytes = json.dumps(
        header, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        output.write(MAGIC)
        output.write(U32.pack(len(header_bytes)))
        output.write(header_bytes)
        output.write(U32.pack(len(ordered)))
        for pose_id, image in ordered:
            rgba = image.convert("RGBA")
            if rgba.size != (width, height):
                raise ValueError(f"{pose_id} does not match the artifact profile")
            pose_id_bytes = pose_id.encode("utf-8")
            if len(pose_id_bytes) > 65535:
                raise ValueError("pose id is too long")
            raw = rgba.tobytes()
            compressed = zlib.compress(raw, 9)
            output.write(RECORD_STRUCT.pack(len(pose_id_bytes), len(raw), len(compressed)))
            output.write(pose_id_bytes)
            output.write(compressed)
    return {
        "path": str(destination),
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "bytes": destination.stat().st_size,
        "pose_count": len(ordered),
        "pose_ids": header["pose_ids"],
    }


class HDPoseArtifact:
    def __init__(self, path: Path, *, cache_size: int = 4):
        if cache_size < 1:
            raise ValueError("HD pose artifact cache size must be positive")
        self.path = Path(path)
        self.cache_size = cache_size
        self.header: dict[str, object]
        self.records: dict[str, PoseRecord]
        self._cache: OrderedDict[str, bytes] = OrderedDict()
        self._cache_lock = threading.Lock()
        with self.path.open("rb") as source:
            self.header, self.records = self._read_index(source)

    @property
    def canvas_size(self) -> tuple[int, int]:
        profile = self.header["profile"]
        if not isinstance(profile, dict):
            raise ValueError("HD pose artifact profile is invalid")
        return int(profile["canvas_width"]), int(profile["canvas_height"])

    @staticmethod
    def _read_index(source: BinaryIO) -> tuple[dict[str, object], dict[str, PoseRecord]]:
        if source.read(len(MAGIC)) != MAGIC:
            raise ValueError("HD pose artifact magic is invalid")
        header_size_data = source.read(U32.size)
        if len(header_size_data) != U32.size:
            raise ValueError("HD pose artifact header is truncated")
        header_size = U32.unpack(header_size_data)[0]
        header = json.loads(source.read(header_size).decode("utf-8"))
        count_data = source.read(U32.size)
        if len(count_data) != U32.size:
            raise ValueError("HD pose artifact record count is truncated")
        records = {}
        for _ in range(U32.unpack(count_data)[0]):
            record_data = source.read(RECORD_STRUCT.size)
            if len(record_data) != RECORD_STRUCT.size:
                raise ValueError("HD pose artifact record is truncated")
            id_size, raw_size, compressed_size = RECORD_STRUCT.unpack(record_data)
            pose_id = source.read(id_size).decode("utf-8")
            if pose_id in records:
                raise ValueError(f"duplicate HD pose id: {pose_id}")
            payload_offset = source.tell()
            source.seek(compressed_size, 1)
            records[pose_id] = PoseRecord(
                pose_id, payload_offset, compressed_size, raw_size
            )
        return header, records

    def load_rgba(self, pose_id: str) -> bytes:
        with self._cache_lock:
            cached = self._cache.pop(pose_id, None)
            if cached is not None:
                self._cache[pose_id] = cached
                return cached
            record = self.records.get(pose_id)
            if record is None:
                raise KeyError(pose_id)
            with self.path.open("rb") as source:
                source.seek(record.payload_offset)
                compressed = source.read(record.compressed_size)
            raw = zlib.decompress(compressed)
            if len(raw) != record.raw_size:
                raise ValueError(f"HD pose payload size mismatch: {pose_id}")
            expected_size = self.canvas_size[0] * self.canvas_size[1] * 4
            if len(raw) != expected_size:
                raise ValueError(f"HD pose RGBA size mismatch: {pose_id}")
            self._cache[pose_id] = raw
            while len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)
            return raw

    def load_pose(self, pose_id: str) -> Image.Image:
        return Image.frombytes("RGBA", self.canvas_size, self.load_rgba(pose_id))


class HDPoseLibrary:
    def __init__(self, index_path: Path, *, cache_size_per_shard: int = 2):
        self.index_path = Path(index_path)
        self.index = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.artifacts: dict[str, HDPoseArtifact] = {}
        self.pose_shards: dict[str, str] = {}
        self.pose_metadata: dict[str, dict[str, object]] = {}
        for shard in self.index["shards"]:
            path = self.index_path.parent / shard["path"]
            digest = sha256_path(path)
            if digest != shard["sha256"]:
                raise ValueError(f"HD pose shard checksum mismatch: {shard['shard_id']}")
            artifact = HDPoseArtifact(path, cache_size=cache_size_per_shard)
            if artifact.canvas_size != self.canvas_size:
                raise ValueError(f"HD pose shard profile mismatch: {shard['shard_id']}")
            self.artifacts[shard["shard_id"]] = artifact
            for pose_id in shard["pose_ids"]:
                if pose_id in self.pose_shards:
                    raise ValueError(f"duplicate HD library pose id: {pose_id}")
                if pose_id not in artifact.records:
                    raise ValueError(f"HD library index references missing pose: {pose_id}")
                self.pose_shards[pose_id] = shard["shard_id"]
                self.pose_metadata[pose_id] = {
                    "shard_id": shard["shard_id"],
                    "artifact_sha256": shard["sha256"],
                    "approval_state": shard["approval_state"],
                    "runtime_admitted": bool(shard["runtime_admitted"]),
                    "source": shard["source"],
                }
        if len(self.pose_shards) != int(self.index["pose_count"]):
            raise ValueError("HD pose library count does not match its index")

    @property
    def canvas_size(self) -> tuple[int, int]:
        profile = self.index["profile"]
        return int(profile["canvas_width"]), int(profile["canvas_height"])

    @property
    def pose_ids(self) -> tuple[str, ...]:
        return tuple(self.pose_shards)

    def load_rgba(self, pose_id: str) -> bytes:
        shard_id = self.pose_shards.get(pose_id)
        if shard_id is None:
            raise KeyError(pose_id)
        return self.artifacts[shard_id].load_rgba(pose_id)

    def load_pose(self, pose_id: str) -> Image.Image:
        return Image.frombytes("RGBA", self.canvas_size, self.load_rgba(pose_id))


__all__ = [
    "HDPoseArtifact",
    "HDPoseLibrary",
    "MAGIC",
    "PoseRecord",
    "sha256_path",
    "write_pose_artifact",
]
