# Wizard Joe Newsroom V2

This package replaces the flat, small-grid newsroom direction with a dimensional voxel
environment derived from the approved Wizard Joe source imagery.

## Authority

The visual authority is the admitted Wizard Joe source set, especially
`WJSRC-0001` and `WJSRC-0014`. The v2 newsroom must share their:

- chunky, individually readable voxel scale;
- stepped silhouettes and several-cubes-deep construction;
- directional face shading and restrained bevel highlights;
- saturated blue, gold, cyan, magenta, and warm brown materials;
- bright white field, soft studio light, and clean contact shadows.

The v1 newsroom package remains historical evidence. It is not the style source for
new graphs.

## Source evidence

Eight 1672x941 PNGs are stored under
`evidence/newsroom-visual-development-v2/source-plates/`:

- four character-free set plates;
- two character-free modular object boards;
- two non-canonical camera-composition boards.

The camera boards may guide blocking and shot design, but their character pixels must
never enter the runtime. The admitted Wizard Joe pose graphs remain authoritative.

## Runtime boundary

No v2 PNG is a runtime render asset. Each admitted scene module must be isolated from
its source, encoded as transparent colored row runs, projected independently, placed
over its source PNG, and visually approved within the five-percent error allowance.

The source and layer gates pass for all six admissible plates and 27 target graphs.
The Rust promotion gate rehashes the approval ledger, every verification report, every
comparison image, and every graph before copying byte-identical graph files into the
runtime. The viewer loads those compressed palette-and-row-run files directly and does
not load a v2 PNG.

## Integration order

1. Audit each source plate and record its checksum.
2. Isolate one module at a time without resizing, cropping, or palette reduction.
3. Split rear architecture, props, effects, and foreground occluders.
4. Encode exact source RGBA colors as palette entries plus horizontal runs.
5. Re-project the graph and create the required comparison images.
6. Visually approve the transparent graph over the original source.
7. Promote only the approved graph to the Rust runtime asset directory.

## Current status

- Source plates admitted: `6 / 6`
- Layer sources visually verified: `6 / 6`
- Independent target graphs: `27`
- Occupied RGBA pixels assigned exactly once: `4,233,630`
- Recomposition silhouette IoU: `1.0` for every source
- Recomposition foreground color fidelity: `1.0` for every source
- Runtime promotion: complete
- Runtime graph copies: `27 / 27` byte-identical to approved evidence
- Runtime raster assets: `0`
- Runtime snapshots: six server-path compositions under `runtime-snapshots/`

See `LAYER_ADMISSION.md`, `layer-admission-ledger.json`, and
`runtime-promotion.json` for the accountable record.
