from __future__ import annotations

import unittest

from tools.verify_deferred_kingfisher_scope import verify_deferred_scope


class DeferredKingfisherScopeTests(unittest.TestCase):
    @staticmethod
    def _fixtures() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        pair = {"ordinal": 1, "runtime_admitted": False, "user_approved": False}
        shipping = {
            "character_id": "kingfisher",
            "asset_set_id": "kingfisher-shipping",
            "sequences": {"kingfisher-all": {}},
        }
        review = {
            "character_id": "kingfisher",
            "asset_set_id": "kingfisher-pair-review",
            "legacy_pair_review": {
                "pair_count": 1,
                "runtime_admitted": False,
                "integrated_speech_pair_count": 0,
                "excluded_speech_pair_count": 1,
                "user_approved_count": 0,
                "pairs": [dict(pair)],
            },
        }
        ledger = {
            "pairs": [dict(pair)],
            "pairwise_full_size_review_summary": {"complete": False},
        }
        return shipping, review, ledger

    def test_accepts_fully_excluded_deferred_pairs(self) -> None:
        self.assertEqual([], verify_deferred_scope(*self._fixtures()))

    def test_rejects_runtime_admission(self) -> None:
        shipping, review, ledger = self._fixtures()
        review["legacy_pair_review"]["pairs"][0]["runtime_admitted"] = True
        self.assertIn(
            "review index pair 1 is runtime-admitted",
            verify_deferred_scope(shipping, review, ledger),
        )

    def test_rejects_deferred_sequence_in_shipping_library(self) -> None:
        shipping, review, ledger = self._fixtures()
        shipping["sequences"]["kingfisher-paired-beaks-review"] = {}
        self.assertIn(
            "shipping index exposes the deferred paired-beak sequence",
            verify_deferred_scope(shipping, review, ledger),
        )
