# Gaze Settle Continuity

Date: 2026-07-18

## Defect

The existing head-eye coordinator correctly gave the eyes a deterministic lead
before an authored head turn. After the head reached the requested facing,
however, the automatic gaze remained pinned toward the turn direction during
the complete settle hold. It then changed to center only when the settle phase
ended. The visible result was a late eye snap after the head had already
arrived.

## Acting Contract

The corrected sequence is:

1. Eyes acquire the turn direction while the head remains in the origin view.
2. The head follows through adjacent authored directional views.
3. Eyes re-center on the same simulation sample that presents the target head
   view.
4. The remaining settle ticks hold a stable target fixation.

Explicit governed or operator gaze remains authoritative. The change applies
only to automatic head-turn gaze and does not add interpolation, synthetic
poses, or a second animation clock.

## Implementation

Commit `3054c97f6ef486d80920a508d660c12b90b6671e` changes
`wizard_avatar/head_eye.py` so automatic gaze is directional only while the
sampled authored facing has not reached the target. The existing simulation
tick, adjacent-view cadence, transactional presentation snapshot, and
idempotent retry behavior remain authoritative.

Regression coverage verifies:

- opposite turns preserve the eye-lead and adjacent-view sequence;
- target arrival re-centers the eyes before settle completes;
- the rendered integration presents centered gaze on the first target-facing
  sample;
- repeated rendering and discarded candidates do not advance the turn;
- blink, face, mouth, performance application, and governed release behavior
  remain compatible.

Focused command:

```text
python3 -m unittest tests.wizard.test_head_eye tests.wizard.test_head_eye_render_integration tests.wizard.test_blink_scheduler tests.wizard.test_frame_source tests.wizard.test_animation_channels tests.wizard.test_mouth tests.wizard.test_performance_application tests.wizard.test_performance_release
```

Result: 73 tests passed.

## Clean Runtime Evidence

Evidence directory:

`evidence/character-director/gaze-settle-3054c97-2026-07-18/`

The strict external visual-review harness ran against a disposable server on
port `8876` from a clean worktree at commit `3054c97`. It captured 332
contiguous frames with zero dropped frames. The relevant ranges contain 21
gaze-left frames, 21 gaze-right frames, 16 face-back frames, and 20 face-front
frames. Runtime identity was stable from start to end.

Contact verification passed across all 332 frames:

- issues: 0;
- maximum root residual: 0 cells;
- maximum planted-anchor drift: approximately `2.01e-14` cells;
- maximum planted raster-span drift: 1 cell.

Artifact SHA-256 values:

- manifest: `28e04c0ced599735eb048ca73adb8893f68ca058fbd0394dc695fb82baafbb8a`;
- contact verification: `d6a78465691fa3bfd352c16996a9afe7435f49aee49051635720854a28617814`;
- animation truth trace: `c7259658e0fa1a05aef1a0a396e2c36409206614c6bb1e8828719b69ca6541d9`;
- exact-frame capture: `a8002f3325087a102df53c9e0739b13bc44474b93fb82e0c8c10bdbe58a6258a`;
- contact sheet: `12fd60fea4ef463483b7bcafde6dc2a0073b1ac48a5bad11ad2ed6b2921412b9`.

## Acceptance Boundary

This evidence demonstrates the corrected target-arrival timing on the real
Python projector and confirms that it does not damage contact continuity. It
does not complete visual scenario V1. V1 still requires a dedicated 12-second
listening scene with viewer/left/viewer targeting, a 90-degree head turn, two
visible blinks, normal- and quarter-speed review, and two independent reviewers.

