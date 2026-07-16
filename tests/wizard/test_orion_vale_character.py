import hashlib
import asyncio
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from wizard_avatar.character_package import (
    ORION_VALE_PACKAGE_PATH,
    CharacterPackageValidationError,
    _validate_extraction_audit,
    load_character_package,
)
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.server import create_app


ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "assets" / "reference" / "personas" / "orion-vale" / "generation-profile.json"


class OrionValeCharacterTests(unittest.TestCase):
    def make_source(self):
        return ProceduralWizardFrameSource(
            cols=160,
            rows=100,
            character_package_path=ORION_VALE_PACKAGE_PATH,
        )

    def assert_package_rejects_byte_tamper(self, target, message):
        target = target.resolve()
        original_read_bytes = Path.read_bytes

        def controlled_read_bytes(path):
            payload = original_read_bytes(path)
            if path.resolve() == target:
                return payload + b"tampered"
            return payload

        with patch.object(Path, "read_bytes", new=controlled_read_bytes):
            with self.assertRaisesRegex(CharacterPackageValidationError, message):
                load_character_package(ORION_VALE_PACKAGE_PATH)

    def test_registry_and_package_expose_orion(self):
        registry = load_character_registry()
        self.assertIn("orion-vale-v1", registry.packages)
        package = registry.get("orion-vale-v1")
        self.assertEqual(package.display_name, "Orion Vale")
        self.assertIsNotNone(package.runtime_profile)
        self.assertIsNotNone(package.extraction_audit)
        self.assertIsNotNone(package.pixel_graph_library)
        self.assertIn("journal_interaction", package.capabilities)
        self.assertIn("inquiry_signature_actions", package.capabilities)

    def test_original_and_canonical_references_are_preserved(self):
        directory = ROOT / "assets" / "reference" / "personas" / "orion-vale"
        self.assertEqual(
            hashlib.sha256((directory / "source-reference.png").read_bytes()).hexdigest(),
            "deb391b66fa438f01e0fad8b710bbcbb333aee5761a6737135fda6a2cda43ada",
        )
        self.assertEqual(
            hashlib.sha256((directory / "canonical-voxel.png").read_bytes()).hexdigest(),
            "a81010fb994724b56956dd7718c19f999b8c425c8a206c0fb6df436990fa464f",
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
        manifest_path = ROOT / "wizard_avatar" / "definitions" / "orion_vale_character_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        hashes = manifest["hashes"]
        self.assertEqual(
            hashes["generation_profile_sha256"],
            hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
        )
        for key, filename in (
            ("character_package_sha256", "orion_vale_character_package.json"),
            ("runtime_profile_sha256", "orion_vale_runtime_profile.json"),
            ("pose_library_sha256", "orion_vale_pose_cells.json"),
            ("animation_graph_sha256", "orion_vale_animation_graph.json"),
            ("animation_matrix_sha256", "orion_vale_animation_matrix.json"),
            ("extraction_audit_sha256", "orion_vale_extraction_audit.json"),
            ("pixel_graph_library_sha256", "orion_vale_pixel_graphs.json"),
        ):
            path = ROOT / "wizard_avatar" / "definitions" / filename
            self.assertEqual(hashes[key], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(hashes["extraction_item_count"], 124)
        self.assertEqual(
            manifest["derivation"]["generation_profile"],
            "assets/reference/personas/orion-vale/generation-profile.json",
        )
        self.assertEqual(
            set(hashes["worksheet_sha256"]),
            {
                "02-turnaround-sheet-candidate-v1.png",
                "01-identity-sheet-candidate-v2.png",
                "03-neutral-base-poses-candidate-v2.png",
                "04-expression-sheet-candidate-v2.png",
                "04-expression-sheet-candidate-v1.png",
                "05-speech-viseme-sheet-candidate-v2.png",
                "06-hand-prop-sheet-candidate-v1.png",
                "07-ground-motion-sheet-candidate-v2.png",
                "08-signature-actions-sheet-candidate-v1.png",
                "09-interaction-poses-candidate-v1.png",
            },
        )

    def test_package_rejects_source_canonical_and_every_accepted_worksheet_tamper(self):
        manifest = json.loads(
            (ROOT / "wizard_avatar" / "definitions" / "orion_vale_character_manifest.json")
            .read_text(encoding="utf-8")
        )
        derivation = manifest["derivation"]
        for source_name in ("original_reference", "canonical_reference"):
            with self.subTest(source=source_name):
                self.assert_package_rejects_byte_tamper(
                    ROOT / derivation[source_name], "manifest hash differs"
                )
        worksheet_dir = ROOT / derivation["approved_worksheets"]
        for filename in manifest["hashes"]["worksheet_sha256"]:
            with self.subTest(worksheet=filename):
                self.assert_package_rejects_byte_tamper(
                    worksheet_dir / filename, "worksheet .* hash differs"
                )

    def test_package_rejects_every_generated_asset_tamper(self):
        definitions = ROOT / "wizard_avatar" / "definitions"
        generated = {
            "generation profile": PROFILE,
            "character package": definitions / "orion_vale_character_package.json",
            "runtime profile": definitions / "orion_vale_runtime_profile.json",
            "pose library": definitions / "orion_vale_pose_cells.json",
            "animation graph": definitions / "orion_vale_animation_graph.json",
            "animation matrix": definitions / "orion_vale_animation_matrix.json",
            "extraction audit": definitions / "orion_vale_extraction_audit.json",
            "pixel graph library": definitions / "orion_vale_pixel_graphs.json",
        }
        for name, path in generated.items():
            with self.subTest(asset=name):
                self.assert_package_rejects_byte_tamper(path, "manifest hash differs")

    def test_load_time_validator_rejects_node_tamper_in_each_of_the_124_graphs(self):
        definitions = ROOT / "wizard_avatar" / "definitions"
        audit = json.loads(
            (definitions / "orion_vale_extraction_audit.json").read_text(encoding="utf-8")
        )
        audit_by_id = {item["graph_id"]: item for item in audit["items"]}
        graph_stores = (
            (definitions / "orion_vale_pixel_graphs.json", "graphs", "nodes", False),
            (definitions / "orion_vale_pose_cells.json", "poses", "cells", True),
        )
        tested = 0
        for target, collection_name, nodes_name, is_pose in graph_stores:
            original = json.loads(target.read_text(encoding="utf-8"))
            for graph in original[collection_name]:
                with self.subTest(graph_id=graph["id"]):
                    tampered_graph = json.loads(json.dumps(graph))
                    node = tampered_graph[nodes_name][0]
                    node["rgb"][0] = (node["rgb"][0] + 1) % 256
                    one_item_audit = {
                        "schema_version": 1,
                        "character_id": "orion-vale-v1",
                        "item_count": 1,
                        "items": [audit_by_id[graph["id"]]],
                    }
                    pose_payload = {"poses": [tampered_graph] if is_pose else []}
                    graph_payload = {"graphs": [] if is_pose else [tampered_graph]}
                    with self.assertRaisesRegex(
                        CharacterPackageValidationError, "hash differs"
                    ):
                        _validate_extraction_audit(
                            "orion-vale-v1",
                            pose_payload,
                            graph_payload,
                            one_item_audit,
                        )
                tested += 1
        self.assertEqual(tested, 124)

    def test_pose_library_has_complete_orion_vocabulary(self):
        package = load_character_package(ORION_VALE_PACKAGE_PATH)
        payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        poses = {pose["id"]: pose for pose in payload["poses"]}
        self.assertEqual(len(poses), 108)
        required = {
            "neutral_front", "neutral_back", "neutral_left_profile", "neutral_right_profile",
            "walk_contact_left", "walk_contact_right", "run_reach", "jump_airborne", "land_recovery",
            "expression_curiosity", "expression_compassion", "expression_skepticism",
            "viseme_wide_vowel", "viseme_tongue_consonant", "viseme_breath_pause",
            "blink_open", "blink_half_closed", "blink_closed",
            "listen_socratic", "inquiry_hidden_question", "inquiry_overloaded_word",
            "inquiry_testable_handle", "inquiry_lens_break", "journal_write",
            "journal_page_turn", "gesture_inquiry_down",
            "interaction_open_hand", "interaction_closed_hand", "interaction_fist",
            "interaction_reach",
            "neutral_base_front", "neutral_base_three_quarter", "neutral_base_profile",
            "neutral_base_back", "expression_listening_ready", "expression_reflective_reset",
            "hand_open_relaxed", "hand_fist", "hand_pointing", "hand_writing_grip",
            "prop_journal_open", "prop_journal_page_turn", "prop_journal_offer",
        }
        self.assertTrue(required.issubset(poses))

    def test_all_124_silhouettes_have_a_repeatable_pixel_graph_audit(self):
        package = load_character_package(ORION_VALE_PACKAGE_PATH)
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
            ROOT / "wizard_avatar" / "definitions" / "orion_vale_extraction_audit.json"
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
                load_character_package(ORION_VALE_PACKAGE_PATH)

    def test_package_rejects_audit_worksheet_hash_and_revision_tampering(self):
        audit_path = (
            ROOT / "wizard_avatar" / "definitions" / "orion_vale_extraction_audit.json"
        ).resolve()
        original = json.loads(audit_path.read_text(encoding="utf-8"))
        original_read_text = Path.read_text
        mutations = (
            ("source_worksheet_sha256", "0" * 64, "audit worksheet"),
            ("source_cell", "unapproved-revision.png#panel-0", "revisions differ"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field):
                tampered = json.loads(json.dumps(original))
                tampered["items"][0][field] = value

                def controlled_read_text(path, *args, **kwargs):
                    if path.resolve() == audit_path:
                        return json.dumps(tampered)
                    return original_read_text(path, *args, **kwargs)

                with patch.object(Path, "read_text", new=controlled_read_text):
                    with self.assertRaisesRegex(CharacterPackageValidationError, message):
                        load_character_package(ORION_VALE_PACKAGE_PATH)

    def test_v2_worksheets_and_pose_local_anchors_are_production_inputs(self):
        package = load_character_package(ORION_VALE_PACKAGE_PATH)
        payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        poses = {pose["id"]: pose for pose in payload["poses"]}
        for pose_id in (
            "idle_relaxed",
            "expression_curiosity",
            "viseme_open_vowel",
            "walk_contact_left",
        ):
            self.assertIn("candidate-v2.png", poses[pose_id]["source"])
        for pose_id in ("blink_open", "blink_half_closed", "blink_closed"):
            self.assertIn("05-speech-viseme-sheet-candidate-v2.png", poses[pose_id]["source"])
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

        journal_pose_ids = {
            pose_id for pose_id, pose in poses.items() if "journal" in pose["anchors"]
        }
        self.assertEqual(
            journal_pose_ids,
            {
                "idle_speaking",
                "idle_listening",
                "gesture_explain",
                "gesture_point",
                "gesture_present",
                "gesture_react",
                "gesture_celebrate",
                "listen_compassionate",
                "inquiry_hidden_question",
                "inquiry_overloaded_word",
                "inquiry_testable_handle",
                "inquiry_lens_break",
                "journal_hold",
                "journal_write",
                "journal_page_turn",
                "gesture_inquiry_down",
                "prop_journal_hold_center",
                "prop_journal_cradle",
                "prop_journal_present",
                "prop_journal_open",
                "prop_journal_write",
                "prop_journal_page_turn",
                "prop_journal_close",
                "prop_journal_side_hold",
                "prop_journal_offer",
            },
        )

    def test_every_pose_respects_safe_bounds_and_has_visual_detail(self):
        package = load_character_package(ORION_VALE_PACKAGE_PATH)
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

        source.apply_command_sync(WizardCommand("speak", {"text": "What is the hidden question?", "duration_ms": 1600}))
        source.advance_simulation(0.12)
        speaking = source.render_current_frame().cells
        self.assertNotEqual(curious, speaking)

        result = source.apply_command_sync(
            WizardCommand("pose", {"pose_id": "inquiry_hidden_question", "duration_ms": 900})
        )
        self.assertTrue(result.ok)
        inquiry = source.render_current_frame().cells
        self.assertNotEqual(speaking, inquiry)
        self.assertEqual(source.current_state().pose_id, "inquiry_hidden_question")

    def test_hand_interaction_poses_are_runtime_addressable(self):
        source = self.make_source()
        self.assertNotIn("hand_open_relaxed", source.pose_ids)
        self.assertNotIn("prop_journal_open", source.pose_ids)
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

    def test_semantic_ground_and_journal_actions_are_runtime_addressable(self):
        source = self.make_source()
        expected = {
            "turn_left": "turn_left",
            "turn_right": "turn_right",
            "crouch": "crouch",
            "jump": "jump_airborne",
            "fall": "fall",
            "land": "land_contact",
            "listening": "listen_socratic",
            "journal_hold": "journal_hold",
            "journal_write": "journal_write",
            "journal_page_turn": "journal_page_turn",
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
        source.current_state().speech_id = "orion-speech-test"
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

    def test_server_exposes_orion_through_character_scoped_architecture(self):
        app = create_app()
        paths = {route.path for route in app.routes}
        self.assertIn("/api/avatar/characters", paths)
        self.assertIn("/api/avatar/{character_id}/{command_type}", paths)
        self.assertIn("/ws/avatar/{character_id}", paths)
        self.assertIn("/avatar/characters/{character_id}/{asset_name}", paths)
        entries = {entry["character_id"]: entry for entry in load_character_registry().public_entries()}
        self.assertEqual(
            entries["orion-vale-v1"]["assets"]["extraction_audit"],
            "/avatar/characters/orion-vale-v1/extraction-audit",
        )
        route = next(
            route for route in app.routes
            if route.path == "/avatar/characters/{character_id}/{asset_name}"
        )
        response = asyncio.run(route.endpoint("orion-vale-v1", "pixel-graph-library"))
        self.assertEqual(
            Path(response.path).resolve(),
            (ROOT / "wizard_avatar" / "definitions" / "orion_vale_pixel_graphs.json").resolve(),
        )

    def test_runtime_render_has_no_flattened_png_dependency(self):
        with patch("PIL.Image.open", side_effect=AssertionError("runtime PNG access")):
            source = self.make_source()
            frame = source.render_current_frame()
        self.assertEqual(len(frame.cells), frame.cols * frame.rows * 4)


if __name__ == "__main__":
    unittest.main()
