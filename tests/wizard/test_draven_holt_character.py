import asyncio
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from wizard_avatar.character_package import (
    DRAVEN_HOLT_PACKAGE_PATH,
    CharacterPackageValidationError,
    load_character_package,
)
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.server import create_app


ROOT = Path(__file__).resolve().parents[2]
PERSONA = ROOT / "assets" / "reference" / "personas" / "draven-holt"
PROFILE = PERSONA / "generation-profile.json"
DEFINITIONS = ROOT / "wizard_avatar" / "definitions"


class DravenHoltCharacterTests(unittest.TestCase):
    def make_source(self):
        return ProceduralWizardFrameSource(
            cols=160, rows=100, character_package_path=DRAVEN_HOLT_PACKAGE_PATH
        )

    def graphs(self):
        package = load_character_package(DRAVEN_HOLT_PACKAGE_PATH)
        references = json.loads(package.pixel_graph_library.read_text(encoding="utf-8"))["graphs"]
        poses = json.loads(package.pose_library.read_text(encoding="utf-8"))["poses"]
        return [(graph["id"], graph["nodes"]) for graph in references] + [
            (pose["id"], pose["cells"]) for pose in poses
        ]

    def test_registry_package_and_exact_draven_capabilities(self):
        registry = load_character_registry()
        package = registry.get("draven-holt-v1")
        self.assertEqual(package.display_name, "Draven Holt")
        self.assertTrue({
            "assign_owner", "deadline_emphasis", "resource_allocation",
            "blocker_escalation", "clipboard_handoff",
            "clipboard_and_pencil_interaction",
        }.issubset(package.capabilities))
        self.assertIsNotNone(package.runtime_profile)
        self.assertIsNotNone(package.manifest)
        self.assertIsNotNone(package.extraction_audit)
        self.assertIsNotNone(package.pixel_graph_library)

    def test_immutable_reference_hashes_and_deterministic_generation(self):
        self.assertEqual(
            hashlib.sha256((PERSONA / "source-reference.png").read_bytes()).hexdigest(),
            "7908ed681f5fb723d14d454b5621eae24645a4e30577e0dc2be79768d237e0d9",
        )
        self.assertEqual(
            hashlib.sha256((PERSONA / "canonical-voxel.png").read_bytes()).hexdigest(),
            "e7fb434cd76e087a5fa9ec35020c6950d1b75d054a3cc4204e5115c12fe3d68b",
        )
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "generate_voxel_persona_character.py"), str(PROFILE), "--check"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_manifest_lineage_hashes_count_and_accepted_sheets(self):
        manifest = json.loads((DEFINITIONS / "draven_holt_character_manifest.json").read_text())
        hashes = manifest["hashes"]
        expected = {f"{index:02d}-{suffix}-approved-v1.png" for index, suffix in (
            (1, "identity-sheet"), (2, "turnaround-sheet"), (3, "neutral-base-poses"),
            (4, "expression-sheet"), (5, "speech-viseme-sheet"), (6, "hand-prop-sheet"),
            (7, "ground-motion-sheet"), (8, "signature-actions-sheet"), (9, "interaction-poses"),
        )}
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
            ("character_package_sha256", "draven_holt_character_package.json"),
            ("runtime_profile_sha256", "draven_holt_runtime_profile.json"),
            ("pose_library_sha256", "draven_holt_pose_cells.json"),
            ("animation_graph_sha256", "draven_holt_animation_graph.json"),
            ("animation_matrix_sha256", "draven_holt_animation_matrix.json"),
            ("extraction_audit_sha256", "draven_holt_extraction_audit.json"),
            ("pixel_graph_library_sha256", "draven_holt_pixel_graphs.json"),
        ):
            self.assertEqual(hashes[key], hashlib.sha256((DEFINITIONS / filename).read_bytes()).hexdigest())

    def test_all_124_transparent_colored_graphs_are_unique_bounded_and_audited(self):
        graphs = self.graphs()
        audit = json.loads((DEFINITIONS / "draven_holt_extraction_audit.json").read_text())
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
                worksheet_name, panel_index = item["source_cell"].split("#panel-")
                self.assertTrue(worksheet_name.endswith(".png"))
                self.assertTrue(panel_index.isdigit())
                self.assertTrue(
                    (PERSONA / "canonical-worksheets" / worksheet_name).is_file(),
                    item["source_cell"],
                )
                self.assertEqual(item["pixel_graph_sha256"], digest)
                self.assertEqual(item["pixel_node_count"], len(nodes))
                self.assertEqual(item["bounds"], {
                    "left": min(xs), "top": min(ys), "right": max(xs), "bottom": max(ys)
                })

    def test_no_background_floor_contact_shadow_or_forbidden_runtime_images(self):
        package = load_character_package(DRAVEN_HOLT_PACKAGE_PATH)
        for path in (package.animation_graph, package.animation_matrix):
            payload = path.read_text(encoding="utf-8").lower()
            self.assertNotIn(".png", payload)
            self.assertNotIn(".svg", payload)
        audit = json.loads(package.extraction_audit.read_text(encoding="utf-8"))
        self.assertEqual(audit["runtime_image_assets"], [])
        for item in audit["items"]:
            self.assertNotIn(".png", item["runtime_asset"].lower())
            self.assertNotIn(".svg", item["runtime_asset"].lower())
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
                bottom = max(node["y"] for node in nodes)
                self.assertLess(len([node for node in nodes if node["y"] == bottom]), 45)

    def test_exact_pose_vocabulary_props_signature_arcs_and_no_persona_leftovers(self):
        poses = {pose["id"] for pose in json.loads((DEFINITIONS / "draven_holt_pose_cells.json").read_text())["poses"]}
        required = {
            "prop_clipboard_grip", "prop_pencil_writing_grip", "prop_clipboard_offered",
            "prop_clipboard_received", "prop_transfer_grip", "prop_deadline_tap",
            "assign_owner_preparation", "assign_owner_open_hand", "assign_owner_confirming_point", "assign_owner_recovery",
            "deadline_raise_clipboard", "deadline_pencil_tap", "deadline_clipboard_emphasis", "deadline_recovery",
            "allocation_checklist_review", "allocation_presentation", "allocation_blocker_escalation", "allocation_recovery",
            "handoff_checklist_scan", "handoff_extend_clipboard", "handoff_release", "handoff_settled_pencil_ready",
        }
        self.assertTrue(required.issubset(poses))
        profile_and_outputs = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in [PROFILE, *DEFINITIONS.glob("draven_holt*.json")]
        )
        for leftover in ("rohan", "meter", "wrench", "finn", "journal", "cigar", "smoke", "tobacco"):
            self.assertNotIn(leftover, profile_and_outputs)

    def test_only_full_body_graphs_are_runtime_pose_capable(self):
        payload = json.loads((DEFINITIONS / "draven_holt_pose_cells.json").read_text())
        full_body = {pose["id"] for pose in payload["poses"] if pose["graph_kind"] == "full_body_graph"}
        features = {pose["id"] for pose in payload["poses"] if pose["graph_kind"] == "feature_graph"}
        self.assertEqual(len(full_body), 92)
        self.assertEqual(len(features), 16)
        source = self.make_source()
        self.assertEqual(set(source.pose_ids), full_body)
        self.assertTrue(features.isdisjoint(source.pose_ids))

    def test_clipboard_and_pencil_anchors_match_profile_declarations(self):
        profile = json.loads(PROFILE.read_text())
        poses = json.loads((DEFINITIONS / "draven_holt_pose_cells.json").read_text())["poses"]
        for anchor in ("clipboard", "pencil"):
            expected = set(profile["anchor_presence"][anchor])
            actual = {pose["id"] for pose in poses if anchor in pose["anchors"]}
            self.assertEqual(actual, expected)
            for pose in poses:
                if anchor in pose["anchors"]:
                    occupied = {(cell["x"], cell["y"]) for cell in pose["cells"]}
                    self.assertIn(tuple(pose["anchors"][anchor]), occupied)

    def test_draven_identity_palette_is_present_in_serialized_rgb_nodes(self):
        colors = [node["rgb"] for _, nodes in self.graphs() for node in nodes]
        counts = {
            "matte_black": sum(max(c) <= 55 for c in colors),
            "vivid_orange": sum(c[0] >= 180 and 50 <= c[1] <= 170 and c[2] <= 60 for c in colors),
            "emerald_green": sum(c[1] >= 100 and c[1] >= c[0] * 1.5 and c[1] >= c[2] * 1.3 for c in colors),
            "warm_brown": sum(c[0] >= 90 and c[0] >= c[1] * 1.35 and c[1] >= c[2] * 1.15 for c in colors),
            "paper_white": sum(min(c) >= 220 and max(c) - min(c) <= 35 for c in colors),
            "neutral_metal": sum(min(c) >= 120 and max(c) - min(c) <= 25 for c in colors),
        }
        self.assertGreater(counts["matte_black"], 100000)
        self.assertGreater(counts["vivid_orange"], 5000)
        self.assertGreater(counts["emerald_green"], 1000)
        self.assertGreater(counts["warm_brown"], 30000)
        self.assertGreater(counts["paper_white"], 2500)
        self.assertGreater(counts["neutral_metal"], 8000)

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
        source.apply_command_sync(WizardCommand("speak", {"text": "Owner confirmed. Deadline locked.", "duration_ms": 1200}))
        source.advance_simulation(0.12)
        self.assertNotEqual(expression, source.render_current_frame().cells)
        expected = {
            "assign_owner": "assign_owner_confirming_point",
            "deadline_emphasis": "deadline_pencil_tap",
            "resource_allocation": "allocation_presentation",
            "clipboard_handoff": "handoff_extend_clipboard",
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
        entry = {item["character_id"]: item for item in load_character_registry().public_entries()}["draven-holt-v1"]
        self.assertEqual(entry["assets"]["pixel_graph_library"], "/avatar/characters/draven-holt-v1/pixel-graph-library")
        route = next(route for route in app.routes if route.path == "/avatar/characters/{character_id}/{asset_name}")
        response = asyncio.run(route.endpoint("draven-holt-v1", "pixel-graph-library"))
        self.assertEqual(Path(response.path).resolve(), (DEFINITIONS / "draven_holt_pixel_graphs.json").resolve())
        with patch("PIL.Image.open", side_effect=AssertionError("runtime image access")):
            frame = self.make_source().render_current_frame()
        self.assertEqual(len(frame.cells), frame.cols * frame.rows * 4)

    def test_contact_sheet_hashes_are_exact(self):
        evidence = ROOT / "evidence" / "draven-holt"
        hashes = json.loads((evidence / "CONTACT_SHEET_HASHES.json").read_text())
        self.assertEqual(hashes["graph_count"], 124)
        self.assertEqual(len(hashes["graph_order"]), 124)
        for key in ("isolated_contact_sheet", "projected_contact_sheet"):
            path = evidence / hashes[key]["file"]
            self.assertEqual(hashes[key]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_package_rejects_audit_and_manifest_tampering(self):
        audit_path = (DEFINITIONS / "draven_holt_extraction_audit.json").resolve()
        tampered = json.loads(audit_path.read_text()); tampered["items"][0]["pixel_graph_sha256"] = "0" * 64
        original = Path.read_text
        def controlled(path, *args, **kwargs):
            return json.dumps(tampered) if path.resolve() == audit_path else original(path, *args, **kwargs)
        with patch.object(Path, "read_text", new=controlled):
            with self.assertRaisesRegex(CharacterPackageValidationError, "hash differs"):
                load_character_package(DRAVEN_HOLT_PACKAGE_PATH)

        pose_path = (DEFINITIONS / "draven_holt_pose_cells.json").resolve()
        original_bytes = Path.read_bytes
        def tampered_bytes(path, *args, **kwargs):
            data = original_bytes(path, *args, **kwargs)
            return data + b" " if path.resolve() == pose_path else data
        with patch.object(Path, "read_bytes", new=tampered_bytes):
            with self.assertRaisesRegex(CharacterPackageValidationError, "manifest hash differs"):
                load_character_package(DRAVEN_HOLT_PACKAGE_PATH)

    def test_package_rejects_every_immutable_and_generated_provenance_tamper(self):
        manifest = json.loads(
            (DEFINITIONS / "draven_holt_character_manifest.json").read_text()
        )
        targets = [
            PROFILE,
            PERSONA / "source-reference.png",
            PERSONA / "canonical-voxel.png",
            DRAVEN_HOLT_PACKAGE_PATH,
            DEFINITIONS / "draven_holt_runtime_profile.json",
            DEFINITIONS / "draven_holt_pose_cells.json",
            DEFINITIONS / "draven_holt_animation_graph.json",
            DEFINITIONS / "draven_holt_animation_matrix.json",
            DEFINITIONS / "draven_holt_extraction_audit.json",
            DEFINITIONS / "draven_holt_pixel_graphs.json",
            *(
                PERSONA / "canonical-worksheets" / filename
                for filename in manifest["hashes"]["worksheet_sha256"]
            ),
        ]
        original_read_bytes = Path.read_bytes
        for target in targets:
            resolved = target.resolve()

            def controlled_read_bytes(path, *args, **kwargs):
                payload = original_read_bytes(path, *args, **kwargs)
                return payload + b"tampered" if path.resolve() == resolved else payload

            with self.subTest(target=target.name):
                with patch.object(Path, "read_bytes", new=controlled_read_bytes):
                    with self.assertRaisesRegex(
                        CharacterPackageValidationError, "hash differs"
                    ):
                        load_character_package(DRAVEN_HOLT_PACKAGE_PATH)


if __name__ == "__main__":
    unittest.main()
