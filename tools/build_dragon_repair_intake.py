#!/usr/bin/env python3
"""Build the fail-closed intake for damaged Dragon source replacements."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_MANIFEST = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "dragon"
    / "source"
    / "source-manifest-v001.json"
)
DEFAULT_EVIDENCE_MANIFEST = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "dragon"
    / "source-evidence"
    / "contaminated-robin-archive-011-030"
    / "source-evidence-manifest.json"
)
DEFAULT_ROBIN_SPEECH_MANIFEST = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "robin_speech"
    / "source"
    / "source-manifest-v003.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "dragon"
    / "source-repair"
    / "repair-intake-manifest-v001.json"
)
CANVAS_SIZE = (1920, 1080)
SCHEMA_VERSION = "1.0.0"


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as destination:
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _transparent_rgb_is_zero(image: Image.Image) -> bool:
    red, green, blue, alpha = image.split()
    transparent = alpha.point(lambda value: 255 if value == 0 else 0)
    return all(
        ImageChops.multiply(channel, transparent).getextrema() == (0, 0)
        for channel in (red, green, blue)
    )


def _strict_image_audit(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG":
            raise ValueError(f"{path.name} is not a PNG")
        if image.mode != "RGBA":
            raise ValueError(f"{path.name} is not RGBA")
        if image.size != CANVAS_SIZE:
            raise ValueError(f"{path.name} is not 1920x1080")
        alpha = image.getchannel("A")
        histogram = alpha.histogram()
        if alpha.getextrema() != (0, 255) or sum(histogram[1:255]):
            raise ValueError(f"{path.name} does not have binary alpha")
        if not _transparent_rgb_is_zero(image):
            raise ValueError(f"{path.name} has nonzero RGB under transparent pixels")
        bbox = alpha.getbbox()
        if bbox is None:
            raise ValueError(f"{path.name} contains no visible pixels")
        return {
            "canvas_size": list(image.size),
            "mode": image.mode,
            "alpha_extrema": [0, 255],
            "transparent_rgb_zero": True,
            "visible_bbox": list(bbox),
            "opaque_pixel_count": histogram[255],
        }


def _repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _candidate_frames(
    evidence_manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, tuple[dict[str, Any], Path]]]:
    manifest = _read_json(evidence_manifest_path)
    if manifest.get("observed_identity") != "dragon":
        raise ValueError("replacement evidence must have observed_identity=dragon")
    if manifest.get("runtime_admitted") is not False:
        raise ValueError("replacement evidence must remain runtime_admitted=false")
    if manifest.get("review_projection") is not False:
        raise ValueError("replacement evidence must remain review_projection=false")

    evidence_root = evidence_manifest_path.parent
    frames: dict[str, tuple[dict[str, Any], Path]] = {}
    for record in manifest.get("frames", []):
        path = evidence_root / record["path"]
        if not path.is_file():
            raise ValueError(f"missing evidence payload: {path}")
        if _sha256_path(path) != record["sha256"]:
            raise ValueError(f"evidence checksum mismatch: {path.name}")
        audit = _strict_image_audit(path)
        if audit["opaque_pixel_count"] != record["image_audit"]["opaque_pixel_count"]:
            raise ValueError(f"evidence audit mismatch: {path.name}")
        frames[record["source_declared_filename"]] = (record, path)
    return manifest, frames


def _rejected_pair_records(
    robin_speech_manifest_path: Path,
) -> dict[str, dict[str, Any]]:
    manifest = _read_json(robin_speech_manifest_path)
    rejected: dict[str, dict[str, Any]] = {}
    root = robin_speech_manifest_path.parent
    for record in manifest.get("frames", []):
        path = root / record["path"]
        filename = path.name
        identity_order = record.get("image_audit", {}).get("identity_order")
        if identity_order != ["robin", "speech"]:
            continue
        rejected[filename] = {
            "path": _repo_path(path),
            "sha256": record["sha256"],
            "opaque_pixel_count": record["image_audit"]["opaque_pixel_count"],
            "identity_order": identity_order,
            "rejection_reason": "paired Robin/Speech artwork is not Dragon source art",
        }
    return rejected


def build_dragon_repair_intake(
    *,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
    evidence_manifest_path: Path = DEFAULT_EVIDENCE_MANIFEST,
    robin_speech_manifest_path: Path = DEFAULT_ROBIN_SPEECH_MANIFEST,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    source_manifest = _read_json(source_manifest_path)
    if source_manifest.get("approval_state") != "source_incomplete":
        raise ValueError("Dragon source manifest is not marked source_incomplete")
    if source_manifest.get("runtime_admitted") is not False:
        raise ValueError("Dragon source manifest must remain runtime_admitted=false")

    evidence_manifest, candidates = _candidate_frames(evidence_manifest_path)
    rejected_pairs = _rejected_pair_records(robin_speech_manifest_path)
    blocked = [
        record
        for record in source_manifest.get("assets", [])
        if record.get("status") != "validated_source"
    ]
    if [record["asset_id"] for record in blocked] != source_manifest.get(
        "blocked_asset_ids"
    ):
        raise ValueError("blocked Dragon records do not match blocked_asset_ids")

    assets: list[dict[str, Any]] = []
    candidate_asset_ids: list[str] = []
    missing_asset_ids: list[str] = []
    for source_record in blocked:
        filename = source_record["filename"]
        expected_opaque = source_record["expected_opaque_pixel_count"]
        candidate_entry = candidates.get(filename)
        rejected_entry = rejected_pairs.get(filename)
        record: dict[str, Any] = {
            "asset_id": source_record["asset_id"],
            "canonical_filename": filename,
            "expected_opaque_pixel_count": expected_opaque,
            "damaged_source_sha256": source_record["sha256"],
            "runtime_admitted": False,
            "review_projection": False,
            "replacement_approval": "not_approved",
        }
        if candidate_entry is None:
            record["status"] = "replacement_missing"
            missing_asset_ids.append(source_record["asset_id"])
        else:
            evidence_record, candidate_path = candidate_entry
            audit = _strict_image_audit(candidate_path)
            delta = audit["opaque_pixel_count"] - expected_opaque
            record["status"] = (
                "candidate_matches_approved_metric"
                if delta == 0
                else "candidate_metric_delta_requires_approval"
            )
            record["candidate"] = {
                "path": _repo_path(candidate_path),
                "sha256": evidence_record["sha256"],
                "source_evidence_set_id": evidence_manifest["evidence_set_id"],
                "source_label_status": evidence_manifest["source_label_status"],
                "observed_identity": evidence_manifest["observed_identity"],
                "exact_filename_match": True,
                "image_audit": audit,
                "opaque_pixel_delta": delta,
                "opaque_pixel_delta_ratio": round(delta / expected_opaque, 8),
                "visual_identity_review": "confirmed_dragon_identity",
                "canonical_equivalence_review": "pending",
            }
            candidate_asset_ids.append(source_record["asset_id"])
        if rejected_entry is not None:
            record["rejected_same_name_alternative"] = rejected_entry
        assets.append(record)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "manifest_type": "dragon_source_repair_intake",
        "repair_set_id": "dragon-drg001-source-repair-v001",
        "approval_state": "source_repair_incomplete",
        "source_manifest": {
            "path": _repo_path(source_manifest_path),
            "sha256": _sha256_path(source_manifest_path),
            "asset_set_id": source_manifest["asset_set_id"],
        },
        "evidence_manifest": {
            "path": _repo_path(evidence_manifest_path),
            "sha256": _sha256_path(evidence_manifest_path),
            "evidence_set_id": evidence_manifest["evidence_set_id"],
        },
        "blocked_asset_count": len(blocked),
        "candidate_asset_count": len(candidate_asset_ids),
        "missing_asset_count": len(missing_asset_ids),
        "candidate_asset_ids": candidate_asset_ids,
        "missing_asset_ids": missing_asset_ids,
        "complete_replacement_inventory": not missing_asset_ids,
        "review_projection": False,
        "runtime_admitted": False,
        "admission_rule": (
            "Every blocked asset requires an intact, visually approved replacement; "
            "metric deltas require explicit canonical-equivalence approval."
        ),
        "assets": assets,
    }
    _write_atomic(output_path, _json_bytes(manifest))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the fail-closed Dragon replacement intake manifest."
    )
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument(
        "--evidence-manifest", type=Path, default=DEFAULT_EVIDENCE_MANIFEST
    )
    parser.add_argument(
        "--robin-speech-manifest", type=Path, default=DEFAULT_ROBIN_SPEECH_MANIFEST
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = build_dragon_repair_intake(
        source_manifest_path=args.source_manifest,
        evidence_manifest_path=args.evidence_manifest,
        robin_speech_manifest_path=args.robin_speech_manifest,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "candidate_asset_ids": manifest["candidate_asset_ids"],
                "missing_asset_ids": manifest["missing_asset_ids"],
                "runtime_admitted": manifest["runtime_admitted"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
