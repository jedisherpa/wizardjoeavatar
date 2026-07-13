# WJP2-05 Integration Spec Evidence

- Spec: `docs/pose-library-expansion/integration-specs/WJP2-05.json`
- Generator command basis: `tools/generate_reference_avatar_cells.py` via its `generate()` function, temp output only.
- Raw 96-row generation: `95 x 96`, crop `[0, 126, 1088, 1229]`, root `[47, 95]`.
- Selected `generation_rows`: `73`; verified raw cols `72 <= 72`.
- Anchor decision: scaled item-record root-relative estimates by `73 / 96` because downscale was required.
