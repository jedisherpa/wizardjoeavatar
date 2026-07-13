# WJP2-06 Integration Spec Evidence

- Spec: `docs/pose-library-expansion/integration-specs/WJP2-06.json`
- Generator command basis: `tools/generate_reference_avatar_cells.py` via its `generate()` function, temp output only.
- Raw 96-row generation: `89 x 96`, crop `[18, 93, 1103, 1261]`, root `[44, 95]`.
- Selected `generation_rows`: `78`; verified raw cols `72 <= 72`.
- Anchor decision: scaled item-record root-relative estimates by `78 / 96` because downscale was required.
