# Character Director V1 Listening Animation Review

**Reviewer:** Fresh independent animation, motion, acting, choreography, and body-language reviewer

**Decision:** **ACCEPTED**

**Candidate commit:** `8fb8c4b80031a0500202a67e8beb70a16c8a0a1c`

**Capture run:** `visual-review-434ae0491d43`

**Capture manifest SHA-256:** `451b60751e083cde4f86dd9821128b6e3b50888c13d3b83a5da0262e02570f1c`

**Review bundle manifest SHA-256:** `8d4c6ba577b0fe1e01382950e858d632819e8d8bf4eecdd3e93ff5ae50468519`
**Scope:** V1 listening only. This review does not accept V2-V10 or the complete Character Director release.

## Review Method

I reviewed the complete 12.000-second, 288-frame normal-speed atomic MP4,
the 48.000-second, 1,152-frame quarter-speed MP4, and the 12.000-second,
288-frame real-browser layout MP4. I inspected the transition-rich contact
sheet, correlated the visible beats to all 288 records in
`animation_truth_trace.ndjson`, and checked the machine report and manifests as
corroborating evidence rather than substitutes for animation judgment.

The reviewed normal-speed, quarter-speed, and browser-layout videos have
SHA-256 values `f11e30a55f22f9d509473650787e30e3bfc6ba8676e3c5c90cd1dd4bf558405d`,
`2b9940ab4401b2584ec1a50a1164e061591125b930abe42541f70a0d8f87d618`,
and `96b795f40dd8ed6ea8955ed11155e878c0ae5243ea175b0298a358313a73df0e`.
The review bundle is complete and identifies candidate commit `8fb8c4b`; the
capture began from a clean tracked worktree and its runtime binding is verified.

## Verdict

**ACCEPTED.** V1 now reads as a restrained listening performance rather than a
sequence of state swaps. The viewer-left-viewer eye choreography is clear, the
eyes lead the large turn by two presented frames, a genuine authored
three-quarter silhouette bridges the turn, the profile arrives under the turn
blink, and the short offset recovery creates a visible settle. Sparse five-frame
head lifts maintain listening presence without making the planted body busy.

Both blinks are visible, bounded, and motivated. The body, robe, wings, hands,
staff, feet, shadow, and contact remain stable throughout. The full silhouette
is uncropped with margins exceeding the contract. The browser canvas preserves
hard square pixel edges and the controls, diagnostics, status, and avatar do not
overlap.

## Acceptance Checklist

| Requirement | Decision | Evidence-backed observation |
| --- | --- | --- |
| Viewer-left-viewer eye choreography | **Pass** | Viewer fixation holds through frame 59, the eyes acquire viewer-left at frame 60, and return to the viewer at frame 120 without a body response or aperture escape. |
| Two-frame eye lead | **Pass** | Frames 186-187 show viewer-left eyes on the unchanged front head before the head begins following at frame 188. |
| Genuine authored three-quarter bridge | **Pass** | Frames 188-191 use authored `walk_front_left` head pixels while the body remains `front_idle`. The distinct brow, nose, beard, hat, and ear silhouette reads clearly at normal and quarter speed. |
| Profile arrival under blink | **Pass** | The turn blink begins on the three-quarter head at frame 191; profile first presents at frame 192 and remains closed through frame 193 before reopening at frame 194. |
| Visible settle | **Pass** | Profile arrives with a one-cell horizontal head offset at frames 192-196, recovers at frame 197, and reaches steady phase at frame 200. The recovery is readable without disturbing the body or prop line. |
| Natural listening breath | **Pass** | Five-frame one-cell head lifts occur at frames 13-17, 90-94, 157-161, and 234-238. Their sparse, uneven spacing reads as quiet breath/attention rather than a short mechanical loop. |
| Two naturally spaced blinks | **Pass** | Closed runs are frames 68-70 and 191-193, each 125 ms. Their measured onset interval is 5.126 seconds, inside the required 2.5-6.5-second range. |
| Stable planted performance | **Pass** | The planted anchor is constant at `(109.38, 125.695588...)`; maximum planted drift, planted raster-span drift, and root residual are all `0.0` cells. Visual inspection finds no robe, wing, hand, staff, foot, shadow, or contact jitter during head swaps. |
| Full canonical framing | **Pass** | Across all frames the intended silhouette occupies `x=79..160`, `y=20..126` on a `240x135` stage: 79 cells on each side, 20 above, and 8 below. This exceeds the 4-cell top/side and 6-cell bottom requirements. |
| Pixel-sharp browser layout | **Pass** | The browser uses a `960x540` canvas for `240x135` cells at DPR 1, exactly 4 device pixels per cell. The browser MP4 shows nearest-neighbor square edges, stable framing, no UI overlap, no decoded or dropped frames, and no page errors. |

## Timecoded Acting Notes

| Normal speed | Quarter speed | Atomic frames | Observation |
| ---: | ---: | ---: | --- |
| 0.000-2.458 s | 0.000-9.833 s | 0-59 | Calm viewer fixation. The brief lift at frames 13-17 keeps the face alive while the grounded silhouette remains still. |
| 2.500 s | 10.000 s | 60 | Eyes acquire viewer-left immediately and cleanly. The target is readable without overshoot, darting, or whole-body compensation. |
| 2.833-2.917 s | 11.333-11.667 s | 68-70 | First blink closes symmetrically for three frames and restores the held left target at frame 71. |
| 3.750-3.917 s | 15.000-15.667 s | 90-94 | A restrained attention lift breaks the hold without changing the stance or prop silhouette. |
| 5.000 s | 20.000 s | 120 | Eyes return to the viewer on the first presented frame; no stale left aim remains. |
| 6.542-6.708 s | 26.167-26.833 s | 157-161 | The third quiet lift continues listening presence without competing with the upcoming turn. |
| 7.500 s | 30.000 s | 180 | Automatic-gaze release is visually neutral. |
| 7.750-7.792 s | 31.000-31.167 s | 186-187 | Two-frame eye lead clearly establishes thought and destination before head motion. |
| 7.833-7.958 s | 31.333-31.833 s | 188-191 | The authored three-quarter head is held long enough to read as a bridge. It is not a front/profile dissolve or a locomotion-body substitution. |
| 7.958-8.042 s | 31.833-32.167 s | 191-193 | The second blink overlaps three-quarter departure and profile arrival, cushioning the change without hiding the already visible bridge. |
| 8.000-8.333 s | 32.000-33.333 s | 192-200 | Profile arrives with a one-cell offset, reopens at frame 194, recovers at frame 197, and becomes steady at frame 200. Normal speed reads as a controlled settle; quarter speed confirms the intended raster steps. |
| 9.750-9.917 s | 39.000-39.667 s | 234-238 | A final restrained profile lift keeps the endpoint attentive before the conclusion hold. |
| 9.958-12.000 s | 39.833-48.000 s | 239-287 | Stable two-second-plus conclusion hold. It reads as sustained listening, not dropped animation. |

## Applicable Scores

| Category | Weight | Score | Finding |
| --- | ---: | ---: | --- |
| Gaze and head-eye coordination | 12 | **4/4** | Targets, two-frame lead, authored bridge, blink-covered arrival, and settle form one coherent thought. |
| Blink | 8 | **4/4** | Two visible 125 ms closures are separated by 5.126 seconds and placed around attention and turn beats rather than a metronomic cadence. |
| Stillness | 10 | **4/4** | Sparse head-only modulation maintains presence while the body and props remain convincingly planted. |
| Framing | 10 | **4/4** | Silhouette is complete, balanced, grounded, and clear of every required boundary in atomic and browser presentation. |

Applicable weighted result: **40/40, normalized to 100/100**. Hand acting,
locomotion, interruption, reduced motion, and long-form repetition are not
scored because V1 does not exercise those scenario contracts.

## Evidence Notes

- The contact sheet includes cadence and exact transition samples, with frame,
  simulation tick, presentation time, scenario, sample reason, command ID,
  authoritative state SHA-256, and frame SHA-256 labels. It exposes the blink,
  three-quarter bridge, profile arrival, reopen, recovery, and steady settle.
- Browser metrics report 288/288 output frames, zero decoded/dropped/ignored
  frames, zero resyncs, and a final presented rate of 23.952 FPS against the
  24 FPS target. The visible browser layout remains stable and pixel-sharp.
- The browser-layout recording begins with a brief profile pre-roll from the
  preceding atomic endpoint before the replay reset reaches the canvas. This
  does not alter the atomic scenario, the page-layout proof, or the pixel-edge
  judgment, but future review recordings should trim or explicitly slate that
  pre-roll.
- The sole browser console event is a `favicon.ico` 404. It has no visible
  layout, animation, timing, or projection effect and is treated as non-visual
  infrastructure noise under the review instruction.

## Blocking Issues

**None for V1 Listening.** No clipping, anatomy break, planted drift, visual
overlap, missing transition, pixel-scaling defect, or evidence omission was
found in the reviewed package.

## V1 Acceptance

**ACCEPTED.** Candidate `8fb8c4b` satisfies the V1 listening animation and
visual-presentation requirements. This is one independent acceptance; the
aggregate release gate still requires the second independent review and does
not authorize advancement of unreviewed V2-V10 scenarios by itself.
