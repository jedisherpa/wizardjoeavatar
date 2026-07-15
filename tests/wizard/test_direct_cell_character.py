import json
import tempfile
import unittest
from pathlib import Path

from wizard_avatar.direct_cell_character import (
    load_direct_cell_runtime_profile,
    resolve_direct_cell_blink_pose_id,
    resolve_direct_cell_pose_id,
    resolve_direct_cell_speech_pose_id,
    validate_direct_cell_runtime_profile,
)
from wizard_avatar.models import WizardState


POSES = (
    "neutral_front",
    "neutral_left_profile",
    "idle_speaking",
    "walk_contact_left",
    "walk_contact_right",
    "gesture_question",
    "expression_curiosity",
    "blink_open",
    "blink_half_closed",
    "blink_closed",
)


class DirectCellCharacterTests(unittest.TestCase):
    def make_profile(self):
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "runtime.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "character_id": "test-persona-v1",
                    "scale_multiplier": 0.9,
                    "default_pose_id": "neutral_front",
                    "facing_poses": {
                        "south": "neutral_front",
                        "west": "neutral_left_profile",
                    },
                    "action_poses": {"pointing": "gesture_question"},
                    "expression_aliases": {"thinking": "curiosity"},
                    "walking_cycle": ["walk_contact_left", "walk_contact_right"],
                    "running_cycle": [],
                    "airborne_poses": {},
                    "speech_poses": ["idle_speaking"],
                    "blink_poses": {
                        "open": "blink_open",
                        "half_closed": "blink_half_closed",
                        "closed": "blink_closed",
                    },
                }
            ),
            encoding="utf-8",
        )
        return temporary, load_direct_cell_runtime_profile(path)

    def test_profile_validates_all_referenced_poses(self):
        temporary, profile = self.make_profile()
        self.addCleanup(temporary.cleanup)
        validate_direct_cell_runtime_profile(profile, POSES)

    def test_profile_rejects_unknown_pose(self):
        temporary, profile = self.make_profile()
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(ValueError, "unknown poses"):
            validate_direct_cell_runtime_profile(
                profile,
                tuple(pose for pose in POSES if pose != "idle_speaking"),
            )

    def test_semantic_channels_resolve_without_character_specific_code(self):
        temporary, profile = self.make_profile()
        self.addCleanup(temporary.cleanup)
        state = WizardState(character_id=profile.character_id)
        state.facing = "west"
        self.assertEqual(resolve_direct_cell_pose_id(state, profile, POSES), "neutral_left_profile")

        state.locomotion = "walking"
        state.walk_phase = 0.75
        self.assertEqual(resolve_direct_cell_pose_id(state, profile, POSES), "walk_contact_right")

        state.locomotion = "idle"
        state.action = "pointing"
        self.assertEqual(resolve_direct_cell_pose_id(state, profile, POSES), "gesture_question")

        state.action = "idle"
        state.expression = "thinking"
        self.assertEqual(resolve_direct_cell_pose_id(state, profile, POSES), "expression_curiosity")

        state.speech_id = "speech-1"
        self.assertEqual(resolve_direct_cell_pose_id(state, profile, POSES), "expression_curiosity")
        self.assertEqual(
            resolve_direct_cell_speech_pose_id(state, profile, POSES),
            "idle_speaking",
        )

        state.expression = "neutral"
        state.action = "crouch"
        profile.action_poses["crouch"] = "neutral_left_profile"
        self.assertEqual(
            resolve_direct_cell_pose_id(state, profile, POSES),
            "neutral_left_profile",
        )

    def test_blink_mapping_is_deterministic_and_does_not_replace_body_pose(self):
        temporary, profile = self.make_profile()
        self.addCleanup(temporary.cleanup)
        state = WizardState(character_id=profile.character_id)
        state.locomotion = "walking"
        state.walk_phase = 0.75
        state.blink_phase = 0.98
        self.assertEqual(resolve_direct_cell_pose_id(state, profile, POSES), "walk_contact_right")
        self.assertEqual(
            resolve_direct_cell_blink_pose_id(state, profile, POSES),
            "blink_closed",
        )


if __name__ == "__main__":
    unittest.main()
