# Pose Expansion Completion

Date: 2026-07-12

## Result

- Baseline production poses: 10
- Supplied new candidates: 30
- Distinct candidates verified and integrated: 29
- Duplicate candidates excluded: 1
- Final Python production library: 39 poses
- Final generated-library SHA-256: `1200e2891902cd1f3147d2c2d298dd2d99313708fbc8e90034376500e1843037`
- Integration lock: clear

`WJFA-10` (`fly_front_hover_ready`) was excluded because its source image duplicates `WJFA-01` (`fly_front_hover_neutral`). The duplicate remains in the tracker with its evidence; it was not silently discarded.

## Reproducible inputs

| Archive | SHA-256 | Candidate role |
|---|---|---|
| `Wizard Joe Poses.zip` | `eb57e0e8c2313a7404e3ec0dd3638ce770eedfafd42671888cd18f954f8d482c` | 10-pose baseline and target image |
| `Wizard Joe Poses 2.zip` | `2d81094336d8151958056b635c77998b2143a596af76200e0dbba7a175551df6` | 10 integrated candidates |
| `Wizard Joe Poses Flying and Action.zip` | `c00e56b139c00c42d51652b3683109ae38263768dc959a25b17f83e533b5bfff` | 19 integrated candidates and 1 duplicate |

Each accepted candidate was applied through `tools/integrate_pose_candidate.py`. That transaction acquires the shared lock, copies one source, updates one manifest entry, regenerates the canonical 72x96 library, validates anchors, runs the full Python suite and strict transition matrix, records evidence, and rolls back on failure. `tools/integrate_pose_queue.py` repeats that transaction serially for a prepared queue.

## Verification

- Deterministic generation: passed, 39 poses.
- `python3 -m unittest discover tests`: 62 passed.
- `python3 tools/verify_animation_quality.py --strict`: 32/32 scenarios passed with zero issues.
- `python3 tools/validate_pose_expansion_workflow.py`: 30 candidates, no errors, integration lock clear.
- `git diff --check`: passed.

## Live demo

The Python server at `http://127.0.0.1:8765/` was exercised through the Play control in a real browser.

- Production poses expected and observed: 39/39
- Missing poses: 0
- Distinct sampled world positions: 258
- Intermediate compositor transitions observed: yes
- Browser console errors: 0
- Play returned to idle: yes
- Final state returned to the centered, stopped position with no pose override: yes

See [Demo Play Verification](DEMO_PLAY_VERIFICATION.md) and [the final browser capture](demo-all-39-poses-moving.png).
