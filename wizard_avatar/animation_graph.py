from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS_DIR = Path(__file__).with_name("definitions")
ANIMATION_GRAPH_V2_PATH = DEFINITIONS_DIR / "reference_avatar_animation_graph_v2.json"
ANIMATION_GRAPH_V2_SCHEMA_PATH = DEFINITIONS_DIR / "reference_avatar_animation_graph_v2.schema.json"
REFERENCE_POSE_LIBRARY_PATH = DEFINITIONS_DIR / "reference_avatar_pose_cells.json"
REFERENCE_POSE_MANIFEST_PATH = ROOT / "assets" / "reference" / "motion_sources" / "manifest.json"

FACINGS = frozenset(
    {
        "north",
        "northeast",
        "east",
        "southeast",
        "south",
        "southwest",
        "west",
        "northwest",
    }
)
CLASSIFICATION_ROLES = frozenset({"clip_sample", "transition_sample", "diagnostic_only"})
ALTITUDE_CLASSES = frozenset({"grounded", "takeoff", "airborne", "landing"})
SUPPORT_CONTACTS = frozenset({"none", "left_foot", "right_foot", "both_feet", "staff"})
WING_MODES = frozenset({"hidden", "folded", "extended", "upstroke", "downstroke", "banked"})
STAFF_MODES = frozenset({"absent", "carried", "planted", "guard", "attack", "spin"})
LOOP_MODES = frozenset({"loop", "once", "hold_last"})
PHASE_SOURCES = frozenset({"none", "time", "ground_distance", "air_distance", "flap_phase"})
ROOT_POLICIES = frozenset({"fixed", "ground_distance", "air_trajectory", "contact_locked"})
INTERRUPT_POLICIES = frozenset({"immediate", "at_marker", "after_commit", "uninterruptible"})
TIMING_MODES = frozenset({"immediate", "marker", "phase", "contact"})
PHASE_POLICIES = frozenset({"preserve", "nearest_contact", "restart", "none"})
CONTACT_POLICIES = frozenset({"preserve", "match", "release", "none"})
REGION_POLICIES = frozenset({"coherent_pose", "presented_snapshot", "declared_masks"})
MARKER_IDS = frozenset(
    {
        "left_contact",
        "left_release",
        "right_contact",
        "right_release",
        "both_contact",
        "staff_contact",
        "staff_release",
        "takeoff_commit",
        "airborne",
        "flap_down_peak",
        "flap_up_peak",
        "bank_apex",
        "landing_contact",
        "landing_settled",
        "action_commit",
        "action_effect",
        "action_recoverable",
        "speech_open",
        "speech_close",
        "shush_hold_start",
        "shush_hold_end",
        "loop_boundary",
    }
)


class AnimationGraphValidationError(ValueError):
    """Raised when graph or pose-library data violates the v2 contract."""


@dataclass(frozen=True)
class PoseMetadata:
    pose_id: str
    source: str
    description: str
    facing: str
    locomotion: str
    actions: Tuple[str, ...]
    phase: Optional[float]
    tags: Tuple[str, ...]
    cols: int
    rows: int
    root_anchor: Tuple[int, int]
    anchors: Mapping[str, Tuple[int, int]]
    cell_count: int


@dataclass(frozen=True)
class PoseClassification:
    roles: Tuple[str, ...]
    altitude_class: str
    support_contact: str
    planted_anchor: Optional[str]
    wing_mode: str
    staff_mode: str
    capability_tier: str


@dataclass(frozen=True)
class Marker:
    marker_id: str
    frame_offset: int


@dataclass(frozen=True)
class ClipSample:
    pose_id: str
    duration_frames: int
    support_contact: str
    planted_anchor: Optional[str]
    normalized_distance: Optional[float]
    markers: Tuple[Marker, ...]


@dataclass(frozen=True)
class ClipDefinition:
    clip_id: str
    family: str
    supported_facings: Tuple[str, ...]
    loop_mode: str
    phase_source: str
    root_policy: str
    minimum_hold_ticks: int
    interrupt_policy: str
    channel_ownership: Tuple[str, ...]
    samples: Tuple[ClipSample, ...]
    entry_markers: Tuple[str, ...]
    exit_markers: Tuple[str, ...]
    secondary_curves: Mapping[str, str]
    legal_successors: Tuple[str, ...]

    @property
    def total_frames(self) -> int:
        return sum(sample.duration_frames for sample in self.samples)


@dataclass(frozen=True)
class NodeDefinition:
    node_id: str
    clip_id: str
    mobility_modes: Tuple[str, ...]
    actions: Tuple[str, ...]


@dataclass(frozen=True)
class TransitionRecipe:
    recipe_id: str
    entry_rule: str
    duration_frames: int
    interrupt_source: str
    region_masks: Tuple[str, ...]


@dataclass(frozen=True)
class TransitionDefinition:
    transition_id: str
    source_node_id: str
    target_node_id: str
    priority: int
    duration_ticks: int
    timing_mode: str
    transition_recipe_id: str
    phase_policy: str
    root_policy: str
    contact_policy: str
    region_policy: str
    interrupt_window: str
    fallback_transition_id: Optional[str]


@dataclass(frozen=True)
class ClipEvaluation:
    clip_id: str
    elapsed_ticks: int
    authored_frame: int
    loop_index: int
    sample_index: int
    sample_frame: int
    pose_id: str
    support_contact: str
    planted_anchor: Optional[str]
    clip_phase_numerator: int
    clip_phase_denominator: int
    active_markers: Tuple[str, ...]

    @property
    def clip_phase(self) -> float:
        return self.clip_phase_numerator / self.clip_phase_denominator


@dataclass(frozen=True)
class AnimationGraph:
    schema_version: int
    graph_id: str
    asset_set_id: str
    authored_fps: int
    simulation_hz: int
    default_node_id: str
    capability_tiers: Mapping[str, Mapping[str, Any]]
    pose_catalog: Mapping[str, PoseMetadata]
    pose_classification: Mapping[str, PoseClassification]
    clips: Mapping[str, ClipDefinition]
    nodes: Mapping[str, NodeDefinition]
    transitions: Tuple[TransitionDefinition, ...]
    transition_recipes: Mapping[str, TransitionRecipe]
    channel_masks: Mapping[str, Tuple[str, ...]]
    fallbacks: Mapping[str, Any]
    source_sha256: str

    def evaluate_clip(
        self,
        clip_id: str,
        elapsed_ticks: int,
        previous_elapsed_ticks: Optional[int] = None,
    ) -> ClipEvaluation:
        if elapsed_ticks < 0:
            raise ValueError("elapsed_ticks must be nonnegative")
        if previous_elapsed_ticks is not None:
            if previous_elapsed_ticks < -1:
                raise ValueError("previous_elapsed_ticks must be at least -1")
            if previous_elapsed_ticks > elapsed_ticks:
                raise ValueError("previous_elapsed_ticks cannot exceed elapsed_ticks")
        try:
            clip = self.clips[clip_id]
        except KeyError as exc:
            raise KeyError(f"Unknown animation clip {clip_id!r}") from exc

        absolute_frame = (elapsed_ticks * self.authored_fps) // self.simulation_hz
        total_frames = clip.total_frames
        if clip.loop_mode == "loop":
            local_frame = absolute_frame % total_frames
            loop_index = absolute_frame // total_frames
        else:
            local_frame = min(absolute_frame, total_frames - 1)
            loop_index = 0

        sample_index, sample_frame = _sample_at_frame(clip, local_frame)
        sample = clip.samples[sample_index]
        previous_tick = elapsed_ticks - 1 if previous_elapsed_ticks is None else previous_elapsed_ticks
        markers = _markers_crossed(
            clip,
            previous_tick,
            elapsed_ticks,
            self.authored_fps,
            self.simulation_hz,
        )
        return ClipEvaluation(
            clip_id=clip.clip_id,
            elapsed_ticks=elapsed_ticks,
            authored_frame=local_frame,
            loop_index=loop_index,
            sample_index=sample_index,
            sample_frame=sample_frame,
            pose_id=sample.pose_id,
            support_contact=sample.support_contact,
            planted_anchor=sample.planted_anchor,
            clip_phase_numerator=local_frame,
            clip_phase_denominator=total_frames,
            active_markers=markers,
        )

    def evaluate_clip_phase(self, clip_id: str, phase: float) -> ClipEvaluation:
        """Evaluate a distance-driven clip at a normalized cycle phase."""

        try:
            clip = self.clips[clip_id]
        except KeyError as exc:
            raise KeyError(f"Unknown animation clip {clip_id!r}") from exc
        normalized = float(phase) % 1.0
        authored_frame = min(int(normalized * clip.total_frames), clip.total_frames - 1)
        sample_index, sample_frame = _sample_at_frame(clip, authored_frame)
        sample = clip.samples[sample_index]
        return ClipEvaluation(
            clip_id=clip.clip_id,
            elapsed_ticks=(authored_frame * self.simulation_hz) // self.authored_fps,
            authored_frame=authored_frame,
            loop_index=0,
            sample_index=sample_index,
            sample_frame=sample_frame,
            pose_id=sample.pose_id,
            support_contact=sample.support_contact,
            planted_anchor=sample.planted_anchor,
            clip_phase_numerator=authored_frame,
            clip_phase_denominator=clip.total_frames,
            active_markers=tuple(
                marker.marker_id
                for marker in sample.markers
                if marker.frame_offset == sample_frame
            ),
        )

    def is_legal_successor(self, source_clip_id: str, target_clip_id: str) -> bool:
        try:
            source = self.clips[source_clip_id]
        except KeyError as exc:
            raise KeyError(f"Unknown source clip {source_clip_id!r}") from exc
        if target_clip_id not in self.clips:
            raise KeyError(f"Unknown target clip {target_clip_id!r}")
        return target_clip_id in source.legal_successors

    def select_transition(
        self,
        source_node_id: str,
        target_node_id: str,
    ) -> Optional[TransitionDefinition]:
        matches = (
            transition
            for transition in self.transitions
            if transition.source_node_id == source_node_id
            and transition.target_node_id == target_node_id
        )
        return max(matches, key=lambda transition: transition.priority, default=None)


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise AnimationGraphValidationError(f"{path}: invalid JSON: {exc}") from exc


def _path_error(path: str, message: str) -> AnimationGraphValidationError:
    return AnimationGraphValidationError(f"{path}: {message}")


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise _path_error(path, "expected object")
    return value


def _sequence(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise _path_error(path, "expected array")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise _path_error(path, "expected nonempty string")
    return value


def _integer(value: Any, path: str, minimum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _path_error(path, "expected integer")
    if minimum is not None and value < minimum:
        raise _path_error(path, f"must be at least {minimum}")
    return value


def _number_or_none(value: Any, path: str) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _path_error(path, "expected number or null")
    return float(value)


def _enum(value: Any, path: str, allowed: Iterable[str]) -> str:
    result = _string(value, path)
    allowed_set = set(allowed)
    if result not in allowed_set:
        values = ", ".join(sorted(allowed_set))
        raise _path_error(path, f"expected one of: {values}")
    return result


def _string_tuple(value: Any, path: str, allow_empty: bool = False) -> Tuple[str, ...]:
    items = _sequence(value, path)
    if not items and not allow_empty:
        raise _path_error(path, "must not be empty")
    result = tuple(_string(item, f"{path}[{index}]") for index, item in enumerate(items))
    if len(set(result)) != len(result):
        raise _path_error(path, "must not contain duplicates")
    return result


def _keys(value: Mapping[str, Any], path: str, required: Iterable[str], optional: Iterable[str] = ()) -> None:
    required_set = set(required)
    allowed = required_set | set(optional)
    missing = sorted(required_set - set(value))
    if missing:
        raise _path_error(path, f"missing required fields: {', '.join(missing)}")
    extra = sorted(set(value) - allowed)
    if extra:
        raise _path_error(path, f"unknown fields: {', '.join(extra)}")


def _point(value: Any, path: str) -> Tuple[int, int]:
    items = _sequence(value, path)
    if len(items) != 2:
        raise _path_error(path, "expected two integers")
    return _integer(items[0], f"{path}[0]"), _integer(items[1], f"{path}[1]")


def load_pose_catalog(
    manifest_path: Path = REFERENCE_POSE_MANIFEST_PATH,
    library_path: Path = REFERENCE_POSE_LIBRARY_PATH,
) -> Mapping[str, PoseMetadata]:
    """Load and cross-check metadata from the source manifest and cell library."""

    manifest = _mapping(_load_json(Path(manifest_path)), str(manifest_path))
    library = _mapping(_load_json(Path(library_path)), str(library_path))
    manifest_poses = _sequence(manifest.get("poses"), f"{manifest_path}.poses")
    library_poses = _sequence(library.get("poses"), f"{library_path}.poses")
    manifest_asset_set = _string(manifest.get("asset_set_id"), f"{manifest_path}.asset_set_id")
    library_asset_set = _string(library.get("asset_set_id"), f"{library_path}.asset_set_id")
    if manifest_asset_set != library_asset_set:
        raise _path_error("pose_library", "manifest and cell-library asset_set_id values differ")

    library_by_id: Dict[str, Mapping[str, Any]] = {}
    for index, raw_pose in enumerate(library_poses):
        pose = _mapping(raw_pose, f"{library_path}.poses[{index}]")
        pose_id = _string(pose.get("id"), f"{library_path}.poses[{index}].id")
        if pose_id in library_by_id:
            raise _path_error(f"{library_path}.poses[{index}].id", f"duplicate pose {pose_id!r}")
        library_by_id[pose_id] = pose

    catalog: Dict[str, PoseMetadata] = {}
    for index, raw_pose in enumerate(manifest_poses):
        manifest_pose = _mapping(raw_pose, f"{manifest_path}.poses[{index}]")
        base = f"{manifest_path}.poses[{index}]"
        pose_id = _string(manifest_pose.get("id"), f"{base}.id")
        if pose_id in catalog:
            raise _path_error(f"{base}.id", f"duplicate pose {pose_id!r}")
        if pose_id not in library_by_id:
            raise _path_error(base, f"pose {pose_id!r} is absent from the cell library")
        library_pose = library_by_id[pose_id]

        facing = _enum(manifest_pose.get("facing"), f"{base}.facing", FACINGS)
        locomotion = _string(manifest_pose.get("locomotion"), f"{base}.locomotion")
        actions = _string_tuple(manifest_pose.get("actions"), f"{base}.actions")
        phase = _number_or_none(manifest_pose.get("phase"), f"{base}.phase")
        if phase is not None and not 0.0 <= phase <= 1.0:
            raise _path_error(f"{base}.phase", "must be in [0, 1]")
        tags = _string_tuple(manifest_pose.get("tags"), f"{base}.tags")

        for field, expected in (
            ("facing", facing),
            ("locomotion", locomotion),
            ("actions", list(actions)),
            ("phase", phase),
            ("tags", list(tags)),
        ):
            if library_pose.get(field) != expected:
                raise _path_error(
                    f"{library_path}.poses[{pose_id!r}].{field}",
                    "does not match source manifest",
                )

        anchors_raw = _mapping(library_pose.get("anchors"), f"{library_path}.poses[{pose_id!r}].anchors")
        anchors = {
            _string(name, f"anchors key for {pose_id}"): _point(point, f"anchors.{pose_id}.{name}")
            for name, point in anchors_raw.items()
        }
        required_anchors = {
            "root",
            "mouth",
            "left_eye",
            "right_eye",
            "left_foot",
            "right_foot",
            "left_hand",
            "right_hand",
            "staff_hand",
            "staff_tip",
        }
        missing_anchors = sorted(required_anchors - set(anchors))
        if missing_anchors:
            raise _path_error(f"anchors.{pose_id}", f"missing anchors: {', '.join(missing_anchors)}")
        cells = _sequence(library_pose.get("cells"), f"{library_path}.poses[{pose_id!r}].cells")
        if not cells:
            raise _path_error(f"{library_path}.poses[{pose_id!r}].cells", "must not be empty")
        catalog[pose_id] = PoseMetadata(
            pose_id=pose_id,
            source=_string(manifest_pose.get("source"), f"{base}.source"),
            description=str(manifest_pose.get("description", "")),
            facing=facing,
            locomotion=locomotion,
            actions=actions,
            phase=phase,
            tags=tags,
            cols=_integer(library_pose.get("cols"), f"{base}.cols", 1),
            rows=_integer(library_pose.get("rows"), f"{base}.rows", 1),
            root_anchor=_point(library_pose.get("root_anchor"), f"{base}.root_anchor"),
            anchors=anchors,
            cell_count=len(cells),
        )

    extra_library_poses = sorted(set(library_by_id) - set(catalog))
    if extra_library_poses:
        raise _path_error("pose_library", f"cell library has unmanifested poses: {', '.join(extra_library_poses)}")
    return catalog


def _parse_classification(
    payload: Mapping[str, Any],
    catalog: Mapping[str, PoseMetadata],
) -> Mapping[str, PoseClassification]:
    expected_ids = set(catalog)
    actual_ids = set(payload)
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if extra:
            details.append(f"unknown: {', '.join(extra)}")
        raise _path_error("$.pose_classification", "; ".join(details))

    result: Dict[str, PoseClassification] = {}
    for pose_id, raw_value in payload.items():
        path = f"$.pose_classification.{pose_id}"
        value = _mapping(raw_value, path)
        _keys(
            value,
            path,
            {
                "roles",
                "altitude_class",
                "support_contact",
                "planted_anchor",
                "wing_mode",
                "staff_mode",
                "capability_tier",
            },
        )
        roles = _string_tuple(value["roles"], f"{path}.roles")
        for index, role in enumerate(roles):
            _enum(role, f"{path}.roles[{index}]", CLASSIFICATION_ROLES)
        planted_anchor_raw = value["planted_anchor"]
        planted_anchor = None if planted_anchor_raw is None else _string(planted_anchor_raw, f"{path}.planted_anchor")
        if planted_anchor is not None and planted_anchor not in catalog[pose_id].anchors:
            raise _path_error(f"{path}.planted_anchor", f"unknown pose anchor {planted_anchor!r}")
        classification = PoseClassification(
            roles=roles,
            altitude_class=_enum(value["altitude_class"], f"{path}.altitude_class", ALTITUDE_CLASSES),
            support_contact=_enum(value["support_contact"], f"{path}.support_contact", SUPPORT_CONTACTS),
            planted_anchor=planted_anchor,
            wing_mode=_enum(value["wing_mode"], f"{path}.wing_mode", WING_MODES),
            staff_mode=_enum(value["staff_mode"], f"{path}.staff_mode", STAFF_MODES),
            capability_tier=_enum(value["capability_tier"], f"{path}.capability_tier", {"A", "B", "C"}),
        )
        if classification.altitude_class == "airborne" and classification.support_contact != "none":
            raise _path_error(path, "airborne poses must declare support_contact 'none'")
        if classification.altitude_class == "airborne" and classification.wing_mode in {"hidden", "folded"}:
            raise _path_error(path, "airborne poses must retain visible wings")
        result[pose_id] = classification
    return result


def _parse_marker(value: Any, path: str, duration_frames: int) -> Marker:
    raw = _mapping(value, path)
    _keys(raw, path, {"id", "frame_offset"})
    marker_id = _enum(raw["id"], f"{path}.id", MARKER_IDS)
    offset = _integer(raw["frame_offset"], f"{path}.frame_offset", 0)
    if offset >= duration_frames:
        raise _path_error(f"{path}.frame_offset", "must be within the sample duration")
    return Marker(marker_id=marker_id, frame_offset=offset)


def _parse_clip(value: Any, path: str, catalog: Mapping[str, PoseMetadata]) -> ClipDefinition:
    raw = _mapping(value, path)
    required = {
        "clip_id",
        "family",
        "supported_facings",
        "loop_mode",
        "phase_source",
        "root_policy",
        "minimum_hold_ticks",
        "interrupt_policy",
        "channel_ownership",
        "samples",
        "entry_markers",
        "exit_markers",
        "secondary_curves",
        "legal_successors",
    }
    _keys(raw, path, required)
    clip_id = _string(raw["clip_id"], f"{path}.clip_id")
    supported_facings = _string_tuple(raw["supported_facings"], f"{path}.supported_facings")
    for index, facing in enumerate(supported_facings):
        _enum(facing, f"{path}.supported_facings[{index}]", FACINGS)
    samples_raw = _sequence(raw["samples"], f"{path}.samples")
    if not samples_raw:
        raise _path_error(f"{path}.samples", "must not be empty")
    samples = []
    for index, raw_sample in enumerate(samples_raw):
        sample_path = f"{path}.samples[{index}]"
        sample_value = _mapping(raw_sample, sample_path)
        _keys(
            sample_value,
            sample_path,
            {"pose_id", "duration_frames", "support_contact", "planted_anchor", "markers"},
            {"normalized_distance"},
        )
        pose_id = _string(sample_value["pose_id"], f"{sample_path}.pose_id")
        if pose_id not in catalog:
            raise _path_error(f"{sample_path}.pose_id", f"unknown pose {pose_id!r}")
        duration = _integer(sample_value["duration_frames"], f"{sample_path}.duration_frames", 1)
        contact = _enum(sample_value["support_contact"], f"{sample_path}.support_contact", SUPPORT_CONTACTS)
        planted_raw = sample_value["planted_anchor"]
        planted = None if planted_raw is None else _string(planted_raw, f"{sample_path}.planted_anchor")
        if planted is not None and planted not in catalog[pose_id].anchors:
            raise _path_error(f"{sample_path}.planted_anchor", f"pose has no anchor {planted!r}")
        distance = _number_or_none(sample_value.get("normalized_distance"), f"{sample_path}.normalized_distance")
        if distance is not None and distance < 0:
            raise _path_error(f"{sample_path}.normalized_distance", "must be nonnegative")
        markers = tuple(
            _parse_marker(marker, f"{sample_path}.markers[{marker_index}]", duration)
            for marker_index, marker in enumerate(_sequence(sample_value["markers"], f"{sample_path}.markers"))
        )
        if len({(marker.marker_id, marker.frame_offset) for marker in markers}) != len(markers):
            raise _path_error(f"{sample_path}.markers", "contains duplicate marker occurrences")
        samples.append(
            ClipSample(
                pose_id=pose_id,
                duration_frames=duration,
                support_contact=contact,
                planted_anchor=planted,
                normalized_distance=distance,
                markers=markers,
            )
        )
    entry_markers = _string_tuple(raw["entry_markers"], f"{path}.entry_markers", allow_empty=True)
    exit_markers = _string_tuple(raw["exit_markers"], f"{path}.exit_markers", allow_empty=True)
    for marker_path, markers in (("entry_markers", entry_markers), ("exit_markers", exit_markers)):
        for index, marker in enumerate(markers):
            _enum(marker, f"{path}.{marker_path}[{index}]", MARKER_IDS)
    curves_raw = _mapping(raw["secondary_curves"], f"{path}.secondary_curves")
    curves = {
        _string(key, f"{path}.secondary_curves key"): _string(value, f"{path}.secondary_curves.{key}")
        for key, value in curves_raw.items()
    }
    return ClipDefinition(
        clip_id=clip_id,
        family=_enum(raw["family"], f"{path}.family", {"idle", "locomotion", "flight", "action", "reaction", "speech", "transition"}),
        supported_facings=supported_facings,
        loop_mode=_enum(raw["loop_mode"], f"{path}.loop_mode", LOOP_MODES),
        phase_source=_enum(raw["phase_source"], f"{path}.phase_source", PHASE_SOURCES),
        root_policy=_enum(raw["root_policy"], f"{path}.root_policy", ROOT_POLICIES),
        minimum_hold_ticks=_integer(raw["minimum_hold_ticks"], f"{path}.minimum_hold_ticks", 0),
        interrupt_policy=_enum(raw["interrupt_policy"], f"{path}.interrupt_policy", INTERRUPT_POLICIES),
        channel_ownership=_string_tuple(raw["channel_ownership"], f"{path}.channel_ownership"),
        samples=tuple(samples),
        entry_markers=entry_markers,
        exit_markers=exit_markers,
        secondary_curves=curves,
        legal_successors=_string_tuple(raw["legal_successors"], f"{path}.legal_successors"),
    )


def parse_animation_graph(
    payload: Any,
    pose_catalog: Optional[Mapping[str, PoseMetadata]] = None,
) -> AnimationGraph:
    """Strictly parse graph v2 data and validate all cross-references."""

    catalog = pose_catalog if pose_catalog is not None else load_pose_catalog()
    raw = _mapping(payload, "$")
    required = {
        "$schema",
        "$id",
        "schema_version",
        "asset_set_id",
        "authored_fps",
        "simulation_hz",
        "default_node_id",
        "capability_tiers",
        "pose_classification",
        "clips",
        "nodes",
        "transitions",
        "transition_recipes",
        "channel_masks",
        "fallbacks",
    }
    _keys(raw, "$", required)
    if _integer(raw["schema_version"], "$.schema_version") != 2:
        raise _path_error("$.schema_version", "must equal 2")
    graph_id = _string(raw["$id"], "$.$id")
    _string(raw["$schema"], "$.$schema")
    asset_set_id = _string(raw["asset_set_id"], "$.asset_set_id")
    catalog_asset_ids = {asset_set_id}
    if not catalog:
        raise _path_error("pose_catalog", "must not be empty")
    # The catalog was cross-checked while loading. The graph asset ID is checked
    # against the canonical source manifest below without rereading pose cells.
    manifest = _mapping(_load_json(REFERENCE_POSE_MANIFEST_PATH), str(REFERENCE_POSE_MANIFEST_PATH))
    catalog_asset_ids.add(_string(manifest.get("asset_set_id"), "manifest.asset_set_id"))
    if len(catalog_asset_ids) != 1:
        raise _path_error("$.asset_set_id", "does not match the pose catalog")

    authored_fps = _integer(raw["authored_fps"], "$.authored_fps", 1)
    simulation_hz = _integer(raw["simulation_hz"], "$.simulation_hz", 1)
    tiers_raw = _mapping(raw["capability_tiers"], "$.capability_tiers")
    if set(tiers_raw) != {"A", "B", "C"}:
        raise _path_error("$.capability_tiers", "must define exactly A, B, and C")
    capability_tiers = {tier: dict(_mapping(value, f"$.capability_tiers.{tier}")) for tier, value in tiers_raw.items()}
    classification = _parse_classification(
        _mapping(raw["pose_classification"], "$.pose_classification"),
        catalog,
    )

    clips_raw = _mapping(raw["clips"], "$.clips")
    if not clips_raw:
        raise _path_error("$.clips", "must not be empty")
    clips: Dict[str, ClipDefinition] = {}
    for key, value in clips_raw.items():
        clip_id = _string(key, "$.clips key")
        clip = _parse_clip(value, f"$.clips.{clip_id}", catalog)
        if clip.clip_id != clip_id:
            raise _path_error(f"$.clips.{clip_id}.clip_id", "must match its object key")
        clips[clip_id] = clip
    for clip in clips.values():
        unknown = sorted(set(clip.legal_successors) - set(clips))
        if unknown:
            raise _path_error(f"$.clips.{clip.clip_id}.legal_successors", f"unknown clips: {', '.join(unknown)}")

    used_pose_ids = {sample.pose_id for clip in clips.values() for sample in clip.samples}
    required_clip_poses = {
        pose_id
        for pose_id, pose_classification in classification.items()
        if "clip_sample" in pose_classification.roles
    }
    missing_uses = sorted(required_clip_poses - used_pose_ids)
    if missing_uses:
        raise _path_error("$.clips", f"classified clip poses are unreachable: {', '.join(missing_uses)}")

    nodes_raw = _mapping(raw["nodes"], "$.nodes")
    nodes: Dict[str, NodeDefinition] = {}
    for node_id, raw_node in nodes_raw.items():
        node_path = f"$.nodes.{node_id}"
        node = _mapping(raw_node, node_path)
        _keys(node, node_path, {"clip_id", "mobility_modes", "actions"})
        clip_id = _string(node["clip_id"], f"{node_path}.clip_id")
        if clip_id not in clips:
            raise _path_error(f"{node_path}.clip_id", f"unknown clip {clip_id!r}")
        nodes[node_id] = NodeDefinition(
            node_id=_string(node_id, "$.nodes key"),
            clip_id=clip_id,
            mobility_modes=_string_tuple(node["mobility_modes"], f"{node_path}.mobility_modes"),
            actions=_string_tuple(node["actions"], f"{node_path}.actions", allow_empty=True),
        )
    default_node_id = _string(raw["default_node_id"], "$.default_node_id")
    if default_node_id not in nodes:
        raise _path_error("$.default_node_id", f"unknown node {default_node_id!r}")

    recipes_raw = _mapping(raw["transition_recipes"], "$.transition_recipes")
    recipes: Dict[str, TransitionRecipe] = {}
    for recipe_id, raw_recipe in recipes_raw.items():
        recipe_path = f"$.transition_recipes.{recipe_id}"
        recipe = _mapping(raw_recipe, recipe_path)
        _keys(recipe, recipe_path, {"entry_rule", "duration_frames", "interrupt_source", "region_masks"})
        recipes[recipe_id] = TransitionRecipe(
            recipe_id=_string(recipe_id, "$.transition_recipes key"),
            entry_rule=_enum(recipe["entry_rule"], f"{recipe_path}.entry_rule", {"phase_match", "marker_gate", "contact_match", "snapshot_handoff", "hard_cut"}),
            duration_frames=_integer(recipe["duration_frames"], f"{recipe_path}.duration_frames", 0),
            interrupt_source=_enum(recipe["interrupt_source"], f"{recipe_path}.interrupt_source", {"presented_snapshot", "authored_sample"}),
            region_masks=_string_tuple(recipe["region_masks"], f"{recipe_path}.region_masks", allow_empty=True),
        )

    transitions_raw = _sequence(raw["transitions"], "$.transitions")
    transitions = []
    transition_ids = set()
    for index, raw_transition in enumerate(transitions_raw):
        path = f"$.transitions[{index}]"
        value = _mapping(raw_transition, path)
        _keys(
            value,
            path,
            {
                "transition_id",
                "source_node_id",
                "target_node_id",
                "priority",
                "duration_ticks",
                "timing_mode",
                "transition_recipe_id",
                "phase_policy",
                "root_policy",
                "contact_policy",
                "region_policy",
                "interrupt_window",
                "fallback_transition_id",
            },
        )
        transition_id = _string(value["transition_id"], f"{path}.transition_id")
        if transition_id in transition_ids:
            raise _path_error(f"{path}.transition_id", f"duplicate transition {transition_id!r}")
        transition_ids.add(transition_id)
        source_node_id = _string(value["source_node_id"], f"{path}.source_node_id")
        target_node_id = _string(value["target_node_id"], f"{path}.target_node_id")
        if source_node_id not in nodes or target_node_id not in nodes:
            raise _path_error(path, "source_node_id and target_node_id must name existing nodes")
        recipe_id = _string(value["transition_recipe_id"], f"{path}.transition_recipe_id")
        if recipe_id not in recipes:
            raise _path_error(f"{path}.transition_recipe_id", f"unknown recipe {recipe_id!r}")
        source_clip_id = nodes[source_node_id].clip_id
        target_clip_id = nodes[target_node_id].clip_id
        if target_clip_id not in clips[source_clip_id].legal_successors:
            raise _path_error(path, f"clip {target_clip_id!r} is not a legal successor of {source_clip_id!r}")
        fallback_raw = value["fallback_transition_id"]
        fallback_id = None if fallback_raw is None else _string(fallback_raw, f"{path}.fallback_transition_id")
        transitions.append(
            TransitionDefinition(
                transition_id=transition_id,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                priority=_integer(value["priority"], f"{path}.priority", 0),
                duration_ticks=_integer(value["duration_ticks"], f"{path}.duration_ticks", 0),
                timing_mode=_enum(value["timing_mode"], f"{path}.timing_mode", TIMING_MODES),
                transition_recipe_id=recipe_id,
                phase_policy=_enum(value["phase_policy"], f"{path}.phase_policy", PHASE_POLICIES),
                root_policy=_enum(value["root_policy"], f"{path}.root_policy", ROOT_POLICIES),
                contact_policy=_enum(value["contact_policy"], f"{path}.contact_policy", CONTACT_POLICIES),
                region_policy=_enum(value["region_policy"], f"{path}.region_policy", REGION_POLICIES),
                interrupt_window=_string(value["interrupt_window"], f"{path}.interrupt_window"),
                fallback_transition_id=fallback_id,
            )
        )
    for index, transition in enumerate(transitions):
        if transition.fallback_transition_id is not None and transition.fallback_transition_id not in transition_ids:
            raise _path_error(
                f"$.transitions[{index}].fallback_transition_id",
                f"unknown transition {transition.fallback_transition_id!r}",
            )

    masks_raw = _mapping(raw["channel_masks"], "$.channel_masks")
    channel_masks = {
        _string(channel, "$.channel_masks key"): _string_tuple(regions, f"$.channel_masks.{channel}")
        for channel, regions in masks_raw.items()
    }
    fallbacks_raw = _mapping(raw["fallbacks"], "$.fallbacks")
    _keys(fallbacks_raw, "$.fallbacks", {"grounded_clip_id", "airborne_clip_id", "by_facing", "by_action"})
    grounded_fallback = _string(fallbacks_raw["grounded_clip_id"], "$.fallbacks.grounded_clip_id")
    airborne_fallback = _string(fallbacks_raw["airborne_clip_id"], "$.fallbacks.airborne_clip_id")
    if grounded_fallback not in clips or airborne_fallback not in clips:
        raise _path_error("$.fallbacks", "grounded and airborne fallbacks must name existing clips")
    by_facing = _mapping(fallbacks_raw["by_facing"], "$.fallbacks.by_facing")
    if set(by_facing) != FACINGS:
        raise _path_error("$.fallbacks.by_facing", "must define all eight facings exactly")
    by_action = _mapping(fallbacks_raw["by_action"], "$.fallbacks.by_action")
    for group_name, group in (("by_facing", by_facing), ("by_action", by_action)):
        for key, clip_id_value in group.items():
            clip_id = _string(clip_id_value, f"$.fallbacks.{group_name}.{key}")
            if clip_id not in clips:
                raise _path_error(f"$.fallbacks.{group_name}.{key}", f"unknown clip {clip_id!r}")

    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return AnimationGraph(
        schema_version=2,
        graph_id=graph_id,
        asset_set_id=asset_set_id,
        authored_fps=authored_fps,
        simulation_hz=simulation_hz,
        default_node_id=default_node_id,
        capability_tiers=capability_tiers,
        pose_catalog=catalog,
        pose_classification=classification,
        clips=clips,
        nodes=nodes,
        transitions=tuple(transitions),
        transition_recipes=recipes,
        channel_masks=channel_masks,
        fallbacks=dict(fallbacks_raw),
        source_sha256=hashlib.sha256(canonical).hexdigest(),
    )


@lru_cache(maxsize=16)
def _load_animation_graph_cached(path: str) -> AnimationGraph:
    return parse_animation_graph(_load_json(Path(path)))


def load_animation_graph(path: Path = ANIMATION_GRAPH_V2_PATH) -> AnimationGraph:
    return _load_animation_graph_cached(str(Path(path).resolve()))


@lru_cache(maxsize=1)
def load_reference_animation_graph_v2() -> AnimationGraph:
    return load_animation_graph()


def _sample_at_frame(clip: ClipDefinition, frame: int) -> Tuple[int, int]:
    cursor = 0
    for index, sample in enumerate(clip.samples):
        end = cursor + sample.duration_frames
        if frame < end:
            return index, frame - cursor
        cursor = end
    raise AssertionError("validated clip frame fell outside its samples")


def _ceil_div(numerator: int, denominator: int) -> int:
    return -(-numerator // denominator)


def _clip_markers(clip: ClipDefinition) -> Tuple[Tuple[int, str], ...]:
    cursor = 0
    markers = []
    for sample in clip.samples:
        for marker in sample.markers:
            markers.append((cursor + marker.frame_offset, marker.marker_id))
        cursor += sample.duration_frames
    return tuple(sorted(markers, key=lambda item: (item[0], item[1])))


def _markers_crossed(
    clip: ClipDefinition,
    previous_tick: int,
    current_tick: int,
    authored_fps: int,
    simulation_hz: int,
) -> Tuple[str, ...]:
    if current_tick < 0 or previous_tick >= current_tick:
        return ()
    markers = _clip_markers(clip)
    if not markers:
        return ()
    occurrences = []
    if clip.loop_mode == "loop":
        max_absolute_frame = (current_tick * authored_fps) // simulation_hz
        max_loop = max_absolute_frame // clip.total_frames
        loop_indexes = range(max_loop + 1)
    else:
        loop_indexes = range(1)
    for loop_index in loop_indexes:
        loop_frame = loop_index * clip.total_frames
        for marker_frame, marker_id in markers:
            absolute_frame = loop_frame + marker_frame
            event_tick = _ceil_div(absolute_frame * simulation_hz, authored_fps)
            if previous_tick < event_tick <= current_tick:
                occurrences.append((event_tick, absolute_frame, marker_id))
    occurrences.sort()
    return tuple(marker_id for _, _, marker_id in occurrences)


__all__ = [
    "ANIMATION_GRAPH_V2_PATH",
    "ANIMATION_GRAPH_V2_SCHEMA_PATH",
    "REFERENCE_POSE_LIBRARY_PATH",
    "REFERENCE_POSE_MANIFEST_PATH",
    "AnimationGraph",
    "AnimationGraphValidationError",
    "ClipDefinition",
    "ClipEvaluation",
    "ClipSample",
    "Marker",
    "NodeDefinition",
    "PoseClassification",
    "PoseMetadata",
    "TransitionDefinition",
    "TransitionRecipe",
    "load_animation_graph",
    "load_pose_catalog",
    "load_reference_animation_graph_v2",
    "parse_animation_graph",
]
