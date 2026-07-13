# Candidate WJFA-20

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_42 PM (10).png`

## Classification

- Proposed semantic ID: `front_staff_spin_flourish`
- Facing: `south` / front-family
- Locomotion: `idle`
- Actions: `["staff_spin", "flourish", "magic_cast"]`
- Phase: `null`
- Tags: `["front", "staff_spin", "flourish", "motion_arc", "open_hand", "wings", "high_fit_risk"]`
- Duplicate comparison: Related to `magic_cast` by staff motion and to WJFA-16 by staff emphasis, but this has a visible spin arc and open presenting hand. It is not a material duplicate.
- Recommended disposition: `ANALYZED`; valuable but high-risk because the staff arc and wide arms overflow canonical bounds.

## Anatomy and anchors

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | Medium | Grounded stride; keep canonical root fixed. |
| mouth | `[36, 35]` | Medium | Open smile. |
| left_eye | `[31, 30]` | Medium | Visual estimate. |
| right_eye | `[42, 30]` | Medium | Visual estimate. |
| left_foot | `[25, 94]` | Medium | Screen-left planted boot. |
| right_foot | `[58, 93]` | Low | Screen-right boot lifted/stepping. |
| left_hand | `[62, 38]` | Medium | Open presenting hand on screen right. |
| right_hand | `[23, 37]` | Medium | Staff grip on screen left. |
| staff_hand | `[23, 37]` | Medium | Same as right hand. |
| staff_tip | `[10, 11]` | Low | Motion arc/staff top extends far left and high. |

## Visual assessment

- Character consistency: Strong; the staff spin arc reads as an action effect while preserving WizardJoe identity.
- Silhouette value: High for flourish/cast anticipation or exit.
- Transition neighbors: `magic_cast`, `front_staff_block_horizontal`, `front_magic_staff_thrust`, and `front_idle`.
- Known risks: Raw generator produces `92 x 96`; naive canonical shift has 467 out-of-bounds cells. Motion arc should likely be effect metadata, not part of stable body silhouette.

## Integration record

- Source destination: Proposed only, not copied: `assets/reference/motion_sources/front_staff_spin_flourish.png`.
- Manifest entry: Proposed only: facing `south`, locomotion `idle`, actions `["staff_spin", "flourish", "magic_cast"]`, tags as above, explicit staff grip/tip and open hand anchors, plus separate effect-region treatment for the motion arc.
- Runtime selection change: Proposed flourish/cast transition key after staff action graph supports it.
- Generated library SHA-256: NOT RUN.
- Files changed: `docs/pose-library-expansion/items/WJFA-20.md`; `evidence/pose-library-expansion/WJFA-20/source-preview.png`; `evidence/pose-library-expansion/WJFA-20/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-20/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-20/intake-analysis.md`

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
- Commands run: Read workflow docs; inspected source PNG/current staff poses; generated intake previews; computed generator fit. Result: source `1122 x 1402`, raw generated `92 x 96`, 467 naive canonical out-of-bounds cells.
- Evidence produced: `evidence/pose-library-expansion/WJFA-20/source-preview.png`; `evidence/pose-library-expansion/WJFA-20/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-20/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-20/intake-analysis.md`
- Risks or uncertainty: High canonical-fit risk; staff spin arc should be separated or cropped before integration.
- Next operator action: Coordinator review for `READY` only after deciding how action-effect arcs are represented.

## Automated integration gate

- Completed: `2026-07-13T04:28:58.341509+00:00`
- Source SHA-256: `1f5a92b90392fc0fae3c1a8cf0a9df7c5893278b413f1cc7f0e6aafca65d63b2`
- Generated library SHA-256: `1200e2891902cd1f3147d2c2d298dd2d99313708fbc8e90034376500e1843037`
- Pose count after integration: `39`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-20/integration-result.json`
