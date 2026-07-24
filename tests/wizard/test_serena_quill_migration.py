import json
import unittest
from collections import Counter
from unittest import mock

from tools.migrate_serena_quill_character import (
    CHARACTER_DIR,
    FROZEN_SOURCE_HASHES,
    INTAKE_DIR,
    OUTPUTS,
    generated_outputs,
)
from wizard_avatar.animation_graph import AnimationGraphValidationError
from wizard_avatar.character_package import load_character_package
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.models import WizardState
from wizard_avatar.pose_selection import select_reference_pose_sample


class SerenaQuillMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pose_library = json.loads(
            (INTAKE_DIR / "serena_quill_pose_cells.json").read_text(
                encoding="utf-8"
            )
        )
        cls.manifest = json.loads(
            OUTPUTS["pose_manifest"].read_text(encoding="utf-8")
        )
        cls.capabilities = json.loads(
            OUTPUTS["capability_manifest"].read_text(encoding="utf-8")
        )

    def test_generated_outputs_are_byte_reproducible(self):
        expected = generated_outputs()

        self.assertEqual(set(expected), set(OUTPUTS.values()))
        for path, content in expected.items():
            self.assertEqual(path.read_bytes(), content, path.name)

    def test_generator_rejects_frozen_source_mismatch(self):
        missing = CHARACTER_DIR / "intake" / "__missing_frozen_source__.json"

        with mock.patch.dict(
            FROZEN_SOURCE_HASHES,
            {missing: "sha256:" + "0" * 64},
        ):
            with self.assertRaisesRegex(
                ValueError,
                "frozen source mismatch",
            ):
                generated_outputs()

    def test_intake_census_and_anchor_contract_are_preserved(self):
        poses = self.pose_library["poses"]

        self.assertEqual(len(poses), 108)
        self.assertEqual(
            Counter(pose["graph_kind"] for pose in poses),
            Counter({"full_body_graph": 92, "feature_graph": 16}),
        )
        required = {
            "root",
            "mouth",
            "left_eye",
            "right_eye",
            "left_foot",
            "right_foot",
            "left_hand",
            "right_hand",
        }
        self.assertTrue(
            all(required.issubset(pose["anchors"]) for pose in poses)
        )
        self.assertEqual(
            sum("orb" in pose["anchors"] for pose in poses),
            45,
        )

    def test_only_evidence_backed_motion_is_admitted(self):
        poses = self.manifest["poses"]

        self.assertEqual(
            Counter(pose["admission"] for pose in poses),
            Counter({"graph_admitted": 79, "diagnostic_only": 29}),
        )
        admitted_motion = {
            pose["id"]
            for pose in poses
            if pose["admission"] == "graph_admitted"
            and pose["locomotion"] != "idle"
        }
        self.assertEqual(
            admitted_motion,
            {"walk_contact_left", "run_contact_left", "jump_airborne"},
        )
        self.assertTrue(
            all(
                pose["admission"] == "diagnostic_only"
                for pose in poses
                if pose["composition"] == "region_overlay"
            )
        )
        reviewed_contacts = {
            pose["id"]
            for pose in poses
            if pose["contact_profile"]["support_contact"] != "none"
        }
        self.assertEqual(
            reviewed_contacts,
            {"walk_contact_left", "run_contact_left"},
        )

    def test_candidate_package_passes_strict_loading_without_registration(self):
        package = load_character_package(OUTPUTS["package"])
        registry = load_character_registry()

        self.assertEqual(package.character_id, "serena-quill-v1")
        self.assertEqual(package.schema_version, 2)
        self.assertEqual(len(package.assets), 10)
        self.assertEqual(
            self.capabilities["status"],
            "migration_candidate_not_registered",
        )
        self.assertEqual(tuple(registry.packages), ("wizard-joe-v1",))
        graph = json.loads(
            OUTPUTS["animation_graph"].read_text(encoding="utf-8")
        )
        selectable = {
            sample["pose_id"]
            for clip in graph["clips"].values()
            for sample in clip["samples"]
        }
        self.assertTrue(
            set(package.runtime_profile_contract.referenced_pose_ids())
            .issubset(selectable)
        )

    def test_serena_contract_does_not_inherit_wizard_staff_semantics(self):
        package = load_character_package(OUTPUTS["package"])
        profile = package.runtime_profile_contract

        self.assertIsNotNone(profile)
        self.assertNotIn("staff", profile.required_anchors)
        self.assertNotIn("staff", profile.optional_anchors)
        self.assertNotIn("staff", profile.props)
        self.assertIn("orb", profile.props)
        self.assertEqual(profile.props["orb"].composition, "whole_pose")
        self.assertEqual(
            self.capabilities["renderer_adapter_id"],
            "asciline.pixel_graph.v1",
        )

    def test_diagnostic_pose_override_fails_closed(self):
        package = load_character_package(OUTPUTS["package"])
        state = WizardState(
            character_id=package.character_id,
            pose_override_id="turn_left",
        )

        with self.assertRaisesRegex(
            AnimationGraphValidationError,
            "not selectable",
        ):
            select_reference_pose_sample(
                state,
                {
                    pose["id"]
                    for pose in self.pose_library["poses"]
                },
                animation_graph_path=package.animation_graph,
                pose_manifest_path=package.pose_manifest,
                pose_library_path=package.pose_library,
                required_anchors=(
                    package.runtime_profile_contract.required_anchors
                ),
                fail_closed=True,
            )

    def test_all_package_paths_remain_character_owned(self):
        package = load_character_package(OUTPUTS["package"])
        character_root = CHARACTER_DIR.resolve()

        self.assertTrue(
            all(
                character_root in asset.path.parents
                for asset in package.assets.values()
            )
        )


if __name__ == "__main__":
    unittest.main()
