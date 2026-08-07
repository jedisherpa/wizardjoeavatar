# Kingfisher Body-Locked Speech Candidate

Date: 2026-08-06

## Decision

Kingfisher speech uses exact whole-pose pairs. Each resting pose owns one
speaking-beak mate with the same authored body, staging, scale, and gesture.
The runtime may switch only within that pair while speech is active. It must
not select a global mouth pose from another gesture.

This addresses the visible beak-alignment failures caused by combining a
selected body pose with an unrelated speaking drawing.

## Candidate Inventory

- Character: `kingfisher`
- Source review library: `pair-review-compiled/library-index.json`
- Candidate package: `pair-review-compiled/kingfisher-character-package-v2.json`
- Total poses: 176
- Exact resting/speaking pairs: 88
- Legacy pairs: 66
- Stage performance pairs: 22
- User-approved pairs: 0
- Runtime admitted: false

The 88 pairs partition the complete 176-pose library. No pose is shared by two
pairs, and no speaking pose can also be a resting pose.

## Runtime Contract

Runtime profile schema V3 adds `speech_pose_pairs`, a digest-bound mapping from
each resting pose ID to its authored speaking-beak pose ID.

During active speech:

1. The selected or currently presented pose is resolved to its pair.
2. A closed mouth selects the resting member.
3. Any open mouth shape selects the speaking member.
4. Returning to closed restores the resting member.
5. A pose without a declared pair remains unchanged.

This resolver applies to both graph-driven poses and explicit pose overrides.
Profiles with the existing global `speech_pose_map` keep their prior behavior.

Kingfisher does not yet have authored eyelid variants. Its three compatibility
blink entries intentionally resolve to the same pose, which the runtime now
treats as no authored visual blink. This prevents a blink from replacing the
active body pose with neutral.

## Reproducible Build

Run:

```bash
python3 tools/build_kingfisher_runtime_candidate.py \
  assets/reference/characters/kingfisher/pair-review-compiled/library-index.json \
  assets/reference/characters/kingfisher/pair-review-compiled
```

The builder verifies the review ledger, derives and validates all 88 pairs,
checks every RGBA frame, and emits a digest-bound V2 character package plus a
candidate receipt. Existing `.wjpose` shards are reused rather than copied
when the output directory is the source directory.

## Evidence

The live package check loaded 176 poses and switched:

```text
kingfisher.act.012.explain-one-point
kingfisher.act.122.explain-one-point-speaking-beak
```

The complete focused run passed 126 tests across Kingfisher pair construction,
review compilation, choreography, package validation, capability portability,
and Serena package regressions. A subsequent targeted run also covered the
no-op blink behavior.

## Admission Boundary

The package is intentionally review-only. Internal pairwise review recorded
64 observable passes and 2 rear-view pairs as not observable; it did not record
user approval. The production registry is unchanged. Admission requires an
explicit art review, user approval evidence, and a newly admitted package
digest.
