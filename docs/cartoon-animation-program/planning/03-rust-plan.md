# Systems Translation and Rust Containment Plan

Status: Planning Wave 2 contribution

Role: Former Rust runtime role, reassigned to Python systems translation and Rust containment

Production target: ASCILINE Python server on port `8765`

Inputs read:

- `docs/cartoon-animation-program/research/01-first-principles-software.md`
- `docs/cartoon-animation-program/research/02-game-animation-motion.md`
- `docs/cartoon-animation-program/research/03-rust-runtime.md`
- `docs/cartoon-animation-program/research/04-project-delivery.md`

## 1. Binding Decisions

### 1.1 Production boundary

The deliverable is exclusively the ASCILINE Python application served on port
`8765`. Rust is not a production language, runtime, dependency, build step,
test gate, CI job, fallback, asset source, protocol authority, or acceptance
surface for this program.

No work item in this plan creates or modifies Rust code. No command in this plan
invokes Cargo. The failing Rust `future_pose_transitions` surface, reported as
357 failures across 170 authored transition checks, is historical evidence only
and cannot block, approve, or measure the Python deliverable.

### 1.2 Current winged and flying character contract

The accepted character is Wizard Joe with rainbow wings. Flying, hovering,
banking, takeoff, and landing are required motion families. The stale no-wings
statements in `docs/30-visual-tests.md` and `docs/37-completion-gate.md` must be
corrected by the shared contract owner before Contract Gate C0 closes.

The authoritative direction for implementation is:

- Preserve the current rainbow wings and their square-cell visual language.
- Support wing visibility and occlusion appropriate to front, back, side, and
  three-quarter poses.
- Treat wing phase and flight height as animation state, not decorative noise.
- Never remove wings to satisfy an obsolete visual test.
- Do not require both wings to be fully visible in every view; correct occlusion
  is acceptable and expected.

This plan records the resolution but does not edit shared contract documents.

### 1.3 Systems ideas translated to Python

Only these ideas are carried forward from general runtime engineering practice:

1. An integer-indexed, fixed-rate simulation clock.
2. A stable, ordered command inbox with explicit acceptance and application
   ticks.
3. Immutable previous/current snapshots so rendering cannot advance simulation.
4. Canonical deterministic replay and state hashing.
5. Bounded catch-up, bounded client queues, and explicit resynchronization.
6. Machine-readable runtime quality evidence.

They must be implemented idiomatically in Python and integrated into the
existing ASCILINE architecture. They are not ports of the Rust crate.

## 2. Role Ownership and Write Boundaries

The role name used in work-item records is `SYS-TRANSLATION`. It replaces the
historical `RUST` role label for implementation purposes.

### 2.1 Files this workstream may own

The systems workstream may add or edit only these paths after the coordinator
creates the corresponding worktree and records an allowlist:

- `wizard_avatar/runtime.py`
- `wizard_avatar/replay.py`
- `wizard_avatar/quality.py`
- `tools/replay_wizard_animation.py`
- `tools/verify_python_runtime_scope.py`
- `tools/run_python_animation_soak.py`
- `tests/wizard/test_runtime_clock.py`
- `tests/wizard/test_runtime_queue.py`
- `tests/wizard/test_runtime_snapshots.py`
- `tests/wizard/test_deterministic_replay.py`
- `tests/wizard/test_runtime_quality.py`
- `tests/wizard/test_python_runtime_scope.py`
- `tests/wizard/test_multiclient_runtime.py`
- compact committed summaries under
  `evidence/cartoon-animation-program/system/`

If an existing path differs after baseline recovery, the coordinator must
update this allowlist before implementation begins. An agent must not infer an
alternate path and write to it without approval.

### 2.2 Shared hot files reserved for the integration lead

This workstream must not directly modify the following without a recorded
one-writer transfer:

- `wizard_avatar/models.py`
- `wizard_avatar/controller.py`
- `wizard_avatar/frame_source.py`
- `wizard_avatar/stream.py`
- `wizard_avatar/server.py`
- `wizard_avatar/protocol.py`
- the animation graph JSON and pose manifest
- `web/avatar/wizardControls.ts`
- `web/avatar/wizardClient.ts`
- shared program trackers, registries, and contract documents

Changes needed in these files are delivered as an integration handoff containing
the exact call site, expected inputs and outputs, test fixture, and rollback
switch. The integration lead remains the only writer.

### 2.3 External ownership contracts

The systems workstream consumes, but does not define, the following:

| Contract | Owning role | Systems dependency |
| --- | --- | --- |
| Semantic command kinds and payload validation | First-principles software | `CommandEnvelope` and command disposition |
| Controller state transitions and leases | First-principles software | Pure `advance_tick` entry point |
| Clip, transition, marker, contact, and wing phase semantics | Animation/motion | Graph v2 schema and evaluator outputs |
| Baseline SHA, worktrees, shared tracker, CI policy | Project delivery | Gate status and path allowlists |
| Shared-file wiring | Integration lead | Hub/server/browser adapter changes |

## 3. Interface Freeze

The exact Python names may be adjusted once to match established repository
conventions during `SYS-C0-002`. After Contract Gate C0, fields and meanings are
frozen unless all consuming roles approve a schema revision.

### 3.1 Clock interface

`wizard_avatar/runtime.py` must expose an integer-tick clock with behavior
equivalent to this interface:

```python
class FixedTickClock:
    simulation_hz: int                 # 60
    tick_seconds: float                # 1 / simulation_hz
    simulation_tick: int               # starts at 0
    accumulator_seconds: float         # unconsumed monotonic time
    last_monotonic_seconds: float | None
    max_catch_up_ticks: int            # default 8
    catch_up_event_count: int
    dropped_time_seconds: float

    def ingest_time(self, now_monotonic_seconds: float) -> "TickBatch": ...
```

`TickBatch` fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `first_tick` | integer | First tick to execute, inclusive |
| `tick_count` | integer | Number of ticks to execute now |
| `alpha` | float in `[0, 1)` | Presentation interpolation only |
| `dropped_seconds` | non-negative float | Excess wall time discarded by the bounded catch-up policy |
| `catch_up_limited` | boolean | Whether the batch hit `max_catch_up_ticks` |

Required semantics:

- `time.monotonic()` is the wall-clock source in production.
- Tests inject time; no test sleeps to prove clock correctness.
- Simulation deadlines are integer ticks, never floating-point timestamps.
- Rendering reads `alpha` but never changes `simulation_tick`.
- A backward or non-finite injected timestamp is rejected explicitly.
- A long pause runs no more than `max_catch_up_ticks`; excess time is counted,
  surfaced in telemetry, and discarded rather than causing a spiral.

### 3.2 Command envelope and queue interface

The command schema is owned by the first-principles role. The systems queue must
consume these frozen fields without redefining their semantics:

| Field | Type | Required behavior |
| --- | --- | --- |
| `schema_version` | integer | Reject unsupported versions |
| `command_id` | string | Unique idempotency key |
| `source_id` | string | Stable controller/browser identity |
| `source_kind` | enum string | Browser, scripted replay, or approved source |
| `sequence` | integer | Strictly increasing per `source_id` |
| `kind` | enum string | Semantic command kind |
| `issued_at_ms` | integer | Diagnostic wall-clock timestamp only |
| `ttl_ms` | integer or null | Converted once to a tick deadline |
| `payload` | object | Validated by the owning semantic layer |

The server assigns this scheduling metadata:

| Field | Type | Meaning |
| --- | --- | --- |
| `received_order` | integer | Process-local monotonically increasing tiebreaker |
| `accepted_tick` | integer | Simulation tick at validation/acceptance |
| `apply_tick` | integer | Tick at which the command becomes visible |
| `priority` | integer | Frozen semantic priority supplied by arbitration |
| `expires_tick` | integer or null | Tick deadline derived from TTL |

Queue ordering is the stable tuple:

```text
(apply_tick, priority, source_id, sequence, received_order)
```

The coordinator must confirm whether lower or higher integer `priority` wins.
Once selected, the comparison direction becomes part of the replay schema and
cannot vary by call site.

Required queue dispositions are:

- `accepted`
- `duplicate`
- `stale_sequence`
- `expired`
- `unsupported_schema`
- `invalid_payload`
- `lease_rejected`
- `applied`

An acknowledgement record contains:

| Field | Type |
| --- | --- |
| `schema_version` | integer |
| `command_id` | string |
| `source_id` | string |
| `sequence` | integer |
| `disposition` | enum string |
| `accepted_tick` | integer or null |
| `apply_tick` | integer or null |
| `state_revision` | integer |
| `reason_code` | string or null |

The systems queue owns ordering, idempotency storage, due-command extraction,
and replay capture. It does not own movement, pose, action, lease, or facial
meaning.

### 3.3 Runtime snapshot interface

The simulation publishes an immutable `RuntimeSnapshot` after every completed
tick. Required fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `schema_version` | integer | Snapshot compatibility |
| `epoch` | integer | Increments on runtime reset/restart |
| `simulation_tick` | integer | Exact state tick |
| `state_revision` | integer | Increments for every published state |
| `previous_state` | immutable controller state | Source for interpolation |
| `current_state` | immutable controller state | Authoritative state |
| `command_sequence_watermark` | mapping | Highest applied sequence per source |
| `active_clip_id` | string | Current Graph v2 clip |
| `transition_id` | string or null | Active authored transition |
| `clip_frame` | integer | Current clip frame at 24 fps semantics |
| `contact_set` | tuple of strings | Current planted/contact anchors |
| `wing_phase` | enum/string or null | Current flight secondary-motion phase |
| `flight_height_cells` | integer or float | Semantic height above contact root |
| `events` | immutable tuple | Events emitted exactly on this tick |

The animation role owns the meaning of `active_clip_id`, `transition_id`,
`clip_frame`, `contact_set`, and `wing_phase`. The systems role only preserves,
hashes, transports, and measures them.

### 3.4 Frame telemetry interface

Every encoded frame must have a telemetry record keyed by `epoch` and
`frame_sequence`:

| Field | Type |
| --- | --- |
| `schema_version` | integer |
| `epoch` | integer |
| `frame_sequence` | integer |
| `simulation_tick` | integer |
| `state_revision` | integer |
| `render_profile` | string |
| `source_hash_sha256` | 64-character lowercase hex |
| `transport_hash` | existing transport hash type |
| `render_ms` | float |
| `encode_ms` | float |
| `broadcast_ms` | float |
| `connected_clients` | integer |
| `max_client_queue_depth` | integer |
| `dropped_client_frames` | integer |
| `resync_count` | integer |
| `catch_up_limited` | boolean |

The existing transport hash remains intact for protocol compatibility. SHA-256
is added for durable replay and evidence comparisons; it does not replace the
wire hash unless a separate protocol version explicitly does so.

### 3.5 Replay artifact interface

A replay is newline-delimited canonical JSON with one header followed by
ordered records. Canonical JSON uses UTF-8, sorted keys, compact separators,
finite numeric values, and explicit quantization for any allowed float before
hashing.

`ReplayHeader` fields:

- `record_type: "header"`
- `schema_version`
- `baseline_commit`
- `python_version`
- `runtime_profile`
- `simulation_hz`
- `render_fps`
- `initial_epoch`
- `initial_state_sha256`
- `graph_sha256`
- `pose_manifest_sha256`
- `seed`

`ReplayCommandRecord` fields:

- `record_type: "command"`
- all accepted command envelope fields
- `received_order`
- `accepted_tick`
- `apply_tick`
- `disposition`
- `state_revision_after_apply`
- `state_sha256_after_apply`

`ReplayFrameRecord` fields:

- `record_type: "frame"`
- `epoch`
- `frame_sequence`
- `simulation_tick`
- `state_revision`
- `active_clip_id`
- `transition_id`
- `clip_frame`
- `contact_set`
- `wing_phase`
- `source_hash_sha256`

Replay comparison ignores only explicitly declared diagnostic wall-clock fields.
No semantic field may be omitted from comparison to make a test pass.

## 4. Work-Item Dependency Graph

External gate aliases used below:

- `EXT-B0`: project-delivery baseline recovery and explicit staging allowlist
- `EXT-P0`: all four research and planning artifacts saved and reviewed
- `EXT-C0-GRAPH`: animation Graph v2 schema and marker/contact contracts frozen
- `EXT-C0-CMD`: semantic command, lease, and arbitration contracts frozen
- `EXT-I0-LOCK`: integration lead grants the one-writer shared-file lock

```text
EXT-B0 + EXT-P0
  -> SYS-C0-001 (winged/flying contract resolution)
  -> SYS-C0-002 (Python systems interface freeze)
  -> SYS-X0-001 (Rust exclusion validator)

SYS-C0-002 + EXT-C0-CMD
  -> SYS-E1-001 (fixed clock)
  -> SYS-E1-002 (ordered command inbox)

SYS-E1-001
  -> SYS-E1-003 (immutable snapshots)

SYS-E1-002 + SYS-E1-003 + EXT-C0-GRAPH
  -> SYS-E1-004 (deterministic replay)

SYS-E1-001 + SYS-E1-003
  -> SYS-E1-005 (pacing, fanout, resync)
  -> SYS-E1-006 (quality telemetry)

SYS-E1-001..006 + SYS-X0-001 + EXT-I0-LOCK
  -> SYS-I0-001 (integration handoff and wiring)

SYS-I0-001
  -> SYS-QA-001 (determinism matrix)
  -> SYS-QA-002 (multiclient and resync)
  -> SYS-QA-003 (latency and soak)

SYS-QA-001..003 + all animation-family gates
  -> SYS-X0-002 (clean-clone Python-only acceptance)
  -> SYS-F0-001 (Rust removal decision package)
```

No downstream item may start based on an agent's verbal claim. Its dependency
must have a tracker record with a baseline SHA, changed-path allowlist, command
results, evidence hashes, reviewer, and status `accepted`.

## 5. Detailed Work Items

### SYS-C0-001: Ratify the winged and flying contract

Owner: `PROJECT-DELIVERY` or designated shared contract owner

Systems role: reviewer only

Dependencies: `EXT-B0`, `EXT-P0`

Shared paths requiring the contract owner's lock:

- `docs/30-visual-tests.md`
- `docs/37-completion-gate.md`
- any central contract registry that repeats the no-wings rule

Required change:

1. Remove or supersede every requirement that Wizard Joe have no wings.
2. State that rainbow wings and flight motion are accepted production behavior.
3. Define view-aware occlusion so hidden rear/side wings are not false failures.
4. Add takeoff, hover/flap, glide/bank, and landing to the required motion set.

Acceptance:

- A repository search reports no active acceptance statement requiring no wings.
- Graph and visual gates can name `wing_phase` and `flight_height_cells` without
  contradicting a numbered document.
- Animation and first-principles reviewers sign the same contract revision.

Evidence:

- `evidence/cartoon-animation-program/contracts/winged-flight-resolution.md`
- compact search result proving stale active wording is gone

Rollback point: the contract-only commit. Reverting it must not alter production
code or generated pose assets.

Handoff criterion: `SYS-C0-002` receives the final wing and flight field names.

### SYS-C0-002: Freeze Python systems interfaces

Owner: `SYS-TRANSLATION`

Dependencies: `EXT-B0`, `EXT-P0`, `SYS-C0-001`

Owned output:

- this plan's interface definitions, mapped to the coordinator's shared schema
  registry by the registry owner
- no production behavior in this item

Steps:

1. Reconcile Python minimum-version constraints with dataclass/type syntax.
2. Confirm `simulation_hz=60`, Graph v2 authored timing at 24 fps, and the
   integer mapping policy between them.
3. Confirm queue priority comparison direction.
4. Confirm immutable controller-state representation.
5. Confirm canonical JSON float quantization or eliminate floats from semantic
   state hashes.
6. Confirm protocol schema-version ownership and compatibility behavior.
7. Record all names and decisions in the shared registry through the registry
   owner.

Acceptance:

- First-principles, animation, systems, and integration owners approve every
  field in Sections 3.1 through 3.5.
- No field has two owners.
- No production interface references a Rust type, crate, artifact, or test.

Evidence:

- `evidence/cartoon-animation-program/system/interface-freeze.json`
- SHA-256 of the accepted schema registry

Rollback point: schema-freeze documentation commit.

Handoff criterion: tracker marks `EXT-C0-CMD` and `EXT-C0-GRAPH` accepted.

### SYS-X0-001: Add the Rust exclusion validator

Owner: `SYS-TRANSLATION`

Dependencies: `EXT-B0`, `EXT-P0`

Owned paths:

- `tools/verify_python_runtime_scope.py`
- `tests/wizard/test_python_runtime_scope.py`

Validator checks:

1. Default Python server and demo commands contain no Cargo or Rust subprocess.
2. Python modules import no Rust extension, FFI binding, generated Rust asset,
   or Rust-produced manifest.
3. Production HTML/TypeScript references no Rust server endpoint or port `8787`.
4. CI and acceptance commands for this program do not invoke Cargo.
5. Committed compact evidence does not claim Rust tests approve Python behavior.
6. Port `8765` is the only documented production port.
7. Rust directories, if retained historically, are outside Python package data,
   release manifests, and runtime path lookup.
8. The validator itself contains no blanket ban on prose that documents the
   historical Rust detour; it distinguishes production references from history.

Required command:

```bash
python3 tools/verify_python_runtime_scope.py \
  --root . \
  --json evidence/cartoon-animation-program/system/rust-exclusion.json
```

Tests:

```bash
python3 -m unittest tests.wizard.test_python_runtime_scope
```

Acceptance:

- Exit `0` on the approved baseline and each accepted Python implementation
  merge.
- A fixture containing a Cargo command, a Rust import, port `8787`, or a Rust
  fallback fails with a precise path and rule code.
- Scan duration is below 5 seconds on the repository baseline, excluding ignored
  generated directories.

Evidence:

- `evidence/cartoon-animation-program/system/rust-exclusion.json`
- fields: `schema_version`, `baseline_commit`, `checked_paths`, `ignored_paths`,
  `rules`, `violations`, `duration_ms`, `result`

Rollback point: additive validator commit. Revert it if it produces ambiguous
false positives; Rust must remain manually excluded while the rule is corrected.

Handoff criterion: project delivery wires this Python command into the program's
Python acceptance workflow without adding a Rust job.

### SYS-E1-001: Implement the deterministic fixed-tick clock

Owner: `SYS-TRANSLATION`

Dependencies: `SYS-C0-002`, `EXT-C0-CMD`

Owned paths:

- `wizard_avatar/runtime.py`
- `tests/wizard/test_runtime_clock.py`

Implementation requirements:

1. Implement `FixedTickClock` and `TickBatch` from Section 3.1.
2. Use 60 simulation ticks per second.
3. Accept an injected monotonic time source.
4. Bound catch-up to 8 ticks by default.
5. Preserve a presentation alpha without allowing presentation to mutate state.
6. Reset explicitly by incrementing epoch through the runtime owner, never by
   silently setting the tick backward.

Focused tests:

- Exact tick counts for 1, 10, 60, 600, and 36,000 simulated ticks.
- Irregular input deltas produce the same tick count as regular deltas for the
  same elapsed time when no catch-up limit is crossed.
- Render polling at 15, 24, 30, 60, and 120 fps does not change final state tick.
- A one-second stall executes at most 8 catch-up ticks and records dropped time.
- Backward, NaN, and infinite timestamps fail explicitly.
- Repeated reset increments epoch and does not reuse `(epoch, tick)` identity.

Commands:

```bash
python3 -m unittest tests.wizard.test_runtime_clock
python3 -m unittest discover tests
```

Measurable gate:

- Zero final-state or event-order differences across 15/24/30 presentation fps
  for a 60-second scripted scenario.
- No tick batch exceeds 8 ticks under the default policy.
- Long-run tick count is exact at 10 minutes of injected time.

Evidence:

- `evidence/cartoon-animation-program/system/runtime-clock.json`
- Include expected/actual ticks, catch-up events, dropped time, presentation fps,
  Python version, and baseline commit.

Rollback point: additive runtime module commit before shared hub wiring.

Handoff criterion: integration lead receives a pure API demonstration that
advances injected controller state without importing server or renderer code.

### SYS-E1-002: Implement the ordered command inbox

Owner: `SYS-TRANSLATION`

Semantic contract owner: `FIRST-PRINCIPLES`

Dependencies: `SYS-C0-002`, `EXT-C0-CMD`

Owned paths:

- queue classes within `wizard_avatar/runtime.py`
- `tests/wizard/test_runtime_queue.py`

Implementation requirements:

1. Consume the frozen command envelope; do not duplicate semantic validation.
2. Assign `received_order`, `accepted_tick`, `apply_tick`, and `expires_tick`.
3. Reject duplicate `command_id` and stale per-source sequence deterministically.
4. Extract due commands in the exact frozen tuple order.
5. Make queue capacity explicit and reject overflow with a reason code; never
   silently discard control commands.
6. Emit acknowledgement records for acceptance, rejection, expiry, and apply.
7. Keep wall-clock milliseconds diagnostic only after TTL conversion.

Focused tests:

- Same-tick commands from one source apply in increasing sequence order.
- Same-tick commands from multiple sources use the frozen priority/source/order
  rules identically across repeated runs.
- Duplicate retries do not apply twice.
- Expired commands never mutate state.
- Queue overflow is observable and deterministic.
- Lease rejection remains owned by arbitration but is captured faithfully.
- Reset starts a new epoch while preserving explicit idempotency policy.

Commands:

```bash
python3 -m unittest tests.wizard.test_runtime_queue
python3 -m unittest discover tests
```

Measurable gate:

- 100 repeated randomized-order fixtures with a fixed seed produce byte-identical
  acknowledgement and application logs.
- Zero silently dropped commands.
- Queue depth never exceeds the configured capacity.

Evidence:

- `evidence/cartoon-animation-program/system/command-ordering.json`
- Include seed, command count, dispositions, max depth, overflow count, and log
  SHA-256.

Rollback point: additive queue commit before hub integration.

Handoff criterion: first-principles owner approves acknowledgements for movement,
action, speech, stop, lease expiry, and emergency-neutral commands.

### SYS-E1-003: Separate simulation snapshots from rendering

Owner: `SYS-TRANSLATION`

Dependencies: `SYS-E1-001`, controller state immutability decision from
`FIRST-PRINCIPLES`

Owned paths:

- snapshot types and publisher within `wizard_avatar/runtime.py`
- `tests/wizard/test_runtime_snapshots.py`

Implementation requirements:

1. Publish previous/current snapshots once per completed tick.
2. Ensure rendering can read snapshots and alpha but cannot call simulation
   advancement.
3. Ensure event tuples are immutable and associated with exactly one tick.
4. Preserve Graph v2 clip, contact, staff, face, wing, and flight fields.
5. Expose a reset epoch so clients can distinguish restart from sequence wrap.

Focused tests:

- Repeated render calls between ticks do not change state revision or tick.
- Skipping render calls does not skip simulation events.
- Events appear on one snapshot only unless authored as persistent state.
- Snapshot mutation attempts fail or cannot affect stored runtime state.
- Wing phase and flight height survive snapshot publication unchanged.

Commands:

```bash
python3 -m unittest tests.wizard.test_runtime_snapshots
python3 -m unittest discover tests
```

Measurable gate:

- State hashes are identical with zero, one, or five render reads per tick.
- Every authored one-shot marker appears exactly once in a 39-pose traversal
  scenario.

Evidence:

- `evidence/cartoon-animation-program/system/snapshot-separation.json`

Rollback point: additive snapshot commit before integration wiring.

Handoff criterion: animation owner verifies all graph/event fields required for
walk, flight, action, face, speech, staff, and effects are present.

### SYS-E1-004: Implement deterministic replay and canonical hashing

Owner: `SYS-TRANSLATION`

Dependencies: `SYS-E1-002`, `SYS-E1-003`, `EXT-C0-GRAPH`

Owned paths:

- `wizard_avatar/replay.py`
- `tools/replay_wizard_animation.py`
- `tests/wizard/test_deterministic_replay.py`

Implementation requirements:

1. Write and read the NDJSON schema in Section 3.5.
2. Canonicalize semantic records before SHA-256 hashing.
3. Refuse non-finite numeric values.
4. Compare replay headers before comparing records and report the first semantic
   divergence with record index and field path.
5. Support capture from scripted command input without a browser.
6. Keep transport hashes and durable evidence hashes as separate fields.
7. Include wing phase, flight height, contacts, transition, and event markers in
   semantic comparisons.

Focused tests:

- Record, replay, and re-record produce byte-identical canonical records.
- The same scenario at render fps 15/24/30 yields identical semantic state hashes.
- A changed command sequence, clip marker, wing phase, contact, or graph hash is
  detected at the first affected record.
- Diagnostic wall-clock differences do not alter semantic comparison.
- Unsupported replay schema fails before applying a command.

Commands:

```bash
python3 -m unittest tests.wizard.test_deterministic_replay
python3 tools/replay_wizard_animation.py \
  --scenario tests/fixtures/cartoon/full-motion-scenario.json \
  --render-fps 24 \
  --output evidence/cartoon-animation-program/system/replay-a.ndjson
python3 tools/replay_wizard_animation.py \
  --scenario tests/fixtures/cartoon/full-motion-scenario.json \
  --render-fps 24 \
  --output evidence/cartoon-animation-program/system/replay-b.ndjson
cmp \
  evidence/cartoon-animation-program/system/replay-a.ndjson \
  evidence/cartoon-animation-program/system/replay-b.ndjson
```

Measurable gate:

- Byte-identical replay output across two clean invocations on the same supported
  Python version and baseline.
- Identical semantic state hashes across render fps 15, 24, and 30.
- First-divergence reporting identifies a deliberately changed fixture field.

Evidence:

- `evidence/cartoon-animation-program/system/replay-a.ndjson`
- `evidence/cartoon-animation-program/system/replay-b.ndjson`
- `evidence/cartoon-animation-program/system/replay-comparison.json`

Only compact comparison summaries and representative bounded replays should be
committed. Large soak logs remain external artifacts with recorded SHA-256.

Rollback point: replay module/tool commit. Runtime behavior remains usable if
the replay tool is reverted; deterministic acceptance remains blocked.

Handoff criterion: animation owner supplies a scenario that visits every
promoted motion family, including winged flight, and first-principles supplies
remote-control command fixtures.

### SYS-E1-005: Define bounded pacing, fanout, and resynchronization

Owner: `SYS-TRANSLATION`

Dependencies: `SYS-E1-001`, `SYS-E1-003`

Owned paths:

- reusable pacing/fanout primitives in `wizard_avatar/quality.py` or a path
  approved at C0
- `tests/wizard/test_multiclient_runtime.py`

Shared-file handoffs:

- `wizard_avatar/stream.py`
- `wizard_avatar/server.py`
- `wizard_avatar/protocol.py`
- `web/avatar/wizardClient.ts`

Required behavior:

1. Simulation remains 60 Hz while presentation remains independently selectable,
   with the production profile at 24 fps unless the shared contract changes.
2. One slow client cannot block simulation or other clients.
3. Each client queue has an explicit maximum depth.
4. When a frame is dropped, the client receives or can request a full-frame
   resynchronization rather than decoding deltas against an unknown base.
5. Epoch and frame sequence identify resets and gaps.
6. Disconnect cleanup removes queues and metrics without leaking tasks.
7. Browser diagnostics report source frame received, decode complete, and
   presentation complete separately.

Focused tests:

- Fast and slow mock clients connected simultaneously.
- Forced queue overflow and full-frame resync.
- Disconnect during broadcast and reconnect with a new epoch/sequence baseline.
- 15/24/30 fps presentation against identical simulation.
- Codec hash and decoded frame parity after a resync.

Commands:

```bash
python3 -m unittest tests.wizard.test_multiclient_runtime
python3 -m unittest discover tests
```

Measurable gate:

- Queue depth never exceeds the configured per-client limit.
- Fast-client delivered cadence remains within 5 percent of target while a slow
  client is intentionally stalled.
- Every detected sequence gap either resynchronizes or closes explicitly; no
  silent delta corruption.
- Decoded frame hash equals source frame hash after every forced resync.

Evidence:

- `evidence/cartoon-animation-program/system/multiclient-resync.json`

Rollback point: additive primitives commit and a separate shared-file wiring
commit. Revert wiring first while preserving the tested primitive.

Handoff criterion: integration lead receives exact method calls and a fixture
that fails on the old unbounded/blocking behavior and passes with new wiring.

### SYS-E1-006: Implement Python-native runtime quality telemetry

Owner: `SYS-TRANSLATION`

Dependencies: `SYS-E1-001`, `SYS-E1-003`

Owned paths:

- `wizard_avatar/quality.py`
- `tools/run_python_animation_soak.py`
- `tests/wizard/test_runtime_quality.py`

Metrics required:

- simulation tick and epoch
- command accepted-to-applied tick latency
- command applied-to-source-frame latency
- source-frame-to-decoded-frame latency
- decoded-frame-to-presented-frame latency when browser evidence is available
- render, encode, and broadcast duration
- catch-up event count and dropped wall time
- command inbox depth and dispositions
- per-client frame queue depth and dropped frames
- resync count and disconnect reason
- state, source-frame, and decoded-frame hashes

Focused tests:

- Metrics are monotonic where specified.
- Empty percentiles produce explicit null/no-sample output rather than zero.
- One injected outlier does not corrupt sample counts.
- Hash mismatch identifies epoch/frame sequence and both hashes.
- Bounded retention prevents telemetry growth during a 10-minute injected soak.

Commands:

```bash
python3 -m unittest tests.wizard.test_runtime_quality
python3 tools/run_python_animation_soak.py \
  --duration-seconds 600 \
  --render-fps 24 \
  --output evidence/cartoon-animation-program/system/soak-summary.json
```

Measurable gate:

- p95 semantic input response is no more than 100 ms.
- p95 visible response is no more than 180 ms end to end.
- Preferred interactive gate: input accepted within 1 simulation tick and visible
  within 2 presentation frames when measured without external browser scheduling
  outliers.
- No unbounded queue or telemetry growth over 10 minutes.
- Zero source/decode hash mismatches after valid resync.

Evidence:

- `evidence/cartoon-animation-program/system/soak-summary.json`
- `evidence/cartoon-animation-program/system/frame-parity.ndjson`

Rollback point: telemetry commit. Observability can be reverted without changing
animation semantics, but final quality acceptance remains blocked.

Handoff criterion: project-delivery owner approves artifact size policy and the
integration lead provides browser presentation timestamps.

### SYS-I0-001: Integrate the Python runtime into port 8765

Owner: `INTEGRATION-LEAD`

Systems role: supplies reviewed modules, tests, and a line-specific wiring guide

Dependencies: `SYS-E1-001` through `SYS-E1-006`, `SYS-X0-001`, `EXT-I0-LOCK`

Shared paths expected to change under the integration lead:

- `wizard_avatar/frame_source.py`
- `wizard_avatar/stream.py`
- `wizard_avatar/server.py`
- `wizard_avatar/protocol.py`
- browser control/client paths selected by the frontend owner

Integration sequence:

1. Instantiate one runtime per live Wizard frame hub.
2. Route validated commands into the ordered inbox, not direct state mutation.
3. Advance simulation only from the fixed clock.
4. Publish immutable snapshots after each tick.
5. Render snapshots at presentation cadence without advancing simulation.
6. Attach epoch, frame sequence, state revision, and telemetry to the existing
   compatible protocol surface.
7. Preserve existing ASCILINE codec and square-cell compositor.
8. Wire bounded per-client queues and full-frame resync.
9. Keep the legacy graph/runtime switch available only through the declared
   rollback window; do not add a second renderer.
10. Confirm server listens on port `8765` and no Rust process is required.

Mandatory commands after the merge:

```bash
python3 -m unittest discover tests
python3 tools/generate_reference_avatar_pose_cells.py --check-deterministic
python3 tools/verify_animation_quality.py --strict
python3 tools/verify_python_runtime_scope.py \
  --root . \
  --json evidence/cartoon-animation-program/system/rust-exclusion.json
python3 tools/run_wizard_avatar_server.py --port 8765
curl -fsS http://127.0.0.1:8765/
```

The server command is run in a managed background session and stopped after
smoke verification. The coordinator records the PID, listener, command, and
shutdown result.

Acceptance:

- Full Python test suite passes.
- Deterministic generator and strict Python animation quality checks pass.
- Port `8765` serves the real Python demo.
- No Rust toolchain, process, artifact, or port is needed.
- Rendering no longer advances simulation.
- Existing clients either remain compatible or receive an explicit protocol
  schema/version error with migration instructions.

Evidence:

- `evidence/cartoon-animation-program/system/integration-gate.json`
- bounded server log, HTTP result, listener evidence, protocol version, and all
  command exit codes

Rollback point:

- Revert the single integration wiring commit or select the recorded legacy
  runtime mode during its temporary rollback window.
- Keep the ASCILINE renderer and codec unchanged during rollback.
- Do not fall back to Rust.

Handoff criterion: all four role reviewers accept I0 before motion-family
promotion begins.

### SYS-QA-001: Run the deterministic cadence matrix

Owner: `SYS-TRANSLATION`

Dependencies: `SYS-I0-001`

Scenarios:

1. Idle breathing and blink.
2. Walk, turn, stop, and resume.
3. Run start, charge, stop, and land.
4. Winged takeoff, hover/flap, glide, bank both directions, and landing.
5. Staff cast and guard while moving.
6. Explain, point, shush, celebrate, and hit/fall/recover.
7. Control lease expiry and emergency neutral.
8. All 39 integrated poses reached through authored clips or explicit showcase
   mode, with showcase excluded from motion-quality acceptance.

Matrix:

| Variable | Values |
| --- | --- |
| Presentation fps | 15, 24, 30 |
| Input cadence | regular, burst, same-tick contention |
| Stall | none, 100 ms, 500 ms, 1000 ms |
| Run count | 3 identical repetitions per cell |

Gates:

- Semantic replay hashes identical across presentation fps.
- Each identical repetition is byte-identical.
- Event order identical across all non-expired equivalent inputs.
- Catch-up never exceeds the configured cap.
- No full-body hashed dissolve appears in production motion.
- Wing phase does not reset spuriously across compatible flight transitions.
- Root/contact/face/staff visual gates from the animation report remain passing.

Evidence:

- `evidence/cartoon-animation-program/system/determinism-matrix.json`
- one compact divergence report per failure, never overwritten

Rollback point: the first motion-family or integration commit that changes the
last known passing matrix cell.

Handoff criterion: animation owner signs visual semantics and first-principles
owner signs command/state semantics.

### SYS-QA-002: Run multiclient, reconnect, and resync acceptance

Owner: `SYS-TRANSLATION`

Dependencies: `SYS-I0-001`

Test topology:

- one normal-speed decoder
- one intentionally slow decoder
- one reconnecting decoder
- one command source holding and releasing a movement lease

Gates:

- Fast client maintains target presentation cadence within 5 percent.
- Slow client queue remains bounded and records drops.
- Reconnecting client obtains a full baseline before applying deltas.
- Epoch/frame gaps never produce an unreported corrupt frame.
- Source and decoded hashes match after resync.
- Stop/release becomes visible within the latency gate.
- Server remains responsive on port `8765` throughout.

Commands:

```bash
python3 -m unittest tests.wizard.test_multiclient_runtime
python3 tools/run_python_animation_soak.py \
  --duration-seconds 120 \
  --clients normal,slow,reconnecting \
  --output evidence/cartoon-animation-program/system/multiclient-soak.json
```

Evidence:

- `evidence/cartoon-animation-program/system/multiclient-soak.json`
- decoded/source hash samples and queue-depth time series summary

Rollback point: fanout/resync integration commit.

Handoff criterion: browser/frontend owner confirms no visual corruption and
project-delivery owner confirms bounded artifact storage.

### SYS-QA-003: Run the final latency and 10-minute soak gate

Owner: `SYS-TRANSLATION`

Dependencies: `SYS-I0-001`, all promoted animation-family gates

Workload:

- continuous movement around the viewport
- repeated walk/run/fly transitions
- alternating banks and turns
- action overlays, staff motion, facial/speech channels
- periodic disconnect/reconnect
- periodic injected 100 ms and 500 ms stalls
- all stop/release paths

Gates:

- 10 minutes without unhandled exception, deadlock, runaway task, or memory/
  queue growth.
- p95 semantic response no more than 100 ms.
- p95 presented response no more than 180 ms.
- Zero invalid delta application.
- Zero silent command loss.
- Zero source/decode hash mismatches after valid resync.
- At least 99 percent of 24 fps presentation intervals within the program's
  agreed jitter band, with the exact band frozen at C0 and reported rather than
  inferred after execution.
- Final runtime returns to neutral after controls are released or lease expires.

Evidence:

- `evidence/cartoon-animation-program/system/soak-summary.json`
- `evidence/cartoon-animation-program/system/runtime-gate.md`
- external full log URI/path and SHA-256, not the full heavy log in Git

Rollback point: latest promoted family or integration commit correlated with
the first failing metric.

Handoff criterion: all metric gates have sample counts, percentiles, thresholds,
and pass/fail results; no qualitative `looks good` substitutes for telemetry.

### SYS-X0-002: Prove clean-clone Python-only acceptance

Owner: `PROJECT-DELIVERY`

Systems role: supplies validator and reviews output

Dependencies: `SYS-QA-001`, `SYS-QA-002`, `SYS-QA-003`

Environment requirements:

- fresh clone at the accepted commit
- supported Python installed
- no Rust toolchain requirement
- no pre-existing generated pose/runtime artifacts outside documented Python
  setup
- port `8765` available

Required checks:

1. Install only documented Python/web dependencies.
2. Run the complete Python test and quality command set.
3. Run `verify_python_runtime_scope.py`.
4. Start the Python server on `8765`.
5. Exercise remote controls and at least idle, walking, running, flying, action,
   face, speech, staff, and recovery behavior.
6. Stop the server and verify no listener remains.

Acceptance:

- Every required command exits `0`.
- The demo works without Cargo, `rustc`, a Rust binary, or port `8787`.
- The accepted winged/flying design appears in the live Python demo.
- Evidence records the exact commit and dependency lock hashes.

Evidence:

- `evidence/cartoon-animation-program/system/clean-clone-python-only.json`

Rollback point: final pre-release integration commit.

Handoff criterion: project-delivery owner may mark the Python release candidate
accepted; Rust status remains irrelevant to that decision.

### SYS-F0-001: Make the eventual Rust removal decision

Owner: `PROJECT-DELIVERY` with `SYS-TRANSLATION` audit support

Dependencies: `SYS-X0-002` and final Python release acceptance

This is a decision package, not Rust implementation work.

Decision options:

- `REMOVE`: delete the historical Rust crate, Rust-only web demo, generated
  target artifacts, Rust evidence, and production-facing Rust references in a
  separate reversible cleanup change.
- `ARCHIVE`: retain a clearly labeled historical snapshot outside production
  paths for a defined time, with no CI, dependency, runtime, or acceptance role.

Recommended default: `REMOVE` after the accepted Python release is tagged and
the clean-clone gate passes. Keeping a duplicate runtime creates future ambiguity
and contradicts the sole-authority production boundary.

Removal preconditions:

1. Python release candidate passes all final gates.
2. No Python source, browser source, package manifest, docs command, CI job, or
   evidence generator consumes a Rust artifact.
3. Any still-useful design rationale has been translated into Python-owned docs.
4. Repository history and release tag preserve recoverability.
5. Cleanup is isolated in its own reviewed commit or pull request.

Decision artifact fields:

- `decision`
- `decision_date`
- `python_release_commit`
- `clean_clone_evidence_sha256`
- `remaining_rust_paths`
- `remaining_production_references`
- `translated_rationale_paths`
- `cleanup_owner`
- `rollback_commit`
- `reviewers`

Evidence:

- `evidence/cartoon-animation-program/system/rust-removal-decision.md`
- machine-readable companion JSON if required by the shared tracker

Handoff criterion: a separately approved cleanup task is created only after the
decision. This program assigns no Rust coding, repair, parity, or test work.

## 6. Motion-Family Promotion Gates Seen by This Role

The animation role owns artistic approval. The systems role supplies deterministic
and runtime evidence for each family before the next family is promoted.

| Family | Required systems assertions | Required animation assertions |
| --- | --- | --- |
| Idle | Stable tick/event order; no render-driven mutation | Clean breathe/blink; face anchors stable |
| Walk/turn | Distance and contact events replay identically | Foot drift <= 1 local cell; stride variation <= 5% |
| Run | Start/stop commands ordered; stop visible within latency gate | Anticipation, attack, recovery; no root pop |
| Flight | `wing_phase` and height in snapshots/replay | Takeoff/hover/flap/glide/bank/land read clearly |
| Actions | Markers emitted exactly once | Face/staff anchors <= 1 cell except authored attack |
| Face/speech | Channel events deterministic; shush precedence recorded | Mouth/eye alignment stable; shush suppresses speech mouth |
| Full composition | Identical source hashes per replay | No duplicate staff/face, dissolve, or incoherent overlap |

Additional winged/flying gates:

- Takeoff begins grounded, releases contact, increases flight height, then enters
  a flight clip in that order.
- Landing decreases flight height, establishes contact, then settles into a
  grounded clip in that order.
- Flight feet do not own the ground shadow while airborne.
- Shadow response changes monotonically with authored flight height.
- Compatible flight transitions preserve wing phase instead of restarting at
  frame zero.
- Left/right bank commands do not mirror staff hand, face, or wing occlusion
  incorrectly.

## 7. Rollback Strategy

### 7.1 Checkpoints

Create one narrow commit after each accepted item:

1. `SYS-X0-001` exclusion validator
2. `SYS-E1-001` fixed clock
3. `SYS-E1-002` ordered command inbox
4. `SYS-E1-003` immutable snapshots
5. `SYS-E1-004` replay
6. `SYS-E1-005` pacing/fanout primitives
7. `SYS-E1-006` telemetry
8. `SYS-I0-001` shared integration wiring

Do not squash these checkpoints before final acceptance unless the project
delivery owner preserves an equivalent rollback map.

### 7.2 Temporary compatibility switches

During integration only, the existing Python runtime/Graph v1 may remain as a
rollback selection. The switch must:

- select Python legacy versus Python fixed runtime only;
- never select Rust;
- use the same ASCILINE renderer and codec;
- be defaulted to the new runtime only after I0 passes;
- have an explicit removal issue once the final soak gate passes.

### 7.3 Failure localization

When a gate fails, record:

- first failing work-item ID
- baseline and candidate commit
- scenario and seed
- first divergent tick/frame/field
- command and exit code
- compact evidence SHA-256
- whether reverting the latest narrow commit restores the prior gate

No agent should rewrite multiple motion families or shared modules in response
to one unexplained visual failure.

## 8. Evidence and Accountability Rules

Every work-item evidence record must contain:

| Field | Required |
| --- | --- |
| `work_item_id` | Yes |
| `owner_role` | Yes |
| `agent_or_worktree` | Yes |
| `baseline_commit` | Yes |
| `candidate_commit` | Yes when committed |
| `allowed_paths` | Yes |
| `changed_paths` | Yes |
| `dependency_statuses` | Yes |
| `commands` | Yes |
| `exit_codes` | Yes |
| `test_counts` | Yes |
| `thresholds` | Yes for quality gates |
| `measurements` | Yes for quality gates |
| `artifact_paths` | Yes |
| `artifact_sha256` | Yes |
| `reviewer` | Yes |
| `rollback_point` | Yes |
| `residual_risks` | Yes |
| `result` | `pass`, `fail`, or `blocked` |

Evidence storage rules:

- Commit compact JSON/Markdown summaries only.
- Store long frame traces, browser videos, and soak logs as external artifacts
  with path/URI, byte size, and SHA-256 in the compact summary.
- Never overwrite a failing artifact with a later passing run.
- Do not stage generated directories or use `git add .`.
- Do not include Rust build/test output as Python acceptance evidence.

## 9. Cross-Role Handoff Packets

### 9.1 From first-principles software to systems

Required before `SYS-E1-002`:

- frozen `CommandEnvelope`
- semantic command enum and payload validators
- arbitration priority rules
- lease acquisition, heartbeat, expiry, and emergency-neutral rules
- pure controller tick function signature
- canonical controller state serialization

Acceptance of handoff: systems queue fixtures can validate ordering without
importing server/browser code or guessing semantic priority.

### 9.2 From animation/motion to systems

Required before `SYS-E1-004`:

- Graph v2 schema hash
- clip IDs and authored frame durations
- marker/event IDs
- contact IDs
- transition IDs and interrupt policy
- wing phase semantics
- flight height and shadow ownership semantics
- one scripted scenario per promoted family

Acceptance of handoff: replay captures all semantic fields without evaluating
artistic rules itself.

### 9.3 From systems to integration lead

Required before `SYS-I0-001`:

- reviewed additive modules
- focused passing test commands
- exact constructor/method signatures
- line-specific shared-file wiring guide
- legacy Python rollback switch definition
- telemetry and evidence schemas
- no Rust dependency or command

Acceptance of handoff: integration lead can wire the modules without copying
logic into shared files.

### 9.4 From integration lead/browser owner to systems

Required before `SYS-QA-002` and `SYS-QA-003`:

- source-frame receipt timestamp
- decode completion timestamp
- presentation timestamp or nearest reliable browser proxy
- epoch/frame sequence visibility
- source and decoded hashes
- disconnect/resync reason codes

Acceptance of handoff: p95 end-to-end latency and frame parity are measurable,
not estimated from server logs alone.

## 10. Required Command Set

No Cargo command belongs in this program. The exact Python commands may be
wrapped by CI, but their behavior and evidence must remain visible.

```bash
# Focused systems tests
python3 -m unittest tests.wizard.test_runtime_clock
python3 -m unittest tests.wizard.test_runtime_queue
python3 -m unittest tests.wizard.test_runtime_snapshots
python3 -m unittest tests.wizard.test_deterministic_replay
python3 -m unittest tests.wizard.test_runtime_quality
python3 -m unittest tests.wizard.test_python_runtime_scope
python3 -m unittest tests.wizard.test_multiclient_runtime

# Full Python regression
python3 -m unittest discover tests

# Existing deterministic and visual quality gates
python3 tools/generate_reference_avatar_pose_cells.py --check-deterministic
python3 tools/verify_animation_quality.py --strict

# Python-only scope gate
python3 tools/verify_python_runtime_scope.py \
  --root . \
  --json evidence/cartoon-animation-program/system/rust-exclusion.json

# Deterministic replay
python3 tools/replay_wizard_animation.py \
  --scenario tests/fixtures/cartoon/full-motion-scenario.json \
  --render-fps 24 \
  --output evidence/cartoon-animation-program/system/replay-a.ndjson

# Soak
python3 tools/run_python_animation_soak.py \
  --duration-seconds 600 \
  --render-fps 24 \
  --output evidence/cartoon-animation-program/system/soak-summary.json

# Live Python smoke
python3 tools/run_wizard_avatar_server.py --port 8765
curl -fsS http://127.0.0.1:8765/
```

If existing tool names or unittest module paths differ at baseline, the
coordinator must record the path mapping once. Agents must not create duplicate
tools merely to preserve a speculative name from this planning document.

## 11. Final Systems Acceptance Checklist

The systems/containment contribution is complete only when every statement below
is supported by committed compact evidence or a hashed external artifact:

- [ ] The accepted contracts explicitly require the current rainbow-winged,
  flying design and contain no active no-wings acceptance rule.
- [ ] Python on port `8765` is the only production runtime.
- [ ] No production dependency, command, CI gate, browser path, or acceptance
  artifact requires Rust.
- [ ] The simulation advances at an integer-indexed 60 Hz independent of render
  cadence.
- [ ] Catch-up is bounded and excess time is observable.
- [ ] Commands are versioned, ordered, idempotent, acknowledged, and applied at
  explicit ticks.
- [ ] Rendering reads immutable previous/current snapshots and never advances
  simulation.
- [ ] Replays are canonical, hashable, and deterministic across 15/24/30 fps
  presentation.
- [ ] Wing phase, flight height, contacts, clips, transitions, and one-shot
  events participate in deterministic evidence.
- [ ] Client queues are bounded and sequence gaps trigger explicit resync or
  disconnect.
- [ ] Source and decoded frame hashes match after resync.
- [ ] p95 semantic response is at most 100 ms and p95 presented response is at
  most 180 ms.
- [ ] The 10-minute mixed-motion soak has no crash, deadlock, silent command
  loss, invalid delta, or unbounded growth.
- [ ] A clean clone runs tests and the live demo with Python dependencies only.
- [ ] Rust `future_pose_transitions` results are absent from Python acceptance.
- [ ] The Rust removal decision is recorded only after the accepted Python
  release, with any cleanup assigned as a separate reversible task.

## 12. Explicit Non-Goals

This workstream will not:

- repair, port, test, optimize, or extend the Rust crate;
- pursue Python/Rust behavioral parity;
- introduce PyO3, FFI, WASM, a Rust sidecar, or a native Rust codec;
- run a Rust server on port `8787`;
- treat direct 39-pose cycling as proof of continuous animation quality;
- replace the ASCILINE square-cell renderer with video, generated sprites, or a
  second rendering stack;
- remove the accepted rainbow wings;
- let client-side simulation become authoritative;
- write shared hot files without the integration lead's recorded lock;
- stage unrelated dirty-tree content or generated evidence in bulk.

The intended result is one understandable Python system: deterministic enough
to test, responsive enough to control live, expressive enough to support the
animation plan, and isolated from the Rust detour without losing the few sound
runtime concepts worth retaining.
