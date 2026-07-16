import hashlib
import asyncio
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from wizard_avatar.character_package import (
    SERENA_QUILL_PACKAGE_PATH,
    CharacterPackageValidationError,
    load_character_package,
)
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.server import create_app


ROOT = Path(__file__).resolve().parents[2]
DEFINITIONS = ROOT / "wizard_avatar" / "definitions"
PERSONA = ROOT / "assets" / "reference" / "personas" / "serena-quill"
PROFILE = PERSONA / "generation-profile.json"


class SerenaQuillCharacterTests(unittest.TestCase):
    def make_source(self):
        return ProceduralWizardFrameSource(
            cols=160,
            rows=100,
            character_package_path=SERENA_QUILL_PACKAGE_PATH,
        )

    def test_registry_and_package_expose_serena(self):
        registry = load_character_registry()
        self.assertIn("serena-quill-v1", registry.packages)
        package = registry.get("serena-quill-v1")
        self.assertEqual(package.display_name, "Serena Quill")
        self.assertIsNotNone(package.runtime_profile)
        self.assertIsNotNone(package.extraction_audit)
        self.assertIsNotNone(package.pixel_graph_library)
        self.assertIn("orb_interaction", package.capabilities)
        self.assertIn("angelic_facilitation_actions", package.capabilities)
        self.assertIn("wing_secondary_motion", package.capabilities)

    def test_original_and_canonical_references_are_preserved(self):
        directory = ROOT / "assets" / "reference" / "personas" / "serena-quill"
        self.assertEqual(
            hashlib.sha256((directory / "source-reference.png").read_bytes()).hexdigest(),
            "1a388910b47b351427981f029dfac90366ffbc9bf891f7bcb294994381d19d3d",
        )
        self.assertEqual(
            hashlib.sha256((directory / "canonical-voxel.png").read_bytes()).hexdigest(),
            "e1a0d2eac7a867b0bbf60810de5cfab40f328bceba6f61b2a18c717b8bcc0349",
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
        manifest_path = ROOT / "wizard_avatar" / "definitions" / "serena_quill_character_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        hashes = manifest["hashes"]
        self.assertEqual(
            hashes["generation_profile_sha256"],
            hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
        )
        for key, filename in (
            ("pose_library_sha256", "serena_quill_pose_cells.json"),
            ("animation_graph_sha256", "serena_quill_animation_graph.json"),
            ("animation_matrix_sha256", "serena_quill_animation_matrix.json"),
            ("extraction_audit_sha256", "serena_quill_extraction_audit.json"),
            ("pixel_graph_library_sha256", "serena_quill_pixel_graphs.json"),
        ):
            path = ROOT / "wizard_avatar" / "definitions" / filename
            self.assertEqual(hashes[key], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(hashes["extraction_item_count"], 124)
        self.assertEqual(
            set(hashes["worksheet_sha256"]),
            {
                "02-turnaround-sheet-candidate-v1.png",
                "01-identity-sheet-candidate-v3.png",
                "03-neutral-base-poses-candidate-v1.png",
                "04-expression-sheet-candidate-v1.png",
                "05-speech-viseme-sheet-candidate-v1.png",
                "06-hand-prop-sheet-candidate-v1.png",
                "07-ground-motion-sheet-candidate-v1.png",
                "08-signature-actions-sheet-candidate-v1.png",
                "09-interaction-poses-candidate-v1.png",
            },
        )

    def test_pose_library_has_complete_serena_vocabulary(self):
        package = load_character_package(SERENA_QUILL_PACKAGE_PATH)
        payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        poses = {pose["id"]: pose for pose in payload["poses"]}
        self.assertEqual(len(poses), 108)
        required = {
            "neutral_front", "neutral_back", "neutral_left_profile", "neutral_right_profile",
            "walk_contact_left", "walk_down_left", "run_contact_left", "jump_airborne", "land_recovery",
            "expression_curiosity", "expression_compassion", "expression_skepticism",
            "viseme_wide_vowel", "viseme_tongue_consonant", "viseme_breath_pause",
            "blink_open", "blink_half_closed", "blink_closed",
            "mentoring_invitation", "emotional_climate_check", "consent_pause",
            "facilitation", "orb_reassurance", "protective_wing_fold",
            "referral_human_help", "active_listening", "compassionate_agreement",
            "safe_disagreement", "reflective_question", "supportive_answer",
            "luminous_encouragement", "careful_celebration", "deescalation",
            "settled_presence", "interaction_open_stance", "interaction_closed_stance",
            "interaction_safe_fist", "interaction_forward_reach",
            "neutral_base_front", "neutral_base_three_quarter", "neutral_base_profile",
            "neutral_base_back", "expression_mentoring_reassurance", "expression_settled_listening",
            "hand_open_relaxed", "hand_safe_fist", "hand_gentle_point", "hand_consent_pause",
            "prop_orb_two_hand_cradle", "prop_orb_transfer", "prop_orb_release",
        }
        self.assertTrue(required.issubset(poses))

    def test_all_124_silhouettes_have_a_repeatable_pixel_graph_audit(self):
        package = load_character_package(SERENA_QUILL_PACKAGE_PATH)
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
                self.assertEqual(item["isolated_silhouette_sha256"], item["pixel_graph_sha256"])
                self.assertEqual(item["projected_diff_pixel_count"], 0)
                self.assertEqual(item["validation_result"], "passed")
                self.assertEqual(item["baseline_y"], 91)
                self.assertEqual(item["root"], [36, 91])
                self.assertIn("source_panel_bounds", item)
                self.assertTrue(item["background_removed"])
                self.assertTrue(item["floor_shadow_removed"])
                self.assertIn("floor_shadow_rejection", item["isolation_method"])
                self.assertEqual(item["runtime_format"], "colored_pixel_nodes_json")
                self.assertNotIn(".png", item["runtime_asset"])
                self.assertNotIn(".svg", item["runtime_asset"])

    def test_package_rejects_a_pixel_graph_changed_after_audit(self):
        audit_path = (
            ROOT / "wizard_avatar" / "definitions" / "serena_quill_extraction_audit.json"
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
                load_character_package(SERENA_QUILL_PACKAGE_PATH)

    def test_package_rejects_tampered_reference_provenance(self):
        manifest_path = (
            ROOT / "wizard_avatar" / "definitions" / "serena_quill_character_manifest.json"
        ).resolve()
        tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
        tampered["hashes"]["canonical_reference_sha256"] = "0" * 64
        original_read_text = Path.read_text

        def controlled_read_text(path, *args, **kwargs):
            if path.resolve() == manifest_path:
                return json.dumps(tampered)
            return original_read_text(path, *args, **kwargs)

        with patch.object(Path, "read_text", new=controlled_read_text):
            with self.assertRaisesRegex(
                CharacterPackageValidationError, "canonical_reference"
            ):
                load_character_package(SERENA_QUILL_PACKAGE_PATH)

    def test_124_up_visual_audit_is_hashed_and_pixel_exact(self):
        evidence = ROOT / "evidence" / "serena-quill"
        summary_path = evidence / "serena-quill-124-visual-audit.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["cell_count"], 124)
        self.assertEqual(summary["failed_count"], 0)
        self.assertEqual(len(summary["comparisons"]), 124)
        self.assertTrue(all(item["different_nodes"] == 0 for item in summary["comparisons"]))
        for name, hash_name in (
            ("serena-quill-124-isolated-silhouettes.png", "isolated_contact_sheet_sha256"),
            ("serena-quill-124-pixel-graph-renders.png", "projected_contact_sheet_sha256"),
        ):
            self.assertEqual(
                hashlib.sha256((evidence / name).read_bytes()).hexdigest(),
                summary[hash_name],
            )

    def test_pale_wings_robe_halo_and_orb_survive_extraction(self):
        package = load_character_package(SERENA_QUILL_PACKAGE_PATH)
        pose_payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        graph_payload = json.loads(package.pixel_graph_library.read_text(encoding="utf-8"))
        graphs = [
            *(graph["nodes"] for graph in graph_payload["graphs"][1:]),
            *(pose["cells"] for pose in pose_payload["poses"]),
        ]
        for nodes in graphs:
            cream_nodes = sum(
                1
                for node in nodes
                if node["rgb"][0] >= 165
                and node["rgb"][1] >= 145
                and node["rgb"][2] >= 95
                and node["rgb"][0] - node["rgb"][2] >= 20
            )
            orange_gold_nodes = sum(
                1
                for node in nodes
                if node["rgb"][0] >= 175
                and node["rgb"][0] >= node["rgb"][1] + 25
                and node["rgb"][1] >= 75
                and node["rgb"][2] <= 135
            )
            self.assertGreater(cream_nodes, 80)
            self.assertGreater(orange_gold_nodes, 250)

    def test_accepted_worksheets_and_pose_local_anchors_are_production_inputs(self):
        package = load_character_package(SERENA_QUILL_PACKAGE_PATH)
        payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        poses = {pose["id"]: pose for pose in payload["poses"]}
        for pose_id in ("idle_relaxed", "expression_curiosity", "viseme_open_vowel", "walk_contact_left"):
            self.assertIn("candidate-v1.png", poses[pose_id]["source"])
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

        orb_pose_ids = {
            pose_id for pose_id, pose in poses.items() if "orb" in pose["anchors"]
        }
        self.assertEqual(
            orb_pose_ids,
            set(json.loads(PROFILE.read_text())["anchor_presence"]["orb"]),
        )

    def test_every_pose_respects_safe_bounds_and_has_visual_detail(self):
        package = load_character_package(SERENA_QUILL_PACKAGE_PATH)
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

        source.apply_command_sync(WizardCommand("speak", {"text": "Would you like support?", "duration_ms": 1600}))
        source.advance_simulation(0.12)
        speaking = source.render_current_frame().cells
        self.assertNotEqual(curious, speaking)

        result = source.apply_command_sync(
            WizardCommand("pose", {"pose_id": "protective_wing_fold", "duration_ms": 900})
        )
        self.assertTrue(result.ok)
        support = source.render_current_frame().cells
        self.assertNotEqual(speaking, support)
        self.assertEqual(source.current_state().pose_id, "protective_wing_fold")

    def test_hand_interaction_poses_are_runtime_addressable(self):
        source = self.make_source()
        self.assertNotIn("hand_open_relaxed", source.pose_ids)
        self.assertNotIn("prop_orb_offered", source.pose_ids)
        for pose_id in (
            "interaction_open_stance",
            "interaction_closed_stance",
            "interaction_safe_fist",
            "interaction_forward_reach",
        ):
            with self.subTest(pose_id=pose_id):
                result = source.apply_command_sync(
                    WizardCommand("pose", {"pose_id": pose_id, "duration_ms": 900})
                )
                self.assertTrue(result.ok)
                source.render_current_frame()
                self.assertEqual(source.current_state().pose_id, pose_id)

    def test_every_runtime_and_animation_pose_reference_is_full_body(self):
        pose_payload = json.loads(
            (DEFINITIONS / "serena_quill_pose_cells.json").read_text()
        )
        graph_kind = {
            pose["id"]: pose.get("graph_kind") for pose in pose_payload["poses"]
        }
        runtime = json.loads(
            (DEFINITIONS / "serena_quill_runtime_profile.json").read_text()
        )
        references = {
            runtime["default_pose_id"],
            *runtime["facing_poses"].values(),
            *runtime["action_poses"].values(),
            *runtime["walking_cycle"],
            *runtime["running_cycle"],
            *runtime["airborne_poses"].values(),
            *runtime["speech_poses"],
            *runtime["blink_poses"].values(),
            *("expression_{}".format(value) for value in runtime["expression_aliases"].values()),
        }
        animation = json.loads(
            (DEFINITIONS / "serena_quill_animation_graph.json").read_text()
        )
        references.update(
            sample["pose_id"]
            for clip in animation["clips"]
            for sample in clip["samples"]
        )
        self.assertTrue(references)
        self.assertEqual(
            {pose_id: graph_kind.get(pose_id) for pose_id in references},
            {pose_id: "full_body_graph" for pose_id in references},
        )
        audit_only = {
            pose_id for pose_id, kind in graph_kind.items()
            if kind in {"feature_graph", "reference_graph"}
        }
        self.assertTrue(audit_only)
        self.assertTrue(audit_only.isdisjoint(references))

    def test_orb_clip_preserves_full_body_orb_action_semantics(self):
        animation = json.loads(
            (DEFINITIONS / "serena_quill_animation_graph.json").read_text()
        )
        orb_clip = next(
            clip for clip in animation["clips"] if clip["clip_id"] == "serena_orb"
        )
        self.assertEqual(
            [sample["pose_id"] for sample in orb_clip["samples"]],
            [
                "orb_reassurance",
                "mentoring_invitation",
                "compassionate_agreement",
                "facilitation",
                "settled_presence",
            ],
        )

    def test_semantic_ground_and_angelic_actions_are_runtime_addressable(self):
        source = self.make_source()
        expected = {
            "turn_left": "turn_left",
            "turn_right": "turn_right",
            "crouch": "crouch",
            "jump": "jump_airborne",
            "fall": "fall",
            "land": "land_contact",
            "listening": "active_listening",
            "mentoring_invitation": "mentoring_invitation",
            "consent_pause": "consent_pause",
            "orb_reassurance": "orb_reassurance",
            "protective_wing_fold": "protective_wing_fold",
            "human_referral": "referral_human_help",
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
        self.assertEqual(source.current_state().pose_id, "walk_up_right")
        changed_cells = sum(
            open_frame[index:index + 4] != blink_frame[index:index + 4]
            for index in range(0, len(open_frame), 4)
        )
        self.assertGreater(changed_cells, 0)
        self.assertLess(changed_cells, 120)
        source.current_state().speech_id = "serena-speech-test"
        source.current_state().speech_until = 2.0
        speech_frame = source.render_current_frame().cells
        self.assertEqual(source.current_state().pose_id, "walk_up_right")
        self.assertNotEqual(blink_frame, speech_frame)

    def test_package_rejects_tampering_across_complete_provenance_chain(self):
        manifest = json.loads(
            (DEFINITIONS / "serena_quill_character_manifest.json").read_text()
        )
        targets = {
            "generation_profile": PROFILE,
            "original_source": PERSONA / "source-reference.png",
            "canonical_voxel": PERSONA / "canonical-voxel.png",
            "character_package": DEFINITIONS / "serena_quill_character_package.json",
            "runtime_profile": DEFINITIONS / "serena_quill_runtime_profile.json",
            "pose_library": DEFINITIONS / "serena_quill_pose_cells.json",
            "animation_graph": DEFINITIONS / "serena_quill_animation_graph.json",
            "animation_matrix": DEFINITIONS / "serena_quill_animation_matrix.json",
            "extraction_audit": DEFINITIONS / "serena_quill_extraction_audit.json",
            "pixel_graph_library": DEFINITIONS / "serena_quill_pixel_graphs.json",
        }
        worksheet_dir = PERSONA / "canonical-worksheets"
        for filename in manifest["hashes"]["worksheet_sha256"]:
            targets["worksheet_{}".format(filename[:2])] = worksheet_dir / filename
        self.assertEqual(
            {label for label in targets if label.startswith("worksheet_")},
            {"worksheet_{:02d}".format(index) for index in range(1, 10)},
        )
        original_read_bytes = Path.read_bytes
        for label, target in targets.items():
            resolved_target = target.resolve()

            def tampered_read_bytes(path, *args, **kwargs):
                data = original_read_bytes(path, *args, **kwargs)
                return data + b"tamper" if path.resolve() == resolved_target else data

            with self.subTest(asset=label), patch.object(
                Path, "read_bytes", new=tampered_read_bytes
            ):
                with self.assertRaises(CharacterPackageValidationError):
                    load_character_package(SERENA_QUILL_PACKAGE_PATH)

    def test_package_rejects_manifest_escape_and_canonical_count_tampering(self):
        manifest_path = (DEFINITIONS / "serena_quill_character_manifest.json").resolve()
        original_manifest = json.loads(manifest_path.read_text())
        cases = []
        wrong_count = json.loads(json.dumps(original_manifest))
        wrong_count["hashes"]["extraction_item_count"] = 123
        cases.append(("exact_124", wrong_count))
        source_escape = json.loads(json.dumps(original_manifest))
        source_escape["derivation"]["generation_profile"] = "../../outside.json"
        cases.append(("source_escape", source_escape))
        worksheet_escape = json.loads(json.dumps(original_manifest))
        worksheet_escape["derivation"]["approved_worksheets"] = "../../"
        cases.append(("worksheet_escape", worksheet_escape))
        missing_worksheet = json.loads(json.dumps(original_manifest))
        missing_worksheet["hashes"]["worksheet_sha256"].pop(
            next(iter(missing_worksheet["hashes"]["worksheet_sha256"]))
        )
        cases.append(("nine_worksheets", missing_worksheet))
        original_read_text = Path.read_text
        for label, tampered in cases:
            def tampered_read_text(path, *args, **kwargs):
                if path.resolve() == manifest_path:
                    return json.dumps(tampered)
                return original_read_text(path, *args, **kwargs)

            with self.subTest(case=label), patch.object(
                Path, "read_text", new=tampered_read_text
            ):
                with self.assertRaises(CharacterPackageValidationError):
                    load_character_package(SERENA_QUILL_PACKAGE_PATH)

    def test_package_rejects_out_of_bounds_duplicate_and_invalid_rgb_nodes(self):
        graph_path = (DEFINITIONS / "serena_quill_pixel_graphs.json").resolve()
        audit_path = (DEFINITIONS / "serena_quill_extraction_audit.json").resolve()
        original_graph = json.loads(graph_path.read_text())
        original_audit = json.loads(audit_path.read_text())
        original_read_text = Path.read_text
        for label, replacement in (
            ("unsafe_x", {"x": 0}),
            ("invalid_rgb", {"rgb": [256, 0, 0]}),
            ("duplicate_coordinate", {"duplicate": True}),
        ):
            graph = json.loads(json.dumps(original_graph))
            audit = json.loads(json.dumps(original_audit))
            target_graph = graph["graphs"][0]
            if replacement.pop("duplicate", False):
                target_graph["nodes"][1]["x"] = target_graph["nodes"][0]["x"]
                target_graph["nodes"][1]["y"] = target_graph["nodes"][0]["y"]
            else:
                target_graph["nodes"][0].update(replacement)
            nodes = target_graph["nodes"]
            item = next(
                entry for entry in audit["items"]
                if entry["graph_id"] == target_graph["id"]
            )
            item["pixel_graph_sha256"] = hashlib.sha256(
                json.dumps(nodes, separators=(",", ":"), sort_keys=True).encode()
            ).hexdigest()

            def tampered_read_text(path, *args, **kwargs):
                if path.resolve() == graph_path:
                    return json.dumps(graph)
                if path.resolve() == audit_path:
                    return json.dumps(audit)
                return original_read_text(path, *args, **kwargs)

            with self.subTest(case=label), patch.object(
                Path, "read_text", new=tampered_read_text
            ):
                with self.assertRaises(CharacterPackageValidationError):
                    load_character_package(SERENA_QUILL_PACKAGE_PATH)

    def test_seeded_simulation_reaches_the_authored_blink_graph(self):
        source = self.make_source()
        open_frame = source.render_current_frame().cells
        source.advance_simulation(4.05)
        blink_frame = source.render_current_frame().cells
        self.assertEqual(source.current_state().pose_id, "neutral_front")
        self.assertNotEqual(open_frame, blink_frame)

    def test_server_exposes_serena_through_character_scoped_architecture(self):
        app = create_app()
        paths = {route.path for route in app.routes}
        self.assertIn("/api/avatar/characters", paths)
        self.assertIn("/api/avatar/{character_id}/{command_type}", paths)
        self.assertIn("/ws/avatar/{character_id}", paths)
        self.assertIn("/avatar/characters/{character_id}/{asset_name}", paths)
        entries = {entry["character_id"]: entry for entry in load_character_registry().public_entries()}
        self.assertEqual(
            entries["serena-quill-v1"]["assets"]["extraction_audit"],
            "/avatar/characters/serena-quill-v1/extraction-audit",
        )
        route = next(
            route for route in app.routes
            if route.path == "/avatar/characters/{character_id}/{asset_name}"
        )
        response = asyncio.run(route.endpoint("serena-quill-v1", "pixel-graph-library"))
        self.assertEqual(
            Path(response.path).resolve(),
            (ROOT / "wizard_avatar" / "definitions" / "serena_quill_pixel_graphs.json").resolve(),
        )

    def test_runtime_render_has_no_flattened_png_dependency(self):
        with patch("PIL.Image.open", side_effect=AssertionError("runtime PNG access")):
            source = self.make_source()
            frame = source.render_current_frame()
        self.assertEqual(len(frame.cells), frame.cols * frame.rows * 4)


if __name__ == "__main__":
    unittest.main()
