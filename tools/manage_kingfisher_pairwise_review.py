#!/usr/bin/env python3
"""Manage Kingfisher's fail-closed full-size closed/open pair review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

PROTOCOL_ID = "kingfisher-full-size-pairwise-v1"
PAIRWISE_STATES = {
    "pending",
    "pass",
    "needs_rebuild",
    "not_observable",
}
PASSING_STATES = {"pass", "not_observable"}
ROOT = Path(__file__).resolve().parents[1]


def _sha256_path(path: Path) -> str:
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


def _summary(pairs: list[dict[str, object]]) -> dict[str, object]:
    states = [
        str(pair.get("pairwise_full_size_review", {}).get("state", "missing"))
        for pair in pairs
    ]
    return {
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "pair_count": len(pairs),
        "pending_count": states.count("pending"),
        "pass_count": states.count("pass"),
        "needs_rebuild_count": states.count("needs_rebuild"),
        "not_observable_count": states.count("not_observable"),
        "missing_count": states.count("missing"),
        "reviewed_count": sum(state != "pending" for state in states),
        "passing_disposition_count": sum(
            state in PASSING_STATES for state in states
        ),
        "complete": all(state in PASSING_STATES for state in states),
        "user_approval_implied": False,
        "runtime_admission_implied": False,
    }


def _validate_pair_boundary(pair: dict[str, object]) -> None:
    if pair.get("user_approved") is not False:
        raise ValueError("pairwise review cannot modify a user-approved pair")
    if pair.get("runtime_admitted") is not False:
        raise ValueError("pairwise review cannot modify a runtime-admitted pair")


def initialize_pairwise_review(
    ledger_path: Path,
    *,
    queued_at: str,
) -> dict[str, object]:
    """Add the pairwise protocol without erasing the prior batch review."""
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    pairs = list(ledger.get("pairs", []))
    if ledger.get("character_id") != "kingfisher":
        raise ValueError("pair ledger must target Kingfisher")
    if len(pairs) != 66:
        raise ValueError("pair ledger must contain exactly 66 rows")

    for pair in pairs:
        _validate_pair_boundary(pair)
        existing = pair.get("pairwise_full_size_review")
        if isinstance(existing, dict):
            if existing.get("protocol_id") != PROTOCOL_ID:
                raise ValueError("pair uses an incompatible pairwise protocol")
            continue

        prior = pair.get("internal_visual_review", {})
        prior_state = prior.get("state")
        if prior_state == "not_observable":
            state = "not_observable"
        elif prior_state == "needs_rebuild":
            state = "needs_rebuild"
        else:
            state = "pending"
        carried = state != "pending"
        pair["pairwise_full_size_review"] = {
            "schema_version": 1,
            "protocol_id": PROTOCOL_ID,
            "state": state,
            "defect_codes": (
                list(prior.get("defect_codes", []))
                if state == "needs_rebuild"
                else []
            ),
            "note": (
                str(prior.get("note", ""))
                if carried
                else "Awaiting full-size one-pair closed/open review."
            ),
            "evidence_path": (
                str(prior.get("evidence_path", "")) if carried else ""
            ),
            "queued_at": queued_at,
            "reviewed_at": (
                str(prior.get("reviewed_at", "")) if carried else None
            ),
            "reviewer": (
                str(prior.get("reviewer", "")) if carried else None
            ),
            "source_disposition": (
                "carried_forward_full_size_disposition"
                if carried
                else "prior_batch_pass_invalidated"
            ),
            "user_approval_implied": False,
            "runtime_admission_implied": False,
        }

    ledger["pairwise_full_size_review_summary"] = _summary(pairs)
    _write_json_atomic(ledger_path, ledger)
    return ledger["pairwise_full_size_review_summary"]


def record_pairwise_review(
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
    """Record one full-size pair disposition without approving or admitting it."""
    if state not in PAIRWISE_STATES - {"pending"}:
        raise ValueError("recorded state must be pass, needs_rebuild, or not_observable")
    if state == "needs_rebuild" and not defect_codes:
        raise ValueError("needs_rebuild requires at least one defect code")
    if state != "needs_rebuild" and defect_codes:
        raise ValueError(f"{state} cannot retain defect codes")
    if not evidence_path.strip():
        raise ValueError("pairwise review requires full-size evidence")

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    pairs = list(ledger.get("pairs", []))
    matching = [
        pair for pair in pairs if int(pair.get("ordinal", -1)) == ordinal
    ]
    if len(matching) != 1:
        raise ValueError(f"expected exactly one ledger row for pair {ordinal}")
    pair = matching[0]
    _validate_pair_boundary(pair)
    current = pair.get("pairwise_full_size_review")
    if not isinstance(current, dict) or current.get("protocol_id") != PROTOCOL_ID:
        raise ValueError("pairwise protocol must be initialized first")
    timestamp = reviewed_at or datetime.now(timezone.utc).isoformat()
    if current.get("state") in PAIRWISE_STATES - {"pending"}:
        history = pair.setdefault("pairwise_full_size_review_history", [])
        history.append(
            {
                "schema_version": 1,
                "superseded_at": timestamp,
                "reason": (
                    "Superseded by a later full-size pairwise review "
                    "disposition."
                ),
                "reporter": reviewer.strip(),
                "superseded_review": current,
            }
        )
    pair["pairwise_full_size_review"] = {
        **current,
        "state": state,
        "defect_codes": sorted(set(defect_codes)),
        "note": note.strip(),
        "evidence_path": evidence_path.strip(),
        "reviewed_at": timestamp,
        "reviewer": reviewer.strip(),
        "source_disposition": "full_size_pairwise_review",
        "user_approval_implied": False,
        "runtime_admission_implied": False,
    }
    ledger["pairwise_full_size_review_summary"] = _summary(pairs)
    _write_json_atomic(ledger_path, ledger)
    return pair


def invalidate_pairwise_reviews(
    ledger_path: Path,
    *,
    first_ordinal: int,
    last_ordinal: int,
    reason: str,
    reporter: str,
    invalidated_at: str | None = None,
) -> dict[str, object]:
    """Return prior passes to pending while preserving their review evidence."""
    if first_ordinal < 1 or last_ordinal < first_ordinal:
        raise ValueError("invalid ordinal range")
    if not reason.strip():
        raise ValueError("review invalidation requires a reason")
    if not reporter.strip():
        raise ValueError("review invalidation requires a reporter")

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    pairs = list(ledger.get("pairs", []))
    timestamp = invalidated_at or datetime.now(timezone.utc).isoformat()
    invalidated: list[int] = []
    for pair in pairs:
        ordinal = int(pair.get("ordinal", -1))
        if not first_ordinal <= ordinal <= last_ordinal:
            continue
        _validate_pair_boundary(pair)
        review = pair.get("pairwise_full_size_review")
        if (
            not isinstance(review, dict)
            or review.get("protocol_id") != PROTOCOL_ID
        ):
            raise ValueError("pairwise protocol must be initialized first")
        if review.get("state") != "pass":
            continue
        history = list(pair.get("pairwise_full_size_review_history", []))
        history.append(
            {
                "schema_version": 1,
                "invalidated_at": timestamp,
                "reason": reason.strip(),
                "reporter": reporter.strip(),
                "superseded_review": review,
            }
        )
        pair["pairwise_full_size_review_history"] = history
        pair["pairwise_full_size_review"] = {
            **review,
            "state": "pending",
            "defect_codes": [],
            "note": reason.strip(),
            "evidence_path": "",
            "reviewed_at": None,
            "reviewer": None,
            "source_disposition": "user_reported_visual_recheck",
            "user_approval_implied": False,
            "runtime_admission_implied": False,
        }
        invalidated.append(ordinal)

    ledger["pairwise_full_size_review_summary"] = _summary(pairs)
    _write_json_atomic(ledger_path, ledger)
    return {
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "invalidated_ordinals": invalidated,
        "invalidated_count": len(invalidated),
        "reason": reason.strip(),
        "reporter": reporter.strip(),
        "invalidated_at": timestamp,
        "summary": ledger["pairwise_full_size_review_summary"],
    }


def _resolve_source_path(root: Path, raw_path: object) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("pair receipt is missing a source image path")
    path = Path(raw_path)
    return path if path.is_absolute() else root / path


def _render_evidence_frame(
    source_path: Path,
    output_path: Path,
    *,
    label: str,
) -> None:
    with Image.open(source_path) as source:
        rgba = source.convert("RGBA")
    frame = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    frame.alpha_composite(rgba)
    header_height = 42
    evidence = Image.new(
        "RGBA",
        (frame.width, frame.height + header_height),
        (255, 255, 255, 255),
    )
    evidence.alpha_composite(frame, (0, header_height))
    draw = ImageDraw.Draw(evidence)
    draw.rectangle(
        (0, 0, evidence.width - 1, header_height - 1),
        fill=(250, 250, 250, 255),
        outline=(210, 210, 210, 255),
    )
    draw.text((14, 14), label, fill=(35, 35, 35, 255))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.{os.getpid()}.tmp")
    try:
        evidence.convert("RGB").save(temporary, format="PNG")
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_flip_review(
    closed_path: Path,
    open_path: Path,
    output_path: Path,
) -> None:
    with Image.open(closed_path) as closed_source:
        closed = closed_source.convert("RGB")
    with Image.open(open_path) as open_source:
        opened = open_source.convert("RGB")
    if closed.size != opened.size:
        raise ValueError("closed/open evidence frames must share one canvas")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.{os.getpid()}.tmp")
    try:
        closed.save(
            temporary,
            format="GIF",
            save_all=True,
            append_images=[opened],
            duration=[650, 650],
            loop=0,
            disposal=2,
        )
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)


def capture_pairwise_evidence(
    ledger_path: Path,
    *,
    ordinal: int,
    output_dir: Path,
    root: Path = ROOT,
) -> dict[str, object]:
    """Render one pair's exact source pixels into full-size review evidence."""
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    matching = [
        pair
        for pair in ledger.get("pairs", [])
        if int(pair.get("ordinal", -1)) == ordinal
    ]
    if len(matching) != 1:
        raise ValueError(f"expected exactly one ledger row for pair {ordinal}")
    pair = matching[0]
    review = pair.get("pairwise_full_size_review")
    if not isinstance(review, dict) or review.get("protocol_id") != PROTOCOL_ID:
        raise ValueError("pairwise protocol must be initialized first")
    receipt_path = ledger_path.parent / str(pair.get("receipt_path", ""))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    resting_path = _resolve_source_path(root, receipt.get("resting_path"))
    speaking_path = _resolve_source_path(root, receipt.get("speaking_path"))
    if not resting_path.is_file() or not speaking_path.is_file():
        raise ValueError("pair receipt references a missing source image")

    slug = str(pair.get("slug", "unknown"))
    state = str(review.get("state", "pending"))
    closed_output = output_dir / "closed-projector.png"
    open_output = output_dir / "open-projector.png"
    flip_output = output_dir / "closed-open-flip.gif"
    receipt_output = output_dir / "pair-evidence-receipt.json"
    prefix = f"{ordinal:02d} / 66 - {slug}"
    _render_evidence_frame(
        resting_path,
        closed_output,
        label=f"{prefix} - closed - {state}",
    )
    _render_evidence_frame(
        speaking_path,
        open_output,
        label=f"{prefix} - open - {state}",
    )
    _write_flip_review(closed_output, open_output, flip_output)
    receipt = {
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "visual_unit": "one_locked_closed_open_pair",
        "ordinal": ordinal,
        "slug": slug,
        "state": state,
        "closed_source": str(resting_path),
        "closed_source_sha256": _sha256_path(resting_path),
        "open_source": str(speaking_path),
        "open_source_sha256": _sha256_path(speaking_path),
        "closed_evidence": str(closed_output),
        "closed_evidence_sha256": _sha256_path(closed_output),
        "open_evidence": str(open_output),
        "open_evidence_sha256": _sha256_path(open_output),
        "flip_evidence": str(flip_output),
        "flip_evidence_sha256": _sha256_path(flip_output),
        "user_approval_implied": False,
        "runtime_admission_implied": False,
    }
    _write_json_atomic(receipt_output, receipt)
    return {
        **receipt,
        "evidence_receipt": str(receipt_output),
        "evidence_receipt_sha256": _sha256_path(receipt_output),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    initialize = subparsers.add_parser("initialize")
    initialize.add_argument("--ledger", type=Path, required=True)
    initialize.add_argument("--queued-at", required=True)

    record = subparsers.add_parser("record")
    record.add_argument("--ledger", type=Path, required=True)
    record.add_argument("--ordinal", type=int, required=True)
    record.add_argument(
        "--state",
        choices=sorted(PAIRWISE_STATES - {"pending"}),
        required=True,
    )
    record.add_argument("--defect-code", action="append", default=[])
    record.add_argument("--note", default="")
    record.add_argument("--evidence-path", required=True)
    record.add_argument("--reviewer", default="codex-full-size-pairwise-review")
    record.add_argument("--reviewed-at")

    capture = subparsers.add_parser("capture")
    capture.add_argument("--ledger", type=Path, required=True)
    capture.add_argument("--ordinal", type=int, required=True)
    capture.add_argument("--output-dir", type=Path, required=True)
    capture.add_argument("--root", type=Path, default=ROOT)
    invalidate = subparsers.add_parser("invalidate")
    invalidate.add_argument("--ledger", type=Path, required=True)
    invalidate.add_argument("--first-ordinal", type=int, required=True)
    invalidate.add_argument("--last-ordinal", type=int, required=True)
    invalidate.add_argument("--reason", required=True)
    invalidate.add_argument("--reporter", default="user-visual-review")
    invalidate.add_argument("--invalidated-at")
    args = parser.parse_args()

    if args.command == "initialize":
        result = initialize_pairwise_review(
            args.ledger,
            queued_at=args.queued_at,
        )
    elif args.command == "record":
        result = record_pairwise_review(
            args.ledger,
            ordinal=args.ordinal,
            state=args.state,
            defect_codes=args.defect_code,
            note=args.note,
            evidence_path=args.evidence_path,
            reviewer=args.reviewer,
            reviewed_at=args.reviewed_at,
        )
    elif args.command == "capture":
        result = capture_pairwise_evidence(
            args.ledger,
            ordinal=args.ordinal,
            output_dir=args.output_dir,
            root=args.root,
        )
    else:
        result = invalidate_pairwise_reviews(
            args.ledger,
            first_ordinal=args.first_ordinal,
            last_ordinal=args.last_ordinal,
            reason=args.reason,
            reporter=args.reporter,
            invalidated_at=args.invalidated_at,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
