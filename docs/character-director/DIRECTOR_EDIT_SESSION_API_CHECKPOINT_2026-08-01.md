# Character Director Edit-Session API Checkpoint

Date: 2026-08-01

Parent checkpoint: `acce78e50f0564c5450c44d031068216de66e510`

## Purpose

This checkpoint exposes the governed score-edit core through a bounded,
authenticated server API without returning the server-custodied portable score,
approved language, conversational content, or raw renderer identifiers.

## Endpoints

### Prepare an editable performance

```text
POST /api/avatar/wizard/director/v1/performances/prepare-editable
```

The request is the existing strict `DirectedPerformancePreparationV1` document.
The runtime captures context, compiles off the event loop, rechecks all current
bindings, publishes the initial immutable compiled generation, and creates an
opaque edit session.

The added `edit_session` response contains:

- opaque session ID and remaining TTL;
- exact base-score hash, revision, character, package, and media bindings;
- cue IDs, track kinds, controlled intent, timing, intensity, lock state, and
  disabled state;
- exact precondition hashes for every supported edit type.

It does not contain direction text, approved reply text, capability requirement
arrays, asset paths, frame IDs, pixel data, or renderer commands.

### Apply and publish edits

```text
POST /api/avatar/wizard/director/v1/edit-sessions/{edit_session_id}/apply
```

The request is one complete hash-sealed `ScoreEditsV1` document. The runtime:

1. checks session existence and expiry;
2. verifies the current media fingerprint, reconciliation generation, control
   generation, runtime epoch, character, package, and capability manifest;
3. applies and recompiles off the event loop;
4. rechecks the exact server-custodied base revision to reject concurrent edits;
5. atomically publishes while holding the state transaction boundary;
6. replaces the in-memory session with the revised score/context and returns
   fresh precondition hashes for the next edit.

Replaying an edit set against the advanced revision fails with HTTP 409.

## Custody And Bounds

- Maximum live edit sessions: 32.
- Session TTL: 15 minutes.
- Expired sessions are pruned before create/read/replace operations.
- Capacity eviction is oldest-session first.
- Portable scores and compiler contexts remain in server memory only.
- Stored score mappings are defensively copied at create and replace.

## Authentication

- Companion mode requires `WIZARD_COMPANION_APP_TOKEN`.
- Standalone connector mode requires `WIZARD_MEDIA_CONNECTOR_TOKEN`.
- The app and connector tokens must remain distinct.
- Browser-origin requests are rejected.
- Loopback enforcement and bounded mutation-body handling remain active.

## Revision Correction

The API test exposed that edited portable scores advanced their revision while
the compiled-score loader defaulted generated artifacts to revision 1. The
compiled score schema now permits an optional revision for backward
compatibility. Edited compiled artifacts explicitly carry the revised portable
generation and receive a content-derived compiled ID. Legacy artifacts that
omit the field continue to load as revision 1.

## Verification

The consolidated focused command covered:

- character-bound compiler authority;
- score-edit contract and application;
- edit-session custody and bounds;
- directed-performance HTTP transactions;
- live-speech and Serena governed score paths;
- compiler, scheduler, score runtime, and schemas;
- Companion mutation-route authentication.

Result:

```text
Ran 85 tests in 133.711s
OK
```

The known broad-suite result remains 1070 tests with 112 failures and 7 errors,
primarily unrelated pose-source/evidence drift. This checkpoint does not alter
or remove that evidence.

## Follow-Up

- The native Companion score-editor controls are implemented and documented in
  `DIRECTOR_SCORE_EDITOR_UI_CHECKPOINT_2026-08-03.md`.

## Remaining Product Work

- Replace truth-bearing context defaults with authoritative observations.
- Connect governed live turns to automatic direction compilation and score
  binding.
- Add current-commit installed Prism audiovisual and long-duration drift proof.
- Continue one-character-at-a-time package admission and visual approval.
