# Candidate WJFA-12

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_41 PM (2).png`

## Classification

- Proposed semantic ID: `front_crouch_landing_staff_plant`
- Facing: `south` / front-family
- Locomotion: `landing`
- Actions: `["landing", "crouch", "staff_plant"]`
- Phase: `null`
- Tags: `["front_family", "landing", "crouch", "hand_contact", "staff_plant", "wings", "high_risk_baseline"]`
- Duplicate comparison: Related to current `front_idle` only by staff/front view and related to WJP2 crouch-style candidates, but the hand-on-ground landing silhouette is distinct. Not a material duplicate of a production pose.
- Recommended disposition: `ANALYZED`; review for `READY` only if crouch/landing poses are in scope.

## Anatomy and anchors

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | Low | Canonical root should remain fixed, but pose has hand and boot contacts competing for baseline. |
| mouth | `[36, 39]` | Medium | Neutral/closed mouth lower than default due crouch. |
| left_eye | `[31, 34]` | Medium | Visual estimate. |
| right_eye | `[41, 34]` | Medium | Visual estimate. |
| left_foot | `[15, 94]` | Medium | Screen-left hand is lower than foot; this anchor marks low left contact region. |
| right_foot | `[50, 91]` | Medium | Bent screen-right boot. |
| left_hand | `[18, 92]` | Medium | Ground-contact hand should be explicit. |
| right_hand | `[56, 39]` | Medium | Staff grip. |
| staff_hand | `[56, 39]` | Medium | Same as right hand. |
| staff_tip | `[68, 6]` | Low | Staff top near edge; high fit risk. |

## Visual assessment

- Character consistency: Strong identity, but crouch compresses the robe and face relative to current standing poses.
- Silhouette value: Valuable landing/recovery pose; gives a grounded endpoint for flying/action sequences.
- Transition neighbors: `front_idle`, `front_run_charge_right_plant`, airborne/fall poses such as `front_airborne_fall_back_staff`, and staff-block poses.
- Known risks: Raw generator produces `94 x 96`; naive canonical shift has 562 out-of-bounds cells, the worst in this batch. Needs tighter crop/downscale and explicit hand-contact versus foot-contact metadata.

## Integration record

- Source destination: Proposed only, not copied: `assets/reference/motion_sources/front_crouch_landing_staff_plant.png`.
- Manifest entry: Proposed only: facing `south`, locomotion `landing`, actions `["landing", "crouch", "staff_plant"]`, tags as above, explicit anchors for hand contact, bent boot, staff hand, and staff tip.
- Runtime selection change: Proposed landing/recovery action only; no current runtime mapping should be changed during intake.
- Generated library SHA-256: NOT RUN.
- Files changed: `docs/pose-library-expansion/items/WJFA-12.md`; `evidence/pose-library-expansion/WJFA-12/source-preview.png`; `evidence/pose-library-expansion/WJFA-12/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-12/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-12/intake-analysis.md`

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
- Commands run: Read workflow docs; inspected source PNG/current poses; generated intake previews; computed generator fit. Result: source `1122 x 1402`, raw generated `94 x 96`, 562 naive canonical out-of-bounds cells.
- Evidence produced: `evidence/pose-library-expansion/WJFA-12/source-preview.png`; `evidence/pose-library-expansion/WJFA-12/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-12/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-12/intake-analysis.md`
- Risks or uncertainty: Baseline/contact semantics are ambiguous because hand, staff, and foot all imply support.
- Next operator action: Coordinator should decide whether landing/crouch belongs in the accepted action set before integration work.

## Automated integration gate

- Completed: `2026-07-13T04:06:55.060842+00:00`
- Source SHA-256: `281861e5eaf61e19cd773097787f7d035ac50e8574e99c4941c52e1a0772932a`
- Generated library SHA-256: `3699ac0942fb8862475355912d243644cd024a116c3bff695949ea23a768cef5`
- Pose count after integration: `31`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-12/integration-result.json`
