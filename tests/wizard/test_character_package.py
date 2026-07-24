import json
import re
import tempfile
import unittest
from pathlib import Path

from wizard_avatar.artifact_hashing import sha256_ref
from wizard_avatar.animation_graph import (
    AnimationGraphValidationError,
    clear_animation_graph_cache,
    load_animation_graph,
)
from wizard_avatar.character_package import (
    CharacterPackageValidationError,
    load_character_package,
)
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.reference_avatar import (
    clear_reference_pose_cache,
    get_reference_pose,
)


class CharacterPackageTests(unittest.TestCase):
    def test_wizard_package_loads_all_production_assets(self):
        package = load_character_package()
        self.assertEqual(package.character_id, "wizard-joe-v1")
        self.assertIn("flight_locomotion", package.capabilities)
        self.assertTrue(package.pose_library.is_file())
        self.assertEqual(package.schema_version, 1)
        self.assertEqual(package.runtime_api_min, 1)
        self.assertEqual(package.runtime_api_max, 1)
        self.assertEqual(
            package.renderer_adapter_id,
            "asciline.legacy_square_cells.v1",
        )

    def test_second_character_uses_same_loader_without_runtime_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "poses.json").write_text(
                json.dumps(
                    {
                        "poses": {
                            "idle": {
                                "description": "Second character idle",
                                "cols": 3,
                                "rows": 3,
                                "root_anchor": [1, 2],
                                "anchors": {"root": [1, 2], "mouth": [1, 1]},
                                "cells": [
                                    {"x": 1, "y": 0, "rgb": [22, 190, 120]},
                                    {"x": 0, "y": 1, "rgb": [250, 90, 90]},
                                    {"x": 1, "y": 1, "rgb": [250, 90, 90]},
                                    {"x": 2, "y": 1, "rgb": [250, 90, 90]},
                                ],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (root / "graph.json").write_text(
                json.dumps({"clips": [{"samples": [{"pose_id": "idle"}]}]}), encoding="utf-8"
            )
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "character_id": "second-character",
                        "display_name": "Second Character",
                        "renderer": "asciline_square_cells",
                        "pose_library": "poses.json",
                        "animation_graph": "graph.json",
                        "default_pose_id": "idle",
                        "capabilities": ["ground_locomotion"],
                    }
                ),
                encoding="utf-8",
            )
            package = load_character_package(root / "package.json")
            self.assertEqual(package.character_id, "second-character")

            source = ProceduralWizardFrameSource(
                cols=64,
                rows=48,
                character_package_path=root / "package.json",
            )
            frame = source.render_next_frame()
            self.assertIsNone(source.animation_graph)
            self.assertEqual(source.current_state().character_id, "second-character")
            self.assertEqual(source.current_state().pose_id, "idle")
            self.assertIn(bytes((ord("#"), 22, 190, 120)), frame.cells)

    def test_v2_package_resolves_and_hash_binds_role_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package_path = self._write_v2_package(root)

            package = load_character_package(package_path)

            self.assertEqual(package.schema_version, 2)
            self.assertEqual(package.character_id, "portable-character-v1")
            self.assertEqual(package.runtime_api_min, 1)
            self.assertEqual(package.runtime_api_max, 2)
            self.assertEqual(
                package.renderer_adapter_id,
                "asciline.pixel_graph.v1",
            )
            self.assertIsNotNone(package.runtime_profile_contract)
            self.assertIn(
                "root",
                package.runtime_profile_contract.required_anchors,
            )
            self.assertEqual(
                set(package.assets),
                {
                    "animation_graph",
                    "capability_manifest",
                    "pose_library",
                    "pose_manifest",
                    "runtime_profile",
                },
            )
            self.assertEqual(
                package.assets["pose_library"].sha256,
                sha256_ref((root / "poses.json").read_bytes()),
            )

    def test_v2_runtime_uses_package_presentation_scale(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package_path = self._write_v2_package(root)
            profile_path = root / "runtime-profile.json"
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            profile["presentation_scale"] = [1, 2]
            profile_path.write_text(
                json.dumps(profile, sort_keys=True),
                encoding="utf-8",
            )
            package_raw = json.loads(package_path.read_text(encoding="utf-8"))
            package_raw["assets"]["runtime_profile"]["sha256"] = sha256_ref(
                profile_path.read_bytes()
            )
            package_path.write_text(
                json.dumps(package_raw, sort_keys=True),
                encoding="utf-8",
            )
            package = load_character_package(package_path)
            source = ProceduralWizardFrameSource.__new__(
                ProceduralWizardFrameSource
            )
            source.character_package = package
            source.pose_library_path = package.pose_library

            self.assertEqual(
                source._reference_presentation_scale("idle"),
                0.5,
            )

    def test_v2_package_rejects_asset_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package_path = self._write_v2_package(root)
            (root / "runtime-profile.json").write_text(
                '{"tampered":true}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CharacterPackageValidationError,
                "does not match asset bytes",
            ):
                load_character_package(package_path)

    def test_v2_package_revalidates_graph_after_cached_source_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package_path = self._write_v2_package(root)
            load_character_package(package_path)
            graph_path = root / "graph.json"
            graph_path.write_text(
                '{"schema_version":2,"clips":[]}',
                encoding="utf-8",
            )
            package_raw = json.loads(package_path.read_text(encoding="utf-8"))
            package_raw["assets"]["animation_graph"]["sha256"] = sha256_ref(
                graph_path.read_bytes()
            )
            package_path.write_text(
                json.dumps(package_raw, sort_keys=True),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CharacterPackageValidationError,
                "not a valid package-owned graph v2",
            ):
                load_character_package(package_path)

    def test_v2_package_admission_invalidates_graph_and_pose_caches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package_path = self._write_v2_package(root)
            first = load_character_package(package_path)
            first_graph = load_animation_graph(
                first.animation_graph,
                pose_manifest_path=first.pose_manifest,
                pose_library_path=first.pose_library,
            )
            first_pose = get_reference_pose("idle", first.pose_library)
            self.assertEqual(first_pose.cells[0].rgb, (255, 255, 255))

            graph_path = root / "graph.json"
            graph_raw = json.loads(graph_path.read_text(encoding="utf-8"))
            graph_raw["$id"] = "portable-character-graph-v2-revised"
            graph_path.write_text(
                json.dumps(graph_raw, sort_keys=True),
                encoding="utf-8",
            )
            pose_path = root / "poses.json"
            pose_raw = json.loads(pose_path.read_text(encoding="utf-8"))
            pose_raw["poses"][0]["cells"][0]["rgb"] = [12, 34, 56]
            pose_path.write_text(
                json.dumps(pose_raw, sort_keys=True),
                encoding="utf-8",
            )
            package_raw = json.loads(package_path.read_text(encoding="utf-8"))
            package_raw["assets"]["animation_graph"]["sha256"] = sha256_ref(
                graph_path.read_bytes()
            )
            package_raw["assets"]["pose_library"]["sha256"] = sha256_ref(
                pose_path.read_bytes()
            )
            package_path.write_text(
                json.dumps(package_raw, sort_keys=True),
                encoding="utf-8",
            )

            revised = load_character_package(package_path)
            revised_graph = load_animation_graph(
                revised.animation_graph,
                pose_manifest_path=revised.pose_manifest,
                pose_library_path=revised.pose_library,
            )
            revised_pose = get_reference_pose("idle", revised.pose_library)

            self.assertNotEqual(first_graph.graph_id, revised_graph.graph_id)
            self.assertEqual(
                revised_graph.graph_id,
                "portable-character-graph-v2-revised",
            )
            self.assertEqual(revised_pose.cells[0].rgb, (12, 34, 56))

    def test_v2_runtime_rejects_asset_changes_after_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = load_character_package(self._write_v2_package(root))

            pose_path = root / "poses.json"
            original_pose_bytes = pose_path.read_bytes()
            pose_path.write_text('{"tampered":true}', encoding="utf-8")
            clear_reference_pose_cache()
            with self.assertRaisesRegex(
                ValueError,
                "Verified reference pose library bytes changed",
            ):
                get_reference_pose("idle", package.pose_library)

            pose_path.write_bytes(original_pose_bytes)
            graph_path = root / "graph.json"
            graph_path.write_text('{"tampered":true}', encoding="utf-8")
            clear_animation_graph_cache()
            with self.assertRaisesRegex(
                AnimationGraphValidationError,
                "verified asset bytes changed",
            ):
                load_animation_graph(
                    package.animation_graph,
                    pose_manifest_path=package.pose_manifest,
                    pose_library_path=package.pose_library,
                )

    def test_v2_profile_references_must_be_selectable_graph_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package_path = self._write_v2_package(root)

            poses_path = root / "poses.json"
            poses = json.loads(poses_path.read_text(encoding="utf-8"))
            other = dict(poses["poses"][0])
            other["id"] = "other"
            other["source"] = "generated:other"
            poses["poses"].append(other)
            poses_path.write_text(
                json.dumps(poses, sort_keys=True),
                encoding="utf-8",
            )

            manifest_path = root / "pose-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            other_manifest = dict(manifest["poses"][0])
            other_manifest["id"] = "other"
            other_manifest["source"] = "generated:other"
            manifest["poses"].append(other_manifest)
            manifest_path.write_text(
                json.dumps(manifest, sort_keys=True),
                encoding="utf-8",
            )

            graph_path = root / "graph.json"
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            graph["pose_classification"]["other"] = {
                "roles": ["clip_sample"],
                "altitude_class": "grounded",
                "support_contact": "none",
                "planted_anchor": None,
                "wing_mode": "hidden",
                "staff_mode": "absent",
                "capability_tier": "A",
            }
            other_clip = dict(graph["clips"]["idle"])
            other_clip["clip_id"] = "other"
            other_clip["samples"] = [
                {
                    "pose_id": "other",
                    "duration_frames": 1,
                    "support_contact": "none",
                    "planted_anchor": None,
                    "markers": [],
                }
            ]
            graph["clips"]["other"] = other_clip
            graph_path.write_text(
                json.dumps(graph, sort_keys=True),
                encoding="utf-8",
            )

            profile_path = root / "runtime-profile.json"
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            profile["facing_poses"]["north"] = "other"
            profile_path.write_text(
                json.dumps(profile, sort_keys=True),
                encoding="utf-8",
            )

            package = json.loads(package_path.read_text(encoding="utf-8"))
            for role, path in (
                ("pose_library", poses_path),
                ("pose_manifest", manifest_path),
                ("animation_graph", graph_path),
                ("runtime_profile", profile_path),
            ):
                package["assets"][role]["sha256"] = sha256_ref(
                    path.read_bytes()
                )
            package_path.write_text(
                json.dumps(package, sort_keys=True),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CharacterPackageValidationError,
                "absent from graph clips: other",
            ):
                load_character_package(package_path)

    def test_v2_package_rejects_unsupported_adapter_and_runtime_api(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package_path = self._write_v2_package(root)
            package_raw = json.loads(package_path.read_text(encoding="utf-8"))
            package_raw["renderer_adapter_id"] = "asciline.missing.v99"
            package_raw["runtime_api"] = {"min": 99, "max": 100}
            package_path.write_text(
                json.dumps(package_raw, sort_keys=True),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CharacterPackageValidationError,
                "renderer_adapter_id is not supported",
            ):
                load_character_package(package_path)

            package_raw["renderer_adapter_id"] = "asciline.pixel_graph.v1"
            package_path.write_text(
                json.dumps(package_raw, sort_keys=True),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                CharacterPackageValidationError,
                "runtime_api does not intersect",
            ):
                load_character_package(package_path)

    def test_v2_package_rejects_absolute_asset_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package_path = self._write_v2_package(root)
            package_raw = json.loads(package_path.read_text(encoding="utf-8"))
            package_raw["assets"]["runtime_profile"]["path"] = str(
                (root / "runtime-profile.json").resolve()
            )
            package_path.write_text(
                json.dumps(package_raw, sort_keys=True),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CharacterPackageValidationError,
                "must be a relative path",
            ):
                load_character_package(package_path)

    def test_package_schemas_reject_absolute_paths(self):
        definitions = (
            Path(__file__).resolve().parents[2] / "wizard_avatar" / "definitions"
        )
        v1 = json.loads(
            (definitions / "character_package.schema.json").read_text(
                encoding="utf-8"
            )
        )
        v2 = json.loads(
            (definitions / "character_package_v2.schema.json").read_text(
                encoding="utf-8"
            )
        )
        patterns = (
            v1["properties"]["pose_library"]["pattern"],
            v1["properties"]["animation_graph"]["pattern"],
            v2["$defs"]["asset"]["properties"]["path"]["pattern"],
        )
        for pattern in patterns:
            self.assertIsNotNone(re.search(pattern, "assets/poses.json"))
            self.assertIsNone(re.search(pattern, "/tmp/poses.json"))
            self.assertIsNone(re.search(pattern, r"C:\poses.json"))
            self.assertIsNone(re.search(pattern, r"\\server\poses.json"))

    @staticmethod
    def _write_v2_package(root: Path) -> Path:
        anchors = {
            "root": [0, 0],
            "mouth": [0, 0],
            "left_eye": [0, 0],
            "right_eye": [0, 0],
            "left_foot": [0, 0],
            "right_foot": [0, 0],
            "left_hand": [0, 0],
            "right_hand": [0, 0],
            "staff_hand": [0, 0],
            "staff_tip": [0, 0],
        }
        pose_metadata = {
            "facing": "south",
            "locomotion": "idle",
            "actions": ["idle"],
            "phase": None,
            "tags": ["idle"],
        }
        files = {
            "poses.json": {
                "asset_set_id": "portable-character-assets-v1",
                "poses": [
                    {
                        "id": "idle",
                        "description": "idle",
                        "source": "generated:idle",
                        "cols": 1,
                        "rows": 1,
                        "root_anchor": [0, 0],
                        "anchors": anchors,
                        "cells": [{"x": 0, "y": 0, "rgb": [255, 255, 255]}],
                        **pose_metadata,
                    }
                ],
            },
            "graph.json": {
                "$schema": "character-graph-v2",
                "$id": "portable-character-graph-v2",
                "schema_version": 2,
                "asset_set_id": "portable-character-assets-v1",
                "authored_fps": 24,
                "simulation_hz": 60,
                "default_node_id": "idle",
                "capability_tiers": {
                    "A": {"description": "authored"},
                    "B": {"description": "fallback"},
                    "C": {"description": "unsupported"},
                },
                "pose_classification": {
                    "idle": {
                        "roles": ["clip_sample"],
                        "altitude_class": "grounded",
                        "support_contact": "both_feet",
                        "planted_anchor": "left_foot",
                        "wing_mode": "hidden",
                        "staff_mode": "absent",
                        "capability_tier": "A",
                    }
                },
                "clips": {
                    "idle": {
                        "clip_id": "idle",
                        "family": "idle",
                        "supported_facings": ["south"],
                        "loop_mode": "loop",
                        "phase_source": "time",
                        "root_policy": "fixed",
                        "minimum_hold_ticks": 1,
                        "interrupt_policy": "immediate",
                        "channel_ownership": ["body"],
                        "samples": [
                            {
                                "pose_id": "idle",
                                "duration_frames": 1,
                                "support_contact": "both_feet",
                                "planted_anchor": "left_foot",
                                "markers": [],
                            }
                        ],
                        "entry_markers": [],
                        "exit_markers": [],
                        "secondary_curves": {},
                        "legal_successors": ["idle"],
                    }
                },
                "nodes": {
                    "idle": {
                        "clip_id": "idle",
                        "mobility_modes": ["grounded_idle"],
                        "actions": [],
                    }
                },
                "transitions": [],
                "transition_recipes": {},
                "channel_masks": {"body": ["body"]},
                "fallbacks": {
                    "grounded_clip_id": "idle",
                    "airborne_clip_id": "idle",
                    "by_facing": {
                        "north": "idle",
                        "northeast": "idle",
                        "east": "idle",
                        "southeast": "idle",
                        "south": "idle",
                        "southwest": "idle",
                        "west": "idle",
                        "northwest": "idle",
                    },
                    "by_action": {},
                },
            },
            "pose-manifest.json": {
                "asset_set_id": "portable-character-assets-v1",
                "poses": [
                    {
                        "id": "idle",
                        "source": "generated:idle",
                        "description": "idle",
                        **pose_metadata,
                    }
                ],
            },
            "runtime-profile.json": {
                "schema_version": 1,
                "character_id": "portable-character-v1",
                "default_pose_id": "idle",
                "presentation_scale": [1, 1],
                "required_anchors": sorted(anchors),
                "optional_anchors": [],
                "facing_poses": {
                    "north": "idle",
                    "northeast": "idle",
                    "east": "idle",
                    "southeast": "idle",
                    "south": "idle",
                    "southwest": "idle",
                    "west": "idle",
                    "northwest": "idle",
                },
                "action_poses": {},
                "expression_aliases": {},
                "locomotion_cycles": {
                    "walk": [],
                    "run": [],
                    "flight": [],
                },
                "speech_poses": [],
                "blink_poses": {
                    "open": "idle",
                    "half_closed": "idle",
                    "closed": "idle",
                },
                "props": {},
            },
            "capabilities.json": {"capabilities": ["idle"]},
        }
        for name, payload in files.items():
            (root / name).write_text(
                json.dumps(payload, sort_keys=True),
                encoding="utf-8",
            )
        role_paths = {
            "pose_library": "poses.json",
            "pose_manifest": "pose-manifest.json",
            "animation_graph": "graph.json",
            "runtime_profile": "runtime-profile.json",
            "capability_manifest": "capabilities.json",
        }
        package_path = root / "package.json"
        package_path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "character_id": "portable-character-v1",
                    "display_name": "Portable Character",
                    "runtime_api": {"min": 1, "max": 2},
                    "renderer": "asciline_square_cells",
                    "renderer_adapter_id": "asciline.pixel_graph.v1",
                    "assets": {
                        role: {
                            "path": path,
                            "sha256": sha256_ref((root / path).read_bytes()),
                        }
                        for role, path in role_paths.items()
                    },
                    "default_pose_id": "idle",
                    "capabilities": ["idle"],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return package_path


if __name__ == "__main__":
    unittest.main()
