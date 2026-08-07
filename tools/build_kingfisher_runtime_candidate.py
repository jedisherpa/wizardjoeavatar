#!/usr/bin/env python3
"""Build Kingfisher's reviewed pose pairs as a fail-closed runtime candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import HDPoseLibrary


GRAPH_SCHEMA = (
    "https://wizardjoe.local/schemas/"
    "reference_avatar_animation_graph_v2.schema.json"
)
FACINGS = (
    "north",
    "northeast",
    "east",
    "southeast",
    "south",
    "southwest",
    "west",
    "northwest",
)
ACTION_ORDINALS = {
    "explaining": 12,
    "pointing": 16,
    "warm_welcome": 26,
    "rhetorical_question": 30,
    "centered_calm": 41,
    "joy": 42,
    "surprise": 48,
    "determination": 59,
    "thinking": 61,
    "read_panel": 63,
    "study_diagram": 64,
    "write_or_tap": 65,
    "select_control": 66,
    "pace_left": 69,
    "pace_right": 77,
    "stage_explain": 89,
    "stage_story": 99,
    "stage_resolution": 109,
}
EXPRESSION_ORDINALS = {
    "happy": 42,
    "amused": 43,
    "thinking": 61,
    "surprised": 48,
    "worried": 51,
    "confident": 46,
    "focused": 59,
    "skeptical": 50,
    "explaining": 12,
}


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _write_json(path: Path, value: Any) -> str:
    content = _json_bytes(value)
    path.write_bytes(content)
    return _sha256(content)


def _linked_copy(source: Path, destination: Path) -> None:
    if source.resolve() == destination.resolve():
        return
    if destination.exists():
        destination.unlink()
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def _ordinal(pose_id: str) -> int:
    return int(pose_id.split(".", 3)[2])


def _slug(pose_id: str) -> str:
    return pose_id.split(".", 3)[3]


def _pose_for_ordinal(pose_ids: Iterable[str], ordinal: int) -> str:
    matches = [pose_id for pose_id in pose_ids if _ordinal(pose_id) == ordinal]
    if len(matches) != 1:
        raise ValueError(
            "expected one Kingfisher pose at ordinal {}, found {}".format(
                ordinal,
                len(matches),
            )
        )
    return matches[0]


def _facing(ordinal: int) -> str:
    return {
        1: "south",
        2: "southwest",
        3: "west",
        4: "northwest",
        5: "north",
        6: "east",
        7: "southeast",
    }.get(ordinal, "south")


def _rgba_bbox(rgba: bytes, width: int, height: int) -> list[int]:
    alpha = Image.frombytes("RGBA", (width, height), rgba).getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError("Kingfisher runtime candidate contains an empty pose")
    return [int(value) for value in bbox]


def _speech_pairs(index: Mapping[str, Any], pose_ids: list[str]) -> dict[str, str]:
    review = index.get("legacy_pair_review")
    if not isinstance(review, Mapping):
        raise ValueError("Kingfisher candidate requires legacy pair review evidence")
    summary = review.get("pairwise_full_size_review_summary")
    if not isinstance(summary, Mapping) or summary.get("complete") is not True:
        raise ValueError("Kingfisher pair review must be complete")
    if int(review.get("user_approved_count", -1)) != 0:
        raise ValueError("review candidate must not claim user approval")
    pairs: dict[str, str] = {}
    for item in review.get("pairs", []):
        if not isinstance(item, Mapping):
            raise ValueError("Kingfisher pair evidence must be an object")
        state = item.get("pairwise_full_size_review", {}).get("state")
        if state not in {"pass", "not_observable"}:
            raise ValueError("Kingfisher pair review contains an unresolved pair")
        resting = str(item["resting_pose_id"])
        speaking = str(item["speaking_pose_id"])
        pairs[resting] = speaking
    for resting_ordinal in range(67, 111, 2):
        pairs[
            _pose_for_ordinal(pose_ids, resting_ordinal)
        ] = _pose_for_ordinal(pose_ids, resting_ordinal + 1)
    if len(pairs) != 88 or set(pairs) & set(pairs.values()):
        raise ValueError("Kingfisher candidate must contain 88 disjoint speech pairs")
    if set(pairs) | set(pairs.values()) != set(pose_ids):
        raise ValueError("Kingfisher speech pairs must partition the pose library")
    return dict(sorted(pairs.items(), key=lambda item: _ordinal(item[0])))


def _pose_documents(
    index: Mapping[str, Any],
    metadata: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    width = int(index["profile"]["canvas_width"])
    height = int(index["profile"]["canvas_height"])
    manifest_poses = []
    library_poses = []
    for pose in metadata:
        pose_id = str(pose["pose_id"])
        bbox = [int(value) for value in pose["source_bbox"]]
        root = [(bbox[0] + bbox[2]) // 2, max(0, bbox[3] - 1)]
        ordinal = _ordinal(pose_id)
        actions = [
            action
            for action, action_ordinal in ACTION_ORDINALS.items()
            if action_ordinal == ordinal
        ] or ["idle"]
        tags = [
            "hd_rgba",
            "candidate_review_only",
            "speaking" if "speaking-beak" in pose_id else "resting",
        ]
        source = "{}#{}".format(pose["source_path"], pose["source_sha256"])
        manifest_poses.append(
            {
                "id": pose_id,
                "description": _slug(pose_id).replace("-", " "),
                "source": source,
                "facing": _facing(ordinal),
                "locomotion": "walk" if 69 <= ordinal <= 84 else "idle",
                "actions": actions,
                "phase": None,
                "tags": tags,
            }
        )
        library_poses.append(
            {
                "id": pose_id,
                "description": _slug(pose_id).replace("-", " "),
                "source": source,
                "cols": width,
                "rows": height,
                "root_anchor": root,
                "presentation_scale": [1, 1],
                "anchors": {"root": root},
                "facing": _facing(ordinal),
                "locomotion": "walk" if 69 <= ordinal <= 84 else "idle",
                "actions": actions,
                "phase": None,
                "tags": tags,
                "cells": [
                    {
                        "x": root[0],
                        "y": root[1],
                        "rgb": [0, 0, 0],
                        "region": "hd_runtime_metadata_sentinel",
                    }
                ],
            }
        )
    asset_set_id = str(index["asset_set_id"]) + "-runtime-candidate-v1"
    return (
        {
            "asset_set_id": asset_set_id,
            "character_id": "kingfisher",
            "poses": manifest_poses,
        },
        {
            "asset_set_id": asset_set_id,
            "character_id": "kingfisher",
            "poses": library_poses,
        },
    )


def _sample(pose_id: str) -> dict[str, Any]:
    return {
        "pose_id": pose_id,
        "duration_frames": 4,
        "support_contact": "none",
        "planted_anchor": None,
        "markers": [],
    }


def _clip(
    clip_id: str,
    pose_ids: list[str],
    *,
    family: str = "action",
    loop_mode: str = "hold_last",
) -> dict[str, Any]:
    return {
        "clip_id": clip_id,
        "authored_fps": 24,
        "family": family,
        "supported_facings": list(FACINGS),
        "loop_mode": loop_mode,
        "phase_source": "ground_distance" if family == "locomotion" else "none",
        "root_policy": "ground_distance" if family == "locomotion" else "fixed",
        "minimum_hold_ticks": 1,
        "interrupt_policy": "immediate",
        "channel_ownership": ["body"],
        "samples": [_sample(pose_id) for pose_id in pose_ids],
        "entry_markers": [],
        "exit_markers": [],
        "secondary_curves": {},
        "legal_successors": [],
    }


def _graph(pose_ids: list[str], asset_set_id: str) -> dict[str, Any]:
    clips: dict[str, Any] = {}
    nodes: dict[str, Any] = {}
    for pose_id in pose_ids:
        ordinal = _ordinal(pose_id)
        clip_id = "pose_{:03d}".format(ordinal)
        clips[clip_id] = _clip(clip_id, [pose_id])
        node_id = "ground_idle" if ordinal == 1 else "pose_{:03d}".format(ordinal)
        nodes[node_id] = {
            "clip_id": clip_id,
            "mobility_modes": ["grounded_idle"],
            "actions": [
                action
                for action, action_ordinal in ACTION_ORDINALS.items()
                if action_ordinal == ordinal
            ],
        }
    clips["pace_left_cycle"] = _clip(
        "pace_left_cycle",
        [_pose_for_ordinal(pose_ids, value) for value in (69, 71, 73, 75)],
        family="locomotion",
        loop_mode="loop",
    )
    clips["pace_right_cycle"] = _clip(
        "pace_right_cycle",
        [_pose_for_ordinal(pose_ids, value) for value in (77, 79, 81, 83)],
        family="locomotion",
        loop_mode="loop",
    )
    nodes["ground_walk_left"] = {
        "clip_id": "pace_left_cycle",
        "mobility_modes": ["grounded_start", "grounded_walk", "grounded_stop"],
        "actions": [],
    }
    nodes["ground_walk_right"] = {
        "clip_id": "pace_right_cycle",
        "mobility_modes": ["grounded_start", "grounded_walk", "grounded_stop"],
        "actions": [],
    }
    for clip in clips.values():
        clip["legal_successors"] = sorted(clips)
    classification = {
        pose_id: {
            "roles": ["clip_sample"],
            "altitude_class": "grounded",
            "support_contact": "none",
            "planted_anchor": None,
            "wing_mode": "folded",
            "staff_mode": "absent",
            "capability_tier": "A",
        }
        for pose_id in pose_ids
    }
    facing_clips = {
        "south": "pose_001",
        "southwest": "pose_002",
        "west": "pose_003",
        "northwest": "pose_004",
        "north": "pose_005",
        "northeast": "pose_004",
        "east": "pose_006",
        "southeast": "pose_007",
    }
    return {
        "$schema": GRAPH_SCHEMA,
        "$id": "https://wizardjoe.local/graphs/kingfisher-paired-performance-v1",
        "schema_version": 2,
        "asset_set_id": asset_set_id,
        "authored_fps": 24,
        "simulation_hz": 120,
        "default_node_id": "ground_idle",
        "capability_tiers": {
            "A": {"description": "Pair-reviewed HD RGBA performance poses."},
            "B": {"description": "Reserved for authored transition upgrades."},
            "C": {"description": "Diagnostic-only poses excluded from runtime."},
        },
        "pose_classification": classification,
        "clips": clips,
        "nodes": nodes,
        "transitions": [],
        "transition_recipes": {
            "hard_cut": {
                "entry_rule": "hard_cut",
                "duration_frames": 0,
                "interrupt_source": "presented_snapshot",
                "region_masks": [],
            }
        },
        "channel_masks": {"body": ["whole_pose"]},
        "fallbacks": {
            "grounded_clip_id": "pose_001",
            "airborne_clip_id": "pose_001",
            "by_facing": facing_clips,
            "by_action": {
                action: "pose_{:03d}".format(ordinal)
                for action, ordinal in ACTION_ORDINALS.items()
            },
        },
    }


def _runtime_profile(
    pose_ids: list[str],
    speech_pairs: Mapping[str, str],
) -> dict[str, Any]:
    pose = lambda ordinal: _pose_for_ordinal(pose_ids, ordinal)
    return {
        "schema_version": 3,
        "character_id": "kingfisher",
        "default_pose_id": pose(1),
        "presentation_scale": [1, 1],
        "required_anchors": ["root"],
        "optional_anchors": [],
        "facing_poses": {
            "north": pose(5),
            "northeast": pose(4),
            "east": pose(6),
            "southeast": pose(7),
            "south": pose(1),
            "southwest": pose(2),
            "west": pose(3),
            "northwest": pose(4),
        },
        "action_poses": {
            action: pose(ordinal) for action, ordinal in ACTION_ORDINALS.items()
        },
        "expression_aliases": {
            expression: pose(ordinal)
            for expression, ordinal in EXPRESSION_ORDINALS.items()
        },
        "locomotion_cycles": {
            "walk": [pose(value) for value in (69, 71, 73, 75, 77, 79, 81, 83)],
            "run": [],
            "flight": [],
        },
        "speech_poses": list(speech_pairs.values()),
        "speech_pose_map": {},
        "speech_pose_pairs": dict(speech_pairs),
        "blink_poses": {"open": pose(1), "half_closed": pose(1), "closed": pose(1)},
        "props": {},
    }


def build_candidate(index_path: Path, destination: Path) -> dict[str, Any]:
    index_path = Path(index_path).resolve()
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    source_index = json.loads(index_path.read_text(encoding="utf-8"))
    if source_index.get("character_id") != "kingfisher":
        raise ValueError("candidate builder accepts only Kingfisher")
    if source_index.get("review_projection") is not True:
        raise ValueError("Kingfisher source must be a review projection")
    if source_index.get("runtime_admitted") is not False:
        raise ValueError("Kingfisher source must remain runtime-unadmitted")
    pose_ids = [str(value) for value in source_index["pose_ids"]]
    if len(pose_ids) != 176 or len(set(pose_ids)) != 176:
        raise ValueError("Kingfisher candidate requires 176 unique poses")
    speech_pairs = _speech_pairs(source_index, pose_ids)

    source_library = HDPoseLibrary(index_path, cache_size_per_shard=2)
    width, height = source_library.canvas_size
    metadata = []
    for pose_id in pose_ids:
        rgba = source_library.load_rgba(pose_id)
        metadata.append(
            {
                "ordinal": _ordinal(pose_id),
                "pose_id": pose_id,
                "slug": _slug(pose_id),
                "source_bbox": _rgba_bbox(rgba, width, height),
                "source_path": index_path.name,
                "source_sha256": _sha256(rgba),
            }
        )

    candidate_index = json.loads(json.dumps(source_index))
    candidate_index["asset_set_id"] = (
        str(source_index["asset_set_id"]) + "-runtime-candidate-v1"
    )
    candidate_index["poses"] = metadata
    candidate_index["runtime_admitted"] = False
    for shard in candidate_index["shards"]:
        source = (index_path.parent / str(shard["path"])).resolve()
        target = destination / source.name
        _linked_copy(source, target)
        shard["path"] = target.name
        if _sha256(target.read_bytes()) != str(shard["sha256"]):
            raise ValueError("copied Kingfisher shard checksum mismatch")
    index_name = "kingfisher-runtime-candidate-library-index.json"
    index_digest = _write_json(destination / index_name, candidate_index)

    pose_manifest, pose_library = _pose_documents(candidate_index, metadata)
    graph = _graph(pose_ids, pose_manifest["asset_set_id"])
    profile = _runtime_profile(pose_ids, speech_pairs)
    choreography = json.loads(
        (ROOT / "assets/reference/characters/kingfisher/kingfisher-choreography-dictionary-v1.json")
        .read_text(encoding="utf-8")
    )
    choreography["dictionary_id"] = "choreography:kingfisher-paired-performance-v1"
    choreography["instructions"]["speech_motion_policy"] = "whole_pose"

    files = {
        "animation_graph": ("kingfisher-animation-graph-v2.json", graph),
        "pose_library": ("kingfisher-pose-catalog-v1.json", pose_library),
        "pose_manifest": ("kingfisher-pose-manifest-v1.json", pose_manifest),
        "runtime_profile": ("kingfisher-runtime-profile-v3.json", profile),
        "choreography_dictionary": (
            "kingfisher-paired-choreography-dictionary-v1.json",
            choreography,
        ),
    }
    assets: dict[str, dict[str, str]] = {}
    for role, (name, content) in files.items():
        digest = _write_json(destination / name, content)
        assets[role] = {"path": name, "sha256": "sha256:" + digest}

    capabilities = [
        "pair_reviewed_whole_pose_speech",
        "body_locked_speech_during_gesture",
        "stage_pacing_cycles",
        "phrase_scale_performance_dictionary",
        "catalog_pose_override",
    ]
    capability = {
        "schema_version": 1,
        "character_id": "kingfisher",
        "renderer_adapter_id": "asciline.hd_rgba_pose.v1",
        "runtime_api_version": 1,
        "status": "candidate_review_only",
        "capabilities": capabilities,
        "counts": {
            "clip_count": len(graph["clips"]),
            "diagnostic_only_pose_count": 0,
            "graph_admitted_pose_count": len(pose_ids),
            "node_count": len(graph["nodes"]),
            "pose_count": len(pose_ids),
            "transition_count": 0,
        },
        "graph_admitted_pose_ids": sorted(pose_ids),
        "diagnostic_only_pose_ids": [],
        "denied_or_pending": [
            "authored_blink_cycle",
            "flight_cycle",
            "governed_av_acceptance_bundle",
            "runtime_registry_admission",
        ],
    }
    capability_name = "kingfisher-capability-manifest-v1.json"
    capability_digest = _write_json(destination / capability_name, capability)
    assets["capability_manifest"] = {
        "path": capability_name,
        "sha256": "sha256:" + capability_digest,
    }
    assets["hd_pose_library_index"] = {
        "path": index_name,
        "sha256": "sha256:" + index_digest,
    }
    for number, shard in enumerate(candidate_index["shards"], start=1):
        assets["hd_pose_shard_{:03d}".format(number)] = {
            "path": str(shard["path"]),
            "sha256": "sha256:" + str(shard["sha256"]),
        }

    package = {
        "schema_version": 2,
        "character_id": "kingfisher",
        "display_name": "Kingfisher",
        "runtime_api": {"min": 1, "max": 1},
        "renderer": "asciline_hd_rgba",
        "renderer_adapter_id": "asciline.hd_rgba_pose.v1",
        "assets": assets,
        "default_pose_id": _pose_for_ordinal(pose_ids, 1),
        "capabilities": capabilities,
    }
    package_name = "kingfisher-character-package-v2.json"
    package_digest = _write_json(destination / package_name, package)
    receipt = {
        "schema_version": 1,
        "status": "candidate_review_only",
        "character_id": "kingfisher",
        "source_library_index": index_path.relative_to(ROOT).as_posix()
        if index_path.is_relative_to(ROOT)
        else index_path.name,
        "source_library_index_sha256": _sha256(index_path.read_bytes()),
        "candidate_library_index_sha256": index_digest,
        "package": package_name,
        "package_sha256": "sha256:" + package_digest,
        "pose_count": len(pose_ids),
        "speech_pair_count": len(speech_pairs),
        "user_approved_count": 0,
        "runtime_admitted": False,
    }
    _write_json(destination / "kingfisher-runtime-candidate-receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the reviewed Kingfisher library as a runtime candidate."
    )
    parser.add_argument("library_index", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            build_candidate(args.library_index, args.destination),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
