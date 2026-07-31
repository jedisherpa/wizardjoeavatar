import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEMO_PATH = ROOT / "web" / "avatar" / "wizardDemo.ts"
STYLE_PATH = ROOT / "web" / "avatar" / "style.css"
LEDGER_PATH = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "kingfisher"
    / "legacy-pairs-v1"
    / "pair-review-ledger.json"
)


class HdPairReviewUiTests(unittest.TestCase):
    def test_pair_review_is_explicit_and_uses_shared_pair_bounds(self):
        source = DEMO_PATH.read_text(encoding="utf-8")
        self.assertIn('params.get("hd-pair-review")', source)
        self.assertIn("HD pair-review sequence must contain closed/open pairs", source)
        self.assertIn("Promise.all([", source)
        self.assertIn("unionBounds(", source)
        self.assertIn("fitPairReviewPresentation(", source)
        self.assertIn("pairReview: true", source)

    def test_pair_review_exposes_stable_navigation_state(self):
        source = DEMO_PATH.read_text(encoding="utf-8")
        self.assertIn("data-pair-previous", source)
        self.assertIn("data-pair-next", source)
        self.assertIn("data-pair-closed", source)
        self.assertIn("data-pair-open", source)
        self.assertIn("data-pair-play", source)
        self.assertIn("document.body.dataset.hdPairNumber", source)
        self.assertIn("document.body.dataset.hdPairState", source)
        self.assertIn('url.searchParams.set("pair"', source)

    def test_pair_review_controls_fit_desktop_and_mobile(self):
        styles = STYLE_PATH.read_text(encoding="utf-8")
        self.assertIn(".hd-pair-review-controls", styles)
        self.assertIn("grid-template-columns: repeat(5, 34px)", styles)
        self.assertIn("left: 8px;", styles)
        self.assertIn("right: 8px;", styles)
        self.assertIn("minmax(0, 1fr)", styles)

    def test_visible_failures_remain_review_only_and_blocked(self):
        ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        by_ordinal = {
            int(pair["ordinal"]): pair
            for pair in ledger["pairs"]
        }
        for ordinal in (59, 62):
            pair = by_ordinal[ordinal]
            self.assertEqual(
                pair["internal_visual_review"]["state"],
                "needs_rebuild",
            )
            self.assertFalse(pair["runtime_admitted"])
            self.assertFalse(pair["user_approved"])
            self.assertFalse(
                pair["internal_visual_review"]["runtime_admission_implied"]
            )
            self.assertFalse(
                pair["internal_visual_review"]["user_approval_implied"]
            )


if __name__ == "__main__":
    unittest.main()
