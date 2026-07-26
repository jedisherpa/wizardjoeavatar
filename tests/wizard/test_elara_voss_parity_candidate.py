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
CHARACTER_ROOT = PARITY_ROOT / "compiled" / "elara-voss"
INDEX_PATH = CHARACTER_ROOT / "library-index.json"
EXISTING_ARTIFACT_PATH = (
    CHARACTER_ROOT / "elara-voss-candidate-source-motion-v001.wjpose"
)
AUTHORED_ROOT = PARITY_ROOT / "authored-source" / "elara-voss"
AUTHORED_FRAME_ROOT = AUTHORED_ROOT / "frames"


class ElaraVossParityCandidateTests(unittest.TestCase):
    def test_real_candidate_preserves_all_48_canonical_pixel_graphs(self):
        self.assertEqual(
            sha256_path(INDEX_PATH),
            "7fd020cb347ec6726e1dd60939166d9659775fe626ce8511108f38441708bde2",
        )
        library = HDPoseLibrary(INDEX_PATH)
        supplied = HDPoseArtifact(EXISTING_ARTIFACT_PATH)
        self.assertEqual(len(library.pose_ids), 48)
        self.assertTrue(library.index["review_projection"])
        self.assertFalse(library.index["runtime_admitted"])

        for pose_number in range(1, 49):
            pose_id = f"elara_voss_motion_{pose_number:03d}"
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

    def test_review_motion_contract_is_non_admitted_broadcast_performance(self):
        contract_path = (
            PARITY_ROOT
            / "source-metadata"
            / "elara-voss"
            / "review-motion-contract-v001.json"
        )
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        self.assertEqual(
            sha256_path(contract_path),
            "a24a1597aad39c522b3f77356ca141e427fa3b8b8f8b022fcffc19072a697b0b",
        )
        self.assertTrue(contract["review_projection"])
        self.assertFalse(contract["runtime_admitted"])
        self.assertEqual(
            contract["sequences"]["g7"]["family"],
            "live_interview_exchange",
        )
        self.assertEqual(contract["sequences"]["g7"]["loop_mode"], "loop")
        self.assertEqual(
            contract["sequences"]["g7"]["pose_ids"],
            [
                f"elara_voss_motion_{pose_number:03d}"
                for pose_number in range(37, 43)
            ],
        )
        self.assertEqual(
            contract["sequences"]["g8"]["family"],
            "on_camera_briefing",
        )
        self.assertEqual(
            contract["sequences"]["g8"]["loop_mode"],
            "hold_last",
        )
        self.assertEqual(
            contract["sequences"]["g8"]["pose_ids"],
            [
                f"elara_voss_motion_{pose_number:03d}"
                for pose_number in range(43, 49)
            ],
        )

    def test_oversize_fit_is_explicit_and_receipted(self):
        manifest = json.loads(
            (AUTHORED_ROOT / "authored-g7-g8-v001.json").read_text(
                encoding="utf-8"
            )
        )
        receipts = json.loads(
            (
                AUTHORED_ROOT / "canonicalization-receipts-v001.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["canonicalization"],
            "integer_translation_with_opt_in_oversize_fit",
        )
        self.assertEqual(len(receipts), 12)
        self.assertEqual(
            [
                Path(receipt["destination_path"]).stem
                for receipt in receipts
                if receipt["resampled"]
            ],
            [
                f"elara_voss_motion_{pose_number:03d}"
                for pose_number in range(42, 49)
            ],
        )
        for receipt in receipts:
            with self.subTest(path=receipt["destination_path"]):
                if receipt["resampled"]:
                    self.assertEqual(receipt["resample_filter"], "lanczos")
                    self.assertGreaterEqual(receipt["scale"], 0.96)
                    self.assertLess(receipt["scale"], 1.0)
                else:
                    self.assertIsNone(receipt["resample_filter"])
                    self.assertEqual(receipt["scale"], 1.0)


if __name__ == "__main__":
    unittest.main()
