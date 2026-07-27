#!/usr/bin/env python3
"""Ingest the approved Dragon alpha inventory without admitting damaged frames."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageFile

ROOT = Path(__file__).resolve().parent.parent
MAIN_ARCHIVE_SHA256 = (
    "35277f5dc01505343921bfcb6ac22b5c733e2e871ee4c3103fea3178eb941689"
)
SUPPLEMENT_ARCHIVE_SHA256 = (
    "1b0d5f59cea9940b30ca6aa4fb3f4f20b43d7870bab02ef2c08aab3121a86a3c"
)
DEFAULT_SOURCE_ROOT = (
    ROOT / "assets" / "reference" / "characters" / "dragon" / "source"
)
CANVAS_SIZE = (1920, 1080)
MAIN_MANIFEST_NAME = "alpha_manifest.csv"
SUPPLEMENT_MANIFEST_NAME = "DRG001_ACT066-ACT080_alpha_manifest.csv"
SOURCE_MANIFEST_NAME = "source-manifest-v001.json"
CANONICAL_PATTERN = re.compile(r"^CAN(?P<ordinal>\d{3})_DRG001_.+_alpha\.png$")
ACTION_PATTERN = re.compile(r"^(?P<ordinal>\d{3})_ACT(?P=ordinal)_.+_alpha\.png$")


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


def _csv_rows(payload: bytes) -> list[dict[str, str]]:
    text = payload.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _archive_entries(archive: zipfile.ZipFile) -> dict[str, tuple[str, bytes]]:
    entries: dict[str, tuple[str, bytes]] = {}
    for info in archive.infolist():
        if info.is_dir():
            continue
        name = Path(info.filename).name
        if name in entries:
            raise ValueError(f"duplicate archive basename: {name}")
        entries[name] = (info.filename, archive.read(info))
    return entries


def _transparent_rgb_is_zero(image: Image.Image) -> bool:
    red, green, blue, alpha = image.split()
    transparent = alpha.point(lambda value: 255 if value == 0 else 0)
    return all(
        ImageChops.multiply(channel, transparent).getextrema() == (0, 0)
        for channel in (red, green, blue)
    )


def _strict_image_audit(payload: bytes, *, filename: str) -> dict[str, Any]:
    with Image.open(io.BytesIO(payload)) as image:
        image.load()
        if image.format != "PNG":
            raise ValueError(f"{filename} is not a PNG")
        if image.mode != "RGBA":
            raise ValueError(f"{filename} is not RGBA")
        if image.size != CANVAS_SIZE:
            raise ValueError(f"{filename} is not 1920x1080")
        alpha = image.getchannel("A")
        histogram = alpha.histogram()
        if alpha.getextrema() != (0, 255) or sum(histogram[1:255]):
            raise ValueError(f"{filename} does not have binary alpha")
        if not _transparent_rgb_is_zero(image):
            raise ValueError(f"{filename} has nonzero RGB under transparent pixels")
        bbox = alpha.getbbox()
        if bbox is None:
            raise ValueError(f"{filename} contains no visible pixels")
        return {
            "canvas_size": list(image.size),
            "mode": image.mode,
            "alpha_extrema": [0, 255],
            "transparent_rgb_zero": True,
            "visible_bbox": list(bbox),
            "opaque_pixel_count": histogram[255],
        }


def _truncated_diagnostic(payload: bytes) -> dict[str, Any] | None:
    previous = ImageFile.LOAD_TRUNCATED_IMAGES
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.load()
            if image.mode != "RGBA" or image.size != CANVAS_SIZE:
                return None
            alpha = image.getchannel("A")
            return {
                "diagnostic_only": True,
                "opaque_pixel_count": alpha.histogram()[255],
                "visible_bbox": list(alpha.getbbox() or ()),
            }
    except Exception:
        return None
    finally:
        ImageFile.LOAD_TRUNCATED_IMAGES = previous


def _validate_archive(path: Path, expected_sha256: str) -> None:
    actual = _sha256_path(path)
    if actual != expected_sha256:
        raise ValueError(
            f"archive checksum mismatch for {path.name}: {actual} != {expected_sha256}"
        )


def _asset_sort_key(row: dict[str, str]) -> tuple[int, int]:
    asset_id = row["asset_id"]
    return (0 if asset_id.startswith("CAN") else 1, int(asset_id[-3:]))


def _expected_opaque_count(row: dict[str, str]) -> int:
    value = row.get("occupied_pixels") or row.get("opaque_pixels")
    if not value:
        raise ValueError(f"{row['asset_id']} has no approved opaque-pixel count")
    return int(value)


def _validate_inventory(rows: list[dict[str, str]]) -> None:
    ids = {row["asset_id"] for row in rows}
    expected = {
        *(f"CAN{ordinal:03d}" for ordinal in range(1, 12)),
        *(f"ACT{ordinal:03d}" for ordinal in range(1, 81)),
    }
    if ids != expected or len(rows) != len(expected):
        missing = sorted(expected - ids)
        extra = sorted(ids - expected)
        raise ValueError(f"Dragon inventory mismatch: missing={missing}, extra={extra}")


def _record_for_asset(
    *,
    row: dict[str, str],
    payload: bytes,
    archive_role: str,
) -> tuple[dict[str, Any], bool]:
    filename = row["filename"]
    asset_id = row["asset_id"]
    expected_opaque = _expected_opaque_count(row)
    strict_error: str | None = None
    audit: dict[str, Any] | None = None
    try:
        audit = _strict_image_audit(payload, filename=filename)
        if audit["opaque_pixel_count"] != expected_opaque:
            strict_error = (
                "opaque pixel count mismatch: "
                f"{audit['opaque_pixel_count']} != {expected_opaque}"
            )
    except Exception as exc:
        strict_error = f"{type(exc).__name__}: {exc}"

    valid = strict_error is None
    record: dict[str, Any] = {
        "asset_id": asset_id,
        "filename": filename,
        "archive_role": archive_role,
        "sha256": _sha256_bytes(payload),
        "bytes": len(payload),
        "expected_opaque_pixel_count": expected_opaque,
        "status": "validated_source" if valid else "blocked_damaged_source",
        "runtime_admitted": False,
    }
    declared_sha = row.get("sha256")
    if declared_sha:
        record["declared_sha256"] = declared_sha
        if declared_sha != record["sha256"]:
            record["status"] = "blocked_manifest_hash_mismatch"
            strict_error = (
                f"manifest SHA-256 mismatch: {record['sha256']} != {declared_sha}"
            )
            valid = False
    if valid and audit is not None:
        record["path"] = f"alphas/{filename}"
        record["image_audit"] = audit
    else:
        record["validation_error"] = strict_error
        diagnostic = _truncated_diagnostic(payload)
        if diagnostic is not None:
            record["truncated_decode_diagnostic"] = diagnostic
    return record, valid


def _standalone_confirmations(
    canonical_root: Path | None,
    archive_payloads: dict[str, bytes],
) -> list[dict[str, Any]]:
    if canonical_root is None:
        return []
    confirmations = []
    for ordinal in range(1, 12):
        candidates = sorted(canonical_root.glob(f"CAN{ordinal:03d}_DRG001_*_alpha.png"))
        if len(candidates) != 1:
            raise ValueError(
                f"expected one standalone CAN{ordinal:03d} in {canonical_root}, "
                f"found {len(candidates)}"
            )
        path = candidates[0]
        payload = path.read_bytes()
        archive_payload = archive_payloads.get(path.name)
        if archive_payload is None:
            raise ValueError(f"standalone canonical is absent from archive: {path.name}")
        confirmations.append(
            {
                "asset_id": f"CAN{ordinal:03d}",
                "filename": path.name,
                "sha256": _sha256_bytes(payload),
                "matches_main_archive_payload": payload == archive_payload,
            }
        )
    return confirmations


def ingest_dragon_source(
    *,
    main_archive_path: Path,
    supplement_archive_path: Path,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    standalone_canonical_root: Path | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    main_archive_path = main_archive_path.resolve()
    supplement_archive_path = supplement_archive_path.resolve()
    source_root = source_root.resolve()
    try:
        source_root.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Dragon source root must stay inside the project") from exc
    _validate_archive(main_archive_path, MAIN_ARCHIVE_SHA256)
    _validate_archive(supplement_archive_path, SUPPLEMENT_ARCHIVE_SHA256)

    with zipfile.ZipFile(main_archive_path) as archive:
        main_entries = _archive_entries(archive)
        main_manifest_entry = main_entries.get(MAIN_MANIFEST_NAME)
        if main_manifest_entry is None:
            raise ValueError("main archive has no alpha_manifest.csv")
        main_rows = _csv_rows(main_manifest_entry[1])
    with zipfile.ZipFile(supplement_archive_path) as archive:
        supplement_entries = _archive_entries(archive)
        supplement_manifest_entry = supplement_entries.get(SUPPLEMENT_MANIFEST_NAME)
        if supplement_manifest_entry is None:
            raise ValueError("supplement archive has no alpha manifest")
        supplement_rows = _csv_rows(supplement_manifest_entry[1])

    rows = main_rows + supplement_rows
    _validate_inventory(rows)
    payloads: dict[str, tuple[bytes, str]] = {}
    for row in main_rows:
        entry = main_entries.get(row["filename"])
        if entry is None:
            raise ValueError(f"main archive is missing {row['filename']}")
        payloads[row["filename"]] = (entry[1], "main_through_act065")
    for row in supplement_rows:
        entry = supplement_entries.get(row["filename"])
        if entry is None:
            raise ValueError(f"supplement archive is missing {row['filename']}")
        if row["filename"] in payloads:
            raise ValueError(f"duplicate Dragon asset filename: {row['filename']}")
        payloads[row["filename"]] = (entry[1], "supplement_act066_act080")

    source_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{source_root.name}-", dir=source_root.parent)
    )
    try:
        alpha_root = staging / "alphas"
        alpha_root.mkdir()
        records = []
        for row in sorted(rows, key=_asset_sort_key):
            payload, archive_role = payloads[row["filename"]]
            record, valid = _record_for_asset(
                row=row,
                payload=payload,
                archive_role=archive_role,
            )
            records.append(record)
            if valid:
                (alpha_root / row["filename"]).write_bytes(payload)

        confirmations = _standalone_confirmations(
            standalone_canonical_root.resolve()
            if standalone_canonical_root is not None
            else None,
            {
                row["filename"]: payloads[row["filename"]][0]
                for row in main_rows
                if row["asset_id"].startswith("CAN")
            },
        )
        valid_records = [record for record in records if record["status"] == "validated_source"]
        blocked_records = [
            record for record in records if record["status"] != "validated_source"
        ]
        manifest = {
            "schema_version": 1,
            "manifest_type": "dragon_approved_alpha_source",
            "asset_set_id": "dragon-drg001-approved-alpha-001-080-v001",
            "character_id": "dragon",
            "archives": {
                "main_through_act065": {
                    "filename": main_archive_path.name,
                    "sha256": MAIN_ARCHIVE_SHA256,
                    "declared_asset_count": len(main_rows),
                },
                "supplement_act066_act080": {
                    "filename": supplement_archive_path.name,
                    "sha256": SUPPLEMENT_ARCHIVE_SHA256,
                    "declared_asset_count": len(supplement_rows),
                },
            },
            "standalone_canonical_confirmations": confirmations,
            "expected_asset_count": len(records),
            "validated_asset_count": len(valid_records),
            "blocked_asset_count": len(blocked_records),
            "blocked_asset_ids": [record["asset_id"] for record in blocked_records],
            "assets": records,
            "approval_state": "source_incomplete",
            "review_projection": False,
            "runtime_admitted": False,
            "notes": [
                "Validated PNGs are preserved byte-for-byte.",
                "Damaged or manifest-mismatched payloads are recorded but not copied.",
                "No Dragon review library or runtime package may be built from this incomplete set.",
            ],
        }
        _write_atomic(staging / SOURCE_MANIFEST_NAME, _json_bytes(manifest))
        if source_root.exists():
            if not replace:
                raise ValueError(f"Dragon source root already exists: {source_root}")
            shutil.rmtree(source_root)
        staging.replace(source_root)
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest and fail-closed audit the DRG001 approved alpha inventory."
    )
    parser.add_argument("main_archive", type=Path)
    parser.add_argument("supplement_archive", type=Path)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--standalone-canonical-root", type=Path)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    manifest = ingest_dragon_source(
        main_archive_path=args.main_archive,
        supplement_archive_path=args.supplement_archive,
        source_root=args.source_root,
        standalone_canonical_root=args.standalone_canonical_root,
        replace=args.replace,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
