# Open Questions and Assumptions Log

## Verified facts

- The primary checkout has Wizard Joe. The dedicated `codex/crystail-character` worktree additionally registers runtime-ready CrystAIl with 63 poses; focused tests pass 9/9. The implementation is branch-local until merged or designated as the runtime base.
- Medium runtime is a 240×135 opaque square-cell framebuffer at 24 fps with fixed camera/projection and no scenic loader.
- Boulder is mountain-bounded on the west; Boulder Creek is a west-to-east connective corridor; Boulder Falls is outside town in the canyon; Pearl Street is a four-block pedestrian mall.
- Eleven Joeville concept images were generated and inspected, including five Castle Grace voxel translations; none is a production-final runtime asset.

## Creative decisions pending approval

1. Approve the crafted block-diorama/colored-ASCII environment thesis after all characters are inspected.
2. Approve town geography and Castle Grace southwest ridge placement.
3. Approve the supplied Castle Grace reference packet as the silhouette/material lock; the earlier generated church-like Castle study remains rejected.
4. Approve fictional business names: Lantern & Lark, Brightroot, Juniper Tonic House, Riverstone Sushi, Joeville Commons Market, Current Hall.
5. Approve whether the town's public name is `Joeville` and the exact graphic wordmark.
6. Choose the first vertical-slice story/set sequence.

## Missing canonical inputs

- Eleven additional character sources, package builds, turnarounds, scale/anchor data and widest/tallest/seated/dance poses. Intake slots are tracked in `../manifests/CAST_BUILD_INTAKE.csv`.
- The different visualizer, if the stated 13-character runtime exists elsewhere.
- Castle Grace floor plan, unexplored rooms, approach/arrival references and source-license history; five canonical visual references were supplied on 2026-07-13.
- Character home/work/location affinities.
- Approved environment background examples and any established town art.

## Technical decisions

- Server-side cell composition vs browser-side image/video scene graph.
- Fixed camera per set vs real camera matrices/moves.
- Alpha/keyed-cell/depth sidecar design.
- Multi-character registry, sorting, collision, bandwidth and reconnect contract.
- Physical-unit/CU-to-world conversion and accessibility standard.

## Legal questions

- Whether any real Boulder business/location name or exact facade is story-essential.
- Rights/license status for any image promoted from factual reference to direct art reference.
- Public-art likenesses and private-interior access.
- Final trademark/title search for Joeville and fictional businesses.
