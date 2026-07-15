# Kai Renner Runtime Integration

Kai is registered as `kai-renner-v1` through the shared character registry. The browser selector, character-scoped REST routes, WebSocket stream, movement controller, projector, adaptive encoder, diagnostics, and reconnect behavior are shared with Wizard Joe and CrystAIl while state and encoder history remain isolated per character.

## Production assets

- `kai_renner_pose_cells.json`: 108 worksheet-derived colored-node graphs from accepted sheets 02–09. Full-body graphs are pose-capable; sheet-06 construction graphs remain audited feature/reference data.
- `kai_renner_pixel_graphs.json`: 16 accepted identity/reference graphs from the revision-2 identity grid. Together with the pose library, these are the exact 124 production graphs.
- `kai_renner_extraction_audit.json`: the 124-item background-removal, source-hash, bounds, node-count, graph-hash, category, and runtime-format gate completed before animation mapping.
- `kai_renner_animation_graph.json`: idle, walk, run, jump/land, build/test, privacy/safety, evidence, prototype, correction, interaction, and turnaround clips.
- `kai_renner_animation_matrix.json`: the supported locomotion, expression, speech, interaction, build/test, safety, metrics, prototype, correction, and recovery vocabulary.
- `kai_renner_character_manifest.json`: identity, origin, attachments, derivation, accepted source hashes, and generated content hashes.
- `kai_renner_runtime_profile.json`: data-driven state/action/expression/speech/blink mappings.
- `kai_renner_character_package.json`: the loader and registry package.

Package loading recomputes every colored-node graph hash and requires the audit to cover exactly the same 124 graph identifiers before the runtime profile or animation controller is constructed. The projector then paints the selected colored nodes directly into the ASCILINE framebuffer; absent nodes are transparent. Worksheet PNGs are preserved provenance and extraction inputs only. No PNG or SVG is a runtime render asset, and runtime rendering does not call an image decoder.

The `prototype` attachment is present only on the eleven reviewed construction or full-body cells that actually contain a controlled prototype or evidence object. Feature/reference cells from sheet 06 are audited but excluded from the pose-capable controller list. The four full-body interaction cells remain directly addressable.

Regenerate deterministically with:

```bash
uv run python tools/generate_voxel_persona_character.py \
  assets/reference/personas/kai-renner/generation-profile.json
```

Verify without writing with the same command plus `--check`.
