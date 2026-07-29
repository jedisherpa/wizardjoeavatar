#!/usr/bin/env python3
"""Rebuild every plan-bound Kingfisher resting/speaking stage pair."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_kingfisher_stage_pair import audit_pair
from tools.stabilize_kingfisher_stage_pair import (
    stabilize_pair,
    validate_articulation_region,
)


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _alpha_filename(ordinal: int, slug: str) -> str:
    return (
        f"{ordinal:03d}_ACT{ordinal:03d}_"
        f"{slug.replace('-', '_')}_alpha.png"
    )


def rebuild_stage_pairs(
    plan_path: Path,
    alpha_root: Path,
    audit_root: Path,
) -> dict[str, object]:
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    alpha_root = Path(alpha_root)
    audit_root = Path(audit_root)
    rebuilt = []
    for performance_key in plan["performance_keys"]:
        poses = performance_key["poses"]
        if len(poses) != 2:
            raise ValueError("each Kingfisher performance key must contain one pair")
        resting = poses[0]
        speaking = poses[1]
        resting_ordinal = int(resting["ordinal"])
        speaking_ordinal = int(speaking["ordinal"])
        if speaking_ordinal != resting_ordinal + 1:
            raise ValueError("Kingfisher stage pair ordinals must be adjacent")
        region = validate_articulation_region(
            tuple(performance_key["articulation_region"])
        )
        resting_path = alpha_root / _alpha_filename(
            resting_ordinal,
            str(resting["slug"]),
        )
        speaking_path = alpha_root / _alpha_filename(
            speaking_ordinal,
            str(speaking["slug"]),
        )
        candidate_path = speaking_path.with_name(
            speaking_path.name.replace("_alpha.png", "_candidate.png")
        )
        stabilize_pair(
            resting_path,
            candidate_path,
            speaking_path,
            articulation_region=region,
        )
        report = audit_pair(
            resting_path,
            speaking_path,
            articulation_region=region,
        )
        if report["passed"] is not True:
            raise ValueError(
                f"Kingfisher stage pair ACT{resting_ordinal:03d}/"
                f"ACT{speaking_ordinal:03d} failed after rebuild"
            )
        audit_path = audit_root / (
            f"{resting_ordinal:03d}_{speaking_ordinal:03d}_pair.json"
        )
        _write_json_atomic(audit_path, report)
        rebuilt.append(
            {
                "key": performance_key["key"],
                "resting_ordinal": resting_ordinal,
                "speaking_ordinal": speaking_ordinal,
                "articulation_region": list(region),
                "changed_rendered_pixels": report["changed_rendered_pixels"],
                "mouth_mean_abs": report["mouth_mean_abs"],
                "silhouette_iou": report["silhouette_iou"],
                "audit_path": audit_path.as_posix(),
            }
        )
    return {
        "schema_version": 1,
        "character_id": "kingfisher",
        "plan_path": Path(plan_path).as_posix(),
        "pair_count": len(rebuilt),
        "pairs": rebuilt,
        "passed": len(rebuilt) == 22,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild all plan-bound Kingfisher stage speech pairs."
    )
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--alpha-root", type=Path, required=True)
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = rebuild_stage_pairs(
        args.plan,
        args.alpha_root,
        args.audit_root,
    )
    if args.report:
        _write_json_atomic(args.report, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
