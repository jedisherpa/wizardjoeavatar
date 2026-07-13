# WJP2-04 Integration Spec Evidence

- Spec: `docs/pose-library-expansion/integration-specs/WJP2-04.json`
- Generator command basis: `tools/generate_reference_avatar_cells.py` via its `generate()` function, temp output only.
- Raw 96-row generation: `74 x 96`, crop `[70, 85, 1045, 1347]`, root `[37, 95]`.
- Selected `generation_rows`: `93`; verified raw cols `72 <= 72`.
- Anchor decision: scaled item-record root-relative estimates by `93 / 96` because downscale was required.
