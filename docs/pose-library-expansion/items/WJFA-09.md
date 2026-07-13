# Candidate WJFA-09

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_11 PM (9).png`

## Classification

- Proposed semantic ID: `fly_southeast_staff_forward`
- Facing: `southeast`
- Locomotion: `flying`
- Actions: `fly`, `glide`, `staff_forward`
- Phase: `0.65`
- Tags: `southeast`, `flying`, `forward_glide`, `staff_forward`, `prone`, `airborne`, `wings`
- Duplicate comparison: Similar to WJFA-05 but not a duplicate; this has a more camera-facing head and staff-forward staging, while WJFA-05 is a cleaner staff-trailing glide.
- Recommended disposition: `ANALYZED`; useful as forward-flight/action variant, lower priority than WJFA-05 if only one forward glide is accepted.

## Anatomy and anchors

Coordinates are proposed for the canonical `72 x 96` canvas with fixed projected root `[36, 95]`.

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | medium | Projected root below pitched body. |
| mouth | `[41, 36]` | medium | Face close to camera, mouth partly open. |
| left_eye | `[36, 28]` | medium | Viewer-left eye. |
| right_eye | `[46, 29]` | medium | Viewer-right eye. |
| left_foot | `[15, 76]` | low | Trailing boot at lower left. |
| right_foot | `[31, 81]` | low | Other boot mostly under robe. |
| left_hand | `[22, 45]` | low | Arm tucked/trailing. |
| right_hand | `[56, 45]` | medium | Staff-forward hand. |
| staff_hand | `[56, 45]` | medium | Explicit override required. |
| staff_tip | `[64, 24]` | low | Crook high at viewer right. |

## Visual assessment

- Character consistency: Strong, but the prone camera angle changes face/body proportions.
- Silhouette value: High; offers staff-forward flight/action contrast.
- Transition neighbors: WJFA-05 forward glide, WJFA-07 banked transition, WJFA-01 hover recovery.
- Known risks: Overlaps WJFA-05 semantically; integrate after deciding whether both forward-flight variants are needed.

## Integration record

- Source destination: proposed `assets/reference/motion_sources/fly_southeast_staff_forward.png`
- Manifest entry: add one pose with `facing: "southeast"`, `locomotion: "flying"`, `actions: ["fly", "glide", "staff_forward"]`, `phase: 0.65`, and explicit diagonal anchors.
- Runtime selection change: add as forward-flight or staff-forward action variant; do not use as generic walking/turning.
- Generated library SHA-256: not generated during intake.
- Files changed: `docs/pose-library-expansion/items/WJFA-09.md`, `evidence/pose-library-expansion/WJFA-09/source-preview.png`, `evidence/pose-library-expansion/WJFA-09/intake-analysis.md`

## Verification

| Gate | Result | Evidence |
|---|---|---|
| Deterministic generation | NOT RUN | Intake only. |
| Anchor bounds | PROPOSED | This record and `evidence/pose-library-expansion/WJFA-09/intake-analysis.md`. |
| Focused tests | NOT RUN | Intake only. |
| Full Python tests | NOT RUN | Intake only. |
| Strict transition matrix | NOT RUN | Intake only. |
| Live browser entry/hold/exit | NOT RUN | Intake only. |

## Handoff

- Previous status: `CLAIMED`
- Proposed next status: `ANALYZED`
- Commands run: read workflow/tracker; inspected source PNG visually; `sips` reported `1122 x 1402`; copied source preview.
- Evidence produced: `source-preview.png`, `intake-analysis.md`
- Risks or uncertainty: May be redundant if WJFA-05 is accepted as the only forward-glide pose.
- Next operator action: Coordinator review for `READY` or defer until WJFA-05 is evaluated.

## Automated integration gate

- Completed: `2026-07-13T04:00:35.679226+00:00`
- Source SHA-256: `3dc54a583d0df0053ba9b532235a46f9fda8908e95dd4283b37074e709909a9b`
- Generated library SHA-256: `4ed3ebd0b04861bf10541a1acb58d08fdfa99c84446bfa3da75dd77537ade153`
- Pose count after integration: `29`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-09/integration-result.json`
