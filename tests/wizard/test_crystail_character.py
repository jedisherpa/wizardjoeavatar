import hashlib
import json
import unittest
from pathlib import Path

from wizard_avatar.character_package import CRYSTAIL_PACKAGE_PATH, load_character_package
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.crystail import CRYSTAIL_POSE_IDS
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.server import create_app


ROOT = Path(__file__).resolve().parents[2]


class CrystailCharacterTests(unittest.TestCase):
    def make_source(self):
        return ProceduralWizardFrameSource(
            cols=160,
            rows=100,
            character_package_path=CRYSTAIL_PACKAGE_PATH,
        )

    def test_registry_exposes_both_characters(self):
        registry = load_character_registry()
        self.assertEqual(registry.default_character_id, "wizard-joe-v1")
        self.assertEqual(set(registry.packages), {"wizard-joe-v1", "crystail-v1"})
        self.assertEqual(registry.get("crystail-v1").display_name, "CrystAIl")

    def test_package_has_full_runtime_capabilities_and_pose_library(self):
        package = load_character_package(CRYSTAIL_PACKAGE_PATH)
        self.assertIn("speech_visemes", package.capabilities)
        self.assertIn("containment_recovery", package.capabilities)
        self.assertEqual(len(CRYSTAIL_POSE_IDS), 63)
        payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        self.assertEqual(len(payload["poses"]), len(CRYSTAIL_POSE_IDS))

    def test_original_reference_is_preserved_byte_for_byte(self):
        original = ROOT / "assets" / "reference" / "crystail" / "original-reference.png"
        self.assertEqual(
            hashlib.sha256(original.read_bytes()).hexdigest(),
            "ca4a5d93e89191d271768f2be0c298cbe68226858a47bf755863f1ed9362b585",
        )

    def test_runtime_pose_retains_worksheet_color_and_voxel_detail(self):
        package = load_character_package(CRYSTAIL_PACKAGE_PATH)
        payload = json.loads(package.pose_library.read_text(encoding="utf-8"))
        pose = next(item for item in payload["poses"] if item["id"] == "neutral_front")
        colors = {tuple(cell["rgb"]) for cell in pose["cells"]}
        self.assertGreater(len(pose["cells"]), 850)
        self.assertGreater(len(colors), 160)
        self.assertIn("canonical-worksheets", pose["source"])
        self.assertTrue(any(r > g * 1.3 and r > b * 1.8 for r, g, b in colors))
        self.assertTrue(any(b > r * 1.2 and b > g * 0.8 for r, g, b in colors))

    def test_motion_expression_speech_and_containment_change_live_cells(self):
        source = self.make_source()
        idle = source.render_current_frame().cells
        source.apply_command_sync(WizardCommand("move", {"x": 2.0, "z": 5.0, "speed": 1.2}))
        source.advance_simulation(0.35)
        walking = source.render_current_frame().cells
        self.assertNotEqual(idle, walking)
        source.apply_command_sync(WizardCommand("expression", {"expression": "excitement"}))
        excited = source.render_current_frame().cells
        self.assertNotEqual(walking, excited)
        source.apply_command_sync(WizardCommand("speak", {"text": "I have an idea!", "duration_ms": 2000}))
        source.advance_simulation(0.12)
        speaking = source.render_current_frame().cells
        self.assertNotEqual(excited, speaking)
        result = source.apply_command_sync(WizardCommand("action", {"action": "containment", "duration_ms": 900}))
        self.assertTrue(result.ok)
        contained = source.render_current_frame().cells
        self.assertNotEqual(speaking, contained)

    def test_server_registers_character_scoped_routes(self):
        app = create_app(self.make_source())
        paths = {route.path for route in app.routes}
        self.assertIn("/api/avatar/characters", paths)
        self.assertIn("/api/avatar/{character_id}/state", paths)
        self.assertIn("/api/avatar/{character_id}/{command_type}", paths)
        self.assertIn("/ws/avatar/{character_id}", paths)


if __name__ == "__main__":
    unittest.main()
