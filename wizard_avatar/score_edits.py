"""Strict, immutable Character Director score edits."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple, Union

from .artifact_hashing import CanonicalJSONError, MAX_SAFE_INTEGER, canonical_json_v1, sha256_ref


SCORE_EDITS_SCHEMA_VERSION = 1
MAX_SCORE_EDITS = 256
MAX_SCORE_EDITS_JSON_BYTES = 128 * 1024
SCORE_EDITS_SCHEMA_PATH = (
    Path(__file__).resolve().parent
    / "definitions"
    / "character_director_score_edits_v1.schema.json"
)

HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
EDIT_SET_ID_PATTERN = re.compile(r"^edits:[a-z0-9][a-z0-9._:-]{0,121}$")
SEMANTIC_ID_PATTERNS = {
    "semantic_clip_id": re.compile(r"^semantic:clip:[a-z0-9][a-z0-9._-]{0,95}$"),
    "semantic_pose_id": re.compile(r"^semantic:pose:[a-z0-9][a-z0-9._-]{0,95}$"),
    "semantic_action_id": re.compile(r"^semantic:action:[a-z0-9][a-z0-9._-]{0,95}$"),
    "semantic_expression_id": re.compile(
        r"^semantic:expression:[a-z0-9][a-z0-9._-]{0,95}$"
    ),
    "semantic_gaze_id": re.compile(r"^semantic:gaze:[a-z0-9][a-z0-9._-]{0,95}$"),
}
EDIT_TYPES = frozenset(
    ("timing_offset_ms", "duration_ms", "intensity_milli")
    + tuple(SEMANTIC_ID_PATTERNS)
)
ACTOR_KINDS = frozenset(("human", "system", "migration"))

_ROOT_CONTENT_FIELDS = (
    "schema_version",
    "edit_set_id",
    "revision",
    "character_id",
    "package_digest",
    "base_score_sha256",
    "parent_edit_set_sha256",
    "actor",
    "operations",
)
_ROOT_FIELDS = _ROOT_CONTENT_FIELDS + ("edit_set_sha256",)
_OPERATION_FIELDS = (
    "operation_id",
    "cue_id",
    "edit_type",
    "expected_value_sha256",
    "value",
    "reason_code",
)
_PRIVATE_VALUE_PATTERNS = (
    re.compile(r"(?i)^bearer(?:\s|:|_)"),
    re.compile(r"(?i)^basic(?:\s|:|_)"),
    re.compile(r"(?i)^(?:sk|xox[baprs])[-_][a-z0-9]"),
    re.compile(r"(?i)^gh[opusr]_[a-z0-9]"),
    re.compile(r"(?i)^-----begin(?:\s|_|-)"),
)
_FORBIDDEN_SEMANTIC_LEAF_PREFIXES = (
    "asset_",
    "cell_",
    "frame_",
    "node_",
    "pixel_",
    "raw_",
    "render_",
    "renderer_",
    "rgba_",
    "sprite_",
)


class ScoreEditsValidationError(ValueError):
    """Stable, path-addressed failure at the score-edit boundary."""

    def __init__(self, code: str, message: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        super().__init__(message)


def _fail(code: str, message: str, path: str) -> ScoreEditsValidationError:
    return ScoreEditsValidationError(code, message, path)


def _reject_duplicate_keys(pairs: Sequence[Tuple[str, object]]) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _fail("duplicate_json_key", "duplicate JSON object key", "$")
        result[key] = value
    return result


def _reject_float(value: str) -> object:
    raise _fail("non_integer_identity_value", "floating-point JSON values are forbidden", "$")


def _reject_constant(value: str) -> object:
    raise _fail("invalid_type", "non-finite JSON values are forbidden", "$")


def _parse_json(source: Union[str, bytes]) -> Mapping[str, object]:
    raw = source.encode("utf-8") if isinstance(source, str) else bytes(source)
    if len(raw) > MAX_SCORE_EDITS_JSON_BYTES:
        raise _fail("artifact_too_large", "score edits JSON exceeds the size limit", "$")
    try:
        decoded = raw.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except ScoreEditsValidationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _fail("invalid_json", "score edits must be valid UTF-8 JSON", "$") from exc
    return _mapping(value, "$")


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _fail("invalid_type", "expected an object", path)
    return value


def _exact(value: Mapping[str, object], fields: Sequence[str], path: str) -> None:
    expected = set(fields)
    actual = set(value)
    if any(type(key) is not str for key in value):
        raise _fail("invalid_type", "object keys must be strings", path)
    missing = sorted(expected - actual)
    if missing:
        raise _fail("missing_field", "required field is missing", path)
    unknown = sorted(actual - expected)
    if unknown:
        raise _fail("unknown_field", "unknown field is forbidden", path)


def _check_json_value(value: object, path: str = "$") -> None:
    if value is None or type(value) in (str, bool):
        if type(value) is str:
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise _fail("invalid_type", "text must be valid UTF-8", path) from exc
        return
    if type(value) is int:
        if value < -MAX_SAFE_INTEGER or value > MAX_SAFE_INTEGER:
            raise _fail("invalid_type", "integer exceeds the canonical range", path)
        return
    if isinstance(value, float):
        raise _fail("non_integer_identity_value", "floating-point values are forbidden", path)
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _check_json_value(item, "{}[{}]".format(path, index))
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is not str:
                raise _fail("invalid_type", "object keys must be strings", path)
            _check_json_value(item, "{}.{}".format(path, key))
        return
    raise _fail("invalid_type", "unsupported JSON value type", path)


def _reject_private_content(value: object, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_private_content(item, "{}.{}".format(path, key))
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_private_content(item, "{}[{}]".format(path, index))
        return
    if isinstance(value, str) and any(pattern.search(value) for pattern in _PRIVATE_VALUE_PATTERNS):
        raise _fail("private_content", "private values are forbidden in score edits", path)


def _id(value: object, path: str) -> str:
    if type(value) is not str or ID_PATTERN.fullmatch(value) is None:
        raise _fail("invalid_id", "expected a stable identifier", path)
    return value


def _hash(value: object, path: str) -> str:
    if type(value) is not str or HASH_PATTERN.fullmatch(value) is None:
        raise _fail("invalid_hash", "expected a lowercase SHA-256 reference", path)
    return value


def _integer(value: object, minimum: int, maximum: int, path: str) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise _fail("invalid_type", "expected a bounded integer", path)
    return value


def _semantic_id(edit_type: str, value: object, path: str) -> str:
    pattern = SEMANTIC_ID_PATTERNS[edit_type]
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise _fail("invalid_semantic_id", "expected a category-bound semantic identifier", path)
    leaf = value.rsplit(":", 1)[-1]
    if leaf.startswith(_FORBIDDEN_SEMANTIC_LEAF_PREFIXES):
        raise _fail("raw_render_identifier", "renderer-level identifiers are forbidden", path)
    return value


@dataclass(frozen=True)
class ScoreEditActorV1:
    kind: str
    actor_id: str

    @classmethod
    def from_mapping(cls, raw: object) -> "ScoreEditActorV1":
        value = _mapping(raw, "$.actor")
        _exact(value, ("kind", "actor_id"), "$.actor")
        kind = value["kind"]
        if type(kind) is not str or kind not in ACTOR_KINDS:
            raise _fail("invalid_enum", "unsupported actor kind", "$.actor.kind")
        return cls(kind, _id(value["actor_id"], "$.actor.actor_id"))

    def to_dict(self) -> Dict[str, object]:
        return {"kind": self.kind, "actor_id": self.actor_id}


@dataclass(frozen=True)
class ScoreEditOperationV1:
    operation_id: str
    cue_id: str
    edit_type: str
    expected_value_sha256: str
    value: Union[int, str]
    reason_code: str

    @classmethod
    def from_mapping(cls, raw: object, index: int) -> "ScoreEditOperationV1":
        path = "$.operations[{}]".format(index)
        operation = _mapping(raw, path)
        _exact(operation, _OPERATION_FIELDS, path)
        edit_type = operation["edit_type"]
        if type(edit_type) is not str or edit_type not in EDIT_TYPES:
            raise _fail("unsafe_edit_type", "unsupported score edit type", path + ".edit_type")
        raw_value = operation["value"]
        if edit_type == "timing_offset_ms":
            value: Union[int, str] = _integer(raw_value, -3600000, 3600000, path + ".value")
        elif edit_type == "duration_ms":
            value = _integer(raw_value, 1, 86400000, path + ".value")
        elif edit_type == "intensity_milli":
            value = _integer(raw_value, 0, 1000, path + ".value")
        else:
            value = _semantic_id(edit_type, raw_value, path + ".value")
        return cls(
            _id(operation["operation_id"], path + ".operation_id"),
            _id(operation["cue_id"], path + ".cue_id"),
            edit_type,
            _hash(operation["expected_value_sha256"], path + ".expected_value_sha256"),
            value,
            _id(operation["reason_code"], path + ".reason_code"),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "cue_id": self.cue_id,
            "edit_type": self.edit_type,
            "expected_value_sha256": self.expected_value_sha256,
            "value": self.value,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class ScoreEditsV1:
    schema_version: int
    edit_set_id: str
    revision: int
    character_id: str
    package_digest: str
    base_score_sha256: str
    parent_edit_set_sha256: Optional[str]
    actor: ScoreEditActorV1
    operations: Tuple[ScoreEditOperationV1, ...]
    edit_set_sha256: str

    @classmethod
    def build(cls, raw: Mapping[str, object]) -> "ScoreEditsV1":
        """Validate unhashed content, add its canonical hash, and freeze it."""

        value = _mapping(raw, "$")
        _exact(value, _ROOT_CONTENT_FIELDS, "$")
        _check_json_value(value)
        _reject_private_content(value)
        try:
            digest = sha256_ref(canonical_json_v1(value))
        except CanonicalJSONError as exc:
            raise _fail("noncanonical_value", "score edits cannot be canonicalized", "$") from exc
        complete = dict(value)
        complete["edit_set_sha256"] = digest
        return cls.from_mapping(complete)

    @classmethod
    def from_json(cls, source: Union[str, bytes]) -> "ScoreEditsV1":
        return cls.from_mapping(_parse_json(source))

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "ScoreEditsV1":
        value = _mapping(raw, "$")
        _exact(value, _ROOT_FIELDS, "$")
        _check_json_value(value)
        _reject_private_content(value)
        if type(value["schema_version"]) is not int:
            raise _fail("invalid_type", "schema version must be an integer", "$.schema_version")
        if value["schema_version"] != SCORE_EDITS_SCHEMA_VERSION:
            raise _fail(
                "schema_version_unsupported",
                "score edits schema must be version 1",
                "$.schema_version",
            )
        edit_set_id = value["edit_set_id"]
        if type(edit_set_id) is not str or EDIT_SET_ID_PATTERN.fullmatch(edit_set_id) is None:
            raise _fail("invalid_id", "invalid edit set identifier", "$.edit_set_id")
        operations_raw = value["operations"]
        if not isinstance(operations_raw, (list, tuple)):
            raise _fail("invalid_type", "operations must be an array", "$.operations")
        if not 1 <= len(operations_raw) <= MAX_SCORE_EDITS:
            raise _fail(
                "edit_count_out_of_bounds",
                "score edit count is out of bounds",
                "$.operations",
            )
        operations = tuple(
            ScoreEditOperationV1.from_mapping(operation, index)
            for index, operation in enumerate(operations_raw)
        )
        operation_ids = [operation.operation_id for operation in operations]
        if len(set(operation_ids)) != len(operation_ids):
            raise _fail("duplicate_id", "operation identifiers must be unique", "$.operations")
        targets = [(operation.cue_id, operation.edit_type) for operation in operations]
        if len(set(targets)) != len(targets):
            raise _fail(
                "duplicate_edit_target",
                "one edit set cannot assign the same cue field twice",
                "$.operations",
            )
        parent = value["parent_edit_set_sha256"]
        parent_hash = None if parent is None else _hash(parent, "$.parent_edit_set_sha256")
        instance = cls(
            SCORE_EDITS_SCHEMA_VERSION,
            edit_set_id,
            _integer(value["revision"], 1, MAX_SAFE_INTEGER, "$.revision"),
            _id(value["character_id"], "$.character_id"),
            _hash(value["package_digest"], "$.package_digest"),
            _hash(value["base_score_sha256"], "$.base_score_sha256"),
            parent_hash,
            ScoreEditActorV1.from_mapping(value["actor"]),
            operations,
            _hash(value["edit_set_sha256"], "$.edit_set_sha256"),
        )
        if instance.edit_set_sha256 != instance.content_sha256():
            raise _fail(
                "hash_mismatch",
                "edit set SHA-256 does not match canonical content",
                "$.edit_set_sha256",
            )
        return instance

    def content_dict(self) -> Dict[str, object]:
        value = self.to_dict()
        value.pop("edit_set_sha256")
        return value

    def content_sha256(self) -> str:
        return sha256_ref(canonical_json_v1(self.content_dict()))

    def canonical_json(self) -> bytes:
        return canonical_json_v1(self.to_dict())

    def validate_binding(
        self,
        *,
        character_id: str,
        package_digest: str,
        base_score_sha256: str,
    ) -> None:
        """Reject application after any authority-bearing binding changes."""

        expected = (character_id, package_digest, base_score_sha256)
        actual = (self.character_id, self.package_digest, self.base_score_sha256)
        if actual != expected:
            raise _fail("stale_binding", "score edit binding no longer matches", "$")

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "edit_set_id": self.edit_set_id,
            "revision": self.revision,
            "character_id": self.character_id,
            "package_digest": self.package_digest,
            "base_score_sha256": self.base_score_sha256,
            "parent_edit_set_sha256": self.parent_edit_set_sha256,
            "actor": self.actor.to_dict(),
            "operations": [operation.to_dict() for operation in self.operations],
            "edit_set_sha256": self.edit_set_sha256,
        }


__all__ = [
    "EDIT_TYPES",
    "MAX_SCORE_EDITS",
    "MAX_SCORE_EDITS_JSON_BYTES",
    "SCORE_EDITS_SCHEMA_PATH",
    "SCORE_EDITS_SCHEMA_VERSION",
    "ScoreEditActorV1",
    "ScoreEditOperationV1",
    "ScoreEditsV1",
    "ScoreEditsValidationError",
]
