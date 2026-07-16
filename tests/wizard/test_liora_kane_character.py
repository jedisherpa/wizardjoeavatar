import asyncio
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from wizard_avatar.character_package import (
    LIORA_KANE_PACKAGE_PATH,
    CharacterPackageValidationError,
    load_character_package,
)
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.server import create_app


ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "assets/reference/personas/liora-kane/generation-profile.json"
DEFINITIONS = ROOT / "wizard_avatar/definitions"


class LioraKaneCharacterTests(unittest.TestCase):
    def make_source(self):
        return ProceduralWizardFrameSource(
            cols=160,
            rows=100,
            character_package_path=LIORA_KANE_PACKAGE_PATH,
        )

    def test_registry_and_package_expose_liora(self):
        registry = load_character_registry()
        package = registry.get("liora-kane-v1")
        self.assertEqual(package.display_name, "Liora Kane")
        self.assertIn("privacy_boundary_actions", package.capabilities)
        self.assertIn("safe_escalation_actions", package.capabilities)
        self.assertIsNotNone(package.runtime_profile)
        self.assertIsNotNone(package.extraction_audit)
        self.assertIsNotNone(package.pixel_graph_library)

    def test_original_and_canonical_references_are_preserved(self):
        directory = ROOT / "assets/reference/personas/liora-kane"
        self.assertEqual(
            hashlib.sha256((directory / "source-reference.png").read_bytes()).hexdigest(),
            "a1ad002278e7477fd05c091c79d929b2b674071484fd8e8e00a638d2fdaeca2e",
        )
        self.assertEqual(
            hashlib.sha256((directory / "canonical-voxel.png").read_bytes()).hexdigest(),
            "c4710c8764b9246fcddff297943da6d8ca83478794331e846758eb44451d1ad9",
        )

    def test_generator_is_deterministic(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/generate_voxel_persona_character.py"),
                str(PROFILE),
                "--check",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_manifest_revalidates_all_production_inputs(self):
        manifest = json.loads(
            (DEFINITIONS / "liora_kane_character_manifest.json").read_text(encoding="utf-8")
        )
        hashes = manifest["hashes"]
        self.assertEqual(
            hashes["generation_profile_sha256"], hashlib.sha256(PROFILE.read_bytes()).hexdigest()
        )
        for key, filename in (
            ("pose_library_sha256", "liora_kane_pose_cells.json"),
            ("animation_graph_sha256", "liora_kane_animation_graph.json"),
            ("runtime_profile_sha256", "liora_kane_runtime_profile.json"),
            ("animation_matrix_sha256", "liora_kane_animation_matrix.json"),
            ("extraction_audit_sha256", "liora_kane_extraction_audit.json"),
            ("pixel_graph_library_sha256", "liora_kane_pixel_graphs.json"),
        ):
            self.assertEqual(
                hashes[key], hashlib.sha256((DEFINITIONS / filename).read_bytes()).hexdigest()
            )
        self.assertEqual(hashes["extraction_item_count"], 124)
        persona = ROOT / "assets/reference/personas/liora-kane"
        self.assertEqual(
            hashes["original_reference_sha256"],
            hashlib.sha256((persona / "source-reference.png").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            hashes["canonical_reference_sha256"],
            hashlib.sha256((persona / "canonical-voxel.png").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            set(hashes["worksheet_sha256"]),
            {
                "01-identity-sheet-candidate-v1.png",
                "02-turnaround-sheet-candidate-v1.png",
                "03-neutral-base-poses-candidate-v1.png",
                "04-expression-sheet-candidate-v1.png",
                "05-speech-viseme-sheet-candidate-v1.png",
                "06-hand-prop-sheet-candidate-v1.png",
                "07-ground-motion-sheet-candidate-v1.png",
                "08-signature-actions-sheet-candidate-v1.png",
                "09-body-hand-poses-candidate-v1.png",
            },
        )
        for filename, expected_hash in hashes["worksheet_sha256"].items():
            worksheet = persona / "canonical-worksheets" / filename
            self.assertEqual(expected_hash, hashlib.sha256(worksheet.read_bytes()).hexdigest())

    def test_exact_124_transparent_graphs_are_audited_before_animation(self):
        package = load_character_package(LIORA_KANE_PACKAGE_PATH)
        pose_payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        reference_payload = json.loads(package.pixel_graph_library.read_text(encoding="utf-8"))
        audit = json.loads(package.extraction_audit.read_text(encoding="utf-8"))
        self.assertEqual(len(pose_payload["poses"]), 108)
        self.assertEqual(reference_payload["graph_count"], 16)
        self.assertEqual(audit["item_count"], 124)
        self.assertEqual(
            audit["category_counts"],
            {
                "identity_reference": 16,
                "turnaround": 8,
                "neutral": 8,
                "expression": 24,
                "viseme_blink": 16,
                "hand_prop": 16,
                "motion": 16,
                "signature": 16,
                "interaction": 4,
            },
        )
        self.assertEqual(audit["runtime_image_assets"], [])
        graphs = {graph["id"]: graph["nodes"] for graph in reference_payload["graphs"]}
        graphs.update({pose["id"]: pose["cells"] for pose in pose_payload["poses"]})
        self.assertEqual(set(graphs), {item["graph_id"] for item in audit["items"]})
        for item in audit["items"]:
            nodes = graphs[item["graph_id"]]
            compact = json.dumps(nodes, separators=(",", ":"), sort_keys=True)
            self.assertEqual(
                item["pixel_graph_sha256"], hashlib.sha256(compact.encode()).hexdigest()
            )
            self.assertEqual(item["pixel_node_count"], len(nodes))
            self.assertTrue(item["background_removed"])
            self.assertTrue(item["floor_and_contact_shadows_removed"])
            self.assertTrue(item["subject_continuity_preserved"])
            self.assertEqual(item["runtime_format"], "colored_pixel_nodes_json")
            self.assertNotIn(".png", item["runtime_asset"])
            self.assertNotIn(".svg", item["runtime_asset"])

    def test_package_rejects_a_graph_changed_after_audit(self):
        audit_path = (DEFINITIONS / "liora_kane_extraction_audit.json").resolve()
        tampered = json.loads(audit_path.read_text(encoding="utf-8"))
        tampered["items"][0]["pixel_graph_sha256"] = "0" * 64
        original_read_text = Path.read_text

        def controlled_read_text(path, *args, **kwargs):
            if path.resolve() == audit_path:
                return json.dumps(tampered)
            return original_read_text(path, *args, **kwargs)

        with patch.object(Path, "read_text", new=controlled_read_text):
            with self.assertRaisesRegex(CharacterPackageValidationError, "hash differs"):
                load_character_package(LIORA_KANE_PACKAGE_PATH)

    def test_package_independently_rejects_every_input_and_generated_asset_tamper(self):
        persona = ROOT / "assets/reference/personas/liora-kane"
        manifest = json.loads(
            (DEFINITIONS / "liora_kane_character_manifest.json").read_text(encoding="utf-8")
        )
        immutable_inputs = [
            PROFILE,
            persona / "source-reference.png",
            persona / "canonical-voxel.png",
            *(
                persona / "canonical-worksheets" / filename
                for filename in manifest["hashes"]["worksheet_sha256"]
            ),
        ]
        generated_assets = [
            DEFINITIONS / "liora_kane_pose_cells.json",
            DEFINITIONS / "liora_kane_animation_graph.json",
            DEFINITIONS / "liora_kane_runtime_profile.json",
            DEFINITIONS / "liora_kane_animation_matrix.json",
            DEFINITIONS / "liora_kane_extraction_audit.json",
            DEFINITIONS / "liora_kane_pixel_graphs.json",
        ]
        original_read_bytes = Path.read_bytes
        for target in [*immutable_inputs, *generated_assets]:
            target = target.resolve()
            with self.subTest(target=target.name):
                def controlled_read_bytes(path, *args, **kwargs):
                    data = original_read_bytes(path, *args, **kwargs)
                    return data + b"\n" if path.resolve() == target else data

                with patch.object(Path, "read_bytes", new=controlled_read_bytes):
                    with self.assertRaisesRegex(CharacterPackageValidationError, "manifest hash differs"):
                        load_character_package(LIORA_KANE_PACKAGE_PATH)

    def test_package_rejects_provenance_paths_that_escape_the_repository(self):
        manifest_path = (DEFINITIONS / "liora_kane_character_manifest.json").resolve()
        tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
        tampered["derivation"]["original_reference"] = "../../../../etc/passwd"
        original_read_text = Path.read_text

        def controlled_read_text(path, *args, **kwargs):
            if path.resolve() == manifest_path:
                return json.dumps(tampered)
            return original_read_text(path, *args, **kwargs)

        with patch.object(Path, "read_text", new=controlled_read_text):
            with self.assertRaisesRegex(CharacterPackageValidationError, "provenance path"):
                load_character_package(LIORA_KANE_PACKAGE_PATH)

    def test_all_graphs_are_detailed_bounded_and_free_of_pale_blue_background(self):
        package = load_character_package(LIORA_KANE_PACKAGE_PATH)
        poses = json.loads(package.pose_library.read_text(encoding="utf-8"))["poses"]
        references = json.loads(package.pixel_graph_library.read_text(encoding="utf-8"))["graphs"]
        graphs = [graph["nodes"] for graph in references]
        graphs.extend(pose["cells"] for pose in poses)
        for ordinal, nodes in enumerate(graphs):
            with self.subTest(ordinal=ordinal):
                xs = [node["x"] for node in nodes]
                ys = [node["y"] for node in nodes]
                self.assertGreater(len(nodes), 1000)
                self.assertGreater(len({tuple(node["rgb"]) for node in nodes}), 900)
                self.assertGreaterEqual(min(xs), 4)
                self.assertLessEqual(max(xs), 67)
                self.assertGreaterEqual(min(ys), 4)
                self.assertLessEqual(max(ys), 91)
                pale_blue_edge_samples = sum(
                    blue >= 170 and blue >= red + 14 and blue >= green + 8
                    for red, green, blue in (node["rgb"] for node in nodes)
                )
                # Lanczos normalization can create a handful of one-pixel
                # antialias samples; a retained backdrop/floor would contain
                # hundreds or thousands of connected pale-blue nodes.
                self.assertLess(pale_blue_edge_samples, 10)
                gray_hoodie_cells = sum(
                    70 <= red <= 230
                    and abs(red - green) <= 30
                    and abs(green - blue) <= 30
                    for red, green, blue in (node["rgb"] for node in nodes)
                )
                teal_plaid_cells = sum(
                    blue >= red + 15
                    and green >= red + 10
                    and blue <= 175
                    and green <= 175
                    for red, green, blue in (node["rgb"] for node in nodes)
                )
                self.assertGreater(gray_hoodie_cells, 500)
                self.assertGreater(teal_plaid_cells, 300)

    def test_liora_signature_vocabulary_and_notebook_anchors_are_exact(self):
        package = load_character_package(LIORA_KANE_PACKAGE_PATH)
        poses = {
            pose["id"]: pose
            for pose in json.loads(package.pose_library.read_text(encoding="utf-8"))["poses"]
        }
        signature = {
            "support_listening_start", "support_listening_nod",
            "family_plan_open_notebook", "family_plan_point_to_page",
            "belonging_checkin_open_hand", "belonging_checkin_pause",
            "privacy_notebook_shield", "privacy_calm_stop_palm",
            "escalation_assess", "escalation_indicate_next_step",
            "support_notebook_write", "support_present_plan",
            "supportive_hand_offer", "protective_grounded_stance",
            "quiet_reassurance", "slow_neutral_recovery",
        }
        self.assertTrue(signature.issubset(poses))
        self.assertFalse(any("inquiry" in pose_id or "orion" in pose_id for pose_id in poses))
        for pose_id in signature:
            self.assertIn("notebook", poses[pose_id]["anchors"])
            occupied = {(node["x"], node["y"]) for node in poses[pose_id]["cells"]}
            self.assertIn(tuple(poses[pose_id]["anchors"]["notebook"]), occupied)

    def test_semantic_support_privacy_and_escalation_actions_are_live(self):
        source = self.make_source()
        expected = {
            "explaining": "support_present_plan",
            "pointing": "family_plan_point_to_page",
            "thinking": "escalation_assess",
            "reaction": "belonging_checkin_pause",
            "celebrating": "supportive_hand_offer",
            "listening": "support_listening_start",
            "journal_hold": "privacy_notebook_shield",
            "journal_write": "support_notebook_write",
            "journal_page_turn": "family_plan_point_to_page",
            "containment": "privacy_calm_stop_palm",
            "magic_cast": "escalation_indicate_next_step",
            "turn_left": "turn_left",
            "turn_right": "turn_right",
            "crouch": "crouch",
            "jump": "jump_airborne",
            "fall": "fall",
            "land": "land_contact",
        }
        frames = []
        for action, pose_id in expected.items():
            result = source.apply_command_sync(
                WizardCommand("action", {"action": action, "duration_ms": 900})
            )
            self.assertTrue(result.ok, result.message)
            frames.append(source.render_current_frame().cells)
            self.assertEqual(source.current_state().pose_id, pose_id)
        self.assertEqual(len(set(frames)), len(set(expected.values())))

    def test_locomotion_expression_speech_and_direct_pose_change_frames(self):
        source = self.make_source()
        idle = source.render_current_frame().cells
        source.apply_command_sync(WizardCommand("move", {"x": 2.0, "z": 5.0, "speed": 1.2}))
        source.advance_simulation(0.35)
        walking = source.render_current_frame().cells
        self.assertNotEqual(idle, walking)
        source.apply_command_sync(WizardCommand("expression", {"expression": "compassion"}))
        compassion = source.render_current_frame().cells
        self.assertNotEqual(walking, compassion)
        source.apply_command_sync(
            WizardCommand("speak", {"text": "We can make a safe plan together.", "duration_ms": 1400})
        )
        source.advance_simulation(0.12)
        speaking = source.render_current_frame().cells
        self.assertNotEqual(compassion, speaking)
        result = source.apply_command_sync(
            WizardCommand("pose", {"pose_id": "support_present_plan", "duration_ms": 900})
        )
        self.assertTrue(result.ok)
        self.assertNotEqual(speaking, source.render_current_frame().cells)

    def test_server_static_and_websocket_architecture_expose_liora(self):
        app = create_app()
        paths = {route.path for route in app.routes}
        self.assertIn("/api/avatar/{character_id}/{command_type}", paths)
        self.assertIn("/ws/avatar/{character_id}", paths)
        self.assertIn("/avatar/characters/{character_id}/{asset_name}", paths)
        entries = {entry["character_id"]: entry for entry in load_character_registry().public_entries()}
        self.assertEqual(
            entries["liora-kane-v1"]["assets"]["pixel_graph_library"],
            "/avatar/characters/liora-kane-v1/pixel-graph-library",
        )
        route = next(
            route for route in app.routes
            if route.path == "/avatar/characters/{character_id}/{asset_name}"
        )
        response = asyncio.run(route.endpoint("liora-kane-v1", "pixel-graph-library"))
        self.assertEqual(
            Path(response.path).resolve(), (DEFINITIONS / "liora_kane_pixel_graphs.json").resolve()
        )

    def test_runtime_does_not_decode_worksheet_images(self):
        with patch("PIL.Image.open", side_effect=AssertionError("runtime PNG access")):
            source = self.make_source()
            frame = source.render_current_frame()
        self.assertEqual(len(frame.cells), frame.cols * frame.rows * 4)

    def test_contact_sheet_is_exactly_the_reviewed_direct_nodes(self):
        path = ROOT / "evidence/liora-kane/124-graph-contact-sheet.png"
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "41628557404a82d52df3e113b8a87523ed11c8a8d6755b1af64e692cef03ddfe",
        )


if __name__ == "__main__":
    unittest.main()
