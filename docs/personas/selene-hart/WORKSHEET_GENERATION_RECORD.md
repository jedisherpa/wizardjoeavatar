# Selene Hart — 124-Cell Worksheet Generation Record

## Scope and acceptance state

Selene's canonical reference package contains exactly **124 accepted cells** across nine deterministic worksheets. All sheets were generated with the built-in GPT Image workflow, visually inspected at sheet scale, decoded successfully, checked for exact grid divisibility, counted, hashed, and compared for accidental duplicates. They remain pose references only; no worksheet image is a runtime asset.

| Sheet | Geometry | Cell geometry | Count | Accepted file | SHA-256 |
| --- | ---: | ---: | ---: | --- | --- |
| Identity | 4×4 at 1256×1256 | 314×314 | 16 | `01-identity-sheet-candidate-v1.png` | `e73b8bc94807662da74b885e5e807adee273891d37a138ba0316db68b6ffcf44` |
| Turnaround | 4×2 at 1536×1024 | 384×512 | 8 | `02-turnaround-sheet-candidate-v1.png` | `76f48150490f161ef40dc7d0dbffbaeda411452f1893b1a4029c7c62bc3aad39` |
| Neutral bases | 4×2 at 1536×1024 | 384×512 | 8 | `03-neutral-base-poses-candidate-v1.png` | `936cc38910ca986e57d4dfd3c46771a276c9b09e39e0bafc019bb61594efb136` |
| Expressions | 6×4 at 1536×1024 | 256×256 | 24 | `04-expression-sheet-candidate-v1.png` | `76e9c087c9dabfbf320de4b59271b85d2df050afbb355f89956832085fd67a62` |
| Visemes/blinks | 4×4 at 1256×1256 | 314×314 | 16 | `05-speech-viseme-sheet-candidate-v1.png` | `e1e8efc483dcdc2f8142b69c1de271482cd50d6f575eb941d28453afd69a23ae` |
| Hands/props | 4×4 at 1256×1256 | 314×314 | 16 | `06-hand-prop-sheet-candidate-v1.png` | `634b3721926ee0daba6303b2b83b4e9ceda5b307e6979aa8776fe444f9ffa3ff` |
| Ground motion | 4×4 at 1256×1256 | 314×314 | 16 | `07-ground-motion-sheet-candidate-v2.png` | `7f0446dd2f680a19aa323da7e3046524d67c768fda3c4c30200634b520518be7` |
| Signature actions | 4×4 at 1256×1256 | 314×314 | 16 | `08-signature-actions-sheet-candidate-v1.png` | `b776b51e12c9c94638cb23bf23790d2b287850f80c4580ab2f18fa7bf0c58f2d` |
| Interaction poses | 2×2 at 1254×1254 | 627×627 | 4 | `09-interaction-poses-candidate-v1.png` | `228c68cdec75ef836cc685562f7666d0a685491b048197f56bb7ea8274d737bf` |
| **Total** |  |  | **124** |  |  |

The five 4×4 built-in outputs arrived at 1254×1254. They were normalized once to 1256×1256 so every accepted cell is an equal 314×314 integer region. The 6×4 and 4×2 sheets were already integer-divisible. The 2×2 sheet is exactly divisible at 627×627 per cell.

## Deterministic cell maps

All maps are zero-ambiguity, left-to-right then top-to-bottom.

### 01 — Identity (16)

1. neutral full-body front
2. neutral full-body three-quarter left
3. face close-up front
4. face close-up three-quarter
5. long dark-brown hair construction front
6. hair construction back
7. taupe draped top construction front
8. taupe draped top construction back
9. full green skirt front
10. skirt back
11. brown flat shoe side
12. brown flat shoe front
13. dark-red rubric folio with gold grid mark
14. gray clipboard with square checklist
15. teal wrist motif close-up
16. canonical scale/proportion reference

### 02 — Turnaround (8)

1. front
2. front three-quarter left
3. left profile
4. back three-quarter left
5. back
6. back three-quarter right
7. right profile
8. front three-quarter right

### 03 — Neutral bases (8)

1. neutral front stance
2. neutral three-quarter stance
3. neutral side stance
4. neutral back stance
5. relaxed idle
6. attentive evaluation idle
7. speaking idle, measured gesture
8. listening idle, hands lowered

### 04 — Expressions (24)

1. neutral
2. calm
3. joy
4. amusement
5. excitement
6. curiosity
7. confidence
8. compassion
9. surprise
10. confusion
11. skepticism
12. concern
13. sadness
14. shame
15. embarrassment
16. fear
17. anxiety
18. anger
19. frustration
20. determination
21. fatigue
22. contemplation
23. evidence-based approval
24. decisive rejection

### 05 — Visemes and blinks (16)

1. rest mouth
2. closed lips
3. slightly open mouth
4. wide vowel
5. open vowel
6. rounded vowel
7. teeth consonant
8. lower-lip consonant
9. tongue consonant
10. smile while speaking
11. frown while speaking
12. speech emphasis
13. breath/pause
14. eyes fully open
15. half blink
16. full blink

### 06 — Hands and props (16)

1. open relaxed hand
2. closed relaxed hand
3. fist
4. pointing hand
5. presenting hand
6. reaching hand
7. rubric-folio grip
8. clipboard grip
9. rubric against torso
10. clipboard inspection hold
11. offering rubric
12. receiving rubric
13. two-hand rubric/clipboard comparison
14. checklist marking with fingertip
15. prop release
16. empty-hand settled recovery

### 07 — Ground motion (16)

1. walk contact A
2. walk passing A
3. walk contact B
4. walk passing B
5. run contact A
6. run contact B
7. locomotion start anticipation
8. locomotion stop/brake
9. planted turn left
10. planted turn right
11. crouch
12. jump anticipation
13. jump airborne
14. fall descending
15. landing contact
16. landing recovery

Cells 9 and 10 are opposite body/head rotations with both feet visibly planted. Cells 13–16 preserve the anticipation/airborne/descent/contact/recovery logic without clipping.

### 08 — Signature action arcs (16)

1. prepare rubric folio
2. present standard
3. indicate rubric grid
4. close rubric at chest
5. raise clipboard
6. inspect checklist
7. indicate checked square
8. lower clipboard thoughtfully
9. hold rubric and clipboard separately
10. compare side-by-side
11. flag gap with controlled point
12. document exception
13. deliberate, props lowered
14. evidence-based approval
15. decisive rejection/stop
16. neutral settled hold

### 09 — Interaction states (4)

1. open relaxed hand offered forward
2. closed relaxed hand at side
3. firm fist near torso
4. full reach toward offscreen object

## Candidate rejection log

`07-ground-motion-sheet-candidate-v1` was rejected before project ingestion because the generator divided its fourth row into five narrow panels, producing 17 visual poses rather than the required 16 equal cells. Rejected source SHA-256: `df8ed3eb6191a32fd7eb0300b2f9909dc672bb72bd64e2cfb6dec416d2978dbb`. It is not an approved derivative and is not referenced by production instructions. The corrected v2 is a rigid 4×4 matrix.

No other candidate was accepted with missing panels, text, runtime bust framing, unapproved props, identity redesign, or clipped full-body silhouette.

## 124-cell reference audit

The accepted sheets were decoded as RGB PNGs and split only by the geometry in the table above. Audit results:

- expected cells: 124; decoded cells: 124
- unique normalized cell thumbnails: 124 of 124
- empty cells: 0
- integer-divisibility failures: 0
- duplicate thumbnail hashes within any sheet: 0
- closest cross-cell normalized grayscale mean absolute difference: 0.730, between speech cells 9 and 13; the source cells remain distinct and semantically mapped
- visible text/captions/watermarks: 0
- unapproved props: 0
- accepted non-full-body runtime-source cells: 0 outside the intentionally diagnostic identity and hand/prop sheets
- full-body expression cells: 24 of 24
- full-body viseme/blink cells: 16 of 16
- opposite planted turn cells: present at ground-motion cells 9 and 10
- source-reference mutation: none; documented source hash remains unchanged

The contact sheets were also visually inspected for face, age, hair, top construction, skirt length, shoe shape, wrist side, prop scale, cube scale, studio logic, baseline continuity, and complete margins. Reference-sheet floor shadows and pale backgrounds are explicitly non-production data.

## Mandatory reference-to-runtime gate

The visualizer implementation must perform this sequence for **all 124 cells**, with no exemptions or direct image fallback:

1. Slice the accepted worksheet using its exact integer grid; do not use content-aware or inferred boundaries.
2. Remove the entire sheet/cell background, floor grid, cast/contact shadow, divider, and neighboring-cell contamination.
3. Isolate the character, body part, or approved prop as a transparent silhouette.
4. Quantize the isolated silhouette to the character package's canonical square-cell palette and scale without changing identity geometry.
5. Normalize every cell to a stable origin/root and baseline; retain at least four transparent pixels on every side used by motion, including hair, skirt, hands, airborne feet, and props.
6. Convert each normalized cell to its own transparent colored-pixel graph. Store only colored pixel nodes or horizontal/vertical color runs plus required anchors, pivots, bounds, baseline, and attachment metadata.
7. Do **not** store or load PNG, JPEG, WebP, SVG, data-URI, canvas snapshot, or other raster/vector render assets in the runtime character package.
8. Have the visualizer projector paint the graph's colored cells onto the animation canvas for every rendered frame.
9. Re-audit all **124 isolated silhouettes** against the accepted contact sheets for identity, crop, bounds, background residue, holes, prop contacts, palette, root, and baseline.
10. Independently re-audit all **124 pixel graphs** after serialization/deserialization for node/run count, color fidelity, bounds, anchors, pivots, attachment points, deterministic checksum, and projected-pixel equivalence.
11. Render a 124-cell projector contact sheet from graph data alone and compare it with the isolated-silhouette contact sheet. Every non-transparent projected pixel must match the graph; no runtime image decoder may participate.
12. Only after the 124/124 silhouette audit and 124/124 graph audit pass may poses be connected to animation states, transitions, REST/WebSocket routes, registry, or browser selector.

Any failure keeps the affected cell and every animation that depends on it disconnected. Fallback to a worksheet image, hero image, PNG crop, SVG, or another persona's cell is forbidden.

## Animation reconnection checklist

For each animation, document the canonical start/end cells, anticipation, action, follow-through, recovery, contacts, pivots, timing, and entry/exit states. Test projection at runtime speed and slow motion. Specifically reject foot sliding, root drift, scale popping, hair/skirt clipping, mirrored wrist asymmetry, prop teleportation, lost checklist/rubric geometry, and any frame that paints outside canonical bounds.

This record approves only the canonical reference package. Runtime conversion, character registration, animation wiring, tests, and browser evidence are separate implementation gates and are not claimed here.
