# Rohan Slate Runtime Integration

Rohan is registered as `rohan-slate-v1` through the shared character registry.
The browser selector, character-scoped REST routes, WebSocket stream, movement
controller, projection, adaptive encoder, diagnostics, and reconnect behavior
are shared with the existing characters while each character keeps isolated
runtime state.

## Production graph set

- `rohan_slate_pixel_graphs.json` contains 16 identity/reference graphs.
- `rohan_slate_pose_cells.json` contains 108 worksheet-derived pose and feature
  graphs from sheets 02–09.
- Together they contain exactly 124 transparent colored-node graphs.
- `rohan_slate_extraction_audit.json` records source lineage, worksheet hashes,
  background removal, node counts, bounds, and graph hashes before animation
  mapping.

The worksheet PNG files are immutable derivation inputs, not runtime render
assets. The visualizer loads JSON colored nodes, treats every absent coordinate
as transparent, and projects the selected graph into the canvas for each frame.
Package loading validates graph hashes, RGB values, node counts, bounds,
generated assets, source references, the generation profile, and all nine
accepted worksheet hashes.

Extraction removes the pale-cyan studio field and all floor/contact shadows.
The approved Rohan silhouette retains his teal eyes, black glasses, curly brown
hair, square beard, forest-green workwear, tool belt, diagnostic meter, and the
single approved wrench. Expression rows use recorded panel expansion because
their source figures cross nominal row boundaries; this prevents head clipping
without changing the original worksheets.

## Persona behavior

The runtime maps shared semantic commands to Rohan's observe-symptom,
inspect-cause, meter-scan/read, indicate-result, safety-stop, precise reset,
watch-and-wait, walkthrough, wrench-presentation, qualified-help, and settled
recovery poses. Turn, crouch, jump, fall, landing, expressions, 13 speech
visemes, and three blink states remain independently reachable. Speech and
blink donors alter only face regions and preserve the active locomotion or
signature-action body graph.

## Regeneration and visual evidence

```bash
python3 tools/generate_voxel_persona_character.py \
  assets/reference/personas/rohan-slate/generation-profile.json
python3 tools/render_persona_graph_contact_sheets.py \
  rohan_slate evidence/rohan-slate
```

Add `--check` to the first command to verify deterministic output without
changing files. The evidence directory contains separate transparent-isolation
and projected-canvas 124-up sheets plus a hash/order manifest. These PNGs are
review evidence only and are never loaded by the runtime.
