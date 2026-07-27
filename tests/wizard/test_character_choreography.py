import json
import unittest
from pathlib import Path

from wizard_avatar.character_choreography import (
    CharacterChoreographyValidationError,
    load_character_choreography_dictionary_bytes,
)
from wizard_avatar.character_package import load_character_package


ROOT = Path(__file__).resolve().parents[2]
SERENA_PACKAGE = (
    ROOT
    / "wizard_avatar"
    / "definitions"
    / "characters"
    / "serena_quill"
    / "serena_quill_character_package_v2.json"
)


def game_dictionary():
    return {
        "schema_version": 1,
        "dictionary_id": "choreography:test-character",
        "character_id": "test-character",
        "library_class": "game_motion",
        "instructions": {
            "selection_unit": "command",
            "transition_policy": "neutral_bridge",
            "speech_motion_policy": "unsupported",
            "locomotion_speech_policy": "unsupported",
            "unsupported_intent_policy": "default_pose",
            "repetition_window_ms": 3000,
            "minimum_stillness_ms": 250,
            "maximum_gestures_per_phrase": 0,
        },
        "intent_bindings": {
            "neutral": {
                "roles": ["game_action", "neutral"],
                "pose_ids": ["idle"],
                "action_ids": ["idle"],
                "clip_ids": ["idle"],
                "speech_compatible": False,
                "interrupt_policy": "immediate",
                "minimum_hold_ms": 250,
                "recovery_intent": None,
            }
        },
    }


class CharacterChoreographyTests(unittest.TestCase):
    def test_frozen_wizard_package_has_comprehensive_dictionary(self):
        package = load_character_package()
        dictionary = package.choreography_dictionary_contract

        self.assertIsNotNone(dictionary)
        self.assertEqual(
            dictionary.library_class,
            "comprehensive_performance",
        )
        self.assertTrue(dictionary.supports_phrase_level_acting)
        self.assertTrue(
            dictionary.binding_for_intent("explain").speech_compatible
        )
        self.assertEqual(
            dictionary.binding_for_intent("unknown").intent_id,
            "neutral",
        )

    def test_serena_package_has_focused_performance_dictionary(self):
        package = load_character_package(SERENA_PACKAGE)
        dictionary = package.choreography_dictionary_contract

        self.assertEqual(dictionary.library_class, "focused_performance")
        self.assertFalse(dictionary.supports_phrase_level_acting)
        self.assertEqual(
            dictionary.instructions.maximum_gestures_per_phrase,
            1,
        )
        self.assertEqual(
            dictionary.binding_for_intent("reassure").recovery_intent,
            "speak",
        )

    def test_game_dictionary_uses_economical_default_pose_fallback(self):
        raw = game_dictionary()
        dictionary = load_character_choreography_dictionary_bytes(
            json.dumps(raw, sort_keys=True).encode("utf-8"),
            character_id="test-character",
            pose_ids={"idle"},
            action_ids={"idle"},
            clip_ids={"idle"},
        )

        self.assertEqual(dictionary.library_class, "game_motion")
        self.assertEqual(
            dictionary.instructions.selection_unit,
            "command",
        )
        self.assertEqual(
            dictionary.binding_for_intent("unsupported").intent_id,
            "neutral",
        )

    def test_dictionary_rejects_cross_package_references(self):
        raw = game_dictionary()
        raw["intent_bindings"]["neutral"]["pose_ids"] = ["other-pose"]

        with self.assertRaisesRegex(
            CharacterChoreographyValidationError,
            "unknown pose ids",
        ):
            load_character_choreography_dictionary_bytes(
                json.dumps(raw, sort_keys=True).encode("utf-8"),
                character_id="test-character",
                pose_ids={"idle"},
                action_ids={"idle"},
                clip_ids={"idle"},
            )

    def test_game_dictionary_rejects_performance_style_instructions(self):
        mutations = (
            ("selection_unit", "phrase"),
            ("transition_policy", "authored_graph"),
            ("speech_motion_policy", "layered"),
            ("locomotion_speech_policy", "allowed"),
            ("maximum_gestures_per_phrase", 1),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                raw = game_dictionary()
                raw["instructions"][field] = value
                with self.assertRaisesRegex(
                    CharacterChoreographyValidationError,
                    "game libraries require",
                ):
                    load_character_choreography_dictionary_bytes(
                        json.dumps(raw, sort_keys=True).encode("utf-8")
                    )

    def test_comprehensive_dictionary_requires_performance_intents(self):
        raw = game_dictionary()
        raw["library_class"] = "comprehensive_performance"
        raw["instructions"]["selection_unit"] = "phrase"
        raw["instructions"]["speech_motion_policy"] = "layered"

        with self.assertRaisesRegex(
            CharacterChoreographyValidationError,
            "require intent bindings",
        ):
            load_character_choreography_dictionary_bytes(
                json.dumps(raw, sort_keys=True).encode("utf-8")
            )

    def test_duplicate_json_keys_fail_closed(self):
        payload = json.dumps(game_dictionary(), sort_keys=True).replace(
            '"schema_version": 1',
            '"schema_version": 1, "schema_version": 1',
            1,
        )

        with self.assertRaisesRegex(
            CharacterChoreographyValidationError,
            "duplicate JSON key",
        ):
            load_character_choreography_dictionary_bytes(
                payload.encode("utf-8")
            )


if __name__ == "__main__":
    unittest.main()
