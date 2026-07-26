import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from wizard_avatar.hd_pose_artifact import HDPoseArtifact, HDPoseLibrary, sha256_path


ROOT = Path(__file__).resolve().parents[2]
PARITY_ROOT = ROOT / "assets" / "reference" / "joeville_48_parity"
CHARACTER_ROOT = PARITY_ROOT / "compiled" / "rohan-slate"
INDEX_PATH = CHARACTER_ROOT / "library-index.json"
SOURCE_ARTIFACT_PATH = (
    CHARACTER_ROOT / "rohan-slate-candidate-source-motion-v001.wjpose"
)
CANDIDATE_ARTIFACT_PATH = (
    CHARACTER_ROOT / "rohan-slate-candidate-authored-parity-v001.wjpose"
)
AUTHORED_ROOT = PARITY_ROOT / "authored-source" / "rohan-slate"
AUTHORED_FRAME_ROOT = AUTHORED_ROOT / "frames"
AUTHORED_MANIFEST_PATH = AUTHORED_ROOT / "authored-g7-g8-v001.json"
ALPHA_RECEIPTS_PATH = AUTHORED_ROOT / "alpha-extraction-receipts-v001.json"
CANONICAL_RECEIPTS_PATH = AUTHORED_ROOT / "canonicalization-receipts-v001.json"
CONTRACT_PATH = (
    PARITY_ROOT
    / "source-metadata"
    / "rohan-slate"
    / "review-motion-contract-v001.json"
)
RECONSTRUCTION_PATH = (
    PARITY_ROOT
    / "source-metadata"
    / "rohan-slate"
    / "reconstruction-manifest-parity-v001.json"
)
CONTACT_SHEET_PATH = (
    PARITY_ROOT
    / "source-metadata"
    / "rohan-slate"
    / "parity-motion-contact-sheet-v001.png"
)

SOURCE_ARTIFACT_SHA256 = (
    "32e480baa58081811621cceac92c9cf7ada6c0d958afe390ab3eaedadce32def"
)
CANDIDATE_ARTIFACT_SHA256 = (
    "005e1776a74acf7f63fccb1a8d93c2451ecc661ce58fac25d7c14f87741e8ce5"
)
INDEX_SHA256 = "442a03c4fa5c82f592dc0f0426fd13df3e2b9e99be252a4c57a3b12ce0e3d424"
AUTHORED_MANIFEST_SHA256 = (
    "f4ee0875fe2b2ca59b121b8400a21dfb92ffa04b6df9243d5eced5c3a83fe5bc"
)
ALPHA_RECEIPTS_SHA256 = (
    "bbcdc72afa5ccdd9d359b5802e8a7f65c991c2b89746bf9689c4cd4f33f1b705"
)
CANONICAL_RECEIPTS_SHA256 = (
    "818307146bcf9140fb0e4e39ba1f9ced9e31112de23331d6c230bbfc9c08a081"
)
CONTRACT_SHA256 = (
    "b1ffb566a9ce99302f8611be60d1af11bbb000b78efbc6be31833b90cd827af4"
)
RECONSTRUCTION_SHA256 = (
    "ef45a8a517a7fcd7c74b1fbac0fdeefc06b70aee4d0fce236970a688d956f5c2"
)
CONTACT_SHEET_SHA256 = (
    "7dbf7ea22b6d6b83164af29d17d623b9b9ef26bd41f197f00f1eee0aac78ee47"
)
AUTHORITY_SHA256 = (
    "740f35730f4aa1e6c6ef96be80115c5b0e117397f792d57fdf5360452bbe78c8"
)


def pose_ids(start: int, stop: int) -> list[str]:
    return [
        f"rohan_slate_motion_{pose_number:03d}"
        for pose_number in range(start, stop)
    ]


def rgba_sha256(path: Path) -> str:
    with Image.open(path) as image:
        return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


class RohanSlateParityCandidateTests(unittest.TestCase):
    def test_candidate_preserves_sources_and_adds_unique_authored_graphs(self):
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

    def test_authored_frames_have_portable_grounded_receipt_chains(self):
        self.assertEqual(
            sha256_path(AUTHORED_MANIFEST_PATH), AUTHORED_MANIFEST_SHA256
        )
        self.assertEqual(sha256_path(ALPHA_RECEIPTS_PATH), ALPHA_RECEIPTS_SHA256)
        self.assertEqual(
            sha256_path(CANONICAL_RECEIPTS_PATH),
            CANONICAL_RECEIPTS_SHA256,
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

            for receipt_path in (
                alpha_receipt["source_path"],
                alpha_receipt["destination_path"],
                canonical_receipt["source_path"],
                canonical_receipt["destination_path"],
            ):
                self.assertFalse(Path(receipt_path).is_absolute())

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

            support_bbox = canonical_receipt[
                "destination_ground_support_bbox"
            ]
            support_center = (support_bbox[0] + support_bbox[2]) / 2
            with self.subTest(pose_id=pose_id):
                self.assertEqual(
                    alpha_receipt["source_sha256"], sha256_path(chroma_path)
                )
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
                self.assertEqual(alpha_receipt["tolerance"], 110)
                self.assertEqual(alpha_receipt["edge_contract"], 1)
                self.assertEqual(
                    canonical_receipt["alignment_mode"],
                    "ground_support_center",
                )
                self.assertEqual(
                    canonical_receipt["ground_support_band_height"], 18
                )
                self.assertLessEqual(abs(support_center - 627.0), 0.5)
                self.assertEqual(bbox[3], 1185)
                self.assertGreaterEqual(bbox[0], 69)
                self.assertGreaterEqual(bbox[1], 69)
                self.assertGreaterEqual(1254 - bbox[2], 69)
                self.assertTrue(all(pixel == (0, 0, 0, 0) for pixel in corners))
                self.assertTrue(
                    all(
                        alpha != 0 or (red, green, blue) == (0, 0, 0)
                        for red, green, blue, alpha in pixels
                    )
                )
                self.assertFalse(canonical_receipt["resampled"])
                self.assertIsNone(canonical_receipt["resample_filter"])
                self.assertEqual(canonical_receipt["scale"], 1.0)

    def test_contract_reconstruction_and_runtime_boundaries_fail_closed(self):
        self.assertEqual(sha256_path(CONTRACT_PATH), CONTRACT_SHA256)
        self.assertEqual(sha256_path(RECONSTRUCTION_PATH), RECONSTRUCTION_SHA256)
        self.assertEqual(sha256_path(CONTACT_SHEET_PATH), CONTACT_SHEET_SHA256)
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))

        self.assertEqual(contract["artifact_sha256"], CANDIDATE_ARTIFACT_SHA256)
        self.assertEqual(contract["library_index_sha256"], INDEX_SHA256)
        self.assertEqual(
            contract["sequences"]["g7"]["family"], "measured_boundary"
        )
        self.assertEqual(
            contract["sequences"]["g8"]["family"],
            "practical_collaboration",
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
                ValueError,
                "alternate HD review library cannot be runtime-admitted",
            ):
                create_app(companion_mode=False, hd_review_index_path=path)


if __name__ == "__main__":
    unittest.main()
