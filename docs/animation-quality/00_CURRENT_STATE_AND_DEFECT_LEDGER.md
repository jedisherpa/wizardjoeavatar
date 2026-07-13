# Current Animation State and Defect Ledger

Baseline date: 2026-07-12  
Branch: `codex/build-repeatable-avatar-animation`  
Commit: `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1`  
Primary runtime: `http://127.0.0.1:8787/`  
Isolated reproduction runtime: `http://127.0.0.1:8788/`

## Scope and Method

This is the pre-fix baseline for the animation-quality pass. The Rust server,
adaptive WebSocket stream, production browser decoder, and browser Canvas path
were exercised together. No animation-quality fixes were made before this
ledger was produced.

The baseline includes:

- four browser recordings and their source frame sequences
- server-authoritative state snapshots at command boundaries
- browser and server frame-pacing samples
- codec and reconnect logs
- browser console errors
- Rust and Python test results
- current listener and multi-client evidence

Evidence root: `evidence/animation-quality/baseline/`

Key artifacts:

- `baseline-summary.json`
- `state-snapshots.json`
- `recordings/01-locomotion-directions.mp4`
- `recordings/02-speech-actions-expressions.mp4`
- `recordings/03-circles-figure-eight.mp4`
- `recordings/04-reconnect-replay.mp4`
- `screenshots/*-contact-sheet.png`
- `logs/browser-frame-pacing.json`
- `logs/browser-console.json`
- `logs/listener-8787.txt`
- `logs/cargo-test.txt`
- `logs/python-test.txt`

## Baseline Results

- Rust: 23 tests passed across unit and integration targets; 0 failed and 0 ignored.
- Python: 31 tests passed; 0 failed and 0 skipped.
- Browser console: 13 captured `Delta frame without previous frame` errors.
- Browser-reported rate: 30-47 rendered frames per second despite a nominal
  24 FPS source.
- Browser sequence advance: 10-20 server frame indices per 200 ms sample,
  averaging 15.92. This is incompatible with one 24 FPS authoritative stream.
- The live 8787 listener had eight established browser sockets during capture.
- A fresh 8788 listener acquired four established sockets from one browser
  surface and advanced the same shared simulation from all four tickers.
- Contact sheets contain deterministic full-character pose snaps plus
  intermittent partially drawn/torn silhouettes.

Passing feature tests therefore do not prove animation continuity. They assert
that states and frames exist, not that transitions are temporally coherent.

## Defect Ledger

### ANIM-GLITCH-001: Every viewer advances the shared simulation

- Severity: critical
- Frequency: always with more than one WebSocket client
- Deterministic: yes
- Reproduction: open two clients to `/ws/avatar/wizard?codec=adaptive` and
  compare `/api/avatar/wizard/state` time and frame-sequence advance with the
  single-client rate.
- Affected states: all locomotion, actions, speech, blink, and paths
- Expected: one 60 Hz authoritative simulation and one rendered frame per
  channel, fanned out to all viewers.
- Actual: every socket owns a 24 Hz ticker and calls
  `ProceduralWizardFrameSource::next_encoded_frame`, which advances the shared
  controller by `1 / fps`.
- Visible symptom: animation speed changes with viewer count; command timers,
  gait phase, blink timing, and paths run too fast.
- Likely subsystem: server fanout and simulation clock
- Relevant source: `src/server.rs::handle_socket`,
  `src/frame_source.rs::next_frame`
- State evidence: 30-47 browser renders per second and 10-20 sequence indices
  per 200 ms; eight sockets on 8787 and four on the clean 8788 listener.
- Evidence: `logs/browser-frame-pacing.json`, `logs/listener-8787.txt`

### ANIM-GLITCH-002: Automatic tours race once per connected client

- Severity: critical
- Frequency: always on connection
- Deterministic: yes
- Reproduction: load the page, do not press Motion tour, and observe semantic
  state changes; add another client and observe overlapping reset/path/action
  commands.
- Affected states: every transition and interruption category
- Expected: the tour runs only after the explicit Motion tour command.
- Actual: `ws.onopen` calls `startMotionTour()` and each client schedules its
  own repeating 28.5 second command sequence.
- Visible symptom: user commands are overwritten, unrelated actions appear,
  and captures show states not requested by the active control sequence.
- Likely subsystem: browser controller and multi-client command ownership
- Relevant source: `web/wizard.js::connect`, `startMotionTour`
- Evidence: all baseline recordings; command/state pairs in
  `state-snapshots.json`

### ANIM-GLITCH-003: Reconnects corrupt the global delta encoder

- Severity: critical
- Frequency: frequent under reconnect or concurrent clients
- Deterministic: yes
- Reproduction: connect a second viewer or reload while another viewer is
  active.
- Affected states: reconnect and replay continuity; all visible frames after a
  reset until a compatible keyframe arrives
- Expected: per-client decode state begins from a fresh keyframe without
  changing other clients' encoder history.
- Actual: every connection calls `source.reset_encoder()` on the one shared
  encoder. Existing viewers can then receive deltas against a frame they never
  received.
- Visible symptom: decode stops and the last frame freezes or flashes.
- Likely subsystem: adaptive encoder ownership and resynchronization
- Relevant source: `src/server.rs::handle_socket`,
  `src/frame_source.rs::reset_encoder`, `web/wizard.js::makeDecoder`
- State evidence: reconnect count jumped from 80 to 82 across one reload.
- Evidence: `recordings/04-reconnect-replay.mp4`,
  `logs/04-reconnect-replay.json`, `logs/browser-console.json`

### ANIM-GLITCH-004: The browser has no bounded frame queue or presentation boundary

- Severity: high
- Frequency: frequent during complex poses and under load
- Deterministic: load-dependent
- Reproduction: run circles or action overlays while capturing consecutive
  browser frames.
- Affected states: all movement and effect-heavy actions
- Expected: ordered decode into a bounded latest-frame queue, then atomic
  presentation on `requestAnimationFrame`.
- Actual: every WebSocket message is appended to an unbounded Promise chain and
  immediately painted through thousands of `fillRect` calls on the visible
  canvas.
- Visible symptom: partially drawn silhouettes, overlapping old/new poses,
  stale-frame latency, and variable browser FPS.
- Likely subsystem: browser decode queue and Canvas presentation
- Relevant source: `web/wizard.js::connect`, `renderFrame`,
  `renderFrameToAvatar`
- Evidence: all contact sheets, especially path and action captures;
  `logs/browser-frame-pacing.json`

### ANIM-GLITCH-005: Per-frame tight cropping erases root motion and causes scale popping

- Severity: high
- Frequency: every rendered frame
- Deterministic: yes
- Reproduction: walk in depth, change direction, or trigger magic effects while
  watching the avatar's size and center.
- Affected states: depth movement, view changes, gestures, magic, shadow
- Expected: the fixed stage projection determines root, scale, and floor
  contact.
- Actual: the client finds the non-white bounding box every frame, expands it by
  six cells, scales it to 90% of a square canvas, and recenters it. A spark,
  staff, shadow, or silhouette change changes the crop.
- Visible symptom: root popping, whole-character size jumps, lost world-space
  travel, and effect-driven reframing.
- Likely subsystem: browser compositor
- Relevant source: `web/wizard.js::renderFrameToAvatar`
- State evidence: server scales ranged from 2.25 to 2.875, but the browser kept
  normalizing each pose to nearly the same canvas occupancy.
- Evidence: all recordings and contact sheets; `baseline-summary.json`

### ANIM-GLITCH-006: Locomotion hard-switches unrelated pose masks

- Severity: high
- Frequency: four times per gait cycle and on every direction boundary
- Deterministic: yes
- Reproduction: walk front or back at constant speed and inspect phase slots
  around 0.25, 0.50, 0.75, and wraparound.
- Affected states: walk, turn, front/diagonal/side/back transitions
- Expected: phase-preserving pose generation or a transition blend with stable
  root and anchors.
- Actual: `walking_pose_id` selects one of four independent pose masks by
  `floor(walk_phase * 4)` with no pose matching, crossfade, or anchor blend.
- Visible symptom: hat, beard, robe, arms, staff, and wings teleport between
  silhouettes.
- Likely subsystem: pose selection and transition graph
- Relevant source: `src/renderer.rs::walking_pose_id`,
  `reference_pose_id_for_state`
- Evidence: `recordings/01-locomotion-directions.mp4`,
  `recordings/03-circles-figure-eight.mp4`

### ANIM-GLITCH-007: Color-classified cell warping tears the character

- Severity: high
- Frequency: every front/back walk phase
- Deterministic: yes
- Reproduction: walk south or north and inspect consecutive frames.
- Affected states: front and back locomotion; staff and outer silhouette
- Expected: explicit region masks and anchor-driven cell motion with one output
  cell footprint per source cell.
- Actual: motion regions are inferred from color, normalized position, and
  saturation. Each source cell is redrawn with a footprint of
  `ceil(scale) + 1`, causing overlaps and order-dependent smearing.
- Visible symptom: shredded horizontal bands, duplicated outlines, detached
  staff fragments, and robe/wing discontinuity.
- Likely subsystem: procedural pose deformation and rasterization
- Relevant source: `src/renderer.rs::reference_walk_cell_offset`,
  `src/cell.rs::blit_scaled_with_offsets`
- Evidence: all contact sheets; the most severe frames are in
  `frame-sequences/01-locomotion-directions/` and
  `frame-sequences/03-circles-figure-eight/`

### ANIM-GLITCH-008: Side and diagonal walking have no complete gait

- Severity: high
- Frequency: always in those directions
- Deterministic: yes
- Reproduction: walk east/west, then any diagonal.
- Affected states: profile and all four diagonal locomotion states
- Expected: two planted contacts, alternating leg swing, arm counter-swing,
  boot clearance, and phase continuity.
- Actual: profile motion only offsets a small boot/hem subset; diagonal motion
  returns `(0, 0)` for every cell.
- Visible symptom: foot sliding and a rigid body translating across the floor.
- Likely subsystem: directional gait authoring
- Relevant source: `src/renderer.rs::reference_walk_cell_offset`
- Evidence: locomotion and path recordings

### ANIM-GLITCH-009: Independent channels collapse into one destructive action state

- Severity: high
- Frequency: every action or speech interruption
- Deterministic: yes
- Reproduction: walk, speak, then explain or point; let either timer expire;
  trigger reaction during another stable action.
- Affected states: walk/speak, speak/walk, explain, point, think, cast, reaction
- Expected: locomotion, face, speech, upper body, and staff remain independent;
  reaction returns to the prior stable state.
- Actual: `set_action` overwrites action, upper-body action, staff state, and one
  shared timeout. Timer completion sets idle without a transition snapshot or
  restoration stack.
- Visible symptom: arms and staff teleport, speech gestures disappear, reaction
  returns to idle, and overlapping commands cancel the wrong channel.
- Likely subsystem: animation state hierarchy and interruption policy
- Relevant source: `src/controller.rs::set_action`, `update_timers`,
  `channels_for_action`
- Evidence: `recordings/02-speech-actions-expressions.mp4`,
  `logs/02-speech-actions-expressions.json`

### ANIM-GLITCH-010: Face, mouth, gesture, and staff overlays are not pose-anchored

- Severity: high
- Frequency: every non-front pose or pose-mask change
- Deterministic: yes
- Reproduction: speak or change expression while turning; point or cast from a
  side/back view.
- Affected states: blink, speech, expressions, gestures, staff during turns
- Expected: overlays use per-pose semantic anchors and scale to the same source
  cell footprint as the body.
- Actual: overlays use fixed local coordinates relative to whichever root anchor
  the selected pose happens to provide, then write isolated single stage cells.
- Visible symptom: facial marks pop or disappear, mouth closure is not coherent,
  effects drift, and the staff hand has no stable attachment contract.
- Likely subsystem: anchor schema and additive layers
- Relevant source: `src/renderer.rs::reference_stage_point`,
  `draw_reference_expression`, `draw_reference_mouth`,
  `draw_reference_action_effects`
- Evidence: action recording and frame sequence

### ANIM-GLITCH-011: Simulation is tied to render production instead of a fixed clock

- Severity: high
- Frequency: always; visible when FPS or viewer count changes
- Deterministic: yes
- Reproduction: vary clients or output FPS and compare path duration.
- Affected states: all locomotion and timed channels
- Expected: a 60 Hz fixed-step simulation with render sampling/interpolation.
- Actual: `next_frame` advances exactly `1 / output_fps` once for each requested
  encoded frame.
- Visible symptom: path, gait, blink, action, and speech timing change with frame
  production and client count.
- Likely subsystem: frame source clocking
- Relevant source: `src/frame_source.rs::next_frame`
- Evidence: browser pacing and listener logs

### ANIM-GLITCH-012: The reference-avatar path drops the specified floor

- Severity: medium
- Frequency: always while reference poses are available
- Deterministic: yes
- Reproduction: render any reference pose and inspect the stage below the feet.
- Affected states: all
- Expected: fixed white background plus faint perspective checkerboard and a
  root-aligned contact shadow.
- Actual: `render_reference_stage` starts from a pure-white `CellCanvas` instead
  of `build_background`; the browser crop then removes stage context anyway.
- Visible symptom: the floor disappears or is reduced to a floating shadow,
  weakening foot contact and making sliding harder to judge.
- Likely subsystem: environment composition and browser crop
- Relevant source: `src/renderer.rs::render_reference_stage`,
  `web/wizard.js::renderFrameToAvatar`
- Evidence: all screenshots and recordings

### ANIM-GLITCH-013: Root and shadow are recomputed from unrelated offsets

- Severity: medium
- Frequency: each gait/action frame
- Deterministic: yes
- Reproduction: walk while speaking, then stop.
- Affected states: walking bob, speaking, depth, shadow
- Expected: one stable projected root; additive channels affect upper regions
  without changing foot contact.
- Actual: reference rendering adds `18 * render_scale`, walk bob, and a separate
  wall-clock speech sine to root Y, while the shadow changes shape and the
  browser recenters their combined bounds.
- Visible symptom: vertical root jitter, shadow drift, and stop/start popping.
- Likely subsystem: root locking and additive motion
- Relevant source: `src/renderer.rs::render_reference_stage`
- Evidence: locomotion and action recordings

### ANIM-GLITCH-014: Paths turn through point-to-point heading snaps

- Severity: medium
- Frequency: every circle segment, sharp path corner, and figure-eight crossover
- Deterministic: yes
- Reproduction: run clockwise, counterclockwise, and figure-eight paths.
- Affected states: turn/walk, circle direction changes, figure-eight crossover
- Expected: arc-length motion, tangent-facing steering, bounded turn rate,
  corner anticipation, and preserved gait phase.
- Actual: circles and figure-eights are polylines; target velocity changes at
  each point and facing is immediately quantized from that velocity.
- Visible symptom: direction snaps, pose flicker near boundaries, and visible
  crossover discontinuity.
- Likely subsystem: path controller, steering, and direction resolver
- Relevant source: `src/controller.rs::cmd_circle`, `cmd_figure_eight`,
  `advance_path_or_stop`, `resolve_direction_from_velocity`
- Evidence: `recordings/03-circles-figure-eight.mp4`

### ANIM-GLITCH-015: Speech adds an unsynchronized whole-root oscillation

- Severity: medium
- Frequency: every speaking or explaining state
- Deterministic: yes
- Reproduction: speak while walking and compare root motion before/during/after.
- Affected states: walk/speak, idle/explain, explain/walk
- Expected: speech drives mouth and approved upper-body offsets without changing
  planted foot contacts.
- Actual: speaking and explaining add a `sin(time_seconds * 12) * 0.7` offset to
  the entire reference root, independent of walk phase.
- Visible symptom: beat interference, vertical jitter, and a pop when speech
  starts or ends.
- Likely subsystem: additive channel masks and timing
- Relevant source: `src/renderer.rs::render_reference_stage`
- Evidence: `recordings/02-speech-actions-expressions.mp4`

### ANIM-GLITCH-016: Existing tests do not assert temporal or multi-client quality

- Severity: high
- Frequency: always in CI
- Deterministic: yes
- Reproduction: run both suites; all pass while the recordings and console show
  the defects above.
- Affected states: all
- Expected: transition continuity, root/anchor stability, fanout, reconnect,
  queue bounds, and visual-diff tests fail on these regressions.
- Actual: tests mainly prove command availability, static frame differences,
  codec round trips, and one-client WebSocket behavior.
- Visible symptom: green tests permit visibly broken animation.
- Likely subsystem: test coverage and quality gates
- Relevant source: `rust/wizard_avatar_engine/tests/`, `tests/wizard/`
- Evidence: `logs/cargo-test.txt`, `logs/python-test.txt`

## Required Transition Coverage

| Transition or invariant | Baseline result | Defects |
| --- | --- | --- |
| idle -> walk | Pops into a discrete gait pose; root/crop changes | 005, 006, 007, 013 |
| walk -> idle | Snaps to idle silhouette and loses gait momentum | 006, 008, 013 |
| walk -> turn | Instant view swap; no turn state | 006, 014 |
| turn -> walk | Enters target view without pose matching | 006, 014 |
| front -> diagonal | Full-mask snap | 006, 008, 010 |
| diagonal -> side | Full-mask snap and rigid slide | 006, 008 |
| side -> back | Full-mask snap; staff ordering changes abruptly | 006, 010 |
| forward -> backward | Heading and pose reverse without transition | 005, 006, 014 |
| clockwise circle changes | Polyline direction snaps; client-count speedup | 001, 006, 014 |
| counterclockwise circle changes | Same as clockwise | 001, 006, 014 |
| figure-eight crossover | Tangent and pose snap at crossover | 006, 014 |
| walk -> speak | Whole-root speech oscillation starts abruptly | 009, 015 |
| speak -> walk | Gesture/root oscillation ends abruptly | 009, 015 |
| idle -> explain | Upper body/staff hard switch | 009, 010 |
| explain -> walk | Timer restores idle rather than prior layered state | 009 |
| walk -> point | Staff/arm channel teleports | 009, 010 |
| point -> idle | No exit transition | 009 |
| idle -> think | Hard action swap | 009, 010 |
| think -> speak | Shared action state overwrites thinking | 009 |
| idle -> cast | Pose/effect bounds reframe the avatar | 005, 006, 010 |
| cast -> idle | Full pose snap and crop pop | 005, 006, 009 |
| reaction -> previous | Previous state is not restored | 009 |
| expression during locomotion | Overlay is not pose-anchored | 010 |
| blink during speech | Eye overlay is hard-coded and can drift | 010 |
| mouth closure after speech | Abrupt fallback to expression mouth | 009, 010 |
| staff during turning | Embedded pose staff has no blended hand anchor | 006, 010 |
| staff during arm gestures | Shared action/staff state hard switches | 009, 010 |
| depth scaling | Browser crop neutralizes server projection | 005, 011 |
| root during view changes | Server root may be stable; browser root is not | 005, 013 |
| contact shadow during locomotion | Shape and crop alter apparent contact | 005, 012, 013 |
| interruption and cancellation | Shared timers/actions cancel wrong channels | 002, 009 |
| reconnect and replay | Global encoder reset causes decoder errors | 001, 003, 004 |

## Initial Classification

- Simulation: ANIM-GLITCH-001, 011, 014
- State machine: ANIM-GLITCH-002, 009
- Pose generation: ANIM-GLITCH-006, 007, 008, 015
- Anchors: ANIM-GLITCH-005, 010, 013
- Transitions: ANIM-GLITCH-006, 009, 014, 015
- Rendering: ANIM-GLITCH-004, 005, 007, 012
- Transport: ANIM-GLITCH-001, 003, 004
- Timing: ANIM-GLITCH-001, 004, 011, 015
- Test coverage: ANIM-GLITCH-016

Every recorded defect has at least one plausible root-cause classification.
Research and planning may refine these classifications before implementation.
