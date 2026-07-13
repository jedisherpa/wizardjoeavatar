# Rust Containment and Python Translation Audit

Role: `RUST` (re-scoped by user correction from Rust production design to containment and translation)

Date: 2026-07-12

Production target: the ASCILINE Python application at `http://127.0.0.1:8765/`

## Executive decision

Rust is a historical implementation detour in this repository. It must not become a production runtime, a sidecar, a Python extension, a WebAssembly module, an alternate browser client, or an acceptance gate for this program. The only production architecture recommended by this report is:

```text
remote controls / browser
        -> FastAPI routes and WebSocket on port 8765
        -> Python semantic command queue
        -> Python fixed-timestep simulation
        -> Python animation graph and motion controllers
        -> Python ASCILINE cell renderer
        -> Python adaptive frame encoder and fanout hub
        -> existing browser decoder and canvas presenter
```

The Rust tree contains several sound design ideas, especially integer simulation ticks, ordered command scheduling, explicit previous/current snapshots, bounded fanout, and deterministic quality evidence. Those ideas should be reimplemented idiomatically in Python. Rust code must not be linked, invoked, imported, translated mechanically, or allowed to own an artifact consumed by port 8765.

The current Rust `future_pose_transitions` failure is explicitly excluded from Python acceptance. The user reports **357 failures across 170 authored transition checks**. Its assertion aggregates every failure at [`rust/wizard_avatar_engine/tests/future_pose_transitions.rs:17`](../../../rust/wizard_avatar_engine/tests/future_pose_transitions.rs#L17) through line 81. That suite evaluates a separate Rust pose artifact, Rust controller, Rust sampler, and Rust quality rules. It is evidence that the historical branch is internally unfinished, not evidence that the Python deliverable fails. Per the user's stop instruction, this audit performed no further Rust builds or tests.

## Audit scope and observed runtime

This report inspected the exact dirty working tree, not merely the last commit. At audit time:

- The live listener on `127.0.0.1:8765` was a Python 3.9 process running `tools/run_wizard_avatar_server.py --port 8765`; the launcher constructs the Python frame source and FastAPI app at [`tools/run_wizard_avatar_server.py:21`](../../../tools/run_wizard_avatar_server.py#L21)-26.
- A stale historical `target/debug/wizard-avatar-server` process was found during containment and stopped. At report completion, Python remained listening on 8765 and no process was listening on the Rust demo port 8787.
- The live API reported a 24 Hz stream, a stable hub rate of approximately 24 Hz, zero hub queue drops, and the Python semantic state.
- The generated Python pose library contains 39 canonical 72 x 96 poses. Its manifest fixes the root at `(36, 95)` and defines root-relative semantic anchors at [`assets/reference/motion_sources/manifest.json:1`](../../../assets/reference/motion_sources/manifest.json#L1)-58.
- The dirty tree contains the entire Rust crate as untracked work, while the Python runtime, web client, tests, pose definitions, and animation-quality evidence also contain active uncommitted work. The Rust crate therefore cannot be treated as a clean historical baseline or as the source of current behavior.
- The Python package declares Python `>=3.9` and depends on FastAPI, Uvicorn, and Pillow in [`pyproject.toml:1`](../../../pyproject.toml#L1)-9. Recommendations below preserve that compatibility unless a separate, explicit runtime-upgrade decision is approved.

## Current Python production architecture

### Authority and transport

`create_app()` creates one `ProceduralWizardFrameSource`, one `WizardFrameHub`, the semantic HTTP routes, the state and hash diagnostics, and the ASCILINE WebSocket in [`wizard_avatar/server.py:23`](../../../wizard_avatar/server.py#L23)-175. All commands pass through the hub lock at lines 79-82. The WebSocket publishes the same encoded stream to browser subscribers at lines 136-173.

This is the correct production boundary. The program should improve it in place and keep its URL and protocol stable.

### Semantic state

The Python `WizardState` currently combines world movement, facing, locomotion, action, facial, speech, projection, and pose-transition state in a mutable dataclass at [`wizard_avatar/models.py:101`](../../../wizard_avatar/models.py#L101)-128. Commands remain loosely typed as a string plus arbitrary dictionary at lines 134-138.

The state is already semantic, which is consistent with the repository contract, but it lacks:

- an integer authoritative simulation tick;
- previous/current snapshots for render interpolation;
- explicit flight mode, altitude, vertical velocity, and takeoff/landing state;
- clip identity, normalized clip time, transition identity, and transition phase;
- command ID, command sequence, issued tick, and accepted tick;
- per-channel generation numbers and interruption ownership;
- contact state for each foot, hand, staff, and wing root;
- deterministic random seed/state for idle variation;
- a schema version in public state.

### Simulation and presentation timing

`WizardAvatarController.advance()` divides a requested duration into `SIMULATION_DT` pieces, but the final piece may be fractional and state time is stored as a float at [`wizard_avatar/controller.py:24`](../../../wizard_avatar/controller.py#L24)-31. The live frame hub advances simulation by exactly one render interval before every render at [`wizard_avatar/stream.py:104`](../../../wizard_avatar/stream.py#L104)-132. Consequently, simulation and presentation are still coupled at 24 Hz in production even though individual calls subdivide that interval internally.

This is sufficient for the pose showcase but not for a controllable cartoon character. Delayed rendering, a changed output FPS, or browser backpressure should not change command ordering, locomotion distance, clip state, contacts, or transition outcomes.

### Pose selection and transitions

The Python graph loader and selector are already the right seam for expansion. They load one JSON graph and prioritize pose override, casting, walking, action, and idle state at [`wizard_avatar/pose_selection.py:36`](../../../wizard_avatar/pose_selection.py#L36)-98. The current graph, however, exposes only idle mappings, six action mappings, and sparse walking samples; single-sample east/west clips visibly hold a still pose, while most of the 29 new action and flight poses are reachable only through the temporary direct pose override.

Transition duration is a global `0.12` seconds converted to render-frame count at [`wizard_avatar/frame_source.py:41`](../../../wizard_avatar/frame_source.py#L41)-53. The transition begins when the selected pose ID changes and advances by rendered frame index at lines 133-170. The compositor aligns only the root and uses a deterministic per-cell threshold dissolve at [`wizard_avatar/pose_compositor.py:63`](../../../wizard_avatar/pose_compositor.py#L63)-101.

That design preserves crisp square cells, but it is not motion synthesis. It does not understand anticipation, contact preservation, trajectory arcs, pose families, authored transition paths, body-part masks, wing phase, foot planting, or interruption windows. A dissolve between arbitrary silhouettes is also why a pose library can feel glitchy even when every endpoint looks good.

### Streaming and browser presentation

The Python hub uses one loop-local lock, bounded per-subscriber queues, forced keyframes after a drop, source hashes, and fanout diagnostics at [`wizard_avatar/stream.py:28`](../../../wizard_avatar/stream.py#L28)-163. These are strong production foundations.

The browser adds a two-frame jitter buffer, ordered decode pump, delta-resync behavior, bounded decoded buffer, presentation pacing, backlog dropping, and decoded/presented hashes at [`web/avatar/wizardClient.ts:3`](../../../web/avatar/wizardClient.ts#L3)-267. The Play button is still a scripted showcase: it walks a looping path while forcing each pose for 900 ms at [`web/avatar/wizardControls.ts:48`](../../../web/avatar/wizardControls.ts#L48)-88. It demonstrates reachability, not a motion graph.

## How the Rust detour diverged

The Rust crate did not remain a narrow performance experiment. It duplicated nearly every production ownership surface:

| Surface | Python production owner | Conflicting Rust surface | Containment finding |
|---|---|---|---|
| Process and listener | `tools/run_wizard_avatar_server.py`, `wizard_avatar/server.py` | `src/main.rs`, `src/server.rs` | Rust binds a second server (default 8787) and must never bind 8765. |
| Semantic state | `wizard_avatar/models.py` | `src/state.rs` | Different fields, enums, defaults, character ID, and serialization contract. |
| Command semantics | `wizard_avatar/controller.py` | `src/controller.rs` | Separate validation, timers, priorities, paths, and pose expiry behavior. |
| Runtime clock | Python frame hub/controller | `src/runtime.rs`, `src/hub.rs` | Rust has a second scheduler and wall-clock policy; it cannot drive Python state. |
| Pose assets | 39-pose generated JSON and manifest | embedded `future_pose_library.v3.json.gz` plus Python JSON include | Two artifacts with different counts, provenance, validators, and transition metadata. |
| Animation graph | `reference_avatar_animation_graph.json` | static Rust pose program and Rust playback | Two incompatible graph languages and transition policies. |
| Renderer/projection | Python frame source/compositor/projection | Rust renderer/projection/pose sampler | Different topology and pixel/cell outcomes. |
| Codec | `wizard_avatar/protocol.py` | `src/codec.rs` | Duplicate wire implementation can drift even when tags share names. |
| Fanout/WebSocket | `wizard_avatar/stream.py`, FastAPI | Rust hub/Axum | Competing connection, queue, resync, epoch, and lag semantics. |
| Browser | `web/avatar/*` | `rust/wizard_avatar_engine/web/*` | A second decoder, renderer, controls, and evidence harness. |
| Evidence and gates | Python tests/tools/evidence | numerous Rust binaries/tests/evidence writers | Rust failures must not block or bless Python delivery. |

The divergence is stated directly by the historical crate itself. Its README claims Rust owns the production runtime and that Python generators are prototypes at [`rust/wizard_avatar_engine/README.md:72`](../../../rust/wizard_avatar_engine/README.md#L72)-99. That is now false by product decision and by the observed live listener.

The pose boundary is especially hazardous:

- Rust embeds the Python generated pose JSON at [`rust/wizard_avatar_engine/src/reference_avatar.rs:11`](../../../rust/wizard_avatar_engine/src/reference_avatar.rs#L11)-17, creating a compile-time copy of a mutable Python artifact.
- Rust also loads its own compressed future-pose archive and enforces exactly 30 records, 29 geometries, and one alias at [`rust/wizard_avatar_engine/src/pose_asset.rs:222`](../../../rust/wizard_avatar_engine/src/pose_asset.rs#L222)-277.
- Rust's static pose program decides whether IDs are authored and carries another set of motion specifications in [`rust/wizard_avatar_engine/src/pose_program.rs:336`](../../../rust/wizard_avatar_engine/src/pose_program.rs#L336)-379.
- The Python production manifest has 39 actual poses and the Python graph currently references only a subset. Any Rust-generated correction would therefore be ambiguous: it could fix the historical Rust artifact while changing nothing on port 8765.

This was architectural scope expansion, not merely a language port. Maintaining parity would require every behavior and every bug fix to be implemented twice. That is unacceptable for animation work where small timing, anchor, and ordering differences are visible.

## Sound Rust ideas to translate into Python

Translation here means redesigning the idea against the Python data model and tests. It does **not** mean calling Rust, generating Python from Rust, sharing mutable runtime artifacts, or copying implementation line for line.

### 1. Integer fixed-tick runtime

The useful idea is represented by Rust's `AvatarRuntime`: integer tick, previous/current snapshots, commands scheduled to ticks, and deterministic same-tick order at [`rust/wizard_avatar_engine/src/runtime.rs:43`](../../../rust/wizard_avatar_engine/src/runtime.rs#L43)-149.

Python equivalent:

- Add `simulation_tick: int` and derive `time_seconds` only for presentation/API compatibility.
- Make `step_tick()` the only mutating simulation operation and use exactly `1/60` internally.
- Keep `previous_state` and `current_state` snapshots.
- Queue commands as `(accepted_tick, sequence, command_id, typed_payload)` and apply all due commands before stepping that tick.
- Render immutable snapshots; rendering must never advance state.
- Implement a monotonic accumulator in Python with a bounded catch-up count and explicit `dropped_simulation_seconds` telemetry.

Python's event loop uses a monotonic clock for delayed scheduling and exposes it through `loop.time()`, so wall-clock adjustments need not affect the accumulator. The official event-loop documentation also notes that callbacks sharing an identical deadline have undefined order; this reinforces the need for an explicit command sequence rather than relying on callback order.

### 2. Bounded catch-up and independent render cadence

The Rust accumulator caps catch-up at eight steps at [`rust/wizard_avatar_engine/src/runtime.rs:6`](../../../rust/wizard_avatar_engine/src/runtime.rs#L6)-40, and its hub separates a runtime task from a 24 Hz render task at [`rust/wizard_avatar_engine/src/hub.rs:144`](../../../rust/wizard_avatar_engine/src/hub.rs#L144)-187.

Python equivalent:

- One hub-owned coroutine remains the only state writer.
- Each wake reads `loop.time()`, runs zero to `MAX_CATCH_UP_TICKS` 60 Hz simulation ticks, then renders only when the presentation deadline is due.
- A render overrun skips presentation slots but never invents fractional simulation ticks.
- Commands enter a bounded inbox and are sequenced by the hub before mutation.
- Diagnostics expose accumulator lag, ticks run, catch-up events, dropped simulation time, render duration, encode duration, queue depth, and end-to-end command latency.

Do not split state mutation across multiple asyncio tasks. The Python hub lock already establishes a single authority; preserve that simpler ownership model.

### 3. Explicit transition playback state

Rust tracks current/previous pose, blend, generation, handoff, and expiry tick in its state at [`rust/wizard_avatar_engine/src/state.rs:311`](../../../rust/wizard_avatar_engine/src/state.rs#L311)-360 and centralizes timed pose playback in [`rust/wizard_avatar_engine/src/pose_playback.rs:1`](../../../rust/wizard_avatar_engine/src/pose_playback.rs#L1)-132.

Python equivalent:

- Add a typed `TransitionState` dataclass with source node, target node, start tick, duration ticks, curve, contact policy, interruption policy, and generation.
- Add independent typed channel states for locomotion, body action, face, speech, staff, wings, and effects.
- Resolve channel ownership once per simulation tick into an `AnimationIntent`.
- Let the animation graph select clips and authored transition clips; do not let the renderer infer a transition merely because a pose ID changed.
- Keep direct `pose` override only as a diagnostic command and mark it non-production in the public graph.

### 4. Ordered snapshots and deterministic evidence

Rust's packet includes epoch, sequence, simulation tick, presentation time, encoded bytes, full logical cells, keyframe status, and diagnostics at [`rust/wizard_avatar_engine/src/hub.rs:15`](../../../rust/wizard_avatar_engine/src/hub.rs#L15)-44. The Python browser already records decoded and presented hashes.

Python equivalent:

- Extend each source-hash history row with simulation tick, command sequence watermark, animation node, transition ID, and contact set.
- Add a deterministic replay file containing schema version, seed, initial state, and sequenced commands.
- Re-run the same replay twice in a headless Python test and require identical semantic-state hashes and source-cell hashes.
- Keep browser-presented hashes supplemental: source and decoded hash parity is necessary, while presentation cadence may legitimately hold or drop frames.

Use `hashlib.sha256` for durable evidence manifests; keep the current FNV-1a hash only as a fast per-frame transport diagnostic. Python's official `hashlib` API provides the stable named SHA-2 constructors.

### 5. Bounded fanout and resynchronization

Rust's broadcast capacity and bootstrap-keyframe ideas overlap with working Python behavior, not missing production functionality. The Python hub already bounds queues and replaces a slow subscriber backlog with a keyframe at [`wizard_avatar/stream.py:134`](../../../wizard_avatar/stream.py#L134)-145. Preserve and strengthen the Python path:

- Keep per-subscriber bounded queues and subscriber-local resync.
- Add explicit stream epoch and command/state watermark to `INIT` or a versioned JSON bootstrap message.
- Validate monotonically increasing frame sequences and reset decoder state on epoch change.
- Never let a slow subscriber slow simulation or other clients.
- Treat queue drop and resync counts as acceptance metrics.

### 6. Quality checks as Python-native contracts

Rust contains useful categories of checks: topology, anchors, contacts, deterministic snapshots, path continuity, projection stability, multiclient fanout, and codec parity. Recreate only applicable checks against the Python renderer and the production 39-pose graph. Do not import Rust thresholds or treat Rust pass/fail as normative.

The Python suite already tests crisp deterministic transition endpoints, channel independence, pose selection, anchor stability, stream contention, contiguous fanout, and subscriber resync. Build on [`tests/wizard/test_crisp_pose_transition.py:20`](../../../tests/wizard/test_crisp_pose_transition.py#L20)-51, [`tests/wizard/test_animation_channels.py:12`](../../../tests/wizard/test_animation_channels.py#L12)-81, and [`tests/wizard/test_stream_hub.py:10`](../../../tests/wizard/test_stream_hub.py#L10)-63.

## Recommended Python architecture

### Module boundaries

The planning wave should map these responsibilities onto conservatively scoped Python modules:

| Proposed Python boundary | Responsibility | Constraint |
|---|---|---|
| `wizard_avatar/runtime.py` | integer clock, accumulator, command inbox, previous/current snapshots | Pure state ownership; no drawing code. |
| `wizard_avatar/commands.py` | typed command payloads, IDs, validation, sequencing | FastAPI and WebSocket use the same parser. |
| `wizard_avatar/animation_state.py` | typed channels, clip state, transition state, contacts | Serializable public state has a schema version. |
| `wizard_avatar/animation_graph.py` | validate/load graph; select nodes, clips, transitions, interruption paths | One graph is the sole motion truth. |
| `wizard_avatar/motion.py` | walk, run, flight, hover, takeoff, bank, landing phase evolution | Returns semantic intent, not cells. |
| `wizard_avatar/frame_source.py` | render immutable snapshot and encode | Must not advance simulation. |
| `wizard_avatar/stream.py` | cadence, fanout, resync, lifecycle, diagnostics | Sole mutating runtime task. |
| `wizard_avatar/quality.py` | source-frame topology, anchor/contact continuity, replay hashes | Python-only acceptance. |

This table describes ownership, not a demand for eight large new files. Existing modules should be extended where they already provide the boundary cleanly.

### Typed Python state without a rewrite

Use standard-library `Enum`/`StrEnum` only if the declared Python floor is raised; Python 3.9 does not include `StrEnum`. Under the current floor, string-valued `Enum` subclasses or validated literals are appropriate. Use frozen dataclasses for immutable snapshots and normal mutable dataclasses for the hub-owned working state. Python's dataclass documentation describes `frozen=True` as emulated immutability, which is enough to prevent accidental renderer mutation in tests.

FastAPI already depends on Pydantic. Replace raw `Dict[str, Any]` route bodies with strict request models so malformed remote commands fail at the boundary instead of during state mutation. Pydantic's official strict-mode documentation distinguishes strict validation from coercion. Keep the internal reducer independent of Pydantic so headless deterministic tests remain cheap.

### Versioned animation graph

Evolve `reference_avatar_animation_graph.json` into the single Python-owned motion schema. At minimum it needs:

- `$schema`, `$id`, `schema_version`, and `asset_set_id`;
- graph nodes for grounded, airborne, action, reaction, and recovery states;
- clips with ordered key poses, normalized times, contacts, looping policy, and motion family;
- authored transitions with source/target patterns, duration ticks, easing, transition clip, contact policy, and interruption windows;
- channel masks for body, face, mouth, staff, wings, and effects;
- fallback paths that always terminate in a valid node;
- graph-level validation that every referenced pose is in the 39-pose library and every production pose has an intentional role or an explicit diagnostic-only classification.

JSON Schema's official guidance recommends declaring a specific `$schema` dialect and a unique `$id`, and supports modular `$defs`/`$ref` composition for non-trivial schemas. The current graph has only custom integer version fields and no machine-enforced schema.

### Remote-control semantics

Remote controls should express intent, not pose IDs:

- continuous movement input: desired planar velocity or destination;
- flight input: take off, land, ascend/descend, desired flight velocity, bank intent;
- action input: explain, point, cast, react, celebrate, guard, shush, flourish;
- face/speech input: expression and phoneme/mouth timing;
- cancellation: stop locomotion, cancel action, emergency reset.

Every accepted command returns `command_id`, `accepted_tick`, `sequence`, and resulting semantic state. A new command either replaces, queues behind, or is rejected by the owning channel according to graph policy. Direct pose forcing remains under a diagnostic namespace and is not used by gameplay controls.

### Async lifecycle

The current Python floor is 3.9, while `asyncio.TaskGroup` is available only from 3.11. Therefore this program should either:

1. keep Python 3.9 and explicitly own/cancel/await the hub and WebSocket receiver tasks with `try/finally`; or
2. approve a separate Python `>=3.11` migration, update the lock and CI matrix, and then use `TaskGroup` for structured cancellation.

Do not silently introduce 3.11-only code into the live 3.9 process. In either case, never swallow `CancelledError` without completing cleanup. The official asyncio task documentation recommends `try/finally` cleanup and explains TaskGroup's cancellation semantics.

## Rust exclusion boundary

### Immediate containment

The implementation plan should include a documentation/CI change with these rules:

1. `rust/wizard_avatar_engine/` is labeled `HISTORICAL-NONPRODUCTION` at its root.
2. No default setup, test, build, demo, release, or server command enters that directory.
3. No Python module imports a Rust extension, starts a Rust subprocess, reads a Rust-generated asset, or uses Rust output as a fallback.
4. No Rust process may bind 8765. Port 8787 is also not part of this program and should remain stopped unless a human explicitly performs archival inspection.
5. Rust tests, including `future_pose_transitions`, are excluded from Python CI status and completion gates.
6. Python artifacts under `wizard_avatar/definitions/` and `assets/reference/motion_sources/` are the sole production pose and graph inputs.
7. The duplicate Rust web directory is not served, bundled, or used for browser evidence.
8. Existing Rust evidence is clearly labeled historical and cannot satisfy Python acceptance criteria.

### Salvage process

For each idea listed in this report:

1. Write a Python behavioral test against the desired contract.
2. Implement the smallest Python design that satisfies it.
3. Compare behavior to the product specification and current Python evidence, not to Rust output.
4. Record the translated concept in the program decision log.
5. Never retain a runtime dependency on the Rust source or artifacts.

### Eventual removal

After all approved concepts have Python tests and the Python workflow has passed final acceptance:

- archive this report and any intentionally retained historical notes;
- remove the Rust crate, its `target/` artifacts, Rust-only evidence, and duplicate Rust web client in a dedicated, reviewable commit;
- verify no docs, scripts, CI files, package metadata, or production assets reference `rust/wizard_avatar_engine`;
- run the complete Python and browser acceptance suite on port 8765 after removal.

Do not remove Rust during the animation implementation waves. Containment first avoids mixing cleanup with behavior changes; removal is a final, separately reversible operation.

## Risks and mitigations

| Risk | Consequence | Mitigation |
|---|---|---|
| Rust re-enters as a performance shortcut | Two authorities and irreproducible visible differences | Enforce the exclusion boundary in docs and CI; optimize Python only after profiling. |
| Render loop remains the simulation clock | Motion changes with FPS or load | Introduce integer 60 Hz ticks, accumulator, bounded catch-up, and render-only snapshots. |
| Graph remains a pose lookup table | New poses still snap/dissolve rather than animate | Add clips, transition clips, contacts, masks, and interruption rules to one schema. |
| Raw dictionaries accept coerced or partial remote commands | Late failures and ambiguous command outcomes | Strict request models plus one internal typed command parser. |
| Direct pose override becomes gameplay API | No coherent contact, action, or recovery semantics | Move forcing to diagnostics; gameplay issues semantic intents. |
| Determinism relies on floats and wall time | Replay hashes diverge | Tick-based timers, seeded local PRNG, stable ordering, quantized output, replay tests. |
| Catch-up monopolizes the event loop | Input and fanout latency spike | Maximum catch-up ticks, explicit dropped-time metric, render budget telemetry. |
| Slow client corrupts delta history | Decode errors or stale motion | Subscriber-local keyframe resync and epoch-aware decoder reset. |
| Python 3.9/3.11 assumptions mix | Runtime-only failures | Decide the version floor explicitly before using TaskGroup, slots, or StrEnum. |
| Historical Rust failure is mistaken for product failure | Delivery blocked by irrelevant test surface | State the Python-only acceptance matrix in every workflow gate. |

## Measurable acceptance criteria for the Python implementation

### Authority and containment

- Exactly one production listener exists: Python on `127.0.0.1:8765`.
- No Rust process, library, subprocess, WASM file, generated asset, or web file participates in a production test.
- A repository search over production Python, web, tools, and CI code finds no runtime dependency on `rust/wizard_avatar_engine`.
- Python completion can pass while the historical Rust `future_pose_transitions` test remains failed or unrun.

### Deterministic simulation

- Simulation advances only by integer 60 Hz ticks; rendering at 15, 24, and 30 Hz produces identical semantic state hashes at matching ticks.
- Two clean runs of the same initial state, seed, and sequenced command log produce byte-identical per-tick semantic hashes and source-cell hashes.
- Commands accepted on the same tick execute in recorded sequence order; a 1,000-command replay is identical across two runs.
- A two-second synthetic stall runs no more than the configured catch-up limit in one event-loop turn and increments dropped-simulation-time telemetry.
- Rendering the same immutable snapshot twice produces identical cell bytes and does not mutate simulation state.

### Animation graph coverage

- All 39 production poses resolve through schema-validated graph clips, authored transitions, or explicit `diagnostic_only` classification.
- Ground motion includes idle, start, continuous walk, turn, stop, and recovery with stable foot contacts.
- Flight includes takeoff, hover/flap cycle, directional travel, bank left/right, action interruption, landing anticipation, contact, and recovery.
- Every public semantic action has a legal entry, interruption policy, and exit/recovery path from every supported locomotion family.
- No production control requires a raw `pose_id`.

### Motion and visual continuity

- Root displacement during local pose transitions is zero cells unless the authored transition declares world motion.
- A planted foot or planted staff contact moves zero cells relative to the projected floor during its contact interval.
- Face and mouth anchors move within the quality limits approved by the animation report; no overlay uses a stale source-pose anchor.
- All output remains cell-aligned with no subpixel filtering, blurred interpolation, duplicated face parts, disconnected staff, or unintended silhouette breakup.
- Walk speed and animation phase are distance-driven and remain synchronized after frame holds or browser drops.

### Remote controls and streaming

- Every HTTP and WebSocket command is schema validated and receives a command ID, sequence, and accepted tick.
- On localhost, 95% of accepted control commands alter authoritative semantic state within two simulation ticks; rejected commands make no partial mutation.
- Three simultaneous browser clients receive one authoritative sequence; a deliberately slow fourth client resynchronizes without causing simulation delay or drops for the other clients.
- Source, decoded, and browser logical hashes agree for every presented keyframe and delta frame in the verification run.
- A 10-minute mixed walking/flying/action/speech soak has no uncaught task exception, no sequence regression, no source/decode mismatch, and no unexplained resync.

### Evidence

- The Python suite includes fixed-clock, command-order, deterministic replay, graph validation, transition matrix, contact continuity, multiclient, resync, and browser-control tests.
- Evidence records schema version, asset hash, graph hash, seed, command log hash, tick, selected clip/transition, contacts, source hash, encoded tag, decoded hash, and presented hash.
- Rust test results and Rust artifacts are absent from the Python completion summary except for a short statement that the historical runtime is excluded.

## Primary and official source bibliography

1. [Python `asyncio` event loop](https://docs.python.org/3/library/asyncio-eventloop.html#scheduling-delayed-callbacks) - the event loop uses a monotonic clock for delayed work; `loop.time()` is the clock reference; equal-deadline callback order is undefined. This supports monotonic accumulation plus explicit command sequencing.
2. [Python `asyncio` synchronization primitives](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Lock) - official lock semantics for protecting the single Python runtime authority.
3. [Python `asyncio` queues](https://docs.python.org/3/library/asyncio-queue.html) - bounded queues and non-thread-safe event-loop ownership match the command inbox and subscriber fanout design.
4. [Python coroutines and tasks](https://docs.python.org/3/library/asyncio-task.html#task-groups) - structured task cancellation, cleanup requirements, timeouts, and the Python 3.11 introduction of `TaskGroup`.
5. [Python dataclasses](https://docs.python.org/3/library/dataclasses.html) - generated value types and `frozen=True` behavior for immutable render snapshots.
6. [Python enumerations](https://docs.python.org/3/library/enum.html) - standard-library typed symbolic states; version availability must respect the project's Python floor.
7. [Python typing `Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol) - structural interfaces can separate clock, renderer, and evidence sinks for deterministic tests without a foreign-language ABI.
8. [Python `hashlib`](https://docs.python.org/3/library/hashlib.html) - official stable SHA-2 constructors for durable artifact and replay evidence.
9. [Python random reproducibility notes](https://docs.python.org/3/library/random.html#notes-on-reproducibility) - seeded generators are reproducible under stated constraints; use one runtime-owned instance and record its seed/state.
10. [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/) - official binary/text/JSON WebSocket handling, disconnect handling, and multiple-client patterns applicable to the existing Python endpoint.
11. [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/) - strict boundary validation prevents implicit coercion of remote-control payloads.
12. [JSON Schema dialect and schema declaration](https://json-schema.org/understanding-json-schema/reference/schema) - official guidance for `$schema` and dialect identity.
13. [JSON Schema modular structure](https://json-schema.org/understanding-json-schema/structuring) - official `$id`, `$defs`, and `$ref` guidance for a non-trivial animation graph.
14. [WHATWG HTML animation frames](https://html.spec.whatwg.org/multipage/imagebitmap-and-animations.html#animation-frames) - browser animation-frame processing is a presentation concern and must not become the authoritative simulation clock.
15. [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/) - official Python metrics/traces/logs support; optional future instrumentation should wrap, not alter, deterministic runtime behavior.

## Planning-wave handoff

The Rust role's planning contribution should not design Rust work. It should turn this report into four Python-only work packages:

1. fixed-tick runtime and typed command queue;
2. versioned animation graph and typed channel/transition state;
3. deterministic replay, quality metrics, and stream observability;
4. Rust containment markers followed by a separately gated eventual-removal task.

Any integrated plan that assigns Rust ownership of simulation, rendering, transport, assets, browser code, evidence, or port 8765 conflicts with this audit and with the user's corrected production decision.
