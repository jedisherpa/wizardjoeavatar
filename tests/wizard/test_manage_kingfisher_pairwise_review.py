from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.manage_kingfisher_pairwise_review import (
    PROTOCOL_ID,
    capture_pairwise_evidence,
    invalidate_pairwise_reviews,
    initialize_pairwise_review,
    record_pairwise_review,
)


class ManageKingfisherPairwiseReviewTests(unittest.TestCase):
    def _ledger(self, root: Path) -> Path:
        path = root / "ledger.json"
        pairs = []
        for ordinal in range(1, 67):
            prior_state = (
                "not_observable"
                if ordinal == 4
                else "needs_rebuild"
                if ordinal == 59
                else "pass"
            )
            pairs.append(
                {
                    "ordinal": ordinal,
                    "user_approved": False,
                    "runtime_admitted": False,
                    "internal_visual_review": {
                        "state": prior_state,
                        "defect_codes": (
                            ["thin_mandible"]
                            if prior_state == "needs_rebuild"
                            else []
                        ),
                        "note": f"prior {prior_state}",
                        "evidence_path": f"prior/{ordinal:03d}.png",
                        "reviewed_at": "2026-07-30T00:00:00+00:00",
                        "reviewer": "prior-reviewer",
                    },
                }
            )
        path.write_text(
            json.dumps(
                {
                    "character_id": "kingfisher",
                    "pairs": pairs,
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_initialization_invalidates_batch_passes_without_erasing_them(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger = self._ledger(Path(temporary))
            summary = initialize_pairwise_review(
                ledger,
                queued_at="2026-07-31T00:00:00+00:00",
            )
            saved = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(
                saved["pairs"][0]["internal_visual_review"]["state"],
                "pass",
            )
            self.assertEqual(
                saved["pairs"][0]["pairwise_full_size_review"]["state"],
                "pending",
            )
            self.assertEqual(
                saved["pairs"][3]["pairwise_full_size_review"]["state"],
                "not_observable",
            )
            self.assertEqual(
                saved["pairs"][58]["pairwise_full_size_review"]["state"],
                "needs_rebuild",
            )
            self.assertEqual(summary["pending_count"], 64)
            self.assertFalse(summary["complete"])

    def test_initialization_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger = self._ledger(Path(temporary))
            initialize_pairwise_review(
                ledger,
                queued_at="2026-07-31T00:00:00+00:00",
            )
            before = ledger.read_bytes()
            initialize_pairwise_review(
                ledger,
                queued_at="2026-08-01T00:00:00+00:00",
            )
            self.assertEqual(ledger.read_bytes(), before)

    def test_records_one_pair_without_approval_or_runtime_admission(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger = self._ledger(Path(temporary))
            initialize_pairwise_review(
                ledger,
                queued_at="2026-07-31T00:00:00+00:00",
            )
            pair = record_pairwise_review(
                ledger,
                ordinal=1,
                state="pass",
                defect_codes=[],
                note="One coherent upper and lower beak.",
                evidence_path="full-size/pair-001.png",
                reviewer="pair-reviewer",
                reviewed_at="2026-07-31T01:00:00+00:00",
            )
            review = pair["pairwise_full_size_review"]
            self.assertEqual(review["state"], "pass")
            self.assertEqual(
                review["source_disposition"],
                "full_size_pairwise_review",
            )
            self.assertFalse(pair["user_approved"])
            self.assertFalse(pair["runtime_admitted"])
            saved = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(
                saved["pairwise_full_size_review_summary"]["pass_count"],
                1,
            )

    def test_rebuild_requires_a_defect_code(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger = self._ledger(Path(temporary))
            initialize_pairwise_review(
                ledger,
                queued_at="2026-07-31T00:00:00+00:00",
            )
            with self.assertRaisesRegex(ValueError, "defect code"):
                record_pairwise_review(
                    ledger,
                    ordinal=1,
                    state="needs_rebuild",
                    defect_codes=[],
                    note="",
                    evidence_path="full-size/pair-001.png",
                    reviewer="pair-reviewer",
                )

    def test_invalidation_preserves_prior_pass_and_returns_pair_to_pending(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger = self._ledger(Path(temporary))
            initialize_pairwise_review(
                ledger,
                queued_at="2026-07-31T00:00:00+00:00",
            )
            record_pairwise_review(
                ledger,
                ordinal=1,
                state="pass",
                defect_codes=[],
                note="Prior full-size pass.",
                evidence_path="full-size/pair-001.png",
                reviewer="pair-reviewer",
                reviewed_at="2026-07-31T01:00:00+00:00",
            )

            result = invalidate_pairwise_reviews(
                ledger,
                first_ordinal=1,
                last_ordinal=3,
                reason="User reported visible beak misalignment.",
                reporter="user-visual-review",
                invalidated_at="2026-08-01T18:00:00+00:00",
            )

            saved = json.loads(ledger.read_text(encoding="utf-8"))
            pair = saved["pairs"][0]
            self.assertEqual(result["invalidated_ordinals"], [1])
            self.assertEqual(
                pair["pairwise_full_size_review"]["state"],
                "pending",
            )
            self.assertEqual(
                pair["pairwise_full_size_review"]["source_disposition"],
                "user_reported_visual_recheck",
            )
            history = pair["pairwise_full_size_review_history"]
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["superseded_review"]["state"], "pass")
            self.assertEqual(
                history[0]["superseded_review"]["evidence_path"],
                "full-size/pair-001.png",
            )

    def test_capture_pairwise_evidence_uses_exact_pair_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pair_dir = root / "pair-work" / "001-neutral-front"
            pair_dir.mkdir(parents=True)
            resting = pair_dir / "resting.png"
            speaking = pair_dir / "speaking.png"
            Image.new("RGBA", (8, 6), (10, 20, 30, 255)).save(resting)
            Image.new("RGBA", (8, 6), (40, 50, 60, 255)).save(speaking)
            (pair_dir / "pair-receipt.json").write_text(
                json.dumps(
                    {
                        "resting_path": str(resting.relative_to(root)),
                        "speaking_path": str(speaking.relative_to(root)),
                    }
                ),
                encoding="utf-8",
            )
            ledger = {
                "character_id": "kingfisher",
                "pairs": [
                    {
                        "ordinal": 1,
                        "slug": "neutral-front",
                        "receipt_path": str(
                            (pair_dir / "pair-receipt.json").relative_to(root)
                        ),
                        "pairwise_full_size_review": {
                            "protocol_id": PROTOCOL_ID,
                            "state": "pass",
                        },
                    }
                ],
            }
            ledger_path = root / "pair-review-ledger.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            output_dir = root / "evidence" / "pair-001"

            receipt = capture_pairwise_evidence(
                ledger_path,
                ordinal=1,
                output_dir=output_dir,
                root=root,
            )

            self.assertEqual(receipt["state"], "pass")
            for name, expected in (
                ("closed-projector.png", (10, 20, 30)),
                ("open-projector.png", (40, 50, 60)),
            ):
                with Image.open(output_dir / name) as evidence:
                    self.assertEqual(evidence.size, (8, 48))
                    self.assertEqual(
                        evidence.convert("RGB").getpixel((4, 46)),
                        expected,
                    )


if __name__ == "__main__":
    unittest.main()
