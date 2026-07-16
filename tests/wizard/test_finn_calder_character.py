import asyncio
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from wizard_avatar.character_package import (
    FINN_CALDER_PACKAGE_PATH,
    CharacterPackageValidationError,
    load_character_package,
)
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.server import create_app


ROOT = Path(__file__).resolve().parents[2]
PERSONA = ROOT / "assets" / "reference" / "personas" / "finn-calder"
PROFILE = PERSONA / "generation-profile.json"
DEFINITIONS = ROOT / "wizard_avatar" / "definitions"


class FinnCalderCharacterTests(unittest.TestCase):
    def make_source(self):
        return ProceduralWizardFrameSource(
            cols=160,
            rows=100,
            character_package_path=FINN_CALDER_PACKAGE_PATH,
        )

    def test_registry_and_package_expose_finn(self):
        registry = load_character_registry()
        self.assertIn("finn-calder-v1", registry.packages)
        package = registry.get("finn-calder-v1")
        self.assertEqual(package.display_name, "Finn Calder")
        self.assertIsNotNone(package.runtime_profile)
        self.assertIsNotNone(package.extraction_audit)
        self.assertIsNotNone(package.pixel_graph_library)
        self.assertTrue(
            {
                "microphone_interaction",
                "welcome_crowd",
                "announce_event",
                "accessibility_check",
                "lead_ritual",
                "celebrate_student_contribution",
                "supervise_transition",
                "community_sign_off",
            }.issubset(package.capabilities)
        )

    def test_original_and_canonical_references_are_preserved(self):
        self.assertEqual(
            hashlib.sha256((PERSONA / "source-reference.png").read_bytes()).hexdigest(),
            "64a602fe7dc96684738a4e7d7728465eefde2d6071b11d555cf05b1e05b12c37",
        )
        self.assertEqual(
            hashlib.sha256((PERSONA / "canonical-voxel.png").read_bytes()).hexdigest(),
            "efac69875fe2b0c38dafe20d3669af2ed97da98b320dc703f41a1c2f9ea9f385",
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
            (DEFINITIONS / "finn_calder_character_manifest.json").read_text(encoding="utf-8")
        )
        hashes = manifest["hashes"]
        expected_sheets = {
            "01-identity-sheet-approved-v1.png",
            "02-turnaround-sheet-approved-v1.png",
            "03-neutral-base-poses-approved-v1.png",
            "04-expression-sheet-approved-v1.png",
            "05-speech-viseme-sheet-approved-v2.png",
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
            ("pose_library_sha256", "finn_calder_pose_cells.json"),
            ("animation_graph_sha256", "finn_calder_animation_graph.json"),
            ("animation_matrix_sha256", "finn_calder_animation_matrix.json"),
            ("extraction_audit_sha256", "finn_calder_extraction_audit.json"),
            ("pixel_graph_library_sha256", "finn_calder_pixel_graphs.json"),
        ):
            self.assertEqual(
                hashes[key], hashlib.sha256((DEFINITIONS / filename).read_bytes()).hexdigest()
            )

    def test_all_124_graphs_are_audited_before_animation_mapping(self):
        package = load_character_package(FINN_CALDER_PACKAGE_PATH)
        pose_payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        reference_payload = json.loads(package.pixel_graph_library.read_text(encoding="utf-8"))
        audit = json.loads(package.extraction_audit.read_text(encoding="utf-8"))
        self.assertEqual(len(pose_payload["poses"]), 92)
        self.assertEqual(reference_payload["graph_count"], 32)
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
                self.assertEqual(
                    item["removed_environment_components"],
                    ["worksheet_background", "grid", "floor", "contact_shadow"],
                )
                self.assertEqual(item["runtime_format"], "colored_pixel_nodes_json")
                self.assertNotIn(".png", item["runtime_asset"].lower())
                self.assertNotIn(".svg", item["runtime_asset"].lower())

    def test_every_graph_is_nonempty_detailed_unique_and_inside_bounds(self):
        package = load_character_package(FINN_CALDER_PACKAGE_PATH)
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
                self.assertGreater(len(nodes), 1200)
                self.assertGreater(len(colors), 250)
                self.assertGreater(max(xs) - min(xs), 20)
                self.assertGreater(max(ys) - min(ys), 29)
                self.assertGreaterEqual(min(xs), 4)
                self.assertLessEqual(max(xs), 67)
                self.assertGreaterEqual(min(ys), 4)
                self.assertLessEqual(max(ys), 91)
                digest = hashlib.sha256(
                    json.dumps(nodes, separators=(",", ":"), sort_keys=True).encode("utf-8")
                ).hexdigest()
                self.assertNotIn(digest, digests)
                digests.add(digest)

    def test_complete_finn_vocabulary_and_pose_local_anchors(self):
        package = load_character_package(FINN_CALDER_PACKAGE_PATH)
        poses = {
            pose["id"]: pose
            for pose in json.loads(package.pose_library.read_text(encoding="utf-8"))["poses"]
        }
        required = {
            "neutral_front", "neutral_back", "turn_left", "turn_right", "crouch",
            "jump_anticipation", "jump_airborne", "fall", "land_contact", "land_recovery",
            "expression_compassion", "expression_skepticism", "expression_determination",
            "viseme_wide_vowel", "viseme_tongue_consonant", "viseme_breath_pause",
            "blink_open", "blink_half_closed", "blink_closed", "welcome_anticipation",
            "inclusive_opening", "microphone_welcome", "energetic_announcement",
            "accessibility_check", "ritual_hold", "scan_listen", "transition_direction",
            "celebration", "appreciation", "community_sign_off",
            "interaction_open_hand", "interaction_closed_hand",
            "interaction_fist", "interaction_reach",
        }
        self.assertTrue(required.issubset(poses))
        feature_graphs = {
            graph["id"]
            for graph in json.loads(package.pixel_graph_library.read_text(encoding="utf-8"))["graphs"]
            if graph["graph_kind"] == "feature_graph"
        }
        self.assertEqual(
            feature_graphs,
            {
                "hand_open_relaxed", "hand_closed", "hand_fist", "hand_pointing",
                "hand_presenting", "hand_reaching", "prop_microphone_grip_front",
                "prop_microphone_grip_three_quarter", "prop_microphone_lowered",
                "prop_microphone_offer", "prop_microphone_receive",
                "prop_microphone_transfer", "prop_microphone_two_hand",
                "prop_microphone_emphasis", "prop_microphone_release",
                "prop_microphone_settled",
            },
        )
        self.assertFalse(feature_graphs & set(poses))
        signature_ids = {
            "welcome_anticipation", "inclusive_opening", "microphone_welcome",
            "welcome_recovery", "announcement_breath", "energetic_announcement",
            "participation_cue", "ritual_hold", "scan_listen", "accessibility_check",
            "transition_direction", "ready_confirmation", "celebration_anticipation",
            "celebration", "appreciation", "community_sign_off",
        }
        self.assertEqual(
            {
                pose["id"]
                for pose in poses.values()
                if "08-signature-actions-sheet-approved-v1.png" in pose["source"]
            },
            signature_ids,
        )
        self.assertFalse(
            {
                "curriculum_explain", "sequence_step_one", "invite_reflection",
                "listen_microphone", "rubric_emphasis", "microphone_present",
                "calm_correction", "protective_seriousness", "measured_celebration",
                "containment_recovery",
            }
            & set(poses)
        )
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

    def test_microphone_anchor_exists_only_on_profile_declared_graphs(self):
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        full_body_ids = {
            pose["id"]
            for pose in profile["poses"]
            if pose.get("graph_kind", "full_body_graph") == "full_body_graph"
        }
        expected = set(profile["anchor_presence"]["microphone"]) & full_body_ids
        poses = json.loads(
            (DEFINITIONS / "finn_calder_pose_cells.json").read_text(encoding="utf-8")
        )["poses"]
        actual = {pose["id"] for pose in poses if "microphone" in pose["anchors"]}
        self.assertEqual(actual, expected)

    def test_animation_graph_references_only_full_body_pose_graphs(self):
        package = load_character_package(FINN_CALDER_PACKAGE_PATH)
        poses = {
            pose["id"]: pose
            for pose in json.loads(package.pose_library.read_text(encoding="utf-8"))["poses"]
        }
        graph = json.loads(package.animation_graph.read_text(encoding="utf-8"))
        sampled_ids = {
            sample["pose_id"]
            for clip in graph["clips"]
            for sample in clip["samples"]
        }
        self.assertTrue(sampled_ids)
        self.assertTrue(sampled_ids.issubset(poses))
        self.assertEqual(
            {poses[pose_id]["graph_kind"] for pose_id in sampled_ids},
            {"full_body_graph"},
        )

    def test_package_rejects_post_audit_graph_and_manifest_tampering(self):
        audit_path = (DEFINITIONS / "finn_calder_extraction_audit.json").resolve()
        tampered = json.loads(audit_path.read_text(encoding="utf-8"))
        tampered["items"][0]["pixel_graph_sha256"] = "0" * 64
        original_read_text = Path.read_text

        def controlled_read_text(path, *args, **kwargs):
            if path.resolve() == audit_path:
                return json.dumps(tampered)
            return original_read_text(path, *args, **kwargs)

        with patch.object(Path, "read_text", new=controlled_read_text):
            with self.assertRaisesRegex(CharacterPackageValidationError, "hash differs"):
                load_character_package(FINN_CALDER_PACKAGE_PATH)

        pose_path = (DEFINITIONS / "finn_calder_pose_cells.json").resolve()
        original_read_bytes = Path.read_bytes

        def controlled_read_bytes(path, *args, **kwargs):
            data = original_read_bytes(path, *args, **kwargs)
            return data + b" " if path.resolve() == pose_path else data

        with patch.object(Path, "read_bytes", new=controlled_read_bytes):
            with self.assertRaisesRegex(CharacterPackageValidationError, "manifest hash differs"):
                load_character_package(FINN_CALDER_PACKAGE_PATH)

    def test_package_rejects_source_worksheet_and_pixel_graph_tampering(self):
        original_read_bytes = Path.read_bytes
        source_path = (PERSONA / "source-reference.png").resolve()

        def source_tamper(path, *args, **kwargs):
            data = original_read_bytes(path, *args, **kwargs)
            return data + b"tamper" if path.resolve() == source_path else data

        with patch.object(Path, "read_bytes", new=source_tamper):
            with self.assertRaisesRegex(
                CharacterPackageValidationError,
                "original_reference_sha256",
            ):
                load_character_package(FINN_CALDER_PACKAGE_PATH)

        worksheet_path = (
            PERSONA
            / "canonical-worksheets"
            / "08-signature-actions-sheet-approved-v1.png"
        ).resolve()

        def worksheet_tamper(path, *args, **kwargs):
            data = original_read_bytes(path, *args, **kwargs)
            return data + b"tamper" if path.resolve() == worksheet_path else data

        with patch.object(Path, "read_bytes", new=worksheet_tamper):
            with self.assertRaisesRegex(
                CharacterPackageValidationError,
                "worksheet 08-signature-actions-sheet-approved-v1.png",
            ):
                load_character_package(FINN_CALDER_PACKAGE_PATH)

        graph_path = (DEFINITIONS / "finn_calder_pixel_graphs.json").resolve()
        graph_payload = json.loads(graph_path.read_text(encoding="utf-8"))
        graph_payload["graphs"][0]["nodes"][0]["rgb"][0] ^= 1
        original_read_text = Path.read_text

        def graph_tamper(path, *args, **kwargs):
            if path.resolve() == graph_path:
                return json.dumps(graph_payload)
            return original_read_text(path, *args, **kwargs)

        with patch.object(Path, "read_text", new=graph_tamper):
            with self.assertRaisesRegex(CharacterPackageValidationError, "hash differs"):
                load_character_package(FINN_CALDER_PACKAGE_PATH)

    def test_live_cells_change_for_motion_expression_speech_and_announcement(self):
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
            WizardCommand("speak", {"text": "Welcome to our community event.", "duration_ms": 1600})
        )
        source.advance_simulation(0.12)
        speaking = source.render_current_frame().cells
        self.assertNotEqual(curious, speaking)
        result = source.apply_command_sync(
            WizardCommand("pose", {"pose_id": "energetic_announcement", "duration_ms": 900})
        )
        self.assertTrue(result.ok)
        announcement = source.render_current_frame().cells
        self.assertNotEqual(speaking, announcement)
        self.assertEqual(source.current_state().pose_id, "energetic_announcement")

    def test_semantic_actions_and_signature_graphs_are_runtime_reachable(self):
        source = self.make_source()
        expected = {
            "turn_left": "turn_left", "turn_right": "turn_right", "crouch": "crouch",
            "jump": "jump_airborne", "fall": "fall", "land": "land_contact",
            "listening": "scan_listen", "explaining": "microphone_welcome",
            "pointing": "transition_direction", "thinking": "accessibility_check",
            "magic_cast": "ritual_hold", "containment": "ready_confirmation",
            "welcome_crowd": "inclusive_opening",
            "announce_event": "energetic_announcement",
            "accessibility_check": "accessibility_check",
            "lead_ritual": "ritual_hold",
            "celebrate_student_contribution": "celebration",
            "supervise_transition": "transition_direction",
            "community_sign_off": "community_sign_off",
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
            "welcome_anticipation", "welcome_recovery", "participation_cue",
            "celebration_anticipation", "appreciation",
            "interaction_open_hand", "interaction_closed_hand", "interaction_fist",
            "interaction_reach",
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
        state.speech_id = "finn-speech-test"
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
            entries["finn-calder-v1"]["assets"]["pixel_graph_library"],
            "/avatar/characters/finn-calder-v1/pixel-graph-library",
        )
        route = next(
            route for route in app.routes
            if route.path == "/avatar/characters/{character_id}/{asset_name}"
        )
        response = asyncio.run(route.endpoint("finn-calder-v1", "pixel-graph-library"))
        self.assertEqual(
            Path(response.path).resolve(),
            (DEFINITIONS / "finn_calder_pixel_graphs.json").resolve(),
        )

    def test_runtime_render_never_decodes_png_or_svg(self):
        with patch("PIL.Image.open", side_effect=AssertionError("runtime image access")):
            source = self.make_source()
            frame = source.render_current_frame()
        self.assertEqual(len(frame.cells), frame.cols * frame.rows * 4)


if __name__ == "__main__":
    unittest.main()
