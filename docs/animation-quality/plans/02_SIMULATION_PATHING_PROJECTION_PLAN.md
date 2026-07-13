# Simulation, Pathing, and Projection Implementation Plan

## Objective

Create one deterministic fixed-step runtime, replace waypoint-reactive steering
with continuous path/tangent control, and make one projection/contact context own
root, depth scale, feet, shadow, and fixed environment composition.

Primary defects: `ANIM-GLITCH-001`, `005`, `008`, `011` through `015`.

## File Ownership

Create:

- `rust/wizard_avatar_engine/src/runtime.rs`
- `rust/wizard_avatar_engine/src/pathing.rs`
- `rust/wizard_avatar_engine/src/projection.rs`
- `rust/wizard_avatar_engine/src/replay.rs`
- `rust/wizard_avatar_engine/tests/fixed_clock.rs`
- `rust/wizard_avatar_engine/tests/path_continuity.rs`
- `rust/wizard_avatar_engine/tests/projection_contact.rs`
- `rust/wizard_avatar_engine/tests/replay_determinism.rs`

Modify:

- `rust/wizard_avatar_engine/src/lib.rs`
- `rust/wizard_avatar_engine/src/main.rs`
- `rust/wizard_avatar_engine/src/state.rs`
- `rust/wizard_avatar_engine/src/controller.rs`
- `rust/wizard_avatar_engine/src/frame_source.rs`
- `rust/wizard_avatar_engine/src/geometry.rs`
- `rust/wizard_avatar_engine/src/renderer.rs`
- `rust/wizard_avatar_engine/src/server.rs`

Plan 1 owns pose/channel semantics. Plan 3 owns fanout, client protocol state,
browser queues/presentation, and live E2E.

## Runtime Types

```rust
pub const SIM_HZ: u32 = 60;
pub const SIM_DT: f32 = 1.0 / SIM_HZ as f32;

pub struct SimulationClock {
    pub tick: u64,
    pub accumulator: Duration,
    pub previous_wall: Instant,
    pub max_accumulated: Duration,
}

pub struct StatePair {
    pub previous: WizardState,
    pub current: WizardState,
}

pub struct AvatarRuntime {
    pub clock: SimulationClock,
    pub controller: WizardAvatarController,
    pub states: StatePair,
    pub commands: VecDeque<ScheduledCommand>,
    pub replay: ReplayRecorder,
}

pub struct ScheduledCommand {
    pub apply_tick: u64,
    pub generation: u64,
    pub command: WizardCommand,
}
```

All semantic timers become ticks, not floating wall-clock deadlines. Keep
human-readable seconds in public diagnostics as `tick / 60.0`.

## Central Clock Loop

```rust
async fn run_simulation(runtime: Arc<RwLock<AvatarRuntime>>) {
    let mut wake = interval(Duration::from_millis(4));
    wake.set_missed_tick_behavior(MissedTickBehavior::Skip);

    loop {
        wake.tick().await;
        let now = Instant::now();
        let mut rt = runtime.write().await;
        let elapsed = now.duration_since(rt.clock.previous_wall)
            .min(rt.clock.max_accumulated);
        rt.clock.previous_wall = now;
        rt.clock.accumulator += elapsed;

        let mut catch_up = 0;
        while rt.clock.accumulator >= SIM_DT_DURATION && catch_up < 8 {
            rt.states.previous = rt.states.current.clone();
            rt.apply_commands_for_next_tick();
            rt.controller.step_tick();
            rt.clock.tick += 1;
            rt.states.current = rt.controller.current_state().clone();
            rt.clock.accumulator -= SIM_DT_DURATION;
            catch_up += 1;
        }
        rt.record_clock_metrics(catch_up);
    }
}
```

Never call simulation from `next_frame`, a render deadline, or a socket task.
`WizardAvatarController::advance(seconds)` becomes `step_tick()` and executes
exactly one `SIM_DT` step. Tests prohibit fractional integration steps.

## Render Sampling Interface

```rust
pub struct SimulationSample {
    pub tick: u64,
    pub alpha: f32,
    pub previous: WizardState,
    pub current: WizardState,
}

impl AvatarRuntime {
    pub fn sample(&self) -> SimulationSample {
        SimulationSample {
            tick: self.clock.tick,
            alpha: self.clock.accumulator.as_secs_f32() / SIM_DT,
            previous: self.states.previous.clone(),
            current: self.states.current.clone(),
        }
    }
}
```

`frame_source` interpolates continuous world/anchor values using `alpha`, keeps
discrete graph/contact state from the deterministic animation runtime, then
renders. Presentation state never feeds back into the controller.

## Movement State and Arrival

```rust
pub struct MovementState {
    pub target: Option<WorldPoint>,
    pub max_speed: f32,
    pub acceleration: f32,
    pub deceleration: f32,
    pub arrival_tolerance: f32,
    pub stop_speed: f32,
    pub desired_velocity: Velocity,
    pub desired_heading: f32,
    pub presented_heading: f32,
    pub candidate_direction: Option<Direction>,
    pub candidate_ticks: u8,
}
```

Use:

```rust
fn step_arrival(state: &mut WizardState, movement: &mut MovementState) {
    let to_target = target - state.world_position;
    let distance = to_target.length();
    let braking = (2.0 * movement.deceleration
        * (distance - movement.arrival_tolerance).max(0.0)).sqrt();
    let desired_speed = movement.max_speed.min(braking);
    movement.desired_velocity = to_target.normalized_or_zero() * desired_speed;

    let rate = if desired_speed < state.velocity.length() {
        movement.deceleration
    } else {
        movement.acceleration
    };
    state.velocity = move_towards(
        state.velocity,
        movement.desired_velocity,
        rate * SIM_DT,
    );

    let step = state.velocity * SIM_DT;
    if step.crosses(to_target)
        || (distance <= movement.arrival_tolerance
            && state.velocity.length() <= movement.stop_speed)
    {
        state.world_position = target;
        state.velocity = Velocity::ZERO;
        advance_path_or_stop_once();
    } else {
        state.world_position += step;
    }
}
```

Parameters: speed 1.25, acceleration 4.0, deceleration 5.0,
tolerance 0.03-0.05, stop speed 0.05. Remove the current 0.25 minimum arrival
speed.

## Heading and Direction Resolver

```rust
pub struct HeadingPolicy {
    pub walking_turn_rate: f32, // radians/s, 2*PI
    pub inplace_turn_rate: f32, // radians/s, 1.5*PI
    pub hysteresis: f32,        // 8 degrees
    pub minimum_facing_speed: f32, // 0.08
    pub candidate_dwell_ticks: u8, // 2
}

fn step_heading(m: &mut MovementState, desired: f32, policy: HeadingPolicy) {
    let error = wrap_pi(desired - m.presented_heading);
    let max_delta = policy.walking_turn_rate * SIM_DT;
    m.presented_heading = wrap_pi(
        m.presented_heading + error.clamp(-max_delta, max_delta)
    );
    update_direction_schmitt_trigger(m, policy);
}
```

Preserve facing below minimum speed unless an explicit face command owns an
in-place turn. Only adjacent sectors become presented in one transition.
Direction changes never reset gait phase/contact.

## Path Types

```rust
pub enum PathCurve {
    PointArrival { target: WorldPoint },
    Circle(CirclePath),
    FigureEight(FigureEightPath),
    Spline(SplinePath),
}

pub struct PathState {
    pub generation: u64,
    pub curve: Option<PathCurve>,
    pub distance_along: f32,
    pub total_length: f32,
    pub speed: f32,
    pub looped: bool,
}

pub struct ArcSample {
    pub distance: f32,
    pub parameter: f32,
    pub position: WorldPoint,
    pub tangent: Velocity,
}
```

### Circle

Store center/radius/signed angle. Advance angle by `speed/radius * dt`.
Position and tangent are analytical. Gait distance is `abs(delta_angle)*radius`.

### Figure eight

Use Gerono equations from research report 2 and a 512-sample deterministic
arc-length table. Advance `distance_along += speed * dt`; binary-search the
table and interpolate parameter. Tangent derives from the analytical derivative.

### Arbitrary point path

Build a centripetal Catmull-Rom curve with explicit endpoint policy and a
deterministic arc-length table when the command is accepted. Validate the
sampled character envelope against world/stage bounds once. Do not regenerate
curve points per frame.

Cancellation increments `PathState::generation`, clears curve/target once, and
prevents stale segment completion from resuming movement.

## Gait Distance Contract

After each semantic world step:

```rust
let travelled = distance(before, after);
animation.walk_phase = fract(animation.walk_phase + travelled / 0.85);
animation.contact_marker = ContactMarker::from_phase(animation.walk_phase);
```

Plan 1 consumes the marker. Path parameter/time never drives gait directly.

## Projection Types

```rust
pub struct ProjectionHistory {
    pub scale_level: i16,
    pub root_cell: Point,
}

pub struct ProjectedPoseContext {
    pub continuous_root: PointF,
    pub quantized_root: Point,
    pub continuous_scale: f32,
    pub quantized_scale: f32,
    pub foot_correction: Point,
    pub horizon_y: f32,
    pub floor_y: f32,
}
```

`project_world_to_screen` stays pure and continuous. New
`ProjectionHistory::quantize` applies one-eighth scale levels with 0.10-level
hysteresis, one level maximum change per rendered frame, and previous-value tie
breaking. Root, body, overlays, feet, staff, and shadow all consume the same
context.

## Foot Contact Solver

```rust
pub struct FootContact {
    pub planted: bool,
    pub planted_stage_cell: Option<Point>,
    pub entered_tick: u64,
}

pub struct FootContactState {
    pub left: FootContact,
    pub right: FootContact,
    pub previous_correction: Point,
}

fn solve_contact(
    pose: &PoseSnapshot,
    projection: &ProjectedPoseContext,
    contacts: &FootContactState,
) -> Point
```

At contact entry, store the current stage boot cell. While planted, correction
is stored minus predicted boot cell. In double support, minimize weighted L1
error to both contacts and use previous correction on ties. Correction is a
presentation offset; world position remains authoritative.

## Environment and Shadow

- Cache `build_background` by grid/profile.
- `render_reference_stage` starts from that cached background.
- Shadow center comes from quantized projected root plus foot correction.
- Shadow width/narrowing comes only from left/right contact flags.
- Speech, gesture, expression, staff, silhouette, and effects cannot alter
  floor, shadow center, root, or projection scale.

## Replay Format

```rust
pub struct ReplayHeader {
    pub schema_version: u16,
    pub initial_state: WizardState,
    pub seed: u64,
    pub profile: RenderProfile,
}

pub struct ReplayCommand {
    pub tick: u64,
    pub generation: u64,
    pub command: WizardCommand,
}
```

Replay records no wall-clock times. Serialize ordered commands and seed. Expose
an offline runner that emits semantic hashes and raw cell hashes by tick/render
sequence for Plan 3 A/B/C comparison.

## Migration Steps

1. Add runtime/replay types and exact `step_tick`; retain old caller behind an
   internal compatibility adapter.
2. Start one central runtime task; make existing frame source sample it.
3. Add viewer-count and 15/24/30 FPS parity tests before removing adapter.
4. Replace arrival and direction resolver.
5. Add path generation/state and migrate move/path/circle/figure-eight commands.
6. Add projection history/context and fixed environment composition.
7. Add contact solver interface consumed by Plan 1 poses.
8. Remove old polyline helpers, fractional `advance`, per-frame projection
   recomputation paths, and reference blank-background path.
9. Enable replay/golden temporal evidence.

## Diagnostics

Expose:

- simulation tick, accumulator, catch-up steps, deadline misses
- command queue depth and applied generation
- position/velocity/desired velocity/speed/braking distance
- desired/presented heading, direction candidate/dwell
- path kind/generation/distance/total/tangent/arc lookup error
- gait phase/contact marker and traveled distance
- continuous/quantized root and scale level/change count
- planted foot cells, correction, and shadow center/width
- replay/state/source-frame hashes

## Tests and Acceptance

- 0/1/2/8 viewers yield identical simulation state and action expiry
- all integration steps are exactly 1/60 second
- common simulation ticks match under 15/24/30 render FPS
- target approach never overshoots or re-enters movement
- direction changes obey max turn rate, hysteresis, dwell, and adjacency
- gait phase equals distance/stride across all paths and speed changes
- circles have constant spatial speed and tangent-facing continuity
- figure-eight crossover has continuous position/tangent and no speed spike
- arbitrary path arc-length error below 0.5%
- cancellation generation blocks stale resume
- depth scale cannot chatter at threshold and changes monotonically with depth
- root and planted foot remain exact through every baseline view/action change
- shadow follows root/contact only
- two replays produce identical semantic and raw-cell hashes

Required IDs: `WIZ-LOCO-*`, `WIZ-STEER-*`, `WIZ-PATH-*`, `WIZ-PROJ-*`, and
`WIZ-CONTACT-*` from research report 2.

## Completion Gate

This track is complete only when simulation state is viewer/render independent,
all path families are continuous and distance-driven, direction presentation is
bounded and hysteretic, and projection/root/foot/shadow invariants pass through
the production renderer.
