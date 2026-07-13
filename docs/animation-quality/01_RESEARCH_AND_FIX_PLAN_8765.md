# Animation Research and Fix Plan for the Live 8765 Avatar

Date: 2026-07-12  
Primary live runtime for this pass: `http://127.0.0.1:8765/`  
Repo: `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar`  
Branch: `codex/build-repeatable-avatar-animation`

## Why This Plan Exists

The user clarified that the work must build from the repo-backed live avatar at
`http://127.0.0.1:8765/`, not from a standalone generated image sequence. That
matters because `8765` is currently the Python/TypeScript demo surface:

- `tools/run_wizard_avatar_server.py` starts the server.
- `wizard_avatar/server.py` serves `/`, `/avatar/*`, semantic command routes,
  and `/ws/avatar/wizard?codec=adaptive`.
- `wizard_avatar/frame_source.py` generates authoritative ASCILINE cell frames.
- `web/avatar/wizardClient.ts` decodes WebSocket frames.
- `web/avatar/wizardCanvas.ts` draws square cells on Canvas.

The Rust engine under `rust/wizard_avatar_engine/` is still important, but for
this pass it is the parity and migration target. The current visual complaint
must be fixed in the live `8765` path first, then mirrored into Rust.

## Agent Process

Three research agents investigated current best practices and this repo:

1. Animation/state design: animation graphs, transitions, blend trees, root and
   foot continuity, pose popping, action channels.
2. Browser/canvas/streaming: WebSocket decode ordering, requestAnimationFrame
   pacing, frame queues, pixel-cell crispness, Canvas hot paths.
3. Rust/data pipeline: shared pose assets, fixed simulation with interpolated
   presentation, Rust caches, parity tests, temporal metrics.

Three planning agents converted those reports into implementation plans:

1. Python authoritative renderer and controller plan.
2. Browser/WebSocket/canvas smoothness plan.
3. Rust parity, repeatable asset generation, and temporal verification plan.

This document consolidates their findings into one implementation roadmap.

## Source Research

These are the outside sources that should shape the implementation:

- [MDN requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame):
  rAF runs at display refresh rate, including 60, 75, 120, and 144 Hz, and
  animation progress must be based on the timestamp rather than assuming one
  callback equals one fixed animation step.
- [MDN Optimizing canvas](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Optimizing_canvas):
  Canvas animation should minimize per-frame work, avoid unnecessary state
  changes, and consider pre-rendering/offscreen work for repeated drawing.
- [MDN imageSmoothingEnabled](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/imageSmoothingEnabled):
  Canvas smoothing must stay disabled for enlarged pixel or square-cell art.
- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API):
  classic WebSocket delivery needs app-level queueing/backpressure behavior for
  real-time animation streams.
- [Unity Animation Transitions](https://docs.unity3d.com/6000.5/Documentation/Manual/class-Transition.html):
  state-to-state animation changes should have explicit transition durations,
  conditions, and controlled interruption behavior.
- [Unity Blend Trees](https://docs.unity3d.com/6000.5/Documentation/Manual/class-BlendTree.html):
  locomotion blends work best when similar clips align in normalized time, such
  as left-foot and right-foot contact points.
- [Godot AnimationTree](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html):
  animation trees model animation selection/blending as data instead of scattered
  one-off conditionals.
- [Bevy fixed timestep example](https://bevy.org/examples/movement/physics-in-fixed-timestep/):
  fixed simulation and visual presentation should be separated, with presentation
  interpolation smoothing the rendered output.
- [Bevy AnimationTransitions](https://docs.rs/bevy/latest/bevy/animation/transition/struct.AnimationTransitions.html):
  transition state belongs in the animation layer, not as immediate clip
  replacement.
- [Rust OnceLock](https://doc.rust-lang.org/std/sync/struct.OnceLock.html):
  Rust can safely cache decoded/generated reference assets once for the process.
- [Playwright visual comparisons](https://playwright.dev/docs/test-snapshots):
  browser snapshots are useful but must be paired with temporal metrics for this
  class of animation bug.

## Repo-Specific Diagnosis

### Primary Live-Path Problems

1. `wizard_avatar/frame_source.py` uses the polished reference avatar only when
   `state.facing == "south"`. Other facings fall back to the procedural avatar.
   A turn can therefore swap art systems, dimensions, anchors, scale, silhouette,
   and background behavior in one frame.

2. `wizard_avatar/reference_avatar.py` only loads
   `wizard_avatar/definitions/reference_avatar_cells.json`. The newer generated
   multi-pose library at
   `wizard_avatar/definitions/reference_avatar_pose_cells.json` exists but is
   not consumed by the live Python renderer.

3. `assets/reference/motion_sources/manifest.json` contains useful pose inputs:
   `front_idle`, `back_idle`, `profile_left`, `profile_right`,
   `walk_front_left`, `walk_front_right`, `back_left`, `back_right`,
   `explaining`, and `magic_cast`. The live `8765` route currently returns 404
   for `/avatar/reference-avatar-pose-cells.json`.

4. `wizard_avatar/controller.py` changes `action`, `upper_body_action`,
   `staff_state`, and `facing` immediately. There is no transition state, no
   foot-plant gating, and no renderer-visible enter/exit progress.

5. `docs/23-animation-channels.md` already says the avatar must have independent
   channels for locomotion, upper body, face, speech, and staff. The code still
   treats `action` as too much of a single mutually exclusive switch.

6. `web/avatar/wizardClient.ts` decodes WebSocket messages asynchronously. Delta
   frames depend on the previous decoded frame, so decode work must be serialized.

7. `web/avatar/wizardClient.ts` draws one queued frame per rAF callback. A
   24 FPS source can be consumed at 60, 120, or 144 Hz, or jitter with delivery
   timing, because presentation is not scheduled by `targetFps` and timestamp.

8. `wizard_avatar/server.py` resets and advances a shared `frame_source` inside
   each WebSocket connection. That violates `docs/26-asciline-frame-source.md`,
   which calls for one encoded frame per channel and fanout to viewers.

9. `web/avatar/wizardCanvas.ts` mutates a large hidden `<pre>` every frame, which
   is unnecessary hot-path DOM pressure for the normal animated view.

10. `docs/00-goal-and-visual-contract.md` says the character has no wings, while
    `assets/reference/README.md` and the supplied later reference poses include
    rainbow wings. This contradiction must be resolved before polishing final
    silhouettes and region metadata.

### Rust Parity Problems

1. Rust already embeds `reference_avatar_pose_cells.json`, but
   `rust/wizard_avatar_engine/src/renderer.rs` hard-switches pose IDs.

2. Rust walking uses phase buckets like `floor(walk_phase * 4)`, causing pose
   snaps rather than graph-based sampling or phase-preserving blends.

3. Rust has color-classified walk offsets that infer wings, staff, and feet from
   RGB/saturation. That is fragile and tears the character during gait.

4. Rust WebSocket handling must also avoid per-client simulation advancement.
   Each client should have its own encoder history, but one authoritative
   controller/render tick.

## Implementation Plan

### Phase 0: Freeze the Correct Baseline

Files and tools:

- `tools/run_wizard_avatar_server.py`
- `wizard_avatar/server.py`
- `wizard_avatar/frame_source.py`
- `web/avatar/wizardClient.ts`
- `web/avatar/wizardCanvas.ts`
- `tools/measure_animation_temporal_quality.py` to be added later

Steps:

1. Capture `http://127.0.0.1:8765/api/avatar/wizard/state`.
2. Capture the WebSocket `INIT` message and first keyframe metadata.
3. Record short frame sequences for idle, face all directions, walking, explain,
   cast, speak while walking, circle, and reconnect.
4. Measure current frame cadence, decode errors, changed-cell spikes, root
   movement, and bounding-box deltas.

Acceptance:

- Evidence proves the current `8765` defects before fixes.
- The report distinguishes Python live-runtime defects from older Rust `8787`
  baseline defects.

### Phase 1: Reconcile the Visual Contract

Files:

- `docs/00-goal-and-visual-contract.md`
- `assets/reference/README.md`
- `assets/reference/motion_sources/manifest.json`
- `wizard_avatar/definitions/reference_avatar_pose_cells.json`

Steps:

1. Decide whether this avatar includes rainbow wings.
2. Update the visual contract and reference README so they agree.
3. If wings remain, model them as explicit pose regions and animation regions.
4. If wings are removed, regenerate source poses and cell masks without wing
   regions.

Acceptance:

- One source of truth defines the character silhouette.
- Future transition tests do not fail because one doc says wings are forbidden
  while the runtime assets include them.

### Phase 2: Make the Pose Library Real and Repeatable

Files:

- `tools/generate_reference_avatar_cells.py`
- `tools/generate_reference_avatar_pose_cells.py`
- `assets/reference/motion_sources/manifest.json`
- `wizard_avatar/definitions/reference_avatar_pose_cells.schema.json`
- `wizard_avatar/definitions/reference_avatar_pose_cells.json`
- `wizard_avatar/definitions/reference_avatar_animation_graph.schema.json`
- `wizard_avatar/definitions/reference_avatar_animation_graph.json`

Steps:

1. Add schema version 2 for `reference_avatar_pose_cells.json`.
2. Extend the manifest with canonical metadata:
   - `asset_set_id`
   - canonical `cols`, `rows`, `root_anchor`, `baseline_y`
   - shared `palette_id` or palette hash
   - per-pose `facing`, `locomotion`, `phase`, `tags`
   - per-pose anchors: `root`, `mouth`, `left_eye`, `right_eye`,
     `left_foot`, `right_foot`, `staff_tip`, `staff_hand`, and hand anchors
   - optional per-cell `region`
3. Generate every pose into the same canonical local grid. Do not independently
   crop and center each source image.
4. Use one shared palette for all poses.
5. Add `--check-deterministic` that generates twice and compares SHA-256.

Acceptance:

- All poses have identical `cols`, `rows`, `root_anchor`, and palette hash.
- Regeneration is deterministic.
- Runtime consumes JSON only. PNGs remain source assets, not runtime animation.

### Phase 3: Teach Python to Use the Pose Library

Files:

- `wizard_avatar/reference_avatar.py`
- `wizard_avatar/pose_selection.py` to be added
- `wizard_avatar/pose_compositor.py` to be added
- `wizard_avatar/frame_source.py`
- `wizard_avatar/server.py`

Steps:

1. Add `REFERENCE_POSE_CELL_PATH`.
2. Add cached loaders:
   - `reference_pose_library_available()`
   - `load_reference_pose_library()`
   - `reference_pose_ids()`
   - `get_reference_pose(pose_id)`
   - `render_reference_pose_local(pose_id)`
3. Serve `/avatar/reference-avatar-pose-cells.json` from the live Python server
   for diagnostics and parity checks.
4. Keep `render_reference_avatar_local()` as a compatibility wrapper around
   `front_idle`.
5. Add pose selection from semantic state:
   - front idle: `south`
   - back idle: `north`
   - profile poses: `east`, `west`
   - back diagonals: `northeast`, `northwest`
   - front diagonals: front-family poses until dedicated diagonal poses exist
   - walk front: `walk_front_left` and `walk_front_right` by normalized gait
     phase
   - walk back: `back_left`, `back_idle`, `back_right` until a better back walk
     clip is authored
   - explain and cast: upper body/staff channels select `explaining` and
     `magic_cast` without overwriting speech or locomotion

Acceptance:

- No live-render path branches on "south gets reference, others get procedural".
- `8765` can render all current pose IDs from the pose JSON.
- Missing pose cases degrade through explicit graph fallbacks, not art-system
  swaps.

### Phase 4: Add Animation State and Crisp Pose Transitions

Files:

- `wizard_avatar/models.py`
- `wizard_avatar/controller.py`
- `wizard_avatar/locomotion.py`
- `wizard_avatar/frame_source.py`
- `wizard_avatar/pose_selection.py`
- `wizard_avatar/pose_compositor.py`
- `wizard_avatar/layers.py`
- `wizard_avatar/skeleton.py`

Steps:

1. Add transition state to `WizardState`:
   - `render_facing`
   - `desired_facing`
   - `pending_facing`
   - `ChannelTransition`
   - `facing_transition`
   - `upper_body_transition`
   - `staff_transition`
   - `pose_transition`
   - `last_pose_id`
   - `root_screen_position`
2. Keep public command fields compatible, but render from the transition-aware
   values.
3. Change `_cmd_face()` to request a facing instead of replacing it instantly.
4. Gate walking-facing changes near foot plants, roughly phase `0.0` or `0.5`.
5. Change `_set_action()` so upper-body and staff states transition without
   clearing locomotion or speech unless explicitly requested.
6. Compute one root screen location for all poses. Remove the special reference
   path offset `sy + 18 * render_scale`.
7. Add `composite_crisp_transition(from_pose, to_pose, progress)`.
8. For crisp square cells, use deterministic cell ownership or coverage
   thresholds. Do not blur the rendered cells. For any RGB interpolation, quantize
   back to the shared palette and assert no soft edges are introduced.
9. Use a monotonic Bayer/hash mask for one-sided cells so cells do not flicker
   back and forth during a transition.

Acceptance:

- Facing changes do not move root/contact shadow by more than one cell when
  world position is unchanged.
- Walking, speaking, explaining, blinking, and staff state can coexist.
- Transition frames preserve hard square cells.
- No action is a single mega-enum that prevents layered animation.

### Phase 5: Fix Browser and WebSocket Presentation

Files:

- `wizard_avatar/server.py`
- `wizard_avatar/stream.py` to be added
- `wizard_avatar/protocol.py`
- `wizard_avatar/diagnostics.py`
- `web/avatar/wizardClient.ts`
- `web/avatar/wizardCodec.ts`
- `web/avatar/wizardCanvas.ts`
- `web/avatar/wizardDiagnostics.ts`
- `web/avatar/wizardDemo.ts`
- `web/avatar/style.css`

Steps:

1. Add `WizardFrameHub` and `WizardSubscriber`.
2. The hub owns one authoritative ticker and one shared frame source.
3. Each client gets a bounded subscriber queue.
4. New clients receive `INIT` plus a non-delta keyframe without resetting the
   global stream.
5. Add `encode_keyframe(frame.cells, frame.frame_index)`.
6. A slow subscriber overflow clears queued deltas and receives a fresh keyframe.
7. `reset` forces the next outbound frame to be a keyframe for all subscribers
   instead of resetting shared encoder state inside one connection.
8. Serialize browser decode with a raw message queue and one decode pump.
9. Add `parseFrameHeader()` and `isKeyframeTag()` to `wizardCodec.ts`.
10. On delta decode failure, reset browser decode state, request `resync`, and
    ignore deltas until a full-frame tag arrives.
11. Present frames by `targetFps` and rAF timestamp:
    - wait for a small jitter buffer
    - draw only when `now >= nextPresentationAt`
    - hold the last frame on underflow
    - drop old decoded frames on backlog
12. Resize Canvas to integer device-pixel cell multiples:
    - `deviceCell = floor(min(innerWidth * dpr / cols, innerHeight * dpr / rows))`
    - backing width is `cols * deviceCell`
    - backing height is `rows * deviceCell`
    - CSS size is backing size divided by DPR
13. Keep `imageSmoothingEnabled = false` after every resize.
14. Draw into an offscreen/back buffer and copy atomically to the visible canvas.
15. Render same-color horizontal runs per row to reduce draw calls.
16. Disable or throttle the hidden `<pre>` text sync to at most 2 Hz.
17. Expose browser metrics through `window.__wizardJoeMetrics()` and
    `window.__wizardJoeCanvas()`.

Acceptance:

- One client and four clients advance the server state at the same rate.
- Presented FPS is near target FPS, not monitor refresh rate.
- Decode errors are zero during a 60 second run.
- Canvas cells remain crisp after resize and on high-DPR displays.
- Diagnostics show bounded queues, frame drops, held frames, decode errors,
  resync count, canvas device cell size, and DPR.

### Phase 6: Mirror the Same Model in Rust

Files:

- `rust/wizard_avatar_engine/src/reference_avatar.rs`
- `rust/wizard_avatar_engine/src/animation.rs` to be added
- `rust/wizard_avatar_engine/src/renderer.rs`
- `rust/wizard_avatar_engine/src/frame_source.rs`
- `rust/wizard_avatar_engine/src/server.rs`
- `rust/wizard_avatar_engine/src/lib.rs`
- `rust/wizard_avatar_engine/web/wizard.js`

Steps:

1. Parse schema v2 pose JSON and animation graph JSON.
2. Add `ReferencePoseCache` using `OnceLock`.
3. Build pose canvases once, not every frame.
4. Add `AnimationPresentationState`.
5. Keep controller physics fixed-step and deterministic; put visual transitions
   in presentation state.
6. Replace hard `walking_pose_id` buckets with graph clip sampling.
7. Preserve normalized gait phase when switching walk directions.
8. Remove or quarantine `reference_walk_cell_offset`.
9. Drive offsets only from explicit generated `region` metadata.
10. Anchor blink, mouth, expression, magic, and gesture overlays to generated
    pose anchors rather than fixed local coordinates.
11. Rust server gets one authoritative frame producer and per-client encoder
    histories.
12. Rust browser should not recenter/crop the avatar every frame; server-rendered
    cells remain authoritative.
13. Disable automatic tours unless the user explicitly starts them.

Acceptance:

- Python and Rust select the same clips for all facing/action/locomotion
  combinations.
- Rust tests prove pose cache initialization is one-time.
- No visible gait behavior depends on color heuristics.
- Multi-client Rust streaming does not speed up the simulation.

### Phase 7: Temporal Verification, Not Just Snapshots

Files:

- `tools/measure_animation_temporal_quality.py` to be added
- `tests/wizard/test_reference_avatar_pose_library.py` to be added
- `tests/wizard/test_pose_selection.py` to be added
- `tests/wizard/test_animation_channels.py` to be added
- `tests/wizard/test_anchor_continuity.py` to be added
- `tests/wizard/test_crisp_pose_transition.py` to be added
- `tests/wizard/test_stream_hub.py` to be added
- `rust/wizard_avatar_engine/tests/reference_pose_library.rs` to be added
- `rust/wizard_avatar_engine/tests/animation_graph.rs` to be added
- `evidence/animation-quality/fixed/`

Test and evidence requirements:

1. Pose library tests:
   - schema validates
   - all graph pose IDs exist
   - all required anchors exist
   - all poses share canonical size, root, and palette hash
   - generation is deterministic
2. Pose selection tests:
   - all eight facings select explicit pose or graph fallback
   - walk phase samples are phase-continuous
   - speech never replaces the body pose
3. Channel tests:
   - walk plus speak
   - walk plus explain
   - walk plus cast
   - expression plus blink plus speech
4. Anchor tests:
   - root and contact shadow move less than or equal to one cell across an idle
     facing transition
   - overlay anchors stay attached across all facings
5. Browser tests:
   - serialized decode with artificial slow inflate
   - reconnect receives keyframe
   - two browser pages do not double simulation time
   - presented FPS is close to target
   - Canvas backing size is an integer multiple of the cell grid
6. Temporal metrics:
   - `decode_error_count == 0`
   - `multi_client_time_scale` is `1.00 +/- 0.05`
   - idle root jitter is `<= 1 cell`
   - adjacent non-command silhouette spike is `<= 3x` rolling median
   - no unblended pose ID jump during walking
   - no frame crop-driven scale reset in browser capture

Acceptance:

- Static snapshots are not enough.
- The fixed evidence package must include temporal metrics, contact sheets,
  before/after clips, Python and Rust test logs, and live `8765` state evidence.

## Recommended Implementation Order

1. Reconcile the visual contract.
2. Normalize and version the pose asset pipeline.
3. Load the pose library in Python and serve it from `8765`.
4. Unify Python render path around selected poses and stable roots.
5. Add channel transition state and crisp pose transitions.
6. Fix WebSocket fanout and browser frame presentation.
7. Port the same schema, graph, and transition rules to Rust.
8. Add temporal verification and publish `evidence/animation-quality/fixed/`.

This order keeps the live demo useful after each wave. It also avoids hiding
server/render defects behind browser-only smoothing.

