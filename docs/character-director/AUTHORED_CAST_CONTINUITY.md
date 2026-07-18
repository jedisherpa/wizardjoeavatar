# Authored Cast Continuity

## Problem

The original front cast mixed full-height and width-fitted pose graphs at one
projection scale. Joe visibly shrank during the wide staff poses, then the
staff jumped from the far right side of the frame directly into a leftward
thrust. Unit timing was valid, but the performance did not read as one body
carrying one prop through a continuous action.

## Pose-Density Contract

Wide source poses now declare an explicit rational `presentation_scale` in the
source manifest. The deterministic pose generator copies that metadata into
the square-cell library, and the projector applies it around the canonical
root. This restores the source's authored cell density without changing the
pixel graph, flattening a PNG at runtime, or moving a planted contact.

The current cast family uses these density ratios:

| Pose graph | Scale ratio |
| --- | --- |
| `front_staff_guard_low` | `96 / 94` |
| `front_staff_guard_windup` | `96 / 78` |
| `front_magic_staff_thrust` | `96 / 73` |

`front_staff_block_horizontal` also carries `96 / 75` for its independent
defensive use. Its foot anchors were recalibrated against colored boot cells,
but it is deliberately excluded from the cast because its rightward guard is
not a coherent intermediate for the leftward spell release.

## Choreography Contract

The 32-frame `cast_front` clip is:

1. `front_idle`, 2 frames
2. `front_staff_guard_low`, 4 frames
3. `front_staff_guard_windup`, 5 frames
4. `front_staff_guard_low`, 3 frames
5. `front_magic_staff_thrust`, 4-frame effect stroke
6. `front_magic_staff_thrust`, 5-frame effect hold
7. `front_staff_guard_low`, 5-frame recovery
8. `front_idle`, 4-frame settle

Markers occur at authored frames 10 (`action_commit`), 14
(`action_effect`), 23 (`action_recoverable`), and 28 (`action_settled`). Speech
before commit may cancel the cast; speech after commit waits through recovery.
The magic effect follows the authored thrust staff tip and fades over recovery.

Regression tests forbid both the old overhead `magic_cast` swap and the
horizontal defensive pose in this clip. They also normalize each sampled staff
tip by its pose-density ratio and cap consecutive horizontal travel at 50 local
cells.

## Verification

Focused pose, channel, marker, overlay, contact, and truth tests passed 64 of
64. `tools/validate_cartoon_animation_program.py` checked 140 Python production
paths with zero violations.

`evidence/character-director/cast-continuity-a8d0e28-2026-07-18/` is a strict
external-runtime capture bound to clean commit `a8d0e28`. It contains 339
contiguous decoded frames with zero drops, gaps, or decoder errors. Runtime
identity was stable from capture start to end. Contact verification passed all
339 frames with zero issues, zero root residual, and effectively zero planted
anchor drift.

- manifest SHA-256: `949e836fef5428aa2e3bf3cefc61af1a64767ae69b9922ec8634e81281e60f24`
- contact report SHA-256: `84732328390d660ed969574d7b24a36582d7d2105c5090fa0a7e6718e82fae52`
- truth trace SHA-256: `9f19f0ac7dc1b4d1eacb64efc737370c8346792b303a1b06ddc79ca17eacf956`
