# Rust Chatbot Animation Implementation Plan

Role: `MOTION`
Plan date: 2026-07-13
Program prefix: `RCHAT-ANIM`
Production crate: `rust/wizard_avatar_engine`
Production endpoint: `http://127.0.0.1:8787/`
Research input: `../research/02-chat-animation-motion.md`
Status vocabulary: `BLOCKED`, `READY`, `IN_PROGRESS`, `REVIEW`, `ACCEPTED`

## 1. Objective

Turn the integrated 89-geometry Rust Wizard Joe engine into a first-class
chatbot visualizer. The delivered character must perform listening, thinking,
response preparation, speaking, clarifying, tool waiting, error acknowledgement,
celebration, and interruption recovery. It
must retain realistic contact, coherent silhouettes, smooth authored timing,
deterministic variation, repeatable clips, and screenshot-per-frame evidence.

This plan is complete when:

- all 89 geometries are classified and reachable;
- all 50 WJFL geometries are used by an authored clip, transition, facial
  accent, or explicitly approved showcase path;
- every conversational state has accepted normal and reduced-motion behavior;
- speech visemes, face emotion, gaze, blink, staff/effects, and secondary
  motion coexist without resetting unowned channels;
- every graph edge, loop boundary, interruption, and recovery passes strict
  frame, anchor, contact, attachment, codec, and presentation gates;
- two deterministic evidence runs produce identical hashes;
- a real browser on port 8787 shows the accepted Rust output with zero console
  errors;
- no Python production authority and no runtime PNG reuse are present.

## 2. Binding constraints

1. Production implementation is Rust. Cargo is the only production build and
   test authority for animation behavior.
2. Python may not generate production poses, direct animation, run the server,
   validate acceptance, or appear in CI gates for this program.
3. Intake PNGs and evidence PNGs may not be loaded by the engine or browser.
   Runtime geometry comes only from the embedded compiled Rust asset.
4. The v4 pose asset remains immutable throughout this program.
5. The implementation starts only after the 50-WJFL integration gate is
   committed and pushed.
6. The current clip and pose playback path remains available as a rollback
   profile until the new graph passes final acceptance.
7. Every behavioral change is keyed to a work ID and has an owner, dependency,
   test, evidence path, threshold, rollback, and acceptance record.
8. The shared Git index, shared server process, shared evidence directory, and
   conflict hotspots are controlled by the integration coordinator.

## 3. Start gate: all poses before chatbot work

No work item after `RCHAT-ANIM-009` may enter `IN_PROGRESS` until all start-gate
checks are green on one commit.

| Gate | Required evidence | Threshold | Owner | Failure action |
|---|---|---:|---|---|
| `RCHAT-ANIM-001` | v4 loader contract | 80 catalog, 79 imported geometries, 1 alias | POSE/INT | Return to pose integration |
| `RCHAT-ANIM-002` | runtime pose census | 89 unique geometries | POSE/INT | Do not start chatbot branch |
| `RCHAT-ANIM-003` | WJFL admission ledger | 50 unique admissions, `WJFL-01..40` and `WJFL-51..60` | POSE/INT | Repair intake/compiler |
| `RCHAT-ANIM-004` | WJFL runtime resolution test | 50/50 | POSE/INT | Repair v4 promotion |
| `RCHAT-ANIM-005` | static frame census | 89 PNGs, zero quality failures | QA/INT | Repair geometry/semantics |
| `RCHAT-ANIM-006` | authored transition test | all authored edges pass | POSE/INT | Repair neighbors/recipes |
| `RCHAT-ANIM-007` | clip coverage test | every imported record covered | POSE/INT | Repair current clip coverage |
| `RCHAT-ANIM-008` | deterministic v4 evidence | two streams identical; decode/presentation parity 100% | QA/INT | Regenerate and investigate |
| `RCHAT-ANIM-009` | clean checkpoint | asset, source, tests, and evidence committed and pushed | INT | No chatbot production edits |

Current inspection found the expected 80/79/1 v4 contract, 89 runtime
geometries, 50 WJFL admissions, 50 WJFL runtime-resolution assertions, and a
zero-failure 89-frame static census. It also found the v4 animation evidence in
progress rather than finalized. The coordinator must rerun and record the full
gate; this document does not substitute for execution evidence.

## 4. Ownership and one-writer rules

### 4.1 Motion-owned new files

The MOTION implementation lane may own these new files:

```text
rust/wizard_avatar_engine/src/chat_performance.rs
rust/wizard_avatar_engine/src/motion_graph.rs
rust/wizard_avatar_engine/src/motion_director.rs
rust/wizard_avatar_engine/src/facial_performance.rs
rust/wizard_avatar_engine/src/secondary_motion.rs
rust/wizard_avatar_engine/src/chat_motion_evidence.rs
rust/wizard_avatar_engine/assets/wizard_chat_motion_graph.v1.json

rust/wizard_avatar_engine/tests/chat_motion_graph.rs
rust/wizard_avatar_engine/tests/chat_turn_states.rs
rust/wizard_avatar_engine/tests/chat_coarticulation.rs
rust/wizard_avatar_engine/tests/chat_secondary_motion.rs
rust/wizard_avatar_engine/tests/chat_interruptions.rs
rust/wizard_avatar_engine/tests/chat_reduced_motion.rs
rust/wizard_avatar_engine/tests/chat_transition_matrix.rs
rust/wizard_avatar_engine/tests/chat_motion_evidence.rs
```

### 4.2 Serial integration hotspots

These paths require a coordinator lock and may not be edited in parallel:

| Path | Motion work ID | Required dependency | Required handoff |
|---|---|---|---|
| `src/lib.rs` | `RCHAT-ANIM-031` | contract modules compile | exported module list |
| `src/state.rs` | `RCHAT-ANIM-032` | shared state contract approved | backward-compatible state fixture |
| `src/controller.rs` | `RCHAT-ANIM-140` | director and interruption tests pass | command mapping and generation report |
| `src/pose.rs` | `RCHAT-ANIM-111` | secondary constraints approved | attachment/topology regression report |
| `src/pose_clip.rs` | `RCHAT-ANIM-042` | graph evaluator accepted in shadow mode | legacy adapter equivalence report |
| `src/pose_playback.rs` | `RCHAT-ANIM-043` | transition recipe tests pass | interruption/restore report |
| `src/renderer.rs` | `RCHAT-ANIM-112` | facial and secondary channel contracts approved | screenshot delta report |
| `src/pose_evidence_main.rs` | `RCHAT-ANIM-170` | evidence schema frozen | complete evidence manifest |
| `src/server.rs` | `RCHAT-ANIM-145` | systems API envelope frozen | live endpoint smoke |
| `web/wizard.js` | `RCHAT-ANIM-176` | systems/browser owner approval | browser control and reduced-motion smoke |

The MOTION lane does not modify the v4 pose compiler, intake files, v4 asset,
codec, hub fanout, or deployment configuration.

## 5. Frozen Rust contracts

Contract names may be adjusted once during `RCHAT-ANIM-019` to follow current
crate conventions. After contract gate C1, field meanings and enum variants are
frozen. Any change requires a decision record and acknowledgements from MOTION,
runtime, systems, and QA owners.

### 5.1 Chat performance intent

`src/chat_performance.rs` defines the semantic input consumed by animation:

```rust
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ChatTurnState {
    Idle,
    Listening,
    Thinking,
    PreparingResponse,
    Speaking,
    Clarifying,
    ToolWait,
    Error,
    Celebrating,
    Interrupted,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MotionProfile { Full, Reduced }

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Emotion {
    Neutral, Joy, Sadness, Anger, Fear, Shame,
    Disgust, Surprise, Pride, Guilt, Love,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ChatPerformanceIntent {
    pub schema_version: u16,          // exactly 1
    pub intent_id: String,
    pub source_sequence: u64,
    pub turn_state: ChatTurnState,
    pub emotion: Emotion,
    pub intensity: u8,                // 0..=100
    pub confidence: u8,               // 0..=100
    pub urgency: u8,                  // 0..=100
    pub speech: Option<SpeechTrack>,
    pub gaze: GazeIntent,
    pub gesture_hint: Option<GestureHint>,
    pub motion_profile: MotionProfile,
    pub deterministic_seed: u64,
    pub issued_tick: u64,
    pub minimum_hold_ticks: u16,
    pub expires_tick: Option<u64>,
}
```

The ten variants serialize exactly as `idle`, `listening`, `thinking`,
`preparing_response`, `speaking`, `clarifying`, `tool_wait`, `error`,
`celebrating`, and `interrupted`. No shortened state alias is accepted at the
wire boundary or stored in graph/profile data.

Validation rejects unknown enum values, intensity/confidence/urgency over 100,
non-monotonic sequence, expired intent, unsupported schema, invalid cue order,
and direct pose IDs. The animation layer never consumes private message text.

### 5.2 Speech and viseme track

```rust
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Viseme {
    Rest, MBP, FV, TH, DTLN, KG, CHSH, SZ, R, A, E, I, O, U,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RenderedMouthPose {
    Closed,
    OpenSmall,
    OpenMedium,
    OpenWide,
    Rounded,
    Smile,
    Frown,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct VisemeCue {
    pub start_tick: u32,
    pub peak_tick: u32,
    pub end_tick: u32,
    pub viseme: Viseme,
    pub strength: u8,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SpeechMarker {
    pub tick: u32,
    pub kind: SpeechMarkerKind, // phrase_start|accent|clause_end|turn_end
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SpeechTrack {
    pub utterance_id: String,
    pub duration_ticks: u32,
    pub cues: Vec<VisemeCue>,
    pub markers: Vec<SpeechMarker>,
}
```

`SpeechTrack.cues` always carries the canonical semantic `Viseme`; it never
carries a rendered pose or legacy renderer state. The exhaustive semantic-to-
render mapping is:

| Semantic viseme | `RenderedMouthPose` |
|---|---|
| `Rest`, `MBP` | `Closed` |
| `FV`, `TH`, `DTLN`, `SZ` | `OpenSmall` |
| `KG`, `CHSH` | `OpenMedium` |
| `A` | `OpenWide` |
| `R`, `O`, `U` | `Rounded` |
| `E`, `I` | `Smile` |

`Frown` is reserved for emotion-biased rest and never replaces or changes a
timed semantic viseme. Rendering crosses one compatibility boundary:
`Viseme -> RenderedMouthPose -> MouthShape`. The first conversion is the exact
14-value mapping above. The second is one exhaustive
`impl From<RenderedMouthPose> for MouthShape` feeding the protocol-v1 legacy
renderer; `MouthShape` is not part of `SpeechTrack` or any semantic event.

Cues are ordered, nonoverlapping after normalization, and quantized before they
enter the director. A track with no cues uses only the versioned deterministic
duration envelope seeded by utterance ID and alternates readable open/rest poses
without claiming phonetic accuracy. No runtime component receives response text
or performs text-to-phoneme inference.

### 5.3 Gaze contract

```rust
pub enum GazeTarget { User, Content, Staff, Down, AwayLeft, AwayRight, Neutral }

pub struct GazeIntent {
    pub target: GazeTarget,
    pub hold_ticks: u16,
    pub return_to_user: bool,
}

pub struct GazeState {
    pub target: GazeTarget,
    pub eye_offset_x: i8,       // -1..=1 cells
    pub eye_offset_y: i8,       // -1..=1 cells
    pub head_bias_x: i8,        // -1..=1 cells
    pub generation: u64,
    pub entered_tick: u64,
    pub release_tick: u64,
}
```

Gaze state never moves the contact root. Reduced motion disables
micro-saccades but retains deliberate target changes.

### 5.4 Motion graph contract

`assets/wizard_chat_motion_graph.v1.json` is embedded with `include_str!` and
validated once through `OnceLock<Result<MotionGraph, String>>`. Required
top-level fields:

```text
schema_version = 1
graph_id
asset_schema_version = 4
required_runtime_geometry_count = 89
required_wjfl_geometry_count = 50
default_clip_id
pose_coverage
clips
transition_recipes
edges
turn_state_profiles
emotion_profiles
variant_sets
reduced_motion_overrides
```

Every pose coverage row is:

```rust
pub struct PoseCoverage {
    pub pose_id: String,
    pub use_kinds: Vec<PoseUseKind>, // clip|transition|face_accent|showcase
    pub capability_tier: CapabilityTier,
    pub approved_facings: Vec<Direction>,
}
```

Every clip is:

```rust
pub struct MotionClip {
    pub clip_id: String,
    pub family: ClipFamily,
    pub loop_mode: LoopMode,       // once|repeat|marked_segment
    pub phase_source: PhaseSource, // time|distance|wing|speech
    pub entry_marker: MotionMarker,
    pub exit_markers: Vec<MotionMarker>,
    pub minimum_hold_ticks: u16,
    pub interrupt_policy: InterruptPolicy,
    pub owned_channels: ChannelMask,
    pub samples: Vec<MotionSample>,
    pub loop_start_sample: Option<usize>,
    pub loop_end_sample: Option<usize>,
    pub reduced_motion_clip_id: Option<String>,
}

pub struct MotionSample {
    pub pose_id: String,
    pub hold_ticks: u16,
    pub transition_recipe_id: String,
    pub markers: Vec<MotionMarker>,
    pub support: SupportContact,
    pub root_offset: [i8; 2],
    pub secondary_profile_id: String,
}
```

Marker vocabulary is closed for schema v1:

```text
entry, anticipation, commit, release, impact, apex, accent_hold,
left_contact, left_release, right_contact, right_release,
staff_plant, staff_release, hand_plant, hand_release,
wing_up, wing_down, glide, phrase_start, speech_accent,
clause_end, recover, settled, loop_start, loop_end, exit
```

### 5.5 Transition recipe contract

```rust
pub struct TransitionRecipe {
    pub recipe_id: String,
    pub source_families: Vec<ClipFamily>,
    pub target_families: Vec<ClipFamily>,
    pub timing: TransitionTiming,
    pub duration_ticks: TickRange,
    pub handoff_marker: MotionMarker,
    pub contact_policy: ContactPolicy,
    pub root_policy: RootPolicy,
    pub region_policy: RegionPolicy,
    pub secondary_policy: SecondaryPolicy,
    pub interrupt_windows: Vec<InterruptWindow>,
    pub fallback_recipe_id: Option<String>,
}
```

Schema v1 includes the named recipes from research:
`coherent_handoff`, `contact_sync`, `anticipation_action_recover`,
`airborne_arc`, `brace_transfer`, `face_coarticulation`,
`secondary_settle`, and `reduced_motion_handoff`.

No edge may omit a recipe. No recipe may select a runtime PNG or arbitrary
cell-dissolve algorithm.

### 5.6 Channel state contract

```rust
pub enum PerformanceChannel {
    BaseBody, UpperBody, FaceEmotion, Speech, Gaze, Blink,
    StaffEffect, Secondary,
}

pub struct ChannelLease {
    pub generation: u64,
    pub priority: u8,
    pub entered_tick: u64,
    pub minimum_hold_until: u64,
    pub expires_tick: Option<u64>,
    pub interrupt_policy: InterruptPolicy,
    pub recovery_policy: RecoveryPolicy,
}

pub struct PerformanceState {
    pub turn_state: ChatTurnState,
    pub emotion: Emotion,
    pub selected_variant_id: String,
    pub clip_id: String,
    pub sample_index: usize,
    pub clip_generation: u64,
    pub active_markers: Vec<MotionMarker>,
    pub channels: BTreeMap<PerformanceChannel, ChannelLease>,
    pub gaze: GazeState,
    pub semantic_viseme: Viseme,
    pub rendered_mouth_pose: RenderedMouthPose,
    pub motion_profile: MotionProfile,
    pub deterministic_seed: u64,
}
```

The public `WizardState` receives a serializable summary, not private speech
content or the full graph. The renderer receives only `RenderedMouthPose` and
converts it through the exhaustive legacy `MouthShape` boundary.

### 5.7 Secondary-motion contract

```rust
pub struct SecondaryOffsets {
    pub hat: [i8; 2],
    pub beard: [i8; 2],
    pub robe: [i8; 2],
    pub staff_tip: [i8; 2],
    pub wing_left: [i8; 2],
    pub wing_right: [i8; 2],
}
```

Each offset is bounded to one cell in schema v1. Staff tip offset becomes zero
while planted. Wing offsets require attachment validation. Offsets are derived
from quantized acceleration, clip markers, and a deterministic profile; they
never use wall time.

### 5.8 Frame evidence contract

Every captured frame row includes:

```text
schema_version, commit_sha, asset_hash, graph_hash, seed,
scenario_id, command_log_hash, simulation_tick, render_index,
turn_state, emotion, motion_profile, selected_variant_id,
clip_id, sample_index, active_markers, transition_recipe_id,
channel_generations, pose_id, previous_pose_id, pose_handoff,
support_contacts, contact_points, contact_drift,
root, face_anchor, mouth_anchor, staff_hand, staff_top,
secondary_offsets, topology_metrics,
source_frame_sha256, codec_tag, decoded_frame_sha256,
presented_frame_sha256, presentation_accepted
```

The manifest records frame count, screenshot count, scenario count, graph-edge
count, pass-one/pass-two stream hashes, parity results, quality failures, and
the exact threshold profile.

## 6. Required 89-geometry taxonomy

`RCHAT-ANIM-020` creates a machine-validated classification for every runtime
geometry. Minimum categories are:

| Taxonomy group | Required coverage |
|---|---|
| Directional baseline | all baseline front/back/profile/walk/explain/cast geometries |
| Ground locomotion | walk, run, start, stop, turn-compatible keys |
| Flight locomotion | takeoff-compatible, hover, flap, glide, bank, fall, landing |
| Guard and staff | windup, block, thrust, spin, plant, cast, recover |
| Reaction and celebration | crouch, jump, fall-back, brace, victory, celebration |
| Social gesture | idle, greeting, thinking, explain, point, sincere, playful, shush |
| Full feeling accents | ten `feeling_*_full` geometries |
| Close-reference accents | ten `feeling_*_close` geometries |

Capability tiers are explicit:

```text
directional_base    authored/procedural for eight-direction travel
front_performance   rich front-facing acting
diagonal_flight     limited southeast/southwest flight acting
face_accent         full-body-safe feeling emphasis
showcase_only       accepted only with written reason and fallback
```

Acceptance: 89 unique geometry IDs and 50 WJFL candidate IDs appear exactly
once in coverage; no unknown ID; every non-showcase pose appears in at least one
clip or transition; `showcase_only` requires an owner and rationale.

## 7. Conversational performance recipes

### 7.1 Idle

Entry: any settled recovery.

Behavior: stable both-feet or both-feet-and-staff contact, sparse blink,
occasional one-cell beard/robe settle, no repeated gesture. Optional greeting
may occur only on an explicit greeting event.

Exit: immediate to `Listening`, 3-6 tick anticipation to `PreparingResponse` or
`Clarifying`, and the shortest safe recovery to all other states.

### 7.2 Listening

Primary geometry family: `front_idle_wings`, baseline front idle, sincere and
thinking micro-accents.

Behavior: gaze to user, closed mouth, tiny deterministic nod no more than once
per 2.5 seconds, no staff flourish. Long listening may select one approved
weight shift without changing contact unexpectedly.

### 7.3 Thinking

Primary keys: `front_thinking_hand_chin_wings`, `front_shush_wings`,
`feeling_surprise_close` at low intensity only when appropriate.

Recipe: `Listening` settle -> gaze avert -> thinking anticipation -> hold ->
gaze return -> recover. `ToolWait` may reuse the hold segment but not the same
facial meaning.

### 7.4 Preparing response

Primary keys: baseline front idle, sincere, open-hand explain anticipation, and
restrained thinking-to-explain bridge poses.

Recipe: settle the previous state -> return gaze toward the user -> acquire the
prepared speech/gesture generations -> select a phrase-start anticipation ->
hold with a closed mouth. Only an explicit speech-start event advances to
`Speaking`; cancellation or replacement recovers without emitting a stale
viseme or committed gesture.

### 7.5 Speaking

Primary keys: open-hand explain, both-hands explain, direct/side point, sincere,
magic accent when explicitly requested.

Recipe: phrase-start anticipation, speech visemes throughout, zero or one
gesture accent per clause, gesture peak within two render frames of speech
accent, recovery at clause end, mouth closed by turn end.

### 7.6 Clarifying

Primary keys: open-hand explain, side point, sincere, surprise close at low
intensity.

Recipe: direct gaze, questioning brow, open-hand accent, 8-18 tick hold, return
to `Listening`. No `Celebrating` or magic variant.

### 7.7 Tool wait

Primary keys: front idle, front idle wings, thinking hand/chin, restrained
magic spark where product semantics allow it.

Recipe: one entry acknowledgement, repeatable patient loop, deterministic gaze
return, optional low-density effect, no speech mouth movement. Stop exits at
`loop_end` or within 12 ticks.

### 7.8 Error

Primary keys: worried/fear/shame/guilt accents and reaction/crouch keys at low
intensity.

Recipe: 3-6 tick surprise acknowledgement, 6-12 tick concern hold, composed
recovery, direct gaze. Do not loop negative feeling poses.

### 7.9 Celebrating

Primary keys: joy, pride, victory cast, celebration jump/staff-up.

Recipe: anticipation -> one action accent -> 6-18 tick hold -> full recovery.
Default intensity must not enter an airborne pose. High intensity may jump only
when reduced motion is off and no speech/tool-wait lock owns the base body.

### 7.10 Interrupted

Immediate actions: invalidate older speech and optional-gesture generations,
close mouth within two render frames, return gaze to user, exit committed body
action at earliest safe marker, then enter `Listening`.

Acceptance: no stale pose, viseme, effect, or queued gesture appears after the
new generation is visible.

## 8. Work breakdown and accountability ledger

All rows begin `BLOCKED` until their dependency is accepted. The owner updates
the program tracker when state changes and links the exact commit and evidence.

### Wave A: contracts and coverage

| ID | Work | Owner | Depends on | Deliverable | Acceptance and evidence | Rollback |
|---|---|---|---|---|---|---|
| `RCHAT-ANIM-010` | Freeze motion requirements and thresholds | MOTION | 009 | approved contract note | all role acknowledgements; no unresolved field meaning | remain on legacy |
| `RCHAT-ANIM-015` | Define graph schema v1 | MOTION | 010 | `motion_graph.rs` types and graph JSON skeleton | good fixture loads; malformed fixtures reject | delete unpromoted graph file |
| `RCHAT-ANIM-019` | Freeze shared Rust interfaces | MOTION/CORE/SYS/QA | 015 | signed interface map | C1 gate recorded | return to schema draft |
| `RCHAT-ANIM-020` | Classify 89 geometries | MOTION | 019 | `pose_coverage` in graph asset | 89/89 and WJFL 50/50; zero unknown/duplicate | no graph promotion |
| `RCHAT-ANIM-021` | Author capability tiers and fallbacks | MOTION | 020 | graph tier/fallback rows | every state resolves for every facing | legacy direction selector |
| `RCHAT-ANIM-025` | Build strict graph validator | MOTION | 020,021 | validator and fixtures | all IDs/edges/recipes/markers/loops valid | reject graph and use legacy |
| `RCHAT-ANIM-030` | Add shadow graph loader | MOTION | 025 | `motion_graph.rs` loader | embedded graph hash stable; no behavior change | remove module export |
| `RCHAT-ANIM-031` | Export contract modules | INT | 030 | `lib.rs` serial wiring | full current tests unchanged | revert wiring commit |
| `RCHAT-ANIM-032` | Add backward-compatible public state summary | MOTION/INT | 019,031 | `state.rs` additions with serde defaults | old state JSON fixture still loads | remove new optional fields |

### Wave B: clip and transition engine

| ID | Work | Owner | Depends on | Deliverable | Acceptance and evidence | Rollback |
|---|---|---|---|---|---|---|
| `RCHAT-ANIM-040` | Implement deterministic clip evaluator | MOTION | 030 | `motion_director.rs` sample/marker evaluator | exact tick tests for once/repeat/marked loops | graph shadow-only |
| `RCHAT-ANIM-041` | Implement transition recipe evaluator | MOTION | 040 | marker/contact/root/interrupt evaluation | every edge resolves one recipe | coherent legacy handoff |
| `RCHAT-ANIM-042` | Adapt legacy clips to graph interface | MOTION/INT | 040,041 | `pose_clip.rs` adapter | legacy command frame hashes unchanged in legacy profile | select legacy profile |
| `RCHAT-ANIM-043` | Add marker-safe replacement/restore | MOTION/INT | 041 | `pose_playback.rs` integration | no stale target; stop/replacement matrix 100% | legacy pending-pose logic |
| `RCHAT-ANIM-044` | Add per-channel generations and leases | MOTION | 032,040 | channel reducer | replacing one channel preserves all unowned generations | disable chat director |
| `RCHAT-ANIM-045` | Add deterministic variant selector | MOTION | 040 | finite seeded selector | same seed/commands produce identical selection stream | fixed first variant |

### Wave C: locomotion, flight, and contact realism

| ID | Work | Owner | Depends on | Deliverable | Acceptance and evidence | Rollback |
|---|---|---|---|---|---|---|
| `RCHAT-ANIM-050` | Author ground start/walk/run/stop/turn clips | MOTION | 020,041 | graph clip families | contact markers complete; loops phase-compatible | current ground clips |
| `RCHAT-ANIM-052` | Preserve distance phase across speed changes | MOTION/CORE | 050 | phase-sync policy | no phase reset; foot switch only on compatible marker | current walk phase |
| `RCHAT-ANIM-055` | Enforce planted foot/staff/hand contacts | MOTION | 050 | contact solver/checker | planted/brace drift <=0.5 cell | coherent handoff without offset |
| `RCHAT-ANIM-057` | Author jump/fall/landing arcs | MOTION | 041,055 | airborne and compression clips | no grounded claim airborne; contact->compression->settle | disable airborne action |
| `RCHAT-ANIM-060` | Author takeoff/hover/flap/glide/bank/land | MOTION | 041,055 | flight family and wing markers | shadow/contact root stable; attachment failures 0 | current hover/bank clips |
| `RCHAT-ANIM-063` | Add honest facing fallbacks | MOTION | 021,050,060 | tiered resolver | no unsupported authored-facing claim | front-performance fallback |

### Wave D: chatbot acting and emotion

| ID | Work | Owner | Depends on | Deliverable | Acceptance and evidence | Rollback |
|---|---|---|---|---|---|---|
| `RCHAT-ANIM-070` | Implement ten canonical turn-state profiles | MOTION | 040,044 | graph profiles and director mapping | every canonical state and snake_case wire value enters, holds, exits deterministically | map all to `Idle`/current actions |
| `RCHAT-ANIM-072` | Author `Listening` and `Idle` variants | MOTION | 070 | restrained repeatable clips | no repeated gesture; long-run distraction gate passes | stable idle |
| `RCHAT-ANIM-074` | Author `Thinking`, `PreparingResponse`, `Clarifying`, and `ToolWait` variants | MOTION | 070 | short clips, phrase-ready anticipation, and patient loop | preparation emits no viseme before speech start; stop <=12 ticks; no fake speech | static thinking pose |
| `RCHAT-ANIM-075` | Map ten emotions to full/close accents | MOTION | 020,070 | emotion profiles | all 20 feeling geometries covered; negative states never loop | neutral expression |
| `RCHAT-ANIM-077` | Author `Error` and `Celebrating` recipes | MOTION | 057,075 | one-shot accents | complete recovery; reduced motion forbids jump | restrained static accent |
| `RCHAT-ANIM-080` | Implement state/intensity/variant selection | MOTION | 045,070,075 | performance selector | valid family for every state/emotion/intensity tuple | default state profile |

### Wave E: face, speech, gaze, and co-articulation

| ID | Work | Owner | Depends on | Deliverable | Acceptance and evidence | Rollback |
|---|---|---|---|---|---|---|
| `RCHAT-ANIM-090` | Implement semantic-viseme reducer and render mapping | MOTION | 019 | `facial_performance.rs` | cue boundaries exact; all 14 semantic values map exactly; all seven rendered poses cross the exhaustive legacy boundary; no one-frame chatter except `MBP` closure | duration-only fallback mouth |
| `RCHAT-ANIM-092` | Preserve emotion mouth bias | MOTION | 075,090 | emotion/viseme co-articulation | phrase rests may select emotion-biased `Frown`; timed semantic visemes retain the canonical mapping and speech peaks remain readable | neutral mouth bias |
| `RCHAT-ANIM-095` | Implement gaze state | MOTION | 070 | gaze target/head bias | offsets bounded; root/contact unchanged | neutral gaze |
| `RCHAT-ANIM-097` | Implement deterministic blink scheduler | MOTION | 045,095 | blink event track | valid seeded interval; surprise/impact suppression | current periodic blink |
| `RCHAT-ANIM-100` | Align phrase gestures to speech markers | MOTION | 070,090 | marker-driven gesture selection | gesture peak within 2 render frames of accent | speech without gesture |
| `RCHAT-ANIM-102` | Implement speech interruption | MOTION | 043,090,100 | generation-safe close/yield | mouth closes <=2 render frames; stale cues never return | clear speech channel immediately |

### Wave F: secondary motion and effects

| ID | Work | Owner | Depends on | Deliverable | Acceptance and evidence | Rollback |
|---|---|---|---|---|---|---|
| `RCHAT-ANIM-110` | Implement quantized secondary state | MOTION | 044 | `secondary_motion.rs` | same state/seed yields same offsets; each <=1 cell | zero offsets |
| `RCHAT-ANIM-111` | Apply constrained region offsets | MOTION/INT | 055,110 | `pose.rs` serial integration | no seam/crack/fragment/attachment regression | zero offsets/profile off |
| `RCHAT-ANIM-112` | Render face/gaze/secondary channels | MOTION/INT | 090,095,111 | `renderer.rs` serial integration | screenshot deltas limited to owned regions | old renderer path |
| `RCHAT-ANIM-114` | Staff plant and tip-lag rules | MOTION | 055,111 | staff secondary policy | one staff component; 0 gaps; planted tip drift <=0.5 | disable staff lag |
| `RCHAT-ANIM-116` | Wing flap/settle constraints | MOTION | 060,111 | wing secondary policy | torso attachment continuous on every frame | authored pose only |
| `RCHAT-ANIM-118` | Robe/beard/hat follow-through | MOTION | 110,111 | bounded settle profiles | topology failures 0; settle within profile bounds | zero offsets |
| `RCHAT-ANIM-119` | Deterministic effect lifetimes | MOTION | 044,112 | effect marker evaluator | origin attached; expires exactly; no stale effect | existing cast effect |

### Wave G: interruption, repeat, reduced motion, and integration

| ID | Work | Owner | Depends on | Deliverable | Acceptance and evidence | Rollback |
|---|---|---|---|---|---|---|
| `RCHAT-ANIM-120` | Build full interruption matrix | MOTION | 043,070,102,119 | state x state interrupt rules | all legal pairs settle; illegal pairs reject explicitly | legacy action priority |
| `RCHAT-ANIM-125` | Add cooldowns and repeat-safe variants | MOTION | 045,080 | variant cooldown state | no immediate repeat when another legal variant exists | fixed variant |
| `RCHAT-ANIM-130` | Implement repeat-until-stop clips | MOTION | 040,120 | marked loop and Stop exit | repeat persists; Stop exits at safe marker | existing clip loop flag |
| `RCHAT-ANIM-135` | Implement reduced-motion graph overrides | MOTION | 070,110,130 | reduced profiles | no root bob/overshoot/repeated celebration/micro-saccade | stable coherent handoff |
| `RCHAT-ANIM-140` | Wire director into controller | MOTION/INT | 080,120,135 | serial `controller.rs` integration | old commands still work; new intent deterministic | runtime profile `legacy` |
| `RCHAT-ANIM-145` | Wire normalized performance API | SYS/INT | 019,140 | server route/command adapter | strict validation; no direct pose field; state smoke | route disabled |
| `RCHAT-ANIM-150` | Publish diagnostics and active profile | SYS/INT | 140,145 | state endpoint fields | graph/asset hashes, state, clip, markers visible | omit optional diagnostics |

### Wave H: exhaustive QA and promotion

| ID | Work | Owner | Depends on | Deliverable | Acceptance and evidence | Rollback |
|---|---|---|---|---|---|---|
| `RCHAT-ANIM-160` | Run focused unit/contract suite | MOTION/QA | 150 | test results | all contract, graph, channel, timing tests pass | block promotion |
| `RCHAT-ANIM-165` | Run exhaustive graph/interrupt matrix | QA | 160 | matrix ledger | 100% edges and interrupt pairs pass | block promotion |
| `RCHAT-ANIM-170` | Extend Rust evidence generator | MOTION/QA/INT | 165 | complete frame manifest/ledger/PNGs/video/sheets | one screenshot per frame; no missing index | block promotion |
| `RCHAT-ANIM-172` | Run two-pass deterministic evidence | QA | 170 | pass-one/pass-two hashes | 100% identical, all quality thresholds pass | block promotion |
| `RCHAT-ANIM-175` | Run source/decode/presentation parity | QA/SYS | 172 | parity ledger | 100% source=decode=presented | block promotion |
| `RCHAT-ANIM-176` | Run real-browser scenario suite on 8787 | QA/SYS/INT | 175 | screenshots, console log, browser manifest | all states/profiles/interruption/reconnect; 0 console errors | keep legacy live |
| `RCHAT-ANIM-180` | Run mixed-state soak and performance profiles | QA/SYS | 176 | soak/performance manifests | 60 Hz simulation, 24 FPS render profile, no queue/resync regression | keep legacy live |
| `RCHAT-ANIM-185` | Shadow-to-default promotion | INT | 180 | graph v1 default with legacy fallback | live smoke and rollback drill pass | set profile back to legacy |
| `RCHAT-ANIM-190` | Final independent acceptance audit | QA/three-agent review | 185 | signed scorecard and handoff | overall >=90%, all structural gates 100%, no blocker | reopen failed work IDs |

## 9. Test and evidence matrix

### Unit and contract tests

| Test file | Required assertions |
|---|---|
| `tests/chat_motion_graph.rs` | schema, 89 coverage, 50 WJFL coverage, references, loops, markers, recipes, fallbacks |
| `tests/chat_turn_states.rs` | exact ten-value snake_case contract plus deterministic enter/hold/exit for all ten canonical states and intensity bands |
| `tests/chat_coarticulation.rs` | cue quantization; all 14 semantic visemes; exact semantic-to-`RenderedMouthPose` table; exhaustive seven-value legacy `MouthShape` conversion; duration-only fallback; emotion bias; gesture-accent alignment; blink collision |
| `tests/chat_secondary_motion.rs` | bounds, settle duration, staff plant, wing attachment, robe/beard/hat topology |
| `tests/chat_interruptions.rs` | all state replacements, generation ownership, stale-event rejection, stop windows |
| `tests/chat_reduced_motion.rs` | semantic parity with reduced movement and effects |
| `tests/chat_transition_matrix.rs` | every graph edge, loop boundary, entry, exit, contact/root/anchor threshold |
| `tests/chat_motion_evidence.rs` | manifest completeness, PNG count, ledger count, hash/parity/threshold fields |

Existing suites remain mandatory:

```text
tests/imported_pose_library.rs
tests/future_pose_transitions.rs
tests/wjfl_clip_quality.rs
tests/pose_clips.rs
tests/frame_quality_gate.rs
tests/animation_transitions.rs
tests/fixed_clock.rs
tests/websocket_stream.rs
web/tests/*.test.mjs
```

### Required scenario families

1. `Idle` for 30 seconds with seeded blink and secondary variation.
2. `Listening -> Thinking -> Listening`, interrupted at every marker.
3. `Listening -> PreparingResponse -> Speaking` with no viseme cues, proving the
   seeded duration-only envelope and zero response-text access.
4. `Listening -> PreparingResponse -> Speaking` with all 14 semantic visemes
   plus dense phrase-marker cues, proving the exact rendered-pose and legacy
   conversion boundaries.
5. `Speaking` with explain, point, sincere, and restrained magic variants.
6. `Speaking` interrupted before anticipation, during anticipation, after
   commit, during impact, during recovery, and at turn end.
7. `Clarifying -> Listening` and
   `Clarifying -> PreparingResponse -> Speaking`.
8. `ToolWait` loop for three cycles, then Stop and then result `Celebrating`.
9. `Error` at low/high allowed intensity, then recover.
10. `Celebrating` at low/high allowed intensity, including reduced motion.
11. All ten emotions at low and high allowed intensity.
12. Every `*_full -> *_close -> *_full` feeling accent path.
13. Walk/run with `Listening`/`Speaking`/gesture overlays and phase-preserving
    speed change.
14. Ground-to-flight-to-ground with speech/gaze and interruption.
15. Staff plant, block, thrust, spin, cast, and recovery.
16. Every repeatable clip through at least three loop boundaries.
17. Rapid state replacement for every legal directed pair.
18. Reset, reconnect, resync, visibility suspend/resume, and context restore.
19. Full and reduced motion with identical semantic command logs.
20. Real browser presentation of all above representative paths.

## 10. Acceptance thresholds

Structural gates are absolute. They cannot be averaged into the 90-percent
program score.

| Gate | Threshold |
|---|---:|
| Geometry coverage | 89/89 |
| WJFL coverage | 50/50 |
| Graph edge and recipe resolution | 100% |
| Canonical turn-state contract | 10/10 exact snake_case values |
| Required scenario completion | 100% |
| Screenshot-per-frame completeness | 100% |
| Deterministic replay equality | 100% |
| Source/decode/presentation parity | 100% |
| Seams, cracks, unexpected fragments | 0 |
| Detached/gapped staff or wings | 0 |
| Root drift in local pose space | 0 cells |
| Planted/brace contact drift | <=0.5 cell |
| Semantic source retention | >=0.94 |
| Visible source retention | >=0.75 |
| Same-pose occupancy ratio | >=0.88 |
| Same-channel face/staff step | <=1.5 cells |
| Authored whole-pose face/staff/free-foot step | <=4/6/8 cells |
| Semantic viseme mapping | 14/14 exact |
| Rendered mouth compatibility conversion | 7/7 exhaustive |
| Response-text access or text-derived inference | 0 |
| Speech interruption mouth close | <=2 render frames |
| Gesture peak to speech accent | <=2 render frames |
| Stop from repeatable chat loop | <=12 simulation ticks unless in committed impact window |
| Browser console errors | 0 |
| Overall independent score | >=90% |

Any threshold exception requires a separate approved work item. It may not be
introduced by changing a test constant inside the same implementation PR.

## 11. Future execution commands

These commands are for implementation and acceptance. They were not run during
this planning-only assignment.

```bash
cargo fmt --manifest-path rust/wizard_avatar_engine/Cargo.toml -- --check
cargo clippy --manifest-path rust/wizard_avatar_engine/Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path rust/wizard_avatar_engine/Cargo.toml
cargo run --manifest-path rust/wizard_avatar_engine/Cargo.toml --bin wizard-avatar-pose-evidence
cargo run --manifest-path rust/wizard_avatar_engine/Cargo.toml --bin wizard-avatar-performance
cargo run --manifest-path rust/wizard_avatar_engine/Cargo.toml --bin wizard-avatar-soak
node --test rust/wizard_avatar_engine/web/tests/*.test.mjs
```

The coordinator must run the server on an available port, with 8787 preferred,
and execute browser QA against the exact commit used by evidence.

## 12. Rollback strategy

### Runtime profiles

The integration introduces an explicit profile selection:

```text
legacy_pose_clips
chat_motion_v1_shadow
chat_motion_v1
```

- `legacy_pose_clips` is the current accepted behavior.
- `chat_motion_v1_shadow` evaluates and records graph decisions but renders the
  legacy result. It proves deterministic selection before visual promotion.
- `chat_motion_v1` renders the new director.

Profile selection is server-owned and reported in diagnostics. It must not be a
browser-only toggle.

### Promotion checkpoints

1. Contract and coverage commit.
2. Shadow graph commit.
3. Clip/contact commit.
4. Chat state and facial channel commit.
5. Secondary and interruption commit.
6. Evidence-complete release candidate.

Each checkpoint is independently buildable. If a wave fails, return to the
last accepted checkpoint and keep the failed graph/features disabled. Never
modify or replace the v4 asset as a motion rollback.

### Immediate rollback triggers

- runtime pose count changes from 89;
- any WJFL geometry becomes unresolved;
- source PNG path appears in runtime source, HTML, JavaScript, or network logs;
- Python becomes a production dependency;
- a graph edge lacks a recipe or fallback;
- contact, attachment, fragmentation, determinism, codec, or presentation gate
  fails;
- interruption resurrects a stale speech, pose, effect, or gesture generation;
- reduced motion changes semantic chatbot state;
- browser output differs from accepted source frames.

## 13. Tracking and handoff protocol

Each work item update records:

```text
work_item: RCHAT-ANIM-xxx
status: BLOCKED|READY|IN_PROGRESS|REVIEW|ACCEPTED
owner:
base_commit:
head_commit:
owned_files_changed:
dependencies_satisfied:
contracts_implemented:
tests_run:
test_results:
evidence_paths:
thresholds_met:
rollback_verified:
risks:
hotspot_wiring_requested:
next_dependency_unblocked:
```

Workflow rules adapted for this repository:

- GitHub branch/PR state is the public execution truth.
- The repository program tracker and work IDs are the internal technical truth
  unless the coordinator explicitly links an external tracker.
- Every PR title includes one or more `RCHAT-ANIM-xxx` IDs.
- No PR is classified merge-ready from its summary; reviewers inspect the full
  diff, tests, evidence manifest, and runtime profile impact.
- A useful but incomplete change is `park` or `rebuild`, not silently merged.
- CI red, missing screenshots, or incomplete parity is a blocker.
- Workers do not stage, commit, or revert files owned by another agent.
- The coordinator performs serial hotspot integration and final index review.

## 14. Cross-agent dependencies

### Runtime/core agent must provide

- ordered, deduplicated semantic command delivery;
- integer-tick deadlines and deterministic sequence ownership;
- immutable runtime snapshots for rendering and evidence;
- priority rules for user interruption, chat intent, autonomous idle, and
  safety/reset;
- no text/private-content leakage into public animation state.

### Systems/browser agent must provide

- strict HTTP/WebSocket envelope validation;
- the normalized `ChatPerformanceIntent` adapter without direct pose control;
- epoch/sequence diagnostics and resync behavior;
- active motion profile reporting;
- real-browser automation, console capture, and presented-frame hashes;
- reduced-motion preference input without client-side simulation.

### QA/program agent must provide

- tracker state and path locks;
- evidence schema review and artifact allowlist;
- screenshot count/ledger/manifest validator;
- deterministic two-pass runner;
- independent final scorecard;
- branch, deployment, and rollback records.

### MOTION provides to the other agents

- frozen turn-state, graph, clip, marker, transition, face, gaze, secondary,
  and evidence contracts;
- 89-geometry taxonomy and capability tiers;
- accepted default and reduced-motion behavior;
- strict visual/contact/anchor thresholds;
- deterministic fixture command logs and expected state/marker traces.

## 15. Definition of done

The MOTION lane is done only when `RCHAT-ANIM-001..190` are either `ACCEPTED` or
explicitly superseded by a linked decision; all start gates and structural
thresholds are green; the overall independent score is at least 90 percent;
the Rust server on port 8787 demonstrates every conversational state and Stop
behavior; the complete screenshot-per-frame evidence exists; and the legacy
rollback has been exercised successfully.

No amount of attractive video replaces missing PNG frames, ledgers, hashes,
contact metrics, or deterministic replay. No runtime PNG reuse and no Python
production authority are permitted at completion.
