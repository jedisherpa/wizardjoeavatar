# WJP2-05 Intake Analysis

- Source: `../intake/poses2/ChatGPT Image Jul 12, 2026, 08_03_22 PM (5).png`
- SHA-256: `c8e837e3eb7b701d7df799ad5f3c14be20a2da25caa000077997d7ac659da319`
- Source preview: `source-preview.png`

## Classification

Front-family kneel/crouch pose with one knee down, staff planted upright, lowered free hand, and open mouth. Reads as a recovery, kneel, brace, or dramatic reaction hold.

Proposed semantic ID: `front_kneel_staff_brace`

## Current-pose comparison

- Not a material duplicate of `front_idle`: body height and leg silhouette are substantially different.
- Not a material duplicate of `explaining`: free hand is lowered and the pose reads as kneeling/brace rather than open-hand speech.
- Not a material duplicate of `magic_cast`: staff is planted, not raised, and there are no spark effects.
- Not a walk-cycle duplicate; it is a held low posture.

## Consistency and transition notes

- Major risk: source includes legacy rainbow wings.
- The kneeling leg changes baseline behavior and may need careful entry/exit transitions to avoid a severe body-height snap.
- Best transition neighbors: `front_idle`, `explaining`, `magic_cast`, and possible future `front_reaction_jump_fist_staff` landing/recovery.

## Anchor notes

Default mouth/eye anchors are likely acceptable after canonical crop. Hand, foot, and staff anchors should be explicit because the staff is planted far to screen right and the free hand is low. Foot anchors should use visible boot contact points, not the default symmetrical stance.
