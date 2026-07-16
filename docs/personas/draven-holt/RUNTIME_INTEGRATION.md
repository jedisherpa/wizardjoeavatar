# Draven Holt Runtime Integration

Draven is registered as `draven-holt-v1` through the shared character
registry. Character-scoped REST, static assets, WebSocket streaming, movement,
projection, encoding, diagnostics, and reconnect behavior use the same
production engine as Wizard Joe and CrystAIl while keeping Draven's state and
assets isolated.

## Exact 124-graph package

- `draven_holt_pixel_graphs.json` stores 16 identity/reference graphs.
- `draven_holt_pose_cells.json` stores 108 worksheet-derived graphs: 8
  turnaround, 8 neutral, 24 expression, 16 viseme/blink, 16 hand/prop, 16
  motion, 16 signature, and 4 interaction.
- The combined audit is exactly 124/124. The 92 full-body production graphs are
  runtime pose-capable. The 16 hand/prop construction graphs and 16 identity
  references remain audit/feature data and cannot replace a body silhouette.
- `draven_holt_extraction_audit.json` records one-to-one accepted-cell lineage,
  node counts, bounds, background removal, RGB encoding, and graph hashes.

Approved worksheet PNG files are immutable extraction inputs, not runtime
render assets. Generated runtime files contain transparent colored pixel nodes
in JSON. The projector paints those nodes into the canvas on every frame; it
does not decode PNG or SVG assets. Package loading validates the generation
profile, original and canonical images, all nine approved worksheets, all
generated files, every graph hash, node count, and bounds before animation is
connected.

The extraction mask removes the blue-gray studio field, sheet boundaries,
floors, and contact/cast shadows while preserving Draven's black suit and hair,
green eyes, orange tie, medium-brown skin, clipboard, white abstract checklist,
silver clip, and orange mechanical pencil. Cigars, tobacco, smoke, readable
text, and other personas' props are prohibited.

## Draven-specific runtime vocabulary

The runtime profile maps only Draven's concise operations vocabulary:
assign-owner preparation/open hand/confirming point/recovery; clipboard raise,
deadline pencil tap, emphasis, and recovery; checklist review, resource
allocation, blocker escalation, and recovery; clipboard scan, extension,
handoff release, and settled pencil-ready recovery. Locomotion, eight facings,
expressions, 13 speech visemes, and three blink states remain independently
reachable. Speech and blink donors alter face regions without replacing the
active walking or signature-action body graph.

## Deterministic regeneration and evidence

```bash
python3 tools/generate_voxel_persona_character.py \
  assets/reference/personas/draven-holt/generation-profile.json
python3 tools/render_persona_graph_contact_sheets.py \
  draven_holt evidence/draven-holt
```

Use `--check` on the first command for a read-only determinism gate. The
evidence directory retains a transparent-isolation 124-up sheet, a projected
canvas 124-up sheet, and an exact hash/order manifest. Evidence PNGs are never
runtime dependencies.
