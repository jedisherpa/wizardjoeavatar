# Synthesis B: PrismGT Connector, Media UX, and Governed Whiz

Status: implementation-ready synthesis

Scope: PrismGT media connector, real media-element wiring, metadata/storage, debug and editor UI, governed Whiz, deployment boundaries, accessibility, test strategy, and two-repository delivery plan

Repositories:

- Wizard runtime: `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar-python`
- PrismGT: `/Users/paul/Documents/Codex/2026-06-28/jedisherpa-prism-geometry-talk-https-github/work/prism-geometry-talk-current`

This document reconciles the twelve specialist reports, the current-state architecture, the program tracker, the full brief, and the code as it exists in both repositories. It does not redesign the animation engine covered by Synthesis A. Its contract is the boundary that Synthesis A consumes.

## 1. Locked decisions

1. The real PrismGT `HTMLAudioElement` is the sole playback clock. `audio.currentTime`, `audio.duration`, `audio.playbackRate`, `audio.readyState`, and its native events are authoritative. React state, the visualizer, transcript timers, and network send time are not clocks.
2. PrismGT sends versioned, idempotent **full playback snapshots with an event cause**, not a firehose of imperative animation commands. Immediate lifecycle snapshots are supplemented by a 4 Hz heartbeat while playing.
3. Browser JavaScript never calls Wizard directly. It posts to a same-origin PrismGT route; the Rust sidecar relays to Wizard over a fixed loopback HTTP destination with a dedicated bearer token.
4. The connector is available only on `DesktopApp` and `LegacyLocal`. `PublicWeb` returns the explicit capability state `unavailable_on_public_web` and exposes no route that can reach a visitor's localhost.
5. The wire time unit is integer milliseconds. Sample indices and higher-resolution internal timing remain local to analysis artifacts. This avoids float drift and forces one conversion boundary.
6. Discontinuity is represented by `media_epoch`. It replaces the competing report names `generation` and `source_epoch`. A new connector page uses a new `connector_session_id`; a seek/source/stop discontinuity increments `media_epoch`.
7. Wizard owns accepted performance score bytes, immutable score revisions, and scheduling state. PrismGT owns durable media identity, provenance, canonical external URL, transcript/alignment references, and pointers to the current accepted score.
8. Live Web Audio analysis remains a cosmetic visualizer input only. Deterministic performance uses precomputed, versioned sidecars and the Wizard scheduler.
9. Whiz launches only a stored, validated `canonicalExternalUrl`; it never launches the playable media URL, a blob URL, a file path, a transcript URL, a provider guess, or a URL supplied by the click request.
10. A Whiz click is a single, explicit user approval for one external navigation. Prism records a content-free signed-ledger grant before opening. No model, tool, chat turn, or standing approval participates.
11. The editor is a focused internal performance editor after transport correctness, not a general nonlinear editor. It writes a new immutable score revision; it never mutates the accepted score in place.
12. Accessibility is part of the protocol and release gate. A resolved motion profile and channel overrides cross the connector; a boolean `reduced_motion` is insufficient.

## 2. Current code reality

### 2.1 PrismGT playback path

The production player already has one correct clock source:

- `src/pages/PrismDodecahedron/index.jsx:3585` owns the hidden `<audio ref={audioRef}>` with `preload="metadata"` and `playsInline`.
- `loadTrackIntoAudio`, `playAudioElement`, `playTrackNow`, and `togglePlayback` at `index.jsx:1141-1214` mutate that element.
- `createAudioMotionController` is attached at `index.jsx:2858-2896`. It may continue to drive presentation reactivity, but it must not become connector transport.
- Track replacement is handled at `index.jsx:2898-2918`; captions at `2920-2985`; playlist auto-advance at `2987-3005`.
- `musicMotion.js:163` owns the analyser loop and currently listens only to `play`, `pause`, `ended`, and `loadedmetadata`. It is a visualizer, not a complete media lifecycle observer.
- `studio/StageUtilityCards.jsx:347-598` renders a read-only progress meter plus previous/play/next, track list, captions, and link-audio controls. It has no seek, rate, stop, transcript, character, motion, connector, Whiz, or editor controls.
- The caption overlay at `index.jsx:3797-3804` uses `aria-live="polite"`, which can cause screen readers to speak the prerecorded audio a second time.

The connector must therefore attach directly to `audioRef.current` in the owner page, not infer state from `audioMetrics.playing`, the 90 ms React update throttle, the Three.js scene, or caption `setTimeout` callbacks.

### 2.2 PrismGT media metadata and storage

There are three distinct media sources today:

| Source | Current identity/storage | Consequence |
|---|---|---|
| Manifest library | `src/pages/PrismDodecahedron/musicLibrary.js`; `/api/library`; `/media/*` or bundled `/music/*` | `normalizeTrack` drops any new performance and canonical-link fields unless extended. |
| Persisted audiobook | `crates/prism-cdiss-cli/src/audiobooks.rs`; `audiobooks/tracks/<track_id>/` | `AudiobookTrack` has useful provider fields but no durable media digest, canonical URL, transcript/alignment URL, or performance pointer. |
| Linked local MP3 | `src/lib/media-normalize.js:16-39`; browser blob URL | Random page-lifetime ID and no durable digest. It may play, but it cannot claim a durable score or Whiz link until imported into managed storage. |

`AudiobookStore::store_audio` writes each file atomically but publishes several files into the final track directory one at a time. Readers can observe a partially updated generation. The implementation must stage a whole generation directory, fsync it, rename it into place, and atomically switch a small `current.json` pointer. Old generation directories remain rollback evidence until retention cleanup.

### 2.3 PrismGT security and governance path

The local router already has the right browser boundary:

- `crates/prism-cdiss-cli/src/web.rs:464-563` builds local routes and applies mutating-request/session-token middleware.
- `src/api/session-token.js` adds `x-prism-token` to same-origin mutating `/api/*` calls and retries once after a sidecar restart.
- `web.rs:7887-7910` validates the per-launch token; `web.rs:7935+` rejects cross-site/same-site mutation attempts and invalid local Origin/Host combinations.
- `build_public_router` deliberately excludes local audiobook mutations. The Wizard connector must follow the same separation.
- `CliApp` owns the signed `ThreadLedger` at `main.rs:1683-1734`; `dispatch_role` at `4600-4633` is suitable for role output, but not for proving a user-approved external navigation because it always sets `prism_holder_approved: false` and discards persistence errors.

Whiz therefore needs a narrow audit method on `CliApp`, not a fake chat turn and not reuse of the X-post pending-action flow.

### 2.4 Wizard runtime path

Wizard's existing server and ordered command runtime are intentionally preserved:

- `wizard_avatar/server.py:24-242` creates FastAPI routes, the semantic command endpoints, and the frame WebSocket.
- `wizard_avatar/stream.py:31-190` owns `WizardFrameHub`, the runtime epoch, the 60 Hz deterministic simulation, and presentation frame publication.
- `wizard_avatar/commanding.py` validates bounded, ordered user/system commands and applies a 120-tick future horizon.
- `tools/run_wizard_avatar_server.py` defaults to loopback.

The media session is not another `WizardCommand`. It needs separate validation, session/epoch ordering, score lookup, and scheduling, then contributes a media-performance layer to the animation compositor described by Synthesis A. It must not enqueue four generic commands per second or overload the existing command horizon.

## 3. Reconciled conflicts

| Conflict in reports | Decision | Reason |
|---|---|---|
| HTTP snapshots versus WebSocket event stream | V1 uses HTTP full snapshots at 4 Hz plus immediate lifecycle sends. | Both servers already have HTTP stacks and acknowledgements. One in-flight request plus one latest pending snapshot bounds work. WebSocket complexity is deferred until measurement proves HTTP inadequate. |
| Event log versus state reconciliation | Every message is a full snapshot; `cause` explains why it was sent. | Lost events cannot strand Wizard. The receiver can reconstruct from any accepted message. |
| Float seconds, microseconds, ticks, or samples | Wire values are integer milliseconds. | Browser media APIs expose seconds, while scores may use samples. Milliseconds are sufficient for the <=100 ms user-visible target and serialize deterministically. |
| `generation`, `source_epoch`, or `media_epoch` | Use `media_epoch`; retain `connector_session_id` and `sequence`. | The field specifically marks media-clock discontinuity, not process lifetime or command ownership. |
| Direct browser-to-Wizard connector versus sidecar relay | Same-origin browser-to-Prism, server-to-server Prism-to-Wizard. | No CORS surface, no Wizard secret in JavaScript, no hosted page probing localhost, and reuse of Prism's current session-token defense. |
| WebSocket command receiver as connector | Do not use it. Harden its origin/auth separately before any external exposure. | The current WebSocket accepts before validating origin/auth and accepts legacy command messages. It is a frame/control transport, not a media contract. |
| `reduced_motion: bool` versus full motion preferences | Send resolved `motion_profile` plus sorted `disabled_channels`. | Users need full, reduced, and still behavior, with independent channel overrides and flash safety. |
| Store score artifacts in Prism versus Wizard | Prism stores score references/status; Wizard stores score bytes and revisions. | Prevents two authorities and keeps the scheduler next to the artifact it executes. |
| Live Web Audio versus offline DSP | Keep live Web Audio for non-authoritative visuals; use offline sidecars for performance. | Live analyser timing is device/browser dependent and cannot reproduce seek/reconnect behavior. |
| Server 303 Whiz versus Tauri opener | Use one governed grant path and two launch adapters: browser navigation for web/local, scoped Tauri opener for desktop. Both open a single-use local redirect URL, never the external URL directly. | This preserves backend URL authority and reliably reaches the system browser from the desktop app. Tauri is only allowed to open the same-origin loopback grant path. |
| Hide unavailable Whiz versus show disabled | Hide for inapplicable media kinds; show a persistent unavailable state for applicable music/video with missing or invalid canonical metadata. | Users should not hunt for a feature that cannot apply, but metadata defects must be visible and testable. |
| Local blob playback with a durable score | Allow playback, force performance status `unbound`, and disable Whiz. | A page-lifetime UUID/blob URL cannot prove media identity. Managed import computes a digest and creates the durable record. |
| Immediate full editor versus late tooling | Ship a read-only debug/score inspector after connector correctness, then a focused editor with semantic alternatives. | Debuggability is required for rollout; a broad editor must not block reliable transport. |
| Caption overlay as a live region | Remove implicit live announcement; offer user-controlled transcript/caption accessibility behavior. | Continuous `aria-live` duplicates prerecorded speech and is disruptive. |

## 4. End-to-end topology

```text
PrismGT HTMLAudioElement
  -> useMediaSessionConnector(audioRef, currentTrack, preferences)
  -> POST /api/connectors/wizard/media-session
       x-prism-token (existing same-origin interceptor)
  -> Rust MediaConnector
       strict body limit, schema validation, queue coalescing
       fixed loopback base URL + dedicated bearer token
  -> POST http://127.0.0.1:<fixed>/api/avatar/wizard/media-session
       Authorization: Bearer <connector token>
  -> Python MediaSessionRegistry
       auth, ordering, active-controller lease, score binding
  -> PlaybackPerformanceScheduler
       authoritative state reconstruction, seek cancellation, lookahead
  -> Synthesis A animation layers
       body + face + eyes + mouth + camera, accessibility clamps
```

The audio path never waits for this chain. Connector failure changes only visual performance status. It must not pause, seek, reload, alter volume, change track, or block the player's controls.

## 5. Media session protocol V1

### 5.1 Request

Route from Prism browser to Prism sidecar:

`POST /api/connectors/wizard/media-session`

Route from Prism sidecar to Wizard:

`POST /api/avatar/wizard/media-session`

Content type is exactly `application/json`. Maximum body size is 16 KiB. Unknown fields are rejected at every object level. Strings are trimmed, bounded, and must contain no control characters. Numeric values must be finite; millisecond values are non-negative integers.

```json
{
  "schema_version": 1,
  "message_id": "5a796ad0-e3ef-480a-a16d-d326453397aa",
  "connector_session_id": "84ae5fb5-4e22-4e30-bba6-9a373e4e3c76",
  "sequence": 42,
  "media_epoch": 3,
  "cause": "seeked",
  "sampled_at_monotonic_ms": 937510,
  "media": {
    "media_id": "studio-chapter-project-chapter-snapshot",
    "media_sha256": "4fc4b75b8e4d7ad008757f0755c6dcb7be8aa36ab5706998d417e5e3754a97f1",
    "kind": "audiobook",
    "source_kind": "studio_chapter",
    "book_id": "book-7",
    "chapter_id": "chapter-12",
    "duration_ms": 1638204
  },
  "playback": {
    "state": "playing",
    "position_ms": 81735,
    "rate": 1.0,
    "ready_state": 4,
    "seeking": false
  },
  "performance": {
    "mode": "narrative",
    "score_id": "score-4fc4b75b-v3",
    "score_revision": 3,
    "score_sha256": "a44f338f048e110e80a065c56f2a03e23bdb351e9b77157b57b42bf08cf219d7",
    "character_id": "wizard-joe",
    "character_package_sha256": "7fa2c19477e6cdccd0d464ef7309ccf2cf3f99ee3d60275efff4183f4fd3bb10",
    "intensity": 0.65,
    "motion_profile": "reduced",
    "disabled_channels": ["camera_motion", "flight", "whole_body_pulse"]
  }
}
```

Field rules:

| Field | Rule |
|---|---|
| `schema_version` | Integer `1`; other versions return `unsupported_schema`. |
| `message_id` | UUID v4 generated per send attempt and used for request-level deduplication. A retry of the same queued snapshot reuses it. |
| `connector_session_id` | UUID v4 generated once per mounted player/page session. It is not persisted across reload. |
| `sequence` | Starts at `0`, strictly increases for every newly sampled snapshot within a connector session, and is never reused for different content. |
| `media_epoch` | Starts at `0`; increments on track/source replacement, seek start, explicit stop/reset, duration-invalidating reload, or media error recovery. `seeked` uses the epoch created by `seeking`. |
| `cause` | One of `mount`, `loadedmetadata`, `durationchange`, `play_intent`, `playing`, `pause`, `waiting`, `stalled`, `seeking`, `seeked`, `ratechange`, `visibilitychange`, `heartbeat`, `ended`, `stop`, `emptied`, `error`, `preferencechange`, `trackchange`, `pagehide`, `reconnect`. |
| `sampled_at_monotonic_ms` | Rounded `performance.now()` from the browser. Diagnostic only; never compared to the server wall clock and never used as an absolute scheduling origin. |
| `media.media_id` | Stable Prism media ID, 1-128 ASCII characters. |
| `media.media_sha256` | Required for `mode != "none"`; otherwise `null`. A mismatch with the score forces neutral performance. |
| `media.kind` | `audiobook`, `podcast`, `music`, or `video`. |
| `media.source_kind` | `library`, `podcast`, `generated`, `studio_chapter`, `managed_import`, or `linked_local`. This is bounded provenance, never a URL or path. |
| `book_id`, `chapter_id` | Nullable stable IDs; never inferred from display title. |
| `duration_ms` | Nullable until metadata loads. A finite positive integer once known. |
| `playback.state` | `empty`, `loading`, `paused`, `playing`, `buffering`, `ended`, `stopped`, or `error`. `play` intent alone is not `playing`; only the native `playing` event establishes it. |
| `position_ms` | Sampled directly from `audio.currentTime` in the event handler immediately before serialization. |
| `rate` | Finite number in `[0.25, 4.0]`; accepted supported rates are returned by capabilities. |
| `ready_state` | Integer `0..4` copied from the media element. |
| `seeking` | Boolean copied from the media element. |
| `performance.mode` | `narrative`, `music`, or `none`. `none` requires null score fields and selects neutral behavior. |
| score fields | All required together when mode is not `none`; score revision is a positive integer. |
| character fields | Stable ID plus exact package digest. Missing/mismatched packages select the neutral fallback and report the mismatch. |
| `intensity` | Finite `[0,1]`, applied after score envelopes and before accessibility clamps. |
| `motion_profile` | Resolved `full`, `reduced`, or `still`. Prism may store user preference `system`, but resolves it before sending. |
| `disabled_channels` | Sorted, unique subset of the frozen channel registry. Unknown values reject the snapshot rather than silently weakening a preference. |

Neither transcript text, caption text, media title, canonical/source URL, local path, provider key, user prompt, nor score bytes are present in this transport.

### 5.2 Acknowledgement

```json
{
  "schema_version": 1,
  "connector_session_id": "84ae5fb5-4e22-4e30-bba6-9a373e4e3c76",
  "accepted_sequence": 42,
  "accepted_media_epoch": 3,
  "disposition": "accepted",
  "wizard_runtime_epoch": "wizard-f59d6f...",
  "resync_required": false,
  "scheduler_state": "synchronized",
  "error": null,
  "capabilities": {
    "media_session_schema": 1,
    "max_snapshot_hz": 4,
    "supported_rates": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
    "motion_profiles": ["full", "reduced", "still"]
  }
}
```

`disposition` is one of `accepted`, `duplicate`, `stale`, `controller_conflict`, `score_missing`, `score_mismatch`, `character_mismatch`, `unavailable`, or `rejected`. `scheduler_state` is one of `synchronized`, `buffering`, `paused`, `neutral`, `uncertain`, or `error`.

HTTP mapping:

| Status | Meaning |
|---|---|
| `200` | Accepted, duplicate, stale, or a typed neutral fallback. The JSON disposition is authoritative. |
| `400` | Malformed JSON. |
| `401` | Missing/invalid Prism-to-Wizard bearer token. Use constant-time comparison and a generic response. |
| `403` | Browser-origin request reached Wizard directly, or Prism same-origin/token middleware rejected the browser request. |
| `409` | Active controller conflict or impossible session/epoch transition requiring a fresh session. |
| `413` | Body exceeds 16 KiB. |
| `415` | Wrong content type. |
| `422` | Schema/range/unknown-field validation failure. |
| `503` | Connector disabled, Wizard unavailable, or scheduler not ready. Audio remains unaffected. |

On any successful response with a changed `wizard_runtime_epoch`, or with `resync_required: true`, Prism immediately sends the newest full snapshot with `cause: "reconnect"`. It does not replay historical events.

## 6. Media-element lifecycle and send policy

The frontend hook installs listeners once per audio element and reads current track/preferences through refs to avoid listener churn. Each handler samples the element synchronously.

| Native/UI event | State action | Epoch action | Send |
|---|---|---|---|
| Hook mount with selected media | Establish session and current media identity. | Start session at `0`. | Immediate `mount`. |
| Track/source change before `load()` | Mark loading and replace media identity. | Increment. | Immediate `trackchange`, then native events. |
| `loadedmetadata` / `durationchange` | Refresh duration and position. | No increment unless duration invalidates prior source identity. | Immediate. |
| User calls play | State stays loading/paused until native confirmation. | None. | Immediate `play_intent`. |
| `playing` | Set playing; start heartbeat. | None. | Immediate. |
| `pause` | Set paused; stop heartbeat. Ignore transient pause immediately followed by ended only for UI wording, not transport. | None. | Immediate. |
| `waiting` / `stalled` | Set buffering; stop forward interpolation after freshness window. | None. | Immediate. |
| `seeking` | Cancel future scheduled work and mark seeking. | Increment immediately. | Immediate. |
| `seeked` | Reconstruct at actual current time and current playing/paused state. | Keep seeking epoch. | Immediate. |
| `ratechange` | Update rate and re-anchor. | None. | Immediate. |
| Explicit Stop control | `pause()`, set `currentTime = 0`, set stopped. | Increment. | Immediate after element mutation. |
| `ended` | Set ended before current Prism auto-next changes the track. | None. | Immediate; next track emits its own increment. |
| `emptied` / `error` | Cancel performance and select neutral. | Increment. | Immediate. |
| Motion/character/intensity change | Apply to current clock without restarting audio. | None. | Immediate `preferencechange`. |
| `visibilitychange` | No semantic playback change. | None. | Immediate, so background throttling is visible. |
| `pagehide` / unmount | Stop heartbeat and release control lease best-effort. | None. | `fetch(..., keepalive: true)` if body fits; freshness timeout is the safety authority. |

While `playing`, send a heartbeat every 250 ms. Do not use `timeupdate`; browsers throttle it variably. Event snapshots are never delayed to the heartbeat.

Queue policy:

- At most one request is in flight.
- At most one unsent snapshot is retained. A newer heartbeat replaces an older heartbeat. A lifecycle edge replaces any pending heartbeat but is itself superseded only by a newer full snapshot because the full state remains sufficient.
- A retry preserves `message_id`, sequence, epoch, and sampled content. A newly sampled replacement receives a new ID/sequence.
- No network response may write to the audio element.

## 7. Synchronization, reconnect, and failure behavior

### 7.1 Clock reconstruction

Wizard records local monotonic receipt time for every accepted snapshot. While `playback.state == "playing"`, `seeking == false`, and the snapshot is younger than 1.5 seconds:

```text
estimated_position_ms = position_ms + elapsed_since_receipt_ms * rate
```

The browser monotonic timestamp is diagnostic only because the processes do not share an epoch. A new snapshot always re-anchors to its reported position.

- Error <=50 ms: continue and re-anchor without visible discontinuity.
- Error >50 ms and <=100 ms: bounded phase correction over at most 200 ms for continuous low-risk channels; discrete cues are recomputed.
- Error >100 ms, epoch change, seek, score change, or character change: cancel scheduled work and hard-reconstruct from the score at the new position.
- Snapshot age >1.5 seconds: mark `uncertain`; do not begin new semantic gestures, scene changes, or flashes. Fade continuous performance channels to neutral over 250 ms while mouth/audio presentation may continue independently.
- Snapshot age >5 seconds: release the active controller lease and remain neutral.

### 7.2 Retry and restart

Prism retries only the latest snapshot with exponential backoff `250 ms, 500 ms, 1 s, 2 s, 5 s`, capped at 5 seconds, with +/-20% jitter. A new native lifecycle event interrupts the timer and attempts the newest state immediately. UI status moves through `connecting`, `connected`, `degraded`, `unavailable`, and `controller_conflict`; no toast repeats on every heartbeat.

Wizard accepts the first live connector session as controller. The same session may reconnect. A different session receives `controller_conflict` until the current session sends `pagehide`/`stop` release or is stale for five seconds. This prevents two Prism tabs from silently fighting over one character.

Wizard restart creates a new `wizard_runtime_epoch`. The first post-restart snapshot reconstructs all current media/performance state. Prism sidecar restart mints a new `x-prism-token`; the existing frontend interceptor refreshes once, after which the media connector sends `reconnect`. Neither restart changes audio playback.

## 8. Local, desktop, public, and cross-origin deployment

### 8.1 Configuration

Prism sidecar reads once at startup:

- `PRISM_WIZARD_CONNECTOR_ENABLED=1`
- `PRISM_WIZARD_BASE_URL=http://127.0.0.1:8765`
- `PRISM_WIZARD_CONNECTOR_TOKEN=<high-entropy secret>`

Wizard reads the same secret from `WIZARD_PRISM_CONNECTOR_TOKEN`. The token is separate from the Prism browser token and never appears in frontend JSON, logs, diagnostics, URLs, or error text.

Startup URL validation is fail-closed:

- scheme exactly `http`;
- host is the literal `127.0.0.1` or `[::1]`, not `localhost` and not a DNS name;
- explicit port is required;
- no username, password, query, or fragment;
- path is empty or `/`;
- redirects are disabled on the relay client;
- request handlers cannot override the destination.

The relay has a 750 ms connect timeout and 1.5 second total timeout. It uses a dedicated `reqwest::Client`, no proxy, no cookie store, and a bounded two-response-body read. Logs contain disposition, latency bucket, session/sequence/epoch, and hashes truncated to a non-identifying prefix; never tokens, URLs, titles, transcript text, score payloads, or query strings.

Wizard's media-session route:

- binds only on the existing loopback service;
- requires `Authorization: Bearer` and compares in constant time;
- rejects requests with any `Origin` header, because only the Rust server is a client;
- uses FastAPI/Pydantic strict models and a 16 KiB body limit;
- emits no permissive CORS headers.

### 8.2 Surface matrix

| Surface | Media connector | Whiz | Required behavior |
|---|---|---|---|
| `DesktopApp` | Enabled only with valid startup config. | Governed grant plus scoped Tauri opener to the single-use local redirect route. | System browser opens; app playback is unchanged. |
| `LegacyLocal` | Same contract and token middleware. | Governed grant plus browser `window.open` to the local redirect route. | Same-origin only. |
| `PublicWeb` | Disabled; local connector route absent. | Enabled only for an authenticated user and a server-held public media record, using the same grant/redirect rules and the public surface's existing session/CSRF defenses. | Hosted code must not probe or instruct a browser to call localhost. |

A future remote Wizard deployment is a separate design requiring TLS, user authentication, tenant authorization, replay protection, rate limiting, and an explicit public ingress. `PRISM_WIZARD_BASE_URL` must not be loosened to support it.

## 9. Durable metadata and storage contract

### 9.1 Prism media record

Extend both manifest normalization and `AudiobookTrack` with additive, optional fields. JSON uses camelCase; Rust fields use snake_case under `#[serde(rename_all = "camelCase")]` and `#[serde(default)]` where needed for old records.

```json
{
  "mediaId": "stable-id",
  "mediaSha256": "64-lowercase-hex",
  "kind": "audiobook",
  "title": "Chapter 12",
  "author": "Author",
  "bookId": "book-7",
  "chapterId": "chapter-12",
  "durationMs": 1638204,
  "audioUrl": "/api/audiobooks/stable-id/audio",
  "captionsUrl": "/api/audiobooks/stable-id/captions.vtt",
  "transcriptUrl": "/api/audiobooks/stable-id/transcript.json",
  "alignmentUrl": "/api/audiobooks/stable-id/alignment.json",
  "sourceUrl": null,
  "canonicalExternalUrl": "https://publisher.example/title/chapter-12",
  "canonicalExternalUrlSource": "publisher_manifest",
  "timing": {
    "status": "verified",
    "schemaVersion": 1,
    "sha256": "64-lowercase-hex"
  },
  "performance": {
    "status": "ready",
    "scoreId": "score-4fc4b75b-v3",
    "scoreRevision": 3,
    "scoreSha256": "64-lowercase-hex",
    "characterPackageSha256": "64-lowercase-hex",
    "analyzerVersion": "audiobook-performance-1"
  }
}
```

Rules:

- `mediaId` is the existing stable track ID. Do not derive it from title during playback.
- `mediaSha256` hashes exact audio bytes and is computed at managed ingestion/storage time. It binds all timing and score artifacts.
- `sourceUrl` records acquisition provenance when policy permits. Whiz never uses it.
- `canonicalExternalUrl` is nullable and specifically means a user-facing publisher/artist/video page suitable for external navigation.
- `canonicalExternalUrlSource` is one of `publisher_manifest`, `provider_metadata`, `user_verified`, or `admin_verified`; guessed/search-derived values are prohibited.
- Status values are `missing`, `pending`, `ready`, `failed`, `stale`, or `mismatch`, with a stable reason code outside any live region.
- Selected character, intensity, and motion preferences are session/user preferences, not media facts, and do not belong in this record.
- Transcript and caption text remain in separate artifacts. Metadata may expose their URLs/status but not inline full text.

### 9.2 Ownership and publication

Prism persisted track layout becomes:

```text
audiobooks/tracks/<media_id>/
  current.json
  generations/<generation_id>/
    audio.mp3
    metadata.json
    captions.vtt          optional
    transcript.json       optional
    alignment.json        optional
    checksums.json
```

Write every generation to a sibling temporary directory, verify hashes and internal references, fsync files/directory, rename to `generations/<id>`, then atomically replace `current.json`. The list/read APIs resolve only a complete current generation. A failed write leaves the previous pointer intact.

Migration is additive. The new reader supports both the legacy root-file layout and generation pointers. Existing root files are not moved or deleted; they remain the compatibility snapshot an older binary can read after a code rollback. Tracks first created in the generation layout may be temporarily invisible to an older binary, but their bytes remain intact and reappear when the new reader is restored. This limitation must be called out in the rollback drill rather than disguised as full backward readability.

Wizard stores performance artifacts under its existing data-root convention, not under Prism's app data:

```text
performance/media/<media_sha256>/
  current.json
  scores/<score_id>/<revision>/
    score.json
    provenance.json
    checksums.json
```

Accepted revisions are immutable. Editing creates `revision + 1`, validates it, writes it atomically, then advances `current.json`. Prism stores only the returned identity/hash/status. An old score whose media or character package digest no longer matches remains inspectable but cannot run.

## 10. Governed Whiz

### 10.1 URL validation

Validate on ingestion/update and again immediately before grant issuance with Rust's `url` parser:

- absolute `http` or `https` only;
- non-empty host;
- maximum serialized length 2048 bytes;
- no username/password;
- no ASCII control characters or embedded whitespace;
- canonical parser serialization must round-trip;
- fragments and query strings are allowed because legitimate publisher/video pages use them, but neither is logged;
- `javascript:`, `data:`, `file:`, `blob:`, custom schemes, relative URLs, and protocol-relative URLs are rejected.

Invalid legacy metadata is retained for repair but produces `invalid_canonical_url`. Do not silently substitute another field.

### 10.2 Two-step single-use launch

1. Applicable UI is rendered only for `music` and `video`. It receives media ID, availability, and display domain; its launch target contains no external URL.
2. On a trusted pointer/keyboard activation, require `event.isTrusted` and active `navigator.userActivation` where supported. Open at most one blank browsing context synchronously on browser surfaces.
3. POST `/api/media/{media_id}/whiz/grants`. The existing Prism session interceptor supplies `x-prism-token`; the local Origin/Host middleware applies.
4. Server looks up the record by media ID, revalidates the stored canonical URL, rate-limits, and appends `MEDIA_EXTERNAL_OPEN_GRANTED` to the signed ledger with `prism_holder_approved: true`.
5. The ledger payload is content-free: action ID, media ID, canonical host hash, URL hash, media kind, surface, timestamp, and result. It contains no raw URL, title, query, transcript, or user text. Audit persistence failure fails closed and returns `audit_unavailable`.
6. Server mints a 256-bit, single-use, 30-second grant bound to media ID, URL hash, current local session, and surface. Response returns only `/api/media/{media_id}/whiz?grant=<opaque>`.
7. Browser/local sets the one blank context to that path. Desktop calls a narrowly scoped Tauri opener for that same-origin loopback path. The external URL is never passed to Tauri or JavaScript.
8. GET consumes the grant exactly once, rechecks record/hash/expiry, and returns `303 See Other` with `Location: <stored canonical URL>`, `Cache-Control: no-store`, and `Referrer-Policy: no-referrer`.
9. Failure closes the blank context when possible and renders one actionable error. A second deliberate click creates a new grant. Playback is untouched.

The grant cache is in-memory and bounded. A sidecar restart invalidates all grants. A replay, wrong media ID, wrong session, expired grant, or changed URL hash returns a generic 404/410 without revealing the destination.

### 10.3 UI states

| State | Presentation |
|---|---|
| Inapplicable media | Whiz is absent. |
| Applicable, canonical URL missing/invalid | Disabled Whiz action remains visible with persistent reason text linked by `aria-describedby`. |
| Ready | Accessible name `Open source page for <title>` and visible destination domain. |
| Granting/opening | One busy state; repeated activation ignored. |
| Opened | Calm status, not an assertive announcement. Do not claim browser completion beyond successful grant dispatch. |
| Failed | Visible error and explicit Retry action. |

## 11. Player, transcript, debug, and editor UX

### 11.1 Player changes

Keep `StageUtilityCards` as the user-facing shell but move stateful media controls into dedicated components/hooks. Required controls:

- seek slider with current/total time and keyboard increments;
- previous, play/pause, stop, next;
- playback-rate select for supported values;
- chapter/track selection;
- captions toggle and transcript-panel toggle as separate controls;
- character select, intensity slider, and motion-profile segmented control;
- connector status button that opens diagnostics;
- Whiz state/action where applicable;
- editor entry visible only under the internal feature flag.

Use familiar icons from an installed icon library when introduced, with tooltips and accessible names. Stable control dimensions must prevent layout shifts. Primary controls target at least 44 by 44 CSS pixels; no control may be smaller than 24 by 24.

### 11.2 Transcript

The transcript panel is persistent, selectable text, not a live subtitle stream. It provides search, current-cue highlighting, cue-to-seek activation, and a user-controlled follow toggle. Follow never steals keyboard focus and turns off after manual scrolling until explicitly resumed. Captions remain a concise overlay; remove `aria-live` from the continuously changing caption node. If the user explicitly enables spoken caption announcements, use a separate opt-in mechanism and warn that it duplicates program audio.

Transcript status distinguishes human-verified, provider timing, forced alignment, draft, stale, and unavailable. Prerecorded audiobook/podcast release requires a transcript/caption artifact unless a documented exception is approved.

### 11.3 Diagnostics

The developer panel is structured HTML (`dl`, table, status text), not only lil-gui or canvas text. It shows:

- connector state, retry count, last HTTP status, and round-trip latency;
- session ID suffix, sequence, media epoch, and Wizard runtime epoch;
- element state, actual position, estimated Wizard position, drift, rate, ready state, and snapshot age;
- media/score/character digest match state;
- current score ID/revision, cue, phase, fallback mode, and scheduler queue depth;
- resolved motion profile and disabled channels;
- a Pause updates control and a Copy sanitized snapshot control.

Do not announce heartbeat updates through a live region. Connection state changes may use `role="status"`; actionable failures may use `role="alert"` once per transition.

### 11.4 Focused performance editor

The editor is a full-width work surface, not a card inside the player and not part of the Three.js scene. It includes:

- waveform/overview with playhead and chapter boundaries;
- lanes for narrative beats, semantic cues, facial/eye emphasis, body action, and camera/scene cues;
- synchronized semantic cue table as a complete non-drag alternative;
- timing fields with 10 ms, 100 ms, and 1 s keyboard adjustments;
- cue enable/disable, action replacement, intensity, attack/release, provenance, confidence, and fallback visibility;
- original score versus working revision comparison;
- undo/redo within the working copy;
- Validate, Preview from cue, Save new revision, and Revert working copy commands.

Dragging is never the sole means of editing. Saving validates ordering, overlap/channel conflicts, media/character hashes, flash/motion limits, and schema before creating an immutable revision. Preview uses the real audio element and connector; it does not invent a second player clock.

## 12. Accessibility contract

### 12.1 Motion profiles

Prism stores preference `system`, `full`, `reduced`, or `still`; `system` resolves from `prefers-reduced-motion` before transport.

| Profile | Required behavior |
|---|---|
| `full` | Authored performance subject to flash and comfort limits. |
| `reduced` | Preserve captions, mouth timing, gaze targets, and low-amplitude facial expression. Disable locomotion, dance, flight, rapid turns, whole-body scale/pulse, audio-reactive whole-body motion, camera movement, simulated depth travel, and repeated spin. |
| `still` | Freeze stage/body/camera at a stable neutral pose; retain captions/transcript and optional minimal mouth/eye state only if separately enabled. |

Independent channel toggles may further disable `mouth`, `eyes`, `face`, `upper_body`, `locomotion`, `dance`, `flight`, `camera_motion`, `scene_flash`, `simulated_depth`, or `whole_body_pulse`. A less restrictive toggle cannot override a more restrictive resolved profile. Changes apply within 250 ms without reloading audio or regenerating the score.

Flash safety is independent of motion preference. No content may exceed three flashes per second; high-contrast repeated transitions are clamped during score validation and again at runtime.

### 12.2 Operability and presentation

- All player, Whiz, transcript, diagnostics, and editor actions are keyboard operable with visible focus.
- At 200% zoom and 320 CSS-pixel width, controls wrap without overlap, clipping, or horizontal page scrolling. Timeline regions may have a clearly labelled local horizontal scroll container.
- Text and controls meet WCAG 2.2 AA contrast; state is never color-only.
- Canvas is decorative to assistive technology. Equivalent performance state is available in diagnostics, but not continuously announced.
- Focus remains in the initiating surface after play/seek/preference changes. Opening a panel moves focus only when standard dialog/panel behavior requires it and restores focus on close.
- Provider-backed transcription, TTS, or LLM analysis requires an explicit privacy preflight naming data, provider, purpose, retention, and a local/offline alternative. The presence of an API key is not consent.

## 13. Exact two-repository file plan

### 13.1 WizardJoeAvatar-python

| File | Change |
|---|---|
| `wizard_avatar/media_session.py` (new) | Strict request/ack dataclasses or Pydantic models, unknown-field rejection, enum/range/hash validation, active-session lease, sequence/message deduplication, media-epoch transition checks, and sanitized diagnostics. |
| `wizard_avatar/performance_score.py` (new) | Immutable score repository keyed by media digest/score ID/revision; atomic generation publication; hash/package binding; current pointer and rollback selection. |
| `wizard_avatar/performance_scheduler.py` (new) | Snapshot reconstruction, freshness state, hard seek cancellation, bounded lookahead, drift policy, score cue selection, accessibility clamps, and neutral fallback output for Synthesis A layers. |
| `wizard_avatar/server.py` | Add authenticated `POST /api/avatar/wizard/media-session` and read-only sanitized connector status; enforce body/content/origin/token rules. Do not route through `WizardCommand` or the frame WebSocket receiver. |
| `wizard_avatar/stream.py` | Own one scheduler instance beside `AvatarRuntime`; sample its current media-performance layer during `_reduce_runtime_tick`. Preserve existing command inbox, frame cadence, and runtime epoch. |
| `wizard_avatar/frame_source.py` | Accept the already-resolved media-performance layer at composition time using Synthesis A's channel boundary; no network or score parsing here. |
| `tools/run_wizard_avatar_server.py` | Validate connector token/config at startup; continue default loopback binding. |
| `contracts/wizard-media-session/v1/schema.json` (new) | Canonical protocol JSON Schema and frozen enum registry. |
| `contracts/wizard-media-session/v1/valid/*.json` (new) | Shared valid lifecycle fixtures. |
| `contracts/wizard-media-session/v1/invalid/*.json` (new) | Unknown field, bounds, hash, epoch, and privacy-negative fixtures. |
| `tests/wizard/test_media_session.py` (new) | Strict schema, auth, deduplication, stale/session conflict, epoch, restart, and privacy tests. |
| `tests/wizard/test_performance_scheduler.py` (new) | Pause/buffer/seek/rate/drift/freshness/reconnect/neutral and accessibility behavior with fake monotonic time. |
| `tests/wizard/test_performance_score.py` (new) | Atomic publication, digest/package mismatch, immutable revision, failed-write rollback, and corrupt pointer handling. |
| `tests/wizard/test_media_session_server.py` (new) | Real FastAPI route tests for body limit, content type, Origin rejection, constant-time token behavior at the observable boundary, and sanitized errors. |
| `tools/verify_prism_media_connector.py` (new) | End-to-end evidence driver that launches/targets both local services, exercises a deterministic media trace, and writes machine-readable drift/reconnect evidence without transcript content. |

Do not modify `wizard_avatar/commanding.py`, `control.py`, or the existing WebSocket protocol to fit media playback. Shared protocol fixtures in this repo are canonical; Prism keeps an identical vendored copy and a parity test compares the manifest SHA-256.

### 13.2 PrismGT

| File | Change |
|---|---|
| `crates/prism-cdiss-cli/src/media_connector.rs` (new) | Connector config parser, loopback URL validator, relay client, body/type models, bounded latest-snapshot relay, retry-independent ACK mapping, sanitized status, and unit tests. |
| `crates/prism-cdiss-cli/src/audiobooks.rs` | Add optional durable metadata/performance fields, media hashing, transcript/alignment URLs, canonical URL validation hooks, whole-generation publication, and old-record compatibility. |
| `crates/prism-cdiss-cli/src/main.rs` | Declare `media_connector`; add a narrow `CliApp::record_user_approved_media_open` that writes `prism_holder_approved: true` and returns persistence failure. Do not call a model or `dispatch_role`. |
| `crates/prism-cdiss-cli/src/web.rs` | Add local media-session/status routes, Whiz grant/redirect handlers, bounded grant store and rate limit, surface gating, router tests, and connector state in `AppState`. Do not add the Wizard relay to `build_public_router`. |
| `Cargo.toml` and `crates/prism-cdiss-cli/Cargo.toml` | Add the `url` parser if not using a single already-pinned parser path; no generic browser-opening crate in the sidecar. |
| `contracts/wizard-media-session/v1/**` (new) | Vendored schema/fixtures byte-identical to Wizard, plus `MANIFEST.sha256`. |
| `src/pages/PrismDodecahedron/media/useMediaSessionConnector.js` (new) | Direct audio-element lifecycle observer, sequence/epoch/session management, 4 Hz heartbeat, one-in-flight/one-pending queue, retry/backoff, and status state. |
| `src/pages/PrismDodecahedron/media/mediaSessionProtocol.js` (new) | Frontend serialization, strict local assertions, element-to-state mapping, privacy allowlist, and fixture tests. |
| `src/pages/PrismDodecahedron/media/PlayerControls.jsx` (new) | Seek/rate/stop/track/caption/transcript/character/intensity/motion controls using the one `audioRef`. |
| `src/pages/PrismDodecahedron/media/TranscriptPanel.jsx` (new) | Searchable selectable transcript, cue seeking, follow behavior, provenance/status, and accessible semantics. |
| `src/pages/PrismDodecahedron/media/ConnectorDiagnostics.jsx` (new) | Structured sanitized status, pause/copy controls, no heartbeat live-region churn. |
| `src/pages/PrismDodecahedron/media/WhizAction.jsx` (new) | Trusted activation, grant request, one-context launch, state/error UI, and no caller-provided URL. |
| `src/pages/PrismDodecahedron/media/PerformanceEditor.jsx` (new, later wave) | Focused timeline plus semantic table, working-copy edits, validation, preview, and immutable revision save. |
| `src/pages/PrismDodecahedron/index.jsx` | Mount the connector hook against `audioRef`, expose narrowly scoped player state/actions through the store, order `ended` before auto-next, and remove caption `aria-live`. Keep the hidden media element as owner. |
| `src/pages/PrismDodecahedron/studio/StageUtilityCards.jsx` | Replace the current inline player body with the dedicated controls/panels; retain utility-card shell and existing track lists during migration. |
| `src/pages/PrismDodecahedron/musicLibrary.js` | Preserve stable media digest, external URL/provenance, transcript/alignment, timing, and performance references instead of dropping them. |
| `src/lib/media-normalize.js` | Preserve new persisted audiobook fields. Mark browser-linked MP3s `durability: "ephemeral"`, `performanceStatus: "unbound"`, and `whizAvailability: "unavailable"`. |
| `src/pages/PrismDodecahedron/index.css` | Responsive player/transcript/diagnostic/editor layouts, stable control dimensions, visible focus, AA states, 200% zoom/320 px behavior, and reduced/still presentation classes. |
| `src-tauri/src/main.rs` | Initialize the official opener plugin only for the desktop Whiz adapter. |
| `src-tauri/Cargo.toml`, `package.json` | Add matched official Tauri opener packages; add Vitest/Testing Library/Playwright development test dependencies and scripts. |
| `src-tauri/capabilities/default.json` | Permit opening only loopback `http://127.0.0.1:*` / `[::1]:*` Whiz grant paths. Do not grant arbitrary `http(s)` or file opening. |
| `vite.config.js` | Add jsdom/Vitest configuration without changing production build behavior. |
| `playwright.config.js` (new) | Chromium and WebKit projects with desktop and 320 px viewport coverage. |
| `src/pages/PrismDodecahedron/media/__tests__/*.test.jsx` (new) | Protocol, event order, seek/rate/stop, queue coalescing, retry, Whiz, transcript, keyboard, and motion tests. |
| `tests/e2e/media-performance.spec.js` (new) | Real short audio, native element events, reconnect, source change, auto-next, accessibility, and one-context Whiz flow. |

`musicMotion.js` remains responsible only for live cosmetic analysis. `createPrismHeroScene.js` and the canvas render loop must not own connector, transcript, editor, or URL-launch logic.

## 14. Delivery waves and ownership gates

### Wave 0: frozen contract and fixtures

- Commit the schema, fixtures, enums, privacy allowlist, and SHA manifest in Wizard first.
- Vendor the exact contract into Prism and make parity a test.
- Implement no UI until both validators accept/reject the same fixture corpus.

Gate: byte-identical schema/fixtures and all negative privacy fixtures rejected.

### Wave 1: Wizard ingress and scheduler shell

- Add authenticated media-session ingress, registry, neutral scheduler, freshness/restart behavior, and diagnostics.
- Integrate a neutral/resolved layer into the existing 60 Hz runtime without altering command ordering.

Gate: deterministic unit tests, auth/security tests, and no regression in the existing Wizard suite.

### Wave 2: Prism relay and real media-element wiring

- Add startup config, local-only relay, direct audio event observer, queue/backoff, and connector diagnostics.
- Add seek, rate, and stop controls against the existing element.

Gate: real browser trace proves play/pause/buffer/seek/rate/end/auto-next and process restart. Audio continues through connector failure.

### Wave 3: metadata, transcript, and Whiz

- Publish durable media generations and expose complete normalized metadata.
- Add transcript panel and governed single-use Whiz grant/redirect with both launch adapters.

Gate: URL attack corpus, audit fail-closed test, single-context test, old-record compatibility, and failed-write rollback.

### Wave 4: score inspection and focused editor

- Add read-only score/debug inspection first.
- Add semantic-table/timeline editing and immutable revision publication after scheduler acceptance is stable.

Gate: original score remains recoverable, invalid edits cannot become current, keyboard-only edit path passes, and preview uses the production element/connector.

### Wave 5: enablement

- Ship flags off, collect local evidence, then enable for internal desktop/local users.
- Public Wizard connector remains absent.

Gate: all acceptance thresholds below, signed evidence bundle, and rollback drill.

## 15. Test matrix and release evidence

### 15.1 Contract/security

- Identical valid/invalid fixture result in JavaScript, Rust, and Python.
- Unknown fields, NaN/infinity, oversized strings/body, control characters, invalid hashes, unsupported enums/rates, and impossible epochs fail closed.
- Browser direct-to-Wizard, missing/wrong token, Origin-bearing requests, redirects, proxy use, DNS hostnames, and non-loopback connector URLs fail.
- Snapshot/log/diagnostic property tests prove absence of transcript/caption/title/path/URL/token/provider-key fields.
- Public router has no Wizard relay route and a hosted browser cannot trigger localhost fetches.

### 15.2 Playback lifecycle

- Load metadata, play intent, playing, pause/resume, waiting/stalled/recovery, forward/backward seek, rapid scrub, rate changes, duration change, stop, ended, auto-next, source replacement, decode error, background/foreground, pagehide.
- Event sampling is compared to the real element at handler time, not React state.
- Four-Hz heartbeat uses fake timers in unit tests and a real media element in browser tests.
- Queue never exceeds one in flight plus one pending under a delayed/failing relay.
- Connector failure never mutates element source/time/rate/paused/volume.

### 15.3 Reconnect and timing

- Restart Wizard mid-play, restart Prism sidecar mid-play, drop 1/5/20 consecutive heartbeats, and open a competing tab.
- New runtime epoch forces immediate full resync; no historical replay.
- Old session/sequence/epoch packets cannot reclaim control.
- Steady-state measured drift target: p95 <=50 ms and maximum <=100 ms after warm-up.
- Seek/reconnect target: scheduler reaches <=100 ms error within 500 ms.
- Stale >1.5 s begins no new semantic cues; stale >5 s is neutral and releases controller.

### 15.4 Metadata/storage/editor

- Same bytes produce same `mediaSha256`; changed bytes invalidate timing/score pointers.
- Process interruption at every publication step leaves either old complete or new complete generation, never a mixed record.
- Old `AudiobookTrack` JSON loads with new optional fields absent.
- Linked blob media stays unbound and cannot inherit a score or canonical link by title.
- Invalid editor save leaves current score unchanged; valid save advances one revision atomically; rollback restores prior pointer without deleting evidence.

### 15.5 Whiz

- Missing, malformed, relative, credentialed, whitespace/control, custom-scheme, `file`, `blob`, `data`, and `javascript` URLs are unavailable.
- A caller-supplied URL field is rejected and cannot influence redirect.
- Synthetic `.click()`, duplicate activation, grant replay, expiry, media mismatch, changed URL hash, and audit failure do not open.
- Pointer and keyboard activation open exactly one system-browser context to the validated destination and do not alter playback.
- Raw URL/query/title never appears in ledger, application log, or returned error.

### 15.6 Accessibility

- Keyboard-only player, transcript, diagnostics, Whiz, and editor pass in Chromium and WebKit.
- Automated axe scan plus manual VoiceOver pass.
- 200% zoom, 320 px width, high contrast, visible focus, and 44 px primary targets.
- Captions are not implicitly double-spoken.
- Reduced and still profiles disable every prohibited channel within 250 ms without audio restart.
- Flash-rate runtime and score-validation gates are tested independently.

Evidence bundle contains protocol fixture results, test reports, sanitized lifecycle trace, drift histogram, restart trace, accessibility report, URL attack results, and rollback drill. It contains no media text or secrets.

## 16. Feature flags and rollback

Flags:

- Prism server: `PRISM_WIZARD_CONNECTOR_ENABLED` (default off).
- Prism frontend capability response: `wizardMediaConnector`, `performanceEditor`, and `whiz` are independently reported; UI does not guess from environment.
- Wizard: media-session route may be registered but returns `503 unavailable` unless the connector token and feature flag are valid.
- Editor: internal-only flag until immutable revision and accessibility gates pass.

Deployment order is Wizard first, Prism second, both disabled. Enable Wizard ingress, verify neutral snapshots, enable Prism connector for internal users, then enable score execution. Whiz and editor can roll independently.

Rollback procedure:

1. Disable `PRISM_WIZARD_CONNECTOR_ENABLED` and restart Prism. Player, captions, transcript, and existing visualizer continue; connector status becomes unavailable.
2. If required, disable Wizard media-session handling. Prism retries then settles into degraded/neutral without touching audio.
3. Roll back the Prism code commit independently. New optional JSON fields in legacy records are ignored by older readers; existing root-layout tracks remain available. Generation-only tracks may be temporarily hidden from the old binary but are preserved. Do not delete user media or generation directories.
4. Roll back the Wizard code commit independently. Preserve all score generations and `current.json`; no destructive migration is required.
5. For a bad score/editor release, atomically repoint Wizard `current.json` to the previous validated revision and update Prism's additive pointer/status. Never overwrite or delete the rejected revision during incident response.
6. Revoke any in-memory Whiz grants by restarting the Prism sidecar; no durable standing grant exists.

Rollback must not restore caption timer-driven performance, route media through generic Wizard commands, loosen URL validation, expose the connector publicly, or delete audit evidence.

## 17. Definition of done

This synthesis is implemented only when all of the following are true:

- The one existing PrismGT audio element remains the only media clock and all lifecycle cases are covered.
- JavaScript, Rust, and Python enforce the same frozen V1 fixture contract.
- Browser-to-Prism and Prism-to-Wizard authentication boundaries pass adversarial tests.
- Seek, pause, buffer, rate, source change, reconnect, and restart reconstruct deterministically within the stated thresholds.
- Connector failure cannot alter or interrupt playback.
- Durable media identity binds exact audio, timing, score, and character package hashes.
- Whiz can open only the stored validated canonical URL from one explicit user activation, with a content-free signed approval record and one browser context.
- PublicWeb has no path to a user's local Wizard service.
- Transcript, controls, diagnostics, reduced/still motion, and editor alternatives pass the accessibility gates.
- Both repositories can roll back independently without data deletion or schema repair.

That boundary gives PrismGT a real media connector rather than a visualizer side effect, and gives Wizard a reconstructable performance clock rather than a stream of brittle commands.
