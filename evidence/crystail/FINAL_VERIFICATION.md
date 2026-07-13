# CrystAIl Worksheet-Parity Verification

Date: 2026-07-13

## Recording diagnosis

The supplied 26.21-second, 2986 by 2012, 60 fps screen recording showed the first procedural pass as a flat, low-detail construction: rectangular head and torso, disconnected neck before correction, minimal limb volume, compressed wings, and no worksheet cube-face shading. It did not meet the Wizard Joe visual-quality bar.

## Replacement

- Removed the simplified procedural character from the production render path.
- Preserved the original reference unchanged at SHA-256 `ca4a5d93e89191d271768f2be0c298cbe68226858a47bf755863f1ed9362b585`.
- Added the five canonical review worksheets plus two identity-locked GPT Image ground/flight worksheets.
- Deterministically converted worksheet panels into 63 direct-cell poses on the canonical 72 by 96 local stage.
- Retained per-cell voxel lighting and color rather than reducing the character to a small fixed palette.
- Added 8 turnaround views, 4-step walk, run, turn, crouch/jump/fall/land, takeoff/hover/glide/banks/touchdown, conversational gestures, containment, and 22 named expression poses.
- Made containment stop active speech and transition to the contained listening pose.
- Kept all runtime art in ASCILINE cell JSON; no PNG, sprite sheet, or video is displayed by the renderer.

## Automated results

- Full Python suite: 160 tests passed in 148.508 seconds.
- CrystAIl generation determinism: passed.
- Animation transition matrix: 32 of 32 scenarios passed, zero issues.
- Python production scope: 49 scanned files, zero violations.
- Cartoon animation program validator: passed, 97 production paths checked, zero errors.
- Pose-expansion workflow: 30 candidates and 30 archives, zero errors.
- Diff whitespace check: passed.

## Live browser results

Candidate URL: `http://127.0.0.1:8766/?character=crystail-v1`

- Character selector: Wizard Joe and CrystAIl both present.
- Stream: 23.60 presented fps against a 24 fps target.
- Decode errors: 0.
- Page errors: 0.
- Console errors: 0.
- Dropped frames: 0.
- Resyncs: 0.
- Walk state selected authored worksheet frame `walk_contact_right`.
- Exact expression route selected `expression_excitement`.
- Speech used worksheet-quality speaking/expression poses.
- Containment cleared the active speech and selected `gesture_containment`.
- Flight selected authored takeoff/hover worksheet frames.

## Curated visual evidence

- `runtime-idle.png`
- `runtime-walk.png`
- `runtime-expression-excitement.png`
- `runtime-flight.png`

Production architecture: ASCILINE Python. Worksheet PNGs are generation inputs only; runtime frames are server-authored direct cells.
