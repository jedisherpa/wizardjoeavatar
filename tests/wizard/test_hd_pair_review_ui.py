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
        self.assertIn("HD pair-review sequence must contain closed/open pairs", source)
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
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", styles)

    def test_pair_comparison_assets_have_explicit_cache_version(self):
        index = INDEX_PATH.read_text(encoding="utf-8")
        self.assertEqual(index.count("hd-pair-compare-v7"), 2)

    def test_user_recheck_keeps_unreviewed_pairs_fail_closed(self):
        ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        by_ordinal = {
            int(pair["ordinal"]): pair
            for pair in ledger["pairs"]
        }
        summary = ledger["pairwise_full_size_review_summary"]

        self.assertFalse(summary["complete"])
        self.assertEqual(summary["pass_count"], 53)
        self.assertEqual(summary["pending_count"], 11)
        self.assertEqual(summary["needs_rebuild_count"], 0)
        self.assertEqual(summary["not_observable_count"], 2)
        self.assertEqual(
            by_ordinal[7]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-007-hinge-refined-2026-08-07-v1",
            by_ordinal[7]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[1]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-001-one-pair-2026-08-07-v3",
            by_ordinal[1]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[2]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-002-one-pair-2026-08-07-v3",
            by_ordinal[2]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[3]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-003-one-pair-2026-08-07-v3",
            by_ordinal[3]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[6]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-006-one-pair-2026-08-07-v4",
            by_ordinal[6]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[8]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-008-one-pair-2026-08-07-v4",
            by_ordinal[8]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[9]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-009-one-pair-2026-08-07-v4",
            by_ordinal[9]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[10]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-010-one-pair-2026-08-07-v4",
            by_ordinal[10]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[11]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-011-one-pair-2026-08-07-v4",
            by_ordinal[11]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[12]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-012-one-pair-2026-08-07-v4",
            by_ordinal[12]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[13]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-013-one-pair-2026-08-07-v4",
            by_ordinal[13]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[14]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-014-one-pair-2026-08-07-v4",
            by_ordinal[14]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[15]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-015-one-pair-2026-08-07-v4",
            by_ordinal[15]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[16]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-016-one-pair-2026-08-07-v4",
            by_ordinal[16]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[17]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-017-one-pair-2026-08-07-v4",
            by_ordinal[17]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[18]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-018-one-pair-2026-08-07-v4",
            by_ordinal[18]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[19]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-019-one-pair-2026-08-07-v4",
            by_ordinal[19]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[20]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-020-one-pair-2026-08-07-v4",
            by_ordinal[20]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[21]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-021-one-pair-2026-08-07-v4",
            by_ordinal[21]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[22]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-022-one-pair-2026-08-07-v4",
            by_ordinal[22]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[23]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-023-one-pair-2026-08-07-v4",
            by_ordinal[23]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[24]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-024-one-pair-2026-08-07-v4",
            by_ordinal[24]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[25]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-025-one-pair-2026-08-07-v4",
            by_ordinal[25]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[26]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-026-one-pair-2026-08-07-v4",
            by_ordinal[26]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[27]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-027-one-pair-2026-08-07-v4",
            by_ordinal[27]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[28]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-028-one-pair-2026-08-07-v4",
            by_ordinal[28]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[29]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-029-one-pair-2026-08-07-v4",
            by_ordinal[29]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[30]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-030-one-pair-2026-08-07-v4",
            by_ordinal[30]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[31]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-031-one-pair-2026-08-07-v4",
            by_ordinal[31]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[32]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-032-one-pair-2026-08-07-v4",
            by_ordinal[32]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[33]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-033-one-pair-2026-08-07-v4",
            by_ordinal[33]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[34]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-034-one-pair-2026-08-07-v4",
            by_ordinal[34]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[35]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-035-one-pair-2026-08-07-v4",
            by_ordinal[35]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[36]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-036-one-pair-2026-08-07-v4",
            by_ordinal[36]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[37]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-037-one-pair-2026-08-07-v4",
            by_ordinal[37]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[38]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-038-one-pair-2026-08-07-v4",
            by_ordinal[38]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[39]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-039-one-pair-2026-08-07-v4",
            by_ordinal[39]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[40]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-040-one-pair-2026-08-08-v4",
            by_ordinal[40]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[41]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-041-one-pair-2026-08-08-v4",
            by_ordinal[41]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[42]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-042-one-pair-2026-08-08-v4",
            by_ordinal[42]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[43]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-043-one-pair-2026-08-08-v4",
            by_ordinal[43]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[44]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-044-one-pair-2026-08-08-v4",
            by_ordinal[44]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[45]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-045-one-pair-2026-08-08-v4",
            by_ordinal[45]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[46]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-046-one-pair-2026-08-08-v4",
            by_ordinal[46]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[47]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-047-one-pair-2026-08-08-v4",
            by_ordinal[47]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[48]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-048-one-pair-2026-08-08-v4",
            by_ordinal[48]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[49]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-049-one-pair-2026-08-08-v4",
            by_ordinal[49]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[50]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-050-one-pair-2026-08-08-v4",
            by_ordinal[50]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[51]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-051-one-pair-2026-08-08-v4",
            by_ordinal[51]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[52]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-052-one-pair-2026-08-08-v4",
            by_ordinal[52]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[53]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-053-one-pair-2026-08-08-v4",
            by_ordinal[53]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[54]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-054-one-pair-2026-08-08-v4",
            by_ordinal[54]["pairwise_full_size_review"]["evidence_path"],
        )
        self.assertEqual(
            by_ordinal[55]["pairwise_full_size_review"]["state"],
            "pass",
        )
        self.assertIn(
            "pair-055-one-pair-2026-08-08-v4",
            by_ordinal[55]["pairwise_full_size_review"]["evidence_path"],
        )
        for ordinal, pair in by_ordinal.items():
            self.assertFalse(pair["runtime_admitted"])
            self.assertFalse(pair["user_approved"])
            if ordinal not in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55}:
                self.assertEqual(
                    pair["pairwise_full_size_review"]["state"],
                    "pending",
                )
                self.assertEqual(
                    pair["pairwise_full_size_review"]["source_disposition"],
                    "user_reported_visual_recheck",
                )



if __name__ == "__main__":
    unittest.main()
