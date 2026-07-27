#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_URI = (
    "https://wizardjoe.local/schemas/"
    "reference_avatar_animation_graph_v2.schema.json"
)
ROOT = Path(__file__).resolve().parents[1]
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
SUPPORTED_SHARED_CANVAS_CHARACTERS = frozenset({"robin", "speech"})
CORE_ACTION_POSE_INDEXES = {
    "explaining": 12,
    "thinking": 61,
    "pointing": 16,
    "magic_cast": 62,
    "reaction": 48,
    "celebrate": 42,
    "guard": 36,
    "block": 75,
    "flourish": 39,
    "shush": 29,
}
EXPRESSION_POSE_INDEXES = {
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


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: Any) -> str:
    content = _json_bytes(value)
    path.write_bytes(content)
    return _sha256(content)


def _linked_copy(source: Path, destination: Path) -> None:
    if destination.exists():
        destination.unlink()
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def _portable_source_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _pose_id(
    index: Mapping[str, Any],
    family: str,
    family_index: int,
) -> str:
    matches = [
        str(pose["pose_id"])
        for pose in index["poses"]
        if str(pose["family"]) == family
        and int(pose["family_index"]) == family_index
    ]
    if len(matches) != 1:
        raise ValueError(
            "expected one {} pose at index {}, found {}".format(
                family,
                family_index,
                len(matches),
            )
        )
    return matches[0]


def _core_action_poses(index: Mapping[str, Any]) -> dict[str, str]:
    return {
        action: _pose_id(index, "ACT", family_index)
        for action, family_index in CORE_ACTION_POSE_INDEXES.items()
    }


def _pose_facing(pose: Mapping[str, Any]) -> str:
    ordinal = int(pose["ordinal"])
    if str(pose["family"]) != "ACT":
        return "south"
    return {
        1: "south",
        2: "southwest",
        3: "west",
        4: "northwest",
        5: "north",
        6: "east",
        7: "southeast",
    }.get(ordinal, "south")


def _pose_locomotion(pose: Mapping[str, Any]) -> str:
    family = str(pose["family"])
    ordinal = int(pose["family_index"])
    if family == "FLY":
        return "flight"
    if family == "ACT" and 76 <= ordinal <= 79:
        return "walk"
    if family == "ACT" and 80 <= ordinal <= 84:
        return "run"
    return "idle"


def _pose_actions(pose: Mapping[str, Any]) -> list[str]:
    locomotion = _pose_locomotion(pose)
    if locomotion != "idle":
        return [locomotion]
    slug = str(pose["slug"]).replace("-", "_")
    return ["idle"] if int(pose["ordinal"]) <= 10 else [slug]


def _pose_tags(pose: Mapping[str, Any]) -> list[str]:
    return [
        str(pose["family"]).lower(),
        str(pose["slug"]).replace("-", "_"),
        "hd_rgba",
        "candidate_review_only",
    ]


def _source_root(
    pose: Mapping[str, Any],
    *,
    split_x: int,
    identity_side: str,
    width: int,
    height: int,
) -> list[int]:
    bbox = [int(value) for value in pose["source_bbox"]]
    root_x = (
        split_x // 2
        if identity_side == "left"
        else (split_x + width) // 2
        if identity_side == "right"
        else (bbox[0] + bbox[2]) // 2
    )
    return [
        max(0, min(width - 1, root_x)),
        max(0, min(height - 1, bbox[3] - 1)),
    ]


def _pose_documents(index: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    profile = index["profile"]
    width = int(profile["canvas_width"])
    height = int(profile["canvas_height"])
    split_x = int(profile.get("identity_split_x", width // 2))
    identity_side = str(index.get("identity_side", ""))
    manifest_poses = []
    library_poses = []
    for pose in index["poses"]:
        pose_id = str(pose["pose_id"])
        facing = _pose_facing(pose)
        locomotion = _pose_locomotion(pose)
        actions = _pose_actions(pose)
        tags = _pose_tags(pose)
        root = _source_root(
            pose,
            split_x=split_x,
            identity_side=identity_side,
            width=width,
            height=height,
        )
        source = "{}#{}".format(
            pose["source_path"],
            pose["source_sha256"],
        )
        manifest_poses.append(
            {
                "id": pose_id,
                "description": str(pose["slug"]).replace("_", " "),
                "source": source,
                "facing": facing,
                "locomotion": locomotion,
                "actions": actions,
                "phase": None,
                "tags": tags,
            }
        )
        library_poses.append(
            {
                "id": pose_id,
                "description": str(pose["slug"]).replace("_", " "),
                "source": source,
                "cols": width,
                "rows": height,
                "root_anchor": root,
                "presentation_scale": [1, 1],
                "anchors": {"root": root},
                "facing": facing,
                "locomotion": locomotion,
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
    asset_set_id = "{}-runtime-candidate-v1".format(index["asset_set_id"])
    return (
        {
            "asset_set_id": asset_set_id,
            "character_id": index["character_id"],
            "poses": manifest_poses,
        },
        {
            "asset_set_id": asset_set_id,
            "character_id": index["character_id"],
            "poses": library_poses,
        },
    )


def _sample(
    pose_id: str,
    *,
    duration_frames: int = 4,
) -> dict[str, Any]:
    return {
        "pose_id": pose_id,
        "duration_frames": duration_frames,
        "support_contact": "none",
        "planted_anchor": None,
        "markers": [],
    }


def _clip(
    clip_id: str,
    pose_ids: Iterable[str],
    *,
    family: str,
    loop_mode: str,
    phase_source: str = "none",
    root_policy: str = "fixed",
) -> dict[str, Any]:
    return {
        "clip_id": clip_id,
        "authored_fps": 24,
        "family": family,
        "supported_facings": list(FACINGS),
        "loop_mode": loop_mode,
        "phase_source": phase_source,
        "root_policy": root_policy,
        "minimum_hold_ticks": 1,
        "interrupt_policy": "immediate",
        "channel_ownership": ["body"],
        "samples": [_sample(pose_id) for pose_id in pose_ids],
        "entry_markers": [],
        "exit_markers": [],
        "secondary_curves": {},
        "legal_successors": [],
    }


def _graph(index: Mapping[str, Any], pose_ids: list[str]) -> dict[str, Any]:
    by_id = {str(pose["pose_id"]): pose for pose in index["poses"]}
    character_id = str(index["character_id"])
    action_poses = _core_action_poses(index)

    def family_ids(family: str, start: int, end: int) -> list[str]:
        return [
            str(pose["pose_id"])
            for pose in index["poses"]
            if str(pose["family"]) == family
            and start <= int(pose["family_index"]) <= end
        ]

    clips = {
        "catalog_all": _clip(
            "catalog_all", pose_ids, family="action", loop_mode="hold_last"
        ),
        "idle_front": _clip(
            "idle_front",
            [_pose_id(index, "ACT", 1)],
            family="idle",
            loop_mode="loop",
        ),
        "idle_left": _clip(
            "idle_left",
            [_pose_id(index, "ACT", 3)],
            family="idle",
            loop_mode="loop",
        ),
        "idle_right": _clip(
            "idle_right",
            [_pose_id(index, "ACT", 6)],
            family="idle",
            loop_mode="loop",
        ),
        "idle_back": _clip(
            "idle_back",
            [_pose_id(index, "ACT", 5)],
            family="idle",
            loop_mode="loop",
        ),
        "walk_front": _clip(
            "walk_front",
            family_ids("ACT", 76, 79),
            family="locomotion",
            loop_mode="loop",
            phase_source="ground_distance",
            root_policy="ground_distance",
        ),
        "run_front": _clip(
            "run_front",
            family_ids("ACT", 80, 81),
            family="locomotion",
            loop_mode="loop",
            phase_source="ground_distance",
            root_policy="ground_distance",
        ),
        "takeoff_cycle": _clip(
            "takeoff_cycle",
            family_ids("FLY", 1, 8),
            family="flight",
            loop_mode="once",
            phase_source="air_distance",
            root_policy="air_trajectory",
        ),
        "glide_cycle": _clip(
            "glide_cycle",
            family_ids("FLY", 9, 20),
            family="flight",
            loop_mode="loop",
            phase_source="flap_phase",
            root_policy="air_trajectory",
        ),
        "hover_cycle": _clip(
            "hover_cycle",
            family_ids("FLY", 40, 40),
            family="flight",
            loop_mode="loop",
            phase_source="flap_phase",
            root_policy="air_trajectory",
        ),
        "bank_left_cycle": _clip(
            "bank_left_cycle",
            family_ids("FLY", 26, 27),
            family="flight",
            loop_mode="loop",
            phase_source="air_distance",
            root_policy="air_trajectory",
        ),
        "bank_right_cycle": _clip(
            "bank_right_cycle",
            family_ids("FLY", 28, 29),
            family="flight",
            loop_mode="loop",
            phase_source="air_distance",
            root_policy="air_trajectory",
        ),
        "landing_cycle": _clip(
            "landing_cycle",
            family_ids("FLY", 47, 50),
            family="flight",
            loop_mode="once",
            phase_source="air_distance",
            root_policy="air_trajectory",
        ),
        "turn_views": _clip(
            "turn_views",
            family_ids("ACT", 1, 7),
            family="transition",
            loop_mode="hold_last",
        ),
        "turn_front_to_east": _clip(
            "turn_front_to_east",
            [
                _pose_id(index, "ACT", 1),
                _pose_id(index, "ACT", 7),
                _pose_id(index, "ACT", 6),
            ],
            family="transition",
            loop_mode="hold_last",
        ),
        "turn_front_to_west": _clip(
            "turn_front_to_west",
            [
                _pose_id(index, "ACT", 1),
                _pose_id(index, "ACT", 2),
                _pose_id(index, "ACT", 3),
            ],
            family="transition",
            loop_mode="hold_last",
        ),
        "idle_recovery": _clip(
            "idle_recovery",
            [_pose_id(index, "ACT", 1)],
            family="locomotion",
            loop_mode="hold_last",
        ),
        "back_walk_fallback": _clip(
            "back_walk_fallback",
            [_pose_id(index, "ACT", 5)],
            family="locomotion",
            loop_mode="loop",
            phase_source="ground_distance",
            root_policy="ground_distance",
        ),
    }
    for action, pose_id in action_poses.items():
        if pose_id in by_id:
            clips["action_{}".format(action)] = _clip(
                "action_{}".format(action),
                [pose_id],
                family="action",
                loop_mode="hold_last",
            )
    successor_ids = sorted(clips)
    for clip in clips.values():
        clip["legal_successors"] = successor_ids

    nodes: dict[str, Any] = {
        "ground_idle": {
            "clip_id": "idle_front",
            "mobility_modes": ["grounded_idle"],
            "actions": [],
        },
        "back_idle": {
            "clip_id": "idle_back",
            "mobility_modes": ["grounded_idle"],
            "actions": [],
        },
        "left_idle": {
            "clip_id": "idle_left",
            "mobility_modes": ["grounded_idle"],
            "actions": [],
        },
        "right_idle": {
            "clip_id": "idle_right",
            "mobility_modes": ["grounded_idle"],
            "actions": [],
        },
        "turn": {
            "clip_id": "turn_views",
            "mobility_modes": ["turn"],
            "actions": [],
        },
        "ground_walk": {
            "clip_id": "walk_front",
            "mobility_modes": [
                "grounded_start",
                "grounded_walk",
                "grounded_stop",
            ],
            "actions": [],
        },
        "ground_walk_left": {
            "clip_id": "walk_front",
            "mobility_modes": [
                "grounded_start",
                "grounded_walk",
                "grounded_stop",
            ],
            "actions": [],
        },
        "ground_walk_right": {
            "clip_id": "walk_front",
            "mobility_modes": [
                "grounded_start",
                "grounded_walk",
                "grounded_stop",
            ],
            "actions": [],
        },
        "ground_turn_front_to_east": {
            "clip_id": "turn_front_to_east",
            "mobility_modes": [
                "grounded_start",
                "grounded_walk",
                "grounded_stop",
            ],
            "actions": [],
        },
        "ground_turn_front_to_west": {
            "clip_id": "turn_front_to_west",
            "mobility_modes": [
                "grounded_start",
                "grounded_walk",
                "grounded_stop",
            ],
            "actions": [],
        },
        "ground_reverse_east_to_west": {
            "clip_id": "turn_front_to_west",
            "mobility_modes": ["grounded_walk", "grounded_stop"],
            "actions": [],
        },
        "ground_reverse_west_to_east": {
            "clip_id": "turn_front_to_east",
            "mobility_modes": ["grounded_walk", "grounded_stop"],
            "actions": [],
        },
        "ground_stop_front_left": {
            "clip_id": "idle_recovery",
            "mobility_modes": ["grounded_stop"],
            "actions": [],
        },
        "ground_stop_front_right": {
            "clip_id": "idle_recovery",
            "mobility_modes": ["grounded_stop"],
            "actions": [],
        },
        "ground_stop_front_left_passing": {
            "clip_id": "idle_recovery",
            "mobility_modes": ["grounded_stop"],
            "actions": [],
        },
        "ground_stop_front_right_passing": {
            "clip_id": "idle_recovery",
            "mobility_modes": ["grounded_stop"],
            "actions": [],
        },
        "ground_stop_left": {
            "clip_id": "idle_left",
            "mobility_modes": ["grounded_stop"],
            "actions": [],
        },
        "ground_stop_right": {
            "clip_id": "idle_right",
            "mobility_modes": ["grounded_stop"],
            "actions": [],
        },
        "back_walk": {
            "clip_id": "back_walk_fallback",
            "mobility_modes": [
                "grounded_start",
                "grounded_walk",
                "grounded_stop",
            ],
            "actions": [],
        },
        "ground_run": {
            "clip_id": "run_front",
            "mobility_modes": ["grounded_run"],
            "actions": ["dash"],
        },
        "run_recovery": {
            "clip_id": "idle_recovery",
            "mobility_modes": ["landing"],
            "actions": [],
        },
        "takeoff": {
            "clip_id": "takeoff_cycle",
            "mobility_modes": ["takeoff", "airborne"],
            "actions": [],
        },
        "glide": {
            "clip_id": "glide_cycle",
            "mobility_modes": ["flight_travel", "airborne"],
            "actions": [],
        },
        "hover": {
            "clip_id": "hover_cycle",
            "mobility_modes": ["hover", "airborne"],
            "actions": [],
        },
        "flight_bank_left": {
            "clip_id": "bank_left_cycle",
            "mobility_modes": ["flight_bank", "airborne"],
            "actions": [],
        },
        "flight_bank_right": {
            "clip_id": "bank_right_cycle",
            "mobility_modes": ["flight_bank", "airborne"],
            "actions": [],
        },
        "air_reaction_node": {
            "clip_id": "hover_cycle",
            "mobility_modes": ["hover", "flight_travel"],
            "actions": ["reaction"],
        },
        "landing": {
            "clip_id": "landing_cycle",
            "mobility_modes": ["landing", "airborne"],
            "actions": [],
        },
        "catalog_review": {
            "clip_id": "catalog_all",
            "mobility_modes": ["grounded_idle", "airborne"],
            "actions": [],
        },
    }
    action_nodes = {
        "cast": ("magic_cast", ["magic_cast"]),
        "guard": ("guard", ["guard"]),
        "block": ("block", ["block"]),
        "flourish": ("flourish", ["flourish", "staff_spin"]),
        "victory_cast": ("celebrate", ["victory_cast"]),
        "explain": ("explaining", ["explaining", "speaking"]),
        "point": ("pointing", ["pointing"]),
        "shush": ("shush", ["shush"]),
        "celebrate": ("celebrate", ["celebrate"]),
        "hit_reaction": ("reaction", ["reaction", "hit"]),
    }
    for node_id, (action, actions) in action_nodes.items():
        clip_id = "action_{}".format(action)
        if clip_id in clips:
            nodes[node_id] = {
                "clip_id": clip_id,
                "mobility_modes": ["grounded_idle", "grounded_walk"],
                "actions": actions,
            }
    nodes["air_celebrate"] = {
        "clip_id": "hover_cycle",
        "mobility_modes": ["hover", "flight_travel"],
        "actions": ["celebrate"],
    }
    nodes["air_staff"] = {
        "clip_id": "hover_cycle",
        "mobility_modes": ["hover", "flight_travel"],
        "actions": ["magic_cast", "staff_forward"],
    }

    classification = {}
    for pose_id in pose_ids:
        airborne = pose_id.startswith(character_id + ".fly.")
        classification[pose_id] = {
            "roles": ["clip_sample"],
            "altitude_class": "airborne" if airborne else "grounded",
            "support_contact": "none",
            "planted_anchor": None,
            "wing_mode": "extended" if airborne else "folded",
            "staff_mode": "absent",
            "capability_tier": "A",
        }
    return {
        "$schema": SCHEMA_URI,
        "$id": "https://wizardjoe.local/graphs/{}-hd-rgba-candidate-v1".format(
            character_id
        ),
        "schema_version": 2,
        "asset_set_id": "{}-runtime-candidate-v1".format(index["asset_set_id"]),
        "authored_fps": 24,
        "simulation_hz": 120,
        "default_node_id": "ground_idle",
        "capability_tiers": {
            "A": {"description": "Source-backed isolated HD RGBA poses."},
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
            "grounded_clip_id": "idle_front",
            "airborne_clip_id": "hover_cycle",
            "by_facing": {
                "north": "idle_back",
                "northeast": "idle_back",
                "east": "idle_right",
                "southeast": "idle_front",
                "south": "idle_front",
                "southwest": "idle_front",
                "west": "idle_left",
                "northwest": "idle_back",
            },
            "by_action": {
                action: "action_{}".format(action)
                for action in action_poses
                if "action_{}".format(action) in clips
            },
        },
    }


def _runtime_profile(index: Mapping[str, Any]) -> dict[str, Any]:
    default_pose = _pose_id(index, "ACT", 1)
    action_poses = {
        action: pose_id
        for action, pose_id in _core_action_poses(index).items()
        if any(
            str(pose["pose_id"]) == pose_id for pose in index["poses"]
        )
    }
    return {
        "schema_version": 2,
        "character_id": index["character_id"],
        "default_pose_id": default_pose,
        "presentation_scale": [1, 1],
        "required_anchors": ["root"],
        "optional_anchors": [],
        "facing_poses": {
            "north": _pose_id(index, "ACT", 5),
            "northeast": _pose_id(index, "ACT", 4),
            "east": _pose_id(index, "ACT", 6),
            "southeast": _pose_id(index, "ACT", 7),
            "south": default_pose,
            "southwest": _pose_id(index, "ACT", 2),
            "west": _pose_id(index, "ACT", 3),
            "northwest": _pose_id(index, "ACT", 4),
        },
        "action_poses": action_poses,
        "expression_aliases": {
            expression: _pose_id(index, "ACT", family_index)
            for expression, family_index in EXPRESSION_POSE_INDEXES.items()
        },
        "locomotion_cycles": {
            "walk": [
                _pose_id(index, "ACT", family_index)
                for family_index in range(76, 80)
            ],
            "run": [
                _pose_id(index, "ACT", family_index)
                for family_index in range(80, 82)
            ],
            "flight": [
                str(pose["pose_id"])
                for pose in index["poses"]
                if str(pose["family"]) == "FLY"
            ],
        },
        "speech_poses": [],
        "speech_pose_map": {},
        "blink_poses": {
            "open": default_pose,
            "half_closed": default_pose,
            "closed": default_pose,
        },
        "props": {},
    }


def _choreography_dictionary(
    index: Mapping[str, Any],
) -> dict[str, Any]:
    character_id = str(index["character_id"])

    def pose(family: str, family_index: int) -> str:
        return _pose_id(index, family, family_index)

    def binding(
        *,
        roles: list[str],
        pose_ids: list[str],
        action_ids: list[str],
        clip_ids: list[str],
        speech_compatible: bool,
        interrupt_policy: str,
        minimum_hold_ms: int,
        recovery_intent: str | None,
    ) -> dict[str, Any]:
        return {
            "roles": roles,
            "pose_ids": pose_ids,
            "action_ids": action_ids,
            "clip_ids": clip_ids,
            "speech_compatible": speech_compatible,
            "interrupt_policy": interrupt_policy,
            "minimum_hold_ms": minimum_hold_ms,
            "recovery_intent": recovery_intent,
        }

    return {
        "schema_version": 1,
        "dictionary_id": "choreography:{}-v1".format(character_id),
        "character_id": character_id,
        "library_class": "comprehensive_performance",
        "instructions": {
            "selection_unit": "phrase",
            "transition_policy": "authored_graph",
            "speech_motion_policy": "whole_pose",
            "locomotion_speech_policy": "allowed",
            "unsupported_intent_policy": "characterful_neutral",
            "repetition_window_ms": 12000,
            "minimum_stillness_ms": 650,
            "maximum_gestures_per_phrase": 2,
        },
        "intent_bindings": {
            "neutral": binding(
                roles=["neutral", "recovery"],
                pose_ids=[pose("ACT", 1)],
                action_ids=[],
                clip_ids=["idle_front"],
                speech_compatible=True,
                interrupt_policy="immediate",
                minimum_hold_ms=650,
                recovery_intent=None,
            ),
            "listen": binding(
                roles=["listening"],
                pose_ids=[pose("ACT", 1)],
                action_ids=[],
                clip_ids=["idle_front"],
                speech_compatible=False,
                interrupt_policy="immediate",
                minimum_hold_ms=850,
                recovery_intent="neutral",
            ),
            "speak": binding(
                roles=["speaking"],
                pose_ids=[pose("ACT", 12)],
                action_ids=["explaining"],
                clip_ids=["action_explaining"],
                speech_compatible=True,
                interrupt_policy="phrase_boundary",
                minimum_hold_ms=400,
                recovery_intent="neutral",
            ),
            "explain": binding(
                roles=["gesture", "speaking"],
                pose_ids=[pose("ACT", 12), pose("ACT", 39)],
                action_ids=["explaining", "flourish"],
                clip_ids=["action_explaining", "action_flourish"],
                speech_compatible=True,
                interrupt_policy="phrase_boundary",
                minimum_hold_ms=650,
                recovery_intent="speak",
            ),
            "pointing": binding(
                roles=["gesture"],
                pose_ids=[pose("ACT", 16)],
                action_ids=["pointing"],
                clip_ids=["action_pointing"],
                speech_compatible=True,
                interrupt_policy="commit_then_recover",
                minimum_hold_ms=500,
                recovery_intent="speak",
            ),
            "think": binding(
                roles=["reaction"],
                pose_ids=[pose("ACT", 61)],
                action_ids=["thinking"],
                clip_ids=["action_thinking"],
                speech_compatible=False,
                interrupt_policy="immediate",
                minimum_hold_ms=850,
                recovery_intent="neutral",
            ),
            "celebrate": binding(
                roles=["gesture", "reaction"],
                pose_ids=[pose("ACT", 42)],
                action_ids=["celebrate"],
                clip_ids=["action_celebrate"],
                speech_compatible=True,
                interrupt_policy="commit_then_recover",
                minimum_hold_ms=750,
                recovery_intent="neutral",
            ),
            "walking": binding(
                roles=["locomotion"],
                pose_ids=[pose("ACT", index) for index in range(76, 80)],
                action_ids=[],
                clip_ids=["walk_front"],
                speech_compatible=True,
                interrupt_policy="commit_then_recover",
                minimum_hold_ms=800,
                recovery_intent="neutral",
            ),
            "flying": binding(
                roles=["flight", "locomotion"],
                pose_ids=[pose("FLY", index) for index in range(14, 18)],
                action_ids=[],
                clip_ids=["glide_cycle"],
                speech_compatible=True,
                interrupt_policy="commit_then_recover",
                minimum_hold_ms=900,
                recovery_intent="neutral",
            ),
            "hover": binding(
                roles=["flight", "speaking"],
                pose_ids=[pose("FLY", 40), pose("FLY", 43), pose("FLY", 44)],
                action_ids=[],
                clip_ids=["hover_cycle"],
                speech_compatible=True,
                interrupt_policy="phrase_boundary",
                minimum_hold_ms=700,
                recovery_intent="flying",
            ),
        },
    }


def build_candidate(index_path: Path, destination: Path) -> dict[str, Any]:
    index_path = Path(index_path).resolve()
    source_root = index_path.parent
    index = json.loads(index_path.read_text(encoding="utf-8"))
    character_id = str(index.get("character_id", ""))
    if character_id not in SUPPORTED_SHARED_CANVAS_CHARACTERS:
        raise ValueError(
            "candidate builder accepts only the audited shared-canvas "
            "characters: {}".format(
                ", ".join(sorted(SUPPORTED_SHARED_CANVAS_CHARACTERS))
            )
        )
    if index.get("review_projection") is not True:
        raise ValueError("source library must be a review projection")
    if index.get("runtime_admitted") is not False:
        raise ValueError("source library must remain runtime-unadmitted")
    destination.mkdir(parents=True, exist_ok=True)

    candidate_index = json.loads(json.dumps(index))
    for shard in candidate_index["shards"]:
        source = (source_root / shard["path"]).resolve()
        target = destination / source.name
        _linked_copy(source, target)
        shard["path"] = source.name
        if hashlib.sha256(target.read_bytes()).hexdigest() != shard["sha256"]:
            raise ValueError("copied shard checksum mismatch")
    index_digest = _write_json(
        destination / "hd-pose-library-index.json",
        candidate_index,
    )

    manifest, library = _pose_documents(candidate_index)
    pose_ids = [str(pose["pose_id"]) for pose in candidate_index["poses"]]
    graph = _graph(candidate_index, pose_ids)
    profile = _runtime_profile(candidate_index)
    choreography = _choreography_dictionary(candidate_index)
    package_capabilities = [
        "seven_view_static_facing_with_declared_northeast_fallback",
        "source_backed_whole_pose_actions",
        "ground_locomotion_cycle",
        "flight_cycle",
        "catalog_pose_override",
    ]
    files = {
        "animation_graph": (
            "{}-animation-graph-v2.json".format(character_id),
            graph,
        ),
        "pose_library": (
            "{}-pose-catalog-v1.json".format(character_id),
            library,
        ),
        "pose_manifest": (
            "{}-pose-manifest-v1.json".format(character_id),
            manifest,
        ),
        "runtime_profile": (
            "{}-runtime-profile-v2.json".format(character_id),
            profile,
        ),
        "choreography_dictionary": (
            "{}-choreography-dictionary-v1.json".format(character_id),
            choreography,
        ),
    }
    asset_records: dict[str, dict[str, str]] = {}
    for role, (name, content) in files.items():
        digest = _write_json(destination / name, content)
        asset_records[role] = {
            "path": name,
            "sha256": "sha256:" + digest,
        }

    clip_count = len(graph["clips"])
    node_count = len(graph["nodes"])
    capability = {
        "schema_version": 1,
        "character_id": candidate_index["character_id"],
        "renderer_adapter_id": "asciline.hd_rgba_pose.v1",
        "runtime_api_version": 1,
        "status": "candidate_review_only",
        "capabilities": package_capabilities,
        "counts": {
            "clip_count": clip_count,
            "diagnostic_only_pose_count": 0,
            "graph_admitted_pose_count": len(pose_ids),
            "node_count": node_count,
            "pose_count": len(pose_ids),
            "transition_count": 0,
        },
        "graph_admitted_pose_ids": sorted(pose_ids),
        "diagnostic_only_pose_ids": [],
        "denied_or_pending": [
            "authored_blink_cycle",
            "facial_viseme_lipsync",
            "governed_av_acceptance_bundle",
            "runtime_registry_admission",
        ],
    }
    capability_name = "{}-capability-manifest-v1.json".format(character_id)
    capability_digest = _write_json(
        destination / capability_name,
        capability,
    )
    asset_records["capability_manifest"] = {
        "path": capability_name,
        "sha256": "sha256:" + capability_digest,
    }
    asset_records["hd_pose_library_index"] = {
        "path": "hd-pose-library-index.json",
        "sha256": "sha256:" + index_digest,
    }
    for shard_number, shard in enumerate(candidate_index["shards"], start=1):
        asset_records["hd_pose_shard_{:03d}".format(shard_number)] = {
            "path": str(shard["path"]),
            "sha256": "sha256:" + str(shard["sha256"]),
        }

    package = {
        "schema_version": 2,
        "character_id": candidate_index["character_id"],
        "display_name": candidate_index["display_name"],
        "runtime_api": {"min": 1, "max": 1},
        "renderer": "asciline_hd_rgba",
        "renderer_adapter_id": "asciline.hd_rgba_pose.v1",
        "assets": asset_records,
        "default_pose_id": _pose_id(candidate_index, "ACT", 1),
        "capabilities": package_capabilities,
    }
    package_name = "{}-character-package-v2.json".format(character_id)
    package_digest = _write_json(destination / package_name, package)
    receipt = {
        "schema_version": 1,
        "status": "candidate_review_only",
        "character_id": candidate_index["character_id"],
        "source_library_index": _portable_source_path(index_path),
        "source_library_index_sha256": _sha256(index_path.read_bytes()),
        "candidate_library_index_sha256": index_digest,
        "package": package_name,
        "package_sha256": "sha256:" + package_digest,
        "pose_count": len(pose_ids),
        "runtime_admitted": False,
    }
    _write_json(destination / "runtime-candidate-receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a review-only HD RGBA CharacterPackage candidate."
    )
    parser.add_argument("library_index", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    receipt = build_candidate(args.library_index, args.destination)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
