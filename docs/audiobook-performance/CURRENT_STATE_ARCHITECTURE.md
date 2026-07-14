# Wizard Joe Audiobook Performance Engine: Current-State Architecture

Status: frozen implementation baseline
Audit date: 2026-07-13
Python branch baseline: `codex/audiobook-performance-engine` from `7781a67c97bfbfa16a64d5b9fb12bdf74bd4c032`
PrismGT baseline: `desktop/prism-gt-influence-integrated` at `0ce9f9bae665b1415cd776e4d6c9ee23565936ac`

This document is the required code-grounded architecture gate. Production work for the audiobook and music performance system begins only after this baseline and the program tracker exist.

## Repository Boundaries

| System | Root | Responsibility |
| --- | --- | --- |
| Wizard Joe Python | `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar-python` | ASCILINE square-cell character, deterministic semantic runtime, commands, rendering, browser visualization |
| PrismGT | `/Users/paul/Documents/Codex/2026-06-28/jedisherpa-prism-geometry-talk-https-github/work/prism-geometry-talk-current` | Media library, audiobook storage/generation, audio playback, captions, browser audio analysis, governed application UI |

The Python engine remains the character-performance authority. PrismGT remains the media playback and product-shell authority. The connector must not duplicate either runtime or introduce Rust into the Python animation implementation.

## Live Python Runtime

- Persistent LaunchAgent: `com.jedisherpa.wizardjoeavatar`.
- Live endpoint: `http://127.0.0.1:8765/`.
- Listener: Python process on `127.0.0.1:8765`.
- Startup: `.venv/bin/python tools/run_wizard_avatar_server.py --port 8765`.
- Runtime dependencies: FastAPI, Uvicorn, Pillow; Python 3.9+.
- Character package: `wizard_avatar/definitions/wizard_joe_character_package.json`.
- Pose library: 89 validated square-cell poses.
- Animation graph: `reference_avatar_animation_graph_v2.json`, authored at 24 FPS with 60 Hz simulation semantics.

### Execution path

1. `tools/run_wizard_avatar_server.py` constructs `ProceduralWizardFrameSource` and the FastAPI app.
2. `wizard_avatar/server.py` exposes REST commands, an ordered command endpoint, diagnostics, and `/ws/avatar/wizard`.
3. `wizard_avatar/stream.py::WizardFrameHub` owns the running task, ordered inbox, replay log, subscribers, and presentation cadence.
4. `wizard_avatar/runtime.py::AvatarRuntime` is the single-writer 60 Hz fixed-tick semantic runtime.
5. `wizard_avatar/controller.py::WizardAvatarController` applies locomotion, action, expression, speech, pose, control-lease, and Prism semantic inputs.
6. `wizard_avatar/frame_source.py` selects the authored pose, applies facial channels and overlays, projects it into the stage, and emits ASCILINE cell frames.
7. The browser decodes adaptive WebSocket frames and renders square cells on canvas.

### Existing control contract

The server already accepts move, path, circle, figure-eight, face, action, pose, control, Prism signal, expression, speak, speech-stop, stop, and reset commands. The ordered endpoint wraps commands in `CommandEnvelopeV1`, providing source identity, monotonic sequence, epoch, priority, TTL, lease, deterministic apply tick, acknowledgement, deduplication, and replay evidence.

### Existing character capabilities

- Ground and flight locomotion.
- Authored actions and pose showcase.
- Speech mouth overlay and expression channels.
- Semantic visual advice through Prism signals.
- Deterministic command replay and frame-hash diagnostics.
- Character package boundary with pose library, animation graph, renderer, default pose, and capability list.

### Current limitations

- No media session, transcript, narrative score, music score, or cue scheduler schema.
- Speech is duration/text driven, not aligned to an authoritative audio clock.
- Pose overrides are timer based and commands are issued one at a time.
- The demo repeat loop is browser-local and random; it is not an editorial performance system.
- Facial overlay support is pose-anchor dependent and needs capability-aware fallbacks.
- The package does not yet declare per-pose performance tags, facial support, transition costs, or multi-character voice/style profiles.
- No persisted, editable, provenance-bearing score cache.
- No media ingestion, local transcription, alignment, DSP analysis, or media privacy audit.

## PrismGT Media Runtime

### Media player path

- Primary component: `src/pages/PrismDodecahedron/index.jsx`.
- Authoritative browser clock: `audioRef.current.currentTime` on the real HTML audio element.
- Playback control: `loadTrackIntoAudio`, `playAudioElement`, `playTrackNow`, `togglePlayback`, track selection, and ended handling.
- Playlist sources: `/api/library`, `/music/playlist.json`, ElevenLabs audiobook APIs, and browser-local linked MP3 object URLs.
- Captions: fetched VTT/SRT, parsed by `src/lib/captions-vtt.js`, selected against `audioMetrics.currentTime`.
- Audio analysis: `createAudioMotionController` in `musicMotion.js` uses Web Audio `AnalyserNode` and reports level, bass, mids, treble, transient, pulse, playback time, and duration.
- UI: `MusicPanel.jsx` and the audiobook/player utility surfaces.

### Media storage and APIs

- Rust web routes in `crates/prism-cdiss-cli/src/web.rs` expose `/api/library`, `/api/audiobooks`, generated audio, captions, deletion, and media file serving.
- `crates/prism-cdiss-cli/src/audiobooks.rs` stores audiobook metadata, audio, and optional captions under the configured application data directory.
- Hosted media uses `PRISM_MEDIA_ROOT`, with `library.json` and media beneath `/var/lib/prism-gt/media` in the documented deployment.
- The repository contains real podcast/story audio, transcripts, captions, and metadata suitable for deterministic fixtures.

### Current limitations

- No versioned Wizard Joe connector or media-performance session protocol.
- React component state is the only source of player event snapshots; no normalized external event bus exists.
- Browser analysis is visual-reactivity oriented, not an offline deterministic music score.
- No performance score URL, hash, generation status, edit history, or character selector in media metadata.
- Local uploads use object URLs and are intentionally session-local; they must never be silently uploaded.
- No governed Whiz action tied to a canonical stored URL.

## Integration Boundary

The first implementation uses a versioned HTTP/WebSocket connector that works in local web mode and can later be hosted behind separate ingress endpoints. It must preserve the HTML audio element as the authoritative clock.

PrismGT publishes normalized media-session commands and clock snapshots from both its main media player and its TTS/speaker element. Python loads or generates a deterministic score, schedules cues against the reported media time, and renders performance state. Audible TTS temporarily takes performance priority and hands back to the latest main-player snapshot when it ends. Python never starts an independent wall-clock performance when connected to PrismGT. On seek or reconnect it derives the complete state from the score and current media time rather than replaying missed UI events.

Required connector properties:

- Explicit session open/close and immutable media identity.
- Schema version, message ID, source sequence, session epoch, media hash, score hash, and character ID.
- Play, pause, seek, rate, ended, heartbeat, and unload events.
- Periodic authoritative `current_time_ms` snapshots while playing.
- Idempotent commands, bounded queues, reconnect handshake, and stale-session rejection.
- Localhost allowlist by default; configurable explicit origin allowlist for hosted deployment.
- No media bytes cross the connector unless the user explicitly selects analysis/import.
- Debug visibility for connection, drift, last event, active cue, score provenance, and fallback state.

## Target Data Flow

```text
PrismGT media metadata + user-selected local media
        |
        +--> transcript/captions ingest or local transcription
        +--> deterministic audio feature extraction
        |
        v
MediaAssetV1 + TranscriptV1
        |
        +--> NarrativeScoreV1 / MusicScoreV1 (cached, editable, provenance-bearing)
        |
        v
PerformanceSessionV1 + authoritative PrismGT clock
        |
        v
Cue scheduler -> existing ordered command/runtime channels
        |
        v
ASCILINE pose, locomotion, expression, eye, mouth, staff, wing, stage movement
        |
        v
WebSocket cell stream + diagnostics + replay/quality evidence
```

## Dependency Baseline

- Present: Python 3.9.6, FastAPI, Uvicorn, Pillow, `ffmpeg`, `ffprobe`, Node 24.
- Not present as a command: Whisper.
- Policy: transcription is an optional local capability with an explicit availability state. Existing captions/transcripts are preferred. No cloud transcription or upload may occur without explicit user action and a visible destination.

## Test and Evidence Baseline

- Existing Python suite covers command ordering, runtime determinism, streams, poses, animation channels, locomotion, semantic mapping, square rendering, and production wiring.
- The coordinator's complete baseline run passed 171 tests. QA separately reproduced the isolated stream-deadline failure in 3/3 runs, so the timing inconsistency remains tracked rather than hidden.
- PrismGT has build, media manifest validation, Rust tests, and browser-facing media fixtures, but no connector contract tests yet.
- Completion requires deterministic score fixtures, scheduler tests, media-clock drift/seek/reconnect tests, privacy tests, schema tests, browser screenshots, live playback evidence, and replay artifacts.

## Non-Negotiable Decisions

1. Audio time is authoritative.
2. Scores are deterministic, cached by content and configuration hashes, editable, and provenance bearing.
3. Local media stays local unless the user explicitly chooses an upload/import action.
4. The connector never falls back to an untracked random pose loop.
5. Unknown capabilities degrade visibly and safely.
6. Whiz opens only a canonical stored `http` or `https` URL after an explicit click; missing or invalid URLs disable the control.
7. Character-specific behavior enters through versioned package capabilities and profiles, not Wizard Joe conditionals in the scheduler.
8. The existing Rust-backed PrismGT product is an integration peer, not a replacement for the Python ASCILINE animation engine.
