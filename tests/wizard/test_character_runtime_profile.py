import json
import tempfile
import unittest
from pathlib import Path

from wizard_avatar.character_runtime_profile import (
    CharacterRuntimeProfileValidationError,
    load_character_runtime_profile,
)


class CharacterRuntimeProfileTests(unittest.TestCase):
    def test_profile_expresses_required_anatomy_and_optional_whole_pose_orb(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            payload = self._profile()
            path.write_text(json.dumps(payload), encoding="utf-8")

            profile = load_character_runtime_profile(path)

            self.assertEqual(profile.character_id, "serena-quill-v1")
            self.assertEqual(
                profile.required_anchors,
                (
                    "root",
                    "mouth",
                    "left_eye",
                    "right_eye",
                    "left_foot",
                    "right_foot",
                    "left_hand",
                    "right_hand",
                ),
            )
            self.assertEqual(profile.optional_anchors, ("orb",))
            self.assertEqual(profile.props["orb"].composition, "whole_pose")
            self.assertEqual(profile.props["orb"].anchor, "orb")
            self.assertIn("neutral_front", profile.referenced_pose_ids())
            self.assertIn("walk_contact_left", profile.referenced_pose_ids())

    def test_required_and_optional_anchors_must_be_disjoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            payload = self._profile()
            payload["optional_anchors"] = ["orb", "root"]
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(
                CharacterRuntimeProfileValidationError,
                "overlap",
            ):
                load_character_runtime_profile(path)

    def test_overlay_prop_requires_a_declared_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            payload = self._profile()
            payload["props"]["orb"] = {
                "composition": "overlay",
                "anchor": None,
                "permission_capability": None,
            }
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(
                CharacterRuntimeProfileValidationError,
                "overlay props require an anchor",
            ):
                load_character_runtime_profile(path)

    @staticmethod
    def _profile():
        return {
            "schema_version": 1,
            "character_id": "serena-quill-v1",
            "default_pose_id": "neutral_front",
            "presentation_scale": [22, 25],
            "required_anchors": [
                "root",
                "mouth",
                "left_eye",
                "right_eye",
                "left_foot",
                "right_foot",
                "left_hand",
                "right_hand",
            ],
            "optional_anchors": ["orb"],
            "facing_poses": {
                "north": "neutral_back",
                "northeast": "neutral_back_three_quarter_right",
                "east": "neutral_right_profile",
                "southeast": "neutral_three_quarter_right",
                "south": "neutral_front",
                "southwest": "neutral_three_quarter_left",
                "west": "neutral_left_profile",
                "northwest": "neutral_back_three_quarter_left",
            },
            "action_poses": {
                "explaining": "facilitation",
                "orb_reassurance": "orb_reassurance",
            },
            "expression_aliases": {
                "happy": "joy",
                "worried": "concern",
            },
            "locomotion_cycles": {
                "walk": [
                    "walk_contact_left",
                    "walk_down_left",
                    "walk_passing_right",
                    "walk_up_right",
                ],
                "run": ["run_contact_left", "run_passing_right"],
                "flight": [],
            },
            "speech_poses": ["viseme_rest", "viseme_open_vowel"],
            "blink_poses": {
                "open": "blink_open",
                "half_closed": "blink_half_closed",
                "closed": "blink_closed",
            },
            "props": {
                "orb": {
                    "composition": "whole_pose",
                    "anchor": "orb",
                    "permission_capability": None,
                }
            },
        }


if __name__ == "__main__":
    unittest.main()
