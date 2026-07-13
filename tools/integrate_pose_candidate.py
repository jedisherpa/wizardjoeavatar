#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROGRAM_DIR = ROOT / "docs" / "pose-library-expansion"
REGISTRY_PATH = PROGRAM_DIR / "registry.json"
TRACKER_PATH = PROGRAM_DIR / "POSE_TRACKER.md"
SPEC_DIR = PROGRAM_DIR / "integration-specs"
ITEM_DIR = PROGRAM_DIR / "items"
MANIFEST_PATH = ROOT / "assets" / "reference" / "motion_sources" / "manifest.json"
ASSET_DIR = MANIFEST_PATH.parent
LIBRARY_PATH = ROOT / "wizard_avatar" / "definitions" / "reference_avatar_pose_cells.json"
EVIDENCE_DIR = ROOT / "evidence" / "pose-library-expansion"


class GateFailure(RuntimeError):
    pass


def stable_json(payload: Any) -> str:
    return json.dumps(payload, indent=2) + "\n"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode:
        raise GateFailure(f"command failed ({completed.returncode}): {' '.join(command)}\n{completed.stdout}")
    return completed.stdout


def load_spec(candidate_id: str) -> dict[str, Any]:
    path = SPEC_DIR / f"{candidate_id}.json"
    if not path.exists():
        raise GateFailure(f"missing integration spec: {path.relative_to(ROOT)}")
    spec = json.loads(path.read_text(encoding="utf-8"))
    required = {"candidate_id", "semantic_id", "source_path", "destination_filename", "manifest"}
    missing = required - set(spec)
    if missing:
        raise GateFailure(f"{candidate_id} spec missing fields: {', '.join(sorted(missing))}")
    if spec["candidate_id"] != candidate_id:
        raise GateFailure(f"spec candidate_id {spec['candidate_id']!r} does not match {candidate_id!r}")
    manifest = spec["manifest"]
    if manifest.get("id") != spec["semantic_id"]:
        raise GateFailure("manifest id does not match semantic_id")
    if manifest.get("source") != spec["destination_filename"]:
        raise GateFailure("manifest source does not match destination_filename")
    if Path(spec["destination_filename"]).name != spec["destination_filename"]:
        raise GateFailure("destination_filename must be a plain filename")
    source = ROOT / spec["source_path"]
    if not source.is_file():
        raise GateFailure(f"source does not exist: {spec['source_path']}")
    return spec


def replace_field(text: str, label: str, value: str) -> str:
    pattern = rf"^{re.escape(label)}:\s*`[^`]+`\s*$"
    updated, count = re.subn(pattern, f"{label}: `{value}`", text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise GateFailure(f"could not update {label} in item record")
    return updated


def update_tracker(registry: dict[str, Any]) -> None:
    text = TRACKER_PATH.read_text(encoding="utf-8")
    candidates = registry["candidates"]
    counts = {
        "Queued": sum(item["status"] == "QUEUED" for item in candidates),
        "Claimed for intake": sum(item["status"] == "CLAIMED" for item in candidates),
        "Analyzed": sum(item["status"] in {"ANALYZED", "READY"} for item in candidates),
        "In integration": sum(item["status"] in {"INTEGRATING", "GENERATED", "TESTED"} for item in candidates),
        "Verified new poses": sum(item["status"] == "VERIFIED" for item in candidates),
        "Duplicate/rejected new poses": sum(item["status"] in {"DUPLICATE", "REJECTED"} for item in candidates),
    }
    for label, count in counts.items():
        text, replaced = re.subn(
            rf"^\| {re.escape(label)} \| \d+ \|$",
            f"| {label} | {count} |",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if replaced != 1:
            raise GateFailure(f"could not update tracker metric {label}")

    lock = registry.get("integration_lock") or "UNCLAIMED"
    text, replaced = re.subn(
        r"^Integration lock: `[^`]+`\.$",
        f"Integration lock: `{lock}`.",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if replaced != 1:
        raise GateFailure("could not update tracker integration lock")

    by_id = {item["id"]: item for item in candidates}
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        columns = [column.strip() for column in line.split("|")[1:-1]]
        if len(columns) != 7 or columns[1] not in by_id:
            continue
        item = by_id[columns[1]]
        columns[3] = str(item["owner"])
        columns[4] = f"`{item['semantic_id']}`" if item.get("semantic_id") else "pending analysis"
        columns[5] = str(item["status"])
        lines[index] = "| " + " | ".join(columns) + " |"
    TRACKER_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_candidate_state(
    registry: dict[str, Any],
    candidate: dict[str, Any],
    item_path: Path,
    status: str,
    owner: str = "coordinator",
) -> None:
    candidate["status"] = status
    candidate["owner"] = owner
    registry["integration_lock"] = candidate["id"] if status in {"INTEGRATING", "GENERATED", "TESTED"} else None
    REGISTRY_PATH.write_text(stable_json(registry), encoding="utf-8")
    item = item_path.read_text(encoding="utf-8")
    item = replace_field(item, "Status", status)
    item = replace_field(item, "Owner", owner)
    item_path.write_text(item, encoding="utf-8")
    update_tracker(registry)


def append_gate_record(item_path: Path, result: dict[str, Any]) -> None:
    item = item_path.read_text(encoding="utf-8").rstrip()
    item += "\n\n## Automated integration gate\n\n"
    item += f"- Completed: `{result['completed_at']}`\n"
    item += f"- Source SHA-256: `{result['source_sha256']}`\n"
    item += f"- Generated library SHA-256: `{result['library_sha256']}`\n"
    item += f"- Pose count after integration: `{result['pose_count']}`\n"
    item += f"- Full Python tests: `{result['tests']}`\n"
    item += f"- Transition matrix: `{result['transition_matrix']}`\n"
    item += f"- Evidence: `{result['evidence_path']}`\n"
    item_path.write_text(item + "\n", encoding="utf-8")


def integrate(candidate_id: str) -> dict[str, Any]:
    spec = load_spec(candidate_id)
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if registry.get("integration_lock") not in {None, candidate_id}:
        raise GateFailure(f"integration lock held by {registry['integration_lock']}")
    candidate = next((item for item in registry["candidates"] if item["id"] == candidate_id), None)
    if candidate is None:
        raise GateFailure(f"candidate not found in registry: {candidate_id}")
    if candidate["status"] not in {"ANALYZED", "READY", "BLOCKED"}:
        raise GateFailure(f"candidate status is not integratable: {candidate['status']}")
    if candidate.get("semantic_id") != spec["semantic_id"]:
        raise GateFailure("registry semantic_id does not match integration spec")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if any(pose["id"] == spec["semantic_id"] for pose in manifest["poses"]):
        raise GateFailure(f"pose already exists in manifest: {spec['semantic_id']}")
    destination = ASSET_DIR / spec["destination_filename"]
    if destination.exists():
        raise GateFailure(f"destination already exists: {destination.relative_to(ROOT)}")

    item_path = ITEM_DIR / f"{candidate_id}.md"
    backups = {
        MANIFEST_PATH: MANIFEST_PATH.read_bytes(),
        LIBRARY_PATH: LIBRARY_PATH.read_bytes(),
    }
    set_candidate_state(registry, candidate, item_path, "INTEGRATING")
    try:
        shutil.copy2(ROOT / spec["source_path"], destination)
        manifest["version"] = int(manifest.get("version", 1)) + 1
        manifest["poses"].append(spec["manifest"])
        MANIFEST_PATH.write_text(stable_json(manifest), encoding="utf-8")

        generator_output = run(
            [sys.executable, "tools/generate_reference_avatar_pose_cells.py", "--check-deterministic"]
        )
        generated = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
        generated_pose = next(
            (pose for pose in generated["poses"] if pose["id"] == spec["semantic_id"]),
            None,
        )
        if generated_pose is None:
            raise GateFailure("generated library does not contain integrated pose")
        if (generated_pose["cols"], generated_pose["rows"]) != (72, 96):
            raise GateFailure("integrated pose is outside canonical 72 x 96 canvas")
        for name, point in generated_pose["anchors"].items():
            if not (0 <= point[0] < 72 and 0 <= point[1] < 96):
                raise GateFailure(f"anchor outside canonical canvas: {name}={point}")

        set_candidate_state(registry, candidate, item_path, "GENERATED")
        tests_output = run([sys.executable, "-m", "unittest", "discover", "tests"])
        set_candidate_state(registry, candidate, item_path, "TESTED")
        matrix_output = run([sys.executable, "tools/verify_animation_quality.py", "--strict"])

        result = {
            "candidate_id": candidate_id,
            "semantic_id": spec["semantic_id"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "source_sha256": sha256(destination),
            "library_sha256": sha256(LIBRARY_PATH),
            "pose_count": len(generated["poses"]),
            "tests": "passed" if "OK" in tests_output else tests_output.strip(),
            "transition_matrix": "passed" if '"issue_count": 0' in matrix_output else matrix_output.strip(),
            "generator_output": generator_output.strip(),
        }
        evidence_path = EVIDENCE_DIR / candidate_id / "integration-result.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        result["evidence_path"] = str(evidence_path.relative_to(ROOT))
        evidence_path.write_text(stable_json(result), encoding="utf-8")
        set_candidate_state(registry, candidate, item_path, "VERIFIED")
        append_gate_record(item_path, result)
        return result
    except Exception as exc:
        for path, content in backups.items():
            path.write_bytes(content)
        destination.unlink(missing_ok=True)
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        candidate = next(item for item in registry["candidates"] if item["id"] == candidate_id)
        set_candidate_state(registry, candidate, item_path, "BLOCKED")
        raise GateFailure(str(exc)) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Integrate and verify exactly one tracked pose candidate.")
    parser.add_argument("candidate_id")
    args = parser.parse_args()
    print(stable_json(integrate(args.candidate_id)), end="")


if __name__ == "__main__":
    main()
