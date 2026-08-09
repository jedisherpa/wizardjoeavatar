import json
import tempfile
import unittest
from pathlib import Path

from tools.build_kingfisher_runtime_candidate import build_candidate


ROOT = Path(__file__).resolve().parents[2]
SHIPPING_INDEX = ROOT / "assets/reference/characters/kingfisher/compiled/library-index.json"
REVIEW_INDEX = ROOT / "assets/reference/characters/kingfisher/pair-review-compiled/library-index.json"


class DeferredKingfisherRuntimeCandidateTests(unittest.TestCase):
    def test_incomplete_pair_review_cannot_build_a_runtime_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "pair review must be complete"):
                build_candidate(REVIEW_INDEX, Path(temporary))

    def test_existing_library_remains_the_shipping_boundary(self) -> None:
        shipping = json.loads(SHIPPING_INDEX.read_text(encoding="utf-8"))
        review = json.loads(REVIEW_INDEX.read_text(encoding="utf-8"))

        self.assertEqual(110, shipping["pose_count"])
        self.assertNotIn("kingfisher-paired-beaks-review", shipping["sequences"])
        self.assertEqual(176, review["pose_count"])
        self.assertIn("kingfisher-paired-beaks-review", review["sequences"])
        self.assertFalse(review["legacy_pair_review"]["runtime_admitted"])
        self.assertEqual(0, review["legacy_pair_review"]["integrated_speech_pair_count"])


if __name__ == "__main__":
    unittest.main()
