# Aurelia Finch — Canonical Worksheet Generation Record

Status: accepted reference worksheet package; runtime conversion is intentionally not performed on this preparation branch.

## Authorities and preservation

| Asset | Role | Dimensions | SHA-256 |
|---|---|---:|---|
| `assets/reference/personas/aurelia-finch/source-reference.png` | Immutable original | 1024×1536 | `bd8bc74059e57f8edafb0161bcbc7b70dd52ddddc59ec72dd1808f8287c87f41` |
| `assets/reference/personas/aurelia-finch/canonical-voxel.png` | Approved voxel identity authority | 1122×1402 | `462dbff7c21e06c4450bf620f13f0bb7c923f57dd4819cb11eb9bfcc8853a821` |

Both authority files were hashed before generation and again after the accepted worksheets were saved. Their hashes were unchanged. No crop, repaint, overwrite, or metadata rewrite was performed on either authority.

## Generation method

- Mode: built-in GPT Image (`image_gen`), not CLI fallback.
- Reference role: `canonical-voxel.png` was the hard production identity reference; `source-reference.png` was supporting immutable identity evidence for the identity sheet.
- Prompt lock shared by all sheets: Aurelia's adult age, warm brown skin, long dark curls, cream wide-brim hat with navy band and right-side orange accent, pearls, burnt-orange wrap dress, brown heels, dark-brown/gold-corner folio, fine cube scale, soft-blue studio, fixed camera, complete silhouettes, and no unapproved objects or readable text.
- Generated outputs were copied from the built-in output store into the project. Accepted grids were mechanically normalized to integer-divisible dimensions without cropping.

## Accepted worksheets and deterministic geometry

The nine accepted grids contain **exactly 124 cells**. Every width is evenly divisible by its column count and every height is evenly divisible by its row count.

| # | Accepted file | Grid | Sheet px | Cell px | Cells | SHA-256 | Cell audit |
|---:|---|---:|---:|---:|---:|---|---|
| 01 | `01-identity-sheet-candidate-v1.png` | 4×4 | 1024×1024 | 256×256 | 16 | `e28850447f89019ee187b2a628cfa9aa43e014e802425f1ae5780135927752a5` | 1–16 pass |
| 02 | `02-turnaround-sheet-candidate-v1.png` | 4×2 | 1024×1024 | 256×512 | 8 | `c700743f194af0103094ab4dd9f62ad5d70e96c3b7df6a6c2c96cd91b14737b9` | 17–24 pass |
| 03 | `03-neutral-base-poses-candidate-v1.png` | 4×2 | 1792×896 | 448×448 | 8 | `a83466add91e58406390ca97f83e4764674952dba0b89579db982085f9c6378f` | 25–32 pass |
| 04 | `04-expression-sheet-candidate-v2.png` | 6×4 | 1536×1024 | 256×256 | 24 | `68f0a6e5fec8b9ebd3f5a455a8020710c14e42184cad6950e3625b31dbaf87d7` | 33–56 pass |
| 05 | `05-speech-viseme-sheet-candidate-v2.png` | 4×4 | 1024×1024 | 256×256 | 16 | `900ca79efd2141691a28385565fb2d646695981a0d23d854f6ea25ba033e26c3` | 57–72 pass |
| 06 | `06-hand-prop-sheet-candidate-v1.png` | 4×4 | 1024×1024 | 256×256 | 16 | `53125372d018bc6f7bf7f52e089b4cf42749e281f5a2c6d5e4a7cc03cd626ae1` | 73–88 pass |
| 07 | `07-ground-motion-sheet-candidate-v1.png` | 4×4 | 1024×1024 | 256×256 | 16 | `999d80d4195ba8be4d93599b1b119e55ea9c82b6eaeb9c672b9a9e0ecf239607` | 89–104 pass |
| 08 | `08-signature-actions-sheet-candidate-v2.png` | 4×4 | 1024×1024 | 256×256 | 16 | `18934f91ae9f21b9144e5db2137a3c9800874e3d422ef3803aa686778bb205b0` | 105–120 pass |
| 09 | `09-interaction-poses-candidate-v1.png` | 2×2 | 1024×1024 | 512×512 | 4 | `57f27892803ad1b5d0e8ea44b02404f3de558a499826d7584bdf21de34164849` | 121–124 pass |

Count proof: `16 + 8 + 8 + 24 + 16 + 16 + 16 + 16 + 4 = 124`.

## Exact row-major panel maps

### 01 — Identity references (cells 1–16)

1. Neutral full-body front
2. Neutral full-body three-quarter
3. Neutral full-body profile
4. Neutral full-body back
5. Face front close-up
6. Face three-quarter close-up
7. Hat front detail
8. Hat right-side orange-accent detail
9. Dress neckline and wrap detail
10. Dress waist and tie detail
11. Dress cuff and sleeve detail
12. Layered skirt and hem detail
13. Open relaxed hand
14. Brown block-heel shoe
15. Closed folio exterior
16. Pearl necklace and earring detail

### 02 — Eight-view turnaround (cells 17–24)

1. Front
2. Front three-quarter left
3. Left profile
4. Back three-quarter left
5. Back
6. Back three-quarter right
7. Right profile
8. Front three-quarter right

### 03 — Neutral anchors (cells 25–32)

1. Neutral front stance
2. Neutral front three-quarter stance
3. Neutral right-facing side stance
4. Neutral back stance
5. Relaxed idle
6. Attentive idle with closed folio
7. Speaking idle with open-hand gesture
8. Listening idle with low two-hand folio hold

### 04 — Full-body expressions (cells 33–56)

1. Neutral
2. Calm
3. Joy
4. Amusement
5. Excitement
6. Curiosity
7. Confidence
8. Compassion
9. Surprise
10. Confusion
11. Skepticism
12. Concern
13. Sadness
14. Shame
15. Embarrassment
16. Fear
17. Anxiety
18. Anger
19. Frustration
20. Determination
21. Fatigue
22. Contemplation
23. Neutral recovery
24. Calm recovery

### 05 — Full-body speech and blink states (cells 57–72)

1. Rest mouth
2. Closed lips
3. Slightly open
4. Wide vowel
5. Open vowel
6. Rounded vowel
7. Teeth consonant
8. Lower-lip consonant
9. Tongue consonant
10. Smile while speaking
11. Frown while speaking
12. Speech emphasis
13. Breath or pause, eyes open
14. Rest mouth, eyes fully open
15. Rest mouth, half blink
16. Rest mouth, full blink

### 06 — Hands and folio (cells 73–88)

1. Relaxed open hand
2. Closed relaxed hand
3. Firm fist
4. Pointing hand
5. Presenting palm
6. Reaching hand
7. Closed-folio side grip
8. Closed-folio underarm grip
9. Folio held at chest
10. Closed folio presented outward
11. Folio offered with two hands
12. Folio received with two hands
13. Stakeholder handshake contact
14. Plain blank evidence page
15. Diplomatic open-palms pair
16. Settled two-hand folio hold

### 07 — Ground and air motion (cells 89–104)

1. Walk contact left
2. Walk down left
3. Walk passing left
4. Walk contact right
5. Run contact left
6. Run contact right
7. Locomotion start anticipation
8. Locomotion stop recovery
9. Planted turn left, left heel anchor
10. Planted turn right, right heel anchor
11. Crouch
12. Jump anticipation
13. Jump airborne
14. Controlled fall
15. Landing contact
16. Landing recovery

### 08 — Persona-specific four-key action arcs (cells 105–120)

1. Partnership pitch — compose
2. Partnership pitch — invitation
3. Partnership pitch — outward pitch
4. Partnership pitch — recovery
5. Stakeholder translation — listen
6. Stakeholder translation — two-hand translation
7. Stakeholder translation — bridge
8. Stakeholder translation — acknowledge
9. Proof presentation — ready
10. Proof presentation — reveal blank evidence
11. Proof presentation — point to proof
12. Proof presentation — close and secure
13. Public promise check — pause
14. Public promise check — commitment
15. Leadership recovery — reconsider
16. Leadership recovery — diplomatic settle

### 09 — Full-body interaction hand states (cells 121–124)

1. Open
2. Closed
3. Fist
4. Reach

## Cell-by-cell visual audit

All 124 accepted cells were inspected at full sheet resolution after the final mechanical dimension normalization. The audit checked:

- identity anchors and apparent age;
- hat presence, right-side accent placement, pearls, hair length and volume;
- dress construction, wrap direction, waist tie, cuffs, hem, heels, and folio dimensions;
- complete extractable silhouette and internal cell clearance;
- stable cube scale, camera language, lighting, palette, and baseline;
- expected expression, viseme, blink, hand state, motion key, and action-arc role;
- limb and digit count, prop restrictions, absence of readable text, and absence of sheet-title contamination;
- distinct left/right planted turns and distinct open/half/full blink states.

Result: **124/124 accepted cells passed the worksheet-stage visual gate.** This is approval of the reference panels, not approval of future background masks or runtime graphs.

## Rejected generations

The following built-in outputs were inspected and rejected before project acceptance; they were not copied into the worksheet directory:

- Expression attempt `exec-126e1c4c-8389-4544-b3a4-e08fcd105571.png`: wrong 8×3 arrangement rather than required 6×4.
- Expression attempt `exec-79e572ef-a794-45fb-bb6d-4c1327ec2913.png`: correct 6×4 grid, but bottom-row silhouettes were cropped.
- Speech attempt `exec-6e239f16-cfce-4a75-8e0f-8c1a5d395ad9.png`: final blink triplet did not clearly distinguish open, half, and fully closed eyelids.
- Signature-action attempt `exec-63605af3-acf8-4029-95f7-adf74dfa718f.png`: bottom-row heels were cropped.

Each rejection was corrected with one targeted prompt revision, and only the corrected successor was accepted.

## Mandatory runtime-conversion handoff

The accepted worksheet PNGs are reference/contact sheets only. They must never be loaded, decoded, displayed, or projected by the runtime.

Before reconnecting Aurelia to any animation state or transition:

1. Split the accepted grids deterministically using the exact geometry and maps above, yielding exactly 124 isolated cells.
2. Remove the sheet/cell background from every isolated cell first.
3. Re-audit **all 124 isolated transparent silhouettes** for complete hat, hair, hands, dress, heels, folio, margins, identity, and absence of separator/background contamination.
4. Convert each approved transparent silhouette into its own transparent pixel graph.
5. Store colored pixel nodes/runs in the direct-cell pose library. Do **not** store or consume PNG or SVG render assets at runtime.
6. Have the visualizer projector paint those colored nodes/runs directly onto its canvas for each animation frame.
7. Re-audit **all 124 pixel graphs** against their approved transparent silhouettes for bounds, root/baseline, color, missing runs, stray pixels, transparency, and identity.
8. Only after both 124-item audits pass may animation states, transitions, timing, and recovery arcs be reconnected.

The future conversion record must therefore contain two explicit gates: `isolated_silhouettes: 124/124 pass` and `pixel_graphs: 124/124 pass`. Worksheet acceptance alone does not satisfy either gate.
