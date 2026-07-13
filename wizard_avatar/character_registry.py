from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from .character_package import CharacterPackage, load_character_package


DEFINITIONS_DIR = Path(__file__).with_name("definitions")
CHARACTER_REGISTRY_PATH = DEFINITIONS_DIR / "character_registry.json"


@dataclass(frozen=True)
class CharacterRegistry:
    default_character_id: str
    packages: Dict[str, CharacterPackage]

    def get(self, character_id: str) -> CharacterPackage:
        try:
            return self.packages[character_id]
        except KeyError as exc:
            raise ValueError("Unknown character: {}".format(character_id)) from exc

    def public_entries(self) -> Tuple[dict, ...]:
        return tuple(
            {
                "character_id": package.character_id,
                "display_name": package.display_name,
                "renderer": package.renderer,
                "default_pose_id": package.default_pose_id,
                "capabilities": list(package.capabilities),
            }
            for package in self.packages.values()
        )


def load_character_registry(path: Path = CHARACTER_REGISTRY_PATH) -> CharacterRegistry:
    registry_path = Path(path).resolve()
    raw = json.loads(registry_path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError("character registry schema_version must be 1")
    packages: Dict[str, CharacterPackage] = {}
    for entry in raw.get("characters", []):
        package_path = (registry_path.parent / str(entry["package"])).resolve()
        if registry_path.parent not in package_path.parents:
            raise ValueError("character package is outside registry directory")
        package = load_character_package(package_path)
        if package.character_id != entry["character_id"]:
            raise ValueError("registry character_id does not match package")
        if package.character_id in packages:
            raise ValueError("duplicate character_id: {}".format(package.character_id))
        packages[package.character_id] = package
    default_id = str(raw.get("default_character_id", ""))
    if default_id not in packages:
        raise ValueError("default character is absent from registry")
    return CharacterRegistry(default_character_id=default_id, packages=packages)


__all__ = ["CHARACTER_REGISTRY_PATH", "CharacterRegistry", "load_character_registry"]
