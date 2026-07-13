# WJP2-08 Integration Spec Evidence

- Spec: `docs/pose-library-expansion/integration-specs/WJP2-08.json`
- Generator command basis: `tools/generate_reference_avatar_cells.py` via its `generate()` function, temp output only.
- Raw 96-row generation: `74 x 96`, crop `[92, 88, 1003, 1274]`, root `[37, 95]`.
- Selected `generation_rows`: `94`; verified raw cols `72 <= 72`.
- Anchor decision: used item-record canonical proposal offsets unchanged; downscale is only two rows and the item already had canonical proposal evidence.
