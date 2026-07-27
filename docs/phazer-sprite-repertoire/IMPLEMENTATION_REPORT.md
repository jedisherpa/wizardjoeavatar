# Phazer Repertoire Implementation Report

## Admission Result

- Intake compiler: `wizard-avatar-phazer-intake`
- Promotion compiler: `wizard-avatar-phazer-promote`
- Input sheets: 8 of 8
- Extracted frames: 48 of 48
- Native PixelGraphs: 48 of 48
- Exact graph reprojections: 48 of 48
- Foreground source-pixel matches: 48 of 48
- Visual review decision: `approved_transparent_overlay_review`
- Checkerboard residue in projected graphs: none observed
- Neighbor-frame fragments in projected graphs: none observed

## Runtime Result

- Compiler ID: `wizard-avatar-production-alpha-plus-normalized-phazer-v4`
- Runtime path: `rust/wizard_avatar_engine/assets/pose_graphs/v9`
- Total runtime poses: 308
- Unique semantic poses: 308
- Source archives: 3
- Phazer authored transition links: 96
- Total authored transition links: 576
- New independent clips: 8
- New complete repertoire loop: 1

## Motion Interpretation

The sheets are treated as authored movement, not as interchangeable still poses. Ground contact,
airborne support, facing, phase, and loopability are recorded per sequence. Frames use zero
synthetic transition ticks so the source poses remain intact; timing is authored through hold
ticks. The engine's actor translation remains responsible for travel across the stage.

All 48 regenerated Phazer frames use per-facing anatomical scale normalization. Joe's central hat
brim is measured independently of wings, staff, crouch depth, and flight pose; each complete
silhouette is then scaled around its authored runtime anchor. The shared runtime frame expands
from 1254 to 1536 with symmetric transparent padding so no extended silhouette is clipped.

The browser requests every immutable graph URL with its catalog `graph_sha256`. A promoted graph
therefore receives a new cache key, preventing an earlier lower-resolution graph from surviving a
runtime catalog upgrade.

## Verification Result

- Pose-tool tests: passed
- Deterministic archived-corpus recompilation: passed
- Authored transition reachability: 576 of 576 passed
- Runtime clips audited: 28
- Locomotion scenarios audited: 4
- Runtime frames rendered and checked: 1,377
- Phazer repertoire loop measured frames: 119
- Incomplete graphs: 0
- Discontinuous clip transitions: 0
- Audit receipt: `rust/wizard_avatar_engine/evidence/runtime-pixelgraph-qa-v7/animation-frame-audit.json`
- Normalized exact graph reprojections: 48 of 48
- Live v9 browser captures: 48 of 48
- Live capture sheet:
  `evidence/phazer-native-regeneration/normalized-v2/review/live-runtime-contact-sheet.png`

## Rollback

Runtime v7 is unchanged and remains the exact 308-pose rollback baseline. Runtime v9 is selected by
the Rust catalog loader and can be reverted by restoring the v7 manifest path and constants.
