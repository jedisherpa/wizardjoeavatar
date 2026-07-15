# Orion Vale Runtime Integration

Orion is registered as `orion-vale-v1` through the shared character registry. The browser selector, character-scoped REST routes, WebSocket stream, movement controller, projection, adaptive encoder, diagnostics, and reconnect behavior are shared with Wizard Joe and CrystAIl while state and encoder history remain isolated per character.

Runtime assets:

- `orion_vale_pose_cells.json`: 108 worksheet-derived graphs from sheets 02–09.
  Full-body graphs are pose-capable; feature graphs remain audited donor data.
- `orion_vale_pixel_graphs.json`: the 16 isolated identity/reference graphs;
  together with the pose library this is the complete 124-graph production set.
- `orion_vale_extraction_audit.json`: the repeatable 124-item pre-animation
  background-removal, bounds, source-hash, node-count, and graph-hash gate.
- `orion_vale_animation_graph.json`: idle, walk, run, jump/land, conversation, inquiry, journal, and turnaround clips.
- `orion_vale_animation_matrix.json`: the supported ground, expression, speech, interaction, journal, and inquiry vocabulary.
- `orion_vale_character_manifest.json`: identity, origin, attachments, derivation, and content hashes.
- `orion_vale_runtime_profile.json`: data-driven state-to-pose mappings.
- `orion_vale_character_package.json`: loader and registry package.

Package loading verifies the audit covers all 124 graphs and recomputes every
graph hash before the animation profile can be loaded. The live projector then
paints the selected colored nodes into the ASCILINE framebuffer each frame;
absent nodes are transparent. It does not load, decode, or display PNG or SVG
references. Regenerate with:

```bash
python3 tools/generate_voxel_persona_character.py assets/reference/personas/orion-vale/generation-profile.json
```

Verify deterministic output with the same command plus `--check`.
