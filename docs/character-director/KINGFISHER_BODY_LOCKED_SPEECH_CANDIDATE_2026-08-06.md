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

The package is intentionally review-only. The current Anatomy V2.1 re-audit
records 52 observable passes, 12 `needs_rebuild` dispositions, and 2 rear-view
pairs as not observable; it does not record user approval. The production
registry is unchanged. Admission requires completion of the isolated art
review, user approval evidence, and a newly admitted package digest.

## Anatomy V2 Re-audit

Later live review showed that silhouette overlap and registration stability did
not prove that a lower bill shared the closed pose's hinge, direction, or tip.
The earlier internal disposition is therefore superseded for affected pairs.

Anatomy V2.1 derives the upper-bill axis from the closed pose itself. Equally
distant upper-tip corners are averaged so a one-pixel radial difference cannot
choose the wrong bill edge. A declared axis more than 25 degrees from that
observed direction fails. Lower-bill displacement and speech aperture are
measured separately: normalized tip offset may not exceed 0.65, and the
hinge-to-tip opening angle may not exceed 50 degrees. The compiler recomputes
these measurements from receipt geometry rather than trusting stored V1
scores.

The first re-audit measured the 63 pairs with explicit hinge geometry and
placed 14 into an explicit one-pair rebuild queue. Pair 001 is also queued
because its legacy receipt predates the required geometry. Pairs 007 and 008
have since passed isolated V2.1 review, leaving this 12-pair queue:

```text
001 006 011 012 017 022 024 025 027 030 047 062
```

Pairs 004 and 005 are excluded because the beak is not observable. The ledger
currently records 52 internal passes, 12 `needs_rebuild` dispositions, 2
`not_observable` dispositions, 0 user
approvals, and 0 runtime admissions.

Pair 062 (`sudden-idea`) was the first demonstrated false positive. Its stored
horizontal direction differed from the closed upper bill by about 34 degrees.
Candidate V12 rotates one connected lower mandible onto the observed diagonal
axis. Its declared-axis error is under 1 degree and its normalized tip offset
is about 0.045, but it remains an unapproved review candidate.

Pair 006 (`right-profile`) is the second isolated rebuild. The prior lower
bill exceeded the Anatomy V2 tip-offset boundary. Candidate V5 rotates the
matched lower-bill donor 10 degrees around the closed pose's rear hinge rather
than translating it as a free patch. A live projector pass also rejected the
first mechanically valid candidate because its pale gap made the lower bill
read as a detached spike. V5 restores a connected dark cavity and the donor's
warm inner edge. The closed pose remains authoritative for the complete body
and upper bill. The rebuilt pair has a 0.41-degree declared-axis error, a
0.344 normalized tip offset, zero registration drift, and zero outside-mouth
mean difference. It remains in `needs_rebuild` until the isolated loop is
visually accepted; these measurements do not constitute user approval or
runtime admission.

Pair 007 (`front-three-quarter-right`) exposed the difference between a
misaligned bill and a legitimate wide-open speech drawing. The accepted art
already had a shared cheek hinge and stable upper bill, but V2 selected one
upper-tip corner and interpreted the 38.79-degree opening as lateral
misalignment. V2.1 averages the two tip corners and records both quantities.
The isolated projector loop passes with a 3.58-degree declared-axis error,
0.6209 lower-to-upper reach ratio, zero outside-mouth change, and zero
registration drift. Its internal pass does not imply user approval or runtime
admission.

Pair 008 (`relaxed-idle`) exposed a receipt-shape error rather than an art
error. Its legacy upper-bill preservation polygon intentionally covered a
larger patch and included crown pixels, so it pointed the measured bill axis
upward. A separate tight bill-only anatomy polygon now measures the visible
bill while leaving the preservation mask and every rendered pixel unchanged.
The isolated enlarged and live-projector loop passes with a 3.03-degree
declared-axis error, 22.32-degree opening angle, 0.9124 lower-to-upper reach
ratio, zero outside-mouth change, and zero registration drift. Its internal
pass does not imply user approval or runtime admission.

Pair 010 (`ready-stance`) exposed a frontal-validation error. Its exact open
pixels were already centered and body-locked, but the compositor's historical
corner rotation point caused the validator to classify the symmetrical bill as
a right-facing profile. Receipts may now preserve that compositor hinge while
declaring a separate centered anatomy hinge. A tight bill outline classifies
the pair as frontal with 0.0094 center offset, 1.3962 lower-to-upper width
ratio, zero outside-mouth change, and zero registration drift. Its internal
pass does not imply user approval or runtime admission.

Every compiled pair now has a dedicated two-frame loop. Pair 062 can be
reviewed locally at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-062-review
```

The same form applies to other ordinals, such as
`kingfisher-pair-006-review`. The Pair 006 candidate is available at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-006-review
```

The accepted Pair 007 review loop is available at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-007-review
```

The accepted Pair 008 review loop is available at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-008-review
```

The accepted Pair 010 frontal review loop is available at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-010-review
```

A pair returns to `pass` only after isolated closed/open visual review; that
internal pass still does not imply user approval or runtime admission.
