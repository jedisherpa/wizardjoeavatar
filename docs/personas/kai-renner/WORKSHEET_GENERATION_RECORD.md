# Kai Renner Canonical Worksheet Production Specification

## Shared visual contract

Every sheet uses `canonical-voxel.png` as the highest visual authority. Kai must remain one identical adult voxel character: black flat-brim `BAKE` cap, square black glasses, blue-gray eyes, short brown hair, squared brown beard, bright yellow long-sleeve shirt, blue trousers, and near-black shoes. Use a fixed small-cube scale, full-body camera distance, pale cyan-blue studio backdrop, faint tiled floor, soft cool key light, and a restrained contact shadow. Keep at least ten percent clear space above the cap and around the widest gesture. Sheet 01 uses full-body identity/reference silhouettes and Sheet 06 uses isolated hand/prop construction silhouettes; every other panel is full body with both feet and the entire cap/brim visible. Do not render panel labels; mapping is positional and recorded below.

## Exact panel map

### 01 — Identity and references, 4 columns by 4 rows (`01-identity-sheet-candidate-v2.png`)

1. neutral front
2. canonical front three-quarter with right thumbs-up
3. strict left profile
4. exact back
5. neutral front face/glasses/beard invariant
6. back three-quarter rear-cap and hair invariant
7. neutral front wardrobe invariant
8. neutral side shoe and cap-brim invariant
9. prototype block held at torso
10. prototype safely offered
11. open left hand separated from torso
12. open right hand separated from torso
13. proportion-neutral front
14. palette/material full-body reference
15. attentive privacy/safety stance
16. upbeat default smile with decisive thumbs-up

Candidate v1 is retained as rejected evidence because its nonuniform callout layout cannot yield 16 deterministic extraction cells. Candidate v2 is the accepted 4-by-4 full-body identity grid.

### 02 — Eight-view turnaround, 4 columns by 2 rows (`02-turnaround-sheet-candidate-v1.png`)

1. front
2. front three-quarter left
3. left profile
4. back three-quarter left
5. back
6. back three-quarter right
7. right profile
8. front three-quarter right

All views use identical standing height, head size, baseline, neutral arms, and camera distance. The front cap word is not mirrored onto rear views.

### 03 — Neutral bases, 4 columns by 2 rows (`03-neutral-base-poses-candidate-v1.png`)

1. neutral front
2. neutral three-quarter
3. neutral side
4. neutral back
5. relaxed idle
6. attentive idle
7. speaking idle with small open presenting hand
8. listening idle with closed mouth and reduced amplitude

### 04 — Full-body expressions, 6 columns by 4 rows (`04-expression-sheet-candidate-v1.png`)

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
23. privacy-safety attentive
24. settled recovery

Every panel remains full body and expresses emotion through head angle, shoulders, spine, hands, stance, and face. No close-ups or bust crops.

### 05 — Full-body visemes and blinks, 4 columns by 4 rows (`05-speech-viseme-sheet-candidate-v1.png`)

1. rest mouth
2. closed lips
3. slightly open
4. wide vowel
5. open vowel
6. rounded vowel
7. teeth consonant
8. lower-lip consonant
9. tongue consonant
10. smile speaking
11. frown speaking
12. speech emphasis
13. breath/pause
14. blink closed
15. blink half-open
16. blink open recovery

All panels use the same full-body speaking-idle pose, camera, scale, baseline, and hands; only mouth/eyes and minimal facial emphasis change.

### 06 — Hand and prop construction, 4 columns by 4 rows (`06-hand-prop-sheet-candidate-v1.png`)

1. open relaxed hand
2. closed relaxed hand
3. fist
4. pointing hand
5. presenting hand
6. gripping hand
7. thumbs-up hand
8. reaching hand
9. two-hand build grip
10. prototype presentation grip
11. privacy-check shield grip
12. metric-card presentation grip
13. gray-blue prototype front/side
14. prototype top/bottom
15. privacy shield/check construction
16. cap/glasses/beard invariant construction reference

Construction callouts may be close, but must retain voxel scale and anatomically plausible five-finger hands.

### 07 — Grounded motion, 4 columns by 4 rows (`07-ground-motion-sheet-candidate-v1.png`)

1. walk contact left
2. walk passing left
3. walk contact right
4. walk passing right
5. run reach
6. run drive
7. start anticipation
8. stop recovery
9. planted-foot turn left
10. planted-foot turn right
11. crouch
12. jump anticipation
13. jump airborne
14. fall
15. land contact
16. land recovery

Turn panels must visibly keep one shoe planted on the shared baseline. All non-airborne panels share the same floor baseline. Keep the entire cap/brim, hands, and shoes inside every panel.

### 08 — Kai signature actions, 4 columns by 4 rows (`08-signature-actions-sheet-candidate-v1.png`)

1. smallest-pilot pitch
2. build gesture
3. test gesture
4. build-test handoff
5. privacy check
6. safety slowdown
7. metric presentation
8. evidence comparison
9. prototype present
10. prototype inspect
11. prototype celebration
12. decisive thumbs-up
13. mid-gesture self-correction
14. kill-the-hype reaction
15. settle and listen
16. energetic recovery

Use only the controlled prototype/shield/metric props described in the uncertainty log. No readable labels or brand marks.

### 09 — Core hand actions, 2 columns by 2 rows (`09-core-hand-actions-candidate-v1.png`)

1. open hand
2. closed hand
3. fist
4. full-body reach

All four are full-body neutral-front variants at identical scale and baseline, with the active hand clearly separated from the torso.

## Review gate

Before approval, inspect every panel for exact `BAKE` spelling when the cap front is visible, identity consistency, full-body framing, cap/brim and extremity clearance, five-finger hands, consistent body height/baseline, correct prop continuity, planted-foot turns, absence of bust frames in runtime sheets, and exact positional mapping. Rejected generations remain candidates and are not runtime assets.

## Generation provenance and accepted candidate hashes

The candidates were generated with the built-in GPT Image workflow using `canonical-voxel.png` as the identity-preserving reference. Each prompt repeated the immutable identity, exact grid geometry, full-body rule, fixed-scale/baseline rule, cap-text rule, studio treatment, margins, and sheet-specific row-major panel map. The files were then copied into this branch and visually inspected at original resolution. Raster geometry was normalized without cropping where needed so 4-by-4 and 2-by-2 sheets are exactly 1256 square. The accepted grids total exactly **124 cells**: 16 + 8 + 8 + 24 + 16 + 16 + 16 + 16 + 4.

| Candidate | SHA-256 | Visual review |
| --- | --- | --- |
| `01-identity-sheet-candidate-v1.png` | `a7e821575fb293218de7e973bbddb29fc1c9a06f31230060fe3c420b24c61d77` | Reject: useful callouts but not a deterministic 16-cell extraction grid |
| `01-identity-sheet-candidate-v2.png` | `b913294ff0084017da12bae9f034db0c0e2cc261dfc4ed9ff457b40988ee68d3` | Pass: 16 equal full-body identity/reference cells; exact `BAKE`; complete margins |
| `02-turnaround-sheet-candidate-v1.png` | `ee7fbdcb2e13c53bfc805f92d8e54faebe8e9d71e84863b49a86ba34b573a9d9` | Pass: eight complete ordered views, stable scale/baseline, front-only text behavior |
| `03-neutral-base-poses-candidate-v1.png` | `1ef772827b69b499893dfdf2e6c51480aef8333cfaf6b8da22b684f9422653d4` | Pass: eight full-body neutral/idle anchors with clear speaking/listening distinction |
| `04-expression-sheet-candidate-v1.png` | `6e61adf3c8afd5db02e8f3525c31cfa18680cfd1d4e01558d73706f17002bc44` | Pass: 24 full-body panels; no bust frames; emotion uses face and posture |
| `05-speech-viseme-sheet-candidate-v1.png` | `c4441ae6b33fd0d70827ed31bf53ee8ccd44d137b391a3fb7362a38875605236` | Pass: 13 mouth states plus three blink states, all full body at a stable camera |
| `06-hand-prop-sheet-candidate-v1.png` | `a96a17707ae31c0ac4c2de442a229edf4212599354f6e72e82e97fa996972331` | Pass: hand vocabulary, prototype, shield/check, card, and invariant head construction |
| `07-ground-motion-sheet-candidate-v1.png` | `c88ae94c2e14e92330df5ae237ebc81e9958a2ca5f83da06714d386867b8f9d4` | Pass: 16 complete motion keys; planted-foot turns and grounded/airborne separation visible |
| `08-signature-actions-sheet-candidate-v1.png` | `087ecab02fd57b885489a6c4c1a66d5198e8c43c058860032afcc7758955b889` | Pass: build/test/privacy/metric/prototype/hype/settle vocabulary, complete silhouettes |
| `09-core-hand-actions-candidate-v1.png` | `cd8d5bb08ef20121964a9f24ab0d75905c795d060fe7261d1a97d009ffc7164e` | Pass: open, closed, fist, and reach are full body with active hands separated from torso |

## Runtime handoff

These PNGs are canonical pose references and extraction sources, never runtime PNG or SVG render assets. The implementation loop must process exactly 124 accepted cells: remove each cell background, isolate each pose/reference silhouette, create one transparent pixel graph for each cell, and store colored pixel nodes/runs only. The visualizer projector paints those graph pixels onto canvas for each animation frame. All 124 isolated silhouettes and all 124 pixel graphs must be re-audited before animation is reconnected. Only afterward may implementation derive pose-local anchors, enforce the shared safety inset, build the package/manifest/animation graph/matrix/registry entry, and validate live playback.
