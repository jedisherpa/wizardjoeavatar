#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
AUTHORITY_ORDER = (
    "serena-quill",
    "aurelia-finch",
    "selene-hart",
    "thorne-vale",
    "elara-voss",
    "kai-renner",
    "mira-solen",
    "draven-holt",
    "liora-kane",
    "rohan-slate",
    "finn-calder",
    "orion-vale",
)
SOURCE_PLANS = {
    "serena-quill": ("w1", "w2", "w3", "w4", "w5", "w6", "w7", "w8"),
    "aurelia-finch": (
        "g1",
        "g2",
        "g3",
        "g4",
        "g5",
        "g6",
        "base",
        "g7",
    ),
    "selene-hart": ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"),
    "thorne-vale": ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"),
    "elara-voss": ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"),
    "kai-renner": ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"),
    "mira-solen": ("g1", "g2", "g3", "g4", "g5", "g6", "p1", "p2"),
    "draven-holt": ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"),
    "liora-kane": ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"),
    "rohan-slate": ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"),
    "finn-calder": ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"),
    "orion-vale": ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"),
}
SOURCE_SELECTION_OVERRIDES = {
    (
        "elara-voss",
        "g3",
    ): "e80460703d5d63a528a1f2ed39be1c8f244197ba46d9130c6ea6b8936d819957",
    (
        "liora-kane",
        "g5",
    ): "e5f9d614ab8bfc4fca38c5fb0a92d27758b4cd35bdf8ba0583e9aeae11776f8a",
    (
        "rohan-slate",
        "g1",
    ): "4ad839e30dee52f6e31c1be6a2969b7094a22121dabfb3d187958327efa85808",
}
GATES = (
    "source_census",
    "source_conflicts_resolved",
    "source_sequence_complete",
    "silhouette_extraction",
    "transparent_pixel_graph",
    "canonical_canvas",
    "visual_parity",
    "package_compilation",
    "runtime_admission",
    "observer_review",
    "product_approval",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as destination:
        json.dump(value, destination, indent=2, sort_keys=True)
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())
    temporary.replace(path)


def _member_name(character_id: str, sequence_id: str) -> str | None:
    if sequence_id == "base":
        return f"sheet-{character_id}.png"
    if sequence_id == "strip":
        return f"strip-{character_id}.png"
    if sequence_id in {"g7", "g8"}:
        return None
    return f"sheet-{character_id}-{sequence_id}.png"


def _source_occurrences(
    census: dict[str, Any], member_name: str
) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for archive in census["archives"]:
        for member in archive["members"]:
            if member["member_name"] == member_name:
                occurrences.append(
                    {
                        "archive_id": archive["archive_id"],
                        "archive_sha256": archive["sha256"],
                        "member_name": member_name,
                        "member_sha256": member["sha256"],
                        "width": member["width"],
                        "height": member["height"],
                        "mode": member["mode"],
                        "decoded_format": member["decoded_format"],
                    }
                )
    return occurrences


def _source_sequence(
    census: dict[str, Any],
    *,
    character_id: str,
    sequence_ordinal: int,
    sequence_id: str,
) -> dict[str, Any]:
    member_name = _member_name(character_id, sequence_id)
    occurrences = (
        _source_occurrences(census, member_name)
        if member_name is not None
        else []
    )
    unique_hashes = {item["member_sha256"] for item in occurrences}
    selected_hash = SOURCE_SELECTION_OVERRIDES.get(
        (character_id, sequence_id)
    )
    selected_source = next(
        (
            occurrence
            for occurrence in occurrences
            if occurrence["member_sha256"] == selected_hash
        ),
        None,
    )
    if selected_hash is not None and selected_source is None:
        raise ValueError(
            f"selected source for {character_id} {sequence_id} "
            "is absent from the census"
        )
    if not occurrences:
        status = "missing_requires_authoring"
    elif len(unique_hashes) > 1 and selected_source is None:
        status = "source_conflict_pending_visual_resolution"
    else:
        status = "available_pending_silhouette_audit"
    return {
        "sequence_ordinal": sequence_ordinal,
        "sequence_id": sequence_id,
        "member_name": member_name,
        "status": status,
        "expected_pose_count": 6,
        "selected_source": selected_source,
        "source_candidates": occurrences,
        "selection_note": (
            "A conflicting member was selected by full-size visual audit; "
            "all alternatives remain provenance-visible."
            if selected_source is not None and len(unique_hashes) > 1
            else None
        ),
    }


def _motion_slots(source_sequences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    pose_number = 1
    for sequence in source_sequences:
        for frame_index in range(1, 7):
            slots.append(
                {
                    "slot_id": f"motion-{pose_number:03d}",
                    "source_sequence_ordinal": sequence["sequence_ordinal"],
                    "source_sequence_id": sequence["sequence_id"],
                    "source_frame_index": frame_index,
                    "source_status": sequence["status"],
                    "pose_id": None,
                    "rgba_sha256": None,
                    "silhouette_status": "pending",
                    "visual_parity": "pending",
                    "runtime_admitted": False,
                }
            )
            pose_number += 1
    if len(slots) != 48:
        raise ValueError("each character parity plan must contain 48 slots")
    return slots


def _gate_statuses(
    source_sequences: list[dict[str, Any]],
) -> dict[str, str]:
    statuses = {gate: "pending" for gate in GATES}
    statuses["source_census"] = "complete"
    has_conflict = any(
        sequence["status"] == "source_conflict_pending_visual_resolution"
        for sequence in source_sequences
    )
    has_missing = any(
        sequence["status"] == "missing_requires_authoring"
        for sequence in source_sequences
    )
    statuses["source_conflicts_resolved"] = (
        "blocked" if has_conflict else "complete"
    )
    statuses["source_sequence_complete"] = (
        "blocked" if has_missing or has_conflict else "complete"
    )
    statuses["runtime_admission"] = "denied_pending_approval"
    return statuses


def build_tracker(census: dict[str, Any]) -> dict[str, Any]:
    display_names = {
        record["character_id"]: record["display_name"]
        for record in census["authority_roster"]
    }
    characters: list[dict[str, Any]] = []
    for character_id in AUTHORITY_ORDER:
        source_sequences = [
            _source_sequence(
                census,
                character_id=character_id,
                sequence_ordinal=ordinal,
                sequence_id=sequence_id,
            )
            for ordinal, sequence_id in enumerate(
                SOURCE_PLANS[character_id], start=1
            )
        ]
        slots = _motion_slots(source_sequences)
        counts = {
            "target_pose_count": 48,
            "available_unique_slot_count": sum(
                slot["source_status"]
                == "available_pending_silhouette_audit"
                for slot in slots
            ),
            "conflicted_slot_count": sum(
                slot["source_status"]
                == "source_conflict_pending_visual_resolution"
                for slot in slots
            ),
            "authoring_required_slot_count": sum(
                slot["source_status"] == "missing_requires_authoring"
                for slot in slots
            ),
            "compiled_pose_count": 0,
            "visually_approved_pose_count": 0,
            "runtime_admitted_pose_count": 0,
        }
        characters.append(
            {
                "character_id": character_id,
                "display_name": display_names[character_id],
                "roster_state": "authority_roster",
                "parity_state": "source_planned",
                "source_sequences": source_sequences,
                "motion_slots": slots,
                "counts": counts,
                "gates": _gate_statuses(source_sequences),
                "supplemental_sources": (
                    [
                        {
                            "member_name": "strip-aurelia-finch.png",
                            "nominal_pose_count": 9,
                            "status": "pending_visual_deduplication",
                            "parity_slots_filled": 0,
                            "reason": (
                                "The strip overlaps earlier gait material and "
                                "cannot fill parity slots until pose-level "
                                "deduplication proves distinct motion."
                            ),
                            "source_candidates": _source_occurrences(
                                census, "strip-aurelia-finch.png"
                            ),
                        }
                    ]
                    if character_id == "aurelia-finch"
                    else []
                ),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": "joeville_12x48_visual_motion_parity_v001",
        "baseline": {
            "character_id": "wizard-joe",
            "reference_sequence": "phazer_all",
            "reference_pose_count": 48,
            "reference_status": "candidate_visual_parity",
            "canonical_canvas": [1254, 1254],
        },
        "contract": {
            "authority_character_count": 12,
            "target_pose_count_per_character": 48,
            "target_total_pose_count": 576,
            "source_pose_count_is_not_runtime_admission": True,
            "visual_parity_requires_human_approval": True,
            "runtime_admission_default": False,
        },
        "characters": characters,
        "supplied_extras": [
            {
                **record,
                "parity_state": "tracked_separately_not_admitted",
            }
            for record in census["supplied_extra_characters"]
        ],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the deterministic JoeVille 12x48 parity ledger."
    )
    parser.add_argument("census", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    tracker = build_tracker(_read_json(args.census.resolve()))
    _write_json_atomic(args.output.resolve(), tracker)
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "characters": len(tracker["characters"]),
                "target_poses": sum(
                    character["counts"]["target_pose_count"]
                    for character in tracker["characters"]
                ),
                "available_unique_slots": sum(
                    character["counts"]["available_unique_slot_count"]
                    for character in tracker["characters"]
                ),
                "conflicted_slots": sum(
                    character["counts"]["conflicted_slot_count"]
                    for character in tracker["characters"]
                ),
                "authoring_required_slots": sum(
                    character["counts"]["authoring_required_slot_count"]
                    for character in tracker["characters"]
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
