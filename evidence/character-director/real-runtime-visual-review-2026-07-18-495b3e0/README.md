# Real-Runtime Visual Review Baseline

Capture date: 2026-07-18 UTC  
Candidate: `495b3e04fa1c39f21e7b8ef55cde7d2490d0ef2f`  
Branch: `codex/character-director`  
Runtime: isolated Python visualizer on `127.0.0.1:8875`

## Result

The strict capture manifest is valid.

| Measurement | Result |
| --- | ---: |
| Duration | 14.554285 s |
| Presentation frames | 345 |
| Frame range | 30603-30947 |
| Presentation rate | 24 FPS |
| Queue high-water | 1/16 |
| Queue overruns | 0 |
| Decoded gaps | 0 |
| Decoder errors | 0 |
| Dropped frames | 0 |
| Hashed artifacts | 45 |

The command matrix covers front idle, gaze left/right, happy and thinking
expressions, walk start, reversal, stop, back/front facing, magic cast, speech,
and speech interruption. Every command used the ordered HTTP envelope and
returned an applied acknowledgment. Frames came from the actual adaptive
ASCILINE WebSocket used by the Python visualizer.

## Artifacts

- `manifest.json`: commands, acknowledgments, time-adjacent state observations,
  frame ledger, scenario ranges, queue statistics, hashes, and clean Git
  provenance. SHA-256:
  `9860e78a7634f2d815685e8c41c04a729c3a2a11f4067142785188662b6b3bbe`.
- `wire/frames.bin`: original ASCILINE messages in presentation order.
- `wire/index.ndjson`: frame, codec, byte offset, byte length, SHA-256, scenario,
  and receipt time for each wire message.
- `visual-review-4d4595aba515-capture.mp4`: exact 345-frame H.264 video at
  960x540 and 24 FPS. SHA-256:
  `ca6e3585ef4b44b4067ac9948b97569478f827556fb90d2e697e307302df1501`.
- `visual-review-4d4595aba515-contact-sheet.png`: sampled square-cell frames.
  SHA-256:
  `61db9cf975fdb39751d12cbaf9dd1d811d66dc7697797c943f790b4f8aac734d`.
- `samples/`: retained PNGs whose bytes and frame hashes are indexed by the
  manifest.

## Visual Inspection

The retained contact sheet was inspected after capture. It shows complete,
uncropped silhouettes through the walk reversal, rear/front turns, cast
extremes, speaking state, and interruption recovery. Square-cell edges remain
crisp, background cells retain their protocol RGB values, and no anatomy
fragmentation is visible in the sampled frames.

This is a baseline inspection, not the final two-reviewer director score.

## What This Proves

- The exact Python candidate can be driven through ordered commands while its
  real ASCILINE stream is captured without detected loss.
- The evidence pipeline fails closed on gaps, decode errors, or queue overrun.
- The projector-to-video path uses colored square cells and ignores the glyph
  byte, matching the Companion renderer's pixel contract.
- The retained artifacts are attributable to a clean worktree and exact Git
  candidate.

## What This Does Not Prove

- Browser canvas pixels are not yet hashed against source and decoded cells.
- HTTP state observations are time-adjacent, not atomic frame/state pairs.
- This silent capture does not prove real Prism TTS or music synchronization.
- It does not complete the 60-second blink/stillness/repetition scene,
  quarter-speed hand and foot review, reduced-motion comparison, responsive
  browser matrix, or two independent director reviews.
- It does not replace the required connected Prism AV recording, eight-hour and
  24-hour soaks, or independent-user package/rollback verification.

The governing rubric and remaining scenarios are recorded in
`docs/character-director/VISUAL_PERFORMANCE_ACCEPTANCE_2026-07-17.md`.
