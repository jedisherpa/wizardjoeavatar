import unittest
from pathlib import Path
from unittest import mock

from wizard_avatar import character_capabilities


ROOT = Path(__file__).resolve().parents[2]
SERENA_PACKAGE_PATH = (
    ROOT
    / "wizard_avatar"
    / "definitions"
    / "characters"
    / "serena_quill"
    / "serena_quill_character_package_v2.json"
)


class CharacterCapabilityPortabilityTests(unittest.TestCase):
    def test_runtime_manifest_does_not_read_workstation_source_images(self):
        with mock.patch.object(
            character_capabilities,
            "_source_asset_path",
            side_effect=AssertionError("runtime attempted to resolve a source PNG"),
        ):
            manifest = character_capabilities.derive_character_capability_manifest()

        self.assertGreater(manifest["counts"]["pose_count"], 0)
        self.assertTrue(
            all(pose["source_asset_sha256"] is None for pose in manifest["poses"])
        )

    def test_verified_v2_package_derives_a_deterministic_character_owned_manifest(self):
        first = character_capabilities.derive_character_capability_manifest(
            SERENA_PACKAGE_PATH
        )
        second = character_capabilities.derive_character_capability_manifest(
            SERENA_PACKAGE_PATH
        )

        self.assertEqual(first, second)
        self.assertEqual(first["character"]["package_schema_version"], 2)
        self.assertEqual(
            first["manifest_sha256"],
            "sha256:1091df47baf476ea34051fc124e484291c3919212704dc4eb34536249eae42f1",
        )
        self.assertEqual(first["character"]["character_id"], "serena-quill-v1")
        self.assertEqual(
            first["sources"]["package_sha256"],
            "sha256:33b37cfb14f95664992f9bd01d7a8b8474500f092a72d74d3cba53f96404e4d0",
        )
        self.assertEqual(
            first["sources"]["runtime_vocabulary_sha256"],
            "sha256:11d2977fe0dddbee799ee7c882495aeab96f9e984d2f289ad146a57a6ac19208",
        )
        self.assertEqual(
            first["sources"]["runtime_mapping_sha256"],
            "sha256:c61e6da543c11be1541c70a681c5ec98220479753e458910ba51c9275879ca18",
        )
        self.assertEqual(
            first["counts"],
            {
                "package_capability_count": 5,
                "clip_count": 79,
                "node_count": 79,
                "transition_count": 156,
                "pose_count": 108,
                "graph_admitted_pose_count": 79,
                "diagnostic_only_pose_count": 29,
                "expression_count": 0,
                "mouth_shape_count": 0,
                "capability_count": 80,
                "diagnostic_count": 4,
            },
        )

    def test_v2_manifest_does_not_read_workstation_source_images(self):
        with mock.patch.object(
            character_capabilities,
            "_source_asset_path",
            side_effect=AssertionError("runtime attempted to resolve a source PNG"),
        ):
            manifest = character_capabilities.derive_character_capability_manifest(
                SERENA_PACKAGE_PATH
            )

        self.assertEqual(manifest["character"]["character_id"], "serena-quill-v1")
        self.assertTrue(
            all(pose["source_asset_sha256"] is None for pose in manifest["poses"])
        )

    def test_v2_manifest_does_not_inherit_wizard_overlays_or_permission_props(self):
        manifest = character_capabilities.derive_character_capability_manifest(
            SERENA_PACKAGE_PATH
        )
        capability_ids = {
            item["capability_id"] for item in manifest["capabilities"]
        }

        self.assertFalse(
            any(
                capability_id.startswith(
                    ("expression:", "mouth:", "ownership:", "prop:")
                )
                for capability_id in capability_ids
            )
        )
        self.assertEqual(
            manifest["permission_world"]["bindings"],
            {
                "world_state_ids": [],
                "effect_ids": [],
                "prop_ids": [],
                "requirements": [],
            },
        )
        self.assertNotIn("clip:idle_front", capability_ids)
        self.assertEqual(
            next(
                item
                for item in manifest["capabilities"]
                if item["capability_id"] == "unsupported:dance"
            )["fallback"]["capability_id"],
            "clip:pose_neutral_front",
        )

    def test_v2_action_maps_to_exact_graph_identity_and_rejects_diagnostic_pose(self):
        manifest = character_capabilities.derive_character_capability_manifest(
            SERENA_PACKAGE_PATH
        )
        capability = character_capabilities.require_admitted_capability(
            manifest,
            "clip:pose_mentoring_invitation",
        )

        self.assertEqual(
            capability["mapping"],
            {
                "action_ids": ["mentoring_invitation"],
                "clip_ids": ["pose_mentoring_invitation"],
                "node_ids": ["node_mentoring_invitation"],
                "pose_ids": ["mentoring_invitation"],
                "expression_ids": [],
                "mouth_ids": [],
                "gaze_ids": [],
                "locomotion_ids": ["grounded"],
                "flight_ids": [],
                "effect_ids": [],
                "prop_ids": [],
                "facings": ["south"],
                "stage_requirements": [],
                "channels": ["body"],
                "ownership": "whole_pose",
            },
        )
        self.assertEqual(capability["accessibility"]["reduced"], "suppressed")
        with self.assertRaises(
            character_capabilities.CharacterCapabilityManifestValidationError
        ) as caught:
            character_capabilities.require_graph_admitted_pose(
                manifest,
                "turn_left",
            )
        self.assertEqual(caught.exception.code, "pose_not_admitted")


if __name__ == "__main__":
    unittest.main()
