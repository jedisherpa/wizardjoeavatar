# Candidate WJFA-15

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_41 PM (5).png`

## Classification

- Proposed semantic ID: `front_celebrate_wings_staff_up`
- Facing: `south`
- Locomotion: `idle`
- Actions: `["celebrate", "reaction"]`
- Phase: `null`
- Tags: `["front", "celebrate", "reaction", "wings_spread", "staff_up", "arms_up", "wings"]`
- Duplicate comparison: Related to WJP2-08 and WJFA-18 as an arms-up celebration family, but this one is grounded with full wing spread and a raised staff. It is not a current-pose duplicate.
- Recommended disposition: `ANALYZED`; strongest low-moderate-risk celebration candidate in this assigned batch.

## Anatomy and anchors

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | High | Grounded stance; canonical default is suitable. |
| mouth | `[36, 35]` | Medium | Open smiling mouth. |
| left_eye | `[31, 30]` | Medium | Visual estimate. |
| right_eye | `[41, 30]` | Medium | Visual estimate. |
| left_foot | `[27, 94]` | Medium | Screen-left planted boot. |
| right_foot | `[52, 94]` | Medium | Screen-right planted boot. |
| left_hand | `[54, 28]` | Medium | Raised fist on screen right. |
| right_hand | `[18, 26]` | Medium | Raised staff hand on screen left. |
| staff_hand | `[18, 26]` | Medium | Same as right hand. |
| staff_tip | `[12, 3]` | Low | Staff top is very high; verify bounds after final crop. |

## Visual assessment

- Character consistency: Strong; all core WizardJoe elements are present and readable.
- Silhouette value: High for celebration/reaction; the wide wings give a clear held pose.
- Transition neighbors: `front_idle`, `front_celebrate_jump_staff_up`, `front_point_direct_staff_held`, and `magic_cast`/reaction exits.
- Known risks: Raw generator produces `77 x 96`; naive canonical shift has only 12 out-of-bounds cells, so this is near-fit but still needs crop/anchor validation for staff top and wing edges.

## Integration record

- Source destination: Proposed only, not copied: `assets/reference/motion_sources/front_celebrate_wings_staff_up.png`.
- Manifest entry: Proposed only: facing `south`, locomotion `idle`, actions `["celebrate", "reaction"]`, tags as above, explicit raised hand/staff anchors.
- Runtime selection change: Proposed reaction/celebrate held pose after graph supports action variants.
- Generated library SHA-256: NOT RUN.
- Files changed: `docs/pose-library-expansion/items/WJFA-15.md`; `evidence/pose-library-expansion/WJFA-15/source-preview.png`; `evidence/pose-library-expansion/WJFA-15/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-15/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-15/intake-analysis.md`

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
- Commands run: Read workflow docs; inspected source PNG/current and other celebration candidates; generated intake previews; computed generator fit. Result: source `1122 x 1402`, raw generated `77 x 96`, 12 naive canonical out-of-bounds cells.
- Evidence produced: `evidence/pose-library-expansion/WJFA-15/source-preview.png`; `evidence/pose-library-expansion/WJFA-15/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-15/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-15/intake-analysis.md`
- Risks or uncertainty: Wings remain a visual-contract issue; staff top is close to upper boundary.
- Next operator action: Coordinator review for `READY` as a grounded celebration/reaction pose.

## Automated integration gate

- Completed: `2026-07-13T04:14:42.114181+00:00`
- Source SHA-256: `59d4a53e2bad336d45f75cf0263bcc2d2edced31f777bd035add448944732df1`
- Generated library SHA-256: `d4c3cfaab604dadefb140684c81f83b1f3a02eda2917c3b530b2297b4ec03649`
- Pose count after integration: `34`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-15/integration-result.json`
