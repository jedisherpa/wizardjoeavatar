# Newsroom V2 Pixel-Graph Admission

## Non-negotiable rule

An admitted newsroom graph is a source-faithful reconstruction of one isolated source
module. It is not a procedural approximation, traced substitute, palette-reduced
variant, resized preview, or PNG-backed runtime layer.

## One-module workflow

1. Select one manifest target and assign a stable graph ID.
2. Record source path, source SHA-256, native dimensions, and extraction bounds.
3. Remove only the connected white sheet/background. Preserve object whites,
   highlights, bevels, and contact shadows belonging to the module.
4. Keep native pixel coordinates. Do not stretch, resize, crop, or resample.
5. Store occupied RGBA values in an exact palette and encode horizontal row runs by
   palette index. Missing coordinates are transparent.
6. Store semantic layer, draw order, anchor, bounds, occlusion role, and allowed
   camera profiles beside the graph.
7. Project the graph through an implementation independent from extraction.
8. Produce all required evidence:
   - isolated normalized source;
   - a contrasting isolation-decision image showing removed matte in magenta;
   - graph render;
   - transparent graph overlay;
   - graph-over-original-source composite;
   - complete metric report and artifact hashes.
9. Compare the transparent projected graph directly over the source PNG at native
   resolution. Visual approval must confirm no more than five-percent disagreement.
10. Record visual approval against the exact source and graph hashes. Approval changes
    evidence state only.
11. A separate layer-classification and promotion command may later consume approved
    evidence. It must rehash every input and must never copy source PNGs into runtime.

## Layer classification result

Layer classification is complete for all six admitted sources. The target-level
ledger is `layer-admission-ledger.json`; detailed results and the 27-graph inventory
are in `LAYER_ADMISSION.md`. Runtime promotion remains deliberately separate.

## Numeric checks

Both silhouette and foreground color must be measured without allowing white
background pixels to inflate the score.

- silhouette precision >= 0.95;
- silhouette recall >= 0.95;
- silhouette IoU >= 0.95;
- foreground exact/near color match ratio >= 0.95;
- non-empty connected component set;
- no occupied coordinates outside declared bounds;
- every generated evidence hash still matches at approval time.

Numeric checks are necessary but not sufficient. The direct visual overlay is the
approval authority.

## Runtime prohibition

The viewer may load compressed scene graphs. It may not load source PNGs, SVGs, data
URLs, filesystem image paths, generated previews, or camera boards.
