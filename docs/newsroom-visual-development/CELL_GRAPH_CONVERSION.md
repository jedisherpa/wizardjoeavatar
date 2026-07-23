# Reference-to-Cell-Graph Conversion

These PNGs are tracing inputs only. The runtime representation is transparent colored cells or horizontal cell runs.

## Required pipeline

1. Select one manifest extraction target and assign a stable ID and version.
2. Remove the white sheet/background before palette analysis. Do not classify white outside the object as an occupied cell.
3. Reconstruct the target on the 320x180 logical grid. Use nearest-cell decisions, never antialiased sampling.
4. Remove generated gloss, gradients, soft shadows, floor reflections, and sub-cell detail.
5. Quantize every occupied cell to an approved versioned palette ID.
6. Split depth responsibilities into separate graphs. For example, a desk becomes rear shell, desk face, and desk lip rather than one opaque bitmap.
7. Encode each graph as transparent row runs: `y`, `x_start`, and ordered palette IDs. Missing coordinates are transparent.
8. Declare anchors, bounds, coverage, occlusion role, allowed camera profiles, and safe zones.
9. Validate deterministic serialization, unique occupied coordinates, bounds, palette membership, and connected-component intent.
10. Render the graph through the projector at native logical size and compare it with the 320x180 reference preview.

## Acceptance checklist

- No PNG, SVG, data URL, filesystem image path, or generated raster is required at runtime.
- The graph has transparent outside cells and transparent intentional holes.
- White object cells are distinguished from transparent background cells.
- Set pieces, props, effects, foreground masks, and broadcast overlays remain independently toggleable.
- Desk, chair, lectern, staff, and wing crossings pass explicit occlusion tests.
- Blank display and card regions remain blank until populated by verified editorial overlays.
- Character pixels on camera boards are never traced or promoted.
- A 320x180 render remains legible, with no one-cell noise created by resampling.
- Human art review approves both the isolated graph and its composed scene.

## Suggested run shape

```text
CellRun {
  y: u16,
  x_start: u16,
  palette_ids: Vec<PaletteId>
}
```

Store provenance beside the graph: source image hash, extraction target ID, palette version, logical bounds, reviewer, review date, and rendered-frame hash.
