"""Deterministic CharacterCapabilityManifestV1 derivation and validation."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .animation_graph import (
    REFERENCE_POSE_MANIFEST_PATH,
    AnimationGraph,
    ClipDefinition,
    load_animation_graph,
)
from .artifact_hashing import canonical_json_v1, sha256_ref
from .character_package import WIZARD_JOE_PACKAGE_PATH, CharacterPackage, load_character_package
from .gestures import ACTION_TO_CHANNELS
from .models import ACTIONS, DIRECTIONS, EXPRESSIONS, MOUTH_SHAPES, STAFF_STATES, UPPER_BODY_ACTIONS
from .mouth import MOUTH_CELLS
from .performance_scheduler import (
    REDUCED_PROHIBITED_CHANNELS,
    STILL_ALLOWED_CHANNELS,
    TRACK_DEFAULT_CHANNEL,
)
from .semantic_animation import SEMANTIC_ANIMATION_MAP_PATH


ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS_DIR = Path(__file__).with_name("definitions")
SCHEMA_PATH = DEFINITIONS_DIR / "character_capability_manifest_v1.schema.json"
EXPRESSIONS_PATH = DEFINITIONS_DIR / "expressions.json"
MANIFEST_ID_PREFIX = "character-capabilities:"
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

_ROOT_FIELDS = {
    "schema_version",
    "manifest_id",
    "character",
    "permission_world",
    "sources",
    "counts",
    "poses",
    "capabilities",
    "diagnostics",
    "manifest_sha256",
}
_PERMISSION_WORLD_FIELDS = {"bindings"}
_PERMISSION_WORLD_BINDING_FIELDS = {
    "world_state_ids",
    "effect_ids",
    "prop_ids",
    "requirements",
}
_PERMISSION_WORLD_REQUIREMENT_FIELDS = {
    "capability_kind",
    "required_scope_class",
    "purpose_code",
}
_CHARACTER_FIELDS = {
    "character_id",
    "display_name",
    "renderer",
    "default_pose_id",
    "package_capabilities",
}
_SOURCE_FIELDS = {
    "package_sha256",
    "pose_library_sha256",
    "animation_graph_sha256",
    "animation_graph_content_sha256",
    "pose_source_manifest_sha256",
    "expressions_sha256",
    "semantic_mapping_sha256",
    "runtime_vocabulary_sha256",
    "runtime_mapping_sha256",
    "evidence",
}
_COUNT_FIELDS = {
    "package_capability_count",
    "clip_count",
    "node_count",
    "transition_count",
    "pose_count",
    "graph_admitted_pose_count",
    "diagnostic_only_pose_count",
    "expression_count",
    "mouth_shape_count",
    "capability_count",
    "diagnostic_count",
}
_POSE_FIELDS = {
    "pose_id",
    "admission",
    "roles",
    "capability_tier",
    "quality_status",
    "facing",
    "locomotion",
    "action_ids",
    "clip_ids",
    "channel_ownership",
    "support_contact",
    "planted_anchor",
    "altitude_class",
    "wing_mode",
    "staff_mode",
    "cell_count",
    "content_sha256",
    "source_asset_sha256",
    "evidence_sha256",
}
_CAPABILITY_FIELDS = {
    "capability_id",
    "category",
    "semantic_meaning",
    "emotional_range",
    "energy_range",
    "admission",
    "mapping",
    "timing",
    "transitions",
    "contacts",
    "compatibility",
    "accessibility",
    "fallback",
    "quality",
    "provenance",
    "runtime_contract",
    "budget",
}
_MAPPING_FIELDS = {
    "action_ids",
    "clip_ids",
    "node_ids",
    "pose_ids",
    "expression_ids",
    "mouth_ids",
    "gaze_ids",
    "locomotion_ids",
    "flight_ids",
    "effect_ids",
    "prop_ids",
    "facings",
    "stage_requirements",
    "channels",
    "ownership",
}
_TIMING_FIELDS = {"authored_fps", "duration_frames", "loop_mode"}
_TRANSITION_FIELDS = {
    "legal_entry_node_ids",
    "legal_exit_clip_ids",
    "entry_markers",
    "exit_markers",
    "minimum_hold_ticks",
    "interrupt_policy",
    "commit_markers",
    "recovery_markers",
}
_CONTACT_FIELDS = {"root_policy", "support_contacts", "planted_anchors"}
_COMPATIBILITY_FIELDS = {
    "speech",
    "locomotion",
    "compatible_channels",
    "disabled_channel_behavior",
}
_ACCESSIBILITY_FIELDS = {"full", "reduced", "still", "enforcement"}
_FALLBACK_FIELDS = {"intent", "capability_id", "reason_code"}
_QUALITY_FIELDS = {"tier", "status"}
_PROVENANCE_FIELDS = {"source_ids", "evidence_sha256", "content_sha256"}
_RUNTIME_FIELDS = {"renderer", "runtime_api_version", "schema_version"}
_BUDGET_FIELDS = {
    "preload_required",
    "frame_cell_count_max",
    "memory_bytes",
    "cost_status",
}
_DIAGNOSTIC_FIELDS = {"severity", "code", "subject_id", "message"}


class CharacterCapabilityManifestValidationError(ValueError):
    """A stable, path-addressed capability contract failure."""

    def __init__(self, code: str, path: str, message: str) -> None:
        self.code = code
        self.path = path
        self.message = message
        super().__init__("{} at {}: {}".format(code, path, message))


@dataclass(frozen=True)
class CapabilityDiagnostic:
    severity: str
    code: str
    subject_id: str
    message: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "subject_id": self.subject_id,
            "message": self.message,
        }


def _error(code: str, path: str, message: str) -> CharacterCapabilityManifestValidationError:
    return CharacterCapabilityManifestValidationError(code, path, message)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _error("source_invalid", str(path), str(exc)) from exc


def _file_sha256(path: Path) -> str:
    try:
        return sha256_ref(path.read_bytes())
    except OSError as exc:
        raise _error("source_missing", str(path), str(exc)) from exc


def _optional_file_sha256(path: Path) -> Optional[str]:
    return _file_sha256(path) if path.is_file() else None


def _hash_value(value: object) -> str:
    return sha256_ref(canonical_json_v1(value))


def _source_value_hash(value: object) -> str:
    """Hash source JSON that may contain authored floats without exporting them."""

    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return sha256_ref(encoded)


def canonical_character_capability_manifest(value: Mapping[str, Any]) -> bytes:
    """Return canonical JSON bytes; arrays retain their declared contract order."""

    return canonical_json_v1(value)


def _source_asset_path(source: str) -> Path:
    candidate = Path(source)
    if candidate.is_absolute():
        return candidate
    if source.startswith("evidence/") or source.startswith("assets/"):
        return ROOT / candidate
    return REFERENCE_POSE_MANIFEST_PATH.parent / candidate


def _evidence_sources() -> List[Dict[str, str]]:
    candidates = (
        (
            "animation_quality_integrity",
            ROOT / "evidence/animation-quality/final/evidence-integrity.json",
        ),
        (
            "animation_transition_metrics",
            ROOT / "evidence/animation-quality/final/transition-metrics.json",
        ),
        (
            "animation_deterministic_replay",
            ROOT / "evidence/animation-quality/final/replay/replay-manifest.json",
        ),
    )
    return [
        {"evidence_id": evidence_id, "sha256": _file_sha256(path)}
        for evidence_id, path in candidates
        if path.is_file()
    ]


def _runtime_vocabulary() -> Dict[str, List[str]]:
    return {
        "actions": list(ACTIONS),
        "directions": list(DIRECTIONS),
        "expressions": list(EXPRESSIONS),
        "mouth_shapes": list(MOUTH_SHAPES),
        "staff_states": list(STAFF_STATES),
        "upper_body_actions": list(UPPER_BODY_ACTIONS),
    }


def _runtime_mapping() -> Dict[str, Any]:
    return {
        "action_channels": {
            action: list(ACTION_TO_CHANNELS[action]) for action in sorted(ACTION_TO_CHANNELS)
        },
        "reduced_prohibited_channels": sorted(REDUCED_PROHIBITED_CHANNELS),
        "still_allowed_channels": sorted(STILL_ALLOWED_CHANNELS),
        "track_default_channels": {
            track: TRACK_DEFAULT_CHANNEL[track] for track in sorted(TRACK_DEFAULT_CHANNEL)
        },
    }


def _markers(clip: ClipDefinition) -> Tuple[str, ...]:
    return tuple(
        marker.marker_id
        for sample in clip.samples
        for marker in sample.markers
    )


def _tier_for_pose_ids(graph: AnimationGraph, pose_ids: Sequence[str]) -> str:
    tiers = {graph.pose_classification[pose_id].capability_tier for pose_id in pose_ids}
    if "C" in tiers:
        return "C"
    if "B" in tiers:
        return "B"
    return "A"


def _empty_mapping() -> Dict[str, Any]:
    return {
        "action_ids": [],
        "clip_ids": [],
        "node_ids": [],
        "pose_ids": [],
        "expression_ids": [],
        "mouth_ids": [],
        "gaze_ids": [],
        "locomotion_ids": [],
        "flight_ids": [],
        "effect_ids": [],
        "prop_ids": [],
        "facings": [],
        "stage_requirements": [],
        "channels": [],
        "ownership": "none",
    }


def _empty_transitions() -> Dict[str, Any]:
    return {
        "legal_entry_node_ids": [],
        "legal_exit_clip_ids": [],
        "entry_markers": [],
        "exit_markers": [],
        "minimum_hold_ticks": 0,
        "interrupt_policy": "not_applicable",
        "commit_markers": [],
        "recovery_markers": [],
    }


def _base_capability(
    capability_id: str,
    category: str,
    semantic_meaning: str,
    admission: str,
    renderer: str,
) -> Dict[str, Any]:
    return {
        "capability_id": capability_id,
        "category": category,
        "semantic_meaning": semantic_meaning,
        "emotional_range": [],
        "energy_range": [],
        "admission": admission,
        "mapping": _empty_mapping(),
        "timing": {"authored_fps": None, "duration_frames": None, "loop_mode": "not_applicable"},
        "transitions": _empty_transitions(),
        "contacts": {"root_policy": "not_applicable", "support_contacts": [], "planted_anchors": []},
        "compatibility": {
            "speech": "not_applicable",
            "locomotion": "not_applicable",
            "compatible_channels": [],
            "disabled_channel_behavior": "project_owned_channels_and_suppress_if_none",
        },
        "accessibility": {
            "full": "unsupported" if admission == "unsupported" else "admitted",
            "reduced": "unsupported" if admission == "unsupported" else "admitted",
            "still": "unsupported" if admission == "unsupported" else "admitted",
            "enforcement": "compiler_required_runtime_unverified",
        },
        "fallback": {"intent": None, "capability_id": None, "reason_code": None},
        "quality": {"tier": None, "status": "unsupported" if admission == "unsupported" else "runtime_supported"},
        "provenance": {"source_ids": [], "evidence_sha256": [], "content_sha256": []},
        "runtime_contract": {
            "renderer": renderer,
            "runtime_api_version": "wizard_avatar.v1",
            "schema_version": 1,
        },
        "budget": {
            "preload_required": False,
            "frame_cell_count_max": 0,
            "memory_bytes": None,
            "cost_status": "not_applicable",
        },
    }


def _clip_capability(
    package: CharacterPackage,
    graph: AnimationGraph,
    clip: ClipDefinition,
    evidence_hashes: Sequence[str],
) -> Dict[str, Any]:
    result = _base_capability(
        "clip:" + clip.clip_id,
        "animation_clip",
        clip.family,
        "graph_admitted",
        package.renderer,
    )
    nodes = sorted(node.node_id for node in graph.nodes.values() if node.clip_id == clip.clip_id)
    actions = sorted({action for node_id in nodes for action in graph.nodes[node_id].actions})
    mobility = sorted({mode for node_id in nodes for mode in graph.nodes[node_id].mobility_modes})
    pose_ids = sorted({sample.pose_id for sample in clip.samples})
    source_nodes = sorted(
        {
            transition.source_node_id
            for transition in graph.transitions
            if transition.target_node_id in nodes
        }
    )
    all_markers = _markers(clip)
    support_contacts = sorted({sample.support_contact for sample in clip.samples})
    planted_anchors = sorted(
        {sample.planted_anchor for sample in clip.samples if sample.planted_anchor is not None}
    )
    frame_cells = max(graph.pose_catalog[pose_id].cell_count for pose_id in pose_ids)
    airborne = any(
        graph.pose_classification[pose_id].altitude_class in {"airborne", "takeoff", "landing"}
        for pose_id in pose_ids
    )
    fallback_clip = str(
        graph.fallbacks["airborne_clip_id" if airborne else "grounded_clip_id"]
    )
    reduced_channels = [
        channel for channel in clip.channel_ownership if channel not in REDUCED_PROHIBITED_CHANNELS
    ]
    still_channels = [
        channel for channel in clip.channel_ownership if channel in STILL_ALLOWED_CHANNELS
    ]
    result["mapping"] = {
        "action_ids": actions,
        "clip_ids": [clip.clip_id],
        "node_ids": nodes,
        "pose_ids": pose_ids,
        "expression_ids": [],
        "mouth_ids": [],
        "gaze_ids": [],
        "locomotion_ids": mobility,
        "flight_ids": [
            mode
            for mode in mobility
            if mode in {"takeoff", "hover", "flight_travel", "flight_bank", "landing"}
        ],
        "effect_ids": ["magic_effect"] if "effect" in clip.channel_ownership else [],
        "prop_ids": ["staff"] if "staff" in clip.channel_ownership else [],
        "facings": list(clip.supported_facings),
        "stage_requirements": [],
        "channels": list(clip.channel_ownership),
        "ownership": "whole_pose",
    }
    result["timing"] = {
        "authored_fps": clip.authored_fps or graph.authored_fps,
        "duration_frames": clip.total_frames,
        "loop_mode": clip.loop_mode,
    }
    result["transitions"] = {
        "legal_entry_node_ids": source_nodes,
        "legal_exit_clip_ids": list(clip.legal_successors),
        "entry_markers": list(clip.entry_markers),
        "exit_markers": list(clip.exit_markers),
        "minimum_hold_ticks": clip.minimum_hold_ticks,
        "interrupt_policy": clip.interrupt_policy,
        "commit_markers": sorted({marker for marker in all_markers if marker.endswith("_commit")}),
        "recovery_markers": sorted(
            {
                marker
                for marker in all_markers
                if "recoverable" in marker or marker.endswith("_settled")
            }
        ),
    }
    result["contacts"] = {
        "root_policy": clip.root_policy,
        "support_contacts": support_contacts,
        "planted_anchors": planted_anchors,
    }
    result["compatibility"] = {
        "speech": "compatible" if "mouth" not in clip.channel_ownership else "incompatible",
        "locomotion": "compatible" if clip.family in {"idle", "locomotion", "run", "flight"} else "conditional",
        "compatible_channels": [
            channel for channel in ("face", "mouth", "speech") if channel not in clip.channel_ownership
        ],
        "disabled_channel_behavior": "project_owned_channels_and_suppress_if_none",
    }
    result["accessibility"] = {
        "full": "admitted",
        "reduced": "admitted_by_scheduler_projection" if reduced_channels else "suppressed",
        "still": "admitted_by_scheduler_projection" if still_channels else "fallback_characterful_neutral",
        "enforcement": "compiler_required_runtime_unverified",
    }
    result["fallback"] = {
        "intent": "characterful_neutral",
        "capability_id": "clip:" + fallback_clip,
        "reason_code": "graph_declared_fallback",
    }
    result["quality"] = {
        "tier": _tier_for_pose_ids(graph, pose_ids),
        "status": "graph_admitted_evidence_bound",
    }
    result["provenance"] = {
        "source_ids": ["character_package", "animation_graph", "pose_library"],
        "evidence_sha256": list(evidence_hashes),
        "content_sha256": [
            _hash_value(
                {
                    "clip_id": clip.clip_id,
                    "node_ids": nodes,
                    "pose_ids": pose_ids,
                    "total_frames": clip.total_frames,
                    "markers": list(all_markers),
                }
            )
        ],
    }
    result["budget"] = {
        "preload_required": True,
        "frame_cell_count_max": frame_cells,
        "memory_bytes": None,
        "cost_status": "frame_cells_measured_memory_unmeasured",
    }
    return result


def _overlay_capability(
    package: CharacterPackage,
    kind: str,
    item_id: str,
    payload: object,
    evidence_hashes: Sequence[str],
) -> Dict[str, Any]:
    capability_id = ("expression:" if kind == "expression" else "mouth:") + item_id
    result = _base_capability(
        capability_id,
        kind + "_overlay",
        item_id,
        "runtime_overlay",
        package.renderer,
    )
    mapping = _empty_mapping()
    if kind == "expression":
        mapping["expression_ids"] = [item_id]
        mouth = payload.get("mouth") if isinstance(payload, Mapping) else None
        mapping["mouth_ids"] = [mouth] if isinstance(mouth, str) else []
        mapping["channels"] = ["face", "mouth"]
        frame_cells = 0
    else:
        mapping["mouth_ids"] = [item_id]
        mapping["channels"] = ["mouth"]
        frame_cells = len(MOUTH_CELLS[item_id])
    mapping["ownership"] = "independently_compositable"
    result["mapping"] = mapping
    result["compatibility"] = {
        "speech": "compatible",
        "locomotion": "compatible",
        "compatible_channels": ["body", "locomotion", "speech"],
        "disabled_channel_behavior": "project_owned_channels_and_suppress_if_none",
    }
    result["accessibility"] = {
        "full": "admitted",
        "reduced": "admitted",
        "still": "admitted",
        "enforcement": "runtime_mapped",
    }
    result["fallback"] = {
        "intent": "neutral",
        "capability_id": "expression:neutral" if kind == "expression" else "mouth:closed",
        "reason_code": "runtime_declared_fallback",
    }
    result["quality"] = {"tier": "runtime", "status": "runtime_supported"}
    result["provenance"] = {
        "source_ids": ["runtime_vocabulary", kind + "_mapping"],
        "evidence_sha256": list(evidence_hashes),
        "content_sha256": [_source_value_hash(payload)],
    }
    result["budget"] = {
        "preload_required": False,
        "frame_cell_count_max": frame_cells,
        "memory_bytes": None,
        "cost_status": "frame_cells_measured_memory_unmeasured" if kind == "mouth" else "unmeasured",
    }
    return result


def _ownership_capability(
    package: CharacterPackage,
    channel: str,
    evidence_hashes: Sequence[str],
) -> Dict[str, Any]:
    result = _base_capability(
        "ownership:" + channel,
        "ownership_declaration",
        channel + " remains part of an atomic pose snapshot",
        "graph_admitted",
        package.renderer,
    )
    mapping = _empty_mapping()
    mapping["channels"] = [channel]
    mapping["ownership"] = "whole_pose"
    if channel == "staff":
        mapping["prop_ids"] = ["staff"]
    result["mapping"] = mapping
    result["quality"] = {"tier": "contract", "status": "whole_pose_only"}
    result["provenance"] = {
        "source_ids": ["animation_graph", "runtime_renderer"],
        "evidence_sha256": list(evidence_hashes),
        "content_sha256": [_hash_value({"channel": channel, "ownership": "whole_pose"})],
    }
    return result


def _permission_prop_overlay_capability(
    package: CharacterPackage,
) -> Dict[str, Any]:
    result = _base_capability(
        "prop:memory_notebook",
        "permission_prop_overlay",
        "permission-bound conversation continuity notebook indicator",
        "runtime_overlay",
        package.renderer,
    )
    mapping = _empty_mapping()
    mapping["prop_ids"] = ["memory_notebook"]
    mapping["channels"] = ["permission_world"]
    mapping["ownership"] = "independently_compositable"
    result["mapping"] = mapping
    result["compatibility"] = {
        "speech": "compatible",
        "locomotion": "compatible",
        "compatible_channels": ["body", "face", "locomotion", "mouth", "speech"],
        "disabled_channel_behavior": "suppress_without_current_permission",
    }
    result["accessibility"] = {
        "full": "admitted",
        "reduced": "admitted",
        "still": "admitted",
        "enforcement": "runtime_mapped",
    }
    result["fallback"] = {
        "intent": None,
        "capability_id": None,
        "reason_code": "permission_world_authority_required",
    }
    result["quality"] = {"tier": "runtime", "status": "runtime_supported"}
    result["provenance"] = {
        "source_ids": ["permission_world", "runtime_renderer"],
        "evidence_sha256": [],
        "content_sha256": [
            _hash_value(
                {
                    "prop_id": "memory_notebook",
                    "renderer": "projected_square_cells",
                    "width_cells": 7,
                    "height_cells": 7,
                }
            )
        ],
    }
    result["budget"] = {
        "preload_required": False,
        "frame_cell_count_max": 49,
        "memory_bytes": None,
        "cost_status": "frame_cells_measured_memory_unmeasured",
    }
    return result


def _unsupported_capability(
    package: CharacterPackage,
    surface: str,
    evidence_hashes: Sequence[str],
) -> Dict[str, Any]:
    result = _base_capability(
        "unsupported:" + surface,
        "unsupported_surface",
        surface,
        "unsupported",
        package.renderer,
    )
    result["fallback"] = {
        "intent": "characterful_neutral",
        "capability_id": "clip:idle_front",
        "reason_code": "no_runtime_mapping",
    }
    result["provenance"] = {
        "source_ids": ["runtime_vocabulary", "animation_graph"],
        "evidence_sha256": list(evidence_hashes),
        "content_sha256": [_hash_value({"surface": surface, "admission": "unsupported"})],
    }
    return result


def _pose_records(
    graph: AnimationGraph,
    pose_library_raw: Mapping[str, Any],
    evidence_hashes: Sequence[str],
) -> List[Dict[str, Any]]:
    raw_by_id = {
        str(item["id"]): item
        for item in pose_library_raw.get("poses", [])
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    }
    clips_by_pose: Dict[str, List[str]] = {pose_id: [] for pose_id in graph.pose_catalog}
    channels_by_pose: Dict[str, set] = {pose_id: set() for pose_id in graph.pose_catalog}
    for clip in graph.clips.values():
        for sample in clip.samples:
            clips_by_pose[sample.pose_id].append(clip.clip_id)
            channels_by_pose[sample.pose_id].update(clip.channel_ownership)

    records: List[Dict[str, Any]] = []
    for pose_id in sorted(graph.pose_catalog):
        metadata = graph.pose_catalog[pose_id]
        classification = graph.pose_classification[pose_id]
        admitted = "clip_sample" in classification.roles
        # Source PNGs are workstation-only audit evidence. Runtime authority is
        # the packaged pixel graph, so capability derivation must not depend on
        # those files being mounted (or even present) on the playback machine.
        # A future compiler may embed their verified digest in the portable
        # pose record; absent that field, the contract truthfully reports null.
        raw_source_asset_sha = raw_by_id[pose_id].get("source_asset_sha256")
        source_asset_sha = (
            raw_source_asset_sha
            if isinstance(raw_source_asset_sha, str)
            else None
        )
        records.append(
            {
                "pose_id": pose_id,
                "admission": "graph_admitted" if admitted else "diagnostic_only",
                "roles": list(classification.roles),
                "capability_tier": classification.capability_tier,
                "quality_status": "graph_admitted_evidence_bound" if admitted else "diagnostic_only_not_selectable",
                "facing": metadata.facing,
                "locomotion": metadata.locomotion,
                "action_ids": list(metadata.actions),
                "clip_ids": sorted(set(clips_by_pose[pose_id])),
                "channel_ownership": sorted(channels_by_pose[pose_id]),
                "support_contact": classification.support_contact,
                "planted_anchor": classification.planted_anchor,
                "altitude_class": classification.altitude_class,
                "wing_mode": classification.wing_mode,
                "staff_mode": classification.staff_mode,
                "cell_count": metadata.cell_count,
                "content_sha256": _source_value_hash(raw_by_id[pose_id]),
                "source_asset_sha256": source_asset_sha,
                "evidence_sha256": list(evidence_hashes),
            }
        )
    return records


def _diagnostics(graph: AnimationGraph) -> Tuple[CapabilityDiagnostic, ...]:
    mapped_actions = {action for node in graph.nodes.values() for action in node.actions}
    mobility_modes = {mode for node in graph.nodes.values() for mode in node.mobility_modes}
    if "grounded_idle" in mobility_modes:
        mapped_actions.add("idle")
    if "grounded_walk" in mobility_modes:
        mapped_actions.add("walking")
    diagnostics = [
        CapabilityDiagnostic(
            "warning",
            "runtime_action_unmapped",
            action,
            "Runtime action has no graph node or clip-family mapping.",
        )
        for action in sorted(set(ACTIONS) - mapped_actions)
    ]
    diagnostics.extend(
        (
            CapabilityDiagnostic(
                "info",
                "unsupported_surface",
                "dance",
                "Dance has no admitted graph clip or runtime application mapping.",
            ),
            CapabilityDiagnostic(
                "warning",
                "runtime_accessibility_unverified",
                "motion_profiles",
                "Reduced and still behavior requires compiler enforcement; final runtime enforcement is unverified.",
            ),
        )
    )
    return tuple(diagnostics)


def _build_manifest(package_path: Path) -> Dict[str, Any]:
    package_path = Path(package_path).resolve()
    package = load_character_package(package_path)
    graph = load_animation_graph(package.animation_graph)
    pose_library_raw = _read_json(package.pose_library)
    expression_raw = _read_json(EXPRESSIONS_PATH)
    semantic_raw = _read_json(SEMANTIC_ANIMATION_MAP_PATH)
    evidence = _evidence_sources()
    evidence_hashes = [item["sha256"] for item in evidence]

    poses = _pose_records(graph, pose_library_raw, evidence_hashes)
    capabilities = [
        _clip_capability(package, graph, graph.clips[clip_id], evidence_hashes)
        for clip_id in sorted(graph.clips)
    ]
    capabilities.extend(
        _overlay_capability(package, "expression", expression_id, expression_raw[expression_id], evidence_hashes)
        for expression_id in sorted(EXPRESSIONS)
    )
    capabilities.extend(
        _overlay_capability(package, "mouth", mouth_id, MOUTH_CELLS[mouth_id], evidence_hashes)
        for mouth_id in sorted(MOUTH_SHAPES)
    )
    capabilities.extend(
        _ownership_capability(package, channel, evidence_hashes)
        for channel in ("staff", "wings")
    )
    capabilities.append(_permission_prop_overlay_capability(package))
    capabilities.append(_unsupported_capability(package, "dance", evidence_hashes))
    capabilities.sort(key=lambda item: item["capability_id"])
    diagnostics = _diagnostics(graph)

    manifest: Dict[str, Any] = {
        "schema_version": 1,
        "manifest_id": MANIFEST_ID_PREFIX + package.character_id + ":v1",
        "character": {
            "character_id": package.character_id,
            "display_name": package.display_name,
            "renderer": package.renderer,
            "default_pose_id": package.default_pose_id,
            "package_capabilities": sorted(package.capabilities),
        },
        "permission_world": {
            "bindings": {
                "world_state_ids": [],
                "effect_ids": [],
                "prop_ids": ["memory_notebook"],
                "requirements": [
                    {
                        "capability_kind": "prop:memory_notebook",
                        "required_scope_class": "current_character",
                        "purpose_code": "conversation_continuity",
                    }
                ],
            }
        },
        "sources": {
            "package_sha256": _file_sha256(package_path),
            "pose_library_sha256": _file_sha256(package.pose_library),
            "animation_graph_sha256": _file_sha256(package.animation_graph),
            "animation_graph_content_sha256": "sha256:" + graph.source_sha256,
            "pose_source_manifest_sha256": _file_sha256(REFERENCE_POSE_MANIFEST_PATH),
            "expressions_sha256": _file_sha256(EXPRESSIONS_PATH),
            "semantic_mapping_sha256": _file_sha256(SEMANTIC_ANIMATION_MAP_PATH),
            "runtime_vocabulary_sha256": _hash_value(_runtime_vocabulary()),
            "runtime_mapping_sha256": _hash_value(_runtime_mapping()),
            "evidence": evidence,
        },
        "counts": {
            "package_capability_count": len(package.capabilities),
            "clip_count": len(graph.clips),
            "node_count": len(graph.nodes),
            "transition_count": len(graph.transitions),
            "pose_count": len(poses),
            "graph_admitted_pose_count": sum(pose["admission"] == "graph_admitted" for pose in poses),
            "diagnostic_only_pose_count": sum(pose["admission"] == "diagnostic_only" for pose in poses),
            "expression_count": len(EXPRESSIONS),
            "mouth_shape_count": len(MOUTH_SHAPES),
            "capability_count": len(capabilities),
            "diagnostic_count": len(diagnostics),
        },
        "poses": poses,
        "capabilities": capabilities,
        "diagnostics": [diagnostic.as_dict() for diagnostic in diagnostics],
    }
    manifest["manifest_sha256"] = _hash_value(manifest)
    return manifest


def derive_character_capability_manifest(
    package_path: Path = WIZARD_JOE_PACKAGE_PATH,
) -> Dict[str, Any]:
    """Derive, validate, and return a fresh manifest from production sources."""

    manifest = _build_manifest(Path(package_path))
    validate_character_capability_manifest(manifest)
    return manifest


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error("invalid_type", path, "expected object")
    return value


def _sequence(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise _error("invalid_type", path, "expected array")
    return value


def _closed(value: Mapping[str, Any], expected: Iterable[str], path: str) -> None:
    expected_set = set(expected)
    missing = sorted(expected_set - set(value))
    if missing:
        raise _error("missing_field", path, "missing fields: {}".format(", ".join(missing)))
    extra = sorted(set(value) - expected_set)
    if extra:
        raise _error("unknown_field", path, "unknown fields: {}".format(", ".join(extra)))


def _text(value: Any, path: str, allow_none: bool = False) -> Optional[str]:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not value:
        raise _error("invalid_type", path, "expected nonempty text")
    return value


def _integer(value: Any, path: str, allow_none: bool = False) -> Optional[int]:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _error("invalid_type", path, "expected nonnegative integer")
    return value


def _texts(value: Any, path: str) -> List[str]:
    result = [_text(item, "{}[{}]".format(path, index)) for index, item in enumerate(_sequence(value, path))]
    strings = [item for item in result if item is not None]
    if len(strings) != len(set(strings)):
        raise _error("duplicate_id", path, "array values must be unique")
    return strings


def _hash(value: Any, path: str, allow_none: bool = False) -> Optional[str]:
    text = _text(value, path, allow_none=allow_none)
    if text is not None and SHA256_PATTERN.fullmatch(text) is None:
        raise _error("invalid_hash", path, "expected lowercase sha256 reference")
    return text


def _validate_capability(value: Any, index: int) -> None:
    path = "$.capabilities[{}]".format(index)
    capability = _mapping(value, path)
    _closed(capability, _CAPABILITY_FIELDS, path)
    _text(capability["capability_id"], path + ".capability_id")
    _text(capability["category"], path + ".category")
    _text(capability["semantic_meaning"], path + ".semantic_meaning")
    _texts(capability["emotional_range"], path + ".emotional_range")
    _texts(capability["energy_range"], path + ".energy_range")
    if capability["admission"] not in {"graph_admitted", "runtime_overlay", "unsupported"}:
        raise _error("invalid_enum", path + ".admission", "invalid capability admission")

    mapping = _mapping(capability["mapping"], path + ".mapping")
    _closed(mapping, _MAPPING_FIELDS, path + ".mapping")
    for field in sorted(_MAPPING_FIELDS - {"ownership"}):
        _texts(mapping[field], path + ".mapping." + field)
    if mapping["ownership"] not in {"whole_pose", "independently_compositable", "none"}:
        raise _error("invalid_enum", path + ".mapping.ownership", "invalid ownership")

    timing = _mapping(capability["timing"], path + ".timing")
    _closed(timing, _TIMING_FIELDS, path + ".timing")
    _integer(timing["authored_fps"], path + ".timing.authored_fps", allow_none=True)
    _integer(timing["duration_frames"], path + ".timing.duration_frames", allow_none=True)
    _text(timing["loop_mode"], path + ".timing.loop_mode")

    transitions = _mapping(capability["transitions"], path + ".transitions")
    _closed(transitions, _TRANSITION_FIELDS, path + ".transitions")
    for field in sorted(_TRANSITION_FIELDS - {"minimum_hold_ticks", "interrupt_policy"}):
        _texts(transitions[field], path + ".transitions." + field)
    _integer(transitions["minimum_hold_ticks"], path + ".transitions.minimum_hold_ticks")
    _text(transitions["interrupt_policy"], path + ".transitions.interrupt_policy")

    contacts = _mapping(capability["contacts"], path + ".contacts")
    _closed(contacts, _CONTACT_FIELDS, path + ".contacts")
    _text(contacts["root_policy"], path + ".contacts.root_policy")
    _texts(contacts["support_contacts"], path + ".contacts.support_contacts")
    _texts(contacts["planted_anchors"], path + ".contacts.planted_anchors")

    compatibility = _mapping(capability["compatibility"], path + ".compatibility")
    _closed(compatibility, _COMPATIBILITY_FIELDS, path + ".compatibility")
    for field in ("speech", "locomotion", "disabled_channel_behavior"):
        _text(compatibility[field], path + ".compatibility." + field)
    _texts(compatibility["compatible_channels"], path + ".compatibility.compatible_channels")

    accessibility = _mapping(capability["accessibility"], path + ".accessibility")
    _closed(accessibility, _ACCESSIBILITY_FIELDS, path + ".accessibility")
    for field in sorted(_ACCESSIBILITY_FIELDS):
        _text(accessibility[field], path + ".accessibility." + field)

    fallback = _mapping(capability["fallback"], path + ".fallback")
    _closed(fallback, _FALLBACK_FIELDS, path + ".fallback")
    for field in sorted(_FALLBACK_FIELDS):
        _text(fallback[field], path + ".fallback." + field, allow_none=True)

    quality = _mapping(capability["quality"], path + ".quality")
    _closed(quality, _QUALITY_FIELDS, path + ".quality")
    _text(quality["tier"], path + ".quality.tier", allow_none=True)
    _text(quality["status"], path + ".quality.status")

    provenance = _mapping(capability["provenance"], path + ".provenance")
    _closed(provenance, _PROVENANCE_FIELDS, path + ".provenance")
    _texts(provenance["source_ids"], path + ".provenance.source_ids")
    for field in ("evidence_sha256", "content_sha256"):
        for item_index, item in enumerate(_sequence(provenance[field], path + ".provenance." + field)):
            _hash(item, "{}.provenance.{}[{}]".format(path, field, item_index))

    runtime = _mapping(capability["runtime_contract"], path + ".runtime_contract")
    _closed(runtime, _RUNTIME_FIELDS, path + ".runtime_contract")
    _text(runtime["renderer"], path + ".runtime_contract.renderer")
    _text(runtime["runtime_api_version"], path + ".runtime_contract.runtime_api_version")
    if runtime["schema_version"] != 1:
        raise _error("schema_version_unsupported", path + ".runtime_contract.schema_version", "must be 1")

    budget = _mapping(capability["budget"], path + ".budget")
    _closed(budget, _BUDGET_FIELDS, path + ".budget")
    if not isinstance(budget["preload_required"], bool):
        raise _error("invalid_type", path + ".budget.preload_required", "expected boolean")
    _integer(budget["frame_cell_count_max"], path + ".budget.frame_cell_count_max")
    _integer(budget["memory_bytes"], path + ".budget.memory_bytes", allow_none=True)
    _text(budget["cost_status"], path + ".budget.cost_status")


def validate_character_capability_manifest(value: Mapping[str, Any]) -> None:
    """Strictly validate structure, references, admission, counts, and hash."""

    root = _mapping(value, "$")
    _closed(root, _ROOT_FIELDS, "$")
    if root["schema_version"] != 1 or isinstance(root["schema_version"], bool):
        raise _error("schema_version_unsupported", "$.schema_version", "must be 1")
    manifest_id = _text(root["manifest_id"], "$.manifest_id")
    character = _mapping(root["character"], "$.character")
    _closed(character, _CHARACTER_FIELDS, "$.character")
    character_id = _text(character["character_id"], "$.character.character_id")
    if manifest_id != MANIFEST_ID_PREFIX + character_id + ":v1":
        raise _error("identity_mismatch", "$.manifest_id", "manifest ID does not bind character ID")
    for field in ("display_name", "renderer", "default_pose_id"):
        _text(character[field], "$.character." + field)
    _texts(character["package_capabilities"], "$.character.package_capabilities")
    if character["package_capabilities"] != sorted(character["package_capabilities"]):
        raise _error("invalid_order", "$.character.package_capabilities", "values must be sorted")

    permission_world = _mapping(root["permission_world"], "$.permission_world")
    _closed(permission_world, _PERMISSION_WORLD_FIELDS, "$.permission_world")
    bindings = _mapping(permission_world["bindings"], "$.permission_world.bindings")
    _closed(bindings, _PERMISSION_WORLD_BINDING_FIELDS, "$.permission_world.bindings")
    for field in sorted(_PERMISSION_WORLD_BINDING_FIELDS):
        if field == "requirements":
            continue
        values = _texts(bindings[field], "$.permission_world.bindings." + field)
        if values != sorted(values):
            raise _error(
                "invalid_order",
                "$.permission_world.bindings." + field,
                "values must be sorted",
            )
    requirements = _sequence(
        bindings["requirements"],
        "$.permission_world.bindings.requirements",
    )
    requirement_capabilities = []
    for index, raw_requirement in enumerate(requirements):
        path = "$.permission_world.bindings.requirements[{}]".format(index)
        requirement = _mapping(raw_requirement, path)
        _closed(requirement, _PERMISSION_WORLD_REQUIREMENT_FIELDS, path)
        for field in sorted(_PERMISSION_WORLD_REQUIREMENT_FIELDS):
            _text(requirement[field], path + "." + field)
        requirement_capabilities.append(requirement["capability_kind"])
    if requirement_capabilities != sorted(set(requirement_capabilities)):
        raise _error(
            "invalid_order",
            "$.permission_world.bindings.requirements",
            "requirements must be unique and sorted by capability_kind",
        )

    sources = _mapping(root["sources"], "$.sources")
    _closed(sources, _SOURCE_FIELDS, "$.sources")
    for field in sorted(_SOURCE_FIELDS - {"evidence"}):
        _hash(sources[field], "$.sources." + field)
    evidence_ids = set()
    for index, item in enumerate(_sequence(sources["evidence"], "$.sources.evidence")):
        evidence = _mapping(item, "$.sources.evidence[{}]".format(index))
        _closed(evidence, {"evidence_id", "sha256"}, "$.sources.evidence[{}]".format(index))
        evidence_id = _text(evidence["evidence_id"], "$.sources.evidence[{}].evidence_id".format(index))
        if evidence_id in evidence_ids:
            raise _error("duplicate_id", "$.sources.evidence", "duplicate evidence ID")
        evidence_ids.add(evidence_id)
        _hash(evidence["sha256"], "$.sources.evidence[{}].sha256".format(index))

    counts = _mapping(root["counts"], "$.counts")
    _closed(counts, _COUNT_FIELDS, "$.counts")
    for field in sorted(_COUNT_FIELDS):
        _integer(counts[field], "$.counts." + field)

    poses = _sequence(root["poses"], "$.poses")
    ordered_pose_ids = []
    pose_ids = set()
    admitted_pose_ids = set()
    diagnostic_pose_ids = set()
    for index, item in enumerate(poses):
        path = "$.poses[{}]".format(index)
        pose = _mapping(item, path)
        _closed(pose, _POSE_FIELDS, path)
        pose_id = _text(pose["pose_id"], path + ".pose_id")
        ordered_pose_ids.append(pose_id)
        if pose_id in pose_ids:
            raise _error("duplicate_id", path + ".pose_id", "duplicate pose ID")
        pose_ids.add(pose_id)
        roles = _texts(pose["roles"], path + ".roles")
        admission = pose["admission"]
        expected_admission = "graph_admitted" if "clip_sample" in roles else "diagnostic_only"
        if admission != expected_admission:
            raise _error("pose_admission_mismatch", path + ".admission", "admission does not match graph roles")
        if admission == "graph_admitted":
            admitted_pose_ids.add(pose_id)
            if pose["capability_tier"] == "C":
                raise _error("tier_c_admitted", path + ".capability_tier", "tier C cannot be admitted")
        else:
            diagnostic_pose_ids.add(pose_id)
            if pose["clip_ids"]:
                raise _error("diagnostic_pose_mapped", path + ".clip_ids", "diagnostic pose cannot map to a clip")
        for field in (
            "capability_tier",
            "quality_status",
            "facing",
            "locomotion",
            "support_contact",
            "altitude_class",
            "wing_mode",
            "staff_mode",
        ):
            _text(pose[field], path + "." + field)
        _text(pose["planted_anchor"], path + ".planted_anchor", allow_none=True)
        for field in ("action_ids", "clip_ids", "channel_ownership"):
            _texts(pose[field], path + "." + field)
        _integer(pose["cell_count"], path + ".cell_count")
        _hash(pose["content_sha256"], path + ".content_sha256")
        _hash(pose["source_asset_sha256"], path + ".source_asset_sha256", allow_none=True)
        for evidence_index, digest in enumerate(_sequence(pose["evidence_sha256"], path + ".evidence_sha256")):
            _hash(digest, "{}.evidence_sha256[{}]".format(path, evidence_index))
    if ordered_pose_ids != sorted(ordered_pose_ids):
        raise _error("invalid_order", "$.poses", "pose records must be sorted by pose_id")

    capabilities = _sequence(root["capabilities"], "$.capabilities")
    capability_ids = []
    for index, capability in enumerate(capabilities):
        _validate_capability(capability, index)
        capability_ids.append(capability["capability_id"])
    if len(capability_ids) != len(set(capability_ids)):
        raise _error("duplicate_id", "$.capabilities", "duplicate capability ID")
    if capability_ids != sorted(capability_ids):
        raise _error("invalid_order", "$.capabilities", "capabilities must be sorted by capability_id")
    admitted_surface_ids = {
        field: {
            surface_id
            for capability in capabilities
            if capability["admission"] != "unsupported"
            for surface_id in capability["mapping"][field]
        }
        for field in ("effect_ids", "prop_ids")
    }
    for field, admitted_ids in admitted_surface_ids.items():
        unadmitted = sorted(set(bindings[field]) - admitted_ids)
        if unadmitted:
            raise _error(
                "permission_binding_unadmitted",
                "$.permission_world.bindings." + field,
                "binding lacks an admitted capability mapping: {}".format(
                    ", ".join(unadmitted)
                ),
            )
    bound_capability_kinds = {
        "{}:{}".format(surface_class, surface_id)
        for surface_class, field in (
            ("world_state", "world_state_ids"),
            ("effect", "effect_ids"),
            ("prop", "prop_ids"),
        )
        for surface_id in bindings[field]
    }
    if set(requirement_capabilities) != bound_capability_kinds:
        raise _error(
            "permission_requirement_mismatch",
            "$.permission_world.bindings.requirements",
            "each permission-bound capability requires one exact scope/purpose rule",
        )
    capability_id_set = set(capability_ids)
    clip_capabilities = {
        capability["mapping"]["clip_ids"][0]: capability
        for capability in capabilities
        if capability["category"] == "animation_clip"
        and len(capability["mapping"]["clip_ids"]) == 1
    }
    for index, capability in enumerate(capabilities):
        path = "$.capabilities[{}]".format(index)
        mapping = capability["mapping"]
        if not set(mapping["pose_ids"]).issubset(admitted_pose_ids):
            raise _error(
                "diagnostic_pose_mapped",
                path + ".mapping.pose_ids",
                "capability references non-admitted pose",
            )
        fallback_id = capability["fallback"]["capability_id"]
        if fallback_id is not None and fallback_id not in capability_id_set:
            raise _error("dangling_reference", path + ".fallback.capability_id", "unknown fallback capability")
        if capability["admission"] == "unsupported" and any(
            mapping[field]
            for field in _MAPPING_FIELDS
            if field != "ownership"
        ):
            raise _error(
                "unsupported_surface_mapped",
                path + ".mapping",
                "unsupported surface cannot have runtime IDs",
            )
        if capability["category"] == "animation_clip":
            if not capability["capability_id"].startswith("clip:"):
                raise _error("identity_mismatch", path + ".capability_id", "clip capability must use clip: prefix")
            if mapping["clip_ids"] != [capability["capability_id"].removeprefix("clip:")]:
                raise _error("identity_mismatch", path + ".mapping.clip_ids", "clip capability ID and mapping differ")
            if not set(capability["transitions"]["legal_exit_clip_ids"]).issubset(clip_capabilities):
                raise _error("dangling_reference", path + ".transitions.legal_exit_clip_ids", "unknown exit clip")

    known_clip_ids = set(clip_capabilities)
    for index, pose in enumerate(poses):
        if not set(pose["clip_ids"]).issubset(known_clip_ids):
            raise _error("dangling_reference", "$.poses[{}].clip_ids".format(index), "unknown clip")

    diagnostics = _sequence(root["diagnostics"], "$.diagnostics")
    for index, item in enumerate(diagnostics):
        path = "$.diagnostics[{}]".format(index)
        diagnostic = _mapping(item, path)
        _closed(diagnostic, _DIAGNOSTIC_FIELDS, path)
        if diagnostic["severity"] not in {"info", "warning", "error"}:
            raise _error("invalid_enum", path + ".severity", "invalid diagnostic severity")
        for field in _DIAGNOSTIC_FIELDS - {"severity"}:
            _text(diagnostic[field], path + "." + field)

    actual_counts = {
        "package_capability_count": len(character["package_capabilities"]),
        "clip_count": sum(capability["category"] == "animation_clip" for capability in capabilities),
        "node_count": len(
            {
                node_id
                for capability in capabilities
                for node_id in capability["mapping"]["node_ids"]
            }
        ),
        "pose_count": len(poses),
        "graph_admitted_pose_count": len(admitted_pose_ids),
        "diagnostic_only_pose_count": len(diagnostic_pose_ids),
        "expression_count": sum(capability["category"] == "expression_overlay" for capability in capabilities),
        "mouth_shape_count": sum(capability["category"] == "mouth_overlay" for capability in capabilities),
        "capability_count": len(capabilities),
        "diagnostic_count": len(diagnostics),
    }
    for field, actual in actual_counts.items():
        if counts[field] != actual:
            raise _error("count_mismatch", "$.counts." + field, "declared count does not match records")
    if character["default_pose_id"] not in admitted_pose_ids:
        raise _error("default_pose_not_admitted", "$.character.default_pose_id", "default pose must be admitted")

    declared_hash = _hash(root["manifest_sha256"], "$.manifest_sha256")
    unhashed = copy.deepcopy(dict(root))
    unhashed.pop("manifest_sha256")
    actual_hash = _hash_value(unhashed)
    if declared_hash != actual_hash:
        raise _error("hash_mismatch", "$.manifest_sha256", "manifest hash does not match canonical content")


def cross_validate_character_capability_manifest(
    value: Mapping[str, Any],
    package_path: Path = WIZARD_JOE_PACKAGE_PATH,
) -> Tuple[CapabilityDiagnostic, ...]:
    """Compare a valid manifest to current sources and return stable diagnostics."""

    validate_character_capability_manifest(value)
    diagnostics = tuple(
        CapabilityDiagnostic(
            severity=item["severity"],
            code=item["code"],
            subject_id=item["subject_id"],
            message=item["message"],
        )
        for item in value["diagnostics"]
    )
    expected = _build_manifest(Path(package_path))
    if canonical_character_capability_manifest(value) != canonical_character_capability_manifest(expected):
        diagnostics += (
            CapabilityDiagnostic(
                "error",
                "source_derivation_mismatch",
                value["character"]["character_id"],
                "Manifest differs from deterministic derivation of current character sources.",
            ),
        )
    return diagnostics


def require_admitted_capability(
    value: Mapping[str, Any], capability_id: str
) -> Mapping[str, Any]:
    """Return an admitted capability or fail with a stable compiler-facing code."""

    validate_character_capability_manifest(value)
    for capability in value["capabilities"]:
        if capability["capability_id"] == capability_id:
            if capability["admission"] == "unsupported":
                raise _error(
                    "capability_not_admitted",
                    "$.capabilities.{}".format(capability_id),
                    "capability is explicitly unsupported",
                )
            return capability
    raise _error(
        "capability_unknown",
        "$.capabilities.{}".format(capability_id),
        "capability ID is absent from the manifest",
    )


def require_graph_admitted_pose(
    value: Mapping[str, Any], pose_id: str
) -> Mapping[str, Any]:
    """Return a graph-admitted pose or reject diagnostic-only asset selection."""

    validate_character_capability_manifest(value)
    for pose in value["poses"]:
        if pose["pose_id"] == pose_id:
            if pose["admission"] != "graph_admitted":
                raise _error(
                    "pose_not_admitted",
                    "$.poses.{}".format(pose_id),
                    "pose is diagnostic-only and cannot be selected",
                )
            return pose
    raise _error(
        "pose_unknown",
        "$.poses.{}".format(pose_id),
        "pose ID is absent from the manifest",
    )


def load_character_capability_manifest(path: Path) -> Dict[str, Any]:
    """Load and strictly validate a derived manifest JSON artifact."""

    raw = _read_json(Path(path))
    manifest = dict(_mapping(raw, "$"))
    validate_character_capability_manifest(manifest)
    return manifest


__all__ = [
    "CapabilityDiagnostic",
    "CharacterCapabilityManifestValidationError",
    "SCHEMA_PATH",
    "canonical_character_capability_manifest",
    "cross_validate_character_capability_manifest",
    "derive_character_capability_manifest",
    "load_character_capability_manifest",
    "require_admitted_capability",
    "require_graph_admitted_pose",
    "validate_character_capability_manifest",
]
