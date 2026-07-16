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
THORNE_VALE_PACKAGE_PATH = DEFINITIONS_DIR / "thorne_vale_character_package.json"


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
        if optional_assets["manifest"] is None:
            raise CharacterPackageValidationError(
                "audited direct-cell packages require a manifest"
            )
    if optional_assets["manifest"] is not None:
        manifest_raw = json.loads(
            optional_assets["manifest"].read_text(encoding="utf-8")
        )
        _validate_character_manifest(
            package_path,
            raw,
            manifest_raw,
            pose_raw,
            pixel_graph_raw if optional_assets["pixel_graph_library"] is not None else {},
            pose_library,
            animation_graph,
            runtime_profile,
            optional_assets,
            audit_raw if optional_assets["extraction_audit"] is not None else None,
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
    if pixel_graph_raw.get("graph_count") != len(graphs):
        raise CharacterPackageValidationError("pixel graph count differs from graph library")
    if pixel_graph_raw.get("character_id") != character_id:
        raise CharacterPackageValidationError("pixel graph character_id does not match package")
    if pixel_graph_raw.get("encoding") != "transparent_colored_pixel_nodes":
        raise CharacterPackageValidationError("pixel graph encoding is not transparent colored nodes")
    if audit_raw.get("runtime_image_assets") != []:
        raise CharacterPackageValidationError("runtime image assets are forbidden")
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
        if not isinstance(cells, list) or not cells:
            raise CharacterPackageValidationError("pixel graph must contain colored nodes")
        try:
            actual_bounds = {
                "left": min(int(cell["x"]) for cell in cells),
                "top": min(int(cell["y"]) for cell in cells),
                "right": max(int(cell["x"]) for cell in cells),
                "bottom": max(int(cell["y"]) for cell in cells),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise CharacterPackageValidationError("pixel graph contains invalid nodes") from exc
        if item.get("bounds") != actual_bounds:
            raise CharacterPackageValidationError(
                "extraction_audit bounds differ for graph {}".format(graph_id)
            )
        for cell in cells:
            rgb = cell.get("rgb") if isinstance(cell, Mapping) else None
            if (
                not isinstance(rgb, list)
                or len(rgb) != 3
                or any(isinstance(channel, bool) or not isinstance(channel, int) or not 0 <= channel <= 255 for channel in rgb)
            ):
                raise CharacterPackageValidationError("pixel graph contains invalid colors")


def _validate_character_manifest(
    package_path: Path,
    package_raw: Mapping[str, Any],
    manifest_raw: Any,
    pose_raw: Mapping[str, Any],
    pixel_graph_raw: Mapping[str, Any],
    pose_library: Path,
    animation_graph: Path,
    runtime_profile: Optional[Path],
    optional_assets: Mapping[str, Optional[Path]],
    audit_raw: Optional[Mapping[str, Any]],
) -> None:
    """Revalidate the complete approved derivation chain at package load."""
    if not isinstance(manifest_raw, Mapping) or manifest_raw.get("schema_version") != 1:
        raise CharacterPackageValidationError("manifest must use schema_version 1")
    if manifest_raw.get("character_id") != package_raw["character_id"]:
        raise CharacterPackageValidationError("manifest character_id does not match package")
    hashes = manifest_raw.get("hashes")
    derivation = manifest_raw.get("derivation")
    if not isinstance(hashes, Mapping) or not isinstance(derivation, Mapping):
        raise CharacterPackageValidationError("manifest must expose hashes and derivation")
    if derivation.get("flattened_runtime_dependency") is not False:
        raise CharacterPackageValidationError("flattened runtime dependencies are forbidden")

    generated_assets = {
        "character_package_sha256": package_path,
        "pose_library_sha256": pose_library,
        "animation_graph_sha256": animation_graph,
        "runtime_profile_sha256": runtime_profile,
        "animation_matrix_sha256": optional_assets.get("animation_matrix"),
        "extraction_audit_sha256": optional_assets.get("extraction_audit"),
        "pixel_graph_library_sha256": optional_assets.get("pixel_graph_library"),
    }
    for hash_name, asset_path in generated_assets.items():
        if asset_path is None:
            raise CharacterPackageValidationError(
                "manifest asset is missing for {}".format(hash_name)
            )
        if hashes.get(hash_name) != _digest_file(asset_path):
            raise CharacterPackageValidationError(
                "manifest hash differs for {}".format(hash_name)
            )
    if (
        audit_raw is None
        or hashes.get("extraction_item_count") != 124
        or audit_raw.get("item_count") != 124
    ):
        raise CharacterPackageValidationError("manifest extraction count must be exactly 124")

    repository_root = package_path.parents[2]
    source_specs = (
        ("generation_profile", "generation_profile_sha256"),
        ("original_reference", "original_reference_sha256"),
        ("canonical_reference", "canonical_reference_sha256"),
    )
    for derivation_name, hash_name in source_specs:
        source = _repository_asset(repository_root, derivation.get(derivation_name), derivation_name)
        if hashes.get(hash_name) != _digest_file(source):
            raise CharacterPackageValidationError(
                "manifest source hash differs for {}".format(derivation_name)
            )
    worksheet_hashes = hashes.get("worksheet_sha256")
    if not isinstance(worksheet_hashes, Mapping) or not worksheet_hashes:
        raise CharacterPackageValidationError("manifest must hash approved worksheets")
    worksheet_dir = _repository_asset(
        repository_root, derivation.get("approved_worksheets"), "approved_worksheets", directory=True
    )
    audit_items = audit_raw.get("items")
    if not isinstance(audit_items, list) or len(audit_items) != 124:
        raise CharacterPackageValidationError("audit must contain exactly 124 items")
    audited_worksheets: set[str] = set()
    for item in audit_items:
        source_cell = item.get("source_cell") if isinstance(item, Mapping) else None
        if not isinstance(source_cell, str) or "#panel-" not in source_cell:
            raise CharacterPackageValidationError("audit source cell is invalid")
        audited_worksheets.add(source_cell.split("#", 1)[0])
    if set(worksheet_hashes) != audited_worksheets:
        raise CharacterPackageValidationError(
            "manifest worksheet set differs from the 124 audited sources"
        )
    for filename, expected_hash in worksheet_hashes.items():
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise CharacterPackageValidationError("approved worksheet name is invalid")
        worksheet = worksheet_dir / filename
        if not worksheet.is_file() or expected_hash != _digest_file(worksheet):
            raise CharacterPackageValidationError(
                "manifest worksheet hash differs for {}".format(filename)
            )
    accepted = dict(worksheet_hashes)
    for item in audit_items:
        source_name = str(item["source_cell"]).split("#", 1)[0]
        if item.get("source_worksheet_sha256") != accepted[source_name]:
            raise CharacterPackageValidationError("audit worksheet hash differs from manifest")

    canonical = pose_raw.get("canonical")
    if not isinstance(canonical, Mapping) or not isinstance(canonical.get("safe_inset"), Mapping):
        raise CharacterPackageValidationError("pose library canonical bounds are invalid")
    cols, rows = int(canonical.get("cols", 0)), int(canonical.get("rows", 0))
    inset = canonical["safe_inset"]
    graphs = [
        *(pixel_graph_raw.get("graphs") or []),
        *(
            {"id": pose.get("id"), "nodes": pose.get("cells")}
            for pose in (pose_raw.get("poses") or [])
            if isinstance(pose, Mapping)
        ),
    ]
    graph_ids = [graph.get("id") for graph in graphs if isinstance(graph, Mapping)]
    audit_graph_ids = [item.get("graph_id") for item in audit_items]
    if (
        len(graphs) != 124
        or len(graph_ids) != 124
        or len(set(graph_ids)) != 124
        or len(audit_graph_ids) != 124
        or len(set(audit_graph_ids)) != 124
        or set(graph_ids) != set(audit_graph_ids)
    ):
        raise CharacterPackageValidationError(
            "direct-cell package must expose 124 unique audited graphs"
        )
    for graph in graphs:
        nodes = graph.get("nodes") if isinstance(graph, Mapping) else None
        if not isinstance(nodes, list) or not nodes:
            raise CharacterPackageValidationError("pixel graph nodes are absent")
        for node in nodes:
            if not isinstance(node, Mapping):
                raise CharacterPackageValidationError("pixel graph node is invalid")
            x, y, rgb = node.get("x"), node.get("y"), node.get("rgb")
            if not isinstance(x, int) or isinstance(x, bool) or not isinstance(y, int) or isinstance(y, bool):
                raise CharacterPackageValidationError("pixel graph coordinates must be integers")
            if not (int(inset["left"]) <= x < cols - int(inset["right"])):
                raise CharacterPackageValidationError("pixel graph x coordinate violates safe bounds")
            if not (int(inset["top"]) <= y <= int(canonical["baseline_y"])):
                raise CharacterPackageValidationError("pixel graph y coordinate violates safe bounds")
            if not isinstance(rgb, list) or len(rgb) != 3 or any(
                not isinstance(channel, int) or isinstance(channel, bool) or not 0 <= channel <= 255
                for channel in rgb
            ):
                raise CharacterPackageValidationError("pixel graph RGB node is invalid")


def _repository_asset(
    repository_root: Path,
    value: Any,
    name: str,
    *,
    directory: bool = False,
) -> Path:
    if not isinstance(value, str) or not value:
        raise CharacterPackageValidationError("{} must be a repository path".format(name))
    asset = (repository_root / value).resolve()
    if repository_root not in asset.parents:
        raise CharacterPackageValidationError("{} escapes the repository".format(name))
    exists = asset.is_dir() if directory else asset.is_file()
    if not exists:
        raise CharacterPackageValidationError("{} is missing".format(name))
    return asset


def _digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


__all__ = [
    "CharacterPackage",
    "CharacterPackageValidationError",
    "WIZARD_JOE_PACKAGE_PATH",
    "CRYSTAIL_PACKAGE_PATH",
    "ORION_VALE_PACKAGE_PATH",
    "THORNE_VALE_PACKAGE_PATH",
    "load_character_package",
]
