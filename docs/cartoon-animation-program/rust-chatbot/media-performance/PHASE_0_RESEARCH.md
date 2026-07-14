# Phase 0 Research Synthesis

Date: 2026-07-13

## Evidence Boundary

Wizard Joe was audited on branch `codex/rust-chatbot-animation-engine` at
`375ff4c68383e34e04377cca9f69862b5a5e83b7`. PrismGT was audited in an isolated
worktree on branch `codex/wizardjoe-media-performance` at
`4ec50226e964fcd078dd846c73a1862778e95b09`.

The Wizard audit was source-grounded because no local process was listening on
port 8787 during the specialist pass. PrismGT source findings were supplemented by
inspection of the installed `/Applications/Prism GT.app`, whose bundled Rust
service answered `/api/health` on loopback. The installed app is older than current
source and is not evidence that new source behavior is live.

No specialist changed tracked files during research.

## Report A: Rust Runtime And Animation Capability

### Evidence

- `rust/wizard_avatar_engine/src/main.rs` starts the Rust server.
- `hub.rs` owns one 60 Hz simulation authority and a separate render producer.
- `renderer.rs` and `web/canvas_renderer.js` render and scale colored cells; they
  do not play PNG character frames.
- `pose.rs` validates the 89-geometry pose authority, eight facings, regions,
  anchors, attachments, effects, and contacts.
- `controller.rs` currently drives movement, facing, paths, clips, expression,
  actions, and duration-based speech.
- `chat_event.rs`, `chat_performance.rs`, `chat_inbox.rs`, `state_regions.rs`,
  `motion_graph.rs`, and `motion_director.rs` contain the typed future runtime
  contracts, but not all are wired into production ingress and rendering.

### Current Findings

Implemented and visible now:

- deterministic fixed-step simulation;
- procedural colored-cell rendering;
- 89 validated pose geometries;
- active movement in eight facings with contact-aware gait deformation;
- authored pose clips and layered expression/action/speech/effect channels;
- ten expressions and seven rendered mouth shapes;
- basic periodic blink and duration-driven mouth motion;
- REST and WebSocket command transport plus adaptive frame streaming.

Present but not production-active:

- 27 typed chat lifecycle events;
- 14 semantic visemes, typed emotion, gesture, attention, and gaze intent;
- bounded ordered command inbox, regional ownership, and replay contracts;
- versioned motion graph and deterministic motion director;
- richer locomotion candidates now accepted separately under ANIM-050.

Absent or insufficient:

- media session/timeline contract;
- score schema, scheduler, and stale-cue invalidation;
- phoneme-aligned narration lip sync;
- gaze/saccade/head-target rendering;
- non-periodic blink policy;
- professional hand-arc and gesture preparation/recovery system;
- true flight locomotion semantics;
- beat/bar/phrase/section-aware dance choreography;
- runtime capability publication endpoint.

### Architecture Implications

The correct path is to wire the typed inbox, regional state, motion graph, and
motion director into the existing controller/runtime, then add media commands to
that same path. A parallel media animation loop would duplicate ownership and make
seek/reconnect correctness unprovable.

The capability manifest must be generated from loaded runtime authorities. It
must distinguish `active`, `shadow_validated`, and `diagnostic_only`, and must
never advertise planned animation IDs.

### Risks

- Hard-coded clips, legacy animation data, and the shadow graph are competing
  sources of truth.
- Passing isolated contract tests can be mistaken for production wiring.
- Direct raw pose commands bypass semantic policy.
- Front-heavy pose coverage limits some multi-direction acting.
- Whole-pose interpolation can produce rubbery transitions without authored
  contact and hand-path constraints.

### Recommendation

Use layered ownership for root/contact locomotion, torso and weight, phrase
gesture, head/gaze, face/emotion, viseme, blink, and secondary motion. Audiobook
gesture peaks should align to semantic accents, with anticipation and recovery;
music should use phase-continuous motion plus sparse accents instead of swapping a
pose on every beat.

### Rejected Alternatives

- PNG/video character playback;
- browser-authoritative animation timing;
- Python animation authority;
- direct LLM-issued pose IDs;
- random gestures or periodic eye motion;
- relabeling existing social clips as invented dance capabilities.

## Report B: PrismGT Media, Governance, And Connector Surface

### Evidence

- `src/pages/PrismDodecahedron/index.jsx` owns one hidden
  `HTMLAudioElement`, playlist state, controls, audiobook UI, and CDISS streaming.
- `musicLibrary.js` normalizes bundled music metadata.
- `musicMotion.js` reads WebAudio FFT/RMS/flux data during animation frames.
- `crates/prism-cdiss-cli/src/audiobooks.rs` durably stores generated/imported
  audiobook audio, metadata, VTT, and alignment beneath app data.
- `crates/prism-cdiss-cli/src/web.rs` exposes audiobook and governed chat routes.
- `crates/prism-cdiss-cli/src/voice.rs` already invokes local `whisper-cli` and
  `ffmpeg` through a blocking subprocess boundary.
- `src-tauri/src/main.rs` supervises a loopback Rust sidecar and opens its HTTP UI;
  HTTP/SSE, not Tauri invoke, is the desktop IPC boundary.

### Current Findings

- The media element's `currentTime`, `duration`, paused/ended state, and rate are
  the honest decoded-playback observations.
- Current play/pause and track-selection behavior mutates React/media-element
  state directly; there is no application-level ordered media event contract.
- Seek, playback-rate control, runtime chapters, resume position, and video are
  not implemented in the audited player.
- WebAudio metrics are useful modulation signals but are not a stable score or
  authoritative clock.
- Audiobook metadata is richer in Rust than in the frontend; normalization drops
  several provenance and duration fields.
- There is no canonical external-source URL model and no generic governed
  external-link action. The existing governed X publication path demonstrates
  approval and payload-hash patterns but cannot simply be bypassed or mislabeled.
- Current audiobook range responses read the whole file before slicing, which is
  unsuitable for long media.
- CDISS stage SSE already carries expression, mouth, energy, stage, and elapsed
  time, but the frontend discards most semantic fields.

### Architecture Implications

PrismGT needs a Rust-owned media-session domain plus a browser adapter. The browser
reports acknowledged observations from the media element with monotonic sequence
numbers. Rust validates ordering, persists media/session metadata, and relays a
versioned snapshot/event stream to Wizard through its command inbox.

Desktop and hosted-capable behavior should share HTTP/SSE/WebSocket contracts;
Tauri-only IPC would create two products.

### Risks

- Server wall time drifts from buffering, decoder state, seeks, and rate changes.
- DOM/RAF-only inference cannot guarantee ordering or reconnect recovery.
- Remote media can produce unusable analyzer data without correct CORS headers.
- A generic `window.open` implementation would bypass action governance.
- Whole-file reads make long audiobooks and video memory-unsafe.

### Recommendation

Add a correlated media-session controller, explicit observed-state snapshots,
file-backed range streaming, preserved provenance, and a governed `source.open`
action. Feed semantic CDISS state and audio-analysis features to Wizard as
separate typed inputs; FFT values may modulate authored choreography but may not
select arbitrary poses.

### Rejected Alternatives

- server wall clock as media authority;
- RAF/DOM events as the sole connector;
- Tauri invoke as the only integration path;
- direct FFT-to-pose mapping;
- Wizard opening links or executing governed actions independently.

## Dependency Research

- Symphonia is a pure-Rust audio decoding/demuxing framework. Version 0.6 requires
  Rust 1.85, while PrismGT currently declares Rust 1.75, so selecting latest would
  silently change the workspace MSRV. Source: https://docs.rs/symphonia/latest/symphonia/
- `whisper.cpp` is MIT-licensed and its maintained CLI supports JSON/full JSON,
  VTT, SRT, word splitting, probability thresholds, offsets, durations, language
  detection, and token-level timestamp options. Sources:
  https://github.com/ggml-org/whisper.cpp and
  https://github.com/ggml-org/whisper.cpp/tree/master/examples/cli
- The `whisper-rs` repository referenced by upstream was archived in 2025. Adding
  it as the primary production boundary would create unnecessary FFI and
  maintenance exposure when PrismGT already has a tested subprocess seam.
- RustFFT is pure Rust, SIMD-capable, and MIT/Apache-2.0. It is appropriate as a
  deterministic DSP primitive, not a complete beat/section-analysis solution.
- aubio provides mature onset/beat/tempo algorithms, but is GPL-3.0 and its latest
  upstream release is old. Embedding it would create license and maintenance
  concerns for the Apache-2.0 PrismGT workspace.

## Synthesis Decision

Proceed with the smallest two-repository architecture:

1. Wizard publishes a generated capability manifest and accepts versioned media
   timeline/score commands through its existing inbox.
2. PrismGT adds durable media identity and a media-session controller around the
   current player.
3. A Rust preprocessing binary in PrismGT orchestrates decoding, provided-transcript
   parsing, transcript verification/alignment, deterministic DSP, optional governed
   LLM analysis, score compilation, validation, caching, and resume. When the user
   explicitly opts in, its managed transcription client invokes the inventoried
   Whisper installation on `root@5.78.137.112` under the documented transfer,
   retention, deletion, and audit contract.
4. PrismGT sends score identity and authoritative observed media snapshots; Wizard
   preloads the validated score and samples it deterministically at simulation
   ticks.
5. Whiz uses a new governed source-open action bound to stored canonical metadata.

This is an architecture decision, not a completion claim.
