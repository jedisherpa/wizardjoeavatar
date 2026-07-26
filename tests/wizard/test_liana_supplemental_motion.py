import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.build_joeville_supplemental_character import (
    build_supplemental_character,
)
from wizard_avatar.hd_pose_artifact import HDPoseLibrary, sha256_path


ROOT = Path(__file__).resolve().parents[2]
LIANA_ROOT = ROOT / "assets" / "reference" / "joeville_supplemental" / "liana"
MANIFEST_PATH = LIANA_ROOT / "motion-manifest-v001.json"
INDEX_PATH = LIANA_ROOT / "compiled-motion" / "library-index.json"
ARTIFACT_PATH = (
    LIANA_ROOT
    / "compiled-motion"
    / "liana-candidate-supplemental-48-v001.wjpose"
)
FRAME_ROOT = LIANA_ROOT / "authored-source" / "frames"


class LianaSupplementalMotionTests(unittest.TestCase):
    def test_real_candidate_is_complete_unique_and_fail_closed(self):
        self.assertEqual(
            sha256_path(MANIFEST_PATH),
            "9d2306c87009fb5971c5c5811ba0d2d245c64079952c516aad56bc1153cf59bf",
        )
        self.assertEqual(
            sha256_path(ARTIFACT_PATH),
            "79535e1b310848bf23d3c8f5db170fdfc6657865a6fa8e0f03040d80630bafee",
        )
        self.assertEqual(
            sha256_path(INDEX_PATH),
            "ff6972de47681a8e3a710b880fff53ca8da205e51f01f314073db409ff4a9d19",
        )

        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        library = HDPoseLibrary(INDEX_PATH)
        self.assertEqual(manifest["pose_count"], 48)
        self.assertEqual(len(library.pose_ids), 48)
        self.assertEqual(manifest["sequence_order"], [f"g{i}" for i in range(1, 9)])
        self.assertTrue(manifest["review_projection"])
        self.assertFalse(manifest["runtime_admitted"])
        self.assertTrue(library.index["review_projection"])
        self.assertFalse(library.index["runtime_admitted"])
        self.assertEqual(library.index["approved_pose_count"], 0)
        self.assertEqual(library.index["candidate_pose_count"], 48)
        index_poses = {
            pose["pose_id"]: pose for pose in library.index["poses"]
        }

        source_hashes = set()
        rgba_hashes = set()
        for pose_number in range(1, 49):
            pose_id = f"liana_motion_{pose_number:03d}"
            metadata = library.pose_metadata[pose_id]
            index_pose = index_poses[pose_id]
            source_path = FRAME_ROOT / f"{pose_id}.png"
            with Image.open(source_path) as image:
                rgba = image.convert("RGBA")
            bbox = rgba.getchannel("A").getbbox()

            with self.subTest(pose_id=pose_id):
                self.assertEqual(rgba.size, (1254, 1254))
                self.assertIsNotNone(bbox)
                self.assertGreaterEqual(bbox[0], 69)
                self.assertGreaterEqual(bbox[1], 69)
                self.assertLessEqual(bbox[2], 1254 - 69)
                self.assertEqual(bbox[3], 1185)
                self.assertFalse(metadata["runtime_admitted"])
                self.assertEqual(
                    hashlib.sha256(rgba.tobytes()).hexdigest(),
                    index_pose["rgba_sha256"],
                )
                self.assertEqual(library.load_rgba(pose_id), rgba.tobytes())
                self.assertTrue(
                    all(
                        r == g == b == 0
                        for r, g, b, a in rgba.getdata()
                        if a == 0
                    )
                )
            source_hashes.add(sha256_path(source_path))
            rgba_hashes.add(hashlib.sha256(rgba.tobytes()).hexdigest())

        self.assertEqual(len(source_hashes), 48)
        self.assertEqual(len(rgba_hashes), 48)

    def test_two_clean_builds_are_bit_identical(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as first_dir:
            with tempfile.TemporaryDirectory(dir=ROOT) as second_dir:
                first = build_supplemental_character(
                    character_id="liana",
                    manifest_path=MANIFEST_PATH,
                    output_dir=Path(first_dir),
                    project_root=ROOT,
                )
                second = build_supplemental_character(
                    character_id="liana",
                    manifest_path=MANIFEST_PATH,
                    output_dir=Path(second_dir),
                    project_root=ROOT,
                )

        self.assertEqual(first["artifact_sha256"], second["artifact_sha256"])
        self.assertEqual(
            first["library_index_sha256"],
            second["library_index_sha256"],
        )
        self.assertEqual(
            first["artifact_sha256"],
            "79535e1b310848bf23d3c8f5db170fdfc6657865a6fa8e0f03040d80630bafee",
        )
        self.assertEqual(
            first["library_index_sha256"],
            "ff6972de47681a8e3a710b880fff53ca8da205e51f01f314073db409ff4a9d19",
        )

    def test_production_registry_is_not_promoted_by_review_candidate(self):
        registry = json.loads(
            (
                ROOT
                / "wizard_avatar"
                / "definitions"
                / "character_registry.json"
            ).read_text(encoding="utf-8")
        )
        self.assertNotIn(
            "liana",
            {entry["character_id"] for entry in registry["characters"]},
        )


if __name__ == "__main__":
    unittest.main()
