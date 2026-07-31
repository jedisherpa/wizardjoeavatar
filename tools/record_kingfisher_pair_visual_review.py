#!/usr/bin/env python3
"""Record one Kingfisher pair's internal anatomical review without approving it."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

REVIEW_STATES = {
    "pass",
    "needs_rebuild",
    "not_observable",
}


def _write_json_atomic(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def record_visual_review(
    ledger_path: Path,
    *,
    ordinal: int,
    state: str,
    defect_codes: list[str],
    note: str,
    evidence_path: str,
    reviewer: str,
    reviewed_at: str | None = None,
) -> dict[str, object]:
    if state not in REVIEW_STATES:
        raise ValueError(
            f"state must be one of: {', '.join(sorted(REVIEW_STATES))}"
        )
    if state == "needs_rebuild" and not defect_codes:
        raise ValueError("needs_rebuild requires at least one defect code")
    if state == "pass" and defect_codes:
        raise ValueError("pass cannot retain defect codes")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    matching = [
        pair for pair in ledger["pairs"]
        if int(pair["ordinal"]) == ordinal
    ]
    if len(matching) != 1:
        raise ValueError(f"expected exactly one ledger row for pair {ordinal}")
    pair = matching[0]
    if bool(pair.get("user_approved")):
        raise ValueError("internal review cannot modify a user-approved pair")
    if bool(pair.get("runtime_admitted")):
        raise ValueError("internal review cannot modify a runtime-admitted pair")
    pair["internal_visual_review"] = {
        "schema_version": 1,
        "state": state,
        "defect_codes": sorted(set(defect_codes)),
        "note": note.strip(),
        "evidence_path": evidence_path,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at or datetime.now(timezone.utc).isoformat(),
        "user_approval_implied": False,
        "runtime_admission_implied": False,
    }
    states = [
        candidate.get("internal_visual_review", {}).get("state")
        for candidate in ledger["pairs"]
    ]
    ledger["internal_visual_review_summary"] = {
        "schema_version": 1,
        "reviewed_count": sum(state in REVIEW_STATES for state in states),
        "pass_count": states.count("pass"),
        "needs_rebuild_count": states.count("needs_rebuild"),
        "not_observable_count": states.count("not_observable"),
        "unreviewed_count": sum(state not in REVIEW_STATES for state in states),
        "user_approval_implied": False,
        "runtime_admission_implied": False,
    }
    _write_json_atomic(ledger_path, ledger)
    return pair


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--ordinal", type=int, required=True)
    parser.add_argument("--state", choices=sorted(REVIEW_STATES), required=True)
    parser.add_argument("--defect-code", action="append", default=[])
    parser.add_argument("--note", default="")
    parser.add_argument("--evidence-path", required=True)
    parser.add_argument("--reviewer", default="codex-pair-closeup-review")
    parser.add_argument("--reviewed-at")
    args = parser.parse_args()
    pair = record_visual_review(
        args.ledger,
        ordinal=args.ordinal,
        state=args.state,
        defect_codes=args.defect_code,
        note=args.note,
        evidence_path=args.evidence_path,
        reviewer=args.reviewer,
        reviewed_at=args.reviewed_at,
    )
    print(json.dumps(pair, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
