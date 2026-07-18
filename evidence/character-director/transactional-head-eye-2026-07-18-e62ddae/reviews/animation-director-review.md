# Independent Animation Director Review

## Attribution and evidence binding

- Reviewer: OpenAI Codex, acting as supervising animation director
- Review date: 2026-07-18
- Review focus: acting, timing, silhouette, weight, gaze/head-eye, interruption, and appeal
- Candidate commit: `e62ddaef8dd9124e4591529e4fb694d93b541c4d`
- Evidence run: `transactional-head-eye-2026-07-18-e62ddae`
- Manifest SHA-256: `647e4e6743037198afa5dfba800304c30593b693227469b173534e5aa155aef2` (verified)
- Rubric: `docs/character-director/VISUAL_PERFORMANCE_ACCEPTANCE_2026-07-17.md`
- Independence statement: I did not author or modify the candidate runtime or retained capture artifacts. This review is based only on the immutable package named above.

## Materials inspected

- Full contact sheet and all 40 labeled PNG samples.
- The 342-frame, 960x540 H.264 MP4 and decoded native-frame sequences for close timing review.
- A locally derived quarter-speed MP4 and enlarged sequential frame strips; GUI playback did not complete before the review cutoff, so motion judgments below are grounded in exact frame order rather than a claim of completed interactive playback.
- Manifest, scenario ranges, command acknowledgments, state snapshots, wire index, continuity fields, and artifact hashes.

The manifest is internally valid and reports 342 contiguous frames at 24 FPS, no decoded gaps, no decoder errors, no dropped frames, and no queue overruns. It also explicitly describes frame/state pairing as `non_atomic_time_adjacent_observations`, has no audio artifact, and does not contain the rubric's full V1-V10 scenario matrix.

## Decision

**REJECT / not release-acceptable.** The run has hard failures in locomotion and interruption, and it omits required acceptance evidence. The visible work does demonstrate immediate bounded eye offsets, a readable cast silhouette, a valid-duration blink, and clean uncropped presentation, but it does not establish release-quality head-eye acting, weighted locomotion, or interruption continuity.

No rubric total is issued because reduced motion and repetition are unproven and several scored observations are only excerpts of the required scenarios. Treating absent scenarios as passing, or silently as zero, would both misrepresent this run.

## Category scores

Scores apply only to the behavior actually visible in this run. "Observed score" is not full-category acceptance where required duration or variants are absent.

| Category | Weight | Observed score | Weighted points | Director finding |
| --- | ---: | ---: | ---: | --- |
| Gaze and head-eye coordination | 12 | 2/4 | 6.0 | Left/right targets are readable and appear within the first evidenced frame, but both shifts are one-frame raster changes with no transition, head follow, or settle. The required 90-degree V1 head turn with visible eye lead is unproven. |
| Blink | 8 | 3/4 | 6.0 | One approximately three-frame blink (about 125 ms) is clean and does not disturb the body. Interval range, variation, and 60-second rhythm are unproven. |
| Hand acting | 14 | 2/4 | 7.0 | The single cast has a strong, legible silhouette and coherent two-hand staff grip. Its recovery is only about two frames before an idle pop; three casts, spacing consistency, and repeat appeal are unproven. |
| Locomotion | 18 | 1/4 | 4.5 | The side pose translates with feet and staff effectively frozen. There is no convincing alternating contact or weight transfer. Reversal anticipation is readable, but the flip and stop remain mechanical. |
| Stillness | 10 | 3/4 | 7.5 | Short idle and speech excerpts keep body and prop stable while the face changes. Listening presence is largely frozen, and the required 20/60-second ratios and two-second conclusion hold are unproven. |
| Interruption | 10 | 1/4 | 2.5 | The speech-to-reset transition removes the mouth state but also produces a large root/screen jump and an emotional idle snap. The required before/after-commit cast interruptions are unproven. |
| Reduced motion | 8 | Unproven | N/A | No full/reduced/still comparison is present. |
| Framing | 10 | 3/4 | 7.5 | The single desktop raster is uncropped, grounded, readable, and free of UI overlap. DPR1/DPR2, portrait DPR3, near/far/edge passes, and browser layout behavior are unproven. |
| Repetition | 10 | Unproven | N/A | The complete reel is about 14.25 seconds and contains only one cast and one short speech excerpt; V8's 60-second fatigue and exact-loop checks cannot be judged. |

Observed subtotal: **41.0 points across 82 evidenced weight points (50.0% normalized)**. This is diagnostic only, not the rubric's release score.

## Hard failures

1. **Planted drift / skating:** frames 120, 132, and 144 preserve essentially the same side-on leg and foot relationship while the entire character translates across the floor. The native sequence shows this over consecutive frames, exceeding the rubric's one-cell planted-drift tolerance and failing the alternating-contact requirement.
2. **Interruption root jump:** frame 319 is an open-mouth speaking pose at the prior screen/root location; by frame 324 the neutral idle is displaced roughly 50 output pixels, about 12 square cells. The manifest also changes world X from approximately `0.5028` to `0.0` on the reset. This exceeds the one-cell interruption limit and reads as a teleport.
3. **Missing required review evidence:** the run does not provide the required V1-V10 connected scenarios, normal- and quarter-speed review captures per scenario, audio/synchronization proof, reduced/still motion variants, responsive DPR variants, or 60-second repetition material. Contact-sheet labels include scenario and frame but omit tick, time, command, state hash, and frame hash. Under the rubric, missing review evidence is itself a hard failure.

No clipping or anatomy break was observed. No stale post-interruption cast replay was evidenced; the captured "speech-interruption" is a reset of speech, not the required V7 cast interruption.

## Frame-specific findings

- **Frames 0-24, front idle:** silhouette is attractive and easy to read, with clean staff and wing separation. The complete stillness over roughly one second reads more like held playback than attentive listening because there is no breath, weight adjustment, or gaze life.
- **Frame 26, gaze left:** pupils change immediately and remain inside the apertures. The target reads, but the change is a hard one-frame switch with no ease or micro-settle.
- **Frame 46, gaze right:** the eyes cross the full left-to-right distance in one frame. This is efficient but dart-like. The head and facial mass do not participate.
- **Frames 67-72, happy/blink:** expression onset is abrupt at frame 67. Frames 69-71 form a clean close/reopen blink of acceptable duration; its placement around the expression change feels motivated.
- **Frames 89-108, thinking:** thinking becomes readable by frame 96, but it is primarily a face substitution. The authoritative right gaze persists, weakening the sense of an internally motivated thought.
- **Frames 112-120, walk start:** the front pose begins moving before resolving rapidly to profile. There is little anticipation, compression, or first-step transfer, so the start feels commanded rather than chosen.
- **Frames 120, 132, 144, walk left:** robe, feet, hand, staff, and torso retain nearly identical relationships while screen position changes. This is clear skating, with no contact/passing rhythm and no staff counter-motion.
- **Frames 145-156, reversal:** the low crouch around frames 153-155 is the best piece of locomotion acting in the reel: direction change is readable and the silhouette broadens. The following profile flip arrives without a convincing planted pivot, so the anticipation does not pay off in weight.
- **Frames 192-204, stop:** frame 193 matches the preceding travel pose and the stopped pose then holds. There is no deceleration, overshoot, robe/wing drag, staff follow-through, or settle.
- **Frames 214-240, face back/front:** the facing changes are transactionally delayed rather than stale, but they resolve as discrete pose replacement. The front command's snapshot reports `head_eye_phase: leading` while the presented pose is still back-facing; because the eyes are not visible, this does not visually prove eye lead or head-eye coordination.
- **Frames 252-267, magic cast:** effects appear at frames 252-253 before the body commits. Prepare is readable for roughly five frames, the staff arc is broad and appealing, and the overhead silhouette is strong. Recovery at frames 265-266 is too short and frame 267 pops to idle, losing residual weight.
- **Frames 268-283, cast aftermath:** detached spark/ring pixels linger after the body has fully returned to idle. Even if intended as residue, they lack a clear decay relationship to the hand or staff and make the finish feel mechanically layered.
- **Frames 284-318, speaking:** mouth changes are readable and body/prop stillness is good for this short excerpt. There is no audio, so lip-sync cannot be judged. The long-held right gaze survives from frame 46 through later actions and makes the delivery feel side-focused and emotionally stale.
- **Frames 319-324, speech reset:** the open mouth closes and the expression clears, but the whole figure jumps left by many cells. This is both a technical discontinuity and an acting failure: the thought is cut off by a neutral reset rather than resolved.
- **Frames 324-341, post-reset:** the final hold is clean but under one second, too short to establish the rubric's two-second conclusion hold.

## Prioritized corrections

1. **P0 - Preserve root continuity on reset and interruption.** A reset must not restore world position while a visible turn is active. Interrupt speech or action in place, retain the current facing/root transform, and recover into the next intention over authored frames.
2. **P0 - Rebuild locomotion around contacts.** Author at least contact, down, passing, and up poses with alternating feet; lock the planted foot to the floor, move the root through that plant, and add robe, wing, and staff drag. Give starts, reversals, and stops explicit anticipation and settle.
3. **P1 - Make head-eye behavior visible and temporal.** Move eyes first, hold the lead for 1-4 frames, rotate the head/facing through readable intermediates, then settle the eyes. Clear or redirect stale authoritative gaze when expression, facing, speech target, or action intent changes.
4. **P1 - Lengthen cast recovery and bind effect timing to the gesture.** Keep at least three recovery frames, preserve staff momentum into the settle, and decay or terminate particles from the hand/staff action rather than leaving a detached loop.
5. **P1 - Capture the actual interruption contract.** Show cast interruption before commit and after commit, each followed by a new speech turn. Prove no stale stroke/effect, root jump no greater than one cell, and recovery within 12 frames.
6. **P2 - Produce the complete acceptance package.** Capture V1-V10 at 24 FPS, include ordinary and quarter-speed review, audio and synchronization records, 60-second blink/repetition scenes, reduced/still modes, responsive DPR passes, atomic or explicitly acceptable frame/state attribution, and fully labeled contact sheets.

## Supervising director note

The character has strong base appeal: the hat, beard, wings, robe stripe, and staff produce an unmistakable silhouette, and the cast poses show that broad graphic acting can work at this resolution. The current limitation is not recognizability; it is continuity. Eyes, body poses, translation, and reset state still behave like separately switched layers. Release quality will come from making those layers share one intention, one center of weight, and one finish.
