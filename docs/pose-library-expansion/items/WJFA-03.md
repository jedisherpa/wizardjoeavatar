# Candidate WJFA-03

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_09 PM (3).png`

## Classification

- Proposed semantic ID: `fly_front_wings_up`
- Facing: `south`
- Locomotion: `flying`
- Actions: `fly`, `hover`
- Phase: `0.5`
- Tags: `front`, `flying`, `flap_cycle`, `wings_up`, `airborne`, `staff_held`
- Duplicate comparison: Not present in current library; the vertical wing upstroke silhouette is materially different from `front_idle`, walking, and `magic_cast`.
- Recommended disposition: `ANALYZED`; strong flap-cycle sample.

## Anatomy and anchors

Coordinates are proposed for the canonical `72 x 96` canvas with fixed projected root `[36, 95]`.

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | high | Virtual projected root below hover shadow. |
| mouth | `[36, 35]` | medium | Smile/open mouth. |
| left_eye | `[31, 25]` | medium | Viewer-left eye. |
| right_eye | `[41, 25]` | medium | Viewer-right eye. |
| left_foot | `[31, 86]` | medium | Airborne boot. |
| right_foot | `[42, 87]` | medium | Airborne boot. |
| left_hand | `[23, 56]` | medium | Free hand. |
| right_hand | `[57, 55]` | medium | Staff hand. |
| staff_hand | `[57, 55]` | medium | Explicit override required. |
| staff_tip | `[65, 17]` | low | Staff crook high/right; verify after full-wing fit. |

## Visual assessment

- Character consistency: Strong, with good face and costume continuity.
- Silhouette value: Very high for wing upstroke and flight readability.
- Transition neighbors: WJFA-02 before/after, WJFA-04 downstroke, WJFA-01 hover hold.
- Known risks: Tall wings may be the limiting crop dimension; body may become smaller than current front poses.

## Integration record

- Source destination: proposed `assets/reference/motion_sources/fly_front_wings_up.png`
- Manifest entry: add one pose with `facing: "south"`, `locomotion: "flying"`, `actions: ["fly", "hover"]`, `phase: 0.5`, tags including `wings_up`.
- Runtime selection change: add as front flying clip upstroke sample.
- Generated library SHA-256: not generated during intake.
- Files changed: `docs/pose-library-expansion/items/WJFA-03.md`, `evidence/pose-library-expansion/WJFA-03/source-preview.png`, `evidence/pose-library-expansion/WJFA-03/intake-analysis.md`

## Verification

| Gate | Result | Evidence |
|---|---|---|
| Deterministic generation | NOT RUN | Intake only. |
| Anchor bounds | PROPOSED | This record and `evidence/pose-library-expansion/WJFA-03/intake-analysis.md`. |
| Focused tests | NOT RUN | Intake only. |
| Full Python tests | NOT RUN | Intake only. |
| Strict transition matrix | NOT RUN | Intake only. |
| Live browser entry/hold/exit | NOT RUN | Intake only. |

## Handoff

- Previous status: `CLAIMED`
- Proposed next status: `ANALYZED`
- Commands run: read workflow/tracker; inspected source PNG visually; `sips` reported `1122 x 1402`; copied source preview.
- Evidence produced: `source-preview.png`, `intake-analysis.md`
- Risks or uncertainty: Tall wing tips and staff tip need crop validation together.
- Next operator action: Coordinator review for `READY`; verify transition churn against WJFA-02 and WJFA-04 before integration.

## Automated integration gate

- Completed: `2026-07-13T03:47:23.895149+00:00`
- Source SHA-256: `f863a43341be44101bc7780f2e4ee4e806c73a1f6dc6eb8f5864d99ec24ea4ab`
- Generated library SHA-256: `45144c6b5f9a4969f54034b3b5e7fa6b5d317b3d69bb467210a210e514ec7907`
- Pose count after integration: `23`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-03/integration-result.json`
