# Character Director V1 Listening Animation Review

**Reviewer:** Independent supervising character animator, acting coach, choreographer, and body-language coach  
**Decision:** **REJECT V1**  
**Candidate runtime commit:** `a652c4606f9a25a7010e7414de240a27f7350d14`  
**Capture run:** `visual-review-7dedbddee9b5`  
**Capture manifest SHA-256:** `969fae9cf44f3ab33a82f125edd710d3cde169ca4db1418339ea292c499d412c`  
**Review bundle manifest SHA-256:** `b2efa72e41aa4023ddc1d5e727cc54d3766d0ebb3a1b0ad9dfb780a13865d9ac`  
**Scope:** V1 listening only. No judgment is made about V2-V10 or overall release quality.

## Review Method

I inspected all 288 frames of the 12.000-second, 24 FPS normal-speed MP4 and
all 1,152 frame positions of the 48.000-second quarter-speed MP4. I also
reviewed the supplied contact sheet and correlated the visible changes against
all 288 records in `animation_truth_trace.ndjson`. The trace and machine report
were used as corroboration, not as substitutes for motion and acting judgment.

The sealed artifact hashes match the review bundle. The normal-speed MP4 is
`8967735e8854a1f76ddb322c97f75db193b3c46ebcfce8bfa278dd6307907fe4`;
the quarter-speed MP4 is
`aea06c705e6a5302cfde9605b5590828ebad308d8b8f8db7a02a149efb4724c8`.

## Decision

**REJECT V1.** The prior acting defects are substantially corrected: this is
no longer a front-to-profile snap, the three-quarter head-follow silhouette is
genuine and readable, the settle is visible, all three blinks paint correctly,
the profile hold contains limited listening modulation, and the root, body,
staff, wings, hands, feet, and planted contact remain stable.

The sealed capture nevertheless has an explicit hard failure under the visual
acceptance contract: **the character silhouette is clipped against the top
edge for the entire 12 seconds.** The hat is cut at the frame boundary and the
staff hook enters from beyond the canvas. The trace corroborates the visual
finding with `staff_tip_raster_span.min_y = 0` and a staff-tip stage position of
`y = -0.375`. This supplies neither the required four-cell top margin nor an
uncropped silhouette. Machine V1 acceptance did not test this framing defect.

## Applicable Scores

| Category | Weight | Score | Director finding |
|---|---:|---:|---|
| Gaze and head-eye coordination | 12 | **4/4** | Targets are immediate and legible. Two-frame eye lead, five-frame three-quarter follow, centered profile arrival, and restrained visible settle form a coherent thought. |
| Blink | 8 | **3/4** | Three closures are visible at 125, 125, and 166.667 ms. Their placement is varied and motivated; the binary lid changes remain slightly hard at quarter speed. |
| Stillness | 10 | **3/4** | The stance is exceptionally stable and now includes sparse head modulation. It reads as listening at normal speed, although the final two seconds are fully static. |
| Framing | 10 | **1/4** | Hat and staff are clipped at the top edge throughout. This is a contract hard failure despite otherwise balanced placement. |

Applicable weighted result: **28/40, normalized to 70/100**. Hand acting,
locomotion, interruption, reduced motion, and long-form repetition are not
scored because V1 does not exercise their scenario contracts.

## Timecoded Findings

| Normal speed | Quarter speed | Trace frames | Finding |
|---:|---:|---:|---|
| 0.000-12.000 s | 0.000-48.000 s | 0-287 | **Blocking:** the hat and staff silhouette remain clipped at the top boundary. Side and bottom framing are clear; the top margin is absent. |
| 0.000-2.458 s | 0.000-9.833 s | 0-59 | Viewer fixation is calm and readable. A brief one-cell head lift at frames 14-18 prevents the opening from feeling like a dead still while the body and props remain planted. |
| 2.500 s | 10.000 s | 60 | Eyes acquire the left target immediately with no dart, aperture escape, root movement, or body disturbance. |
| 2.833-2.917 s | 11.333-11.667 s | 68-70 | Three-frame scheduled blink closes visibly and symmetrically, then restores the left fixation at frame 71. It does not read as punctuation or a metronome beat. |
| 3.792-3.917 s | 15.167-15.667 s | 91-94 | Restrained head lift gives the left-target hold a small pulse of attention without disturbing feet, staff, wings, or root. |
| 5.000 s | 20.000 s | 120 | Viewer return is clean on the first presented frame. There is no overshoot, stale left gaze, or whole-body response. |
| 6.583-6.750 s | 26.333-27.000 s | 158-162 | A second subtle head lift keeps the viewer-facing hold alive. The repeated idle vocabulary is noticeable at quarter speed but unobtrusive at normal speed. |
| 7.500 s | 30.000 s | 180 | Automatic-gaze release causes no visible pop. |
| 7.750-7.792 s | 31.000-31.167 s | 186-187 | Eyes lead screen-left for two frames while the head remains front. The intention is clear before the head moves. |
| 7.833-8.000 s | 31.333-32.000 s | 188-192 | **Previous snap corrected:** the southwest/three-quarter head is a genuinely distinct silhouette held for five frames. It reads as head follow, not as a full-body walking-pose substitution; body, robe, wings, hand, staff, feet, and shadow remain unchanged. |
| 7.958-8.042 s | 31.833-32.167 s | 191-193 | The three-frame turn blink bridges three-quarter into profile. It is motivated by the turn and does not conceal a front-to-profile pop because the open three-quarter view has already been established. |
| 8.042-8.333 s | 32.167-33.333 s | 193-200 | **Settle is now visible:** profile arrives with centered gaze and a one-cell positive horizontal head offset, reopens at frame 194, recovers to the final head position at frame 197, and becomes steady at frame 200. Quarter speed reveals discrete raster steps, but normal speed reads as a restrained settle rather than a hidden state label. |
| 8.333-12.000 s | 33.333-48.000 s | 200-287 | The profile endpoint is no longer wholly frozen. A four-frame blink at 9.083-9.208 s and a one-cell head lift at 9.792-9.917 s preserve listening presence. Frames 240-287 (10.000-12.000 s) are fully static, which is acceptable as a two-second conclusion hold but leaves no reserve for a longer listening scene. |

## Previous Rejection Causes

- **Front-to-profile snap:** Corrected.
- **Missing three-quarter head-follow silhouette:** Corrected; five source frames are clearly readable at normal and quarter speed.
- **Hidden or missing settle:** Corrected at the minimum acceptable scale; the one-cell arrival offset and recovery are visibly presented.
- **Mechanical blinks:** Corrected to acceptable. All three paint, durations vary, and one is motivated by the turn.
- **Frozen profile hold:** Corrected enough for this 12-second scene by a profile blink and head lift; the final two-second hold remains intentionally still.
- **Body/root/staff/wing/foot instability:** No instability found. Trace root span, planted drift, and root residual are all zero, and visual inspection finds no prop or contact jitter during the head swaps.
- **Listening presence:** Passes at the minimum acceptable level. The eyes acquire targets decisively, the head accents are restrained, and stillness reads as attention rather than inactivity.
- **Framing/clipping:** Fails. The top silhouette is cut for the complete run and independently blocks V1 acceptance.

## Residual Concerns

1. Reframe and recapture with at least the required four-cell top margin around
   both hat and staff. Do not solve this by cropping another edge or reducing
   the required bottom grounding margin.
2. The settle and idle lifts are serviceable but rely on one-cell pose changes.
   At quarter speed they expose the limited raster vocabulary. This is not an
   acting blocker for V1, but the same cadence should not be repeated unchanged
   in V8 or longer conversational holds.
3. The supplied contact sheet samples every 12 frames and therefore omits most
   blink and settle beats. Its visible labels also do not include all tick,
   time, command, state-hash, and frame-hash fields required by the acceptance
   document. The videos and trace were sufficient for this review, but the
   contact sheet should be regenerated for a release-complete package.
4. This is one independent review. A corrected capture still requires the
   second independent reviewer and aggregate release gate.

## V1 Acceptance

**REJECT.** The character acting now meets the V1 listening intent, including
the formerly missing three-quarter follow and visible settle, but the sealed
candidate cannot be accepted while the hat and staff are visibly clipped for
the entire capture.
