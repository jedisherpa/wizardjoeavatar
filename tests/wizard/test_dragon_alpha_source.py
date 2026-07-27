import hashlib
import json
import unittest

from tools.import_dragon_alpha_source import DEFAULT_SOURCE_ROOT


class DragonAlphaSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            (DEFAULT_SOURCE_ROOT / "source-manifest-v001.json").read_text(
                encoding="utf-8"
            )
        )

    def test_inventory_is_complete_and_fail_closed(self):
        self.assertEqual(self.manifest["expected_asset_count"], 91)
        self.assertEqual(self.manifest["validated_asset_count"], 84)
        self.assertEqual(self.manifest["blocked_asset_count"], 7)
        self.assertEqual(
            self.manifest["blocked_asset_ids"],
            ["CAN007", "ACT007", "ACT011", "ACT025", "ACT032", "ACT044", "ACT060"],
        )
        self.assertEqual(self.manifest["approval_state"], "source_incomplete")
        self.assertFalse(self.manifest["review_projection"])
        self.assertFalse(self.manifest["runtime_admitted"])

    def test_only_validated_assets_are_preserved(self):
        for record in self.manifest["assets"]:
            path = DEFAULT_SOURCE_ROOT / "alphas" / record["filename"]
            with self.subTest(asset_id=record["asset_id"]):
                if record["status"] == "validated_source":
                    self.assertTrue(path.is_file())
                    self.assertEqual(
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                        record["sha256"],
                    )
                    self.assertEqual(
                        record["image_audit"]["opaque_pixel_count"],
                        record["expected_opaque_pixel_count"],
                    )
                else:
                    self.assertFalse(path.exists())
                    self.assertIn("validation_error", record)

    def test_standalone_canonicals_confirm_but_do_not_repair_archive(self):
        confirmations = self.manifest["standalone_canonical_confirmations"]
        self.assertEqual(len(confirmations), 11)
        self.assertTrue(
            all(item["matches_main_archive_payload"] for item in confirmations)
        )
        can007 = next(item for item in confirmations if item["asset_id"] == "CAN007")
        record = next(
            item for item in self.manifest["assets"] if item["asset_id"] == "CAN007"
        )
        self.assertEqual(can007["sha256"], record["sha256"])
        self.assertEqual(record["status"], "blocked_damaged_source")


if __name__ == "__main__":
    unittest.main()
