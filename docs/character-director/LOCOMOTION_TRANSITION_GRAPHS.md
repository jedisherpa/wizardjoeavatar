# Locomotion Transition Pixel Graphs

## Problem

The authored `walk_front` clip previously inserted `front_idle` between its two
contact poses. At runtime this read as a full-body reset twice per stride. A
mirrored passing-pose experiment was rejected because it moved the staff to the
wrong side or damaged the arm and wing while attempting to restore the prop.

## Repeatable generation

The source manifest now declares two `derived_blend` poses:

- `walk_front_left_to_right`
- `walk_front_right_to_left`

`tools/generate_reference_avatar_pose_cells.py` builds all authored PNG poses
first, aligns them to the canonical 72 by 96 canvas and root, and then composes
each derived pose from the two normalized endpoint pixel graphs. The compositor
uses the same deterministic crisp threshold as runtime pose transitions. Every
output pixel is selected from an endpoint; no interpolated colors, PNG runtime
assets, SVGs, or text glyphs are introduced.

The staff and its hand occupy an explicit canonical prop-side slice beginning at
cell x=56. The derived pose copies that entire slice, including transparent
cells, from its target endpoint. This keeps the prop atomic instead of producing
dotted shaft fragments while the body interior changes pose.

## Animation contract

The front walk loop is now:

1. `walk_front_left`
2. `walk_front_left_to_right`
3. `walk_front_right`
4. `walk_front_right_to_left`

Both transition samples are release phases with no planted anchor. The authored
contact poses retain left- and right-foot contact authority. The legacy graph
and graph V2 use the same four-pose order, and `front_idle` is forbidden inside
the front walk clip by regression test.

## Verification

The pose-library tests require every transition pixel to match one endpoint at
the same coordinate and require the complete x>=56 slice to match the target
endpoint exactly. Pose selection, contact gating, capability derivation, program
registry, and deterministic generation are verified together before runtime
evidence is accepted.

Current generated library:

- pose count: 91
- SHA-256: `00dfb01aa169b52ea29ecb91fb0aec138f78369789d6be084f28a20ff0d9ff91`

## Runtime evidence

`evidence/character-director/locomotion-transitions-eccb583-2026-07-18/`
is a strict external-runtime capture bound to clean commit `eccb583`. It contains
341 contiguous decoded frames, the original adaptive wire stream, frame index,
truth trace, sampled PNGs, H.264 capture, contact sheet, and contact report.
Semantic replay passed with zero dropped frames and zero contact issues. The
trace records 87 `walk_front` frames and repeatedly presents the four-pose order
above without an idle sample.

- manifest SHA-256: `8ba20adbf81af8fb8f11c1c9c71403c16323d1d3effa7fe66af7deef677f94a9`
- contact report SHA-256: `1151ff81e1108fc6fb954d56374fc83af2fdc7e884a9a00a45f8823358faf96e`
