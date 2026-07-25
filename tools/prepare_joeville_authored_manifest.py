#!/usr/bin/env python3
"""Freeze authored JoeVille alpha sources into a hash-bound manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AUTHORITY = (
    ROOT / "assets" / "reference" / "hd_canonical" / "manifest.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_manifest(
    *,
    character_id: str,
    brief_plan_path: Path,
    existing_manifest_path: Path,
    authority_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    plan = _read_json(brief_plan_path)
    existing = _read_json(existing_manifest_path)
    authority = _read_json(authority_path)
    if plan.get("character_id") != character_id:
        raise ValueError("authoring brief character_id mismatch")
    if existing.get("character_id") != character_id:
        raise ValueError("existing reconstruction character_id mismatch")
    if list(plan.get("sequences", {})) != existing["missing_sequences"]:
        raise ValueError("authoring briefs do not match source sequence gaps")
    profile = authority["master_profile"]
    expected_size = (
        int(profile["canvas_width"]),
        int(profile["canvas_height"]),
    )
    output_root = output_path.parent.resolve()
    sequences: dict[str, Any] = {}
    seen_hashes: set[str] = set()
    for sequence_id, sequence in plan["sequences"].items():
        frames = []
        for brief in sequence["frames"]:
            pose_id = brief["pose_id"]
            filename = f"{pose_id}.png"
            frame_path = output_root / "frames" / filename
            alpha_path = output_root / "alpha-extracted" / filename
            chroma_path = output_root / "chroma-source" / filename
            for path in (frame_path, alpha_path, chroma_path):
                if not path.is_file():
                    raise ValueError(f"missing authored source: {path}")
            with Image.open(frame_path) as source:
                source.load()
                if source.format != "PNG" or source.mode != "RGBA":
                    raise ValueError(f"{filename} must be an RGBA PNG")
                if source.size != expected_size:
                    raise ValueError(f"{filename} profile dimensions mismatch")
                rgba = source.tobytes()
                bbox = source.getchannel("A").getbbox()
            if bbox is None or bbox[3] != int(profile["baseline_y"]):
                raise ValueError(f"{filename} canonical baseline mismatch")
            source_hash = _sha256(frame_path)
            rgba_hash = hashlib.sha256(rgba).hexdigest()
            if source_hash in seen_hashes or rgba_hash in seen_hashes:
                raise ValueError("authored frames must not duplicate artwork")
            seen_hashes.update((source_hash, rgba_hash))
            frames.append(
                {
                    **brief,
                    "source_path": str(frame_path.relative_to(output_root)),
                    "source_sha256": source_hash,
                    "rgba_sha256": rgba_hash,
                    "alpha_extracted_path": str(
                        alpha_path.relative_to(output_root)
                    ),
                    "alpha_extracted_sha256": _sha256(alpha_path),
                    "chroma_source_path": str(
                        chroma_path.relative_to(output_root)
                    ),
                    "chroma_source_sha256": _sha256(chroma_path),
                    "canonical_bbox": list(bbox),
                    "authorship": "authored_full_size_imagegen_v1",
                }
            )
        sequences[sequence_id] = {
            "intent": sequence["intent"],
            "fps": int(sequence.get("fps", 8)),
            "loop": bool(sequence.get("loop", False)),
            "motion_contract": dict(sequence["motion_contract"]),
            "frames": frames,
        }
    manifest = {
        "schema_version": 1,
        "character_id": character_id,
        "profile_id": profile["profile_id"],
        "authority_manifest_sha256": _sha256(authority_path),
        "existing_reconstruction_sha256": _sha256(existing_manifest_path),
        "existing_artifact_sha256": existing["artifact"]["sha256"],
        "authoring_brief_sha256": _sha256(brief_plan_path),
        "generation_method": (
            "built_in_imagegen_flat_chroma_then_local_alpha_extraction"
        ),
        "canonicalization": "integer_translation_only_no_resampling",
        "runtime_admitted": False,
        "approval_state": "pending_visual_parity",
        "sequences": sequences,
    }
    payload = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(
        f".{output_path.name}.{os.getpid()}.tmp"
    )
    with temporary.open("wb") as destination:
        destination.write(payload)
        destination.flush()
        os.fsync(destination.fileno())
    temporary.replace(output_path)
    return {
        "path": str(output_path),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "pose_count": sum(
            len(sequence["frames"]) for sequence in sequences.values()
        ),
        "sequence_ids": list(sequences),
        "runtime_admitted": False,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("character_id")
    parser.add_argument("brief_plan", type=Path)
    parser.add_argument("existing_manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = prepare_manifest(
        character_id=args.character_id,
        brief_plan_path=args.brief_plan.resolve(),
        existing_manifest_path=args.existing_manifest.resolve(),
        authority_path=args.authority.resolve(),
        output_path=args.output.resolve(),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
