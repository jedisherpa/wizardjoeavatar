# WJP2-04 Intake Analysis

- Source: `../intake/poses2/ChatGPT Image Jul 12, 2026, 08_03_22 PM (4).png`
- SHA-256: `36c85a0d9214145fe4fb2ffb351b3e96dcd617e917b6e35d0baece0ef7e23970`
- Source preview: `source-preview.png`

## Classification

Front-family airborne celebration/reaction pose with the free fist thrust toward camera, staff held upright in the opposite hand, open mouth, and both feet off the ground.

Proposed semantic ID: `front_reaction_jump_fist_staff`

## Current-pose comparison

- Not a material duplicate of `explaining`: hand is closed/fist-forward rather than open explanatory palm.
- Not a material duplicate of `magic_cast`: staff is held, not raised/casting, and there are no magic sparks.
- Not a material duplicate of `walk_front_left` or `walk_front_right`: both feet are airborne and the pose reads as a jump/reaction rather than a walk-cycle phase.

## Consistency and transition notes

- Major risk: source includes legacy rainbow wings.
- Major risk: airborne pose has no grounded baseline. Default foot/root assumptions would collapse the jump into a grounded stance unless a transition system intentionally handles jump height.
- Best transition neighbors: `front_idle`, `walk_front_left`, `walk_front_right`, `magic_cast` exit reaction.

## Anchor notes

Defaults are mostly wrong for hands and feet because the pose is airborne and the free fist is extreme foreground. Root should remain the canonical canvas root, but any integration needs explicit foot/hand/staff anchors and a separate vertical-motion transition plan.
