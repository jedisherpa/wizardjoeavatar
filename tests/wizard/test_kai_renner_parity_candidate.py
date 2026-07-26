import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from wizard_avatar.hd_pose_artifact import (
    HDPoseArtifact,
    HDPoseLibrary,
    sha256_path,
)


ROOT = Path(__file__).resolve().parents[2]
PARITY_ROOT = ROOT / "assets" / "reference" / "joeville_48_parity"
CHARACTER_ROOT = PARITY_ROOT / "compiled" / "kai-renner"
INDEX_PATH = CHARACTER_ROOT / "library-index.json"
SOURCE_ARTIFACT_PATH = (
    CHARACTER_ROOT / "kai-renner-candidate-source-motion-v001.wjpose"
)
CANDIDATE_ARTIFACT_PATH = (
    CHARACTER_ROOT / "kai-renner-candidate-authored-parity-v001.wjpose"
)
AUTHORED_ROOT = PARITY_ROOT / "authored-source" / "kai-renner"
AUTHORED_FRAME_ROOT = AUTHORED_ROOT / "frames"
AUTHORED_MANIFEST_PATH = AUTHORED_ROOT / "authored-g7-g8-v001.json"
CANONICALIZATION_RECEIPTS_PATH = (
    AUTHORED_ROOT / "canonicalization-receipts-v001.json"
)
ALPHA_EXTRACTION_RECEIPTS_PATH = (
    AUTHORED_ROOT / "alpha-extraction-receipts-v001.json"
)
CONTRACT_PATH = (
    PARITY_ROOT
    / "source-metadata"
    / "kai-renner"
    / "review-motion-contract-v001.json"
)

SOURCE_ARTIFACT_SHA256 = (
    "7b73ec39dc91c0b1ac50e444bd786c893687880645b59ca6cc26b6f27b9d69e1"
)
CANDIDATE_ARTIFACT_SHA256 = (
    "2e15a54fda170005919711a0d9177253880cd169cd5d300349845d6b48569873"
)
INDEX_SHA256 = "768854f8c57528f51768198bc126d75dd61199cd372b6abca41e2aa8a35ab980"
AUTHORED_MANIFEST_SHA256 = (
    "1150cb6d315823b0899e41ad2e7701ca038bca05b8ab648819c47d570551cc6b"
)
ALPHA_EXTRACTION_RECEIPTS_SHA256 = (
    "46c6c458f911423bb244df328b1780fd4a54b1b0a506d80d38f4e150f88f1828"
)
CANONICALIZATION_RECEIPTS_SHA256 = (
    "3249ece047e6c14330aae17d162de8de24383be5e18591ab222c07cd78c7ce31"
)
CONTRACT_SHA256 = (
    "0e4c99b1c398f7666362e26992b9e8be2d2206d66dcab697207eead2796580be"
)


def kai_pose_ids(start: int, stop: int) -> list[str]:
    return [
        f"kai_renner_motion_{pose_number:03d}"
        for pose_number in range(start, stop)
    ]


class KaiRennerParityCandidateTests(unittest.TestCase):
    def test_real_candidate_preserves_all_48_unique_canonical_pixel_graphs(self):
        self.assertEqual(sha256_path(SOURCE_ARTIFACT_PATH), SOURCE_ARTIFACT_SHA256)
        self.assertEqual(
            sha256_path(CANDIDATE_ARTIFACT_PATH), CANDIDATE_ARTIFACT_SHA256
        )
        self.assertEqual(sha256_path(INDEX_PATH), INDEX_SHA256)

        source = HDPoseArtifact(SOURCE_ARTIFACT_PATH)
        candidate = HDPoseArtifact(CANDIDATE_ARTIFACT_PATH)
        library = HDPoseLibrary(INDEX_PATH)
        expected_pose_ids = kai_pose_ids(1, 49)

        self.assertEqual(source.header["pose_ids"], expected_pose_ids[:36])
        self.assertEqual(candidate.header["pose_ids"], expected_pose_ids)
        self.assertEqual(library.pose_ids, tuple(expected_pose_ids))
        self.assertEqual(len(library.pose_ids), 48)
        self.assertEqual(len(set(library.pose_ids)), 48)
        self.assertTrue(library.index["review_projection"])
        self.assertFalse(library.index["runtime_admitted"])

        for pose_number, pose_id in enumerate(expected_pose_ids, start=1):
            actual = library.load_rgba(pose_id)
            with self.subTest(pose_id=pose_id):
                self.assertFalse(
                    library.pose_metadata[pose_id]["runtime_admitted"]
                )
                if pose_number <= 36:
                    expected = source.load_rgba(pose_id)
                else:
                    with Image.open(
                        AUTHORED_FRAME_ROOT / f"{pose_id}.png"
                    ) as image:
                        expected = image.convert("RGBA").tobytes()
                self.assertEqual(
                    hashlib.sha256(actual).hexdigest(),
                    hashlib.sha256(expected).hexdigest(),
                )

    def test_authored_poses_bind_provenance_and_canonical_transform_mode(self):
        self.assertEqual(
            sha256_path(AUTHORED_MANIFEST_PATH), AUTHORED_MANIFEST_SHA256
        )
        self.assertEqual(
            sha256_path(ALPHA_EXTRACTION_RECEIPTS_PATH),
            ALPHA_EXTRACTION_RECEIPTS_SHA256,
        )
        self.assertEqual(
            sha256_path(CANONICALIZATION_RECEIPTS_PATH),
            CANONICALIZATION_RECEIPTS_SHA256,
        )
        manifest = json.loads(
            AUTHORED_MANIFEST_PATH.read_text(encoding="utf-8")
        )
        receipts = json.loads(
            CANONICALIZATION_RECEIPTS_PATH.read_text(encoding="utf-8")
        )
        candidate = HDPoseArtifact(CANDIDATE_ARTIFACT_PATH)
        provenance = candidate.header["provenance"]

        self.assertEqual(
            manifest["existing_artifact_sha256"], SOURCE_ARTIFACT_SHA256
        )
        self.assertEqual(
            manifest["canonicalization"],
            (
                "source_canvas_normalization_then_integer_translation_"
                "with_opt_in_oversize_fit"
            ),
        )
        self.assertFalse(manifest["runtime_admitted"])
        self.assertEqual(
            provenance["existing_source_artifact_sha256"],
            SOURCE_ARTIFACT_SHA256,
        )
        self.assertEqual(
            provenance["authored_manifest_sha256"],
            AUTHORED_MANIFEST_SHA256,
        )
        self.assertEqual(
            provenance["reconstruction"],
            "supplied_graph_plus_full_size_authored_rgba_v1",
        )
        self.assertFalse(provenance["runtime_admitted"])

        authored_frames = [
            frame
            for sequence_id in ("g7", "g8")
            for frame in manifest["sequences"][sequence_id]["frames"]
        ]
        self.assertEqual(
            [frame["pose_id"] for frame in authored_frames],
            kai_pose_ids(37, 49),
        )
        self.assertEqual(len(receipts), 12)
        receipts_by_pose = {
            Path(receipt["destination_path"]).stem: receipt
            for receipt in receipts
        }
        self.assertEqual(
            {
                pose_id
                for pose_id, receipt in receipts_by_pose.items()
                if receipt["resampled"]
            },
            {
                "kai_renner_motion_044",
                "kai_renner_motion_046",
                "kai_renner_motion_047",
            },
        )

        for frame in authored_frames:
            pose_id = frame["pose_id"]
            frame_path = AUTHORED_ROOT / frame["source_path"]
            receipt = receipts_by_pose[pose_id]
            with Image.open(frame_path) as image:
                rgba_sha256 = hashlib.sha256(
                    image.convert("RGBA").tobytes()
                ).hexdigest()
            with self.subTest(pose_id=pose_id):
                self.assertEqual(
                    frame["authorship"], "authored_full_size_imagegen_v1"
                )
                self.assertEqual(frame["source_sha256"], sha256_path(frame_path))
                self.assertEqual(frame["rgba_sha256"], rgba_sha256)
                self.assertEqual(
                    receipt["destination_sha256"], frame["source_sha256"]
                )
                self.assertEqual(
                    receipt["destination_rgba_sha256"], frame["rgba_sha256"]
                )
                if receipt["resampled"]:
                    self.assertEqual(receipt["resample_filter"], "lanczos")
                    self.assertLess(receipt["scale"], 1.0)
                    self.assertGreater(receipt["scale"], 0.98)
                else:
                    self.assertIsNone(receipt["resample_filter"])
                    self.assertEqual(receipt["scale"], 1.0)

    def test_review_motion_contract_is_non_admitted_kai_performance(self):
        self.assertEqual(sha256_path(CONTRACT_PATH), CONTRACT_SHA256)
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

        self.assertEqual(contract["artifact_sha256"], CANDIDATE_ARTIFACT_SHA256)
        self.assertEqual(contract["library_index_sha256"], INDEX_SHA256)
        self.assertTrue(contract["review_projection"])
        self.assertFalse(contract["runtime_admitted"])
        self.assertEqual(
            contract["sequences"]["g7"]["family"],
            "counter_service_exchange",
        )
        self.assertEqual(contract["sequences"]["g7"]["loop_mode"], "loop")
        self.assertEqual(
            contract["sequences"]["g7"]["pose_ids"], kai_pose_ids(37, 43)
        )
        self.assertEqual(
            contract["sequences"]["g8"]["family"],
            "craft_quality_explanation",
        )
        self.assertEqual(
            contract["sequences"]["g8"]["loop_mode"], "hold_last"
        )
        self.assertEqual(
            contract["sequences"]["g8"]["pose_ids"], kai_pose_ids(43, 49)
        )

    def test_runtime_and_library_boundaries_fail_closed(self):
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        self.assertTrue(
            all(not shard["runtime_admitted"] for shard in index["shards"])
        )
        self.assertTrue(
            all(
                not sequence["runtime_admitted"]
                for sequence in index["sequences"].values()
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checksum_index = json.loads(
                INDEX_PATH.read_text(encoding="utf-8")
            )
            checksum_index["shards"][0]["path"] = str(CANDIDATE_ARTIFACT_PATH)
            checksum_index["shards"][0]["sha256"] = "0" * 64
            checksum_index_path = root / "checksum-library-index.json"
            checksum_index_path.write_text(
                json.dumps(checksum_index), encoding="utf-8"
            )
            with self.assertRaisesRegex(
                ValueError, "HD pose shard checksum mismatch"
            ):
                HDPoseLibrary(checksum_index_path)

            runtime_index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
            runtime_index["runtime_admitted"] = True
            runtime_index_path = root / "runtime-library-index.json"
            runtime_index_path.write_text(
                json.dumps(runtime_index), encoding="utf-8"
            )
            from wizard_avatar.server import create_app

            with self.assertRaisesRegex(
                ValueError, "alternate HD review library cannot be runtime-admitted"
            ):
                create_app(
                    companion_mode=False,
                    hd_review_index_path=runtime_index_path,
                )

        library = HDPoseLibrary(INDEX_PATH)
        with self.assertRaises(KeyError):
            library.load_rgba("kai_renner_motion_049")


if __name__ == "__main__":
    unittest.main()
