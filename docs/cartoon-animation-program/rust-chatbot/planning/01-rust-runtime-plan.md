# Rust Runtime Implementation Plan: First-Class Chatbot Visualizer

Role: `RUNTIME`

Plan ID: `RCHAT-RUN`

Date: 2026-07-13

Research input: `../research/01-rust-runtime-chatbot.md` plus the copied documents under `docs/cartoon-animation-program/`.

Production target: `rust/wizard_avatar_engine` with `rust/wizard_avatar_pose_tool` as its offline cell-asset compiler.

This document is implementation-ready planning. It does not authorize production edits by this planning agent.

## 1. Outcome and Binding Decisions

The delivered system will turn typed chatbot lifecycle events into smooth, deterministic Wizard Joe behavior while preserving the existing procedural square-cell visual style, all 89 runtime geometries, all 50 WJFL geometries, all 621 authored directed transition relationships, adaptive ASCILINE streaming, and the no-runtime-PNG rule.

The following decisions are binding for this plan:

1. Rust is the sole animation runtime, pose evaluator, renderer, codec authority, and HTTP/WebSocket server.
2. Python is neither a runtime dependency nor an acceptance path. Python-only exclusions in the copied documents are superseded.
3. Chat systems emit semantic events and optional bounded hints. They do not choose raw pose IDs in production.
4. `AvatarRuntime` is the only mutating simulation owner.
5. Simulation advances in exact integer 60 Hz ticks. Presentation defaults to 24 FPS and never advances state.
6. HTTP and WebSocket are adapters into one typed inbox and return the same terminal acknowledgement contract.
7. Speech is a typed lifecycle with tick-quantized viseme timing, cancellation, recovery, and deterministic fallback.
8. Emotion and gesture selection are deterministic policy, not random pose roulette.
9. Interruption starts from the currently presented state and uses authored neighbors/recovery.
10. Existing flat `WizardState` fields and legacy routes remain compatibility projections during migration, not competing sources of truth.
11. Reference PNGs are offline compiler/evidence inputs only. The production binary consumes embedded validated cell geometry and metadata.
12. The 89/50/621 pose baseline must pass and be checkpointed before chatbot implementation begins.

## 2. Start Gate: Pose Integration Must Be Complete First

No `RCHAT-RUN-*` implementation item after `RCHAT-RUN-000` may merge until `RCHAT-GATE-P0` is `PASS` against one immutable Git commit.

### `RCHAT-GATE-P0` required facts

| Requirement | Exact acceptance |
|---|---|
| Runtime geometry census | Exactly 89 unique runtime geometries: 10 baseline plus 79 imported. |
| WJFL census | Exactly 50 unique WJFL geometries: `WJFL-01..40` and `WJFL-51..60`. |
| Imported catalog | 80 records, 79 geometries, one alias. |
| Transition census | Exactly 621 authored directed transition-neighbor relationships in the promoted v4 asset. |
| Static quality | All 89 geometries render; required anchors/regions/contacts/attachments validate. |
| Dynamic quality | Every one of the 621 authored directed transitions passes breakup, topology, contact, attachment, root, and frame continuity gates. |
| Clip coverage | Every WJFL geometry appears in a reviewed clip or declared semantic behavior path. |
| Determinism | Two clean v4 compiler runs produce identical JSON/gzip hashes and admission ledger. |
| Runtime isolation | Promoted runtime asset contains no source PNG path and production runtime performs no PNG load. |
| Checkpoint | Local and remote commit SHA, asset hash, test commands, totals, and evidence manifest are recorded. |

The current working tree contains evidence for these counts, but this RUNTIME agent did not execute tests. `RCHAT-RUN-000` must turn the observed baseline into a reproducible, pushed fact before later work begins.

## 3. Ownership and One-Writer Rules

Three coordinated lanes are assumed:

| Lane | Primary responsibility |
|---|---|
| `RUNTIME` | event/command contracts, fixed clock, state regions, speech/viseme runtime, behavior policy, replay, telemetry, transport/runtime wiring |
| `ANIMATION` | clip and transition authorship, pose taxonomy, gesture/emotion mappings, visual thresholds, visual approval |
| `WORKFLOW` | registry, gates, CI, evidence schemas, branch/checkpoint discipline, final accountability |

### 3.1 RUNTIME-owned new paths

These files are designed for parallel-safe creation by the RUNTIME implementer:

```text
rust/wizard_avatar_engine/src/chat_event.rs
rust/wizard_avatar_engine/src/command.rs
rust/wizard_avatar_engine/src/state_regions.rs
rust/wizard_avatar_engine/src/chat_policy.rs
rust/wizard_avatar_engine/src/speech.rs
rust/wizard_avatar_engine/src/replay.rs
rust/wizard_avatar_engine/src/telemetry.rs

rust/wizard_avatar_engine/tests/chat_event_contract.rs
rust/wizard_avatar_engine/tests/command_ordering.rs
rust/wizard_avatar_engine/tests/chat_state_regions.rs
rust/wizard_avatar_engine/tests/speech_timeline.rs
rust/wizard_avatar_engine/tests/chat_behavior_policy.rs
rust/wizard_avatar_engine/tests/chat_interruption.rs
rust/wizard_avatar_engine/tests/chat_replay.rs
rust/wizard_avatar_engine/tests/chat_transport.rs
rust/wizard_avatar_engine/tests/chat_multiclient.rs
rust/wizard_avatar_engine/tests/chatbot_pose_coverage.rs

rust/wizard_avatar_engine/tests/fixtures/chat/*.json
rust/wizard_avatar_engine/tests/fixtures/replay/*.ndjson
```

### 3.2 Shared conflict hotspots

Only the integration coordinator edits these paths, one work item at a time, after reviewing the producing lane's handoff:

| Path | Lock | Planned wiring item |
|---|---|---|
| `rust/wizard_avatar_engine/Cargo.toml` | `LOCK-RCHAT-CARGO` | `RCHAT-RUN-010`, then serial dependency updates only |
| `src/lib.rs` | `LOCK-RCHAT-LIB` | module exports after focused tests pass |
| `src/runtime.rs` | `LOCK-RCHAT-RUNTIME` | `RCHAT-RUN-020`, `030`, `090` |
| `src/state.rs` | `LOCK-RCHAT-STATE` | compatibility projection in `RCHAT-RUN-040` |
| `src/controller.rs` | `LOCK-RCHAT-CONTROLLER` | typed reducer bridge in `RCHAT-RUN-050` |
| `src/animation.rs` | `LOCK-RCHAT-CHANNELS` | region ownership bridge in `RCHAT-RUN-080` |
| `src/pose_clip.rs` | `LOCK-RCHAT-CLIPS` | ANIMATION-authored chatbot clips only |
| `src/pose_playback.rs` | `LOCK-RCHAT-PLAYBACK` | presented-state interruption bridge only |
| `src/hub.rs` | `LOCK-RCHAT-HUB` | `RCHAT-RUN-120` |
| `src/server.rs` | `LOCK-RCHAT-SERVER` | `RCHAT-RUN-110` |
| `src/frame_source.rs` | `LOCK-RCHAT-FRAME` | immutable region snapshot consumption only |
| `web/*` | `LOCK-RCHAT-WEB` | browser protocol/diagnostics lane, serially integrated |
| promoted v4 pose asset | `LOCK-POSE-V4` | frozen after `RCHAT-GATE-P0`; changed only through the pose workflow |

No agent may revert concurrent edits. A hotspot handoff must include base SHA, changed APIs, focused test results, and the exact coordinator wiring requested.

## 4. Target Module Architecture

```text
server.rs
  HTTP/WS parsing, auth hook, compatibility routes
      |
      v
chat_event.rs + command.rs
  strict serde contracts, validation, acknowledgements
      |
      v
runtime.rs
  integer clock, bounded inbox, dedupe, ordering, snapshots
      |
      +--> chat_policy.rs
      |      conversation -> emotion/gesture/clip intent
      |
      +--> speech.rs
      |      lifecycle -> tick visemes -> mouth intent
      |
      +--> state_regions.rs
      |      owners, priorities, generations, deadlines
      |
      +--> controller.rs / animation.rs / pose playback
      |      movement, channels, clips, transitions
      |
      +--> replay.rs + telemetry.rs
             canonical records, causal metrics
      |
      v
hub.rs -> frame_source.rs -> codec.rs -> browser
```

The renderer remains cell-based. None of the proposed modules may import a PNG decoder or open a reference-image path.

## 5. Frozen Rust Contracts

Contract changes after `RCHAT-GATE-C0` require a decision record, schema/version update, affected-test update, and all three lane acknowledgements.

### 5.1 Identifier and source types

Use validated string newtypes at the JSON boundary and opaque Rust types internally:

```rust
pub struct EventId(String);
pub struct CommandId(String);
pub struct SessionId(String);
pub struct TurnId(String);
pub struct UtteranceId(String);
pub struct OperationId(String);
pub struct SourceId(String);

pub enum SourceKind {
    Browser,
    Chatbot,
    Tts,
    Automation,
    Demo,
    System,
    LegacyAdapter,
}
```

Rules:

- IDs are 1..128 printable ASCII characters with no whitespace/control characters.
- The runtime treats IDs as opaque and never parses semantic meaning from them.
- Telemetry uses bounded source-kind labels, not raw IDs.
- Replay may include IDs; logs default to hashing session/turn/utterance IDs with a per-run salt.

### 5.2 Typed semantic chat event ingress

```rust
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ChatEventEnvelopeV1 {
    pub schema_version: u16,       // exactly 1
    pub event_id: EventId,
    pub session_id: SessionId,
    pub turn_id: Option<TurnId>,
    pub source_id: SourceId,
    pub source_kind: SourceKind,
    pub source_sequence: u64,
    pub requested_apply_tick: Option<u64>,
    pub ttl_ms: u32,               // 0..=5000
    pub event: ChatEventV1,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(tag = "type", content = "payload", rename_all = "snake_case")]
pub enum ChatEventV1 {
    SessionStarted { locale: Option<String> },
    SessionEnded { reason: SessionEndReason },
    UserTurnStarted,
    UserTurnCommitted,
    UserTurnCancelled,
    AssistantThinkingStarted,
    AssistantThinkingEnded,
    AssistantResponsePlanned { speech_expected: bool },
    ClarificationRequested(ClarificationRequestV1),
    ToolWaitStarted(ToolWaitStartedV1),
    ToolWaitEnded(ToolWaitEndedV1),
    AssistantError(AssistantErrorV1),
    CelebrationRequested(CelebrationRequestV1),
    SpeechPrepared(SpeechPlanV1),
    SpeechStarted { utterance_id: UtteranceId },
    SpeechProgress { utterance_id: UtteranceId, elapsed_ms: u32 },
    SpeechPaused { utterance_id: UtteranceId },
    SpeechResumed { utterance_id: UtteranceId },
    SpeechCancelled { utterance_id: UtteranceId, reason: CancelReason },
    SpeechCompleted { utterance_id: UtteranceId },
    SpeechFailed { utterance_id: UtteranceId, code: SpeechFailureCode },
    EmotionHint(EmotionHintV1),
    GestureHint(GestureHintV1),
    AttentionTarget(AttentionTargetV1),
    SafetyClamp(SafetyClampV1),
    ConnectionDegraded,
    ConnectionRecovered,
}
```

The five central performance-state payloads are closed, content-free contracts:

```rust
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ClarificationRequestV1 {
    pub reason: ClarificationReason,
    pub urgency: u8, // 0..=100
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ToolWaitStartedV1 {
    pub operation_id: OperationId,
    pub kind: ToolWaitKind,
    pub expected_duration_ms: Option<u32>, // when present: 1..=1_800_000
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ToolWaitEndedV1 {
    pub operation_id: OperationId,
    pub outcome: ToolWaitOutcome,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AssistantErrorV1 {
    pub code: AssistantErrorCode,
    pub recoverable: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CelebrationRequestV1 {
    pub reason: CelebrationReason,
    pub intensity: u8, // 0..=100
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ClarificationReason {
    MissingInformation,
    AmbiguousRequest,
    ConfirmationRequired,
    UnsupportedRequest,
    Other,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ToolWaitKind {
    Retrieval,
    Computation,
    ExternalAction,
    FileOperation,
    Other,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ToolWaitOutcome { Completed, Failed, Cancelled, TimedOut }

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AssistantErrorCode {
    InvalidRequest,
    UpstreamUnavailable,
    ToolFailure,
    NetworkFailure,
    RateLimited,
    SafetyBlocked,
    Internal,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CelebrationReason {
    TaskCompleted,
    MilestoneReached,
    UserSuccess,
    PositiveFeedback,
    Other,
}
```

Their canonical wire tags are `clarification_requested`, `tool_wait_started`,
`tool_wait_ended`, `assistant_error`, and `celebration_requested`. They map to
the conversation/performance states `clarifying`, `tool_wait`, `idle`, `error`,
and `celebrating`, respectively. `tool_wait_ended` applies `idle` first; a later
ordered event at the same tick may then select the next explicit state.

Validation is strict: unknown fields, unknown enum variants, invalid ranges, excessive arrays, non-finite numbers, and oversized payloads are rejected before queue admission. `OperationId` follows the same opaque 1..128 printable-ASCII rules as the other IDs. `urgency` and `intensity` are `0..=100`; a present `expected_duration_ms` is `1..=1_800_000`. `ToolWaitEnded` must correlate to the active operation and otherwise returns a stable rejection ack without changing state. These payloads cannot contain response text, clarification text, tool names, tool arguments/results, URLs, or error messages; such keys are unknown fields and must be rejected. The default request-body/control-message limit is 64 KiB; a speech plan is limited to 4,096 viseme cues and 30 minutes.

### 5.3 Internal semantic commands

Transport events reduce to commands before entering runtime state:

```rust
pub enum SemanticCommandV1 {
    ApplyChatEvent(ChatEventV1),
    SetMotionIntent(MotionIntentV1),
    StartGesture(GestureRequestV1),
    SetEmotion(EmotionRequestV1),
    PrepareSpeech(SpeechPlanV1),
    StartSpeech(UtteranceId),
    UpdateSpeechProgress { utterance_id: UtteranceId, elapsed_ms: u32 },
    PauseSpeech(UtteranceId),
    ResumeSpeech(UtteranceId),
    CancelSpeech { utterance_id: UtteranceId, reason: CancelReason },
    CompleteSpeech(UtteranceId),
    Stop(StopScope),
    Reset(ResetScope),
    Legacy(LegacyCommandV1),
    DiagnosticPose(DiagnosticPoseRequest),
}
```

`DiagnosticPose` is disabled on unauthenticated/public ingress and never emitted by chat policy.

### 5.4 Ordered, idempotent command envelope

```rust
pub struct CommandEnvelopeV1 {
    pub schema_version: u16,
    pub command_id: CommandId,
    pub source_id: SourceId,
    pub source_kind: SourceKind,
    pub source_sequence: u64,
    pub requested_apply_tick: Option<u64>,
    pub ttl_ms: u32,
    pub command: SemanticCommandV1,

    // Server assigned after validation:
    pub server_sequence: u64,
    pub accepted_tick: u64,
    pub apply_tick: u64,
    pub expires_tick: u64,
}

pub enum AckStatus {
    Accepted,
    Duplicate,
    RejectedInvalid,
    RejectedStale,
    RejectedExpired,
    RejectedUnauthorized,
    RejectedQueueFull,
    RejectedConflict,
}

pub struct CommandAckV1 {
    pub schema_version: u16,
    pub command_id: CommandId,
    pub status: AckStatus,
    pub source_sequence: u64,
    pub server_sequence: Option<u64>,
    pub accepted_tick: Option<u64>,
    pub apply_tick: Option<u64>,
    pub state_revision: u64,
    pub runtime_epoch: RuntimeEpoch,
    pub error_code: Option<CommandErrorCode>,
}
```

Ordering and idempotency rules:

- Default `apply_tick = current_tick + 1`.
- A client-requested apply tick must be between the default and `current_tick + 120`.
- Queue ordering is total and stable by `(apply_tick, server_sequence)`.
- The runtime assigns `server_sequence`; clients cannot set it.
- Exact duplicate `command_id` returns the original terminal ack and never mutates state again.
- A non-increasing source sequence is stale unless it is the exact duplicate command ID.
- The pending inbox is bounded at 1,024 commands.
- The completed-ack cache is bounded by 8,192 entries or 15 minutes of simulation ticks, whichever expires first.
- Reset/emergency stop may be assigned the earliest safe apply tick, but remains ordered and replay-visible.
- Every accepted or rejected ingress receives exactly one terminal ack.

### 5.5 Integer 60 Hz clock and runtime API

Replace floating accumulated seconds with integer units:

```rust
pub const SIMULATION_HZ: u64 = 60;
pub const MAX_CATCH_UP_TICKS: u32 = 8;
pub const UNITS_PER_TICK: u128 = 1_000_000_000;

pub struct RuntimeClock {
    last_monotonic_ns: Option<u64>,
    accumulator_units: u128,       // elapsed_ns * 60
    dropped_monotonic_ns: u64,
    catch_up_drop_count: u64,
}

impl AvatarRuntime {
    pub fn enqueue(&mut self, request: IngressRequestV1) -> CommandAckV1;
    pub fn step_tick(&mut self) -> Arc<AvatarSnapshotV1>;
    pub fn advance_wall_clock(&mut self, monotonic_ns: u64) -> RuntimeAdvance;
    pub fn snapshot(&self) -> Arc<AvatarSnapshotV1>;
    pub fn drain_runtime_events(&mut self) -> Vec<RuntimeEventV1>;
    pub fn metrics(&self) -> RuntimeMetricsSnapshotV1;
}
```

Clock rules:

- One tick costs exactly `1_000_000_000` accumulator units.
- Elapsed nanoseconds contribute `elapsed_ns * 60` units.
- At most eight ticks execute per event-loop turn.
- Excess lag is dropped deterministically, counted, and emitted as `CatchUpDropped`.
- Lease and TTL expiry run before the first resumed semantic update.
- Unit tests call `step_tick()` without sleep.
- Rendering reads `Arc<AvatarSnapshotV1>` and has no mutable runtime reference.

### 5.6 Orthogonal state regions

```rust
pub struct RegionHeader {
    pub generation: u64,
    pub entered_tick: u64,
    pub owner: RegionOwner,
    pub priority: u8,
    pub deadline_tick: Option<u64>,
}

pub struct AvatarSemanticStateV1 {
    pub schema_version: u16,
    pub character_id: String,
    pub session: SessionRegion,
    pub mobility: MobilityRegion,
    pub conversation: ConversationRegion,
    pub speech: SpeechRegion,
    pub face: FaceRegion,
    pub mouth: MouthRegion,
    pub gesture: GestureRegion,
    pub pose: PoseRegion,
    pub staff: StaffRegion,
    pub wings: WingRegion,
    pub effects: EffectsRegion,
    pub control: ControlRegion,
}
```

Required modes:

| Region | Required modes/fields |
|---|---|
| Session | disconnected, ready, degraded; session/turn IDs; attention target |
| Mobility | grounded idle/start/walk/run/stop; takeoff/hover/travel/bank/fall/land; position, velocity, facing, altitude, contacts, phases |
| Conversation | idle, listening, thinking, preparing_response, speaking, clarifying, tool_wait, error, celebrating, interrupted |
| Speech | idle, prepared, active, paused, cancelling, completed, failed; utterance ID, plan hash, start tick, cursor, suppression |
| Face | base emotion, transient expression, intensity, blink state, gaze target |
| Mouth | semantic viseme, mapped mouth shape, previous shape, blend, owner, cue index, confidence |
| Gesture | gesture ID, anticipation/commit/hold/recovery phase, marker, interrupt policy, restoration policy |
| Pose | clip/sample/pose IDs, transition ID/progress, visual root, contacts, presented-state hash |
| Staff | held/planted/guard/thrust/block/spin/raised; hand and contact |
| Wings | folded/neutral/upstroke/downstroke/glide/bank left/right; phase and visibility |
| Effects | ordered bounded effect instances with generation/deadline |
| Control | source watermarks, active mobility lease, safety clamp, queue watermark |

`WizardState` remains available as `impl From<&AvatarSemanticStateV1> for WizardState` during protocol v1. All compatibility fields are projections from regions.

### 5.7 Speech lifecycle and viseme timeline

```rust
pub struct SpeechPlanV1 {
    pub utterance_id: UtteranceId,
    pub text_hash: String,
    pub text_length: u32,
    pub duration_ms: u32,
    pub timing_source: TimingSource,
    pub cues: Vec<VisemeCueV1>,
}

pub struct VisemeCueV1 {
    pub start_ms: u32,
    pub end_ms: u32,
    pub viseme: Viseme,
    pub weight: u8,
}

pub enum Viseme {
    Rest, MBP, FV, TH, DTLN, KG, CHSH, SZ, R, A, E, I, O, U,
}

pub enum RenderedMouthPose {
    Closed,
    OpenSmall,
    OpenMedium,
    OpenWide,
    Rounded,
    Smile,
    Frown,
}

pub struct QuantizedSpeechPlan {
    pub utterance_id: UtteranceId,
    pub duration_ticks: u64,
    pub cues: Vec<QuantizedVisemeCue>,
    pub plan_sha256: [u8; 32],
}
```

The exhaustive semantic-to-render mapping is:

| Semantic viseme | `RenderedMouthPose` |
|---|---|
| `Rest`, `MBP` | `Closed` |
| `FV`, `TH`, `DTLN`, `SZ` | `OpenSmall` |
| `KG`, `CHSH` | `OpenMedium` |
| `A` | `OpenWide` |
| `R`, `O`, `U` | `Rounded` |
| `E`, `I` | `Smile` |

`Frown` is reserved for emotion-biased rest and does not replace a timed
speech viseme. One exhaustive `From<RenderedMouthPose> for MouthShape`
compatibility conversion feeds the existing renderer during protocol v1.
`MouthShape` is not used in the semantic event schema.

Rules:

- `SpeechPrepared` validates ordering, overlap policy, bounds, and hashes before admission.
- Millisecond timing is quantized once using a documented half-up rule.
- Empty cue sets use only duration-derived neutral syllable timing seeded by
  utterance ID. Production animation never receives or infers from response
  text.
- The low-confidence duration fallback is versioned and its version is in
  replay headers.
- `SpeechStarted` binds cue zero to the authoritative start tick.
- Progress may fast-forward the cursor but never replay elapsed cues.
- Pause holds for up to six ticks then eases to `Rest`; resume continues from authoritative progress.
- Cancel reaches `Rest` in at most six ticks and emits one `SpeechCancelled` runtime event.
- Complete reaches `Rest` in at most four ticks.
- Shush and safety clamps explicitly suppress the mouth channel and are replay-visible.
- Semantic visemes map many-to-one through `RenderedMouthPose`; the exhaustive
  compatibility conversion to current `MouthShape` is deterministic and
  test-covered.

### 5.8 Emotion and gesture policy

```rust
pub struct EmotionStateV1 {
    pub primary: Emotion,
    pub intensity: u8,
    pub valence: i8,
    pub arousal: u8,
    pub confidence: u8,
    pub source: EmotionSource,
    pub expires_tick: Option<u64>,
}

pub struct GestureCandidate {
    pub gesture_id: GestureId,
    pub clip_id: &'static str,
    pub owned_regions: RegionMask,
    pub required_pose_family: PoseFamily,
    pub cooldown_ticks: u32,
    pub minimum_hold_ticks: u16,
    pub maximum_hold_ticks: u16,
    pub interrupt_policy: InterruptPolicyV1,
    pub recovery: RecoveryPolicyV1,
}

pub trait ChatBehaviorPolicy {
    fn reduce_event(
        &self,
        snapshot: &AvatarSnapshotV1,
        event: &ChatEventV1,
    ) -> BehaviorDecisionV1;
}
```

Selection is deterministic. Candidate score components and tie-breaking are fixed in the policy version. At minimum:

- semantic event match;
- conversation phase;
- emotion compatibility;
- current pose/transition continuity;
- contact compatibility;
- region conflict;
- cooldown and recent repetition;
- authored transition distance;
- stable gesture ID tie-break after seeded variation.

The ANIMATION lane supplies a catalog classifying all 50 WJFL geometries and all chatbot-useful baseline/imported geometries into gesture, emotion, locomotion, flight, reaction, recovery, and conversational home roles.

### 5.9 Interruption and recovery API

```rust
pub enum InterruptPolicyV1 {
    Immediate,
    HigherPriority,
    MarkerWindow(Vec<MarkerId>),
    AtCommitEnd,
    AtClipEnd,
    UninterruptibleUntil(MarkerId),
}

pub enum RecoveryPolicyV1 {
    Neutral,
    ResumeIfCompatible,
    RestartPrevious,
    AuthoredClip(ClipId),
    NearestStableNeighbor,
}

pub struct InterruptionDecisionV1 {
    pub source_presented_pose: String,
    pub preserved_regions: RegionMask,
    pub released_regions: RegionMask,
    pub bridge_or_recovery_clip: Option<ClipId>,
    pub target_behavior: BehaviorId,
    pub reason: InterruptionReason,
}
```

The runtime must sample the presented pose/channel state, not merely the previous clip target. An interruption is invalid if it requires a transition absent from the authored graph and no approved bridge/recovery exists.

### 5.10 Canonical replay

```rust
pub struct ReplayHeaderV1 {
    pub schema_version: u16,
    pub engine_version: String,
    pub runtime_epoch: RuntimeEpoch,
    pub initial_state_sha256: String,
    pub pose_asset_sha256: String,
    pub policy_sha256: String,
    pub viseme_policy_version: u16,
    pub seed: u64,
    pub tick_rate: u32,       // 60
    pub presentation_rate: u32,
}

pub enum ReplayRecordV1 {
    IngressReceived(IngressRecord),
    CommandAck(CommandAckV1),
    TickState(TickStateRecord),
    BehaviorDecision(BehaviorDecisionV1),
    SpeechEvent(SpeechRuntimeEventV1),
    RuntimeEvent(RuntimeEventV1),
    RenderFrame(RenderFrameRecord),
    Footer(ReplayFooterV1),
}
```

Canonical serialization rules:

- ordered struct fields and stable enum names;
- deterministic map ordering through `BTreeMap` or canonical serializer;
- no wall-clock timestamp in state hash;
- no NaN/infinity;
- replay-critical phases use integer/fixed-point representation where practical;
- SHA-256 is the durable hash; existing transport hashes remain diagnostics;
- private text is omitted by default; record hash, length, locale, and timing only.

### 5.11 Telemetry contract

`RuntimeTelemetry` uses atomics or runtime-owned counters plus bounded fixed histograms. It must not lock the render hot path or create labels from unbounded IDs.

Required snapshot fields:

```text
simulation_tick, state_revision, runtime_epoch
commands by disposition
events by type and disposition
inbox depth/current/high-water
dedupe cache size/evictions
accepted-to-apply tick histogram
apply-to-source-frame tick histogram
source-to-present latency histogram when client feedback is available
catch-up ticks/dropped nanoseconds
gesture selected/rejected/coalesced/interrupted/recovered/fallback
speech lifecycle counts
viseme late/skipped/current cue/mouth-rest latency
transition attempts/failures
contact/attachment/topology failures
subscriber count, lagged receivers, bootstrap/resync count
encoded frame/keyframe/delta counts and bytes
```

### 5.12 HTTP and WebSocket compatibility

Add versioned routes while preserving current routes as adapters:

```text
POST /api/avatar/wizard/v1/events
POST /api/avatar/wizard/v1/commands
GET  /api/avatar/wizard/v1/snapshot
GET  /api/avatar/wizard/v1/capabilities
GET  /api/avatar/wizard/v1/telemetry
GET  /ws/avatar/wizard?protocol=2&codec=adaptive
```

Protocol-2 WebSocket rules:

- Binary messages remain adaptive ASCILINE frames; frame bytes do not change during the command-contract wave.
- JSON messages are tagged `hello`, `capabilities`, `event`, `command`, `ack`, `runtime_event`, `snapshot`, `presented`, or `resync`.
- Server sends capabilities and runtime epoch before accepting commands.
- Every ingress message yields one terminal `ack` JSON message.
- Client `presented` feedback is optional and rate-limited; it carries frame sequence/hash only.
- Reconnect uses event/command IDs and source sequence watermarks to avoid duplicate mutation.
- Existing HTTP endpoints build `LegacyAdapter` envelopes and use the same inbox.
- Existing protocol-1 WebSocket remains available through the migration gate and never bypasses typed validation.

## 6. Work-Item DAG

```text
RCHAT-RUN-000 pose baseline checkpoint
    -> RCHAT-RUN-010 contracts
        -> RCHAT-RUN-020 integer clock
        -> RCHAT-RUN-030 inbox/idempotency
        -> RCHAT-RUN-040 state regions
        -> RCHAT-RUN-060 speech/visemes
        -> RCHAT-RUN-090 replay
        -> RCHAT-RUN-100 telemetry
    -> ANIMATION chatbot taxonomy/clip/interrupt contract

020 + 030 + 040
    -> RCHAT-RUN-050 chat reducer
040 + 060 + ANIMATION contract
    -> RCHAT-RUN-070 emotion/gesture policy
040 + 070 + ANIMATION contract
    -> RCHAT-RUN-080 interruption/recovery
030 + 050 + 060 + 090 + 100
    -> RCHAT-RUN-110 HTTP/WS adapters
020 + 040 + 080 + 100 + 110
    -> RCHAT-RUN-120 hub/runtime integration
all implementation items
    -> RCHAT-RUN-130 compatibility migration
    -> RCHAT-RUN-140 deterministic/coverage QA
    -> RCHAT-RUN-150 browser/soak QA
    -> RCHAT-RUN-160 release gate
```

## 7. Accountable Work-Item Ledger

| ID | Deliverable | Dependencies | Primary paths | Gate |
|---|---|---|---|---|
| `RCHAT-RUN-000` | Freeze pose-v4 readiness baseline. | none | existing pose tool/engine/evidence; no behavioral edits | `P0` |
| `RCHAT-RUN-010` | Serde contracts, strict validation, fixtures, schema/version policy. | `000` | new `chat_event.rs`, `command.rs`, fixtures | `C0` |
| `RCHAT-RUN-020` | Integer 60 Hz clock and immutable snapshot API. | `010` | new clock types plus serial `runtime.rs` wiring | `R1` |
| `RCHAT-RUN-030` | Bounded ordered inbox, dedupe cache, source watermarks, terminal acks. | `010` | `command.rs`, serial `runtime.rs` wiring | `R2` |
| `RCHAT-RUN-040` | Typed orthogonal regions and legacy state projection. | `010` | `state_regions.rs`, serial `state.rs` wiring | `R3` |
| `RCHAT-RUN-050` | Chat-event reducer and conversation lifecycle. | `020`,`030`,`040` | `chat_policy.rs`, controller bridge | `B1` |
| `RCHAT-RUN-060` | Speech lifecycle, timing quantization, semantic visemes, mouth mapping. | `010`,`040` | `speech.rs`, fixtures | `RS1` |
| `RCHAT-RUN-070` | Deterministic emotion/gesture selection using ANIMATION catalog. | `040`,`050`,`060`, `ANIM-C0` | `chat_policy.rs`, animation data | `B2` |
| `RCHAT-RUN-080` | Region-aware interruption, coalescing, restoration, recovery. | `040`,`070`, `ANIM-C0` | policy plus serial playback/channel wiring | `B3` |
| `RCHAT-RUN-090` | Canonical replay writer/reader/hash comparator. | `010`,`020`,`030`,`040` | `replay.rs` | `D1` |
| `RCHAT-RUN-100` | Bounded causal telemetry and snapshots. | `010`,`020`,`030` | `telemetry.rs` | `O1` |
| `RCHAT-RUN-110` | Versioned HTTP/WS ingress, acks, capabilities, legacy adapters. | `030`,`050`,`060`,`090`,`100` | serial `server.rs` wiring | `T1` |
| `RCHAT-RUN-120` | Single hub-owned runtime cadence and snapshot/render lineage. | `020`,`040`,`080`,`100`,`110` | serial `hub.rs`, frame bridge | `I1` |
| `RCHAT-RUN-130` | Compatibility projection, temporary feature flags, migration docs. | `120` | shared integration paths | `I2` |
| `RCHAT-RUN-140` | Full deterministic, pose, transition, replay, cadence, interruption QA. | `130` | Rust tests and evidence binaries | `Q1` |
| `RCHAT-RUN-150` | Live browser, multiclient, reconnect, TTS timing, 10-minute soak. | `140` | integration/evidence only | `Q2` |
| `RCHAT-RUN-160` | Clean-clone release, push, deploy, endpoint verification. | `150`, workflow final gate | compact evidence, release docs | `F0` |

## 8. Detailed Work Items

### `RCHAT-RUN-000` - Pose-v4 readiness checkpoint

Owner: integration coordinator with pose owner review.

Actions:

1. Finish and commit the current pose-v4 work without mixing chatbot changes.
2. Run pose-tool format, clippy, unit/integration, deterministic compile, promotion, engine tests, static census, exhaustive transition evidence, and WJFL clip quality.
3. Confirm 89 runtime geometries, 50 WJFL geometries, and 621 authored directed transitions.
4. Verify every generated frame and transition has a machine-readable pass result.
5. Verify the production engine loads the v4 gzip and never opens source PNGs.
6. Push the checkpoint and record local/remote parity.

Required evidence:

```text
evidence/cartoon-animation-program/rust-chatbot/gates/P0.json
evidence/cartoon-animation-program/rust-chatbot/checkpoints/pose-v4.json
```

Rollback: no chatbot work begins. Repair the pose branch through its existing serial admission workflow.

### `RCHAT-RUN-010` - Freeze contracts

Owner: RUNTIME.

Actions:

- implement all Section 5 serde types as new modules;
- reject unknown fields with `#[serde(deny_unknown_fields)]` on external structs;
- implement bounded validation without state mutation;
- add valid/invalid fixtures for every event and command variant;
- add canonical fixtures for all five central state events and assert their exact
  `snake_case` tags and payload field sets;
- add negative fixtures for unknown clarification reasons, tool kinds/outcomes,
  assistant error codes, celebration reasons, out-of-range urgency/intensity,
  zero/oversized tool-wait duration, mismatched operation IDs, and forbidden
  free-form content fields;
- produce capabilities schema/version constants;
- document compatibility rules and maximum payload sizes.

Focused tests:

```bash
cargo test --manifest-path rust/wizard_avatar_engine/Cargo.toml --test chat_event_contract
cargo test --manifest-path rust/wizard_avatar_engine/Cargo.toml --test command_ordering contract_
```

Acceptance:

- all good fixtures round-trip byte-stably through canonical JSON;
- all malformed/unknown/oversized fixtures fail with stable error codes;
- the five central state-event fixtures reduce to `clarifying`, `tool_wait`,
  `idle`, `error`, and `celebrating` without inspecting private text;
- no production behavior changes;
- no PNG/runtime raster dependency is introduced.

Rollback: revert only new contract modules/exports; pose-v4 checkpoint remains unchanged.

### `RCHAT-RUN-020` - Integer fixed clock

Owner: RUNTIME; coordinator holds `LOCK-RCHAT-RUNTIME` for wiring.

Actions:

- replace float accumulation with integer units;
- retain maximum eight catch-up ticks;
- emit explicit dropped-time events;
- make tick stepping and wall-clock advancement separate APIs;
- return immutable reference-counted snapshots;
- ensure presentation interpolation cannot mutate semantics.

Focused tests:

```bash
cargo test --manifest-path rust/wizard_avatar_engine/Cargo.toml --test fixed_clock
cargo test --manifest-path rust/wizard_avatar_engine/Cargo.toml --test chat_replay clock_
```

Acceptance:

- 60,000 scripted ticks produce exactly 1,000 simulated seconds;
- irregular wall-clock chunks with equal elapsed nanoseconds produce equal state hashes;
- 15/24/30/60 FPS sampling does not change semantic hashes at common ticks;
- a two-second stall executes eight ticks maximum and records dropped time deterministically.

Rollback: restore prior accumulator behind temporary `WIZARD_CHAT_RUNTIME=legacy`; no downstream promotion may continue.

### `RCHAT-RUN-030` - Ordered inbox and idempotency

Owner: RUNTIME.

Actions:

- implement validation, server sequence assignment, bounded queue, ack cache, and source watermarks;
- apply commands only on their accepted apply tick;
- make duplicate/stale/expired/conflict outcomes non-mutating;
- record acks and queue events in replay and telemetry interfaces.

Focused tests cover permutation ordering, duplicate storms, reconnect retries, future ticks, TTL boundaries, queue overflow, sequence wrap policy, and emergency stop ordering.

Acceptance:

- each ingress gets exactly one terminal ack;
- 100 retries of one command cause one mutation;
- 10,000 randomized same-tick envelopes replay in identical order twice;
- inbox and cache never exceed configured bounds;
- no stale/expired/rejected command changes state revision.

Rollback: disable versioned ingress; legacy adapter remains available at the last verified runtime checkpoint.

### `RCHAT-RUN-040` - State regions

Owner: RUNTIME with coordinator-held state/controller locks.

Actions:

- add `AvatarSemanticStateV1` and all region types;
- add owner/priority/generation/deadline invariants;
- migrate one region at a time: session, conversation, speech/mouth, face, gesture, pose, props/wings/effects, then mobility/control;
- project legacy `WizardState` from semantic regions;
- forbid two-way synchronization after each region migrates.

Acceptance:

- every state mutation names exactly one owner and increments the correct generation;
- unrelated region generations remain unchanged;
- legacy JSON fields remain compatible in protocol v1;
- canonical state contains no wall-clock float deadline;
- invariant test rejects conflicting ownership or expired region state.

Rollback: revert the last migrated region only. The projection remains one-way; do not restore dual authority.

### `RCHAT-RUN-050` - Conversation lifecycle reducer

Owner: RUNTIME.

Event-to-state requirements:

| Event | Required visual state |
|---|---|
| user turn starts | listening posture; cancel/suppress assistant speech; preserve safe mobility |
| user turn commits | attentive hold then thinking preparation |
| assistant thinking starts | bounded thinking posture with no repetitive extreme gesture |
| assistant response planned | prepare response posture; no mouth motion before speech start |
| clarification requested | clarifying state; suppress incompatible speech/gesture; use enum reason and bounded urgency only |
| tool wait starts | tool_wait state correlated to opaque operation ID; patient bounded loop; no tool-name/argument inspection |
| tool wait ends | settle to idle before any later ordered event; outcome may select bounded recovery accent but not a private-content branch |
| assistant error | error state with bounded non-looping acknowledgement; code and recoverability only |
| celebration requested | celebrating state with bounded intensity and one-shot recovery; no unbounded repeat |
| speech starts | speaking state; acquire speech/mouth; optional compatible gesture |
| speech pauses | mouth rest policy; gesture may hold/recover |
| speech completes | mouth rest; conversational recovery; await user |
| connection degraded | low-amplitude neutral/degraded posture; no panic loop |
| safety clamp | immediate bounded neutralization of prohibited channels |

Acceptance:

- every event variant has deterministic reducer tests;
- all ten canonical conversation states are entered, held, interrupted, and
  exited by explicit table-driven tests;
- duplicate clarification, error, and celebration events are idempotent;
- duplicate tool-wait starts preserve the active operation generation, while a
  mismatched or duplicate end cannot mutate the conversation region;
- `tool_wait_ended` deterministically applies idle before a later same-tick
  event is reduced in envelope order;
- content is not required to select a safe default behavior;
- explicit user movement survives compatible conversational changes;
- cancelling speech never cancels unrelated movement;
- duplicate lifecycle events are idempotent.

### `RCHAT-RUN-060` - Speech and visemes

Owner: RUNTIME; ANIMATION reviews mouth visual mapping.

Test matrix:

```text
authoritative cue timeline
empty cues with deterministic fallback
single long phoneme
rapid consonant cluster
long silence/pause
late SpeechStarted
progress fast-forward
pause/resume
cancel before start
cancel during speech
complete without final progress
shush suppression
emotion amplitude overlay
reconnect duplicate events
```

Acceptance:

- quantized cue boundaries differ from supplied time by at most one simulation tick;
- mouth reaches expected semantic viseme by the first tick at/after its start;
- cancellation reaches `Rest` within six ticks;
- completion reaches `Rest` within four ticks;
- replayed mouth/viseme records are identical;
- no random mouth motion and no audio waveform dependency.

### `RCHAT-RUN-070` - Emotion and gesture policy

Owner: RUNTIME for algorithm; ANIMATION for catalog and visual approval.

Required ANIMATION handoff:

```text
gesture catalog with semantic tags
emotion-to-full/close pose mapping
owned region masks
entry/commit/hold/recovery markers
cooldowns and intensity bounds
legal authored neighbors/bridges
speech compatibility
visual root/contact constraints
```

Acceptance:

- all ten WJFL feeling pairs are semantically classified;
- all 50 WJFL poses are reachable through reviewed behavior paths;
- all 89 geometries are either runtime-reachable or explicitly diagnostic with rationale;
- same state/event/policy/seed produces same selected gesture;
- no gesture repeats more than policy allows;
- low-confidence hints cannot displace explicit user action or safety clamps;
- policy never returns an unregistered raw pose.

### `RCHAT-RUN-080` - Interruption and recovery

Owner: RUNTIME for arbitration; ANIMATION for authored paths.

Required scenarios:

```text
explain -> user interruption -> listening
speech -> pause -> resume
speech -> cancel -> neutral
thinking -> surprise reaction -> recovery
gesture -> higher-priority safety clamp
flight -> conversation gesture compatible overlay
walking -> speech without locomotion cancellation
extreme feeling -> neutral home recovery
close feeling -> full feeling -> conversational home
disconnect while command/gesture/speech is active
```

Acceptance:

- no interruption starts from an obsolete target pose;
- preserved regions remain byte-identical at the interruption tick;
- released regions enter recovery once;
- every interruption reaches a stable state within its declared bound;
- every used transition belongs to the authored set or an approved generated bridge;
- zero detached staff, face, mouth, wing, hand, or contact artifacts in captured frames.

### `RCHAT-RUN-090` - Replay and hashes

Owner: RUNTIME.

Acceptance:

- record -> replay -> re-record is byte-identical for canonical records;
- first divergence reports tick, state field, event/command ID, pose/transition, and frame sequence;
- changed asset/policy/viseme version fails header compatibility before mutation;
- same semantic replay sampled at 15/24/30/60 FPS has identical tick-state hashes;
- private text is absent from default replay artifacts.

### `RCHAT-RUN-100` - Telemetry

Owner: RUNTIME; WORKFLOW owns evidence schema consumption.

Acceptance:

- counters/histograms cover Section 5.11;
- no unbounded label or queue growth during a 10-minute soak;
- telemetry reads do not mutate simulation;
- source-to-visible lineage can be reconstructed when browser feedback is enabled;
- telemetry disabled/enabled produces identical semantic and frame hashes.

### `RCHAT-RUN-110` - HTTP/WebSocket adapters

Owner: coordinator under server lock, consuming RUNTIME contracts.

Acceptance:

- HTTP and WS versions of the same ingress produce the same ack and state hash;
- protocol-2 capabilities expose schema, asset, policy, and supported event versions;
- protocol-1/legacy routes use `LegacyAdapter` envelopes;
- one socket can receive binary frames and JSON acks/events without ambiguity;
- malformed JSON, binary command attempts, oversized messages, and unauthorized diagnostics fail safely;
- reconnect retry causes no duplicate state mutation;
- existing adaptive binary frame decode tests remain unchanged and pass.

### `RCHAT-RUN-120` - Hub and render integration

Owner: coordinator under hub/frame locks.

Acceptance:

- one runtime advances regardless of viewer count;
- 0, 1, 2, and 4 viewers change simulation rate by at most 1%;
- slow/lagged viewer resync is subscriber-local;
- immutable snapshot state revision and source frame lineage are present in diagnostics;
- command apply never waits on a slow network send;
- rendering cannot acquire a runtime write lock;
- no runtime PNG open/load occurs.

### `RCHAT-RUN-130` - Compatibility and promotion switches

Temporary switches:

```text
WIZARD_CHAT_RUNTIME=legacy|v1
WIZARD_CHAT_INGRESS=0|1
WIZARD_SPEECH_TIMING=duration|viseme-v1
WIZARD_CHAT_POLICY=direct|semantic-v1
WIZARD_WS_PROTOCOL_DEFAULT=1|2
```

Rules:

- switches select adapters/policy, not two simultaneously mutating runtimes;
- default changes only after the corresponding gate passes;
- every switch combination tested in the supported migration matrix;
- final release defaults to Rust semantic runtime v1, viseme v1, semantic policy v1, protocol 2;
- legacy compatibility remains read/adapter-only and is scheduled for removal in a later protocol-major plan.

### `RCHAT-RUN-140` - Deterministic and coverage QA

Mandatory suites:

```bash
cargo fmt --manifest-path rust/wizard_avatar_engine/Cargo.toml -- --check
cargo clippy --manifest-path rust/wizard_avatar_engine/Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path rust/wizard_avatar_engine/Cargo.toml --all-targets
cargo test --manifest-path rust/wizard_avatar_pose_tool/Cargo.toml --all-targets
```

In addition, run deterministic compiler promotion, static census, exhaustive 621-transition verification, all chatbot event/replay tests, cadence matrix, interruption matrix, and no-runtime-PNG scope verifier.

Gate `Q1` requires 100% pass. A 90% visual score is insufficient because known breakup in any authored path is user-visible; the program target is at least 90%, but this runtime plan retains the existing stricter zero-failure transition gate.

### `RCHAT-RUN-150` - Live browser and soak QA

Live scenarios:

- full user/assistant turn lifecycle;
- partial/committed/cancelled user turns;
- thinking, response preparation, clarification, timed speech,
  pause/resume/cancel/fail/complete;
- tool wait start/end for completed, failed, cancelled, and timed-out outcomes,
  including duplicate start, duplicate end, mismatched operation ID, and a
  same-tick follow-up event;
- recoverable/non-recoverable assistant error and bounded celebration at
  minimum/maximum intensity;
- all ten feeling families at low/high bounded intensity;
- gesture during walking and flight;
- rapid interruption and recovery;
- duplicate/out-of-order/expired network events;
- reconnect/resync with retained source sequence;
- one controller plus four viewers, including one slow viewer;
- 10-minute mixed chatbot, locomotion, speech, feeling, and connection-degradation soak.

Acceptance:

- zero unhandled browser console errors or decode errors;
- zero command/event mutations without terminal ack;
- p95 accepted-to-applied <= 2 ticks on loopback;
- p95 accepted-to-source-frame <= 3 ticks, excluding declared marker-window waits;
- p95 source-frame-to-browser-present <= 2 presentation frames on loopback;
- no unbounded queue/telemetry growth;
- no visible breakup, clipped cells, antialiasing, detached anatomy/prop, or runtime raster substitution;
- final state returns to stable conversational home after every scenario.

### `RCHAT-RUN-160` - Release and deployment

Owner: integration coordinator with WORKFLOW approval.

Actions:

1. Build/test from a clean clone of the exact pushed SHA.
2. Verify asset/policy/replay schema hashes and compact evidence manifest.
3. Run the live browser gate against the exact release binary.
4. Push without force and verify remote SHA.
5. Deploy the release binary through the repository's approved Rust deployment workflow.
6. Verify the public endpoint, listener/process, health, capabilities, state, WS bootstrap, command ack, speech lifecycle, and one complete animated turn.
7. Record rollback binary/SHA and endpoint evidence.

Release is blocked if evidence came from a different SHA or if the endpoint is serving a stale binary.

## 9. Gate Matrix

| Gate | Blocking result | Automated evidence | Live/visual evidence |
|---|---|---|---|
| `P0` | pose baseline frozen | 89/50/621 counts, compiler hashes, all Rust pose tests | static/transition contact sheets |
| `C0` | contracts frozen | fixtures, strict validation, compatibility schema | none |
| `R1` | integer clock | cadence/catch-up hashes | none |
| `R2` | ordered idempotent inbox | ordering/dedupe/TTL/overflow tests | reconnect retry smoke |
| `R3` | region authority | ownership/generation/projection tests | diagnostic state inspection |
| `B1` | conversation reducer | lifecycle matrix | one neutral turn |
| `RS1` | speech/viseme runtime | timing/cancel/replay tests | timed mouth recording |
| `B2` | emotion/gesture policy | classification/determinism/cooldown tests | ten-feeling review reel |
| `B3` | interruption/recovery | interruption matrix and transition checks | captured recovery sequences |
| `D1` | canonical replay | two-run byte/hash parity | none |
| `O1` | telemetry | cardinality/causality/disabled-parity tests | live diagnostics |
| `T1` | HTTP/WS parity | protocol tests | browser command/ack smoke |
| `I1` | hub integration | multiclient/resync/frame lineage | 4-viewer live run |
| `I2` | migration | switch matrix and legacy projection | legacy/new client smoke |
| `Q1` | deterministic quality | full Rust suites, 621 transitions, replay/cadence | complete contact sheets |
| `Q2` | live quality | soak metrics | Chromium recordings/screenshots |
| `F0` | release | clean clone, pushed SHA, manifest | deployed endpoint proof |

## 10. Measurable Acceptance Contract

### Runtime and commands

```text
simulation tick                         exactly 1/60 second
max catch-up per event-loop turn        8 ticks
semantic replay hash divergence         0
duplicate command mutations             0
commands/events without terminal ack    0
rejected command state revisions        0
pending inbox maximum                    1,024
dedupe cache maximum                     8,192
viewer-count simulation variance        <= 1%
```

### Chat and speech

```text
event accepted-to-applied p95            <= 2 ticks loopback
authoritative viseme boundary error      <= 1 tick
speech cancel to Rest                    <= 6 ticks
speech complete to Rest                  <= 4 ticks
late elapsed visemes replayed            0
mouth movement before SpeechStarted      0
unbounded repeated extreme gestures      0
```

### Pose and visual quality

```text
runtime geometries                       89/89
WJFL geometries integrated               50/50
authored directed transitions passing    621/621
unclassified WJFL poses                  0
unresolved behavior paths                0
detached staff/face/mouth/wing/hand       0 frames
runtime PNG loads                        0
antialiased/interpolated cells            0
```

### Transport and observability

```text
HTTP/WS semantic parity failures         0
decode/source hash mismatches            0
unhandled browser console errors         0
unexplained resyncs                      0
unbounded telemetry labels/queues        0
source-frame-to-present p95              <= 2 frames loopback
```

## 11. Evidence Layout

Compact committed evidence:

```text
evidence/cartoon-animation-program/rust-chatbot/
  checkpoints/
    pose-v4.json
    contracts.json
    integration.json
  gates/
    P0.json C0.json R1.json R2.json R3.json
    B1.json RS1.json B2.json B3.json
    D1.json O1.json T1.json I1.json I2.json
    Q1.json Q2.json F0.json
  release/
    manifest.json
    checksums.sha256
    FINAL_VERIFICATION.md
```

Large raw frames, RGB dumps, videos, browser traces, full NDJSON replays, and soak logs are CI/release artifacts, not committed source. Each gate JSON records:

```text
gate_id, status, tested_sha, branch, timestamp_utc
rustc_version, cargo_version, target_triple
pose_asset_hash, policy_hash, contract_hash, replay_schema
commands with exit code/duration/summary
test totals and skipped/ignored counts
runtime, speech, transition, browser, and soak metrics
artifact paths/URLs and SHA-256
reviewer, limitations, rollback_sha
```

## 12. Rollback Strategy

### Checkpoints

1. `P0`: pose-v4 baseline.
2. `C0`: contracts only.
3. `R1-R3`: clock, inbox, regions.
4. `B1-RS1`: chat reducer and speech.
5. `B2-B3`: behavior/interruption.
6. `D1-O1`: replay/telemetry.
7. `T1-I2`: transport/integration/default migration.
8. `Q2`: release candidate.

### Failure procedure

1. Stop the integration queue.
2. Record failed work item, exact command, exit code, first actionable error, SHA, and evidence paths.
3. Preserve replay, state hash, frame, and browser artifacts from the first divergent tick.
4. Disable only the failing temporary feature switch or revert the failing integration commit normally.
5. Restore the last verified Rust binary/SHA. Never replace it with a Python authority.
6. Re-run the previous gate and live smoke.
7. Update the workflow ledger before resuming.

The pose-v4 asset is never silently downgraded to bypass a chatbot failure. If the asset itself fails `P0`, chatbot implementation remains blocked until pose integration is repaired.

## 13. Cross-Lane Dependencies

### RUNTIME -> ANIMATION

RUNTIME supplies:

- region IDs and ownership masks;
- semantic chat/conversation/speech events;
- gesture request and behavior-decision types;
- interrupt/recovery policy enums;
- marker-crossing and presented-state requirements;
- viseme vocabulary and mouth-mapping interface;
- deterministic policy scoring inputs.

### ANIMATION -> RUNTIME

ANIMATION must supply before `RCHAT-RUN-070`:

- reviewed behavior taxonomy for all 50 WJFL poses;
- conversational home, listening, thinking, speaking, reacting, and recovery clips;
- emotion full/close selection rules;
- region ownership and speech compatibility;
- anticipation/commit/hold/recovery markers;
- legal interrupts, bridges, cooldowns, and visual thresholds;
- proof that selected paths are within the 621 authored transition graph or approved bridge additions.

### RUNTIME -> WORKFLOW

RUNTIME supplies:

- stable work IDs and dependency graph;
- exact tests and gate metrics;
- contract/policy/replay hashes;
- evidence field requirements;
- rollback switches and stop conditions.

### WORKFLOW -> RUNTIME

WORKFLOW must supply:

- machine-readable registry entries and owners;
- checkpoint/branch rules and hotspot locks;
- CI required-check names;
- artifact retention and evidence validator;
- final clean-clone, push, deploy, and endpoint-verification procedure.

## 14. Required Handoff Format

Every implementation handoff must contain:

```text
ROLE:
WORK_ITEM_ID:
STATUS: REVIEW_READY | BLOCKED
BASE_SHA:
BRANCH:
COMMIT_SHA:
LOCKS_HELD_AND_RELEASED:
ALLOWED_PATHS:
FILES_CHANGED:
INTERFACES_CONSUMED:
INTERFACES_PRODUCED:
COMMANDS_RUN:
EXACT_RESULTS_AND_TOTALS:
EVIDENCE_PATHS_AND_HASHES:
POSE_ASSET_HASH:
POLICY_OR_CONTRACT_HASH:
FIRST_DIVERGENT_TICK_IF_ANY:
VISUAL_REVIEW_REQUIRED:
KNOWN_LIMITATIONS:
ROLLBACK_POINT:
DEPENDENTS_UNBLOCKED:
NEXT_OPERATOR_ACTION:
```

Vague statements such as `tests pass` or `looks good` are not acceptable.

## 15. Stop Conditions

Implementation stops immediately when any of these occurs:

- `P0` is not proven at a fixed pushed SHA;
- an agent edits an unowned hotspot or overwrites concurrent work;
- Python becomes a production runtime dependency;
- a chatbot event directly selects a production pose;
- a rejected/duplicate/stale command mutates state;
- rendering or a client advances simulation;
- speech mouth motion begins before lifecycle start or replays elapsed visemes;
- an interruption uses an unauthored/unapproved transition;
- runtime code loads a PNG/reference raster;
- telemetry/replay records private chat content by default;
- any of the 621 authored transition gates regresses;
- required Rust tests are skipped, ignored, or made non-blocking;
- evidence SHA differs from the code deployed or pushed.

## 16. Definition of Done

The RUNTIME lane is complete only when:

- [ ] `P0` proves all 89 geometries, all 50 WJFL poses, and all 621 authored directed transitions.
- [ ] Typed chat events and commands are strict, versioned, ordered, bounded, and idempotent.
- [ ] One integer 60 Hz runtime owns all semantic mutation.
- [ ] Orthogonal regions expose explicit owner, priority, generation, and tick deadlines.
- [ ] Conversation lifecycle behavior is deterministic and does not unnecessarily cancel mobility.
- [ ] Speech supports prepared/start/progress/pause/resume/cancel/complete/fail with deterministic visemes.
- [ ] Emotion/gesture selection classifies the WJFL vocabulary and obeys cooldown/intensity/continuity policy.
- [ ] Interruption starts from the presented state and recovers through approved paths.
- [ ] Replay is canonical and reproduces semantic and source-frame hashes.
- [ ] Telemetry is causal, bounded, privacy-safe, and behavior-neutral.
- [ ] HTTP and WebSocket have semantic parity and terminal acks while binary ASCILINE compatibility remains intact.
- [ ] Browser, reconnect, multiclient, transition, and 10-minute soak gates pass with zero breakup.
- [ ] Production performs zero runtime PNG loads.
- [ ] Clean clone, exact pushed SHA, deployed binary, and public endpoint are all verified.
