import json
import unittest
from pathlib import Path

from wizard_avatar.character_choreography import (
    load_character_choreography_dictionary,
)


ROOT = Path(__file__).resolve().parents[2]
KINGFISHER_ROOT = (
    ROOT / "assets" / "reference" / "characters" / "kingfisher"
)
BASE_INDEX = KINGFISHER_ROOT / "compiled" / "library-index.json"
STAGE_PLAN = KINGFISHER_ROOT / "stage-expansion-v1" / "pose-plan.json"
DICTIONARY = (
    KINGFISHER_ROOT / "kingfisher-choreography-dictionary-v1.json"
)


class KingfisherChoreographyDictionaryTests(unittest.TestCase):
    def test_dictionary_matches_the_base_and_stage_review_vocabularies(self):
        base = json.loads(BASE_INDEX.read_text(encoding="utf-8"))
        plan = json.loads(STAGE_PLAN.read_text(encoding="utf-8"))
        stage_pose_ids = {
            "kingfisher.act.{:03d}.{}".format(
                int(pose["ordinal"]),
                pose["slug"],
            )
            for key in plan["performance_keys"]
            for pose in key["poses"]
        }
        dictionary = load_character_choreography_dictionary(
            DICTIONARY,
            character_id="kingfisher",
            pose_ids=set(base["pose_ids"]) | stage_pose_ids,
            action_ids=set(),
            clip_ids=set(),
        )
        self.assertEqual(
            dictionary.library_class,
            "comprehensive_performance",
        )
        self.assertTrue(dictionary.supports_phrase_level_acting)
        self.assertEqual(
            dictionary.instructions.speech_motion_policy,
            "layered",
        )
        self.assertEqual(
            dictionary.instructions.locomotion_speech_policy,
            "allowed",
        )
        self.assertEqual(
            set(dictionary.intent_bindings),
            {
                "call_to_action",
                "comic_aside",
                "confess",
                "explain",
                "listen",
                "neutral",
                "pace_left",
                "pace_right",
                "question",
                "resolve",
                "reveal",
                "speak",
                "suspense",
                "welcome",
            },
        )


if __name__ == "__main__":
    unittest.main()
