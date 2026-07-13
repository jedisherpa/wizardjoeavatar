# Candidate WJFA-19

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_42 PM (9).png`

## Classification

- Proposed semantic ID: `front_shush_secret_staff_held`
- Facing: `south`
- Locomotion: `idle`
- Actions: `["shush", "secret", "thinking"]`
- Phase: `null`
- Tags: `["front", "shush", "secret", "finger_to_mouth", "staff_held", "wings", "low_fit_risk"]`
- Duplicate comparison: No current pose covers the finger-to-mouth gesture. It is not a duplicate of `explaining`, `thinking`, or speech overlays.
- Recommended disposition: `ANALYZED`; useful expressive/action pose if face-hand overlap is supported.

## Anatomy and anchors

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | High | Grounded pose fits canonical root. |
| mouth | `[36, 35]` | Low | Finger occludes mouth; mouth overlay should likely be suppressed. |
| left_eye | `[31, 30]` | Medium | Visual estimate. |
| right_eye | `[41, 30]` | Medium | Visual estimate. |
| left_foot | `[27, 90]` | Low | Lifted/back boot, not primary contact. |
| right_foot | `[50, 94]` | Medium | Screen-right planted boot. |
| left_hand | `[35, 44]` | Medium | Finger-to-mouth hand; should be face/gesture region. |
| right_hand | `[57, 45]` | Medium | Staff grip. |
| staff_hand | `[57, 45]` | Medium | Same as right hand. |
| staff_tip | `[61, 11]` | Medium | Staff top inside bounds. |

## Visual assessment

- Character consistency: Strong, with a clear mischievous/secret expression.
- Silhouette value: Medium-high; provides a semantic expression/action that current mouth/face overlays cannot express alone.
- Transition neighbors: `front_idle`, `front_point_direct_staff_held`, `explaining`, and `thinking`.
- Known risks: Finger-to-mouth gesture conflicts with mouth/speech overlays and must mask or suppress mouth rendering. Fit is good: raw generated `72 x 96`, zero naive canonical out-of-bounds cells.

## Integration record

- Source destination: Proposed only, not copied: `assets/reference/motion_sources/front_shush_secret_staff_held.png`.
- Manifest entry: Proposed only: facing `south`, locomotion `idle`, actions `["shush", "secret", "thinking"]`, tags as above, explicit finger/face and staff anchors.
- Runtime selection change: Proposed expressive action state; must coordinate with speech/mouth ownership.
- Generated library SHA-256: NOT RUN.
- Files changed: `docs/pose-library-expansion/items/WJFA-19.md`; `evidence/pose-library-expansion/WJFA-19/source-preview.png`; `evidence/pose-library-expansion/WJFA-19/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-19/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-19/intake-analysis.md`

## Verification

| Gate | Result | Evidence |
|---|---|---|
| Deterministic generation | NOT RUN | |
| Anchor bounds | NOT RUN | |
| Focused tests | NOT RUN | |
| Full Python tests | NOT RUN | |
| Strict transition matrix | NOT RUN | |
| Live browser entry/hold/exit | NOT RUN | |

## Handoff

- Previous status: `CLAIMED`
- Proposed next status: `ANALYZED`
- Commands run: Read workflow docs; inspected source PNG/current expressions and gestures; generated intake previews; computed generator fit. Result: source `1122 x 1402`, raw generated `72 x 96`, 0 naive canonical out-of-bounds cells.
- Evidence produced: `evidence/pose-library-expansion/WJFA-19/source-preview.png`; `evidence/pose-library-expansion/WJFA-19/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-19/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-19/intake-analysis.md`
- Risks or uncertainty: Needs explicit action-channel rule for mouth suppression/face mask.
- Next operator action: Coordinator review for `READY`; integrator should add focused overlay/mouth conflict tests if accepted.

## Automated integration gate

- Completed: `2026-07-13T04:25:59.806461+00:00`
- Source SHA-256: `242360990cb6e7c48c28d52ee1c5939ef986183ee2c1e2654d605cb7a8f3aa4d`
- Generated library SHA-256: `7f141045ef4e759e5967f752129167ebfaa675726f6d2b1c321b6b4a7c7a54d8`
- Pose count after integration: `38`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-19/integration-result.json`
