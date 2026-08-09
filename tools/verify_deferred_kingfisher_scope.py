#!/usr/bin/env python3
"""Verify that deferred Kingfisher speech-pair work cannot enter shipping scope."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def verify_deferred_scope(
    shipping_index: Mapping[str, Any],
    review_index: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if shipping_index.get("character_id") != "kingfisher":
        errors.append("shipping index is not the Kingfisher library")
    if review_index.get("character_id") != "kingfisher":
        errors.append("review index is not the Kingfisher library")
    if shipping_index.get("asset_set_id") == review_index.get("asset_set_id"):
        errors.append("shipping and deferred review indexes identify the same asset set")
    if "kingfisher-paired-beaks-review" in shipping_index.get("sequences", {}):
        errors.append("shipping index exposes the deferred paired-beak sequence")

    review = review_index.get("legacy_pair_review")
    if not isinstance(review, dict):
        errors.append("review index has no legacy_pair_review contract")
        return errors
    pair_count = review.get("pair_count")
    if not isinstance(pair_count, int) or pair_count <= 0:
        errors.append("review index pair_count is missing or invalid")
        return errors
    if review.get("runtime_admitted") is not False:
        errors.append("deferred review library must remain runtime_admitted=false")
    if review.get("integrated_speech_pair_count") != 0:
        errors.append("deferred review library integrates speech pairs")
    if review.get("user_approved_count") != 0:
        errors.append("deferred review library records user-approved pairs")
    if review.get("excluded_speech_pair_count") != pair_count:
        errors.append("every deferred speech pair must remain excluded")

    index_pairs = review.get("pairs")
    ledger_pairs = ledger.get("pairs")
    if not isinstance(index_pairs, list) or len(index_pairs) != pair_count:
        errors.append("review index pair inventory does not match pair_count")
        index_pairs = []
    if not isinstance(ledger_pairs, list) or len(ledger_pairs) != pair_count:
        errors.append("ledger pair inventory does not match pair_count")
        ledger_pairs = []
    for source, pairs in (("review index", index_pairs), ("ledger", ledger_pairs)):
        for pair in pairs:
            if not isinstance(pair, dict):
                errors.append(f"{source} contains a non-object pair")
                continue
            ordinal = pair.get("ordinal", "unknown")
            if pair.get("runtime_admitted") is not False:
                errors.append(f"{source} pair {ordinal} is runtime-admitted")
            if pair.get("user_approved") is not False:
                errors.append(f"{source} pair {ordinal} is user-approved")
    summary = ledger.get("pairwise_full_size_review_summary")
    if not isinstance(summary, dict):
        errors.append("ledger has no pairwise review summary")
    elif summary.get("complete") is not False:
        errors.append("deferred ledger must remain explicitly incomplete")
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shipping-index", type=Path, required=True)
    parser.add_argument("--review-index", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    arguments = parser.parse_args(argv)
    errors = verify_deferred_scope(
        _load(arguments.shipping_index),
        _load(arguments.review_index),
        _load(arguments.ledger),
    )
    print(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "kingfisher-additional-pose-freeze",
                "passed": not errors,
                "errors": errors,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
