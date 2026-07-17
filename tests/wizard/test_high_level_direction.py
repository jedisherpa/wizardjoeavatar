import json
import tempfile
import unittest

from wizard_avatar.artifact_hashing import canonical_json_v1
from wizard_avatar.character_capabilities import derive_character_capability_manifest
from wizard_avatar.controller import WizardAvatarController
from wizard_avatar.direction_compiler import (
    DirectionCompileError,
    HighLevelDirectionRequestV1,
    compile_high_level_direction,
)
from wizard_avatar.performance_context import PerformanceContextV1
from wizard_avatar.performance_application import PerformanceApplication
from wizard_avatar.performance_score import CompiledScoreLoader, CompiledScoreRepository
from wizard_avatar.performance_scheduler import PerformanceScheduler
from tests.wizard.test_performance_context import context_mapping
from tests.wizard.test_performance_scheduler import bound_snapshot


def _request(text, context, *, intent="explain"):
    digest = "b" * 64
    return HighLevelDirectionRequestV1.from_mapping(
        {
            "schema_version": 1,
            "direction_id": "direction:show-opening",
            "direction_text": text,
            "context_sha256": context.context_sha256,
            "intent": intent,
            "duration_ms": 9000,
            "media_id": "media:sha256:" + digest,
            "media_sha256": "sha256:" + digest,
            "seed": 17,
        }
    )


def _context(manifest, *, allowed=("explain", "listen"), denied=("external_action",), profile="full"):
    raw = context_mapping()
    raw.pop("context_sha256")
    raw["character"].update(
        {
            "character_id": manifest["character"]["character_id"],
            "package_digest": manifest["sources"]["package_sha256"],
            "manifest_digest": manifest["manifest_sha256"],
        }
    )
    raw["preferences"]["motion_profile"] = profile
    raw["governance"]["allowed_semantic_actions"] = sorted(allowed)
    raw["governance"]["denied_semantic_actions"] = sorted(denied)
    raw["evidence"]["package_digest"] = manifest["sources"]["package_sha256"]
    raw["evidence"]["score_binding"] = {
        "score_id": None,
        "score_revision": None,
        "score_sha256": None,
    }
    return PerformanceContextV1.build(raw)


class HighLevelDirectionCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = derive_character_capability_manifest()

    def test_high_level_example_compiles_through_existing_loader_and_scheduler(self):
        context = _context(self.manifest)
        request = _request(
            "Wizard Joe enters with delighted surprise, circles toward center stage, "
            "stops, leans closer, and tells the user something important.",
            context,
        )

        first = compile_high_level_direction(request, context, self.manifest)
        second = compile_high_level_direction(request, context, self.manifest)

        self.assertEqual(
            canonical_json_v1(first.compiled_score),
            canonical_json_v1(second.compiled_score),
        )
        self.assertEqual(first.plan.plan_sha256, second.plan.plan_sha256)
        self.assertEqual(first.portable_score["mode"], "directed")
        self.assertEqual(first.bound_context.source.media_id, request.media_id)
        self.assertEqual(
            first.bound_context.evidence.score_binding.score_id,
            first.portable_score["score_id"],
        )
        self.assertTrue(
            any(item.reason_code == "circle_to_linear_stage_fallback" for item in first.plan.fallbacks)
        )

        encoded = canonical_json_v1(first.compiled_score)
        self.assertNotIn(request.direction_text.encode("utf-8"), encoded)
        portable_encoded = canonical_json_v1(first.portable_score)
        self.assertNotIn(b"clip:", portable_encoded)
        self.assertNotIn(b"expression:", portable_encoded)
        loaded = CompiledScoreLoader().from_mapping(first.compiled_score)
        self.assertEqual(loaded.media_id, request.media_id)
        self.assertEqual(loaded.media_sha256, request.media_sha256)
        self.assertEqual(loaded.duration_ms, request.duration_ms)
        scheduler = PerformanceScheduler(loaded)

        stage_cue = next(
            cue
            for track in first.compiled_score["tracks"]
            if track["kind"] == "stage"
            for cue in track["cues"]
        )
        halfway = (stage_cue["start_ms"] + stage_cue["end_ms"]) // 2
        stage_state = scheduler.evaluate(halfway)
        self.assertIn("stage", stage_state.owned_channels)
        self.assertNotEqual(stage_state.world_position_milli, (0, 0))
        self.assertEqual(stage_state.facing, "south")

        speaking_cue = next(
            cue
            for track in first.compiled_score["tracks"]
            if track["kind"] == "body_base"
            for cue in track["cues"]
            if cue["intent"] == "explain"
        )
        speaking_state = scheduler.evaluate(
            (speaking_cue["start_ms"] + speaking_cue["end_ms"]) // 2
        )
        self.assertIn(speaking_state.clip_id, {"explain_front", "point_front"})

        with tempfile.TemporaryDirectory() as temporary:
            repository = CompiledScoreRepository(temporary)
            repository.publish(loaded)
            application = PerformanceApplication(
                "directed-runtime-test",
                score_repository=repository,
            )
            snapshot = bound_snapshot(
                loaded,
                position=halfway,
                kind="audiobook",
                mode="narrative",
            )
            prepared = application.prepare_snapshot(snapshot)
            ack = application.accept_snapshot(snapshot, 0)
            controller = WizardAvatarController()
            initial_x = controller.state.world_position["x"]
            applied = application.apply(controller, 0)

        self.assertTrue(prepared.ready)
        self.assertEqual(ack.scheduler_state, "playing")
        self.assertTrue(applied.active)
        self.assertNotEqual(controller.state.world_position["x"], initial_x)

    def test_mid_level_example_preserves_explicit_order_and_three_second_walk_weight(self):
        context = _context(self.manifest)
        request = _request(
            "Walk from stage-left rear to center over three seconds, turn toward the viewer, "
            "transition to warm seriousness, raise the right hand, hold for one second, then speak.",
            context,
        )

        result = compile_high_level_direction(request, context, self.manifest)

        requirements = [step.capability_requirement for step in result.plan.steps]
        self.assertEqual(
            requirements,
            [
                "locomotion.stage_walk",
                "body.viewer_turn",
                "face.focused",
                "gesture.point",
                "gesture.point",
                "body.explain",
            ],
        )
        self.assertEqual(result.plan.steps[0].weight_ms, 3000)
        self.assertEqual(result.plan.steps[4].weight_ms, 1000)

    def test_unsupported_clause_is_rejected_instead_of_silently_substituted(self):
        context = _context(self.manifest)
        request = _request("Wizard Joe backflips over the moon, then speaks.", context)

        with self.assertRaises(DirectionCompileError) as caught:
            compile_high_level_direction(request, context, self.manifest)

        self.assertEqual(caught.exception.code, "direction_unsupported")
        self.assertNotIn("backflips", str(caught.exception).lower())

    def test_governance_denial_fails_closed_before_score_compilation(self):
        context = _context(
            self.manifest,
            allowed=("explain", "listen"),
            denied=("celebrate", "external_action"),
        )
        request = _request("Wizard Joe celebrates, then stops.", context, intent="celebrate")

        with self.assertRaises(DirectionCompileError) as caught:
            compile_high_level_direction(request, context, self.manifest)

        self.assertEqual(caught.exception.code, "direction_not_authorized")

    def test_reduced_motion_removes_stage_travel_but_retains_supported_face_acting(self):
        context = _context(self.manifest, profile="reduced")
        request = _request(
            "Wizard Joe enters toward center stage, transitions to warm seriousness, then speaks.",
            context,
        )
        result = compile_high_level_direction(
            request,
            context,
            self.manifest,
        )

        self.assertFalse(
            any(
                cue
                for track in result.compiled_score["tracks"]
                if track["kind"] == "stage"
                for cue in track["cues"]
            )
        )
        self.assertTrue(
            any(
                cue
                for track in result.compiled_score["tracks"]
                if track["kind"] == "face"
                for cue in track["cues"]
            )
        )
        reasons = {item["reason_code"] for item in result.compiled_score["fallback_records"]}
        self.assertIn("motion_profile_projection", reasons)

    def test_request_contract_is_closed_bounded_and_content_safe(self):
        raw = json.loads(
            json.dumps(
                {
                    "schema_version": 1,
                    "direction_id": "direction:bounded",
                    "direction_text": "Wizard Joe speaks.",
                    "context_sha256": "sha256:" + "d" * 64,
                    "intent": "explain",
                    "duration_ms": 3000,
                    "media_id": "media:sha256:" + "c" * 64,
                    "media_sha256": "sha256:" + "c" * 64,
                    "seed": 0,
                }
            )
        )
        raw["unknown"] = True
        with self.assertRaises(DirectionCompileError) as unknown:
            HighLevelDirectionRequestV1.from_mapping(raw)
        self.assertEqual(unknown.exception.code, "unknown_field")

        raw.pop("unknown")
        raw["direction_text"] = "sk-privatecanary"
        with self.assertRaises(DirectionCompileError) as private:
            HighLevelDirectionRequestV1.from_mapping(raw)
        self.assertEqual(private.exception.code, "private_content")
        self.assertNotIn("privatecanary", str(private.exception))

    def test_request_rejects_stale_context_binding(self):
        original_context = _context(self.manifest)
        request = _request("Wizard Joe speaks.", original_context)
        changed_context = _context(self.manifest, profile="reduced")

        with self.assertRaises(DirectionCompileError) as caught:
            compile_high_level_direction(request, changed_context, self.manifest)

        self.assertEqual(caught.exception.code, "stale_binding")

    def test_material_action_must_match_governed_request_intent(self):
        context = _context(self.manifest)
        request = _request("Wizard Joe celebrates.", context, intent="explain")

        with self.assertRaises(DirectionCompileError) as caught:
            compile_high_level_direction(request, context, self.manifest)

        self.assertEqual(caught.exception.code, "direction_intent_mismatch")


if __name__ == "__main__":
    unittest.main()
