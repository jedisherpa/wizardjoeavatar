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
records 62 observable passes, 2 `needs_rebuild` dispositions, and 2 rear-view
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
because its legacy receipt predates the required geometry. Pairs 007, 008,
010, 011, 012, 017, 022, 024, 025, 027, 030, 047, and 062 have since passed
isolated V2.1 review, leaving this 2-pair queue:

```text
001 006
```

Pairs 004 and 005 are excluded because the beak is not observable. The ledger
currently records 62 internal passes, 2 `needs_rebuild` dispositions, 2
`not_observable` dispositions, 0 user
approvals, and 0 runtime admissions.

Pair 062 (`sudden-idea`) was the first demonstrated false positive. Its stored
horizontal direction differed from the closed upper bill by about 34 degrees.
The accepted V12 successor rotates one connected lower mandible onto the
observed diagonal axis while preserving the complete body and immutable upper
bill. Anatomy V2.1 records a 0.5968-degree declared-axis error, 0.8143
lower-to-upper reach ratio, and 0.0449 normalized tip offset. Native enlarged
head review and the live two-frame projector loop show one rear hinge, no
duplicate edge, and no body drift. The body-lock audit records zero
outside-mouth change, zero registration drift, and 0.999939 silhouette IoU.
Its internal pass does not imply user approval or runtime admission.

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

Pair 011 (`neutral-speaking-gesture`) validates the same separation for a
deeper frontal speech aperture. The retained v2 mouth pixels form one centered
V while the raised presentation wing and cheek overlap stay immutable. Its
centered anatomy hinge uses a 26-pixel shared-base radius without changing the
original compositor hinge. The pair passes at 0.0062 center offset, 1.037
lower-to-upper width ratio, zero outside-mouth change, and zero registration
drift. Its internal pass does not imply user approval or runtime admission.

Pair 012 (`explain-one-point`) preserves its existing centered speaking art.
The visible frame was sound, but its legacy receipt incorrectly treated the
frontal bill as a right-facing profile. A centered anatomy hinge now measures
the actual frame: 0.0086 center offset, 0.7414 lower-to-upper width ratio, zero
outside-mouth change, and zero registration drift. The raised pointing wing,
crown, eyes, throat, hoodie, legs, and feet remain unchanged. Its internal
pass does not imply user approval or runtime admission.

Pair 017 (`insight-upward-point`) preserves the previously rebuilt restrained
profile mate after a fresh one-pair audit. The oversized pre-pairwise wedge
remains rejected. The accepted lower bill shares the closed frame's rear hinge
and opens beneath the immutable upward-left upper bill while the eye, crown,
throat, raised insight wing, hoodie, body, feet, scale, and canvas remain
unchanged. Anatomy V2.1 records an inferred axis of
`(-0.828391, -0.560150)`, a 0.7022 lower-to-upper reach ratio, 0.3700 tip
offset ratio, and 27.7889-degree opening angle. The body-lock audit records
zero outside-mouth change, zero registration drift, and 0.995961 silhouette
IoU. Its internal pass does not imply user approval or runtime admission.

Pair 022 (`small-acknowledgment`) retains the restrained v5 speaking mate.
The v4 overlay remains rejected because it creates a third interior beak edge,
and the v6 solid-cavity alternative remains rejected because it reads as a
black slab. The legacy preservation polygon included face and crown pixels, so
a separate tight bill-only anatomy polygon now measures the visible down-right
upper bill without changing any rendered pixel. The accepted pair has a
0.8772-degree declared-axis error, 0.9615 lower-to-upper reach ratio, 0.2778
tip offset ratio, 16.1141-degree opening angle, zero outside-mouth change, zero
registration drift, and 0.999766 silhouette IoU. Its internal pass does not
imply user approval or runtime admission.

Pair 024 (`polite-interruption`) retains the selected donor-v6 speaking mate
after a fresh one-pair review. The legacy preservation polygon covered much of
the face and did not represent the visible bill axis, so a separate tight
bill-only anatomy polygon now measures the upper bill without altering any
rendered pixel. The lower bill shares the closed pose's rear hinge, follows the
same right-facing axis, and ends beneath the upper tip. Anatomy V2.1 records a
0.2559-degree declared-axis error, 1.0281 lower-to-upper reach ratio, 0.3423
tip offset ratio, and 18.4149-degree opening angle. The body-lock audit records
zero outside-mouth change, zero registration drift, and 1.0 silhouette IoU.
Native, 3x nearest-neighbor head, and live two-frame projector reviews expose
only the intended bill articulation. Its internal pass does not imply user
approval or runtime admission.

Pair 025 (`hand-over-the-floor`) replaces the overshooting v6 lower bill with
the tip-locked v7 mate. Both are derived from the preserved pair-specific
donor, but v7 keeps the same authored cheek hinge while shortening the lower
bill so its tip lands beneath the immutable closed upper tip. Tight bill-only
Anatomy V2.1 geometry records a 0.2196-degree declared-axis error, 1.0041
lower-to-upper reach ratio, 0.4264 tip offset ratio, and 23.0098-degree opening
angle. The body-lock audit records zero outside-mouth change, zero registration
drift, and 0.998266 silhouette IoU. Native, 3x nearest-neighbor, and live
two-frame review confirm that the eye, crown, cheek, throat, hoodie, feet, and
extended presenting wing remain fixed. Its internal pass does not imply user
approval or runtime admission.

Pair 027 (`intimate-confidence`) retains the compact selected v5 speaking art.
Its legacy preservation polygon covered the tilted face instead of tracing the
visible bill, which made the earlier directional measurement unreliable. A
tight upper-bill anatomy polygon now records the true screen-right rear hinge
and down-left bill axis without changing rendered pixels. Anatomy V2.1 records
a 0-degree declared-axis error, 1.0408 lower-to-upper reach ratio, 0.0957 tip
offset ratio, and 5.2522-degree opening angle. The body-lock audit records zero
outside-mouth change, zero registration drift, and 1.0 silhouette IoU. Native,
3x nearest-neighbor, and live two-frame review show a restrained connected
opening while the crown, eyes, cheeks, throat, hoodie, held-in wings, body, and
feet remain fixed. Its internal pass does not imply user approval or runtime
admission.

Pair 030 (`rhetorical-question`) retains the selected v3 speaking art
byte-for-byte. Native, 4x nearest-neighbor head, and live projector review
confirm a single centered opening with both rear corners attached while the
upper bill, crown, eyes, throat, raised wings, hoodie, body, and feet remain
fixed. Its legacy receipt incorrectly classified the tilted frontal bill as a
left-facing profile. A tight upper-bill outline and separate centered anatomy
hinge now classify the same pixels as frontal with 0.0170 center offset and a
1.4205 lower-to-upper width ratio. The body-lock audit records zero
outside-mouth change, zero registration drift, and 1.0 silhouette IoU. The
isolated loop produced exactly two stable frame hashes. Its internal pass does
not imply user approval or runtime admission.

Pair 047 (`compassion`) retains the selected v2 speaking art byte-for-byte.
Its legacy preservation polygon included face and crown pixels and therefore
measured the steeply tilted bill as a short horizontal shape. A tight
bill-only outline now follows the visible down-left upper bill from the
screen-right rear hinge. Anatomy V2.1 records a 0.2685-degree declared-axis
error, 0.9538 lower-to-upper reach ratio, 0.3106 tip-offset ratio, and
18.0352-degree opening angle. Native, 5x nearest-neighbor head, and live
two-frame projector review confirm one connected lower bill while the eye,
crown, cheek, throat, hoodie, extended wing, body, feet, scale, and
registration remain fixed. The body-lock audit records zero outside-mouth
change, zero registration drift, and 1.0 silhouette IoU. Its internal pass
does not imply user approval or runtime admission.

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

The accepted Pair 011 frontal review loop is available at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-011-review
```

The accepted Pair 012 frontal review loop is available at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-012-review
```

The accepted Pair 017 upward-profile review loop is available at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-017-review
```

The accepted Pair 022 small-acknowledgment review loop is available at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-022-review
```

The accepted Pair 024 polite-interruption review loop is available at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-024-review
```

The accepted Pair 025 hand-over-the-floor review loop is available at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-025-review
```

The accepted Pair 027 intimate-confidence review loop is available at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-027-review
```

The accepted Pair 030 rhetorical-question review loop is available at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-030-review
```

The accepted Pair 047 compassion review loop is available at:

```text
http://127.0.0.1:8667/?hd-sequence=kingfisher-pair-047-review
```

A pair returns to `pass` only after isolated closed/open visual review; that
internal pass still does not imply user approval or runtime admission.
