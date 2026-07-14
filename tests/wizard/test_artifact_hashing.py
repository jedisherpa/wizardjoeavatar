import json
import unittest
from pathlib import Path

from wizard_avatar.artifact_hashing import (
    MAX_SAFE_INTEGER,
    CanonicalJSONError,
    artifact_identity_hash,
    canonical_json_v1,
    sha256_ref,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "audiobook_contracts"
    / "canonical_json_v1_vectors.json"
)


class ArtifactHashingTests(unittest.TestCase):
    def test_cross_language_golden_vectors(self):
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

        for vector in fixture["vectors"]:
            with self.subTest(vector=vector["id"]):
                encoded = canonical_json_v1(vector["value"])
                self.assertEqual(encoded, vector["canonical_utf8"].encode("utf-8"))
                self.assertEqual(sha256_ref(encoded), vector["sha256"])

    def test_object_keys_use_unicode_code_point_order_and_arrays_keep_order(self):
        value = {"\U0001f600": [3, 2, 1], "\ue000": [], "\u00e9": "ok"}
        self.assertEqual(
            canonical_json_v1(value).decode("utf-8"),
            '{"\u00e9":"ok","\ue000":[],"\U0001f600":[3,2,1]}',
        )

    def test_identity_hash_hashes_only_the_declared_mapping(self):
        identity = {"media": "fixture", "revision": 1}
        self.assertEqual(
            artifact_identity_hash(identity),
            sha256_ref(canonical_json_v1(identity)),
        )

    def test_rejects_floats_and_non_json_python_values(self):
        invalid = (
            1.0,
            {"nested": float("nan")},
            b"bytes",
            (1, 2),
            {"set"},
            {1: "non-string-key"},
            object(),
        )
        for value in invalid:
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(CanonicalJSONError):
                    canonical_json_v1(value)

    def test_rejects_lone_surrogates_and_out_of_range_integers(self):
        invalid = (
            "\ud800",
            {"\udfff": "key"},
            MAX_SAFE_INTEGER + 1,
            -MAX_SAFE_INTEGER - 1,
        )
        for value in invalid:
            with self.subTest(value=repr(value)):
                with self.assertRaises(CanonicalJSONError):
                    canonical_json_v1(value)

    def test_sha256_ref_requires_bytes(self):
        self.assertEqual(
            sha256_ref(b""),
            "sha256:e3b0c44298fc1c149afbf4c8996fb924"
            "27ae41e4649b934ca495991b7852b855",
        )
        with self.assertRaises(TypeError):
            sha256_ref(bytearray())


if __name__ == "__main__":
    unittest.main()
