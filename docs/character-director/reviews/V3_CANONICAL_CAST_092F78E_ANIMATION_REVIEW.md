# Character Director V3 Canonical Cast Animation Review

**Reviewer:** Independent supervising animation director
**Decision:** **PASS V3**
**Candidate runtime commit:** `092f78e7ca58dae1a457b2646d04aa8ef776f646`
**Evidence bundle:** `evidence/character-director/v3-canonical-cast-092f78e-2026-07-19`
**Bundle manifest SHA-256:** `ec3e0c490295b5d6dc5a68dc5327857ac484366ab2167b367d1f0f15819d97cb`
**Scope:** V3 canonical front cast only. This decision does not accept V1-V2,
V4-V10, or the overall Character Director release.

## Review Method And Limitation

I verified the bundle provenance against commit
`092f78e7ca58dae1a457b2646d04aa8ef776f646`, recalculated the retained
artifact hashes, inspected the full contact sheet, inspected decoded frame
sequences for all 36 presented frames of each of the three casts, and
correlated the visible action with all 240 records in
`animation_truth_trace.ndjson`, `contact_verification.json`, and
`v3-machine-acceptance.json`.

Direct real-time video playback was unavailable in this review environment.
Normal-speed and quarter-speed judgment therefore uses the retained MP4
metadata and decoded frames rather than live playback. The normal artifact is
240 frames at 24 FPS over 10.000 seconds. The quarter-speed artifact retains
240 ordered frames at nominal 6 FPS over 39.875 seconds. A decoded comparison
measured SSIM `0.999856`, supporting that the slowed artifact presents the
same visual sequence with only negligible H.264 re-encoding differences. This
limitation does not block V3 because the complete ordered frame sequence,
timing, contact sheet, trace, and machine measurements are retained and
internally consistent.

## Decision

**PASS V3.** The corrected outward staff path reads as one controlled cast:
neutral preparation, outward windup, effect stroke, readable hold, recovery,
and exact return to neutral. The crook no longer crosses Joe's eye, face, or
hat brim. The grip remains attached to one hand, the body and planted stance
remain stable, and the effect stays visually associated with the staff tip.
All three repetitions preserve the same action structure without a pose pop,
prop teleport, crop, or recovery hitch.

The performance is deliberately restrained and prop-led. It is acceptable as
the canonical V3 cast, though it is not yet a large, body-driven hero cast.

## Director Assessment

| Area | Finding |
| --- | --- |
| Silhouette | **Pass.** Staff, hand, wings, robe, feet, and hat remain separately readable throughout. No anatomy break or silhouette collapse appears in the retained frames. |
| Face and hat clearance | **Pass.** At closest approach, the crook remains outside the facial silhouette and above/right of the brim. Effect pixels occupy the negative space between hat and crook without obscuring the eyes. |
| Staff arc | **Pass.** The outward arc has clear preparation, stroke, hold, and return. Quarter-speed frames expose discrete pixel stepping, as expected, but no reversal, teleport, or one-frame kink. Machine evidence reports no adjacent movement above two local cells. |
| Fixed grip | **Pass.** The staff pivots through a stable right-hand contact. No hand switch, sliding grasp, detached shaft, or root compensation is visible; measured grip drift is `0.0`. |
| Staging | **Pass.** Joe remains centered, grounded, and balanced while the action expands into open space on screen right. The stable body keeps the effect readable rather than competing with the wings. |
| Timing | **Pass.** The 32 authored phases provide readable preparation, commitment, stroke, hold, recovery, and settle within each 1.5-second cast window. Marker order is identical in all three casts: commit 10, effect 14, recoverable 23, settled 28. |
| Effect readability | **Pass.** The small blue, gold, and white effect appears at the crook on the stroke, remains anchored during the active/recovery phases, and clears before neutral. It is legible against the retained white stage without becoming a disconnected particle trail. |
| Settle | **Pass.** By authored frame 28 the staff has returned to the original vertical line, the effect is inactive, and the remaining frames hold cleanly. There is no final-frame snap. |
| Repetition consistency | **Pass.** The same authored staff path and marker sequence recur three times. Machine evidence reports no repeated-frame conflicts. The blink visible during the third cast is an independent facial overlay and does not disturb the cast geometry. |
| Cropping and margins | **Pass.** No cast frame is clipped. The measured silhouette span is `x=79..160`, `y=22..126` on the `240 x 135` stage, leaving 79 cells on each side, 22 above, and 8 below. This exceeds the four-cell top/side and six-cell bottom contract. |
| Normal/quarter-speed support | **Pass with stated review limitation.** The normal timing supports a compact cast; the slowed frame sequence exposes no hidden continuity or contact defect. Direct real-time playback was unavailable, as noted above. |

Applicable rubric judgment: **hand acting 3/4**, **framing 4/4**, and **V3
repetition consistency 4/4**. The hand score reflects the intentionally fixed
arm and body, not a continuity defect.

## Machine Corroboration

The machine report passes all nine V3 checks over 240 contiguous owned frames:

- 91 canonical cast trace records and authored frames `0..30` observed;
- all four action markers occur once and in order for every cast;
- world-root drift, stage-root drift, planted drift, and staff-grip drift are
  all `0.0`;
- zero staff continuity failures, repeated-frame conflicts, effect failures,
  dropped frames, missing truth frames, or clipped frames;
- all three effect starts retain a valid authored staff-tip anchor.

Machine evidence corroborates the visible result; it does not substitute for
the silhouette and acting judgment above.

## Residual Risks

1. The body, arm, robe, and wings intentionally remain structurally still
   while the staff pivots. This is clean for the canonical cast but limits
   weight and anticipation. A future hero-cast variant should add authored
   upper-body participation without weakening the fixed-grip and contact
   guarantees.
2. The effect is appropriately restrained on the white evidence stage, but
   its pale pixels may lose contrast over bright or visually complex worlds.
   Background contrast belongs in later staging and V10 review.
3. V3 proves a stationary front cast only. Turning, locomotion blending,
   interruption, reduced-motion behavior, and long-form repetition remain
   separate V6-V9 gates.
4. This is one independent review. Overall release acceptance still requires
   the second independent reviewer and aggregate release gate.

None of these residual risks blocks V3.

## Artifact Binding

| Artifact | SHA-256 |
| --- | --- |
| `manifest.json` | `ec3e0c490295b5d6dc5a68dc5327857ac484366ab2167b367d1f0f15819d97cb` |
| `scenario-program.json` | `fb4ca6d69ffbbd829ffaf98dd5bfc2234aca8b7f1df4617b050b871cb95f5108` |
| `animation_truth_trace.ndjson` | `872a30797d4de2d1ff7dbdedad500735783f3928a6e9a3c9345b5342e5c5070c` |
| `contact_verification.json` | `3bd2f97ef4eec8cdc408d9c8090ee46186031a707e8c70b742977f17ed6475c7` |
| `v3-machine-acceptance.json` | `426fadc97d2b37e60e86e383a78158536f51ea43b0bf020b3c47fef77d97e8a9` |
| `visual-review-050ab52e8764-capture.mp4` | `bb4b01970898a315f1177f27789f3122afa5096212c71264758dcf6180efc7a0` |
| `v3-quarter-speed.mp4` | `5f03ad2db38e7e6622f1aa0afbbe96c3bfba557b85cdb122513ccbb9d7f81dcc` |
| `visual-review-050ab52e8764-contact-sheet.png` | `aa564eed80b85c41c0e163e7d61fcb4bc3da849b4401d75c25eb126d5cca4593` |

## V3 Acceptance

**PASS.** The immutable evidence bound to commit
`092f78e7ca58dae1a457b2646d04aa8ef776f646` supports acceptance of the
canonical three-cast V3 scenario. The staff arc is coherent, the fixed grip
and planted staging hold, the effect reads at the correct event, the face and
hat remain clear, every repetition settles cleanly, and the complete
silhouette stays inside the canonical frame.
