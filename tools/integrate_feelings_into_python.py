#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "assets" / "reference" / "motion_sources" / "manifest.json"
METADATA_PATH = ROOT / "assets" / "reference" / "motion_sources" / "feelings_python_metadata.json"
GRAPH_PATH = ROOT / "wizard_avatar" / "definitions" / "reference_avatar_animation_graph_v2.json"
LIBRARY_PATH = ROOT / "wizard_avatar" / "definitions" / "reference_avatar_pose_cells.json"
EXPECTED_NEW_POSES = 50
EXPECTED_TOTAL_POSES = 186


def stable_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def _point(anchor_map: Mapping[str, Mapping[str, int]], name: str) -> tuple[int, int]:
    point = anchor_map[name]
    return int(point["x"]), int(point["y"])


def _anchor_offsets(pose: Mapping[str, Any]) -> dict[str, list[int]]:
    raw = {str(anchor["id"]): anchor["point"] for anchor in pose["anchors"]}
    aliases = {
        "root": "root",
        "mouth": "mouth",
        "left_eye": "left_eye",
        "right_eye": "right_eye",
        "left_foot": "left_foot",
        "right_foot": "right_foot",
        "left_hand": "left_wrist",
        "right_hand": "right_wrist",
        "staff_hand": "staff_hand",
        "staff_tip": "staff_top",
    }
    root_x, root_y = _point(raw, "root")
    offsets: dict[str, list[int]] = {}
    for target, source in aliases.items():
        x, y = _point(raw, source)
        offsets[target] = [x - root_x, y - root_y]
    return offsets


def _phase(pose: Mapping[str, Any]) -> float | None:
    raw = pose["motion"].get("phase")
    if raw is None:
        return None
    denominator = int(raw["denominator"])
    return int(raw["numerator"]) / denominator


def _actions(semantic_id: str) -> list[str]:
    if semantic_id.startswith("feeling_"):
        return ["reaction", semantic_id.removeprefix("feeling_").rsplit("_", 1)[0]]
    if semantic_id.startswith("run_") or "run_charge" in semantic_id:
        return ["walking", "dash"]
    if "magic" in semantic_id or "victory_cast" in semantic_id:
        return ["magic_cast"]
    if "point" in semantic_id:
        return ["pointing"]
    if "thinking" in semantic_id:
        return ["thinking"]
    if "explaining" in semantic_id or "greeting" in semantic_id or "sincere" in semantic_id:
        return ["explaining"]
    if "idle" in semantic_id:
        return ["idle"]
    if "shush" in semantic_id:
        return ["shush"]
    if "staff_spin" in semantic_id:
        return ["staff_spin", "magic_cast"]
    if "celebrate" in semantic_id:
        return ["celebrate", "reaction"]
    if "guard" in semantic_id or "block" in semantic_id:
        return ["guard", "reaction"]
    return ["reaction"]


def _classification(pose: Mapping[str, Any]) -> dict[str, Any]:
    semantic_id = str(pose["semantic_id"])
    airborne = pose["motion"]["contact_mode"] == "airborne"
    if "staff_spin" in semantic_id:
        staff_mode = "spin"
    elif "guard" in semantic_id or "block" in semantic_id:
        staff_mode = "guard"
    elif "thrust" in semantic_id:
        staff_mode = "attack"
    elif "planted" in semantic_id or "brace" in semantic_id:
        staff_mode = "planted"
    else:
        staff_mode = "carried"
    return {
        "roles": ["diagnostic_only"],
        "altitude_class": "airborne" if airborne else "grounded",
        "support_contact": "none" if airborne else "both_feet",
        "planted_anchor": None if airborne else "left_foot",
        "wing_mode": "extended",
        "staff_mode": staff_mode,
        "capability_tier": "C",
    }


def _description(semantic_id: str) -> str:
    return semantic_id.replace("_", " ")


def _manifest_entry(pose: Mapping[str, Any]) -> dict[str, Any]:
    semantic_id = str(pose["semantic_id"])
    source_path = ROOT / str(pose["source"])
    if not source_path.is_file():
        raise ValueError(f"Missing tracked feelings source: {source_path.relative_to(ROOT)}")
    family = str(pose["motion"]["family"])
    tags = [
        "front",
        "wings",
        "feelings_expansion",
        family,
        str(pose["candidate_id"]).lower(),
    ]
    if semantic_id.startswith("feeling_"):
        tags.extend(semantic_id.removeprefix("feeling_").split("_"))
    return {
        "id": semantic_id,
        "source": str(source_path.relative_to(ROOT)),
        "source_path": str(source_path.relative_to(ROOT)),
        "description": _description(semantic_id),
        "facing": str(pose["facing"]["direction"]),
        "locomotion": "walking" if family == "run" else "idle",
        "actions": _actions(semantic_id),
        "phase": _phase(pose),
        "generation_rows": int(pose["generation_rows"]),
        "tags": tags,
        "anchor_offsets": _anchor_offsets(pose),
    }


def _load_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    return metadata, manifest, graph


def integrate(*, check_only: bool = False) -> dict[str, Any]:
    metadata, manifest, graph = _load_inputs()
    metadata_poses = list(metadata["poses"])
    if metadata.get("pose_count") != EXPECTED_NEW_POSES or len(metadata_poses) != EXPECTED_NEW_POSES:
        raise ValueError(
            f"Expected {EXPECTED_NEW_POSES} Python pose metadata records, found {len(metadata_poses)}"
        )

    existing_by_id = {str(pose["id"]): pose for pose in manifest["poses"]}
    added_ids: list[str] = []
    for pose in metadata_poses:
        semantic_id = str(pose["semantic_id"])
        entry = _manifest_entry(pose)
        existing = existing_by_id.get(semantic_id)
        if existing is None:
            manifest["poses"].append(entry)
            existing_by_id[semantic_id] = entry
            added_ids.append(semantic_id)
        elif existing != entry:
            raise ValueError(f"Existing Python manifest entry drifted for {semantic_id}")
        graph["pose_classification"].setdefault(semantic_id, _classification(pose))

    if len(manifest["poses"]) != EXPECTED_TOTAL_POSES:
        raise ValueError(
            f"Expected {EXPECTED_TOTAL_POSES} Python poses, found {len(manifest['poses'])}"
        )
    if set(graph["pose_classification"]) != set(existing_by_id):
        raise ValueError("Animation graph classification does not cover the complete Python pose catalog")

    if check_only:
        library = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
        library_ids = {str(pose["id"]) for pose in library["poses"]}
        if library_ids != set(existing_by_id):
            raise ValueError("Generated Python cell library is out of sync with the expanded manifest")
    else:
        if added_ids:
            manifest["version"] = int(manifest.get("version", 1)) + len(added_ids)
        MANIFEST_PATH.write_text(stable_json(manifest), encoding="utf-8")
        GRAPH_PATH.write_text(stable_json(graph), encoding="utf-8")
        subprocess.run(
            [sys.executable, "tools/generate_reference_avatar_pose_cells.py", "--check-deterministic"],
            cwd=ROOT,
            check=True,
        )

    return {
        "result": "passed",
        "added_pose_count": len(added_ids),
        "python_pose_count": len(manifest["poses"]),
        "pose_ids": [str(pose["id"]) for pose in manifest["poses"]],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministically integrate the unique feelings poses into the Python ASCILINE library."
    )
    parser.add_argument("--check", action="store_true", help="Verify the integrated outputs without writing them.")
    args = parser.parse_args()
    print(stable_json(integrate(check_only=args.check)), end="")


if __name__ == "__main__":
    main()
