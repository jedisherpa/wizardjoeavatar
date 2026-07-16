import asyncio
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from wizard_avatar.character_package import (
    ROHAN_SLATE_PACKAGE_PATH,
    CharacterPackageValidationError,
    load_character_package,
)
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.server import create_app


ROOT = Path(__file__).resolve().parents[2]
PERSONA = ROOT / "assets" / "reference" / "personas" / "rohan-slate"
PROFILE = PERSONA / "generation-profile.json"
DEFINITIONS = ROOT / "wizard_avatar" / "definitions"


class RohanSlateCharacterTests(unittest.TestCase):
    def make_source(self):
        return ProceduralWizardFrameSource(
            cols=160,
            rows=100,
            character_package_path=ROHAN_SLATE_PACKAGE_PATH,
        )

    def test_registry_and_package_expose_rohan(self):
        registry = load_character_registry()
        self.assertIn("rohan-slate-v1", registry.packages)
        package = registry.get("rohan-slate-v1")
        self.assertEqual(package.display_name, "Rohan Slate")
        self.assertIsNotNone(package.runtime_profile)
        self.assertIsNotNone(package.extraction_audit)
        self.assertIsNotNone(package.pixel_graph_library)
        self.assertTrue(
            {
                "diagnostic_meter_interaction",
                "facilities_diagnostics",
                "safety_stop",
                "meter_reset_and_verification",
                "maintenance_walkthrough",
                "qualified_help_signal",
                "wrench_presentation",
            }.issubset(package.capabilities)
        )

    def test_original_and_canonical_references_are_preserved(self):
        self.assertEqual(
            hashlib.sha256((PERSONA / "source-reference.png").read_bytes()).hexdigest(),
            "b3711407b803d432c97233ec9680d5e394f8f109839265a3e03259aa890741e6",
        )
        self.assertEqual(
            hashlib.sha256((PERSONA / "canonical-voxel.png").read_bytes()).hexdigest(),
            "9669b00c83e1f7bc57b25b4611a440a4b3a1f6de12a1253c37de8158709b0114",
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

    def test_manifest_hashes_only_accepted_worksheet_revisions(self):
        manifest = json.loads(
            (DEFINITIONS / "rohan_slate_character_manifest.json").read_text(encoding="utf-8")
        )
        hashes = manifest["hashes"]
        expected_sheets = {
            "01-identity-sheet-approved-v1.png",
            "02-turnaround-sheet-approved-v1.png",
            "03-neutral-base-poses-approved-v1.png",
            "04-expression-sheet-approved-v1.png",
            "05-speech-viseme-sheet-approved-v3.png",
            "06-hand-prop-sheet-approved-v1.png",
            "07-ground-motion-sheet-approved-v1.png",
            "08-signature-actions-sheet-approved-v1.png",
            "09-interaction-poses-approved-v1.png",
        }
        self.assertEqual(set(hashes["worksheet_sha256"]), expected_sheets)
        for name in expected_sheets:
            self.assertEqual(
                hashes["worksheet_sha256"][name],
                hashlib.sha256((PERSONA / "canonical-worksheets" / name).read_bytes()).hexdigest(),
            )
        self.assertEqual(hashes["extraction_item_count"], 124)
        for key, filename in (
            ("character_package_sha256", "rohan_slate_character_package.json"),
            ("pose_library_sha256", "rohan_slate_pose_cells.json"),
            ("animation_graph_sha256", "rohan_slate_animation_graph.json"),
            ("runtime_profile_sha256", "rohan_slate_runtime_profile.json"),
            ("animation_matrix_sha256", "rohan_slate_animation_matrix.json"),
            ("extraction_audit_sha256", "rohan_slate_extraction_audit.json"),
            ("pixel_graph_library_sha256", "rohan_slate_pixel_graphs.json"),
        ):
            self.assertEqual(
                hashes[key], hashlib.sha256((DEFINITIONS / filename).read_bytes()).hexdigest()
            )

    def test_all_124_graphs_are_audited_before_animation_mapping(self):
        package = load_character_package(ROHAN_SLATE_PACKAGE_PATH)
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
        graphs = {graph["id"]: graph["nodes"] for graph in reference_payload["graphs"]}
        graphs.update({pose["id"]: pose["cells"] for pose in pose_payload["poses"]})
        self.assertEqual({item["graph_id"] for item in audit["items"]}, set(graphs))
        for item in audit["items"]:
            with self.subTest(graph_id=item["graph_id"]):
                nodes = graphs[item["graph_id"]]
                compact = json.dumps(nodes, separators=(",", ":"), sort_keys=True)
                self.assertEqual(
                    item["pixel_graph_sha256"],
                    hashlib.sha256(compact.encode("utf-8")).hexdigest(),
                )
                self.assertEqual(item["pixel_node_count"], len(nodes))
                self.assertTrue(item["background_removed"])
                self.assertEqual(item["runtime_format"], "colored_pixel_nodes_json")
                self.assertNotIn(".png", item["runtime_asset"].lower())
                self.assertNotIn(".svg", item["runtime_asset"].lower())

    def test_every_graph_is_nonempty_detailed_unique_and_inside_bounds(self):
        package = load_character_package(ROHAN_SLATE_PACKAGE_PATH)
        poses = json.loads(package.pose_library.read_text(encoding="utf-8"))["poses"]
        references = json.loads(package.pixel_graph_library.read_text(encoding="utf-8"))["graphs"]
        graph_nodes = [(graph["id"], graph["nodes"]) for graph in references]
        graph_nodes.extend((pose["id"], pose["cells"]) for pose in poses)
        digests = set()
        for graph_id, nodes in graph_nodes:
            with self.subTest(graph_id=graph_id):
                xs = [node["x"] for node in nodes]
                ys = [node["y"] for node in nodes]
                colors = {tuple(node["rgb"]) for node in nodes}
                self.assertTrue(all(len(node["rgb"]) == 3 for node in nodes))
                self.assertTrue(all(
                    isinstance(channel, int) and 0 <= channel <= 255
                    for node in nodes for channel in node["rgb"]
                ))
                self.assertGreater(len(nodes), 1300)
                self.assertGreater(len(colors), 1200)
                self.assertGreater(max(xs) - min(xs), 20)
                self.assertGreater(max(ys) - min(ys), 50)
                self.assertGreaterEqual(min(xs), 4)
                self.assertLessEqual(max(xs), 67)
                self.assertGreaterEqual(min(ys), 4)
                self.assertLessEqual(max(ys), 91)
                digest = hashlib.sha256(
                    json.dumps(nodes, separators=(",", ":"), sort_keys=True).encode("utf-8")
                ).hexdigest()
                self.assertNotIn(digest, digests)
                digests.add(digest)

    def test_complete_rohan_vocabulary_and_pose_local_anchors(self):
        package = load_character_package(ROHAN_SLATE_PACKAGE_PATH)
        poses = {
            pose["id"]: pose
            for pose in json.loads(package.pose_library.read_text(encoding="utf-8"))["poses"]
        }
        required = {
            "neutral_front", "neutral_back", "turn_left", "turn_right", "crouch",
            "jump_anticipation", "jump_airborne", "fall", "land_contact", "land_recovery",
            "expression_compassion", "expression_skepticism", "expression_determination",
            "viseme_wide_vowel", "viseme_tongue_consonant", "viseme_breath_pause",
            "blink_open", "blink_half_closed", "blink_closed", "observe_symptom",
            "inspect_cause_low", "meter_scan_anticipation", "meter_scan_reading",
            "indicate_result", "safety_stop_anticipation", "safety_stop_hold",
            "safety_stop_recovery", "reset_anticipation", "precise_meter_reset",
            "watch_and_wait", "reset_success_nod", "walkthrough_direction",
            "wrench_presentation", "qualified_help_signal",
            "settled_ready_tools_returned", "interaction_open_hand", "interaction_closed_hand",
            "interaction_fist", "interaction_reach", "prop_meter_grip",
            "prop_meter_offered", "prop_meter_transfer", "prop_meter_release",
        }
        self.assertTrue(required.issubset(poses))
        anchor_sets = {
            tuple(sorted((name, tuple(point)) for name, point in pose["anchors"].items()))
            for pose in poses.values()
        }
        self.assertGreater(len(anchor_sets), 20)
        for pose in poses.values():
            occupied = {(cell["x"], cell["y"]) for cell in pose["cells"]}
            for name, point in pose["anchors"].items():
                if name != "root":
                    self.assertIn(tuple(point), occupied, (pose["id"], name, point))

    def test_tool_anchors_exist_only_on_profile_declared_graphs(self):
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        poses = json.loads(
            (DEFINITIONS / "rohan_slate_pose_cells.json").read_text(encoding="utf-8")
        )["poses"]
        for anchor in ("meter", "wrench"):
            expected = set(profile["anchor_presence"][anchor])
            actual = {pose["id"] for pose in poses if anchor in pose["anchors"]}
            self.assertEqual(actual, expected)

    def test_studio_cyan_and_ground_contact_shadows_are_absent(self):
        package = load_character_package(ROHAN_SLATE_PACKAGE_PATH)
        poses = json.loads(package.pose_library.read_text(encoding="utf-8"))["poses"]
        references = json.loads(package.pixel_graph_library.read_text(encoding="utf-8"))["graphs"]
        graph_nodes = [(graph["id"], graph["nodes"]) for graph in references]
        graph_nodes.extend((pose["id"], pose["cells"]) for pose in poses)
        for graph_id, nodes in graph_nodes:
            with self.subTest(graph_id=graph_id):
                studio_cyan = [
                    node for node in nodes
                    if node["rgb"][0] >= 170
                    and node["rgb"][1] >= 210
                    and node["rgb"][2] >= 225
                ]
                self.assertEqual(studio_cyan, [])
                bottom_y = max(node["y"] for node in nodes)
                bottom_xs = [node["x"] for node in nodes if node["y"] == bottom_y]
                self.assertLess(len(bottom_xs), 30, (graph_id, bottom_y, bottom_xs))

    def test_runtime_assets_are_json_nodes_and_contact_sheet_hashes_are_exact(self):
        package = load_character_package(ROHAN_SLATE_PACKAGE_PATH)
        for path in (
            package.pose_library,
            package.pixel_graph_library,
            package.extraction_audit,
            package.animation_graph,
            package.animation_matrix,
        ):
            self.assertIsNotNone(path)
            self.assertEqual(path.suffix, ".json")
        audit = json.loads(package.extraction_audit.read_text(encoding="utf-8"))
        for item in audit["items"]:
            self.assertNotIn(".png", item["runtime_asset"].lower())
            self.assertNotIn(".svg", item["runtime_asset"].lower())
        evidence_dir = ROOT / "evidence" / "rohan-slate"
        hashes = json.loads(
            (evidence_dir / "CONTACT_SHEET_HASHES.json").read_text(encoding="utf-8")
        )
        self.assertEqual(hashes["graph_count"], 124)
        self.assertEqual(len(hashes["graph_order"]), 124)
        for key in ("isolated_contact_sheet", "projected_contact_sheet"):
            path = evidence_dir / hashes[key]["file"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                hashes[key]["sha256"],
            )

    def test_package_rejects_post_audit_graph_and_manifest_tampering(self):
        audit_path = (DEFINITIONS / "rohan_slate_extraction_audit.json").resolve()
        tampered = json.loads(audit_path.read_text(encoding="utf-8"))
        tampered["items"][0]["pixel_graph_sha256"] = "0" * 64
        original_read_text = Path.read_text

        def controlled_read_text(path, *args, **kwargs):
            if path.resolve() == audit_path:
                return json.dumps(tampered)
            return original_read_text(path, *args, **kwargs)

        with patch.object(Path, "read_text", new=controlled_read_text):
            with self.assertRaisesRegex(CharacterPackageValidationError, "hash differs"):
                load_character_package(ROHAN_SLATE_PACKAGE_PATH)

        manifest = json.loads(
            (DEFINITIONS / "rohan_slate_character_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        targets = [
            PROFILE,
            PERSONA / "source-reference.png",
            PERSONA / "canonical-voxel.png",
            ROHAN_SLATE_PACKAGE_PATH,
            DEFINITIONS / "rohan_slate_runtime_profile.json",
            DEFINITIONS / "rohan_slate_pose_cells.json",
            DEFINITIONS / "rohan_slate_animation_graph.json",
            DEFINITIONS / "rohan_slate_animation_matrix.json",
            DEFINITIONS / "rohan_slate_extraction_audit.json",
            DEFINITIONS / "rohan_slate_pixel_graphs.json",
        ]
        targets.extend(
            PERSONA / "canonical-worksheets" / filename
            for filename in manifest["hashes"]["worksheet_sha256"]
        )
        original_read_bytes = Path.read_bytes
        for target in targets:
            resolved = target.resolve()

            def controlled_read_bytes(path, *args, **kwargs):
                data = original_read_bytes(path, *args, **kwargs)
                return data + b"tampered" if path.resolve() == resolved else data

            with self.subTest(target=target.name):
                with patch.object(Path, "read_bytes", new=controlled_read_bytes):
                    with self.assertRaisesRegex(
                        CharacterPackageValidationError,
                        "manifest hash differs|worksheet",
                    ):
                        load_character_package(ROHAN_SLATE_PACKAGE_PATH)

    def test_live_cells_change_for_motion_expression_speech_and_diagnostics(self):
        source = self.make_source()
        idle = source.render_current_frame().cells
        source.apply_command_sync(WizardCommand("move", {"x": 2.0, "z": 5.0, "speed": 1.2}))
        source.advance_simulation(0.35)
        walking = source.render_current_frame().cells
        self.assertNotEqual(idle, walking)
        source.apply_command_sync(WizardCommand("expression", {"expression": "curiosity"}))
        curious = source.render_current_frame().cells
        self.assertNotEqual(walking, curious)
        source.apply_command_sync(
            WizardCommand("speak", {"text": "The meter confirms the fault.", "duration_ms": 1600})
        )
        source.advance_simulation(0.12)
        speaking = source.render_current_frame().cells
        self.assertNotEqual(curious, speaking)
        result = source.apply_command_sync(
            WizardCommand("pose", {"pose_id": "meter_scan_reading", "duration_ms": 900})
        )
        self.assertTrue(result.ok)
        diagnostic = source.render_current_frame().cells
        self.assertNotEqual(speaking, diagnostic)
        self.assertEqual(source.current_state().pose_id, "meter_scan_reading")

    def test_semantic_actions_and_signature_graphs_are_runtime_reachable(self):
        source = self.make_source()
        expected = {
            "turn_left": "turn_left", "turn_right": "turn_right", "crouch": "crouch",
            "jump": "jump_airborne", "fall": "fall", "land": "land_contact",
            "listening": "watch_and_wait", "explaining": "walkthrough_direction",
            "pointing": "indicate_result", "thinking": "observe_symptom",
            "magic_cast": "wrench_presentation", "containment": "safety_stop_hold",
            "journal_write": "precise_meter_reset", "journal_page_turn": "meter_scan_anticipation",
            "observe_symptom": "observe_symptom", "inspect_cause": "inspect_cause_low",
            "meter_scan": "meter_scan_reading", "safety_stop": "safety_stop_hold",
            "reset": "precise_meter_reset", "watch_wait": "watch_and_wait",
            "walkthrough": "walkthrough_direction", "wrench_present": "wrench_presentation",
            "qualified_help": "qualified_help_signal",
        }
        for action, pose_id in expected.items():
            with self.subTest(action=action):
                result = source.apply_command_sync(
                    WizardCommand("action", {"action": action, "duration_ms": 900})
                )
                self.assertTrue(result.ok, result.message)
                source.render_current_frame()
                self.assertEqual(source.current_state().pose_id, pose_id)
        for pose_id in (
            "safety_stop_recovery", "reset_success_nod", "settled_ready_tools_returned",
            "interaction_open_hand", "interaction_closed_hand",
            "interaction_fist", "interaction_reach",
        ):
            result = source.apply_command_sync(
                WizardCommand("pose", {"pose_id": pose_id, "duration_ms": 900})
            )
            self.assertTrue(result.ok)
            source.render_current_frame()
            self.assertEqual(source.current_state().pose_id, pose_id)

    def test_blink_and_speech_preserve_active_body_graph(self):
        source = self.make_source()
        state = source.current_state()
        state.locomotion = "walking"
        state.walk_phase = 0.75
        state.blink_phase = 0.0
        open_frame = source.render_current_frame().cells
        state.blink_phase = 0.98
        blink_frame = source.render_current_frame().cells
        self.assertEqual(state.pose_id, "walk_passing_right")
        changed = sum(
            open_frame[index:index + 4] != blink_frame[index:index + 4]
            for index in range(0, len(open_frame), 4)
        )
        self.assertGreater(changed, 0)
        self.assertLess(changed, 120)
        state.speech_id = "rohan-speech-test"
        state.speech_until = 2.0
        speech_frame = source.render_current_frame().cells
        self.assertEqual(state.pose_id, "walk_passing_right")
        self.assertNotEqual(blink_frame, speech_frame)

    def test_server_routes_and_static_graph_asset_are_character_scoped(self):
        app = create_app()
        paths = {route.path for route in app.routes}
        self.assertIn("/api/avatar/characters", paths)
        self.assertIn("/api/avatar/{character_id}/{command_type}", paths)
        self.assertIn("/ws/avatar/{character_id}", paths)
        self.assertIn("/avatar/characters/{character_id}/{asset_name}", paths)
        entries = {
            entry["character_id"]: entry
            for entry in load_character_registry().public_entries()
        }
        self.assertEqual(
            entries["rohan-slate-v1"]["assets"]["pixel_graph_library"],
            "/avatar/characters/rohan-slate-v1/pixel-graph-library",
        )
        route = next(
            route for route in app.routes
            if route.path == "/avatar/characters/{character_id}/{asset_name}"
        )
        response = asyncio.run(route.endpoint("rohan-slate-v1", "pixel-graph-library"))
        self.assertEqual(
            Path(response.path).resolve(),
            (DEFINITIONS / "rohan_slate_pixel_graphs.json").resolve(),
        )

    def test_runtime_render_never_decodes_png_or_svg(self):
        with patch("PIL.Image.open", side_effect=AssertionError("runtime image access")):
            source = self.make_source()
            frame = source.render_current_frame()
        self.assertEqual(len(frame.cells), frame.cols * frame.rows * 4)


if __name__ == "__main__":
    unittest.main()
