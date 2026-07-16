import asyncio
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from wizard_avatar.character_package import MIRA_SOLEN_PACKAGE_PATH, load_character_package
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.server import create_app


ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "assets/reference/personas/mira-solen/generation-profile.json"
DEFINITIONS = ROOT / "wizard_avatar/definitions"


class MiraSolenCharacterTests(unittest.TestCase):
    def make_source(self):
        return ProceduralWizardFrameSource(
            cols=160, rows=100, character_package_path=MIRA_SOLEN_PACKAGE_PATH
        )

    def test_registry_package_and_runtime_lineage(self):
        registry = load_character_registry()
        package = registry.get("mira-solen-v1")
        self.assertEqual(package.display_name, "Mira Solen")
        self.assertIn("artwork_tray_interaction", package.capabilities)
        self.assertIn("student_voice_amplification", package.capabilities)
        manifest = json.loads(package.manifest.read_text())
        hashes = manifest["hashes"]
        self.assertEqual(hashes["generation_profile_sha256"], hashlib.sha256(PROFILE.read_bytes()).hexdigest())
        self.assertEqual(hashes["extraction_item_count"], 124)
        for key, filename in (
            ("pose_library_sha256", "mira_solen_pose_cells.json"),
            ("animation_graph_sha256", "mira_solen_animation_graph.json"),
            ("animation_matrix_sha256", "mira_solen_animation_matrix.json"),
            ("extraction_audit_sha256", "mira_solen_extraction_audit.json"),
            ("pixel_graph_library_sha256", "mira_solen_pixel_graphs.json"),
        ):
            self.assertEqual(hashes[key], hashlib.sha256((DEFINITIONS / filename).read_bytes()).hexdigest())

    def test_original_canonical_and_identity_v3_are_exact(self):
        directory = ROOT / "assets/reference/personas/mira-solen"
        self.assertEqual(hashlib.sha256((directory / "source-reference.png").read_bytes()).hexdigest(), "ee88963dc59ab9efb8f4500734aa8a7b66f67b378e075088207df49cf6e08f6a")
        self.assertEqual(hashlib.sha256((directory / "canonical-voxel.png").read_bytes()).hexdigest(), "7802522fbc0d26370fdb826ab409ca3b8d063eac75c62af1bdf888848bb6561e")
        manifest = json.loads((DEFINITIONS / "mira_solen_character_manifest.json").read_text())
        worksheets = manifest["hashes"]["worksheet_sha256"]
        self.assertEqual(len(worksheets), 9)
        self.assertIn("01-identity-sheet-candidate-v3.png", worksheets)
        self.assertNotIn("01-identity-sheet-candidate-v1.png", worksheets)

    def test_exact_124_transparent_json_graphs_and_no_background_residue(self):
        package = load_character_package(MIRA_SOLEN_PACKAGE_PATH)
        poses = json.loads(package.pose_library.read_text())["poses"]
        identity = json.loads(package.pixel_graph_library.read_text())["graphs"]
        audit = json.loads(package.extraction_audit.read_text())
        self.assertEqual((len(identity), len(poses), audit["item_count"]), (16, 108, 124))
        self.assertEqual(audit["runtime_image_assets"], [])
        self.assertEqual(audit["category_counts"], {
            "identity_reference": 16, "turnaround": 8, "neutral": 8,
            "expression": 24, "viseme_blink": 16, "hand_prop": 16,
            "motion": 16, "signature": 16, "interaction": 4,
        })
        for graph in [*identity, *({"nodes": pose["cells"]} for pose in poses)]:
            self.assertTrue(graph["nodes"])
            self.assertLess(len(graph["nodes"]), 5000)
            self.assertGreaterEqual(min(node["x"] for node in graph["nodes"]), 4)
            self.assertLessEqual(max(node["x"] for node in graph["nodes"]), 67)
            self.assertGreaterEqual(min(node["y"] for node in graph["nodes"]), 4)
            self.assertLessEqual(max(node["y"] for node in graph["nodes"]), 91)
        flame = next(pose for pose in poses if pose["id"] == "blue_flame_inspiration")
        self.assertGreater(sum(1 for node in flame["cells"] if node["rgb"][2] >= 155 and node["rgb"][0] <= 65), 20)

    def test_pose_vocabulary_is_mira_specific_and_has_no_persona_leftovers(self):
        pose_ids = {pose["id"] for pose in json.loads((DEFINITIONS / "mira_solen_pose_cells.json").read_text())["poses"]}
        required = {
            "reveal_artwork_forward", "invite_critique", "shield_dignity",
            "creative_reframe", "amplify_student_voice", "blue_flame_inspiration",
            "prop_tray_level_torso", "expression_inspired_delight",
            "expression_protective_resolve", "interaction_reach",
        }
        self.assertTrue(required.issubset(pose_ids))
        combined = "\n".join((
            PROFILE.read_text(),
            (DEFINITIONS / "mira_solen_runtime_profile.json").read_text(),
            (DEFINITIONS / "mira_solen_animation_graph.json").read_text(),
            (DEFINITIONS / "mira_solen_animation_matrix.json").read_text(),
        )).lower()
        for leftover in ("orion", "journal", "folio", "orb", "serena", "aurelia", "liora", "rohan"):
            self.assertNotIn(leftover, combined)

    def test_generator_is_deterministic(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/generate_voxel_persona_character.py"), str(PROFILE), "--check"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_live_semantic_channels_and_cell_diff(self):
        source = self.make_source()
        idle = source.render_current_frame().cells
        expression_result = source.apply_command_sync(WizardCommand("expression", {"expression": "curiosity"}))
        self.assertTrue(expression_result.ok, expression_result.message)
        inspired = source.render_current_frame().cells
        self.assertNotEqual(idle, inspired)
        source.apply_command_sync(WizardCommand("move", {"x": 2.0, "z": 5.0, "speed": 1.2}))
        source.advance_simulation(0.35)
        walking = source.render_current_frame().cells
        self.assertNotEqual(inspired, walking)
        result = source.apply_command_sync(WizardCommand("action", {"action": "blue_flame_inspiration", "duration_ms": 900}))
        self.assertTrue(result.ok, result.message)
        signature = source.render_current_frame().cells
        self.assertNotEqual(inspired, signature)
        self.assertEqual(source.current_state().pose_id, "blue_flame_inspiration")

    def test_all_mira_semantic_actions_are_addressable(self):
        source = self.make_source()
        expected = {
            "artwork_reveal": "reveal_artwork_forward",
            "invite_critique": "invite_critique",
            "protect_dignity": "shield_dignity",
            "creative_reframe": "creative_reframe",
            "student_voice": "amplify_student_voice",
            "blue_flame_inspiration": "blue_flame_inspiration",
            "listening": "listen_contemplatively",
            "jump": "jump_airborne",
            "fall": "fall_descending",
            "land": "land_contact",
        }
        for action, pose_id in expected.items():
            with self.subTest(action=action):
                result = source.apply_command_sync(WizardCommand("action", {"action": action, "duration_ms": 900}))
                self.assertTrue(result.ok, result.message)
                source.render_current_frame()
                self.assertEqual(source.current_state().pose_id, pose_id)

    def test_forced_pil_failure_proves_runtime_uses_json_nodes_only(self):
        with patch("PIL.Image.open", side_effect=AssertionError("runtime image access")):
            frame = self.make_source().render_current_frame()
        self.assertEqual(len(frame.cells), frame.cols * frame.rows * 4)

    def test_registry_static_rest_and_websocket_surfaces(self):
        app = create_app()
        paths = {route.path for route in app.routes}
        self.assertIn("/api/avatar/characters", paths)
        self.assertIn("/api/avatar/{character_id}/{command_type}", paths)
        self.assertIn("/ws/avatar/{character_id}", paths)
        self.assertIn("/avatar/characters/{character_id}/{asset_name}", paths)
        entries = {entry["character_id"]: entry for entry in load_character_registry().public_entries()}
        self.assertEqual(entries["mira-solen-v1"]["assets"]["pixel_graph_library"], "/avatar/characters/mira-solen-v1/pixel-graph-library")
        route = next(route for route in app.routes if route.path == "/avatar/characters/{character_id}/{asset_name}")
        response = asyncio.run(route.endpoint("mira-solen-v1", "pixel-graph-library"))
        self.assertEqual(Path(response.path).resolve(), (DEFINITIONS / "mira_solen_pixel_graphs.json").resolve())


if __name__ == "__main__":
    unittest.main()
