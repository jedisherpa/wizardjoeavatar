# Animation Graph and Pose-Blending Implementation Plan

## Objective

Replace hard full-pose switching, color-classified cell warping, and bundled
action timing with a deterministic cell animation graph. Preserve semantic
server authority, direct ASCILINE cell generation, current character identity,
all eight directions, and independent locomotion/expression/gesture/speech/staff
channels.

Primary defects: `ANIM-GLITCH-006` through `010`, `013`, and `015`.

## File Ownership

Create:

- `rust/wizard_avatar_engine/src/animation.rs`
- `rust/wizard_avatar_engine/src/pose.rs`
- `rust/wizard_avatar_engine/tests/animation_transitions.rs`
- `rust/wizard_avatar_engine/tests/pose_metadata.rs`

Modify:

- `rust/wizard_avatar_engine/src/lib.rs`
- `rust/wizard_avatar_engine/src/state.rs`
- `rust/wizard_avatar_engine/src/controller.rs`
- `rust/wizard_avatar_engine/src/reference_avatar.rs`
- `rust/wizard_avatar_engine/src/renderer.rs`
- `rust/wizard_avatar_engine/src/cell.rs`
- `wizard_avatar/definitions/reference_avatar_pose_cells.json`
- `rust/wizard_avatar_engine/src/pose_builder.rs`
- `rust/wizard_avatar_engine/src/pose_builder_main.rs`

The Rust pose builder is the only accepted generator. Python pose tooling is
owned by another workstream and cannot generate, validate, or approve any pose
for this implementation.

Plan 2 owns the central clock, world steering, projection context, and contact
solver. Plan 3 owns frame fanout, codec/resync, browser presentation, and E2E.

## Data Model

### Channel and transition types

```rust
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum InterruptPolicy {
    Immediate,
    AtContact,
    HigherPriorityOnly,
    Finish,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum EasingCurve {
    Linear,
    SmoothStep,
    CubicHermite,
    Inertialized,
}

pub struct AnimationTransition<T> {
    pub source: T,
    pub target: T,
    pub started_tick: u64,
    pub duration_ticks: u16,
    pub easing: EasingCurve,
    pub interrupt_policy: InterruptPolicy,
    pub generation: u64,
    pub source_pose: PoseSnapshot,
    pub preserve_root: bool,
    pub preserve_walk_phase: bool,
    pub preserve_contact: bool,
}

pub struct ChannelState<T> {
    pub stable: T,
    pub target: T,
    pub generation: u64,
    pub expires_at_tick: Option<u64>,
    pub restore_to: Option<T>,
    pub transition: Option<AnimationTransition<T>>,
}
```

`ChannelState::expire(tick, generation)` must ignore stale generations.
`ChannelState::interrupt` first samples the currently presented pose and
velocity, then creates the next transition from that snapshot.

### Internal animation graph

```rust
pub struct AnimationRuntimeState {
    pub locomotion: ChannelState<LocomotionMode>,
    pub upper_body: ChannelState<UpperBodyAction>,
    pub staff: ChannelState<StaffState>,
    pub expression: ChannelState<Expression>,
    pub blink: ChannelState<BlinkState>,
    pub speech: ChannelState<SpeechState>,
    pub effects: ChannelState<EffectState>,
    pub presented_direction: Direction,
    pub pending_direction: Option<Direction>,
    pub walk_phase: f32,
    pub contact_marker: ContactMarker,
    pub previous_pose: PoseSnapshot,
    pub presented_pose: PoseSnapshot,
}
```

Keep `WizardState` serializable and semantic. Add `simulation_tick`, requested
channel states, and public diagnostics; keep derived pose correspondence caches
inside controller/runtime objects.

### Pose schema v2

```rust
pub enum RegionId {
    Hat, Head, Beard, Torso, Robe, InnerRobe,
    LeftArm, RightArm, LeftLeg, RightLeg,
    LeftBoot, RightBoot, Staff, AdornmentLeft,
    AdornmentRight, Face, Mouth, Effect,
}

pub enum AnchorId {
    Root, Pelvis, Chest, Head,
    LeftShoulder, LeftElbow, LeftWrist,
    RightShoulder, RightElbow, RightWrist,
    LeftHip, LeftKnee, LeftAnkle,
    RightHip, RightKnee, RightAnkle,
    LeftEye, RightEye, Mouth,
    StaffHand, StaffTop,
}

pub struct PoseCell {
    pub x: i16,
    pub y: i16,
    pub glyph: u8,
    pub rgb: Rgb,
    pub region: RegionId,
    pub stable_id: u32,
}

pub struct PoseDefinition {
    pub id: String,
    pub direction: Direction,
    pub gait_marker: Option<ContactMarker>,
    pub root_anchor: Point,
    pub anchors: BTreeMap<AnchorId, PointF>,
    pub cells: Vec<PoseCell>,
    pub z_order: Vec<RegionId>,
    pub correction_masks: BTreeMap<Direction, Vec<CellCorrection>>,
}
```

The JSON root gains `schema_version: 2`. Loader supports v1 only during the
migration and emits a diagnostic; production tests require v2. Region metadata
is authored/generated offline and reviewed. Runtime RGB/saturation anatomy
classification is prohibited.

### Pose snapshot

```rust
pub struct PoseSnapshot {
    pub tick: u64,
    pub direction: Direction,
    pub root: PointF,
    pub anchors: BTreeMap<AnchorId, AnchorSample>,
    pub regions: BTreeMap<RegionId, RegionPose>,
    pub contact: FootContactState,
}

pub struct AnchorSample {
    pub position: PointF,
    pub velocity: PointF,
}
```

## Graph Evaluation Order

At each exact simulation tick:

1. Apply tick-stamped semantic commands.
2. Update channel generations, expiry, priority, and restoration.
3. Update locomotion phase/contact and pending direction from Plan 2.
4. Advance each channel transition in deterministic priority order.
5. Produce an unquantized semantic pose snapshot.
6. Apply root/foot constraints from Plan 2.
7. Quantize once and rasterize ordered regions.

At each render sample:

1. Interpolate continuous anchor parameters between fixed snapshots.
2. Evaluate discrete transition occupancy deterministically from tick/alpha.
3. Apply channel masks.
4. Run constraints.
5. Rasterize into the fixed stage.

## Channel Priorities and Masks

| Channel | Priority | Owned regions/anchors | Restoration |
| --- | --- | --- | --- |
| Locomotion | stop/turn > path walk > idle | legs, boots, pelvis, base robe; never face/staff | preserve phase |
| Upper body | cast > react > point > explain > think > none | approved torso/arm anchors | reaction restores prior stable action |
| Staff | cast > point > held > rest | staff hand/top and staff region | restore prior stable staff state |
| Expression | persistent request | brows, eyes, approved cheek cells | survives actions/blink |
| Blink | temporary override | eye cells only | returns to requested expression |
| Speech | cancel/end > active > closed | mouth and approved beard-edge cells | immediate close on cancel |
| Effects | cast/reaction envelopes | effect region only | expires independently |

Development builds assert that a channel does not write outside its mask.
Root, planted feet, and projected scale are never writable by additive channels.

## Transition Eligibility and Durations

- idle to walk: start immediately, ramp gait amplitude over 6-10 ticks; phase
  continues from stored value
- walk to idle: decelerate immediately, settle at next contact within four ticks
- adjacent direction: 6-10 ticks, same gait marker and planted foot
- larger turn: decompose into adjacent directions under Plan 2 turn-rate
- arm/staff action: 6-10 ticks (100-167 ms)
- face/mouth: 4-6 ticks (67-100 ms)
- hat/beard secondary motion: 8-12 ticks (133-200 ms)
- reaction: higher priority, stores and restores previous upper-body/staff states
- cast: can interrupt any lower-priority upper-body/staff state; locomotion
  continues unless the semantic command explicitly stops it

No bounce, elastic, overshoot, or wall-clock sine curves.

## Presented-Pose Interruption

```rust
fn interrupt_channel<T>(
    channel: &mut ChannelState<T>,
    target: T,
    tick: u64,
    presented: &PoseSnapshot,
    spec: TransitionSpec,
) {
    channel.generation += 1;
    channel.target = target;
    channel.transition = Some(AnimationTransition {
        source: channel.presented_value(),
        target,
        started_tick: tick,
        duration_ticks: spec.duration_ticks,
        easing: spec.easing,
        interrupt_policy: spec.interrupt_policy,
        generation: channel.generation,
        source_pose: presented.clone(),
        preserve_root: true,
        preserve_walk_phase: true,
        preserve_contact: spec.preserve_contact,
    });
}
```

For inertialized anchors, decay the source-target position/velocity residual
with the cubic Hermite form from research report 1. Planted foot/root residuals
are zero by constraint.

## Gait Pose Sampling

Replace `walking_pose_id` hard slots with:

```rust
fn sample_gait(
    direction: Direction,
    phase: f32,
    speed_ratio: f32,
    poses: &PoseLibrary,
) -> PoseSample
```

The sampler selects the two neighboring contact/passing definitions for the
same direction, aligns both to root and planted-foot anchors, interpolates
anchors, and resolves region occupancy. Direction changes reuse the same phase
and contact marker.

For authored non-joint regions:

1. Precompute matches only within the same `RegionId`.
2. Cost is `4*L1 position + 2*color mismatch + glyph mismatch`.
3. Reject matches beyond the region threshold.
4. Move matched cells on a monotone integer schedule.
5. Reveal/retire unmatched cells from/to the region anchor.
6. Resolve collisions by `(z_index, region_id, stable_id)`.

Precompute correspondence when the pose library loads; no per-frame assignment
search.

## Rasterization Changes

- Add `CellCanvas::blit_pose_sample` as a destination-driven renderer.
- One source logical cell maps to the exact nearest-neighbor destination area.
- Remove `ceil(scale) + 1` footprints.
- Delete runtime color classifiers once v2 metadata is required.
- Draw joint-driven limbs/staff from interpolated anchors with integer line and
  polygon primitives.
- Draw expression/mouth/effects through per-view anchors and scaled region cells,
  not isolated hard-coded stage cells.

## Migration Steps

1. Add animation/pose types and v1-compatible loader with no behavior change.
2. Extend the pose-generation tool to emit explicit anchors, regions, contacts,
   stable cell IDs, and z-order.
3. Review all eight directions and gait markers; add schema validation tests.
4. Introduce channel state/generation while keeping old renderer behind a
   temporary internal feature flag.
5. Add pose sampler and exact raster footprint tests.
6. Switch front/back walking to new sampler; verify temporal metrics.
7. Add side/diagonal gait and adjacent direction transitions.
8. Move face/mouth/staff/gesture overlays to anchors.
9. Remove old `walking_pose_id`, `reference_walk_cell_offset`, RGB classifiers,
   bundled `set_action`, and wall-clock speech root bob.
10. Remove compatibility flag after full tests and evidence pass.

## Diagnostics

Expose/log:

- simulation tick and channel generations
- stable/target value and transition progress per channel
- presented direction and pending direction
- gait phase/contact marker/planted foot
- root/foot/staff-hand/face-anchor stage cells
- region occupancy and per-frame region XOR/churn
- unexpected channel-mask writes
- pose correspondence cache hits/build time
- transition interruption/restoration counts

## Tests and Acceptance

Add:

- phase survives every direction, speed, action, expression, and speech change
- root jump is zero for every transition
- planted-foot jump is zero while contact is active
- staff hand differs from hand anchor by zero cells at stable frames and at most
  one during reviewed transition frames
- blink writes only eyes; speech only mouth mask; expression only face mask
- stale action expiry cannot cancel a newer generation
- reaction restores prior upper-body/staff stable states
- point interrupted by cast begins from presented anchors
- no pose transition exceeds reviewed region-churn thresholds
- all eight directions have v2 anchors/regions/contact metadata
- no runtime code references RGB/saturation classifiers for anatomy
- deterministic repeated command logs yield identical pose/cell hashes

Required temporal IDs: `WIZ-ANIM-001` through `WIZ-ANIM-010` from research
report 1, plus named transition recordings for the full baseline matrix.

## Completion Gate

This track is complete only when hard pose slots and color-classified warping are
removed from production, every channel is independent and generation-safe,
every pose has reviewed semantic metadata, and root/foot/staff/face temporal
invariants pass through the real renderer.
