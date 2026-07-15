# Mira Solen — 124-Cell Worksheet Generation Record

## Scope and acceptance state

Mira's canonical reference package contains exactly **124 accepted cells** across nine deterministic worksheets. All sheets were generated with the built-in GPT Image workflow, visually inspected at sheet scale, decoded successfully, checked for exact grid divisibility, counted, hashed, and compared for accidental duplicates. They remain pose references only; no worksheet image is a runtime asset.

| Sheet | Geometry | Cell geometry | Count | Accepted file | SHA-256 |
| --- | ---: | ---: | ---: | --- | --- |
| Identity | 4x4 at 1256x1256 | 314x314 | 16 | `01-identity-sheet-candidate-v3.png` | `8fa5e28a04b7b710cbdcc5ba30b6678a81857799c83ced9b082cfff4475825f1` |
| Turnaround | 4x2 at 1672x940 | 418x470 | 8 | `02-turnaround-sheet-candidate-v1.png` | `8f19fe35f59b5166ad519bba585d449d7f9657a80f1a3763e4868d9da216803e` |
| Neutral bases | 4x2 at 1672x940 | 418x470 | 8 | `03-neutral-base-poses-candidate-v1.png` | `a5b3d36f7082cef78087451e7d2ecec2a540cc4838e0d536e1ff07bc0bd6bcfc` |
| Expressions | 6x4 at 1536x1024 | 256x256 | 24 | `04-expression-sheet-candidate-v1.png` | `5019c020e9e966636d4763b10773c9a8780ced1060b68a93a34d332eea5189ff` |
| Visemes/blinks | 4x4 at 1256x1256 | 314x314 | 16 | `05-speech-viseme-sheet-candidate-v2.png` | `0f62d92637b2cfab45fefb8b6f3b39ff907c428433f1339ea23971b5199fdb61` |
| Hands/props | 4x4 at 1256x1256 | 314x314 | 16 | `06-hand-prop-sheet-candidate-v1.png` | `198dcb84a6d04380adad200861a419be701f957458317fcad503bcb38717e8ab` |
| Ground motion | 4x4 at 1256x1256 | 314x314 | 16 | `07-ground-motion-sheet-candidate-v1.png` | `1dc7bb65a8a50337038d4acfe643ec6b8de59a308a3d2a095632ccea1225ad76` |
| Signature actions | 4x4 at 1256x1256 | 314x314 | 16 | `08-signature-actions-sheet-candidate-v1.png` | `57da614af36d3e8c8f530e8650ce6eaaa36bac4b3f648fa13ec9cd13f7212e0a` |
| Interaction poses | 2x2 at 1254x1254 | 627x627 | 4 | `09-interaction-poses-candidate-v1.png` | `fb77553dcb627d74f2dbfce81d450d39fa012d690b4818f8e535c3aaf33e70fc` |
| **Total** |  |  | **124** |  |  |

Built-in 4x4 outputs arrived at 1254x1254 and were normalized once to 1256x1256 so every accepted cell is an equal 314x314 integer region. The 4x2 sheets arrived at 1672x941 and were normalized once to 1672x940 so their cells are exact 418x470 regions. The 6x4 sheet was already integer-divisible. The 2x2 sheet is exactly divisible at 627x627 per cell. These deterministic worksheet normalizations did not modify `source-reference.png` or `canonical-voxel.png`.

## Deterministic cell maps

All maps are left-to-right then top-to-bottom.

### 01 — Identity (16)

1. neutral full-body front
2. neutral full-body three-quarter
3. neutral full-body profile
4. neutral full-body back
5. face close-up front
6. face close-up three-quarter
7. hair construction front
8. hair construction back
9. asymmetrical dress construction front
10. asymmetrical dress construction back
11. upper-arm geometric emblem close-up
12. black cord and gold pendant close-up
13. open relaxed hand
14. closed relaxed hand
15. white low block shoe
16. black tray with orange core and blue outer flame

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
5. relaxed reflective idle
6. attentive listening idle
7. speaking idle with measured open gesture
8. contemplative idle with hands settled

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
23. inspired delight
24. protective resolve

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

### 06 — Hands and signature artwork prop (16)

1. open relaxed hand
2. closed relaxed hand
3. firm fist
4. pointing hand
5. presenting hand
6. reaching hand
7. two-hand tray grip close-up
8. one-hand tray support detail
9. tray level at torso
10. artwork reveal forward
11. offering tray
12. receiving tray
13. drawing tray protectively inward
14. deliberate slight tray tilt
15. prop release transition
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

Cells 9 and 10 use opposite body/head rotations with both feet visibly planted. Cells 12-16 preserve anticipation, airborne, descent, contact, and recovery without clipping.

### 08 — Signature action arcs (16)

1. prepare tray at waist
2. raise artwork
3. reveal artwork forward
4. settle reveal
5. invite critique with open hand
6. listen contemplatively
7. acknowledge student voice
8. dignified recovery
9. notice public discomfort
10. draw artwork protectively inward
11. shield dignity with calm stop hand
12. reassuring recovery
13. creative reframe with compressed flame
14. blue-flame inspiration with upward flare
15. amplify student voice with open upward gesture
16. neutral settled hold

### 09 — Interaction states (4)

1. open relaxed hand offered forward
2. closed relaxed hand at side
3. firm fist near torso
4. full-body reach toward an offscreen object

## Candidate rejection log

- `01-identity-sheet-rejected-v1.png` was rejected because it contains only eight cells and cannot satisfy the 16-cell identity map. SHA-256: `ef6add4529bd237bc46cbe491097aa27312baba2e185e430ddc99c6fba58bc18`.
- `01-identity-sheet-rejected-v2.png` was rejected because the diagnostic map drifted: the geometric emblem appears on the back garment and one face construction panel omits the canonical face. SHA-256: `e175330bfb6b748e91fe9662125e85306cee5307f8d45d609d2f872fb948af41`.
- `05-speech-viseme-sheet-rejected-v1.png` was rejected because the final blink stages are not visibly distinct enough to provide separate half-blink and full-blink references. SHA-256: `2aa1b876765da7adcf241cec40e63019b5fb4ec15c38587d72927069ed8c500e`.

No rejected candidate is an approved derivative or a production instruction.

## 124-cell reference audit

The accepted sheets were decoded as RGB PNGs and split only by the geometry in the table above. Audit results:

- expected cells: 124; decoded cells: 124
- exact unique cell pixel hashes: 124 of 124
- empty cells: 0
- integer-divisibility failures: 0
- duplicate cell hashes within any sheet: 0
- closest normalized 32x32 grayscale thumbnail mean absolute difference: 1.274, between accepted speech cells 11 and 15; source cells remain distinct and semantically mapped
- visible captions, labels, or watermarks: 0
- unapproved props in accepted sheets: 0
- full-body expression cells: 24 of 24
- full-body viseme/blink cells: 16 of 16
- opposite planted turn cells: present at ground-motion cells 9 and 10
- source-reference mutation: none; source SHA-256 remains `ee88963dc59ab9efb8f4500734aa8a7b66f67b378e075088207df49cf6e08f6a`

The contact sheets were visually inspected for face, age, bob silhouette, dress construction, emblem laterality, pendant design, shoe shape, tray/flame continuity, cube scale, studio logic, baseline continuity, and complete margins. Reference-sheet backgrounds, floor grids, and shadows are non-production data.

## Mandatory reference-to-runtime gate

This package deliberately performs no runtime integration. Any later visualizer implementation must complete this sequence for **all 124 cells**, without exemptions or image fallback:

1. Slice each accepted worksheet using its exact integer grid; do not infer boundaries.
2. Remove the whole background, floor grid, cast/contact shadow, divider, and neighboring-cell contamination.
3. Isolate the character, body part, or approved prop as a transparent silhouette.
4. Quantize the silhouette to the canonical square-cell palette and scale without changing identity geometry.
5. Normalize every cell to a stable origin/root and baseline, retaining at least four transparent pixels on every motion side.
6. Convert every normalized cell to its own transparent colored-pixel graph with anchors, pivots, bounds, baseline, and attachment metadata.
7. Do not store or load PNG, JPEG, WebP, SVG, data URI, canvas snapshot, or any other raster/vector render asset in the runtime character package.
8. Re-audit all 124 isolated silhouettes for identity, crop, bounds, residue, holes, prop contacts, palette, root, and baseline.
9. Independently re-audit all 124 serialized pixel graphs for node/run count, color fidelity, bounds, anchors, pivots, attachment points, deterministic checksum, and projected-pixel equivalence.
10. Render a 124-cell projector contact sheet from graph data alone and compare it to the isolated-silhouette contact sheet.
11. Only after both audits pass 124/124 may poses connect to animation states, routes, registry, or browser selection.

Any failed cell and its dependent animations remain disconnected. Falling back to a worksheet image, hero image, PNG crop, SVG, or another persona is forbidden.

This record approves only the canonical reference package. Runtime conversion, character registration, animation wiring, tests, and browser evidence are separate gates and are not claimed here.
