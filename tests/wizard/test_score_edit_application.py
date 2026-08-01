import copy
import tempfile
import unittest

from tests.wizard.test_directed_performance import main_snapshot, preparation_mapping
from wizard_avatar.character_capabilities import derive_character_capability_manifest
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.controller import WizardAvatarController
from wizard_avatar.directed_performance import DirectedPerformancePreparationV1
from wizard_avatar.direction_compiler import compile_high_level_direction
from wizard_avatar.performance_application import PerformanceApplication
from wizard_avatar.performance_score import CompiledScoreRepository
from wizard_avatar.score_edit_application import (
    ScoreEditApplicationError,
    apply_score_edits,
    publish_score_edits,
    score_edit_target_sha256,
)
from wizard_avatar.score_edits import ScoreEditsV1


class ScoreEditApplicationTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_character_registry()
        self.manifest = derive_character_capability_manifest()
        self.package = self.registry.get(self.registry.default_character_id)
        self.temporary = tempfile.TemporaryDirectory()
        self.repository = CompiledScoreRepository(self.temporary.name)
        self.application = PerformanceApplication(
            "wizard-runtime-score-edits",
            score_repository=self.repository,
            character_id=self.registry.default_character_id,
            package_digest=self.package.package_sha256,
            manifest_digest=self.manifest["manifest_sha256"],
            capability_manifest=self.manifest,
            character_registry=self.registry,
        )
        controller = WizardAvatarController(
            ("front_idle",),
            self.registry.default_character_id,
        )
        self.application.accept_snapshot(main_snapshot(self.registry), 1_000_000)
        preparation = DirectedPerformancePreparationV1.from_mapping(
            preparation_mapping()
        )
        self.preliminary_context = self.application.capture_performance_context(
            preparation.context_request,
            controller,
            1_010_000,
            source_slot="main",
        )
        compilation = compile_high_level_direction(
            preparation.bind_context(self.preliminary_context),
            self.preliminary_context,
            self.manifest,
        )
        self.base_score = compilation.portable_score
        self.compiled_directed = self.application.compile_directed_performance(
            preparation,
            self.preliminary_context,
        )

    def tearDown(self):
        self.temporary.cleanup()

    def edits(self, operations):
        from wizard_avatar.artifact_hashing import canonical_json_v1, sha256_ref

        return ScoreEditsV1.build(
            {
                "schema_version": 1,
                "edit_set_id": "edits:director-application-001",
                "revision": 1,
                "character_id": self.preliminary_context.character.character_id,
                "package_digest": self.preliminary_context.character.package_digest,
                "base_score_sha256": sha256_ref(canonical_json_v1(self.base_score)),
                "parent_edit_set_sha256": None,
                "actor": {"kind": "human", "actor_id": "local:director"},
                "operations": operations,
            }
        )

    def operation(self, index, cue_id, edit_type, value, *, expected=None):
        return {
            "operation_id": "op:{:04d}".format(index),
            "cue_id": cue_id,
            "edit_type": edit_type,
            "expected_value_sha256": expected
            or score_edit_target_sha256(self.base_score, cue_id, edit_type),
            "value": value,
            "reason_code": "director_choice",
        }

    def cue_ids(self):
        return [
            cue["cue_id"]
            for track in self.base_score["tracks"]
            for cue in track["cues"]
        ]

    def test_applies_recompiles_publishes_and_replays_deterministically(self):
        stage, point, explain, face = self.cue_ids()
        edits = self.edits(
            [
                self.operation(1, point, "timing_offset_ms", -120),
                self.operation(2, explain, "duration_ms", 3000),
                self.operation(3, face, "intensity_milli", 725),
                self.operation(4, stage, "disabled", True),
                self.operation(
                    5,
                    point,
                    "semantic_clip_id",
                    "semantic:clip:explain_front",
                ),
            ]
        )

        first = apply_score_edits(
            self.base_score,
            edits,
            self.preliminary_context,
            capability_manifest=self.manifest,
        )
        second = apply_score_edits(
            self.base_score,
            edits,
            self.preliminary_context,
            capability_manifest=self.manifest,
        )
        published = publish_score_edits(first, repository=self.repository)
        loaded = self.repository.load_current(first.compiled_score.media_sha256)

        self.assertEqual(first.revised_score_sha256, second.revised_score_sha256)
        self.assertEqual(
            first.compiled_score.artifact_sha256,
            second.compiled_score.artifact_sha256,
        )
        self.assertEqual(published.publication.score_sha256, loaded.artifact_sha256)
        self.assertEqual(first.portable_score["revision"], self.base_score["revision"] + 1)
        self.assertEqual(first.compiled_score.revision, first.portable_score["revision"])
        self.assertEqual(
            first.portable_score["provenance"]["edit_set_sha256"],
            edits.edit_set_sha256,
        )
        compiled_cue_ids = {
            cue.cue_id
            for track in first.compiled_score.tracks
            for cue in track.index.cues
        }
        self.assertNotIn(stage, compiled_cue_ids)
        edited_point = next(
            cue
            for track in first.portable_score["tracks"]
            for cue in track["cues"]
            if cue["cue_id"] == point
        )
        self.assertEqual(edited_point["start_ms"], 3840)
        self.assertEqual(edited_point["capability_requirements"], ["clip:explain_front"])

    def test_expected_value_lock_and_range_conflicts_fail_closed(self):
        stage, point, _explain, _face = self.cue_ids()
        stale = self.edits(
            [
                self.operation(
                    1,
                    point,
                    "intensity_milli",
                    700,
                    expected="sha256:" + "f" * 64,
                )
            ]
        )
        with self.assertRaises(ScoreEditApplicationError) as mismatch:
            apply_score_edits(
                self.base_score,
                stale,
                self.preliminary_context,
                capability_manifest=self.manifest,
            )
        self.assertEqual(mismatch.exception.code, "expected_value_mismatch")

        locked_score = copy.deepcopy(self.base_score)
        locked_score["tracks"][1]["cues"][0]["manual"]["locked"] = True
        from wizard_avatar.artifact_hashing import canonical_json_v1, sha256_ref

        locked_edits_raw = self.edits(
            [self.operation(1, point, "intensity_milli", 700)]
        ).content_dict()
        locked_edits_raw["base_score_sha256"] = sha256_ref(
            canonical_json_v1(locked_score)
        )
        locked_edits = ScoreEditsV1.build(locked_edits_raw)
        with self.assertRaises(ScoreEditApplicationError) as locked:
            apply_score_edits(
                locked_score,
                locked_edits,
                self.preliminary_context,
                capability_manifest=self.manifest,
            )
        self.assertEqual(locked.exception.code, "cue_locked")

        out_of_bounds = self.edits(
            [self.operation(1, stage, "timing_offset_ms", -1)]
        )
        with self.assertRaises(ScoreEditApplicationError) as timing:
            apply_score_edits(
                self.base_score,
                out_of_bounds,
                self.preliminary_context,
                capability_manifest=self.manifest,
            )
        self.assertEqual(timing.exception.code, "time_out_of_bounds")

    def test_performance_application_exposes_edit_and_atomic_publish_path(self):
        stage = self.cue_ids()[0]
        edits = self.edits([self.operation(1, stage, "disabled", True)])

        applied = self.application.apply_directed_score_edits(
            self.compiled_directed,
            edits,
        )
        published = self.application.publish_directed_score_edits(applied)
        loaded = self.repository.load_current(applied.compiled_score.media_sha256)

        self.assertEqual(
            published.publication.score_sha256,
            loaded.artifact_sha256,
        )
        self.assertEqual(
            published.applied.edit_set_sha256,
            edits.edit_set_sha256,
        )


if __name__ == "__main__":
    unittest.main()
