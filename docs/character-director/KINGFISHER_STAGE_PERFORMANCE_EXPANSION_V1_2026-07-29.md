# Kingfisher Stage Performance Expansion V1

Date: 2026-07-29

## Objective

Expand the Kingfisher from 66 static whole-pose performance drawings to a
review-gated 110-pose corpus with enough connected standing, pacing, speaking,
storytelling, and presenting material for phrase-level choreography.

## Corpus Design

The expansion reserves ACT067 through ACT110 as 22 paired body performances.
Every body performance has:

- a resting-beak pose;
- a speaking-beak pose;
- identical facing, feet, wings, scale, costume, and registration across the
  pair; and
- an explicit stage purpose and recovery path.

This paired design lets the Director animate speech while preserving the body
performance selected by the choreographer. It also avoids visually unrelated
pose changes for every mouth beat.

| Family | Body keys | Poses | Intended use |
| --- | ---: | ---: | --- |
| Marks, pacing, and turns | 10 | 20 | Crosses, arrivals, audience address, and intimate forward emphasis |
| Explanatory gesture | 5 | 10 | Welcome, emphasis, comparison, large idea, and small detail |
| Story beats | 6 | 12 | Question, suspense, reveal, confession, aside, and call to action |
| Recovery | 1 | 2 | Warm resolution and return to neutral |
| Total | 22 | 44 | ACT067-ACT110 |

The machine-readable specification is
`assets/reference/characters/kingfisher/stage-expansion-v1/pose-plan.json`.

## Visual Contract

- Use the approved Kingfisher identity from ACT001.
- Keep the black hoodie and centered white fishbone emblem.
- Wings remain feathered wings and perform the hand-like acting.
- Preserve the compact bird proportions, crest, orange cheek and chest
  markings, white throat, dark blue-gray feathering, and brown bird feet.
- Produce one isolated full-body subject per frame.
- Register to a 960 x 540 transparent canvas.
- Preserve binary alpha after import.
- Normalize with the existing body-core, bottom-center presentation policy.
- Do not admit the new poses to production runtime before live visual review.

## Approval Gates

1. Identity and costume match.
2. Full silhouette and both feet are uncropped.
3. Pose purpose is readable at normal observer scale.
4. Resting/speaking pair differs only at beak and minimal throat articulation.
5. Pair registration does not jump.
6. Pacing poses preserve believable weight transfer and foot contact.
7. Presentation normalization remains stable across all 110 poses.
8. Choreography sequences use authored neighbors and recovery poses.
9. Full-resolution observer review is recorded.
10. Runtime admission remains separate from visual acceptance.

## Implemented Choreography Sequences

- `kingfisher-stage-center`
- `kingfisher-pace-left`
- `kingfisher-pace-right`
- `kingfisher-stage-explain`
- `kingfisher-stage-story`
- `kingfisher-stage-resolution`
- `kingfisher-stage-performance-all`

Each sequence carries explicit hold timing and pair-aware speech alternation.
The character-specific interpretation policy is recorded in
`assets/reference/characters/kingfisher/kingfisher-choreography-dictionary-v1.json`.

## Implementation Record

Status: compiled and visually reviewed as a review-only corpus. Production
runtime admission remains false.

- Existing corpus: ACT001-ACT066.
- Stage expansion: ACT067-ACT110.
- Compiled corpus: 110 poses in 4 deterministic `.wjpose` shards.
- Authored sequences: 13 total, including the 7 stage sequences above.
- Stage pairs audited: 22 of 22 passed.
- Minimum resting/speaking silhouette IoU: `0.992983`.
- Maximum registration-bound delta: `0` pixels.
- Minimum visible mouth-region change: `8.45214`.
- Maximum change outside the articulation region: `0.0`.
- Rendered pixels changed inside each articulation region: `5,437` to
  `10,331`.
- Every body performance owns a plan-bound mouth region no larger than
  140 x 130 pixels. Stabilization uses a feathered rounded mask inside that
  region, and compilation rejects audits made against any other region.
- Pair audit receipts bind the exact resting and speaking alpha bytes by
  SHA-256 and compare composited RGBA output so invisible transparent RGB
  cannot satisfy or invalidate the visual gate.
- Stage shard SHA-256:
  `973263f01f5f1a22839b125a69e1031d199833d0d3eecf062b7505273dad322d`.
- Library index SHA-256:
  `93a68f478b77a1e8c7f6be56036089108445e37d6450e40049e506e21be4b3cf`.
- Canonical 66-pose source archive SHA-256:
  `81618492a556bd7fe45bb7793706506b888b05bb0da26614ed2a930aedfa9b81`.

The imported and generated evidence is retained under
`assets/reference/characters/kingfisher/stage-expansion-v1/generated/`:

- `chroma/` contains the flat-green generated source frames;
- `alphas/` contains raw intermediates, registered pair candidates, and the
  final transparent 960 x 540 binary-alpha frames; and
- `audits/` contains individual registration reports plus one machine-readable
  pair report for every resting/speaking body performance.

The generation passes used the registered ACT001 Kingfisher as the identity
reference, the approved ACT067 stage styling as the performance reference, and
the same chroma-key, registration, stabilization, and pair-audit pipeline for
every new pose. Speaking poses were derived from their resting twins, then
restricted to the articulation region so body acting does not jump while the
beak moves.

## Reproduction

Recover the original 66-pose review library from the supplied source archive:

```bash
python3 tools/recover_kingfisher_review_library.py \
  --archive "assets/reference/characters/kingfisher/source/Archive 2.zip" \
  --profile assets/reference/characters/kingfisher/compiled/library-index.json \
  --output-root /tmp/kingfisher-recovered-base
```

The recovery tool accepts either the original 66-pose profile or the compiled
110-pose profile. It validates character identity, runtime IDs, pose ordering,
canvas size, archive uniqueness, and sequence references, then reconstructs
only the canonical ACT001-ACT066 base shards.

For each generated frame, remove chroma and register it with:

```bash
python3 tools/register_kingfisher_stage_pose.py --help
```

Rebuild and audit every plan-bound resting/speaking pair with:

```bash
python3 tools/rebuild_kingfisher_stage_pairs.py \
  --plan assets/reference/characters/kingfisher/stage-expansion-v1/pose-plan.json \
  --alpha-root assets/reference/characters/kingfisher/stage-expansion-v1/generated/alphas \
  --audit-root assets/reference/characters/kingfisher/stage-expansion-v1/generated/audits
```

The lower-level stabilization and auditing commands remain available for
single-pair diagnosis:

```bash
python3 tools/stabilize_kingfisher_stage_pair.py --help
python3 tools/audit_kingfisher_stage_pair.py --help
```

Compile the accepted stage expansion:

```bash
python3 tools/compile_kingfisher_stage_library.py \
  --base-index assets/reference/characters/kingfisher/compiled/library-index.json \
  --plan assets/reference/characters/kingfisher/stage-expansion-v1/pose-plan.json \
  --choreography assets/reference/characters/kingfisher/kingfisher-choreography-dictionary-v1.json \
  --alpha-root assets/reference/characters/kingfisher/stage-expansion-v1/generated/alphas \
  --audit-root assets/reference/characters/kingfisher/stage-expansion-v1/generated/audits \
  --output-root assets/reference/characters/kingfisher/compiled
```

Render the stage range for visual review:

```bash
python3 tools/render_hd_pose_contact_sheet.py \
  --index assets/reference/characters/kingfisher/compiled/library-index.json \
  --output /tmp/kingfisher-stage-act067-110-contact.png \
  --start 67 \
  --end 110 \
  --columns 4 \
  --thumbnail 320
```

## Verification

The focused suite passed 34 tests covering portable registration evidence,
plan-bound pair rebuilding, tight articulation masks, alpha-aware and
checksum-bound pair auditing, deterministic and relocatable compilation,
archive recovery, choreography vocabulary, HD pose loading, observer behavior,
and structured-ID contact-sheet ranges:

```bash
python3 -m unittest \
  tests.wizard.test_register_kingfisher_stage_pose \
  tests.wizard.test_stabilize_kingfisher_stage_pair \
  tests.wizard.test_audit_kingfisher_stage_pair \
  tests.wizard.test_rebuild_kingfisher_stage_pairs \
  tests.wizard.test_compile_kingfisher_stage_library \
  tests.wizard.test_recover_kingfisher_review_library \
  tests.wizard.test_kingfisher_choreography_dictionary \
  tests.wizard.test_hd_pose_artifact \
  tests.wizard.test_character_observer \
  tests.wizard.test_render_hd_pose_contact_sheet
```

Live review was performed in the dual observer at
`http://127.0.0.1:8665/`, with approved HD Wizard Joe retained as the top
baseline and the expanded Kingfisher reel below. The new Kingfisher runtime was
loaded from the compiled 110-pose index and observed cycling late-stage
storytelling gestures without changing the Joe process.
