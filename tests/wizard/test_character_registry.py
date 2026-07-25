import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from wizard_avatar.artifact_hashing import canonical_json_v1, sha256_ref
from wizard_avatar.character_registry import (
    CharacterAdmissionV1,
    CharacterRegistry,
    CharacterRegistryValidationError,
    load_character_registry,
)
from wizard_avatar.character_package import animation_graph_path_for


class CharacterRegistryTests(unittest.TestCase):
    def test_registry_cannot_be_self_issued_by_direct_construction(self):
        with self.assertRaisesRegex(
            CharacterRegistryValidationError,
            "load_character_registry",
        ):
            CharacterRegistry(
                schema_version=2,
                default_character_id="self-issued",
                packages={},
                admissions={},
                persona_characters={},
            )

    def test_production_registry_defaults_to_verified_wizard_package(self):
        registry = load_character_registry()

        self.assertEqual(registry.schema_version, 2)
        self.assertEqual(registry.default_character_id, "wizard-joe-v1")
        self.assertEqual(tuple(registry.packages), ("wizard-joe-v1",))
        package = registry.get("wizard-joe-v1")
        admission = registry.admission_for_character("wizard-joe-v1")
        self.assertEqual(admission.persona_id, "persona:wizard-joe")
        self.assertEqual(
            registry.admission_for_persona("persona:wizard-joe"),
            admission,
        )
        self.assertEqual(
            registry.resolve_admission(
                "wizard-joe-v1",
                package.package_sha256,
            ),
            admission,
        )
        self.assertIsNone(
            registry.resolve_admission(
                "wizard-joe-v1",
                "sha256:" + "0" * 64,
            )
        )
        self.assertEqual(package.display_name, "Wizard Joe")
        self.assertEqual(
            registry.public_entries(),
            (
                {
                    "character_id": "wizard-joe-v1",
                    "persona_id": "persona:wizard-joe",
                    "display_name": "Wizard Joe",
                    "renderer": "asciline_square_cells",
                    "renderer_adapter_id": "asciline.legacy_square_cells.v1",
                    "runtime_api": {"min": 1, "max": 1},
                    "package_sha256": package.package_sha256,
                    "admission_sha256": admission.admission_sha256,
                    "runtime_admitted": True,
                    "default_pose_id": package.default_pose_id,
                    "capabilities": package.capabilities,
                },
            ),
        )
        self.assertEqual(
            animation_graph_path_for("wizard-joe-v1"),
            package.animation_graph,
        )

    def test_python_v2_binding_fixture_is_canonically_hash_sealed(self):
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "performance_binding_v2_python.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        admission = fixture["admission"]
        binding_content = dict(fixture)
        binding_sha256 = binding_content.pop("binding_sha256")

        self.assertEqual(
            fixture["admission_sha256"],
            sha256_ref(canonical_json_v1(admission)),
        )
        self.assertEqual(
            binding_sha256,
            sha256_ref(canonical_json_v1(binding_content)),
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

    def test_v1_registry_rejects_noncanonical_wizard_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_minimal_package(root, "wizard-joe-v1")
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "default_character_id": "wizard-joe-v1",
                        "characters": [
                            {
                                "character_id": "wizard-joe-v1",
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
                "frozen wizard-joe-v1 package",
            ):
                load_character_registry(registry_path)

    def test_v1_registry_accepts_only_the_frozen_wizard_package(self):
        definitions = (
            Path(__file__).resolve().parents[2]
            / "wizard_avatar"
            / "definitions"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "wizard_joe_character_package.json",
                "reference_avatar_pose_cells.json",
                "reference_avatar_animation_graph_v2.json",
            ):
                shutil.copy2(definitions / name, root / name)
            package_sha256 = self._package_hash(
                root,
                package_name="wizard_joe_character_package.json",
            )
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "default_character_id": "wizard-joe-v1",
                        "characters": [
                            {
                                "character_id": "wizard-joe-v1",
                                "package": "wizard_joe_character_package.json",
                                "package_sha256": package_sha256,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            registry = load_character_registry(registry_path)
            admission = registry.admission_for_character("wizard-joe-v1")

        self.assertEqual(package_sha256, admission.package_sha256)
        self.assertEqual(admission.persona_id, "persona:wizard-joe")
        self.assertEqual(
            admission.admission_sha256,
            "sha256:d7b23f23ea0c7bda0fafeeb1dfb92d48d60a6ab5ed95e61bc48d232d09cc1199",
        )

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
            / "character_registry_v2.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        pattern = schema["properties"]["characters"]["items"]["properties"][
            "package"
        ]["pattern"]

        self.assertIsNotNone(re.search(pattern, "wizard/package.json"))
        self.assertIsNone(re.search(pattern, "/tmp/package.json"))
        self.assertIsNone(re.search(pattern, r"C:\package.json"))
        self.assertIsNone(re.search(pattern, r"\\server\package.json"))

    def test_registry_rejects_tampered_admission_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_minimal_package(root, "bound-character")
            package_sha256 = self._package_hash(root)
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "default_character_id": "bound-character",
                        "characters": [
                            {
                                "character_id": "bound-character",
                                "persona_id": "persona:bound-character",
                                "package": "package.json",
                                "package_sha256": package_sha256,
                                "admission_sha256": "sha256:" + "0" * 64,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CharacterRegistryValidationError,
                "admission hash",
            ):
                load_character_registry(registry_path)

    def test_registry_rejects_duplicate_persona_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_minimal_package(root, "first-character")
            first_package = root / "package.json"
            second_root = root / "second"
            second_root.mkdir()
            self._write_minimal_package(second_root, "second-character")
            first_hash = sha256_ref(first_package.read_bytes())
            second_hash = sha256_ref((second_root / "package.json").read_bytes())
            entries = []
            for character_id, package_path, package_sha256 in (
                ("first-character", "package.json", first_hash),
                ("second-character", "second/package.json", second_hash),
            ):
                admission = CharacterAdmissionV1.build(
                    persona_id="persona:shared",
                    character_id=character_id,
                    package_sha256=package_sha256,
                )
                entries.append(
                    {
                        "character_id": character_id,
                        "persona_id": admission.persona_id,
                        "package": package_path,
                        "package_sha256": package_sha256,
                        "admission_sha256": admission.admission_sha256,
                    }
                )
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "default_character_id": "first-character",
                        "characters": entries,
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CharacterRegistryValidationError,
                "duplicate persona_id",
            ):
                load_character_registry(registry_path)

    @staticmethod
    def _package_hash(root: Path, package_name: str = "package.json") -> str:
        return sha256_ref((root / package_name).read_bytes())

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
