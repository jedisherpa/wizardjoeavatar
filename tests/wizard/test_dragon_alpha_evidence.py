import hashlib
import json
import unittest

from tools.preserve_dragon_alpha_evidence import DEFAULT_EVIDENCE_ROOT


class DragonAlphaEvidenceTests(unittest.TestCase):
    def test_mislabeled_frames_are_preserved_but_not_admitted(self):
        manifest = json.loads(
            (DEFAULT_EVIDENCE_ROOT / "source-evidence-manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(manifest["frame_count"], 20)
        self.assertEqual(manifest["observed_identity"], "dragon")
        self.assertEqual(manifest["source_label_status"], "mislabeled_as_robin")
        self.assertEqual(manifest["approval_state"], "quarantined_source_evidence")
        self.assertFalse(manifest["review_projection"])
        self.assertFalse(manifest["runtime_admitted"])
        self.assertEqual(
            [record["ordinal"] for record in manifest["frames"]],
            list(range(11, 31)),
        )
        for record in manifest["frames"]:
            path = DEFAULT_EVIDENCE_ROOT / record["path"]
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    record["sha256"],
                )
                self.assertEqual(record["image_audit"]["canvas_size"], [1920, 1080])
                self.assertEqual(record["image_audit"]["mode"], "RGBA")


if __name__ == "__main__":
    unittest.main()
