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

## Review State

The machine-readable authority is:

`assets/reference/characters/kingfisher/legacy-pairs-v1/pair-review-ledger.json`

Current internal review totals:

- pairs reviewed: 66;
- anatomical passes: 64;
- not observable: 2;
- currently awaiting rebuild: 0;
- user-approved pairs: 0; and
- runtime-admitted pairs: 0.

The close-up evidence is under:

`assets/reference/characters/kingfisher/legacy-pairs-v1/review-evidence/detail-boards/`

Pair 59 (`determination`) and pair 62 (`sudden idea`) were rebuilt from their
original lower-mandible pixels at a -14 degree hinge rotation. Pair 59's
parallel second-beak edge and pair 62's oversized black wedge were removed.
Their earlier candidates remain in the corresponding `pair-work` folders as
rejected evidence.

## Review Projection

The review-only library contains:

- ACT001-ACT066 normalized closed masters;
- ACT111-ACT176 body-locked speaking mates; and
- ACT067-ACT110 stage-performance poses.

The paired review sequence alternates each exact closed/open pair:

`kingfisher-paired-beaks-review`

Local observer:

`http://127.0.0.1:8667/?hd-sequence=kingfisher-paired-beaks-review`

The current content-addressed pair artifact is:

`kingfisher_act_001_066_111_176_pair_review-6ecc7f1356cecf46.wjpose`

Artifact SHA-256:

`6ecc7f1356cecf46340e4b19eff4baf5dcd29c002cfc28a779c5d3cd42a505c4`

Library-index SHA-256:

`5e5c428d5561cba95b14bf49ea2a073b041ae13c63f44938c614bffe85dc0237`

Artifacts are published to content-addressed filenames. A running observer
continues reading its prior complete file while a new artifact and index are
written, avoiding partial-file reads during review updates.

## Reproduction

Rebuild all candidate pairs:

```bash
python3 tools/rebuild_kingfisher_legacy_pairs.py \
  --plan assets/reference/characters/kingfisher/legacy-pairs-v1/rebuild-plan.json
```

Reconstruct one failed lower mandible:

```bash
python3 tools/articulate_kingfisher_lower_mandible.py --help
```

Record one internal visual disposition:

```bash
python3 tools/record_kingfisher_pair_visual_review.py --help
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

The focused suite passed 33 tests covering:

- deterministic lower-mandible articulation;
- immutable upper-beak construction;
- pair receipt and checksum enforcement;
- pair reconstruction and stabilization;
- alpha-aware articulation auditing;
- review-only compilation;
- interrupted artifact publication;
- content-addressed artifact naming; and
- internal visual-review accounting.

The machine verifier loaded all 176 review poses and confirmed:

- 176 of 176 poses use 960 x 540 binary-alpha frames;
- the paired sequence contains exactly 132 alternating closed/open frames;
- minimum pair silhouette IoU is `0.978551`;
- maximum registration-bound delta is `1` pixel;
- 64 visible pairs have passing internal visual dispositions;
- two rear-facing pairs are explicitly not observable; and
- user approval and runtime admission remain zero.

Verification receipt:

`assets/reference/characters/kingfisher/legacy-pairs-v1/review-evidence/pair-review-verification.json`

Internal anatomical review is not user approval. The candidate library remains
review-only until the user accepts it and a separate runtime-admission step is
completed.
