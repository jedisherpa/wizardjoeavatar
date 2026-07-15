# Elara Voss Canonical Worksheet Production Specification

## Shared visual contract

Every sheet uses `canonical-voxel.png` as the voxel identity authority. Elara remains one identical adult feminine lime-green alien: large rectangular cuboid head, enormous black stepped eyes with outward lash blocks, two square nostrils, small mouth, burnt-orange jacket and knee-length skirt, cream blouse, slim green limbs, and orange heels. Use a fixed small-cube scale, pale cool-blue studio, faint tiled floor, soft cool lighting, stable camera distance, and restrained contact shadow. Runtime-oriented panels show the complete body with generous clearance. Positional mappings below are authoritative; sheets contain no rendered labels.

## Exact panel map

### 01 — Identity and references, 4 columns by 4 rows (`01-identity-sheet-candidate-v3.png`)

1. neutral front, no microphone
2. canonical front three-quarter holding microphone
3. strict left profile
4. exact back
5. neutral front face invariant
6. back three-quarter rear-head invariant
7. neutral front wardrobe invariant
8. neutral side heel invariant
9. microphone vertical at torso
10. microphone offered safely
11. open left hand separated from torso
12. open right hand separated from torso
13. proportion-neutral front
14. palette/material full-body reference
15. attentive academic support with microphone lowered
16. warm calm smile with hands settled

Every identity cell is a complete, independently extractable full-body silhouette. Candidate v1 is rejected because it used a nonuniform callout layout rather than 16 deterministic cells. Candidate v2 is rejected because cell 5 cropped the shoes. Candidate v3 is authoritative and maintains complete silhouettes with generous margins.

### 02 — Eight-view turnaround, 4 columns by 2 rows (`02-turnaround-sheet-candidate-v1.png`)

1. front
2. front three-quarter left
3. left profile
4. back three-quarter left
5. back
6. back three-quarter right
7. right profile
8. front three-quarter right

All views share standing height, head size, baseline, camera distance, and neutral arms. Face geometry remains on the front plane rather than wrapping around the side or back.

### 03 — Neutral bases, 4 columns by 2 rows (`03-neutral-base-poses-candidate-v1.png`)

1. neutral front
2. neutral three-quarter
3. neutral side
4. neutral back
5. relaxed idle
6. attentive idle
7. speaking idle with microphone and measured presenting hand
8. listening idle with microphone lowered and closed mouth

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
23. protective seriousness
24. settled recovery

Every expression is full body. Emotion uses eyelid aperture, mouth, head angle, shoulders, spine, hands, stance, and center of gravity without changing the skull or eye design.

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
13. breath or pause
14. eyes open
15. half blink
16. full blink

All panels use the same full-body speaking-idle pose, microphone placement, scale, camera, and baseline; only mouth, eyes, and minimal facial emphasis change.

### 06 — Hand and prop construction, 4 columns by 4 rows (`06-hand-prop-sheet-candidate-v1.png`)

1. open relaxed hand
2. closed relaxed hand
3. fist
4. pointing hand
5. presenting hand
6. reaching hand
7. microphone grip front
8. microphone grip three-quarter
9. lowered microphone grip
10. offered microphone
11. received microphone
12. handoff or transfer
13. two-hand microphone hold
14. emphasis beside microphone
15. microphone release
16. settled microphone hold

Close construction views are permitted on this sheet, but anatomy, voxel scale, microphone geometry, and wardrobe remain canonical.

### 07 — Grounded motion, accepted 4 columns by 4 rows (`07-ground-motion-sheet-candidate-v2.png`)

1. walk contact left
2. walk passing left
3. walk contact right
4. walk passing right
5. run reach
6. run drive
7. start anticipation
8. stop recovery
9. planted-left-foot turn left
10. planted-right-foot turn right
11. crouch
12. jump anticipation
13. jump airborne
14. fall
15. land contact
16. land recovery

Candidate v1 is rejected because panels 9 and 10 read as similar hands-on-hips stances rather than distinct opposite planted turns. Candidate v2 visibly plants opposite shoes, strongly counter-rotates torso and arms, and separates grounded from airborne phases.

### 08 — Elara signature actions, 4 columns by 4 rows (`08-signature-actions-sheet-candidate-v1.png`)

1. curriculum explanation
2. sequencing step one
3. inviting reflection
4. attentive microphone listening
5. rubric emphasis
6. microphone presentation
7. calm correction
8. protective seriousness
9. agreement
10. disagreement
11. question invitation
12. answer presentation
13. warm laugh
14. measured celebration
15. settle and listen
16. containment recovery

Only the canonical microphone is used. Gesture amplitude stays measured and deliberate.

### 09 — Core interaction poses, 2 columns by 2 rows (`09-interaction-poses-candidate-v1.png`)

1. open hand
2. closed hand
3. fist
4. full-body reach

All four are full-body variants at a stable scale and baseline with the active hand clear of the torso.

## Generation, normalization, and review record

The candidates were generated with the built-in GPT Image workflow using `canonical-voxel.png` as the identity reference. Prompts repeated the immutable identity, grid geometry, full-body rule, fixed scale and baseline, margins, studio treatment, and exact row-major maps. Raster dimensions were then normalized without cropping to exact grid-divisible dimensions: 1256-square for 4-by-4 and 2-by-2 sheets, 1776-by-888 for 4-by-2 sheets, 1536-by-1024 for the 6-by-4 sheet, and 1448-by-1088 for the signature 4-by-4 sheet. The accepted grids contain exactly **124 cells**: 16 + 8 + 8 + 24 + 16 + 16 + 16 + 16 + 4.

| Candidate | SHA-256 | Visual review |
| --- | --- | --- |
| `01-identity-sheet-candidate-v1.png` | `0a3cadd9466a031c9a671064f75d50f0d8142a1f97c0aed68a65424d20a799be` | Reject: useful callouts, but nonuniform layout cannot yield 16 deterministic cells |
| `01-identity-sheet-candidate-v2.png` | `f3362222f2344431ed5f36665a916946818abda17b0255ed37ceac4ba810242b` | Reject: correct 4-by-4 layout, but cell 5 crops both shoes |
| `01-identity-sheet-candidate-v3.png` | `5a685da06982b8cd492d6b6e8ad80970ddf04c49715fe43c4f7e8e88e10ae378` | Pass: 16 complete full-body identity/reference silhouettes with stable scale and margins |
| `02-turnaround-sheet-candidate-v1.png` | `6dee2c932ee77afab25ff1e90e697c3eb2b58766661ccc78546144e008e3f245` | Pass: eight ordered full-body views with front-plane face logic and stable silhouette |
| `03-neutral-base-poses-candidate-v1.png` | `eb34359a91751abefff0327ee952053cfffb866a53b8f11ab6cfa15fe46ebcbc` | Pass: eight full-body neutral and conversational anchors |
| `04-expression-sheet-candidate-v1.png` | `a862b20435cee6fe09f98e4cfd9784be784c841f58971a83cddaa0268d1a8339` | Pass: 24 full-body states; identity and wardrobe stable |
| `05-speech-viseme-sheet-candidate-v1.png` | `a36158b9d60738b9848672a4915616323313d14d370ca493a29f1801c65ce0f3` | Pass: 13 speech mouths and three eye states at a stable full-body camera |
| `06-hand-prop-sheet-candidate-v1.png` | `8b84124b78186d69e8149e99b42fc0e5476f6b964d7bb14794446c0a01c2e25c` | Pass: required hand vocabulary and microphone continuity |
| `07-ground-motion-sheet-candidate-v1.png` | `35ac3c2ddb838ac221ea5ecb6f1ee07a6aceae526602b7420f35574a6281651b` | Reject: opposite planted turns were not visually distinct |
| `07-ground-motion-sheet-candidate-v2.png` | `a905810a245b92699d1498372e3bacbbce9f1fd3f451e25a91cbfe598f7625d2` | Pass: complete motion keys, distinct planted turns, clear airborne/contact phases, full margins |
| `08-signature-actions-sheet-candidate-v1.png` | `c46761d4c1d7114a6565cb58cdd08c532149a6bbe2061ba9617153b3739a9bb7` | Pass: curriculum, sequencing, reflection, rubric, microphone, correction, and settle vocabulary |
| `09-interaction-poses-candidate-v1.png` | `da4c0105396daeb718629fceee5f6735bc9ed38805fb98b2d31d23b1bd3b405f` | Pass: open, closed, fist, and reach are full body with clear hands |

## Runtime handoff

These PNGs are canonical pose references and deterministic extraction sources, not runtime render assets. Runtime implementation must select only the accepted versions and process exactly 124 cells. It must remove each cell background, isolate each silhouette, convert every isolated result into its own transparent pixel graph, and store colored pixel nodes/runs rather than PNG or SVG render assets. The visualizer projector must paint those graph pixels onto canvas for each frame. All 124 isolated silhouettes and all 124 pixel graphs must be re-audited before any animation is reconnected. Only then may implementation compute pose-local bounds and anchors, preserve a four-cell safety inset, build Elara's package/manifest/graph/matrix/profile, register it through the generic character architecture, and verify live idle, locomotion, speaking, expression, interaction, signature action, widest silhouette, fallbacks, and transitions before promotion.
