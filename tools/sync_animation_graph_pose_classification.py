#!/usr/bin/env python3
"""Synchronize animation-graph pose classifications with the source manifest."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from wizard_avatar.motion_manifest import expand_derived_bridge_series


DEFAULT_MANIFEST = ROOT / "assets" / "reference" / "motion_sources" / "manifest.json"
DEFAULT_GRAPH = (
    ROOT
    / "wizard_avatar"
    / "definitions"
    / "reference_avatar_animation_graph_v2.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def infer_classification(
    pose: dict[str, Any],
    uses: list[tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    locomotion = str(pose.get("locomotion", "idle"))
    tags = {str(tag) for tag in pose.get("tags", [])}
    airborne = locomotion in {"airborne", "flying"}
    if locomotion == "landing":
        altitude_class = "landing"
    elif locomotion == "jump":
        altitude_class = "takeoff"
    elif airborne:
        altitude_class = "airborne"
    else:
        altitude_class = "grounded"

    roles = ["clip_sample"] if uses else ["diagnostic_only"]
    if uses and (
        "inbetween" in tags
        or "turn" in tags
        or "stop" in tags
        or all(clip["family"] == "transition" for clip, _sample in uses)
    ):
        roles.append("transition_sample")

    contacts = [str(sample["support_contact"]) for _clip, sample in uses]
    if airborne:
        support_contact = "none"
        planted_anchor = None
    elif "both_feet" in contacts:
        support_contact = "both_feet"
        planted_anchor = next(
            (
                sample.get("planted_anchor")
                for _clip, sample in uses
                if sample.get("planted_anchor") is not None
            ),
            "left_foot",
        )
    elif contacts:
        support_contact = Counter(contacts).most_common(1)[0][0]
        planted_anchor = next(
            (
                sample.get("planted_anchor")
                for _clip, sample in uses
                if sample["support_contact"] == support_contact
            ),
            None,
        )
    else:
        support_contact = "none"
        planted_anchor = None

    return {
        "roles": roles,
        "altitude_class": altitude_class,
        "support_contact": support_contact,
        "planted_anchor": planted_anchor,
        "wing_mode": "extended",
        "staff_mode": "carried",
        "capability_tier": "A",
    }


def synchronized_graph(
    manifest: dict[str, Any],
    graph: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[str]]:
    expanded = expand_derived_bridge_series(manifest)
    poses = expanded.get("poses", [])
    classifications = graph.get("pose_classification", {})
    clips = graph.get("clips", {})
    uses_by_pose: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for clip in clips.values():
        for sample in clip["samples"]:
            uses_by_pose.setdefault(str(sample["pose_id"]), []).append((clip, sample))

    pose_ids = [str(pose["id"]) for pose in poses]
    unknown_uses = sorted(set(uses_by_pose) - set(pose_ids))
    if unknown_uses:
        raise ValueError(
            "animation clips reference poses absent from the expanded manifest: "
            + ", ".join(unknown_uses)
        )

    added = []
    reclassified = []
    synchronized = {}
    for pose in poses:
        pose_id = str(pose["id"])
        uses = uses_by_pose.get(pose_id, [])
        existing = classifications.get(pose_id)
        if existing is None:
            existing = infer_classification(pose, uses)
            added.append(pose_id)
        else:
            existing = dict(existing)
            roles = list(existing["roles"])
            if uses:
                normalized_roles = [
                    role for role in roles if role != "diagnostic_only"
                ]
                if "clip_sample" not in normalized_roles:
                    normalized_roles.insert(0, "clip_sample")
            else:
                normalized_roles = [
                    role for role in roles if role != "clip_sample"
                ]
                if "diagnostic_only" not in normalized_roles:
                    normalized_roles.append("diagnostic_only")
            if normalized_roles != roles:
                existing["roles"] = normalized_roles
                reclassified.append(pose_id)
        synchronized[pose_id] = existing

    return {**graph, "pose_classification": synchronized}, added, reclassified


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    graph = load_json(args.graph)
    updated, added, reclassified = synchronized_graph(load_json(args.manifest), graph)
    serialized = stable_json(updated)
    current = args.graph.read_text(encoding="utf-8")
    if args.check:
        if current != serialized:
            raise SystemExit(
                f"{args.graph} is not synchronized; {len(added)} classifications are missing"
                f" and {len(reclassified)} classifications have stale roles"
            )
    else:
        args.graph.write_text(serialized, encoding="utf-8")
    print(
        json.dumps(
            {
                "graph": str(args.graph),
                "pose_classifications": len(updated["pose_classification"]),
                "added": added,
                "reclassified": reclassified,
                "changed": current != serialized,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
