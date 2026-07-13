# CrystAIl Worksheet Generation Record

Mode: built-in image generation, identity-preserving reference generation.

The original reference, accepted identity sheet, and accepted neutral-pose sheet were supplied together as visual authorities. Outputs were copied into `assets/reference/crystail/canonical-worksheets/`; the built-in originals remain preserved in the Codex generated-images directory.

## Ground motion sheet

File: `06-ground-motion-sheet-v1.png`.

Prompt scope: a 4 by 3 high-detail 3D voxel worksheet containing walk contact/passing pairs, run reach/drive, left/right turns, crouch anticipation, jump airborne, fall, and landing compression. It locked the emerald body, modeled squared muzzle, tan rectangular eyes, stepped horns, four upper teeth, cream segmented throat/belly, rainbow wings with blue tips, stepped tail, two toes, three hand digits, no prop, no costume, stable camera/scale, graceful arcs, counter-sway, and soft recovery.

## Flight motion sheet

File: `07-flight-motion-sheet-v1.png`.

Prompt scope: a 4 by 3 high-detail 3D voxel worksheet containing takeoff anticipation/launch, hover up/down, glide, power flap, left/right bank, ascend, descend, landing approach, and touchdown recovery. It repeated the complete identity lock and required wing arcs, body counter-rotation, pointed-toe finish, stable camera/scale, and no anatomy or palette drift.

The generated PNGs are not runtime sprites. The deterministic generator segments their panels into the same direct-cell JSON architecture used by Wizard Joe.
