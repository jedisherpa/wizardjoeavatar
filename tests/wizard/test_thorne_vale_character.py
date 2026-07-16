import hashlib
import asyncio
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from wizard_avatar.character_package import (
    THORNE_VALE_PACKAGE_PATH,
    CharacterPackageValidationError,
    load_character_package,
)
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.server import create_app


ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "assets/reference/personas/thorne-vale/generation-profile.json"
DEFINITIONS = ROOT / "wizard_avatar/definitions"


class ThorneValeCharacterTests(unittest.TestCase):
    def make_source(self):
        return ProceduralWizardFrameSource(
            cols=160,
            rows=100,
            character_package_path=THORNE_VALE_PACKAGE_PATH,
        )

    def test_registry_and_package_expose_thorne(self):
        registry = load_character_registry()
        self.assertIn("thorne-vale-v1", registry.packages)
        package = registry.get("thorne-vale-v1")
        self.assertEqual(package.display_name, "Thorne Vale")
        self.assertIn("sword_and_parchment_interaction", package.capabilities)
        self.assertIn("decision_rights_signature_actions", package.capabilities)
        self.assertIsNotNone(package.runtime_profile)
        self.assertIsNotNone(package.extraction_audit)
        self.assertIsNotNone(package.pixel_graph_library)

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

    def test_manifest_preserves_and_hashes_the_complete_approved_lineage(self):
        package = load_character_package(THORNE_VALE_PACKAGE_PATH)
        manifest = json.loads(package.manifest.read_text(encoding="utf-8"))
        hashes = manifest["hashes"]
        persona_dir = ROOT / "assets/reference/personas/thorne-vale"
        self.assertEqual(
            hashes["original_reference_sha256"],
            hashlib.sha256((persona_dir / "source-reference.png").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            hashes["canonical_reference_sha256"],
            hashlib.sha256((persona_dir / "canonical-voxel.png").read_bytes()).hexdigest(),
        )
        self.assertEqual(hashes["extraction_item_count"], 124)
        self.assertEqual(
            set(hashes["worksheet_sha256"]),
            {
                "01-identity-sheet-v3.png",
                "02-turnaround-sheet-v1.png",
                "03-neutral-base-poses-v1.png",
                "04-full-body-expression-sheet-v1.png",
                "05-full-body-viseme-blink-sheet-v1.png",
                "06-hand-prop-sheet-v1.png",
                "07-grounded-motion-sheet-v2.png",
                "08-signature-actions-sheet-v1.png",
                "09-articulation-open-closed-fist-reach-v1.png",
            },
        )
        self.assertNotIn("01-identity-sheet-v1.png", hashes["worksheet_sha256"])
        self.assertNotIn("01-identity-sheet-v2.png", hashes["worksheet_sha256"])
        self.assertNotIn("07-grounded-motion-sheet-v1.png", hashes["worksheet_sha256"])

    def test_all_124_transparent_graphs_pass_the_repeatable_audit(self):
        package = load_character_package(THORNE_VALE_PACKAGE_PATH)
        pose_payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        graph_payload = json.loads(package.pixel_graph_library.read_text(encoding="utf-8"))
        audit = json.loads(package.extraction_audit.read_text(encoding="utf-8"))
        self.assertEqual(len(pose_payload["poses"]), 108)
        self.assertEqual(graph_payload["graph_count"], 16)
        self.assertEqual(audit["item_count"], 124)
        self.assertEqual(audit["runtime_image_assets"], [])
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
        graphs = {graph["id"]: graph["nodes"] for graph in graph_payload["graphs"]}
        graphs.update({pose["id"]: pose["cells"] for pose in pose_payload["poses"]})
        self.assertEqual(set(graphs), {item["graph_id"] for item in audit["items"]})
        for item in audit["items"]:
            with self.subTest(graph_id=item["graph_id"]):
                nodes = graphs[item["graph_id"]]
                digest = hashlib.sha256(
                    json.dumps(nodes, separators=(",", ":"), sort_keys=True).encode("utf-8")
                ).hexdigest()
                self.assertEqual(item["pixel_graph_sha256"], digest)
                self.assertEqual(item["pixel_node_count"], len(nodes))
                self.assertTrue(item["background_removed"])
                self.assertEqual(item["runtime_format"], "colored_pixel_nodes_json")
                self.assertNotIn(".png", item["runtime_asset"].lower())
                self.assertNotIn(".svg", item["runtime_asset"].lower())

    def test_accepted_identity_v3_and_motion_v2_are_the_only_runtime_sources(self):
        package = load_character_package(THORNE_VALE_PACKAGE_PATH)
        audit = json.loads(package.extraction_audit.read_text(encoding="utf-8"))
        identity_sources = {
            item["source_cell"].split("#", 1)[0]
            for item in audit["items"]
            if item["category"] == "identity_reference"
        }
        motion_sources = {
            item["source_cell"].split("#", 1)[0]
            for item in audit["items"]
            if item["category"] == "motion"
        }
        self.assertEqual(identity_sources, {"01-identity-sheet-v3.png"})
        self.assertEqual(motion_sources, {"07-grounded-motion-sheet-v2.png"})

    def test_package_rejects_graph_hash_count_and_bounds_tampering(self):
        audit_path = (DEFINITIONS / "thorne_vale_extraction_audit.json").resolve()
        original = json.loads(audit_path.read_text(encoding="utf-8"))
        original_read_text = Path.read_text
        mutations = (
            ("pixel_graph_sha256", "0" * 64, "hash differs"),
            ("pixel_node_count", 1, "node count differs"),
            ("bounds", {"left": 0, "top": 0, "right": 0, "bottom": 0}, "bounds differ"),
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
                        load_character_package(THORNE_VALE_PACKAGE_PATH)

    def test_package_rejects_source_canonical_and_worksheet_hash_tampering(self):
        manifest_path = (DEFINITIONS / "thorne_vale_character_manifest.json").resolve()
        original = json.loads(manifest_path.read_text(encoding="utf-8"))
        original_read_text = Path.read_text
        cases = (
            ("original_reference_sha256", "source hash differs"),
            ("canonical_reference_sha256", "source hash differs"),
        )
        for hash_name, message in cases:
            with self.subTest(hash_name=hash_name):
                tampered = json.loads(json.dumps(original))
                tampered["hashes"][hash_name] = "0" * 64

                def controlled_read_text(path, *args, **kwargs):
                    if path.resolve() == manifest_path:
                        return json.dumps(tampered)
                    return original_read_text(path, *args, **kwargs)

                with patch.object(Path, "read_text", new=controlled_read_text):
                    with self.assertRaisesRegex(CharacterPackageValidationError, message):
                        load_character_package(THORNE_VALE_PACKAGE_PATH)
        tampered = json.loads(json.dumps(original))
        tampered["hashes"]["worksheet_sha256"]["01-identity-sheet-v3.png"] = "0" * 64

        def controlled_read_text(path, *args, **kwargs):
            if path.resolve() == manifest_path:
                return json.dumps(tampered)
            return original_read_text(path, *args, **kwargs)

        with patch.object(Path, "read_text", new=controlled_read_text):
            with self.assertRaisesRegex(CharacterPackageValidationError, "worksheet hash differs"):
                load_character_package(THORNE_VALE_PACKAGE_PATH)

    def test_package_rejects_every_immutable_and_generated_asset_tamper(self):
        persona = ROOT / "assets/reference/personas/thorne-vale"
        manifest = json.loads(
            (DEFINITIONS / "thorne_vale_character_manifest.json").read_text(encoding="utf-8")
        )
        targets = [
            PROFILE,
            persona / "source-reference.png",
            persona / "canonical-voxel.png",
            THORNE_VALE_PACKAGE_PATH,
            DEFINITIONS / "thorne_vale_runtime_profile.json",
            DEFINITIONS / "thorne_vale_animation_graph.json",
            DEFINITIONS / "thorne_vale_animation_matrix.json",
            DEFINITIONS / "thorne_vale_pose_cells.json",
            DEFINITIONS / "thorne_vale_extraction_audit.json",
            DEFINITIONS / "thorne_vale_pixel_graphs.json",
            *(
                persona / "canonical-worksheets" / filename
                for filename in manifest["hashes"]["worksheet_sha256"]
            ),
        ]
        original_read_bytes = Path.read_bytes
        for target in targets:
            resolved = target.resolve()
            with self.subTest(target=target.name):
                def controlled_read_bytes(path, *args, **kwargs):
                    payload = original_read_bytes(path, *args, **kwargs)
                    return payload + b"tampered" if path.resolve() == resolved else payload

                with patch.object(Path, "read_bytes", new=controlled_read_bytes):
                    with self.assertRaisesRegex(
                        CharacterPackageValidationError,
                        "hash differs|worksheet hash differs",
                    ):
                        load_character_package(THORNE_VALE_PACKAGE_PATH)

    def test_identity_and_signature_vocabulary_are_locked(self):
        package = load_character_package(THORNE_VALE_PACKAGE_PATH)
        manifest = json.loads(package.manifest.read_text(encoding="utf-8"))
        immutable = set(manifest["identity_lock"]["immutable"])
        self.assertTrue(
            {
                "tall bright-gold crenellated crown",
                "rectangular green eyes",
                "thick dark-brown mustache",
                "bright-gold knee-length jacket",
                "straight gray sword",
                "rolled tan policy parchment",
            }.issubset(immutable)
        )
        production_text = " ".join(
            (DEFINITIONS / filename).read_text(encoding="utf-8").lower()
            for filename in (
                "thorne_vale_pose_cells.json",
                "thorne_vale_animation_graph.json",
                "thorne_vale_runtime_profile.json",
                "thorne_vale_character_manifest.json",
            )
        )
        self.assertNotIn("cigar", production_text)
        self.assertNotIn("smoke", production_text)
        poses = {
            pose["id"]
            for pose in json.loads(package.pose_library.read_text(encoding="utf-8"))["poses"]
        }
        for arc in ("decision_rights", "tradeoff", "risk_review", "incentive"):
            for phase in ("anticipation", "action", "follow_through", "recovery"):
                self.assertIn("{}_{}".format(arc, phase), poses)

    def test_semantic_thorne_actions_are_runtime_addressable(self):
        source = self.make_source()
        expected = {
            "sword_upright": "decision_rights_action",
            "sword_guard_low": "decision_rights_recovery",
            "parchment_read": "risk_review_anticipation",
            "policy_present": "tradeoff_action",
            "decision_rights": "decision_rights_action",
            "tradeoff_compare": "tradeoff_action",
            "risk_review": "risk_review_action",
            "incentive_analysis": "incentive_action",
            "guarded_approval": "incentive_recovery",
        }
        for action, pose_id in expected.items():
            with self.subTest(action=action):
                result = source.apply_command_sync(
                    WizardCommand("action", {"action": action, "duration_ms": 900})
                )
                self.assertTrue(result.ok, result.message)
                source.render_current_frame()
                self.assertEqual(source.current_state().pose_id, pose_id)

    def test_live_motion_expression_speech_and_signature_change_cells(self):
        source = self.make_source()
        idle = source.render_current_frame().cells
        source.apply_command_sync(WizardCommand("move", {"x": 1.5, "z": 5.0, "speed": 1.1}))
        source.advance_simulation(0.35)
        walking = source.render_current_frame().cells
        self.assertNotEqual(idle, walking)
        source.apply_command_sync(WizardCommand("expression", {"expression": "skepticism"}))
        skeptical = source.render_current_frame().cells
        self.assertNotEqual(walking, skeptical)
        source.apply_command_sync(WizardCommand("speak", {"text": "Review the tradeoff.", "duration_ms": 1200}))
        source.advance_simulation(0.15)
        speaking = source.render_current_frame().cells
        self.assertNotEqual(skeptical, speaking)
        source.apply_command_sync(WizardCommand("pose", {"pose_id": "risk_review_action", "duration_ms": 900}))
        reviewed = source.render_current_frame().cells
        self.assertNotEqual(speaking, reviewed)
        self.assertEqual(source.current_state().pose_id, "risk_review_action")

    def test_feature_donors_are_audited_but_not_pose_addressable(self):
        source = self.make_source()
        self.assertNotIn("hand_open_relaxed", source.pose_ids)
        self.assertNotIn("prop_sword_upright", source.pose_ids)
        for pose_id in (
            "interaction_open_hand",
            "interaction_closed_hand",
            "interaction_fist",
            "interaction_reach",
        ):
            result = source.apply_command_sync(
                WizardCommand("pose", {"pose_id": pose_id, "duration_ms": 900})
            )
            self.assertTrue(result.ok)

    def test_runtime_profiles_and_animation_clips_only_target_full_body_graphs(self):
        package = load_character_package(THORNE_VALE_PACKAGE_PATH)
        payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        full_body = {
            pose["id"] for pose in payload["poses"]
            if pose["graph_kind"] == "full_body_graph"
        }
        features = {
            pose["id"] for pose in payload["poses"]
            if pose["graph_kind"] == "feature_graph"
        }
        self.assertEqual(len(full_body), 92)
        self.assertEqual(len(features), 16)
        source = self.make_source()
        self.assertEqual(set(source.pose_ids), full_body)
        self.assertTrue(features.isdisjoint(source.pose_ids))

        profile = json.loads(package.runtime_profile.read_text(encoding="utf-8"))
        profile_targets = set(profile["facing_poses"].values())
        profile_targets.update(profile["action_poses"].values())
        profile_targets.update(profile["walking_cycle"])
        profile_targets.update(profile["running_cycle"])
        profile_targets.update(profile["speech_poses"])
        profile_targets.update(profile["blink_poses"].values())
        profile_targets.update(
            "expression_{}".format(value)
            for value in profile["expression_aliases"].values()
        )
        self.assertTrue(profile_targets.issubset(full_body))

        graph = json.loads(package.animation_graph.read_text(encoding="utf-8"))
        clip_targets = {
            sample["pose_id"]
            for clip in graph["clips"]
            for sample in clip["samples"]
        }
        self.assertTrue(clip_targets.issubset(full_body))

    def test_runtime_render_never_decodes_png_or_svg(self):
        with patch("PIL.Image.open", side_effect=AssertionError("runtime image access")):
            source = self.make_source()
            frame = source.render_current_frame()
        self.assertEqual(len(frame.cells), frame.cols * frame.rows * 4)

    def test_live_rest_and_websocket_routes_stream_thorne(self):
        app = create_app(cols=96, rows=64, fps=24.0)
        by_path = {route.path: route.endpoint for route in app.routes}

        class OneFrameWebSocket:
            def __init__(self):
                self.accepted = False
                self.text = []
                self.frames = []

            async def accept(self):
                self.accepted = True

            async def send_text(self, value):
                self.text.append(value)

            async def send_bytes(self, value):
                self.frames.append(value)
                raise RuntimeError("one live frame captured")

            async def receive_text(self):
                await asyncio.Future()

            async def close(self, code):  # pragma: no cover - success path.
                raise AssertionError(code)

        async def exercise():
            listing = await by_path["/api/avatar/characters"]()
            ids = {item["character_id"] for item in listing["characters"]}
            self.assertIn("thorne-vale-v1", ids)
            state = await by_path["/api/avatar/{character_id}/{command_type}"](
                "thorne-vale-v1",
                "action",
                {"action": "decision_rights", "duration_ms": 900},
            )
            self.assertEqual(state["action"], "decision_rights")
            static = await by_path["/avatar/characters/{character_id}/{asset_name}"](
                "thorne-vale-v1", "extraction-audit"
            )
            self.assertEqual(
                json.loads(Path(static.path).read_text(encoding="utf-8"))["item_count"],
                124,
            )
            websocket = OneFrameWebSocket()
            await asyncio.wait_for(
                by_path["/ws/avatar/{character_id}"](websocket, "thorne-vale-v1"),
                timeout=2.0,
            )
            self.assertTrue(websocket.accepted)
            self.assertTrue(websocket.text[0].startswith("INIT:24.0"))
            self.assertGreater(len(websocket.frames[0]), 20)

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
