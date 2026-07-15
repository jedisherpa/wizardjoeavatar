import hashlib
import asyncio
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from wizard_avatar.character_package import (
    KAI_RENNER_PACKAGE_PATH,
    CharacterPackageValidationError,
    load_character_package,
)
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.server import create_app


ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "assets" / "reference" / "personas" / "kai-renner" / "generation-profile.json"


class KaiRennerCharacterTests(unittest.TestCase):
    def make_source(self):
        return ProceduralWizardFrameSource(
            cols=160,
            rows=100,
            character_package_path=KAI_RENNER_PACKAGE_PATH,
        )

    def test_registry_and_package_expose_kai(self):
        registry = load_character_registry()
        self.assertIn("kai-renner-v1", registry.packages)
        package = registry.get("kai-renner-v1")
        self.assertEqual(package.display_name, "Kai Renner")
        self.assertIsNotNone(package.runtime_profile)
        self.assertIsNotNone(package.extraction_audit)
        self.assertIsNotNone(package.pixel_graph_library)
        self.assertIn("prototype_interaction", package.capabilities)
        self.assertIn("build_test_signature_actions", package.capabilities)
        self.assertIn("privacy_safety_slowdown", package.capabilities)

    def test_original_and_canonical_references_are_preserved(self):
        directory = ROOT / "assets" / "reference" / "personas" / "kai-renner"
        self.assertEqual(
            hashlib.sha256((directory / "source-reference.png").read_bytes()).hexdigest(),
            "882e005783758986883064105c500bb1dfde5447c3b3e3fac9aa1f6f6f6b5f4b",
        )
        self.assertEqual(
            hashlib.sha256((directory / "canonical-voxel.png").read_bytes()).hexdigest(),
            "fc73a37b15383b6af8c1ffb3c00ad7d584a0faf2a54bd28783f0b026a640d439",
        )

    def test_generator_is_deterministic(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "generate_voxel_persona_character.py"),
                str(PROFILE),
                "--check",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_manifest_hashes_only_the_approved_production_inputs(self):
        manifest_path = ROOT / "wizard_avatar" / "definitions" / "kai_renner_character_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        hashes = manifest["hashes"]
        self.assertEqual(
            hashes["generation_profile_sha256"],
            hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
        )
        for key, filename in (
            ("pose_library_sha256", "kai_renner_pose_cells.json"),
            ("animation_graph_sha256", "kai_renner_animation_graph.json"),
            ("animation_matrix_sha256", "kai_renner_animation_matrix.json"),
            ("extraction_audit_sha256", "kai_renner_extraction_audit.json"),
            ("pixel_graph_library_sha256", "kai_renner_pixel_graphs.json"),
        ):
            path = ROOT / "wizard_avatar" / "definitions" / filename
            self.assertEqual(hashes[key], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(hashes["extraction_item_count"], 124)
        self.assertEqual(
            set(hashes["worksheet_sha256"]),
            {
                "02-turnaround-sheet-candidate-v1.png",
                "01-identity-sheet-candidate-v2.png",
                "04-expression-sheet-candidate-v1.png",
                "03-neutral-base-poses-candidate-v1.png",
                "05-speech-viseme-sheet-candidate-v1.png",
                "06-hand-prop-sheet-candidate-v1.png",
                "07-ground-motion-sheet-candidate-v1.png",
                "08-signature-actions-sheet-candidate-v1.png",
                "09-core-hand-actions-candidate-v1.png",
            },
        )

    def test_pose_library_has_complete_kai_vocabulary(self):
        package = load_character_package(KAI_RENNER_PACKAGE_PATH)
        payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        poses = {pose["id"]: pose for pose in payload["poses"]}
        self.assertEqual(len(poses), 108)
        required = {
            "neutral_front", "neutral_back", "neutral_left_profile", "neutral_right_profile",
            "walk_contact_left", "walk_contact_right", "run_reach", "jump_airborne", "land_recovery",
            "expression_curiosity", "expression_compassion", "expression_skepticism",
            "viseme_wide_vowel", "viseme_tongue_consonant", "viseme_breath_pause",
            "blink_open", "blink_half_closed", "blink_closed",
            "pilot_smallest_pitch", "build_gesture", "test_gesture", "build_test_handoff",
            "privacy_check", "safety_slowdown", "metric_presentation", "evidence_comparison",
            "prototype_present", "prototype_inspect", "prototype_celebration",
            "decisive_thumbs_up", "self_correction", "kill_the_hype",
            "settle_and_listen", "energetic_recovery",
            "interaction_open_hand", "interaction_closed_hand", "interaction_fist",
            "interaction_reach",
            "neutral_base_front", "neutral_base_three_quarter", "neutral_base_profile",
            "neutral_base_back", "expression_privacy_safety_attentive",
            "expression_settled_recovery", "hand_open_relaxed", "hand_fist",
            "hand_pointing", "hand_thumbs_up", "hand_reaching",
            "prop_two_hand_build_grip", "prop_prototype_presentation_grip",
            "prop_privacy_check_shield_grip", "prop_metric_card_presentation_grip",
        }
        self.assertTrue(required.issubset(poses))

    def test_all_124_silhouettes_have_a_repeatable_pixel_graph_audit(self):
        package = load_character_package(KAI_RENNER_PACKAGE_PATH)
        pose_payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        pixel_graph_payload = json.loads(
            package.pixel_graph_library.read_text(encoding="utf-8")
        )
        audit = json.loads(package.extraction_audit.read_text(encoding="utf-8"))
        self.assertEqual(pixel_graph_payload["graph_count"], 16)
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
        poses = {pose["id"]: pose for pose in pose_payload["poses"]}
        graphs = {
            graph["id"]: graph for graph in pixel_graph_payload["graphs"]
        }
        graphs.update(
            {
                pose_id: {"id": pose_id, "nodes": pose["cells"]}
                for pose_id, pose in poses.items()
            }
        )
        self.assertEqual({item["graph_id"] for item in audit["items"]}, set(graphs))
        for item in audit["items"]:
            with self.subTest(graph_id=item["graph_id"]):
                graph = graphs[item["graph_id"]]
                graph_text = json.dumps(
                    graph["nodes"], separators=(",", ":"), sort_keys=True
                )
                self.assertEqual(
                    item["pixel_graph_sha256"],
                    hashlib.sha256(graph_text.encode("utf-8")).hexdigest(),
                )
                self.assertEqual(item["pixel_node_count"], len(graph["nodes"]))
                self.assertTrue(item["background_removed"])
                self.assertEqual(item["runtime_format"], "colored_pixel_nodes_json")
                self.assertNotIn(".png", item["runtime_asset"])
                self.assertNotIn(".svg", item["runtime_asset"])

    def test_package_rejects_a_pixel_graph_changed_after_audit(self):
        audit_path = (
            ROOT / "wizard_avatar" / "definitions" / "kai_renner_extraction_audit.json"
        ).resolve()
        tampered = json.loads(audit_path.read_text(encoding="utf-8"))
        tampered["items"][0]["pixel_graph_sha256"] = "0" * 64
        original_read_text = Path.read_text

        def controlled_read_text(path, *args, **kwargs):
            if path.resolve() == audit_path:
                return json.dumps(tampered)
            return original_read_text(path, *args, **kwargs)

        with patch.object(Path, "read_text", new=controlled_read_text):
            with self.assertRaisesRegex(
                CharacterPackageValidationError, "hash differs"
            ):
                load_character_package(KAI_RENNER_PACKAGE_PATH)

    def test_package_rejects_runtime_nodes_changed_after_audit(self):
        pose_path = (
            ROOT / "wizard_avatar" / "definitions" / "kai_renner_pose_cells.json"
        ).resolve()
        tampered = json.loads(pose_path.read_text(encoding="utf-8"))
        tampered["poses"][0]["cells"][0]["rgb"][0] ^= 1
        original_read_text = Path.read_text

        def controlled_read_text(path, *args, **kwargs):
            if path.resolve() == pose_path:
                return json.dumps(tampered)
            return original_read_text(path, *args, **kwargs)

        with patch.object(Path, "read_text", new=controlled_read_text):
            with self.assertRaisesRegex(
                CharacterPackageValidationError, "hash differs"
            ):
                load_character_package(KAI_RENNER_PACKAGE_PATH)

    def test_accepted_worksheets_and_pose_local_anchors_are_production_inputs(self):
        package = load_character_package(KAI_RENNER_PACKAGE_PATH)
        payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        poses = {pose["id"]: pose for pose in payload["poses"]}
        for pose_id in ("idle_relaxed", "expression_curiosity", "viseme_open_vowel", "walk_contact_left"):
            self.assertIn("candidate-v1.png", poses[pose_id]["source"])
        for pose_id in ("blink_open", "blink_half_closed", "blink_closed"):
            self.assertIn("05-speech-viseme-sheet-candidate-v1.png", poses[pose_id]["source"])
        self.assertTrue(
            all("01-identity-sheet-candidate-v2.png" in graph["source"] for graph in
                json.loads(package.pixel_graph_library.read_text(encoding="utf-8"))["graphs"])
        )
        anchor_sets = {
            tuple(sorted((name, tuple(point)) for name, point in pose["anchors"].items()))
            for pose in poses.values()
        }
        self.assertGreater(len(anchor_sets), 20)
        for pose in poses.values():
            self.assertTrue(
                {"root", "mouth", "left_eye", "right_eye", "left_hand", "right_hand"}
                .issubset(pose["anchors"])
            )
            occupied = {(cell["x"], cell["y"]) for cell in pose["cells"]}
            for anchor_name, point in pose["anchors"].items():
                if anchor_name != "root":
                    self.assertIn(tuple(point), occupied, (pose["id"], anchor_name, point))

        prototype_pose_ids = {
            pose_id for pose_id, pose in poses.items() if "prototype" in pose["anchors"]
        }
        self.assertEqual(
            prototype_pose_ids,
            {
                "prop_two_hand_build_grip", "prop_prototype_presentation_grip",
                "prop_prototype_front_side", "prop_prototype_top_bottom",
                "pilot_smallest_pitch", "build_test_handoff", "metric_presentation",
                "evidence_comparison", "prototype_present", "prototype_inspect",
                "prototype_celebration",
            },
        )

    def test_every_pose_respects_safe_bounds_and_has_visual_detail(self):
        package = load_character_package(KAI_RENNER_PACKAGE_PATH)
        payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        for pose in payload["poses"]:
            with self.subTest(pose_id=pose["id"]):
                xs = [cell["x"] for cell in pose["cells"]]
                ys = [cell["y"] for cell in pose["cells"]]
                colors = {tuple(cell["rgb"]) for cell in pose["cells"]}
                self.assertGreaterEqual(min(xs), 4)
                self.assertLessEqual(max(xs), 67)
                self.assertGreaterEqual(min(ys), 4)
                self.assertLessEqual(max(ys), 91)
                self.assertGreater(len(pose["cells"]), 350)
                self.assertGreater(len(colors), 120)

    def test_live_channels_and_signature_poses_change_cells(self):
        source = self.make_source()
        idle = source.render_current_frame().cells
        source.apply_command_sync(WizardCommand("move", {"x": 2.0, "z": 5.0, "speed": 1.2}))
        source.advance_simulation(0.35)
        walking = source.render_current_frame().cells
        self.assertNotEqual(idle, walking)

        source.apply_command_sync(WizardCommand("expression", {"expression": "curiosity"}))
        curious = source.render_current_frame().cells
        self.assertNotEqual(walking, curious)

        source.apply_command_sync(WizardCommand("speak", {"text": "Build the smallest pilot, then test it.", "duration_ms": 1600}))
        source.advance_simulation(0.12)
        speaking = source.render_current_frame().cells
        self.assertNotEqual(curious, speaking)

        result = source.apply_command_sync(
            WizardCommand("pose", {"pose_id": "pilot_smallest_pitch", "duration_ms": 900})
        )
        self.assertTrue(result.ok)
        pilot = source.render_current_frame().cells
        self.assertNotEqual(speaking, pilot)
        self.assertEqual(source.current_state().pose_id, "pilot_smallest_pitch")

    def test_hand_interaction_poses_are_runtime_addressable(self):
        source = self.make_source()
        self.assertNotIn("hand_open_relaxed", source.pose_ids)
        self.assertNotIn("prop_prototype_front_side", source.pose_ids)
        for pose_id in (
            "interaction_open_hand",
            "interaction_closed_hand",
            "interaction_fist",
            "interaction_reach",
        ):
            with self.subTest(pose_id=pose_id):
                result = source.apply_command_sync(
                    WizardCommand("pose", {"pose_id": pose_id, "duration_ms": 900})
                )
                self.assertTrue(result.ok)
                source.render_current_frame()
                self.assertEqual(source.current_state().pose_id, pose_id)

    def test_semantic_ground_and_kai_signature_actions_are_runtime_addressable(self):
        source = self.make_source()
        expected = {
            "turn_left": "turn_left",
            "turn_right": "turn_right",
            "crouch": "crouch",
            "jump": "jump_airborne",
            "fall": "fall",
            "land": "land_contact",
            "listening": "settle_and_listen",
            "smallest_pilot": "pilot_smallest_pitch",
            "build": "build_gesture",
            "test": "test_gesture",
            "build_test_handoff": "build_test_handoff",
            "privacy_check": "privacy_check",
            "safety_slowdown": "safety_slowdown",
            "metrics": "metric_presentation",
            "evidence": "evidence_comparison",
            "prototype_present": "prototype_present",
            "prototype_inspect": "prototype_inspect",
            "prototype_celebrate": "prototype_celebration",
            "thumbs_up": "decisive_thumbs_up",
            "self_correction": "self_correction",
            "kill_the_hype": "kill_the_hype",
            "settle": "settle_and_listen",
            "energetic_recovery": "energetic_recovery",
        }
        for action, pose_id in expected.items():
            with self.subTest(action=action):
                result = source.apply_command_sync(
                    WizardCommand("action", {"action": action, "duration_ms": 900})
                )
                self.assertTrue(result.ok, result.message)
                source.render_current_frame()
                self.assertEqual(source.current_state().pose_id, pose_id)

    def test_blink_and_speech_preserve_the_base_body_pose(self):
        source = self.make_source()
        source.current_state().locomotion = "walking"
        source.current_state().walk_phase = 0.75
        source.current_state().blink_phase = 0.0
        open_frame = source.render_current_frame().cells
        source.current_state().blink_phase = 0.98
        blink_frame = source.render_current_frame().cells
        self.assertEqual(source.current_state().pose_id, "walk_passing_right")
        changed_cells = sum(
            open_frame[index:index + 4] != blink_frame[index:index + 4]
            for index in range(0, len(open_frame), 4)
        )
        self.assertGreater(changed_cells, 0)
        self.assertLess(changed_cells, 120)
        source.current_state().speech_id = "kai-speech-test"
        source.current_state().speech_until = 2.0
        speech_frame = source.render_current_frame().cells
        self.assertEqual(source.current_state().pose_id, "walk_passing_right")
        self.assertNotEqual(blink_frame, speech_frame)

    def test_seeded_simulation_reaches_the_authored_blink_graph(self):
        source = self.make_source()
        open_frame = source.render_current_frame().cells
        source.advance_simulation(4.05)
        blink_frame = source.render_current_frame().cells
        self.assertEqual(source.current_state().pose_id, "neutral_front")
        self.assertNotEqual(open_frame, blink_frame)

    def test_server_exposes_kai_through_character_scoped_architecture(self):
        app = create_app()
        paths = {route.path for route in app.routes}
        self.assertIn("/api/avatar/characters", paths)
        self.assertIn("/api/avatar/{character_id}/{command_type}", paths)
        self.assertIn("/ws/avatar/{character_id}", paths)
        self.assertIn("/avatar/characters/{character_id}/{asset_name}", paths)
        entries = {entry["character_id"]: entry for entry in load_character_registry().public_entries()}
        self.assertEqual(
            entries["kai-renner-v1"]["assets"]["extraction_audit"],
            "/avatar/characters/kai-renner-v1/extraction-audit",
        )
        route = next(
            route for route in app.routes
            if route.path == "/avatar/characters/{character_id}/{asset_name}"
        )
        response = asyncio.run(route.endpoint("kai-renner-v1", "pixel-graph-library"))
        self.assertEqual(
            Path(response.path).resolve(),
            (ROOT / "wizard_avatar" / "definitions" / "kai_renner_pixel_graphs.json").resolve(),
        )

    def test_runtime_render_has_no_flattened_png_dependency(self):
        with patch("PIL.Image.open", side_effect=AssertionError("runtime PNG access")):
            source = self.make_source()
            frame = source.render_current_frame()
        self.assertEqual(len(frame.cells), frame.cols * frame.rows * 4)


if __name__ == "__main__":
    unittest.main()
