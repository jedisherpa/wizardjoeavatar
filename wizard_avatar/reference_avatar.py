from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Dict, Mapping, Tuple

from .compositor import CellCanvas
from .glyphs import glyph


REFERENCE_CELL_PATH = Path(__file__).with_name("definitions") / "reference_avatar_cells.json"
REFERENCE_POSE_CELL_PATH = Path(__file__).with_name("definitions") / "reference_avatar_pose_cells.json"
REFERENCE_FRONT_IDLE_POSE_ID = "front_idle"
REFERENCE_LAYER_ID = "reference_voxel_png"
REFERENCE_SCALE_MULTIPLIER = 0.90
_VERIFIED_POSE_LIBRARY_HASHES: Mapping[Path, str] = MappingProxyType({})
_VERIFIED_POSE_LIBRARY_HASH_LOCK = threading.RLock()


@dataclass(frozen=True)
class ReferencePoseCell:
    x: int
    y: int
    rgb: Tuple[int, int, int]
    region: str = ""


@dataclass(frozen=True)
class ReferencePose:
    pose_id: str
    description: str
    cols: int
    rows: int
    root_anchor: Tuple[int, int]
    presentation_scale: Tuple[int, int]
    anchors: Dict[str, Tuple[int, int]]
    cells: Tuple[ReferencePoseCell, ...]


@lru_cache(maxsize=1)
def _load_reference_payload() -> dict:
    with open(REFERENCE_CELL_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=None)
def load_reference_pose_library(path: Path = REFERENCE_POSE_CELL_PATH) -> dict:
    library_path = Path(path).resolve()
    content = library_path.read_bytes()
    expected = _VERIFIED_POSE_LIBRARY_HASHES.get(library_path)
    actual = "sha256:" + hashlib.sha256(content).hexdigest()
    if expected is not None and actual != expected:
        raise ValueError(
            "Verified reference pose library bytes changed: {}".format(
                library_path
            )
        )
    return json.loads(content.decode("utf-8"))


def register_verified_reference_pose_library(
    path: Path,
    sha256: str,
) -> None:
    """Bind later pose parsing to the bytes admitted by a character package."""

    global _VERIFIED_POSE_LIBRARY_HASHES
    with _VERIFIED_POSE_LIBRARY_HASH_LOCK:
        library_path = Path(path).resolve()
        updated = dict(_VERIFIED_POSE_LIBRARY_HASHES)
        updated[library_path] = sha256
        _VERIFIED_POSE_LIBRARY_HASHES = MappingProxyType(updated)
        clear_reference_pose_cache()


def clear_reference_pose_cache() -> None:
    """Drop parsed pose and rendered-canvas caches after package admission."""

    load_reference_pose_library.cache_clear()
    _reference_pose_map.cache_clear()
    _render_reference_pose_canvas.cache_clear()


@lru_cache(maxsize=None)
def _reference_pose_map(path: Path = REFERENCE_POSE_CELL_PATH) -> Dict[str, ReferencePose]:
    library_path = Path(path).resolve()
    payload = load_reference_pose_library(library_path)
    poses: Dict[str, ReferencePose] = {}
    raw_poses = payload.get("poses", [])
    if isinstance(raw_poses, Mapping):
        pose_items = raw_poses.items()
    else:
        pose_items = ((None, pose) for pose in raw_poses)
    for keyed_pose_id, pose in pose_items:
        if not isinstance(pose, Mapping):
            raise ValueError("Reference pose entries must be objects")
        raw_pose_id = keyed_pose_id or pose.get("id") or pose.get("pose_id")
        if raw_pose_id is None:
            raise ValueError("Reference pose is missing an id")
        pose_id = str(raw_pose_id)
        root = pose["root_anchor"]
        presentation_scale = pose.get("presentation_scale", [1, 1])
        if (
            not isinstance(presentation_scale, list)
            or len(presentation_scale) != 2
            or any(
                isinstance(value, bool) or not isinstance(value, int) or value < 1
                for value in presentation_scale
            )
        ):
            raise ValueError(
                f"Reference pose {pose_id!r} has an invalid presentation_scale"
            )
        anchors = {
            str(name): (int(point[0]), int(point[1]))
            for name, point in pose.get("anchors", {}).items()
        }
        anchors.setdefault("root", (int(root[0]), int(root[1])))
        cells = tuple(
            ReferencePoseCell(
                x=int(cell["x"]),
                y=int(cell["y"]),
                rgb=tuple(int(channel) for channel in cell["rgb"]),
                region=str(cell.get("region", "")),
            )
            for cell in pose.get("cells", [])
        )
        poses[pose_id] = ReferencePose(
            pose_id=pose_id,
            description=str(pose.get("description", "")),
            cols=int(pose["cols"]),
            rows=int(pose["rows"]),
            root_anchor=(int(root[0]), int(root[1])),
            presentation_scale=(
                int(presentation_scale[0]),
                int(presentation_scale[1]),
            ),
            anchors=anchors,
            cells=cells,
        )
    if not poses:
        raise ValueError(f"No reference poses found in {library_path}")
    return poses


def reference_avatar_available(path: Path = REFERENCE_POSE_CELL_PATH) -> bool:
    return reference_pose_library_available(path) or REFERENCE_CELL_PATH.exists()


def reference_pose_library_available(path: Path = REFERENCE_POSE_CELL_PATH) -> bool:
    return Path(path).resolve().exists()


def reference_pose_ids(path: Path = REFERENCE_POSE_CELL_PATH) -> Tuple[str, ...]:
    return tuple(_reference_pose_map(Path(path).resolve()).keys())


def get_reference_pose(
    pose_id: str,
    path: Path = REFERENCE_POSE_CELL_PATH,
) -> ReferencePose:
    poses = _reference_pose_map(Path(path).resolve())
    try:
        return poses[pose_id]
    except KeyError as exc:
        available = ", ".join(sorted(poses))
        raise KeyError(f"Unknown reference pose {pose_id!r}; available poses: {available}") from exc


def reference_pose_root_anchor(
    pose_id: str = REFERENCE_FRONT_IDLE_POSE_ID,
    path: Path = REFERENCE_POSE_CELL_PATH,
) -> Tuple[int, int]:
    return get_reference_pose(pose_id, path).root_anchor


def reference_pose_anchor(
    pose_id: str,
    anchor_name: str,
    path: Path = REFERENCE_POSE_CELL_PATH,
) -> Tuple[int, int]:
    pose = get_reference_pose(pose_id, path)
    try:
        return pose.anchors[anchor_name]
    except KeyError as exc:
        available = ", ".join(sorted(pose.anchors))
        raise KeyError(
            f"Reference pose {pose_id!r} is missing anchor {anchor_name!r}; "
            f"available anchors: {available}"
        ) from exc


def reference_pose_presentation_scale(
    pose_id: str,
    path: Path = REFERENCE_POSE_CELL_PATH,
) -> float:
    numerator, denominator = get_reference_pose(pose_id, path).presentation_scale
    return numerator / denominator


def reference_root_anchor() -> Tuple[int, int]:
    if reference_pose_library_available():
        return reference_pose_root_anchor(REFERENCE_FRONT_IDLE_POSE_ID)
    payload = _load_reference_payload()
    root = payload["root_anchor"]
    return int(root[0]), int(root[1])


@lru_cache(maxsize=None)
def _render_reference_pose_canvas(
    pose_id: str,
    path: Path = REFERENCE_POSE_CELL_PATH,
) -> CellCanvas:
    pose = get_reference_pose(pose_id, path)
    canvas = CellCanvas(pose.cols, pose.rows)
    layer_id = f"{REFERENCE_LAYER_ID}:{pose.pose_id}"
    for cell in pose.cells:
        canvas.set(
            cell.x,
            cell.y,
            glyph("solid_fill"),
            cell.rgb,
            cell.region or layer_id,
        )
    return canvas


def render_reference_pose_local(
    pose_id: str,
    path: Path = REFERENCE_POSE_CELL_PATH,
) -> CellCanvas:
    return _render_reference_pose_canvas(pose_id, Path(path).resolve()).copy()


@lru_cache(maxsize=1)
def _render_legacy_reference_avatar_canvas() -> CellCanvas:
    payload = _load_reference_payload()
    canvas = CellCanvas(int(payload["cols"]), int(payload["rows"]))
    for cell in payload["cells"]:
        rgb = tuple(int(channel) for channel in cell["rgb"])
        canvas.set(int(cell["x"]), int(cell["y"]), glyph("solid_fill"), rgb, REFERENCE_LAYER_ID)
    return canvas


def render_reference_avatar_local() -> CellCanvas:
    if reference_pose_library_available():
        return render_reference_pose_local(REFERENCE_FRONT_IDLE_POSE_ID)
    return _render_legacy_reference_avatar_canvas().copy()
