import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.build_joeville_supplemental_identity import build_identity
from wizard_avatar.hd_pose_artifact import HDPoseArtifact, HDPoseLibrary, sha256_path
from wizard_avatar.stream import character_runtime_epoch_prefix


ROOT = Path(__file__).resolve().parents[2]
LIANA_ROOT = ROOT / "assets" / "reference" / "joeville_supplemental" / "liana"
MANIFEST_PATH = LIANA_ROOT / "identity-manifest-v001.json"
FRAME_PATH = (
    LIANA_ROOT
    / "authored-source"
    / "frames"
    / "liana_identity_front_v001.png"
)
LIORA_SOURCE = (
    ROOT
    / "assets"
    / "reference"
    / "joeville_48_parity"
    / "compiled"
    / "liora-kane"
    / "liora-kane-candidate-source-motion-v001.wjpose"
)


class LianaSupplementalIdentityTests(unittest.TestCase):
    def test_identity_manifest_is_additive_and_fail_closed(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

        self.assertEqual(manifest["character_id"], "liana")
        self.assertEqual(
            manifest["roster_state"], "supplemental_authored_character"
        )
        self.assertEqual(
            manifest["derived_identity"]["reference_character_id"],
            "liora-kane",
        )
        self.assertTrue(manifest["review_projection"])
        self.assertFalse(manifest["runtime_admitted"])
        self.assertNotIn("liana", LIORA_SOURCE.name)
        self.assertTrue(LIORA_SOURCE.is_file())
        self.assertNotIn(
            "liana",
            {
                character["character_id"]
                for character in json.loads(
                    (
                        ROOT
                        / "assets"
                        / "reference"
                        / "joeville_48_parity"
                        / "source-metadata"
                        / "parity-tracker-v001.json"
                    ).read_text(encoding="utf-8")
                )["characters"]
            },
        )

    def test_canonical_identity_has_transparency_and_expected_profile(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        with Image.open(FRAME_PATH) as image:
            image.load()
            rgba = image.convert("RGBA")

        self.assertEqual(image.format, "PNG")
        self.assertEqual(rgba.size, (1254, 1254))
        self.assertEqual(rgba.getchannel("A").getbbox(), (428, 69, 827, 1185))
        self.assertEqual(
            hashlib.sha256(rgba.tobytes()).hexdigest(),
            manifest["identity_pose"]["rgba_sha256"],
        )
        self.assertEqual(sha256_path(FRAME_PATH), manifest["identity_pose"]["sha256"])
        for corner in ((0, 0), (1253, 0), (0, 1253), (1253, 1253)):
            self.assertEqual(rgba.getpixel(corner), (0, 0, 0, 0))
        for receipt in manifest["receipt_chain"].values():
            receipt_value = json.loads(
                (LIANA_ROOT / receipt["path"]).read_text(encoding="utf-8")
            )
            self.assertFalse(Path(receipt_value["source_path"]).is_absolute())
            self.assertFalse(
                Path(receipt_value["destination_path"]).is_absolute()
            )
            self.assertNotIn("/Users/", json.dumps(receipt_value))

    def test_repeatable_builder_emits_review_only_pixel_graph(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = build_identity(MANIFEST_PATH, Path(first_dir))
            second = build_identity(MANIFEST_PATH, Path(second_dir))

            self.assertEqual(first["artifact"]["sha256"], second["artifact"]["sha256"])
            self.assertEqual(
                first["library_index"]["sha256"],
                second["library_index"]["sha256"],
            )
            self.assertEqual(
                first["build_receipt"]["sha256"],
                second["build_receipt"]["sha256"],
            )
            library = HDPoseLibrary(Path(first_dir) / "library-index.json")
            artifact = HDPoseArtifact(
                Path(first_dir) / "liana-identity-review-v001.wjpose"
            )

        self.assertEqual(library.pose_ids, ("liana_identity_front_v001",))
        self.assertEqual(
            artifact.header["pose_ids"], ["liana_identity_front_v001"]
        )
        self.assertTrue(library.index["review_projection"])
        self.assertFalse(library.index["runtime_admitted"])
        self.assertFalse(
            library.pose_metadata["liana_identity_front_v001"][
                "runtime_admitted"
            ]
        )

    def test_runtime_epoch_namespace_is_character_specific(self):
        self.assertEqual(character_runtime_epoch_prefix("liana-v1"), "liana")
        self.assertEqual(
            character_runtime_epoch_prefix("liora-kane-v1"), "liora_kane"
        )

    def test_production_registry_remains_unchanged_and_fail_closed(self):
        registry = json.loads(
            (
                ROOT
                / "wizard_avatar"
                / "definitions"
                / "character_registry.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            [entry["character_id"] for entry in registry["characters"]],
            ["wizard-joe-v1"],
        )


if __name__ == "__main__":
    unittest.main()
