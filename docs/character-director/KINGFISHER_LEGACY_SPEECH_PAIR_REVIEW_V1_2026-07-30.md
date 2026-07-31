# Kingfisher Legacy Speech Pair Review V1

Date: 2026-07-30

## Purpose

Give each of Kingfisher's original ACT001-ACT066 body performances a
body-locked speaking mate at ACT111-ACT176, then review every closed/open pair
for anatomical beak alignment before any user approval or runtime admission.

This work is a review extension of the existing Python projector. It does not
create a second animation runtime and does not admit candidate art to the
production character library.

## Why The First Pass Was Rejected

The bulk donor-transfer experiment was rejected because several tilted and
profile poses acquired a second, misaligned beak edge. Registration and
silhouette tests could pass even when a generated mouth looked anatomically
wrong: the frame stayed centered, but too much of the beak had been redrawn
inside the allowed articulation region.

The rejection is recorded in:

`assets/reference/characters/kingfisher/legacy-pairs-v1/bulk-synthesis-rejection.json`

## Pair-By-Pair Workflow

Every pair is handled as an independent review unit:

1. Normalize the source body onto the registered 960 x 540 canvas.
2. Preserve the normalized closed frame as the body and head master.
3. Produce one open-beak candidate for the same authored body performance.
4. Restrict changes to the declared articulation region.
5. Run binary-alpha, body-lock, silhouette, registration, and checksum audits.
6. Render a nearest-neighbor closed/open beak closeup.
7. Inspect the mouth corner, upper beak, lower-mandible arc, and head lock.
8. Record an internal disposition in the pair ledger.
9. Keep user approval and runtime admission false.

For generated candidates that redraw or misalign the beak, the replacement
method rotates pixels from the original lower mandible around a declared
hinge. The upper beak remains immutable source art. The rejected candidate is
retained beside the corrected result.

## Anatomical Review Contract

A visible pair passes internal review only when:

- both mandibles converge at one authored mouth corner;
- the upper beak preserves its original position and facing;
- the lower mandible follows a coherent rotational arc;
- no detached or parallel "second beak" remains;
- the head and body do not drift between closed and open frames;
- the mouth opening is visible at observer scale; and
- no pixels change outside the reviewed articulation region.

ACT004 and ACT005 face away from the viewer. They are retained as body poses
but are recorded as `not_observable`, not as successful visible lip-sync
pairs.

## Review Authority

The original close-up batch dispositions remain preserved under each row's
`internal_visual_review` field. They are historical evidence only. They no
longer authorize a pair for animation because a contact sheet can hide
mandible thickness, duplicate edges, and hinge drift.

The current authority is `pairwise_full_size_review`, protocol
`kingfisher-full-size-pairwise-v1`. Each pair must be projected by itself at
full observer size, switched manually between closed and open, and assigned
one of four fail-closed states:

- `pending`: not yet inspected under the pairwise protocol;
- `pass`: visible closed/open anatomy passed;
- `needs_rebuild`: a named defect blocks the pair;
- `not_observable`: the authored rear view has no visible mouth to judge.

Changing a pair's state never implies user approval or runtime admission.

## Review State

The machine-readable authority is:

`assets/reference/characters/kingfisher/legacy-pairs-v1/pair-review-ledger.json`

Current authoritative pairwise totals:

- full-size anatomical passes: 14;
- pending full-size reviews: 49;
- not observable: 2;
- currently awaiting rebuild: 1;
- user-approved pairs: 0; and
- runtime-admitted pairs: 0.

The close-up evidence is under:

`assets/reference/characters/kingfisher/legacy-pairs-v1/review-evidence/detail-boards/`

Pair 59 (`determination`) and pair 62 (`sudden idea`) exposed a limitation in
the source-pixel hinge experiment. Pair 59's selected source mandible was too
thin, while pair 62 retained a closed-beak edge behind the rotated layer. The
original failures remain preserved as rejected evidence.

Full-size failure evidence is under:

`assets/reference/characters/kingfisher/legacy-pairs-v1/review-evidence/full-size-failures/`

The replacement workflow then handled each pose as an independent pair:

- pair 59 uses its own aligned matched render inside one bounded articulation
  polygon, preserving every source pixel outside the mouth region; and
- pair 62 promotes its previously rendered, body-locked matched alpha as an
  explicit source artifact and deterministically re-composites only its
  articulation region.

The compositor now accepts transparent matched alpha sources directly. A
separate lower-mandible patch tool also enforces minimum thickness,
single-component connectivity, hinge contact, optional residual-edge clearing,
and exact source-upper-beak restoration for pairs whose matched render can be
reduced to a local jaw patch.

Both candidates were inspected individually at full observer size. That review
rejected pair 59 because its lower mandible collapsed to a needle-thin line,
and rejected pair 62 because stacked edges leave its hinge ambiguous. Their
failure evidence is under:

`assets/reference/characters/kingfisher/legacy-pairs-v1/review-evidence/full-size-failures/`

Pair 59 was subsequently rebuilt as one independent pair. A new matched
speaking render supplied only the lower-mandible pixels. The deterministic
compositor preserved the canonical head, upper beak, body, and registration;
enforced a connected minimum-thickness mandible; and horizontally registered
the mandible to the authored upper-beak tip. The full-size projector review
then passed the pair. Its evidence is under:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-059/`

Pair 13 (`balance two ideas`) was also rejected during the one-pair full-size
pass because its speaking bill and mouth cavity drifted screen-left. Its
original speaking source is preserved beside the pair. The accepted candidate
keeps the closed body and upper bill immutable and moves only a connected,
bounded lower-mouth patch 9 pixels right and 4 pixels down. The pair audit
reports zero changed pixels outside the mouth region, stable registration
bounds, and a visible articulation. Its evidence is under:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-013/`

Pair 62 remains `needs_rebuild`. This remains internal anatomical review, not
user approval.

## Review Projection

The review-only library contains:

- ACT001-ACT066 normalized closed masters;
- ACT111-ACT176 body-locked speaking mates; and
- ACT067-ACT110 stage-performance poses.

The paired review sequence alternates each exact closed/open pair:

`kingfisher-paired-beaks-review`

Local observer:

`http://127.0.0.1:8667/?hd-pair-review=kingfisher-paired-beaks-review`

Optional direct pair selection:

`http://127.0.0.1:8667/?hd-pair-review=kingfisher-paired-beaks-review&pair=59`

The reviewer loads one closed/open pair together, computes one shared opaque
silhouette bound, and applies the same full-size presentation transform to
both frames. The arrow buttons change pairs, the square and diamond buttons
select closed or open, and the play button alternates only the current pair.
This transform changes presentation only; source RGBA pixels, registration,
checksums, approval state, and runtime admission remain unchanged.

The current content-addressed pair artifact is:

`kingfisher_act_001_066_111_176_pair_review-cd5c5b4ba5020f15.wjpose`

Artifact SHA-256:

`cd5c5b4ba5020f15d1c923c1131017fe6e405c95e2da654f256fc10e0ee9b650`

Library-index SHA-256:

`5e55c1958e18b7376f487ef2207164c951acf2490c25c69d01141afab73e4e50`

Artifacts are published to content-addressed filenames. A running observer
continues reading its prior complete file while a new artifact and index are
written, avoiding partial-file reads during review updates.

## Reproduction

Inspect the complete legacy rebuild command:

```bash
python3 tools/rebuild_kingfisher_legacy_pairs.py --help
```

Reconstruct one failed lower mandible:

```bash
python3 tools/articulate_kingfisher_lower_mandible.py --help
```

Composite one connected, thickness-gated lower-mandible patch:

```bash
python3 tools/compose_kingfisher_pair_mandible_patch.py --help
```

Record one internal visual disposition:

```bash
python3 tools/record_kingfisher_pair_visual_review.py --help
```

Initialize or record the authoritative full-size pairwise queue:

```bash
python3 tools/manage_kingfisher_pairwise_review.py initialize --help
python3 tools/manage_kingfisher_pairwise_review.py record --help
```

Compile the review-only library:

```bash
python3 tools/compile_kingfisher_pair_review_library.py \
  --base-index assets/reference/characters/kingfisher/compiled/library-index.json \
  --ledger assets/reference/characters/kingfisher/legacy-pairs-v1/pair-review-ledger.json \
  --output-root assets/reference/characters/kingfisher/pair-review-compiled
```

Render the full-resolution beak detail boards:

```bash
python3 tools/render_kingfisher_pair_detail_boards.py \
  --index assets/reference/characters/kingfisher/pair-review-compiled/library-index.json \
  --ledger assets/reference/characters/kingfisher/legacy-pairs-v1/pair-review-ledger.json \
  --output-root assets/reference/characters/kingfisher/legacy-pairs-v1/review-evidence/detail-boards
```

## Verification

The Kingfisher-focused suite passed 63 tests covering:

- deterministic lower-mandible articulation;
- transparent matched-source loading;
- connected, minimum-thickness mandible extraction;
- hinge-contact and detached-geometry rejection;
- residual closed-edge clearing;
- immutable upper-beak construction;
- pair receipt and checksum enforcement;
- pair reconstruction and stabilization;
- alpha-aware articulation auditing;
- review-only compilation;
- interrupted artifact publication;
- content-addressed artifact naming; and
- preserved historical review accounting;
- fail-closed full-size pairwise queue management;
- protocol-ID enforcement;
- viewer disposition presentation; and
- structured blocked-verification receipts.

The review projection still loads all 176 poses and retains the following
machine measurements:

- 176 of 176 poses use 960 x 540 binary-alpha frames;
- the paired sequence contains exactly 132 alternating closed/open frames;
- minimum pair silhouette IoU is `0.978551`;
- maximum registration-bound delta is `1` pixel;
- three visible pairs have passing full-size pairwise dispositions;
- 60 pairs remain pending full-size review;
- pair 62 remains an explicit rebuild blocker;
- two rear-facing pairs are explicitly not observable; and
- user approval and runtime admission remain zero.

The strict verifier now exits nonzero with
`pair 3 lacks a passing full-size pairwise disposition`. The tracked
verification receipt
records `passed: false` and
`verification_state: blocked_by_pairwise_full_size_review`. The current ledger
points every pair to its independent pairwise state and blocks incomplete
review from approval or runtime admission.

Verification receipt:

`assets/reference/characters/kingfisher/legacy-pairs-v1/review-evidence/pair-review-verification.json`

Internal anatomical review is not user approval. The candidate library remains
review-only until the user accepts it and a separate runtime-admission step is
completed.
