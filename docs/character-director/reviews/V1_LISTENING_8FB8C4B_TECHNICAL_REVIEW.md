# V1 Listening `8fb8c4b` Technical/Evidence Review

**Verdict: ACCEPTED**

**Reviewer role:** fresh independent technical/evidence reviewer  
**Candidate:** `8fb8c4b80031a0500202a67e8beb70a16c8a0a1c`  
**Candidate tree:** `0b83c1933028af0592f2430e0086ecd724dfb2d4`  
**Evidence package:** `evidence/character-director/v1-listening-8fb8c4b-2026-07-18/`  
**Capture manifest SHA-256:** `451b60751e083cde4f86dd9821128b6e3b50888c13d3b83a5da0262e02570f1c`

## Decision

The immutable package is technically sufficient to proceed to independent V1
visual acceptance. The source/runtime chain is attributable, the exact capture
is lossless and atomically paired with authoritative animation truth, the
browser replay proves the real Chrome layout and canvas presentation, and the
machine, contact, framing, and timing gates pass. Direct inspection of the
normal-speed video, quarter-speed derivative, browser-layout video, contact
sheet, blink sequences, and head-turn sequence found no technical blocker.

This acceptance is limited to V1 Listening and does not approve V2-V10 or the
overall Character Director release.

## Provenance And Runtime Binding

- The capture began on branch `codex/character-director` at the exact candidate
  commit and tree above. The recorded initial Git status and tracked diff are
  empty, with SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- The candidate commit is the worktree `HEAD`; no tracked worktree difference
  was present during this review.
- The harness-owned Python 3.9.6 runtime was launched from the candidate
  worktree on isolated port `8896` by
  `tools/run_wizard_avatar_server.py`. Start and end identities retain the same
  commit, tree, launcher hash, process epoch, render geometry, and PID.
- The runtime end identity lists only the evidence files being created under
  this package. Its tracked-diff hash remains empty. This is expected capture
  output, not source drift.
- The capture manifest's built-in semantic validator and review-bundle
  validator both replayed successfully against the immutable files.

## Exact Capture Integrity

- The exact capture contains **288 owned frames**, indexed contiguously from
  `0` through `287`, with presentation indexes `0` through `287` and no
  unowned spill.
- Five acknowledged windows contain exactly `60 + 60 + 60 + 6 + 102 = 288`
  frames in the declared scenario order.
- All five ordered commands have unique IDs, contiguous source sequences, an
  `applied` acknowledgment, accepted/apply ticks, response state, and an
  adjacent diagnostic snapshot. No command reports an error.
- Dropped frames: **0**. Decoded gaps: **0**. Decoder errors: **0**. Queue
  overruns: **0**. Queue high-water mark: **1 of 16**.
- The wire index covers `frames.bin` with contiguous byte ranges and no
  trailing bytes. Independent semantic replay verifies every wire SHA-256,
  codec tag, decoded index, decoded byte length, decoded SHA-256, and FNV-1a
  hash.
- Every decoded frame is paired by frame index, codec, encoded size, decoded
  frame SHA-256, and authoritative state SHA-256 with one
  `animation_truth_trace_v1` record. Coverage is **288/288**; there are 288
  distinct authoritative state hashes.

## Contact, Framing, And Timing

- Recomputed strict raster contact verification passes all 288 frames with
  planted drift `0.0` cells, planted raster-span drift `0.0` cells, and root
  residual `0.0` cells.
- Presented root remains exactly `(120.0, 126.82058823529412)` and the planted
  anchor remains exactly `(109.38, 125.69558823529412)` throughout the run.
- Render scale is fixed at `1.125`. Across all frames the silhouette occupies
  `x=79..160`, `y=20..126` in the `240x135` raster. Minimum margins are 79
  cells left, 79 right, 20 top, and 8 bottom, exceeding the V1 requirements of
  4 top/side and 6 bottom.
- Two visible three-frame blink closures are present. Each lasts **125 ms**.
  Their onset interval is **5.126 s**, within the required 2.5-6.5 s range.
- The turn sequence visibly and atomically progresses through front,
  three-quarter, and profile head views with eye lead and settle phases while
  body pose, feet, staff, wings, and root remain stable.

## Video And Browser Evidence

- `visual-review-434ae0491d43-capture.mp4` is H.264/yuv420p,
  `1440x810`, 24 FPS, exactly **288 frames / 12.000 s**.
- `v1-quarter-speed.mp4` is H.264/yuv420p, `1440x810`, 24 FPS, exactly
  **1,152 frames / 48.000 s**, a four-times-duration review derivative bound
  to the normal-speed source hash.
- `v1-browser-layout.mp4` is H.264, `1280x634`, 24 FPS, exactly **288 frames /
  12.000 s**. The browser metrics bind it to this candidate, capture-manifest
  hash, run ID, and process epoch.
- Chrome was requested at `1280x720` DPR1. The measured page viewport is
  `1280x633`; its recorded frame is one pixel taller because of the screencast
  surface. The canvas is `960x540` CSS and backing pixels at DPR1, with a
  `240x135` logical raster and 4-device-pixel cells. The measured canvas,
  toolbar, and media-status rectangles fit without overlap or clipping.
- During the browser replay, decoded and presented frame counters each advance
  by exactly 288. Client metrics report zero dropped/raw-dropped frames, zero
  decode errors, zero resyncs, zero skipped presentation slots, and queue
  high-water marks of 2 decoded / 1 raw.
- All five browser replay commands were applied by the same command runtime
  epoch with contiguous browser source sequences.
- Direct frame inspection shows the full silhouette and ground contact in both
  decoded and browser recordings. Dense inspection around frames `184-203`
  confirms the eye-lead, three-quarter bridge, blink-covered profile arrival,
  and stable settle. Dense inspection around both blink runs confirms complete
  closure and restoration without body or root movement.

## Contact Sheet

The `1620x7440` contact sheet contains 60 chronological samples: the six-frame
cadence plus event-boundary samples. Actual rendered labels were inspected at
native resolution. Each sample identifies frame, simulation tick, presentation
time, scenario, sample reason, command ID, complete authoritative state
SHA-256, and complete frame SHA-256. Event samples include the blink and turn
boundaries omitted by cadence-only sampling.

## Nonblocking Observation

Chrome records one network console error: `GET /favicon.ico` returned 404.
This is classified as nonblocking because it is the browser's conventional
page-icon request, not a script, stylesheet, command, WebSocket, canvas, or
evidence artifact. There are no page exceptions; the WebSocket remains open;
all commands are acknowledged; the canvas presents all 288 planned frames; and
the video shows no visible failure. Adding an explicit favicon remains a useful
cleanup item but does not undermine V1 animation evidence.

## Residual Risks

- Chrome emitted 258 screencast events while the recorder produced the required
  288-frame constant-rate video, repeating 35 sampled screencast images. This
  browser artifact therefore proves layout, scale, and live presentation but
  is not a one-browser-screenshot-per-runtime-frame parity ledger. The separate
  288-frame exact decoded capture and atomic trace provide that ledger.
- The browser's measured content viewport is `1280x633`, not the requested
  outer `1280x720`. It is transparently recorded and fully contains V1, but the
  formal multi-DPR and mobile/desktop viewport matrix remains V10 work.
- Runtime diagnostics report one stale-render discard during the gaze/turn
  boundary. It did not produce a wire gap, decoded gap, browser drop, root
  discontinuity, or visible corruption, so it is retained as an operational
  observation rather than a V1 blocker.
- The technical package establishes evidence integrity and observable V1
  behavior. Final acting appeal and director judgment remain the responsibility
  of the separate independent animation reviewer.

## Final Verdict

**ACCEPTED.** The V1 Listening package is attributable, complete, internally
replayable, browser-evidenced, and technically adequate for independent visual
acceptance. No provenance, transport, hash-pairing, acknowledgment, contact,
framing, blink-timing, media, or contact-sheet blocker remains.
