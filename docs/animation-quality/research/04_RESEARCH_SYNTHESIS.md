# Animation-Quality Research Synthesis

Synthesis date: 2026-07-12  
WizardJoeAvatar revision: `codex/build-repeatable-avatar-animation` at recorded
base commit `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1`  
ASCILINE revision: `main` at
`05cc6ebd2152f5987ab348038d5619d279ecec27`

Inputs:

1. [`01_CHARACTER_ANIMATION_TRANSITIONS.md`](01_CHARACTER_ANIMATION_TRANSITIONS.md)
2. [`02_LOCOMOTION_PATHING_AND_PROJECTION.md`](02_LOCOMOTION_PATHING_AND_PROJECTION.md)
3. [`03_FRAME_PACING_ASCILINE_AND_RENDER_STABILITY.md`](03_FRAME_PACING_ASCILINE_AND_RENDER_STABILITY.md)
4. [`../00_CURRENT_STATE_AND_DEFECT_LEDGER.md`](../00_CURRENT_STATE_AND_DEFECT_LEDGER.md)

## Integrated Conclusion

The visible glitches are not one bad walk cycle. Four ownership violations
compound each other:

```text
viewer owns simulation tick        -> speed and state races
connection shares encoder history  -> invalid delta bases
pose ID owns the whole character   -> silhouette and anchor snaps
content bounds own the camera      -> root and scale popping
```

The quality pass must reverse those ownerships:

```text
one channel runtime owns semantic time and commands
one render/encoder producer owns source sequence and delta history
orthogonal animation channels own named semantic regions and anchors
one fixed projection context owns root, scale, feet, shadow, and viewport
one rAF loop owns visible browser presentation
```

Transport and clock repair must come first. Otherwise pose improvements are
measured against accelerated simulation and corrupted deltas. Pose metadata,
gait/contact motion, channel transitions, and pathing follow. Temporal browser
verification is the final gate.

## Consensus Across the Reports

All three reports agree on these non-negotiable practices:

- one authoritative fixed-step simulation, independent of viewer count and
  render FPS
- distance-driven persistent gait phase
- named anchors, semantic regions, and explicit contact markers
- root and planted-foot ownership outside additive animation layers
- independent locomotion, upper-body, staff, expression, blink, and speech
  channels
- transition snapshots from the currently presented pose, not a nominal source
  state
- one final integer-grid quantization step with stable tie breaking
- fixed stage presentation with nearest-neighbor block rendering
- bounded ordered decode and explicit keyframe recovery
- deterministic replay and temporal tests, not only static snapshots

## Resolved Design Decisions

### 1. Clock and producer topology

Adopt one 60 Hz channel simulation task and one render producer per output
profile. `frame_source::next_frame` becomes a sampler and encoder, not a clock.
WebSocket handlers subscribe and forward; they never advance state.

Use an accumulator against a monotonic clock, exact 1/60 simulation ticks, and
previous/current snapshots. A 24/30 Hz render deadline samples continuous
parameters between fixed states. Missed render deadlines are skipped; semantic
ticks are never skipped merely to keep pictures flowing.

### 2. Canonical encoding and resynchronization

Preserve existing ASCILINE codec tags and the five-byte
`[frame_index][tag][payload]` binary envelope during this pass. This retains
compatibility with the checked-out decoder and avoids mixing an animation fix
with an unnecessary wire-format migration.

Add versioned stream metadata and epoch to the text initialization/control
plane. Under this codec version, a delta's required base is exactly the prior
frame sequence in the same epoch. The browser validates contiguity before a
delta decode.

The channel producer encodes once and broadcasts immutable packets. It also
caches the latest full logical frame. A new or lagging viewer receives a
non-mutating full-frame encoding of cached sequence N, then only canonical
packets newer than N. A reconnect never clears canonical encoder history.

If a bounded broadcast receiver lags, it discards pending deltas, receives a
current full frame, and resumes. It must not skip one delta and apply later
deltas. This adapts ASCILINE's last-sent-base rule to the required encode-once
fanout architecture.

### 3. Browser queue and presentation

Use one generation-scoped decoder and two queues:

- encoded dependency queue: at most four messages or 2 MiB, with a 250 ms age
  limit; overflow enters `awaiting_keyframe`
- decoded queue: at most two complete frames; obsolete complete frames may be
  discarded

Only a continuous `requestAnimationFrame` loop commits visible output. Decode
callbacks never paint. Build each 480 by 270 logical block image into
`ImageData`, an `OffscreenCanvas`, or a detached Canvas, then perform one atomic
visible commit with smoothing disabled.

Render the fixed full stage. Remove per-frame non-white bounds, content-based
scale/centering, and independent HTTP-polled visual transforms. Semantic state
may remain visible as diagnostics but decoded ASCILINE frames are the sole
visual authority.

### 4. Simulation interpolation versus cell interpolation

Interpolate only continuous semantic values on the server: world root,
velocity, heading, and named anchor parameters. Do not interpolate finished
ASCILINE framebuffers in the browser. Do not bilinearly scale, alpha-crossfade,
or blur full silhouettes.

Discrete pose topology changes through the animation graph. Limb and staff
anchors interpolate, then rerasterize. Authored hat/beard/robe/adornment regions
use reviewed correction masks or deterministic region-local cell
correspondence. Root and planted feet never crossfade.

### 5. Pose and anchor schema

Extend the reference pose data with:

- root, pelvis, chest, head, facial, joint, foot, staff-hand, and staff-top
  anchors
- semantic region ID per cell
- left/right contact marker metadata
- explicit per-view z-order
- reviewed adjacent-direction transition corrections

The runtime must not classify anatomy by RGB or saturation. The current
`reference_walk_cell_offset` color tests are appearance heuristics, not an
animation model.

### 6. Locomotion and pathing

Use exact distance phase:

```text
walk_phase = fract(walk_phase + distance_travelled / 0.85)
```

Use braking-distance arrival, no minimum arrival speed, no-overshoot target
capture, continuous desired/presented heading, a bounded turn rate, eight-sector
hysteresis, and two-tick candidate dwell.

Represent circles analytically. Represent the figure-eight analytically with a
deterministic arc-length table. Precompute centripetal Catmull-Rom or reviewed
corner arcs for arbitrary point paths. Path tangent drives desired heading;
distance along the curve drives gait phase.

### 7. Root, depth, feet, and shadow

One `ProjectedPoseContext` owns continuous and quantized root/scale. Use
one-eighth scale levels with hysteresis and retain previous values on exact
ties. Apply at most one scale level change per rendered frame.

At gait contact, lock the planted foot in stage-cell coordinates. Compute an
integer presentation correction after projection; do not change semantic world
position. Derive contact shadow only from projected root, scale, and contact
flags. Compose the cached faint floor for reference-avatar frames instead of
starting from blank white.

### 8. Channel graph and interruption

Replace bundled global action timing with generation-safe channel states:

```text
locomotion: idle | start | walk | stop | turn
upper body: none | explain | point | think | cast | react
staff: held | point | cast | rest
expression: requested stable expression
blink: open | half | closed
speech: inactive | timed mouth schedule | interrupted
effects: inactive | cast/reaction envelope
```

Each channel owns a transition snapshot, priority, generation, expiry, and
optional restore target. Stale timers cannot complete a newer generation.
Reaction restores the prior stable upper-body/staff state. Speech does not own
root or locomotion and closes immediately on interruption.

Use short monotone/Hermite or inertialized transitions for anchors. Never apply
bounce, elastic, back/overshoot, underdamped spring, or independent wall-clock
root oscillation.

## Engine-Specific Versus Universal Guidance

### Universal control principles

- fixed authoritative time and ordered commands
- persistent phase and semantic event markers
- root/contact constraints
- orthogonal layers and explicit conflict priority
- bounded queues and known refresh points
- interpolation for presentation, never as authoritative feedback
- deterministic replay and invariants

### ASCILINE/cell-grid adaptations

- one glyph/RGB cell remains the transport atom
- anchor interpolation precedes integer rasterization
- semantic region masks replace bone masks
- Bresenham/polygon redraw replaces skeletal skinning
- region-local occupancy morph replaces whole-mesh crossfade
- nearest-neighbor `ImageData` presentation replaces antialiased Canvas glyph
  loops for the colored-block view
- sequence contiguity is the delta-base contract under the compatible envelope

### Techniques intentionally rejected

- full skeletal IK, FABRIK, CCD, skinning, quaternion blending
- animation-authored root motion driving semantic world position
- a large runtime motion-matching database
- full-frame alpha crossfades or motion blur
- subpixel CSS motion and smoothing
- prerecorded video, flattened sprites, or PNG runtime animation
- per-cell anatomy classification from color

## Defect-to-Root-Cause Synthesis

| Defect | Confirmed root cause | Class | Primary files | Required fix |
| --- | --- | --- | --- | --- |
| ANIM-GLITCH-001 | each socket ticks one shared source and divides one delta chain | simulation, transport | `server.rs`, `frame_source.rs` | central runtime and immutable fanout |
| ANIM-GLITCH-002 | every `onopen` starts a repeating semantic command tour | state race | `web/wizard.js` | explicit single-owner tour command |
| ANIM-GLITCH-003 | reconnect clears global encoder history; no targeted bootstrap | transport | `server.rs`, `frame_source.rs`, `codec.rs` | cached full bootstrap and resync state |
| ANIM-GLITCH-004 | unbounded Promise decode and decode-driven visible paint | rendering, pacing | `web/wizard.js` | bounded queues, rAF, back buffer |
| ANIM-GLITCH-005 | content bounds recompute camera plus unsequenced CSS transforms | rendering, anchors | `web/wizard.js` | fixed stage transform, frame-only visuals |
| ANIM-GLITCH-006 | quarter-cycle full-pose switches and immediate view replacement | pose, transition | `renderer.rs` | marker sampler and anchor transition |
| ANIM-GLITCH-007 | color/position heuristics plus oversized source-cell footprint | pose, raster | `renderer.rs`, `cell.rs` | semantic regions and destination raster |
| ANIM-GLITCH-008 | profile has tiny boot motion; diagonals return no gait offsets | pose | `renderer.rs`, pose data | authored directional gait/contact data |
| ANIM-GLITCH-009 | one action overwrites upper body, staff, timer, and restoration | state machine | `controller.rs`, `state.rs` | independent generation-safe channels |
| ANIM-GLITCH-010 | overlays use fixed coordinates and isolated stage cells | anchors, layers | `renderer.rs`, pose data | per-view anchors and masked layers |
| ANIM-GLITCH-011 | render demand calls simulation with fractional remainder steps | timing, simulation | `frame_source.rs`, `controller.rs` | exact 60 Hz owner plus render sampler |
| ANIM-GLITCH-012 | reference path bypasses cached floor; crop removes stage context | environment, rendering | `renderer.rs`, `web/wizard.js` | shared background compositor/full stage |
| ANIM-GLITCH-013 | root mixes scale offset, gait bob, speech sine, and crop effects | anchors, timing | `renderer.rs`, `web/wizard.js` | single root context and masked secondary motion |
| ANIM-GLITCH-014 | circle/figure-eight polylines and direct heading quantization | pathing, transition | `controller.rs` | analytical/arc-length steering |
| ANIM-GLITCH-015 | wall-clock speech sine modifies the entire root | timing, channels | `renderer.rs` | mouth/upper-body-only speech channel |
| ANIM-GLITCH-016 | tests assert existence/static differences, not temporal invariants | verification | Rust/Python/browser tests | transition, multi-client, A/B/C and soak gates |

Every ledger defect has a concrete root-cause classification and a mapped
implementation surface. No defect remains classified only as an unexplained
visual symptom.

## Ranked Work by Impact, Dependency, and Risk

| Rank | Work package | Visual impact | Dependency | Risk |
| --- | --- | --- | --- | --- |
| 1 | central clock, canonical render/encode, fanout | critical | none | high concurrency risk |
| 2 | targeted bootstrap/resync and client sequence gate | critical | 1 | high protocol/state risk |
| 3 | fixed-stage atomic browser renderer | critical | 1-2 | medium browser risk |
| 4 | A/B/C hashes and temporal test harness | enabling | 1-3 | low/medium |
| 5 | pose anchors, regions, exact cell footprint | very high | 4 | high data-authoring risk |
| 6 | persistent gait/contact and root/foot lock | very high | 5 | high visual tuning risk |
| 7 | independent channel graph/interruption | high | 5-6 | medium/high state risk |
| 8 | steering, analytical paths, depth hysteresis | high | 1, 4, 6 | medium |
| 9 | temporal goldens, browser matrix, soak | release gate | all | medium test-runtime risk |

## Source-Code Architecture Target

```text
semantic commands (tick stamped)
        |
        v
AvatarRuntime: exact 60 Hz controller + channel graph
        |
 previous/current state + transition/contact snapshots
        |
        v
RenderSampler: 24/30 Hz continuous semantic sample
        |
        v
PoseSampler: direction + gait marker + semantic anchors/regions
        |
        v
ConstraintPass: root, planted feet, staff hand, face anchors
        |
        v
CellRasterizer: ordered layers + one integer quantization
        |
        v
FixedEnvironmentCompositor: white stage + floor + shadow
        |
        v
CanonicalEncoder: one sequence/history per profile
        |
        v
Bounded Broadcast Hub ----- cached latest full logical frame
        |
        v
Per-client bootstrap/resync gate
        |
        v
Browser ordered decoder -> 2-frame complete queue -> rAF back-buffer commit
```

## Parameter Starting Points

These values are testable starting points, not final visual approval:

- simulation: 60 Hz exact ticks
- medium render: 24 FPS; high: 30 FPS
- encoded queue: 4 messages / 2 MiB / 250 ms maximum age
- decoded queue: 2 complete frames
- jitter target: 1-2 source frames
- stride length: 0.85 world units
- max walk speed: 1.25 world units/s
- acceleration/deceleration: 4.0 / 5.0 units/s^2
- arrival tolerance: 0.03-0.05; stop speed 0.05
- turn rate: 360 deg/s walking, 270 deg/s in-place
- direction hysteresis: 8 degrees plus 2-tick candidate dwell
- scale step: 1/8 with 0.10-level hysteresis
- arm/staff transition: 100-160 ms
- face/mouth transition: 60-100 ms
- hat/beard secondary settle: 120-200 ms
- periodic keyframe: retain 48 source frames initially; explicit resync handles
  known gaps immediately

## Verification Strategy

Implementation must add and pass:

1. multi-client clock/fanout tests proving viewer-count independence
2. reconnect and missing-delta recovery through the production decoder
3. rAF-only atomic fixed-stage presentation tests
4. deterministic raw/decoded/presented A/B/C cell hashes
5. gait phase, root, planted-foot, staff, and face-anchor invariants
6. every baseline transition as a short temporal sequence
7. circles/figure-eight arc-speed and tangent tests
8. 15/24/30 FPS replay parity at common simulation ticks
9. 30-minute CI and two-hour nightly queue/memory/pacing soak
10. browser compatibility across stable Chromium, Firefox, and Safari, including
    hidden/resume and context restore

Passing static frames alone is not evidence of completion. The independent
verification agent must replay the exact baseline command categories, capture
post-fix recordings/logs, and demonstrate that each defect is closed or remains
explicitly open.

## Planning Handoff

The three planning agents should divide work as follows:

1. animation graph, semantic pose schema, anchors, gait/contact, and channel
   interruption
2. fixed simulation, steering/pathing, projection, foot/root/shadow constraints,
   and deterministic replay
3. canonical fanout, resync, browser decode/presentation, instrumentation, and
   verification harness

The integration plan must reconcile their file ownership and order the work so
no pose-quality judgment occurs before clock, transport, and fixed presentation
are trustworthy.
