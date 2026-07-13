# Candidate WJFA-14

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_41 PM (4).png`

## Classification

- Proposed semantic ID: `front_airborne_fall_back_staff`
- Facing: `south` / front-family
- Locomotion: `airborne`
- Actions: `["flying", "falling", "reaction"]`
- Phase: `null`
- Tags: `["front_family", "airborne", "falling", "feet_up", "staff_held", "wings", "high_risk_baseline"]`
- Duplicate comparison: Not a duplicate of current poses. It is closest in purpose to airborne candidates like WJP2-04, but the body is tilted backward with both feet forward and staff on screen right.
- Recommended disposition: `ANALYZED`; review for `READY` only if flying/fall poses are accepted.

## Anatomy and anchors

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | Low | Canonical root should remain stage root; pose has no planted contact. |
| mouth | `[36, 34]` | Medium | Open mouth in tilted face. |
| left_eye | `[31, 29]` | Medium | Visual estimate. |
| right_eye | `[42, 29]` | Medium | Visual estimate. |
| left_foot | `[31, 86]` | Low | Airborne boot, not contact. |
| right_foot | `[61, 83]` | Low | Airborne boot, not contact. |
| left_hand | `[20, 47]` | Medium | Open screen-left hand. |
| right_hand | `[56, 41]` | Medium | Staff grip. |
| staff_hand | `[56, 41]` | Medium | Same as right hand. |
| staff_tip | `[68, 14]` | Low | Near right edge after rough canonical fit. |

## Visual assessment

- Character consistency: Strong visual identity, with coherent wings, robe, hat, beard, and staff.
- Silhouette value: High for airborne/falling reaction; visually distinct from grounded standing and walking poses.
- Transition neighbors: `front_crouch_landing_staff_plant`, `front_celebrate_jump_staff_up`, `front_run_charge_right_plant`, and `front_idle` only through an explicit airborne/fall transition.
- Known risks: Raw generator produces `87 x 96`; naive canonical shift has 210 out-of-bounds cells. Feet are not contacts, so current foot/baseline tests would need airborne semantics.

## Integration record

- Source destination: Proposed only, not copied: `assets/reference/motion_sources/front_airborne_fall_back_staff.png`.
- Manifest entry: Proposed only: facing `south`, locomotion `airborne`, actions `["flying", "falling", "reaction"]`, tags as above, explicit non-contact feet and staff anchors.
- Runtime selection change: Proposed future airborne/fall action; requires graph support for no planted foot.
- Generated library SHA-256: NOT RUN.
- Files changed: `docs/pose-library-expansion/items/WJFA-14.md`; `evidence/pose-library-expansion/WJFA-14/source-preview.png`; `evidence/pose-library-expansion/WJFA-14/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-14/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-14/intake-analysis.md`

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
- Commands run: Read workflow docs; inspected source PNG/current poses; generated intake previews; computed generator fit. Result: source `1122 x 1402`, raw generated `87 x 96`, 210 naive canonical out-of-bounds cells.
- Evidence produced: `evidence/pose-library-expansion/WJFA-14/source-preview.png`; `evidence/pose-library-expansion/WJFA-14/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-14/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-14/intake-analysis.md`
- Risks or uncertainty: Airborne root/contact semantics are not current defaults; fit requires width handling.
- Next operator action: Coordinator should decide whether flying/fall poses are in scope before integration.

## Automated integration gate

- Completed: `2026-07-13T04:12:02.311130+00:00`
- Source SHA-256: `4f18717a56425385e5d1a18b1982cc612e4f9f344bdba328b5cea44bb9061e0a`
- Generated library SHA-256: `9c4ef6b1d70d12edf914c5213fcc914fcc1db46c24cdc51fd350a83044e46f1e`
- Pose count after integration: `33`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-14/integration-result.json`
