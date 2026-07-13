# WJP2-02 Integration Spec Evidence

- Spec: `docs/pose-library-expansion/integration-specs/WJP2-02.json`
- Generator command basis: `tools/generate_reference_avatar_cells.py` via its `generate()` function, temp output only.
- Raw 96-row generation: `67 x 96`, crop `[65, 22, 992, 1355]`, root `[33, 95]`.
- Selected `generation_rows`: `96`; verified raw cols `67 <= 72`.
- Anchor decision: used item-record manifest offsets unchanged because no row downscale was required.
