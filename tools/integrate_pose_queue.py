#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from integrate_pose_candidate import GateFailure, integrate


ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "docs" / "pose-library-expansion" / "registry.json"
SPEC_DIR = ROOT / "docs" / "pose-library-expansion" / "integration-specs"


def queued_candidates(requested: list[str]) -> list[str]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    allowed = {
        item["id"]
        for item in registry["candidates"]
        if item["status"] in {"ANALYZED", "READY", "BLOCKED"}
        and (SPEC_DIR / f"{item['id']}.json").exists()
    }
    if requested:
        missing = [candidate_id for candidate_id in requested if candidate_id not in allowed]
        if missing:
            raise GateFailure(f"candidates are not ready: {', '.join(missing)}")
        return requested
    return [
        item["id"]
        for item in sorted(registry["candidates"], key=lambda entry: int(entry["order"]))
        if item["id"] in allowed
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run serial one-pose integration transactions.")
    parser.add_argument("candidate_ids", nargs="*")
    args = parser.parse_args()
    candidates = queued_candidates(args.candidate_ids)
    results = []
    for index, candidate_id in enumerate(candidates, start=1):
        print(f"[{index}/{len(candidates)}] integrating {candidate_id}", flush=True)
        result = integrate(candidate_id)
        results.append(
            {
                "candidate_id": candidate_id,
                "semantic_id": result["semantic_id"],
                "pose_count": result["pose_count"],
                "library_sha256": result["library_sha256"],
            }
        )
        print(f"[{index}/{len(candidates)}] verified {candidate_id}", flush=True)
    print(json.dumps({"verified": results}, indent=2))


if __name__ == "__main__":
    main()
