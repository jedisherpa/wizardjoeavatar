import copy
import json
import unittest
from pathlib import Path

from wizard_avatar.character_capabilities import (
    CharacterCapabilityManifestValidationError,
    canonical_character_capability_manifest,
    cross_validate_character_capability_manifest,
    derive_character_capability_manifest,
    require_admitted_capability,
    require_graph_admitted_pose,
    validate_character_capability_manifest,
)
from wizard_avatar.permission_world import PermissionWorldCapabilityIndexV1


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    ROOT
    / "wizard_avatar"
    / "definitions"
    / "character_capability_manifest_v1.schema.json"
)


class CharacterCapabilityManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = derive_character_capability_manifest()

    def assert_validation_code(self, code, value):
        with self.assertRaises(CharacterCapabilityManifestValidationError) as caught:
            validate_character_capability_manifest(value)
        self.assertEqual(caught.exception.code, code)

    def test_derivation_is_byte_deterministic_and_has_stable_golden_hash(self):
        first = canonical_character_capability_manifest(self.manifest)
        second = canonical_character_capability_manifest(
            derive_character_capability_manifest()
        )
        self.assertEqual(first, second)

        without_hash = copy.deepcopy(self.manifest)
        without_hash.pop("manifest_sha256")
        self.assertEqual(
            self.manifest["manifest_sha256"],
            "sha256:" + __import__("hashlib").sha256(
                canonical_character_capability_manifest(without_hash)
            ).hexdigest(),
        )
        self.assertEqual(
            self.manifest["manifest_sha256"],
            "sha256:3f9ff9f185a9bd2c20be78718bd03b80e2fcf259c7d96d0afdd03e275448efa3",
        )

    def test_current_character_counts_and_admission_are_truthful(self):
        counts = self.manifest["counts"]
        self.assertEqual(counts["clip_count"], 40)
        self.assertEqual(counts["node_count"], 40)
        self.assertEqual(counts["transition_count"], 91)
        self.assertEqual(counts["pose_count"], 184)
        self.assertEqual(counts["graph_admitted_pose_count"], 128)
        self.assertEqual(counts["diagnostic_only_pose_count"], 56)
        self.assertEqual(counts["expression_count"], 10)
        self.assertEqual(counts["mouth_shape_count"], 7)
        self.assertEqual(counts["capability_count"], 61)
        self.assertEqual(counts["diagnostic_count"], 3)

        admitted = {
            pose["pose_id"]
            for pose in self.manifest["poses"]
            if pose["admission"] == "graph_admitted"
        }
        diagnostic = {
            pose["pose_id"]
            for pose in self.manifest["poses"]
            if pose["admission"] == "diagnostic_only"
        }
        self.assertEqual(len(admitted), 128)
        self.assertEqual(len(diagnostic), 56)
        self.assertFalse(admitted & diagnostic)
        self.assertTrue(all(pose_id.endswith("_close") for pose_id in diagnostic if "_close" in pose_id))
        self.assertFalse(any(pose_id.endswith("_close") for pose_id in admitted))

    def test_graph_capability_carries_exact_transition_contact_and_channel_data(self):
        capabilities = {
            item["capability_id"]: item for item in self.manifest["capabilities"]
        }
        walk = capabilities["clip:walk_front"]
        self.assertEqual(walk["category"], "animation_clip")
        self.assertEqual(walk["admission"], "graph_admitted")
        self.assertEqual(walk["mapping"]["clip_ids"], ["walk_front"])
        self.assertEqual(walk["mapping"]["node_ids"], ["ground_walk"])
        self.assertEqual(
            walk["mapping"]["facings"], ["south", "southeast", "southwest"]
        )
        self.assertEqual(walk["mapping"]["channels"], ["body", "staff", "wings"])
        self.assertEqual(
            walk["mapping"]["locomotion_ids"],
            ["grounded_start", "grounded_stop", "grounded_walk"],
        )
        self.assertEqual(walk["mapping"]["ownership"], "whole_pose")
        self.assertEqual(
            walk["contacts"]["support_contacts"],
            ["left_foot", "none", "right_foot"],
        )
        self.assertEqual(walk["transitions"]["interrupt_policy"], "at_marker")
        self.assertEqual(
            walk["transitions"]["entry_markers"], ["left_contact", "right_contact"]
        )
        self.assertEqual(
            walk["transitions"]["exit_markers"], ["left_contact", "right_contact"]
        )
        self.assertIn("idle_front", walk["transitions"]["legal_exit_clip_ids"])
        self.assertIn("ground_idle", walk["transitions"]["legal_entry_node_ids"])
        self.assertEqual(walk["compatibility"]["speech"], "compatible")
        self.assertEqual(walk["compatibility"]["locomotion"], "compatible")
        self.assertEqual(walk["fallback"]["capability_id"], "clip:idle_front")
        self.assertEqual(walk["fallback"]["reason_code"], "graph_declared_fallback")
        self.assertEqual(walk["quality"]["tier"], "A")
        self.assertEqual(
            walk["provenance"]["source_ids"],
            ["character_package", "animation_graph", "pose_library"],
        )
        self.assertEqual(
            walk["provenance"]["evidence_sha256"],
            [
                "sha256:f991c215d4b7be9bf3a98fbafabba0843e629789bdf0baeb591528dceeac2a1d",
                "sha256:604e22b9dffb36dd759e5aa9dfd77971e9d8023a0139edf24edb5c1fc41f6210",
                "sha256:926a8c9842d2da3512a65d0e27b308e7c65ce8cf1b18120bd52471143a4323ac",
            ],
        )
        self.assertEqual(
            walk["provenance"]["content_sha256"],
            ["sha256:31d3856f94eaf72b08b5f1871c9fa55bec3994ac8310acb310e567ad07b0109d"],
        )

    def test_overlays_and_unsupported_surfaces_are_explicit(self):
        capabilities = {
            item["capability_id"]: item for item in self.manifest["capabilities"]
        }
        expression = capabilities["expression:happy"]
        self.assertEqual(expression["admission"], "runtime_overlay")
        self.assertEqual(expression["mapping"]["expression_ids"], ["happy"])
        self.assertEqual(expression["mapping"]["channels"], ["face", "mouth"])
        self.assertEqual(expression["mapping"]["ownership"], "independently_compositable")

        mouth = capabilities["mouth:open_small"]
        self.assertEqual(mouth["mapping"]["mouth_ids"], ["open_small"])
        self.assertEqual(mouth["mapping"]["channels"], ["mouth"])

        dance = capabilities["unsupported:dance"]
        self.assertEqual(dance["admission"], "unsupported")
        self.assertEqual(dance["fallback"]["reason_code"], "no_runtime_mapping")
        self.assertEqual(dance["mapping"]["pose_ids"], [])

        staff = capabilities["ownership:staff"]
        wings = capabilities["ownership:wings"]
        self.assertEqual(staff["mapping"]["ownership"], "whole_pose")
        self.assertEqual(wings["mapping"]["ownership"], "whole_pose")

    def test_memory_notebook_is_admitted_and_permission_world_indexed(self):
        self.assertEqual(
            self.manifest["permission_world"],
            {
                "bindings": {
                    "world_state_ids": [],
                    "effect_ids": [],
                    "prop_ids": ["memory_notebook"],
                    "requirements": [
                        {
                            "capability_kind": "prop:memory_notebook",
                            "required_scope_class": "current_character",
                            "purpose_code": "conversation_continuity",
                        }
                    ],
                }
            },
        )
        capability = next(
            item
            for item in self.manifest["capabilities"]
            if item["capability_id"] == "prop:memory_notebook"
        )
        self.assertEqual(capability["admission"], "runtime_overlay")
        self.assertEqual(capability["category"], "permission_prop_overlay")
        self.assertEqual(capability["mapping"]["prop_ids"], ["memory_notebook"])
        self.assertEqual(
            capability["mapping"]["ownership"], "independently_compositable"
        )
        self.assertEqual(
            capability["provenance"]["source_ids"],
            ["permission_world", "runtime_renderer"],
        )

        index = PermissionWorldCapabilityIndexV1.from_character_manifest(
            self.manifest
        )
        self.assertEqual(index.world_state_ids, ())
        self.assertEqual(index.effect_ids, ())
        self.assertEqual(index.prop_ids, ("memory_notebook",))

    def test_compiler_guards_reject_diagnostic_and_unsupported_selection(self):
        self.assertEqual(
            require_admitted_capability(self.manifest, "clip:walk_front")["admission"],
            "graph_admitted",
        )
        with self.assertRaises(CharacterCapabilityManifestValidationError) as caught:
            require_admitted_capability(self.manifest, "unsupported:dance")
        self.assertEqual(caught.exception.code, "capability_not_admitted")

        self.assertEqual(
            require_graph_admitted_pose(self.manifest, "front_idle")["admission"],
            "graph_admitted",
        )
        with self.assertRaises(CharacterCapabilityManifestValidationError) as caught:
            require_graph_admitted_pose(self.manifest, "feeling_joy_close")
        self.assertEqual(caught.exception.code, "pose_not_admitted")

    def test_accessibility_is_explicit_and_does_not_overclaim_runtime_enforcement(self):
        capabilities = {
            item["capability_id"]: item for item in self.manifest["capabilities"]
        }
        idle = capabilities["clip:idle_front"]
        self.assertEqual(idle["accessibility"]["full"], "admitted")
        self.assertEqual(
            idle["accessibility"]["reduced"], "admitted_by_scheduler_projection"
        )
        self.assertEqual(
            idle["accessibility"]["still"], "fallback_characterful_neutral"
        )

        cast = capabilities["clip:cast_front"]
        self.assertEqual(
            cast["accessibility"]["reduced"], "admitted_by_scheduler_projection"
        )
        self.assertEqual(
            cast["accessibility"]["still"], "fallback_characterful_neutral"
        )
        self.assertEqual(
            cast["accessibility"]["enforcement"], "compiler_required_runtime_unverified"
        )

    def test_schema_is_closed_and_validation_rejects_tampering(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["$schema"], "https://json-schema.org/draft/2020-12/schema"
        )

        def assert_closed(value):
            if isinstance(value, dict):
                if value.get("type") == "object":
                    self.assertIs(value.get("additionalProperties"), False)
                for child in value.values():
                    assert_closed(child)
            elif isinstance(value, list):
                for child in value:
                    assert_closed(child)

        assert_closed(schema)
        validate_character_capability_manifest(copy.deepcopy(self.manifest))

        extra = copy.deepcopy(self.manifest)
        extra["capabilities"][0]["mapping"]["asset_path"] = "/private/closeup.png"
        self.assert_validation_code("unknown_field", extra)

        bad_hash = copy.deepcopy(self.manifest)
        bad_hash["manifest_sha256"] = "sha256:" + "0" * 64
        self.assert_validation_code("hash_mismatch", bad_hash)

        unadmitted_binding = copy.deepcopy(self.manifest)
        unadmitted_binding["permission_world"]["bindings"]["prop_ids"] = [
            "unknown_prop"
        ]
        self.assert_validation_code(
            "permission_binding_unadmitted", unadmitted_binding
        )

        admitted_closeup = copy.deepcopy(self.manifest)
        closeup = next(
            pose for pose in admitted_closeup["poses"] if pose["pose_id"].endswith("_close")
        )
        closeup["admission"] = "graph_admitted"
        self.assert_validation_code("pose_admission_mismatch", admitted_closeup)

    def test_cross_validation_emits_stable_diagnostics_for_runtime_gaps(self):
        diagnostics = cross_validate_character_capability_manifest(self.manifest)
        by_code = {(item.code, item.subject_id) for item in diagnostics}
        self.assertIn(("runtime_action_unmapped", "thinking"), by_code)
        self.assertIn(("unsupported_surface", "dance"), by_code)
        self.assertIn(("runtime_accessibility_unverified", "motion_profiles"), by_code)
        self.assertFalse(any(item.severity == "error" for item in diagnostics))


if __name__ == "__main__":
    unittest.main()
