# Candidate WJFA-10

Status: `DUPLICATE`

Owner: `Hooke`

Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_11 PM (10).png`

## Classification

- Proposed semantic ID: `fly_front_hover_ready`
- Facing: `south`
- Locomotion: `flying`
- Actions: `idle`, `hover`
- Phase: `null`
- Tags: `front`, `flying`, `hover`, `airborne`, `staff_held`, `wings`, `duplicate_candidate`
- Duplicate comparison: Materially overlaps WJFA-01 as a front neutral hover. It is also close to current `front_idle` in body/staff arrangement, with the main difference being airborne feet and wings.
- Recommended disposition: `DUPLICATE`; prefer WJFA-01 as the canonical front hover if one neutral hover is needed.

## Anatomy and anchors

Coordinates are preserved for possible revival, but this candidate is not recommended for first-pass integration.

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | high | Virtual projected root below hovering body. |
| mouth | `[36, 35]` | medium | Slight open mouth. |
| left_eye | `[31, 25]` | medium | Viewer-left eye. |
| right_eye | `[41, 25]` | medium | Viewer-right eye. |
| left_foot | `[31, 86]` | medium | Airborne boot. |
| right_foot | `[43, 86]` | medium | Airborne boot. |
| left_hand | `[21, 55]` | medium | Free hand gesture. |
| right_hand | `[55, 51]` | medium | Staff hand. |
| staff_hand | `[55, 51]` | medium | Explicit override required if revived. |
| staff_tip | `[62, 13]` | medium | Crook top near upper right. |

## Visual assessment

- Character consistency: Strong.
- Silhouette value: Medium; pleasant hover pose but redundant with WJFA-01.
- Transition neighbors: WJFA-01 duplicate/base, WJFA-02 and WJFA-04 as actual flap/action neighbors.
- Known risks: Adding both WJFA-01 and WJFA-10 would bloat the library without adding a clear runtime transition state.

## Integration record

- Source destination: none recommended while duplicate.
- Manifest entry: none recommended; if revived, use `fly_front_hover_ready.png` with same flying/hover semantics as WJFA-01.
- Runtime selection change: none recommended while duplicate.
- Generated library SHA-256: not generated during intake.
- Files changed: `docs/pose-library-expansion/items/WJFA-10.md`, `evidence/pose-library-expansion/WJFA-10/source-preview.png`, `evidence/pose-library-expansion/WJFA-10/intake-analysis.md`

## Verification

| Gate | Result | Evidence |
|---|---|---|
| Deterministic generation | NOT RUN | Duplicate intake only. |
| Anchor bounds | PROPOSED | This record and `evidence/pose-library-expansion/WJFA-10/intake-analysis.md`. |
| Focused tests | NOT RUN | Duplicate intake only. |
| Full Python tests | NOT RUN | Duplicate intake only. |
| Strict transition matrix | NOT RUN | Duplicate intake only. |
| Live browser entry/hold/exit | NOT RUN | Duplicate intake only. |

## Handoff

- Previous status: `CLAIMED`
- Proposed next status: `DUPLICATE`
- Commands run: read workflow/tracker; inspected source PNG visually; `sips` reported `1122 x 1402`; copied source preview.
- Evidence produced: `source-preview.png`, `intake-analysis.md`
- Risks or uncertainty: If WJFA-01 is later rejected for crop/fit reasons, WJFA-10 can be reconsidered as a backup hover source.
- Next operator action: Coordinator should mark terminal duplicate or hold as backup pending WJFA-01 integration outcome.
