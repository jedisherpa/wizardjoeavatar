from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


LIBRARY_CLASSES = frozenset(
    {
        "comprehensive_performance",
        "focused_performance",
        "game_motion",
    }
)
SELECTION_UNITS = frozenset({"phrase", "beat", "command"})
TRANSITION_POLICIES = frozenset({"authored_graph", "neutral_bridge"})
SPEECH_MOTION_POLICIES = frozenset(
    {"layered", "whole_pose", "mouth_only", "unsupported"}
)
LOCOMOTION_SPEECH_POLICIES = frozenset(
    {"allowed", "restricted", "unsupported"}
)
UNSUPPORTED_INTENT_POLICIES = frozenset(
    {"characterful_neutral", "default_pose", "reject"}
)
INTERRUPT_POLICIES = frozenset(
    {"immediate", "phrase_boundary", "commit_then_recover"}
)
INTENT_ROLES = frozenset(
    {
        "neutral",
        "listening",
        "speaking",
        "gesture",
        "reaction",
        "locomotion",
        "flight",
        "game_action",
        "transition",
        "recovery",
    }
)
_STABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SEMANTIC_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class CharacterChoreographyValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ChoreographyInstructionsV1:
    selection_unit: str
    transition_policy: str
    speech_motion_policy: str
    locomotion_speech_policy: str
    unsupported_intent_policy: str
    repetition_window_ms: int
    minimum_stillness_ms: int
    maximum_gestures_per_phrase: int


@dataclass(frozen=True)
class ChoreographyIntentBindingV1:
    intent_id: str
    roles: Tuple[str, ...]
    pose_ids: Tuple[str, ...]
    action_ids: Tuple[str, ...]
    clip_ids: Tuple[str, ...]
    speech_compatible: bool
    interrupt_policy: str
    minimum_hold_ms: int
    recovery_intent: Optional[str]


@dataclass(frozen=True)
class CharacterChoreographyDictionaryV1:
    schema_version: int
    dictionary_id: str
    character_id: str
    library_class: str
    instructions: ChoreographyInstructionsV1
    intent_bindings: Mapping[str, ChoreographyIntentBindingV1]

    @property
    def supports_phrase_level_acting(self) -> bool:
        return (
            self.library_class == "comprehensive_performance"
            and self.instructions.selection_unit == "phrase"
        )

    def binding_for_intent(
        self,
        intent_id: str,
    ) -> Optional[ChoreographyIntentBindingV1]:
        binding = self.intent_bindings.get(intent_id)
        if binding is not None:
            return binding
        if self.instructions.unsupported_intent_policy == "reject":
            return None
        return self.intent_bindings["neutral"]


def load_character_choreography_dictionary(
    path: Path,
    *,
    character_id: Optional[str] = None,
    pose_ids: Optional[set[str]] = None,
    action_ids: Optional[set[str]] = None,
    clip_ids: Optional[set[str]] = None,
) -> CharacterChoreographyDictionaryV1:
    try:
        content = Path(path).read_bytes()
    except OSError as exc:
        raise CharacterChoreographyValidationError(str(exc)) from exc
    return load_character_choreography_dictionary_bytes(
        content,
        character_id=character_id,
        pose_ids=pose_ids,
        action_ids=action_ids,
        clip_ids=clip_ids,
    )


def load_character_choreography_dictionary_bytes(
    content: bytes,
    *,
    character_id: Optional[str] = None,
    pose_ids: Optional[set[str]] = None,
    action_ids: Optional[set[str]] = None,
    clip_ids: Optional[set[str]] = None,
) -> CharacterChoreographyDictionaryV1:
    try:
        raw = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except CharacterChoreographyValidationError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CharacterChoreographyValidationError(
            "choreography dictionary must be valid UTF-8 JSON"
        ) from exc
    dictionary = _parse_dictionary(raw)
    if character_id is not None and dictionary.character_id != character_id:
        raise CharacterChoreographyValidationError(
            "choreography dictionary character_id does not match package"
        )
    _validate_references(
        dictionary,
        pose_ids=pose_ids,
        action_ids=action_ids,
        clip_ids=clip_ids,
    )
    return dictionary


def _parse_dictionary(raw: Any) -> CharacterChoreographyDictionaryV1:
    if not isinstance(raw, Mapping):
        raise CharacterChoreographyValidationError(
            "choreography dictionary must be an object"
        )
    _closed(
        raw,
        {
            "schema_version",
            "dictionary_id",
            "character_id",
            "library_class",
            "instructions",
            "intent_bindings",
        },
        "choreography dictionary",
    )
    schema_version = raw["schema_version"]
    if schema_version != 1 or isinstance(schema_version, bool):
        raise CharacterChoreographyValidationError(
            "choreography dictionary schema_version must be 1"
        )
    dictionary_id = _stable_id(raw["dictionary_id"], "dictionary_id")
    character_id = _stable_id(raw["character_id"], "character_id")
    library_class = raw["library_class"]
    if library_class not in LIBRARY_CLASSES:
        raise CharacterChoreographyValidationError(
            "library_class is unsupported"
        )
    instructions = _instructions(raw["instructions"])
    bindings_raw = raw["intent_bindings"]
    if not isinstance(bindings_raw, Mapping) or not bindings_raw:
        raise CharacterChoreographyValidationError(
            "intent_bindings must be a non-empty object"
        )
    bindings = {
        _semantic_id(intent_id, "intent_bindings key"): _binding(
            intent_id,
            value,
        )
        for intent_id, value in bindings_raw.items()
    }
    required_intents = {"neutral"}
    if library_class == "focused_performance":
        required_intents.update({"listen", "speak"})
    elif library_class == "comprehensive_performance":
        required_intents.update(
            {"listen", "speak", "explain"}
        )
    missing_intents = sorted(required_intents - set(bindings))
    if missing_intents:
        raise CharacterChoreographyValidationError(
            "{} libraries require intent bindings: {}".format(
                library_class,
                ", ".join(missing_intents),
            )
        )
    for intent_id, binding in bindings.items():
        if (
            binding.recovery_intent is not None
            and binding.recovery_intent not in bindings
        ):
            raise CharacterChoreographyValidationError(
                "intent_bindings.{} references unknown recovery_intent".format(
                    intent_id
                )
            )
    if (
        library_class == "comprehensive_performance"
        and instructions.speech_motion_policy == "unsupported"
    ):
        raise CharacterChoreographyValidationError(
            "comprehensive libraries must support speech motion"
        )
    _validate_class_instructions(library_class, instructions)
    return CharacterChoreographyDictionaryV1(
        schema_version=1,
        dictionary_id=dictionary_id,
        character_id=character_id,
        library_class=str(library_class),
        instructions=instructions,
        intent_bindings=MappingProxyType(bindings),
    )


def _instructions(value: Any) -> ChoreographyInstructionsV1:
    if not isinstance(value, Mapping):
        raise CharacterChoreographyValidationError(
            "instructions must be an object"
        )
    _closed(
        value,
        {
            "selection_unit",
            "transition_policy",
            "speech_motion_policy",
            "locomotion_speech_policy",
            "unsupported_intent_policy",
            "repetition_window_ms",
            "minimum_stillness_ms",
            "maximum_gestures_per_phrase",
        },
        "instructions",
    )
    selection_unit = _enum(
        value["selection_unit"],
        SELECTION_UNITS,
        "instructions.selection_unit",
    )
    transition_policy = _enum(
        value["transition_policy"],
        TRANSITION_POLICIES,
        "instructions.transition_policy",
    )
    speech_motion_policy = _enum(
        value["speech_motion_policy"],
        SPEECH_MOTION_POLICIES,
        "instructions.speech_motion_policy",
    )
    locomotion_speech_policy = _enum(
        value["locomotion_speech_policy"],
        LOCOMOTION_SPEECH_POLICIES,
        "instructions.locomotion_speech_policy",
    )
    unsupported_intent_policy = _enum(
        value["unsupported_intent_policy"],
        UNSUPPORTED_INTENT_POLICIES,
        "instructions.unsupported_intent_policy",
    )
    return ChoreographyInstructionsV1(
        selection_unit=selection_unit,
        transition_policy=transition_policy,
        speech_motion_policy=speech_motion_policy,
        locomotion_speech_policy=locomotion_speech_policy,
        unsupported_intent_policy=unsupported_intent_policy,
        repetition_window_ms=_integer(
            value["repetition_window_ms"],
            "instructions.repetition_window_ms",
            minimum=0,
            maximum=600_000,
        ),
        minimum_stillness_ms=_integer(
            value["minimum_stillness_ms"],
            "instructions.minimum_stillness_ms",
            minimum=0,
            maximum=60_000,
        ),
        maximum_gestures_per_phrase=_integer(
            value["maximum_gestures_per_phrase"],
            "instructions.maximum_gestures_per_phrase",
            minimum=0,
            maximum=16,
        ),
    )


def _validate_class_instructions(
    library_class: str,
    instructions: ChoreographyInstructionsV1,
) -> None:
    if library_class == "comprehensive_performance":
        if (
            instructions.selection_unit != "phrase"
            or instructions.transition_policy != "authored_graph"
        ):
            raise CharacterChoreographyValidationError(
                "comprehensive libraries require phrase selection and "
                "authored_graph transitions"
            )
        return
    if library_class == "focused_performance":
        if (
            instructions.selection_unit != "beat"
            or instructions.transition_policy != "neutral_bridge"
        ):
            raise CharacterChoreographyValidationError(
                "focused libraries require beat selection and "
                "neutral_bridge transitions"
            )
        return
    if (
        instructions.selection_unit != "command"
        or instructions.transition_policy != "neutral_bridge"
        or instructions.maximum_gestures_per_phrase != 0
        or instructions.speech_motion_policy
        not in {"mouth_only", "unsupported"}
        or instructions.locomotion_speech_policy
        not in {"restricted", "unsupported"}
    ):
        raise CharacterChoreographyValidationError(
            "game libraries require command selection, neutral_bridge "
            "transitions, no phrase gestures, and restricted or unsupported "
            "speech motion"
        )


def _binding(
    intent_id: str,
    value: Any,
) -> ChoreographyIntentBindingV1:
    if not isinstance(value, Mapping):
        raise CharacterChoreographyValidationError(
            "intent binding must be an object"
        )
    _closed(
        value,
        {
            "roles",
            "pose_ids",
            "action_ids",
            "clip_ids",
            "speech_compatible",
            "interrupt_policy",
            "minimum_hold_ms",
            "recovery_intent",
        },
        "intent_bindings.{}".format(intent_id),
    )
    roles = _sorted_unique_text(
        value["roles"],
        "intent_bindings.{}.roles".format(intent_id),
        allowed=INTENT_ROLES,
        allow_empty=False,
    )
    pose_ids = _sorted_unique_text(
        value["pose_ids"],
        "intent_bindings.{}.pose_ids".format(intent_id),
    )
    action_ids = _sorted_unique_text(
        value["action_ids"],
        "intent_bindings.{}.action_ids".format(intent_id),
    )
    clip_ids = _sorted_unique_text(
        value["clip_ids"],
        "intent_bindings.{}.clip_ids".format(intent_id),
    )
    if not pose_ids and not action_ids and not clip_ids:
        raise CharacterChoreographyValidationError(
            "intent_bindings.{} must select at least one pose, action, or clip".format(
                intent_id
            )
        )
    speech_compatible = value["speech_compatible"]
    if not isinstance(speech_compatible, bool):
        raise CharacterChoreographyValidationError(
            "intent binding speech_compatible must be a boolean"
        )
    recovery = value["recovery_intent"]
    if recovery is not None:
        recovery = _semantic_id(
            recovery,
            "intent_bindings.{}.recovery_intent".format(intent_id),
        )
    return ChoreographyIntentBindingV1(
        intent_id=_semantic_id(intent_id, "intent_id"),
        roles=roles,
        pose_ids=pose_ids,
        action_ids=action_ids,
        clip_ids=clip_ids,
        speech_compatible=speech_compatible,
        interrupt_policy=_enum(
            value["interrupt_policy"],
            INTERRUPT_POLICIES,
            "intent_bindings.{}.interrupt_policy".format(intent_id),
        ),
        minimum_hold_ms=_integer(
            value["minimum_hold_ms"],
            "intent_bindings.{}.minimum_hold_ms".format(intent_id),
            minimum=0,
            maximum=60_000,
        ),
        recovery_intent=recovery,
    )


def _validate_references(
    dictionary: CharacterChoreographyDictionaryV1,
    *,
    pose_ids: Optional[set[str]],
    action_ids: Optional[set[str]],
    clip_ids: Optional[set[str]],
) -> None:
    for intent_id, binding in dictionary.intent_bindings.items():
        for kind, references, admitted in (
            ("pose", binding.pose_ids, pose_ids),
            ("action", binding.action_ids, action_ids),
            ("clip", binding.clip_ids, clip_ids),
        ):
            if admitted is None:
                continue
            unknown = sorted(set(references) - admitted)
            if unknown:
                raise CharacterChoreographyValidationError(
                    "intent_bindings.{} references unknown {} ids: {}".format(
                        intent_id,
                        kind,
                        ", ".join(unknown),
                    )
                )


def _reject_duplicate_keys(
    pairs: Sequence[Tuple[str, object]],
) -> Mapping[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CharacterChoreographyValidationError(
                "choreography dictionary contains a duplicate JSON key"
            )
        result[key] = value
    return result


def _closed(
    value: Mapping[str, object],
    fields: set[str],
    name: str,
) -> None:
    missing = sorted(fields - set(value))
    unknown = sorted(set(value) - fields)
    if missing or unknown:
        raise CharacterChoreographyValidationError(
            "{} fields are invalid; missing={} unknown={}".format(
                name,
                missing,
                unknown,
            )
        )


def _stable_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or _STABLE_ID.fullmatch(value) is None:
        raise CharacterChoreographyValidationError(
            "{} must be a stable identifier".format(name)
        )
    return value


def _semantic_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or _SEMANTIC_ID.fullmatch(value) is None:
        raise CharacterChoreographyValidationError(
            "{} must be a lowercase semantic identifier".format(name)
        )
    return value


def _enum(value: Any, allowed: frozenset[str], name: str) -> str:
    if value not in allowed:
        raise CharacterChoreographyValidationError(
            "{} is unsupported".format(name)
        )
    return str(value)


def _integer(
    value: Any,
    name: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise CharacterChoreographyValidationError(
            "{} must be an integer from {} through {}".format(
                name,
                minimum,
                maximum,
            )
        )
    return value


def _sorted_unique_text(
    value: Any,
    name: str,
    *,
    allowed: Optional[frozenset[str]] = None,
    allow_empty: bool = True,
) -> Tuple[str, ...]:
    if not isinstance(value, list):
        raise CharacterChoreographyValidationError(
            "{} must be an array".format(name)
        )
    if not allow_empty and not value:
        raise CharacterChoreographyValidationError(
            "{} must not be empty".format(name)
        )
    if any(
        not isinstance(item, str)
        or not item
        or (allowed is not None and item not in allowed)
        for item in value
    ):
        raise CharacterChoreographyValidationError(
            "{} contains an unsupported identifier".format(name)
        )
    if value != sorted(value) or len(set(value)) != len(value):
        raise CharacterChoreographyValidationError(
            "{} must be sorted and unique".format(name)
        )
    return tuple(value)


__all__ = [
    "CharacterChoreographyDictionaryV1",
    "CharacterChoreographyValidationError",
    "ChoreographyInstructionsV1",
    "ChoreographyIntentBindingV1",
    "LIBRARY_CLASSES",
    "load_character_choreography_dictionary",
    "load_character_choreography_dictionary_bytes",
]
