"""Versioned canonical JSON and content identity helpers for artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Dict, List


MAX_SAFE_INTEGER = (1 << 53) - 1


class CanonicalJSONError(ValueError):
    """Raised when a value cannot be represented by canonical JSON V1."""


def _validate_text(value: str, path: str) -> str:
    for character in value:
        if 0xD800 <= ord(character) <= 0xDFFF:
            raise CanonicalJSONError("{} contains a lone surrogate".format(path))
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CanonicalJSONError("{} is not valid UTF-8 text".format(path)) from exc
    return value


def _normalize(value: object, path: str) -> object:
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if value < -MAX_SAFE_INTEGER or value > MAX_SAFE_INTEGER:
            raise CanonicalJSONError("{} exceeds the JSON safe integer range".format(path))
        return value
    if type(value) is str:
        return _validate_text(value, path)
    if type(value) is list:
        normalized: List[object] = []
        for index, item in enumerate(value):
            normalized.append(_normalize(item, "{}[{}]".format(path, index)))
        return normalized
    if isinstance(value, Mapping):
        normalized_mapping: Dict[str, object] = {}
        for key in value:
            if type(key) is not str:
                raise CanonicalJSONError("{} contains a non-string object key".format(path))
            _validate_text(key, "{} object key".format(path))
        for key in sorted(value.keys()):
            if key in normalized_mapping:
                raise CanonicalJSONError("{} contains duplicate object key {!r}".format(path, key))
            normalized_mapping[key] = _normalize(value[key], "{}.{}".format(path, key))
        return normalized_mapping
    if isinstance(value, float):
        raise CanonicalJSONError("{} contains a floating-point value".format(path))
    raise CanonicalJSONError(
        "{} contains unsupported value type {}".format(path, type(value).__name__)
    )


def canonical_json_v1(value: object) -> bytes:
    """Encode accepted artifact JSON using the frozen canonical V1 rules.

    Objects are ordered by Unicode code point, arrays retain their order, and
    only cross-language-safe JSON integers are accepted. JSON text must be
    parsed with a duplicate-key-rejecting loader before it reaches this API.
    """

    normalized = _normalize(value, "$")
    try:
        encoded = json.dumps(
            normalized,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        return encoded.encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise CanonicalJSONError("value cannot be encoded as canonical JSON V1") from exc


def sha256_ref(data: bytes) -> str:
    """Return a lowercase, algorithm-qualified SHA-256 reference."""

    if type(data) is not bytes:
        raise TypeError("data must be bytes")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def artifact_identity_hash(identity: Mapping[str, object]) -> str:
    """Hash a declared artifact identity object without deleting metadata."""

    if not isinstance(identity, Mapping):
        raise CanonicalJSONError("artifact identity must be an object")
    return sha256_ref(canonical_json_v1(identity))


__all__ = [
    "MAX_SAFE_INTEGER",
    "CanonicalJSONError",
    "artifact_identity_hash",
    "canonical_json_v1",
    "sha256_ref",
]
