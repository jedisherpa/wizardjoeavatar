import json
import tempfile
import unittest
from pathlib import Path

from wizard_avatar.character_package import animation_graph_path_for, load_character_package
from wizard_avatar.frame_source import ProceduralWizardFrameSource


class CharacterPackageTests(unittest.TestCase):
    def test_wizard_package_loads_all_production_assets(self):
        package = load_character_package()
        self.assertEqual(package.character_id, "wizard-joe-v1")
        self.assertIn("flight_locomotion", package.capabilities)
        self.assertTrue(package.pose_library.is_file())
        self.assertEqual(
            animation_graph_path_for(package.character_id),
            package.animation_graph,
        )

    def test_second_character_uses_same_loader_without_runtime_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "poses.json").write_text(
                json.dumps(
                    {
                        "poses": {
                            "idle": {
                                "description": "Second character idle",
                                "cols": 3,
                                "rows": 3,
                                "root_anchor": [1, 2],
                                "anchors": {"root": [1, 2], "mouth": [1, 1]},
                                "cells": [
                                    {"x": 1, "y": 0, "rgb": [22, 190, 120]},
                                    {"x": 0, "y": 1, "rgb": [250, 90, 90]},
                                    {"x": 1, "y": 1, "rgb": [250, 90, 90]},
                                    {"x": 2, "y": 1, "rgb": [250, 90, 90]},
                                ],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (root / "graph.json").write_text(
                json.dumps({"clips": [{"samples": [{"pose_id": "idle"}]}]}), encoding="utf-8"
            )
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "character_id": "second-character",
                        "display_name": "Second Character",
                        "renderer": "asciline_square_cells",
                        "pose_library": "poses.json",
                        "animation_graph": "graph.json",
                        "default_pose_id": "idle",
                        "capabilities": ["ground_locomotion"],
                    }
                ),
                encoding="utf-8",
            )
            package = load_character_package(root / "package.json")
            self.assertEqual(package.character_id, "second-character")
            self.assertEqual(
                animation_graph_path_for("second-character"),
                package.animation_graph,
            )

            source = ProceduralWizardFrameSource(
                cols=64,
                rows=48,
                character_package_path=root / "package.json",
            )
            frame = source.render_next_frame()
            self.assertIsNone(source.animation_graph)
            self.assertEqual(source.current_state().character_id, "second-character")
            self.assertEqual(source.current_state().pose_id, "idle")
            self.assertIn(bytes((ord("#"), 22, 190, 120)), frame.cells)


if __name__ == "__main__":
    unittest.main()
