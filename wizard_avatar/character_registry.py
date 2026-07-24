from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Tuple

from .character_package import (
    CharacterPackage,
    load_character_package,
    replace_admitted_character_packages,
)


DEFINITIONS_DIR = Path(__file__).with_name("definitions")
CHARACTER_REGISTRY_PATH = DEFINITIONS_DIR / "character_registry.json"
_SHA256_REF = re.compile(r"^sha256:[0-9a-f]{64}$")


class CharacterRegistryValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CharacterRegistry:
    schema_version: int
    default_character_id: str
    packages: Mapping[str, CharacterPackage]

    def get(self, character_id: str) -> CharacterPackage:
        try:
            return self.packages[character_id]
        except KeyError as exc:
            raise CharacterRegistryValidationError(
                "unknown character_id: {}".format(character_id)
            ) from exc

    def public_entries(self) -> Tuple[Mapping[str, Any], ...]:
        return tuple(
            {
                "character_id": package.character_id,
                "display_name": package.display_name,
                "renderer": package.renderer,
                "renderer_adapter_id": package.renderer_adapter_id,
                "runtime_api": {
                    "min": package.runtime_api_min,
                    "max": package.runtime_api_max,
                },
                "package_sha256": package.package_sha256,
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
    if raw["schema_version"] != 1 or isinstance(raw["schema_version"], bool):
        raise CharacterRegistryValidationError("schema_version must be 1")
    default_character_id = raw["default_character_id"]
    if not isinstance(default_character_id, str) or not default_character_id:
        raise CharacterRegistryValidationError(
            "default_character_id must be non-empty text"
        )
    characters = raw["characters"]
    if not isinstance(characters, list) or not characters:
        raise CharacterRegistryValidationError("characters must be a non-empty array")

    packages: dict[str, CharacterPackage] = {}
    for index, entry in enumerate(characters):
        if not isinstance(entry, Mapping):
            raise CharacterRegistryValidationError(
                "characters[{}] must be an object".format(index)
            )
        if set(entry) != {"character_id", "package", "package_sha256"}:
            raise CharacterRegistryValidationError(
                "characters[{}] must contain character_id, package, and package_sha256".format(
                    index
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
        packages[character_id] = package

    if default_character_id not in packages:
        raise CharacterRegistryValidationError(
            "default_character_id is absent from characters"
        )
    replace_admitted_character_packages(packages)
    return CharacterRegistry(
        schema_version=1,
        default_character_id=default_character_id,
        packages=MappingProxyType(dict(packages)),
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
    "CharacterRegistry",
    "CharacterRegistryValidationError",
    "load_character_registry",
]
