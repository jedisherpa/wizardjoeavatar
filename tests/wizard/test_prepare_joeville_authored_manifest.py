import json
import tempfile
import unittest
from pathlib import Path

from tools.prepare_joeville_authored_manifest import _canonicalization_mode


class JoeVilleAuthoredManifestPreparationTests(unittest.TestCase):
    def test_reports_strict_translation_without_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                _canonicalization_mode(Path(directory)),
                "integer_translation_only_no_resampling",
            )

    def test_reports_source_normalization_and_oversize_fit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "alpha-extraction-receipts-v001.json").write_text(
                json.dumps([{"canvas_normalized": True}]),
                encoding="utf-8",
            )
            (root / "canonicalization-receipts-v001.json").write_text(
                json.dumps([{"resampled": True}]),
                encoding="utf-8",
            )

            self.assertEqual(
                _canonicalization_mode(root),
                (
                    "source_canvas_normalization_then_integer_translation_"
                    "with_opt_in_oversize_fit"
                ),
            )


if __name__ == "__main__":
    unittest.main()
