import asyncio
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from wizard_avatar.character_package import (
    SELENE_HART_PACKAGE_PATH,
    CharacterPackageValidationError,
    load_character_package,
)
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.server import create_app


ROOT = Path(__file__).resolve().parents[2]
PERSONA = ROOT / "assets" / "reference" / "personas" / "selene-hart"
PROFILE = PERSONA / "generation-profile.json"
DEFINITIONS = ROOT / "wizard_avatar" / "definitions"


class SeleneHartCharacterTests(unittest.TestCase):
    def make_source(self):
        return ProceduralWizardFrameSource(
            cols=160, rows=100, character_package_path=SELENE_HART_PACKAGE_PATH
        )

    def graphs(self):
        package = load_character_package(SELENE_HART_PACKAGE_PATH)
        references = json.loads(package.pixel_graph_library.read_text(encoding="utf-8"))["graphs"]
        poses = json.loads(package.pose_library.read_text(encoding="utf-8"))["poses"]
        return [(graph["id"], graph["nodes"]) for graph in references] + [
            (pose["id"], pose["cells"]) for pose in poses
        ]

    def test_registry_package_and_exact_selene_capabilities(self):
        registry = load_character_registry()
        package = registry.get("selene-hart-v1")
        self.assertEqual(package.display_name, "Selene Hart")
        self.assertTrue({
            "define_standard", "inspect_evidence", "compare_rubric", "flag_gap",
            "compliance_review", "issue_measured_result", "document_exception",
            "rubric_and_clipboard_interaction",
        }.issubset(package.capabilities))
        self.assertIsNotNone(package.runtime_profile)
        self.assertIsNotNone(package.manifest)
        self.assertIsNotNone(package.extraction_audit)
        self.assertIsNotNone(package.pixel_graph_library)

    def test_immutable_reference_hashes_and_deterministic_generation(self):
        self.assertEqual(
            hashlib.sha256((PERSONA / "source-reference.png").read_bytes()).hexdigest(),
            "2019ae7b2349abb8a6c2f5e3cf17535b94442f294810c3852e062d4e87663969",
        )
        self.assertEqual(
            hashlib.sha256((PERSONA / "canonical-voxel.png").read_bytes()).hexdigest(),
            "5ade95e07beab8b8eb25f88195d804542cfbbd6c6ada7d6403d6099d3a6be1d1",
        )
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "generate_voxel_persona_character.py"), str(PROFILE), "--check"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_manifest_lineage_hashes_count_and_accepted_sheets(self):
        manifest = json.loads((DEFINITIONS / "selene_hart_character_manifest.json").read_text())
        hashes = manifest["hashes"]
        expected = {
            "01-identity-sheet-candidate-v1.png", "02-turnaround-sheet-candidate-v1.png",
            "03-neutral-base-poses-candidate-v1.png", "04-expression-sheet-candidate-v1.png",
            "05-speech-viseme-sheet-candidate-v1.png", "06-hand-prop-sheet-candidate-v1.png",
            "07-ground-motion-sheet-candidate-v2.png", "08-signature-actions-sheet-candidate-v1.png",
            "09-interaction-poses-candidate-v1.png",
        }
        self.assertEqual(set(hashes["worksheet_sha256"]), expected)
        self.assertEqual(hashes["extraction_item_count"], 124)
        self.assertEqual(
            hashes["generation_profile_sha256"], hashlib.sha256(PROFILE.read_bytes()).hexdigest()
        )
        for name in expected:
            self.assertEqual(
                hashes["worksheet_sha256"][name],
                hashlib.sha256((PERSONA / "canonical-worksheets" / name).read_bytes()).hexdigest(),
            )
        for key, filename in (
            ("pose_library_sha256", "selene_hart_pose_cells.json"),
            ("animation_graph_sha256", "selene_hart_animation_graph.json"),
            ("animation_matrix_sha256", "selene_hart_animation_matrix.json"),
            ("extraction_audit_sha256", "selene_hart_extraction_audit.json"),
            ("pixel_graph_library_sha256", "selene_hart_pixel_graphs.json"),
        ):
            self.assertEqual(hashes[key], hashlib.sha256((DEFINITIONS / filename).read_bytes()).hexdigest())

    def test_all_124_transparent_colored_graphs_are_unique_bounded_and_audited(self):
        graphs = self.graphs()
        audit = json.loads((DEFINITIONS / "selene_hart_extraction_audit.json").read_text())
        self.assertEqual(len(graphs), 124)
        self.assertEqual(audit["item_count"], 124)
        self.assertEqual(audit["runtime_image_assets"], [])
        self.assertEqual(audit["category_counts"], {
            "identity_reference": 16, "turnaround": 8, "neutral": 8,
            "expression": 24, "viseme_blink": 16, "hand_prop": 16,
            "motion": 16, "signature": 16, "interaction": 4,
        })
        audit_by_id = {item["graph_id"]: item for item in audit["items"]}
        digests = set()
        for graph_id, nodes in graphs:
            with self.subTest(graph_id=graph_id):
                self.assertGreater(len(nodes), 1100)
                self.assertTrue(all(set(node) == {"x", "y", "rgb"} for node in nodes))
                self.assertTrue(all(
                    len(node["rgb"]) == 3 and all(isinstance(c, int) and 0 <= c <= 255 for c in node["rgb"])
                    for node in nodes
                ))
                xs, ys = [node["x"] for node in nodes], [node["y"] for node in nodes]
                self.assertGreaterEqual(min(xs), 4); self.assertLessEqual(max(xs), 67)
                self.assertGreaterEqual(min(ys), 4); self.assertLessEqual(max(ys), 91)
                compact = json.dumps(nodes, separators=(",", ":"), sort_keys=True)
                digest = hashlib.sha256(compact.encode()).hexdigest()
                self.assertNotIn(digest, digests); digests.add(digest)
                item = audit_by_id[graph_id]
                self.assertTrue(item["background_removed"])
                self.assertEqual(item["runtime_format"], "colored_pixel_nodes_json")
                self.assertEqual(item["pixel_graph_sha256"], digest)
                self.assertEqual(item["pixel_node_count"], len(nodes))
                self.assertEqual(item["bounds"], {
                    "left": min(xs), "top": min(ys), "right": max(xs), "bottom": max(ys)
                })

    def test_no_background_floor_contact_shadow_or_forbidden_runtime_images(self):
        package = load_character_package(SELENE_HART_PACKAGE_PATH)
        for path in (
            package.pose_library, package.pixel_graph_library, package.extraction_audit,
            package.animation_graph, package.animation_matrix,
        ):
            payload = path.read_text(encoding="utf-8").lower()
            self.assertNotIn(".png", payload)
            self.assertNotIn(".svg", payload)
        for graph_id, nodes in self.graphs():
            with self.subTest(graph_id=graph_id):
                studio_cyan = [
                    node for node in nodes
                    if node["rgb"][0] >= 100
                    and node["rgb"][1] >= node["rgb"][0] + 18
                    and node["rgb"][2] >= node["rgb"][0] + 25
                    and node["rgb"][2] >= node["rgb"][1] - 5
                ]
                self.assertEqual(studio_cyan, [])
                if not graph_id.startswith(("identity_reference_", "hand_", "prop_", "interaction_")):
                    bottom = max(node["y"] for node in nodes)
                    self.assertLess(len([node for node in nodes if node["y"] == bottom]), 45)

    def test_exact_pose_vocabulary_props_signature_arcs_and_no_persona_leftovers(self):
        poses = {pose["id"] for pose in json.loads((DEFINITIONS / "selene_hart_pose_cells.json").read_text())["poses"]}
        required = {
            "prop_rubric_folio_grip", "prop_clipboard_grip", "prop_rubric_against_torso",
            "prop_clipboard_inspection_hold", "prop_offering_rubric", "prop_receiving_rubric",
            "prop_rubric_clipboard_comparison", "prop_checklist_marking", "prop_release",
            "prepare_rubric_folio", "present_standard", "indicate_rubric_grid", "close_rubric_at_chest",
            "raise_clipboard", "inspect_checklist", "indicate_checked_square", "lower_clipboard_thoughtfully",
            "hold_rubric_and_clipboard_separately", "compare_side_by_side", "flag_gap_controlled_point",
            "document_exception", "deliberate_props_lowered", "evidence_based_approval",
            "decisive_rejection_stop", "neutral_settled_hold",
        }
        self.assertTrue(required.issubset(poses))
        profile_and_outputs = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in [PROFILE, *DEFINITIONS.glob("selene_hart*.json")]
        )
        for leftover in ("rohan", "meter", "wrench", "finn", "journal", "cigar", "smoke", "tobacco", "draven", "pencil", "serena", "orb", "halo", "wings"):
            self.assertNotIn(leftover, profile_and_outputs)

    def test_only_full_body_graphs_are_runtime_pose_capable(self):
        payload = json.loads((DEFINITIONS / "selene_hart_pose_cells.json").read_text())
        full_body = {pose["id"] for pose in payload["poses"] if pose["graph_kind"] == "full_body_graph"}
        features = {pose["id"] for pose in payload["poses"] if pose["graph_kind"] == "feature_graph"}
        self.assertEqual(len(full_body), 88)
        self.assertEqual(len(features), 20)
        source = self.make_source()
        self.assertEqual(set(source.pose_ids), full_body)
        self.assertTrue(features.isdisjoint(source.pose_ids))

    def test_rubric_and_clipboard_anchors_match_declared_semantics(self):
        profile = json.loads(PROFILE.read_text())
        poses = json.loads((DEFINITIONS / "selene_hart_pose_cells.json").read_text())["poses"]
        for anchor in ("rubric", "clipboard"):
            expected = set(profile["anchor_presence"][anchor])
            actual = {pose["id"] for pose in poses if anchor in pose["anchors"]}
            self.assertEqual(actual, expected)
            for pose in poses:
                if anchor in pose["anchors"]:
                    occupied = {(cell["x"], cell["y"]) for cell in pose["cells"]}
                    self.assertIn(tuple(pose["anchors"][anchor]), occupied)

    def test_selene_identity_palette_is_present_in_serialized_rgb_nodes(self):
        colors = [node["rgb"] for _, nodes in self.graphs() for node in nodes]
        counts = {
            "dark_hair": sum(max(c) <= 90 and c[0] >= c[2] for c in colors),
            "taupe_top": sum(c[0] >= 100 and c[0] >= c[1] >= c[2] and c[0] - c[2] <= 90 for c in colors),
            "green_skirt": sum(c[1] >= 70 and c[1] >= c[0] * 1.05 and c[1] >= c[2] * 1.15 for c in colors),
            "warm_skin": sum(c[0] >= 120 and c[0] >= c[1] + 15 and c[1] >= c[2] + 12 for c in colors),
            "folio_red": sum(c[0] >= 55 and c[0] >= c[1] * 1.35 and c[1] >= c[2] * 1.05 for c in colors),
            "clipboard_gray": sum(min(c) >= 90 and max(c) - min(c) <= 35 for c in colors),
            "teal_motif": sum(c[1] >= 85 and c[2] >= 70 and c[1] >= c[0] * 1.35 and abs(c[1] - c[2]) <= 45 for c in colors),
        }
        self.assertGreater(counts["dark_hair"], 50000)
        self.assertGreater(counts["taupe_top"], 50000)
        self.assertGreater(counts["green_skirt"], 40000)
        self.assertGreater(counts["warm_skin"], 70000)
        self.assertGreater(counts["folio_red"], 90000)
        self.assertGreater(counts["clipboard_gray"], 1000)
        self.assertGreater(counts["teal_motif"], 10000)

    def test_runtime_actions_motion_expression_speech_and_signature_are_reachable(self):
        source = self.make_source()
        idle = source.render_current_frame().cells
        source.apply_command_sync(WizardCommand("move", {"x": 2.0, "z": 5.0, "speed": 1.2}))
        source.advance_simulation(0.35)
        walking = source.render_current_frame().cells
        self.assertNotEqual(idle, walking)
        source.apply_command_sync(WizardCommand("expression", {"expression": "curiosity"}))
        expression = source.render_current_frame().cells
        self.assertNotEqual(walking, expression)
        source.apply_command_sync(WizardCommand("speak", {"text": "Evidence inspected. Standard applied.", "duration_ms": 1200}))
        source.advance_simulation(0.12)
        self.assertNotEqual(expression, source.render_current_frame().cells)
        expected = {
            "define_standard": "present_standard",
            "inspect_evidence": "inspect_checklist",
            "compare_rubric": "compare_side_by_side",
            "flag_gap": "flag_gap_controlled_point",
            "compliance_review": "hold_rubric_and_clipboard_separately",
            "issue_measured_result": "evidence_based_approval",
            "document_exception": "document_exception",
        }
        for action, pose_id in expected.items():
            result = source.apply_command_sync(WizardCommand("action", {"action": action, "duration_ms": 900}))
            self.assertTrue(result.ok, result.message)
            source.render_current_frame()
            self.assertEqual(source.current_state().pose_id, pose_id)

    def test_rest_static_ws_and_forced_pil_failure(self):
        app = create_app()
        paths = {route.path for route in app.routes}
        self.assertIn("/api/avatar/{character_id}/{command_type}", paths)
        self.assertIn("/ws/avatar/{character_id}", paths)
        self.assertIn("/avatar/characters/{character_id}/{asset_name}", paths)
        entry = {item["character_id"]: item for item in load_character_registry().public_entries()}["selene-hart-v1"]
        self.assertEqual(entry["assets"]["pixel_graph_library"], "/avatar/characters/selene-hart-v1/pixel-graph-library")
        route = next(route for route in app.routes if route.path == "/avatar/characters/{character_id}/{asset_name}")
        response = asyncio.run(route.endpoint("selene-hart-v1", "pixel-graph-library"))
        self.assertEqual(Path(response.path).resolve(), (DEFINITIONS / "selene_hart_pixel_graphs.json").resolve())
        with patch("PIL.Image.open", side_effect=AssertionError("runtime image access")):
            frame = self.make_source().render_current_frame()
        self.assertEqual(len(frame.cells), frame.cols * frame.rows * 4)

    def test_contact_sheet_hashes_are_exact(self):
        evidence = ROOT / "evidence" / "selene-hart"
        hashes = json.loads((evidence / "CONTACT_SHEET_HASHES.json").read_text())
        self.assertEqual(hashes["graph_count"], 124)
        self.assertEqual(len(hashes["graph_order"]), 124)
        for key in ("isolated_contact_sheet", "projected_contact_sheet"):
            path = evidence / hashes[key]["file"]
            self.assertEqual(hashes[key]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_package_rejects_audit_and_manifest_tampering(self):
        audit_path = (DEFINITIONS / "selene_hart_extraction_audit.json").resolve()
        tampered = json.loads(audit_path.read_text()); tampered["items"][0]["pixel_graph_sha256"] = "0" * 64
        original = Path.read_text
        def controlled(path, *args, **kwargs):
            return json.dumps(tampered) if path.resolve() == audit_path else original(path, *args, **kwargs)
        with patch.object(Path, "read_text", new=controlled):
            with self.assertRaisesRegex(CharacterPackageValidationError, "hash differs"):
                load_character_package(SELENE_HART_PACKAGE_PATH)

        pose_path = (DEFINITIONS / "selene_hart_pose_cells.json").resolve()
        original_bytes = Path.read_bytes
        def tampered_bytes(path, *args, **kwargs):
            data = original_bytes(path, *args, **kwargs)
            return data + b" " if path.resolve() == pose_path else data
        with patch.object(Path, "read_bytes", new=tampered_bytes):
            with self.assertRaisesRegex(CharacterPackageValidationError, "manifest hash differs"):
                load_character_package(SELENE_HART_PACKAGE_PATH)


if __name__ == "__main__":
    unittest.main()
