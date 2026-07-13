# WJP2-10 Integration Spec Evidence

- Spec: `docs/pose-library-expansion/integration-specs/WJP2-10.json`
- Generator command basis: `tools/generate_reference_avatar_cells.py` via its `generate()` function, temp output only.
- Raw 96-row generation: `71 x 96`, crop `[73, 35, 1043, 1349]`, root `[35, 95]`.
- Selected `generation_rows`: `96`; verified raw cols `71 <= 72`.
- Anchor decision: used item-record canonical proposal offsets unchanged because no row downscale was required.
