# Kingfisher Pairwise Review Protocol V1

Date: 2026-07-31

## Decision

Kingfisher's 66 closed/open beak pairs are reviewed one pair at a time at full
projector size. Contact sheets and prior batch dispositions are retained as
history but cannot pass the current gate.

Protocol ID:

`kingfisher-full-size-pairwise-v1`

Machine authority:

`assets/reference/characters/kingfisher/legacy-pairs-v1/pair-review-ledger.json`

## Pair Gate

For each ordinal:

1. Load only its closed and open alpha frames.
2. Compute one shared opaque bound and one presentation transform.
3. Inspect the closed frame at full observer size.
4. Inspect the open frame at the same size and registration.
5. Check one rear hinge, immutable upper beak, substantial connected lower
   mandible, coherent perspective, stable head/eyes/body, and no residual
   closed edge.
6. Save both projected screenshots under the pair's evidence directory.
7. Record exactly one `pass`, `needs_rebuild`, or `not_observable`
   disposition.
8. Recompile the review-only content-addressed artifact.
9. Keep `user_approved` and `runtime_admitted` false.

`pending` is the default and is not a passing state.

## Rebuild Gate

A failed pair is rebuilt independently. Generated art may provide a matched
lower-mandible source, but generated head, eye, clothing, body, and upper-beak
pixels are discarded. The deterministic compositor:

- restores the canonical upper beak;
- permits changes only inside declared mouth masks;
- requires a minimum mandible height;
- requires one connected mandible component;
- requires contact with the declared rear hinge;
- rejects changes outside the masks;
- preserves registered silhouette bounds; and
- writes checksummed source and output receipts.

The rebuilt pair returns to full-size closed/open review. Automated geometry
passing does not substitute for visual review.

## Current Queue

- pair count: 66;
- pairwise passes: 3 (pairs 1, 2, and rebuilt 59);
- pending: 60;
- needs rebuild: 1 (pair 62);
- not observable: 2 (pairs 4 and 5);
- user approved: 0;
- runtime admitted: 0.

Pair 59 demonstrates the complete workflow. The batch candidate was rejected
for a doubled upper edge. A source-pixel rotation was rejected for insufficient
mandible thickness. A one-pair speaking render was then reduced to a connected
lower-mandible patch, horizontally registered to the canonical upper bill, and
passed at full projector size.

Evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/`

Evidence frames are rendered from the pair receipt's exact source PNGs at the
native canvas size, rather than captured from a browser compositor. This keeps
the visual receipt deterministic and avoids blank or stale canvas captures:

```bash
python3 tools/manage_kingfisher_pairwise_review.py capture \
  --ledger assets/reference/characters/kingfisher/legacy-pairs-v1/pair-review-ledger.json \
  --ordinal 59 \
  --output-dir assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-059
```

## Viewer

`http://127.0.0.1:8667/?hd-pair-review=kingfisher-paired-beaks-review`

The status line includes pair number, pose label, closed/open state, and
pairwise disposition. Direct pair selection uses `&pair=N`.

## Verification

Focused queue/compiler/viewer tests: 15 passed.

Complete Kingfisher-focused tests: 63 passed.

The strict verifier intentionally exits nonzero until all observable pairs
pass and all rear views are explicitly `not_observable`. It writes a structured
failure receipt even while blocked:

`assets/reference/characters/kingfisher/legacy-pairs-v1/review-evidence/pair-review-verification.json`

Current blocker:

`pair 3 lacks a passing full-size pairwise disposition`

This failure is expected and proves the queue is fail-closed.
