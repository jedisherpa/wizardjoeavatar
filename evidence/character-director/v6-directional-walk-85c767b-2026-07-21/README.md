# Character Director V6 Directional-Walk Evidence

Status: **rejected for V6 acceptance**. Machine and browser checks passed, but
the independent technical and animation reviews both failed the candidate.
This directory is retained as immutable historical evidence for the rejected
two-pose implementation.

## Candidate

- Directional locomotion commit: `47c7598`
- Grounded profile-stop correction: `85c767ba9c39693536cf6c707a5716f93d08c963`
- Runtime proof branch: `codex/v6-proof-47c7598`
- Runtime tree: `e81673e69ebbd4abe3a40e0f8a89b738b3a87604`
- Capture run: `visual-review-e6a51fe3698b`
- Capture checkout was clean before and throughout capture.

## Acceptance Result

The automated result below describes what the original analyzer accepted. It
is not the final V6 decision. Independent review found that the side gait was
an idle silhouette plus a one-cell whole-body translation, while the visible
90-degree turn and 180-degree reversal were hard pose swaps masked by facing
metadata. V6 therefore remains open.

Authoritative rejection reports:

- `docs/character-director/reviews/V6_DIRECTIONAL_WALK_85C767B_ANIMATION_REVIEW.md`
- `docs/character-director/reviews/V6_DIRECTIONAL_WALK_85C767B_TECHNICAL_REVIEW.md`

The replacement source-graph contract is recorded in
`docs/character-director/reviews/V6_RESUBMISSION_PIXEL_GRAPH_DESIGN.md`.

The V6 program walks forward, turns through adjacent facing sectors into a
right profile walk, reverses through the rear sectors into a left profile
walk, stops without changing construction, and settles at the exact requested
target. Direction changes retain one continuous distance-driven gait phase;
the runtime does not insert a neutral front pose inside either turn.

`v6-machine-acceptance.json` passes every V6 gate:

- 210 contiguous scenario-owned frames with zero drops.
- A 90-degree turn through south, southeast, and east with no skipped sector.
- A 180-degree reversal through east, southeast, south, southwest, and west.
- Correct right- and left-profile pose families throughout side travel.
- Twenty alternating support changes with zero planted-anchor drift.
- Continuous gait phase across both directional transitions.
- Maximum adjacent world-root step of 0.0625 units.
- Exact target arrival at `(-2.4, 3.8)` and a 31-frame zero-speed suffix.
- Maximum decoded-raster foot-span change of one cell.
- Zero clipped silhouettes.

The side gait is intentionally limited pixel animation. Each direction uses a
complete profile contact graph plus a complete one-cell passing graph derived
deterministically from the approved transparent pixel graph. The projector
renders colored graph cells only; no PNG, SVG, scan-line morph, or partial
runtime image is introduced. This V6 evidence proves direction, phase,
contact, and transition continuity. It does not claim fully articulated
profile leg drawings beyond those two authored graph states.

## Media Evidence

| Artifact | Dimensions | Frames | Rate | Duration | SHA-256 |
| --- | ---: | ---: | ---: | ---: | --- |
| `visual-review-e6a51fe3698b-capture.mp4` | 960x540 | 210 | 24 fps | 8.75 s | `787c4567ae167d0f191858d4b1b12aa340332ff6a3f373d65a55f8a5ec95a9dd` |
| `v6-quarter-speed.mp4` | 960x540 | 840 | 24 fps | 35.00 s | `fd4d1aa09e15552dd40c12589b288ef8469571e21a52ad59c4400a1213d9f5c5` |
| `v6-browser-layout.mp4` | 1280x634 | 210 | 24 fps | 8.75 s | `802325d07b023a973020fc39d085825adc4b19fc0251289be2756f89f6149f85` |

The browser pass reports zero decoder errors, dropped frames, raw-message
drops, resyncs, skipped presentation slots, console errors, or page errors.
It presented 195 frames and decoded 196 frames while retaining all 210
scenario frames in the authoritative capture. The 960x540 canvas at
`(160, 46.5)` and 452x52 toolbar at `(414, 569)` fit inside the measured
1280x633 viewport without overlap or clipping.

## Bundle Integrity

`review-bundle-manifest.json` is a strict-valid
`character_director_review_bundle_manifest_v1` version 2 bundle. It binds the
capture manifest, normal-speed source, quarter-speed derivative,
browser-layout recording and metrics, contact report, and machine report by
byte count and SHA-256.

- Bundle manifest: `558752c6e957e49692c967c5a975fe3a1b70ca5209f1a68c56f83f5bc12ca5b6`
- Capture manifest: `4e355d43fe80298fe8779fac5d088ca828ec1e9251f70ea34fc694a396ebeb5f`
- Animation truth trace: `1bd65d50961a8a76b0e53bc91ca834663fa989762133aff58ed2225abccc1901`
- Contact report: `fd9fb225b2799e4738a9d592a8786800b8599fb7e9893d255754306af7144c6b`
- Machine acceptance: `890b20006b30c150e435203adf50af863ee1a15f683e809d8cdba0af967bdc98`

Primary files:

- `manifest.json`: authoritative capture and Git provenance.
- `animation_truth_trace.ndjson`: one truth record for every captured frame.
- `contact_verification.json`: declared and decoded-raster contact report.
- `scenario-program.json`: exact V6 scenario program.
- `v6-machine-acceptance.json`: machine-verifiable V6 gates.
- `review-bundle-manifest.json`: strict artifact lineage and integrity record.
- `visual-review-e6a51fe3698b-contact-sheet.png`: sampled review sheet.
- `samples/`: all 211 retained rendered samples, including frame zero.
- `wire/`: captured transport payloads and frame index.

The focused final V6 regression suite passed 44 tests. A broader locomotion,
pathing, contact, trace, frame-source, end-to-end, pose-library, and V4-V6
suite is rerun as part of final evidence acceptance and recorded in the
independent technical review.
