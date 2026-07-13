# Candidate WJFA-11

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_41 PM (1).png`

## Classification

- Proposed semantic ID: `front_run_charge_right_plant`
- Facing: `south` / front-family
- Locomotion: `running`
- Actions: `["running", "charge"]`
- Phase: `0.25`
- Tags: `["front_family", "run", "charge", "right_foot_plant", "left_foot_lift", "staff_held", "wings"]`
- Duplicate comparison: Closest current poses are `walk_front_left` and `walk_front_right`, but this has a forward charge lean, clenched screen-left fist, wider stride, and staff carried high on screen right. It is not a material duplicate of the current walk pair.
- Recommended disposition: `ANALYZED`; review for `READY` only if running/charge poses are in scope.

## Anatomy and anchors

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | Medium | Keep canonical root fixed; action stride should not move the stage root. |
| mouth | `[36, 36]` | Medium | Open mouth, close to front-family default. |
| left_eye | `[32, 31]` | Medium | Visual estimate on rough 72 x 96 preview. |
| right_eye | `[42, 31]` | Medium | Visual estimate on rough 72 x 96 preview. |
| left_foot | `[28, 86]` | Low | Lifted trailing boot; do not use as planted contact. |
| right_foot | `[54, 94]` | Medium | Screen-right boot is the apparent plant/contact. |
| left_hand | `[24, 56]` | Medium | Forward clenched fist. |
| right_hand | `[57, 49]` | Medium | Staff grip on screen right. |
| staff_hand | `[57, 49]` | Medium | Same as right hand. |
| staff_tip | `[68, 13]` | Low | Staff top is near right edge; fit is high risk. |

## Visual assessment

- Character consistency: Strong WizardJoe identity: blue robe, magenta stripe, gold-star hat, beard, staff, rainbow wings, and square voxel style.
- Silhouette value: High value for charge/run, more dynamic than current front walk phases.
- Transition neighbors: `walk_front_right`, `walk_front_left`, `front_idle`, and future run/fly takeoff poses.
- Known risks: Raw generator produces `90 x 96` before canonical shift; naive fit has 282 out-of-bounds cells. Integration needs tighter crop, reduced margin, or action-specific downscale/canonical width handling for wings and staff.

## Integration record

- Source destination: Proposed only, not copied: `assets/reference/motion_sources/front_run_charge_right_plant.png`.
- Manifest entry: Proposed only: facing `south`, locomotion `running`, actions `["running", "charge"]`, phase `0.25`, tags as above, explicit anchors for planted foot, lifted foot, hands, staff hand, and staff tip.
- Runtime selection change: Proposed future run/charge selection; do not wire until coordinator grants integration lock.
- Generated library SHA-256: NOT RUN.
- Files changed: `docs/pose-library-expansion/items/WJFA-11.md`; `evidence/pose-library-expansion/WJFA-11/source-preview.png`; `evidence/pose-library-expansion/WJFA-11/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-11/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-11/intake-analysis.md`

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
- Commands run: Read workflow docs; inspected source PNG and current pose manifest; generated source/canonical proposal previews; computed generator fit. Result: source `1122 x 1402`, raw generated `90 x 96`, 282 naive canonical out-of-bounds cells.
- Evidence produced: `evidence/pose-library-expansion/WJFA-11/source-preview.png`; `evidence/pose-library-expansion/WJFA-11/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-11/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-11/intake-analysis.md`
- Risks or uncertainty: Fit and contact metadata are the main risks; the lifted foot should not be treated as grounded.
- Next operator action: Coordinator should decide whether run/charge is in scope and, if yes, queue for `READY` with explicit fit and contact-marker requirements.

## Automated integration gate

- Completed: `2026-07-13T04:04:26.808402+00:00`
- Source SHA-256: `42c2bc01a3d201202719388afbb380757c33fddfdce40e668c0eab049c76f321`
- Generated library SHA-256: `8148d229f13dc9c2df806a1a35af4169e5d0e8391ea936e7b57b5332b57bb978`
- Pose count after integration: `30`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-11/integration-result.json`
