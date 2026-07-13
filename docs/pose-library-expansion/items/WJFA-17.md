# Candidate WJFA-17

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_42 PM (7).png`

## Classification

- Proposed semantic ID: `front_point_direct_staff_held`
- Facing: `south`
- Locomotion: `idle`
- Actions: `["pointing", "explaining"]`
- Phase: `null`
- Tags: `["front", "pointing", "direct_point", "staff_held", "wings", "low_fit_risk"]`
- Duplicate comparison: Semantically related to current `explaining`, but `explaining` is palm-up/open-hand while this has a clear extended pointing finger. It is not a material duplicate.
- Recommended disposition: `ANALYZED`; good candidate for `READY` as a clean pointing pose.

## Anatomy and anchors

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | High | Grounded pose fits current canonical root well. |
| mouth | `[36, 36]` | Medium | Open speaking mouth. |
| left_eye | `[31, 31]` | Medium | Visual estimate. |
| right_eye | `[41, 31]` | Medium | Visual estimate. |
| left_foot | `[25, 94]` | Medium | Screen-left planted boot. |
| right_foot | `[53, 94]` | Medium | Screen-right planted boot. |
| left_hand | `[13, 35]` | Medium | Extended pointing hand. |
| right_hand | `[57, 45]` | Medium | Staff grip. |
| staff_hand | `[57, 45]` | Medium | Same as right hand. |
| staff_tip | `[63, 10]` | Medium | Staff top inside bounds. |

## Visual assessment

- Character consistency: Strong and readable; proportions are close to existing front poses.
- Silhouette value: High for direct pointing and instructional/explaining states.
- Transition neighbors: `explaining`, `front_idle`, `front_staff_block_horizontal`, and `front_shush_secret_staff_held`.
- Known risks: Finger/hand should be masked separately from mouth/speech overlays. Otherwise low fit risk: raw generated `73 x 96`, zero naive canonical out-of-bounds cells.

## Integration record

- Source destination: Proposed only, not copied: `assets/reference/motion_sources/front_point_direct_staff_held.png`.
- Manifest entry: Proposed only: facing `south`, locomotion `idle`, actions `["pointing", "explaining"]`, tags as above, explicit pointing hand and staff anchors.
- Runtime selection change: Proposed direct `pointing` pose after integration lock.
- Generated library SHA-256: NOT RUN.
- Files changed: `docs/pose-library-expansion/items/WJFA-17.md`; `evidence/pose-library-expansion/WJFA-17/source-preview.png`; `evidence/pose-library-expansion/WJFA-17/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-17/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-17/intake-analysis.md`

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
- Commands run: Read workflow docs; inspected source PNG/current `explaining`; generated intake previews; computed generator fit. Result: source `1122 x 1402`, raw generated `73 x 96`, 0 naive canonical out-of-bounds cells.
- Evidence produced: `evidence/pose-library-expansion/WJFA-17/source-preview.png`; `evidence/pose-library-expansion/WJFA-17/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-17/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-17/intake-analysis.md`
- Risks or uncertainty: Needs explicit hand/face mask ordering for speech/expression overlays.
- Next operator action: Coordinator review for `READY`; this is one of the safer candidates in the batch.

## Automated integration gate

- Completed: `2026-07-13T04:20:12.832081+00:00`
- Source SHA-256: `c6b03a269aa4e9f12911dab45204c5baa93a21c679b024c69807e124bab316fb`
- Generated library SHA-256: `52f59df2b0341b618683993cf1f35536e427c009c175fc8a2985c86ab9a52330`
- Pose count after integration: `36`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-17/integration-result.json`
