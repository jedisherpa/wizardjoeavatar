import json
import re
import tempfile
import unittest
from pathlib import Path

from wizard_avatar.artifact_hashing import sha256_ref
from wizard_avatar.character_registry import (
    CharacterRegistryValidationError,
    load_character_registry,
)
from wizard_avatar.character_package import animation_graph_path_for


class CharacterRegistryTests(unittest.TestCase):
    def test_production_registry_defaults_to_verified_wizard_package(self):
        registry = load_character_registry()

        self.assertEqual(registry.schema_version, 1)
        self.assertEqual(registry.default_character_id, "wizard-joe-v1")
        self.assertEqual(tuple(registry.packages), ("wizard-joe-v1",))
        package = registry.get("wizard-joe-v1")
        self.assertEqual(package.display_name, "Wizard Joe")
        self.assertEqual(
            registry.public_entries(),
            (
                {
                    "character_id": "wizard-joe-v1",
                    "display_name": "Wizard Joe",
                    "renderer": "asciline_square_cells",
                    "renderer_adapter_id": "asciline.legacy_square_cells.v1",
                    "runtime_api": {"min": 1, "max": 1},
                    "package_sha256": package.package_sha256,
                    "default_pose_id": package.default_pose_id,
                    "capabilities": package.capabilities,
                },
            ),
        )
        self.assertEqual(
            animation_graph_path_for("wizard-joe-v1"),
            package.animation_graph,
        )

    def test_unknown_character_fails_closed(self):
        registry = load_character_registry()

        with self.assertRaisesRegex(
            CharacterRegistryValidationError,
            "unknown character_id",
        ):
            registry.get("unverified-character")

    def test_registry_rejects_character_package_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_minimal_package(root, "actual-character")
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "default_character_id": "declared-character",
                        "characters": [
                            {
                                "character_id": "declared-character",
                                "package": "package.json",
                                "package_sha256": self._package_hash(root),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CharacterRegistryValidationError,
                "does not match package",
            ):
                load_character_registry(registry_path)

    def test_registry_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "default_character_id": "escaped",
                        "characters": [
                            {
                                "character_id": "escaped",
                                "package": "../package.json",
                                "package_sha256": "sha256:" + "0" * 64,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CharacterRegistryValidationError,
                "outside the registry or missing",
            ):
                load_character_registry(registry_path)

    def test_registry_rejects_package_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_minimal_package(root, "bound-character")
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "default_character_id": "bound-character",
                        "characters": [
                            {
                                "character_id": "bound-character",
                                "package": "package.json",
                                "package_sha256": "sha256:" + "0" * 64,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CharacterRegistryValidationError,
                "does not match package bytes",
            ):
                load_character_registry(registry_path)
            self.assertIsNone(animation_graph_path_for("bound-character"))

    def test_registry_rejects_absolute_package_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_minimal_package(root, "absolute-character")
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "default_character_id": "absolute-character",
                        "characters": [
                            {
                                "character_id": "absolute-character",
                                "package": str((root / "package.json").resolve()),
                                "package_sha256": self._package_hash(root),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CharacterRegistryValidationError,
                "must be a relative path",
            ):
                load_character_registry(registry_path)

    def test_registry_mapping_is_immutable(self):
        registry = load_character_registry()

        with self.assertRaises(TypeError):
            registry.packages["unvalidated"] = registry.get("wizard-joe-v1")

    def test_registry_schema_rejects_absolute_package_paths(self):
        schema_path = (
            Path(__file__).resolve().parents[2]
            / "wizard_avatar"
            / "definitions"
            / "character_registry_v1.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        pattern = schema["properties"]["characters"]["items"]["properties"][
            "package"
        ]["pattern"]

        self.assertIsNotNone(re.search(pattern, "wizard/package.json"))
        self.assertIsNone(re.search(pattern, "/tmp/package.json"))
        self.assertIsNone(re.search(pattern, r"C:\package.json"))
        self.assertIsNone(re.search(pattern, r"\\server\package.json"))

    @staticmethod
    def _package_hash(root: Path) -> str:
        return sha256_ref((root / "package.json").read_bytes())

    @staticmethod
    def _write_minimal_package(root: Path, character_id: str) -> None:
        (root / "poses.json").write_text(
            json.dumps(
                {
                    "poses": {
                        "idle": {
                            "description": "idle",
                            "cols": 1,
                            "rows": 1,
                            "root_anchor": [0, 0],
                            "anchors": {"root": [0, 0]},
                            "cells": [{"x": 0, "y": 0, "rgb": [255, 255, 255]}],
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        (root / "graph.json").write_text(
            json.dumps({"clips": [{"samples": [{"pose_id": "idle"}]}]}),
            encoding="utf-8",
        )
        (root / "package.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "character_id": character_id,
                    "display_name": character_id,
                    "renderer": "asciline_square_cells",
                    "pose_library": "poses.json",
                    "animation_graph": "graph.json",
                    "default_pose_id": "idle",
                    "capabilities": ["idle"],
                }
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
