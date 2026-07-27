import json
import unittest
from pathlib import Path

from tools.build_character_choreography_dictionary import (
    build_game_motion_dictionary,
)
from wizard_avatar.character_choreography import (
    load_character_choreography_dictionary,
)


ROOT = Path(__file__).resolve().parents[2]
PARITY_ROOT = ROOT / "assets" / "reference" / "joeville_48_parity" / "compiled"
LIANA_INDEX = (
    ROOT
    / "assets"
    / "reference"
    / "joeville_supplemental"
    / "liana"
    / "compiled-motion"
    / "library-index.json"
)


class GameMotionChoreographyTests(unittest.TestCase):
    def test_each_small_library_has_its_own_valid_dictionary(self):
        indexes = sorted(PARITY_ROOT.glob("*/library-index.json")) + [
            LIANA_INDEX
        ]
        self.assertEqual(len(indexes), 13)
        dictionary_ids = set()
        for index_path in indexes:
            with self.subTest(index=index_path):
                output = build_game_motion_dictionary(index_path)
                index = json.loads(index_path.read_text(encoding="utf-8"))
                pose_ids = {
                    pose_id
                    for sequence in index["sequences"].values()
                    for pose_id in sequence["pose_ids"]
                }
                dictionary = load_character_choreography_dictionary(
                    output,
                    character_id=index["character_id"],
                    pose_ids=pose_ids,
                    action_ids=set(),
                    clip_ids=set(),
                )
                self.assertEqual(dictionary.library_class, "game_motion")
                self.assertEqual(
                    dictionary.instructions.selection_unit,
                    "command",
                )
                self.assertEqual(
                    dictionary.instructions.speech_motion_policy,
                    "unsupported",
                )
                self.assertNotIn(dictionary.dictionary_id, dictionary_ids)
                dictionary_ids.add(dictionary.dictionary_id)


if __name__ == "__main__":
    unittest.main()
