# Media Performance Architecture

## Repository Ownership

### Wizard Joe Avatar

Owns:

- capability-manifest wire V2 generation from loaded runtime authorities;
- `PerformanceScoreV1` validation and canonical hashing;
- media timeline command decoding through the existing command inbox;
- bounded score preload and cue index construction;
- deterministic tick-to-media-time projection;
- cue activation, interruption, recovery, and stale-generation rejection;
- animation, gaze, face, speech, locomotion, secondary-motion execution;
- frame, cue, replay, topology, and synchronization evidence.

Does not own:

- media playback;
- transcription or LLM calls;
- user media library persistence;
- external URL opening;
- a second media clock.

### PrismGT

Owns:

- media files, metadata, chapters, canonical external URL, and content hashes;
- `HTMLMediaElement` lifecycle and observed playback time;
- player controls and media-session event ordering;
- preprocessing jobs, checkpoints, cancellation, privacy, provider disclosure;
- transcript, alignment, analysis, and score version storage;
- connector lifecycle and reconnection snapshots;
- governed Whiz source-open action and audit records;
- performance editor and source-analysis diagnostics.

## Proposed Rust Boundaries

Wizard remains one crate until coupling proves a split is warranted. Add focused
modules rather than a workspace rewrite:

```text
wizard_avatar_engine/src/
  capability_manifest.rs
  media_protocol.rs
  performance_score.rs
  score_validator.rs
  cue_scheduler.rs
  media_runtime.rs
  performance_telemetry.rs
```

PrismGT should add one library domain and one CLI binary within the existing Cargo
workspace:

```text
crates/prism-cdiss-core/src/media_performance/
  identity.rs
  session.rs
  protocol.rs
  provenance.rs
  governed_source.rs

crates/prism-cdiss-cli/src/media_performance/
  store.rs
  connector.rs
  routes.rs
  jobs.rs

crates/prism-media-prepare/
  decode.rs
  transcript.rs
  verify.rs
  align.rs
  narrative.rs
  music.rs
  compile.rs
  validate.rs
```

The exact Prism crate split requires a focused implementation review before files
are created; this layout records responsibility, not invented current modules.

## Typed Identity

All IDs are non-empty bounded newtypes with canonical serialization:

- `MediaId`: derived from normalized content hash plus media type.
- `MediaSessionId`: unique playback session.
- `TimelineGeneration`: increments on load, seek start, track/chapter change,
  restart, or authoritative discontinuity.
- `ConnectorSequence`: monotonically increasing per connector epoch.
- `ScoreId`: hash of canonical score body and version header.
- `ScoreVersion`: schema plus compiler version.
- `CharacterId`, `CapabilityId`, `CueId`, `ChapterId`, `JobId`.

## Media Identity Record

The immutable source media is content-addressed. Mutable metadata is versioned and
stored separately.

Required fields:

- media ID and SHA-256 content hash;
- managed local file reference, never a browser-exposed arbitrary path;
- media type and MIME type;
- title, author/artist, album/book, cover reference;
- duration and chapter records;
- canonical external URL plus provenance source;
- transcript/alignment/analysis/score status and version references;
- creation/modification timestamps;
- privacy/provider history.

## Performance Score

### Capability Manifest Wire Contract

Media-performance V1 binds the generated Wizard capability document whose wire
`schema_version` and `capability_api_version` are exactly `2`. Version 2 is required
because typed applicability, fallback topology, aliases, controller-command census,
and compatibility fields are breaking additions to the former strict schema. The
current Rust source type names retain their historical `V1` suffix only for internal
source compatibility; consumers negotiate and validate the numeric wire versions.
The versioned endpoint is `/api/avatar/wizard/v2/capabilities`; the unversioned route
is an adapter to V2, and `/v1/capabilities` must not serve V2 bytes.

The document and manifest use these exact fields in this declaration order:

```rust
struct CapabilityDocumentWireV2 {
    manifest_sha256: Sha256Hex,
    manifest: CapabilityManifestWireV2,
}

struct CapabilityManifestWireV2 {
    schema_version: u16,                       // exactly 2
    character_id: CharacterId,
    versions: RuntimeVersionsV1,
    imported_pose_asset_schema_version: u32,
    imported_pose_archive_sha256: Sha256Hex,
    runtime_geometry_authority_sha256: Sha256Hex,
    pose_geometry_count: u16,
    pose_alias_count: u16,
    motion_graph_schema_version: u16,
    motion_graph_sha256: Sha256Hex,
    feelings: Vec<Emotion>,
    controller_command_surface: Vec<ControllerCommandKind>,
    state_facing_fallbacks: Vec<StateFacingFallbackV1>,
    safe_idle: RuntimeSafeIdleProfileV1,
    support: RuntimeSupportFlagsV1,
    capabilities: Vec<CapabilityEntryWireV2>,
}

struct RuntimeSafeIdleProfileV1 {
    idle_turn_state: ChatTurnState,       // exactly idle; uses facing fallback table
    stop_behavior_id: CapabilityId,       // exactly behavior.stop
    neutral_expression_id: CapabilityId,  // exactly expression.neutral
    rest_mouth_pose_id: CapabilityId,     // exactly mouth.closed
    preserve_mode: bool,
    preserve_root_position: bool,
    preserve_facing: bool,
    clear_gesture: bool,
    clear_gaze_override: bool,
    clear_viseme_override: bool,
    clear_blink_override: bool,
    clear_prop_effects: bool,
    settle_secondary_motion: bool,
}

struct CapabilityEntryWireV2 {
    id: CapabilityId,
    kind: CapabilityKind,
    status: CapabilityStatus,
    category: CapabilityCategoryV1,
    emotional_uses: ApplicabilityV1<Emotion>,
    energy: u8,
    directions: Vec<Direction>,
    duration: Option<TickDurationV1>,
    loop_behavior: LoopBehaviorV1,
    interruptibility: InterruptibilityV1,
    valid_entry_states: ApplicabilityV1<ChatTurnState>,
    valid_exit_states: ApplicabilityV1<ChatTurnState>,
    face_policy: FacePolicyV1,
    compatible_face_states: ApplicabilityV1<Expression>,
    compatible_locomotion_states: ApplicabilityV1<Locomotion>,
    compatible_motion_profiles: Vec<MotionProfile>,
    controller_commands: ApplicabilityV1<ControllerCommandKind>,
    runtime_surfaces: Vec<RuntimeSurfaceV1>,
    prop_requirements: Vec<PropRequirementV1>,
    runtime_cost: RuntimeCostV1,
    quality_status: QualityStatusV1,
    pose_coverage: Option<PoseCoverageV1>,
    pose_alias: Option<PoseAliasV1>,
    transition_limitations: ApplicabilityV1<TransitionLimitationV1>,
    narrative_uses: ApplicabilityV1<NarrativeUseV1>,
    inappropriate_uses: ApplicabilityV1<InappropriateUseV1>,
    fallback: FallbackTopologyV1,
}
```

All structs deny unknown fields and serialize without omitted fields or insignificant
whitespace. `ApplicabilityV1` uses `{"applicability": tag, "values": [...]}` with
tag `applicable` and mandatory non-empty values, or
`{"applicability":"not_applicable"}` with no values. `FallbackTopologyV1` uses
`{"topology":"fallbacks","ids":[...]}`, `{"topology":"terminal"}`, or
`{"topology":"not_applicable"}`. Capability category uses mandatory `domain` and
variant-dependent `value`. Closed enum spellings and every auxiliary nested field are
frozen by the complete generated fixture
[`fixtures/capability-manifest-v2.json`](fixtures/capability-manifest-v2.json), which
must deserialize under strict fields and round-trip byte-for-byte.

Manifest arrays are deterministic: capability entries sort strictly by ID; feelings,
controller commands, state-facing fallbacks, and every set-valued entry field sort by
their Rust enum/order or string ID and contain no duplicates. The inner `manifest`
hash is SHA-256 over its whitespace-free Serde JSON bytes in the declaration order
above; the outer document repeats that hash. Validation rebuilds the manifest from
the exact loaded runtime registries and requires equality before exposing it. A score's
`capability_manifest_sha256` equals this nonzero `manifest_sha256`; an all-zero or
unresolvable binding is invalid even in fixtures. The safe-idle profile is also
generated and validated: its three capability IDs must resolve to active entries of
the exact command/expression/mouth categories, idle must have all eight state-facing
fallbacks, and every preservation/clear/settle boolean is required to be true. It
defines one deterministic fallback for every score region: preserve mode; stop root
velocity while preserving position and facing; resolve the idle body pose through the
facing table; clear gesture and gaze overrides; set neutral face; clear viseme and set
the closed mouth; clear blink override and prop effects; and settle secondary motion.

The checked-in Phase 0 manifest truthfully reports
`support.deterministic_media_scores = false`; it proves the generated schema, hash,
census, and score capability resolution but does not claim runtime score activation.
Until MP-WIZ-040 is accepted, preload/activate returns `unsupported_runtime_profile`.
That gate may flip the flag only with implementation evidence, regenerate the complete
manifest fixture and hash, and rebind/re-hash every accepted score fixture in the same
atomic promotion commit.

`PerformanceScoreV1` is deterministic JSON with canonical field ordering during
hashing. Its header binds:

- schema and score version;
- score ID;
- media ID and content hash;
- transcript/alignment/analysis versions;
- character ID and capability-manifest hash;
- animation-library and motion-graph hashes;
- compiler and validator versions;
- seed;
- media duration/timebase;
- reduced-motion profile;
- creation provenance.

The body contains ordered non-overlapping or explicitly layered tracks:

- narrative mode and scene/beat state;
- root locomotion and stage position;
- body pose and weight shift;
- gesture preparation, stroke, hold, and recovery;
- gaze/head target and eye behavior;
- emotion/expression transition;
- speech/viseme plan;
- blink opportunities and suppression windows;
- prop/effect/secondary motion;
- music beat/bar/phrase/section and dance phrase;
- explicit stillness.

Every capability reference must resolve against the bound capability manifest.
Unknown, inactive, incompatible, or under-quality IDs fail validation before
playback. Runtime fallback is explicit and telemetered; it is never silent.

## Connector Protocol

Use one versioned semantic command envelope carried by Wizard's current remote
command transport. This is gated on acceptance of `RCHAT-RUN-110`: the typed
bounded inbox, reducer ordering, ACK/error model, and replay contract must be in
the production server path first. Until then, the existing REST/WebSocket
controls remain authoritative and media commands are rejected as unsupported.
After promotion, the legacy decoder translates existing controls into the same
typed inbox and maps typed ACK/errors back to their existing HTTP/WS responses.

Negotiation starts with `connector.hello` and `connector.welcome`. Peers exchange
supported protocol ranges, maximum payload bytes, maximum in-flight commands,
heartbeat interval, authentication mode, and capability/score hash support. No
media command is accepted before negotiation and connector authentication pass.
The negotiated heartbeat uses standard WebSocket Ping/Pong control frames with an
empty payload, not another JSON message. Two missed intervals destroy the auth context
and require a new hello/welcome exchange.

V1 has one authentication mode, `bearer_channel_v1`. The connector credential is
exactly 32 random bytes provisioned outside protocol payloads, stored with owner-only
permissions, scoped only to `media_performance`, and rotated on Wizard restart or
explicit revocation. It is presented once in the existing transport authorization
header. Non-loopback use requires TLS with certificate validation; plaintext is
permitted only when both peers resolve the socket as loopback. `connector.welcome`
returns a random 32-byte server nonce and authenticated-principal ID. The resulting
auth context is bound to `(principal_id, server_nonce, connector_epoch,
negotiated_protocol_version, transport_connection_id)` and cannot migrate to a new
connection. Wizard stores only the credential hash and bounded auth-context record.
Disconnect, restart, credential rotation, five failed attempts, or ten minutes of
inactivity destroys the context and requires a fresh authorization exchange.

The nonce, connector epoch, strictly increasing sequence, command fingerprint, and
single transport binding provide replay protection. A previously accepted identical
command on the same live context receives its cached ACK while that terminal response
is retained; any cross-context replay, nonce mismatch, epoch reuse, or sequence reuse
with different bytes fails before inbox mutation. Authentication errors never disclose
whether a credential ID exists.

Media payload variants:

- `media.loaded` / `media.unloaded`;
- `media.playing` / `media.paused` / `media.stopped`;
- `media.buffering` / `media.waiting` / `media.stalled` / `media.ended`;
- `media.seek_started` / `media.seek_completed`;
- `media.chapter_changed` / `media.track_changed`;
- `media.rate_changed`;
- `media.position_observed`;
- `media.session_restarted`;
- `performance.score_preload` / `performance.score_activate`;
- `performance.mode_changed` / `performance.intensity_changed`;
- `performance.character_changed`;
- `connector.snapshot`.

The V1 JSON wire shape is frozen by these Rust-equivalent definitions. Every struct
uses `deny_unknown_fields`; every enum uses the exact rename shown; no field has a
Serde default; and optional fields are present as explicit JSON `null` rather than
being omitted. The outer `type` and command `operation` tags are mandatory.
Canonical protocol encoding recursively sorts every object key lexicographically by
UTF-8 bytes, preserves array order, emits no insignificant whitespace, uses shortest
integer spelling, and forbids floating-point numbers. The Rust codec serializes to a
`serde_json::Value`, recursively rebuilds each object through a `BTreeMap<String,
Value>`, and then uses `serde_json::to_vec`; it never hashes or compares direct struct
field-order serialization. Decoding followed by encoding must produce those bytes.

```rust
#[serde(tag = "type", content = "body")]
enum MediaProtocolMessageV1 {
    #[serde(rename = "connector.hello")]
    Hello(ConnectorHelloV1),
    #[serde(rename = "connector.welcome")]
    Welcome(ConnectorWelcomeV1),
    #[serde(rename = "media.command")]
    Command(MediaCommandEnvelopeV1),
    #[serde(rename = "media.ack")]
    Ack(MediaAckV1),
    #[serde(rename = "connector.snapshot")]
    Snapshot(ConnectorSnapshotV1),
}

struct ConnectorHelloV1 {
    schema_version: u16,                 // exactly 1
    minimum_protocol_version: u16,       // exactly 1 in V1
    maximum_protocol_version: u16,       // exactly 1 in V1
    source: SourceId,
    client_nonce: Sha256Hex,
    maximum_payload_bytes: u32,          // 1..=262_144
    maximum_in_flight: u16,              // 1..=128
    transport_heartbeat_interval_ms: u32, // 1_000..=30_000
    observation_interval_ms: u32,        // 100..=500
    authentication_mode: AuthenticationModeV1,
    capability_manifest_sha256: Sha256Hex,
    score_hash_algorithms: Vec<HashAlgorithmV1>, // exactly [sha256]
}

struct ConnectorWelcomeV1 {
    schema_version: u16,                 // exactly 1
    protocol_version: u16,               // exactly 1
    source: SourceId,                    // Wizard source ID
    server_nonce: Sha256Hex,
    principal_id: PrincipalId,
    auth_context_id: AuthContextId,
    connector_epoch: u64,                // nonzero
    maximum_payload_bytes: u32,
    maximum_in_flight: u16,
    transport_heartbeat_interval_ms: u32,
    observation_interval_ms: u32,
    capability_manifest_sha256: Sha256Hex,
    score_hash_algorithm: HashAlgorithmV1,
}

struct MediaCommandEnvelopeV1 {
    protocol_version: u16,               // exactly 1
    source: SourceId,
    auth_context_id: AuthContextId,
    connector_epoch: u64,
    sequence: u64,                       // nonzero
    session_id: SessionId,
    timeline_generation: u64,            // nonzero
    media_id: MediaId,
    observed_media_timestamp_us: MediaTimestamp,
    observed_monotonic_us: u64,          // diagnostics only
    correlation_id: CorrelationId,
    ttl_ms: u32,
    command: MediaCommandV1,
}

#[serde(tag = "operation", content = "payload")]
enum MediaCommandV1 {
    #[serde(rename = "media.loaded")]
    Loaded { media_type: MediaTypeV1, mime_type: MimeType,
             duration_us: MediaTimestamp, canonical_source_available: bool,
             score_id: Option<ScoreId> },
    #[serde(rename = "media.unloaded")]
    Unloaded { reason: UnloadReasonV1 },
    #[serde(rename = "media.playing")]
    Playing {},
    #[serde(rename = "media.paused")]
    Paused {},
    #[serde(rename = "media.stopped")]
    Stopped {},
    #[serde(rename = "media.buffering")]
    Buffering {},
    #[serde(rename = "media.waiting")]
    Waiting {},
    #[serde(rename = "media.stalled")]
    Stalled {},
    #[serde(rename = "media.ended")]
    Ended {},
    #[serde(rename = "media.seek_started")]
    SeekStarted { target_us: MediaTimestamp },
    #[serde(rename = "media.seek_completed")]
    SeekCompleted { actual_us: MediaTimestamp },
    #[serde(rename = "media.chapter_changed")]
    ChapterChanged { chapter_id: ChapterId, chapter_index: u32,
                     start_us: MediaTimestamp, end_us: MediaTimestamp },
    #[serde(rename = "media.track_changed")]
    TrackChanged { track_id: TrackId, track_index: u32, kind: TrackKindV1 },
    #[serde(rename = "media.rate_changed")]
    RateChanged { rate: PlaybackRateV1 },
    #[serde(rename = "media.position_observed")]
    PositionObserved { decoded_position_us: MediaTimestamp },
    #[serde(rename = "media.session_restarted")]
    SessionRestarted { previous_session_id: Option<SessionId>,
                       reason: RestartReasonV1 },
    #[serde(rename = "performance.score_preload")]
    ScorePreload { score_id: ScoreId, score_sha256: Sha256Hex,
                   canonical_size_bytes: u64, installed_receipt_id: ReceiptId },
    #[serde(rename = "performance.score_activate")]
    ScoreActivate { score_id: ScoreId },
    #[serde(rename = "performance.mode_changed")]
    ModeChanged { mode: PerformanceModeV1 },
    #[serde(rename = "performance.intensity_changed")]
    IntensityChanged { intensity_percent: u8 },
    #[serde(rename = "performance.character_changed")]
    CharacterChanged { character_id: CharacterId,
                       capability_manifest_sha256: Sha256Hex },
}
```

Closed V1 values are: `authentication_mode = bearer_channel_v1`, hash algorithm
`sha256`, media type `audiobook|music|video`, track kind
`audio|video|text|chapter`, unload reason `user|replaced|error`, restart reason
`source_changed|decoder_reset|connector_recovered`, playback state
`unloaded|paused|playing|stopped|buffering|waiting|stalled|ended`, and performance
mode `audiobook|music|media_companion`. `MimeType` is lowercase ASCII `type/subtype`,
`1..=128` bytes, with no parameters. All IDs are `1..=128` UTF-8 bytes. Percent
values are `0..=100`; chapter and track indices are bounded to `0..=1_000_000`.

`performance.score_preload` names an already installed immutable score; it never
embeds score bytes. Prism first performs authenticated `PUT
/api/avatar/wizard/performance-scores/{score_id}` on the existing Wizard server with
`Content-Type: application/json`, `X-Content-SHA256`, and `Content-Length`. The body
is bounded to 64 MiB. The server streams into an owner-only temporary file, validates
canonical bytes, score ID, manifest binding, length, and SHA-256, atomically renames
it, and returns `{installed_receipt_id, score_id, score_sha256,
canonical_size_bytes}`. That receipt is scoped to the live auth context and score
hash. Partial, mismatched, expired-context, or duplicate-different uploads are deleted
and rejected; an identical installed score returns the original receipt.

```rust
struct MediaAckV1 {
    protocol_version: u16,
    correlation_id: CorrelationId,
    connector_epoch: u64,
    sequence: u64,
    media_id: MediaId,
    session_id: SessionId,
    timeline_generation: u64,
    reducer_revision: u64,
    disposition: AckDispositionV1,
    error: Option<MediaErrorV1>,
    retry_after_ms: Option<u32>,
    authoritative_snapshot_revision: Option<u64>,
}

struct MediaErrorV1 {
    code: MediaErrorCodeV1,
    message: String,
    retryable: bool,
}

struct ConnectorSnapshotV1 {
    active_cues: Vec<ActiveCueSnapshotV1>, // canonical order, at most 4,096
    protocol_version: u16,
    source: SourceId,
    auth_context_id: AuthContextId,
    connector_epoch: u64,
    command_sequence_high_watermark: u64,
    correlation_id: CorrelationId,
    session_id: SessionId,
    timeline_generation: u64,
    media_id: Option<MediaId>,
    observed_media_timestamp_us: MediaTimestamp,
    observed_monotonic_us: u64,
    ttl_ms: u32,
    snapshot_revision: u64,
    media_type: Option<MediaTypeV1>,
    mime_type: Option<MimeType>,
    duration_us: Option<MediaTimestamp>,
    canonical_source_available: bool,
    playback_state: PlaybackStateV1,
    rate: PlaybackRateV1,
    chapter_id: Option<ChapterId>,
    track_id: Option<TrackId>,
    score_id: Option<ScoreId>,
    mode: PerformanceModeV1,
    intensity_percent: u8,
    reduced_motion_profile: ReducedMotionProfileV1,
}

struct ActiveCueSnapshotV1 {
    layer: RegionLayerV1,
    cue_id: CueId,
    resolved_capability_id: CapabilityId,
    cue_local_time_us: MediaTimestamp,
    fallback_index: u8,
    owner_generation: u64,
}
```

ACK `disposition` is the closed set listed below. `error` is non-null exactly for
`rejected` or `snapshot_required`; `retry_after_ms` is non-null only for `overloaded`;
the authoritative snapshot revision is non-null exactly when reconciliation is
possible. The canonical complete protocol transcript fixture is
[`fixtures/media-protocol-v1.minimal.json`](fixtures/media-protocol-v1.minimal.json).
It contains hello, welcome, command, ACK, and snapshot messages and must round-trip
byte-for-byte through the Rust codec.
Snapshot `active_cues` sort by `(layer, cue_id)`, contain no duplicates, require
`cue_local_time_us >= 0`, and must match the active score/generation. Empty snapshots,
one entry, exactly 4,096 entries, 4,097 rejection, duplicate IDs, stale capability,
and wrong generation are mandatory boundary fixtures.

Snapshots are out-of-band reconciliation records, not commands. They do not consume a
command sequence, receive an ACK, or enter the 4,096-entry terminal command replay
cache. `command_sequence_high_watermark` declares the last command sequence whose
effects are represented by the snapshot; the next command must use the following
sequence. Within one connector epoch, `snapshot_revision` is strictly increasing. A
byte-identical repeat of the latest revision is ignored idempotently, an older revision
is rejected as stale without mutation, and reuse of a revision with different bytes
closes the connector as a reconciliation conflict. An accepted snapshot atomically
replaces the reducer's session/generation state and command high-water mark.

Every command envelope includes protocol version, source, auth-context ID, connector
epoch, command sequence, session ID, timeline generation, media ID, observed media
timestamp, monotonic observation timestamp for diagnostics only, correlation ID, and
`ttl_ms`. Snapshots use the separate reconciliation fields defined above.
`ttl_ms` is an integer in `1..=10_000`. Wizard records its own receive tick and
derives the exclusive expiry tick with checked fixed-clock arithmetic; clocks are
never compared across hosts. A command received or dispatched at or after that tick
is rejected as expired. Validation also rejects stale generation, non-monotonic
sequence, wrong media/session, bad rate, invalid timestamp, and unknown score.

Normative wire rules:

- `MediaTimestamp` is a signed 64-bit integer count of microseconds. Browser
  seconds convert with finite/range checks and round-half-away-from-zero; Rust
  converts with checked arithmetic. Negative playback timestamps are rejected.
- Playback rate is `{numerator: u32, denominator: u32}` in reduced form, with
  nonzero denominator and policy bounds of `1/4..=4/1`. Floating-point rate is
  never used in deterministic projection.
- An envelope is at most 256 KiB, identifiers are at most 128 UTF-8 bytes, a
  snapshot has at most 4,096 active cue references, and at most 128 commands may
  be in flight per authenticated connector.
- Each auth context retains at most 4,096 terminal command ACK/error records, keyed by
  sequence. Insertion beyond that bound evicts the smallest sequence. The context
  separately retains only its sequence high-water mark, so storage remains bounded.
  A byte-identical duplicate still in the terminal cache returns the original ACK;
  any sequence at or below the high-water mark that is no longer retained returns
  `replay_window_expired` with `snapshot_required` and is never applied again.
- `(connector_epoch, sequence)` maps one-to-one to the typed inbox ordering key.
  A byte-identical duplicate returns the original ACK. Reuse with different
  bytes returns `sequence_conflict`; gaps return `sequence_gap` and require a
  snapshot. Unknown versions return `unsupported_version` with supported bounds.
- ACKs carry correlation ID, accepted epoch/sequence, media/session/generation,
  resulting reducer revision, and one closed disposition: `applied`, `duplicate`,
  `queued`, `rejected`, or `snapshot_required`. Errors carry one closed code:
  `authentication_required`, `authentication_failed`, `auth_context_expired`,
  `unsupported_version`, `payload_too_large`, `invalid_envelope`, `invalid_ttl`,
  `expired`, `sequence_gap`, `sequence_conflict`, `replay_window_expired`, `stale_generation`,
  `wrong_session`, `wrong_media`, `invalid_timestamp`, `invalid_rate`,
  `unknown_score`, `unknown_capability`, `unsupported_runtime_profile`, `overloaded`,
  or `internal_fault`.
  Error messages are at most 256 UTF-8 bytes and include `retryable` plus the
  authoritative snapshot revision only when reconciliation is possible.
- `authentication_required`, `authentication_failed`, `sequence_conflict`, and
  `internal_fault` close the connector after the error ACK. `auth_context_expired`
  requires reauthentication. `sequence_gap`, `stale_generation`, `wrong_session`,
  `wrong_media`, and `replay_window_expired` require a snapshot before retry.
  `expired` is terminal for that correlation ID. No rejected command advances
  reducer revision or becomes visible.
- Snapshots include media type, MIME type, duration, canonical source-link
  availability (never the URL), playback state, rate, chapter/track, score ID,
  mode, intensity, reduced-motion state, and the complete timeline generation.
- Backpressure is explicit: full inboxes return `overloaded` without mutation;
  the connector retries only after `retry_after_ms` and snapshot reconciliation.

## Clock Model

The browser media element is authoritative for observed decoded playback.

The hello/welcome negotiation carries two independent intervals. Standard WebSocket
Ping/Pong uses `transport_heartbeat_interval_ms` only to determine connector liveness.
Playback observations use `observation_interval_ms`, negotiated in `100..=500 ms`, and
never depend on Ping/Pong traffic.

PrismGT emits:

- discrete acknowledged state changes immediately;
- bounded periodic position observations while playing;
- a complete snapshot on connector establishment/reconnection;
- a new timeline generation after discontinuities;
- playback observations no less often than the negotiated observation interval while
  playing, seeking, buffering, waiting, or stalled.

Wizard records the most recent accepted observation `(media_time_us, receive_tick,
rate_ratio, playback_state, generation, observation_sequence)`. Between valid
observations it projects media time with checked integer arithmetic. The
observation lease is exactly `min(2 * observation_interval_ms, 1_000 ms)` using
checked integer arithmetic. Lease expiry atomically freezes score time, blocks new cue activation,
and emits `observation_lease_expired`; it never extrapolates through connector
silence.

`seek_started` increments the timeline generation, atomically suspends the
scheduler, clears every old-generation active/queued cue, and switches regional
owners to their declared safe hold. `seeking`, `buffering`, `waiting`, and
`stalled` states freeze projection and cannot activate cues. Only one complete
`seek_completed` or reconnect snapshot carrying media/session/generation,
timestamp, duration, rate, playback state, chapter/track, and score ID may rebase
and resume the scheduler. Late events from the prior generation are rejected
before visible mutation.

Pause and ended freeze score time. Resume begins only from a fresh authoritative
observation. Playback rate changes preserve media time and change the rational
projection slope. Small error may be slewed inside a frozen acceptance threshold;
large error causes a generation-changing atomic rebase. No cue is keyed directly
to wall-clock time.

## Performance Score Wire Model

The canonical format is UTF-8 JSON with lexicographically sorted object keys,
array order preserved, no insignificant whitespace, shortest round-trippable
integer spelling, and no floating-point numbers. `score_id` is SHA-256 of the
canonical bytes with the `score_id` field omitted. Every duration and boundary is
an integer `MediaTimestamp` in microseconds.

```rust
struct PerformanceScoreV1 {
    header: ScoreHeaderV1,
    checkpoints: Vec<ScoreCheckpointV1>,
    tracks: Vec<ScoreTrackV1>,
}

struct ScoreHeaderV1 {
    schema_version: u16,                 // exactly 1
    score_id: Sha256Hex,
    media_id: MediaId,
    media_sha256: Sha256Hex,
    character_id: CharacterId,
    capability_manifest_sha256: Sha256Hex,
    animation_library_sha256: Sha256Hex,
    motion_graph_sha256: Sha256Hex,
    transcript_version: ArtifactVersion,
    alignment_version: ArtifactVersion,
    analysis_version: ArtifactVersion,
    compiler_version: ArtifactVersion,
    validator_version: ArtifactVersion,
    duration_us: MediaTimestamp,
    timebase_hz: u32,                    // exactly 1_000_000
    seed: u64,
    reduced_motion_profile: ReducedMotionProfileV1,
    provenance: ScoreProvenanceV1,
}

struct ScoreCueV1 {
    cue_id: CueId,
    cue_type: CueTypeV1,
    start_us: MediaTimestamp,
    end_us: MediaTimestamp, // exclusive: [start_us, end_us)
    layer: RegionLayerV1,
    priority: u16,
    capability_id: CapabilityId,
    fallback_capability_ids: Vec<CapabilityId>,
    transition_in: TransitionSpecV1,
    transition_out: TransitionSpecV1,
    payload: CuePayloadV1,
}

struct ScoreTrackV1 {
    track_id: TrackId,
    layer: RegionLayerV1,
    cues: Vec<ScoreCueV1>,
}

struct ScoreCheckpointV1 {
    at_us: MediaTimestamp,
    next_cue_indices: Vec<u32>, // exactly one entry per track
    regions: Vec<RegionCheckpointV1>, // exactly one entry per RegionLayerV1
}

struct RegionCheckpointV1 {
    layer: RegionLayerV1,
    active_cues: Vec<ActiveCueCheckpointV1>,
    owner_generation: u64,
}

struct ActiveCueCheckpointV1 {
    cue_id: CueId,
    resolved_capability_id: CapabilityId,
    cue_local_time_us: MediaTimestamp,
    fallback_index: u8, // 0 = primary; 1..=4 indexes fallback_capability_ids
}

struct ScoreProvenanceV1 {
    kind: ScoreProvenanceKindV1, // manual | deterministic_compiler | imported
    source_artifact_sha256: Sha256Hex,
}
```

`animation_library_sha256` binds the manifest's
`runtime_geometry_authority_sha256`, not the compressed imported pose archive.
`motion_graph_sha256` and `capability_manifest_sha256` must likewise equal the exact
runtime manifest values. The canonical fixture must pass full manifest validation;
fixtures intentionally expected to mismatch are not promotion evidence.

All score structs use `deny_unknown_fields`. IDs and version strings are `1..=128`
UTF-8 bytes; SHA values are exactly 64 lowercase hexadecimal bytes. Duration is
`1..=604_800_000_000` microseconds. A score is at most 64 MiB canonical bytes,
contains `1..=32` tracks, `1..=100_000` cues total, `1..=20_160` checkpoints, at
most 4,096 simultaneously active cues, and no collection or arithmetic operation
may exceed those bounds. Track IDs and cue IDs are unique. Times are nonnegative,
checked against duration, and every cue has `start_us < end_us`.

`RegionLayerV1` is closed over `mode`, `root`, `body`, `gesture`, `gaze`, `face`,
`speech`, `blink`, `prop_effect`, `secondary_motion`, and `stillness`. `CueTypeV1`
is closed over `mode`, `locomotion`, `body_pose`, `gesture`, `gaze`, `expression`,
`viseme`, `blink`, `prop_effect`, `dance_phrase`, and `stillness`.
`CuePayloadV1` is a tagged closed enum with these exact variants and fields:

- `mode { mode }`, where mode is `audiobook`, `music`, or `media_companion`;
- `locomotion { target_x_millicells, target_y_millicells, facing, speed_percent }`;
- `body_pose { weight_shift_percent }`;
- `gesture { phase, intensity_percent }`, phase `prepare|stroke|hold|recover`;
- `gaze { target, head_weight_percent, eye_weight_percent }`;
- `expression { emotion, intensity_percent }`;
- `viseme { viseme, weight_percent }`;
- `blink { state }`, state `open|closing|closed|opening`;
- `prop_effect { intensity_percent }`;
- `dance_phrase { beat_phase_q32, energy_percent }`;
- `stillness { locked_layers }`.

The closed V1 scalar domains are exact and reuse the Rust runtime wire spellings:

- `ReducedMotionProfileV1`: `full|reduced|minimal`;
- locomotion `facing`: `south|southwest|west|northwest|north|northeast|east|southeast`;
- gaze `target`: `user|content|staff|down|away_left|away_right|neutral`;
- expression `emotion`: `neutral|joy|sadness|anger|fear|shame|disgust|surprise|pride|guilt|love`;
- `viseme`: `rest|mbp|fv|th|dtln|kg|chsh|sz|r|a|e|i|o|u`.

No other string value is valid in schema version 1.

Every percent is `0..=100`; stage coordinates are each
`-1_000_000..=1_000_000` millicells; `beat_phase_q32` is a full-range `u32` fixed
point phase. Transition kind is `cut|linear|authored`, duration is
`0..=10_000_000` microseconds, and `cut` requires zero duration. Payload type,
cue type, and layer must match this frozen compatibility table:

| Cue and payload type | Permitted layer |
|---|---|
| `mode` | `mode` |
| `locomotion` | `root` |
| `body_pose`, `dance_phrase` | `body` |
| `gesture` | `gesture` |
| `gaze` | `gaze` |
| `expression` | `face` |
| `viseme` | `speech` |
| `blink` | `blink` |
| `prop_effect` | `prop_effect` |
| `stillness` | any layer named in `locked_layers`; `mode` is forbidden |

A track's declared layer must equal every cue layer it contains. A stillness cue uses
its own declared capability on its cue layer and may name at most eight unique locked
layers in canonical enum order. Each other named layer freezes its current resolved
sample, local time, and owner for the half-open stillness interval. If a named layer
has no current owner, that region applies the generated safe-idle profile above;
there is no guessed layer-specific capability. `secondary_motion` is checkpointed and
runtime-owned but receives no direct V1 score cue; it follows the resolved body,
prop, and authored-transition policies. The standalone `stillness` layer records
global lock ownership and accepts only stillness cues whose `locked_layers` contains
every currently active lockable layer.

Tracks are sorted by `(layer, track_id)`. Within each track, cues are sorted by
`(start_us, Reverse(priority), cue_id)`. Intervals are half-open. At equal time in
one layer, highest priority wins.
Equal-priority overlap is invalid except for `prop_effect`: active prop-effect cues
compose in ascending cue-ID order by taking the sorted union of distinct capability
IDs and checked integer addition of `intensity_percent`, saturated exactly at 100.
No other payload is additive, and no floating-point blend arithmetic is permitted.

Each cue declares `1..=4` ordered fallback capability IDs, all distinct from the
primary and valid for the same type/layer. Validation resolves the entire chain
against the bound manifest. If no primary or fallback can resolve before activation,
the score is rejected. If capability availability changes after activation, runtime
tries the declared chain in order, emits `capability_fallback` for each substitution,
and on exhaustion applies the manifest's explicit `safe_idle`, blocks only
the affected track, and emits `fallback_exhausted`. It never guesses an ID or resumes
that track without a new score generation.

Checkpoints are sorted by `at_us`; every checkpoint's `regions` array is in the exact
`RegionLayerV1` declaration order shown above; `next_cue_indices` uses the canonical
track order; and each region's `active_cues` entries are sorted by cue ID. Active-cue
entries contain one independently resolved capability, local offset, and fallback
index for every active cue. This is
required even when a layer normally has one winner because `prop_effect` composes
multiple cues. `fallback_index` must be zero for the primary or `1..=4` for the
corresponding declared fallback and must resolve to `resolved_capability_id`.

Checkpoints are required at time zero, chapter/section boundaries, after every
seek-safe discontinuity, and at most every 30 seconds. A checkpoint contains the
complete reconstructable state for all eleven region layers, active cue IDs, local
cue offsets, resolved capability/fallback selection, regional owner/generation, and
the next cue index for every track. Checkpoints are strictly increasing and the
first is exactly zero.
Arbitrary seek binary-searches the latest checkpoint at or before target, restores
it, then replays indexed cue boundaries through the target without rendering
intermediate frames. Schema migrations are explicit pure Rust transforms from a
named source version and must preserve the pre-migration bytes and hash.

The canonical complete fixture is
[`fixtures/performance-score-v1.minimal.json`](fixtures/performance-score-v1.minimal.json).
Its body contains every mandatory header, transition, payload, checkpoint, track,
and fallback field. Implementation must parse, validate, canonicalize, omit only
`header.score_id` for hashing, and reproduce the embedded score ID byte-for-byte.

## Runtime Data Flow

```text
media element observation
  -> Prism browser adapter
  -> Prism Rust media-session validation/persistence
  -> connector envelope
  -> Wizard existing WebSocket/command decoder
  -> bounded ordered inbox
  -> media timeline reducer
  -> deterministic cue scheduler
  -> regional animation ownership
  -> existing controller/motion director
  -> renderer
  -> frame/cue/sync telemetry
```

## Preprocessing Data Flow

```text
immutable media
  -> hash/probe/decode
  -> transcript discovery or explicit opt-in HTTPS job to the Rust server worker
  -> inventoried server Whisper CLI (invoked locally by that worker without a shell)
  -> transcript verification
  -> word/phrase/sentence/paragraph/chapter alignment
  -> deterministic narrative feature extraction
  -> optional governed structured LLM analysis
  -> deterministic DSP music analysis
  -> capability-constrained score compiler
  -> independent score validator
  -> versioned cache and editor override layer
```

Each step writes an atomic checkpoint containing input hashes, tool versions,
configuration, output hash, warnings, and completion state. Cancellation leaves a
resumable checkpoint; it never publishes a partial score as playable.

## Governed Whiz Action

The button is disabled when the active media record lacks a valid canonical URL.
On explicit activation:

1. Frontend sends media ID and current metadata revision, not an arbitrary URL.
2. Prism Rust loads the canonical URL from storage.
3. CDISS dispatches a new closed `source.open` governed action class through the
   same approval, policy, payload-hash, audit, replay, and expiry machinery used by
   existing governed actions. No X-publication permit is reused or relabeled.
4. The policy validates scheme, host syntax, provenance, metadata revision, and
   exact user-action correlation. It records the canonical URL hash and returns a
   short-lived (maximum 10 seconds), single-use permit bound to media ID, URL hash,
   frontend instance, and action nonce. Replay, expiry, mismatch, or cancellation
   fails closed and is audited.
5. Desktop invokes the Tauri shell opener only after the Rust sidecar consumes the
   permit. Hosted mode synchronously opens an `about:blank` window from the user
   gesture, uses `noopener,noreferrer`, completes the governed round trip, then
   navigates that handle; denial/timeout closes it and shows a bounded error. This
   avoids depending on user activation surviving an asynchronous request.
6. Success/failure and opener mechanism are recorded. Media playback is unchanged
   unless platform behavior explicitly requires otherwise.

Wizard never receives the URL and cannot activate this action.

## Privacy And Provider Boundary

- Local media and transcript data remain local by default. Provided-transcript
  parsing and deterministic DSP execute locally.
- Server Whisper transcription is a separate, explicit opt-in remote transfer.
  Before upload, Prism shows the inventoried server/tool/model identity, transport,
  data scope, retention and deletion policy, and audit record. Cancellation and
  completion follow the documented server deletion policy; declining leaves media
  local and preserves the provided-transcript path.
- The runtime client uses a dedicated least-privilege transcription credential and
  validated HTTPS. It never receives or uses the deployment SSH key. The Rust server
  worker deletes successful or cancelled job content immediately after acknowledgement,
  deletes abandoned/failed content within one hour, and retains content-free deletion
  receipts and tool/model hashes for audit.
- Optional LLM analysis must show provider/model, requested data scope, and local
  alternative before dispatch.
- Provider calls use the existing governed Prism model gateway and write auditable
  job metadata without storing secrets.
- Playback never requires a live LLM call.
