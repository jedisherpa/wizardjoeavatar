import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageOps

from tools.build_dragon_interim_candidates import (
    DEFAULT_OUTPUT,
    MIRRORS,
    build_dragon_interim_candidates,
)


class DragonInterimCandidateTests(unittest.TestCase):
    def test_partial_build_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "interim"
            manifest = build_dragon_interim_candidates(output)
            self.assertEqual(manifest["candidate_count"], 2)
            self.assertEqual(manifest["expected_candidate_count"], 48)
            self.assertEqual(len(manifest["missing_asset_ids"]), 46)
            self.assertFalse(manifest["review_projection"])
            self.assertFalse(manifest["runtime_admitted"])
            self.assertEqual(
                manifest["approval_state"], "candidate_inventory_incomplete"
            )

    def test_mirrors_are_exact_and_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "interim"
            first = build_dragon_interim_candidates(output)
            first_bytes = (
                output / "interim-candidate-manifest-v001.json"
            ).read_bytes()
            second = build_dragon_interim_candidates(output)
            self.assertEqual(first, second)
            self.assertEqual(
                first_bytes,
                (output / "interim-candidate-manifest-v001.json").read_bytes(),
            )
            by_id = {record["asset_id"]: record for record in first["assets"]}
            for asset_id, (_, source_path, _) in MIRRORS.items():
                with self.subTest(asset_id=asset_id):
                    with Image.open(source_path) as source:
                        expected = ImageOps.mirror(source.convert("RGBA")).tobytes()
                    output_path = output / "alphas" / Path(by_id[asset_id]["path"]).name
                    with Image.open(output_path) as actual:
                        observed = actual.convert("RGBA").tobytes()
                    self.assertEqual(
                        hashlib.sha256(expected).hexdigest(),
                        hashlib.sha256(observed).hexdigest(),
                    )

    def test_workspace_manifest_remains_review_only(self):
        manifest_path = DEFAULT_OUTPUT / "interim-candidate-manifest-v001.json"
        if not manifest_path.is_file():
            self.skipTest("workspace interim manifest has not been built")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertFalse(manifest["review_projection"])
        self.assertFalse(manifest["runtime_admitted"])
        self.assertEqual(manifest["candidate_count"], 48)
        self.assertEqual(manifest["missing_asset_ids"], [])
        generated = [
            record
            for record in manifest["assets"]
            if record["method"]
            == "identity_locked_image_generation_then_chroma_extraction"
        ]
        self.assertEqual(len(generated), 46)
        for record in generated:
            with self.subTest(asset_id=record["asset_id"]):
                self.assertTrue(record["generation_intent"])
                self.assertEqual(
                    record["prompt_contract_id"],
                    manifest["prompt_contract_id"],
                )
                self.assertEqual(len(record["chroma_source_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
