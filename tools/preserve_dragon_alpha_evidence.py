#!/usr/bin/env python3
"""Preserve the Dragon alphas mislabeled in an older Robin/Speech archive."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CONTAMINATED_ARCHIVE_SHA256 = (
    "c7378b144453a9af98518f72025ac5237f17d44906d33c5a5683f1d45a1e1805"
)
DEFAULT_EVIDENCE_ROOT = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "dragon"
    / "source-evidence"
    / "contaminated-robin-archive-011-030"
)
CANVAS_SIZE = (1920, 1080)
EXPECTED_ORDINALS = set(range(11, 31))


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
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as destination:
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _validate_alpha(payload: bytes, *, name: str) -> dict[str, Any]:
    with Image.open(io.BytesIO(payload)) as image:
        image.load()
        if image.format != "PNG" or image.mode != "RGBA":
            raise ValueError(f"{name} must be an RGBA PNG")
        if image.size != CANVAS_SIZE:
            raise ValueError(f"{name} must be exactly 1920x1080")
        alpha = image.getchannel("A")
        histogram = alpha.histogram()
        if alpha.getextrema() != (0, 255) or sum(histogram[1:255]):
            raise ValueError(f"{name} must have binary transparency")
        bbox = alpha.getbbox()
        if bbox is None:
            raise ValueError(f"{name} has no visible pixels")
        return {
            "canvas_size": list(image.size),
            "mode": image.mode,
            "alpha_extrema": [0, 255],
            "visible_bbox": list(bbox),
            "opaque_pixel_count": histogram[255],
        }


def preserve_evidence(
    *,
    archive_path: Path,
    evidence_root: Path = DEFAULT_EVIDENCE_ROOT,
    replace: bool = False,
) -> dict[str, Any]:
    archive_path = archive_path.resolve()
    evidence_root = evidence_root.resolve()
    try:
        evidence_root.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("evidence root must stay inside the project") from exc
    if _sha256_path(archive_path) != CONTAMINATED_ARCHIVE_SHA256:
        raise ValueError("contaminated archive checksum mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        selected: dict[int, tuple[str, bytes]] = {}
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename).name
            if len(name) < 4 or not name[:3].isdigit() or name[3] != "_":
                continue
            ordinal = int(name[:3])
            if ordinal in EXPECTED_ORDINALS:
                if ordinal in selected:
                    raise ValueError(f"duplicate Dragon evidence ordinal: {ordinal}")
                selected[ordinal] = (name, archive.read(info))
    if set(selected) != EXPECTED_ORDINALS:
        raise ValueError("Dragon evidence inventory must contain ordinals 011-030")

    evidence_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{evidence_root.name}-",
            dir=evidence_root.parent,
        )
    )
    try:
        alpha_root = staging / "alphas"
        alpha_root.mkdir()
        records = []
        for ordinal in sorted(selected):
            name, payload = selected[ordinal]
            audit = _validate_alpha(payload, name=name)
            (alpha_root / name).write_bytes(payload)
            records.append(
                {
                    "ordinal": ordinal,
                    "path": f"alphas/{name}",
                    "source_declared_filename": name,
                    "sha256": _sha256_bytes(payload),
                    "bytes": len(payload),
                    "image_audit": audit,
                }
            )
        manifest = {
            "schema_version": 1,
            "manifest_type": "dragon_alpha_source_evidence",
            "evidence_set_id": "dragon-mislabeled-robin-archive-011-030-v001",
            "observed_identity": "dragon",
            "source_label_status": "mislabeled_as_robin",
            "source_archive": {
                "filename": archive_path.name,
                "sha256": CONTAMINATED_ARCHIVE_SHA256,
            },
            "frame_count": len(records),
            "frames": records,
            "approval_state": "quarantined_source_evidence",
            "review_projection": False,
            "runtime_admitted": False,
            "notes": [
                "Preserved byte-for-byte from the user-provided archive.",
                "Not compiled, registered, approved, or exposed by the runtime.",
                "Requires a separate Dragon identity audit before use.",
            ],
        }
        _write_atomic(staging / "source-evidence-manifest.json", _json_bytes(manifest))
        if evidence_root.exists():
            if not replace:
                raise ValueError(f"evidence root already exists: {evidence_root}")
            shutil.rmtree(evidence_root)
        staging.replace(evidence_root)
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preserve mislabeled Dragon frames as quarantined source evidence."
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    manifest = preserve_evidence(
        archive_path=args.archive,
        evidence_root=args.evidence_root,
        replace=args.replace,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
