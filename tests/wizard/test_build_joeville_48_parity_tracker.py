import json
import unittest
from pathlib import Path

from tools.build_joeville_48_parity_tracker import build_tracker


ROOT = Path(__file__).resolve().parents[2]
CENSUS = (
    ROOT
    / "assets"
    / "reference"
    / "joeville_48_parity"
    / "source-metadata"
    / "archive-census-v001.json"
)


class JoeVille48ParityTrackerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tracker = build_tracker(json.loads(CENSUS.read_text(encoding="utf-8")))

    def test_tracker_contains_exact_authority_roster_and_576_slots(self):
        self.assertEqual(len(self.tracker["characters"]), 12)
        self.assertEqual(
            sum(
                len(character["motion_slots"])
                for character in self.tracker["characters"]
            ),
            576,
        )
        self.assertEqual(
            self.tracker["supplied_extras"][0]["character_id"], "crystail"
        )

    def test_existing_sources_do_not_imply_runtime_admission(self):
        for character in self.tracker["characters"]:
            self.assertEqual(
                character["counts"]["runtime_admitted_pose_count"], 0
            )
            self.assertTrue(
                all(
                    not slot["runtime_admitted"]
                    for slot in character["motion_slots"]
                )
            )

    def test_known_source_gaps_and_conflicts_remain_explicit(self):
        by_id = {
            character["character_id"]: character
            for character in self.tracker["characters"]
        }
        self.assertEqual(
            by_id["selene-hart"]["counts"]["authoring_required_slot_count"],
            12,
        )
        self.assertEqual(
            by_id["elara-voss"]["counts"]["conflicted_slot_count"], 0
        )
        self.assertEqual(
            by_id["elara-voss"]["source_sequences"][2]["selected_source"][
                "archive_id"
            ],
            "sprites-3",
        )
        self.assertEqual(
            by_id["aurelia-finch"]["counts"]["authoring_required_slot_count"],
            6,
        )
        self.assertEqual(
            by_id["serena-quill"]["counts"]["available_unique_slot_count"],
            48,
        )


if __name__ == "__main__":
    unittest.main()
