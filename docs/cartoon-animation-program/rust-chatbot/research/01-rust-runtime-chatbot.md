# Rust Runtime Research: First-Class Chatbot Visualizer

Role: `RUNTIME`

Date: 2026-07-13

Scope: current Rust implementation in `rust/wizard_avatar_engine`, the Rust pose compiler in `rust/wizard_avatar_pose_tool`, the copied cartoon-animation program, and the current schema-v4 pose evidence.

This report is research, not production code. It separates facts directly verified from the current working tree from proposed design decisions. The companion implementation plan is `../planning/01-rust-runtime-plan.md`.

## 1. Executive Decision

Wizard Joe should become a first-class chatbot visualizer by extending the existing Rust engine, not by recreating the copied Python architecture. The Rust engine is already the strongest implementation surface in this repository: it owns procedural cell geometry, a deterministic controller, a 60 Hz simulation path, pose clips, interruption and restoration, an adaptive cell codec, an Axum HTTP/WebSocket server, browser presentation, and the schema-v4 pose library.

The copied documents remain useful requirements research, especially their command-envelope, orthogonal-state, replay, transport, and evidence ideas. Their Python-only clauses are obsolete for this project and are explicitly superseded in Section 5.

The target architecture is one Rust authority:

```text
chatbot / TTS / UI / automation
    -> typed semantic chat event adapters
    -> ordered, idempotent command inbox
    -> deterministic 60 Hz Rust runtime
    -> orthogonal state regions and behavior arbitration
    -> pose/clip/transition evaluator using 89 runtime geometries
    -> procedural direct-cell renderer
    -> adaptive ASCILINE frames plus typed control events
    -> HTTP and WebSocket clients
```

Reference PNGs remain offline compiler inputs and visual evidence only. The runtime must never load or composite them.

## 2. Research Method and Confidence Labels

The following labels are used throughout:

- **Verified current fact**: observed directly in current source, embedded assets, or generated evidence.
- **Observed but not re-executed**: present in tests/evidence, but not freshly run because this assignment permits read-only inspection commands only.
- **Proposal**: recommended future behavior, module, API, metric, or workflow.

No build, test, server, or evidence-generation command was run for this report. The shared worktree contains concurrent uncommitted pose-v4 work, so this report does not claim that the current suite is green.

## 3. Verified Current Baseline

### 3.1 Pose library and evidence

| Fact | Evidence | Status |
|---|---|---|
| The embedded imported asset is schema v4. | `rust/wizard_avatar_engine/assets/wizard_pose_library.v4.json.gz`; `pose_asset.rs` requires schema `4` and compiler `wizard-avatar-pose-tool-rust-v4`. | Verified current fact |
| The imported archive contains 79 unique geometries and one catalog alias across 80 catalog records. | Embedded v4 JSON and `evidence/pose-library-expansion/rust-v4/admission-ledger.json`. | Verified current fact |
| The runtime pose library contains 89 unique geometries. | 10 baseline pose IDs in `pose_program.rs` plus 79 imported geometries; static census reports `catalog_frames: 89` and `unique_geometry_count: 89`. | Verified current fact |
| Fifty unique WJFL poses are integrated. | Embedded v4 JSON contains 50 `WJFL-*` geometries; the admission ledger records `WJFL-01..40` and `WJFL-51..60`. | Verified current fact |
| The embedded v4 geometries declare 621 directed authored transition neighbors. | Sum of `motion.authored_transition_neighbors` in the embedded v4 JSON. | Verified current fact |
| Runtime geometry is direct cell data, not source PNG paths. | `pose_asset.rs` embeds compressed JSON and converts cells into `PoseDefinition`; `archive_compile.rs` asserts serialized output contains no `.png`. | Verified current fact |
| Serial admission and deterministic hashes are represented. | `compile_archive_with_admission_trace`, `pose_promote_main.rs`, and the v4 admission ledger. | Observed but not re-executed |
| Exhaustive transition and WJFL clip quality tests exist. | `tests/future_pose_transitions.rs`, `tests/wjfl_clip_quality.rs`, and `pose_evidence_main.rs`. | Observed but not re-executed |

The important count distinction is:

```text
10 baseline runtime geometries
+ 79 imported v4 geometries
= 89 runtime geometries

80 imported catalog records
- 1 alias record
= 79 imported geometries

50 of the 79 imported geometries are WJFL poses
```

### 3.2 Runtime ownership and timing

**Verified current facts:**

- `runtime.rs` defines `AvatarRuntime`, `RuntimeSnapshot`, tick scheduling, and `SimulationAccumulator`.
- `AvatarRuntime::step_tick()` applies due commands, advances `WizardAvatarController`, increments the runtime tick, and publishes previous/current state.
- The controller advances at `SIMULATION_HZ = 60.0` and `SIMULATION_DT = 1.0 / 60.0`.
- `hub.rs` creates one runtime behind `Arc<RwLock<_>>`, runs simulation independently from rendering, and samples a snapshot for each rendered frame.
- Render production uses a fixed presentation interval and does not call the controller directly.
- Catch-up is bounded to eight steps per accumulator advance.

**Limitation:** the current accumulator stores floating-point seconds. The copied first-principles plan's integer nanosecond accumulator is stricter and should be adopted in Rust to eliminate platform-sensitive fractional accumulation from replay-critical scheduling.

### 3.3 Current semantic state and animation channels

**Verified current facts:**

- `WizardState` contains world position, velocity, eight-way facing, locomotion, action, expression, mouth shape, gait phase, contacts, pose transition state, clip state, staff/effects state, speech ID/deadline, projection, simulation tick, and channel generations.
- `AnimationChannels` independently tracks upper body, staff, expression, speech, and effects through generation counters, expiry ticks, restoration targets, and smooth-step blends.
- `PosePlayback::interrupt` and `PoseClipPlayback` support replacement, restoration, looping, and direction-aware return.
- Sixteen Rust pose clips currently exist, including ground, flight, staff, reaction, conversation, WJFL movement, WJFL social, and WJFL feeling sequences.
- Current expression vocabulary has ten values. Current mouth vocabulary has seven shapes.
- Current speech behavior starts a duration, opens the mouth to a fallback shape, optionally owns the explain channel, and restores an expression-derived mouth after expiry.

**Limitations:**

- State is mostly one flat struct rather than typed orthogonal regions with explicit owners and priorities.
- Speech has no lifecycle beyond active/inactive duration, no text/audio alignment contract, no phoneme/viseme timeline, no pause/cancel semantics, and no audio clock reconciliation.
- Emotion and gesture are direct commands or fixed clip choices, not deterministic policy outputs from semantic chat events.
- `pose_clip` content proves reachability and movement, but it is not yet a chatbot behavior-selection layer.

### 3.4 Commands and arbitration

**Verified current facts:**

- `WizardCommand` is `{ type: String, payload: serde_json::Value }`.
- `AvatarRuntime::schedule_command` assigns a local insertion order and applies commands by scheduled tick then insertion order.
- HTTP routes and WebSocket text messages both reach the same hub/runtime/controller.
- Command results include `ok`, `message`, and the resulting state.

**Limitations:**

- No schema version, command ID, source ID, source sequence, TTL, requested tick, or server sequence exists.
- No duplicate-command cache or exactly-once mutation guarantee exists.
- No typed rejection code or terminal acknowledgement is sent for WebSocket commands.
- HTTP compatibility routes directly build string commands; they do not pass through a versioned envelope adapter.
- There is no bounded command inbox policy, source lease, or channel-specific priority arbitration.

### 3.5 HTTP, WebSocket, frame fanout, and browser

**Verified current facts:**

- `server.rs` uses Axum and exposes state, movement, path, action, expression, speech, stop/reset, and ASCILINE WebSocket routes.
- WebSocket startup sends an `INIT` line, then a full bootstrap frame, then ordered binary adaptive frames.
- Sequence gaps or subscriber lag trigger subscriber-local bootstrap/resynchronization.
- `AvatarFrameHub` uses a bounded Tokio broadcast channel and tracks epoch, frame sequence, simulation tick, subscriber count, keyframe state, and frame diagnostics.
- The browser receives binary direct-cell frames; presentation is separate from simulation.

**Limitations:**

- One WebSocket multiplexes binary frames and unacknowledged JSON commands without a typed control-message protocol.
- There is no explicit capability negotiation for semantic chat events, acknowledgements, snapshots, telemetry, or replay watermarks.
- Slow-subscriber and resync behavior exists, but command latency and accepted-to-visible lineage are not first-class metrics.

### 3.6 Replay and telemetry

**Verified current facts:**

- The repository has deterministic evidence/replay machinery, exact render-clock helpers, frame hashes, transition matrices, static census, snapshots, performance evidence, and soak binaries.
- Hub diagnostics expose a useful but small live diagnostic surface.

**Limitations:**

- Replay is not an always-available runtime protocol contract.
- Accepted commands, acknowledgements, semantic state hashes, behavior decisions, speech events, viseme samples, transition reasons, and rendered-frame lineage are not recorded in one canonical log.
- Telemetry does not yet expose bounded histograms/counters for command admission, speech lateness, event coalescing, interruption, fallback, resync, queue pressure, or state-to-frame latency.

## 4. First-Principles Requirements for a Chatbot Visualizer

A chatbot visualizer is not a pose carousel. It is a deterministic presentation system that turns asynchronous conversational signals into coherent continuous character behavior.

The runtime must satisfy these principles:

1. **Semantic ingress, visual ownership.** Chat systems say what happened, not which raw pose to show. The Rust visualizer owns gesture, expression, clip, transition, and timing selection.
2. **One authoritative clock.** All deadlines, gesture phases, interruption windows, visemes, blinks, and transition markers are integer 60 Hz ticks.
3. **Orthogonal regions.** Listening posture, locomotion, speech mouth, emotion, gesture, staff, wings, and effects may coexist when their ownership masks do not conflict.
4. **Deterministic arbitration.** The same initial state, seed, event log, asset hash, and policy hash produce the same semantic states and source frames.
5. **Idempotent ingress.** Network retries and reconnects never replay a gesture or restart speech accidentally.
6. **Speech is a lifecycle.** Queued, preparing, started, paused, resumed, cancelled, completed, and failed are explicit state transitions.
7. **Mouth timing is data-driven.** Timed visemes take precedence; deterministic text-derived visemes are the fallback; random open/close motion is not acceptable.
8. **Emotion is bounded context.** Emotion influences posture, face, gesture probability, amplitude, and recovery, but never bypasses safety, explicit user control, or interruption rules.
9. **Interruption starts from what is visible.** Replacing an action samples the currently presented pose/channel state, preserves compatible ownership, and follows an authored recovery path.
10. **Transport is an adapter.** HTTP and WebSocket map into the same typed event/command contracts. Neither transport mutates the controller directly.
11. **Evidence follows causality.** Every visible frame can be traced to accepted event IDs, runtime tick, semantic state hash, pose/transition decision, and asset/policy version.
12. **No runtime raster dependency.** PNGs may inform the offline compiler and evidence generator only. Production runtime input is validated cell geometry and metadata.

## 5. Supersession of Python-Only Documentation

This Rust plan intentionally supersedes the following copied-program rules.

| Copied rule | Rust-project replacement |
|---|---|
| Python is the sole production authority. | `wizard_avatar_engine` is the sole animation/runtime/render/transport authority. |
| Rust is historical, excluded, or a containment target. | Rust is the production implementation and required acceptance surface. |
| No Cargo command belongs in the program. | `cargo fmt`, `cargo clippy`, `cargo test`, Rust evidence binaries, and clean Rust builds are mandatory gates. |
| Port 8765 Python is the only live target. | The configured Rust endpoint is authoritative; local compatibility defaults may remain on 8787 while deployment configuration selects the public endpoint. Port numbers are configuration, not architecture. |
| Rust artifacts and evidence must be excluded from commits. | Compact Rust source, the compiled v4 cell asset, manifests, and bounded evidence summaries are required; raw frame dumps remain artifact-only. |
| Reimplement Rust ideas in Python. | Extend the existing Rust types and modules directly; no Python runtime dependency is introduced. |
| Rust test failures are irrelevant to acceptance. | Rust unit, integration, deterministic replay, transition, browser, and soak gates are release blockers. |
| Eventual Rust removal is recommended. | Rust removal is rejected. The obsolete duplicate Python authority may be deprecated only after compatibility consumers migrate. |
| FastAPI/dataclasses/Python enums define interfaces. | Serde-tagged Rust enums/structs define interfaces and JSON compatibility. |
| No Rust process may serve the browser. | Axum/Tokio serve the browser, command protocol, diagnostics, and ASCILINE WebSocket. |

Requirements that remain valid independent of language are retained: one simulation authority, strict command validation, bounded queues, 60 Hz deterministic ticks, 24 FPS default presentation, immutable render snapshots, adaptive frame compatibility, subscriber-local resync, no runtime PNGs, exhaustive visual evidence, and serial promotion with rollback.

## 6. Proposed Rust Chat Event Contract

**Proposal:** create a transport-neutral `ChatEventEnvelopeV1` with a tagged `ChatEventV1` payload.

Required event families:

```text
SessionStarted, SessionEnded
UserTurnStarted, UserTurnPartial, UserTurnCommitted, UserTurnCancelled
AssistantThinkingStarted, AssistantThinkingUpdated, AssistantThinkingEnded
AssistantResponsePlanned
SpeechPrepared, SpeechStarted, SpeechProgress, SpeechPaused,
SpeechResumed, SpeechCancelled, SpeechCompleted, SpeechFailed
EmotionHint, GestureHint, AttentionTarget, SafetyClamp
ConnectionDegraded, ConnectionRecovered
```

The envelope carries `event_id`, `session_id`, `source_id`, `source_sequence`, optional `turn_id`, monotonic source timestamp for diagnostics, TTL, requested apply tick, and a typed payload. Raw private prompt, retrieved documents, chain-of-thought, and model internals are not animation state. Adapters must reduce them to bounded visual intent before ingress.

The event-to-behavior reducer emits typed internal commands; it never emits a raw pose ID except through a diagnostic-only API.

## 7. Proposed Deterministic State Regions

**Proposal:** replace flat-state authority with regions, while preserving `WizardState` as a compatibility projection during migration.

```text
SessionRegion       connection, turn ownership, attention, degradation
MobilityRegion      grounded/flying mode, position, velocity, facing, contacts
ConversationRegion  idle/listening/thinking/responding/awaiting/cancelled
SpeechRegion        lifecycle, utterance, audio/timeline cursor, suppression
FaceRegion          base emotion, transient expression, blink, gaze
MouthRegion         viseme owner, current/previous viseme, blend, confidence
GestureRegion       selected gesture, phase, commitment, recovery policy
PoseRegion          clip, sample, pose, transition, root/contact state
PropRegion          staff ownership/contact
WingRegion          visibility, flap/bank mode and phase
EffectsRegion       typed bounded effects
ControlRegion       active leases, source watermarks, safety clamps
```

Every region has `generation`, `entered_tick`, `owner`, and `priority`. Timed state uses tick deadlines only. Rendering receives an immutable `Arc<AvatarSnapshot>`.

## 8. Proposed Speech and Viseme Model

Speech must support two input qualities:

1. **Authoritative timing:** TTS supplies word/phoneme/viseme intervals relative to audio start.
2. **Deterministic fallback:** text is tokenized by a small Rust rule set into viseme classes and durations using a policy-versioned algorithm.

Recommended compact viseme set:

```text
Rest, MBP, FV, TH, DTLN, KG, CHSH, SZ, R, A, E, I, O, U
```

The renderer may map multiple semantic visemes to the seven existing `MouthShape` values initially. This preserves a stable semantic protocol while allowing cell art to improve later.

Rules:

- Timelines are quantized to simulation ticks once at `SpeechPrepared`.
- `SpeechStarted` binds audio epoch/start time to a simulation tick.
- Late progress events advance the cursor; they do not replay elapsed visemes.
- A pause holds or eases to `Rest` according to pause length.
- Cancellation reaches `Rest` within six ticks and starts gesture recovery.
- Shush/safety suppression owns the mouth channel explicitly and is recorded.
- Emotion may alter amplitude and coarticulation, never phoneme identity or ordering.
- No runtime behavior depends on audio waveform decoding.

## 9. Proposed Emotion and Gesture Selection

Emotion should be represented as a bounded `EmotionState` with categorical primary emotion, intensity, valence, arousal, confidence, source, and expiry. It should influence selection without becoming a direct pose command.

The 20 full/close feeling geometries provide strong targets for ten emotions: joy, sadness, anger, fear, shame, disgust, surprise, pride, guilt, and love. Close/full variants should be selected by presentation context and transition compatibility, not by camera zoom or runtime raster scaling.

Gesture selection should use a deterministic score:

```text
score = semantic_match
      + emotion_match
      + conversation_phase_match
      + pose_continuity
      + contact_compatibility
      + cooldown_bonus
      - recent_repetition
      - channel_conflict
      - transition_cost
```

Ties are resolved by stable ID order plus a replay-seeded deterministic variation stream. Required policies include cooldowns, maximum gesture frequency, minimum neutral time, intensity clamps, no repeated extreme gesture, and recovery to a conversational home pose.

## 10. Proposed Interruption and Recovery

Every gesture/clip declares:

- owned regions;
- priority;
- anticipation, commit, hold, and recovery markers;
- interrupt windows;
- interruption policy;
- restoration policy;
- safe recovery clip;
- compatible speech/emotion overlays.

Interruption classes:

| Class | Examples | Behavior |
|---|---|---|
| Emergency | reset, safety clamp, disconnect stop | Immediate; clear unsafe ownership and recover to a known stable pose. |
| Turn lifecycle | user starts speaking while assistant speaks | Cancel/suppress speech mouth immediately; upper body recovers at nearest safe marker. |
| Higher priority semantic | surprise/reaction during explain | Start from presented state; preserve compatible face/mouth; route through authored neighbor. |
| Equal/lower priority | another decorative gesture | Queue, coalesce, or reject until current recovery window. |
| Duplicate/stale | retried event | Return prior ack; no state mutation. |

The existing `PosePlayback` and `PoseClipPlayback` are suitable low-level mechanisms. The missing layer is typed ownership and a policy engine deciding when and how they are invoked.

## 11. Proposed Replay, Telemetry, and Evidence

Replay should be canonical NDJSON or length-delimited JSON with a versioned header and records for event receipt, command ack, tick state, behavior decision, speech/viseme event, runtime warning, and render frame.

Canonical state hashes must exclude wall-clock timestamps and process IDs. Floats must use a specified canonical encoding; fixed-point integers should be preferred for replay-critical phases and deadlines.

Required telemetry:

- accepted, duplicate, stale, expired, invalid, unauthorized, and queue-full counts;
- event-to-apply, apply-to-state, and state-to-visible latency histograms;
- pending-command and subscriber queue high-water marks;
- simulation catch-up/dropped-time counters;
- gesture selected/rejected/interrupted/recovered/fallback counts;
- speech prepared/started/paused/cancelled/completed/failed counts;
- viseme lateness, skipped elapsed visemes, and mouth-rest latency;
- transition, attachment, contact, resync, decode, and frame-hash failures;
- active session/viewer counts with bounded cardinality.

Evidence must prove causality across event ID, command ID, accepted tick, state revision, behavior decision, pose/transition, source frame hash, encoded sequence, and browser-presented hash.

## 12. Risks and Open Decisions

| Risk or decision | Current evidence | Required resolution |
|---|---|---|
| Current v4 work is uncommitted and was not freshly tested by this agent. | Dirty shared worktree; v4 source/asset/evidence present. | Pose readiness gate must run and record exact SHA before chatbot work begins. |
| The float accumulator can diverge at boundaries. | `SimulationAccumulator` stores `f64` seconds. | Replace with integer accumulator units and compare replay hashes across cadence matrices. |
| Existing `WizardState` compatibility consumers may depend on flat fields. | HTTP state and browser diagnostics serialize it directly. | Add region state first, project old fields, remove projection only in a later protocol major version. |
| Viseme art supports fewer shapes than semantic speech needs. | Seven current `MouthShape` values. | Introduce semantic visemes now, deterministic many-to-one mapping initially, art expansion later. |
| TTS providers differ in timing vocabulary. | No current TTS timing adapter contract. | Define one provider-neutral timeline and adapters outside the runtime core. |
| Full/close feeling poses could be overused or cause visual jumps. | Feeling clip currently cycles all variants. | Add semantic selection, cooldowns, compatibility costs, and per-transition gates. |
| WebSocket binary and JSON multiplexing needs protocol clarity. | Current socket accepts both but only frames are acknowledged by sequence. | Add versioned JSON control frames and terminal acks without changing binary frame bytes. |
| Telemetry cardinality can grow without bound. | Current diagnostics are bounded by fixed fields. | Use enum labels, fixed histograms, ring buffers, and hashed/session-sampled identifiers. |
| Chat content privacy could leak into logs/evidence. | Current speak command carries text. | Record text hashes/lengths by default; make content capture explicit, opt-in, and redacted. |

## 13. Research Conclusion

The Rust project is ready for a chatbot-runtime implementation pass only after the v4 pose gate proves the integrated 89 geometries, 50 WJFL poses, and 621 authored directed transitions at a fixed commit. The pose work supplies the visual vocabulary; it does not by itself supply conversational behavior.

The recommended next layer is a typed, deterministic Rust orchestration core built around semantic chat events, idempotent command envelopes, orthogonal state ownership, speech/viseme timing, bounded emotion and gesture policy, authored interruption/recovery, canonical replay, and causal telemetry. It should extend the existing runtime/hub/server/renderer rather than replace them, and it must preserve the direct-cell, no-runtime-PNG architecture.
