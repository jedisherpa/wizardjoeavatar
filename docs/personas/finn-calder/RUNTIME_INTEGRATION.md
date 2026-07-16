# Finn Calder Runtime Integration

Finn is registered as `finn-calder-v1` through the shared character registry.
The browser selector, character-scoped REST routes, WebSocket stream, movement
controller, projection, adaptive encoder, diagnostics, and reconnect behavior
are shared with the existing characters while runtime state remains isolated.

## Production graph set

- `finn_calder_pixel_graphs.json` contains 32 audit-only graphs: the 16
  identity/reference cells and all 16 close hand/microphone feature cells.
- `finn_calder_pose_cells.json` contains the 92 full-body worksheet-derived
  graphs that are eligible for live poses and animation.
- Together those files contain exactly 124 transparent colored-pixel graphs.
- No reference or close-feature graph is registered as a pose, sampled by an
  animation clip, or accepted by the live pose command.
- `finn_calder_extraction_audit.json` records all 124 source cells, accepted
  worksheet hashes, background-removal status, node counts, bounds, and graph
  hashes before animation mapping.

There are no PNG or SVG runtime render assets. The live ASCILINE projector
loads the audited JSON nodes, treats absent nodes as transparent, and paints
the selected colored nodes into the framebuffer for every frame. Package load
recomputes graph hashes, node counts, bounds, generated-asset hashes, source
reference hashes, and accepted worksheet hashes before creating the runtime.

## Persona behavior

The data-driven runtime profile maps semantic actions onto the exact approved
Finn vocabulary: welcome crowd, announce event, accessibility check, lead
ritual, celebrate student contribution, supervise transition, and community
sign-off. The accepted anticipation, action, follow-through, and recovery
panels stay directly reachable alongside turn, crouch, jump, fall, landing,
expressions, 13 speech visemes, and three blink states.
Speech and blink donor regions are composited over the active body graph, so
they do not replace locomotion or signature-action silhouettes.

## Regeneration

```bash
python3 tools/generate_voxel_persona_character.py \
  assets/reference/personas/finn-calder/generation-profile.json
```

Add `--check` to verify deterministic output without changing files.
