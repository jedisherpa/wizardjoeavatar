import copy
import json
import unittest
from dataclasses import FrozenInstanceError

from wizard_avatar.artifact_hashing import canonical_json_v1, sha256_ref
from wizard_avatar.performance_context import (
    PerformanceContextBindingsV1,
    PerformanceContextError,
    PerformanceContextV1,
)


def context_mapping():
    payload = {
        "schema_version": 1,
        "runtime": {
            "wizard_runtime_epoch": "runtime:2026-07-15:0001",
            "simulation_tick": 4242,
            "reconciliation_generation": 7,
            "created_at_monotonic_ms": 900100,
        },
        "source": {
            "connector_session_id": "00000000-0000-4000-8000-000000000011",
            "snapshot_event_id": "00000000-0000-4000-8000-000000000012",
            "accepted_sequence": 83,
            "media_epoch": 4,
            "media_id": "media:sha256:" + "a" * 64,
            "media_sha256": "sha256:" + "a" * 64,
            "source_slot": "speech",
            "source_epoch": "source:0001:speech:4",
            "turn_id": "turn:0042",
            "utterance_id": "utterance:0042:1",
        },
        "clock": {
            "authoritative_media_position_ms": 1750,
            "playback_state": "playing",
            "rate_milli": 1000,
            "snapshot_age_ms": 18,
            "freshness": "fresh",
            "hard_reconcile_reason": "speech_preempted_main",
        },
        "conversation": {
            "intent": "explain",
            "tone": "warm",
            "sensitivity": "ordinary",
            "urgency": "normal",
            "humor_band": 250,
            "uncertainty_band": 125,
            "relational_stance": "collaborative",
            "response_artifact_id": "response:0042",
        },
        "pipeline": {
            "observed_stage": "speaking",
            "mapped_status": "active",
            "stage_started_at_monotonic_ms": 899900,
            "expected_next_event": "speech_ended",
            "cancellation_posture": "not_requested",
            "error_posture": "none",
            "tts_readiness": "ready",
            "alignment_readiness": "ready",
        },
        "approval": {
            "presentation_state": "approved_for_presentation",
            "presentation_artifact_sha256": "sha256:" + "1" * 64,
            "pending_action_posture": "none",
        },
        "character": {
            "character_id": "wizard-joe",
            "package_digest": "sha256:" + "2" * 64,
            "manifest_digest": "sha256:" + "3" * 64,
            "runtime_api_version": 1,
            "current_pose_id": "pose:front_idle",
            "current_action_id": "action:speaking",
            "position_milli": {"x": 500, "y": 1000, "z": 0},
            "facing": "south",
            "gaze": "direct_viewer",
            "expression": "friendly",
            "world_state": "default",
            "recent_performance": [
                {
                    "performance_id": "performance:0041",
                    "intent": "listen",
                    "disposition": "completed",
                }
            ],
        },
        "display": {
            "width_px": 1280,
            "height_px": 720,
            "scale_factor_milli": 1000,
            "orientation": "landscape",
            "safe_area_px": {"top": 0, "right": 0, "bottom": 24, "left": 0},
            "caption_area_milli": {"x": 50, "y": 760, "width": 900, "height": 190},
            "stage_bounds_milli": {"x": 40, "y": 30, "width": 920, "height": 700},
        },
        "governance": {
            "allowed_semantic_actions": ["explain", "listen"],
            "denied_semantic_actions": ["external_action"],
            "pending_approval_references": [],
            "memory_scope": "session",
            "external_action_posture": "not_requested",
            "notification_scope": "current_surface",
            "linked_surface_state": "unlinked",
        },
        "preferences": {
            "motion_profile": "full",
            "intensity_band": 600,
            "disabled_channels": ["dance", "scene_flash"],
            "caption_mode": "auto",
            "progressive_reveal_preference": "enabled",
            "voice_preference": "synchronized",
        },
        "control": {
            "user_locomotion_lease_id": None,
            "user_locomotion_lease_expires_at_monotonic_ms": None,
            "manual_override_state": "inactive",
            "channel_claims": [
                {
                    "channel": "speech",
                    "owner": "performance",
                    "lease_id": "claim:speech:0042",
                    "expires_at_monotonic_ms": 905000,
                }
            ],
            "cancellation_generation": 3,
        },
        "evidence": {
            "ordered_fingerprints": ["sha256:" + "4" * 64, "sha256:" + "5" * 64],
            "source_commits": [
                {"component": "prism", "commit": "0123456789abcdef0123456789abcdef01234567"},
                {"component": "wizard", "commit": "89abcdef0123456789abcdef0123456789abcdef"},
            ],
            "schema_versions": [
                {"schema_id": "media-session-snapshot", "version": 1},
                {"schema_id": "performance-context", "version": 1},
            ],
            "score_binding": {
                "score_id": "score:speech:0042",
                "score_revision": 2,
                "score_sha256": "sha256:" + "6" * 64,
            },
            "package_digest": "sha256:" + "2" * 64,
        },
    }
    return PerformanceContextV1.build(payload).to_dict()


class PerformanceContextTests(unittest.TestCase):
    def assert_code(self, code, value):
        with self.assertRaises(PerformanceContextError) as caught:
            PerformanceContextV1.from_mapping(value)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_context_is_frozen_deeply_immutable_and_deterministic(self):
        value = context_mapping()
        context = PerformanceContextV1.from_mapping(value)

        self.assertEqual(context.to_dict(), value)
        self.assertEqual(context.canonical_json(), canonical_json_v1(value))
        self.assertEqual(context.content_sha256(), value["context_sha256"])
        self.assertIsInstance(context.character.recent_performance, tuple)
        self.assertIsInstance(context.control.channel_claims, tuple)

        with self.assertRaises(FrozenInstanceError):
            context.schema_version = 2
        with self.assertRaises(TypeError):
            context.character.position_milli["x"] = 0

        unhashed = copy.deepcopy(value)
        unhashed.pop("context_sha256")
        expected = sha256_ref(canonical_json_v1(unhashed))
        self.assertEqual(expected, value["context_sha256"])
        reordered = {key: unhashed[key] for key in reversed(unhashed)}
        self.assertEqual(PerformanceContextV1.build(reordered).context_sha256, expected)

    def test_boundary_rejects_duplicates_floats_unknown_fields_and_private_data(self):
        with self.assertRaises(PerformanceContextError) as caught:
            PerformanceContextV1.from_json(b'{"schema_version":1,"schema_version":1}')
        self.assertEqual(caught.exception.code, "duplicate_json_key")

        value = context_mapping()
        value["conversation"]["humor_band"] = 0.5
        self.assert_code("non_integer_identity_value", value)

        value = context_mapping()
        value["clock"]["extra"] = 1
        self.assert_code("unknown_field", value)

        value = context_mapping()
        value["conversation"]["prompt"] = "private-canary"
        caught = self.assert_code("private_content", value)
        self.assertNotIn("private-canary", str(caught))

        value = context_mapping()
        value["conversation"]["response_artifact_id"] = "Bearer private-canary"
        caught = self.assert_code("private_content", value)
        self.assertNotIn("private-canary", str(caught))

    def test_media_package_score_control_accessibility_and_governance_are_bound(self):
        context = PerformanceContextV1.from_mapping(context_mapping())
        bindings = PerformanceContextBindingsV1.from_context(context)

        self.assertEqual(bindings.media_id, context.source.media_id)
        self.assertEqual(bindings.media_sha256, context.source.media_sha256)
        self.assertEqual(bindings.package_digest, context.character.package_digest)
        self.assertEqual(bindings.score_sha256, context.evidence.score_binding.score_sha256)
        self.assertEqual(bindings.cancellation_generation, context.control.cancellation_generation)
        self.assertEqual(context.preferences.motion_profile, "full")
        self.assertEqual(context.governance.allowed_semantic_actions, ("explain", "listen"))
        context.validate_binding(bindings)

    def test_validate_binding_rejects_every_current_authority_mismatch(self):
        context = PerformanceContextV1.from_mapping(context_mapping())
        current = PerformanceContextBindingsV1.from_context(context)
        replacements = {
            "context_sha256": "sha256:" + "f" * 64,
            "wizard_runtime_epoch": "runtime:other",
            "connector_session_id": "00000000-0000-4000-8000-000000000099",
            "accepted_sequence": 99,
            "media_epoch": 99,
            "media_id": "media:other",
            "media_sha256": "sha256:" + "e" * 64,
            "source_slot": "main",
            "source_epoch": "source:other",
            "turn_id": "turn:other",
            "utterance_id": "utterance:other",
            "character_id": "other-character",
            "package_digest": "sha256:" + "d" * 64,
            "reconciliation_generation": 99,
            "score_sha256": "sha256:" + "c" * 64,
            "cancellation_generation": 99,
        }
        for field, replacement in replacements.items():
            with self.subTest(field=field):
                values = current.to_dict()
                values[field] = replacement
                with self.assertRaises(PerformanceContextError) as caught:
                    context.validate_binding(PerformanceContextBindingsV1(**values))
                self.assertEqual(caught.exception.code, "stale_binding")
                self.assertEqual(caught.exception.path, "$.{}".format(field))

    def test_media_identity_and_cross_group_package_binding_are_strict(self):
        value = context_mapping()
        value["source"]["media_id"] = "media:sha256:" + "b" * 64
        self.assert_code("hash_mismatch", value)

        value = context_mapping()
        value["evidence"]["package_digest"] = "sha256:" + "9" * 64
        self.assert_code("invalid_binding", value)

        value = context_mapping()
        value["evidence"]["score_binding"]["score_sha256"] = None
        self.assert_code("invalid_binding", value)


if __name__ == "__main__":
    unittest.main()
