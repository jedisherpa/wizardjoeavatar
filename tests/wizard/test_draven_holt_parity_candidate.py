import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from wizard_avatar.hd_pose_artifact import HDPoseArtifact, HDPoseLibrary, sha256_path


ROOT = Path(__file__).resolve().parents[2]
PARITY_ROOT = ROOT / "assets" / "reference" / "joeville_48_parity"
CHARACTER_ROOT = PARITY_ROOT / "compiled" / "draven-holt"
INDEX_PATH = CHARACTER_ROOT / "library-index.json"
SOURCE_ARTIFACT_PATH = (
    CHARACTER_ROOT / "draven-holt-candidate-source-motion-v001.wjpose"
)
CANDIDATE_ARTIFACT_PATH = (
    CHARACTER_ROOT / "draven-holt-candidate-authored-parity-v001.wjpose"
)
AUTHORED_ROOT = PARITY_ROOT / "authored-source" / "draven-holt"
AUTHORED_FRAME_ROOT = AUTHORED_ROOT / "frames"
AUTHORED_MANIFEST_PATH = AUTHORED_ROOT / "authored-g7-g8-v001.json"
ALPHA_RECEIPTS_PATH = AUTHORED_ROOT / "alpha-extraction-receipts-v001.json"
CANONICAL_RECEIPTS_PATH = AUTHORED_ROOT / "canonicalization-receipts-v001.json"
CONTRACT_PATH = (
    PARITY_ROOT
    / "source-metadata"
    / "draven-holt"
    / "review-motion-contract-v001.json"
)

SOURCE_ARTIFACT_SHA256 = (
    "244627668d46ad2c552d2ec2d7f5d24ce4ef4750c3a423d097bee1929c01e724"
)
CANDIDATE_ARTIFACT_SHA256 = (
    "ac51bba7f40bd42b374857b3070d62716f878894b99190d76cd434f08a843e82"
)
INDEX_SHA256 = "6fc822bf34011fa0d3e110a1c261851c04ceadab35184e9e95db378b11ce0069"
AUTHORED_MANIFEST_SHA256 = (
    "9fed5b1dc78ffab132885742589ba5021a8602a33c5ca804ede562870897271c"
)
ALPHA_RECEIPTS_SHA256 = (
    "23cb83653f8a9de2bc4c71f96c6d303d732c481c868e883a136022c29789de26"
)
CANONICAL_RECEIPTS_SHA256 = (
    "b6ed2386bb2a372581b5ca680e23e1529a71dbf57db2443b35a918b39bf45273"
)
CONTRACT_SHA256 = (
    "10a9678fdcc13a902f7ad32c000e1ac3bfd8d5904c14b3e15903510c746b98b4"
)
AUTHORITY_SHA256 = (
    "740f35730f4aa1e6c6ef96be80115c5b0e117397f792d57fdf5360452bbe78c8"
)


def pose_ids(start: int, stop: int) -> list[str]:
    return [
        f"draven_holt_motion_{pose_number:03d}"
        for pose_number in range(start, stop)
    ]


def rgba_sha256(path: Path) -> str:
    with Image.open(path) as image:
        return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


class DravenHoltParityCandidateTests(unittest.TestCase):
    def test_candidate_preserves_36_sources_and_adds_12_unique_authored_graphs(
        self,
    ):
        self.assertEqual(sha256_path(SOURCE_ARTIFACT_PATH), SOURCE_ARTIFACT_SHA256)
        self.assertEqual(
            sha256_path(CANDIDATE_ARTIFACT_PATH), CANDIDATE_ARTIFACT_SHA256
        )
        self.assertEqual(sha256_path(INDEX_PATH), INDEX_SHA256)

        source = HDPoseArtifact(SOURCE_ARTIFACT_PATH)
        candidate = HDPoseArtifact(CANDIDATE_ARTIFACT_PATH)
        library = HDPoseLibrary(INDEX_PATH)
        expected = pose_ids(1, 49)

        self.assertEqual(source.header["pose_ids"], expected[:36])
        self.assertEqual(candidate.header["pose_ids"], expected)
        self.assertEqual(library.pose_ids, tuple(expected))
        self.assertEqual(len(set(library.pose_ids)), 48)
        self.assertTrue(library.index["review_projection"])
        self.assertFalse(library.index["runtime_admitted"])

        rgba_hashes = []
        for number, pose_id in enumerate(expected, start=1):
            actual = library.load_rgba(pose_id)
            rgba_hashes.append(hashlib.sha256(actual).hexdigest())
            if number <= 36:
                expected_rgba = source.load_rgba(pose_id)
            else:
                with Image.open(AUTHORED_FRAME_ROOT / f"{pose_id}.png") as image:
                    expected_rgba = image.convert("RGBA").tobytes()
            with self.subTest(pose_id=pose_id):
                self.assertEqual(actual, expected_rgba)
                self.assertFalse(
                    library.pose_metadata[pose_id]["runtime_admitted"]
                )
        self.assertEqual(len(set(rgba_hashes)), 48)

    def test_every_authored_frame_has_a_complete_receipt_chain(self):
        self.assertEqual(
            sha256_path(AUTHORED_MANIFEST_PATH), AUTHORED_MANIFEST_SHA256
        )
        self.assertEqual(sha256_path(ALPHA_RECEIPTS_PATH), ALPHA_RECEIPTS_SHA256)
        self.assertEqual(
            sha256_path(CANONICAL_RECEIPTS_PATH), CANONICAL_RECEIPTS_SHA256
        )
        manifest = json.loads(AUTHORED_MANIFEST_PATH.read_text(encoding="utf-8"))
        alpha_receipts = json.loads(
            ALPHA_RECEIPTS_PATH.read_text(encoding="utf-8")
        )
        canonical_receipts = json.loads(
            CANONICAL_RECEIPTS_PATH.read_text(encoding="utf-8")
        )
        alpha_by_pose = {
            Path(receipt["destination_path"]).stem: receipt
            for receipt in alpha_receipts
        }
        canonical_by_pose = {
            Path(receipt["destination_path"]).stem: receipt
            for receipt in canonical_receipts
        }
        frames = [
            frame
            for sequence_id in ("g7", "g8")
            for frame in manifest["sequences"][sequence_id]["frames"]
        ]

        self.assertEqual([frame["pose_id"] for frame in frames], pose_ids(37, 49))
        self.assertEqual(set(alpha_by_pose), set(pose_ids(37, 49)))
        self.assertEqual(set(canonical_by_pose), set(pose_ids(37, 49)))
        self.assertFalse(manifest["runtime_admitted"])

        for frame in frames:
            pose_id = frame["pose_id"]
            chroma_path = AUTHORED_ROOT / "chroma-source" / f"{pose_id}.png"
            alpha_path = AUTHORED_ROOT / "alpha-extracted" / f"{pose_id}.png"
            final_path = AUTHORED_ROOT / frame["source_path"]
            alpha_receipt = alpha_by_pose[pose_id]
            canonical_receipt = canonical_by_pose[pose_id]

            with Image.open(final_path) as image:
                rgba = image.convert("RGBA")
                pixels = rgba.getdata()
                bbox = rgba.getchannel("A").getbbox()
                corners = [
                    rgba.getpixel((0, 0)),
                    rgba.getpixel((1253, 0)),
                    rgba.getpixel((0, 1253)),
                    rgba.getpixel((1253, 1253)),
                ]

            with self.subTest(pose_id=pose_id):
                self.assertEqual(alpha_receipt["source_sha256"], sha256_path(chroma_path))
                self.assertEqual(
                    alpha_receipt["destination_sha256"], sha256_path(alpha_path)
                )
                self.assertEqual(
                    alpha_receipt["destination_rgba_sha256"],
                    rgba_sha256(alpha_path),
                )
                self.assertEqual(
                    canonical_receipt["source_sha256"], sha256_path(alpha_path)
                )
                self.assertEqual(
                    canonical_receipt["destination_sha256"],
                    sha256_path(final_path),
                )
                self.assertEqual(
                    canonical_receipt["destination_rgba_sha256"],
                    rgba_sha256(final_path),
                )
                self.assertEqual(
                    canonical_receipt["authority_manifest_sha256"],
                    AUTHORITY_SHA256,
                )
                self.assertEqual(frame["source_sha256"], sha256_path(final_path))
                self.assertEqual(frame["rgba_sha256"], rgba_sha256(final_path))
                self.assertTrue(canonical_receipt["resampled"])
                self.assertEqual(
                    canonical_receipt["resample_filter"], "lanczos"
                )
                self.assertGreater(canonical_receipt["scale"], 0.95)
                self.assertEqual(bbox[1], 69)
                self.assertEqual(bbox[3], 1185)
                self.assertTrue(all(pixel == (0, 0, 0, 0) for pixel in corners))
                self.assertTrue(
                    all(
                        alpha != 0 or (red, green, blue) == (0, 0, 0)
                        for red, green, blue, alpha in pixels
                    )
                )

    def test_motion_contract_and_runtime_boundaries_fail_closed(self):
        self.assertEqual(sha256_path(CONTRACT_PATH), CONTRACT_SHA256)
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))

        self.assertEqual(contract["artifact_sha256"], CANDIDATE_ARTIFACT_SHA256)
        self.assertEqual(contract["library_index_sha256"], INDEX_SHA256)
        self.assertEqual(
            contract["sequences"]["g7"]["family"], "foreman_status_exchange"
        )
        self.assertEqual(
            contract["sequences"]["g8"]["family"], "site_safety_intervention"
        )
        self.assertEqual(contract["sequences"]["g7"]["pose_ids"], pose_ids(37, 43))
        self.assertEqual(contract["sequences"]["g8"]["pose_ids"], pose_ids(43, 49))
        self.assertTrue(contract["review_projection"])
        self.assertFalse(contract["runtime_admitted"])
        self.assertTrue(all(not shard["runtime_admitted"] for shard in index["shards"]))
        self.assertTrue(
            all(
                not sequence["runtime_admitted"]
                for sequence in index["sequences"].values()
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            runtime_index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
            runtime_index["runtime_admitted"] = True
            path = Path(directory) / "runtime-library-index.json"
            path.write_text(json.dumps(runtime_index), encoding="utf-8")
            from wizard_avatar.server import create_app

            with self.assertRaisesRegex(
                ValueError, "alternate HD review library cannot be runtime-admitted"
            ):
                create_app(companion_mode=False, hd_review_index_path=path)


if __name__ == "__main__":
    unittest.main()
