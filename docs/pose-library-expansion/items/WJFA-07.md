# Candidate WJFA-07

Status: `VERIFIED`
Owner: `coordinator`
Archive entry: `ChatGPT Image Jul 12, 2026, 08_15_10 PM (7).png`

## Classification

- Proposed semantic ID: `fly_southeast_banked_staff`
- Facing: `southeast`
- Locomotion: `flying`
- Actions: `fly`, `bank`
- Phase: `null`
- Tags: `southeast`, `flying`, `banked`, `turn`, `staff_right`, `airborne`, `wings`
- Duplicate comparison: Related to WJFA-06, but not a duplicate; this is the opposite bank/staff side and better bridge to WJFA-05/WJFA-09.
- Recommended disposition: `ANALYZED`; useful as a banked flight transition pose.

## Anatomy and anchors

Coordinates are proposed for the canonical `72 x 96` canvas with fixed projected root `[36, 95]`.

| Anchor | Proposed local coordinate | Confidence | Notes |
|---|---|---|---|
| root | `[36, 95]` | medium | Projected root below angled body. |
| mouth | `[38, 34]` | medium | Open mouth. |
| left_eye | `[33, 25]` | medium | Viewer-left eye. |
| right_eye | `[43, 26]` | medium | Viewer-right eye. |
| left_foot | `[24, 83]` | low | Airborne boot on viewer left. |
| right_foot | `[38, 90]` | low | Lower boot near center. |
| left_hand | `[23, 50]` | medium | Free pointing/gesture hand. |
| right_hand | `[55, 57]` | medium | Staff hand. |
| staff_hand | `[55, 57]` | medium | Explicit override required. |
| staff_tip | `[61, 32]` | low | Crook top; lower staff end also needs crop review. |

## Visual assessment

- Character consistency: Strong.
- Silhouette value: Medium-high; good diagonal bank and asymmetric wings.
- Transition neighbors: WJFA-06 opposite bank, WJFA-05 and WJFA-09 forward glide, WJFA-08 cheer/action.
- Known risks: Staff lower end approaches bottom crop; decide whether to preserve whole staff or crop consistently.

## Integration record

- Source destination: proposed `assets/reference/motion_sources/fly_southeast_banked_staff.png`
- Manifest entry: add one pose with `facing: "southeast"`, `locomotion: "flying"`, `actions: ["fly", "bank"]`, `phase: null`, and explicit staff anchors.
- Runtime selection change: add southeast banked flying transition selection.
- Generated library SHA-256: not generated during intake.
- Files changed: `docs/pose-library-expansion/items/WJFA-07.md`, `evidence/pose-library-expansion/WJFA-07/source-preview.png`, `evidence/pose-library-expansion/WJFA-07/intake-analysis.md`

## Verification

| Gate | Result | Evidence |
|---|---|---|
| Deterministic generation | NOT RUN | Intake only. |
| Anchor bounds | PROPOSED | This record and `evidence/pose-library-expansion/WJFA-07/intake-analysis.md`. |
| Focused tests | NOT RUN | Intake only. |
| Full Python tests | NOT RUN | Intake only. |
| Strict transition matrix | NOT RUN | Intake only. |
| Live browser entry/hold/exit | NOT RUN | Intake only. |

## Handoff

- Previous status: `CLAIMED`
- Proposed next status: `ANALYZED`
- Commands run: read workflow/tracker; inspected source PNG visually; `sips` reported `1122 x 1402`; copied source preview.
- Evidence produced: `source-preview.png`, `intake-analysis.md`
- Risks or uncertainty: Staff crop and direction label require integration-time visual checks.
- Next operator action: Coordinator review for `READY`; pair transition testing with WJFA-06 and WJFA-05/WJFA-09.

## Automated integration gate

- Completed: `2026-07-13T03:55:55.556495+00:00`
- Source SHA-256: `541a1249ae8a988381451cd456ec6c5c87bfd66129865c227a91bbb303acb5c2`
- Generated library SHA-256: `7d6e2096a7ee07024fc9d1c7abb287a61bcc29612f324f6eb284efcf7880b064`
- Pose count after integration: `27`
- Full Python tests: `passed`
- Transition matrix: `passed`
- Evidence: `evidence/pose-library-expansion/WJFA-07/integration-result.json`
