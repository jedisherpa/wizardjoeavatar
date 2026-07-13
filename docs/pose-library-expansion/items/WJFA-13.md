# Candidate WJFA-13

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_41 PM (3).png`

## Classification

- Proposed semantic ID: `front_magic_staff_thrust`
- Facing: `south` / front-family
- Locomotion: `idle`
- Actions: `["magic_cast", "staff_thrust"]`
- Phase: `null`
- Tags: `["front", "magic", "staff_thrust", "spark", "wide_stance", "wings"]`
- Duplicate comparison: Closest current pose is `magic_cast`, but this thrusts the staff forward to screen left with spark particles and a different wide stance. It is a magic-cast variant, not a material duplicate.
- Recommended disposition: `ANALYZED`; useful as a second cast key if action variants are accepted.

## Anatomy and anchors

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | Medium | Keep canonical root fixed at stance midpoint. |
| mouth | `[43, 36]` | Medium | Face is offset screen right by staff thrust composition. |
| left_eye | `[39, 31]` | Medium | Visual estimate. |
| right_eye | `[49, 31]` | Medium | Visual estimate. |
| left_foot | `[23, 94]` | Medium | Screen-left planted boot. |
| right_foot | `[57, 92]` | Medium | Screen-right planted boot. |
| left_hand | `[27, 43]` | Medium | Staff-thrust hand near screen-left body. |
| right_hand | `[59, 54]` | Medium | Free clenched hand. |
| staff_hand | `[27, 43]` | Medium | Same as left hand. |
| staff_tip | `[8, 25]` | Low | Spark/staff tip is far left and may need effect-region trimming. |

## Visual assessment

- Character consistency: Strong; spell spark and staff orientation are compatible with WizardJoe's magic identity.
- Silhouette value: High, provides active forward-cast pose distinct from the current vertical `magic_cast`.
- Transition neighbors: `magic_cast`, `front_idle`, `explaining`, `front_staff_spin_flourish`.
- Known risks: Raw generator produces `95 x 96`; naive canonical shift has 427 out-of-bounds cells. Spark particles and staff tip may need effect-region crop or separate non-body overlay so canonical body fit remains stable.

## Integration record

- Source destination: Proposed only, not copied: `assets/reference/motion_sources/front_magic_staff_thrust.png`.
- Manifest entry: Proposed only: facing `south`, locomotion `idle`, actions `["magic_cast", "staff_thrust"]`, tags as above, explicit anchors for shifted face, staff hand, staff tip, and wide stance.
- Runtime selection change: Proposed alternate magic-cast key or cast anticipation/impact pose after graph supports variants.
- Generated library SHA-256: NOT RUN.
- Files changed: `docs/pose-library-expansion/items/WJFA-13.md`; `evidence/pose-library-expansion/WJFA-13/source-preview.png`; `evidence/pose-library-expansion/WJFA-13/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-13/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-13/intake-analysis.md`

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
- Commands run: Read workflow docs; inspected source PNG/current `magic_cast`; generated intake previews; computed generator fit. Result: source `1122 x 1402`, raw generated `95 x 96`, 427 naive canonical out-of-bounds cells.
- Evidence produced: `evidence/pose-library-expansion/WJFA-13/source-preview.png`; `evidence/pose-library-expansion/WJFA-13/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-13/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-13/intake-analysis.md`
- Risks or uncertainty: Effect spark and staff extension may exceed canonical bounds; integrator should decide whether to crop spark from body pose or model it as an effect overlay.
- Next operator action: Coordinator review for `READY` as a cast variant, pending fit/effect policy.

## Automated integration gate

- Completed: `2026-07-13T04:09:26.899497+00:00`
- Source SHA-256: `50c99ea05546e8fb5a605f2326b2343f5ac6f98ff2e40ddfc77083b0cc22247d`
- Generated library SHA-256: `9a23cb90e9a66573209af2c3f59bb0d0673801397c4e8559eb034e4bb9cec6bc`
- Pose count after integration: `32`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-13/integration-result.json`
