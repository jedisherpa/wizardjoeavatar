# WJP2-06 Intake Analysis

- Source: `../intake/poses2/ChatGPT Image Jul 12, 2026, 08_03_22 PM (6).png`
- SHA-256: `b9e762a5c7ec49389f377536aea62dec7aa620c67b0a646695719de22f6eece5`
- Source preview: `source-preview.png`

## Classification

Front-right/facing-south family two-handed staff windup/guard pose. Staff is held diagonally across the body with both hands, mouth open, wide stance, no visible sparks.

Proposed semantic ID: `front_staff_guard_windup`

## Current-pose comparison

- Related to `magic_cast`, but not a material duplicate: this is a two-handed diagonal staff windup/guard without raised-staff spark effects.
- Not a duplicate of `explaining`: both hands are committed to staff control.
- Not a duplicate of walk poses: stance is wide but upper body action dominates.

## Consistency and transition notes

- Major risk: source includes legacy rainbow wings.
- Strong transition neighbor for entering `magic_cast`; can also return to `front_idle`.
- Possible overlap with WJP2-07 as a staff-guard family phase, but WJP2-06 keeps the staff higher and more outward, reading as windup.

## Anchor notes

Defaults are clearly wrong for both hands and staff tip. Integration should define `left_hand`, `right_hand`, `staff_hand`, and `staff_tip` explicitly along the diagonal staff. Eye and mouth defaults are likely close.
