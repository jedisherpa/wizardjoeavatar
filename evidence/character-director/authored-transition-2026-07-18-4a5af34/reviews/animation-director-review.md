# Independent Animation Director Review

## Attribution and evidence binding

- Reviewer: OpenAI Codex, acting as independent supervising animation director
- Review date: 2026-07-18
- Candidate commit: `4a5af34bef9166e5ffe3fe9651aa7de50935bf9b`
- Evidence run: `authored-transition-2026-07-18-4a5af34`
- Manifest SHA-256: `9b62cf3967d5faa8c04e744977ab38ab75874016fbdee78c134af6c331892522`
- Comparison review: `transactional-head-eye-2026-07-18-e62ddae/reviews/animation-director-review.md`
- Rubric: `docs/character-director/VISUAL_PERFORMANCE_ACCEPTANCE_2026-07-17.md`
- Independence statement: I did not author or modify the candidate runtime or retained capture artifacts. I wrote only this review, based on the immutable package above.

## Materials inspected

- `manifest.json`, including provenance, ordered command acknowledgments, scenario ranges, state snapshots, frame records, queue/decoder facts, and artifact hashes.
- The complete 341-frame, 960x540, 24 FPS H.264 capture at native frame order, plus locally derived sequential frame strips for start/cycle/reversal/stop, face turns, cast, speech, and interruption.
- The full contact sheet and all 40 labeled samples, with close inspection of the locomotion, cast, and interruption samples.
- `wire/index.ndjson` and the manifest frame index for continuity; all 341 indexes from 0 through 340 are present.
- `wire/frames.bin` and every retained artifact checksum. All 44 manifest-listed artifacts verify.
- The prior independent rejection for candidate `e62ddaef8dd9124e4591529e4fb694d93b541c4d`.

The capture is valid as a lossless decoded-cell recording: no index gaps, decoder errors, dropped frames, or queue overruns are reported. The clean provenance points to the candidate commit. Frame/state observations remain explicitly non-atomic, and the package has no audio.

## Decision

**REJECT / not release-acceptable.** This is a material improvement over the prior rejected run, especially in the presence of authored locomotion drawings, cast recovery, and root-preserving speech interruption. It is not an acceptance pass. The locomotion drawings do not yet connect into a coherent weighted start, cycle, reversal, and stop; the reversal contains a one-frame facing discontinuity; and required release evidence remains absent.

No full rubric score is issued. Reduced motion and repetition are not visibly evidenced, and the run is not the required V1-V10 matrix. The numeric result below is normalized only across categories visibly observed in this package.

## Observed category scores

| Category | Weight | Prior observed | Current observed | Weighted points | Director finding |
| --- | ---: | ---: | ---: | ---: | --- |
| Gaze and head-eye coordination | 12 | 2/4 | 2/4 | 6.0 | Targets remain readable and bounded, but left and right are still hard raster switches. Face turns do not show eye lead, head follow, or settle, and the authoritative right gaze persists through later intentions. |
| Blink | 8 | 3/4 | 3/4 | The same clean, approximately three-frame blink is visible. Long-form interval variation is not evidenced. |
| Hand acting | 14 | 2/4 | 3/4 | Prepare, stroke, overhead hold, and a three-frame recovery now read as distinct phases with strong staff silhouettes. Early effect onset, long detached residue, and the absence of three repeated casts prevent release quality. |
| Locomotion | 18 | 1/4 | 2/4 | Distinct stride and compression drawings replace the prior frozen-profile skate, but lateral travel stays front-facing, the low guard reads as an action pose rather than a passing/contact pose, feet are not convincingly planted, reversal flashes to back for one frame, and stop snaps to profile idle. |
| Stillness | 10 | 3/4 | 3/4 | Short speech and post-interruption holds keep body and prop stable. Listening life and the required two-second conclusion hold are absent. |
| Interruption | 10 | 1/4 | 3/4 | The prior many-cell reset teleport is fixed: speech closes in place between frames 317 and 318 and the root remains stable through frame 340. The acting is still a one-frame mouth cut with no visible interruption reaction or emotional settle. |
| Framing | 10 | 3/4 | 3/4 | The character remains uncropped, grounded, and readable at the one captured desktop raster. Required responsive/DPR passes are absent. |

Observed subtotal: **54.0 points across 82 visibly evidenced weight points, or 65.9% normalized**. This is a diagnostic comparison, not a release score. The prior run normalized to 50.0% over the same evidenced weight.

## P0 release blockers

1. **P0 - Locomotion continuity is still below acceptance.** The start moves directly from idle at frame 111 into a frontal stride at frame 112 without anticipation. Frames 112-143 cycle among stride, neutral, and a two-hand low guard; the guard silhouette is appealing but does not describe a clear passing/contact phase. During reversal, frame 147 flashes to a back-facing raster between frontal stride drawings, then frames 148-189 continue lateral travel mostly facing the viewer. At stop, frame 190 is still a frontal traveling stride and frame 191 is already a static right-profile idle. There is no readable deceleration, planted pivot, overshoot, prop drag, or settle. This is improved drawing coverage, not yet a weighted locomotion system, and a 2/4 category cannot pass the rubric's every-category-at-least-3 gate.
2. **P0 - Required review evidence remains missing, which the rubric defines as a hard failure.** This 14.21-second reel is not the connected V1-V10 matrix. It lacks three casts, cast interruptions before and after commit, audio/synchronization proof, 20/60-second behavior, reduced/still variants, responsive DPR passes, real-browser layout proof, and per-scenario normal/quarter-speed review. Contact-sheet labels identify scenario and frame but omit tick, time, command, state hash, and frame hash. Non-atomic state observations also cannot prove exact contact, marker, or interruption measurements.

No clipping or anatomy break was observed. The prior interruption root jump is no longer present, and no stale post-speech-stop action is visible.

## P1 animation issues

1. **P1 - Author the reversal around a planted decision.** Remove the frame-147 back flash. Show braking compression, a readable contact, center-of-weight transfer, stepped facing change, then acceleration in the new direction while preserving cycle phase.
2. **P1 - Replace pose substitution with locomotion contacts.** Use recognizable contact, down, passing, and up relationships with alternating feet. The two-hand staff guard can be retained as an anticipation accent, but it should not occupy the passing beat. Add robe, wing, and staff lag so the prop and costume participate in momentum.
3. **P1 - Give starts and stops their own timing.** The start needs intent/compression before root travel. The stop needs deceleration, a final plant, small overshoot, and settle instead of the frame-190-to-191 frontal-stride/profile-idle cut.
4. **P1 - Make face turns acted transitions.** Face-back replaces the held profile with back at frame 213. Face-front holds back through frame 233, passes through profile for only frame 234, and is front by frame 235. Preserve the side intermediary for several frames, lead with visible eyes where possible, and let hat, beard, wings, and staff settle after the torso.
5. **P1 - Coordinate gaze with intention.** The left target appears at frame 26 and the full left-to-right eye move occurs at frame 46, both as hard switches. The right gaze then survives happy, thinking, locomotion, cast, speech, and interruption. Redirect or release authoritative gaze at thought/action boundaries and add a short lead and settle rather than a perpetual side stare.
6. **P1 - Bind cast effects to the body phrase.** Effects begin at frames 249-250 while the body is still idle; the preparation becomes visible around frame 251. The broad stroke and overhead hold are strong, and recovery is now readable at frames 262-264, but the body is idle by frame 265 while detached effect pixels persist through frame 280. Start the effect at commit/stroke and decay it from the staff path through recovery.
7. **P1 - Add interruption acting after preserving continuity.** The technical fix is good: frame 317 speaks, frame 318 closes, and position/facing remain stable. Add a small breath catch, eye response, or thought settle without disturbing the root. Extend the final hold from roughly 23 frames to the required two seconds.

## Frame-specific comparison

- **Frames 0-110:** idle, gaze, blink, happy, and thinking behavior is effectively unchanged from the prior rejection. Silhouette remains clean and appealing, but gaze changes are abrupt and the thinking/right-gaze combination becomes stale.
- **Frames 111-143, walk start/cycle:** unlike the prior frozen profile, the candidate supplies multiple authored poses and visible foot separation. The strongest low pose at frames 129-133 is readable as bracing or guarding, not as weight passing over a planted foot; cadence therefore feels like action-pose alternation rather than walking.
- **Frames 144-189, reversal:** the prior run had a readable crouch but no convincing pivot. The new run has more continuous raster change, yet frame 147 introduces a back-facing flash and the remaining motion returns to frontal stride/guard cycling. Direction changes in screen travel, but the body does not perform the turn.
- **Frames 190-210, stop:** root travel ceases without the prior reset teleport, but the frontal stride-to-profile-idle cut at frames 190-191 is a visible pose pop. Frames 191-210 are a clean hold, not a stop recovery.
- **Frames 211-248, turns:** silhouette directions are unambiguous, but transitions are discrete replacements. The single-frame profile bridge on the return is useful evidence of intended sequencing, not yet convincing turn acting.
- **Frames 249-281, cast:** this is the clearest improvement. The crouched prepare, diagonal stroke, overhead hold, and low recovery create a strong graphic phrase; recovery no longer collapses after two frames. Premature and detached effects weaken causality and finish.
- **Frames 282-316, speech:** mouth variation is readable and body/prop stillness is stable. With no audio, lip-sync cannot be judged. The unchanged right gaze and thinking expression make the line feel emotionally preselected rather than responsive.
- **Frames 317-340, speech interruption:** the prior run jumped the root and reset to a different emotional idle. This run keeps root, facing, thinking expression, and gaze continuous while closing the mouth in one frame. That is a substantial technical continuity fix; it still needs an acted interruption beat and a longer conclusion hold.

## Supervising director note

The authored-transition work is going in the right direction. The character now has enough strong drawings to support appealing motion, and the cast demonstrates that prepare/stroke/hold/recovery can read at this resolution. The remaining problem is connective performance: locomotion poses must share one center of weight and one facing intention, turns must be visible actions rather than raster swaps, and effects/gaze must release when the body's thought releases. Approve another iteration, not release.
