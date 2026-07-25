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

- Compiler ID: `wizard-avatar-production-alpha-plus-phazer-v2`
- Runtime path: `rust/wizard_avatar_engine/assets/pose_graphs/v7`
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

All 48 Phazer frames use one uniform 47:20 nearest-neighbor enlargement before canonical
placement. The enlargement replicates authored color pixels without interpolation, preserves
relative choreography across the sheets, and brings the occupied silhouette into the same
approximately 1100-cell height band as the established Wizard Joe runtime poses.

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

## Rollback

Runtime v6 is unchanged and remains the exact 260-pose rollback baseline. Runtime v7 is selected by
the Rust catalog loader and can be reverted by restoring the v6 manifest path and constants.
