import json
import tempfile
import unittest
from collections import OrderedDict
from pathlib import Path

from PIL import Image

from tools.compile_kingfisher_stage_library import compile_stage_library
from wizard_avatar.hd_pose_artifact import (
    HDPoseLibrary,
    sha256_path,
    write_pose_artifact,
)


class CompileKingfisherStageLibraryTests(unittest.TestCase):
    def _create_fixture(self, root: Path) -> dict[str, object]:
        base_root = root / "base"
        alphas = root / "alphas"
        audits = root / "audits"
        base_root.mkdir()
        alphas.mkdir()
        audits.mkdir()
        profile = {
            "profile_id": "test",
            "canvas_width": 960,
            "canvas_height": 540,
            "color_space": "sRGB",
            "alpha_mode": "binary_straight",
        }
        base_pose_ids = [
            f"kingfisher.act.{ordinal:03d}.base"
            for ordinal in range(1, 67)
        ]
        base_image = Image.new("RGBA", (960, 540), (0, 0, 0, 0))
        base_image.paste((20, 30, 40, 255), (450, 100, 510, 529))
        base_shards = []
        base_artifact_paths = []
        for first, last in ((1, 25), (26, 50), (51, 66)):
            shard_pose_ids = base_pose_ids[first - 1:last]
            shard_id = f"kingfisher_act_{first:03d}_{last:03d}"
            artifact_path = base_root / f"{shard_id}.wjpose"
            receipt = write_pose_artifact(
                artifact_path,
                OrderedDict(
                    (pose_id, base_image)
                    for pose_id in shard_pose_ids
                ),
                profile=profile,
                provenance={"source": "test"},
            )
            base_artifact_paths.append(artifact_path)
            base_shards.append(
                {
                    "shard_id": shard_id,
                    "path": artifact_path.name,
                    "sha256": receipt["sha256"],
                    "bytes": receipt["bytes"],
                    "pose_count": len(shard_pose_ids),
                    "pose_ids": shard_pose_ids,
                    "approval_state": "candidate_visual_review",
                    "review_projection": True,
                    "runtime_admitted": False,
                    "source": "test",
                }
            )
        base_index = {
            "schema_version": 1,
            "asset_set_id": "base",
            "character_id": "kingfisher",
            "display_name": "Kingfisher",
            "identity_side": None,
            "profile": profile,
            "presentation_normalization": None,
            "pose_count": 66,
            "pose_ids": base_pose_ids,
            "shards": base_shards,
            "sequences": {
                "kingfisher-all": {
                    "approval_state": "candidate_visual_review",
                    "fps": 6,
                    "loop": True,
                    "pose_ids": base_pose_ids,
                    "review_projection": True,
                    "runtime_admitted": False,
                }
            },
            "review_projection": True,
            "runtime_admitted": False,
        }
        base_index_path = base_root / "library-index.json"
        base_index_path.write_text(json.dumps(base_index), encoding="utf-8")

        performance_keys = []
        alpha_paths = {}
        audit_paths = []
        for pair_index, resting in enumerate(range(67, 111, 2), start=1):
            speaking = resting + 1
            rest_slug = f"test-{pair_index:02d}-resting-beak"
            speak_slug = f"test-{pair_index:02d}-speaking-beak"
            performance_keys.append(
                {
                    "key": f"test_{pair_index:02d}",
                    "articulation_region": [420, 200, 540, 320],
                    "poses": [
                        {"ordinal": resting, "slug": rest_slug},
                        {"ordinal": speaking, "slug": speak_slug},
                    ],
                }
            )
            for ordinal, slug in (
                (resting, rest_slug),
                (speaking, speak_slug),
            ):
                image = Image.new("RGBA", (960, 540), (0, 0, 0, 0))
                image.paste((50, 60, 70, 255), (400, 100, 560, 529))
                alpha_path = alphas / (
                    f"{ordinal:03d}_ACT{ordinal:03d}_"
                    f"{slug.replace('-', '_')}_alpha.png"
                )
                image.save(alpha_path)
                alpha_paths[ordinal] = alpha_path
            audit_path = audits / f"{resting:03d}_{speaking:03d}_pair.json"
            audit_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "passed": True,
                        "resting_sha256": sha256_path(alpha_paths[resting]),
                        "speaking_sha256": sha256_path(alpha_paths[speaking]),
                        "silhouette_iou": 1.0,
                        "outside_mouth_mean_abs": 0.0,
                        "mouth_mean_abs": 10.0,
                        "changed_rendered_pixels": 100,
                        "mouth_region": [420, 200, 540, 320],
                    }
                ),
                encoding="utf-8",
            )
            audit_paths.append(audit_path)
        plan_path = root / "pose-plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "character_id": "kingfisher",
                    "expansion_id": "test-stage",
                    "runtime_admitted": False,
                    "performance_keys": performance_keys,
                }
            ),
            encoding="utf-8",
        )
        choreography_path = root / "choreography.json"
        binding = {
            "roles": ["neutral"],
            "pose_ids": [base_pose_ids[0]],
            "action_ids": [],
            "clip_ids": [],
            "speech_compatible": True,
            "interrupt_policy": "immediate",
            "minimum_hold_ms": 700,
            "recovery_intent": None,
        }
        choreography_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "dictionary_id": "choreography:kingfisher-test",
                    "character_id": "kingfisher",
                    "library_class": "comprehensive_performance",
                    "instructions": {
                        "selection_unit": "phrase",
                        "transition_policy": "authored_graph",
                        "speech_motion_policy": "layered",
                        "locomotion_speech_policy": "allowed",
                        "unsupported_intent_policy": "characterful_neutral",
                        "repetition_window_ms": 12000,
                        "minimum_stillness_ms": 700,
                        "maximum_gestures_per_phrase": 2,
                    },
                    "intent_bindings": {
                        "neutral": binding,
                        "listen": {
                            **binding,
                            "roles": ["listening"],
                            "speech_compatible": False,
                            "recovery_intent": "neutral",
                        },
                        "speak": {
                            **binding,
                            "roles": ["speaking"],
                            "recovery_intent": "neutral",
                        },
                        "explain": {
                            **binding,
                            "roles": ["gesture", "speaking"],
                            "recovery_intent": "neutral",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        return {
            "base_root": base_root,
            "base_index_path": base_index_path,
            "base_shards": base_shards,
            "base_artifact_paths": base_artifact_paths,
            "plan_path": plan_path,
            "choreography_path": choreography_path,
            "alphas": alphas,
            "alpha_paths": alpha_paths,
            "audits": audits,
            "audit_paths": audit_paths,
        }

    def _compile(
        self,
        fixture: dict[str, object],
        output_root: Path,
    ) -> dict[str, object]:
        return compile_stage_library(
            fixture["base_index_path"],
            fixture["plan_path"],
            fixture["choreography_path"],
            fixture["alphas"],
            fixture["audits"],
            output_root,
        )

    def test_compiles_audited_stage_poses_without_runtime_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._create_fixture(Path(directory))
            compiled = fixture["base_root"]

            result = self._compile(fixture, compiled)

            library = HDPoseLibrary(compiled / "library-index.json")
            self.assertEqual(result["pose_count"], 110)
            self.assertEqual(result["pair_count"], 22)
            self.assertEqual(len(library.pose_ids), 110)
            self.assertEqual(
                library.index["sequences"]["kingfisher-all"]["pose_ids"],
                list(library.pose_ids),
            )
            self.assertFalse(library.index["runtime_admitted"])
            self.assertEqual(
                library.index["stage_expansion"]["pair_count"],
                22,
            )
            first_audit = library.index["stage_expansion"]["pair_audits"][0]
            self.assertEqual(
                first_audit["resting_sha256"],
                sha256_path(fixture["alpha_paths"][67]),
            )
            self.assertEqual(
                first_audit["speaking_sha256"],
                sha256_path(fixture["alpha_paths"][68]),
            )
            self.assertEqual(
                library.index["shards"][-1]["sha256"],
                sha256_path(compiled / "kingfisher_act_067_110.wjpose"),
            )
            self.assertEqual(
                library.index["choreography_dictionary"]["dictionary_id"],
                "choreography:kingfisher-test",
            )

    def test_rejects_alpha_modified_after_pair_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._create_fixture(Path(directory))
            resting_path = fixture["alpha_paths"][67]
            with Image.open(resting_path) as loaded:
                modified = loaded.convert("RGBA")
            modified.putpixel((450, 100), (80, 90, 100, 255))
            modified.save(resting_path)

            with self.assertRaisesRegex(
                ValueError,
                "resting alpha checksum mismatch",
            ):
                self._compile(fixture, fixture["base_root"])

    def test_rejects_missing_or_fabricated_pair_audit_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._create_fixture(Path(directory))
            audit_path = fixture["audit_paths"][0]
            original = json.loads(audit_path.read_text(encoding="utf-8"))
            cases = (
                ("missing", "speaking_sha256", None, "must include speaking_sha256"),
                (
                    "fabricated",
                    "resting_sha256",
                    "0" * 64,
                    "resting alpha checksum mismatch",
                ),
            )
            for name, field, value, message in cases:
                with self.subTest(name=name):
                    report = dict(original)
                    if value is None:
                        report.pop(field)
                    else:
                        report[field] = value
                    audit_path.write_text(json.dumps(report), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, message):
                        self._compile(fixture, fixture["base_root"])
            audit_path.write_text(json.dumps(original), encoding="utf-8")

    def test_rejects_pair_audit_for_a_different_articulation_region(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._create_fixture(Path(directory))
            audit_path = fixture["audit_paths"][0]
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            audit["mouth_region"] = [280, 120, 680, 350]
            audit_path.write_text(json.dumps(audit), encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                "articulation region mismatch",
            ):
                self._compile(fixture, fixture["base_root"])

    def test_copies_base_shards_to_separate_output_without_mutating_source(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._create_fixture(Path(directory))
            output_root = Path(directory) / "portable-output"
            source_paths = [
                fixture["base_index_path"],
                *fixture["base_artifact_paths"],
            ]
            source_hashes = {
                path: sha256_path(path)
                for path in source_paths
            }

            result = self._compile(fixture, output_root)

            self.assertEqual(
                Path(result["index_path"]).resolve(),
                (output_root / "library-index.json").resolve(),
            )
            self.assertEqual(
                {path: sha256_path(path) for path in source_paths},
                source_hashes,
            )
            for shard in fixture["base_shards"]:
                source = fixture["base_root"] / shard["path"]
                copied = output_root / shard["path"]
                self.assertEqual(sha256_path(copied), shard["sha256"])
                self.assertEqual(copied.read_bytes(), source.read_bytes())
            library = HDPoseLibrary(output_root / "library-index.json")
            self.assertEqual(len(library.pose_ids), 110)
            self.assertTrue((output_root / "choreography.json").is_file())


if __name__ == "__main__":
    unittest.main()
