# Locomotion, Pathing, and Projection

Research date: 2026-07-12  
WizardJoeAvatar branch: `codex/build-repeatable-avatar-animation`  
Recorded base commit: `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1`  
ASCILINE revision: `external/ASCILINE` `main` at
`05cc6ebd2152f5987ab348038d5619d279ecec27`

This report completes research track 2. Two assigned locomotion research agents
were used, but neither emitted the required artifact after bounded conclude
requests. The integration lead therefore completed this report from the shared
baseline, exact Rust source, the two completed peer research reports, and the
authoritative sources cited below. No runtime code was modified.

## Executive Conclusion

The current movement is jerky for three independent reasons:

1. **Clock ownership is wrong.** Every WebSocket viewer asks the shared source
   to advance simulation by `1 / render_fps`; viewer count therefore changes
   path speed, gait speed, blink timing, and action timing.
2. **Steering is point-reactive.** Paths are sampled into waypoints and the
   controller repeatedly aims at the next point with no curvature, tangent,
   turn-rate, or arc-length state. Facing is immediately quantized from the
   resulting velocity.
3. **Presentation destroys projection continuity.** The server quantizes depth
   scale, then the browser independently crops, rescales, and recenters the
   changing silhouette every frame.

The correct model is one deterministic 60 Hz semantic simulation, a separate
24/30 Hz render sampler, distance-driven gait phase, braking-distance arrival,
continuous heading with an eight-sector Schmitt trigger, analytical or
arc-length-parameterized paths, and one final integer projection/foot-lock pass.
The browser must present the fixed full stage and must not recompute the camera
from content bounds.

## Source Applicability

The recommendations use these established controls rather than importing a
mesh locomotion system:

- Glenn Fiedler's accumulator loop separates a fixed simulation step from
  variable rendering and bounds catch-up work
  ([Fix Your Timestep](https://gafferongames.com/post/fix_your_timestep/)).
- Godot's official physics interpolation stores previous/current transforms and
  interpolates only for presentation
  ([Godot physics interpolation](https://docs.godotengine.org/en/stable/tutorials/physics/interpolation/physics_interpolation_introduction.html)).
- Craig Reynolds' steering model separates desired velocity from bounded
  steering acceleration and defines arrival/path-following behavior
  ([Steering Behaviors For Autonomous Characters, GDC 1999](https://www.red3d.com/cwr/steer/gdc99/)).
- Unreal's Distance Matching advances locomotion from distance rather than
  elapsed animation time, especially for starts and stops
  ([Unreal Distance Matching](https://dev.epicgames.com/documentation/en-us/unreal-engine/distance-matching-in-unreal-engine)).
- Unreal Sync Groups and markers preserve shared gait events across related
  motions
  ([Unreal Animation Sync Groups](https://dev.epicgames.com/documentation/unreal-engine/animation-sync-groups-in-unreal-engine?lang=en-US)).
- Centripetal Catmull-Rom parameterization avoids the cusps and self-intersections
  possible with uniform parameterization
  ([Yuksel, Schaefer, and Keyser, 2011](https://www.cemyuksel.com/research/catmullrom_param/)).
- Planted-foot constraints are the transferable part of motion-capture footskate
  cleanup
  ([Kovar, Schreiner, and Gleicher, 2002](https://graphics.cs.wisc.edu/Papers/2002/KSG02/cleanup.pdf)).

## 1. Why the Current Movement Looks Jerky

### Clock and integration defects

`frame_source.rs::next_frame` calls `controller.advance(1.0 / fps)` every time
any viewer requests a frame. `controller.rs::advance` subdivides that interval
using `min(SIMULATION_DT, remaining)`, but at 24 FPS this produces two 1/60
steps plus one 1/120 remainder. It is not a strict 60 Hz tick sequence. With N
viewers, it repeats N times as fast. This is `ANIM-GLITCH-001` and `011`.

### Steering and arrival defects

`move_toward_target` aims directly at the current target. Near the target it
scales speed by `max(dist / 0.45, 0.25)`, so desired speed never reaches zero.
The target snap prevents an infinite orbit in common cases, but the residual
minimum speed and abrupt waypoint replacement create a visible acceleration
and heading discontinuity. Circle and figure-eight commands merely generate
48/96 point polylines, so every point boundary is a small corner. This is
`ANIM-GLITCH-014`.

### Direction and pose defects

Velocity is mapped immediately to one of eight directions. Hysteresis reduces
boundary chatter, but there is no continuous presented heading, turn-rate
limit, pending sector, or contact-aligned direction transition. The renderer
then selects an unrelated full pose mask. This couples steering discontinuity
to `ANIM-GLITCH-006` and `008`.

### Projection and browser defects

Depth scale changes in one-eighth steps, which is appropriate for a cell grid,
but the client ignores the fixed stage transform. It derives a new tight content
box and centers it at 90% occupancy every frame. Server root motion and depth
therefore appear as size/center pops instead of travel. This is
`ANIM-GLITCH-005`, `012`, and `013`.

## 2. Simulation, Rendering, or Both?

| Symptom | Simulation contribution | Rendering/presentation contribution | Defects |
| --- | --- | --- | --- |
| Speed changes with viewers | per-client simulation advance | browser exposes aggregate cadence | 001, 011 |
| Start/stop snap | action/locomotion state changes immediately | hard pose slot and crop switch | 006, 009, 013 |
| Foot sliding | no contact state or foot lock | side/diagonal poses translate rigidly | 008, 013 |
| Direction snap | immediate velocity quantization | unrelated view masks switch | 006, 014 |
| Circle/figure-eight jitter | waypoint tangent discontinuities | pose/crop amplifies each sector change | 005, 006, 014 |
| Depth popping | scale quantized without hysteresis | dynamic crop defeats projection | 005, 013 |
| Shadow drift | no explicit contact data | shadow and character use unstable bounds/root offsets | 005, 012, 013 |
| Torn/ghost frame | global delta-base corruption | unbounded decode and non-atomic presentation | 001, 003, 004 |

Movement quality cannot be judged until the clock/fanout and fixed presentation
are repaired. After that, raw source-frame hashes distinguish the remaining
steering/pose defects from transport defects as specified in research report 3.

## 3. Separating 60 Hz Simulation from Render FPS

One channel task owns the simulation accumulator:

```text
SIM_DT = 1 / 60
MAX_ACCUMULATED = 0.25 seconds

on monotonic wake(now):
    elapsed = clamp(now - previous_now, 0, MAX_ACCUMULATED)
    accumulator += elapsed
    previous_now = now

    while accumulator >= SIM_DT:
        previous_state = current_state
        apply_tick_stamped_commands(tick + 1)
        simulate_exact_tick(current_state, SIM_DT)
        tick += 1
        accumulator -= SIM_DT

    alpha = accumulator / SIM_DT
```

Render tasks sample that channel at their own deadlines:

```text
render_state.continuous = lerp(previous_state, current_state, alpha)
render_state.discrete = current_state.discrete_transition_state
render_state.tick = current_state.tick
render_cells(render_state)
```

The render task does not advance simulation. WebSocket tasks subscribe to
rendered frames and never call `advance`. If a render deadline is missed, render
the newest state and count a missed render; do not run simulation faster to
manufacture old pictures.

Code mapping:

- Replace caller-driven time in `frame_source.rs::next_frame`.
- Keep exact-tick logic in `controller.rs`, changing `advance(seconds)` to
  `step_tick()` or requiring exact multiples of `SIMULATION_DT`.
- Add a central channel/runtime task in `server.rs` or a new `runtime.rs`.
- Store `simulation_tick: u64`, previous/current snapshots, render sequence,
  and presentation timestamp.

This directly fixes `ANIM-GLITCH-001`, `011`, and the timing part of `016`.

## 4. Preserving Walk Phase as Speed or Direction Changes

Gait phase belongs to traveled root distance:

```text
ds = length(world_position_next - world_position_previous)
walk_phase = fract(walk_phase + ds / stride_length)
```

Use the current `stride_length = 0.85` world units initially. Do not reset phase
when speed, path segment, direction, expression, speech, or upper-body action
changes. Directional pose samplers share these contact markers:

```text
0.00 left contact
0.25 left passing / right support
0.50 right contact
0.75 right passing / left support
```

For a large turn, keep phase running from distance and change the presented view
only through adjacent sectors. Align source and target poses to the same contact
marker and planted-foot identity. For a normal stop, begin deceleration
immediately but settle the pose at the next contact marker, bounded to four
simulation ticks. For an emergency stop, lock the currently planted foot and
inertialize only non-contact regions.

Speed changes affect stride *frequency* through distance traveled, not animation
amplitude. Pose stride amplitude can be warped from normalized speed with a
bounded monotone function, for example:

```text
speed_ratio = clamp(speed / nominal_walk_speed, 0, 1.25)
stride_amplitude = smoothstep(0, 1, speed_ratio)
```

Do not advance phase from wall time while stationary. This implements the
distance-matching principle without a skeletal animation clip.

Code mapping: retain phase update in `controller.rs::step_locomotion`; replace
`renderer.rs::walking_pose_id` with a marker-aware pose sampler; add contact and
pending-turn state. Fixes `ANIM-GLITCH-006`, `008`, and `014`.

## 5. Preventing Oscillation at a Target

Use braking-distance arrival rather than a permanent minimum speed:

```text
to_target = target - position
distance = length(to_target)
direction = normalize_or_zero(to_target)
braking_speed = sqrt(2 * deceleration * max(distance - tolerance, 0))
desired_speed = min(max_speed, braking_speed)
desired_velocity = direction * desired_speed

velocity = move_towards(
    velocity,
    desired_velocity,
    acceleration_or_deceleration * dt
)
```

Use acceleration when desired speed exceeds current speed and deceleration
otherwise. Then enforce a no-overshoot rule:

```text
step = velocity * dt
if dot(to_target, step) >= squared_length(to_target)
   or (distance <= tolerance and speed <= stop_speed):
    position = target
    velocity = 0
    advance_path_or_stop_once()
```

Recommended starting parameters at 60 Hz:

- max walk speed: 1.25 world units/s
- acceleration: 4.0 units/s^2
- deceleration: 5.0 units/s^2
- arrival tolerance: 0.03-0.05 world units
- stop speed: 0.05 world units/s
- no nonzero minimum arrival speed

Store a path-segment generation/index and advance it once, so a stale command or
second completion cannot re-enter the old segment. This prevents oscillation,
overshoot, and repeated stop/start state changes.

## 6. Preventing Facing-Direction Flicker

Maintain two headings:

- `desired_heading`: continuous angle from steering/tangent velocity
- `presented_heading`: rate-limited continuous angle used by view selection

Update with shortest-angle motion:

```text
error = wrap_pi(desired_heading - presented_heading)
max_delta = turn_rate * dt
presented_heading += clamp(error, -max_delta, max_delta)
```

Start with a 360 degree/s maximum while walking and 270 degree/s for deliberate
in-place turns. Select the eight-direction sector through a Schmitt trigger:

- nominal sector half-width: 22.5 degrees
- retain current sector until heading crosses boundary plus 8 degrees
- require the candidate sector for two consecutive simulation ticks
- when speed is below 0.08 world units/s, preserve the previous facing unless an
  explicit face command owns the turn

Only adjacent sectors may become presented on one tick. A 180 degree reversal
therefore passes through reviewed intermediate directions rather than replacing
front with back. Gait phase and foot contact stay unchanged.

Code mapping: replace direct assignment in
`controller.rs::resolve_direction_from_velocity` with heading/sector state;
expose pending/presented direction to the animation graph. Fixes
`ANIM-GLITCH-006`, `008`, and `014`.

## 7. Coherent Circles and Figure-Eight Motion

### Circle

Do not approximate a commanded circle with a waypoint polygon. Maintain an
analytical path state:

```text
angular_speed = linear_speed / radius
theta += direction_sign * angular_speed * dt
x = center_x + radius * cos(theta)
z = center_z + radius * sin(theta)
tangent = direction_sign * (-sin(theta), cos(theta))
desired_heading = atan2(tangent.x, -tangent.z)
```

Accumulate traveled arc distance as `abs(delta_theta) * radius`, which drives
gait phase exactly. Stop after the requested signed arc length, not after a
rounded waypoint count.

### Figure eight

Use a continuous analytical curve, for example a Gerono lemniscate:

```text
x(theta) = center_x + radius * sin(theta)
z(theta) = center_z + radius * sin(theta) * cos(theta)

dx/dtheta = radius * cos(theta)
dz/dtheta = radius * cos(2 * theta)
```

Parameter speed is not spatially uniform. Build a deterministic arc-length
lookup table when the command is accepted:

```text
samples = 512
table[0] = (0, 0)
for i in 1..samples:
    theta_i = TAU * i / samples
    table[i].s = table[i-1].s + distance(p(theta_i), p(theta_i-1))

distance_along += speed * dt
theta = binary_search_and_lerp(table, distance_along)
```

The tangent derivative supplies facing through the same rate-limited heading
controller. At the crossover, position and tangent remain continuous; only the
eight-direction presentation sector may change under hysteresis.

### Arbitrary paths

For user points, precompute a centripetal Catmull-Rom curve or reviewed corner
arcs, then build the same arc-length table. Clamp/control endpoint tangents and
reject any sampled envelope that violates world/stage bounds. Path data is
created once per command, not each frame.

Code mapping: replace polyline generation in `cmd_circle` and
`cmd_figure_eight`; extend `PathState` with curve kind, distance, arc-length
table, and tangent. Fixes `ANIM-GLITCH-014` and stabilizes `006`/`008`.

## 8. Stabilizing Depth Scaling

Project continuous world state once on the server. Interpolate world position
between fixed simulation snapshots at the render deadline, then compute
continuous `screen_x`, `screen_y`, and scale. Quantize only at the final cell
presentation boundary.

For the required one-eighth scale steps, use hysteresis around the current
quantized level:

```text
step = 1 / 8
current_level = display_scale / step
continuous_level = projected_scale / step

if continuous_level > current_level + 0.5 + hysteresis:
    current_level += 1
else if continuous_level < current_level - 0.5 - hysteresis:
    current_level -= 1

display_scale = current_level * step
```

Start with `hysteresis = 0.10` scale levels (0.0125 absolute scale). Permit at
most one level change per render frame. Break exact boundary ties by retaining
the previous level. Record scale-level changes for tests.

Root screen cells use the same previous-cell tie rule. Do not independently
round the root, shadow, foot anchors, overlays, and staff in different spaces.
All consume one `ProjectedPoseContext` containing the continuous projection and
final quantized root/scale.

Most importantly, remove `web/wizard.js::renderFrameToAvatar` content-bound
cropping. Render the full fixed 16:9 stage, or one authored constant viewport
that encloses every legal world position and effect. Browser layout may scale
that fixed rectangle, with smoothing off, but may never derive it from current
non-white cells.

This fixes the projection portion of `ANIM-GLITCH-005`, `012`, and `013`.

## 9. Preserving Feet and Contact Shadow on the Floor

Each gait marker declares foot contact. On contact entry, store the planted
boot's stage cell. After projection and pose sampling, compute:

```text
predicted_foot = quantize(root + local_foot_anchor * scale)
foot_correction = planted_stage_cell - predicted_foot
```

Apply this integer correction to the local presentation pose, not to semantic
`world_position`. In double support, choose the correction minimizing weighted
L1 error to both feet, with deterministic previous-correction tie breaking.
Never let upper-body, speech, expression, or staff channels modify this
correction.

The contact shadow uses only:

- projected root/floor point
- quantized scale
- left/right contact flags
- configured grounded/lifted widths

It must not derive its position from current silhouette bounds. Compose the
cached faint perspective floor first, then shadow, then the anchored character.
The reference-avatar renderer currently starts from pure white instead of
`build_background`; correct that composition before judging foot contact.

Code mapping: add contact state to animation/controller runtime; pass one
projection context into `render_reference_stage` and `draw_contact_shadow`;
remove speech/root coupling. Fixes `ANIM-GLITCH-008`, `012`, `013`, and `015`.

## 10. Easing Functions by Transition Type

Easing is not one global curve. Use the smallest rule that preserves the
physical or semantic invariant.

| Transition | Recommended rule | Starting duration/parameter |
| --- | --- | --- |
| World acceleration | bounded velocity approach | 4.0 units/s^2 |
| World deceleration/arrival | braking-speed rule | 5.0 units/s^2; no fixed duration |
| Continuous heading | shortest-angle rate limit, optionally critically damped | 360 deg/s walk, 270 deg/s in-place |
| Gait phase | linear in traveled distance | stride 0.85 world units |
| Start/stop pose amplitude | `smoothstep(0,1,t)` aligned to contact | 100-180 ms |
| Adjacent direction anchors | cubic Hermite / critically damped, monotone | 100-160 ms |
| Interrupted arm/staff | inertialized cubic Hermite residual | 100-160 ms |
| Hat/beard follow-through | critically damped secondary parameter | 120-200 ms |
| Face/mouth | short monotone smoothstep; blink uses authored timings | 60-100 ms |
| Depth scale | one-eighth Schmitt quantizer | no post-quantization easing |
| Shadow width | derive from contact; monotone one-cell schedule | one contact transition |

For a critically damped scalar parameter with target `x_t`, use a stable
closed-form or fixed-step implementation of:

```text
y = x - x_t
y'' + 2 * omega * y' + omega^2 * y = 0
```

Choose `omega` from the desired settling time and integrate only on exact 60 Hz
ticks. Do not apply the spring to authoritative root position; world movement
uses bounded acceleration/braking. Use it for presented heading and secondary
anchors where velocity continuity matters.

## 11. Easing Functions That Should Not Be Used

Reject these for locomotion and contact-critical transitions:

- elastic, bounce, back/overshoot, or underdamped springs
- independent sinusoidal root bob not keyed to gait phase
- exponential ease that approaches the target forever without a deterministic
  completion condition
- generic smoothstep applied to world distance, which produces speed unrelated
  to acceleration limits or path arc length
- whole-frame alpha crossfade, bilinear interpolation, motion blur, or subpixel
  CSS transforms
- post-quantization smoothing of cell positions or scale
- per-frame random noise and wall-clock oscillators

These either overshoot contacts, produce target oscillation, break deterministic
completion, or hide discontinuities instead of correcting anchors.

## 12. Keeping the System Deterministic

Use these invariants:

1. All semantic commands receive a target simulation tick and generation.
2. One ordered command queue is consumed by one simulation owner.
3. Simulation time is `tick * SIM_DT`; renderer code never reads wall clock.
4. Gait phase derives from deterministic traveled distance.
5. Blink/effect randomness uses a serialized seeded generator.
6. Path/arc-length tables use fixed sample counts and stable iteration order.
7. Do not use hash-map iteration to choose cells, collisions, or ties.
8. Quantize once with previous-value tie breaking.
9. Render sequence and simulation tick are explicit protocol metadata.
10. Replay records command tick, payload, seed, profile, and initial state.
11. Presentation interpolation never feeds back into simulation.
12. Viewer count and render FPS cannot call simulation code.

For cross-platform golden hashes, prefer integer/fixed-point storage for tick,
phase accumulator, path distance, and quantized projection thresholds where
practical. If `f32` remains, define compiler/platform scope for bit-exact hashes
and separately assert invariant tolerances before final cell quantization.

## Concrete Data and Code Changes Recommended

This is research guidance, not implementation.

### State/runtime additions

```text
SimulationClock {
    tick: u64,
    accumulator_seconds: f64,
    previous_state: WizardState,
    current_state: WizardState,
}

LocomotionState {
    mode: Idle | Starting | Walking | Stopping | Turning,
    desired_velocity: Velocity,
    desired_heading: f32,
    presented_heading: f32,
    presented_direction: Direction,
    candidate_direction: Option<Direction>,
    candidate_ticks: u8,
    gait_phase: f32,
    contact: FootContactState,
}

PathState {
    generation: u64,
    curve: PathCurve,
    distance_along: f32,
    total_length: f32,
    arc_table: Vec<ArcSample>,
    looped: bool,
}

ProjectedPoseContext {
    continuous_root: (f32, f32),
    quantized_root: (i32, i32),
    continuous_scale: f32,
    quantized_scale: f32,
    foot_correction: (i32, i32),
}
```

### File/function mapping

| File/function | Required change | Defects |
| --- | --- | --- |
| `controller.rs::advance` | exact tick step, no fractional remainder | 001, 011 |
| `controller.rs::move_toward_target` | braking-distance arrival and no-overshoot | 014 |
| `resolve_direction_from_velocity` | continuous heading, rate limit, Schmitt sectors | 006, 008, 014 |
| `cmd_circle`, `cmd_figure_eight` | analytical/arc-length path state | 014 |
| `PathState` | curve distance/tangent/generation | 009, 014 |
| `frame_source.rs::next_frame` | sample state, never advance it | 001, 011 |
| `renderer.rs::project_quantized` | stateful scale/root hysteresis context | 005, 013 |
| `render_reference_stage` | one projection/root context and cached floor | 005, 012, 013, 015 |
| `draw_contact_shadow` | contact-driven dimensions and same root | 008, 012, 013 |
| `web/wizard.js::renderFrameToAvatar` | fixed full-stage viewport | 005 |

## Recommended Deterministic Tests

### Clock and locomotion

- `WIZ-LOCO-001`: 0/1/2/8 viewers produce identical tick, position, velocity,
  gait phase, and expiry state for one command log.
- `WIZ-LOCO-002`: common simulation ticks are identical when rendered at 15,
  24, and 30 FPS.
- `WIZ-LOCO-003`: every integration step is exactly 1/60 second; no fractional
  render remainder enters simulation.
- `WIZ-LOCO-004`: equal traveled distance produces equal gait phase across
  acceleration profiles and direction changes.

### Arrival and steering

- `WIZ-STEER-001`: target approach never crosses the target plane and enters
  tolerance once.
- `WIZ-STEER-002`: speed is exactly zero after arrival and remains zero for 600
  ticks.
- `WIZ-STEER-003`: heading change per tick never exceeds turn-rate bound.
- `WIZ-STEER-004`: oscillating desired headings inside boundary hysteresis do
  not change presented direction.
- `WIZ-STEER-005`: a 180 degree reversal visits only adjacent sectors while
  preserving gait phase and planted-foot identity.

### Paths

- `WIZ-PATH-001`: clockwise and counterclockwise circles have constant spatial
  speed and tangent-facing error below one degree before direction quantization.
- `WIZ-PATH-002`: one circle ends at the start within 0.01 world units and with
  expected traveled arc length.
- `WIZ-PATH-003`: figure-eight crossover has continuous position and tangent;
  no zero-speed or direction spike.
- `WIZ-PATH-004`: arbitrary path arc-length error remains below 0.5% at the
  configured table resolution.
- `WIZ-PATH-005`: cancellation increments generation; old segment completion
  cannot resume movement.

### Projection/contact

- `WIZ-PROJ-001`: stationary depth near a quantizer threshold cannot alternate
  scale levels.
- `WIZ-PROJ-002`: monotone depth travel produces monotone scale-level changes,
  at most one step per render frame.
- `WIZ-PROJ-003`: view, expression, mouth, staff, and effects cannot change the
  fixed viewport, root, or scale for fixed world state.
- `WIZ-CONTACT-001`: a planted foot remains on exactly one stage cell through
  start, stop, adjacent turn, speech, and gesture overlays.
- `WIZ-CONTACT-002`: contact shadow center matches projected root in all phases;
  width changes only from declared contact state.

### Replay and visual sequences

- Replay the full baseline transition matrix twice and require identical
  semantic snapshots and raw cell-frame hashes by tick.
- Record 12 frames before/after every direction and path-boundary transition;
  assert root jump 0, planted-foot jump 0, staff-hand jump at most one cell
  during transition and 0 at completion.
- Compare raw source, browser-decoded, and logical presented cell hashes so a
  steering failure cannot be confused with codec/presentation corruption.

## Recommended Implementation Order

1. Central simulation/render clock and multi-client fanout.
2. Fixed browser stage presentation and A/B/C frame hashing.
3. Braking-distance arrival plus generation-safe path cancellation.
4. Continuous heading, turn-rate, and sector hysteresis.
5. Analytical circle and arc-length figure-eight/path sampling.
6. Shared gait markers, foot contact, and integer root/foot lock.
7. Stateful depth/root quantization and contact-driven shadow.
8. Temporal and deterministic verification across every baseline sequence.

## Sources

- Glenn Fiedler, “Fix Your Timestep”:
  <https://gafferongames.com/post/fix_your_timestep/>
- Godot Engine, Physics Interpolation:
  <https://docs.godotengine.org/en/stable/tutorials/physics/interpolation/physics_interpolation_introduction.html>
- Craig Reynolds, “Steering Behaviors For Autonomous Characters,” GDC 1999:
  <https://www.red3d.com/cwr/steer/gdc99/>
- Unreal Engine, Distance Matching:
  <https://dev.epicgames.com/documentation/en-us/unreal-engine/distance-matching-in-unreal-engine>
- Unreal Engine, Animation Sync Groups:
  <https://dev.epicgames.com/documentation/unreal-engine/animation-sync-groups-in-unreal-engine?lang=en-US>
- Cem Yuksel, Scott Schaefer, and John Keyser, “Parameterization and
  Applications of Catmull-Rom Curves,” 2011:
  <https://www.cemyuksel.com/research/catmullrom_param/>
- Lucas Kovar, John Schreiner, and Michael Gleicher, “Footskate Cleanup for
  Motion Capture Editing,” SCA 2002:
  <https://graphics.cs.wisc.edu/Papers/2002/KSG02/cleanup.pdf>
- Andrew Witkin and David Baraff, “Physically Based Modeling,” SIGGRAPH course
  notes (damped systems and numerical integration):
  <https://www.cs.cmu.edu/~baraff/sigcourse/>
- J. E. Bresenham, “Algorithm for Computer Control of a Digital Plotter,” IBM
  Systems Journal 1965: <https://doi.org/10.1147/sj.41.0025>
- RFC 3550, sequence/timestamp/jitter model:
  <https://www.rfc-editor.org/rfc/rfc3550.html>
