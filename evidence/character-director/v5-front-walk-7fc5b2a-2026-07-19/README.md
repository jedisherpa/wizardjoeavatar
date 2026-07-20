# Character Director V5 Front-Walk Evidence

Status: machine, browser, independent technical, and independent animation
review pass.

## Candidate

- Runtime and analyzer commit: `7fc5b2af354b81aafd7f7b39b849fd033b25fc56`
- Runtime branch: `codex/v5-proof-dbb5043`
- Runtime tree: `43629b30c0cb6b1195ccfa4dc0a8687a58491a8e`
- Capture run: `visual-review-61539fb79909`
- Capture checkout was clean before and throughout capture.

## Acceptance Result

The V5 program starts neutral, walks forward through three complete
distance-driven cycles, alternates left/right support contacts, eases into a
contact-locked stop, and settles to neutral at the exact requested target.

The accepted stop uses an intentional pose-to-pose contact cut. Anticipation
frames present one complete authored walk graph; recovery frames present one
complete lock-aligned idle graph. This replaces rejected scan-line and
cell-splat candidates that visibly bisected the robe, face, wings, or staff.

`v5-machine-acceptance.json` passes all ten gates:

- Exact V5 program identity and scenario order.
- 102 contiguous scenario-owned frames with zero drops.
- Three complete distance-driven cycles over 2.55 world units.
- Six alternating contacts with zero planted-anchor drift.
- Six distinct deceleration speeds and an eleven-frame zero-speed suffix.
- Exact stop-pose sequence through 25, 50, 62.5, 75, 87.5, and 100 percent.
- Runtime body hashes prove atomic anticipation and recovery topology groups.
- Exact target arrival, stable idle suffix, and zero clipped silhouettes.

The focused V5, pose-library, pose-selection, compositor, and staff suite passed
57 tests. Deterministic pose-library regeneration produced SHA-256
`b21f3bc7d5ad226da86f3a0340ba7517a83722c776be3ac714b82498b587256f`.

## Media Evidence

| Artifact | Dimensions | Frames | Rate | Duration | SHA-256 |
| --- | ---: | ---: | ---: | ---: | --- |
| `visual-review-61539fb79909-capture.mp4` | 960x540 | 102 | 24 fps | 4.25 s | `4e7fcbd2fcf92b5b90158b95a508252d51ba4689f82c96654484e1536fb987e9` |
| `v5-quarter-speed.mp4` | 960x540 | 408 | 24 fps | 17.00 s | `ad3f764b3443d82f5f124d5a17207d1b11353a966052cf3730805d79842de87e` |
| `v5-browser-layout.mp4` | 1280x634 | 102 | 24 fps | 4.25 s | `1847aefd88ff75a406641acf60ca22638850ace0c47f68c21383e3fc1db50981` |

The browser pass reports zero decoder errors, dropped frames, raw-message
drops, resyncs, skipped presentation slots, console errors, or page errors.
The 960x540 canvas and 452x52 toolbar fit inside the measured 1280x633 viewport
without overlap or clipping. Command acknowledgement latency was 32.461 to
38.204 ms.

## Bundle Integrity

`review-bundle-manifest.json` is a strict-valid
`character_director_review_bundle_manifest_v1` version 2 bundle. It binds the
capture manifest, normal-speed source, quarter-speed derivative, browser-layout
recording and metrics, and machine report by byte count and SHA-256.

Primary files:

- `manifest.json`: authoritative capture and Git provenance.
- `animation_truth_trace.ndjson`: one truth record for every captured frame.
- `contact_verification.json`: zero-drift contact report.
- `scenario-program.json`: exact V5 authored scenario program.
- `v5-machine-acceptance.json`: ten machine-verifiable acceptance gates.
- `review-bundle-manifest.json`: strict artifact lineage and integrity record.
- `visual-review-61539fb79909-contact-sheet.png`: sampled review sheet.
- `samples/`: all 102 rendered frames.
- `wire/`: captured transport payloads and frame index.

Primary animation review passed the contact cut at both speeds. The cut is
obvious at quarter speed but reads as deliberate limited animation at normal
speed. The final recenter from lock-aligned recovery to exact neutral idle is a
non-blocking polish note; the character remains grounded and intact.
