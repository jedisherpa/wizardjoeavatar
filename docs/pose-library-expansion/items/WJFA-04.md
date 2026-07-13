# Candidate WJFA-04

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_10 PM (4).png`

## Classification

- Proposed semantic ID: `fly_front_wings_down`
- Facing: `south`
- Locomotion: `flying`
- Actions: `fly`, `hover`
- Phase: `0.75`
- Tags: `front`, `flying`, `flap_cycle`, `wings_down`, `airborne`, `staff_held`
- Duplicate comparison: Not a duplicate of `front_idle`; feet are suspended and wings form a broad downward arc.
- Recommended disposition: `ANALYZED`; useful as downstroke sample for front flying.

## Anatomy and anchors

Coordinates are proposed for the canonical `72 x 96` canvas with fixed projected root `[36, 95]`.

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | high | Projected root/shadow, not body bottom. |
| mouth | `[36, 35]` | medium | Open mouth. |
| left_eye | `[31, 25]` | medium | Viewer-left eye. |
| right_eye | `[41, 25]` | medium | Viewer-right eye. |
| left_foot | `[31, 84]` | medium | Airborne boot. |
| right_foot | `[42, 84]` | medium | Airborne boot. |
| left_hand | `[20, 51]` | medium | Free fist. |
| right_hand | `[56, 47]` | medium | Staff hand. |
| staff_hand | `[56, 47]` | medium | Explicit override required. |
| staff_tip | `[62, 14]` | medium | Crook near upper right. |

## Visual assessment

- Character consistency: Strong.
- Silhouette value: High; gives the first set a complete wing cycle with WJFA-02 and WJFA-03.
- Transition neighbors: WJFA-03 upstroke, WJFA-01 hover recovery, WJFA-02 mid-flap.
- Known risks: Very wide low wings may squeeze body scale or collide with ground shadow/canonical baseline.

## Integration record

- Source destination: proposed `assets/reference/motion_sources/fly_front_wings_down.png`
- Manifest entry: add one pose with `facing: "south"`, `locomotion: "flying"`, `actions: ["fly", "hover"]`, `phase: 0.75`, tags including `wings_down`.
- Runtime selection change: add as front flying clip downstroke sample.
- Generated library SHA-256: not generated during intake.
- Files changed: `docs/pose-library-expansion/items/WJFA-04.md`, `evidence/pose-library-expansion/WJFA-04/source-preview.png`, `evidence/pose-library-expansion/WJFA-04/intake-analysis.md`

## Verification

| Gate | Result | Evidence |
|---|---|---|
| Deterministic generation | NOT RUN | Intake only. |
| Anchor bounds | PROPOSED | This record and `evidence/pose-library-expansion/WJFA-04/intake-analysis.md`. |
| Focused tests | NOT RUN | Intake only. |
| Full Python tests | NOT RUN | Intake only. |
| Strict transition matrix | NOT RUN | Intake only. |
| Live browser entry/hold/exit | NOT RUN | Intake only. |

## Handoff

- Previous status: `CLAIMED`
- Proposed next status: `ANALYZED`
- Commands run: read workflow/tracker; inspected source PNG visually; `sips` reported `1122 x 1402`; copied source preview.
- Evidence produced: `source-preview.png`, `intake-analysis.md`
- Risks or uncertainty: Wing tips may dominate the crop and reduce face readability.
- Next operator action: Coordinator review for `READY`; evaluate as part of the same front flying clip as WJFA-01..03.

## Automated integration gate

- Completed: `2026-07-13T03:49:26.153882+00:00`
- Source SHA-256: `61f6f8b1c1137011440fae8b96f3e456a8c1db3e1b3bd7cd3615c2f7581ad46f`
- Generated library SHA-256: `0ad55ebd3f8f24a03e16387029882c3ed9f362951462602b6a6db7b12c6ff831`
- Pose count after integration: `24`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-04/integration-result.json`
