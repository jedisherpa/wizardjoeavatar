# Selene Hart — Canonical Identity Lock

## Authority and derivation

1. `assets/reference/personas/selene-hart/source-reference.png` is immutable source evidence. SHA-256: `2019ae7b2349abb8a6c2f5e3cf17535b94442f294810c3852e062d4e87663969`.
2. `assets/reference/personas/selene-hart/canonical-voxel.png` is the approved voxel interpretation. SHA-256: `5ade95e07beab8b8eb25f88195d804542cfbbd6c6ada7d6403d6099d3a6be1d1`.
3. The nine accepted worksheet images in `canonical-worksheets/` derive from the canonical voxel image and are pose references, not runtime render assets.

The source and canonical images must never be cropped, repainted, overwritten, or used as substitutes for production poses.

## Visual analysis

- **Silhouette and proportions:** tall adult woman; roughly 7.3 heads high in the canonical interpretation; narrow shoulders, long torso, full ankle-length A-line skirt, straight lower legs, and low block-heel flats. Hair and skirt make the two dominant vertical masses.
- **Head and face:** angular oval face with a squared voxel jaw, high cheek plane, straight brows, almond-shaped dark eyes, compact straight nose, closed composed mouth, and small exposed ears where the hair permits. Default expression is attentive and mildly appraising.
- **Hair:** very long dark-brown block hair, center-to-soft-left part, close over the crown, falling in stepped strands past the chest and across most of the back. The silhouette is full but controlled, not curly or windblown at rest.
- **Clothing:** taupe draped long-sleeved wrap top with broad sleeves and an asymmetric overlapping front; full muted-green ankle-length skirt with deep vertical block folds; brown closed-toe flat shoes with a low squared heel.
- **Hands and asymmetry:** warm medium skin; canonical voxel hands with a thumb and four readable finger blocks where scale permits. A teal-and-gold geometric wrist motif is worn on Selene's right wrist and must remain on that wrist in every view.
- **Props:** dark-red rubric folio with a centered gold rectangular grid/check emblem; gray clipboard with dark rim and top clip, cream paper, square checklist grid, and restrained check marks. Their dimensions and colors are stable. Neither prop contains language.
- **Shape language:** vertical, rectangular, measured, and layered. Soft garment drapes are represented by disciplined stepped voxel planes. Prop grids repeat Selene's standards/evaluation motif.
- **Materials:** matte voxel cloth, semi-matte skin and hair blocks, slightly firmer folio cover, and neutral clipboard surfaces. No gloss, metallic jewelry, or translucent materials.
- **Rendering:** high-detail 3D voxel construction, no outlines, no pixel-art outlines, fixed cube granularity, soft cool studio key light, gentle occlusion, pale blue-gray background, and restrained floor shadow.
- **Posture and movement:** upright center of gravity, measured hand travel, modest shoulder rotation, economical stride, clear pauses, and decisive recoveries. She communicates fairness through stillness and evidence-led gestures rather than enthusiasm.

## Approximate palette

These values are sampled or visually normalized from the canonical image; lighting may shift individual visible faces but not the material identity.

| Material | Representative colors |
| --- | --- |
| Skin | `#DB9D5D`, `#B7753B` |
| Hair | `#1B0E09`, `#4D261A`, `#7E4D29` |
| Taupe top | `#CBC0AF`, `#977C54`, `#826D52` |
| Green skirt | `#709068`, `#4F7752`, `#315239`, `#293929` |
| Brown shoes | `#59412B`, `#2F2013` |
| Rubric folio | `#5E2621`, `#3E1715` |
| Rubric emblem | `#C59A55` |
| Clipboard | `#BFC0B4`, `#424846`, `#EEE4D1` |
| Wrist motif | `#287C72`, `#C59A55` |

## Immutable identity features

1. Adult age, tall proportions, angular face, dark almond eyes, straight brows, compact nose, and controlled mouth.
2. Long dark-brown stepped hair, including its crown part, front fall, and back length.
3. Taupe asymmetric draped top, full muted-green ankle-length skirt, and brown flat shoes.
4. Teal-and-gold motif on the right wrist only.
5. Dark-red/gold rubric folio and gray/cream checklist clipboard as the only normal props.
6. Stable voxel cube scale, camera family, matte materials, studio-light logic, and complete-canvas character scale.
7. Calm, exacting, fair performance vocabulary; no exuberant or slapstick default behavior.

## Features allowed to articulate or deform

- Eyelids, brows, eyes, mouth, cheeks, jaw, and head angle may articulate for the approved expression and viseme set without changing skull structure or age.
- Neck, shoulders, elbows, wrists, fingers, spine, hips, knees, ankles, hair tips, and skirt folds may move within the canonical construction.
- The draped top may compress or open modestly at joints; the overlap seam and sleeve construction remain recognizable.
- Hair and skirt may use restrained follow-through during locomotion, jump/fall/land, and turns.
- Rubric and clipboard may translate and rotate only through explicit hand contacts, releases, and recovery poses.

## Recognition test

A frame is Selene only if it reads immediately as the same long-haired standards evaluator in the taupe wrap top and long green skirt, with the right-wrist teal motif and restrained evidence-led posture. Any change to face architecture, hair length, garment construction, prop design, apparent age, body proportion, cube size, or wrist side is identity drift and requires rejection.

## Production invariants

- Every full-body runtime cell must preserve a stable root and baseline, include the entire silhouette, and retain at least four transparent pixels on every used side after normalization.
- Left/right mirroring may not move the wrist motif to the wrong anatomical wrist or mirror prop emblems into inconsistent geometry.
- Runtime data is a transparent colored-pixel graph (nodes or runs), never a PNG/SVG render dependency.
- No pose may reconnect to an animation until its isolated silhouette and derived pixel graph have both passed the 124-cell audit defined in `WORKSHEET_GENERATION_RECORD.md`.
