# Authored Turn Continuity

## Problem

The head-and-eye coordinator already advanced idle turns through adjacent
eight-direction facings, but the final pose selector collapsed every diagonal
to a front or back pose. A quarter or half turn therefore discarded its
three-quarter silhouettes and appeared to snap between front, profile, and
back views.

## Authored View Contract

Idle presentation now maps every compass facing to an existing admitted pixel
graph:

| Facing | Pose graph |
| --- | --- |
| south | `front_idle` |
| southeast | `walk_front_right` |
| east | `profile_right` |
| northeast | `back_right` |
| north | `back_idle` |
| northwest | `back_left` |
| west | `profile_left` |
| southwest | `walk_front_left` |

The mapping is presentation-only. It does not advance animation state, replace
an action pose, synthesize pixels, or create a second runtime. If a character
package does not provide the mapped graph, presentation falls back to the pose
selected by the animation graph.

## Motion Contract

The transactional head-and-eye coordinator remains the timing authority. It
leads a turn with gaze, advances through adjacent facings at its fixed cadence,
and commits each complete authored pixel graph atomically. A south-to-north
turn therefore presents front, front three-quarter, profile, rear
three-quarter, and back silhouettes. The reverse path presents the same views
in reverse order.

## Verification

Pose-selection tests cover all eight mappings, action preservation, and missing
pose fallback. Render integration requires the complete five-pose half-turn
sequence. Head/eye transaction, frame-source, animation-truth, visual-review,
and contact-verifier suites passed after the change.

`evidence/character-director/turn-continuity-8ea550c-2026-07-18/` is a strict
external-runtime capture bound to clean commit `8ea550c`. It contains 340
contiguous decoded frames with zero drops or decoder errors. Runtime identity
was stable from capture start to end. Semantic replay passed, and contact
verification reported zero issues with no root residual.

The trace records the critical turn frames directly:

- east to north: `profile_right` -> `back_right` -> `back_idle`
- north to south: `back_idle` -> `back_right` -> `profile_right` ->
  `walk_front_right` -> `front_idle`

- manifest SHA-256: `c2cdd38dae4fa0ae11e66f4ef9e549c30224ec84cc89469173ab024715f65a84`
- contact report SHA-256: `0dcf314540833b42f159977fa0cbd722156b76ff4bb00fd14d12fe24f098494c`
- truth trace SHA-256: `cc681fb692148664570a2a6721c30d5bc0b976ab657233e21ff055f66f10a76f`
