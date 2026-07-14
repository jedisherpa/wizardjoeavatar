from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, Mapping, Optional, Sequence


_CACHE_TYPE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_SHA256_REF = re.compile(r"^sha256:[0-9a-f]{64}$")


class CacheIdentityError(ValueError):
    pass


@dataclass(frozen=True)
class CacheKey:
    cache_type: str
    version: int
    digest: str
    identity: Mapping[str, object]

    @property
    def storage_key(self) -> str:
        return "{}-v{}-{}".format(
            self.cache_type, self.version, self.digest.split(":", 1)[1]
        )

    def to_mapping(self) -> Dict[str, object]:
        return {
            "cache_type": self.cache_type,
            "version": self.version,
            "digest": self.digest,
            "identity": dict(self.identity),
        }


def canonical_identity_bytes(value: object) -> bytes:
    _validate_identity_value(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_cache_key(
    cache_type: str,
    identity: Mapping[str, object],
    *,
    version: int = 1,
) -> CacheKey:
    if not isinstance(cache_type, str) or _CACHE_TYPE.fullmatch(cache_type) is None:
        raise CacheIdentityError("cache_type is invalid")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise CacheIdentityError("cache version must be a positive integer")
    if not isinstance(identity, Mapping):
        raise CacheIdentityError("cache identity must be an object")
    full_identity = {
        "cache_type": cache_type,
        "version": version,
        **dict(identity),
    }
    digest = "sha256:" + hashlib.sha256(
        canonical_identity_bytes(full_identity)
    ).hexdigest()
    return CacheKey(
        cache_type=cache_type,
        version=version,
        digest=digest,
        identity=MappingProxyType(full_identity),
    )


def pcm_cache_key(
    *,
    source_sha256: str,
    ffmpeg_binary_sha256: str,
    ffmpeg_version_sha256: str,
    arguments: Sequence[str],
    sample_rate_hz: int,
    channels: int,
    sample_format: str,
    resampler_config: str,
) -> CacheKey:
    for name, value in (
        ("source_sha256", source_sha256),
        ("ffmpeg_binary_sha256", ffmpeg_binary_sha256),
        ("ffmpeg_version_sha256", ffmpeg_version_sha256),
    ):
        _require_hash(name, value)
    return build_cache_key(
        "pcm",
        {
            "source_sha256": source_sha256,
            "ffmpeg_binary_sha256": ffmpeg_binary_sha256,
            "ffmpeg_version_sha256": ffmpeg_version_sha256,
            "arguments": list(arguments),
            "sample_rate_hz": sample_rate_hz,
            "channels": channels,
            "sample_format": sample_format,
            "resampler_config": resampler_config,
        },
    )


def narrative_cache_key(
    *,
    transcript_sha256: str,
    alignment_sha256: str,
    pipeline_version: str,
    policy_sha256: str,
    seed: int,
) -> CacheKey:
    for name, value in (
        ("transcript_sha256", transcript_sha256),
        ("alignment_sha256", alignment_sha256),
        ("policy_sha256", policy_sha256),
    ):
        _require_hash(name, value)
    return build_cache_key(
        "narrative",
        {
            "transcript_sha256": transcript_sha256,
            "alignment_sha256": alignment_sha256,
            "pipeline_version": pipeline_version,
            "policy_sha256": policy_sha256,
            "seed": seed,
        },
    )


def music_cache_key(
    *,
    pcm_sha256: str,
    pipeline_version: str,
    numerical_lock_sha256: str,
    fixed_hop_config: Mapping[str, object],
    algorithm_sha256: str,
    model_sha256: Optional[str],
    execution_policy: str,
) -> CacheKey:
    for name, value in (
        ("pcm_sha256", pcm_sha256),
        ("numerical_lock_sha256", numerical_lock_sha256),
        ("algorithm_sha256", algorithm_sha256),
    ):
        _require_hash(name, value)
    if model_sha256 is not None:
        _require_hash("model_sha256", model_sha256)
    return build_cache_key(
        "music",
        {
            "pcm_sha256": pcm_sha256,
            "pipeline_version": pipeline_version,
            "numerical_lock_sha256": numerical_lock_sha256,
            "fixed_hop_config": dict(fixed_hop_config),
            "algorithm_sha256": algorithm_sha256,
            "model_sha256": model_sha256,
            "execution_policy": execution_policy,
        },
    )


def _require_hash(name: str, value: str) -> None:
    if not isinstance(value, str) or _SHA256_REF.fullmatch(value) is None:
        raise CacheIdentityError("{} must be a SHA-256 reference".format(name))


def _validate_identity_value(value: object) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _validate_identity_value(item)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CacheIdentityError("cache identity keys must be strings")
            _validate_identity_value(item)
        return
    raise CacheIdentityError(
        "cache identity accepts only null, bool, integer, string, array, and object"
    )


__all__ = [
    "CacheIdentityError",
    "CacheKey",
    "build_cache_key",
    "canonical_identity_bytes",
    "music_cache_key",
    "narrative_cache_key",
    "pcm_cache_key",
]
