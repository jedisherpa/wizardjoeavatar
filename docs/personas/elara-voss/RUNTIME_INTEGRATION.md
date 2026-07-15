# Elara Voss Runtime Integration

Elara is registered as `elara-voss-v1` through the shared character registry.
The browser selector, character-scoped REST routes, WebSocket stream, movement
controller, projection, adaptive encoder, diagnostics, and reconnect behavior
are shared with the existing characters while runtime state remains isolated.

## Production graph set

- `elara_voss_pixel_graphs.json` contains the 16 identity/reference graphs
  isolated from the accepted revision-3 identity worksheet.
- `elara_voss_pose_cells.json` contains 108 worksheet-derived graphs from
  sheets 02–09. Full-body graphs are pose-capable; close hand/prop graphs stay
  audited feature/reference data.
- Together those files contain exactly 124 transparent colored-pixel graphs.
- `elara_voss_extraction_audit.json` records all 124 source cells, accepted
  worksheet hashes, background-removal status, node counts, bounds, and graph
  hashes before animation mapping.

There are no PNG or SVG runtime render assets. The live ASCILINE projector
loads the audited JSON nodes, treats absent nodes as transparent, and paints
the selected colored nodes into the framebuffer for every frame. Package load
recomputes graph hashes, node counts, bounds, generated-asset hashes, source
reference hashes, and accepted worksheet hashes before creating the runtime.

## Persona behavior

The data-driven runtime profile maps shared semantic actions onto Elara’s own
curriculum explanation, sequencing, reflection, microphone presentation,
listening, rubric emphasis, calm correction, measured celebration, and
containment/recovery poses. Turn, crouch, jump, fall, landing, expressions,
13 speech visemes, and three blink states remain independently reachable.
Speech and blink donor regions are composited over the active body graph, so
they do not replace locomotion or signature-action silhouettes.

## Regeneration

```bash
python3 tools/generate_voxel_persona_character.py \
  assets/reference/personas/elara-voss/generation-profile.json
```

Add `--check` to verify deterministic output without changing files.
