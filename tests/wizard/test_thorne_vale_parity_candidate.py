import hashlib
import json
import unittest
from pathlib import Path

from PIL import Image

from wizard_avatar.hd_pose_artifact import (
    HDPoseArtifact,
    HDPoseLibrary,
    sha256_path,
)


ROOT = Path(__file__).resolve().parents[2]
PARITY_ROOT = ROOT / "assets" / "reference" / "joeville_48_parity"
CHARACTER_ROOT = PARITY_ROOT / "compiled" / "thorne-vale"
INDEX_PATH = CHARACTER_ROOT / "library-index.json"
EXISTING_ARTIFACT_PATH = (
    CHARACTER_ROOT / "thorne-vale-candidate-source-motion-v001.wjpose"
)
AUTHORED_FRAME_ROOT = (
    PARITY_ROOT / "authored-source" / "thorne-vale" / "frames"
)


class ThorneValeParityCandidateTests(unittest.TestCase):
    def test_real_candidate_preserves_all_48_canonical_pixel_graphs(self):
        self.assertEqual(
            sha256_path(INDEX_PATH),
            "937abf76db2da70cb85d36237b9124a2e5dd59b3bfc19f240563e20a71abcde2",
        )
        library = HDPoseLibrary(INDEX_PATH)
        supplied = HDPoseArtifact(EXISTING_ARTIFACT_PATH)
        self.assertEqual(len(library.pose_ids), 48)
        self.assertTrue(library.index["review_projection"])
        self.assertFalse(library.index["runtime_admitted"])

        for pose_number in range(1, 49):
            pose_id = f"thorne_vale_motion_{pose_number:03d}"
            actual = library.load_rgba(pose_id)
            with self.subTest(pose_id=pose_id):
                self.assertFalse(
                    library.pose_metadata[pose_id]["runtime_admitted"]
                )
                if pose_number <= 36:
                    expected = supplied.load_rgba(pose_id)
                else:
                    with Image.open(
                        AUTHORED_FRAME_ROOT / f"{pose_id}.png"
                    ) as image:
                        expected = image.convert("RGBA").tobytes()
                self.assertEqual(
                    hashlib.sha256(actual).hexdigest(),
                    hashlib.sha256(expected).hexdigest(),
                )

    def test_review_motion_contract_is_non_admitted_counsel_performance(self):
        contract_path = (
            PARITY_ROOT
            / "source-metadata"
            / "thorne-vale"
            / "review-motion-contract-v001.json"
        )
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        self.assertEqual(
            sha256_path(contract_path),
            "1c403584f625f1e533538c516c7e00fc803b8dfbc8623e7b3379afd6149bb037",
        )
        self.assertTrue(contract["review_projection"])
        self.assertFalse(contract["runtime_admitted"])
        self.assertEqual(
            contract["sequences"]["g7"]["family"],
            "royal_counsel",
        )
        self.assertEqual(contract["sequences"]["g7"]["loop_mode"], "loop")
        self.assertEqual(
            contract["sequences"]["g7"]["pose_ids"],
            [
                f"thorne_vale_motion_{pose_number:03d}"
                for pose_number in range(37, 43)
            ],
        )
        self.assertEqual(
            contract["sequences"]["g8"]["family"],
            "evidence_briefing",
        )
        self.assertEqual(
            contract["sequences"]["g8"]["loop_mode"],
            "hold_last",
        )
        self.assertEqual(
            contract["sequences"]["g8"]["pose_ids"],
            [
                f"thorne_vale_motion_{pose_number:03d}"
                for pose_number in range(43, 49)
            ],
        )


if __name__ == "__main__":
    unittest.main()
