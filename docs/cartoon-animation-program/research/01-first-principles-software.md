# Research Wave 1: First-Principles Software Architecture

Role: `FPSE`
Date: 2026-07-12
Production target: the existing ASCILINE Python service at `http://127.0.0.1:8765/`

## Executive conclusion

WizardJoe already has a credible server-authoritative delivery system and a valuable 39-pose source library. It does **not** yet have a 39-pose animation system. The current Python runtime has a legacy animation graph that references only eight unique poses, a presentation-only pose override, a render-coupled clock, immediate command mutation, and a three-frame spatial dissolve between unrelated complete rasters. The browser Play demo proves that every pose can be displayed while world position changes; it does not prove that the poses form coherent clips, that transitions preserve anatomy and contact, or that a remote controller can drive continuous motion.

The production path should remain Python, FastAPI, the existing direct ASCILINE cell framebuffer, the adaptive codec, and the browser client. The correct next architecture is an incremental refactoring inside that path:

1. one deterministic 60 Hz simulation owner with integer ticks and an accumulator independent of the 24 fps renderer;
2. one ordered command queue and explicit input-arbitration layer;
3. orthogonal semantic state regions for ground locomotion, flight, action, face, speech, staff, and effects;
4. data-driven animation clips and a motion graph that consume all pose metadata;
5. phase-preserving discrete playback for square-cell art, with authored transition recipes and anchor/contact constraints;
6. remote-control intents with sequence numbers, leases, dead zones, expiry, acknowledgement, and release semantics;
7. replay, state-hash, frame-hash, contact, and live-browser acceptance gates.

Rust is not a production target, dependency, migration path, or acceptance gate. It appears in the dirty tree only as historical work from an earlier side request. Where that work happens to illustrate a useful concept, the concept must be re-derived and implemented idiomatically in Python.

## Scope and method

This report was produced from the exact dirty working tree rather than from `HEAD` alone.

- Branch: `codex/build-repeatable-avatar-animation`
- `HEAD`: `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1`
- Dirty-tree entries at inspection: 60
- Live listener: Python PID 29196 on `127.0.0.1:8765`
- Live profile: 240 x 135 cells at 24 fps
- Live fanout at inspection: three subscribers, no queue drops, 24.0 actual fps
- Current Python regression suite: 62 tests passed in 17.857 seconds
- Generated production library: 39 poses, as recorded in the expansion evidence ([`evidence/pose-library-expansion/POSE_EXPANSION_COMPLETION.md:7-15`](../../../evidence/pose-library-expansion/POSE_EXPANSION_COMPLETION.md))

The report inspected the product contract, Python state/controller/locomotion/renderer/hub/protocol, browser controls/decoder/presenter, pose manifest/library/schema, animation graph, tests, live state, and current evidence. Technical recommendations were cross-checked against primary standards and official engine/runtime documentation listed in the bibliography.

## Non-negotiable boundary

The repository contract requires semantic server authority and direct cell generation rather than a flattened video or moving PNG ([`CODEX_GOAL.md:7-9`](../../../CODEX_GOAL.md), [`docs/03-required-architecture.md:31-54`](../../03-required-architecture.md)). The cartoon-animation program now records the same production boundary explicitly: Python controller, direct-cell renderer, FastAPI, WebSocket, and browser client are authoritative; Rust is historical only ([`docs/cartoon-animation-program/README.md:7-12`](../README.md), [`docs/cartoon-animation-program/README.md:42-47`](../README.md)). All recommendations below preserve that boundary.

## Current-state architecture

### What is already sound

1. **Server authority is real.** HTTP control routes create semantic `WizardCommand` objects and apply them through the shared frame hub ([`wizard_avatar/server.py:65-128`](../../../wizard_avatar/server.py)). WebSocket viewers receive one server-generated stream, and WebSocket commands enter the same hub ([`wizard_avatar/server.py:136-173`](../../../wizard_avatar/server.py)).
2. **There is one Python producer and fanout point.** `WizardFrameHub` holds a lock across simulation, rendering, encoding, and command mutation, then publishes the same message to all subscribers ([`wizard_avatar/stream.py:85-87`](../../../wizard_avatar/stream.py), [`wizard_avatar/stream.py:104-145`](../../../wizard_avatar/stream.py)). This is the right ownership boundary to keep.
3. **The codec and browser recover from delta loss.** Frames carry indices and adaptive tags; periodic full frames are generated every 48 frames ([`wizard_avatar/protocol.py:9-14`](../../../wizard_avatar/protocol.py), [`wizard_avatar/protocol.py:65-102`](../../../wizard_avatar/protocol.py)). The browser resets and requests resynchronization after an undecodable delta ([`web/avatar/wizardClient.ts:119-181`](../../../web/avatar/wizardClient.ts)).
4. **Browser presentation is atomic and crisp.** The client decodes complete logical frames, buffers them, presents on `requestAnimationFrame`, and drops stale backlog ([`web/avatar/wizardClient.ts:184-232`](../../../web/avatar/wizardClient.ts)). The canvas uses integer-sized cells, disables smoothing, draws to an offscreen canvas, then performs one visible `drawImage` ([`web/avatar/wizardCanvas.ts:43-72`](../../../web/avatar/wizardCanvas.ts), [`web/avatar/wizardCanvas.ts:75-135`](../../../web/avatar/wizardCanvas.ts)).
5. **Basic movement uses world space and distance-driven gait phase.** Position, velocity, acceleration, deceleration, and target are semantic state ([`wizard_avatar/models.py:67-79`](../../../wizard_avatar/models.py)). Walk phase advances from distance travelled, not render-frame count ([`wizard_avatar/locomotion.py:76-97`](../../../wizard_avatar/locomotion.py)). Direction selection includes an 8-degree hysteresis region ([`wizard_avatar/views.py:38-65`](../../../wizard_avatar/views.py)).
6. **The asset pipeline has useful semantic metadata.** The canonical manifest defines a fixed 72 x 96 canvas and root ([`assets/reference/motion_sources/manifest.json:1-17`](../../../assets/reference/motion_sources/manifest.json)), while individual entries carry facing, locomotion, action tags, phase, and anchor offsets. The flying family already contains hover/flap phases ([`assets/reference/motion_sources/manifest.json:833-969`](../../../assets/reference/motion_sources/manifest.json)). The generated schema requires root, face, feet, hands, and staff anchors ([`wizard_avatar/definitions/reference_avatar_pose_cells.schema.json:90-179`](../../../wizard_avatar/definitions/reference_avatar_pose_cells.schema.json)).
7. **Existing tests provide a useful floor.** The suite proves channel non-cancellation/restoration ([`tests/wizard/test_animation_channels.py:12-82`](../../../tests/wizard/test_animation_channels.py)), fanout parity and resync ([`tests/wizard/test_stream_hub.py:30-66`](../../../tests/wizard/test_stream_hub.py)), deterministic crisp-cell transition output ([`tests/wizard/test_crisp_pose_transition.py:20-51`](../../../tests/wizard/test_crisp_pose_transition.py)), and the ability to display all library poses while locomotion remains `walking` ([`tests/wizard/test_e2e.py:8-34`](../../../tests/wizard/test_e2e.py)). These are foundations, not proof of finished animation.

### What the 39-pose integration actually provides

The library has 39 complete raster poses, but its distribution is heavily asymmetric: 26 are south-facing, six southeast, two southwest, and only one each for east, west, north, northeast, and northwest. Locomotion tags describe 17 idle, nine flying, five walking, three running, two jumping, and one each airborne, kneeling, and landing. The schema carries phase and anchor data, but the runtime loader keeps only ID, description, size, root, anchors, and cells ([`wizard_avatar/reference_avatar.py:27-35`](../../../wizard_avatar/reference_avatar.py), [`wizard_avatar/reference_avatar.py:50-81`](../../../wizard_avatar/reference_avatar.py)). It drops facing, locomotion, actions, phase, and tags at load time.

The current animation graph still uses the original small set:

- eight idle-facing mappings, two of which map a stopped diagonal character to walking poses ([`wizard_avatar/definitions/reference_avatar_animation_graph.json:6-16`](../../../wizard_avatar/definitions/reference_avatar_animation_graph.json));
- six action mappings, with point aliased to explaining and reaction aliased to magic cast ([`wizard_avatar/definitions/reference_avatar_animation_graph.json:17-24`](../../../wizard_avatar/definitions/reference_avatar_animation_graph.json));
- four front-walk samples, three back-walk samples, two diagonal samples, and one static sample for each side view ([`wizard_avatar/definitions/reference_avatar_animation_graph.json:25-164`](../../../wizard_avatar/definitions/reference_avatar_animation_graph.json)).

Consequently, 31 of the 39 library poses are not selected by ordinary semantic locomotion or actions. They are reached by `pose_override_id`, which outranks the graph and labels the sample `pose_showcase` ([`wizard_avatar/pose_selection.py:49-75`](../../../wizard_avatar/pose_selection.py)). The Play button fetches every ID and issues 39 timed pose overrides while an unrelated looping walking path runs beneath them ([`web/avatar/wizardControls.ts:48-80`](../../../web/avatar/wizardControls.ts)). That is an excellent asset census and smoke test. It is not a motion graph.

## Concrete gaps from pose library to cartoon character

### 1. The simulation is not actually fixed-step at the live 24 fps profile

`SIMULATION_DT` is 1/60 second ([`wizard_avatar/locomotion.py:13-15`](../../../wizard_avatar/locomotion.py)), but `WizardAvatarController.advance()` repeatedly uses `min(SIMULATION_DT, remaining)` until the requested duration is exhausted ([`wizard_avatar/controller.py:24-31`](../../../wizard_avatar/controller.py)). The hub calls it once per 1/24-second render interval ([`wizard_avatar/stream.py:104-113`](../../../wizard_avatar/stream.py)). Since 1/24 is 2.5 simulation ticks, each render advances two 1/60 steps and one 1/120 partial step. Physics behavior therefore depends on render rate and includes variable steps despite the specification's fixed-60-Hz requirement ([`docs/16-world-space-movement.md:1-5`](../../16-world-space-movement.md)).

The hub's deadline uses `time.perf_counter()` and incremental sleeps ([`wizard_avatar/stream.py:104-132`](../../../wizard_avatar/stream.py)), but it advances a nominal frame interval rather than measured accumulated monotonic time. Under load it can render late without a bounded catch-up policy; under a different output fps it changes the simulation-step pattern.

### 2. Commands mutate state immediately instead of entering a deterministic event queue

`WizardCommand` has an optional `issued_at`, but it is not consumed ([`wizard_avatar/models.py:134-138`](../../../wizard_avatar/models.py)). `apply_command()` reflects on a handler and mutates the controller immediately ([`wizard_avatar/controller.py:33-41`](../../../wizard_avatar/controller.py)). HTTP and WebSocket commands execute whenever they acquire the hub lock, so command order depends on arrival and event-loop scheduling rather than an explicit server tick, source sequence, or priority policy ([`wizard_avatar/server.py:79-82`](../../../wizard_avatar/server.py), [`wizard_avatar/server.py:145-160`](../../../wizard_avatar/server.py)).

The original route contract requires stale-command rejection ([`docs/27-semantic-control-routes.md:62-72`](../../27-semantic-control-routes.md)); the current implementation has no stale definition, command ID, source ID, sequence, deadline, deduplication, acknowledgement over WebSocket, or audit log.

### 3. There is no input-arbitration model for remote controls

The browser maps each keydown to a distant absolute target and ignores repeated keydown events ([`web/avatar/wizardControls.ts:24-45`](../../../web/avatar/wizardControls.ts)). There is no keyup handling, normalized movement vector, analog magnitude, dead zone, heartbeat, lease, focus-loss release, controller disconnect release, or ownership rule. A remote control should express a short-lived **intent** such as `move_vector=(0.7,-0.4)` or `ascend=0.5`, not repeatedly choose world destinations.

Multiple HTTP clients and WebSocket clients can issue conflicting commands with last-lock-winner behavior. `stop`, path following, demo control, keyboard control, gamepad control, and a future external remote have no declared preemption or resumption semantics.

### 4. The state model conflates durable semantics, channel state, and presentation state

`WizardState` mixes world state, action timers, speech timers, pose transition bookkeeping, screen projection, encoder-facing diagnostics, and debug override state in one mutable dataclass ([`wizard_avatar/models.py:101-128`](../../../wizard_avatar/models.py)). `action` overlaps with `locomotion`; `_set_action("walking")` can directly set locomotion ([`wizard_avatar/controller.py:59-78`](../../../wizard_avatar/controller.py)). Reaction interruption saves a hand-built partial dictionary and later restores it ([`wizard_avatar/controller.py:59-90`](../../../wizard_avatar/controller.py)). This approach cannot safely scale to nested sequences such as walk + talk + point, fly + bank + cast, jump + land + recover, or remote interruption + resume.

The declared locomotion values are effectively idle/walking in Python runtime behavior; the asset metadata includes running, flying, jump, landing, kneel, and airborne states that have no semantic controller states. No altitude, vertical velocity, grounded flag, flight target, takeoff state, or landing state exists.

### 5. Pose selection and motion control are not separated cleanly

The graph selector first special-cases cast, then walking, then action, then idle ([`wizard_avatar/pose_selection.py:78-98`](../../../wizard_avatar/pose_selection.py)). This silently makes locomotion outrank most upper-body actions, even though the product contract calls for independent channels ([`docs/23-animation-channels.md:1-45`](../../23-animation-channels.md)). The graph provides no transition edges, entry conditions, exit conditions, interruptibility, minimum holds, phase synchronization, contact events, or action phases.

The current `PoseSample` can report contact, clip ID, and phase ([`wizard_avatar/pose_selection.py:28-34`](../../../wizard_avatar/pose_selection.py)), but rendering uses only `pose_id`; contact and clip are discarded immediately ([`wizard_avatar/frame_source.py:79-88`](../../../wizard_avatar/frame_source.py)). Contact therefore cannot drive planted-foot correction, shadow lift, landing, or transition selection. Shadow lift is instead inferred from a hard-coded walk-phase range ([`wizard_avatar/frame_source.py:97-101`](../../../wizard_avatar/frame_source.py)).

### 6. The transition compositor is deterministic but anatomically unaware

Each pose change lasts approximately 0.12 seconds in render frames ([`wizard_avatar/frame_source.py:41-53`](../../../wizard_avatar/frame_source.py)). Source and target are root-aligned, then each differing cell independently changes according to a coordinate hash threshold and smoothstep progress ([`wizard_avatar/frame_source.py:133-170`](../../../wizard_avatar/frame_source.py), [`wizard_avatar/pose_compositor.py:63-101`](../../../wizard_avatar/pose_compositor.py)).

This preserves square colors and repeatability, but it is a spatial dissolve, not interpolation of motion. At intermediate frames, unrelated pieces of both full-body rasters coexist. Root alignment alone cannot preserve planted foot, staff hand, eye line, silhouette connectivity, occlusion, or apparent volume. A three-frame dissolve between a grounded front pose and a banked flight pose is inherently incapable of producing anticipation, takeoff, arc, follow-through, or landing.

### 7. The reference path bypasses much of the original procedural face/channel renderer

When the reference library exists, `frame_source` always selects a complete pose raster and does not call the original procedural `render_wizard_local()` path ([`wizard_avatar/frame_source.py:79-96`](../../../wizard_avatar/frame_source.py)). The reference overlay currently draws only a toggled speaking mouth, magic/reaction sparks, and thinking dots ([`wizard_avatar/frame_source.py:181-241`](../../../wizard_avatar/frame_source.py)). It does not render blink or expression overlays. `blink_phase` is present in state but is not advanced by the Python controller; blink logic is consumed only by the bypassed legacy layer renderer ([`wizard_avatar/blink.py:4-25`](../../../wizard_avatar/blink.py), [`wizard_avatar/layers.py:198-199`](../../../wizard_avatar/layers.py)).

State tests can therefore pass while the corresponding visual channel is absent. For example, expression changes are asserted semantically by the transition matrix, but there is no reference-pose expression visualization gate.

### 8. Evidence currently checks availability and coarse continuity, not animation quality

The all-pose E2E test verifies that each override becomes the current pose and locomotion remains walking; it does not verify allowed neighbors, motion semantics, visual anatomy, contacts, or temporal pacing ([`tests/wizard/test_e2e.py:8-34`](../../../tests/wizard/test_e2e.py)). The anchor continuity test checks only framebuffer size, projected screen position, and scale across three directions ([`tests/wizard/test_anchor_continuity.py:7-30`](../../../tests/wizard/test_anchor_continuity.py)). The transition tool records churn, root/scale deltas, and final state, but only root and scale can currently create failures ([`tools/verify_animation_quality.py:122-180`](../../../tools/verify_animation_quality.py)).

Thus 32/32 transition scenarios and 62/62 tests are genuine regression evidence, but they do not establish planted-foot lock, hand-to-staff continuity, eye/mouth continuity, connected silhouettes, cyclic phase, input latency, command determinism, or flight behavior.

## Recommended Python production architecture

### A. One authoritative deterministic runtime

Keep `WizardFrameHub` as the sole live owner, but place a new `AvatarRuntime` inside it with these boundaries:

```text
monotonic wall clock
  -> fixed-step accumulator
      -> ordered command queue at tick boundary
          -> semantic statechart microstep
              -> locomotion/flight integration
                  -> animation graph evaluation
                      -> presented-pose snapshot
                          -> ASCILINE renderer
                              -> existing codec/fanout
```

Required runtime state:

```python
@dataclass
class RuntimeClock:
    simulation_tick: int
    accumulated_seconds: float
    dropped_seconds: float
    max_catch_up_steps: int

@dataclass
class RuntimeSnapshot:
    previous: SemanticAvatarState
    current: SemanticAvatarState
    presentation: PresentationState
```

Rules:

- The only physics step is exactly `1 / 60` second.
- Wall-clock elapsed time comes from the running asyncio loop's monotonic clock.
- Render rate may be 15, 24, or 30 fps without changing state at a given simulation tick.
- Catch-up is bounded; excess backlog is counted and dropped rather than producing an unbounded spiral.
- All timers are integer tick deadlines, not floating-point `*_until` seconds.
- Rendering samples state and never advances simulation itself.
- Tests can call `step_tick()` directly with no wall clock or sleep.

Python's event-loop documentation explicitly states that delayed scheduling uses monotonic clocks and `loop.time()` returns the loop's internal monotonic time. This matches the existing asyncio owner and avoids a parallel clock.

### B. Ordered command envelope and run-to-completion semantics

Replace ad hoc route payloads at the controller boundary with one validated envelope:

```json
{
  "schema_version": 1,
  "command_id": "uuid-or-client-generated-token",
  "source_id": "browser:session-id",
  "source_kind": "keyboard|gamepad|remote|demo|api",
  "sequence": 481,
  "kind": "control_intent",
  "issued_at_ms": 123456.0,
  "ttl_ms": 250,
  "payload": {}
}
```

The server assigns `received_order` and `apply_tick`. At the start of each simulation tick it:

1. sorts due commands by `(apply_tick, priority, received_order)`;
2. rejects duplicate `command_id` and non-increasing source sequence;
3. rejects expired continuous intents;
4. processes one command to completion, including all internal channel transitions;
5. emits an acknowledgement with applied tick, disposition, state revision, and optional validation error;
6. moves to the next external command only after the previous macrostep is stable.

This is an implementation of deterministic, run-to-completion statechart semantics rather than a requirement to adopt SCXML or XML. W3C SCXML is useful here because it formally separates parallel state regions while retaining deterministic serial event processing and explicit conflict priority.

### C. Explicit input arbitration

Separate **commands** from **continuous control intents**.

Commands are one-shot and server-owned: reset, stop, play action, speak, follow path, return to center. Intents are leased snapshots: ground move vector, flight move vector, ascend/descend, facing vector, and held action buttons.

Recommended arbitration:

| Priority | Source/intent | Behavior |
|---:|---|---|
| 100 | emergency stop/reset | cancels all locomotion, flight, path, and action leases |
| 80 | explicit one-shot action with `interrupt=true` | interrupts only channels declared interruptible |
| 60 | active direct-control lease | preempts path/demo locomotion while lease is fresh |
| 40 | path/demo controller | resumes only if configured and still valid |
| 20 | autonomous idle behavior | fills channels not owned by higher layers |

Use one active locomotion lease at a time, selected by priority then most recent accepted sequence. Leases expire after 250 ms unless refreshed. `keyup`, `blur`, visibility loss, gamepad disconnect, and WebSocket close send or cause a zero intent immediately. This prevents a remotely controlled wizard from continuing to walk after the controller disappears.

Keyboard and D-pad map to normalized digital axes. Gamepad axes retain their normalized `[-1, 1]` range, apply a configurable radial dead zone, then produce magnitude-aware speed. The W3C Gamepad specification defines axes in `[-1, 1]`, buttons in `[0, 1]`, and update timestamps, so the web adapter should preserve those semantics before sending a server-neutral intent.

### D. Orthogonal semantic state regions

Do not replace the current channels with one giant animation enum. Replace loosely coupled strings with explicit, legal regions:

```text
mobility:
  grounded.idle | grounded.walk | grounded.run
  takeoff | flying.hover | flying.travel | flying.bank
  landing | disabled

upper_body:
  neutral | explain | point | guard | cast | celebrate | shush | staff_spin

face:
  expression + blink

speech:
  inactive | active(phoneme/viseme timeline)

staff:
  held | planted | guard | thrust | spin | raised

effects:
  none | casting | reaction
```

Each region needs:

- current state and generation number;
- entry tick and optional deadline tick;
- priority and owner;
- interruption policy;
- restoration policy (`discard`, `resume_if_valid`, `restart`, or `return_to_neutral`);
- explicit transition event rather than direct cross-region field mutation.

Add `altitude`, `vertical_velocity`, `grounded`, and optional `target_altitude` to mobility state. Keep world `x/z` movement and projection intact. Altitude offsets the rendered root vertically and controls shadow separation; it must not be faked solely by selecting a flying raster.

### E. Motion graph distinct from pose assets

Extend the loader so `ReferencePose` retains the metadata already generated: facing, locomotion, actions, phase, tags, and all anchors. Then define a versioned motion-graph schema with:

```json
{
  "clips": {
    "walk_south": {
      "mode": "loop",
      "phase_source": "distance",
      "samples": [
        {"phase": 0.00, "pose_id": "walk_front_left", "contact": "left"},
        {"phase": 0.25, "pose_id": "front_idle", "contact": "passing"},
        {"phase": 0.50, "pose_id": "walk_front_right", "contact": "right"},
        {"phase": 0.75, "pose_id": "walk_front_right_lift", "contact": "passing"}
      ]
    }
  },
  "states": {},
  "transitions": []
}
```

Clip state belongs to presentation, not semantic world state:

- clip ID;
- normalized phase;
- source and target sample;
- transition recipe ID;
- transition start tick and duration ticks;
- contact marker and planted-foot anchor;
- action-event markers;
- previous fully presented snapshot.

Ground walk/run phase remains distance-driven. Flight flap phase is time-driven but persists across facing/bank changes. One-shot actions have anticipation, action, follow-through, and recovery segments. Entry chooses a compatible sample based on current phase/contact rather than always starting sample zero. Interruptions begin from the actual presented snapshot, not merely the nominal source pose ID.

Official Godot animation documentation is relevant as a design reference, not a dependency: it separates state machines, blend spaces, one-shots, and nested blend trees; for frame-by-frame 2D it explicitly offers discrete and carry modes, and its cyclic synchronization modes preserve locomotion phase. The same concepts should be implemented in the small Python graph evaluator without introducing Godot.

### F. Square-cell transition strategy

The output must remain crisp cells. Do not color-interpolate or geometrically resample the final framebuffer. Replace universal per-cell dissolve with ordered transition recipes:

1. **Within a coherent loop:** select complete authored samples at phase thresholds; carry normalized phase when changing speed or compatible facing.
2. **Between compatible poses:** root-align, apply integer planted-foot correction, and switch complete regions only when region metadata and anchor confidence allow it.
3. **Between incompatible full-body silhouettes:** use authored anticipation/recovery poses or a clean full-pose cut at a low-motion/contact-safe point. A coherent cut is preferable to a shredded dissolve.
4. **For flight takeoff/landing:** drive altitude and shadow continuously in world/presentation space while selecting complete takeoff, airborne, and landing poses at authored events.
5. **For face/speech/staff overlays:** mask and redraw only schema-declared semantic regions using pose-local anchors. Never infer anatomy from color at runtime.

Transition selection should be data, not nested conditionals. Every edge needs source family, target family, duration ticks, phase policy, root policy, contact policy, region policy, and interruption policy. Unsupported edges must fall back to an explicit safe recipe and emit diagnostics.

### G. Versioned protocol without replacing the ASCILINE stream

Keep the binary cell-frame format and adaptive codec initially. Add an application-level protocol version and command acknowledgements around it:

- negotiate a named WebSocket subprotocol such as `wizardjoe.asciline.v1`;
- include protocol version, runtime epoch, state revision, simulation tick, and frame sequence in initialization metadata;
- keep binary frame messages ordered and atomic;
- send typed JSON acknowledgement/event messages for commands, lease expiry, state transitions, and errors;
- retain per-viewer resync keyframes;
- preserve HTTP routes as automation-friendly adapters to the same command-envelope queue;
- publish JSON Schemas for commands, acknowledgements, motion graph, and pose metadata;
- never maintain separate HTTP and WebSocket controller implementations.

RFC 6455 guarantees message-fragment ordering, not application-level command freshness, deduplication, or arbitration. Those are WizardJoe protocol responsibilities. RFC 9110 also warns that POST is not inherently idempotent, so clients must not blindly retry control POSTs; command IDs and result lookup make retries safe at the application level.

### H. Browser control adapter

Keep the browser presentation loop independent of simulation. Add an input adapter that:

- owns keydown/keyup, blur, visibility, and gamepad connect/disconnect lifecycle;
- polls gamepads on `requestAnimationFrame` using its supplied timestamp;
- reduces all devices to one normalized `ControlIntent`;
- sends on value change and at a 10-20 Hz heartbeat while nonzero;
- immediately sends zero on release/loss;
- displays connection/lease/ack status through diagnostics;
- never changes world position or animation state locally.

`requestAnimationFrame` can run at 60, 75, 120, or 144 Hz and is paused in background tabs, so the browser must use timestamps and server leases rather than treating callback count as time. The server remains authoritative and safe when callbacks pause.

## Migration strategy

The refactor should preserve a runnable port-8765 system after every wave.

### Wave 0: Freeze the real baseline

- Record dirty-tree SHA/content manifest, Python version, generated-library hash, live profile, and existing 62-test result.
- Add a deterministic scenario log for current behavior before changing semantics.
- Label Rust evidence non-authoritative so it cannot satisfy Python gates accidentally.

### Wave 1: Schemas and metadata only

- Add command-envelope, acknowledgement, motion-graph, transition-recipe, and extended pose schemas.
- Make `ReferencePose` retain all existing generated metadata.
- Add validators and census reports; no rendering behavior changes.

### Wave 2: Deterministic runtime clock and queue

- Introduce `step_tick()`, fixed-step accumulator, integer deadlines, ordered command queue, state revision, and replay log.
- Keep old routes as adapters.
- Prove state/frame equivalence for existing scripted scenarios where semantics are intentionally unchanged.

### Wave 3: Input arbitration and direct control

- Add control leases, normalized move/facing/flight intents, key release, disconnect expiry, acknowledgements, and multiple-source priority tests.
- Add keyboard first, then gamepad and external remote using the same envelope.

### Wave 4: Motion graph and locomotion clips

- Replace legacy pose selection with data-driven clips for idle, walk, run, flight, takeoff, landing, and bank.
- Preserve distance gait phase and flight flap phase across compatible transitions.
- Keep pose override only behind an explicit debug/showcase route; it must not participate in production control.

### Wave 5: Constrained transition compositor and independent visual channels

- Add transition recipes, region masks, planted-foot/root correction, staff/face anchor handling, and presented-snapshot interruption.
- Re-enable visible blink, expression, and speech overlays for all compatible poses.
- Remove the universal coordinate-hash dissolve from production graph edges.

### Wave 6: Live browser, remote, and evidence gates

- Run deterministic replay twice and compare state/frame hashes.
- Exercise keyboard, gamepad, external WebSocket control, focus loss, disconnect, reconnect, and resync.
- Capture clips and per-frame metrics for every required transition family.
- Run the complete test suite and strict Python quality verifier against port 8765.

## Risks and mitigations

| Risk | Why it exists now | Mitigation |
|---|---|---|
| Pose incompatibility | Complete source images were independently generated; equal canvas/root does not imply anatomical correspondence | Classify compatibility families; use authored intermediates or coherent cuts; never assume universal cell correspondence |
| Sparse directional coverage | 26 of 39 poses are south-facing and side/back families are thin | Limit graph edges to supported families, mirror only after art review, and add missing source poses deliberately |
| Incorrect anchors | Several integrations use estimated/default anchor offsets | Add per-pose reviewed confidence and anchor QA; block region blending below confidence threshold |
| Foot sliding | Current renderer ignores contact metadata | Make contact/planted foot a runtime presentation constraint and test integer foot displacement |
| Staff popping/side swap | Staff placement differs dramatically between poses | Track hand, tip, and optional second endpoint/shaft region; require staff-compatible transitions |
| Render-dependent behavior | 24 fps currently creates partial 60 Hz steps | Fixed accumulator with integer ticks and render-only sampling |
| Stuck remote input | No release, lease, or disconnect semantics | 250 ms server lease, zero intent on release/loss, expiry event and tests |
| Command races | HTTP and multiple WebSockets mutate on arrival | One ordered queue, source sequence, command ID, priority, apply tick, acknowledgement |
| Action restore corruption | Partial dictionaries do not compose | Channel generations and explicit interruption/restoration policies |
| State says feature works but pixels do not | Reference path bypasses procedural face/blink layers | Pixel-level channel tests and reviewed frame evidence for every state change |
| Protocol regressions | New control messages share the frame socket | Version and type every message, retain resync tests, and add A/B source/decode/present hash checks |
| Performance regression | 39 large JSON rasters and richer graph evaluation run in one loop | Cache immutable pose canvases/metadata, precompile transition tables, measure tick/render/encode budgets separately |
| Scope drift into Rust | Dirty tree contains extensive historical Rust work | Exclude `rust/` from production ownership, implementation DAG, CI gates, and acceptance evidence |

## Measurable acceptance criteria

### Determinism and timing

- Simulation advances only in exact 1/60-second ticks; no partial tick is ever passed to locomotion or animation logic.
- The same initial state and command log produce byte-identical semantic state hashes at every tick in two runs.
- The same tick snapshots rendered at 15, 24, and 30 output fps produce identical frames for matching simulation ticks.
- A two-second scheduler stall executes no more than the configured catch-up cap and reports all dropped simulation time.
- All action, speech, lease, and transition deadlines are integer simulation ticks.

### Command and remote control

- Every accepted command receives exactly one acknowledgement containing `command_id`, `apply_tick`, `state_revision`, and result.
- Duplicate IDs and non-increasing source sequences do not apply twice.
- Expired/stale inputs are rejected deterministically.
- Conflicting sources resolve according to the documented priority table in 100% of permutation tests.
- Keyboard keyup, browser blur, hidden-tab transition, gamepad disconnect, WebSocket close, and missing heartbeat all produce zero locomotion within 250 ms plus one simulation tick.
- Gamepad axes and keyboard inputs drive the same normalized intent schema; no client changes world position directly.
- Measured local control-to-first-semantic-change p95 is at most 100 ms and control-to-first-presented-frame p95 is at most 180 ms under the normal 24 fps profile.

### Motion graph

- Every one of the 39 poses is either referenced by at least one reviewed clip/transition/debug-only classification or explicitly marked unused with rationale.
- Production locomotion never depends on `pose_override_id`.
- Idle, walk, run, hover, flight travel, bank, takeoff, landing, and stop have explicit legal transitions and safe fallbacks.
- Walk/run phase is continuous through speed and adjacent-facing changes; flight flap phase is continuous through hover/travel/bank changes.
- Unsupported state transitions fail validation before runtime.
- Stopped characters resolve to a semantically idle pose, never a pose tagged only as walking/running/flying.

### Visual continuity

- Root screen displacement is 0 cells for fixed-world action/facing changes.
- Planted-foot displacement is 0 cells across grounded loop sample boundaries and at most 1 cell during approved takeoff/landing release frames.
- Staff-hand anchor error is 0 cells in stable frames and at most 1 cell on approved compatible transitions.
- Mouth and eye anchors move at most 1 cell between adjacent face-compatible frames.
- No intermediate frame contains two heads, two staffs, disconnected face features, or a mixed source/target silhouette outside declared region masks.
- All visible cells remain exact integer squares with palette colors; no antialiasing or color interpolation appears.
- Blink, every supported expression, and speech mouth motion produce a measurable pixel change on the reference-pose path while preserving root position.

### Delivery and protocol

- One Python hub owns simulation, rendering, encoding, and fanout on port 8765.
- Two simultaneous viewers receive the same decoded logical frame hash sequence.
- Injected delta loss causes one viewer-specific keyframe resync without resetting simulation or other viewers.
- Command traffic cannot interleave partial frame presentation or mutate the browser locally.
- HTTP and WebSocket adapters produce the same queued command envelope and semantic result.
- The existing 62 tests remain green, and new deterministic-clock, queue, arbitration, motion-graph, visual-channel, and browser-control suites pass.
- Final evidence includes command logs, state hashes, source/decode/present hashes, transition metrics, browser console output, screenshots/contact sheets, and short recordings from the live Python service.

## Architectural decisions recommended for planning wave

1. **Adopt:** Python `AvatarRuntime` with fixed-step accumulator and tick queue inside `WizardFrameHub`.
2. **Adopt:** versioned command envelope, acknowledgement, source sequence, lease, state revision, and replay log.
3. **Adopt:** orthogonal state regions with deterministic run-to-completion processing.
4. **Adopt:** metadata-complete pose loader and versioned clip/transition graph.
5. **Adopt:** discrete phase-carry playback and constrained authored transition recipes.
6. **Adopt:** browser input adapter for keyboard/gamepad/remote intents; keep server authority.
7. **Retain:** direct ASCILINE cell rendering, adaptive codec, per-viewer keyframe resync, offscreen atomic canvas drawing.
8. **Deprecate from production:** universal pose override as motion control, coordinate-hash body dissolve, floating-point timer deadlines, render-coupled partial simulation steps, absolute-target key controls, unacknowledged unsequenced remote commands.
9. **Reject:** Rust migration, Rust production dependency, client-side world simulation, video/sprite-sheet substitution, or a second animation runtime beside the Python controller.

## Primary and official bibliography

1. [W3C SCXML 1.0 Recommendation](https://www.w3.org/TR/scxml/) - parallel state regions, deterministic priority, and run-to-completion event processing. Used as a semantic model, not as a proposed XML dependency.
2. [Python `asyncio` event loop documentation](https://docs.python.org/3/library/asyncio-eventloop.html#scheduling-delayed-callbacks) - event-loop scheduling uses a monotonic clock and exposes `loop.time()` on the same clock.
3. [Godot Engine stable documentation: Using AnimationTree](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html) - official reference for separating state machines, blend spaces, blend trees, one-shots, discrete/carry playback, cyclic phase synchronization, and root motion. Used as architecture research only; Godot is not a dependency.
4. [W3C Gamepad specification](https://www.w3.org/TR/gamepad/) - normalized axes/buttons, input timestamps, connection state, and standard mapping semantics for the browser adapter.
5. [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/rfc/rfc6455.html) - message framing/order, binary and text messages, control frames, and subprotocol negotiation. Application freshness and arbitration remain WizardJoe responsibilities.
6. [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) - request semantics and idempotency; POST commands require application-level IDs/deduplication before safe retry.
7. [JSON Schema Draft 2020-12 Validation](https://json-schema.org/draft/2020-12/json-schema-validation) - structural assertion vocabulary for commands, acknowledgements, pose metadata, and motion graphs.
8. [WHATWG HTML Standard: animation frames](https://html.spec.whatwg.org/multipage/imagebitmap-and-animations.html#animation-frames) - normative browser animation-frame scheduling model for presentation and gamepad polling.

## Handoff to the four-agent planning wave

The coordinated plan should preserve these ownership boundaries:

- FPSE: Python runtime clock, command envelope/queue, state regions, arbitration, replay, and protocol adapters.
- ANIM: clip taxonomy, pose compatibility, phase/contact annotations, transition recipes, timing, and visual thresholds.
- Rust role: containment audit only; translate any generally useful deterministic-testing ideas into Python tasks without adding Rust scope.
- PLAN: wave DAG, disjoint file ownership, checkpoint commits, acceptance evidence, rollback points, and port-8765 release gate.

The plan should not begin by adding more poses. It should first make the existing 39 poses semantically loadable, classifiable, replayable, and safely transitionable in the one authoritative Python runtime.
