#!/usr/bin/env python3
"""Freeze a supplemental JoeVille character's 48 authored poses."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AUTHORITY = (
    ROOT / "assets" / "reference" / "hd_canonical" / "manifest.json"
)
TARGET_POSE_COUNT = 48
SEQUENCE_COUNT = 8
FRAMES_PER_SEQUENCE = 6
CANONICAL_PROFILE = {
    "profile_id": "wizardjoe_hd_alpha_1254_v001",
    "canvas_width": 1254,
    "canvas_height": 1254,
    "baseline_y": 1185,
    "minimum_margin": 69,
    "color_space": "sRGB",
    "alpha_mode": "straight",
}
CHARACTER_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MOTION_CONTRACT_FIELDS = {
    "entry_handoffs",
    "exit_handoffs",
    "family",
    "hold_frame_indices",
    "interrupt_policy",
    "interruptible_frame_indices",
    "loop_mode",
    "root_policy",
    "support_policy",
}
PROJECTION_NORMALIZATION_FIELDS = {
    "anchor",
    "method",
    "resampling",
    "scale_basis_points",
    "schema_version",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as destination:
        destination.write(payload)
        destination.flush()
        os.fsync(destination.fileno())
    temporary.replace(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_character_id(character_id: str) -> None:
    if not CHARACTER_ID_PATTERN.fullmatch(character_id):
        raise ValueError("supplemental character_id must be a safe slug")


def _project_path(path: Path, project_root: Path, role: str) -> str:
    resolved_root = project_root.resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{role} must stay inside the project root") from exc
    if not relative.parts:
        raise ValueError(f"{role} must identify a project file")
    return relative.as_posix()


def _resolve_project_path(
    project_root: Path, value: object, role: str
) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{role} must be a project-relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{role} must be a project-relative path")
    root = project_root.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{role} escaped the project root") from exc
    return resolved


def _validate_profile(profile: object) -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise ValueError("authority must declare a master profile")
    if profile != CANONICAL_PROFILE:
        raise ValueError("supplemental poses require the canonical 1254 profile")
    return dict(profile)


def _validate_portable_receipt(
    receipt_path: Path, project_root: Path, role: str
) -> dict[str, Any]:
    receipt = _read_json(receipt_path)

    def visit(value: object, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, str(child_key))
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif key.endswith("_path"):
            resolved = _resolve_project_path(
                project_root, value, f"{role} {key}"
            )
            if not resolved.is_file():
                raise ValueError(f"{role} references a missing project file")

    visit(receipt)
    return receipt


def _validate_motion_contract(
    sequence_id: str, sequence: dict[str, Any]
) -> None:
    if not isinstance(sequence.get("intent"), str) or not sequence["intent"]:
        raise ValueError(f"{sequence_id} must declare an intent")
    if not isinstance(sequence.get("fps"), int) or sequence["fps"] <= 0:
        raise ValueError(f"{sequence_id} must declare a positive fps")
    if not isinstance(sequence.get("loop"), bool):
        raise ValueError(f"{sequence_id} must declare loop as a boolean")
    contract = sequence.get("motion_contract")
    if not isinstance(contract, dict) or set(contract) != MOTION_CONTRACT_FIELDS:
        raise ValueError(f"{sequence_id} motion contract fields mismatch")
    expected_loop_mode = "loop" if sequence["loop"] else "hold_last"
    if contract["loop_mode"] != expected_loop_mode:
        raise ValueError(f"{sequence_id} loop mode contradicts loop flag")


def _validate_projection_normalization(
    value: object,
    *,
    character_id: str,
) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != (
        PROJECTION_NORMALIZATION_FIELDS
    ):
        raise ValueError("projection normalization fields mismatch")
    if value["schema_version"] != 1:
        raise ValueError("projection normalization schema_version must be 1")
    if value["method"] != "per_pose_uniform_scale_v1":
        raise ValueError("unsupported projection normalization method")
    if value["anchor"] != "visible_bbox_center_baseline":
        raise ValueError("unsupported projection normalization anchor")
    if value["resampling"] != "nearest":
        raise ValueError("projection normalization must use nearest resampling")
    overrides = value["scale_basis_points"]
    if not isinstance(overrides, dict) or not overrides:
        raise ValueError("projection normalization needs pose scale overrides")
    expected_pose_ids = {
        f"{character_id.replace('-', '_')}_motion_{number:03d}"
        for number in range(1, TARGET_POSE_COUNT + 1)
    }
    for pose_id, basis_points in overrides.items():
        if pose_id not in expected_pose_ids:
            raise ValueError(
                "projection normalization references an unknown pose_id"
            )
        if (
            isinstance(basis_points, bool)
            or not isinstance(basis_points, int)
            or not 7500 <= basis_points <= 13500
            or basis_points == 10000
        ):
            raise ValueError(
                "projection scale basis points must be an integer "
                "between 7500 and 13500 and must change the pose"
            )
    return {
        "schema_version": 1,
        "method": value["method"],
        "anchor": value["anchor"],
        "resampling": value["resampling"],
        "scale_basis_points": dict(sorted(overrides.items())),
    }


def prepare_manifest(
    *,
    character_id: str,
    brief_plan_path: Path,
    authority_path: Path,
    output_path: Path,
    project_root: Path = ROOT,
) -> dict[str, Any]:
    """Validate and hash-freeze a supplemental character authoring set."""

    _validate_character_id(character_id)
    project_root = project_root.resolve()
    brief_plan_path = brief_plan_path.resolve()
    authority_path = authority_path.resolve()
    output_path = output_path.resolve()
    _project_path(brief_plan_path, project_root, "authoring brief")
    _project_path(authority_path, project_root, "authority manifest")
    _project_path(output_path, project_root, "supplemental manifest")

    plan = _read_json(brief_plan_path)
    authority = _read_json(authority_path)
    profile = _validate_profile(authority.get("master_profile"))
    if plan.get("schema_version") != 1:
        raise ValueError("supplemental authoring brief schema_version must be 1")
    if plan.get("character_id") != character_id:
        raise ValueError("supplemental authoring brief character_id mismatch")
    if not isinstance(plan.get("display_name"), str) or not plan["display_name"]:
        raise ValueError("supplemental authoring brief needs a display_name")
    if plan.get("roster_state") != "supplemental_authored_character":
        raise ValueError("supplemental authoring brief roster_state mismatch")
    if plan.get("review_projection") is not True:
        raise ValueError("supplemental authoring must be a review projection")
    if plan.get("runtime_admitted") is not False:
        raise ValueError("supplemental authoring must deny runtime admission")
    if plan.get("profile_id") != profile["profile_id"]:
        raise ValueError("supplemental authoring profile_id mismatch")
    projection_normalization = _validate_projection_normalization(
        plan.get("projection_normalization"),
        character_id=character_id,
    )

    plan_sequences = plan.get("sequences")
    if not isinstance(plan_sequences, dict):
        raise ValueError("supplemental authoring sequences must be an object")
    sequence_order = plan.get("sequence_order", list(plan_sequences))
    if (
        not isinstance(sequence_order, list)
        or len(sequence_order) != SEQUENCE_COUNT
        or len(set(sequence_order)) != SEQUENCE_COUNT
        or set(sequence_order) != set(plan_sequences)
    ):
        raise ValueError("supplemental authoring requires eight unique sequences")

    authored_root = output_path.parent / "authored-source"
    sequences: dict[str, Any] = {}
    seen_source_hashes: set[str] = set()
    seen_rgba_hashes: set[str] = set()
    pose_number = 1
    for sequence_id in sequence_order:
        sequence = plan_sequences[sequence_id]
        if not isinstance(sequence_id, str) or not sequence_id:
            raise ValueError("supplemental sequence_id must be non-empty")
        if not isinstance(sequence, dict):
            raise ValueError(f"{sequence_id} must be an object")
        _validate_motion_contract(sequence_id, sequence)
        briefs = sequence.get("frames")
        if not isinstance(briefs, list) or len(briefs) != FRAMES_PER_SEQUENCE:
            raise ValueError(f"{sequence_id} must contain exactly six frames")
        frames: list[dict[str, Any]] = []
        for frame_index, brief in enumerate(briefs, start=1):
            if not isinstance(brief, dict):
                raise ValueError(f"{sequence_id} frame must be an object")
            pose_id = (
                f"{character_id.replace('-', '_')}_motion_{pose_number:03d}"
            )
            slot_id = f"motion-{pose_number:03d}"
            if brief.get("pose_id") != pose_id:
                raise ValueError(f"{sequence_id} pose_id topology mismatch")
            if brief.get("slot_id") != slot_id:
                raise ValueError(f"{sequence_id} slot_id topology mismatch")
            if brief.get("frame_index") != frame_index:
                raise ValueError(f"{sequence_id} frame_index must be contiguous")

            filename = f"{pose_id}.png"
            paths = {
                "source": authored_root / "frames" / filename,
                "alpha_extracted": (
                    authored_root / "alpha-extracted" / filename
                ),
                "chroma_source": authored_root / "chroma-source" / filename,
                "alpha_extraction_receipt": (
                    authored_root
                    / "alpha-extraction-receipts"
                    / f"{pose_id}.json"
                ),
                "canonicalization_receipt": (
                    authored_root
                    / "canonicalization-receipts"
                    / f"{pose_id}.json"
                ),
            }
            for role, path in paths.items():
                _project_path(path, project_root, f"{pose_id} {role}")
                if not path.is_file():
                    raise ValueError(f"missing supplemental source: {path}")
            _validate_portable_receipt(
                paths["alpha_extraction_receipt"],
                project_root,
                f"{pose_id} alpha extraction receipt",
            )
            _validate_portable_receipt(
                paths["canonicalization_receipt"],
                project_root,
                f"{pose_id} canonicalization receipt",
            )

            with Image.open(paths["source"]) as source:
                source.load()
                if source.format != "PNG" or source.mode != "RGBA":
                    raise ValueError(f"{filename} must be an RGBA PNG")
                if source.size != (
                    profile["canvas_width"],
                    profile["canvas_height"],
                ):
                    raise ValueError(f"{filename} profile dimensions mismatch")
                rgba_sha256 = hashlib.sha256(source.tobytes()).hexdigest()
                bbox = source.getchannel("A").getbbox()
            if bbox is None:
                raise ValueError(f"{filename} has no visible silhouette")
            if bbox[3] != profile["baseline_y"]:
                raise ValueError(f"{filename} canonical baseline mismatch")
            margin = profile["minimum_margin"]
            if (
                bbox[0] < margin
                or bbox[1] < margin
                or profile["canvas_width"] - bbox[2] < margin
            ):
                raise ValueError(f"{filename} violates the canonical margin")

            source_sha256 = _sha256(paths["source"])
            if rgba_sha256 in seen_rgba_hashes:
                raise ValueError("supplemental RGBA poses must be unique")
            if source_sha256 in seen_source_hashes:
                raise ValueError("supplemental PNG poses must be unique")
            seen_source_hashes.add(source_sha256)
            seen_rgba_hashes.add(rgba_sha256)
            frames.append(
                {
                    **brief,
                    "source_path": _project_path(
                        paths["source"], project_root, "source frame"
                    ),
                    "source_sha256": source_sha256,
                    "rgba_sha256": rgba_sha256,
                    "alpha_extracted_path": _project_path(
                        paths["alpha_extracted"],
                        project_root,
                        "alpha extracted frame",
                    ),
                    "alpha_extracted_sha256": _sha256(
                        paths["alpha_extracted"]
                    ),
                    "chroma_source_path": _project_path(
                        paths["chroma_source"],
                        project_root,
                        "chroma source frame",
                    ),
                    "chroma_source_sha256": _sha256(paths["chroma_source"]),
                    "alpha_extraction_receipt": {
                        "path": _project_path(
                            paths["alpha_extraction_receipt"],
                            project_root,
                            "alpha extraction receipt",
                        ),
                        "sha256": _sha256(
                            paths["alpha_extraction_receipt"]
                        ),
                    },
                    "canonicalization_receipt": {
                        "path": _project_path(
                            paths["canonicalization_receipt"],
                            project_root,
                            "canonicalization receipt",
                        ),
                        "sha256": _sha256(
                            paths["canonicalization_receipt"]
                        ),
                    },
                    "canonical_bbox": list(bbox),
                    "authorship": "authored_full_size_imagegen_v1",
                }
            )
            pose_number += 1
        sequences[sequence_id] = {
            "intent": sequence["intent"],
            "fps": sequence["fps"],
            "loop": sequence["loop"],
            "motion_contract": dict(sequence["motion_contract"]),
            "frames": frames,
        }

    if pose_number - 1 != TARGET_POSE_COUNT:
        raise ValueError("supplemental authoring must contain exactly 48 poses")
    manifest = {
        "schema_version": 1,
        "manifest_type": "joeville_supplemental_character_motion",
        "character_id": character_id,
        "display_name": plan["display_name"],
        "roster_state": "supplemental_authored_character",
        "profile": profile,
        "authority_manifest": {
            "path": _project_path(
                authority_path, project_root, "authority manifest"
            ),
            "sha256": _sha256(authority_path),
        },
        "authoring_brief": {
            "path": _project_path(
                brief_plan_path, project_root, "authoring brief"
            ),
            "sha256": _sha256(brief_plan_path),
        },
        "pose_count": TARGET_POSE_COUNT,
        "sequence_order": list(sequence_order),
        "sequences": sequences,
        "approval_state": "pending_visual_parity",
        "review_projection": True,
        "runtime_admitted": False,
    }
    if projection_normalization is not None:
        manifest["projection_normalization"] = projection_normalization
    payload = _json_bytes(manifest)
    _write_bytes_atomic(output_path, payload)
    return {
        "path": _project_path(
            output_path, project_root, "supplemental manifest"
        ),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "character_id": character_id,
        "pose_count": TARGET_POSE_COUNT,
        "sequence_ids": list(sequence_order),
        "review_projection": True,
        "runtime_admitted": False,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("character_id")
    parser.add_argument("brief_plan", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = prepare_manifest(
        character_id=args.character_id,
        brief_plan_path=args.brief_plan,
        authority_path=args.authority,
        output_path=args.output,
        project_root=args.project_root,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
