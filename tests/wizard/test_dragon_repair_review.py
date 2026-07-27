import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.build_dragon_repair_review import (
    DEFAULT_OUTPUT,
    build_dragon_repair_review,
)
from wizard_avatar.hd_pose_artifact import HDPoseLibrary


class DragonRepairReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index_path = DEFAULT_OUTPUT / "library-index.json"
        cls.index = json.loads(cls.index_path.read_text(encoding="utf-8"))
        cls.library = HDPoseLibrary(cls.index_path)

    def test_library_is_explicitly_incomplete_and_review_only(self):
        self.assertEqual(self.index["pose_count"], 134)
        self.assertEqual(self.index["validated_source_pose_count"], 84)
        self.assertEqual(self.index["candidate_pose_count"], 50)
        self.assertEqual(self.index["missing_pose_count"], 0)
        self.assertEqual(self.index["missing_asset_ids"], [])
        self.assertEqual(
            self.index["approval_state"], "incomplete_source_repair_review"
        )
        self.assertTrue(self.index["review_projection"])
        self.assertFalse(self.index["runtime_admitted"])
        self.assertTrue(
            all(not shard["runtime_admitted"] for shard in self.index["shards"])
        )
        self.assertFalse(
            self.index["sequences"]["dragon-repair-review"]["runtime_admitted"]
        )

    def test_candidate_poses_are_present_but_not_approved(self):
        poses = {record["asset_id"]: record for record in self.index["poses"]}
        self.assertEqual(
            poses["ACT011"]["source_state"],
            "replacement_candidate_unapproved",
        )
        self.assertEqual(
            poses["ACT025"]["source_state"],
            "replacement_candidate_unapproved",
        )
        self.assertEqual(poses["ACT011"]["replacement_approval"], "not_approved")
        self.assertEqual(poses["ACT025"]["replacement_approval"], "not_approved")
        for asset_id in (
            "CAN007",
            "ACT007",
            "ACT032",
            "ACT044",
            "ACT060",
            "ACT099",
            "ACT100",
            "ACT123",
        ):
            self.assertEqual(
                poses[asset_id]["source_state"], "interim_candidate_unapproved"
            )
            self.assertEqual(poses[asset_id]["replacement_approval"], "not_approved")

    def test_artifacts_reconstruct_source_rgba_exactly(self):
        root = DEFAULT_OUTPUT.parents[5]
        for record in self.index["poses"]:
            with self.subTest(pose_id=record["pose_id"]):
                source_path = root / record["source_path"]
                from PIL import Image

                with Image.open(source_path) as image:
                    image.load()
                    expected = image.convert("RGBA").tobytes()
                actual = self.library.load_rgba(record["pose_id"])
                self.assertEqual(
                    hashlib.sha256(actual).hexdigest(),
                    hashlib.sha256(expected).hexdigest(),
                )

    def test_rebuild_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first"
            second = Path(temporary) / "second"
            build_dragon_repair_review(output_dir=first)
            build_dragon_repair_review(output_dir=second)
            first_files = {
                path.relative_to(first): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in first.iterdir()
            }
            second_files = {
                path.relative_to(second): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in second.iterdir()
            }
            self.assertEqual(first_files, second_files)


if __name__ == "__main__":
    unittest.main()
