import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEMO_PATH = ROOT / "web" / "avatar" / "wizardDemo.ts"
STYLE_PATH = ROOT / "web" / "avatar" / "style.css"
INDEX_PATH = ROOT / "web" / "avatar" / "index.html"
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
        self.assertIn('reviewSequence === "kingfisher-all"', source)
        self.assertIn(
            'pairReviewSequence = "kingfisher-paired-beaks-review"',
            source,
        )
        self.assertIn(
            "HD pair-review sequence must contain closed/open pairs",
            source,
        )
        self.assertIn("Promise.all([", source)
        self.assertIn("unionBounds(", source)
        self.assertIn("differenceBoundsRgba(", source)
        self.assertIn("expandPairFocusBounds(", source)
        self.assertIn("canvasElement.style.clipPath", source)
        self.assertIn("fitPairReviewPresentation(", source)
        self.assertIn('reviewFraming === "beak" ? 1 : 0.1', source)
        self.assertIn('comparisonMode: "locked-side-by-side"', source)
        self.assertIn('openCanvas.configure(width, height, "rgba")', source)
        self.assertIn("canvas.draw(presentPose(pairFrames[0]))", source)
        self.assertIn("openCanvas.draw(presentPose(pairFrames[1]))", source)
        self.assertIn("pairReview: true", source)

    def test_pair_review_exposes_stable_navigation_state(self):
        source = DEMO_PATH.read_text(encoding="utf-8")
        self.assertIn("data-pair-previous", source)
        self.assertIn("data-pair-next", source)
        self.assertIn("data-pair-closed", source)
        self.assertIn("data-pair-open", source)
        self.assertIn("data-pair-play", source)
        self.assertIn("data-pair-framing", source)
        self.assertIn("openCanvasElement.dataset.pairActive", source)
        self.assertIn("document.body.dataset.hdPairNumber", source)
        self.assertIn("document.body.dataset.hdPairState", source)
        self.assertIn("document.body.dataset.hdPairDisposition", source)
        self.assertIn("sequence.pair_review_states", source)
        self.assertIn(
            "HD pair-review dispositions must match pair count",
            source,
        )
        self.assertIn('url.searchParams.set("pair"', source)

    def test_pair_review_controls_fit_desktop_and_mobile(self):
        styles = STYLE_PATH.read_text(encoding="utf-8")
        self.assertIn(".hd-pair-review-controls", styles)
        self.assertIn("grid-template-columns: repeat(6, 34px)", styles)
        self.assertIn("left: 8px;", styles)
        self.assertIn("right: 8px;", styles)
        self.assertIn("minmax(0, 1fr)", styles)
        self.assertIn(".hd-pair-comparison-labels", styles)
        self.assertIn('[data-pair-active="false"]', styles)
        self.assertIn(
            "grid-template-columns: repeat(2, minmax(0, 1fr))",
            styles,
        )

    def test_pair_comparison_assets_have_explicit_cache_version(self):
        index = INDEX_PATH.read_text(encoding="utf-8")
        self.assertEqual(index.count("hd-pair-compare-v7"), 2)

    def test_user_report_reopens_every_observable_pair_fail_closed(self):
        ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        summary = ledger["pairwise_full_size_review_summary"]
        pairs = ledger["pairs"]

        self.assertFalse(summary["complete"])
        self.assertEqual(summary["pass_count"], 0)
        self.assertEqual(summary["pending_count"], 63)
        self.assertEqual(summary["needs_rebuild_count"], 1)
        self.assertEqual(summary["not_observable_count"], 2)
        self.assertEqual(summary["passing_disposition_count"], 2)
        for pair in pairs:
            self.assertFalse(pair["runtime_admitted"])
            self.assertFalse(pair["user_approved"])
            review = pair["pairwise_full_size_review"]
            if review["state"] == "not_observable":
                continue
            if int(pair["ordinal"]) == 1:
                self.assertEqual(review["state"], "needs_rebuild")
                self.assertIn(
                    "awaiting_user_visual_approval",
                    review["defect_codes"],
                )
                self.assertIn(
                    "Pair rebuilt one-at-a-time",
                    review["note"],
                )
                continue
            self.assertEqual(review["state"], "pending")
            self.assertEqual(
                review["source_disposition"],
                "user_reported_visual_recheck",
            )
            self.assertEqual(review["evidence_path"], "")
            self.assertIn(
                "one-pair render workflow",
                review["note"],
            )


if __name__ == "__main__":
    unittest.main()
