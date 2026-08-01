import copy
import json
import tempfile
import unittest
from pathlib import Path

from wizard_avatar.artifact_hashing import canonical_json_v1, sha256_ref
from wizard_avatar.character_capabilities import derive_character_capability_manifest
from wizard_avatar.performance_compiler import (
    PerformanceCompileError,
    canonical_artifact_bytes,
    compile_character_bound_performance,
)
from wizard_avatar.performance_context import PerformanceContextV1
from wizard_avatar.performance_scheduler import PerformanceScheduler
from wizard_avatar.performance_score import CompiledScoreLoader, CompiledScoreRepository
from wizard_avatar.score_runtime import SCORE_ADMISSION_MISMATCH, ScoreRuntime
from tests.wizard.test_performance_context import context_mapping
from tests.wizard.test_performance_scheduler import bound_snapshot


FIXTURES = Path(__file__).resolve().parent / "fixtures"
PORTABLE_SCORE = FIXTURES / "audiobook_contracts" / "performance_score_v1.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _score_hash(score):
    return sha256_ref(canonical_artifact_bytes(score))


def _bound_context(score, manifest, *, motion_profile="full", disabled_channels=(), generation=7):
    raw = context_mapping()
    raw.pop("context_sha256")
    raw["runtime"]["reconciliation_generation"] = generation
    raw["character"].update(
        {
            "character_id": manifest["character"]["character_id"],
            "package_digest": manifest["sources"]["package_sha256"],
            "manifest_digest": manifest["manifest_sha256"],
        }
    )
    raw["preferences"]["motion_profile"] = motion_profile
    raw["preferences"]["disabled_channels"] = sorted(disabled_channels)
    raw["evidence"]["package_digest"] = manifest["sources"]["package_sha256"]
    raw["evidence"]["score_binding"] = {
        "score_id": score["score_id"],
        "score_revision": score["revision"],
        "score_sha256": _score_hash(score),
    }
    return PerformanceContextV1.build(raw)


def _score_with_requirement(requirement, *, track_kind="body_base"):
    score = _load(PORTABLE_SCORE)
    score["tracks"][0]["kind"] = track_kind
    score["tracks"][0]["cues"][0]["capability_requirements"] = [requirement]
    return score


def _minimal_manifest(source):
    manifest = copy.deepcopy(source)
    manifest["manifest_id"] = "character-capabilities:minimal-stage-v1:v1"
    manifest["character"].update(
        {
            "character_id": "minimal-stage-v1",
            "display_name": "Minimal Stage",
            "package_capabilities": [],
        }
    )
    manifest["sources"]["package_sha256"] = "sha256:" + "7" * 64
    manifest["poses"] = [
        copy.deepcopy(next(pose for pose in source["poses"] if pose["pose_id"] == "front_idle"))
    ]
    manifest["poses"][0]["clip_ids"] = ["idle_front"]
    idle = copy.deepcopy(
        next(capability for capability in source["capabilities"] if capability["capability_id"] == "clip:idle_front")
    )
    idle["transitions"]["legal_exit_clip_ids"] = ["idle_front"]
    manifest["capabilities"] = [idle]
    manifest["permission_world"]["bindings"] = {
        "world_state_ids": [],
        "effect_ids": [],
        "prop_ids": [],
        "requirements": [],
    }
    manifest["diagnostics"] = []
    manifest["counts"].update(
        {
            "package_capability_count": 0,
            "clip_count": 1,
            "node_count": 1,
            "transition_count": 0,
            "pose_count": 1,
            "graph_admitted_pose_count": 1,
            "diagnostic_only_pose_count": 0,
            "expression_count": 0,
            "mouth_shape_count": 0,
            "capability_count": 1,
            "diagnostic_count": 0,
        }
    )
    manifest.pop("manifest_sha256")
    manifest["manifest_sha256"] = sha256_ref(canonical_json_v1(manifest))
    return manifest


class CharacterBoundPerformanceCompilerTests(unittest.TestCase):
    def setUp(self):
        self.manifest = derive_character_capability_manifest()

    def test_exact_capability_binding_is_repeatable_loader_and_scheduler_compatible(self):
        score = _score_with_requirement("clip:explain_front")
        context = _bound_context(score, self.manifest)

        first = compile_character_bound_performance(context, score, self.manifest)
        second = compile_character_bound_performance(context, score, self.manifest)

        self.assertEqual(canonical_artifact_bytes(first), canonical_artifact_bytes(second))
        cue = first["tracks"][0]["cues"][0]
        self.assertEqual(cue["start_ms"], 1000)
        self.assertEqual(cue["end_ms"], 2000)
        self.assertEqual(cue["mapping_id"], "clip:explain_front")
        self.assertEqual(cue["clip_id"], "explain_front")
        self.assertEqual(cue["node_id"], "explain")
        self.assertEqual(first["performance_score_sha256"], _score_hash(score))
        self.assertEqual(first["character"]["package_digest"], context.character.package_digest)
        loaded = CompiledScoreLoader().from_mapping(first)
        state = PerformanceScheduler(loaded).evaluate(1500)
        self.assertEqual(state.clip_id, "explain_front")
        self.assertEqual(state.node_id, "explain")

        moved_context = _bound_context(score, self.manifest, generation=8)
        moved = compile_character_bound_performance(moved_context, score, self.manifest)
        self.assertNotEqual(first["mapping_policy_sha256"], moved["mapping_policy_sha256"])
        self.assertNotEqual(first["compiled_score_id"], moved["compiled_score_id"])

    def test_lowest_compiler_boundary_rejects_unapproved_and_denied_scores(self):
        score = _score_with_requirement("clip:explain_front")
        context = _bound_context(score, self.manifest)

        unapproved_raw = context.content_dict()
        unapproved_raw["approval"]["presentation_state"] = "unapproved"
        unapproved_raw["approval"]["presentation_artifact_sha256"] = None
        unapproved = PerformanceContextV1.build(unapproved_raw)
        with self.assertRaises(PerformanceCompileError) as presentation:
            compile_character_bound_performance(unapproved, score, self.manifest)
        self.assertEqual(presentation.exception.code, "presentation_not_approved")

        denied_score = copy.deepcopy(score)
        denied_score["tracks"][0]["cues"][0]["capability_requirements"] = [
            "semantic:action:external_action"
        ]
        denied_context = _bound_context(denied_score, self.manifest)
        with self.assertRaises(PerformanceCompileError) as denied:
            compile_character_bound_performance(
                denied_context,
                denied_score,
                self.manifest,
            )
        self.assertEqual(denied.exception.code, "direction_not_authorized")

        denied_score["tracks"][0]["cues"][0]["manual"]["disabled"] = True
        denied_context = _bound_context(denied_score, self.manifest)
        compiled = compile_character_bound_performance(
            denied_context,
            denied_score,
            self.manifest,
        )
        compiled_cue_ids = {
            cue["cue_id"]
            for track in compiled["tracks"]
            for cue in track["cues"]
        }
        self.assertNotIn(
            denied_score["tracks"][0]["cues"][0]["cue_id"],
            compiled_cue_ids,
        )

    def test_compiled_score_is_admitted_by_real_character_asset_contract(self):
        portable = _score_with_requirement("clip:explain_front")
        context = _bound_context(portable, self.manifest)
        compiled = compile_character_bound_performance(
            context,
            portable,
            self.manifest,
        )
        score = CompiledScoreLoader().from_mapping(compiled)
        snapshot = bound_snapshot(score)
        pose_ids = {
            str(pose["pose_id"])
            for pose in self.manifest["poses"]
        }
        clip_ids = {
            str(clip_id)
            for capability in self.manifest["capabilities"]
            for clip_id in capability["mapping"]["clip_ids"]
        }
        node_ids = {
            str(node_id)
            for capability in self.manifest["capabilities"]
            for node_id in capability["mapping"]["node_ids"]
        }
        with tempfile.TemporaryDirectory() as directory:
            repository = CompiledScoreRepository(directory)
            repository.publish(score)
            runtime = ScoreRuntime(
                repository,
                character_id=score.character_id,
                package_digest=score.package_digest,
                pose_library_digest=compiled["character"]["pose_library_digest"],
                graph_digest=compiled["character"]["graph_digest"],
                admitted_pose_ids=pose_ids,
                admitted_clip_ids=clip_ids,
                admitted_node_ids=node_ids,
            )

            prepared = runtime.prepare_snapshot(snapshot)

            self.assertTrue(prepared.ready)
            self.assertIs(runtime.resolve(snapshot), prepared.score)

    def test_schema_valid_unknown_preload_fails_runtime_admission(self):
        portable = _score_with_requirement("clip:explain_front")
        context = _bound_context(portable, self.manifest)
        compiled = compile_character_bound_performance(
            context,
            portable,
            self.manifest,
        )
        compiled["tracks"][0]["cues"][0]["preload_asset_ids"].append(
            "unknown:pose"
        )
        score = CompiledScoreLoader().from_mapping(compiled)
        snapshot = bound_snapshot(score)
        pose_ids = {
            str(pose["pose_id"])
            for pose in self.manifest["poses"]
        }
        clip_ids = {
            str(clip_id)
            for capability in self.manifest["capabilities"]
            for clip_id in capability["mapping"]["clip_ids"]
        }
        node_ids = {
            str(node_id)
            for capability in self.manifest["capabilities"]
            for node_id in capability["mapping"]["node_ids"]
        }
        with tempfile.TemporaryDirectory() as directory:
            repository = CompiledScoreRepository(directory)
            repository.publish(score)
            runtime = ScoreRuntime(
                repository,
                character_id=score.character_id,
                package_digest=score.package_digest,
                pose_library_digest=compiled["character"]["pose_library_digest"],
                graph_digest=compiled["character"]["graph_digest"],
                admitted_pose_ids=pose_ids,
                admitted_clip_ids=clip_ids,
                admitted_node_ids=node_ids,
            )

            prepared = runtime.prepare_snapshot(snapshot)

            self.assertFalse(prepared.ready)
            self.assertEqual(prepared.code, SCORE_ADMISSION_MISMATCH)
            self.assertIsNone(runtime.resolve(snapshot))

    def test_unsupported_capability_uses_only_its_declared_admitted_fallback(self):
        score = _score_with_requirement("unsupported:dance", track_kind="dance")
        context = _bound_context(score, self.manifest)

        compiled = compile_character_bound_performance(context, score, self.manifest)

        cue = compiled["tracks"][0]["cues"][0]
        self.assertEqual(cue["mapping_id"], "clip:idle_front")
        self.assertNotEqual(cue["mapping_id"], "unsupported:dance")
        self.assertEqual(compiled["fallback_records"][0]["reason_code"], "no_runtime_mapping")
        self.assertEqual(compiled["fallback_records"][0]["selected_mapping_id"], "clip:idle_front")

    def test_diagnostic_only_pose_is_rejected_before_mapping(self):
        score = _score_with_requirement("pose:feeling_anger_close")
        context = _bound_context(score, self.manifest)

        with self.assertRaises(PerformanceCompileError) as caught:
            compile_character_bound_performance(context, score, self.manifest)

        self.assertEqual(caught.exception.code, "pose_not_admitted")

    def test_semantic_intent_rejects_raw_pose_and_clip_identifiers(self):
        for raw_intent in ("clip:explain_front", "explain_front", "front_idle"):
            with self.subTest(raw_intent=raw_intent):
                score = _score_with_requirement("clip:explain_front")
                score["tracks"][0]["cues"][0]["intent"] = raw_intent
                context = _bound_context(score, self.manifest)

                with self.assertRaises(PerformanceCompileError) as caught:
                    compile_character_bound_performance(context, score, self.manifest)

                self.assertEqual(caught.exception.code, "raw_renderer_intent")

    def test_private_values_are_rejected_without_echoing_them(self):
        score = _score_with_requirement("clip:explain_front")
        canary = "sk-privatecanary"
        score["tracks"][0]["cues"][0]["source_ids"] = [canary]
        context = _bound_context(score, self.manifest)

        with self.assertRaises(PerformanceCompileError) as caught:
            compile_character_bound_performance(context, score, self.manifest)

        self.assertEqual(caught.exception.code, "private_content")
        self.assertNotIn(canary, str(caught.exception))

    def test_motion_profile_and_disabled_channels_are_compiled_explicitly(self):
        score = _score_with_requirement("clip:explain_front")
        reduced = _bound_context(
            score,
            self.manifest,
            motion_profile="reduced",
            disabled_channels=("mouth",),
        )
        still = _bound_context(score, self.manifest, motion_profile="still")

        reduced_score = compile_character_bound_performance(reduced, score, self.manifest)
        still_score = compile_character_bound_performance(still, score, self.manifest)

        self.assertEqual(reduced_score["tracks"][0]["cues"], [])
        self.assertTrue(
            any(record["reason_code"] == "channel_disabled" for record in reduced_score["fallback_records"])
        )
        self.assertTrue(
            any(
                record["reason_code"] == "motion_profile_projection"
                for record in reduced_score["fallback_records"]
            )
        )
        still_cue = still_score["tracks"][0]["cues"][0]
        self.assertEqual(still_cue["owned_channels"], ["mouth"])
        self.assertTrue(
            any(record["reason_code"] == "motion_profile_projection" for record in still_score["fallback_records"])
        )

    def test_characterful_neutral_resolves_for_a_smaller_character_without_branches(self):
        manifest = _minimal_manifest(self.manifest)
        score = _score_with_requirement("body.characterful_neutral")
        context = _bound_context(score, manifest)

        compiled = compile_character_bound_performance(context, score, manifest)

        self.assertEqual(compiled["character"]["character_id"], "minimal-stage-v1")
        self.assertEqual(compiled["tracks"][0]["cues"][0]["mapping_id"], "clip:idle_front")


if __name__ == "__main__":
    unittest.main()
