# Thorne Vale Runtime Integration

Thorne is registered as `thorne-vale-v1` through the shared character registry.
He uses the same character-scoped REST, WebSocket, projection, command,
diagnostics, and reconnect architecture as Wizard Joe and CrystAIl, with an
isolated state controller and encoder history.

The production package contains exactly 124 transparent colored-node graphs:

- 16 identity/reference graphs from the accepted 4-by-4 identity revision 3.
- 108 pose/feature graphs from sheets 02–09, including the accepted motion
  revision 2.
- 124 audit records containing source-sheet hashes, bounds, node counts, and
  canonical graph hashes.

The runtime projector paints the selected JSON nodes directly onto the canvas.
Worksheet PNGs are preserved derivation inputs only; PNG and SVG files are not
runtime render assets. Package loading revalidates every graph hash, count,
bounds record, source reference hash, canonical reference hash, and accepted
worksheet hash before constructing the controller.

Thorne's locked design keeps the tall gold crown and jacket, rectangular green
eyes, dark mustache, safe gray sword, and tan policy parchment. His authored
movement is restrained and authoritative. The signature arcs cover decision
rights, tradeoff comparison, risk review, and incentive analysis, each with
anticipation, action, follow-through, and recovery. Cigar and smoke imagery are
not part of the production character.

Regenerate and verify the deterministic package with:

```bash
uv run python tools/generate_voxel_persona_character.py \
  assets/reference/personas/thorne-vale/generation-profile.json --check
```
