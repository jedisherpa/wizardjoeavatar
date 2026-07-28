# Directed Performance Admission V1

Date: 2026-07-27

## Status

Implemented on `codex/character-director` as a bounded production API slice.
This release does not constitute full Character Director production acceptance.
It does not admit additional character packages or replace any visual approval
gate.

## Purpose

The runtime previously exposed the generic high-level direction compiler only
through tests and through the speech-specific `speaks` adapter. The new
transaction makes governed direction a real production operation while
preserving the existing architecture:

1. Prism owns approved-reply custody and connector authentication.
2. Python captures the current authority-bearing `PerformanceContextV1`.
3. Python compiles the controlled direction off the render loop.
4. Python revalidates media, runtime, package, reconciliation, and cancellation
   bindings.
5. Python publishes the immutable score through `CompiledScoreRepository`.
6. The connector advances `media_epoch` and attaches the returned score binding
   in a normal media-session snapshot.
7. The existing `ScoreRuntime`, `PerformanceScheduler`, and projector activate
   the score from the authoritative media clock.

There is no second scheduler, animation runtime, clock, remote-command path, or
connector.

## Python Endpoint

`POST /api/avatar/wizard/director/v1/performances/prepare`

The route:

- requires the existing loopback connector bearer token;
- rejects browser-origin requests;
- requires exact `application/json`;
- enforces a 64 KiB body limit;
- validates a closed `DirectedPerformancePreparationV1`;
- accepts `main` or `speech` as the authoritative source slot;
- returns only hashes, identifiers, semantic plan data, and an immutable score
  binding.

The request contains a content-free `PerformanceContextRequestV1`, one
controlled high-level direction, and exact media identity, duration, intent,
and deterministic seed.

The response contains the preliminary content-free context, the compiled
semantic plan and fallback records, and the exact score, character, package,
media, and context bindings. It does not echo direction or approved reply text.

## Transaction Fences

Compilation and repository publication run outside the frame hub writer lock.
The transaction rechecks the following before publication and again before
returning the binding:

- source-slot snapshot fingerprint;
- media ID, media SHA-256, and duration;
- reconciliation generation;
- controller cancellation generation;
- character runtime epoch;
- character ID;
- package digest;
- capability-manifest digest.

If a binding changes during compilation, the operation returns
`media_session_changed` and does not publish. If authority changes after an
immutable generation has been written, the operation does not return a usable
binding; activation still requires a later admitted media-session snapshot.

## Activation Contract

Preparation does not activate or mutate the scheduler directly. The connector
must send a subsequent media-session snapshot with the returned score binding,
the same media identity, the admitted character/package identity, and an
advanced `media_epoch`. Adding a score changes authoritative media/performance
identity. Attaching it in the old epoch correctly produces
`reconcile_required`.

## Verification

Focused verification covers duplicate-safe parsing, schema closure, media and
intent binding, private-direction rejection, deterministic compilation,
immutable publication/reload, hard-reconciled activation, existing-scheduler
projection, authentication, content-free responses, duration mismatch, and a
cancellation change during compilation.

## Remaining Production Gates

This slice does not complete unrestricted natural-language direction, score
editing UI, current-HEAD visual acceptance, long-duration soaks, complete
audiobook alignment, music-structure analysis, non-Wizard registry admission,
or per-character visual parity. Those gates remain explicit in the Character
Director acceptance documents.
