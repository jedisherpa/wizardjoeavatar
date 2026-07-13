# Candidate WJFA-01

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_09 PM (1).png`

## Classification

- Proposed semantic ID: `fly_front_hover_neutral`
- Facing: `south`
- Locomotion: `flying`
- Actions: `idle`, `hover`
- Phase: `null` / hover base
- Tags: `front`, `flying`, `hover`, `airborne`, `staff_held`, `wings`
- Duplicate comparison: Closest current pose is `front_idle`; not a duplicate because this is airborne with active spread wings and feet above the projected ground. WJFA-10 materially overlaps this candidate.
- Recommended disposition: `ANALYZED`; good base pose if the runtime accepts a flying/hover locomotion family.

## Anatomy and anchors

Coordinates are proposed for the canonical `72 x 96` canvas with fixed projected root `[36, 95]`.

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | high | Virtual ground projection below hovering body; do not move root to feet. |
| mouth | `[36, 35]` | medium | Smile/open mouth; verify after crop. |
| left_eye | `[31, 25]` | medium | Viewer-left eye. |
| right_eye | `[41, 25]` | medium | Viewer-right eye. |
| left_foot | `[30, 86]` | medium | Airborne boot, above baseline. |
| right_foot | `[42, 86]` | medium | Airborne boot, above baseline. |
| left_hand | `[21, 57]` | medium | Free hand low at viewer left. |
| right_hand | `[55, 52]` | medium | Staff hand at viewer right. |
| staff_hand | `[55, 52]` | medium | Needs explicit override; current defaults put staff hand on the wrong side for front staff poses. |
| staff_tip | `[62, 13]` | medium | Crook top near upper right. |

## Visual assessment

- Character consistency: Strong; same hat, beard, robe, staff, and rainbow wings as current source family.
- Silhouette value: High for establishing a front hover state.
- Transition neighbors: `front_idle`, WJFA-02, WJFA-03, WJFA-04; WJFA-10 should be treated as duplicate/alternate.
- Known risks: Wide wings may force body scale down; root must remain projected ground rather than foot contact.

## Integration record

- Source destination: proposed `assets/reference/motion_sources/fly_front_hover_neutral.png`
- Manifest entry: add one pose with `facing: "south"`, `locomotion: "flying"`, `actions: ["idle", "hover"]`, `phase: null`, and explicit staff/foot anchors.
- Runtime selection change: requires a `flying` or `hover` locomotion/action branch; do not replace grounded `front_idle`.
- Generated library SHA-256: not generated during intake.
- Files changed: `docs/pose-library-expansion/items/WJFA-01.md`, `evidence/pose-library-expansion/WJFA-01/source-preview.png`, `evidence/pose-library-expansion/WJFA-01/intake-analysis.md`

## Verification

| Gate | Result | Evidence |
|---|---|---|
| Deterministic generation | NOT RUN | Intake only. |
| Anchor bounds | PROPOSED | This record and `evidence/pose-library-expansion/WJFA-01/intake-analysis.md`. |
| Focused tests | NOT RUN | Intake only. |
| Full Python tests | NOT RUN | Intake only. |
| Strict transition matrix | NOT RUN | Intake only. |
| Live browser entry/hold/exit | NOT RUN | Intake only. |

## Handoff

- Previous status: `CLAIMED`
- Proposed next status: `ANALYZED`
- Commands run: read workflow/tracker; inspected source PNG visually; `sips` reported `1122 x 1402`; copied source preview.
- Evidence produced: `source-preview.png`, `intake-analysis.md`
- Risks or uncertainty: Anchor coordinates need generator-time validation after actual canonical crop.
- Next operator action: Coordinator review for `READY`; integrate only after the flying locomotion semantics are approved.

## Automated integration gate

- Completed: `2026-07-13T03:43:29.895567+00:00`
- Source SHA-256: `556bf22f58af35652fcecd5f5b604eee6a52ca47b2fc430ff6d3392a68380450`
- Generated library SHA-256: `8ce4b72e0e8a6bc9e0d93c7eb48309f4cf1e7e8b3ebe8f73c2b196d50917fcc0`
- Pose count after integration: `21`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-01/integration-result.json`
