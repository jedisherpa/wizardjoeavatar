# Candidate WJFA-06

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_10 PM (6).png`

## Classification

- Proposed semantic ID: `fly_southwest_banked_staff`
- Facing: `southwest`
- Locomotion: `flying`
- Actions: `fly`, `bank`
- Phase: `null`
- Tags: `southwest`, `flying`, `banked`, `turn`, `staff_left`, `airborne`, `wings`
- Duplicate comparison: Not covered by `profile_left`, `profile_right`, `back_left`, or `back_right`; this is a front-family airborne bank with staff on viewer-left side.
- Recommended disposition: `ANALYZED`; useful as a bank/turn transition pose.

## Anatomy and anchors

Coordinates are proposed for the canonical `72 x 96` canvas with fixed projected root `[36, 95]`.

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | medium | Projected hover root under body center. |
| mouth | `[39, 33]` | medium | Face angled slightly. |
| left_eye | `[34, 25]` | medium | Viewer-left eye. |
| right_eye | `[44, 26]` | medium | Viewer-right eye. |
| left_foot | `[28, 84]` | low | Airborne trailing boot. |
| right_foot | `[41, 89]` | low | Lower boot near robe. |
| left_hand | `[15, 56]` | medium | Staff hand on viewer left. |
| right_hand | `[57, 51]` | medium | Forward free fist. |
| staff_hand | `[15, 56]` | medium | Explicit override required; opposite side from front staff defaults. |
| staff_tip | `[4, 22]` | low | Staff crook at far left. |

## Visual assessment

- Character consistency: Strong; same costume and wing style.
- Silhouette value: Medium-high; good for directional banking, less central than forward-glide poses.
- Transition neighbors: WJFA-07 opposite bank, WJFA-05/WJFA-09 forward flight, WJFA-01 front hover.
- Known risks: Staff side switch may create hand/staff popping unless transition neighbors are explicit.

## Integration record

- Source destination: proposed `assets/reference/motion_sources/fly_southwest_banked_staff.png`
- Manifest entry: add one pose with `facing: "southwest"`, `locomotion: "flying"`, `actions: ["fly", "bank"]`, `phase: null`, and explicit staff-side anchors.
- Runtime selection change: add banked flying transition selection; do not reuse walking turn semantics directly.
- Generated library SHA-256: not generated during intake.
- Files changed: `docs/pose-library-expansion/items/WJFA-06.md`, `evidence/pose-library-expansion/WJFA-06/source-preview.png`, `evidence/pose-library-expansion/WJFA-06/intake-analysis.md`

## Verification

| Gate | Result | Evidence |
|---|---|---|
| Deterministic generation | NOT RUN | Intake only. |
| Anchor bounds | PROPOSED | This record and `evidence/pose-library-expansion/WJFA-06/intake-analysis.md`. |
| Focused tests | NOT RUN | Intake only. |
| Full Python tests | NOT RUN | Intake only. |
| Strict transition matrix | NOT RUN | Intake only. |
| Live browser entry/hold/exit | NOT RUN | Intake only. |

## Handoff

- Previous status: `CLAIMED`
- Proposed next status: `ANALYZED`
- Commands run: read workflow/tracker; inspected source PNG visually; `sips` reported `1122 x 1402`; copied source preview.
- Evidence produced: `source-preview.png`, `intake-analysis.md`
- Risks or uncertainty: Direction label and staff-side anchors need integrator validation against runtime direction naming.
- Next operator action: Coordinator review for `READY`; integrate only with an explicit bank/turn transition test.

## Automated integration gate

- Completed: `2026-07-13T03:53:41.315130+00:00`
- Source SHA-256: `7f998a80d8959ae639fa1e1aa3dc672e30e9d8569943b7458afb4433ff7edd3b`
- Generated library SHA-256: `d0a793befaac143fb5bd6d47ace0297d2575fd15146937b90371dcb341148110`
- Pose count after integration: `26`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-06/integration-result.json`
