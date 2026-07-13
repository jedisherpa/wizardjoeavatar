import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = ROOT / "docs" / "pose-library-expansion" / "integration-specs"


class PoseIntegrationSpecTests(unittest.TestCase):
    def test_every_integration_spec_is_structurally_consistent(self):
        for path in sorted(SPEC_DIR.glob("*.json")):
            with self.subTest(path=path.name):
                spec = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(path.stem, spec["candidate_id"])
                self.assertEqual(spec["semantic_id"], spec["manifest"]["id"])
                self.assertEqual(spec["destination_filename"], spec["manifest"]["source"])
                self.assertTrue((ROOT / spec["source_path"]).is_file())
                self.assertGreater(spec["manifest"]["generation_rows"], 0)
                self.assertLessEqual(spec["manifest"]["generation_rows"], 96)
                self.assertIn("anchor_offsets", spec["manifest"])


if __name__ == "__main__":
    unittest.main()
