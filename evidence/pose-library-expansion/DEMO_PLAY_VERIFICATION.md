# Demo Play Verification

Date: 2026-07-12

URL: `http://127.0.0.1:8765/`

## Contract

The Play control fetches the generated reference pose library, starts a looping world-space path, presents every production pose through the normal compositor, returns to center, and stops. The pose list is not hardcoded in the browser.

## Live browser result

- Expected production poses: 39
- Observed production poses: 39
- Missing poses: 0
- Distinct sampled world positions: 258
- Intermediate pose-transition progress observed: yes
- Demo elapsed time: 38.549 seconds
- Browser console errors: 0
- Play button returned to idle state: yes

All 39 entries in `wizard_avatar/definitions/reference_avatar_pose_cells.json` were observed in generated-library order. The browser obtains this list dynamically rather than maintaining a second hardcoded list.

Screenshot: [demo-all-39-poses-moving.png](demo-all-39-poses-moving.png)

## Regression verification

- `python3 -m unittest discover tests`: 62 passed.
- `python3 tools/verify_animation_quality.py --strict`: 32/32 scenarios passed.
- `python3 tools/validate_pose_expansion_workflow.py`: 30 candidates, no errors, integration lock clear.

This verification must be repeated after each pose is promoted to `VERIFIED`. The expected pose count must increase automatically with the generated library.
