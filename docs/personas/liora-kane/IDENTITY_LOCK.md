# Liora Kane Identity Lock

## Visual authority

`assets/reference/personas/liora-kane/canonical-voxel.png` is the highest production authority. `source-reference.png` informs the original human character and emotional tone, but production sheets must preserve the canonical voxel reconstruction rather than reverting to anime rendering.

## Immutable identity features

- Adult woman with a tall, slim, softly rounded build and an approximately five-and-a-half-head stylized proportion.
- Large rounded-rectangle voxel head; warm peach skin; broad smooth forehead; small voxel nose; soft jaw and chin.
- Long, thick, wavy brown hair with a loose near-center part, face-framing locks, and multiple curled lengths falling past the waist. Hair remains brown and voluminous in every view.
- Thick dark-brown brows, dark lashes, and warm dark-brown eyes. Her default expression is a gentle closed-eye smile with subtle warm cheeks.
- Light-gray pullover hoodie with a substantial hood, two cream-white drawstrings, ribbed cuffs and hem, and one front kangaroo pocket. No logos, crop, zipper, jewelry, or exposed midriff.
- Loose full-length plaid trousers in deep teal, muted blue-green, and cream. The plaid grid, wide legs, and rolled/cuffed ankles remain visible.
- Cream/off-white low voxel sneakers with pale beige sole and toe detail.
- Dark navy-blue support notebook with cream page block. The notebook has no title, emblem, or invented decoration.
- Refined high-detail 3D voxel construction: small uniform cubes, softly beveled cube edges, soft studio key light, gentle contact shadow, blue gradient studio backdrop, and faint blue tiled floor.
- No glasses, hat, wings, tail, weapon, jewelry, extra bags, or additional costume layer.

## Articulating and deformable features

- Brows, eyelids, pupils, cheeks, mouth, jaw, and head angle may change for expression and speech without changing skull construction.
- Hair locks may lag, compress, or sway slightly with motion while retaining length, part, volume, and curl pattern.
- Hood, drawstrings, sleeves, cuffs, pocket, trouser folds, cuffs, and shoe angles may respond to movement while retaining construction and color.
- Shoulders, spine, elbows, wrists, fingers, hips, knees, and ankles may articulate. Hands always retain two readable voxel hands with consistent finger construction.
- Notebook may move between relaxed hold, two-hand hold, writing, presenting, and protective privacy hold. Its scale, navy cover, cream pages, and rectangular construction are fixed.

## Stable proportions and alignment

- Use one orthographic-like three-quarter studio camera with minimal perspective distortion except where a profile/back view is explicitly required.
- Every full-body panel uses the same apparent height, head size, cube scale, and foot baseline.
- Preserve generous clear space on all four sides. Hair tips, elbows, notebook, hands, trouser cuffs, and shoes must never touch a panel edge.
- Grounded poses keep at least one clearly planted foot and an explicit stable root between the feet. Turning poses keep a planted pivot foot.
- No busts or close-up runtime frames: expression, speech, blink, hand, and signature-action panels must still show the complete character from hair top through both shoes.

## Performance lock

Liora is steady, protective, patient, and quietly warm. Her movement uses open shoulders, small-to-medium gesture amplitude, careful notebook handling, attentive eye contact, measured nods, and slow recoveries. Safety, privacy, escalation, and family-communication actions must remain calm and grounded rather than bubbly or theatrical.

## Worksheet acceptance invariants

- A turnaround is valid only when cells 1-8 are eight distinct views in the specified angular sequence. The two back-three-quarter views must reveal different side depth and must not duplicate the exact-back cell.
- Speech cells 1-13 keep open eyes so speech and blink channels remain separable. Blink cells 14-16 share one neutral rest mouth and progress visibly from open to half-closed to fully closed.
- Full-body expression and speech panels retain the notebook and footwear even when the face is the primary changing feature.
- The two planted-foot turn cells show floor contact at the named pivot foot and change torso/head direction without teleporting the root.
- Every approved raster must divide exactly by its declared grid columns and rows.
