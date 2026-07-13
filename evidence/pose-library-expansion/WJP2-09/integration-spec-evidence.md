# WJP2-09 Integration Spec Evidence

- Spec: `docs/pose-library-expansion/integration-specs/WJP2-09.json`
- Generator command basis: `tools/generate_reference_avatar_cells.py` via its `generate()` function, temp output only.
- Raw 96-row generation: `102 x 96`, crop `[41, 213, 1050, 1167]`, root `[51, 95]`.
- Selected `generation_rows`: `68`; verified raw cols `72 <= 72`.
- Anchor decision: used item-record canonical proposal offsets unchanged because the item already identified low-pose canonical anchors after proposal preview review.
