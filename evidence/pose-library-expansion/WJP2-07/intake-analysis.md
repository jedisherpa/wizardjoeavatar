# WJP2-07 Intake Analysis

- Source: `../intake/poses2/ChatGPT Image Jul 12, 2026, 08_03_22 PM (7).png`
- SHA-256: `30eaa4a8b9e33c4c05a1aab863d4ce8601ecd112c8b34d138bace1b083707f78`
- Source preview: `source-preview.png`

## Classification

Front-family two-handed staff guard pose with staff crossing the torso down toward screen right, open mouth, and stable wide stance. Reads as a defensive hold or staff-ready transition.

Proposed semantic ID: `front_staff_guard_low`

## Current-pose comparison

- Related to `magic_cast`, but not a material duplicate: the staff is horizontal/low across the body rather than raised with spark effects.
- Related to WJP2-06, but distinct enough as a lower guard/hold phase.
- Not a duplicate of `explaining` or walk poses because both hands grip the staff and the body is held.

## Consistency and transition notes

- Major risk: source includes legacy rainbow wings.
- Good transition neighbor for `front_idle`, `front_staff_guard_windup`, and `magic_cast`.
- The staff crosses in front of face/chest, so transition compositing should watch for double-staff artifacts and facial occlusion.

## Anchor notes

Defaults are clearly wrong for both hands and staff tip. Integration should define explicit staff-hand and staff-tip anchors. Eye and mouth defaults are close; feet are wider than default and should be explicit if integrated.
