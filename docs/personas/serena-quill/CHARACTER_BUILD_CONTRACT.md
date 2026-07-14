# WizardJoeAvatar Persona Character Build Contract

This branch is a character-preparation branch. The supplied source image is immutable reference material; `canonical-voxel.png` is the approved visual direction. Runtime animation must use WizardJoeAvatar's native direct-cell character architecture rather than displaying PNG sprites.

## Required production sequence

1. Preserve `source-reference.png` byte-for-byte. Record its SHA-256 hash and never crop, repaint, or overwrite it.
2. Write an identity lock before generating poses. Separate immutable anatomy, face, hair/headwear, costume, colors, props, and asymmetries from features allowed to articulate.
3. Create an uncertainty log for details hidden by the source. Use the least disruptive inference and do not invent new costume pieces or anatomy without recording why.
4. Produce, in order: identity sheet, eight-view turnaround, neutral base-pose sheet, expression sheet, mouth/viseme sheet, hand/prop sheet, ground-motion sheet, and any character-specific special-action sheet.
5. Use `canonical-voxel.png` and the identity sheet as hard visual references for every generation. Keep the same cube scale, face construction, body proportions, costume construction, palette, lighting logic, and camera distance.
6. Reject any candidate with identity drift, changed age, altered face structure, different costume seams, missing accessories, extra digits or limbs, cropped extremities, inconsistent cube scale, or a different rendering style.
7. Convert approved worksheet panels deterministically into direct square-cell assets. Target the character package's canonical canvas, retain at least a four-cell transparent safety inset on every side used by motion, and align every frame to a stable root/baseline.
8. Store generated cells in the character pose library JSON. Runtime code must not load, decode, or display the PNG references.
9. Add a character package, manifest, animation graph, animation matrix, and registry entry. Expose the character through the existing character-scoped REST and WebSocket routes and through the browser character selector.
10. Map the complete supported vocabulary: neutral/idle, eight facings, walk, run, turn, crouch, jump, fall, land, speak, listen, conversational gestures, all supported expressions, character prop actions, and special movement where applicable.
11. For every animation define anticipation, primary action, follow-through, recovery, contact points, pivots, timing, entry state, and exit state. Test at runtime speed and slow motion; correct sliding, popping, scale changes, baseline drift, and clipped silhouettes.
12. Implement personality through timing, posture, gesture amplitude, gaze, pauses, and recovery—not by redesigning anatomy between frames.

## Acceptance gate

- Original hash and derivation chain documented.
- Canonical sheets and human-readable contact sheets present.
- Every pose stays inside canvas safety bounds.
- Identity, palette, materials, costume, prop scale, and voxel size remain stable.
- Character manifest and registry validate.
- Missing-pose and fallback behavior validate.
- Focused character tests, full Python suite, production-scope validation, animation-quality verification, and browser playback all pass.
- Runtime evidence includes idle, locomotion, expression, speaking, signature action, and widest-silhouette screenshots with zero browser errors or dropped frames.

The character is complete only when the live visualizer can use the full movement, expression, speech, gesture, interaction, and state vocabulary without visible identity drift.
