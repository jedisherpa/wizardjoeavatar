# Candidate WJFA-18

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_42 PM (8).png`

## Classification

- Proposed semantic ID: `front_celebrate_jump_staff_up`
- Facing: `south`
- Locomotion: `jump`
- Actions: `["celebrate", "reaction", "jump"]`
- Phase: `null`
- Tags: `["front", "celebrate", "jump", "airborne", "staff_up", "fist_up", "wings"]`
- Duplicate comparison: Similar to WJP2-04 and WJFA-15 in the celebration family. It is not a current-production duplicate; versus WJFA-15 it is airborne with knees tucked and both contacts lifted, so keep as a separate candidate pending coordinator scope.
- Recommended disposition: `ANALYZED`; review for `READY` only if airborne celebration poses are accepted.

## Anatomy and anchors

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | Low | Stage root remains fixed; character is airborne above it. |
| mouth | `[36, 37]` | Medium | Open cheering mouth. |
| left_eye | `[31, 32]` | Medium | Visual estimate. |
| right_eye | `[42, 32]` | Medium | Visual estimate. |
| left_foot | `[27, 86]` | Low | Airborne boot, no contact. |
| right_foot | `[49, 88]` | Low | Airborne boot, no contact. |
| left_hand | `[21, 24]` | Medium | Raised fist. |
| right_hand | `[54, 23]` | Medium | Raised staff hand. |
| staff_hand | `[54, 23]` | Medium | Same as right hand. |
| staff_tip | `[61, 5]` | Medium | Staff top inside rough bounds. |

## Visual assessment

- Character consistency: Strong. Reads as the same winged WizardJoe with a cheerful jump.
- Silhouette value: High if jump/celebrate animation is desired; lower if only grounded actions are accepted.
- Transition neighbors: `front_celebrate_wings_staff_up`, WJP2-04-style jump reaction, `front_crouch_landing_staff_plant`, and `front_idle`.
- Known risks: Airborne foot anchors must be marked non-contact; otherwise root/feet gates will fail. Fit itself is good: raw generated `75 x 96`, zero naive canonical out-of-bounds cells.

## Integration record

- Source destination: Proposed only, not copied: `assets/reference/motion_sources/front_celebrate_jump_staff_up.png`.
- Manifest entry: Proposed only: facing `south`, locomotion `jump`, actions `["celebrate", "reaction", "jump"]`, tags as above, explicit non-contact feet and raised hand/staff anchors.
- Runtime selection change: Proposed airborne celebration key after graph supports jump/flying states.
- Generated library SHA-256: NOT RUN.
- Files changed: `docs/pose-library-expansion/items/WJFA-18.md`; `evidence/pose-library-expansion/WJFA-18/source-preview.png`; `evidence/pose-library-expansion/WJFA-18/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-18/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-18/intake-analysis.md`

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
- Commands run: Read workflow docs; inspected source PNG and related celebration candidates; generated intake previews; computed generator fit. Result: source `1122 x 1402`, raw generated `75 x 96`, 0 naive canonical out-of-bounds cells.
- Evidence produced: `evidence/pose-library-expansion/WJFA-18/source-preview.png`; `evidence/pose-library-expansion/WJFA-18/canonical-proposal-preview.png`; `evidence/pose-library-expansion/WJFA-18/intake-analysis.json`; `evidence/pose-library-expansion/WJFA-18/intake-analysis.md`
- Risks or uncertainty: Duplicates the broad purpose of WJP2-04/WJFA-15 but not the exact silhouette; coordinator should pick preferred celebration family members to avoid overpopulating the graph.
- Next operator action: Coordinator should decide whether to keep as a separate airborne celebration pose or collapse into another celebration candidate before `READY`.

## Automated integration gate

- Completed: `2026-07-13T04:23:04.755379+00:00`
- Source SHA-256: `95a5a88b1642f1e8b50f84527185757b6d9dcd45921bea787b39c775e0fdcee7`
- Generated library SHA-256: `ab0d0eab2843a17628b6957145e2a4794d7a9d548acfa79c4bf9ef570e815296`
- Pose count after integration: `37`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-18/integration-result.json`
