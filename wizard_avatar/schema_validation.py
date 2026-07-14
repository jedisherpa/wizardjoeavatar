"""Strict standard-library validation for audiobook artifact contracts."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .artifact_hashing import MAX_SAFE_INTEGER, canonical_json_v1


DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
DEFINITIONS_DIR = Path(__file__).resolve().parent / "definitions"

SCHEMA_FILES = {
    "MediaAssetV1": "media_asset_v1.schema.json",
    "TranscriptV1": "transcript_v1.schema.json",
    "AlignmentV1": "alignment_v1.schema.json",
    "NarrativeScoreV1": "narrative_score_v1.schema.json",
    "MusicScoreV1": "music_score_v1.schema.json",
    "PerformanceScoreV1": "performance_score_v1.schema.json",
    "ScoreEditsV1": "score_edits_v1.schema.json",
    "CompiledPerformanceScoreV1": "compiled_performance_score_v1.schema.json",
    "MediaSessionSnapshotV1": "media_session_snapshot_v1.schema.json",
    "MediaSessionAckV1": "media_session_ack_v1.schema.json",
}


class ContractValidationError(ValueError):
    """A stable, path-addressed contract validation failure."""

    def __init__(self, code: str, path: str, message: str) -> None:
        self.code = code
        self.path = path
        self.message = message
        super().__init__("{} at {}: {}".format(code, path, message))


def _error(code: str, path: str, message: str) -> ContractValidationError:
    return ContractValidationError(code, path, message)


def _reject_duplicate_keys(pairs: Sequence[Tuple[str, object]]) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _error("duplicate_json_key", "$", "duplicate object key {!r}".format(key))
        result[key] = value
    return result


def _reject_float(value: str) -> object:
    raise _error(
        "non_integer_identity_value",
        "$",
        "floating-point JSON number {!r} is forbidden".format(value),
    )


def _reject_constant(value: str) -> object:
    raise _error("invalid_type", "$", "non-finite JSON value {!r} is forbidden".format(value))


def _parse_json(text: str, source: str) -> object:
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except ContractValidationError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise _error("invalid_json", "$", "{} is not valid JSON".format(source)) from exc


def _json_equal(left: object, right: object) -> bool:
    return type(left) is type(right) and left == right


def _path(parent: str, key: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return "{}.{}".format(parent, key)
    return "{}[{!r}]".format(parent, key)


def _check_json_value(value: object, path: str = "$") -> None:
    if value is None or type(value) in (str, bool):
        if type(value) is str:
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise _error("invalid_type", path, "string contains a lone surrogate") from exc
        return
    if type(value) is int:
        if value < -MAX_SAFE_INTEGER or value > MAX_SAFE_INTEGER:
            raise _error("invalid_type", path, "integer exceeds the JSON safe range")
        return
    if isinstance(value, float):
        raise _error("non_integer_identity_value", path, "floating-point values are forbidden")
    if type(value) is list:
        for index, item in enumerate(value):
            _check_json_value(item, "{}[{}]".format(path, index))
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise _error("invalid_type", path, "object keys must be strings")
            _check_json_value(key, "{} object key".format(path))
            _check_json_value(item, _path(path, key))
        return
    raise _error("invalid_type", path, "unsupported JSON value type {}".format(type(value).__name__))


def _matches_type(value: object, expected: str) -> bool:
    if expected == "object":
        return type(value) is dict
    if expected == "array":
        return type(value) is list
    if expected == "string":
        return type(value) is str
    if expected == "integer":
        return type(value) is int
    if expected == "boolean":
        return type(value) is bool
    if expected == "null":
        return value is None
    return False


def _pattern_code(path: str, pattern: str) -> str:
    leaf = path.rsplit(".", 1)[-1]
    if "sha256" in leaf or leaf.endswith("digest") or "sha256:" in pattern:
        return "invalid_hash"
    if (
        leaf.endswith("_id")
        or leaf in {"intent", "mapping_id", "clip_id", "node_id"}
        or pattern == "^[a-z0-9][a-z0-9._:-]{0,127}$"
    ):
        return "invalid_id"
    return "invalid_format"


def _resolve_ref(root: Mapping[str, object], reference: str) -> Mapping[str, object]:
    if not reference.startswith("#/"):
        raise _error("invalid_schema", "$", "only local schema references are supported")
    current: object = root
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if type(current) is not dict or token not in current:
            raise _error("invalid_schema", "$", "unresolved schema reference {}".format(reference))
        current = current[token]
    if type(current) is not dict:
        raise _error("invalid_schema", "$", "schema reference does not name an object")
    return current


def _validate_schema_node(
    value: object,
    schema: Mapping[str, object],
    root: Mapping[str, object],
    path: str,
) -> None:
    reference = schema.get("$ref")
    if reference is not None:
        if type(reference) is not str:
            raise _error("invalid_schema", "$", "$ref must be a string")
        _validate_schema_node(value, _resolve_ref(root, reference), root, path)
        return

    one_of = schema.get("oneOf")
    if one_of is not None:
        if type(one_of) is not list:
            raise _error("invalid_schema", "$", "oneOf must be an array")
        matches = 0
        failures = []  # type: List[ContractValidationError]
        for candidate in one_of:
            try:
                _validate_schema_node(value, candidate, root, path)
            except ContractValidationError as exc:
                failures.append(exc)
                continue
            matches += 1
        if matches == 0:
            specific = next(
                (failure for failure in reversed(failures) if failure.code != "invalid_type"),
                None,
            )
            if specific is not None:
                raise specific
            raise _error("invalid_type", path, "value must match exactly one allowed shape")
        if matches != 1:
            raise _error("invalid_type", path, "value must match exactly one allowed shape")
        return

    any_of = schema.get("anyOf")
    if any_of is not None:
        for candidate in any_of:
            try:
                _validate_schema_node(value, candidate, root, path)
                break
            except ContractValidationError:
                continue
        else:
            raise _error("invalid_type", path, "value does not match an allowed shape")

    expected = schema.get("type")
    if expected is not None:
        allowed_types = expected if type(expected) is list else [expected]
        if not all(type(item) is str for item in allowed_types):
            raise _error("invalid_schema", "$", "schema type must contain strings")
        if not any(_matches_type(value, item) for item in allowed_types):
            raise _error("invalid_type", path, "expected {}".format(" or ".join(allowed_types)))

    if "const" in schema and not _json_equal(value, schema["const"]):
        if path == "$.schema_version" and type(value) is not type(schema["const"]):
            code = "invalid_type"
        else:
            code = "schema_version_unsupported" if path == "$.schema_version" else "invalid_enum"
        raise _error(code, path, "must equal {!r}".format(schema["const"]))
    if "enum" in schema and not any(_json_equal(value, item) for item in schema["enum"]):
        raise _error("invalid_enum", path, "value is not in the allowed enum")

    if type(value) is dict:
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        if type(required) is not list or type(properties) is not dict:
            raise _error("invalid_schema", "$", "object schema has invalid properties/required")
        missing = sorted(set(required) - set(value))
        if missing:
            raise _error("missing_field", path, "missing required fields: {}".format(", ".join(missing)))
        unknown = sorted(set(value) - set(properties))
        if unknown and schema.get("additionalProperties") is False:
            raise _error("unknown_field", path, "unknown fields: {}".format(", ".join(unknown)))
        for key, item in value.items():
            if key in properties:
                _validate_schema_node(item, properties[key], root, _path(path, key))
        if "minProperties" in schema and len(value) < schema["minProperties"]:
            raise _error("invalid_type", path, "object has too few properties")

    if type(value) is list:
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise _error("invalid_type", path, "array has too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise _error("invalid_type", path, "array has too many items")
        if schema.get("uniqueItems"):
            seen = set()
            for index, item in enumerate(value):
                marker = canonical_json_v1(item)
                if marker in seen:
                    raise _error("duplicate_id", "{}[{}]".format(path, index), "duplicate array item")
                seen.add(marker)
        items = schema.get("items")
        if items is not None:
            for index, item in enumerate(value):
                _validate_schema_node(item, items, root, "{}[{}]".format(path, index))

    if type(value) is str:
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise _error("invalid_type", path, "string is too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise _error("invalid_type", path, "string is too long")
        pattern = schema.get("pattern")
        if pattern is not None and re.search(pattern, value) is None:
            raise _error(_pattern_code(path, pattern), path, "string does not match the required pattern")

    if type(value) is int:
        if "minimum" in schema and value < schema["minimum"]:
            raise _error("time_out_of_bounds" if path.endswith(("_ms", "_sample", "_samples")) else "invalid_type", path, "value is below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise _error("time_out_of_bounds" if path.endswith(("_ms", "_sample", "_samples")) else "invalid_type", path, "value exceeds maximum")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            raise _error("range_invalid", path, "value must exceed exclusive minimum")


def _walk_objects(value: object, path: str = "$") -> Iterable[Tuple[str, Mapping[str, object]]]:
    if type(value) is dict:
        yield path, value
        for key, item in value.items():
            yield from _walk_objects(item, _path(path, key))
    elif type(value) is list:
        for index, item in enumerate(value):
            yield from _walk_objects(item, "{}[{}]".format(path, index))


def _validate_ranges(value: Mapping[str, object]) -> None:
    for path, item in _walk_objects(value):
        for start_key, end_key in (("start_ms", "end_ms"), ("start_sample", "end_sample")):
            if start_key in item and end_key in item and item[start_key] >= item[end_key]:
                raise _error("range_invalid", path, "{} must be less than {}".format(start_key, end_key))
        if {"start_ms", "apex_ms", "end_ms"}.issubset(item):
            if not item["start_ms"] <= item["apex_ms"] < item["end_ms"]:
                raise _error("range_invalid", path, "apex_ms must lie in the half-open range")


def _require_unique(items: Sequence[object], key: str, path: str) -> None:
    seen = set()
    for index, item in enumerate(items):
        if type(item) is not dict or key not in item:
            continue
        identifier = item[key]
        if identifier in seen:
            raise _error("duplicate_id", "{}[{}].{}".format(path, index, key), "duplicate identifier")
        seen.add(identifier)


def _validate_media_asset(value: Mapping[str, object]) -> None:
    source_hash = value["identity"]["source_sha256"]
    _validate_media_hash_binding(value["media_id"], source_hash, "$.media_id")


def _validate_media_hash_binding(media_id: object, media_hash: object, path: str) -> None:
    if media_id != "media:sha256:" + media_hash.split(":", 1)[1]:
        raise _error(
            "hash_mismatch",
            path,
            "media_id must derive from the bound media SHA-256",
        )


def _validate_transcript(value: Mapping[str, object]) -> None:
    chapters = value["chapters"]
    blocks = value["blocks"]
    _require_unique(chapters, "chapter_id", "$.chapters")
    _require_unique(blocks, "block_id", "$.blocks")
    chapter_ids = {chapter["chapter_id"] for chapter in chapters}
    block_by_id = {block["block_id"]: block for block in blocks}
    referenced = []
    for chapter in chapters:
        for block_id in chapter["block_ids"]:
            if block_id not in block_by_id:
                raise _error("dangling_reference", "$.chapters", "unknown block_id {!r}".format(block_id))
            if block_by_id[block_id]["chapter_id"] != chapter["chapter_id"]:
                raise _error("dangling_reference", "$.chapters", "block belongs to another chapter")
            referenced.append(block_id)
    if len(referenced) != len(set(referenced)) or set(referenced) != set(block_by_id):
        raise _error("dangling_reference", "$.chapters", "every block must be referenced exactly once")
    for block in blocks:
        if block["chapter_id"] not in chapter_ids:
            raise _error("dangling_reference", "$.blocks", "unknown chapter_id")


def _validate_alignment(value: Mapping[str, object]) -> None:
    _validate_media_hash_binding(value["media_id"], value["media_sha256"], "$.media_id")
    _require_unique(value["units"], "unit_id", "$.units")
    _require_unique(value["silences"], "silence_id", "$.silences")
    duration = value["duration_ms"]
    previous_word_end = 0
    for index, unit in enumerate(value["units"]):
        if unit["end_ms"] > duration:
            raise _error("time_out_of_bounds", "$.units[{}].end_ms".format(index), "unit exceeds duration")
        if unit["kind"] == "word" and unit["start_ms"] < previous_word_end:
            raise _error("exclusive_overlap", "$.units[{}]".format(index), "lexical units overlap or are not monotonic")
        if unit["kind"] == "word":
            previous_word_end = unit["end_ms"]
    for index, silence in enumerate(value["silences"]):
        if silence["end_ms"] > duration:
            raise _error("time_out_of_bounds", "$.silences[{}].end_ms".format(index), "silence exceeds duration")


def _validate_narrative(value: Mapping[str, object]) -> None:
    _require_unique(value["chapter_envelopes"], "chapter_id", "$.chapter_envelopes")
    _require_unique(value["beats"], "beat_id", "$.beats")
    duration = value["duration_ms"]
    for index, envelope in enumerate(value["chapter_envelopes"]):
        if envelope["end_ms"] > duration:
            raise _error(
                "time_out_of_bounds",
                "$.chapter_envelopes[{}].end_ms".format(index),
                "chapter envelope exceeds duration",
            )
    for index, beat in enumerate(value["beats"]):
        if beat["end_ms"] > duration:
            raise _error("time_out_of_bounds", "$.beats[{}].end_ms".format(index), "beat exceeds duration")


def _validate_music(value: Mapping[str, object]) -> None:
    _validate_media_hash_binding(value["media_id"], value["media_sha256"], "$.media_id")
    _require_unique(value["sections"], "section_id", "$.sections")
    duration = value["duration_samples"]
    for collection in ("beats", "downbeats", "onsets"):
        samples = [item["sample"] for item in value[collection]]
        if samples != sorted(samples) or len(samples) != len(set(samples)):
            raise _error("range_invalid", "$.{}".format(collection), "sample positions must be sorted and unique")
        if any(sample > duration for sample in samples):
            raise _error("time_out_of_bounds", "$.{}".format(collection), "sample exceeds duration")
    for collection in ("tempo_regions", "meter_regions", "sections"):
        previous_end = 0
        for index, region in enumerate(value[collection]):
            if region["end_sample"] > duration:
                raise _error("time_out_of_bounds", "$.{}[{}]".format(collection, index), "region exceeds duration")
            if region["start_sample"] < previous_end:
                raise _error("exclusive_overlap", "$.{}[{}]".format(collection, index), "regions overlap")
            previous_end = region["end_sample"]


def _validate_cue(cue: Mapping[str, object], path: str, duration: Optional[int]) -> None:
    if duration is not None and cue["end_ms"] > duration:
        raise _error("time_out_of_bounds", path + ".end_ms", "cue exceeds media duration")
    phases = cue.get("phase_ranges")
    if phases is not None:
        ordered = [name for name in ("anticipation", "stroke", "hold", "release", "settle") if name in phases]
        previous_end = cue["start_ms"]
        for name in ordered:
            start, end = phases[name]
            if start != previous_end or end <= start or start < cue["start_ms"] or end > cue["end_ms"]:
                raise _error("range_invalid", path + ".phase_ranges", "phase ranges must be contiguous and inside the cue")
            previous_end = end
        if ordered and previous_end != cue["end_ms"]:
            raise _error("range_invalid", path + ".phase_ranges", "phase ranges must cover the cue")


def _validate_tracks(tracks: Sequence[object], duration: Optional[int], path: str = "$.tracks") -> None:
    _require_unique(tracks, "track_id", path)
    cue_ids = set()
    for track_index, track in enumerate(tracks):
        previous_end = 0
        for cue_index, cue in enumerate(track["cues"]):
            cue_path = "{}[{}].cues[{}]".format(path, track_index, cue_index)
            if cue["cue_id"] in cue_ids:
                raise _error("duplicate_id", cue_path + ".cue_id", "cue IDs are score-global")
            cue_ids.add(cue["cue_id"])
            _validate_cue(cue, cue_path, duration)
            if track["exclusive"] and cue["start_ms"] < previous_end:
                raise _error("exclusive_overlap", cue_path, "exclusive track cues overlap")
            previous_end = max(previous_end, cue["end_ms"])


def _validate_performance(value: Mapping[str, object]) -> None:
    _validate_media_hash_binding(
        value["media"]["media_id"],
        value["media"]["media_sha256"],
        "$.media.media_id",
    )
    _validate_tracks(value["tracks"], value["media"]["duration_ms"])


def _validate_score_edits(value: Mapping[str, object]) -> None:
    _require_unique(value["operations"], "operation_id", "$.operations")
    for index, operation in enumerate(value["operations"]):
        path = "$.operations[{}]".format(index)
        if operation["op"] == "add_cue":
            if type(operation["value"]) is not dict:
                raise _error("invalid_type", path + ".value", "add_cue requires a complete cue object")
            _validate_cue(operation["value"], path + ".value", None)
        elif operation["op"] == "replace":
            if operation["field"] is None or operation["old_value_sha256"] is None:
                raise _error("missing_field", path, "replace requires field and old_value_sha256")
        elif operation["value"] is not None:
            raise _error("invalid_type", path + ".value", "this operation requires a null value")


def _validate_compiled(value: Mapping[str, object]) -> None:
    _validate_tracks(value["tracks"], None)
    _require_unique(value["checkpoints"], "checkpoint_id", "$.checkpoints")
    _require_unique(value["fallback_records"], "fallback_id", "$.fallback_records")
    times = [checkpoint["media_time_ms"] for checkpoint in value["checkpoints"]]
    if times != sorted(times) or len(times) != len(set(times)):
        raise _error("range_invalid", "$.checkpoints", "checkpoint times must be sorted and unique")


def _validate_snapshot(value: Mapping[str, object]) -> None:
    _validate_media_hash_binding(
        value["media"]["media_id"],
        value["media"]["media_sha256"],
        "$.media.media_id",
    )
    if value["playback"]["position_ms"] > value["media"]["duration_ms"]:
        raise _error("position_out_of_bounds", "$.playback.position_ms", "position exceeds duration")
    channels = value["performance"]["disabled_channels"]
    if channels != sorted(channels) or len(channels) != len(set(channels)):
        raise _error("invalid_enum", "$.performance.disabled_channels", "channels must be sorted and unique")


def _validate_ack(value: Mapping[str, object]) -> None:
    rates = value["capabilities"]["supported_rate_milli"]
    if rates != sorted(rates) or len(rates) != len(set(rates)):
        raise _error("invalid_enum", "$.capabilities.supported_rate_milli", "rates must be sorted and unique")
    if value["disposition"] in {"rejected", "resync_required"} and value["error_code"] is None:
        raise _error("missing_field", "$.error_code", "error_code is required for this disposition")


SEMANTIC_VALIDATORS = {
    "MediaAssetV1": _validate_media_asset,
    "TranscriptV1": _validate_transcript,
    "AlignmentV1": _validate_alignment,
    "NarrativeScoreV1": _validate_narrative,
    "MusicScoreV1": _validate_music,
    "PerformanceScoreV1": _validate_performance,
    "ScoreEditsV1": _validate_score_edits,
    "CompiledPerformanceScoreV1": _validate_compiled,
    "MediaSessionSnapshotV1": _validate_snapshot,
    "MediaSessionAckV1": _validate_ack,
}


def _lookup_binding(value: Mapping[str, object], dotted_path: str) -> object:
    current: object = value
    for component in dotted_path.split("."):
        if type(current) is not dict or component not in current:
            raise _error("stale_binding", "$", "binding path {!r} is absent".format(dotted_path))
        current = current[component]
    return current


class SchemaRegistry:
    """Load and apply the frozen audiobook JSON schemas by contract name."""

    def __init__(self, schema_dir: Path = DEFINITIONS_DIR) -> None:
        self.schema_dir = Path(schema_dir)
        self._schemas: Dict[str, Mapping[str, object]] = {}

    @property
    def names(self) -> Tuple[str, ...]:
        return tuple(SCHEMA_FILES)

    def _canonical_name(self, name: str) -> str:
        for contract_name, filename in SCHEMA_FILES.items():
            if name in {contract_name, filename, filename.replace(".schema.json", "")}:
                return contract_name
        raise _error("schema_version_unsupported", "$.schema_version", "unknown contract schema {!r}".format(name))

    def schema(self, name: str) -> Mapping[str, object]:
        canonical_name = self._canonical_name(name)
        if canonical_name not in self._schemas:
            path = self.schema_dir / SCHEMA_FILES[canonical_name]
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise _error("invalid_schema", "$", "cannot read {}".format(path)) from exc
            parsed = _parse_json(text, str(path))
            if type(parsed) is not dict or parsed.get("$schema") != DRAFT_2020_12:
                raise _error("invalid_schema", "$", "schema must declare Draft 2020-12")
            self._schemas[canonical_name] = parsed
        return self._schemas[canonical_name]

    def validate(
        self,
        name: str,
        value: object,
        *,
        expected_bindings: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, object]:
        canonical_name = self._canonical_name(name)
        _check_json_value(value)
        schema = self.schema(canonical_name)
        _validate_schema_node(value, schema, schema, "$")
        if type(value) is not dict:
            raise _error("invalid_type", "$", "contract root must be an object")
        _validate_ranges(value)
        SEMANTIC_VALIDATORS[canonical_name](value)
        if expected_bindings:
            for dotted_path, expected in expected_bindings.items():
                actual = _lookup_binding(value, dotted_path)
                if not _json_equal(actual, expected):
                    raise _error(
                        "stale_binding",
                        "$.{}".format(dotted_path),
                        "artifact binding does not match the expected value",
                    )
        return value


def load_and_validate_json(
    source: Union[str, bytes, Path],
    schema_name: str,
    *,
    registry: Optional[SchemaRegistry] = None,
    expected_bindings: Optional[Mapping[str, object]] = None,
) -> Mapping[str, object]:
    """Parse duplicate-safe JSON, reject floats, and validate one contract."""

    if isinstance(source, Path):
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise _error("invalid_json", "$", "cannot read {}".format(source)) from exc
    elif type(source) is bytes:
        try:
            text = source.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _error("invalid_json", "$", "input is not valid UTF-8") from exc
    elif type(source) is str:
        text = source
    else:
        raise _error("invalid_type", "$", "source must be JSON text, bytes, or Path")
    value = _parse_json(text, str(source) if isinstance(source, Path) else "input")
    return (registry or SchemaRegistry()).validate(
        schema_name,
        value,
        expected_bindings=expected_bindings,
    )


__all__ = [
    "DEFINITIONS_DIR",
    "DRAFT_2020_12",
    "SCHEMA_FILES",
    "ContractValidationError",
    "SchemaRegistry",
    "load_and_validate_json",
]
