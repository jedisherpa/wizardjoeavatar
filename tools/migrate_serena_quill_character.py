#!/usr/bin/env python3
"""Deterministically migrate Serena Quill intake into target package artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
CHARACTER_DIR = (
    ROOT / "wizard_avatar" / "definitions" / "characters" / "serena_quill"
)
INTAKE_DIR = CHARACTER_DIR / "intake"
REFERENCE_DIR = ROOT / "assets" / "reference" / "personas" / "serena-quill"
SOURCE_COMMIT = "196c2389c71ca5276eed594d822d29b76310dd2f"
ASSET_SET_ID = "serena-quill-worksheet-motion-v1"
CHARACTER_ID = "serena-quill-v1"
CORE_ANCHORS = (
    "root",
    "mouth",
    "left_eye",
    "right_eye",
    "left_foot",
    "right_foot",
    "left_hand",
    "right_hand",
)
MOTION_IDS = {
    "walk_contact_left",
    "walk_down_left",
    "walk_passing_right",
    "walk_up_right",
    "run_contact_left",
    "run_passing_right",
    "start",
    "stop",
    "turn_left",
    "turn_right",
    "crouch",
    "jump_anticipation",
    "jump_airborne",
    "fall",
    "land_contact",
    "land_recovery",
}
EVIDENCE_BACKED_MOTION_IDS = {
    "walk_contact_left",
    "run_contact_left",
    "jump_airborne",
}
OUTPUTS = {
    "pose_manifest": CHARACTER_DIR / "serena_quill_pose_manifest.json",
    "animation_graph": CHARACTER_DIR / "serena_quill_animation_graph_v2.json",
    "runtime_profile": CHARACTER_DIR / "serena_quill_runtime_profile_v1.json",
    "capability_manifest": CHARACTER_DIR / "serena_quill_capability_profile_v1.json",
    "intake_manifest": CHARACTER_DIR / "serena_quill_intake_manifest.json",
    "package": CHARACTER_DIR / "serena_quill_character_package_v2.json",
}
FROZEN_SOURCE_HASHES = {
    INTAKE_DIR / "serena_quill_animation_graph.json": (
        "sha256:25cd9eb67320d31182a58b0bec0e6b9e037e9ce948d4b00c78096fd2c8ace23e"
    ),
    INTAKE_DIR / "serena_quill_animation_matrix.json": (
        "sha256:bb9731d964e936a448f8348981bf89fb86df48cf6bf65e685871826568ea8263"
    ),
    INTAKE_DIR / "serena_quill_character_manifest.json": (
        "sha256:2ed81123cce1ac7a6cc2a1c2f22de550f5edb8cd68f1284affec2469d035003a"
    ),
    INTAKE_DIR / "serena_quill_character_package.json": (
        "sha256:1973d1c7a726c0daf23ab56b22491c74b704c4aa6764546df93dbbfe20598de9"
    ),
    INTAKE_DIR / "serena_quill_extraction_audit.json": (
        "sha256:577eb6f58dd03ce95a08243cbd40dc5f1f1309cc532e1ae5c433f5adc3bd790f"
    ),
    INTAKE_DIR / "serena_quill_pixel_graphs.json": (
        "sha256:0f6da5165d029632edba67a12791ca545a5d74d3c81b2c1a98922c7e2f0232fa"
    ),
    INTAKE_DIR / "serena_quill_pose_cells.json": (
        "sha256:8aaa6fc0ba3fb0a2a92a0d3ba5f95101b0ea06deba625b9e3f17ad36368c22e4"
    ),
    INTAKE_DIR / "serena_quill_runtime_profile.json": (
        "sha256:43e06748c51f1d3b9896ce396329146e751efe13e0a737542ca982c8491f504e"
    ),
    REFERENCE_DIR / "canonical-voxel.png": (
        "sha256:e1a0d2eac7a867b0bbf60810de5cfab40f328bceba6f61b2a18c717b8bcc0349"
    ),
    REFERENCE_DIR
    / "canonical-worksheets"
    / "01-identity-sheet-candidate-v1-rejected.png": (
        "sha256:42bfd209f4e493164ef56c8c466f99c39a12cee1ddd7155b0515790c74555301"
    ),
    REFERENCE_DIR
    / "canonical-worksheets"
    / "01-identity-sheet-candidate-v2.png": (
        "sha256:18ae92d61482755c06960b3bb532d2e56a45cc59bb7070cd06bac7e2315f3602"
    ),
    REFERENCE_DIR
    / "canonical-worksheets"
    / "01-identity-sheet-candidate-v3.png": (
        "sha256:a6405defd8a031426bd3f3c2f0bbe426ed5a766f6f5063290cd46ebbd5047fbb"
    ),
    REFERENCE_DIR
    / "canonical-worksheets"
    / "02-turnaround-sheet-candidate-v1.png": (
        "sha256:d476d6aa2d1c2961135a6e6774bde2fc50d765174cddca0cec9c273201bfdafd"
    ),
    REFERENCE_DIR
    / "canonical-worksheets"
    / "03-neutral-base-poses-candidate-v1.png": (
        "sha256:be5702f9e655dac6bf9b826bf162588d0d6cf69f91ddb1e3cf3ead6f8697fdf2"
    ),
    REFERENCE_DIR
    / "canonical-worksheets"
    / "04-expression-sheet-candidate-v1.png": (
        "sha256:f163614a617a6ca601e9862d4b04843ec77b8d9bf53c9b60926951cb8fba1f71"
    ),
    REFERENCE_DIR
    / "canonical-worksheets"
    / "05-speech-viseme-sheet-candidate-v1.png": (
        "sha256:f35dc783f6192a99f6b422c7cc1dd5408d74d8afb57c84277f40aee87582a29f"
    ),
    REFERENCE_DIR
    / "canonical-worksheets"
    / "06-hand-prop-sheet-candidate-v1.png": (
        "sha256:b7ef9f1f79840efc0892f52590341e8847dbb2bd01a1d29456e773ce27661c41"
    ),
    REFERENCE_DIR
    / "canonical-worksheets"
    / "07-ground-motion-sheet-candidate-v1.png": (
        "sha256:85082be9d7566eefe4af68301896ec4d41ec9fb8c5745e7c1840e983500a4413"
    ),
    REFERENCE_DIR
    / "canonical-worksheets"
    / "08-signature-actions-sheet-candidate-v1.png": (
        "sha256:6f3db8f1ab455a593f33af235ba634041899a7d174264c2ab15d7b18271e7c94"
    ),
    REFERENCE_DIR
    / "canonical-worksheets"
    / "09-interaction-poses-candidate-v1.png": (
        "sha256:353b91fc8492aac9f544a79584545dfcd12388416584d43633b9ccec341c856e"
    ),
    REFERENCE_DIR / "generation-profile.json": (
        "sha256:25de4fb4ed3718ca948981bffcfbb66fc5c51ef28897e772966d7ca9721dc6ab"
    ),
    REFERENCE_DIR / "source-reference.png": (
        "sha256:1a388910b47b351427981f029dfac90366ffbc9bf891f7bcb294994381d19d3d"
    ),
}


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _encoded(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _verify_frozen_sources() -> None:
    expected_paths = set(FROZEN_SOURCE_HASHES)
    actual_paths = {
        path for path in INTAKE_DIR.rglob("*") if path.is_file()
    }
    actual_paths.update(
        path for path in REFERENCE_DIR.rglob("*") if path.is_file()
    )
    mismatches = {
        str(path.relative_to(ROOT))
        for path, expected in FROZEN_SOURCE_HASHES.items()
        if not path.is_file() or _sha256(path) != expected
    }
    mismatches.update(
        "unexpected:" + str(path.relative_to(ROOT))
        for path in actual_paths - expected_paths
    )
    mismatches.update(
        "missing:" + str(path.relative_to(ROOT))
        for path in expected_paths - actual_paths
    )
    if mismatches:
        raise ValueError(
            "Serena Quill frozen source mismatch: {}".format(
                ", ".join(sorted(mismatches))
            )
        )


def _pose_category(pose_id: str, graph_kind: str) -> str:
    if graph_kind == "feature_graph":
        return "feature"
    if pose_id.startswith("expression_"):
        return "expression"
    if pose_id.startswith("viseme_") or pose_id.startswith("blink_"):
        return "speech"
    if pose_id in MOTION_IDS:
        return "motion"
    if pose_id.startswith("neutral_"):
        return "neutral"
    if pose_id.startswith("idle_"):
        return "idle"
    if pose_id.startswith("interaction_"):
        return "interaction"
    return "signature"


def _admission(pose: Mapping[str, Any]) -> str:
    if pose["graph_kind"] == "feature_graph":
        return "diagnostic_only"
    if pose["id"] in MOTION_IDS and pose["id"] not in EVIDENCE_BACKED_MOTION_IDS:
        return "diagnostic_only"
    return "graph_admitted"


def _contact(pose_id: str, admission: str) -> Mapping[str, Any]:
    if pose_id == "jump_airborne":
        return {
            "altitude_class": "airborne",
            "support_contact": "none",
            "planted_anchor": None,
            "root_policy": "air_trajectory",
            "evidence": "pose_id_exact",
        }
    if pose_id in {"walk_contact_left", "run_contact_left"}:
        return {
            "altitude_class": "grounded",
            "support_contact": "left_foot",
            "planted_anchor": "left_foot",
            "root_policy": "contact_locked",
            "evidence": "pose_id_exact",
        }
    if admission == "graph_admitted":
        return {
            "altitude_class": "grounded",
            "support_contact": "none",
            "planted_anchor": None,
            "root_policy": "fixed",
            "evidence": "unreviewed_static",
        }
    return {
        "altitude_class": (
            "airborne" if pose_id in {"fall"} else "grounded"
        ),
        "support_contact": "none",
        "planted_anchor": None,
        "root_policy": "fixed",
        "evidence": "unresolved_diagnostic",
    }


def _phase(pose_id: str) -> float | None:
    phases = {
        "walk_contact_left": 0.0,
        "walk_down_left": 0.25,
        "walk_passing_right": 0.5,
        "walk_up_right": 0.75,
        "run_contact_left": 0.0,
        "run_passing_right": 0.5,
    }
    return phases.get(pose_id)


def _locomotion(pose_id: str, category: str) -> str:
    if pose_id.startswith("walk_"):
        return "walk"
    if pose_id.startswith("run_"):
        return "run"
    if pose_id in {"jump_airborne", "fall"}:
        return "airborne"
    if category == "motion":
        return "transition"
    return "idle"


def _source_profile() -> Mapping[str, Any]:
    return _read(INTAKE_DIR / "serena_quill_runtime_profile.json")


def _runtime_profile() -> Mapping[str, Any]:
    source = _source_profile()
    action_poses = {
        action_id: pose_id
        for action_id, pose_id in source["action_poses"].items()
        if pose_id not in MOTION_IDS
        or pose_id in EVIDENCE_BACKED_MOTION_IDS
    }
    return {
        "schema_version": 1,
        "character_id": CHARACTER_ID,
        "default_pose_id": source["default_pose_id"],
        "presentation_scale": [22, 25],
        "required_anchors": list(CORE_ANCHORS),
        "optional_anchors": ["orb"],
        "facing_poses": dict(source["facing_poses"]),
        "action_poses": action_poses,
        "expression_aliases": dict(source["expression_aliases"]),
        "locomotion_cycles": {
            "walk": [],
            "run": [],
            "flight": [],
        },
        "speech_poses": list(source["speech_poses"]),
        "blink_poses": dict(source["blink_poses"]),
        "props": {
            "orb": {
                "composition": "whole_pose",
                "anchor": "orb",
                "permission_capability": None,
            }
        },
    }


def _pose_manifest(
    pose_library: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> Mapping[str, Any]:
    actions_by_pose: dict[str, list[str]] = defaultdict(list)
    for action_id, pose_id in profile["action_poses"].items():
        actions_by_pose[pose_id].append(action_id)
    poses = []
    for pose in pose_library["poses"]:
        pose_id = pose["id"]
        category = _pose_category(pose_id, pose["graph_kind"])
        admission = _admission(pose)
        contact = _contact(pose_id, admission)
        actions = sorted(actions_by_pose.get(pose_id, []))
        if not actions:
            actions = ["speaking"] if category == "speech" else ["idle"]
        poses.append(
            {
                "id": pose_id,
                "source": pose["source"],
                "description": pose.get("description", ""),
                "facing": pose.get("facing", "south"),
                "locomotion": _locomotion(pose_id, category),
                "actions": actions,
                "phase": _phase(pose_id),
                "tags": [
                    category,
                    pose["graph_kind"],
                    admission,
                    contact["evidence"],
                ],
                "admission": admission,
                "composition": (
                    "region_overlay"
                    if pose["graph_kind"] == "feature_graph"
                    else "whole_pose"
                ),
                "features": {
                    "orb": "orb" in pose.get("anchors", {}),
                    "wings": pose["graph_kind"] == "full_body_graph",
                    "halo": pose["graph_kind"] == "full_body_graph",
                },
                "contact_profile": dict(contact),
                "provenance": {
                    "source_commit": SOURCE_COMMIT,
                    "source_graph_kind": pose["graph_kind"],
                    "migration_status": admission,
                },
            }
        )
    return {
        "schema_version": 1,
        "asset_set_id": ASSET_SET_ID,
        "character_id": CHARACTER_ID,
        "required_anchors": list(CORE_ANCHORS),
        "optional_anchors": ["orb"],
        "poses": poses,
    }


def _family(category: str, pose_id: str) -> str:
    if category == "speech":
        return "speech"
    if category == "motion":
        return "flight" if pose_id == "jump_airborne" else "locomotion"
    if category in {"neutral", "idle"}:
        return "idle"
    return "action"


def _animation_graph(
    pose_library: Mapping[str, Any],
    manifest: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> Mapping[str, Any]:
    manifest_by_id = {pose["id"]: pose for pose in manifest["poses"]}
    admitted = [
        pose["id"]
        for pose in pose_library["poses"]
        if manifest_by_id[pose["id"]]["admission"] == "graph_admitted"
    ]
    default_pose_id = profile["default_pose_id"]
    clip_ids = {pose_id: "pose_" + pose_id for pose_id in admitted}
    node_ids = {pose_id: "node_" + pose_id for pose_id in admitted}
    all_clip_ids = [clip_ids[pose_id] for pose_id in admitted]
    actions_by_pose: dict[str, list[str]] = defaultdict(list)
    for action_id, pose_id in profile["action_poses"].items():
        if pose_id in clip_ids:
            actions_by_pose[pose_id].append(action_id)

    classifications = {}
    clips = {}
    nodes = {}
    for pose in pose_library["poses"]:
        pose_id = pose["id"]
        metadata = manifest_by_id[pose_id]
        contact = metadata["contact_profile"]
        admitted_pose = pose_id in clip_ids
        classifications[pose_id] = {
            "roles": ["clip_sample"] if admitted_pose else ["diagnostic_only"],
            "altitude_class": contact["altitude_class"],
            "support_contact": contact["support_contact"],
            "planted_anchor": contact["planted_anchor"],
            "wing_mode": (
                "folded" if pose_id == "protective_wing_fold" else "extended"
            ),
            "staff_mode": "absent",
            "capability_tier": "A" if admitted_pose else "C",
        }
        if not admitted_pose:
            continue
        category = _pose_category(pose_id, pose["graph_kind"])
        clip_id = clip_ids[pose_id]
        clips[clip_id] = {
            "clip_id": clip_id,
            "family": _family(category, pose_id),
            "supported_facings": [metadata["facing"]],
            "loop_mode": "loop" if pose_id == default_pose_id else "hold_last",
            "phase_source": "time" if pose_id == default_pose_id else "none",
            "root_policy": contact["root_policy"],
            "minimum_hold_ticks": 1,
            "interrupt_policy": "immediate",
            "channel_ownership": ["body"],
            "samples": [
                {
                    "pose_id": pose_id,
                    "duration_frames": 8,
                    "support_contact": contact["support_contact"],
                    "planted_anchor": contact["planted_anchor"],
                    "markers": [],
                }
            ],
            "entry_markers": [],
            "exit_markers": [],
            "secondary_curves": {},
            "legal_successors": all_clip_ids,
            "authored_fps": 24,
        }
        nodes[node_ids[pose_id]] = {
            "clip_id": clip_id,
            "mobility_modes": [
                "airborne" if contact["altitude_class"] == "airborne" else "grounded"
            ],
            "actions": sorted(actions_by_pose.get(pose_id, [])),
        }

    transitions = []
    default_node = node_ids[default_pose_id]
    for pose_id in admitted:
        if pose_id == default_pose_id:
            continue
        target_node = node_ids[pose_id]
        for source, target, suffix in (
            (default_node, target_node, "enter"),
            (target_node, default_node, "return"),
        ):
            transitions.append(
                {
                    "transition_id": "{}_{}_{}".format(source, target, suffix),
                    "source_node_id": source,
                    "target_node_id": target,
                    "priority": 10,
                    "duration_ticks": 0,
                    "timing_mode": "immediate",
                    "transition_recipe_id": "coherent_cut",
                    "phase_policy": "restart",
                    "root_policy": "fixed",
                    "contact_policy": "release",
                    "region_policy": "coherent_pose",
                    "interrupt_window": "immediate",
                    "fallback_transition_id": None,
                }
            )

    fallback_by_facing = {
        facing: clip_ids[pose_id]
        for facing, pose_id in profile["facing_poses"].items()
    }
    fallback_by_action = {
        action_id: clip_ids[pose_id]
        for action_id, pose_id in profile["action_poses"].items()
        if pose_id in clip_ids
    }
    return {
        "$schema": "https://wizardjoe.local/schemas/reference_avatar_animation_graph_v2.schema.json",
        "$id": "https://wizardjoe.local/graphs/serena-quill-v1",
        "schema_version": 2,
        "asset_set_id": ASSET_SET_ID,
        "authored_fps": 24,
        "simulation_hz": 60,
        "default_node_id": default_node,
        "capability_tiers": {
            "A": {"description": "Evidence-backed whole-pose Serena states."},
            "B": {"description": "Reserved for authored transition upgrades."},
            "C": {"description": "Diagnostic-only intake; not runtime selectable."},
        },
        "pose_classification": classifications,
        "clips": clips,
        "nodes": nodes,
        "transitions": transitions,
        "transition_recipes": {
            "coherent_cut": {
                "entry_rule": "hard_cut",
                "duration_frames": 0,
                "interrupt_source": "authored_sample",
                "region_masks": [],
            }
        },
        "channel_masks": {"body": ["whole_pose"]},
        "fallbacks": {
            "grounded_clip_id": clip_ids[default_pose_id],
            "airborne_clip_id": clip_ids["jump_airborne"],
            "by_facing": fallback_by_facing,
            "by_action": fallback_by_action,
        },
    }


def _capability_manifest(
    manifest: Mapping[str, Any],
    graph: Mapping[str, Any],
) -> Mapping[str, Any]:
    admitted = [
        pose["id"]
        for pose in manifest["poses"]
        if pose["admission"] == "graph_admitted"
    ]
    diagnostic = [
        pose["id"]
        for pose in manifest["poses"]
        if pose["admission"] == "diagnostic_only"
    ]
    return {
        "schema_version": 1,
        "character_id": CHARACTER_ID,
        "status": "migration_candidate_not_registered",
        "runtime_api_version": 1,
        "renderer_adapter_id": "asciline.pixel_graph.v1",
        "counts": {
            "pose_count": len(manifest["poses"]),
            "graph_admitted_pose_count": len(admitted),
            "diagnostic_only_pose_count": len(diagnostic),
            "clip_count": len(graph["clips"]),
            "node_count": len(graph["nodes"]),
            "transition_count": len(graph["transitions"]),
        },
        "graph_admitted_pose_ids": admitted,
        "diagnostic_only_pose_ids": diagnostic,
        "capabilities": [
            "eight_direction_static_facing",
            "evidence_backed_static_actions",
            "speech_whole_pose_frames",
            "blink_whole_pose_frames",
            "orb_whole_pose_states",
        ],
        "denied_or_pending": [
            "feature_overlay_composition",
            "full_walk_cycle",
            "full_run_cycle",
            "turn_contact_authoring",
            "landing_contact_authoring",
            "semantic_region_overlays",
            "production_registry_admission",
        ],
    }


def _intake_manifest() -> Mapping[str, Any]:
    files = []
    for path in sorted(INTAKE_DIR.rglob("*")):
        if not path.is_file():
            continue
        files.append(
            {
                "path": str(path.relative_to(CHARACTER_DIR)),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    for path in sorted(REFERENCE_DIR.rglob("*")):
        if path.is_file():
            files.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": _sha256(path),
                    "bytes": path.stat().st_size,
                }
            )
    return {
        "schema_version": 1,
        "character_id": CHARACTER_ID,
        "source_commit": SOURCE_COMMIT,
        "source_branch": "codex/persona-serena-quill",
        "files": files,
        "total_files": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
    }


def _package(generated: Mapping[Path, bytes]) -> Mapping[str, Any]:
    role_paths = {
        "pose_library": INTAKE_DIR / "serena_quill_pose_cells.json",
        "pose_manifest": OUTPUTS["pose_manifest"],
        "animation_graph": OUTPUTS["animation_graph"],
        "runtime_profile": OUTPUTS["runtime_profile"],
        "capability_manifest": OUTPUTS["capability_manifest"],
        "extraction_audit": INTAKE_DIR / "serena_quill_extraction_audit.json",
        "pixel_graph_library": INTAKE_DIR / "serena_quill_pixel_graphs.json",
        "source_character_manifest": INTAKE_DIR / "serena_quill_character_manifest.json",
        "source_animation_matrix": INTAKE_DIR / "serena_quill_animation_matrix.json",
        "intake_manifest": OUTPUTS["intake_manifest"],
    }
    return {
        "schema_version": 2,
        "character_id": CHARACTER_ID,
        "display_name": "Serena Quill",
        "runtime_api": {"min": 1, "max": 1},
        "renderer": "asciline_square_cells",
        "renderer_adapter_id": "asciline.pixel_graph.v1",
        "assets": {
            role: {
                "path": str(path.relative_to(CHARACTER_DIR)),
                "sha256": _sha256_bytes(
                    generated[path] if path in generated else path.read_bytes()
                ),
            }
            for role, path in sorted(role_paths.items())
        },
        "default_pose_id": "neutral_front",
        "capabilities": [
            "eight_direction_static_facing",
            "evidence_backed_static_actions",
            "speech_whole_pose_frames",
            "blink_whole_pose_frames",
            "orb_whole_pose_states",
        ],
    }


def generated_outputs() -> Mapping[Path, bytes]:
    _verify_frozen_sources()
    pose_library = _read(INTAKE_DIR / "serena_quill_pose_cells.json")
    profile = _runtime_profile()
    manifest = _pose_manifest(pose_library, profile)
    graph = _animation_graph(pose_library, manifest, profile)
    capability = _capability_manifest(manifest, graph)
    intake = _intake_manifest()
    values = {
        OUTPUTS["runtime_profile"]: profile,
        OUTPUTS["pose_manifest"]: manifest,
        OUTPUTS["animation_graph"]: graph,
        OUTPUTS["capability_manifest"]: capability,
        OUTPUTS["intake_manifest"]: intake,
    }
    encoded = {path: _encoded(value) for path, value in values.items()}
    encoded[OUTPUTS["package"]] = _encoded(_package(encoded))
    return encoded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify committed outputs without replacing them",
    )
    args = parser.parse_args()
    expected = generated_outputs()
    if args.check:
        mismatches = [
            str(path.relative_to(ROOT))
            for path, content in expected.items()
            if not path.is_file() or path.read_bytes() != content
        ]
        if mismatches:
            print("mismatched outputs:")
            for mismatch in mismatches:
                print("  " + mismatch)
            return 1
        print("Serena Quill migration outputs are reproducible.")
        return 0
    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        print("{} {}".format(_sha256(path), path.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
