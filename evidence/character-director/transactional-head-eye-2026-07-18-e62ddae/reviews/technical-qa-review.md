# Independent Technical Animation QA Review

## Attribution and decision

- Reviewer: Codex (OpenAI), acting as independent technical animation QA reviewer
- Review date: 2026-07-18
- Candidate: `e62ddaef8dd9124e4591529e4fb694d93b541c4d`
- Evidence run: `transactional-head-eye-2026-07-18-e62ddae`
- Supplied and verified manifest SHA-256: `647e4e6743037198afa5dfba800304c30593b693227469b173534e5aa155aef2`
- Rubric: `docs/character-director/VISUAL_PERFORMANCE_ACCEPTANCE_2026-07-17.md`
- Decision: **REJECT / NOT RELEASE-ACCEPTABLE**

The capture is useful diagnostic evidence for transactional raster presentation, but it is not the required visual-performance acceptance package. Visible frames are coherent and untorn, while authored motion still contains pose swaps, skating, weak recovery, and no demonstrated head-eye turn coordination. Required scenarios and truth-chain records are also missing.

## Review method

I inspected the supplied contact sheet, representative individual PNG samples at original resolution, the manifest and wire index, and dense one-, two-, and three-frame interval decodes from the MP4 around every important transition. The MP4 is H.264, 960x540, 24 FPS, 342 frames, 14.25 seconds, with no audio stream. A quarter-speed derivative was prepared outside the immutable run, but live-player review was interrupted; frame-by-frame MP4 decodes were used for slow-motion continuity judgment instead. No evidence files or runtime code were modified.

## Hard failures and blockers

1. **Hard failure: missing review evidence.** The rubric requires connected normal-speed and quarter-speed evidence for V1-V10. This run is one 14.25-second montage of 13 short commands. It does not contain the required 12 s listening, 20 s governed speech, repeated casts, explain/hold/point sequence, three-cycle front walk, specified turn matrix, cast interruptions before and after commit, 60 s repetition scene, reduced/still modes, or DPR/portrait framing passes.
2. **Truth-chain blocker.** The manifest explicitly declares `frame_state_pairing` as `non_atomic_time_adjacent_observations`; it does not establish atomic command/state/wire/decoded/presented-pixel association. `replay_exported` is false.
3. **Browser and synchronization blockers.** There is no real-browser recording or browser console/layout record, and the video has no audio stream or AV synchronization timeline. Governed speech and lip-sync therefore cannot pass.
4. **Contact-sheet attribution blocker.** Labels identify scenario and frame only. They omit tick, time, command, state hash, and frame hash required by the rubric.

No clipping or anatomy break was seen in the supplied frames. A planted-drift hard failure cannot be formally measured because contact labels/measurements are absent, although the visible locomotion strongly reads as skating. Reduced-motion scenery/body behavior and stale post-cast-interruption action are untested.

## Category scores

Scores are provisional and apply only to material actually shown. `N/S` means not scored because the required behavior is not evidenced; it is not an inferred zero.

| Category | Score | Evidence-based finding |
| --- | ---: | --- |
| Gaze and head-eye coordination | **2/4** | Left/right eye targets are readable and remain in the aperture, but changes are single-frame swaps followed by static holds. No evidenced 90-degree turn shows eyes leading the head by 1-4 frames, and there is no authored settle. |
| Blink | **N/S** | No identifiable blink event, duration, interval series, or 60 s rhythm evidence. |
| Hand acting | **2/4** | One cast has readable crouch, reach, overhead silhouette, and effect, but it is not repeated three times and has no marker/anchor measurements. Recovery returns to idle in one frame, and effect timing is poorly tied to the body action. |
| Locomotion | **1/4** | Start and reversal respond, but the side silhouette translates for long spans with little or no alternating contact action. Reversal is a rapid whole-pose turn and stop freezes the current side pose without a visible decelerated settle. |
| Stillness | **3/4 provisional** | During the brief speaking segment the body and prop remain stable while the mouth changes, which is visually coherent. The segment is only about 1.4 s, has no audio, and cannot prove the 70% speech ratio or 2 s conclusion hold. |
| Interruption | **N/S** | Only a reset after brief speech is shown. V7 cast interruption before and after commit, stale-effect suppression, interrupt windows, and measured recovery are absent. |
| Reduced motion | **N/S** | No full/reduced/still comparison is present. |
| Framing | **3/4 provisional** | The 960x540 raster remains uncropped, grounded, and balanced with ample top/side space in the shown pass. Browser layout, DPR1/2/3, edge/near/far, and 390x844 behavior are absent. |
| Repetition | **N/S** | The 14.25 s run contains one cast and no 60 s repeated-phrase scene, so loop fatigue and gesture recurrence cannot be judged. |

Provisional scored subtotal: **32.5 / 64 weighted points available**, or **50.8/100 normalized across only the five scored categories**. This is not an acceptance score: four categories are unscored, and the release gate requires every category to score at least 3 plus at least 85/100 overall.

## Frame-specific findings

- **Frames 24-26, gaze left:** neutral hold changes to the left-eye raster at frame 26 without visible anticipation. The head and body remain unchanged through the rest of the left-gaze range.
- **Frames 45-46, gaze reversal:** gaze switches directly from left to right at the scenario boundary. The target reads, but the one-frame reversal has no eye easing, head follow, or settle and feels mechanical.
- **Frames 112-116, walk start:** frame 112 still presents the prior front pose; the renderer then replaces the full front silhouette with a side walk silhouette over only a few frames. Staff, wings, robe, and feet change together rather than resolving as a weighted start.
- **Frames 120-144, walk left:** the root travels while the side pose is nearly static. There is no convincing alternating foot contact, robe cadence, staff follow-through, or transfer of weight; visually this is skating.
- **Frames 145-151 and approximately 154-156, reversal:** the old side silhouette persists after the scenario boundary, then the body executes a very short wholesale turn into the mirrored side pose. The directional change is readable but lacks anticipation and continuous foot/root mechanics.
- **Frames 192-204, stop:** frame 193 is pixel-identical in decoded content to frame 192, and sampled frame 204 remains the same stopped raster. There is no root pop, which is good, but there is also no deceleration, contact resolution, robe/staff follow-through, or authored settle.
- **Frames 214-216, face back:** the side pose holds through frame 215 and becomes a complete back pose at frame 216. This is a clean transactional frame with no tearing, but a conspicuous atomic pose pop.
- **Frames 236-238, face front:** back, side, and front silhouettes are traversed in roughly two frames. Renderer coherence is maintained, but the timing is too abrupt to read as a weighted 180-degree turn or head-eye coordinated action.
- **Frames 252-266, cast:** effect pixels appear while the body is still idle at frames 252-253. The body then moves through crouch/reach/overhead poses, but recovery goes from a diagonal staff/body pose around frame 265 to front idle at frame 266. That one-frame recovery is the strongest hand-acting continuity defect.
- **Frames 266-284, effect tail:** the body is idle while the small cyan/orange effect remains visible through the remainder of the cast and into the speech boundary. Without marker records this cannot be called stale action, but the effect lifecycle reads detached from prepare/stroke/hold/recovery.
- **Frames 284-318, speaking:** body, wings, root, and staff remain stable while mouth shapes alternate. This is the cleanest shown behavior, but absent audio and a longer governed-speech capture it proves neither AV timing nor sustained stillness quality.
- **Frames 319-324, speech reset:** the mouth closes and the character returns to neutral without a visible root/body jump. This supports a narrow speech-reset continuity claim only; it does not evidence rubric scenario V7.
- **All shown frames, renderer coherence:** complete rasters are presented without half-updated body regions, tearing, crop, or codec corruption. The continuity defects are coherent whole-pose changes, not mixed-frame rendering artifacts.

## Evidence sufficiency

Positive evidence facts: the manifest hash matches the supplied value; provenance binds the run to the full candidate commit on `codex/character-director` with a clean captured worktree; the wire index contains contiguous frame indices 0-341; the manifest reports no decoded gaps, decoder errors, dropped frames, or queue overruns; and MP4 frame count/rate agree with the manifest capture count.

Unproven acceptance facts: atomic frame/state association, presented real-browser pixels, browser layout/scaling and console health, audio/lip-sync, blink timing and variation, contact alternation and planted drift, target error, cast markers and anchors, interruption before/after commit, reduced/still suppression, 60 s repetition behavior, multi-DPR/mobile framing, and normal/quarter-speed evidence per required scenario.

## Prioritized corrections

1. **P0 - Replace translation-only locomotion with contact-authored cycles.** Show alternating planted contacts, constrain planted drift, preserve phase through reversal, and add decelerated stop plus robe/staff follow-through. Capture contact labels and measurements so the skating observation can be resolved quantitatively.
2. **P0 - Produce a rubric-complete immutable run.** Capture V1-V10 separately at connected 24 FPS with normal and quarter-speed videos, required durations/repetitions/modes/viewports, audio and AV timeline, real-browser recording, and labels containing scenario/frame/tick/time/command/state hash/frame hash.
3. **P0 - Complete the truth chain.** Bind acknowledgment, state revision/hash, original wire bytes, decoded buffer/hash, and presented browser pixels atomically on one timeline; export replay and fail closed on any mismatch.
4. **P1 - Execute authored transition intent instead of whole-pose replacement.** Add anticipation and multi-frame root/contact continuity for starts, 180-degree reversal, side/back/front turns, and stop settle while retaining transactional presentation.
5. **P1 - Author head-eye behavior.** Add two observable blinks to V1, eye lead on turns, controlled head follow, and 2-4-frame settles; vary blink timing in V2/V8 and preserve mouth/blink independence.
6. **P1 - Repair cast phase and effect timing.** Keep prepare/stroke/hold/recovery durations and hand/staff anchors measurable, remove the one-frame frame-265-to-266 recovery snap, and couple effect onset/release to explicit markers. Then demonstrate three casts and both V7 interruption windows.
7. **P2 - Verify accessibility, repetition, and framing.** Add full/reduced/still comparisons, a 60 s loop/repetition analysis, and browser captures for DPR1/DPR2 plus 390x844 DPR3 edge/near/far passes.

## Final assessment

Candidate `e62ddae` appears to improve transactional renderer coherence: every observed update is a complete, internally consistent frame. That property does not make the animation performance acceptable. The current evidence shows atomic pose changes where authored transitions are needed, locomotion without convincing contacts, and a cast recovery pop, while most of the acceptance matrix remains unproven. The run must not be used as release acceptance evidence.
