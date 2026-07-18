# Atomic Contact Lock `b7b6101` Technical Review

Date: 2026-07-18  
Reviewer: independent animation systems / production verification review  
Candidate: `b7b6101c86b6abd04622935331684b76e3ce8591`  
Evidence: `evidence/character-director/atomic-contact-lock-b7b6101-2026-07-18`  
Acceptance contract: `docs/character-director/VISUAL_PERFORMANCE_ACCEPTANCE_2026-07-17.md`

## Decision

**REQUEST CHANGES - not release evidence.** The candidate is a useful technical
checkpoint: this run has credible frame/hash/codec pairing, contiguous transport,
transactional stale-candidate rejection, and a materially better planted-root
implementation. It does not satisfy the release contract. The bounded acceptance
score is **42/100**, with several required categories unproven and therefore scored
zero rather than inferred.

## Findings

### HIGH - External runtime is not bound to the recorded Git candidate

The manifest records a clean worktree at `b7b6101`, but also declares
`base_runtime: external`. It records neither the server launch command, executable
identity, process identity, isolated port, nor a runtime-reported build digest.
Consequently the evidence proves which checkout ran the harness, not that the
external server producing frames was built from that checkout. This breaks the
contract's immutable candidate-to-run provenance chain. The commit is pushed on
`origin/codex/character-director`, but that fact does not close the runtime gap.

### HIGH - The planted-contact verifier does not prove visible raster contact

`wizard_avatar/contact_verifier.py:134-151` compares the declared continuous
`planted_anchor_stage` against its first value for each contact generation. That
coordinate and the contact correction originate from the same transform path. The
verifier does not inspect `planted_anchor_raster_span`, confirm a colored foot cell
exists in the decoded frame, compare raster spans over the stance, or enforce
left/right alternation. Its two tests only prove a normal generated trace passes and
a synthetic `+2.0` change to the same declared stage coordinate fails.

The archived trace is encouraging: all 302 contact frames include raster spans,
the walking segment visibly alternates left/right support, and declared drift is
`1.42e-14` cells. The report's `passed: true` nevertheless proves mathematical
self-consistency, not the acceptance contract's visible output-cell foot lock. This
remains a contact truthfulness blocker.

### HIGH - Cast markers are absent from the accepted 24 FPS trace

All 17 published `cast_front` records (frames 250-266) have empty
`active_markers`, including authored frames 6, 7, 14, and 17 where the graph defines
`action_commit`, `action_effect`, `action_recoverable`, and `action_settled`.
Markers are transient simulation-tick events and can be cleared before a 24 FPS
presentation sample is captured. The effect still starts at authored frame 7,
holds through 13, decays at 14 and 16, and is absent at 17; however, the evidence
cannot prove ordered marker/effect causality as required for V3/V7.

### HIGH - This package is not the required V1-V10 acceptance matrix

The video is a valid 340-frame, 14.17-second, 24 FPS H.264 stream, but the package
contains 13 short diagnostic scenarios rather than V1-V10. It has no real-browser
recording, audio/synchronization timeline, quarter-speed renders, reduced/still
motion passes, 60-second repetition scene, DPR/mobile framing matrix, or two bound
independent reviews. Contact-sheet labels identify scenario and frame only, not
tick, time, command, state hash, and frame hash. The manifest may truthfully call
this capture lossless, but `valid: true` must not be interpreted as release-valid.

### MEDIUM - Slow-subscriber overflow still creates subscriber-local transport truth

Explicit resync is improved: `wizard_avatar/stream.py:213-226` clears stale deltas
and forces the next globally committed publication to be a keyframe, and
`wizard_avatar/stream.py:549-565` updates the accepted trace with that forced
transport. In contrast, queue overflow at `wizard_avatar/stream.py:743-754`
re-encodes `_latest_frame` directly for one subscriber after clearing its queue.
That replacement message is not represented by a corresponding amended atomic
trace record. The external harness should detect the resulting gap or codec/hash
disagreement and fail closed, but the runtime trace is not universally one
transport record per delivered message. No new test covers overflow plus trace
pairing.

### MEDIUM - Reversal is logically improved; stop and cast still pop visually

The reversal trace stays in `ground_walk` / `walk_front` while horizontal velocity
changes direction, avoiding the previous accidental back-walk family. Declared
support alternates and contact correction releases by at most one stage cell per
presented frame.

The contact sheet and frame trace still show atomic silhouette changes rather than
authored in-betweens. The stop moves from `walk_front_right_lift` to
`walk_front_left`, `walk_front_right`, `front_idle`, and `profile_right` over frames
197-207. The cast jumps its staff tip from approximately `(101,33)` to `(164,55)`,
then `(100,67)`, back to `(101,33)`, and later `(113,54)`. These discontinuities
exceed the acceptance intent for hand/staff continuity and read as pose pops at
normal speed. Contact locking prevents foot skate but does not itself provide
weight, anticipation, arcs, or follow-through.

### LOW - Accepted stale-frame handling is sound for the covered path

`wizard_avatar/stream.py:510-565` checks authoritative state and permission-world
signatures before committing, rejects generation conflicts transactionally, forces
a later keyframe, and appends trace only after acceptance. The focused stale-worker
test confirms a blocked obsolete candidate is absent from the published trace. The
evidence is contiguous from frame 0 through 339 with no queue overrun, decoder
error, duplicate, or dropped frame. Residual coverage is limited to one stale-state
mutation; permission-policy races and sustained stale-render pressure are not
demonstrated here.

## Positive Verification

- `tools/run_character_director_visual_review.py:550-589` pairs every captured
  frame by frame index, decoded-frame SHA-256, and codec tag.
- All 340 wire records and all 340 trace records cover frame indexes 0-339 without
  gaps or duplicates; trace `encoded_size` matches every archived wire message.
- Queue high-water mark is 1/16, with zero harness overruns and zero dropped frames.
- Artifact byte counts and SHA-256 values are recorded, the worktree provenance is
  clean, and the exact commit is present on the pushed remote branch.
- The supplied contact sheet and MP4 are consistent with the trace's major pose
  changes; no silhouette crop is visible in this desktop raster capture.

## Acceptance Score

| Category | Score (0-4) | Weighted | Basis |
| --- | ---: | ---: | --- |
| Gaze/head-eye | 2 | 6.0/12 | Short left/right checks only; no required head turn or latency proof |
| Blink | 0 | 0.0/8 | Required blink timing/variation absent |
| Hand acting | 2 | 7.0/14 | Cast phases exist, but markers are absent and staff discontinuities pop |
| Locomotion | 2 | 9.0/18 | Better support/root logic; visible raster lock and authored stop quality unproven |
| Stillness | 2 | 5.0/10 | Short speech excerpt only; no measured body-still ratio or conclusion hold |
| Interruption | 1 | 2.5/10 | Speech stop shown; required pre/post-commit cast interruption absent |
| Reduced motion | 0 | 0.0/8 | Full/reduced/still comparison absent |
| Framing | 4 | 10.0/10 | Desktop evidence is uncropped and balanced; DPR/mobile matrix still absent |
| Repetition | 1 | 2.5/10 | No 60-second repetition test or loop analysis |
| **Total** |  | **42/100** | Release requires at least 85, every category at least 3, and no blocker |

## Residual Risks

- A stale or differently configured external server could reproduce this manifest
  while the harness checkout still reports `b7b6101`.
- The contact gate can pass internally consistent but visually wrong anchor data.
- Marker loss between 60 Hz simulation and 24 FPS presentation can conceal ordering
  defects and makes cast interruption evidence non-attributable.
- Subscriber overflow remains a liveness recovery path outside the global atomic
  publication record.
- Full-sprite pose changes can satisfy hashes and contact math while still failing
  weight, anatomy continuity, acting clarity, and normal-speed appeal.

## Release Recommendation

Do not release or count this package as a completed visual-performance gate. Retain
`b7b6101` as a checkpoint for atomic accepted-frame tracing and contact-correction
work. Before re-review: bind a harness-owned runtime to a reported candidate digest;
verify raster/pixel contacts and alternation; preserve marker events until presented;
remove subscriber-local untraced resync transport; author smoother stop/cast
transitions; and capture the complete V1-V10 matrix with browser, AV, reduced-motion,
quarter-speed, labeled evidence, and two independent manifest-bound reviews.
