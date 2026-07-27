import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops

from tools.import_robin_speech_alpha_library import (
    CANVAS_SIZE,
    DEFAULT_SOURCE_ROOT,
    PAIR_ARCHIVE_SHA256,
    ROBIN_SPEECH_BASE_ARCHIVE_SHA256,
    ROOT,
    _audit_source_root,
    _chroma_masks,
    _identity_image,
    _parse_frame_name,
    build_review_libraries,
    verify_deterministic_build,
)
from wizard_avatar.hd_pose_artifact import HDPoseLibrary


class RobinSpeechAlphaImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.records = _audit_source_root(DEFAULT_SOURCE_ROOT)

    def test_source_manifest_freezes_complete_shared_canvas_inventory(self):
        manifest = self.manifest
        records = self.records

        self.assertEqual(manifest["frame_count"], 200)
        self.assertEqual(manifest["deduplicated_overlap_count"], 10)
        self.assertEqual(len(records), 200)
        self.assertEqual(records[0]["pose_suffix"], "act.001.neutral-front")
        self.assertEqual(
            records[-1]["pose_suffix"],
            "int.050.speech-apologizes",
        )
        self.assertTrue(all(record["image_audit"]["mode"] == "RGBA" for record in records))
        self.assertTrue(
            all(record["image_audit"]["canvas_size"] == [1920, 1080] for record in records)
        )
        self.assertTrue(
            all(
                record["image_audit"]["identity_order"] == ["robin", "speech"]
                for record in records
            )
        )
        self.assertEqual(
            manifest["archives"]["robin_speech_base_001_160"]["sha256"],
            ROBIN_SPEECH_BASE_ARCHIVE_SHA256,
        )
        self.assertEqual(
            manifest["archives"]["pair_tail_151_200"]["sha256"],
            PAIR_ARCHIVE_SHA256,
        )
        self.assertFalse(manifest["runtime_admitted"])

    def test_identity_isolation_preserves_hard_interaction_frames(self):
        for ordinal in (24, 65, 109, 155, 176, 192, 195):
            with self.subTest(ordinal=ordinal):
                source_path = self.records[ordinal - 1]["resolved_path"]
                source = Image.open(source_path).convert("RGBA")
                robin = _identity_image(source_path, "robin")
                speech = _identity_image(source_path, "speech")

                self.assertEqual(robin.size, CANVAS_SIZE)
                self.assertEqual(speech.size, CANVAS_SIZE)
                reconstructed = Image.alpha_composite(robin, speech)
                self.assertEqual(reconstructed.tobytes(), source.tobytes())
                overlap = ImageChops.multiply(
                    robin.getchannel("A"),
                    speech.getchannel("A"),
                )
                self.assertIsNone(overlap.getbbox())
                robin_green, robin_blue = _chroma_masks(robin)
                speech_green, speech_blue = _chroma_masks(speech)
                self.assertIsNotNone(robin_green.getbbox())
                self.assertLessEqual(robin_blue.histogram()[255], 64)
                self.assertLessEqual(speech_green.histogram()[255], 64)
                self.assertIsNotNone(speech_blue.getbbox())

    def test_corrected_act_011_030_range_contains_both_birds(self):
        for record in self.records[10:30]:
            with self.subTest(ordinal=record["ordinal"]):
                source = Image.open(record["resolved_path"]).convert("RGBA")
                green, blue = _chroma_masks(source)
                self.assertIsNotNone(green.getbbox())
                self.assertIsNotNone(blue.getbbox())

    def test_compiler_builds_loadable_fail_closed_identity_libraries(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "compiled"
            receipt = build_review_libraries(
                source_root=DEFAULT_SOURCE_ROOT,
                output_root=output,
            )

            self.assertEqual(receipt["frame_count"], 200)
            self.assertFalse(receipt["runtime_admitted"])
            for identity in ("robin", "speech"):
                library = HDPoseLibrary(output / identity / "library-index.json")
                index = json.loads(
                    (output / identity / "library-index.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(len(library.pose_ids), 200)
                self.assertEqual(library.canvas_size, CANVAS_SIZE)
                self.assertEqual(
                    len(index["sequences"][f"{identity}-all"]["pose_ids"]),
                    200,
                )
                self.assertTrue(index["review_projection"])
                self.assertFalse(index["runtime_admitted"])
                self.assertEqual(index["approved_pose_count"], 0)
                self.assertEqual(
                    index["candidate_acceptance_audit"][
                        "runtime_admission_recommendation"
                    ],
                    "blocked",
                )

    def test_two_clean_builds_are_byte_identical(self):
        hashes = verify_deterministic_build(source_root=DEFAULT_SOURCE_ROOT)

        self.assertEqual(len(hashes), 23)
        self.assertIn("robin/library-index.json", hashes)
        self.assertIn("speech/library-index.json", hashes)

    def test_review_candidates_are_not_runtime_registered(self):
        registry = json.loads(
            (
                ROOT
                / "wizard_avatar"
                / "definitions"
                / "character_registry.json"
            ).read_text(encoding="utf-8")
        )
        identities = {
            value.lower()
            for character in registry["characters"]
            for value in (
                character["character_id"],
                character["persona_id"],
            )
        }

        self.assertFalse(any("robin" in identity for identity in identities))
        self.assertFalse(any("speech" in identity for identity in identities))

    def test_filename_parser_rejects_mismatched_ordinal(self):
        with self.assertRaisesRegex(ValueError, "ordinal/family index mismatch"):
            _parse_frame_name("101_FLY002_wrong_alpha.png")


if __name__ == "__main__":
    unittest.main()
