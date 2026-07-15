# Serena Quill — Canonical Worksheet Generation Record

## Status

The Serena Quill canonical production worksheet package contains nine accepted board types and exactly **124 deterministic cells**. Sheet 01 v1 is retained only as a rejected provenance artifact; Sheet 01 v2 is the production candidate.

This record covers reference generation and human-readable visual QA. It does not approve runtime integration. Runtime acceptance still requires isolation, background removal, pixel-graph conversion, per-cell re-audit, animation mapping, live playback, and the complete branch acceptance gate.

## Provenance

- Tool path: built-in GPT Image workflow (`image_gen`), not CLI fallback.
- Use case: `stylized-concept` with identity-preserving reference generation.
- Absolute character authority: `assets/reference/personas/serena-quill/canonical-voxel.png`
- Supporting original provenance: `assets/reference/personas/serena-quill/source-reference.png`
- Original SHA-256: `1a388910b47b351427981f029dfac90366ffbc9bf891f7bcb294994381d19d3d`
- Canonical SHA-256: `e1a0d2eac7a867b0bbf60810de5cfab40f328bceba6f61b2a18c717b8bcc0349`
- Original and canonical references were read but not overwritten, cropped, repainted, or otherwise modified.

## Shared prompt lock

Every production prompt named `canonical-voxel.png` as the absolute identity authority and repeated these invariants: bright-orange stepped bob; softly squared peach face; dark rectangular eyes; one complete centered circular gold halo; warm-cream floor-length broad-sleeved robe with vertical folds and flared hem; small cream block footwear; two broad symmetrical stepped cream wings; one fixed-size warm orange-gold voxel orb when mapped; fixed cube scale; pale-blue studio; soft frontal-upper lighting; complete silhouette; stable camera/root/baseline; generous margins; no clipping, redesign, extra anatomy, extra props, costume drift, realistic feathers/fingers, text, watermark, or scenery.

Each board prompt also specified its exact grid and row-major semantic mapping. The identity board was regenerated after the required package count changed from 117 to exactly 124 cells.

## Accepted files, dimensions, hashes, and extraction geometry

Cell rectangles are isolated deterministically with integer proportional boundaries:

`x0=floor(column*width/columns)`, `x1=floor((column+1)*width/columns)`, `y0=floor(row*height/rows)`, `y1=floor((row+1)*height/rows)`.

This formula handles the few one-pixel remainder differences without interpolation, overlap, or dropped pixels. Pale-blue gutters visually separate every cell.

| Sheet | File | Grid | Cells | Pixel dimensions | SHA-256 | Visual status |
|---|---|---:|---:|---:|---|---|
| 01 | `01-identity-sheet-candidate-v2.png` | 4x4 | 16 | 1254x1254 | `18ae92d61482755c06960b3bb532d2e56a45cc59bb7070cd06bac7e2315f3602` | Accepted production candidate |
| 02 | `02-turnaround-sheet-candidate-v1.png` | 4x2 | 8 | 1536x1024 | `d476d6aa2d1c2961135a6e6774bde2fc50d765174cddca0cec9c273201bfdafd` | Accepted production candidate |
| 03 | `03-neutral-base-poses-candidate-v1.png` | 4x2 | 8 | 1774x887 | `be5702f9e655dac6bf9b826bf162588d0d6cf69f91ddb1e3cf3ead6f8697fdf2` | Accepted production candidate |
| 04 | `04-expression-sheet-candidate-v1.png` | 6x4 | 24 | 1536x1024 | `f163614a617a6ca601e9862d4b04843ec77b8d9bf53c9b60926951cb8fba1f71` | Accepted production candidate |
| 05 | `05-speech-viseme-sheet-candidate-v1.png` | 4x4 | 16 | 1536x1024 | `f35dc783f6192a99f6b422c7cc1dd5408d74d8afb57c84277f40aee87582a29f` | Accepted production candidate |
| 06 | `06-hand-prop-sheet-candidate-v1.png` | 4x4 | 16 | 1448x1086 | `b7ef9f1f79840efc0892f52590341e8847dbb2bd01a1d29456e773ce27661c41` | Accepted production candidate |
| 07 | `07-ground-motion-sheet-candidate-v1.png` | 4x4 | 16 | 1536x1024 | `85082be9d7566eefe4af68301896ec4d41ec9fb8c5745e7c1840e983500a4413` | Accepted production candidate |
| 08 | `08-signature-actions-sheet-candidate-v1.png` | 4x4 | 16 | 1448x1086 | `6f3db8f1ab455a593f33af235ba634041899a7d174264c2ab15d7b18271e7c94` | Accepted production candidate |
| 09 | `09-interaction-poses-candidate-v1.png` | 2x2 | 4 | 1254x1254 | `353b91fc8492aac9f544a79584545dfcd12388416584d43633b9ccec341c856e` | Accepted production candidate |
| **Total** | Sheets 01–09 | — | **124** | — | — | **Required isolation count** |

## Rejected artifact

`01-identity-sheet-candidate-v1-rejected.png` (3x3, 1254x1254, SHA-256 `42bfd209f4e493164ef56c8c466f99c39a12cee1ddd7155b0515790c74555301`) is rejected because its nine-cell layout cannot satisfy the required 16-cell Sheet 01 or 124-cell package total. Its character rendering was visually useful, but its geometry and cell count make it non-production. It must not be isolated, converted, registered, or used as a runtime source.

## Exact row-major mappings

### Sheet 01 — identity/reference, 4x4, 16 cells

1. Original-source visual reference inset
2. Approved canonical full-body front with orb
3. Normalized neutral full-body front
4. Normalized neutral full-body front-three-quarter
5. Face close-up
6. Full-body left profile
7. Full-body back
8. Palette/material swatches
9. Full-body robe construction front with wings relaxed
10. Full-body robe construction back with wings relaxed
11. Complete wing construction front
12. Complete wing construction back
13. Full-body halo construction/profile
14. Full-body orb construction/offer
15. Full-body open-hand design with hand clear of torso
16. Full-body scale/proportion guide

### Sheet 02 — turnaround, 4x2, 8 cells

1. Front
2. Front three-quarter left
3. Left profile
4. Back three-quarter left
5. Back
6. Back three-quarter right
7. Right profile
8. Front three-quarter right

### Sheet 03 — neutral bases, 4x2, 8 cells

1. Neutral front stance with orb
2. Neutral front-three-quarter stance with orb
3. Neutral side stance with orb
4. Neutral back stance
5. Relaxed idle
6. Attentive idle
7. Speaking idle
8. Listening idle

### Sheet 04 — full-body expressions, 6x4, 24 cells

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
23. Mentoring reassurance
24. Quiet containment / settled listening

### Sheet 05 — full-body speech and blinks, 4x4, 16 cells

1. Rest mouth
2. Closed lips
3. Slightly open mouth
4. Wide vowel
5. Open vowel
6. Rounded vowel
7. Teeth consonant
8. Lower-lip consonant
9. Tongue consonant
10. Smile while speaking
11. Frown while speaking
12. Speech emphasis
13. Breath or pause
14. Eyes fully open
15. Half blink
16. Full blink

### Sheet 06 — full-body hands and orb, 4x4, 16 cells

1. Open relaxed hand
2. Closed relaxed hand
3. Safe nonthreatening fist
4. Gentle pointing hand
5. Presenting hand
6. Reaching hand
7. Canonical two-hand orb cradle
8. One-hand orb support
9. Orb lowered
10. Orb offered
11. Orb received
12. Orb transfer
13. Two-hand reassurance around orb
14. Open-palmed consent pause
15. Release gesture with orb settled
16. Settled listening hands with orb lowered

### Sheet 07 — full-body grounded motion, 4x4, 16 cells

1. Walk contact left
2. Walk down left
3. Walk passing right
4. Walk up right
5. Run contact left
6. Run passing right
7. Locomotion start anticipation
8. Locomotion stop / brake
9. Planted turn left
10. Planted turn right
11. Crouch
12. Jump anticipation
13. Airborne jump
14. Controlled fall
15. Landing contact
16. Landing recovery

### Sheet 08 — full-body signature actions, 4x4, 16 cells

1. Mentoring invitation
2. Emotional-climate check
3. Consent pause
4. Facilitation
5. Orb reassurance
6. Protective wing fold
7. Careful referral to human help
8. Active listening
9. Compassionate agreement
10. Safe disagreement
11. Reflective question
12. Clear supportive answer
13. Restrained luminous encouragement
14. Careful celebration
15. De-escalation
16. Plain still containment / settled presence

### Sheet 09 — full-body interaction poses, 2x2, 4 cells

1. Open interaction stance
2. Closed interaction stance
3. Safe nonthreatening fist emphasis
4. Forward reach

## Human-readable visual audit

- **Identity:** accepted. Orange bob, rectangular eyes, circular halo, cream robe, paired stepped wings, and orange-gold orb remain recognizable throughout.
- **Scale and baseline:** accepted at worksheet-reference level. Runtime boards maintain comparable full-body scale and stable studio framing; dynamic airborne/fall cells remain fully bounded.
- **Margins:** accepted. Entire halo, wing tips, hands, robe hem, and feet are visible in all runtime-oriented panels. No worksheet cell has an intentionally cropped silhouette.
- **Turnaround:** accepted. Eight directional views preserve height, head scale, robe construction, halo depth, wing roots, and left/right symmetry. Rear views use the logged least-disruptive construction.
- **Neutral bases:** accepted. Eight distinct anchor states are readable; listening uses a gentle incline and settled wings.
- **Expressions:** accepted. All 24 cells are full body; face, skull, age, costume, and wing construction remain stable while posture and orb/wing energy carry emotion.
- **Speech/blinks:** accepted. All 16 cells are full body; mouth variations are restrained; panels 14–16 form an open/half/full blink sequence.
- **Hands/prop:** accepted. All 16 cells preserve complete silhouettes; free hands are posed clear of the torso; only one fixed-size orb appears when mapped.
- **Ground motion:** accepted. Four walk keys, two run keys, start, stop, crouch, jump, fall and landing states are distinct. Cells 9 and 10 form a visibly mirrored planted-foot turn pair.
- **Signature actions:** accepted. Mentoring, consent, referral, protective fold, de-escalation and still containment are nonthreatening and persona-aligned.
- **Interaction poses:** accepted. Open, closed, fist-emphasis and reach states are distinct and keep the full silhouette in frame.
- **Forbidden drift check:** passed at contact-sheet review level: no new costume, weapon, book, staff, microphone, armor, jewelry, extra wing, missing limb, or different rendering medium.

## Runtime handoff — mandatory 124-cell pixel-graph conversion

1. Treat the accepted Sheet 01 v2 and Sheets 02–09 as the only extraction sources.
2. Isolate exactly **124 cells** using the grid metadata and proportional integer boundary formula above: 16 + 8 + 8 + 24 + 16 + 16 + 16 + 16 + 4.
3. Remove the pale-blue background independently from every isolated cell. Preserve the complete halo glow and orb glow while making all non-character/background pixels transparent.
4. Normalize each isolated pose to the character package's canonical transparent canvas with the required safety inset, stable root, and pose-appropriate baseline. Do not rescale one pose independently merely to fill its cell.
5. Convert each normalized transparent pose into its **own transparent pixel graph**.
6. Store only colored pixel nodes and/or deterministic horizontal colored-pixel runs plus required graph metadata. Runtime character rendering must never load, decode, display, or project a PNG or SVG asset.
7. The existing canvas projector must paint each frame from the stored colored pixel graph/runs.
8. Before reconnecting any animation mapping, re-audit **all 124 isolated silhouettes and all 124 generated graphs** against the accepted worksheets. Verify identity, cell mapping, background removal, transparent bounds, halo/wing tips, orb presence, root, baseline, scale, colors, connected components, and absence of neighboring-cell contamination.
9. Only after the 124/124 silhouette and 124/124 graph audit passes may poses be mapped to the animation graph, matrix, state transitions, speech, expressions, interactions, and signature actions.
10. Keep the original source and all worksheet PNGs strictly in reference material. They are evidence and derivation sources, never runtime render assets.

## Required runtime audit evidence

- Machine-readable list of all 124 cell IDs, source sheet, row, column, pixel bounds, semantic name, isolated-silhouette hash, graph hash, node/run count, transparent bounds, root, baseline, and validation result.
- A human-readable 124-cell isolated-silhouette contact sheet and a separate 124-cell graph-render contact sheet.
- Automated equality or bounded-difference comparison between each isolated silhouette and its canvas-projected graph render.
- Explicit zero-count checks for missing, duplicated, unmapped, or extra cells.
- Live visualizer evidence for idle, locomotion, expression, speech, blink, interaction, signature action, and widest-wing silhouette, with zero clipping and no PNG/SVG runtime loads.
