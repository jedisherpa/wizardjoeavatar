# Planning Wave 2: First-Principles Python Runtime Plan

Role: `FPSE`
Date: 2026-07-12
Production target: the existing ASCILINE Python service on `127.0.0.1:8765`
Research inputs: all four reports in `../research/`

## 1. Binding decisions

This contribution is an implementation contract for the coordinator and the other three roles. The following decisions are settled and must not be reopened inside an implementation work item.

1. **Python is the sole production authority.** Simulation, commands, animation state, graph evaluation, rendering, ASCILINE encoding, fanout, HTTP, and WebSocket delivery remain in the existing Python application on port 8765.
2. **Rust is excluded.** No work item may add a Rust import, extension, subprocess, generated artifact, WASM module, listener, build step, CI job, acceptance command, or evidence dependency. Existing `rust/` files and Rust evidence are historical and non-authoritative.
3. **Rainbow wings and flight are accepted requirements.** The `no wings` bullets in `docs/30-visual-tests.md` and `docs/37-completion-gate.md` are stale. Before implementation starts, the coordinator must update those shared contracts to require the current rainbow-winged character and winged takeoff, hover, flight, bank, and landing behavior. Existing winged poses are production assets, not defects.
4. **Art coverage remains honest.** Current art supports strong south/front and southeast flight. The runtime must expose explicit facing capability and coherent fallback behavior; it must not claim equally authored eight-direction flight where source poses do not exist.
5. **The ASCILINE binary frame stream remains compatible.** Runtime redesign must not change existing keyframe/delta bytes during the contract and clock waves. Protocol evolution is additive around the stream.
6. **The browser remains an input adapter and presenter.** It never advances world state, chooses production poses, or runs a second animation graph.
7. **All animation time is derived from integer 60 Hz simulation ticks.** The normal 24 FPS render cadence samples immutable runtime snapshots. Render callbacks never mutate simulation.
8. **Whole-pose cell dissolve is not production motion synthesis.** The graph chooses coherent authored poses and transition recipes. FPSE owns graph execution; ANIM owns clip/edge authorship and visual approval.

## 2. Start gate and cross-role contracts

No FPSE implementation item may begin until these coordinator-owned prerequisites are recorded as passed in the program ledger.

| Gate ID | Required result | Owning role | Blocking FPSE items |
|---|---|---|---|
| `PRG-B0` | Reproducible 39-pose Python baseline is committed and pushed with Rust/raw evidence excluded | PLAN/coordinator | all |
| `PRG-P0` | Four planning contributions and integrated workflow are committed and pushed | PLAN/coordinator | all |
| `PRG-WING-001` | Stale no-wings clauses are superseded in `README.md`, `docs/00-goal-and-visual-contract.md`, `docs/30-visual-tests.md`, and `docs/37-completion-gate.md` | PLAN/coordinator | `FPSE-060` onward |
| `ANIM-CONTRACT-001` | ANIM freezes graph-v2 field meanings, clip inventory, marker vocabulary, compatibility families, and visual thresholds | ANIM | `FPSE-060` onward |
| `SYS-CONTRACT-001` | Python systems role freezes ASCILINE stream compatibility, epoch/sequence bootstrap fields, and source/decode/present evidence fields | translated RUST/systems role | `FPSE-080` onward |

The integrated plan may rename cross-role IDs, but it must preserve a one-to-one mapping in the registry. FPSE IDs below are stable and must not be renumbered.

## 3. Ownership and one-writer locks

### 3.1 FPSE-owned new files

These paths may be implemented in parallel only where the work-item table permits it:

```text
wizard_avatar/commands.py
wizard_avatar/runtime.py
wizard_avatar/control.py
wizard_avatar/animation_state.py
wizard_avatar/animation_graph.py
wizard_avatar/replay.py
wizard_avatar/canonical_hash.py

wizard_avatar/definitions/wizard_command_envelope.schema.json
wizard_avatar/definitions/wizard_command_ack.schema.json
wizard_avatar/definitions/wizard_public_state.schema.json
wizard_avatar/definitions/wizard_replay.schema.json

tests/wizard/test_command_envelope.py
tests/wizard/test_avatar_runtime.py
tests/wizard/test_control_arbitration.py
tests/wizard/test_animation_state_regions.py
tests/wizard/test_animation_graph_runtime.py
tests/wizard/test_runtime_replay.py
tests/wizard/test_server_command_protocol.py
tests/wizard/test_runtime_stream_integration.py

tools/replay_wizard_runtime.py
tools/verify_runtime_determinism.py
```

### 3.2 Shared conflict hotspots

FPSE may modify these files only during the named serial integration item and only after the coordinator grants the path lock:

| Path | FPSE lock item | Required handoff before lock | Required handoff after lock |
|---|---|---|---|
| `wizard_avatar/models.py` | `FPSE-050` | baseline public-state snapshot | compatibility test and field map |
| `wizard_avatar/controller.py` | `FPSE-070` | ANIM state/marker contract | reducer/mobility integration tests |
| `wizard_avatar/locomotion.py` | `FPSE-070` | ANIM contact semantics | fixed-tick ground/flight tests |
| `wizard_avatar/server.py` | `FPSE-080` | `SYS-CONTRACT-001` | HTTP/WS compatibility report |
| `wizard_avatar/stream.py` | `FPSE-090` | systems-role pacing/fanout review | runtime ownership and soak report |
| `wizard_avatar/frame_source.py` | `FPSE-090` wiring only | ANIM renderer snapshot interface | immutable-render test and full regression |
| `tools/run_wizard_avatar_server.py` | `FPSE-080` | coordinator configuration decision | documented port-8765 launch smoke |

FPSE does **not** own these paths:

- `wizard_avatar/definitions/reference_avatar_animation_graph.json`
- `wizard_avatar/definitions/reference_avatar_animation_graph.schema.json`
- `wizard_avatar/pose_selection.py` clip authorship decisions
- `wizard_avatar/pose_compositor.py` transition visuals
- `web/avatar/*`
- `.github/workflows/*`
- program tracker, registry, integrated plan, or other role reports/plans
- any path under `rust/`

ANIM owns graph data, transition recipes, pose compatibility, and visual thresholds. The systems role owns codec/browser transport hardening and reviews stream integration. PLAN owns CI, registry, artifacts, and release bookkeeping. The integration lead owns final browser wiring and any cross-role edit to `frame_source.py` beyond consuming an immutable snapshot.

## 4. Frozen interface model

### 4.1 Runtime clock

`AvatarRuntime` is the sole mutating simulation owner. It must expose this conceptual interface without importing FastAPI or rendering modules:

```python
class AvatarRuntime:
    TICK_RATE = 60
    MAX_CATCH_UP_TICKS = 8

    def enqueue(self, envelope: CommandEnvelope) -> CommandAck: ...
    def step_tick(self) -> RuntimeSnapshot: ...
    def advance_wall_clock(self, monotonic_ns: int) -> RuntimeAdvanceResult: ...
    def current_snapshot(self) -> RuntimeSnapshot: ...
    def drain_events(self) -> tuple[RuntimeEvent, ...]: ...
```

Clock rules:

- `simulation_tick` starts at zero and increments exactly once per `step_tick()`.
- The only physics delta is the module constant `1.0 / 60.0`; no caller supplies a duration.
- Wall time is converted once to integer nanoseconds. The accumulator stores integer `nanoseconds * 60` units; one simulation tick costs exactly `1_000_000_000` units.
- One event-loop turn executes at most eight due simulation ticks.
- Excess accumulated wall time is discarded, added to `dropped_simulation_ns`, and emits one `runtime.catch_up_dropped` event. There is no partial physics tick.
- A lease whose deadline elapsed during a scheduler stall is cleared before the first resumed physics tick.
- Rendering reads a frozen snapshot and cannot call `step_tick()`.
- Unit tests use `step_tick()` directly and require no sleep or wall clock.

`RuntimeClockState` fields:

```text
simulation_tick: int
state_revision: int
runtime_epoch: str
last_monotonic_ns: int | None
accumulator_units: int
dropped_simulation_ns: int
catch_up_event_count: int
last_step_count: int
```

`runtime_epoch` is a server-start UUID used for stream/replay boundaries; it is not generated during deterministic replay, where the header supplies it.

### 4.2 Command envelope and acknowledgement

All HTTP and WebSocket commands must become one internal envelope before entering the queue.

```text
CommandEnvelope
  schema_version: 1
  command_id: string UUID
  source_id: string, 1..128 characters
  source_kind: browser_keyboard | browser_gamepad | external_remote |
               http_automation | demo | system | legacy_adapter
  source_sequence: integer >= 0
  command_type: move_intent | takeoff | land | action | expression |
                speak | stop | reset | move_to | path | circle |
                figure_eight | face | diagnostic_pose
  payload: command-specific strict object
  issued_at_ms: integer | null, diagnostics only
  ttl_ms: integer 0..5000
  requested_apply_tick: integer | null
  received_monotonic_ns: integer, server-assigned
  server_sequence: integer, server-assigned
  apply_tick: integer, server-assigned
```

Clients never choose `server_sequence`, priority, or accepted ownership. `apply_tick` defaults to `current_tick + 1`. A requested tick is accepted only when it is at least the default and no more than 120 ticks ahead. `reset` and emergency `stop` are server-priority commands and cannot be delayed by a client.

`move_intent.payload`:

```text
move_x: number in [-1.0, 1.0]
move_z: number in [-1.0, 1.0]
vertical: number in [-1.0, 1.0]
speed_mode: walk | run
flight_mode: grounded | auto | airborne
facing_preference: north | northeast | east | southeast | south |
                   southwest | west | northwest | null
```

The server clamps no malformed values. Strict validation rejects out-of-range, coerced, unknown, or missing fields before queue insertion.

`CommandAck` fields:

```text
schema_version: 1
command_id: string
status: accepted | duplicate | rejected_stale | rejected_expired |
        rejected_unauthorized | rejected_invalid | rejected_queue_full
source_id: string
source_sequence: int
server_sequence: int | null
accepted_tick: int | null
apply_tick: int | null
state_revision: int
runtime_epoch: string
message: string
```

Queue ordering is the total key `(apply_tick, server_sequence)`. Duplicate `command_id` returns the original acknowledgement and never mutates state twice. A non-increasing `source_sequence` is rejected unless it is the exact duplicate command ID. The bounded inbox capacity is 1,024 pending envelopes; overflow rejects the incoming command and increments telemetry.

### 4.3 Control lease and arbitration

Only continuous mobility intent requires a lease. Discrete actions use channel policy and do not seize mobility ownership.

```text
ControlLease
  source_id: str
  source_kind: enum
  generation: int
  priority: int, assigned by server
  last_source_sequence: int
  accepted_tick: int
  expires_tick: int
  expires_monotonic_ns: int
  intent: MotionIntent
```

Priority table:

| Priority | Owner | Rule |
|---:|---|---|
| 100 | reset / emergency stop | Clears all leases, paths, actions, and queued non-system commands |
| 80 | explicit scripted/cinematic command | Owns only declared channels for bounded duration |
| 60 | active direct-control lease | Preempts path/demo mobility while fresh |
| 40 | path/circle/figure-eight/demo | Runs only without a higher mobility owner |
| 20 | autonomous idle behavior | Fills otherwise unowned channels |

The default direct-control TTL is 250 ms, represented as 15 simulation ticks and a matching monotonic deadline. A refreshed lease must come from the same `source_id` with a strictly increasing sequence. Equal-priority takeover by a different source is rejected until release/expiry; there is no last-packet-wins controller theft. Zero intent releases the lease after applying one deceleration-safe tick. WebSocket disconnect, browser blur/visibility release forwarded by the client, gamepad disconnect, and heartbeat expiry all produce the same `control.released` runtime event.

### 4.4 Typed orthogonal state regions

Python 3.9 compatibility is mandatory. Use string-valued `Enum` subclasses, dataclasses, and `typing.Literal`; do not use `StrEnum`, `TaskGroup`, or other 3.11-only APIs unless a separate program-level version migration is approved.

```text
SemanticAvatarState
  schema_version: int
  character_id: str
  world: WorldRegion
  mobility: MobilityRegion
  upper_body: UpperBodyRegion
  face: FaceRegion
  speech: SpeechRegion
  staff: StaffRegion
  wings: WingRegion
  effects: EffectsRegion
  control: ControlRegion
  animation: AnimationPresentationState
```

Every region contains `generation`, `entered_tick`, `owner`, and `priority`. Timed regions additionally contain `deadline_tick`. No region stores a wall-clock float.

Required region fields:

```text
WorldRegion
  position_x, position_z: float
  velocity_x, velocity_z: float
  facing: 8-way enum

MobilityRegion
  mode: grounded_idle | grounded_start | grounded_walk | grounded_run |
        grounded_stop | takeoff | flying_hover | flying_travel |
        flying_bank | falling | landing | disabled
  grounded: bool
  altitude: float
  vertical_velocity: float
  target_altitude: float | null
  support_contact: none | left_foot | right_foot | both_feet | staff
  distance_phase: float in [0, 1)
  flight_phase: float in [0, 1)

UpperBodyRegion
  mode: neutral | explain | point | guard | cast | block | flourish |
        celebrate | shush | reaction
  committed: bool
  restoration: discard | resume_if_valid | restart | neutral

FaceRegion
  expression: existing supported expression enum
  blink_state: open | closing | closed | opening
  blink_generation: int

SpeechRegion
  mode: inactive | active
  speech_id: str | null
  mouth_shape: closed | open | wide | narrow
  suppressed_by: str | null

StaffRegion
  mode: held | planted | guard | thrust | horizontal_block | spin | raised
  owning_hand: left | right
  contact_active: bool

WingRegion
  mode: folded | neutral | upstroke | downstroke | glide | bank_left | bank_right
  phase: float in [0, 1)
  visible: bool

EffectsRegion
  active_effects: ordered tuple of typed effect instances

ControlRegion
  active_lease: ControlLease | null
  last_accepted_sequence_by_source: mapping[str, int]

AnimationPresentationState
  graph_version: int
  node_id: str
  clip_id: str
  clip_tick: int
  clip_phase: float
  sample_index: int
  pose_id: str
  transition_id: str | null
  transition_start_tick: int | null
  transition_duration_ticks: int
  transition_generation: int
  contact_marker: str
  visual_root_offset_x, visual_root_offset_y: int
```

`WizardState.as_public_dict()` remains backward compatible during migration: existing top-level keys remain, while a new `runtime` object and new typed-region objects are added. Compatibility fields are projections from typed state, never a second source of truth.

### 4.5 Motion graph runtime boundary

ANIM owns graph-v2 JSON and schema. FPSE owns loading the validated data into immutable runtime objects and evaluating it. The evaluator never draws cells.

Required graph fields:

```text
schema_version: 2
asset_set_id: str
graph_id: str
clips: mapping[clip_id, Clip]
nodes: mapping[node_id, GraphNode]
transitions: ordered list[TransitionEdge]
fallbacks: ordered list[FallbackRule]
```

`Clip`:

```text
clip_id: str
family: idle | locomotion | flight | action | reaction | recovery
supported_facings: non-empty list of 8-way facings
loop_mode: once | loop | hold_last
phase_source: simulation_time | distance | flight_phase | manual
root_policy: grounded_in_place | world_distance | airborne |
             planted_foot | planted_staff | authored_root_motion
owned_channels: list of typed region/channel IDs
samples: non-empty ordered list[ClipSample]
entry_markers, exit_markers: list[str]
```

`ClipSample`:

```text
pose_id: one of the 39 generated pose IDs
duration_ticks: integer >= 1
expected_presented_frames_24: integer >= 1
markers: ordered list[str]
contact: none | left_foot | right_foot | both_feet | staff
visual_root_offset: integer [x, y]
```

`duration_ticks` is authoritative. `expected_presented_frames_24` is an ANIM review expectation and does not drive progression. Validation rejects a sample whose duration makes the declared visual hold impossible at 24 FPS.

`TransitionEdge`:

```text
transition_id: str
source_node: str
target_node: str
priority: int
condition: typed declarative condition, no embedded code
duration_ticks: int >= 0
phase_policy: preserve | nearest_marker | reset | explicit_entry
contact_policy: preserve | release | acquire | none
root_policy: preserve | planted_foot | planted_staff | authored
interrupt_policy: immediate | marker_window | at_end | uninterruptible
bridge_clip_id: str | null
safe_fallback_transition_id: str | null
```

`AnimationGraphRuntime.evaluate(previous, current, events) -> AnimationIntent` returns node, clip, phase, sample, markers crossed, contacts, transition state, and region ownership. It must satisfy:

- deterministic first-match ordering by `priority` then declaration index;
- run-to-completion microsteps with a hard limit of 32 transitions per simulation tick;
- validation failure for ambiguous same-priority edges with overlapping conditions;
- marker emission exactly once when a tick crosses a marker;
- phase carry for compatible walk/run and hover/flap/bank families;
- explicit safe fallback diagnostics; no raw pose roulette;
- front-biased flight capability declared honestly;
- wings visible and semantically active in takeoff/flight/bank/landing clips;
- every stable node has a legal path to grounded idle or flying hover;
- direct pose override exists only as `diagnostic_pose` and never participates in production transition selection.

### 4.6 Replay and canonical hashes

Replay files are NDJSON with one header followed by ordered records.

Header fields:

```text
record_type: header
schema_version: 1
runtime_epoch: str
python_version: str
baseline_commit: str
asset_sha256: str
graph_sha256: str
seed: int
initial_state: canonical state object
tick_rate: 60
render_rate: 24
```

Record types:

- `command_received`
- `command_ack`
- `tick_state`
- `runtime_event`
- `render_frame`
- `footer`

Every `tick_state` records `simulation_tick`, `state_revision`, command watermark, active lease, node/clip/phase/sample, contacts, state SHA-256, and event IDs. Every `render_frame` records frame index, simulation tick, source SHA-256, transport FNV-1a diagnostic, codec tag, and keyframe flag.

Canonical hashing recursively sorts mapping keys, preserves list order, encodes enums as strings, and represents every float with Python `float.hex()` before UTF-8 JSON serialization. SHA-256 is the durable evidence hash. The existing FNV-1a frame hash remains a transport diagnostic and is not the release artifact hash.

## 5. Work-item DAG

```text
PRG-B0 + PRG-P0
        |
        v
FPSE-010 contracts/types
   |       |        |
   v       v        v
FPSE-020  FPSE-030  FPSE-050
 clock     queue     regions
   \       /          /
    v     v          /
    FPSE-040 leases  /
          \         /
           v       v
          FPSE-060 graph runtime <-- ANIM-CONTRACT-001 + PRG-WING-001
                  |
                  v
          FPSE-070 semantic reducer/mobility
                  |
                  v
          FPSE-080 FastAPI/WebSocket adapters <-- SYS-CONTRACT-001
                  |
                  v
          FPSE-090 hub/render integration
                  |
                  v
          FPSE-100 replay/hash evidence
                  |
                  v
          FPSE-110 FPSE handoff gate
```

`FPSE-020`, `FPSE-030`, and `FPSE-050` may run in separate worktrees after `FPSE-010` passes because their owned paths are disjoint. Everything from `FPSE-060` onward is serial.

## 6. Explicit work items

### `FPSE-010` - Freeze Python contracts and schemas

**Dependencies:** `PRG-B0`, `PRG-P0`
**Owner:** FPSE contract agent
**Allowed writes:**

```text
wizard_avatar/commands.py
wizard_avatar/animation_state.py
wizard_avatar/definitions/wizard_command_envelope.schema.json
wizard_avatar/definitions/wizard_command_ack.schema.json
wizard_avatar/definitions/wizard_public_state.schema.json
wizard_avatar/definitions/wizard_replay.schema.json
tests/wizard/test_command_envelope.py
tests/wizard/test_animation_state_regions.py
```

**Implementation:**

1. Add Python 3.9-compatible enums and dataclasses for every field in Sections 4.2-4.4.
2. Separate transport validation from internal types. FastAPI/Pydantic models may be added later in `FPSE-080`; these modules must be importable without FastAPI.
3. Add strict construction functions that reject unknown keys and bool-as-int coercion.
4. Add JSON Schemas with `$schema`, `$id`, `schema_version`, `additionalProperties: false`, numeric bounds, and command-specific payload unions.
5. Add deterministic `as_dict()` methods without wall-clock defaults or global randomness.

**Tests/commands:**

```bash
uv run pytest -q tests/wizard/test_command_envelope.py tests/wizard/test_animation_state_regions.py
uv run python -m json.tool wizard_avatar/definitions/wizard_command_envelope.schema.json >/dev/null
uv run python -m json.tool wizard_avatar/definitions/wizard_command_ack.schema.json >/dev/null
uv run python -m json.tool wizard_avatar/definitions/wizard_public_state.schema.json >/dev/null
uv run python -m json.tool wizard_avatar/definitions/wizard_replay.schema.json >/dev/null
```

**Gate:** all accepted and rejected examples are enumerated; schema and Python validators agree; import succeeds under Python 3.9; no existing test changes.
**Rollback:** remove the additive modules/schemas; production behavior is untouched.
**Evidence:** `evidence/cartoon-animation-program/fpse/FPSE-010-contract-cases.json`.
**Handoff:** publish field tables, sample accepted/rejected envelopes, and schema hashes to ANIM, systems, browser, and PLAN roles.

### `FPSE-020` - Implement fixed-tick `AvatarRuntime`

**Dependencies:** `FPSE-010`
**Owner:** FPSE runtime agent
**Allowed writes:**

```text
wizard_avatar/runtime.py
tests/wizard/test_avatar_runtime.py
```

**Implementation:**

1. Implement the integer accumulator and exact `step_tick()` boundary from Section 4.1.
2. Inject clock, reducer, and event sink through small `typing.Protocol` interfaces; production defaults are supplied only during integration.
3. Store frozen previous/current snapshots.
4. Bound catch-up at eight ticks and record discarded time.
5. Prove rendering callbacks are absent from the runtime module.
6. Expose timing telemetry without reading global process time in unit tests.

**Required tests:** zero elapsed, one exact tick, 2.5 render intervals, 15/24/30 FPS sampling, backward clock rejection, two-second stall, catch-up cap, snapshot immutability, repeated render read, cancellation-safe re-entry, and 100,000 direct ticks.

```bash
uv run pytest -q tests/wizard/test_avatar_runtime.py
uv run pytest -q tests/wizard/test_locomotion.py tests/wizard/test_pathing.py
```

**Runtime gates:** no fractional reducer delta; same tick state hash under 15/24/30 render schedules; eight or fewer catch-up steps per turn; 100,000 ticks without tick loss/regression.
**Rollback:** additive module remains unused; delete or revert it without touching the live hub.
**Evidence:** `evidence/cartoon-animation-program/fpse/FPSE-020-clock-matrix.json`.
**Handoff:** provide the runtime protocol and snapshot constructor to `FPSE-030` and `FPSE-050`.

### `FPSE-030` - Implement ordered command queue and acknowledgements

**Dependencies:** `FPSE-010`
**Owner:** FPSE command agent
**Allowed writes:**

```text
wizard_avatar/commands.py
tests/wizard/test_command_envelope.py
```

The coordinator must transfer the `commands.py` lock from `FPSE-010` before work starts.

**Implementation:**

1. Add bounded priority queue ordered by `(apply_tick, server_sequence)`.
2. Add server sequence assignment, per-source watermark, 4,096-entry command-ID dedup cache, and deterministic eviction by oldest server sequence.
3. Cache and return the original acknowledgement for exact duplicates.
4. Reject stale sequence, expired TTL, unauthorized source, invalid requested tick, and queue overflow with no mutation.
5. Drain all commands due at the current tick before the semantic reducer step.

**Tests:** all permutation orders for same-tick commands, duplicate retry, stale sequence, delayed future command, 121-tick rejection, queue full, reset precedence, dedup eviction, and 1,000-command replay order.

```bash
uv run pytest -q tests/wizard/test_command_envelope.py -k 'queue or order or duplicate or stale or expiry'
```

**Gate:** two queue runs produce byte-identical ack/event order; every accepted command has exactly one apply result; rejected commands leave state revision unchanged.
**Rollback:** runtime continues with legacy direct application until `FPSE-080`; additive queue can be reverted independently.
**Evidence:** `evidence/cartoon-animation-program/fpse/FPSE-030-command-order.json`.
**Handoff:** frozen enqueue/drain/ack interface to leases, replay, and server adapters.

### `FPSE-040` - Implement leases and input arbitration

**Dependencies:** `FPSE-020`, `FPSE-030`
**Owner:** FPSE control agent
**Allowed writes:**

```text
wizard_avatar/control.py
tests/wizard/test_control_arbitration.py
```

**Implementation:**

1. Implement the priority table and lease fields from Section 4.3.
2. Normalize nonzero planar vectors to magnitude at most one while preserving analog magnitude below one.
3. Treat zero input, explicit release, disconnect, and expiry as one release reducer event.
4. Keep path/demo intent suspended while direct control owns mobility; resume only if the path remains valid and its policy says `resume_if_valid`.
5. Keep actions independent unless their graph ownership explicitly blocks mobility.
6. Expose deterministic arbitration diagnostics: winner, rejected contender, reason, generation, expiry tick.

**Tests:** every priority pair in both arrival orders, same-priority second-source rejection, same-source refresh, missing heartbeat, zero release, disconnect, blur-equivalent release, path suspend/resume, emergency reset, analog vector bounds, and permutation property tests.

```bash
uv run pytest -q tests/wizard/test_control_arbitration.py
```

**Gate:** 100% of arbitration permutations resolve to the documented owner; stale/unauthorized packets never alter motion; expiry clears intent by tick 15 and before the first resumed tick after a scheduler stall.
**Rollback:** disable direct-intent route and retain legacy path/move commands; no state migration required.
**Evidence:** `evidence/cartoon-animation-program/fpse/FPSE-040-arbitration-matrix.json`.
**Handoff:** browser role receives heartbeat/release contract; PLAN receives authority matrix.

### `FPSE-050` - Make typed regions the semantic source of truth

**Dependencies:** `FPSE-010`, `FPSE-020`
**Owner:** FPSE state agent
**Allowed writes:**

```text
wizard_avatar/animation_state.py
wizard_avatar/models.py
tests/wizard/test_animation_state_regions.py
tests/wizard/test_animation_channels.py
```

The coordinator must grant the `models.py` hotspot lock and freeze all concurrent edits.
The coordinator must also transfer the `animation_state.py` lock from completed item `FPSE-010`; no contract and state agent may edit it concurrently.

**Implementation:**

1. Add `SemanticAvatarState` and typed regions exactly as Section 4.4.
2. Preserve existing public keys as read-only projections.
3. Replace float deadlines in the new state with integer ticks; legacy float fields remain projection-only until final cleanup.
4. Replace hand-built action-restore dictionaries with generation-aware restoration policy.
5. Make wings a typed, visible production region. Grounded idles may show wings according to authored pose; airborne states must never silently hide them.
6. Add invariants: `grounded` implies zero altitude within tolerance; airborne states imply no foot support; shush may suppress speech mouth; planted staff requires staff contact; every region owner/priority is legal.

**Tests/commands:**

```bash
uv run pytest -q tests/wizard/test_animation_state_regions.py tests/wizard/test_animation_channels.py
uv run pytest -q tests/wizard/test_e2e.py -k 'not pose_showcase'
```

**Gate:** all existing public keys remain present and retain compatible types; region invariants reject illegal combinations; channel interruption/restoration passes without partial dictionaries.
**Rollback:** configuration keeps `v1` state projection active; revert this item before any graph-v2 data is promoted.
**Evidence:** `evidence/cartoon-animation-program/fpse/FPSE-050-public-state-compat.json`.
**Handoff:** ANIM receives immutable state/intent fixtures; systems/browser receive additive public-state example.

### `FPSE-060` - Implement graph-v2 validation and deterministic evaluator

**Dependencies:** `FPSE-040`, `FPSE-050`, `ANIM-CONTRACT-001`, `PRG-WING-001`
**Owner:** FPSE graph-runtime agent
**Allowed writes:**

```text
wizard_avatar/animation_graph.py
tests/wizard/test_animation_graph_runtime.py
```

ANIM supplies graph JSON/schema and fixtures but does not edit the evaluator. FPSE may not alter pose order, durations, markers, or visual thresholds to make tests pass.

**Implementation:**

1. Parse already schema-validated graph-v2 data into frozen Python objects.
2. Add semantic validation: known pose IDs, reachable nodes, stable-state exits, transition ambiguity, marker validity, contact legality, duration/24-FPS hold feasibility, and fallback termination.
3. Implement deterministic edge ordering, 32-microstep cap, marker crossing, phase carry, interruption policy, and diagnostics.
4. Return `AnimationIntent`; do not import `frame_source`, `pose_compositor`, Pillow, FastAPI, or browser code.
5. Ensure flight topology is `grounded -> takeoff -> airborne -> landing -> grounded`; bank/glide cannot be entered directly from idle.
6. Require winged flight clips and reject stale no-wing expectations.

**Tests:** graph census for all 39 poses or explicit `diagnostic_only`; every stable node reaches idle/hover; illegal wildcard edges; equal-priority ambiguity; zero duration; unknown marker/pose; duplicate marker emission; phase preservation; interruption before/during/after commitment; takeoff/landing order; unsupported-facing fallback; 10,000 random legal events without microstep overflow.

```bash
uv run pytest -q tests/wizard/test_animation_graph_runtime.py
uv run pytest -q tests/wizard/test_pose_selection.py tests/wizard/test_reference_avatar_pose_library.py
```

**Graph gates:** no production control resolves through `pose_override_id`; every promoted clip has an explicit entry, exit, interrupt, contact, root, and fallback policy; wings are present in required flight states.
**Rollback:** server continues loading graph v1; graph-v2 evaluator remains additive until `FPSE-090`.
**Evidence:** `evidence/cartoon-animation-program/fpse/FPSE-060-graph-audit.json`.
**Handoff:** ANIM signs the evaluator trace for each clip family before semantic integration.

### `FPSE-070` - Integrate reducer, grounded motion, and flight semantics

**Dependencies:** `FPSE-060`
**Owner:** FPSE semantic integration agent
**Allowed writes:**

```text
wizard_avatar/controller.py
wizard_avatar/locomotion.py
tests/wizard/test_locomotion.py
tests/wizard/test_pathing.py
tests/wizard/test_animation_channels.py
tests/wizard/test_animation_graph_runtime.py
```

**Implementation:**

1. Make one `reduce_tick(state, due_commands)` operation the only semantic mutation path.
2. Retain distance-driven ground phase and existing x/z world projection semantics.
3. Add walk/run acceleration, deterministic start/stop modes, and contact-safe stop requests.
4. Add altitude, vertical velocity, target altitude, grounded state, takeoff, hover/travel/bank, falling, and landing reducers.
5. Keep contact root on the ground while body altitude changes; expose visual root correction separately.
6. Feed typed semantic state into graph evaluation and apply crossed graph events once.
7. Ensure reset clears commands, leases, paths, region generations, altitude, visual correction, and secondary state.

**Tests:** existing paths and all eight movement directions; constant-speed walk distance/phase; walk/run switch; stop at contact; takeoff order; hover; flight travel; left/right bank; action while flying; controller loss safe hover/stop; landing first contact/compression/settle; reset from every mobility mode.

```bash
uv run pytest -q tests/wizard/test_locomotion.py tests/wizard/test_pathing.py tests/wizard/test_animation_channels.py tests/wizard/test_animation_graph_runtime.py
```

**Motion gates:**

- world distance per walk cycle within `+-5%` of configured stride;
- no phase reversal on compatible gait/facing changes;
- takeoff and landing states occur in declared order;
- feet never own contact while airborne;
- flight phase does not restart on compatible hover/travel/bank transitions;
- safe stop/hover occurs no later than 15 ticks after last valid direct input;
- simulation state at matching ticks is independent of 15/24/30 FPS rendering.

**Rollback:** set runtime configuration to `v1`; graph v1 and legacy controller remain available until final gate. Revert only this integration commit if semantic behavior regresses.
**Evidence:** `evidence/cartoon-animation-program/fpse/FPSE-070-motion-traces.ndjson` plus compact summary JSON.
**Handoff:** ANIM reviews clip/event traces and provides approved transition recipes; integration lead receives immutable snapshots.

### `FPSE-080` - Add backward-compatible FastAPI and WebSocket command adapters

**Dependencies:** `FPSE-070`, `SYS-CONTRACT-001`
**Owner:** FPSE API integration agent
**Allowed writes:**

```text
wizard_avatar/server.py
tools/run_wizard_avatar_server.py
tests/wizard/test_server_command_protocol.py
```

**Compatibility rules:**

1. Existing routes and route paths remain available.
2. Existing successful route responses retain all existing state keys; new runtime/ack metadata is additive.
3. Existing `{type, payload}` WebSocket commands remain accepted through a `legacy_adapter` envelope.
4. Existing `INIT:` and binary ASCILINE frame bytes remain unchanged for legacy viewers.
5. New clients use additive `POST /api/avatar/wizard/command` and WebSocket protocol `wizardjoe.asciline.v2` for typed acknowledgements/events.
6. HTTP and WebSocket use the same strict parser and runtime queue; neither calls controller methods directly.
7. `diagnostic_pose` is available only through an explicitly diagnostic route or flag and is not accepted as gameplay motion.
8. A viewer is passive unless it acquires a direct-control lease; merely opening a socket never claims control.

**Strict boundary models:** use Pydantic strict mode where available, but immediately translate to internal dataclasses. Unknown fields and coercion fail with structured errors.

**Tests:** every legacy route; new command route; malformed/coerced payloads; HTTP/WS envelope parity; ack fields; duplicate retry; stale/out-of-order; viewer/controller separation; disconnect release; legacy INIT and binary decode; reset keyframe; WebSocket cleanup and cancellation.

```bash
uv run pytest -q tests/wizard/test_server_command_protocol.py tests/wizard/test_stream_hub.py tests/wizard/test_codec.py
```

**API gates:** legacy tests pass unchanged where contract remains valid; accepted HTTP/WS equivalents yield identical envelope and semantic result; every v2 command gets exactly one ack; rejected inputs produce no partial state mutation.
**Rollback:** disable v2 command endpoint/subprotocol and route legacy adapters to v1 under one configuration switch; ASCILINE stream never changes.
**Evidence:** `evidence/cartoon-animation-program/fpse/FPSE-080-api-compatibility.json`.
**Handoff:** browser role receives protocol examples and failure matrix; systems role reviews socket lifecycle and framing.

### `FPSE-090` - Make the hub own runtime cadence and immutable rendering

**Dependencies:** `FPSE-080`
**Owner:** FPSE hub integration agent, with systems-role review
**Allowed writes:**

```text
wizard_avatar/stream.py
wizard_avatar/frame_source.py
tests/wizard/test_runtime_stream_integration.py
tests/wizard/test_stream_hub.py
tests/wizard/test_frame_source.py
```

The coordinator must hold both hotspot locks for the short serial wiring window. No ANIM or systems branch may edit these files concurrently.

**Implementation:**

1. `WizardFrameHub` owns one `AvatarRuntime`, one command inbox, one render deadline, and one fanout sequence.
2. Each loop wake advances the accumulator, obtains an immutable snapshot, renders only when due, encodes once, and fans out one message.
3. `frame_source` accepts a snapshot and cannot advance simulation or apply commands.
4. Add diagnostics: tick, revision, command queue depth, command watermark, lease owner/expiry, catch-up steps, dropped simulation ns, graph/node/clip/sample/contact, render ms, encode ms, subscribers, queue drops, and resyncs.
5. Preserve subscriber-local keyframe recovery and one simulation regardless of viewer count.
6. Add runtime/graph feature selection: `v1` emergency fallback and `v2` candidate on the same Python/ASCILINE path. Default remains v1 until `FPSE-110` and integrated visual gates pass.

**Tests/commands:**

```bash
uv run pytest -q tests/wizard/test_runtime_stream_integration.py tests/wizard/test_stream_hub.py tests/wizard/test_frame_source.py tests/wizard/test_codec.py
uv run pytest -q tests/wizard/test_e2e.py
```

**Hub gates:**

- renderer called with frozen snapshot and cannot mutate it;
- 1, 2, and 4 viewers produce identical simulation ticks and source frame hashes;
- a slow fifth viewer resyncs locally with no queue growth or delay for others;
- 15/24/30 FPS profiles produce identical state hashes at matching ticks;
- render overrun never creates a fractional or extra simulation step;
- existing adaptive keyframe/delta decoder tests remain green.

**Rollback:** select v1 through validated configuration; no second listener, renderer, codec, or browser exists.
**Evidence:** `evidence/cartoon-animation-program/fpse/FPSE-090-hub-matrix.json` and compact source-hash traces.
**Handoff:** systems role signs fanout/resync metrics; integration lead releases browser wiring.

### `FPSE-100` - Add deterministic replay and durable hash evidence

**Dependencies:** `FPSE-090`
**Owner:** FPSE evidence agent
**Allowed writes:**

```text
wizard_avatar/replay.py
wizard_avatar/canonical_hash.py
tools/replay_wizard_runtime.py
tools/verify_runtime_determinism.py
tests/wizard/test_runtime_replay.py
```

**Implementation:**

1. Implement the NDJSON model and canonical hashing in Section 4.6.
2. Record accepted and rejected commands, system expiry events, every tick hash, and rendered source hash.
3. Replay without sleeps, sockets, FastAPI, browser, or wall time.
4. Compare two runs and report the first divergent record with field-level state diff.
5. Add fixture scenarios: ground walk/turn/stop, run/land, takeoff/hover/bank/land, action interruption, speech while moving/flying, lease takeover rejection, disconnect expiry, and reset.
6. Keep raw frames out of Git; commit compact hashes and summaries only.

**Tests/commands:**

```bash
uv run pytest -q tests/wizard/test_runtime_replay.py
uv run python tools/verify_runtime_determinism.py --scenario all --runs 2 --output evidence/cartoon-animation-program/fpse/FPSE-100-replay
```

**Replay gates:** byte-identical tick-state and source-frame SHA-256 sequences for two runs; 1,000-command stress replay identical; first-difference output proven by a deliberate negative fixture; no Rust artifact or command in the manifest.
**Rollback:** evidence tooling is additive; if hash schema changes before freeze, increment replay schema and retain a reader for the immediately prior planning version only.
**Evidence:** output directory named above containing `manifest.json`, `commands.ndjson`, `run-1.ndjson`, `run-2.ndjson`, and `comparison.json`.
**Handoff:** PLAN validates artifact hashes; ANIM consumes event/frame indexes for visual evidence; browser role correlates presented hashes.

### `FPSE-110` - FPSE completion and cross-role handoff gate

**Dependencies:** `FPSE-100` plus ANIM visual signoff and systems stream signoff
**Owner:** FPSE lead/reviewer
**Allowed writes:** no production files; evidence summary is coordinator-owned

Run from the tested implementation SHA:

```bash
uv sync --locked
uv run pytest -q
uv run python tools/generate_reference_avatar_pose_cells.py
git diff --exit-code -- wizard_avatar/definitions/reference_avatar_pose_cells.json
uv run python tools/verify_animation_quality.py --strict --output-dir evidence/cartoon-animation-program/final/animation-quality
uv run python tools/verify_runtime_determinism.py --scenario all --runs 2 --output evidence/cartoon-animation-program/final/replay
uv run python tools/run_wizard_avatar_server.py --host 127.0.0.1 --port 8765
```

The server command is a live gate and runs in its own managed process. Against it, the coordinator must verify:

```bash
curl -fsS http://127.0.0.1:8765/api/avatar/wizard/state
curl -fsS http://127.0.0.1:8765/api/avatar/wizard/frame-hashes
```

**Completion criteria:** every criterion in Sections 7 and 8 passes; no required test is skipped; no Rust command runs; all evidence names the tested Git SHA; browser and server evidence come from port 8765; v2 becomes default only after coordinator promotion.
**Rollback:** if any gate fails, keep v1 default, record the failing work-item/commit/evidence path, and reopen only the smallest owning item.
**Handoff:** coordinator may integrate/publish only after independent FPSE determinism review, ANIM visual review, systems delivery review, and PLAN evidence/scope audit.

## 7. Measurable runtime and protocol gates

### Determinism and clocks

- Simulation mutates only on integer ticks at exactly 60 Hz.
- No call to locomotion, graph evaluation, or channel reducers receives a partial delta.
- Matching simulation ticks have identical canonical state hashes under 15, 24, and 30 FPS render schedules.
- Two complete replays have byte-identical command ack, runtime event, tick-state SHA-256, and source-frame SHA-256 sequences.
- A synthetic two-second scheduler stall executes no more than eight catch-up ticks in one event-loop turn, records discarded time, and expires stale direct input before resumed motion.
- Rendering the same snapshot twice yields identical cells and no state revision change.

### Commands and arbitration

- Every accepted command receives one ack with command ID, source sequence, server sequence, accepted tick, apply tick, state revision, and epoch.
- Duplicate IDs never apply twice; stale, expired, unauthorized, malformed, and overflowed commands never mutate state.
- All same-tick ordering permutations reduce identically after sorting by the server-assigned total order.
- One direct controller owns mobility at a time. Equal-priority contenders cannot steal it by packet timing.
- Release, disconnect, blur/visibility release, gamepad loss, or missing heartbeat clears intent within 15 ticks and initiates the authored safe stop/hover behavior.
- In deterministic in-process tests, accepted movement changes semantic intent by the next tick.
- On local port 8765, command receipt to semantic change is p95 `<=100 ms`; receipt to first frame containing that revision is p95 `<=180 ms`. The animation/browser stretch target is two 24 FPS presentation frames (`<=84 ms`) when scheduling permits.

### Typed state and motion graph

- Every region transition increments that region's generation exactly once.
- Illegal grounded/airborne/contact/wing/staff combinations fail invariant checks before rendering.
- Every production pose is in a reviewed clip/transition or explicitly `diagnostic_only`.
- Every promoted state reaches stable grounded idle or flying hover; no unapproved dead end or unbounded microstep cycle exists.
- Walk/run phase carries across compatible speed/facing changes; flight phase carries across compatible hover/travel/bank changes.
- Takeoff, airborne, bank/glide, landing contact, compression, and settle occur in authored order.
- Wings remain part of the accepted character and visibly participate in flight clips. No stale no-wings assertion may pass as a release gate.
- Unsupported flight facings use documented coherent fallback nodes rather than synthesized arbitrary morphs.

### ASCILINE delivery

- One Python hub owns one simulation on port 8765 regardless of subscriber count.
- Legacy HTTP routes, legacy WebSocket commands, `INIT:`, and adaptive binary frame decoding remain functional.
- New HTTP and WebSocket adapters produce equivalent internal envelopes and outcomes.
- Two normal viewers receive identical decoded frame hash sequences; a slow viewer resyncs without affecting simulation or other viewers.
- No source PNG, video, flattened frame sequence, client-side sprite engine, or Rust artifact participates at runtime.

## 8. Measurable visual gates supplied to ANIM/integration

FPSE does not approve aesthetics, but the runtime must expose enough data for these hard gates:

- Fixed-world transitions settle with root displacement `0` cells; no adjacent transition frame exceeds `1` cell unless authored root motion declares it.
- Planted foot or staff contact drifts `0` cells in stable contact and at most `1` cell on an explicitly approved release/acquire frame.
- Mouth, eye, staff-hand, and staff-tip anchor changes are at most `1` local cell between face/prop-compatible frames, excluding authored smear/attack windows.
- No production transition frame contains duplicate heads, duplicate staffs, detached face features, shredded mixed silhouettes, or undeclared floating cells.
- Output remains integer square cells with palette colors and no antialiasing, blur, or color interpolation.
- Takeoff shows anticipation before first no-contact frame; landing shows first contact, compression, and settle.
- Shadow remains at contact root while winged body altitude changes; shadow response is monotonic with altitude.
- Speech, blink, and supported expressions produce visible pixel changes on the reference-pose path without moving the body root.
- A ten-minute mixed walk/run/fly/action/speech session has no invalid state, stuck lease/action, unbounded queue, hash mismatch, decode error, or uncaught task exception.

Required evidence per promoted motion family:

```text
commands.ndjson
runtime-events.ndjson
tick-hashes.json
frame-hashes.json
anchor-contact-metrics.json
browser-console.json
contact-sheet.png
recording artifact URL and SHA-256
review.json with ANIM approver and tested commit
```

Only compact summaries/contact sheets belong in Git. Raw recordings, frames, traces, and long logs are workflow artifacts.

## 9. Rollback map

| Rollback ID | Protected checkpoint | Trigger | Action |
|---|---|---|---|
| `RB-FPSE-0` | pushed Python 39-pose baseline | contract/type tests fail | revert additive contract commit |
| `RB-FPSE-1` | contract schemas | runtime clock/queue fails | leave modules unused; v1 remains live |
| `RB-FPSE-2` | fixed runtime and queue | typed-state compatibility fails | restore v1 state projection/default |
| `RB-FPSE-3` | graph-v2 evaluator additive | graph authoring/visual family fails | keep graph v1 selected; disable only failed family |
| `RB-FPSE-4` | semantic v2 behind config | API compatibility fails | disable v2 endpoint/subprotocol; keep legacy adapters |
| `RB-FPSE-5` | hub integration | pacing/fanout/render mutation fails | select v1 runtime on the same hub/renderer/codec |
| `RB-FPSE-6` | v2 release candidate | final replay/browser/visual gate fails | keep v1 default, record first failing item, do not publish |

Rollback never starts a second service, swaps to Rust, changes the browser into the authority, or substitutes videos/PNGs. Schema evolution remains additive until all active branches have rebased. A failed motion family is disabled by graph configuration rather than reverting unrelated accepted families.

## 10. Handoff packets

Every FPSE item hands off a machine-readable packet containing:

```text
work_item_id
owner
branch
tested_commit_sha
baseline_sha
allowed_paths
changed_paths
dependency_results
commands_with_exit_codes
test_counts
schema_or_artifact_sha256
evidence_paths
rollback_id
known_limitations
reviewer
```

Role-specific handoffs:

### To ANIM

- frozen typed region and `AnimationIntent` fixtures;
- graph evaluator validation/error catalog;
- exact tick/marker/contact traces for every clip family;
- runtime fields needed by anchor/contact verifier;
- explicit confirmation that winged flight is required and direction coverage is capability-tiered.

ANIM acceptance is required before `FPSE-070` traces or `FPSE-090` frames can be promoted.

### To translated RUST/systems role

- runtime snapshot/epoch/sequence interface;
- command watermark and frame correlation fields;
- hub pacing and subscriber-resync traces;
- confirmation that binary ASCILINE bytes are unchanged or a reviewed versioned change exists.

Systems signoff is required before `FPSE-090` and `FPSE-110` pass.

### To browser/integration lead

- command/ack JSON examples and schemas;
- source ID/sequence/TTL/heartbeat requirements;
- release/disconnect semantics;
- additive state/diagnostic response example;
- v2 WebSocket text-message types while preserving binary frame handling.

The browser must prove keydown **and** keyup, blur/visibility release, gamepad disconnect, heartbeat, and no local world mutation.

### To PLAN/coordinator

- tested SHA and exact gate outputs;
- ownership audit with no out-of-scope paths;
- compact evidence manifest and heavy-artifact URLs/hashes;
- rollback checkpoint and feature-default state;
- explicit `rust_dependency_count: 0` and `production_listener: 127.0.0.1:8765` assertions.

## 11. Final FPSE definition of done

FPSE work is complete only when all of the following are true:

1. `PRG-B0`, `PRG-P0`, and the wing-contract correction are pushed and recorded.
2. `FPSE-010` through `FPSE-100` pass on one tested implementation SHA.
3. The service runs entirely in Python on port 8765 with no Rust toolchain installed.
4. Simulation is integer-tick, render-independent, replayable, and hash-verifiable.
5. Commands are typed, ordered, acknowledged, deduplicated, stale-safe, bounded, and arbitrated.
6. Direct control cannot remain stuck after release, disconnect, or timeout.
7. Typed regions represent grounded and winged flight behavior without contradictory state.
8. The graph runtime executes ANIM-authored clips and transitions deterministically without choosing raw poses as gameplay control.
9. Existing ASCILINE viewers and legacy HTTP/WebSocket controls remain compatible.
10. Independent ANIM, systems, PLAN, and coordinator reviews accept the same commit and evidence.

This plan deliberately builds the deterministic semantic spine before visual polish. Once that spine is stable, animation agents can tune timing and transition recipes repeatedly without changing command order, remote-control safety, simulation ownership, or ASCILINE delivery.
