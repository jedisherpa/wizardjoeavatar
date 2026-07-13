# Planning Wave 2: Python ASCILINE Multi-Agent Delivery Workflow

- Role: `PLAN`, integrated delivery and multi-agent workflow
- Program: `wizardjoe-cartoon-animation-2026-07-12`
- Repository: `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar`
- Production runtime: ASCILINE Python on `http://127.0.0.1:8765/`
- Baseline branch: `codex/build-repeatable-avatar-animation`
- Baseline commit before checkpointing: `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1` plus the audited dirty tree
- Baseline pose library: 39 poses, SHA-256 `1200e2891902cd1f3147d2c2d298dd2d99313708fbc8e90034376500e1843037`

## 1. Binding decisions

This planning contribution reconciles all four Research Wave 1 reports. The following decisions are binding for the integrated implementation plan.

1. **Python is the only production architecture.** Production code, dependencies, tests, CI, evidence, browser assets, and acceptance commands must use `wizard_avatar/`, `web/avatar/`, Python tools/tests, and the existing ASCILINE protocol on port 8765.
2. **Rust is excluded.** No implementation item may modify, import, execute, package, serve, test, or depend on `rust/`, Cargo, ports 8787/8788, Rust-generated assets, or Rust evidence. Historical Rust files remain untouched during implementation and cannot satisfy a gate.
3. **The winged design is authoritative.** Rainbow wings and flying are required. The stale `no wings` language in `docs/30-visual-tests.md` and `docs/37-completion-gate.md` must be corrected at checkpoint item `CAP-000` before implementation begins. Tests must verify the expected wing count for winged poses rather than reject wings globally.
4. **The 39-pose library is the starting asset set, not the animation system.** Every pose must be assigned to a production clip, authored transition, or explicit `showcase_only` classification. Production locomotion may not use the raw pose override.
5. **One Python runtime owns state.** `WizardFrameHub` remains the sole live authority. The new runtime performs integer 60 Hz simulation ticks, queued command application, animation evaluation, rendering, encoding, and fanout without a second renderer or client simulation.
6. **Rendering does not advance simulation.** Rendering consumes immutable snapshots. A monotonic accumulator owned by the hub runs exact `1/60` steps with bounded catch-up.
7. **Remote controls express intent, not pose IDs or browser transforms.** Keyboard, gamepad, API, and external remote controls reduce to the same sequenced, leased semantic command envelope.
8. **Crisp coherent poses take priority over arbitrary interpolation.** The hashed full-body dissolve is diagnostic-only in graph v2. Production edges use authored samples, coherent cuts, marker-timed handoffs, bounded integer offsets, and reviewed region overlays.
9. **Python 3.9 remains the minimum for this program.** Do not use `StrEnum`, `asyncio.TaskGroup`, or other 3.11-only features unless a separate version-floor decision is approved, documented, and reflected in the dependency lock and CI matrix.
10. **The current renderer, ASCILINE codec, per-subscriber resync, and offscreen atomic Canvas presentation are retained.** Work extends this spine rather than replacing it.

## 2. Program invariants

Every work item and integration gate must preserve these invariants.

```text
INV-01  Exactly one production listener: Python on 127.0.0.1:8765.
INV-02  Exactly one semantic state authority: the Python hub-owned runtime.
INV-03  Exactly one production motion graph: graph schema v2 after promotion.
INV-04  Direct ASCILINE cell frames; no video, moving PNG, sprite-sheet player, or client world simulation.
INV-05  Fixed 60 Hz integer simulation ticks; 24 FPS standard rendering.
INV-06  All visible geometry remains integer cell aligned and unblurred.
INV-07  The current 39 pose IDs remain present unless an explicit asset migration is approved.
INV-08  Wings and flying are supported and tested; no stale no-wings gate remains.
INV-09  HTTP and WebSocket commands enter one parser, queue, arbitration policy, and reducer.
INV-10  Rust is absent from production paths, dependency metadata, CI jobs, and release evidence.
INV-11  No agent stages or commits another agent's unreviewed files.
INV-12  Only the coordinator/integration lead controls the shared Git index and port 8765 process.
```

## 3. Frozen interface package

`CAP-100` creates these interfaces before parallel implementation. Field names and meanings are frozen at gate `C0`. A later change requires a decision record, lock `LOCK-CONTRACT`, and acknowledgment from every affected owner.

### 3.1 `CommandEnvelopeV1`

```python
@dataclass(frozen=True)
class CommandEnvelopeV1:
    schema_version: int             # exactly 1
    command_id: str                 # stable client-generated token
    source_id: str                  # stable for one controller session
    source_kind: str                # keyboard|gamepad|remote|demo|api
    sequence: int                   # strictly increasing per source_id
    kind: str                       # control_intent|action|path|stop|reset|...
    issued_at_ms: float             # client diagnostic timestamp only
    ttl_ms: Optional[int]           # required for control_intent
    payload: Mapping[str, object]
```

Server-assigned queue metadata:

```python
@dataclass(frozen=True)
class QueuedCommand:
    envelope: CommandEnvelopeV1
    received_order: int
    accepted_tick: int
    apply_tick: int
    priority: int
```

Rules:

- `command_id` is deduplicated for the runtime epoch.
- `sequence` must be greater than the last accepted sequence for `source_id`.
- `apply_tick` defaults to the next tick and is never earlier than `accepted_tick`.
- Continuous intents require `ttl_ms` in `[50, 1000]`; default client heartbeat is 100 ms and required lease timeout is 250 ms.
- `issued_at_ms` is not trusted as the simulation clock.
- Emergency stop/reset priority is 100; interrupting one-shot action 80; direct-control lease 60; path/demo 40; autonomous idle 20.

### 3.2 `ControlIntentV1`

```python
@dataclass(frozen=True)
class ControlIntentV1:
    move_x: float                   # normalized [-1.0, 1.0]
    move_z: float                   # normalized [-1.0, 1.0]
    ascend: float                   # normalized [-1.0, 1.0]
    face_x: Optional[float]         # optional facing vector
    face_z: Optional[float]
    speed_mode: str                 # walk|run
    mobility_request: str           # keep|takeoff|land
    held_actions: tuple[str, ...]   # semantic actions only
```

Rules:

- Planar magnitude above 1 is normalized by Python.
- Digital keyboard and analog gamepad inputs share this shape.
- Zero intent is sent immediately on key release, blur, hidden tab, gamepad disconnect, explicit release, or WebSocket close.
- Browser code never changes world position, altitude, pose, phase, or animation state.

### 3.3 `CommandAckV1`

```python
@dataclass(frozen=True)
class CommandAckV1:
    schema_version: int
    command_id: str
    source_id: str
    sequence: int
    disposition: str               # accepted|applied|rejected|duplicate|expired|unauthorized
    accepted_tick: Optional[int]
    apply_tick: Optional[int]
    state_revision: int
    runtime_epoch: str
    error_code: Optional[str]
    message: str
```

Every command receives one terminal acknowledgment. Rejected commands make no partial state mutation.

### 3.4 Runtime and controller state

```python
@dataclass
class RuntimeClock:
    simulation_tick: int
    accumulator_seconds: float
    dropped_simulation_seconds: float
    max_catch_up_ticks: int         # initial value 8
    state_revision: int

@dataclass
class ControllerLease:
    source_id: Optional[str]
    source_kind: Optional[str]
    generation: int
    priority: int
    last_sequence: int
    expires_tick: int
    intent: ControlIntentV1

@dataclass(frozen=True)
class RuntimeSnapshot:
    previous: SemanticAvatarState
    current: SemanticAvatarState
    presentation: PresentationState
```

All action, speech, lease, marker, and transition deadlines are integer ticks. `time_seconds` remains derived compatibility output only.

### 3.5 Orthogonal semantic state

```text
MobilityState
  mode: grounded_idle|grounded_start|grounded_walk|grounded_run|
        grounded_stop|turn|crouch|kneel|takeoff|hover|flight_travel|
        flight_bank|fall|landing|disabled
  world_x, world_z
  velocity_x, velocity_z
  altitude, vertical_velocity, target_altitude
  grounded
  support_contact: none|left_foot|right_foot|both_feet|staff
  gait_phase, flap_phase

ChannelState (one each for upper_body, face, speech, staff, wings, effects)
  state_id
  owner_source
  generation
  entry_tick
  deadline_tick
  priority
  interrupt_policy
  restore_policy: discard|resume_if_valid|restart|return_to_neutral
```

`contact_root` remains the projected ground/shadow owner. `visual_root_offset` is a bounded integer correction. `altitude` moves the rendered body above the contact root and never moves the shadow with wing motion.

### 3.6 `PresentationState`

```python
@dataclass(frozen=True)
class PresentationState:
    graph_version: int
    node_id: str
    clip_id: str
    clip_generation: int
    clip_phase: float
    sample_index: int
    pose_id: str
    previous_pose_id: str
    transition_id: Optional[str]
    transition_generation: int
    transition_start_tick: int
    transition_duration_ticks: int
    transition_progress: float
    active_markers: tuple[str, ...]
    support_contact: str
    planted_anchor: Optional[str]
    visual_root_offset_x: int
    visual_root_offset_y: int
    effect_events: tuple[str, ...]
```

The renderer receives this immutable object. It does not infer state transitions from a changed pose ID.

### 3.7 Animation graph v2

Required top-level JSON fields:

```text
$schema
$id
schema_version = 2
asset_set_id
default_node_id
capability_tiers
pose_classification
clips
nodes
transitions
transition_recipes
channel_masks
fallbacks
```

Each clip declares:

```text
clip_id, family, supported_facings, loop_mode, phase_source,
root_policy, minimum_hold_ticks, interrupt_policy, channel_ownership,
samples[{pose_id, duration_frames, normalized_distance?, markers[]}],
entry_markers, exit_markers, secondary_curves
```

Each transition declares:

```text
transition_id, source_pattern, target_pattern, priority,
duration_ticks, timing_mode, transition_recipe_id,
phase_policy, root_policy, contact_policy, region_policy,
interrupt_window, fallback_transition_id
```

Each of the 39 pose IDs must be listed in `pose_classification` as one or more of:

```text
clip_sample | transition_sample | diagnostic_only
```

No pose may be silently unreachable.

### 3.8 Evidence record

Every deterministic evidence row includes:

```text
schema_version, commit_sha, runtime_epoch, asset_hash, graph_hash,
seed, command_log_hash, simulation_tick, state_revision,
command_sequence_watermark, mobility_mode, clip_id, clip_phase,
transition_id, transition_progress, support_contact, active_markers,
world_position, altitude, root_screen, visual_root_offset,
pose_id, source_frame_sha256, encoded_tag, decoded_hash,
presented_hash, subscriber_count, queue_depth, resync_count
```

## 4. Roles, branches, worktrees, and write ownership

All implementation branches start from the **pushed planning checkpoint SHA**, not from the original dirty checkout. Worktree paths shown below are recommendations; the coordinator may choose equivalent absolute paths but must record them.

| Role | Branch | Worktree | Primary responsibility |
|---|---|---|---|
| FPSE | `codex/cartoon-fpse-runtime` | `/Users/paul/Documents/WizardJoeAsci/worktrees/cartoon-fpse-runtime` | contracts, fixed runtime, commands, arbitration, motion physics |
| ANIM | `codex/cartoon-animation-graph` | `/Users/paul/Documents/WizardJoeAsci/worktrees/cartoon-animation-graph` | clips, graph, contacts, transition recipes, visual channels |
| SYS | `codex/cartoon-python-systems` | `/Users/paul/Documents/WizardJoeAsci/worktrees/cartoon-python-systems` | Python stream/server/protocol, browser transport, metrics, soak |
| PLAN | `codex/cartoon-program-gates` | `/Users/paul/Documents/WizardJoeAsci/worktrees/cartoon-program-gates` | workflow validator, CI, evidence manifests, scope/release gates |
| INT | `codex/cartoon-python-integration` | coordinator-controlled | serial shared-file integration and live port-8765 acceptance |

`SYS` is the prior Rust-expert perspective translated into Python systems work. It owns no Rust implementation.

### 4.1 Path allowlists

#### FPSE allowlist

```text
wizard_avatar/commands.py
wizard_avatar/runtime.py
wizard_avatar/animation_state.py
wizard_avatar/models.py
wizard_avatar/controller.py
wizard_avatar/locomotion.py
wizard_avatar/pathing.py
wizard_avatar/views.py
tests/wizard/test_command_envelopes.py
tests/wizard/test_command_ordering.py
tests/wizard/test_controller_leases.py
tests/wizard/test_fixed_runtime.py
tests/wizard/test_deterministic_replay.py
tests/wizard/test_motion_intents.py
tests/wizard/test_ground_motion.py
tests/wizard/test_flight_motion.py
```

#### ANIM allowlist

```text
wizard_avatar/animation_graph.py
wizard_avatar/motion.py
wizard_avatar/quality.py
wizard_avatar/pose_selection.py
wizard_avatar/pose_compositor.py
wizard_avatar/reference_avatar.py
wizard_avatar/definitions/reference_avatar_animation_graph.v2.json
wizard_avatar/definitions/reference_avatar_animation_graph.v2.schema.json
wizard_avatar/definitions/reference_avatar_pose_cells.schema.json
tools/verify_motion_graph.py
tools/verify_motion_visuals.py
tests/wizard/test_animation_graph_v2.py
tests/wizard/test_clip_playback.py
tests/wizard/test_contact_continuity.py
tests/wizard/test_transition_recipes.py
tests/wizard/test_animation_markers.py
tests/wizard/test_visual_channels_v2.py
```

#### SYS allowlist

```text
wizard_avatar/stream.py
wizard_avatar/protocol.py
wizard_avatar/server.py
wizard_avatar/diagnostics.py
web/avatar/wizardClient.ts
web/avatar/wizardCodec.ts
web/avatar/wizardDiagnostics.ts
web/avatar/wizardInput.ts
tests/wizard/test_command_transport.py
tests/wizard/test_stream_epoch.py
tests/wizard/test_stream_hub_v2.py
tests/wizard/test_remote_control_transport.py
tests/web/wizardInput.test.mjs
tests/web/wizardClient.test.mjs
tools/verify_remote_control.py
tools/run_python_avatar_soak.py
```

#### PLAN allowlist

```text
.github/workflows/cartoon-animation-python.yml
.github/CODEOWNERS
requirements-dev.txt
tools/validate_cartoon_animation_program.py
tools/build_cartoon_evidence_manifest.py
tools/verify_python_production_scope.py
tools/verify_release_clone.py
tests/wizard/test_cartoon_program_workflow.py
docs/cartoon-animation-program/**
evidence/cartoon-animation-program/**/*.md
evidence/cartoon-animation-program/**/*.json
```

#### INT allowlist

```text
wizard_avatar/frame_source.py
wizard_avatar/shadow.py
wizard_avatar/projection.py
web/avatar/wizardControls.ts
web/avatar/wizardDemo.ts
web/avatar/wizardCanvas.ts
web/avatar/style.css
README.md
docs/00-goal-and-visual-contract.md
docs/23-animation-channels.md
docs/27-semantic-control-routes.md
docs/28-browser-demo-controls.md
docs/30-visual-tests.md
docs/31-locomotion-tests.md
docs/36-evidence-package.md
docs/37-completion-gate.md
docs/INDEX.md
.gitignore
```

No path outside an agent's allowlist may be changed without a coordinator-issued handoff that updates the ledger before editing begins.

### 4.2 Conflict-hotspot locks

| Lock | Protected surface | Owner while held | Release condition |
|---|---|---|---|
| `LOCK-CONTRACT` | command/state/graph interface field meanings | FPSE, then INT after `C0` | schemas merged and all four roles acknowledge |
| `LOCK-MODELS` | `models.py`, `animation_state.py` | FPSE | focused tests and contract review pass |
| `LOCK-GRAPH` | graph v2 JSON/schema and evaluator | ANIM | graph validator passes and graph hash recorded |
| `LOCK-FRAME` | `frame_source.py`, shadow/projection wiring | INT only | each family integration gate passes |
| `LOCK-SERVER` | `server.py`, public routes, WS bootstrap | SYS | HTTP/WS parity tests pass |
| `LOCK-WEB-CONTROL` | input/control/browser wiring | SYS for adapter, INT for final control surface | browser tests and live smoke pass |
| `LOCK-TRACKER` | shared tracker/registry | coordinator only | status update committed |
| `LOCK-GIT-INDEX` | staging, commits, pushes on integration branch | coordinator only | remote SHA verified |
| `LOCK-PORT-8765` | live acceptance server | coordinator only | test server stopped or deliberately left live |

Lock rules:

1. Exactly one active owner.
2. Claim and release are recorded in the coordinator ledger.
3. A lock cannot be held across an idle handoff without an explicit reason and expiry.
4. Worktree agents run in-process tests or ephemeral ports. They do not stop, restart, or bind port 8765.
5. INT never edits an owner's branch directly; it merges/cherry-picks reviewed commits, then performs wiring in its own branch.

## 5. Work-item DAG

Status transitions:

```text
QUEUED -> CLAIMED -> IN_PROGRESS -> REVIEW_READY -> GATE_RUNNING -> VERIFIED -> MERGED
                               \-> BLOCKED
                               \-> REJECTED
```

### 5.1 Ledger

| ID | Owner | Dependencies | Purpose | Integration gate |
|---|---|---|---|---|
| `CAP-000` | INT | none | Resolve wings contract in favor of winged/flying design | `B0-A` |
| `CAP-001` | PLAN + INT | `CAP-000` | Inventory exact Python baseline and generate staging manifest | `B0-B` |
| `CAP-002` | PLAN + INT | `CAP-001` | Ignore/quarantine Rust and raw evidence; staged-size audit | `B0-C` |
| `CAP-003` | INT | `CAP-002` | Commit and push reproducible Python 39-pose baseline | `B0` |
| `CAP-010` | INT | `CAP-003` | Synthesize four plans into implementation plan/workflow | `P0-A` |
| `CAP-011` | INT | `CAP-010` | Commit/push planning checkpoint and record remote SHA | `P0` |
| `CAP-100` | FPSE | `CAP-011` | Frozen Python command/runtime/state interfaces | `C0-A` |
| `CAP-110` | ANIM | `CAP-100` | Metadata-complete pose loader and pose census | `C0-B` |
| `CAP-120` | ANIM | `CAP-100`, `CAP-110` | Graph v2 schema, validator, 39-pose classification | `C0-C` |
| `CAP-130` | PLAN | `CAP-100`, `CAP-120` | Workflow validator and ownership/Rust-exclusion checks | `C0-D` |
| `CAP-140` | INT | `CAP-100..130` | Contract freeze merge and role acknowledgment | `C0` |
| `CAP-200` | FPSE | `CAP-140` | Integer 60 Hz runtime and immutable snapshots | `R1-A` |
| `CAP-210` | FPSE | `CAP-200` | Ordered command queue, acks, replay, tick deadlines | `R1-B` |
| `CAP-220` | FPSE | `CAP-210` | Controller lease, arbitration, direct intent | `R1-C` |
| `CAP-230` | FPSE | `CAP-200`, `CAP-220` | Ground/run/flight semantic physics | `R1-D` |
| `CAP-300` | ANIM | `CAP-140` | Graph evaluator, clips, markers, events | `A1-A` |
| `CAP-310` | ANIM | `CAP-300` | Authored clip inventory and legal transition topology | `A1-B` |
| `CAP-320` | ANIM | `CAP-300`, `CAP-310` | Coherent transition recipes and interruption snapshots | `A1-C` |
| `CAP-330` | ANIM | `CAP-320` | Blink/expression/speech/secondary visual channels | `A1-D` |
| `CAP-400` | SYS | `CAP-140`, `CAP-210` | Versioned HTTP/WS adapters, bootstrap, ack transport | `S1-A` |
| `CAP-410` | SYS | `CAP-400` | Hub cadence, bounded catch-up, epoch, metrics, resync | `S1-B` |
| `CAP-420` | SYS | `CAP-220`, `CAP-400` | Browser input adapter, release/heartbeat/gamepad lifecycle | `S1-C` |
| `CAP-430` | SYS | `CAP-410`, `CAP-420` | Multi-viewer and slow-subscriber soak harness | `S1-D` |
| `CAP-500` | PLAN | `CAP-140` | Python-only CI, artifact policy, required-check definitions | `Q0-A` |
| `CAP-510` | PLAN | `CAP-120` | Evidence schema/manifest and gate-report tools | `Q0-B` |
| `CAP-520` | PLAN | `CAP-500`, `CAP-510` | Release-scope and clean-clone validators | `Q0` |
| `CAP-600` | INT | `CAP-200`, `CAP-210`, `CAP-300`, `CAP-400` | Wire runtime/graph/transport without behavior promotion | `I0` |
| `CAP-610` | INT | `CAP-230`, `CAP-310`, `CAP-320`, `CAP-600` | Promote idle/start/walk/turn/stop/run family | `M1` |
| `CAP-620` | INT | `CAP-230`, `CAP-310`, `CAP-320`, `CAP-610` | Promote takeoff/hover/flap/glide/bank/land family | `M2` |
| `CAP-630` | INT | `CAP-310`, `CAP-320`, `CAP-330`, `CAP-620` | Promote action/reaction/speech/expression families | `M3` |
| `CAP-640` | INT | `CAP-420`, `CAP-630` | Promote remote controls and final browser controls | `M4` |
| `CAP-700` | PLAN + independent reviewers | `CAP-640`, `CAP-520` | Deterministic replay and full Python verification | `V1` |
| `CAP-710` | INT + ANIM reviewer | `CAP-700` | Live real-browser motion/visual acceptance on 8765 | `V2` |
| `CAP-720` | SYS + FPSE reviewer | `CAP-710` | 10-minute mixed control/multiclient soak | `V3` |
| `CAP-800` | PLAN + INT | `CAP-720` | Compact evidence manifest and release report | `F0-A` |
| `CAP-810` | INT | `CAP-800` | Clean-clone release verification, push, live restart | `F0` |
| `CAP-900` | coordinator, separate cleanup | `CAP-810` | Optional historical Rust removal in a later reversible commit | not release-blocking |

### 5.2 Parallel execution windows

```text
Window W0 (serial coordinator)
  CAP-000 -> 001 -> 002 -> 003 -> 010 -> 011

Window W1 (contract freeze)
  CAP-100 -> CAP-110 -> CAP-120
                  \-> CAP-130
  all -> CAP-140

Window W2 (parallel after C0)
  FPSE: CAP-200 -> 210 -> 220 -> 230
  ANIM: CAP-300 -> 310 -> 320 -> 330
  SYS:  CAP-400 -> 410; CAP-420 waits for 220; then CAP-430
  PLAN: CAP-500; CAP-510 -> 520

Window W3 (serial integration)
  CAP-600 -> 610 -> 620 -> 630 -> 640

Window W4 (serial verification/release)
  CAP-700 -> 710 -> 720 -> 800 -> 810
```

No item in W2 may merge directly to the baseline branch. INT integrates only after item handoff and gate evidence.

## 6. Work-package specifications

### `CAP-000`: winged/flying contract correction

- Owner: INT under `LOCK-CONTRACT` and `LOCK-TRACKER`.
- Required edits: `README.md`, `docs/00-goal-and-visual-contract.md`, `docs/30-visual-tests.md`, `docs/37-completion-gate.md`, and index references if needed.
- Required decision text: wings are required for the current accepted WizardJoe; flying is a production mobility family; no-wings assertions are superseded.
- Test change requirement: legacy visual tests must validate expected wings by pose/tag, not globally reject wing pixels.
- Gate: `rg -n "no wings|has no wings|without wings" README.md docs/00-goal-and-visual-contract.md docs/30-visual-tests.md docs/37-completion-gate.md` returns no active contradictory requirement. Historical context must be labeled historical.
- Rollback: revert only the contract commit. Implementation cannot start until a replacement decision exists.
- Evidence: `evidence/cartoon-animation-program/checkpoints/CAP-000-contract.json` with changed paths and approved wording hash.

### `CAP-001..003`: reproducible baseline checkpoint

- Record branch, `HEAD`, Python version, `uv.lock` hash, manifest hash, generated-library hash, tracked modifications, untracked files, file sizes, listener PID/command, and current verification results.
- Generate `docs/cartoon-animation-program/checkpoints/python-baseline-paths.txt` as a newline-delimited allowlist.
- Generate `docs/cartoon-animation-program/checkpoints/python-baseline-exclusions.txt`.
- Baseline commit message: `checkpoint: capture Python 39-pose ASCILINE baseline`.
- Push baseline commit before planning checkpoint.
- Gate result must include the remote branch SHA from `git ls-remote`.

Baseline include allowlist:

```text
README.md
docs/00-goal-and-visual-contract.md
docs/27-semantic-control-routes.md
docs/30-visual-tests.md
docs/37-completion-gate.md
docs/INDEX.md
docs/pose-library-expansion/**
assets/reference/motion_sources/**
wizard_avatar/**/*.py
wizard_avatar/definitions/reference_avatar_animation_graph.json
wizard_avatar/definitions/reference_avatar_animation_graph.schema.json
wizard_avatar/definitions/reference_avatar_pose_cells.json
wizard_avatar/definitions/reference_avatar_pose_cells.schema.json
web/avatar/**
tests/wizard/**
tools/*.py
uv.lock
evidence/pose-library-expansion/POSE_EXPANSION_COMPLETION.md
evidence/pose-library-expansion/DEMO_PLAY_VERIFICATION.md
evidence/pose-library-expansion/demo-all-39-poses-moving.png
.gitignore
```

Baseline mandatory exclusions:

```text
rust/**
evidence/wizard/rust-*/**
evidence/animation-quality/**/tmp/**
evidence/animation-quality/**/*.rgb
evidence/animation-quality/**/*.mp4
evidence/animation-quality/**/*.ndjson
evidence/pose-library-expansion/intake/**
evidence/pose-library-expansion/*/source-preview.png
**/target/**
**/__pycache__/**
*.log
```

Large-file gate:

- no staged file above 25 MiB without an explicit asset exception
- no staged file above GitHub's 100 MiB hard limit
- generated 16 MiB pose JSON is an approved deterministic exception below 25 MiB
- source pose PNGs are approved inputs; duplicates/previews are not

Exact pre-commit audit:

```bash
git add --dry-run --pathspec-from-file=docs/cartoon-animation-program/checkpoints/python-baseline-paths.txt
git add --pathspec-from-file=docs/cartoon-animation-program/checkpoints/python-baseline-paths.txt
git diff --cached --check
git diff --cached --name-only
git diff --cached --stat
git diff --cached --name-only -z | xargs -0 stat -f '%z %N' | sort -nr | head -50
git grep -nE 'rust/wizard_avatar_engine|cargo (run|test|build)|127\.0\.0\.1:878[78]' --cached -- wizard_avatar web/avatar tools .github
```

The final grep must produce no production matches. Do not use `git add .`, `git add -A`, or force-add ignored files.

Baseline verification:

```bash
python3 -m unittest discover tests
python3 tools/generate_reference_avatar_pose_cells.py --check-deterministic
python3 tools/verify_animation_quality.py --strict
python3 tools/validate_pose_expansion_workflow.py
git diff --check
```

Expected floor: 62 Python tests, 39 deterministic poses with the approved hash, 32/32 strict scenarios, 30 workflow candidates with zero errors.

### `CAP-010..011`: planning checkpoint

Planning commit allowlist:

```text
docs/cartoon-animation-program/README.md
docs/cartoon-animation-program/PROGRAM_TRACKER.md
docs/cartoon-animation-program/registry.json
docs/cartoon-animation-program/research/*.md
docs/cartoon-animation-program/planning/*.md
docs/cartoon-animation-program/IMPLEMENTATION_PLAN.md
docs/cartoon-animation-program/WORKFLOW.md
docs/cartoon-animation-program/checkpoints/*.txt
docs/INDEX.md
```

Planning commit message: `docs: define Python cartoon animation implementation program`.

Before push:

```bash
python3 tools/validate_cartoon_animation_program.py --phase planning --strict
git diff --cached --check
git diff --cached --name-only
git grep -nE 'cargo (run|test|build)|rust/wizard_avatar_engine.*(required|production|gate)' --cached -- docs/cartoon-animation-program .github
```

After push:

```bash
git push origin codex/build-repeatable-avatar-animation
git rev-parse HEAD
git ls-remote --heads origin codex/build-repeatable-avatar-animation
```

No W1/W2 worktree is created until local and remote planning SHAs match and the registry records `planning_checkpoint.pushed=true`.

### `CAP-100..140`: contract freeze

Deliverables:

- Python dataclasses and strict boundary models for all interfaces in Section 3.
- JSON Schemas for command envelope, acknowledgment, public state, graph v2, and evidence rows.
- Pose loader retains facing, locomotion, actions, phase, tags, and anchor confidence.
- Graph census classifies all 39 poses and reports directional capability tiers.
- Workflow validator enforces dependencies, locks, allowlists, Python-only production, and tracker/registry agreement.

Focused commands:

```bash
python3 -m unittest tests.wizard.test_command_envelopes
python3 -m unittest tests.wizard.test_reference_avatar_pose_library
python3 -m unittest tests.wizard.test_animation_graph_v2
python3 -m unittest tests.wizard.test_cartoon_program_workflow
python3 tools/verify_motion_graph.py --graph wizard_avatar/definitions/reference_avatar_animation_graph.v2.json --strict
python3 tools/validate_cartoon_animation_program.py --phase contracts --strict
```

Gate `C0`:

- every field is documented and schema validated
- all 39 poses classified
- unsupported direction claims rejected
- all graph nodes have a path to a stable idle/hover fallback
- zero overlapping active path ownership
- zero Rust production dependencies
- all four role agents return `CONTRACT_ACK=<schema hash>` in handoff

Rollback: contracts are additive and graph v1 remains active. Revert `C0` commits without changing current behavior.

### `CAP-200..230`: deterministic runtime and semantic motion

Required behaviors:

- `step_tick()` is the only simulation mutation step and always uses exactly `1/60`.
- accumulator uses event-loop monotonic time and executes at most eight catch-up ticks per turn.
- excess backlog increments `dropped_simulation_seconds`.
- commands apply at tick boundaries in `(apply_tick, priority, received_order)` order.
- all timers become integer deadlines.
- replay records initial state, seed, ordered commands, and per-tick hashes.
- lease expiration produces zero intent within 250 ms plus one tick.
- ground, run, altitude, takeoff, flight, bank, descent, and landing state remain semantic and cell-free.

Focused commands:

```bash
python3 -m unittest tests.wizard.test_fixed_runtime
python3 -m unittest tests.wizard.test_command_ordering
python3 -m unittest tests.wizard.test_deterministic_replay
python3 -m unittest tests.wizard.test_controller_leases
python3 -m unittest tests.wizard.test_motion_intents
python3 -m unittest tests.wizard.test_ground_motion
python3 -m unittest tests.wizard.test_flight_motion
```

Gate `R1`:

- no fractional simulation step in 10,000 ticks
- 15/24/30 FPS schedules have identical semantic hashes at matching ticks
- two 1,000-command replays are byte-identical
- synthetic two-second stall executes at most eight catch-up ticks per event-loop turn
- duplicate/out-of-order/expired commands never mutate state
- all priority permutations resolve identically
- lease release cases pass for keyup, blur, hidden, disconnect, close, and heartbeat expiry

Rollback: graph v1 remains active; runtime compatibility adapter can be reverted to the baseline hub SHA. Preserve replay evidence before revert.

### `CAP-300..330`: graph, clips, transitions, and channels

Initial required clips:

```text
idle_front
walk_front
run_charge_front
run_land_front
turn_views
takeoff_front
hover_front
glide_southeast
bank_left
bank_right
air_reaction
land_front
cast_front
guard_front
block_front
flourish_front
victory_cast_front
explain_front
point_front
shush_front
celebrate_front
hit_fall_recover_front
```

Capability tiers:

- Tier A: authored front/southeast grounded, flight, and action clips.
- Tier B: coherent adjacent/fallback views with honest reduced motion.
- Tier C: diagnostic/showcase-only poses or unsupported direction/action combinations.
- No whole-frame mirroring without staff/hand/wing ownership review.

Timing floor at 24 FPS:

```text
tiny anticipation       2-3 frames
standard anticipation   4-6 frames
attack/release          1-3 frames
smear/effect accent     1-2 frames
readable hold           4-10 frames
recovery                3-8 frames
idle hold               8-24 frames
walk key                2-4 distance-driven frames
wing downstroke         2-3 frames
wing upstroke/settle    4-7 frames
```

Focused commands:

```bash
python3 tools/verify_motion_graph.py --strict
python3 -m unittest tests.wizard.test_animation_graph_v2
python3 -m unittest tests.wizard.test_clip_playback
python3 -m unittest tests.wizard.test_animation_markers
python3 -m unittest tests.wizard.test_transition_recipes
python3 -m unittest tests.wizard.test_contact_continuity
python3 -m unittest tests.wizard.test_visual_channels_v2
python3 tools/verify_motion_visuals.py --headless --strict
```

Gate `A1`:

- no production transition uses coordinate-hash full-body dissolve
- no wildcard every-pose-to-every-pose edge
- all production nodes have legal entry, interrupt, recovery, and fallback
- walk/run phase carries across compatible speed/facing changes
- flap phase carries across hover/travel/bank changes
- marker events emit exactly once per traversal
- grounded loops alternate contacts or are classified non-loop bursts
- airborne clips declare no foot contact; landing declares first and settled contact
- blink, expression, and mouth produce pixel changes on the reference-pose path without root movement
- shush owns/suppresses mouth writes during its hold

Rollback: graph v2 files and evaluator are inert until INT promotion; graph v1 remains the active configuration.

### `CAP-400..430`: Python transport, browser input, and systems verification

Required behaviors:

- HTTP and WebSocket use one strict command parser and queue.
- WS bootstrap includes protocol version, runtime epoch, simulation tick, state revision, frame sequence, graph hash, and asset hash.
- JSON command acks/events and binary ASCILINE frames remain typed and ordered.
- frame queues are bounded; resync is subscriber-local.
- browser input sends on change and 10 Hz heartbeat while nonzero.
- keydown/keyup, blur, visibility, gamepad connect/disconnect, and WS close release intent.
- browser diagnostics display controller source, lease generation/expiry, accepted sequence, simulation tick, state revision, node/clip/phase, transition, queue depths, and latency.

Focused commands:

```bash
python3 -m unittest tests.wizard.test_command_transport
python3 -m unittest tests.wizard.test_stream_epoch
python3 -m unittest tests.wizard.test_stream_hub_v2
python3 -m unittest tests.wizard.test_remote_control_transport
node --test tests/web/*.test.mjs
python3 tools/run_python_avatar_soak.py --headless --duration-seconds 30 --viewers 4 --strict
```

Gate `S1`:

- every accepted command gets exactly one terminal ack
- injected delta loss resyncs one viewer without state reset or impact on others
- one controller plus four viewers advances simulation within 1% of single-viewer timing
- deliberately slow viewer does not increase other viewers' queue depth above the configured bound
- zero sequence regression and zero source/decode mismatch
- Python 3.9 task cancellation closes/awaits receiver and hub tasks without uncaught exceptions

Rollback: retain the old routes as compatibility adapters to the same queue until final release. Revert transport commits without changing graph assets.

### `CAP-500..520`: CI, workflow validation, and evidence

Required check names:

```text
python-3.9-unit
python-production-unit
pose-determinism
motion-graph-v2
transition-quality
python-production-scope
web-unit
live-browser-8765
multiclient-soak-short
evidence-manifest
```

CI rules:

- concurrency group `${workflow}-${ref}` with superseded PR runs canceled
- `setup-python` explicitly selects 3.9 and production Python
- dependency installation uses the checked lock; no Cargo action or Rust cache
- CI grep fails on runtime Rust/Cargo/8787/8788 dependencies
- raw evidence is uploaded as artifacts, not committed
- test output uploads even on failure
- required checks cannot use `continue-on-error`
- no skipped/ignored required tests

Artifact policy:

| Artifact | PR retention | release retention | Commit compact summary? |
|---|---:|---:|---|
| unit/JUnit logs | 14 days | 90 days | totals only |
| replay logs/hashes | 30 days | 90 days | manifest and aggregate hashes |
| browser screenshots | 14 days | 90 days | one curated image if under 2 MiB |
| browser recordings | 14 days | 90 days | no |
| raw frames/RGB/NDJSON | 7 days | 30 days | no |
| soak logs | 14 days | 90 days | aggregate JSON only |
| final evidence bundle | n/a | 90 days minimum | index, checksums, artifact URLs |

Gate `Q0`:

- validator rejects overlapping ownership, unmet dependencies, stale locks, missing evidence, unrecorded SHA, and Rust production references
- all required check names exist
- artifact paths are outside staged source allowlists
- committed evidence files are under 5 MiB each unless explicitly approved

### `CAP-600..640`: serial integration and family promotion

Only INT works these items, one at a time, under `LOCK-FRAME`, `LOCK-GIT-INDEX`, and when live testing, `LOCK-PORT-8765`.

Serial merge order:

```text
1. CAP-100 contract types and schemas
2. CAP-110 pose metadata loader
3. CAP-120 graph schema/validator
4. CAP-200 fixed runtime
5. CAP-210 command queue/replay
6. CAP-400 command transport/bootstrap
7. CAP-300 graph evaluator
8. CAP-230 semantic ground/flight physics
9. CAP-310 authored clips/topology
10. CAP-320 transition recipes
11. CAP-410 hub cadence/metrics
12. CAP-420 browser input adapter
13. CAP-330 visual channels
14. CAP-500..520 gates/evidence
15. INT-only frame-source, controls, shadow, and docs wiring
```

After each numbered merge:

```bash
python3 -m unittest discover tests
python3 tools/generate_reference_avatar_pose_cells.py --check-deterministic
python3 tools/verify_motion_graph.py --strict
python3 tools/verify_animation_quality.py --strict
python3 tools/validate_cartoon_animation_program.py --phase integration --strict
git diff --check
```

Promotion flags:

```text
WIZARD_ANIMATION_GRAPH=v1|v2
WIZARD_REMOTE_CONTROL_V2=0|1
```

These flags select behavior/data on the same Python renderer and ASCILINE stream. They do not create a second runtime. Defaults stay `v1`/`0` until each promotion gate passes.

Promotion order:

1. `M1`: idle, start, walk, turn, stop, run burst/recovery.
2. `M2`: takeoff, hover/flap, travel, bank, fall, landing/recovery.
3. `M3`: cast, guard, block, flourish, explain, point, shush, celebrate, reaction, speech/expression.
4. `M4`: held remote input, gamepad, external WebSocket control, final Play performance.

An integration failure stops the queue. No later family is merged around a failed family.

## 7. Verification matrix

| Gate | Automated requirements | Visual/live requirements | Required evidence |
|---|---|---|---|
| `B0` | 62-test floor, deterministic 39-pose hash, 32/32 strict matrix, no Rust staged | current 39-pose demo still works | baseline manifest, staged paths, remote SHA |
| `P0` | planning validator, no implementation diff | none | four reports, four plans, integrated plan/workflow, remote SHA |
| `C0` | schema validation, 39/39 classification, graph reachability, ownership audit | capability-tier review | contract hashes, pose census, role ACKs |
| `R1` | fixed tick, command order, replay, lease/arbitration permutations | none | per-tick hashes, queue/latency metrics |
| `A1` | clip/marker/transition/contact tests | contact sheets for every initial clip | graph hash, clip inventory, visual metrics |
| `S1` | HTTP/WS parity, epoch/resync, browser input unit, four-viewer short soak | browser diagnostics readable | sequence/hash/queue logs |
| `I0` | full suite after each merge | one smoke frame per active graph family | merge SHA, commands, result summary |
| `M1` | walk/run phase, stride, contacts, stop timing | three front walk cycles, turn, start/stop, run recovery | recording, contact/root plot |
| `M2` | altitude, no-contact, flap phase, landing markers, shadow monotonicity | takeoff, hover, bank both ways, glide, land | recording, altitude/shadow trace |
| `M3` | action markers, interrupt windows, shush/mouth, channel ownership | each montage entry/hold/recover, speech while moving/flying | montage reel, marker/state log |
| `M4` | sequence, TTL, lease, keyup/blur/disconnect, source priority | keyboard/gamepad/external remote control session | control log, latency distribution |
| `V1` | two deterministic full replays, all tests, all strict tools | none | replay parity and complete totals |
| `V2` | source/decoded/presented hash parity | real Chromium on live 8765, zero console errors | screenshots, recordings, browser metrics |
| `V3` | 10-minute mixed soak, four viewers, slow client | continuous watch sample | soak aggregate and raw artifact |
| `F0` | clean clone, locked install, all required CI checks, scope audit | final live demo at pushed SHA | final report, artifact index, live PID/listener proof |

### 7.1 Visual thresholds

```text
fixed-world root jump              <= 1 stage cell per adjacent frame; 0 after settle
planted foot drift                 <= 1 local cell during stance
stable staff-hand/tip drift        <= 1 local cell except authored attack/smear
stable eye/mouth anchor drift      <= 1 local cell between compatible frames
world distance per walk cycle      within +/-5% of configured stride
walk stop after speed threshold    <= 250 ms
action extreme hold                >= 2 rendered frames
magic covering eyes/mouth          <= 2 consecutive frames unless explicitly authored
occupied stable palette compliance >= 95% expected reviewed role colors
```

Hard visual failures:

- two heads or two faces
- more than one disconnected staff
- detached eyes/mouth/hand/staff tip
- mixed full-body dissolve outside declared region masks
- foot contact claimed while airborne
- shadow following body/wing motion instead of ground contact root
- antialiasing, color interpolation, or non-integer cell placement
- stage clipping or per-frame whole-character rescaling
- missing required wings or unexplained extra wing regions

### 7.2 Runtime/control thresholds

```text
simulation step                    exactly 1/60 second
standard render rate               24 FPS
max catch-up ticks/turn            8
lease TTL                          250 ms default
input heartbeat                    100 ms while nonzero
accepted intent to semantic p95    <= 100 ms; target <= 2 simulation ticks
accepted intent to visible p95     <= 180 ms; target <= 2 frames on loopback
viewer-count simulation variance   <= 1% across 1, 2, and 4 viewers
decode errors                      0
source/decode hash mismatches      0
unhandled browser console errors   0
unexplained resyncs                0
unbounded queue growth             0
```

## 8. Live port-8765 procedure

Only INT executes this procedure under `LOCK-PORT-8765`.

1. Record any existing listener:

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN
ps -p <PID> -o pid,ppid,lstart,command
curl -fsS http://127.0.0.1:8765/api/avatar/wizard/state
```

2. Stop only the program-owned previous listener using its recorded PID. Do not kill unrelated Python processes.
3. Start the pushed candidate:

```bash
python3 tools/run_wizard_avatar_server.py --host 127.0.0.1 --port 8765 --cols 240 --rows 135 --fps 24
```

4. Verify listener and bootstrap:

```bash
curl -fsS http://127.0.0.1:8765/api/avatar/wizard/state
curl -fsS http://127.0.0.1:8765/avatar/reference-avatar-pose-cells.json
python3 tools/verify_remote_control.py --url http://127.0.0.1:8765 --strict
python3 tools/verify_live_cartoon_browser.py --url http://127.0.0.1:8765 --browser chromium --strict
```

5. Evidence records the actual listener PID, command, Git SHA, graph hash, asset hash, runtime epoch, and browser version.
6. On failure, preserve artifacts before rollback. On success, leave the requested test server live and record its PID in the final report.

## 9. Failure, blocking, and rollback procedure

### 9.1 Item failure

An item becomes `BLOCKED` when its required gate fails. The owner must provide:

```text
item_id
failed command
exit code
first actionable failure
full log artifact
current commit SHA
files changed
whether shared contract is implicated
recommended next action
rollback commit or feature flag
```

No downstream dependency may start or merge while the item is blocked.

### 9.2 Integration failure

1. Stop integration queue.
2. Record failing merge SHA and pre-merge SHA.
3. Preserve test, replay, browser, and visual evidence.
4. If unpushed, reset only the integration worktree through an approved coordinator operation; never alter agent worktrees.
5. If pushed, create a normal revert commit. Do not rewrite shared history.
6. Restore graph behavior to `v1` or disable the failed family flag.
7. Restart Python 8765 from the last verified SHA.
8. Re-run `B0` smoke plus the gate immediately before the failure.
9. Update tracker/registry with failure, rollback SHA, evidence, and new dependency state.

### 9.3 Runtime emergency rollback

Preferred non-code rollback:

```text
WIZARD_ANIMATION_GRAPH=v1
WIZARD_REMOTE_CONTROL_V2=0
```

Then restart the same Python service. If the fixed runtime itself is implicated, deploy the last verified Git SHA. No Rust fallback is allowed.

### 9.4 Contract change after `C0`

1. Claim `LOCK-CONTRACT`.
2. Write a decision record with old/new schema hashes.
3. Enumerate affected items and branches.
4. Obtain FPSE, ANIM, SYS, PLAN, and INT acknowledgment.
5. Update validators and contract tests first.
6. Rebase affected worktrees onto the new contract checkpoint.
7. Release lock only after all affected focused suites pass.

## 10. Evidence package and retention

Committed compact structure:

```text
evidence/cartoon-animation-program/
  checkpoints/
    python-baseline.json
    planning-checkpoint.json
    contract-freeze.json
  gates/
    B0.json
    P0.json
    C0.json
    R1.json
    A1.json
    S1.json
    M1.json
    M2.json
    M3.json
    M4.json
    V1.json
    V2.json
    V3.json
    F0.json
  release/
    manifest.json
    checksums.sha256
    FINAL_VERIFICATION.md
```

Heavy CI artifacts:

```text
wizardjoe-<gate>-<sha>-test-logs
wizardjoe-<gate>-<sha>-replay
wizardjoe-<gate>-<sha>-browser
wizardjoe-<gate>-<sha>-recordings
wizardjoe-<gate>-<sha>-raw-frames
wizardjoe-<gate>-<sha>-soak
```

Every compact gate JSON contains:

```text
gate_id, status, tested_sha, base_sha, branch, timestamp_utc,
python_version, dependency_lock_hash, asset_hash, graph_hash,
commands[{command, exit_code, duration_ms, result_summary, artifact_url}],
test_totals, visual_metrics, runtime_metrics, reviewer,
rollback_sha, limitations
```

Raw `.rgb`, full `.ndjson`, recordings, frame dumps, browser traces, and temporary files are never force-added to Git.

## 11. Handoff contract for every agent

Required handoff format:

```text
ROLE:
WORK_ITEM_ID:
STATUS: REVIEW_READY|BLOCKED
BASE_SHA:
BRANCH:
COMMIT_SHA:
LOCKS_HELD_AND_RELEASED:
ALLOWED_PATHS:
FILES_CHANGED:
INTERFACES_CONSUMED:
INTERFACES_PRODUCED:
COMMANDS_RUN:
EXACT_RESULTS:
EVIDENCE_PATHS_AND_HASHES:
VISUAL_REVIEW_REQUIRED:
KNOWN_LIMITATIONS:
ROLLBACK_POINT:
DEPENDENTS_UNBLOCKED:
NEXT_OPERATOR_ACTION:
```

Review-ready criteria:

- branch contains only allowlisted paths
- commit is based on the recorded checkpoint
- focused tests pass
- full suite result is reported, even if an unrelated known failure exists
- generated output is deterministic where applicable
- no Rust/Cargo/8787/8788 production reference
- no raw evidence committed
- lock released or explicitly handed to INT
- work item and evidence hashes agree

INT rejection criteria:

- missing base or commit SHA
- overlapping path ownership
- undocumented interface change
- skipped required test
- vague `tests pass` without command/totals
- production pose override used as gameplay motion
- full-body hashed dissolve used on a graph v2 production edge
- browser-side world/pose simulation
- Rust implementation or acceptance dependency

## 12. Branch and push sequencing

```text
Step 1  INT commits CAP-000..003 Python baseline checkpoint.
Step 2  INT commits CAP-010..011 planning checkpoint on top.
Step 3  INT pushes both commits and verifies remote planning SHA.
Step 4  Coordinator creates W1 role branches/worktrees from planning SHA.
Step 5  CAP-100..140 contract commits merge serially and produce C0 SHA.
Step 6  Role branches rebase/create W2 work from C0 SHA.
Step 7  Each W2 item produces one or more scoped commits and handoff.
Step 8  INT integrates in Section 6 serial order with full gate after every merge.
Step 9  INT pushes verified integration checkpoints after I0, M1, M2, M3, M4.
Step 10 V1..V3 test the exact pushed candidate SHA.
Step 11 INT commits compact F0 evidence, pushes final SHA, verifies remote.
Step 12 INT starts that exact final SHA on Python port 8765 and records listener proof.
```

Push safety:

- inspect workflow triggers before the first implementation push
- no force push
- no history rewrite after another worktree branches from a checkpoint
- remote SHA must be verified after every checkpoint push
- required checks attach to the exact pushed SHA
- evidence generated from a different SHA is invalid

## 13. Final release gate `F0`

Release is prohibited until every item below is true.

### Scope and reproducibility

- [ ] Clean clone of final remote SHA succeeds.
- [ ] Locked Python dependencies install without Rust toolchain.
- [ ] Production scope scan finds no Rust/Cargo/8787/8788 dependency.
- [ ] Server starts from documented command on port 8765.
- [ ] Manifest contains all 39 expected pose IDs and deterministic hash.
- [ ] Graph v2 classifies all 39 poses with no silent unreachable pose.
- [ ] Winged/flying contract is consistent across README, numbered docs, tests, and graph.

### Runtime and remote control

- [ ] Exact 60 Hz integer ticks; no fractional step.
- [ ] 15/24/30 render schedules match semantic hashes at common ticks.
- [ ] Two full command replays have identical state/source hashes.
- [ ] Every command has one terminal ack and deterministic ordering.
- [ ] Duplicate, stale, expired, unauthorized, and out-of-order commands do not mutate state.
- [ ] Key release, blur, hidden tab, gamepad disconnect, WS close, and heartbeat expiry safely release motion.
- [ ] One controller plus four viewers does not change simulation speed by more than 1%.

### Animation

- [ ] Ground idle/start/walk/turn/stop/run/recovery passes `M1`.
- [ ] Takeoff/hover/flap/travel/bank/fall/land passes `M2`.
- [ ] Required actions, interruption/recovery, speech, blink, expression, and secondary motion pass `M3`.
- [ ] Remote controls drive semantic motion rather than pose override.
- [ ] Production edges use no full-body hashed dissolve.
- [ ] Root/contact/staff/face/wing thresholds pass.
- [ ] Unsupported directional capability is honestly labeled and uses reviewed coherent fallback.

### ASCILINE and browser

- [ ] Source, decoded, and presented hashes agree in live browser sampling.
- [ ] New viewer bootstrap and subscriber-local resync pass.
- [ ] Standard profile sustains 24 presented FPS.
- [ ] Zero decode errors and zero unhandled console errors.
- [ ] Canvas remains crisp, integer aligned, and atomically presented.
- [ ] No PNG/video/sprite runtime replaces direct cells.

### Verification and evidence

- [ ] All Python tests pass; no skips/expected failures in required suite.
- [ ] All JavaScript input/client tests pass.
- [ ] Pose determinism, graph, transition, scope, browser, and soak checks pass.
- [ ] 10-minute mixed remote-control soak passes.
- [ ] Compact evidence manifest records exact final SHA and artifact URLs.
- [ ] Required GitHub checks are green on final SHA.
- [ ] Final commit is pushed and remote SHA matches local.
- [ ] Exact pushed SHA is running on Python port 8765 with recorded PID/command.

Final release command set:

```bash
python3 -m unittest discover tests
python3 tools/generate_reference_avatar_pose_cells.py --check-deterministic
python3 tools/verify_motion_graph.py --strict
python3 tools/verify_animation_quality.py --strict
python3 tools/verify_motion_visuals.py --strict
python3 tools/validate_pose_expansion_workflow.py
python3 tools/validate_cartoon_animation_program.py --phase release --strict
python3 tools/verify_python_production_scope.py --strict
node --test tests/web/*.test.mjs
python3 tools/verify_remote_control.py --url http://127.0.0.1:8765 --strict
python3 tools/verify_live_cartoon_browser.py --url http://127.0.0.1:8765 --browser chromium --strict
python3 tools/run_python_avatar_soak.py --url http://127.0.0.1:8765 --duration-seconds 600 --viewers 4 --slow-viewer --strict
python3 tools/build_cartoon_evidence_manifest.py --gate F0 --strict
git diff --check
```

The final report must say explicitly: `Production architecture: ASCILINE Python on port 8765. Rust: excluded and not executed.`

## 14. Coordinator synthesis notes

The integrated `IMPLEMENTATION_PLAN.md` and `WORKFLOW.md` should adopt this file's IDs, locks, checkpoint sequence, and release gate. Other role plans may refine implementation details inside their allowlists, but they may not:

- weaken Python-only production scope
- reintroduce the no-wings requirement
- use raw pose override as production motion
- remove deterministic command ordering or lease expiry
- claim equal directional animation quality unsupported by current art
- bypass serial INT wiring of shared files
- replace live port-8765 browser evidence with headless-only evidence
- commit raw captures or Rust artifacts as production proof

Implementation may begin only after `CAP-003` and `CAP-011` are pushed, their remote SHAs are recorded, and `CAP-140` freezes the shared contract.
