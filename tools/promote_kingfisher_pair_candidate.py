#!/usr/bin/env python3
"""Promote one audited Kingfisher pair candidate into its review receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _portable_path(raw_path: object, *, root: Path) -> str:
    if not isinstance(raw_path, (str, os.PathLike)) or not str(raw_path):
        raise ValueError("candidate receipt contains an invalid path")
    path = Path(raw_path).expanduser().resolve()
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def promote_candidate(
    receipt_path: Path,
    audit_path: Path,
    candidate_receipt_path: Path,
    candidate_audit_path: Path,
    history_path: Path,
    *,
    reviewer: str,
    reason: str,
    promoted_at: str | None = None,
    root: Path = ROOT,
) -> dict[str, object]:
    if not reviewer.strip():
        raise ValueError("candidate promotion requires a reviewer")
    if not reason.strip():
        raise ValueError("candidate promotion requires a reason")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_receipt_path.read_text(encoding="utf-8"))
    candidate_audit = json.loads(
        candidate_audit_path.read_text(encoding="utf-8")
    )
    if candidate.get("approval_state") != "candidate_visual_review":
        raise ValueError("candidate must remain in visual review")
    if candidate.get("runtime_admitted") is not False:
        raise ValueError("candidate promotion cannot imply runtime admission")
    if candidate_audit.get("passed") is not True:
        raise ValueError("candidate audit must pass before promotion")
    if candidate.get("resting_sha256") != receipt.get("resting_sha256"):
        raise ValueError("candidate does not use the pair's exact closed frame")
    if candidate.get("speaking_sha256") != candidate_audit.get(
        "speaking_sha256"
    ):
        raise ValueError("candidate receipt and audit hashes do not match")
    speaking_path = Path(str(candidate.get("speaking_path", ""))).resolve()
    if not speaking_path.is_file():
        raise ValueError("candidate speaking frame is missing")
    if _sha256(speaking_path) != candidate.get("speaking_sha256"):
        raise ValueError("candidate speaking frame hash does not match")

    timestamp = promoted_at or datetime.now(timezone.utc).isoformat()
    history = (
        json.loads(history_path.read_text(encoding="utf-8"))
        if history_path.is_file()
        else {
            "schema_version": 1,
            "character_id": "kingfisher",
            "receipt_path": _portable_path(receipt_path, root=root),
            "entries": [],
        }
    )
    entries = history.get("entries")
    if not isinstance(entries, list):
        raise ValueError("receipt history must contain an entries list")
    entries.append(
        {
            "schema_version": 1,
            "superseded_at": timestamp,
            "reviewer": reviewer.strip(),
            "reason": reason.strip(),
            "receipt": receipt,
            "audit": audit,
        }
    )

    promoted = {
        **candidate,
        "resting_path": _portable_path(candidate["resting_path"], root=root),
        "speaking_path": _portable_path(candidate["speaking_path"], root=root),
        "speaking_donor_path": _portable_path(
            candidate["speaking_donor_path"], root=root
        ),
        "pairwise_promotion": {
            "schema_version": 1,
            "promoted_at": timestamp,
            "reviewer": reviewer.strip(),
            "reason": reason.strip(),
            "candidate_receipt_path": _portable_path(
                candidate_receipt_path, root=root
            ),
            "candidate_audit_path": _portable_path(
                candidate_audit_path, root=root
            ),
            "history_path": _portable_path(history_path, root=root),
            "user_approval_implied": False,
            "runtime_admission_implied": False,
        },
    }
    promoted_audit = {
        **candidate_audit,
        "resting_path": promoted["resting_path"],
        "speaking_path": promoted["speaking_path"],
        "pairwise_promotion": promoted["pairwise_promotion"],
    }
    _write_json_atomic(history_path, history)
    _write_json_atomic(receipt_path, promoted)
    _write_json_atomic(audit_path, promoted_audit)
    return {
        "schema_version": 1,
        "receipt_path": _portable_path(receipt_path, root=root),
        "audit_path": _portable_path(audit_path, root=root),
        "speaking_path": promoted["speaking_path"],
        "speaking_sha256": promoted["speaking_sha256"],
        "history_path": _portable_path(history_path, root=root),
        "history_entry_count": len(entries),
        "runtime_admitted": False,
        "user_approval_implied": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--candidate-receipt", type=Path, required=True)
    parser.add_argument("--candidate-audit", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--promoted-at")
    args = parser.parse_args()
    result = promote_candidate(
        args.receipt,
        args.audit,
        args.candidate_receipt,
        args.candidate_audit,
        args.history,
        reviewer=args.reviewer,
        reason=args.reason,
        promoted_at=args.promoted_at,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
