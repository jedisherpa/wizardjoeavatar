# Animation-Quality Implementation Report

## Earlier Python 8765 Pass

## Scope

This pass applies the existing animation-quality research and planning work to
the Python server used by the live browser demo at `http://127.0.0.1:8765/`.

The implementation preserves:

- server-authoritative semantic state
- direct ASCILINE glyph/RGB frames
- adaptive keyframe/delta WebSocket streaming
- reference pose-cell assets
- fixed white stage with faint floor marks
- crisp square-cell rendering

## Current Revision

- Branch: `codex/build-repeatable-avatar-animation`
- Pre-pass SHA recorded by implementation lead: `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1`

## Multi-Agent Inputs

Three read-only agents audited the Python `8765` path:

- Spec/repo gap audit
- Python animation runtime audit
- Independent verification audit

Their conclusions agreed that the highest-impact Python gaps were:

- render-coupled simulation clock
- hard-coded pose sampling instead of the animation graph
- no anchor-normalized pose transition compositor
- speech/action state stomping locomotion and cast channels
- missing temporal/server-hub tests

## Runtime Changes

### Graph-Backed Pose Selection

`wizard_avatar/pose_selection.py` now loads
`reference_avatar_animation_graph.json` and exposes `PoseSample` through
`select_reference_pose_sample()`.

The Python server now samples authored graph clips with the same "last sample at
or before phase" rule used by the Rust implementation.

### Canonical Pose Asset Layout

`tools/generate_reference_avatar_pose_cells.py` now normalizes every generated
reference pose into one canonical canvas after subject extraction.

Current canonical layout:

```text
cols=72
rows=96
root_anchor=(36, 95)
mouth_anchor=(36, 36)
root_anchor_strategy=fixed_canonical_root_v1
crop_strategy=per_pose_subject_crop_then_canonical_canvas_v1
```

The generated pose library is deterministic:

```text
sha256 35be1fd441b3f8a9014ea9a725512fa948e35b1b01a6413469b5a0b09eb97de2
```

### Crisp Anchor-Normalized Transitions

`wizard_avatar/pose_compositor.py` now includes
`composite_anchor_transition()`.

This aligns source and target poses by their root anchors, then performs a
deterministic hard-cell transition. It does not alpha blend, blur, or soften
cell colors.

### Explicit Simulation and Render APIs

`wizard_avatar/frame_source.py` now separates:

- `advance_simulation(seconds)`
- `render_current_frame()`
- compatibility `render_next_frame()`

`wizard_avatar/stream.py` now advances simulation explicitly in the authoritative
hub before rendering and encoding the current frame.

### Stable Reference Root

Reference root placement no longer includes speech sine bob. Speech changes
mouth cells only and does not move the body/root/contact placement.

### Speech Channel Isolation

`wizard_avatar/controller.py` no longer uses global `_set_action("speaking")`
for speech commands. Speech owns `speech_id`, `speech_until`, and mouth state,
while preserving active locomotion and active cast/staff channels.

### Reaction Interruption Restore

Reaction now snapshots the previous active action channel and restores it when
the reaction timer expires, provided the previous action is still valid. This
keeps temporary reactions from dropping an active cast/staff state to idle.

### Adjacent Facing Steps

Velocity-driven facing changes now step one adjacent compass sector at a time
through `step_direction_towards()`. Explicit face commands remain direct
semantic commands.

## Tests Added or Updated

- `tests/wizard/test_animation_channels.py`
- `tests/wizard/test_crisp_pose_transition.py`
- `tests/wizard/test_direction_transitions.py`
- `tests/wizard/test_reference_overlays.py`
- `tests/wizard/test_stream_hub.py`
- `tests/wizard/test_pose_selection.py`
- `tests/wizard/test_visuals.py`
- `tests/wizard/test_reference_avatar_pose_library.py`
- `tools/verify_animation_quality.py`

## Verification

Local Python suite:

```text
python3 -m unittest discover tests
Ran 52 tests in 13.250s
OK
```

Rust verification also passed after regenerating the shared pose JSON:

```text
cargo fmt --check
cargo test
```

Live server:

```text
http://127.0.0.1:8765/
PID 78523
```

Latest live PID after reaction-restore restart:

```text
PID 23987
```

Live WebSocket smoke:

```text
INIT:24.0:5:240:135:0:0:0.000
tags [3, 2, 2, 2, 2, 2]
decoded frame size 129600
four clients received identical contiguous frame indices
state elapsed 0.25s over 0.24s wall time
```

Transition matrix:

```text
python3 tools/verify_animation_quality.py --strict
scenario_count 30
passed_count 30
issue_count 0
```

Artifacts:

- `evidence/animation-quality/final/transition-matrix-8765.json`
- `evidence/animation-quality/final/TRANSITION_MATRIX_8765.md`

Live channel smoke:

```text
speech during walking: locomotion remained walking
speech expired: speech_id became null
post-speech locomotion remained walking
server reset after smoke
```

## Earlier Python Pass Remaining Work

This pass materially improves the Python `8765` runtime, but the complete
animation-quality program still has larger remaining work:

- canonicalize every reference pose to one reviewed crop/root/region schema
- add stable region IDs and contact markers to every generated cell
- replace path polyline circles/figure-eights with arc-length analytical paths
- add full temporal transition-matrix recordings under final evidence
- add browser A/B/C source/decoded/presented hash capture
- add long-duration soak and cross-browser evidence

## Rust Waves 0-5 Implementation

### Scope and Revision

This section records the authoritative Rust implementation under
`rust/wizard_avatar_engine` and its directly served browser client. Waves 0-5
are summarized here; Wave 6 evidence and final results are recorded below and
in `06_FINAL_VERIFICATION_EVIDENCE.md`.

- Branch: `codex/build-repeatable-avatar-animation`
- Recorded pre-pass SHA: `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1`
- Simulation: one central `AvatarRuntime`, exact 60 Hz ticks
- Rendering: one canonical 24 Hz producer
- Presentation: fixed 480x270 ASCILINE cell stage, visible commits on rAF only

### Wave 1 Clock Fidelity Closure

`SimulationAccumulator` consumes measured wall-clock `Duration` values and
emits only whole 1/60-second simulation steps. `run_runtime` no longer uses a
Tokio interval with Burst behavior. Catch-up is bounded to eight steps per
poll (`MAX_CATCH_UP_STEPS`); excess wall time is counted as dropped time rather
than producing an unbounded fast-forward. Commands scheduled for a tick are
applied in deterministic arrival order before that tick advances.

Render sampling remains a separate 24 Hz consumer and cannot advance the
runtime. Tests cover irregular wall-time chunks without drift, bounded
catch-up, exact tick deltas, deterministic same-tick command order, and
0/1/2/4/8-viewer independence.

### Wave 3: Semantic Pose Schema and Rasterization

- Added checked Rust pose schema version 2 with 25 required named anchors,
  including root/contact, feet, hands, head/face/mouth, staff, and effect
  origins.
- Every loaded occupied cell receives an explicit semantic `RegionId`, stable
  cell ID, and deterministic z-order. Enrichment uses named-anchor geometry,
  never RGB or saturation classification, and validates all eight views.
- Direction transitions present one complete coherent source or target pose at
  a time. Arbitrary region-cell correspondence was removed after final evidence
  exposed silhouette tearing between views with different topology. Gait and
  channel offsets remain continuous; glyphs, RGB values, framebuffers, and
  palette indices are never blended.
- Removed oversized `ceil(scale) + 1` rasterization. The renderer uses one
  destination-driven `blit_scaled` footprint.
- Face, mouth, brows, staff gestures, magic, and reactions are all placed from
  pose anchors. No overlay uses a fixed stage coordinate.

### Wave 4: Gait, Steering, Paths, Projection, and Contact

- Replaced pose-slot walking with a distance-driven continuous gait phase and
  eight contact markers covering stance, toe-off, passing, and heel strike for
  alternating feet.
- Added acceleration, braking-distance deceleration, no-overshoot arrival,
  lateral/diagonal stride differentiation, turn anticipation, shortest-arc
  facing, adjacent-view changes, hysteresis, and two-tick direction dwell.
- Added analytical arc-length circles, a deterministic arc-length
  figure-eight lookup, and Catmull-Rom spline traversal. Curves expose tangent
  facing and exact loop endpoints; arbitrary paths begin at current position.
- Added one persistent projection/contact context with one-eighth scale levels,
  hysteresis, one-level-per-frame changes, planted-foot correction bounded to
  one cell per frame and two cells total, and a contact-owned shadow.
- Projection and cached white/faint-floor composition share fixed horizon and
  floor ratios. The bounded depth scale keeps the complete 96-row pose and
  staff effect inside the fixed 270-row stage.

### Focused Visual Gait Refinement

The four-quarter gait was refined after regenerated snapshots showed boots
moving beneath an almost rigid silhouette. The revision changes placement only;
glyphs, RGB values, stage, floor, square-cell rasterization, and character
proportions are unchanged.

- `ContactRoot` remains the fixed projection origin while the visual root,
  pelvis, torso, and shoulders compress during support, rise during passing,
  and transfer weight toward the stance side.
- Robe and inner-robe cells are split into semantic left/right panels. Hem
  opening increases through passing and heel strike, follows the active leg,
  and settles in support instead of retaining a rectangular baseline.
- Contact-aligned foot curves now use explicit front, lateral, and diagonal
  stride vectors. Swing feet gain toe clearance and reach; stance legs read
  compressed between the moving pelvis and planted boot.
- The free arm swings opposite gait phase while the staff arm follows the body.
  Staff cells interpolate from an exact hand attachment toward a damped tip,
  keeping the shaft stable without freezing the upper body.
- Head, hat, beard, face, and mouth use a delayed low-amplitude counter-motion
  rather than sharing the torso offset.
- Gait amplitude uses smooth zero-to-one `speed_ratio`; the previous minimum
  35% walking amplitude was removed, eliminating idle/walk boundary jumps.
- Direction-specific pose stride now supplies almost all planted-foot lock.
  Projection correction is a residual capped at two cells, so it cannot grow
  until it cancels visible world translation.

New deterministic gates require at least three cells of support-to-passing root
rise, four cells of robe-width opening, five horizontal/two vertical cells of
free-arm reversal, two cells of swing-boot clearance, distinct front/side/
diagonal stride vectors, monotonic speed-ratio amplitude, exact staff grip, and
damped staff-tip travel. A three-cycle projection test requires at least 150
stage cells of root progress while each stance foot remains locally bounded.

### Wave 5: Independent Animation Channels

- Added generation-scoped channels for upper body/action, staff, expression,
  speech/mouth, and effects, plus independent locomotion, facing, and blink
  generations/state.
- New commands replace only their owned channel generations. Stale expiry
  cannot cancel a replacement; reaction captures and restores prior upper-body
  and staff targets.
- Speech and gestures overlay locomotion without resetting walk phase. Cast
  owns upper-body/staff/effect regions, while expression, blink, and mouth stay
  anchored to face masks.
- Base pose selection now depends only on facing. Gait and actions are semantic
  region transforms rather than hard full-pose switches.

### Browser Generation and Procedural-Only Surface

- `requestResync`, generation reset, and invalidation now clear the complete
  two-frame presentation queue as well as encoded/decode state.
- The live page contains no `<img>`, PNG reference, reference DOM overlay, or
  duplicate CSS avatar animation. `web/reference-avatar.png` was removed.
- The stream remains the shared adaptive ASCILINE codec path with bounded,
  generation-scoped ordered decode and rAF-only complete-frame presentation.
- Connection open updates diagnostics only; the motion tour requires explicit
  user action.

### Changed Files for the Rust Continuation

Core implementation:

- `rust/wizard_avatar_engine/src/animation.rs`
- `rust/wizard_avatar_engine/src/cell.rs`
- `rust/wizard_avatar_engine/src/controller.rs`
- `rust/wizard_avatar_engine/src/frame_source.rs`
- `rust/wizard_avatar_engine/src/hub.rs`
- `rust/wizard_avatar_engine/src/lib.rs`
- `rust/wizard_avatar_engine/src/pathing.rs`
- `rust/wizard_avatar_engine/src/pose.rs`
- `rust/wizard_avatar_engine/src/projection.rs`
- `rust/wizard_avatar_engine/src/reference_avatar.rs`
- `rust/wizard_avatar_engine/src/renderer.rs`
- `rust/wizard_avatar_engine/src/runtime.rs`
- `rust/wizard_avatar_engine/src/state.rs`

Focused tests:

- `rust/wizard_avatar_engine/tests/animation_graph.rs`
- `rust/wizard_avatar_engine/tests/animation_transitions.rs`
- `rust/wizard_avatar_engine/tests/fixed_clock.rs`
- `rust/wizard_avatar_engine/tests/path_continuity.rs`
- `rust/wizard_avatar_engine/tests/pose_metadata.rs`
- `rust/wizard_avatar_engine/tests/projection_contact.rs`
- `rust/wizard_avatar_engine/tests/rust_objective_contract.rs`
- regenerated `evidence/wizard/rust-snapshots/`

Browser surface:

- `rust/wizard_avatar_engine/web/asciline_client.js`
- `rust/wizard_avatar_engine/web/index.html`
- `rust/wizard_avatar_engine/web/tests/codec_queue.test.mjs`
- removed `rust/wizard_avatar_engine/web/reference-avatar.png`
- `docs/animation-quality/05_IMPLEMENTATION_REPORT.md`

Wave 0-2 files retained from the immediately preceding Rust pass include the
codec/hub/server, canonical fanout and WebSocket tests, shared browser codec,
fixed renderer, rAF client, and browser renderer tests.

### Verification

```text
cargo fmt --check
PASS

cargo test
PASS: 57 Rust tests, 0 failed

cargo clippy --all-targets -- -D warnings
PASS

cargo run --bin wizard-avatar-snapshots
PASS: regenerated manifest, README, and 30 PPM snapshots

node --test web/tests/*.test.mjs
PASS: 16 tests, 0 failed

source-only grep for <img>, .png, reference-avatar, avatar-reference
PASS: no matches

filesystem assertion for web/reference-avatar.png
PASS: absent

live server smoke at http://127.0.0.1:8792/
PASS: HTTP state, INIT epoch metadata, binary ASCILINE keyframe,
walking + speech + cast overlap, reset to idle
```

The focused Rust tests cover schema/anchor validation, distinct complete
samples in all eight directions, anchor continuity, action replacement and
reaction restoration, speech/action/locomotion overlap, direction hysteresis
and shortest-arc turn, exact circle/figure-eight closure, spline endpoint
continuity, scale hysteresis, continuous correction, and actual planted-foot
stage-cell lock. The focused visual gait tests additionally cover semantic
quarter silhouettes, anchor/region extents, speed-ratio ramping, stride axes,
staff stabilization, and multi-cycle root progression.

### Wave 6 Final Evidence

- Added a serialized deterministic replay manifest covering 36 defect-ledger
  transitions. Two exact 60 Hz runs sampled at exact rational 24 Hz produced
  identical semantic hash `1f8db3d09f8d495f` and raw-frame hash
  `69d2f9e4e8a39288` across 1,008 frames.
- Added Rust source, production adaptive encode/decode, and shipped browser
  queue/renderer A/B/C parity. All 52 vectors match and cover existing ASCILINE
  tags 0/1/2/3 without changing the five-byte envelope.
- Produced four MP4 recordings, four contact sheets, final frame sequences,
  state/event logs, transition jump metrics, codec hashes, and an integrity
  manifest under `evidence/animation-quality/final/`.
- Added malformed-frame, resync, hidden/resume, context-restore, stale
  generation, and bounded ordered-decode browser module tests.
- Added a wall-clock soak runner for 0/1/2/4/8 viewers with deadline, FPS,
  continuity, queue, canonical-hash, lag, and RSS metrics. The 15-second short
  run passed; 30-minute CI and two-hour nightly modes are configured.
- Added an exhaustive adjacent-facing coherence regression over 136 blend
  samples. It rejects missing regions, cell-count collapse, component
  explosion, excessive fragmentation, and detached head/staff/root anchors.
- Regenerated 30 snapshots and performance evidence. The fast demo completed
  123 frames at 23.7 FPS; the full demo completed 1,023 frames at 24.0 FPS.

### Remaining Limits

- The production Chromium surface was verified interactively at desktop and
  mobile sizes with a clean console, live adaptive WebSocket frames, and
  repeat-until-Stop playback. Cross-browser, device-pixel-ratio, and long-run
  compositor timing coverage remain outside this pass.
- The configured 30-minute CI and two-hour nightly soaks were not run during
  this interactive pass.
- Direction interpolation intentionally uses a coherent whole-pose handoff at
  the blend midpoint. It does not synthesize in-between cell topology.

The semantic schema-v2 cells are deterministically enriched and validated by
Rust from the existing editable pose-cell asset and named anchors. Baking those
semantic IDs back into the shared generator/JSON is outside this Rust-owned
pass and is not required by the runtime.
