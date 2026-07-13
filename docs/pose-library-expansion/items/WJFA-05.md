# Candidate WJFA-05

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_10 PM (5).png`

## Classification

- Proposed semantic ID: `fly_southeast_forward_glide`
- Facing: `southeast`
- Locomotion: `flying`
- Actions: `fly`, `glide`
- Phase: `0.35`
- Tags: `southeast`, `flying`, `forward_glide`, `prone`, `airborne`, `staff_trailing`, `wings`
- Duplicate comparison: No current pose provides a prone forward-flight silhouette. WJFA-09 is related but has staff-forward staging rather than staff-trailing glide.
- Recommended disposition: `ANALYZED`; high-priority candidate because it expands beyond front hover.

## Anatomy and anchors

Coordinates are proposed for the canonical `72 x 96` canvas with fixed projected root `[36, 95]`.

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | medium | Projected shadow point under diagonal body mass. |
| mouth | `[44, 31]` | medium | Face is turned to viewer right. |
| left_eye | `[39, 25]` | medium | Viewer-left visible eye. |
| right_eye | `[48, 25]` | medium | Viewer-right visible eye. |
| left_foot | `[20, 78]` | low | Trailing boot at lower left. |
| right_foot | `[28, 80]` | low | Other trailing boot partly occluded. |
| left_hand | `[14, 48]` | medium | Staff/trailing hand at viewer left. |
| right_hand | `[58, 48]` | medium | Forward free hand. |
| staff_hand | `[14, 48]` | medium | Staff is trailing left; explicit override required. |
| staff_tip | `[4, 44]` | low | Crook/tip is far left and may be cropped; verify in generator. |

## Visual assessment

- Character consistency: Strong, though prone body changes the robe read.
- Silhouette value: Very high; most semantically distinct pose in WJFA-01..10.
- Transition neighbors: WJFA-07 banked entry, WJFA-09 staff-forward variant, WJFA-01 front hover recovery.
- Known risks: Long diagonal body and staff may be hard to fit without shrinking the character.

## Integration record

- Source destination: proposed `assets/reference/motion_sources/fly_southeast_forward_glide.png`
- Manifest entry: add one pose with `facing: "southeast"`, `locomotion: "flying"`, `actions: ["fly", "glide"]`, `phase: 0.35`, and explicit staff/foot anchors.
- Runtime selection change: add southeast flying/glide branch, not walking or turn.
- Generated library SHA-256: not generated during intake.
- Files changed: `docs/pose-library-expansion/items/WJFA-05.md`, `evidence/pose-library-expansion/WJFA-05/source-preview.png`, `evidence/pose-library-expansion/WJFA-05/intake-analysis.md`

## Verification

| Gate | Result | Evidence |
|---|---|---|
| Deterministic generation | NOT RUN | Intake only. |
| Anchor bounds | PROPOSED | This record and `evidence/pose-library-expansion/WJFA-05/intake-analysis.md`. |
| Focused tests | NOT RUN | Intake only. |
| Full Python tests | NOT RUN | Intake only. |
| Strict transition matrix | NOT RUN | Intake only. |
| Live browser entry/hold/exit | NOT RUN | Intake only. |

## Handoff

- Previous status: `CLAIMED`
- Proposed next status: `ANALYZED`
- Commands run: read workflow/tracker; inspected source PNG visually; `sips` reported `1122 x 1402`; copied source preview.
- Evidence produced: `source-preview.png`, `intake-analysis.md`
- Risks or uncertainty: Staff tip and trailing boots need post-crop anchor correction; may require a flight-specific canonical fit strategy.
- Next operator action: Coordinator review for `READY`; consider integrating before lower-value hover duplicates because it adds a new locomotion silhouette.

## Automated integration gate

- Completed: `2026-07-13T03:51:31.512232+00:00`
- Source SHA-256: `9507fd79854bbea38075b9602316fb7ff9a82cfcfa77a595ba0fd25dc58660e6`
- Generated library SHA-256: `01c1ee7dc0f0604271c85e8a2b8a90624279d183beeec9ae76b58bc944217ce1`
- Pose count after integration: `25`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-05/integration-result.json`
