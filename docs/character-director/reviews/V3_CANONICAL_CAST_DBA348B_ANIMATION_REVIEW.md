# V3 Canonical Cast Independent Animation Review

## Review Scope

This is an independent animation and motion review of candidate
`dba348be4ff0af21f868491cbd8de877c13d3ee2` and the published evidence bundle
`evidence/character-director/v3-canonical-cast-dba348b-2026-07-19`.

The review retained the acceptance criteria used for the rejected `a72f791`
candidate. In particular, it treated a held-prop construction swap, an omitted
recovery pose, hand/prop separation, clipping, or a visible settle discontinuity
as a V3 blocker rather than a cosmetic issue.

## Artifacts Inspected

- `README.md`
- `visual-review-0365dd9b28ac-capture.mp4` at normal speed
- `v3-quarter-speed.mp4`
- `v3-browser-layout.mp4`
- `visual-review-0365dd9b28ac-contact-sheet.png`
- representative and event PNGs covering the full first cast, all first-cast
  recovery frames, later-cast action/recovery samples, holds, and final settle
- `animation_truth_trace.ndjson`
- `v3-machine-acceptance.json`
- `contact_verification.json`
- `manifest.json`, `review-bundle-manifest.json`, and `scenario-program.json`

All three MP4 files decode completely. The normal presentation contains 312
frames at 24 FPS over 13 seconds, the quarter-speed presentation contains 1,248
frames at 24 FPS over 52 seconds, and the browser presentation contains 312
frames at 24 FPS over 13 seconds.

## Prior Blocker Verification

### 1. Staff construction swap at authored frames 2 to 3 and 27 to 28

Resolved. The first cast's authored 2 to 3 boundary is visible at transport
frames 14 to 15. Both frames retain the same long tan/brown shaft, pale wrapped
section, asymmetric brown hook, palette, and hand grip. The staff advances by a
one-cell tip step from local `(58, 12)` to `(59, 13)`; it does not change into a
shorter, darker, synthetic staff.

The first cast's authored 27 to 28 boundary is visible at transport frames 39 to
40. It makes the inverse one-cell step from `(59, 13)` to the neutral `(58, 12)`
while retaining the same complete staff construction. The contact sheet,
normal-speed presentation, quarter-speed presentation, critical PNGs, and
full-raster machine measurements agree. The full staff graph remains in the
313-cell range, with a maximum adjacent nearest-cell displacement of three
cells at the strongest square-grid rotation step rather than an object swap.

### 2. Skipped first-cast recovery frames

Resolved. The first cast presents authored recovery frames 23, 24, 25, 26, 27,
28, 29, and 30 contiguously at transport frames 35 through 42. The effect falls
through intensities `1.0`, `0.8`, `0.6`, `0.4`, `0.2`, and `0.0`; the staff
returns through adjacent arc poses; and frames 28 through 30 hold the neutral
staff before the following neutral state. No recovery frame is cut over.

The same complete 23-through-30 recovery is present in casts two and three.
The truth trace reports no recovery gaps for any cast and the visual cadence is
repeatable across all three performances.

## Animation Judgment

### Pose readability and timing

The canonical cast reads clearly as a restrained staff spell. The early frames
provide visible preparation, the staff reaches and holds an outward apex for
the action/effect phrase, and the return arc supplies a deliberate recovery and
settle. At normal speed the motion is modest but legible; at quarter speed its
step order and spacing remain coherent without reversals or pops.

The marker order supports the visible phrasing in every cast:
`action_commit` at authored frame 10, `action_effect` at 14,
`action_recoverable` at 23, and `action_settled` at 28. The tip effect appears
after commitment, stays attached to the moving hook region, and dissipates
during recovery rather than surviving the settle.

### Held prop, hand contact, and body continuity

The hand remains fixed to the same staff grip throughout all three casts. There
is no sliding grip, detached shaft, duplicate prop, or frame in which the hand
and staff separate. The character's feet and world/stage root remain planted,
with zero reported drift.

Head, torso, wings, robe, and arms remain visually continuous while the staff
rotates. Their restraint limits dramatic weight, but it is consistent with the
scope of a canonical cast and does not create a continuity failure. The stable
body gives the staff arc and effect a clear visual hierarchy.

### Silhouette, clipping, pixels, and layout

The character and complete staff remain within the canonical 240 by 135 stage
for every captured frame. The measured silhouette stays inside raster bounds
`x=79..160`, `y=22..126`, leaving visible clearance around the hat, wings,
staff hook, feet, and effect. No prop, wing, hand, hat, or effect is clipped.

Pixel edges remain crisp in the retained 960 by 540 PNGs and videos. The
browser capture uses a 1,200 by 675 backing canvas with a five-pixel device
cell, preserving square pixel presentation without smoothing artifacts. In the
1,440-pixel-wide browser layout, the character is centered with usable margins;
the media status, diagnostics, and toolbar do not obscure the silhouette or
effect. No incoherent overlap or layout jump is visible.

## Residual Notes Beyond V3

- This is intentionally a restrained canonical cast. A future hero-cast variant
  could add torso compression, shoulder lead, head follow-through, and wing
  counter-motion for more dramatic weight without changing this accepted
  baseline.
- The pale tip effect reads on the white review stage, but later environment
  testing should verify its contrast over bright or detailed backgrounds.

Neither note is a V3 acceptance blocker. The two blocking defects from the
`a72f791` review are demonstrably resolved, and no replacement motion blocker
was found.

Verdict: PASS V3
