from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Tuple


FACINGS = frozenset(
    {
        "north",
        "northeast",
        "east",
        "southeast",
        "south",
        "southwest",
        "west",
        "northwest",
    }
)
LOCOMOTION_CYCLES = frozenset({"walk", "run", "flight"})
BLINK_STATES = frozenset({"open", "half_closed", "closed"})
PROP_COMPOSITIONS = frozenset({"whole_pose", "overlay"})
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class CharacterRuntimeProfileValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PropBinding:
    prop_id: str
    composition: str
    anchor: str | None
    permission_capability: str | None


@dataclass(frozen=True)
class CharacterRuntimeProfile:
    schema_version: int
    character_id: str
    default_pose_id: str
    presentation_scale: Tuple[int, int]
    required_anchors: Tuple[str, ...]
    optional_anchors: Tuple[str, ...]
    facing_poses: Mapping[str, str]
    action_poses: Mapping[str, str]
    expression_aliases: Mapping[str, str]
    locomotion_cycles: Mapping[str, Tuple[str, ...]]
    speech_poses: Tuple[str, ...]
    blink_poses: Mapping[str, str]
    props: Mapping[str, PropBinding]

    def referenced_pose_ids(self) -> Tuple[str, ...]:
        pose_ids = {
            self.default_pose_id,
            *self.facing_poses.values(),
            *self.action_poses.values(),
            *self.speech_poses,
            *self.blink_poses.values(),
        }
        for cycle in self.locomotion_cycles.values():
            pose_ids.update(cycle)
        return tuple(sorted(pose_ids))


def load_character_runtime_profile(path: Path) -> CharacterRuntimeProfile:
    profile_path = Path(path)
    try:
        content = profile_path.read_bytes()
    except OSError as exc:
        raise CharacterRuntimeProfileValidationError(str(exc)) from exc
    return load_character_runtime_profile_bytes(content)


def load_character_runtime_profile_bytes(
    content: bytes,
) -> CharacterRuntimeProfile:
    try:
        raw = json.loads(content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CharacterRuntimeProfileValidationError(str(exc)) from exc
    return _parse_character_runtime_profile(raw)


def _parse_character_runtime_profile(
    raw: Any,
) -> CharacterRuntimeProfile:
    if not isinstance(raw, Mapping):
        raise CharacterRuntimeProfileValidationError(
            "runtime profile must be an object"
        )
    required = {
        "schema_version",
        "character_id",
        "default_pose_id",
        "presentation_scale",
        "required_anchors",
        "optional_anchors",
        "facing_poses",
        "action_poses",
        "expression_aliases",
        "locomotion_cycles",
        "speech_poses",
        "blink_poses",
        "props",
    }
    _closed(raw, required, "runtime profile")
    if raw["schema_version"] != 1 or isinstance(raw["schema_version"], bool):
        raise CharacterRuntimeProfileValidationError(
            "schema_version must be 1"
        )
    character_id = _text(raw["character_id"], "character_id")
    default_pose_id = _text(raw["default_pose_id"], "default_pose_id")
    presentation_scale = _positive_pair(
        raw["presentation_scale"],
        "presentation_scale",
    )
    required_anchors = _identifier_tuple(
        raw["required_anchors"],
        "required_anchors",
        allow_empty=False,
    )
    if "root" not in required_anchors:
        raise CharacterRuntimeProfileValidationError(
            "required_anchors must include root"
        )
    optional_anchors = _identifier_tuple(
        raw["optional_anchors"],
        "optional_anchors",
        allow_empty=True,
    )
    overlap = sorted(set(required_anchors) & set(optional_anchors))
    if overlap:
        raise CharacterRuntimeProfileValidationError(
            "required_anchors and optional_anchors overlap: {}".format(
                ", ".join(overlap)
            )
        )
    facing_poses = _string_mapping(raw["facing_poses"], "facing_poses")
    if set(facing_poses) != FACINGS:
        raise CharacterRuntimeProfileValidationError(
            "facing_poses must define all eight facings exactly"
        )
    action_poses = _string_mapping(raw["action_poses"], "action_poses")
    expression_aliases = _string_mapping(
        raw["expression_aliases"],
        "expression_aliases",
    )
    locomotion_raw = raw["locomotion_cycles"]
    if not isinstance(locomotion_raw, Mapping) or set(locomotion_raw) != LOCOMOTION_CYCLES:
        raise CharacterRuntimeProfileValidationError(
            "locomotion_cycles must define walk, run, and flight exactly"
        )
    locomotion_cycles = MappingProxyType(
        {
            cycle: _text_tuple(
                locomotion_raw[cycle],
                "locomotion_cycles.{}".format(cycle),
                allow_empty=True,
            )
            for cycle in sorted(LOCOMOTION_CYCLES)
        }
    )
    speech_poses = _text_tuple(
        raw["speech_poses"],
        "speech_poses",
        allow_empty=True,
    )
    blink_poses = _string_mapping(raw["blink_poses"], "blink_poses")
    if set(blink_poses) != BLINK_STATES:
        raise CharacterRuntimeProfileValidationError(
            "blink_poses must define open, half_closed, and closed exactly"
        )
    props = _props(
        raw["props"],
        set(required_anchors) | set(optional_anchors),
    )
    return CharacterRuntimeProfile(
        schema_version=1,
        character_id=character_id,
        default_pose_id=default_pose_id,
        presentation_scale=presentation_scale,
        required_anchors=required_anchors,
        optional_anchors=optional_anchors,
        facing_poses=facing_poses,
        action_poses=action_poses,
        expression_aliases=expression_aliases,
        locomotion_cycles=locomotion_cycles,
        speech_poses=speech_poses,
        blink_poses=blink_poses,
        props=props,
    )


def _props(
    value: Any,
    declared_anchors: set[str],
) -> Mapping[str, PropBinding]:
    if not isinstance(value, Mapping):
        raise CharacterRuntimeProfileValidationError("props must be an object")
    result: dict[str, PropBinding] = {}
    for prop_id, raw_binding in value.items():
        _identifier(prop_id, "props key")
        if not isinstance(raw_binding, Mapping):
            raise CharacterRuntimeProfileValidationError(
                "props.{} must be an object".format(prop_id)
            )
        _closed(
            raw_binding,
            {"composition", "anchor", "permission_capability"},
            "props.{}".format(prop_id),
        )
        composition = raw_binding["composition"]
        if composition not in PROP_COMPOSITIONS:
            raise CharacterRuntimeProfileValidationError(
                "props.{}.composition is unsupported".format(prop_id)
            )
        anchor = _optional_identifier(
            raw_binding["anchor"],
            "props.{}.anchor".format(prop_id),
        )
        if anchor is not None and anchor not in declared_anchors:
            raise CharacterRuntimeProfileValidationError(
                "props.{}.anchor is not a declared anchor".format(prop_id)
            )
        if composition == "overlay" and anchor is None:
            raise CharacterRuntimeProfileValidationError(
                "overlay props require an anchor"
            )
        permission = _optional_identifier(
            raw_binding["permission_capability"],
            "props.{}.permission_capability".format(prop_id),
        )
        result[prop_id] = PropBinding(
            prop_id=prop_id,
            composition=composition,
            anchor=anchor,
            permission_capability=permission,
        )
    return MappingProxyType(result)


def _closed(
    value: Mapping[str, Any],
    fields: set[str],
    path: str,
) -> None:
    missing = sorted(fields - set(value))
    unknown = sorted(set(value) - fields)
    if missing or unknown:
        raise CharacterRuntimeProfileValidationError(
            "{} fields invalid; missing={} unknown={}".format(
                path,
                missing,
                unknown,
            )
        )


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise CharacterRuntimeProfileValidationError(
            "{} must be non-empty text".format(path)
        )
    return value


def _identifier(value: Any, path: str) -> str:
    text = _text(value, path)
    if _IDENTIFIER.fullmatch(text) is None:
        raise CharacterRuntimeProfileValidationError(
            "{} must be a lowercase snake_case identifier".format(path)
        )
    return text


def _optional_identifier(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _identifier(value, path)


def _positive_pair(value: Any, path: str) -> Tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise CharacterRuntimeProfileValidationError(
            "{} must contain two positive integers".format(path)
        )
    if any(
        isinstance(item, bool) or not isinstance(item, int) or item < 1
        for item in value
    ):
        raise CharacterRuntimeProfileValidationError(
            "{} must contain two positive integers".format(path)
        )
    return int(value[0]), int(value[1])


def _text_tuple(
    value: Any,
    path: str,
    *,
    allow_empty: bool,
) -> Tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise CharacterRuntimeProfileValidationError(
            "{} must be an array{}".format(
                path,
                "" if allow_empty else " with at least one item",
            )
        )
    result = tuple(_text(item, "{}[]".format(path)) for item in value)
    if len(set(result)) != len(result):
        raise CharacterRuntimeProfileValidationError(
            "{} must not contain duplicates".format(path)
        )
    return result


def _identifier_tuple(
    value: Any,
    path: str,
    *,
    allow_empty: bool,
) -> Tuple[str, ...]:
    result = _text_tuple(value, path, allow_empty=allow_empty)
    for item in result:
        _identifier(item, "{}[]".format(path))
    return result


def _string_mapping(value: Any, path: str) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise CharacterRuntimeProfileValidationError(
            "{} must be an object".format(path)
        )
    result: dict[str, str] = {}
    for key, item in value.items():
        result[_identifier(key, "{} key".format(path))] = _text(
            item,
            "{}.{}".format(path, key),
        )
    return MappingProxyType(result)


__all__ = [
    "CharacterRuntimeProfile",
    "CharacterRuntimeProfileValidationError",
    "PropBinding",
    "load_character_runtime_profile",
    "load_character_runtime_profile_bytes",
]
