from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.record_kingfisher_pair_visual_review import record_visual_review


class RecordKingfisherPairVisualReviewTests(unittest.TestCase):
    def _ledger(self, root: Path) -> Path:
        path = root / "pair-review-ledger.json"
        path.write_text(
            json.dumps(
                {
                    "pairs": [
                        {
                            "ordinal": 1,
                            "user_approved": False,
                            "runtime_admitted": False,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_records_internal_pass_without_implying_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = self._ledger(Path(temporary))
            pair = record_visual_review(
                ledger,
                ordinal=1,
                state="pass",
                defect_codes=[],
                note="Hinge and upper beak are stable.",
                evidence_path="detail-boards/pair-detail-page-01.png",
                reviewer="test-reviewer",
                reviewed_at="2026-07-30T00:00:00+00:00",
            )
            review = pair["internal_visual_review"]
            self.assertEqual(review["state"], "pass")
            self.assertFalse(review["user_approval_implied"])
            self.assertFalse(review["runtime_admission_implied"])
            self.assertFalse(pair["user_approved"])
            self.assertFalse(pair["runtime_admitted"])
            saved = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(
                saved["internal_visual_review_summary"],
                {
                    "schema_version": 1,
                    "reviewed_count": 1,
                    "pass_count": 1,
                    "needs_rebuild_count": 0,
                    "not_observable_count": 0,
                    "unreviewed_count": 0,
                    "user_approval_implied": False,
                    "runtime_admission_implied": False,
                },
            )

    def test_needs_rebuild_requires_a_defect_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = self._ledger(Path(temporary))
            with self.assertRaisesRegex(ValueError, "defect code"):
                record_visual_review(
                    ledger,
                    ordinal=1,
                    state="needs_rebuild",
                    defect_codes=[],
                    note="",
                    evidence_path="detail.png",
                    reviewer="test-reviewer",
                )

    def test_refuses_runtime_admitted_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = self._ledger(Path(temporary))
            payload = json.loads(ledger.read_text(encoding="utf-8"))
            payload["pairs"][0]["runtime_admitted"] = True
            ledger.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "runtime-admitted"):
                record_visual_review(
                    ledger,
                    ordinal=1,
                    state="pass",
                    defect_codes=[],
                    note="",
                    evidence_path="detail.png",
                    reviewer="test-reviewer",
                )


if __name__ == "__main__":
    unittest.main()
