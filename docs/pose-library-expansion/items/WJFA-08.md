# Candidate WJFA-08

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_11 PM (8).png`

## Classification

- Proposed semantic ID: `fly_southeast_cheer`
- Facing: `southeast`
- Locomotion: `flying`
- Actions: `reaction`, `cheer`
- Phase: `null`
- Tags: `southeast`, `flying`, `airborne`, `cheer`, `raised_fist`, `reaction`, `staff_held`, `wings`
- Duplicate comparison: Not a duplicate of `explaining` or `magic_cast`; the raised fist is closed and celebratory, not explanatory or spell-casting.
- Recommended disposition: `ANALYZED`; valuable as an airborne reaction/action pose.

## Anatomy and anchors

Coordinates are proposed for the canonical `72 x 96` canvas with fixed projected root `[36, 95]`.

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | medium | Projected root under hovering body. |
| mouth | `[39, 34]` | medium | Open cheering mouth. |
| left_eye | `[34, 25]` | medium | Viewer-left eye. |
| right_eye | `[44, 26]` | medium | Viewer-right eye. |
| left_foot | `[29, 85]` | low | Airborne lower boot. |
| right_foot | `[42, 89]` | low | Airborne lower boot. |
| left_hand | `[22, 24]` | medium | Raised fist at upper viewer left. |
| right_hand | `[56, 42]` | medium | Staff hand. |
| staff_hand | `[56, 42]` | medium | Explicit override required. |
| staff_tip | `[62, 5]` | low | Staff crook high near top boundary. |

## Visual assessment

- Character consistency: Strong.
- Silhouette value: High for action/reaction; not a generic flying cycle frame.
- Transition neighbors: WJFA-07 banked entry, WJFA-01 hover recovery, current `magic_cast` as action-family comparator.
- Known risks: Raised fist and staff tip compete for top crop; action should not be selected for ordinary flight.

## Integration record

- Source destination: proposed `assets/reference/motion_sources/fly_southeast_cheer.png`
- Manifest entry: add one pose with `facing: "southeast"`, `locomotion: "flying"`, `actions: ["reaction", "cheer"]`, `phase: null`, and raised-fist/staff anchors.
- Runtime selection change: add airborne reaction/cheer selection separate from grounded `reaction`/`magic_cast`.
- Generated library SHA-256: not generated during intake.
- Files changed: `docs/pose-library-expansion/items/WJFA-08.md`, `evidence/pose-library-expansion/WJFA-08/source-preview.png`, `evidence/pose-library-expansion/WJFA-08/intake-analysis.md`

## Verification

| Gate | Result | Evidence |
|---|---|---|
| Deterministic generation | NOT RUN | Intake only. |
| Anchor bounds | PROPOSED | This record and `evidence/pose-library-expansion/WJFA-08/intake-analysis.md`. |
| Focused tests | NOT RUN | Intake only. |
| Full Python tests | NOT RUN | Intake only. |
| Strict transition matrix | NOT RUN | Intake only. |
| Live browser entry/hold/exit | NOT RUN | Intake only. |

## Handoff

- Previous status: `CLAIMED`
- Proposed next status: `ANALYZED`
- Commands run: read workflow/tracker; inspected source PNG visually; `sips` reported `1122 x 1402`; copied source preview.
- Evidence produced: `source-preview.png`, `intake-analysis.md`
- Risks or uncertainty: Needs action-priority rules so it does not replace speech/mouth or locomotion unexpectedly.
- Next operator action: Coordinator review for `READY`; integrator should add a focused airborne reaction transition test.

## Automated integration gate

- Completed: `2026-07-13T03:58:14.099109+00:00`
- Source SHA-256: `2918867078b8110a1a8c2c071804c2f4e2e0f521268d4757774d10f62fb719dc`
- Generated library SHA-256: `dc0250f9ffc4ca7b2dc5364750af31a85b2a7509991d78c28351b9ca337b7b3b`
- Pose count after integration: `28`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-08/integration-result.json`
