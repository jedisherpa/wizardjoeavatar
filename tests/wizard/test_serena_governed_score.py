import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from wizard_avatar.artifact_hashing import canonical_json_v1
from wizard_avatar.character_capabilities import (
    derive_character_capability_manifest,
)
from wizard_avatar.character_registry import CharacterAdmissionV1
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.performance_compiler import (
    PerformanceCompileError,
    canonical_artifact_bytes,
    compile_character_bound_performance,
)
from wizard_avatar.performance_context import PerformanceContextV1
from wizard_avatar.performance_score import (
    CompiledScoreLoader,
    CompiledScoreRepository,
)
from wizard_avatar.media_session import MediaSessionSnapshotV2
from wizard_avatar.stream import WizardFrameHub

from tests.wizard.test_performance_context import context_mapping
from tests.wizard.test_performance_scheduler import bound_snapshot


ROOT = Path(__file__).resolve().parents[2]
SERENA_PACKAGE_PATH = (
    ROOT
    / "wizard_avatar"
    / "definitions"
    / "characters"
    / "serena_quill"
    / "serena_quill_character_package_v2.json"
)
PORTABLE_SCORE_PATH = (
    ROOT
    / "tests"
    / "wizard"
    / "fixtures"
    / "audiobook_contracts"
    / "performance_score_v1.json"
)


def _portable_score():
    score = json.loads(PORTABLE_SCORE_PATH.read_text(encoding="utf-8"))
    score["score_id"] = "performance:serena-g1-mentoring"
    cue = score["tracks"][0]["cues"][0]
    cue["intent"] = "explain"
    cue["capability_requirements"] = ["mentoring_invitation"]
    cue["fallback_intents"] = ["characterful_neutral"]
    return score


def _bound_context_mapping(manifest, score, motion_profile="full"):
    score_sha256 = "sha256:" + hashlib.sha256(
        canonical_artifact_bytes(score)
    ).hexdigest()
    value = context_mapping()
    value.pop("context_sha256")
    value["character"].update(
        {
            "character_id": manifest["character"]["character_id"],
            "package_digest": manifest["sources"]["package_sha256"],
            "manifest_digest": manifest["manifest_sha256"],
            "current_pose_id": "neutral_front",
            "current_action_id": "idle",
            "expression": "neutral",
        }
    )
    value["governance"]["allowed_semantic_actions"] = ["explain"]
    value["preferences"]["motion_profile"] = motion_profile
    value["evidence"]["package_digest"] = manifest["sources"]["package_sha256"]
    value["evidence"]["score_binding"] = {
        "score_id": score["score_id"],
        "score_revision": score["revision"],
        "score_sha256": score_sha256,
    }
    return value


def _bound_context(manifest, score, motion_profile="full"):
    return PerformanceContextV1.build(
        _bound_context_mapping(manifest, score, motion_profile)
    )


class SerenaGovernedScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = derive_character_capability_manifest(SERENA_PACKAGE_PATH)
        cls.portable_score = _portable_score()

    def admitted_source(self, root):
        package_root = root / "serena_quill"
        shutil.copytree(SERENA_PACKAGE_PATH.parent, package_root)
        package_path = package_root / SERENA_PACKAGE_PATH.name
        source = ProceduralWizardFrameSource(
            cols=96,
            rows=54,
            fps=24,
            character_package_path=package_path,
        )
        package = source.character_package
        admission = CharacterAdmissionV1.build(
            persona_id="serena-quill",
            character_id=package.character_id,
            package_sha256=package.package_sha256,
        )
        registry_path = root / "character_registry.json"
        registry_path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "default_character_id": package.character_id,
                    "characters": [
                        {
                            "character_id": package.character_id,
                            "persona_id": admission.persona_id,
                            "package": str(package_path.relative_to(root)),
                            "package_sha256": package.package_sha256,
                            "admission_sha256": admission.admission_sha256,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return source, registry_path

    @staticmethod
    def admitted_v2_snapshot(snapshot, performance):
        mapping = copy.deepcopy(snapshot.to_dict())
        mapping["schema_version"] = 2
        mapping["performance"].pop("character_id")
        mapping["performance"].pop("character_package_sha256")
        mapping["performance"]["admission"] = (
            performance.character_admission.to_dict()
        )
        return MediaSessionSnapshotV2.from_mapping(mapping)

    def test_full_motion_score_compiles_to_exact_serena_graph_identity(self):
        context = _bound_context(self.manifest, self.portable_score)

        first = compile_character_bound_performance(
            context,
            self.portable_score,
            self.manifest,
        )
        second = compile_character_bound_performance(
            context,
            copy.deepcopy(self.portable_score),
            copy.deepcopy(self.manifest),
        )

        self.assertEqual(canonical_json_v1(first), canonical_json_v1(second))
        cue = first["tracks"][0]["cues"][0]
        self.assertEqual(cue["mapping_id"], "clip:pose_mentoring_invitation")
        self.assertEqual(cue["clip_id"], "pose_mentoring_invitation")
        self.assertEqual(cue["node_id"], "node_mentoring_invitation")
        self.assertEqual(
            cue["preload_asset_ids"],
            ["mentoring_invitation", "pose_mentoring_invitation"],
        )
        self.assertEqual(cue["owned_channels"], ["body"])
        self.assertEqual(first["fallback_records"], [])
        self.assertEqual(first["character"]["package_version"], "2.0.0")

    def test_compiler_rejects_each_foreign_serena_identity_dimension(self):
        cases = (
            ("character_id", "foreign-character-v1"),
            ("package_digest", "sha256:" + "9" * 64),
            ("manifest_digest", "sha256:" + "8" * 64),
        )
        for field, foreign_value in cases:
            with self.subTest(field=field):
                value = _bound_context_mapping(
                    self.manifest,
                    self.portable_score,
                )
                value["character"][field] = foreign_value
                if field == "package_digest":
                    value["evidence"]["package_digest"] = foreign_value
                context = PerformanceContextV1.build(value)

                with self.assertRaises(PerformanceCompileError) as caught:
                    compile_character_bound_performance(
                        context,
                        self.portable_score,
                        self.manifest,
                    )

                self.assertEqual(caught.exception.code, "stale_binding")

    def test_reduced_motion_truthfully_suppresses_whole_pose_action(self):
        context = _bound_context(
            self.manifest,
            self.portable_score,
            motion_profile="reduced",
        )

        compiled = compile_character_bound_performance(
            context,
            self.portable_score,
            self.manifest,
        )

        self.assertEqual(compiled["tracks"][0]["cues"], [])
        self.assertEqual(
            {
                record["reason_code"]
                for record in compiled["fallback_records"]
            },
            {"motion_profile_projection", "motion_profile_suppressed"},
        )

    def test_compiled_score_publishes_preloads_and_applies_in_production_hub(self):
        context = _bound_context(self.manifest, self.portable_score)
        compiled = compile_character_bound_performance(
            context,
            self.portable_score,
            self.manifest,
        )
        loaded = CompiledScoreLoader().from_mapping(compiled)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = CompiledScoreRepository(root / "scores")
            repository.publish(loaded)
            source, registry_path = self.admitted_source(root)
            hub = WizardFrameHub(
                source,
                score_repository=repository,
                character_registry_path=registry_path,
            )
            snapshot = self.admitted_v2_snapshot(
                bound_snapshot(
                    loaded,
                    position=1500,
                    kind="audiobook",
                    mode="narrative",
                ),
                hub.performance,
            )

            prepared = hub.performance.prepare_snapshot(snapshot)
            accepted = hub.performance.accept_snapshot(snapshot, 0)
            applied = hub.performance.apply(source.controller, 0)
            source.resolve_authoritative_animation_state()

        self.assertTrue(prepared.ready)
        self.assertEqual(prepared.code, "score_ready")
        self.assertEqual(accepted.scheduler_state, "playing")
        self.assertTrue(applied.active)
        self.assertEqual(applied.action, "mentoring_invitation")
        self.assertEqual(
            source.controller.state.action,
            "mentoring_invitation",
        )
        self.assertEqual(
            source.controller.state.pose_id,
            "mentoring_invitation",
        )
        self.assertEqual(
            source.controller.state.animation_clip_id,
            "pose_mentoring_invitation",
        )
        self.assertEqual(
            source.controller.state.animation_node_id,
            "node_mentoring_invitation",
        )

    def test_replay_is_pixel_deterministic_and_pause_releases_the_serena_pose(self):
        context = _bound_context(self.manifest, self.portable_score)
        compiled = compile_character_bound_performance(
            context,
            self.portable_score,
            self.manifest,
        )
        loaded = CompiledScoreLoader().from_mapping(compiled)
        frames = []
        sources = []
        hubs = []

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = CompiledScoreRepository(root / "scores")
            repository.publish(loaded)
            for index in range(2):
                instance_root = root / "instance-{}".format(index)
                instance_root.mkdir()
                source, registry_path = self.admitted_source(instance_root)
                hub = WizardFrameHub(
                    source,
                    score_repository=repository,
                    character_registry_path=registry_path,
                )
                snapshot = self.admitted_v2_snapshot(
                    bound_snapshot(
                        loaded,
                        position=1500,
                        kind="audiobook",
                        mode="narrative",
                    ),
                    hub.performance,
                )
                self.assertTrue(
                    hub.performance.prepare_snapshot(snapshot).ready
                )
                self.assertEqual(
                    hub.performance.accept_snapshot(
                        snapshot,
                        0,
                    ).scheduler_state,
                    "playing",
                )
                hub.performance.apply(source.controller, 0)
                source.resolve_authoritative_animation_state()
                frames.append(source.render_current_frame().cells)
                sources.append(source)
                hubs.append(hub)

            paused = self.admitted_v2_snapshot(
                bound_snapshot(
                    loaded,
                    sequence=1,
                    state="paused",
                    position=1500,
                    kind="audiobook",
                    mode="narrative",
                ),
                hubs[0].performance,
            )
            pause_ack = hubs[0].performance.accept_snapshot(paused, 1_000)
            inactive = hubs[0].performance.apply(
                sources[0].controller,
                1_000,
            )
            sources[0].resolve_authoritative_animation_state()

        self.assertEqual(frames[0], frames[1])
        self.assertEqual(pause_ack.scheduler_state, "paused")
        self.assertFalse(inactive.active)
        self.assertEqual(sources[0].controller.state.action, "idle")
        self.assertIsNone(sources[0].controller.state.pose_override_id)
        self.assertEqual(sources[0].controller.state.pose_id, "neutral_front")


if __name__ == "__main__":
    unittest.main()
