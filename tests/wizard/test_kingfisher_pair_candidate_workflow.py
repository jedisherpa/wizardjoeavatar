from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.promote_kingfisher_pair_candidate import promote_candidate
from tools.refine_kingfisher_pair_mandible import refine_pair_mandible


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class KingfisherPairCandidateWorkflowTests(unittest.TestCase):
    def make_candidate(self, root: Path) -> tuple[Path, Path, Path, Path]:
        resting_path = root / "resting.png"
        donor_path = root / "donor.png"
        candidate_path = root / "candidate.png"
        candidate_receipt_path = root / "candidate-receipt.json"
        resting = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(resting)
        draw.rectangle((28, 18, 52, 58), fill=(70, 80, 90, 255))
        draw.polygon(
            [(30, 24), (7, 24), (6, 29), (30, 29)],
            fill=(25, 35, 45, 255),
        )
        resting.save(resting_path)
        donor = resting.copy()
        ImageDraw.Draw(donor).polygon(
            [(30, 28), (29, 35), (10, 38), (8, 34), (24, 29)],
            fill=(160, 75, 45, 255),
        )
        donor.save(donor_path)
        refine_pair_mandible(
            resting_path,
            donor_path,
            candidate_path,
            candidate_receipt_path,
            mandible_polygon=[
                (30, 28),
                (29, 35),
                (10, 38),
                (8, 34),
                (24, 29),
            ],
            cavity_polygon=[(30, 27), (30, 33), (12, 35), (23, 29)],
            upper_beak_polygon=[(30, 24), (7, 24), (6, 29), (30, 29)],
            hinge=(30, 29),
            rotation_degrees=-8,
        )
        return (
            resting_path,
            donor_path,
            candidate_path,
            candidate_receipt_path,
        )

    def test_refinement_changes_only_the_mouth_and_preserves_upper_beak(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resting_path, _, candidate_path, receipt_path = self.make_candidate(
                root
            )
            resting = Image.open(resting_path).convert("RGBA")
            candidate = Image.open(candidate_path).convert("RGBA")
            self.assertEqual(candidate.getpixel((40, 45)), resting.getpixel((40, 45)))
            self.assertEqual(candidate.getpixel((15, 25)), resting.getpixel((15, 25)))
            self.assertNotEqual(candidate.tobytes(), resting.tobytes())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertFalse(receipt["runtime_admitted"])
            self.assertFalse(receipt["outside_mouth_change"])
            self.assertFalse(receipt["outside_articulation_change"])
            self.assertEqual(
                receipt["method"],
                "pair_specific_connected_mandible_patch_v1",
            )
            self.assertEqual(
                receipt["upper_beak_policy"], "immutable_source_pixels"
            )
            self.assertGreaterEqual(
                receipt["mandible_connected_ratio"],
                receipt["minimum_connected_ratio"],
            )
            self.assertTrue(receipt["beak_anatomy"]["passed"])

    def test_promotion_preserves_prior_receipt_and_requires_passing_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resting_path, _, candidate_path, candidate_receipt_path = (
                self.make_candidate(root)
            )
            old_speaking = root / "old-speaking.png"
            Image.open(resting_path).save(old_speaking)
            receipt_path = root / "pair-receipt.json"
            audit_path = root / "pair-audit.json"
            history_path = root / "pair-receipt-history.json"
            candidate_audit_path = root / "candidate-audit.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "resting_path": resting_path.as_posix(),
                        "resting_sha256": sha256_path(resting_path),
                        "speaking_path": old_speaking.as_posix(),
                        "speaking_sha256": sha256_path(old_speaking),
                    }
                ),
                encoding="utf-8",
            )
            audit_path.write_text(
                json.dumps({"schema_version": 2, "passed": True}),
                encoding="utf-8",
            )
            candidate_audit_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "passed": True,
                        "resting_path": resting_path.as_posix(),
                        "resting_sha256": sha256_path(resting_path),
                        "speaking_path": candidate_path.as_posix(),
                        "speaking_sha256": sha256_path(candidate_path),
                    }
                ),
                encoding="utf-8",
            )
            result = promote_candidate(
                receipt_path,
                audit_path,
                candidate_receipt_path,
                candidate_audit_path,
                history_path,
                reviewer="pair-reviewer",
                reason="one-pair hinge repair",
                promoted_at="2026-08-07T12:00:00+00:00",
                root=root,
            )
            promoted = json.loads(receipt_path.read_text(encoding="utf-8"))
            history = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(result["history_entry_count"], 1)
            self.assertEqual(promoted["speaking_path"], "candidate.png")
            self.assertFalse(promoted["runtime_admitted"])
            self.assertEqual(len(history["entries"]), 1)
            self.assertEqual(
                history["entries"][0]["receipt"]["speaking_path"],
                old_speaking.as_posix(),
            )

            failed_audit = json.loads(
                candidate_audit_path.read_text(encoding="utf-8")
            )
            failed_audit["passed"] = False
            candidate_audit_path.write_text(
                json.dumps(failed_audit), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "must pass"):
                promote_candidate(
                    receipt_path,
                    audit_path,
                    candidate_receipt_path,
                    candidate_audit_path,
                    history_path,
                    reviewer="pair-reviewer",
                    reason="should fail",
                    root=root,
                )

    def test_pair_7_canonical_receipt_is_the_hinge_refined_candidate(self) -> None:
        root = Path(__file__).resolve().parents[2]
        pair_root = (
            root
            / "assets"
            / "reference"
            / "characters"
            / "kingfisher"
            / "legacy-pairs-v1"
            / "pair-work"
            / "007-front-three-quarter-right"
        )
        receipt = json.loads(
            (pair_root / "pair-receipt.json").read_text(encoding="utf-8")
        )
        audit = json.loads(
            (pair_root / "pair-audit.json").read_text(encoding="utf-8")
        )
        speaking_path = root / receipt["speaking_path"]
        resting_path = root / receipt["resting_path"]
        self.assertIn("v10-hinge-refined", speaking_path.name)
        self.assertEqual(receipt["method"], "pair_specific_connected_mandible_patch_v1")
        self.assertEqual(receipt["speaking_sha256"], sha256_path(speaking_path))
        self.assertEqual(receipt["resting_sha256"], sha256_path(resting_path))
        self.assertEqual(receipt["upper_beak_policy"], "immutable_source_pixels")
        self.assertFalse(receipt["outside_articulation_change"])
        self.assertFalse(receipt["runtime_admitted"])
        self.assertTrue(receipt["beak_anatomy"]["passed"])
        self.assertLess(receipt["beak_anatomy"]["opening_angle_degrees"], 25)
        self.assertTrue(audit["passed"])


if __name__ == "__main__":
    unittest.main()
