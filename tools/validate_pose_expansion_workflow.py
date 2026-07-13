#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROGRAM_DIR = ROOT / "docs" / "pose-library-expansion"
REGISTRY_PATH = PROGRAM_DIR / "registry.json"
TRACKER_PATH = PROGRAM_DIR / "POSE_TRACKER.md"
ITEM_DIR = PROGRAM_DIR / "items"
ARCHIVE_MANIFEST_PATH = ROOT / "evidence" / "pose-library-expansion" / "intake" / "manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def field(text: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}:\s*`([^`]+)`\s*$", text, re.MULTILINE)
    if match is None:
        raise ValueError(f"missing {label} field")
    return match.group(1)


def validate() -> dict[str, object]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    tracker = TRACKER_PATH.read_text(encoding="utf-8")
    allowed = set(registry["allowed_statuses"])
    candidates = registry["candidates"]
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_semantic_ids: set[str] = set()
    integrating: list[str] = []

    for candidate in candidates:
        candidate_id = str(candidate["id"])
        status = str(candidate["status"])
        owner = str(candidate["owner"])
        semantic_id = candidate.get("semantic_id")
        if candidate_id in seen_ids:
            errors.append(f"duplicate candidate id: {candidate_id}")
        seen_ids.add(candidate_id)
        if status not in allowed:
            errors.append(f"{candidate_id}: invalid registry status {status}")
        if status in {"INTEGRATING", "GENERATED", "TESTED"}:
            integrating.append(candidate_id)
        if semantic_id:
            if semantic_id in seen_semantic_ids:
                errors.append(f"duplicate semantic id: {semantic_id}")
            seen_semantic_ids.add(str(semantic_id))

        item_path = ITEM_DIR / f"{candidate_id}.md"
        if not item_path.exists():
            errors.append(f"{candidate_id}: missing item record")
            continue
        item = item_path.read_text(encoding="utf-8")
        try:
            item_status = field(item, "Status")
            item_owner = field(item, "Owner")
            archive_entry = field(item, "Archive entry")
        except ValueError as exc:
            errors.append(f"{candidate_id}: {exc}")
            continue
        if item_status != status:
            errors.append(f"{candidate_id}: registry status {status} != item status {item_status}")
        if item_owner != owner:
            errors.append(f"{candidate_id}: registry owner {owner} != item owner {item_owner}")
        if archive_entry != candidate["archive_entry"]:
            errors.append(f"{candidate_id}: archive entry mismatch")
        if f"| {candidate_id} |" not in tracker:
            errors.append(f"{candidate_id}: missing tracker row")

    lock = registry.get("integration_lock")
    if len(integrating) > 1:
        errors.append(f"multiple candidates integrating: {', '.join(integrating)}")
    expected_lock = integrating[0] if integrating else None
    if lock != expected_lock:
        errors.append(f"integration_lock {lock!r} != active integration candidate {expected_lock!r}")

    archive_manifest = json.loads(ARCHIVE_MANIFEST_PATH.read_text(encoding="utf-8"))
    archive_records = [
        image
        for pack in archive_manifest.get("packs", [])
        for image in pack.get("images", [])
    ]
    archived_ids: set[str] = set()
    for record in archive_records:
        candidate_id = str(record["candidate_id"])
        if candidate_id in archived_ids:
            errors.append(f"duplicate archived candidate id: {candidate_id}")
        archived_ids.add(candidate_id)
        path = ROOT / str(record["repository_path"])
        if not path.is_file():
            errors.append(f"{candidate_id}: archived source is missing: {path}")
            continue
        if sha256(path) != record["sha256"]:
            errors.append(f"{candidate_id}: archived source hash mismatch")
        if record.get("runtime_disposition") != "reference_only":
            errors.append(f"{candidate_id}: archived source must remain reference_only")

    if archived_ids != seen_ids:
        missing = sorted(seen_ids - archived_ids)
        extra = sorted(archived_ids - seen_ids)
        errors.append(f"archive/registry candidate mismatch: missing={missing}, extra={extra}")
    if archive_manifest.get("image_count") != len(archive_records):
        errors.append("archive manifest image_count does not match its records")

    result = {
        "program_id": registry["program_id"],
        "candidate_count": len(candidates),
        "archive_count": len(archive_records),
        "integration_lock": lock,
        "errors": errors,
    }
    if errors:
        raise SystemExit(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
