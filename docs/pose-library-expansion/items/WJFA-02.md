# Candidate WJFA-02

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_09 PM (2).png`

## Classification

- Proposed semantic ID: `fly_front_knee_up`
- Facing: `south`
- Locomotion: `flying`
- Actions: `fly`, `hover`
- Phase: `0.25`
- Tags: `front`, `flying`, `flap_cycle`, `knee_up`, `airborne`, `staff_held`, `wings`
- Duplicate comparison: Not a duplicate of `walk_front_left` or `walk_front_right`; the feet are airborne and one knee is lifted as part of a flying motion.
- Recommended disposition: `ANALYZED`; useful as an active front flying phase.

## Anatomy and anchors

Coordinates are proposed for the canonical `72 x 96` canvas with fixed projected root `[36, 95]`.

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | high | Virtual ground projection below airborne body. |
| mouth | `[36, 35]` | medium | Open mouth visible. |
| left_eye | `[31, 25]` | medium | Viewer-left eye. |
| right_eye | `[41, 25]` | medium | Viewer-right eye. |
| left_foot | `[27, 88]` | medium | Lower trailing boot, airborne. |
| right_foot | `[43, 80]` | medium | Raised knee/boot. |
| left_hand | `[24, 58]` | medium | Forward/free fist. |
| right_hand | `[55, 53]` | medium | Staff hand. |
| staff_hand | `[55, 53]` | medium | Explicit side override required. |
| staff_tip | `[63, 13]` | medium | Crook top. |

## Visual assessment

- Character consistency: Strong; same face, hat, robe colors, staff, and wing language.
- Silhouette value: High for front flap cycle because leg and wing pose differ from hover.
- Transition neighbors: WJFA-01 entry/hold, WJFA-03 upstroke, WJFA-04 downstroke.
- Known risks: Raised knee can be confused with walking unless metadata keeps it in `flying`.

## Integration record

- Source destination: proposed `assets/reference/motion_sources/fly_front_knee_up.png`
- Manifest entry: add one pose with `facing: "south"`, `locomotion: "flying"`, `actions: ["fly", "hover"]`, `phase: 0.25`, and explicit airborne foot anchors.
- Runtime selection change: add to front flying clip between neutral hover and wings-up/down phases.
- Generated library SHA-256: not generated during intake.
- Files changed: `docs/pose-library-expansion/items/WJFA-02.md`, `evidence/pose-library-expansion/WJFA-02/source-preview.png`, `evidence/pose-library-expansion/WJFA-02/intake-analysis.md`

## Verification

| Gate | Result | Evidence |
|---|---|---|
| Deterministic generation | NOT RUN | Intake only. |
| Anchor bounds | PROPOSED | This record and `evidence/pose-library-expansion/WJFA-02/intake-analysis.md`. |
| Focused tests | NOT RUN | Intake only. |
| Full Python tests | NOT RUN | Intake only. |
| Strict transition matrix | NOT RUN | Intake only. |
| Live browser entry/hold/exit | NOT RUN | Intake only. |

## Handoff

- Previous status: `CLAIMED`
- Proposed next status: `ANALYZED`
- Commands run: read workflow/tracker; inspected source PNG visually; `sips` reported `1122 x 1402`; copied source preview.
- Evidence produced: `source-preview.png`, `intake-analysis.md`
- Risks or uncertainty: Canonical fit must avoid shrinking the face too much to include full wing width.
- Next operator action: Coordinator review for `READY`; integrator should wire this only after a front flying clip exists.

## Automated integration gate

- Completed: `2026-07-13T03:45:25.016009+00:00`
- Source SHA-256: `64abc6bb057e383f4d40ab9e2e90ab934ed3d4c70733754daf3f4fe90530d15f`
- Generated library SHA-256: `89cf224e5ee1b3bea45318f334ed5c1aee1a515125b7bd8192f39839ac8ff7f4`
- Pose count after integration: `22`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-02/integration-result.json`
