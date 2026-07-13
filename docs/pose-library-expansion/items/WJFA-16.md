# Candidate WJFA-16

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_42 PM (6).png`

## Classification

- Proposed semantic ID: `front_staff_block_horizontal`
- Facing: `south`
- Locomotion: `idle`
- Actions: `["block", "guard", "staff_ready"]`
- Phase: `null`
- Tags: `["front", "defense", "block", "staff_horizontal", "wide_stance", "wings"]`
- Duplicate comparison: Not a duplicate of current `explaining` or `magic_cast`; it is a defensive/guard silhouette with the staff horizontal across the body.
- Recommended disposition: `ANALYZED`; useful if defensive/staff-ready actions are in scope.

## Anatomy and anchors

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | High | Grounded wide stance; default root works. |
| mouth | `[36, 35]` | Medium | Slight smile/grit. |
| left_eye | `[31, 30]` | Medium | Visual estimate. |
| right_eye | `[42, 30]` | Medium | Visual estimate. |
| left_foot | `[22, 94]` | Medium | Screen-left planted boot. |
| right_foot | `[55, 94]` | Medium | Screen-right planted boot. |
| left_hand | `[17, 47]` | Medium | Screen-left staff grip. |
| right_hand | `[44, 44]` | Medium | Screen-right staff grip. |
| staff_hand | `[17, 47]` | Medium | Primary staff hand; second grip should be region metadata. |
| staff_tip | `[69, 41]` | Low | Horizontal staff extends to right edge; left end is also important. |

## Visual assessment

- Character consistency: Strong; expression, robe, staff, wings, and hat remain coherent.
- Silhouette value: High for defensive/staff-ready action and as a transition from cast to idle.
- Transition neighbors: `front_idle`, `front_magic_staff_thrust`, `front_staff_spin_flourish`, and `front_point_direct_staff_held`.
- Known risks: Raw generator produces `92 x 96`; naive canonical shift has 150 out-of-bounds cells. Horizontal staff needs both end anchors or region metadata; single `staff_tip` default is insufficient.

## Integration record

- Source destination: Proposed only, not copied: `assets/reference/motion_sources/front_staff_block_horizontal.png`.
- Manifest entry: Proposed only: facing `south`, locomotion `idle`, actions `["block", "guard", "staff_ready"]`, tags as above, explicit anchors for both grips and staff endpoints.
- Runtime selection change: Proposed defensive/staff-ready action after action graph supports it.
- Generated library SHA-256: NOT RUN.
- Files changed: `docs/pose-library-expansion/items/WJFA-16.md`; `evidence/pose-library-expansion/WJFA-16/source-preview.png`; `evidence/pose-library-expansion/WJFA-16/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-16/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-16/intake-analysis.md`

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
- Commands run: Read workflow docs; inspected source PNG/current poses; generated intake previews; computed generator fit. Result: source `1122 x 1402`, raw generated `92 x 96`, 150 naive canonical out-of-bounds cells.
- Evidence produced: `evidence/pose-library-expansion/WJFA-16/source-preview.png`; `evidence/pose-library-expansion/WJFA-16/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-16/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-16/intake-analysis.md`
- Risks or uncertainty: Needs explicit horizontal-staff metadata and width handling.
- Next operator action: Coordinator review for `READY` if defensive staff poses are desired.

## Automated integration gate

- Completed: `2026-07-13T04:17:25.659478+00:00`
- Source SHA-256: `5fc228f1722fec151e9edb1f52ed6cfc30dabd346f3f4ffc2ea8b8dcf8f3edf4`
- Generated library SHA-256: `98ba30a57a8a1cf733a5bf2225870deac28a3fdfced6e5c99ddf72f02679f6ff`
- Pose count after integration: `35`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-16/integration-result.json`
