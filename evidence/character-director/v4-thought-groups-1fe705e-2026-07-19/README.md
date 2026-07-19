# Character Director V4 Thought-Group Evidence

Status: machine and primary visual review pass; independent animation and
technical review pending.

## Candidate

- Runtime commit: `1fe705e3e60c3dac612c6d5c2aa7a98392cfaae9`
- Runtime branch: `codex/v4-localized-1fe705e`
- Runtime tree: `dc2a8039abdece6d9e973213f2f126d03b73b9bd`
- Capture run: `visual-review-ed4d9343d974`
- Capture checkout was clean before and throughout the runtime capture.
- Post-capture analyzer correction: `c009607` aligns scenario-owned coverage
  with the bounded transition frame that carries authored frame zero. The
  correction does not change runtime frames, poses, timing, or capture data.

## Acceptance Result

The V4 program presents two explain strokes, neutral thought-group holds, one
point stroke, and a final settle. The accepted implementation keeps the
canonical body, face, stance, staff, and opposite arm stable while carrying the
acting arm as a localized pixel graph. A prior global landmark-warp attempt was
rejected because it caused a visible full-body pop at the gesture endpoint.

`v4-machine-acceptance.json` passes all eight machine gates:

- Exact seven-scenario program identity and order.
- 168 contiguous transport frames: 162 scenario-owned frames and six bounded
  transition frames, with zero dropped frames.
- Three motivated strokes in authored marker order.
- Complete authored action and recovery coverage with neutral holds.
- Exact explain and point pixel-graph sequences and palette contract.
- Zero planted contact drift.
- Zero stage-root and world-root drift.
- Zero clipped silhouettes on the canonical 240 by 135 stage.

The analyzer was replayed after generation and produced a byte-identical JSON
report. The focused V4/runtime suite passed 72 tests.

## Media Evidence

| Artifact | Dimensions | Frames | Rate | Duration | SHA-256 |
| --- | ---: | ---: | ---: | ---: | --- |
| `visual-review-ed4d9343d974-capture.mp4` | 960x540 | 162 | 24 fps | 6.75 s | `39c55a0cc16a9e436f51d6681a711cb646017d951e1bd447c13555a3d275a4ea` |
| `v4-quarter-speed.mp4` | 960x540 | 648 | 24 fps | 27.00 s | `425c3cdc2a8d5452e1926d2d24337a1418b1bdd2cc05968254e9ea6fe471ea47` |
| `v4-browser-layout.mp4` | 1280x634 | 162 | 24 fps | 6.75 s | `bdcf5770cfde78b383e2bf698d606a004f1b4fb48ca643b20e35bcb4d885846a` |

The browser run reports zero decode errors, dropped frames, raw-message drops,
resyncs, resync skips, skipped presentation slots, console errors, or page
errors. The 960x540 canvas and 452x52 toolbar both fit inside the measured
1280x633 content viewport without overlap or clipping. Command acknowledgement
latencies were 20.903 to 50.827 ms.

## Bundle Integrity

`review-bundle-manifest.json` is a strict-valid
`character_director_review_bundle_manifest_v1` version 2 bundle. It binds the
capture manifest, normal-speed source, quarter-speed derivative, browser-layout
recording and metrics, and machine acceptance report by byte count and SHA-256.

Primary files:

- `manifest.json`: authoritative capture and provenance record.
- `animation_truth_trace.ndjson`: one truth record for every transport frame.
- `contact_verification.json`: zero-drift contact report.
- `scenario-program.json`: exact V4 authored scenario program.
- `v4-machine-acceptance.json`: machine-verifiable acceptance result.
- `review-bundle-manifest.json`: strict artifact lineage and integrity record.
- `visual-review-ed4d9343d974-contact-sheet.png`: complete sampled review sheet.
- `samples/`: all 162 scenario-owned rendered frames.
- `wire/`: captured transport payloads and index.

Human review must still judge gesture motivation, accent clarity, silhouette,
restraint, acting rhythm, and the absence of visible body pops at both speeds.
