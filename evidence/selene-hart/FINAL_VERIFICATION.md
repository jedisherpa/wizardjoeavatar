# Selene Hart — Final Production Verification

## Outcome

Selene Hart is registered as `selene-hart-v1` in the ASCILINE Python visualizer. Runtime rendering paints transparent colored pixel nodes directly to the canvas. No runtime PNG, SVG, worksheet crop, flattened sprite, or image decoder is used.

The hard gate contains exactly **124** independently isolated and serialized graphs:

| Category | Count |
| --- | ---: |
| Identity/reference | 16 |
| Turnaround | 8 |
| Neutral | 8 |
| Expression | 24 |
| Viseme/blink | 16 |
| Hand/prop | 16 |
| Motion | 16 |
| Signature | 16 |
| Interaction | 4 |
| **Total** | **124** |

The runtime pose vocabulary contains **88 full-body graphs**. The **20 feature graphs** and **16 identity/reference graphs** are retained for audit and lineage only and cannot be selected as body poses.
Automated tests enumerate every animation-graph sample and runtime-profile pose
reference and require it to resolve to one of those 88 full-body graphs.

## Visual and data audit

- 124/124 worksheet cells isolated with the studio background, dividers, floor, cast shadow, and contact shadow removed.
- 124/124 serialized graphs contain RGB pixel nodes only and pass canonical bounds and four-cell inset checks.
- 124 unique graph IDs and 124 unique graph hashes; no empty graphs or image-backed runtime assets.
- Projector comparison: 124 passed, 0 failed, with pixel-for-pixel equality after serialization.
- Human review of the projected 124-up sheet confirmed stable face, long dark hair, taupe wrap top, green skirt, brown shoes, anatomical-right teal wrist motif, rubric/clipboard scale, complete silhouettes, and no visible background residue.
- Rubric and clipboard anchors are present only on the explicitly declared prop-bearing cells, and every declared anchor lands on an occupied node.

## Immutable lineage hashes

| Artifact | SHA-256 |
| --- | --- |
| Original reference | `2019ae7b2349abb8a6c2f5e3cf17535b94442f294810c3852e062d4e87663969` |
| Canonical voxel reference | `5ade95e07beab8b8eb25f88195d804542cfbbd6c6ada7d6403d6099d3a6be1d1` |
| Generation profile | `5650efc5ebe782f3a9cb4b294bb87e51ff3befccf0d4aaf0ed9a3d1c6a333b5d` |
| Production pose graph library | `c88fd31f547cdbd893ca2a7f5ff746ddcc545f0b4a4535b516dab534d74d2353` |
| Identity/reference graph library | `18991b71a7df27eee88e9ec11dbebe413472bfc85903cddcc3150d8411bcab62` |
| Extraction audit | `0dc6e8ad701c235739485c5a636ac4dd04ec75ffa61d3b3dcf62466e3d02056b` |
| 124-cell visual comparison audit | `5d3851ebcf95fb82c70b14028fbbf01c97c3c6470a0c605b261324ee700b2217` |
| Isolated-silhouette contact sheet | `13b7bdf3df1e18dfe34bc83219d9b04fb69df00ee18ba63546a773d24733822e` |
| Projected-graph contact sheet | `13b7bdf3df1e18dfe34bc83219d9b04fb69df00ee18ba63546a773d24733822e` |

The equal contact-sheet hashes are expected: the isolated node lists and the deserialized projector node lists are exactly equivalent. They are rendered through separate audit inputs.

## Automated verification

- Deterministic generation check: passed.
- Focused Selene/direct-cell suite: **19/19 passed**.
- Full Python suite: **180/180 passed** in 146.745 seconds.
- Forced `PIL.Image.open` failure during runtime rendering: passed; an ASCILINE frame still rendered successfully.
- Manifest validation rehashes the generation profile, character package,
  runtime profile, original and canonical references, all nine accepted
  worksheets, every generated library, and the extraction audit. A destructive
  tamper matrix calls the real loader for every one of those inputs: passed.
- Animation-quality transition matrix: **32/32 scenarios passed**, 0 issues.

## Live Python runtime verification

The actual server was exercised through its character-scoped static, REST, and WebSocket paths:

- WebSocket initialization: `INIT:24.0:5:240:135:0:0:0.000`.
- Idle binary frame: **10,155 bytes**.
- Signature-action binary frame: **12,023 bytes**.
- A real semantic action was submitted over the running server. After the next render tick, live state reached the expected Selene signature pose.
- The focused runtime test independently verifies every Selene semantic action after a render tick: `define_standard → present_standard`, `inspect_evidence → inspect_checklist`, `compare_rubric → compare_side_by_side`, `flag_gap → flag_gap_controlled_point`, `compliance_review → hold_rubric_and_clipboard_separately`, `issue_measured_result → evidence_based_approval`, and `document_exception → document_exception`.

Production architecture: ASCILINE Python direct-cell rendering. Runtime image assets: none.
