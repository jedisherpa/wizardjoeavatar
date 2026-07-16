import asyncio
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from wizard_avatar.character_package import (
    AURELIA_FINCH_PACKAGE_PATH,
    CharacterPackageValidationError,
    load_character_package,
)
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.server import create_app


ROOT = Path(__file__).resolve().parents[2]
PERSONA = ROOT / "assets" / "reference" / "personas" / "aurelia-finch"
PROFILE = PERSONA / "generation-profile.json"
DEFINITIONS = ROOT / "wizard_avatar" / "definitions"


class AureliaFinchCharacterTests(unittest.TestCase):
    def make_source(self):
        return ProceduralWizardFrameSource(
            cols=160, rows=100, character_package_path=AURELIA_FINCH_PACKAGE_PATH
        )

    def test_registry_package_and_character_scoped_assets(self):
        registry = load_character_registry()
        package = registry.get("aurelia-finch-v1")
        self.assertEqual(package.display_name, "Aurelia Finch")
        self.assertIsNotNone(package.runtime_profile)
        self.assertIsNotNone(package.manifest)
        self.assertIsNotNone(package.extraction_audit)
        self.assertIsNotNone(package.pixel_graph_library)
        self.assertTrue({
            "partnership_pitch", "stakeholder_translation", "proof_presentation",
            "public_promise_check", "leadership_briefing", "diplomatic_recovery",
        }.issubset(package.capabilities))
        entry = {item["character_id"]: item for item in registry.public_entries()}[
            "aurelia-finch-v1"
        ]
        self.assertEqual(
            entry["assets"]["pixel_graph_library"],
            "/avatar/characters/aurelia-finch-v1/pixel-graph-library",
        )

    def test_source_lineage_and_generated_hashes(self):
        self.assertEqual(
            hashlib.sha256((PERSONA / "source-reference.png").read_bytes()).hexdigest(),
            "bd8bc74059e57f8edafb0161bcbc7b70dd52ddddc59ec72dd1808f8287c87f41",
        )
        self.assertEqual(
            hashlib.sha256((PERSONA / "canonical-voxel.png").read_bytes()).hexdigest(),
            "462dbff7c21e06c4450bf620f13f0bb7c923f57dd4819cb11eb9bfcc8853a821",
        )
        manifest = json.loads(
            (DEFINITIONS / "aurelia_finch_character_manifest.json").read_text()
        )
        hashes = manifest["hashes"]
        self.assertEqual(hashes["extraction_item_count"], 124)
        self.assertEqual(len(hashes["worksheet_sha256"]), 9)
        for key, filename in (
            ("character_package_sha256", "aurelia_finch_character_package.json"),
            ("runtime_profile_sha256", "aurelia_finch_runtime_profile.json"),
            ("pose_library_sha256", "aurelia_finch_pose_cells.json"),
            ("animation_graph_sha256", "aurelia_finch_animation_graph.json"),
            ("animation_matrix_sha256", "aurelia_finch_animation_matrix.json"),
            ("extraction_audit_sha256", "aurelia_finch_extraction_audit.json"),
            ("pixel_graph_library_sha256", "aurelia_finch_pixel_graphs.json"),
        ):
            self.assertEqual(hashes[key], hashlib.sha256((DEFINITIONS / filename).read_bytes()).hexdigest())

    def test_exact_124_transparent_colored_graphs_and_no_blue_background(self):
        package = load_character_package(AURELIA_FINCH_PACKAGE_PATH)
        poses = json.loads(package.pose_library.read_text())["poses"]
        references = json.loads(package.pixel_graph_library.read_text())["graphs"]
        audit = json.loads(package.extraction_audit.read_text())
        self.assertEqual(len(poses), 108)
        self.assertEqual(len(references), 16)
        self.assertEqual(audit["item_count"], 124)
        self.assertEqual(audit["category_counts"], {
            "identity_reference": 16, "turnaround": 8, "neutral": 8,
            "expression": 24, "viseme_blink": 16, "hand_prop": 16,
            "motion": 16, "signature": 16, "interaction": 4,
        })
        graphs = {item["id"]: item["nodes"] for item in references}
        graphs.update({item["id"]: item["cells"] for item in poses})
        self.assertEqual(set(graphs), {item["graph_id"] for item in audit["items"]})
        for item in audit["items"]:
            nodes = graphs[item["graph_id"]]
            self.assertTrue(nodes)
            self.assertTrue(item["background_removed"])
            self.assertTrue(item["floor_shadow_removed"])
            self.assertEqual(item["runtime_format"], "colored_pixel_nodes_json")
            self.assertEqual(item["projected_diff_pixel_count"], 0)
            self.assertEqual(item["validation_result"], "passed")
            self.assertNotIn(".png", item["runtime_asset"].lower())
            self.assertEqual(item["pixel_node_count"], len(nodes))
            compact = json.dumps(nodes, separators=(",", ":"), sort_keys=True)
            self.assertEqual(item["pixel_graph_sha256"], hashlib.sha256(compact.encode()).hexdigest())
            for node in nodes:
                red, green, blue = node["rgb"]
                self.assertFalse(
                    blue >= 100 and blue >= red + 20 and blue >= green + 12,
                    (item["graph_id"], node),
                )

    def test_exact_worksheet_pose_semantics_without_inherited_orion_ids(self):
        profile = json.loads(PROFILE.read_text())
        ids = [item["id"] for item in profile["poses"]]
        expected = {
            "partnership_pitch_compose", "partnership_pitch_invitation",
            "partnership_pitch_outward_pitch", "partnership_pitch_recovery",
            "stakeholder_translation_listen", "stakeholder_translation_two_hand_translation",
            "stakeholder_translation_bridge", "stakeholder_translation_acknowledge",
            "proof_presentation_ready", "proof_presentation_reveal_blank_evidence",
            "proof_presentation_point_to_proof", "proof_presentation_close_and_secure",
            "public_promise_check_pause", "public_promise_check_commitment",
            "leadership_recovery_reconsider", "leadership_recovery_diplomatic_settle",
            "stakeholder_handshake", "prop_blank_evidence_page", "diplomatic_open_palms",
        }
        self.assertTrue(expected.issubset(ids))
        inherited = {
            "gesture_explain", "inquiry_hidden_question", "folio_write", "folio_page_turn",
            "listen_socratic", "orion_idle", "run_reach", "run_drive",
        }
        self.assertTrue(inherited.isdisjoint(ids))
        graph_text = json.dumps(profile["animation_graph"])
        self.assertNotIn("orion", graph_text.lower())
        identity_text = json.dumps(profile["identity_lock"]).lower()
        self.assertNotIn("beard", identity_text)
        self.assertNotIn("glasses", identity_text)

    def test_deterministic_generator_and_hashed_124_up_evidence(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "generate_voxel_persona_character.py"), str(PROFILE), "--check"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        evidence = ROOT / "evidence" / "aurelia-finch"
        summary = json.loads((evidence / "aurelia-finch-124-visual-audit.json").read_text())
        self.assertEqual(summary["cell_count"], 124)
        self.assertEqual(summary["failed_count"], 0)
        self.assertTrue(all(item["different_nodes"] == 0 for item in summary["comparisons"]))
        for filename, key in (
            ("aurelia-finch-124-isolated-silhouettes.png", "isolated_contact_sheet_sha256"),
            ("aurelia-finch-124-pixel-graph-renders.png", "projected_contact_sheet_sha256"),
        ):
            self.assertEqual(hashlib.sha256((evidence / filename).read_bytes()).hexdigest(), summary[key])

    def test_semantic_actions_are_live_and_persona_specific(self):
        source = self.make_source()
        expected = {
            "partnership_pitch": "partnership_pitch_outward_pitch",
            "stakeholder_translation": "stakeholder_translation_bridge",
            "proof_presentation": "proof_presentation_reveal_blank_evidence",
            "public_promise_check": "public_promise_check_commitment",
            "leadership_briefing": "proof_presentation_ready",
            "leadership_recovery": "leadership_recovery_reconsider",
            "diplomatic_recovery": "leadership_recovery_diplomatic_settle",
            "turn_left": "planted_turn_left", "turn_right": "planted_turn_right",
            "fall": "controlled_fall", "land": "landing_contact",
        }
        for action, pose_id in expected.items():
            result = source.apply_command_sync(WizardCommand("action", {"action": action, "duration_ms": 900}))
            self.assertTrue(result.ok, result.message)
            source.render_current_frame()
            self.assertEqual(source.current_state().pose_id, pose_id)

    def test_runtime_channels_routes_websocket_shape_and_forced_pil_failure(self):
        with patch("PIL.Image.open", side_effect=AssertionError("runtime image access")):
            source = self.make_source()
            idle = source.render_current_frame().cells
            source.apply_command_sync(WizardCommand("move", {"x": 2.0, "z": 5.0, "speed": 1.2}))
            source.advance_simulation(0.35)
            walking = source.render_current_frame().cells
            self.assertNotEqual(idle, walking)
        app = create_app()
        paths = {route.path for route in app.routes}
        self.assertIn("/api/avatar/characters", paths)
        self.assertIn("/api/avatar/{character_id}/{command_type}", paths)
        self.assertIn("/ws/avatar/{character_id}", paths)
        route = next(route for route in app.routes if route.path == "/avatar/characters/{character_id}/{asset_name}")
        response = asyncio.run(route.endpoint("aurelia-finch-v1", "pixel-graph-library"))
        self.assertEqual(Path(response.path).resolve(), (DEFINITIONS / "aurelia_finch_pixel_graphs.json").resolve())

    def test_package_rejects_audited_graph_and_manifest_tampering(self):
        audit_path = (DEFINITIONS / "aurelia_finch_extraction_audit.json").resolve()
        tampered = json.loads(audit_path.read_text())
        tampered["items"][0]["pixel_graph_sha256"] = "0" * 64
        original = Path.read_text
        def controlled(path, *args, **kwargs):
            return json.dumps(tampered) if path.resolve() == audit_path else original(path, *args, **kwargs)
        with patch.object(Path, "read_text", new=controlled):
            with self.assertRaisesRegex(CharacterPackageValidationError, "hash differs"):
                load_character_package(AURELIA_FINCH_PACKAGE_PATH)

    def test_package_rejects_source_canonical_and_worksheet_lineage_tampering(self):
        manifest = json.loads(
            (DEFINITIONS / "aurelia_finch_character_manifest.json").read_text()
        )
        targets = [
            (PROFILE, "generation_profile"),
            (PERSONA / "source-reference.png", "original_reference"),
            (PERSONA / "canonical-voxel.png", "canonical_reference"),
            (AURELIA_FINCH_PACKAGE_PATH, "manifest hash differs"),
            (DEFINITIONS / "aurelia_finch_runtime_profile.json", "manifest hash differs"),
            (DEFINITIONS / "aurelia_finch_pose_cells.json", "manifest hash differs"),
            (DEFINITIONS / "aurelia_finch_animation_graph.json", "manifest hash differs"),
            (DEFINITIONS / "aurelia_finch_animation_matrix.json", "manifest hash differs"),
            (DEFINITIONS / "aurelia_finch_extraction_audit.json", "manifest hash differs"),
            (DEFINITIONS / "aurelia_finch_pixel_graphs.json", "manifest hash differs"),
        ]
        targets.extend(
            (
                PERSONA / "canonical-worksheets" / filename,
                "accepted worksheet",
            )
            for filename in manifest["hashes"]["worksheet_sha256"]
        )
        original = Path.read_bytes
        for target, expected_message in targets:
            resolved = target.resolve()

            def controlled(path, *args, **kwargs):
                payload = original(path, *args, **kwargs)
                return payload + b"tampered" if path.resolve() == resolved else payload

            with self.subTest(target=target.name):
                with patch.object(Path, "read_bytes", new=controlled):
                    with self.assertRaisesRegex(
                        CharacterPackageValidationError, expected_message
                    ):
                        load_character_package(AURELIA_FINCH_PACKAGE_PATH)


if __name__ == "__main__":
    unittest.main()
