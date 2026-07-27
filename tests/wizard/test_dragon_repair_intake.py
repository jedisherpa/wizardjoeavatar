import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.build_dragon_repair_intake import (
    DEFAULT_EVIDENCE_MANIFEST,
    DEFAULT_OUTPUT,
    DEFAULT_SOURCE_MANIFEST,
    build_dragon_repair_intake,
)


class DragonRepairIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    def test_repair_inventory_is_explicit_and_fail_closed(self):
        self.assertEqual(self.manifest["blocked_asset_count"], 7)
        self.assertEqual(self.manifest["candidate_asset_count"], 2)
        self.assertEqual(self.manifest["missing_asset_count"], 5)
        self.assertEqual(
            self.manifest["candidate_asset_ids"], ["ACT011", "ACT025"]
        )
        self.assertEqual(
            self.manifest["missing_asset_ids"],
            ["CAN007", "ACT007", "ACT032", "ACT044", "ACT060"],
        )
        self.assertFalse(self.manifest["complete_replacement_inventory"])
        self.assertFalse(self.manifest["review_projection"])
        self.assertFalse(self.manifest["runtime_admitted"])
        self.assertEqual(
            self.manifest["approval_state"], "source_repair_incomplete"
        )

    def test_candidates_are_intact_but_not_canonically_approved(self):
        records = {
            record["asset_id"]: record for record in self.manifest["assets"]
        }
        self.assertEqual(
            records["ACT011"]["candidate"]["opaque_pixel_delta"],
            26,
        )
        self.assertEqual(
            records["ACT025"]["candidate"]["opaque_pixel_delta"],
            -11307,
        )
        for asset_id in ("ACT011", "ACT025"):
            with self.subTest(asset_id=asset_id):
                record = records[asset_id]
                self.assertEqual(
                    record["status"], "candidate_metric_delta_requires_approval"
                )
                self.assertEqual(record["replacement_approval"], "not_approved")
                self.assertEqual(
                    record["candidate"]["canonical_equivalence_review"], "pending"
                )
                path = DEFAULT_OUTPUT.parents[5] / record["candidate"]["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    record["candidate"]["sha256"],
                )

    def test_same_name_paired_bird_art_is_rejected(self):
        records = {
            record["asset_id"]: record for record in self.manifest["assets"]
        }
        for asset_id in ("ACT007", "ACT011", "ACT025", "ACT032", "ACT044", "ACT060"):
            with self.subTest(asset_id=asset_id):
                rejected = records[asset_id]["rejected_same_name_alternative"]
                self.assertEqual(rejected["identity_order"], ["robin", "speech"])
                self.assertIn("not Dragon", rejected["rejection_reason"])

    def test_rebuild_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.json"
            second = Path(temporary) / "second.json"
            build_dragon_repair_intake(output_path=first)
            build_dragon_repair_intake(output_path=second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(
                json.loads(first.read_text(encoding="utf-8")),
                self.manifest,
            )

    def test_non_dragon_evidence_fails_closed(self):
        evidence = json.loads(DEFAULT_EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
        evidence["observed_identity"] = "robin"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_path = root / "source-evidence-manifest.json"
            evidence_path.write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "observed_identity=dragon"):
                build_dragon_repair_intake(
                    source_manifest_path=DEFAULT_SOURCE_MANIFEST,
                    evidence_manifest_path=evidence_path,
                    output_path=root / "output.json",
                )


if __name__ == "__main__":
    unittest.main()
