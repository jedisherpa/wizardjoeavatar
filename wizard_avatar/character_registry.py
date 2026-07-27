from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional, Tuple

from .artifact_hashing import canonical_json_v1, sha256_ref
from .character_package import (
    CharacterPackage,
    load_character_package,
    replace_admitted_character_packages,
)


DEFINITIONS_DIR = Path(__file__).with_name("definitions")
CHARACTER_REGISTRY_PATH = DEFINITIONS_DIR / "character_registry.json"
_SHA256_REF = re.compile(r"^sha256:[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_LEGACY_WIZARD_CHARACTER_ID = "wizard-joe-v1"
_LEGACY_WIZARD_PERSONA_ID = "persona:wizard-joe"
_LEGACY_WIZARD_PACKAGE_SHA256 = (
    "sha256:e35d9fee572e8f984a25a3776e2be51e1920b2a09f568170f12ccd3f0851b387"
)


class CharacterRegistryValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CharacterAdmissionV1:
    schema_version: int
    persona_id: str
    character_id: str
    package_sha256: str
    admission_sha256: str

    @classmethod
    def build(
        cls,
        *,
        persona_id: str,
        character_id: str,
        package_sha256: str,
    ) -> "CharacterAdmissionV1":
        content = {
            "schema_version": 1,
            "persona_id": persona_id,
            "character_id": character_id,
            "package_digest": package_sha256,
        }
        return cls(
            schema_version=1,
            persona_id=persona_id,
            character_id=character_id,
            package_sha256=package_sha256,
            admission_sha256=sha256_ref(canonical_json_v1(content)),
        )

    def validate(self) -> None:
        if self.schema_version != 1 or isinstance(self.schema_version, bool):
            raise CharacterRegistryValidationError(
                "character admission schema_version must be 1"
            )
        for name, value in (
            ("persona_id", self.persona_id),
            ("character_id", self.character_id),
        ):
            if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
                raise CharacterRegistryValidationError(
                    "character admission {} must be a valid identifier".format(name)
                )
        for name, value in (
            ("package_sha256", self.package_sha256),
            ("admission_sha256", self.admission_sha256),
        ):
            if not isinstance(value, str) or _SHA256_REF.fullmatch(value) is None:
                raise CharacterRegistryValidationError(
                    "character admission {} must be a lowercase SHA-256 reference".format(
                        name
                    )
                )
        if self.admission_sha256 != self.computed_admission_sha256():
            raise CharacterRegistryValidationError(
                "character admission hash does not match canonical content"
            )

    def content_dict(self) -> Mapping[str, object]:
        return {
            "schema_version": self.schema_version,
            "persona_id": self.persona_id,
            "character_id": self.character_id,
            "package_digest": self.package_sha256,
        }

    def computed_admission_sha256(self) -> str:
        return sha256_ref(canonical_json_v1(self.content_dict()))

    def to_dict(self) -> Mapping[str, object]:
        return {
            **self.content_dict(),
            "admission_sha256": self.admission_sha256,
        }


_REGISTRY_CONSTRUCTION_SEAL = object()


@dataclass(frozen=True, init=False)
class CharacterRegistry:
    schema_version: int
    default_character_id: str
    packages: Mapping[str, CharacterPackage]
    admissions: Mapping[str, CharacterAdmissionV1]
    persona_characters: Mapping[str, str]

    def __init__(
        self,
        *,
        schema_version: int,
        default_character_id: str,
        packages: Mapping[str, CharacterPackage],
        admissions: Mapping[str, CharacterAdmissionV1],
        persona_characters: Mapping[str, str],
        _construction_seal: object = None,
    ) -> None:
        if _construction_seal is not _REGISTRY_CONSTRUCTION_SEAL:
            raise CharacterRegistryValidationError(
                "character registries must be created by load_character_registry"
            )
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "default_character_id", default_character_id)
        object.__setattr__(self, "packages", packages)
        object.__setattr__(self, "admissions", admissions)
        object.__setattr__(self, "persona_characters", persona_characters)

    def get(self, character_id: str) -> CharacterPackage:
        try:
            return self.packages[character_id]
        except KeyError as exc:
            raise CharacterRegistryValidationError(
                "unknown character_id: {}".format(character_id)
            ) from exc

    def admission_for_character(self, character_id: str) -> CharacterAdmissionV1:
        try:
            return self.admissions[character_id]
        except KeyError as exc:
            raise CharacterRegistryValidationError(
                "character is not runtime-admitted: {}".format(character_id)
            ) from exc

    def admission_for_persona(self, persona_id: str) -> CharacterAdmissionV1:
        try:
            character_id = self.persona_characters[persona_id]
        except KeyError as exc:
            raise CharacterRegistryValidationError(
                "persona is not runtime-admitted: {}".format(persona_id)
            ) from exc
        return self.admissions[character_id]

    def resolve_admission(
        self,
        character_id: str,
        package_sha256: str,
    ) -> Optional[CharacterAdmissionV1]:
        admission = self.admissions.get(character_id)
        if admission is None or admission.package_sha256 != package_sha256:
            return None
        return admission

    def public_entries(self) -> Tuple[Mapping[str, Any], ...]:
        return tuple(
            {
                "character_id": package.character_id,
                "persona_id": self.admissions[package.character_id].persona_id,
                "display_name": package.display_name,
                "renderer": package.renderer,
                "renderer_adapter_id": package.renderer_adapter_id,
                "runtime_api": {
                    "min": package.runtime_api_min,
                    "max": package.runtime_api_max,
                },
                "package_sha256": package.package_sha256,
                "admission_sha256": (
                    self.admissions[package.character_id].admission_sha256
                ),
                "runtime_admitted": True,
                "default_pose_id": package.default_pose_id,
                "capabilities": package.capabilities,
            }
            for package in self.packages.values()
        )


def load_character_registry(
    path: Path = CHARACTER_REGISTRY_PATH,
) -> CharacterRegistry:
    registry_path = Path(path).resolve()
    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CharacterRegistryValidationError(str(exc)) from exc
    if not isinstance(raw, Mapping):
        raise CharacterRegistryValidationError("character registry must be an object")
    required = {"schema_version", "default_character_id", "characters"}
    unknown = sorted(set(raw) - required)
    missing = sorted(required - set(raw))
    if unknown or missing:
        raise CharacterRegistryValidationError(
            "invalid registry fields; missing={} unknown={}".format(missing, unknown)
        )
    if raw["schema_version"] not in (1, 2) or isinstance(raw["schema_version"], bool):
        raise CharacterRegistryValidationError("schema_version must be 1 or 2")
    schema_version = raw["schema_version"]
    default_character_id = raw["default_character_id"]
    if not isinstance(default_character_id, str) or not default_character_id:
        raise CharacterRegistryValidationError(
            "default_character_id must be non-empty text"
        )
    characters = raw["characters"]
    if not isinstance(characters, list) or not characters:
        raise CharacterRegistryValidationError("characters must be a non-empty array")

    packages: dict[str, CharacterPackage] = {}
    admissions: dict[str, CharacterAdmissionV1] = {}
    persona_characters: dict[str, str] = {}
    for index, entry in enumerate(characters):
        if not isinstance(entry, Mapping):
            raise CharacterRegistryValidationError(
                "characters[{}] must be an object".format(index)
            )
        expected_fields = (
            {"character_id", "package", "package_sha256"}
            if schema_version == 1
            else {
                "character_id",
                "persona_id",
                "package",
                "package_sha256",
                "admission_sha256",
            }
        )
        if set(entry) != expected_fields:
            raise CharacterRegistryValidationError(
                "characters[{}] fields do not match registry schema_version {}".format(
                    index, schema_version
                )
            )
        character_id = entry["character_id"]
        package_name = entry["package"]
        package_sha256 = entry["package_sha256"]
        if not isinstance(character_id, str) or not character_id:
            raise CharacterRegistryValidationError(
                "characters[{}].character_id must be non-empty text".format(index)
            )
        if (
            not isinstance(package_sha256, str)
            or _SHA256_REF.fullmatch(package_sha256) is None
        ):
            raise CharacterRegistryValidationError(
                "characters[{}].package_sha256 must be a lowercase SHA-256 reference".format(
                    index
                )
            )
        package_path = _registry_package_path(
            registry_path,
            package_name,
            index,
        )
        package = load_character_package(package_path)
        if not package.runtime_admitted:
            raise CharacterRegistryValidationError(
                "characters[{}] package is review-only and cannot be admitted".format(
                    index
                )
            )
        if package.character_id != character_id:
            raise CharacterRegistryValidationError(
                "characters[{}].character_id does not match package".format(index)
            )
        if package.package_sha256 != package_sha256:
            raise CharacterRegistryValidationError(
                "characters[{}].package_sha256 does not match package bytes".format(
                    index
                )
            )
        if character_id in packages:
            raise CharacterRegistryValidationError(
                "duplicate character_id: {}".format(character_id)
            )
        if schema_version == 1:
            if character_id != _LEGACY_WIZARD_CHARACTER_ID:
                raise CharacterRegistryValidationError(
                    "schema_version 1 supports only wizard-joe-v1"
                )
            if package_sha256 != _LEGACY_WIZARD_PACKAGE_SHA256:
                raise CharacterRegistryValidationError(
                    "schema_version 1 supports only the frozen wizard-joe-v1 package"
                )
            admission = CharacterAdmissionV1.build(
                persona_id=_LEGACY_WIZARD_PERSONA_ID,
                character_id=character_id,
                package_sha256=package_sha256,
            )
        else:
            admission = CharacterAdmissionV1(
                schema_version=1,
                persona_id=entry["persona_id"],
                character_id=character_id,
                package_sha256=package_sha256,
                admission_sha256=entry["admission_sha256"],
            )
            admission.validate()
        if admission.persona_id in persona_characters:
            raise CharacterRegistryValidationError(
                "duplicate persona_id: {}".format(admission.persona_id)
            )
        packages[character_id] = package
        admissions[character_id] = admission
        persona_characters[admission.persona_id] = character_id

    if default_character_id not in packages:
        raise CharacterRegistryValidationError(
            "default_character_id is absent from characters"
        )
    replace_admitted_character_packages(packages)
    return CharacterRegistry(
        schema_version=schema_version,
        default_character_id=default_character_id,
        packages=MappingProxyType(dict(packages)),
        admissions=MappingProxyType(dict(admissions)),
        persona_characters=MappingProxyType(dict(persona_characters)),
        _construction_seal=_REGISTRY_CONSTRUCTION_SEAL,
    )


def _registry_package_path(
    registry_path: Path,
    value: Any,
    index: int,
) -> Path:
    if not isinstance(value, str) or not value:
        raise CharacterRegistryValidationError(
            "characters[{}].package must be a relative path".format(index)
        )
    relative = Path(value)
    if relative.is_absolute():
        raise CharacterRegistryValidationError(
            "characters[{}].package must be a relative path".format(index)
        )
    package_path = (registry_path.parent / relative).resolve()
    if registry_path.parent not in package_path.parents or not package_path.is_file():
        raise CharacterRegistryValidationError(
            "characters[{}].package is outside the registry or missing".format(index)
        )
    return package_path


__all__ = [
    "CHARACTER_REGISTRY_PATH",
    "CharacterAdmissionV1",
    "CharacterRegistry",
    "CharacterRegistryValidationError",
    "load_character_registry",
]
