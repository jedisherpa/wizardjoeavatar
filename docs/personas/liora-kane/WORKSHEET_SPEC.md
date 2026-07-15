# Liora Kane Production Worksheet Specification

## Shared generation contract

Every sheet uses the canonical voxel reference as an identity image, not as loose inspiration. Render one consistent Liora in the exact declared grid and raster geometry with equal panel cells, pale blue gradient studio background, faint blue tiled floor, soft studio light, and no labels or text inside the image. Each panel must show the complete character from hair top through both shoes, including both hands and the entire notebook when present. Keep constant cube scale, apparent height, head size, camera distance, foot baseline, palette, material response, and generous safety margins. No panel may crop hair, elbows, hands, notebook, trouser cuffs, or shoes. No busts, portraits, floating heads, duplicate limbs, extra fingers, added costume pieces, or style changes.

Runtime extraction uses panel order left-to-right, top-to-bottom.

## Approved raster geometry

The accepted files use integer-divisible dimensions so extraction never rounds a panel edge:

| Sheet | Raster | Grid | Exact cell |
| --- | --- | --- | --- |
| 01 identity | 1256 x 1256 | 4 x 4 | 314 x 314 |
| 02 turnaround | 1536 x 1024 | 4 x 2 | 384 x 512 |
| 03 neutral bases | 1776 x 888 | 4 x 2 | 444 x 444 |
| 04 expressions | 1536 x 1024 | 6 x 4 | 256 x 256 |
| 05 visemes and blinks | 1256 x 1256 | 4 x 4 | 314 x 314 |
| 06 hands and notebook | 1256 x 1256 | 4 x 4 | 314 x 314 |
| 07 grounded motion | 1256 x 1256 | 4 x 4 | 314 x 314 |
| 08 signature actions | 1256 x 1256 | 4 x 4 | 314 x 314 |
| 09 required body-hand poses | 1256 x 1256 | 2 x 2 | 628 x 628 |

The sub-0.2-percent raster normalization used on generated odd-sized sheets changes only the outer raster geometry. It does not reorder, crop, repaint, or synthesize panels.

## 01 — Identity sheet (4 by 4)

File: `01-identity-sheet-candidate-v1.png`

1. neutral front full body with notebook
2. canonical front three-quarter full body
3. left profile full body
4. back full body
5. face construction shown on full body neutral front
6. hair construction shown on full body back three-quarter
7. hoodie construction, arms relaxed
8. plaid trouser and shoe construction
9. notebook front-cover hold
10. notebook open two-hand hold
11. relaxed open left hand, full body
12. relaxed open right hand, full body
13. proportion guide neutral front
14. immutable palette/material reference pose
15. attentive support stance
16. gentle default closed-eye smile

## 02 — Eight-view turnaround (4 by 2)

File: `02-turnaround-sheet-candidate-v1.png`

1. front
2. front three-quarter left
3. left profile
4. back three-quarter left
5. back
6. back three-quarter right
7. right profile
8. front three-quarter right

All eight views use neutral posture, notebook held vertically at the torso, matching height, stable baseline, and view-correct hair/notebook occlusion.

## 03 — Neutral bases (4 by 2)

File: `03-neutral-base-poses-candidate-v1.png`

1. neutral front
2. neutral three-quarter
3. neutral side
4. neutral back
5. relaxed idle
6. attentive idle
7. speaking idle
8. listening idle

## 04 — Full-body expressions (6 by 4)

File: `04-expression-sheet-candidate-v1.png`

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
23. gentle reassurance recovery
24. neutral reset

Facial and body expression may change, but every panel retains the same full-body scale, anatomy, costume, notebook, and voxel identity.

## 05 — Full-body visemes and blinks (4 by 4)

File: `05-speech-viseme-sheet-candidate-v1.png`

1. rest mouth
2. closed lips
3. slightly open
4. wide vowel
5. open vowel
6. rounded vowel
7. teeth consonant
8. lower-lip consonant
9. tongue consonant
10. smile while speaking
11. frown while speaking
12. speech emphasis
13. breath or pause
14. eyes open
15. eyes half closed
16. eyes closed

## 06 — Hand and notebook construction (4 by 4)

File: `06-hand-prop-sheet-candidate-v1.png`

1. open relaxed hand
2. closed relaxed hand
3. fist
4. pointing hand
5. presenting hand
6. notebook gripping hand
7. reaching hand
8. writing/pen grip
9. notebook held to chest
10. notebook open in both hands
11. notebook page turn
12. notebook writing
13. privacy hold with cover inward
14. safe handoff of notebook
15. two-hand grounding clasp
16. neutral recovery

Every panel remains full body; hand/prop construction is communicated through readable pose silhouette, not cropped detail insets.

## 07 — Grounded motion with planted-foot turns (4 by 4)

File: `07-ground-motion-sheet-candidate-v1.png`

1. walk contact left
2. walk passing left
3. walk contact right
4. walk passing right
5. run reach
6. run drive
7. start anticipation
8. stop settle
9. planted-left turn left
10. planted-right turn right
11. crouch
12. jump anticipation
13. jump airborne
14. fall
15. land contact
16. land recovery

Turns must visibly keep the named foot planted. Notebook stays secure and hair follows motion without changing length or volume.

## 08 — Persona signature actions (4 by 4)

File: `08-signature-actions-sheet-candidate-v1.png`

1. compassionate listening start
2. compassionate listening nod
3. family-communication planning open notebook
4. family-communication planning point to page
5. belonging check-in open hand
6. belonging check-in attentive pause
7. privacy boundary notebook shield low
8. privacy boundary calm stop palm
9. safe escalation assess
10. safe escalation indicate next step
11. notebook-guided support write
12. notebook-guided support present plan
13. supportive hand offer
14. protective grounded stance
15. quiet reassurance
16. slow neutral recovery

## 09 — Required body-hand poses (2 by 2)

File: `09-body-hand-poses-candidate-v1.png`

1. full-body open-hand neutral
2. full-body closed-hand neutral
3. full-body fist neutral
4. full-body forward reach

The four panels use identical front three-quarter camera, character scale, root, baseline, notebook placement, and neutral face so only the requested arm/hand articulation changes.

## Review gate

Reject a sheet if any panel changes Liora's apparent age, face, hair part/length, hoodie construction, trouser plaid, shoe design, notebook scale/color, cube size, lighting logic, camera distance, or body proportions; crops an extremity or prop; omits a required panel; uses a bust; invents text; or produces malformed anatomy. Approved outputs remain pose references only. Runtime assets must be deterministic direct-cell data and must not load these PNGs.
