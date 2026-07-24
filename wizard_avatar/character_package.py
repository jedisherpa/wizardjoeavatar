from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Tuple

from .artifact_hashing import sha256_ref
from .character_runtime_profile import (
    CharacterRuntimeProfile,
    CharacterRuntimeProfileValidationError,
    load_character_runtime_profile_bytes,
)


DEFINITIONS_DIR = Path(__file__).with_name("definitions")
WIZARD_JOE_PACKAGE_PATH = DEFINITIONS_DIR / "wizard_joe_character_package.json"
_ANIMATION_GRAPHS_BY_CHARACTER_ID: Mapping[str, Path] = MappingProxyType({})
_SHA256_REF = re.compile(r"^sha256:[0-9a-f]{64}$")
_ASSET_ROLE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
SUPPORTED_CHARACTER_RUNTIME_API_VERSIONS = frozenset({1})
SUPPORTED_RENDERER_ADAPTER_IDS = frozenset(
    {
        "asciline.legacy_square_cells.v1",
        "asciline.pixel_graph.v1",
    }
)
_V2_REQUIRED_ASSET_ROLES = {
    "animation_graph",
    "capability_manifest",
    "pose_library",
    "pose_manifest",
    "runtime_profile",
}


class CharacterPackageValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CharacterAsset:
    role: str
    path: Path
    sha256: str


@dataclass(frozen=True)
class CharacterPackage:
    schema_version: int
    package_path: Path
    package_sha256: str
    character_id: str
    display_name: str
    renderer: str
    renderer_adapter_id: str
    runtime_api_min: int
    runtime_api_max: int
    assets: Mapping[str, CharacterAsset]
    pose_library: Path
    animation_graph: Path
    pose_manifest: Path | None
    runtime_profile: Path | None
    runtime_profile_contract: CharacterRuntimeProfile | None
    capability_manifest: Path | None
    default_pose_id: str
    capabilities: Tuple[str, ...]


def load_character_package(path: Path = WIZARD_JOE_PACKAGE_PATH) -> CharacterPackage:
    package_path = Path(path).resolve()
    try:
        package_bytes = package_path.read_bytes()
        raw = json.loads(package_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CharacterPackageValidationError(str(exc)) from exc
    if not isinstance(raw, Mapping):
        raise CharacterPackageValidationError("character package must be an object")
    schema_version = raw.get("schema_version")
    if schema_version == 1 and not isinstance(schema_version, bool):
        package = _load_v1_package(package_path, package_bytes, raw)
    elif schema_version == 2 and not isinstance(schema_version, bool):
        package = _load_v2_package(package_path, package_bytes, raw)
    else:
        raise CharacterPackageValidationError("schema_version must be 1 or 2")
    return package


def _load_v1_package(
    package_path: Path,
    package_bytes: bytes,
    raw: Mapping[str, Any],
) -> CharacterPackage:
    required = {
        "schema_version",
        "character_id",
        "display_name",
        "renderer",
        "pose_library",
        "animation_graph",
        "default_pose_id",
        "capabilities",
    }
    unknown = sorted(set(raw) - required)
    missing = sorted(required - set(raw))
    if unknown or missing:
        raise CharacterPackageValidationError(
            "invalid package fields; missing={} unknown={}".format(missing, unknown)
        )
    for name in ("character_id", "display_name", "renderer", "default_pose_id"):
        if not isinstance(raw[name], str) or not raw[name]:
            raise CharacterPackageValidationError("{} must be non-empty text".format(name))
    if raw["renderer"] != "asciline_square_cells":
        raise CharacterPackageValidationError("unsupported renderer")
    capabilities = _capabilities(raw["capabilities"])

    pose_library = _package_asset(package_path, raw["pose_library"], "pose_library")
    animation_graph = _package_asset(package_path, raw["animation_graph"], "animation_graph")
    assets = MappingProxyType(
        {
            "animation_graph": CharacterAsset(
                role="animation_graph",
                path=animation_graph,
                sha256=sha256_ref(animation_graph.read_bytes()),
            ),
            "pose_library": CharacterAsset(
                role="pose_library",
                path=pose_library,
                sha256=sha256_ref(pose_library.read_bytes()),
            ),
        }
    )
    _validate_pose_and_graph(
        raw["default_pose_id"],
        pose_library.read_bytes(),
        animation_graph.read_bytes(),
    )
    return CharacterPackage(
        schema_version=1,
        package_path=package_path,
        package_sha256=sha256_ref(package_bytes),
        character_id=str(raw["character_id"]),
        display_name=str(raw["display_name"]),
        renderer=str(raw["renderer"]),
        renderer_adapter_id="asciline.legacy_square_cells.v1",
        runtime_api_min=1,
        runtime_api_max=1,
        assets=assets,
        pose_library=pose_library,
        animation_graph=animation_graph,
        pose_manifest=None,
        runtime_profile=None,
        runtime_profile_contract=None,
        capability_manifest=None,
        default_pose_id=str(raw["default_pose_id"]),
        capabilities=capabilities,
    )


def _load_v2_package(
    package_path: Path,
    package_bytes: bytes,
    raw: Mapping[str, Any],
) -> CharacterPackage:
    required = {
        "schema_version",
        "character_id",
        "display_name",
        "runtime_api",
        "renderer",
        "renderer_adapter_id",
        "assets",
        "default_pose_id",
        "capabilities",
    }
    unknown = sorted(set(raw) - required)
    missing = sorted(required - set(raw))
    if unknown or missing:
        raise CharacterPackageValidationError(
            "invalid package fields; missing={} unknown={}".format(missing, unknown)
        )
    for name in (
        "character_id",
        "display_name",
        "renderer",
        "renderer_adapter_id",
        "default_pose_id",
    ):
        if not isinstance(raw[name], str) or not raw[name]:
            raise CharacterPackageValidationError("{} must be non-empty text".format(name))
    if raw["renderer"] != "asciline_square_cells":
        raise CharacterPackageValidationError("unsupported renderer")
    if raw["renderer_adapter_id"] not in SUPPORTED_RENDERER_ADAPTER_IDS:
        raise CharacterPackageValidationError(
            "renderer_adapter_id is not supported by this runtime"
        )
    runtime_api = raw["runtime_api"]
    if not isinstance(runtime_api, Mapping) or set(runtime_api) != {"min", "max"}:
        raise CharacterPackageValidationError(
            "runtime_api must contain only min and max"
        )
    runtime_api_min = _positive_integer(runtime_api["min"], "runtime_api.min")
    runtime_api_max = _positive_integer(runtime_api["max"], "runtime_api.max")
    if runtime_api_min > runtime_api_max:
        raise CharacterPackageValidationError(
            "runtime_api.min must not exceed runtime_api.max"
        )
    if not any(
        runtime_api_min <= version <= runtime_api_max
        for version in SUPPORTED_CHARACTER_RUNTIME_API_VERSIONS
    ):
        raise CharacterPackageValidationError(
            "runtime_api does not intersect this runtime's supported versions"
        )
    capabilities = _capabilities(raw["capabilities"])
    assets_raw = raw["assets"]
    if not isinstance(assets_raw, Mapping):
        raise CharacterPackageValidationError("assets must be an object")
    missing_roles = sorted(_V2_REQUIRED_ASSET_ROLES - set(assets_raw))
    if missing_roles:
        raise CharacterPackageValidationError(
            "assets missing required roles: {}".format(", ".join(missing_roles))
        )
    assets: dict[str, CharacterAsset] = {}
    asset_contents: dict[str, bytes] = {}
    resolved_paths: set[Path] = set()
    for role, descriptor in assets_raw.items():
        if not isinstance(role, str) or _ASSET_ROLE.fullmatch(role) is None:
            raise CharacterPackageValidationError(
                "asset roles must use lowercase snake_case identifiers"
            )
        if not isinstance(descriptor, Mapping) or set(descriptor) != {"path", "sha256"}:
            raise CharacterPackageValidationError(
                "assets.{} must contain only path and sha256".format(role)
            )
        asset_path = _package_asset(
            package_path,
            descriptor["path"],
            "assets.{}.path".format(role),
        )
        if asset_path in resolved_paths:
            raise CharacterPackageValidationError(
                "asset path is reused by more than one role"
            )
        resolved_paths.add(asset_path)
        declared_hash = descriptor["sha256"]
        if not isinstance(declared_hash, str) or _SHA256_REF.fullmatch(declared_hash) is None:
            raise CharacterPackageValidationError(
                "assets.{}.sha256 must be a lowercase SHA-256 reference".format(role)
            )
        content = asset_path.read_bytes()
        actual_hash = sha256_ref(content)
        if actual_hash != declared_hash:
            raise CharacterPackageValidationError(
                "assets.{}.sha256 does not match asset bytes".format(role)
            )
        assets[role] = CharacterAsset(
            role=role,
            path=asset_path,
            sha256=actual_hash,
        )
        asset_contents[role] = content

    pose_library = assets["pose_library"].path
    animation_graph = assets["animation_graph"].path
    _validate_pose_and_graph(
        raw["default_pose_id"],
        asset_contents["pose_library"],
        asset_contents["animation_graph"],
    )
    try:
        runtime_profile_contract = load_character_runtime_profile_bytes(
            asset_contents["runtime_profile"]
        )
    except CharacterRuntimeProfileValidationError as exc:
        raise CharacterPackageValidationError(
            "runtime_profile is invalid: {}".format(exc)
        ) from exc
    if runtime_profile_contract.character_id != raw["character_id"]:
        raise CharacterPackageValidationError(
            "runtime_profile character_id does not match package"
        )
    if runtime_profile_contract.default_pose_id != raw["default_pose_id"]:
        raise CharacterPackageValidationError(
            "runtime_profile default_pose_id does not match package"
        )
    pose_ids = _pose_ids(
        json.loads(asset_contents["pose_library"].decode("utf-8"))
    )
    missing_profile_poses = sorted(
        set(runtime_profile_contract.referenced_pose_ids()) - pose_ids
    )
    if missing_profile_poses:
        raise CharacterPackageValidationError(
            "runtime_profile references unknown poses: {}".format(
                ", ".join(missing_profile_poses)
            )
        )
    try:
        from .animation_graph import (
            AnimationGraphValidationError,
            load_animation_graph,
            register_verified_animation_assets,
        )
        from .reference_avatar import register_verified_reference_pose_library

        animation_graph_contract = load_animation_graph(
            animation_graph,
            pose_manifest_path=assets["pose_manifest"].path,
            pose_library_path=pose_library,
            required_anchors=runtime_profile_contract.required_anchors,
            expected_asset_hashes={
                "animation_graph": assets["animation_graph"].sha256,
                "pose_manifest": assets["pose_manifest"].sha256,
                "pose_library": assets["pose_library"].sha256,
            },
            use_cache=False,
        )
        missing_runtime_poses = sorted(
            set(runtime_profile_contract.referenced_pose_ids())
            - animation_graph_contract.selectable_pose_ids()
        )
        if missing_runtime_poses:
            raise CharacterPackageValidationError(
                "runtime_profile references poses absent from graph clips: "
                + ", ".join(missing_runtime_poses)
            )
        register_verified_animation_assets(
            {
                assets["animation_graph"].path: assets[
                    "animation_graph"
                ].sha256,
                assets["pose_manifest"].path: assets[
                    "pose_manifest"
                ].sha256,
                assets["pose_library"].path: assets["pose_library"].sha256,
            }
        )
        register_verified_reference_pose_library(
            assets["pose_library"].path,
            assets["pose_library"].sha256,
        )
    except CharacterPackageValidationError:
        raise
    except (AnimationGraphValidationError, OSError, ValueError) as exc:
        raise CharacterPackageValidationError(
            "animation_graph is not a valid package-owned graph v2: {}".format(exc)
        ) from exc
    return CharacterPackage(
        schema_version=2,
        package_path=package_path,
        package_sha256=sha256_ref(package_bytes),
        character_id=str(raw["character_id"]),
        display_name=str(raw["display_name"]),
        renderer=str(raw["renderer"]),
        renderer_adapter_id=str(raw["renderer_adapter_id"]),
        runtime_api_min=runtime_api_min,
        runtime_api_max=runtime_api_max,
        assets=MappingProxyType(assets),
        pose_library=pose_library,
        animation_graph=animation_graph,
        pose_manifest=assets["pose_manifest"].path,
        runtime_profile=assets["runtime_profile"].path,
        runtime_profile_contract=runtime_profile_contract,
        capability_manifest=assets["capability_manifest"].path,
        default_pose_id=str(raw["default_pose_id"]),
        capabilities=capabilities,
    )


def _validate_pose_and_graph(
    default_pose_id: Any,
    pose_library: bytes,
    animation_graph: bytes,
) -> None:
    try:
        pose_raw = json.loads(pose_library.decode("utf-8"))
        graph_raw = json.loads(animation_graph.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CharacterPackageValidationError(str(exc)) from exc
    pose_ids = _pose_ids(pose_raw)
    if default_pose_id not in pose_ids:
        raise CharacterPackageValidationError("default pose is absent from pose library")
    graph_pose_ids = _graph_pose_ids(graph_raw)
    if not graph_pose_ids.issubset(pose_ids):
        raise CharacterPackageValidationError("animation graph references unknown poses")


def _capabilities(value: Any) -> Tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise CharacterPackageValidationError(
            "capabilities must be a non-empty array"
        )
    if any(not isinstance(item, str) or not item for item in value):
        raise CharacterPackageValidationError(
            "capabilities must contain non-empty text"
        )
    if len(set(value)) != len(value):
        raise CharacterPackageValidationError(
            "capabilities must not contain duplicates"
        )
    return tuple(value)


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CharacterPackageValidationError(
            "{} must be a positive integer".format(name)
        )
    return value


def animation_graph_path_for(character_id: str) -> Path | None:
    """Return the graph selected by the loaded package for ``character_id``."""

    return _ANIMATION_GRAPHS_BY_CHARACTER_ID.get(character_id)


def replace_admitted_character_packages(
    packages: Mapping[str, CharacterPackage],
) -> None:
    """Atomically publish graphs only after a complete registry validates."""

    global _ANIMATION_GRAPHS_BY_CHARACTER_ID
    admitted = {
        character_id: package.animation_graph
        for character_id, package in packages.items()
    }
    _ANIMATION_GRAPHS_BY_CHARACTER_ID = MappingProxyType(admitted)


def _package_asset(package_path: Path, value: Any, name: str) -> Path:
    if not isinstance(value, str) or not value:
        raise CharacterPackageValidationError("{} must be a relative path".format(name))
    relative = Path(value)
    if relative.is_absolute():
        raise CharacterPackageValidationError("{} must be a relative path".format(name))
    asset = (package_path.parent / relative).resolve()
    if package_path.parent not in asset.parents or not asset.is_file():
        raise CharacterPackageValidationError("{} is outside the package or missing".format(name))
    return asset


def _pose_ids(raw: Any) -> set[str]:
    if isinstance(raw, Mapping) and isinstance(raw.get("poses"), Mapping):
        return {str(key) for key in raw["poses"]}
    if isinstance(raw, Mapping) and isinstance(raw.get("poses"), list):
        return {
            str(item.get("pose_id", item.get("id")))
            for item in raw["poses"]
            if isinstance(item, Mapping) and ("pose_id" in item or "id" in item)
        }
    raise CharacterPackageValidationError("pose library does not expose poses")


def _graph_pose_ids(raw: Any) -> set[str]:
    if not isinstance(raw, Mapping):
        raise CharacterPackageValidationError("animation graph does not expose clips")
    clips = raw.get("clips")
    if isinstance(clips, Mapping):
        clip_values = clips.values()
    elif isinstance(clips, list):
        clip_values = clips
    else:
        raise CharacterPackageValidationError("animation graph does not expose clips")
    result: set[str] = set()
    for clip in clip_values:
        if not isinstance(clip, Mapping):
            continue
        for sample in clip.get("samples", []):
            if isinstance(sample, Mapping) and isinstance(sample.get("pose_id"), str):
                result.add(sample["pose_id"])
    return result


__all__ = [
    "CharacterAsset",
    "CharacterPackage",
    "CharacterPackageValidationError",
    "WIZARD_JOE_PACKAGE_PATH",
    "SUPPORTED_CHARACTER_RUNTIME_API_VERSIONS",
    "SUPPORTED_RENDERER_ADAPTER_IDS",
    "animation_graph_path_for",
    "load_character_package",
    "replace_admitted_character_packages",
]
