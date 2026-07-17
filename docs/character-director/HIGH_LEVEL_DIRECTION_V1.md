# High-Level Direction V1

Date: 2026-07-17

## Purpose

`HighLevelDirectionRequestV1` is a deterministic, governed, controlled-language
entry point for Character Director. It converts supported stage and acting
direction into the existing portable score, character-bound compiler,
`CompiledScoreLoader`, `PerformanceScheduler`, `PerformanceApplication`,
controller, and pixel-graph renderer path. It does not add another renderer,
runtime, connector, or live model call.

## Boundary

The request is a closed Draft 2020-12 JSON contract in
`wizard_avatar/definitions/high_level_direction_request_v1.schema.json`. It
binds:

- a stable direction ID and controlled direction text;
- the exact `PerformanceContextV1` hash that grants authority;
- one governed semantic intent;
- duration, immutable media identity/hash, and deterministic seed.

Compilation fails closed when the context is stale, the intent is denied or
not allowed, presentation is unapproved, the text contains a private-token
shape, a material action conflicts with the governed intent, or any clause is
unsupported. Errors use stable content-free codes and do not echo the request.

## Supported Controlled Language

V1 recognizes ordered comma/semicolon/`then` clauses for:

- enter, walk, or move from stage-left/right/rear toward center;
- an explicit one-to-five-second walk duration;
- delighted surprise on entrance;
- circle toward center, with an explicit recorded linear-trajectory fallback;
- stop or plant the feet;
- turn toward the viewer;
- transition to warm seriousness;
- raise the right hand, hold one second, or lean closer;
- speak, explain, or tell the user something important;
- celebrate, when the governed root intent is also `celebrate`.

The two acceptance examples are executable regression fixtures. Unrestricted
natural language, arbitrary choreography, and implicit substitutions are not
supported in V1.

## Compilation

`wizard_avatar.direction_compiler.compile_high_level_direction` performs:

1. strict request and exact context-hash validation;
2. governance and presentation checks;
3. controlled clause parsing into immutable semantic plan steps;
4. deterministic fixed-point scheduling over the requested duration;
5. portable `PerformanceScoreV1` generation in `directed` mode;
6. context rebinding to the generated score and media identity;
7. character-bound compilation against the capability manifest.

Portable cues contain semantic requirements such as
`locomotion.stage_walk`, `body.viewer_turn`, `face.focused`, and
`body.explain`. They never contain `clip:*`, pose IDs, or expression renderer
IDs. Only `compile_character_bound_performance` selects an admitted runtime
capability. Stage coordinates are derived from the context display bounds and
stored as integer milli-unit trajectories, so planning is deterministic across
supported viewports.

The compiled score retains media identity, duration, trajectory, facing,
expression, gaze, mouth, speaking, and phrase-origin execution fields. The
same execution object is accepted by `ScoreEditsV1`, preserving editability.
Reduced-motion compilation removes stage travel and position ownership while
retaining supported face/speech acting.

## Explicit Fallbacks

V1 records the requested and selected shape plus a stable reason code. The
only planner-level fallback currently admitted is:

| Requested | Selected | Reason |
| --- | --- | --- |
| Circular path toward center | Smooth linear stage trajectory | `circle_to_linear_stage_fallback` |

Character capability fallback remains the responsibility of the existing
character-bound compiler and is recorded in the compiled score. Unsupported
language is rejected with `direction_unsupported`; it is never silently
converted to neutral behavior.

## Verification

`tests/wizard/test_high_level_direction.py` proves:

- byte-identical repeated compilation and stable plan hashes;
- both high- and mid-level acceptance examples;
- portable semantic-only cues and character-bound runtime selection;
- media identity through `CompiledScoreLoader`;
- stage ownership and movement through `PerformanceScheduler`;
- real world-position change through `PerformanceApplication` and
  `WizardAvatarController`;
- reduced-motion projection;
- unsupported language, denied intent, intent mismatch, stale context, unknown
  fields, bounds, and private-token rejection.

`tests/wizard/test_contract_schemas.py` additionally verifies that directed
execution data survives the strict score-edit contract.

## Known Limits

This is intentionally a closed controlled-language compiler, not a general
natural-language choreographer. New phrases require a parser rule, semantic
capability requirement, governance analysis, deterministic fallback or
rejection policy, and regression test before admission. Long-duration,
connected audiovisual, and professional acting review remain separate
acceptance gates.
