# Character Parity Rollout

Updated: 2026-07-27

## Rule

Characters enter the existing Python Character Director one at a time. A
character is not listed in the production registry until its package, graph,
capabilities, runtime, connector, tests, evidence, independent reviews, and
product approval all refer to the same frozen candidate.

No character may introduce a parallel server, renderer, connector, control
clock, or governance path.

## Production Baseline

| Character | State | Authority |
| --- | --- | --- |
| Wizard Joe | Production baseline | Existing V1 compatibility package |

The registry is fail-closed and currently contains Wizard Joe only. Its entry
binds the exact package SHA-256. CharacterPackageV2 additionally binds every
declared asset by role and SHA-256 and declares a renderer adapter and supported
runtime API range.

## Planned Roster

| Order | Character | Frozen source commit | State |
| ---: | --- | --- | --- |
| 1 | Serena Quill | `196c2389` | Package-driven facing, action, blink, and speech poses passed; locomotion and performance parity pending; not registered |
| 2 | Aurelia Finch | `5514fe9b` | Source discovered |
| 3 | Selene Hart | `e64f868f` | Source discovered |
| 4 | Thorne Vale | `582fb82d` | Source discovered |
| 5 | Elara Voss | `a1df4aee` | Source discovered |
| 6 | Kai Renner | `7e9bda4c` | Source discovered |
| 7 | Mira Solen | `1c467fa6` | Source discovered |
| 8 | Draven Holt | `d81cabb5` | Source discovered |
| 9 | Liora Kane | `92fabac2` | Source discovered |
| 10 | Rohan Slate | `375a3f9a` | Source discovered |
| 11 | Finn Calder | `40b9a346` | Source discovered |
| 12 | Orion Vale | `50eab748` | Source discovered |
| 13 | Robin | Source manifest `2c33d3e0` | Corrected 200-pose review library published locally; runtime blocked |
| 14 | Speech | Source manifest `2c33d3e0` | Corrected 200-pose review library built; runtime blocked |
| 15 | Dragon | Source manifest `024a5643` | 84 of 91 assets valid; seven damaged replacements required; review and runtime blocked |
| 16 | Kingfisher | To be frozen during intake | Not started |
| 17 | Liana | Supplemental authored intake | Identity candidate; not registered |

Crystail and Falcor remain separate library discoveries. They do not silently
expand or replace the explicit parity roster above.

Liana is additive supplemental work derived from Liora's identity proportions.
She does not expand the fixed 12 x 48 authority matrix, and she does not alter
Liora's assets or pose IDs. Her separate 48-pose approval program is defined in
`reports/LIANA_ANIMATION_DIRECTION_2026-07-25.md`.

Robin and Speech now use the corrected 200-frame shared-canvas source. A
deterministic component/geodesic partition preserves each identity while
requiring exact source reconstruction and zero overlap. Both compiled libraries
remain review-only and fail closed at production admission. See
`ROBIN_SPEECH_ALPHA_INTEGRATION_2026-07-27.md`.

Dragon has a frozen 91-entry source inventory, but seven supplied PNG streams
are truncated. The 84 valid files are preserved byte-for-byte; failed payloads
are manifest records only and cannot enter review or runtime. See
`DRAGON_ALPHA_SOURCE_AUDIT_2026-07-27.md`.

## Per-Character Gates

1. **Intake:** source commit, source hashes, license/provenance, asset census,
   identity lock, uncertainty log.
2. **Package:** CharacterPackageV2, package-local assets, exact hashes, runtime
   API range, renderer adapter, fail-closed registry candidate.
3. **Catalog:** transparent pixel graphs, truthful anchors, runtime versus
   diagnostic admission, no fabricated props.
4. **Animation:** complete graph V2, legal transitions, contacts, markers,
   interruption, fallback, accessibility, deterministic replay.
5. **Performance:** package-scoped vocabulary and mappings, semantic score
   compatibility, expressions, gaze, speech, and body-language behavior.
6. **Governance:** character and package digest admission, permission-world
   boundaries, no unapproved output, no authority claims from presentation.
7. **Runtime:** real hub boot, bounded streaming, command sequencing, shared
   clock, pause, seek, rate, reconnect, and runtime epoch behavior.
8. **Presentation:** desktop and mobile framing, no crop or overlap, integer
   physical pixels, responsive controls, clean start identity.
9. **Verification:** focused tests, full regression, browser recording,
   independent animation review, independent technical review.
10. **Acceptance:** exact frozen candidate, explicit product approval, registry
    hash update, commit, push, deployment proof, and rollback instructions.

## Parity Matrix

Every candidate must prove:

- package and asset tamper rejection;
- real graph load against its own manifest and pose library;
- real hub and server boot;
- idle, walk, turn, stop, expression, gaze, and speech behavior where declared;
- truthful denial or fallback for undeclared capabilities;
- portable semantic score admission;
- character ID and package digest mismatch rejection;
- deterministic frame identity and replay;
- planted-contact stability;
- interruption and accessibility profiles;
- REST and WebSocket stream behavior;
- existing Prism connector behavior without a duplicate integration;
- desktop and mobile visual acceptance;
- clean installation and rollback.

## Accountability

Each character receives:

- an intake audit;
- an implementation checklist;
- a machine-readable evidence manifest;
- an animation review;
- a technical review;
- an acceptance document containing the exact commit and artifact hashes.

The tracker must distinguish `discovered`, `intake-audited`,
`implementation-ready`, `candidate`, `technically-passed`,
`product-approved`, and `production-registered`. No weaker state is reported
as parity.
