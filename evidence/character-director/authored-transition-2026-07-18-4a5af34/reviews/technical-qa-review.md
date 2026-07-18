# Independent Technical Animation QA Review

## Attribution and decision

- Reviewer: Codex (OpenAI), acting as independent technical animation QA reviewer
- Review date: 2026-07-18
- Candidate: `4a5af34bef9166e5ffe3fe9651aa7de50935bf9b`
- Evidence run: `authored-transition-2026-07-18-4a5af34`
- Supplied in README and independently verified manifest SHA-256: `9b62cf3967d5faa8c04e744977ab38ab75874016fbdee78c134af6c331892522`
- Comparison run: `transactional-head-eye-2026-07-18-e62ddae`
- Comparison review: `transactional-head-eye-2026-07-18-e62ddae/reviews/technical-qa-review.md`
- Rubric: `docs/character-director/VISUAL_PERFORMANCE_ACCEPTANCE_2026-07-17.md`
- Release decision: **REJECT / NOT RELEASE-ACCEPTABLE**
- Narrow regression decision: **PASS for removal of the demonstrated terminal reset displacement; PARTIAL PASS for reduced side-profile skating; no pass for planted-foot drift or general locomotion acceptance**

This package demonstrates two real improvements over the prior run. The speech interruption no longer resets the retained locomotion root to origin, and horizontal locomotion now presents a changing front-walk cycle instead of translating one side-profile raster for most of the travel. Those are useful regression results. They do not close the release gate: the package repeats the same short montage rather than V1-V10, carries no audio or real Prism/browser evidence, does not measure foot contacts or planted drift, and still shows abrupt stop, turn, and cast-recovery pose replacement.

## Review method

I verified repository provenance and commit ancestry, recomputed the manifest hash, checked every listed artifact byte length and SHA-256, checked all 341 wire records against `frames.bin`, and compared every wire index field to the corresponding manifest frame record. I inspected the 40 PNG samples and contact sheet, decoded dense one-frame MP4 sequences around walk start, reversal, stop, face turns, cast, and speech stop, and compared equivalent dense sequences from the prior MP4. I also examined command acknowledgments, response states, all 15 state snapshots, queue/drop/gap/decoder diagnostics, and frame-arrival cadence.

No evidence artifact or runtime source was modified. This review file is the only file added by this review.

## Claim verdicts

| Claim | Verdict | Evidence |
| --- | --- | --- |
| Terminal reset displacement is eliminated | **VERIFIED for this scripted speech-stop path** | The prior terminal `reset` changes authoritative `world_position.x` from `0.5028117517` to `0.0`; its visible sprite median shifts from about x=528 at sampled frame 319 to x=484 at frame 324, a 44-output-pixel displacement consistent with the reported screen-root change. The new command is `speech_stop`, and `world_position.x` remains `0.5006686019` through command response, after-ack snapshot, and capture end. Sampled frames 317, 324, and 336 retain the same sprite x position. |
| Side skating is reduced | **VERIFIED qualitatively, not quantitatively** | The prior frames 120, 132, and 144 translate the same narrow side silhouette while the root travels. The new dense frames 112-190 cycle through distinct front contact/lift/brace silhouettes, with clearly different sampled poses at 120, 132, 156, 168, 180, and 190. The old dominant side-raster slide is materially reduced. |
| Side skating is eliminated | **REJECTED / NOT PROVEN** | There are no per-frame contact labels, planted-foot anchors, or drift calculations. Some poses hold while the root continues to move, and the evidence cannot identify which foot is intended to be planted. The rubric's at-most-one-output-cell planted-drift threshold is untested. |
| Authored transitions are fully evidenced | **REJECTED** | Pixel sequences show more pose variety, but all command response states report transition phase `stable`, transition ID null, entry tick `0`, source contact `unknown`, and null source/target transition identifiers. Non-atomic snapshots frequently lag the acknowledgment state. The package does not expose a per-frame transition/contact/marker trace. |

The prior technical review's statement that frames 319-324 had no visible root/body jump was too generous. Direct comparison of the prior state and PNG evidence shows the reset displacement clearly. The new package fixes that exact defect by using `speech_stop`, not by making reset root-preserving.

## Provenance and integrity

Positive findings:

- Git object `4a5af34bef9166e5ffe3fe9651aa7de50935bf9b` exists, is the current `codex/character-director` HEAD, and is two commits after prior candidate `e62ddaef8dd9124e4591529e4fb694d93b541c4d`; the prior candidate is an ancestor.
- The manifest records the full candidate SHA, branch, no status lines, empty tracked-diff SHA-256, and `worktree_clean: true`. This supports a clean source worktree at capture time.
- All 44 manifest-listed artifacts match their recorded byte lengths and SHA-256 values.
- The wire index contains exactly 341 records, indices 0-340 without a gap. Offsets are contiguous and end exactly at byte 563,334, the length of `wire/frames.bin`.
- Every indexed wire slice matches its recorded SHA-256. Every `index.ndjson` field checked against the manifest frame record matches.
- All 40 sample records point to the matching manifest frame hash, and each PNG file is independently bound by its artifact hash.
- The MP4 probes as H.264 High, 960x540, 24 FPS, 341 frames, and 14.208333 seconds. Frame count, dimensions, and nominal rate agree with the manifest.

Limitations:

- The evidence directory is generated and currently untracked. The README supplies the manifest and primary-artifact hashes, and the manifest binds its listed children, but the README is itself unlisted, unsigned, and not externally anchored. This is a useful local integrity record, not a complete chain of custody.
- The README records the isolated Python visualizer address, candidate, and branch, but the package has no environment inventory, runtime executable/build hash, browser identity, or FFmpeg version record. `base_runtime: external` is not enough to reproduce the exact runtime environment.
- `source_epoch` value `visual-review-d5a6a414361c` is a run identifier, not a Git revision.
- `replay_exported` is false, so replay completeness and deterministic reproduction remain unverified.
- `frame_state_pairing` is explicitly `non_atomic_time_adjacent_observations`; clean provenance and artifact hashes do not establish an atomic command/state/wire/decoded/presented-pixel truth chain.

## Transport, decoder, and timing

- Manifest-level capture health is good: zero `dropped_frames`, zero `decoded_gaps`, zero `decoder_errors`, queue high-water mark 1 of 16, and zero queue overruns.
- State diagnostics peak at zero hub queue drops, zero slow subscribers, zero frame-hub failures, zero resyncs, and zero dropped frames. One stale-render discard is recorded from early in the run.
- The wire stream contains 303 codec-tag-2 records and 38 codec-tag-3 records. Decoder output has 118 distinct frame hashes; static holds account for many valid 13-byte deltas.
- Delivery is contiguous but not cadence-perfect. The 340 observed inter-frame intervals span 14.503 seconds, or 23.443 FPS actual average. Mean interval is 42.656 ms, p95 is 50 ms, p99 is 75 ms, and maximum is 84 ms. Eight intervals exceed 62.5 ms and one exceeds two nominal 24 FPS periods.
- Runtime `schedule_overruns` rises from 0 to 8. These overruns did not create index gaps, but the constant-24-FPS MP4 retimes the received frames and therefore masks actual arrival jitter. This is diagnostic-quality connected evidence, not strict proof of real-time 24 FPS performance.
- There is no audio stream. Decoder success cannot be used to infer AV synchronization.

## State and transition anatomy

All 13 commands have ordered source sequences, unique IDs, applied dispositions, no error code, and apply on the tick after acceptance. That is a sound command-ordering result. It is not a per-frame animation trace.

The snapshots expose the expected non-atomic race. For example, the walk-start response is revision/tick 287 and reports `ground_walk`, while the later after-ack snapshot is simulation tick 288 but state revision 286 and still presents `ground_idle`/`idle_front`. At stop, the command response reports `right_idle` at tick 497 while the later snapshot at tick 499 still reports the previous `ground_walk` presentation at revision 496. Similar facing/presented-facing lag appears on both face commands.

The response states do not retain useful transition anatomy: transition ID is null, phase is `stable`, entry tick is `0`, source pose is null, source contact is `unknown`, and target node/clip are null. Transition generations advance, but the skipped intermediate generations and absent per-frame records prevent verification of wait-gate, contact-match, handoff, or commit behavior. The visible raster is therefore the only evidence for most transition timing.

## Frame-specific findings

- **Frames 111-112, walk start:** frame 111 is still the prior front idle; frame 112 changes within one presented frame. Start response is prompt. The subsequent cycle is pose-authored rather than a static profile slide, but individual changes remain complete-raster swaps rather than interpolated weight transfer.
- **Frames 112-143, walk left:** the sprite alternates among front walk/contact/lift/brace shapes while moving left. This is a material improvement over prior frames 120-144, where the same profile silhouette translated. Staff, robe, wings, and legs now participate in the cycle. No contact label identifies the planted foot, so drift and alternation cannot be formally scored.
- **Frames 144-190, reversal:** the root continues left briefly after the reversal command and velocity magnitude decreases in the adjacent state observations before travel reverses. The body continues cycling front-walk poses instead of performing the prior rapid side-to-side whole-pose flip, which makes direction change less visually brittle. Frame 147 nevertheless flashes a complete back-facing raster between front-facing stride drawings, a one-frame facing discontinuity. Root/contact continuity across every frame is still not provable from the time-adjacent snapshots.
- **Frames 190-192, stop:** frame 190 is still a walk pose; frame 191/192 changes to a static right profile and then holds through frame 212. Authoritative velocity goes directly to zero at the stop apply tick. There is no evidenced deceleration, contact-resolution pose, robe/staff follow-through, or multi-frame settle. The stop remains abrupt.
- **Frames 211-213, face back:** the profile holds after the scenario boundary, then becomes the complete back raster at frame 213. The update is whole and untorn but still an atomic pose pop.
- **Frames 229-235, face front:** the back pose holds through frame 233, changes to profile at frame 234, and changes to front at frame 235. This two-frame back/profile/front sequence is coherent but too abrupt to establish a weighted 180-degree turn or eye-led head coordination.
- **Frames 249-265, cast:** effect pixels start at frame 249 while the body remains idle through frame 250. Prepare begins around frame 251, followed by readable stroke/overhead/guard poses. Frames 262-264 provide a clearer multi-frame low recovery than the prior run, which is an improvement. Frame 265 nevertheless replaces that guard with a complete idle raster in one frame, so the final settle still snaps.
- **Frames 265-281, effect tail:** the body is idle while the effect persists and decays. Without marker records, staff/hand anchors, or an effect lifecycle trace, effect onset and release remain visibly detached from authored body markers.
- **Frames 282-317, speaking:** body, prop, root, and wings remain stable while three mouth rasters cycle. This is coherent stillness over a short segment, but there is no audio and the duration is far below V2.
- **Frames 317-318, speech stop:** frame 317 retains the open-small mouth from speech; frame 318 is closed/neutral, after which the raster remains stable through frame 340. This is a one-presented-frame visual response with no stale mouth and no root displacement.

## Root continuity and whole-sprite integrity

The new run preserves the post-walk root at `world_position.x = 0.5006686019` across stop, face changes, cast, speaking, `speech_stop`, and capture end. Sampled speaking/interruption frames retain the same visible x coordinate. This verifies the narrow reset-displacement fix.

During walk and reversal, the available command/snapshot observations show continuous world positions rather than a teleport, and dense pixels show continuous stage travel. However, the package lacks per-frame authoritative root values and atomic frame pairing, so it cannot prove the one-cell root-jump limit at every transition. Stop motion is especially weak because velocity is set to zero immediately while the raster resolves by pose replacement.

Across all 40 supplied PNGs and dense transition decodes, the sprite remains complete, grounded, and uncropped. I found no half-updated body region, codec corruption, clipping, missing limb, mixed old/new sprite region, or obvious anatomy break. Ground contact stays within the raster with ample margins. The defects are coherent whole-sprite pose changes and motion mechanics, not transactional tearing.

## Interruption semantics

The revised final scenario proves one narrow behavior: targeted speech cancellation preserves world/root state, closes the mouth within one presented frame, clears `speech_id`, returns action to idle, and does not replay a stale speech mouth shape.

It does not exercise the rubric's interruption scenario. There is no cast interruption before commit, no cast interruption after commit, no replacement speech turn during either cast window, no stale-effect assertion, no recovery-time trace, and no root-jump measurement linked atomically to those frames. The package therefore does not score V7 and cannot support a general claim that interruption semantics are correct.

## Comparison with prior review

The prior review's renderer-coherence conclusion remains valid: both runs present complete rasters. The prior locomotion score of 1/4 can reasonably improve to **2/4 provisional** for this diagnostic material because the static side-profile slide has been replaced by a visibly varying front cycle and reversal no longer depends on a rapid mirrored side-pose flip. It cannot reach 3/4 without contact/drift measurements, a three-cycle front walk, decelerated stop, and the required turn matrix.

The prior hard blockers remain unchanged: non-atomic frame/state association, no replay, no browser/presented-pixel truth chain, no audio or synchronization timeline, and contact-sheet labels that contain only scenario/frame naming rather than tick, time, command, state hash, and frame hash. Most scored categories remain either provisional or not scored because this is the same short 13-command montage.

## Remaining evidence gaps and blockers

1. **P0 - Planted-foot drift:** provide per-frame left/right/both/air contact labels, foot anchor coordinates, atomic root coordinates, and drift calculations in output cells. Demonstrate alternating contacts and at most one-cell planted drift over three complete cycles, reversal, and stop.
2. **P0 - V1-V10 coverage:** capture the required durations, repetitions, turn matrix, cast interruptions, 60-second repetition scene, reduced/still modes, and desktop/mobile DPR framing passes as separate connected normal- and quarter-speed evidence.
3. **P0 - Real Prism AV:** record the actual Prism/browser presentation with its real audio output, audio artifact, media clock, mouth/phoneme or alignment timeline, AV offset measurements, browser console, layout bounds, and presented-pixel hashes. This silent generated MP4 cannot validate Prism AV.
4. **P0 - Atomic truth chain:** associate command acknowledgment, state revision/hash, transition/contact/marker state, wire sequence/hash, decoded buffer/hash, and real presented pixels on one frame-indexed timeline. Export and verify replay.
5. **P1 - Stop and turn mechanics:** preserve root/contact phase through a visibly decelerated stop; add contact resolution and robe/staff settle. Replace the frame-213 profile/back pop and frame-234/235 back/profile/front traversal with authored turn timing and eye/head lead where applicable.
6. **P1 - Cast lifecycle:** align effect onset with an explicit stroke/commit marker, provide prepare/stroke/hold/recovery durations and hand/staff anchors, and add a connected settle after the improved frames-262-264 recovery instead of the frame-264-to-265 idle snap. Then run both V7 interrupt windows.
7. **P1 - Capture cadence:** eliminate schedule overruns or preserve real presentation timestamps in playback so normal-speed review reflects actual timing rather than constant-rate retiming.
8. **P2 - Package chain of custody:** extend the README or add a signed outer record with environment/tool versions, runtime build hash, exact capture command, and an external anchor for the manifest and reviewer bindings.

## Final assessment

Candidate `4a5af34` is a meaningful diagnostic improvement over `e62ddae`: it removes the demonstrated terminal reset displacement and replaces most horizontal side-raster sliding with a varied front-walk cycle. Those claims are accepted only at that narrow scope.

Release acceptance remains rejected. Planted-foot behavior is unmeasured, stop and turn transitions remain abrupt, cast recovery still snaps, transition-state anatomy is not captured per frame, and the required V1-V10 and real Prism AV evidence are absent. This package should be retained as regression evidence for the two narrow improvements, not promoted as visual-performance acceptance evidence.
