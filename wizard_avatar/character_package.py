from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Tuple


DEFINITIONS_DIR = Path(__file__).with_name("definitions")
WIZARD_JOE_PACKAGE_PATH = DEFINITIONS_DIR / "wizard_joe_character_package.json"
CRYSTAIL_PACKAGE_PATH = DEFINITIONS_DIR / "crystail_character_package.json"
ORION_VALE_PACKAGE_PATH = DEFINITIONS_DIR / "orion_vale_character_package.json"
ROHAN_SLATE_PACKAGE_PATH = DEFINITIONS_DIR / "rohan_slate_character_package.json"


class CharacterPackageValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CharacterPackage:
    schema_version: int
    character_id: str
    display_name: str
    renderer: str
    pose_library: Path
    animation_graph: Path
    default_pose_id: str
    capabilities: Tuple[str, ...]
    package_path: Path
    runtime_profile: Optional[Path] = None
    manifest: Optional[Path] = None
    animation_matrix: Optional[Path] = None
    extraction_audit: Optional[Path] = None
    pixel_graph_library: Optional[Path] = None


def load_character_package(path: Path = WIZARD_JOE_PACKAGE_PATH) -> CharacterPackage:
    package_path = Path(path).resolve()
    try:
        raw = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CharacterPackageValidationError(str(exc)) from exc
    if not isinstance(raw, Mapping):
        raise CharacterPackageValidationError("character package must be an object")
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
    optional = {
        "runtime_profile", "manifest", "animation_matrix", "extraction_audit",
        "pixel_graph_library",
    }
    unknown = sorted(set(raw) - required - optional)
    missing = sorted(required - set(raw))
    if unknown or missing:
        raise CharacterPackageValidationError(
            "invalid package fields; missing={} unknown={}".format(missing, unknown)
        )
    if raw["schema_version"] != 1 or isinstance(raw["schema_version"], bool):
        raise CharacterPackageValidationError("schema_version must be 1")
    for name in ("character_id", "display_name", "renderer", "default_pose_id"):
        if not isinstance(raw[name], str) or not raw[name]:
            raise CharacterPackageValidationError("{} must be non-empty text".format(name))
    if raw["renderer"] != "asciline_square_cells":
        raise CharacterPackageValidationError("unsupported renderer")
    capabilities = raw["capabilities"]
    if not isinstance(capabilities, list) or not capabilities:
        raise CharacterPackageValidationError("capabilities must be a non-empty array")
    if any(not isinstance(item, str) or not item for item in capabilities):
        raise CharacterPackageValidationError("capabilities must contain non-empty text")

    pose_library = _package_asset(package_path, raw["pose_library"], "pose_library")
    animation_graph = _package_asset(package_path, raw["animation_graph"], "animation_graph")
    pose_raw = json.loads(pose_library.read_text(encoding="utf-8"))
    graph_raw = json.loads(animation_graph.read_text(encoding="utf-8"))
    pose_ids = _pose_ids(pose_raw)
    if raw["default_pose_id"] not in pose_ids:
        raise CharacterPackageValidationError("default pose is absent from pose library")
    graph_pose_ids = _graph_pose_ids(graph_raw)
    if not graph_pose_ids.issubset(pose_ids):
        raise CharacterPackageValidationError("animation graph references unknown poses")
    runtime_profile = None
    if "runtime_profile" in raw:
        runtime_profile = _package_asset(package_path, raw["runtime_profile"], "runtime_profile")
        profile_raw = json.loads(runtime_profile.read_text(encoding="utf-8"))
        if not isinstance(profile_raw, Mapping) or profile_raw.get("schema_version") != 1:
            raise CharacterPackageValidationError("runtime_profile must use schema_version 1")
        if profile_raw.get("character_id") != raw["character_id"]:
            raise CharacterPackageValidationError("runtime_profile character_id does not match package")
    optional_assets = {}
    for name in ("manifest", "animation_matrix", "extraction_audit", "pixel_graph_library"):
        optional_assets[name] = (
            _package_asset(package_path, raw[name], name) if name in raw else None
        )
    if (optional_assets["extraction_audit"] is None) != (
        optional_assets["pixel_graph_library"] is None
    ):
        raise CharacterPackageValidationError(
            "extraction_audit and pixel_graph_library must be supplied together"
        )
    if optional_assets["extraction_audit"] is not None:
        audit_raw = json.loads(
            optional_assets["extraction_audit"].read_text(encoding="utf-8")
        )
        pixel_graph_raw = json.loads(
            optional_assets["pixel_graph_library"].read_text(encoding="utf-8")
        )
        _validate_extraction_audit(
            raw["character_id"], pose_raw, pixel_graph_raw, audit_raw
        )
    if optional_assets["manifest"] is not None:
        _validate_manifest_hashes(
            package_path,
            raw["character_id"],
            optional_assets,
        )
    return CharacterPackage(
        schema_version=1,
        character_id=str(raw["character_id"]),
        display_name=str(raw["display_name"]),
        renderer=str(raw["renderer"]),
        pose_library=pose_library,
        animation_graph=animation_graph,
        default_pose_id=str(raw["default_pose_id"]),
        capabilities=tuple(capabilities),
        package_path=package_path,
        runtime_profile=runtime_profile,
        manifest=optional_assets["manifest"],
        animation_matrix=optional_assets["animation_matrix"],
        extraction_audit=optional_assets["extraction_audit"],
        pixel_graph_library=optional_assets["pixel_graph_library"],
    )


def _package_asset(package_path: Path, value: Any, name: str) -> Path:
    if not isinstance(value, str) or not value:
        raise CharacterPackageValidationError("{} must be a relative path".format(name))
    asset = (package_path.parent / value).resolve()
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


def _validate_extraction_audit(
    character_id: str,
    pose_raw: Any,
    pixel_graph_raw: Any,
    audit_raw: Any,
) -> None:
    """Reject unaudited or altered pixel graphs before runtime pose mapping."""
    if not isinstance(audit_raw, Mapping) or audit_raw.get("schema_version") != 1:
        raise CharacterPackageValidationError("extraction_audit must use schema_version 1")
    if audit_raw.get("character_id") != character_id:
        raise CharacterPackageValidationError("extraction_audit character_id does not match package")
    poses = pose_raw.get("poses") if isinstance(pose_raw, Mapping) else None
    graphs = pixel_graph_raw.get("graphs") if isinstance(pixel_graph_raw, Mapping) else None
    items = audit_raw.get("items")
    if not isinstance(poses, list) or not isinstance(graphs, list) or not isinstance(items, list):
        raise CharacterPackageValidationError("extraction_audit must expose pose items")
    pose_by_id = {
        str(pose.get("id")): pose
        for pose in poses
        if isinstance(pose, Mapping) and isinstance(pose.get("id"), str)
    }
    graph_by_id = {
        str(graph.get("id")): graph
        for graph in graphs
        if isinstance(graph, Mapping) and isinstance(graph.get("id"), str)
    }
    for pose_id, pose in pose_by_id.items():
        if pose_id in graph_by_id:
            raise CharacterPackageValidationError(
                "pixel graph library duplicates runtime pose: {}".format(pose_id)
            )
        graph_by_id[pose_id] = {"id": pose_id, "nodes": pose.get("cells")}
    item_by_id = {
        str(item.get("graph_id")): item
        for item in items
        if isinstance(item, Mapping) and isinstance(item.get("graph_id"), str)
    }
    if set(graph_by_id) != set(item_by_id) or audit_raw.get("item_count") != len(graph_by_id):
        raise CharacterPackageValidationError("extraction_audit does not cover every pixel graph")
    for graph_id, graph in graph_by_id.items():
        item = item_by_id[graph_id]
        if item.get("background_removed") is not True:
            raise CharacterPackageValidationError("pose background removal was not audited")
        if item.get("runtime_format") != "colored_pixel_nodes_json":
            raise CharacterPackageValidationError("unsupported audited runtime format")
        runtime_asset = item.get("runtime_asset")
        if not isinstance(runtime_asset, str) or runtime_asset.lower().endswith((".png", ".svg")):
            raise CharacterPackageValidationError("runtime image assets are forbidden")
        cells = graph.get("nodes")
        compact = json.dumps(cells, separators=(",", ":"), sort_keys=True)
        digest = hashlib.sha256(compact.encode("utf-8")).hexdigest()
        if item.get("pixel_graph_sha256") != digest:
            raise CharacterPackageValidationError(
                "extraction_audit hash differs for graph {}".format(graph_id)
            )
        if item.get("pixel_node_count") != len(cells):
            raise CharacterPackageValidationError(
                "extraction_audit node count differs for graph {}".format(graph_id)
            )
        if not cells:
            raise CharacterPackageValidationError("pixel graph is empty: {}".format(graph_id))
        expected_bounds = {
            "left": min(int(cell["x"]) for cell in cells),
            "top": min(int(cell["y"]) for cell in cells),
            "right": max(int(cell["x"]) for cell in cells),
            "bottom": max(int(cell["y"]) for cell in cells),
        }
        if item.get("bounds") != expected_bounds:
            raise CharacterPackageValidationError(
                "extraction_audit bounds differ for graph {}".format(graph_id)
            )


def _validate_manifest_hashes(
    package_path: Path,
    character_id: str,
    optional_assets: Mapping[str, Optional[Path]],
) -> None:
    """Verify generated production assets before runtime animation mapping."""
    manifest_path = optional_assets["manifest"]
    if manifest_path is None:  # pragma: no cover - guarded by caller.
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping) or manifest.get("schema_version") != 1:
        raise CharacterPackageValidationError("manifest must use schema_version 1")
    if manifest.get("character_id") != character_id:
        raise CharacterPackageValidationError("manifest character_id does not match package")
    hashes = manifest.get("hashes")
    if not isinstance(hashes, Mapping):
        raise CharacterPackageValidationError("manifest hashes must be an object")
    package_raw = json.loads(package_path.read_text(encoding="utf-8"))
    generated = {
        "pose_library_sha256": package_path.parent / package_raw["pose_library"],
        "animation_graph_sha256": package_path.parent / package_raw["animation_graph"],
        "animation_matrix_sha256": optional_assets["animation_matrix"],
        "extraction_audit_sha256": optional_assets["extraction_audit"],
        "pixel_graph_library_sha256": optional_assets["pixel_graph_library"],
    }
    for hash_name, asset_path in generated.items():
        if asset_path is None:
            continue
        actual = hashlib.sha256(asset_path.read_bytes()).hexdigest()
        if hashes.get(hash_name) != actual:
            raise CharacterPackageValidationError(
                "manifest hash differs for {}".format(hash_name)
            )
    audit_path = optional_assets["extraction_audit"]
    if audit_path is not None:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        if hashes.get("extraction_item_count") != audit.get("item_count"):
            raise CharacterPackageValidationError("manifest extraction count differs")
    derivation = manifest.get("derivation")
    if not isinstance(derivation, Mapping):
        raise CharacterPackageValidationError("manifest derivation must be an object")
    repository_root = package_path.parent.parent.parent
    source_assets = {
        "generation_profile_sha256": derivation.get("generation_profile"),
        "original_reference_sha256": derivation.get("original_reference"),
        "canonical_reference_sha256": derivation.get("canonical_reference"),
    }
    for hash_name, relative_name in source_assets.items():
        if relative_name is None and hash_name == "generation_profile_sha256":
            # Legacy packages did not name their build profile. Their generated
            # assets are still checked above; new direct-cell packages name it.
            continue
        if not isinstance(relative_name, str) or not relative_name:
            raise CharacterPackageValidationError("manifest source path is invalid")
        source_path = (repository_root / relative_name).resolve()
        if repository_root not in source_path.parents or not source_path.is_file():
            raise CharacterPackageValidationError("manifest source path is outside repository or missing")
        if hashes.get(hash_name) != hashlib.sha256(source_path.read_bytes()).hexdigest():
            raise CharacterPackageValidationError("manifest hash differs for {}".format(hash_name))
    worksheet_hashes = hashes.get("worksheet_sha256")
    worksheet_dir_name = derivation.get("approved_worksheets")
    if worksheet_hashes is not None:
        if not isinstance(worksheet_hashes, Mapping) or not isinstance(worksheet_dir_name, str):
            raise CharacterPackageValidationError("manifest worksheet hashes are invalid")
        worksheet_dir = (repository_root / worksheet_dir_name).resolve()
        if repository_root not in worksheet_dir.parents or not worksheet_dir.is_dir():
            raise CharacterPackageValidationError("manifest worksheet directory is invalid")
        for name, expected_hash in worksheet_hashes.items():
            if not isinstance(name, str) or Path(name).name != name:
                raise CharacterPackageValidationError("manifest worksheet name is invalid")
            worksheet = worksheet_dir / name
            if not worksheet.is_file() or hashlib.sha256(worksheet.read_bytes()).hexdigest() != expected_hash:
                raise CharacterPackageValidationError("manifest hash differs for worksheet {}".format(name))


__all__ = [
    "CharacterPackage",
    "CharacterPackageValidationError",
    "WIZARD_JOE_PACKAGE_PATH",
    "CRYSTAIL_PACKAGE_PATH",
    "ORION_VALE_PACKAGE_PATH",
    "ROHAN_SLATE_PACKAGE_PATH",
    "load_character_package",
]
