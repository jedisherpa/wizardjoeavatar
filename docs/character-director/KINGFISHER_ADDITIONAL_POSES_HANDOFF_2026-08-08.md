# Kingfisher Additional Poses Handoff

Date: 2026-08-08

## Decision

The user has placed the Kingfisher additional-pose program on hold and directed
the Character Director release to finish without these additions. This is a
scope deferral, not an approval, deletion, or runtime admission.

The existing 110-pose Kingfisher library remains available at:

`assets/reference/characters/kingfisher/compiled/library-index.json`

The unfinished 66-pair closed/open speech expansion remains preserved at:

- `assets/reference/characters/kingfisher/legacy-pairs-v1/`
- `assets/reference/characters/kingfisher/pair-review-compiled/`
- `docs/character-director/KINGFISHER_PAIRWISE_REVIEW_PROTOCOL_V1_2026-07-31.md`

## Frozen state

The authoritative ledger is:

`assets/reference/characters/kingfisher/legacy-pairs-v1/pair-review-ledger.json`

At the freeze point it records 66 pairs, zero user approvals, zero runtime
admissions, zero integrated speech pairs, 63 pending pairs, two rear-view
`not_observable` pairs, and Pair 1 awaiting direct visual approval. Historical
passes and rejected candidates remain in each pair's review history; none of
them are authoritative after the latest user visual rejection.

The last full release receipt before deferral was
`/tmp/character-director-release-full-524651cc.json`. It passed isolated clone,
Git LFS materialization, frozen dependency installation, verifier imports,
Dragon rebuild, and Robin/Speech rebuild, then stopped at the intentionally
fail-closed Kingfisher pair review.

## Why work stopped

The user observed that many open beaks were visibly misaligned in sequence
playback. Metric-led and batch reconstruction repeatedly allowed anatomically
bad frames to survive. The accepted recovery method is therefore visual and
strictly serial: one body-locked closed/open pair, reviewed at native size and
in an alternating flip, before the next pair begins.

## Resume procedure

1. Start from Pair 1 (`neutral-front`), regardless of any `pair=` query left in
   a browser tab.
2. Open
   `http://127.0.0.1:8667/?hd-pair-review=kingfisher-paired-beaks-review&pair=1`.
3. Compare the exact closed frame and its open mate at native resolution.
4. Preserve the canvas, registration, body, crown, eyes, throat, and upper bill.
5. Change only one connected lower mandible and oral cavity at the authored
   hinge. Do not add a second mouth, tongue wedge, throat bar, or detached beak.
6. Require direct user visual approval before recording a pair as passed.
7. Rebuild and inspect Pair 2 only after Pair 1 is approved.
8. Continue in ordinal order. Never batch-approve pairs from metrics or contact
   sheets.
9. Keep `user_approved=false` and `runtime_admitted=false` until the explicit
   approval and admission gates are both satisfied.
10. Re-enable the pair-review release phase only after all observable pairs
    pass and the user approves the complete playback.

The deferred-candidate test at
`tests/wizard/test_build_kingfisher_runtime_candidate.py` currently proves the
incomplete review cannot build a runtime package and that the 110-pose index is
the shipping boundary. When the program resumes, restore the positive candidate
package and closed/open choreography assertions from commit `8121d1e0`, then
make them pass only after the pair-review completion gate passes.

## Integrity check

Run the freeze verifier while this program remains deferred:

```sh
python3 tools/verify_deferred_kingfisher_scope.py \
  --shipping-index assets/reference/characters/kingfisher/compiled/library-index.json \
  --review-index assets/reference/characters/kingfisher/pair-review-compiled/library-index.json \
  --ledger assets/reference/characters/kingfisher/legacy-pairs-v1/pair-review-ledger.json
```

It fails if a deferred pair becomes user-approved or runtime-admitted, if an
additional pair enters the shipping library, or if the review inventory stops
matching its ledger.
