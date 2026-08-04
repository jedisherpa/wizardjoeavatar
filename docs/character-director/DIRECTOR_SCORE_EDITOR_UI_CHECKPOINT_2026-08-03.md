# Character Director Score-Editor UI Checkpoint

Date: 2026-08-03

Parent checkpoint: `DIRECTOR_EDIT_SESSION_API_CHECKPOINT_2026-08-01.md`

## Purpose

This checkpoint connects the existing governed edit-session engine to the
native Wizard Joe Companion. A director can bind an explicit performance
direction to the active Prism speech or media source, inspect the resulting
content-free cues, and publish bounded human edits without exposing the
private app token or server-custodied score to browser code.

## Native Flow

The existing collapsible Director panel now includes a Performance score
section with:

- an authoritative Prism source selector for speech or main media;
- explicit intent, tone, stakes, urgency, relational stance, and action
  posture controls;
- a human-authored performance direction;
- cue controls for timing offset, duration, intensity, and enabled state;
- preparation and publication status tied to the current score revision.

Pressing **Prepare score** is the human approval action for the entered
direction. The UI hashes that exact direction as the presentation approval
artifact, binds it to the active media ID and digest reported by the server,
and opens a 15-minute opaque edit session. Each published cue change includes
the server-issued precondition hash for that exact field. Stale sessions and
concurrent edits therefore fail closed instead of overwriting newer work.

## Content-Free Source Inspection

The server adds this authenticated route:

```text
GET /api/avatar/wizard/director/v1/source-slots/{main|speech}
```

It reports only the source slot, media identity and duration, playback state,
character ID, and package digest. It does not return transcripts, titles,
messages, provider payloads, connector credentials, or raw score content.

The native Tauri bridge allowlists only the two literal source routes, the
literal preparation route, and apply routes containing an exact lowercase
`edit-session:` identifier. Other methods, malformed identifiers, path
traversal, and extra suffixes are rejected. The app token remains owned by the
native shell and is never injected into the webview.

## Scope And Safety

- The UI exposes the four non-semantic edit types whose valid values can be
  rendered without revealing server-owned asset identifiers.
- Published edits create a new immutable score revision through the existing
  edit-session service; the UI does not mutate the scheduler directly.
- Preparing or publishing a score does not activate it by itself. Runtime
  activation still requires an authoritative media-session binding.
- This work does not admit review-only character packages or change any
  character approval state.
- Existing Kingfisher pair evidence and unrelated untracked pose artifacts are
  preserved unchanged.

## Verification

The checkpoint is covered by:

- frontend contract tests for source binding, approval hashing, exact edit-set
  hashing, private-field exclusion, and browser-preview round trips;
- Python service tests for authentication, unavailable and ready source states,
  invalid slots, exact media identity, and content-free responses;
- Rust shell tests for the narrow route allowlist and malformed-session
  rejection;
- desktop and 390-pixel mobile visual checks with no horizontal overflow;
- an interactive browser-preview publication from score revision 1 to 2.

Focused command results:

```text
Companion frontend: 31 passed
Native shell:       17 passed
Python services:    49 passed
Total:              97 passed, 0 failed
```

`node --check companion/frontend/app.js`, native formatting verification, and
`git diff --check` also completed without errors.

## Remaining Product Work

- Replace truth-bearing context defaults with authoritative observations.
- Connect governed live turns to automatic direction compilation and score
  binding where explicit product policy permits it.
- Add current-commit installed Prism audiovisual and long-duration drift proof.
- Continue one-character-at-a-time package admission and visual approval.
