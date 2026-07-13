# Character Animation and State Transitions

Research date: 2026-07-12  
Repository branch: `codex/build-repeatable-avatar-animation`  
Recorded shared base commit: `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1`  
Baseline evidence: [`00_CURRENT_STATE_AND_DEFECT_LEDGER.md`](../00_CURRENT_STATE_AND_DEFECT_LEDGER.md)  
ASCILINE revision inspected: clean `external/ASCILINE`, branch `main`, commit
[`05cc6ebd2152f5987ab348038d5619d279ecec27`](https://github.com/YusufB5/ASCILINE/tree/05cc6ebd2152f5987ab348038d5619d279ecec27)

## Executive Conclusion

WizardJoeAvatar does not need a mesh animation system transplanted into Rust. It
needs the same *control invariants* that mature animation systems enforce:

1. one persistent locomotion phase clock;
2. explicit contact markers and a root that is owned by world simulation;
3. orthogonal animation channels with masks and priorities;
4. transitions that begin from the currently presented pose, including its
   velocity, rather than from a nominal source state;
5. semantic anchors and regions instead of color-classified cell motion; and
6. continuous internal parameters followed by one deterministic integer-grid
   quantization step.

The highest-value change is therefore a small, deterministic animation graph for
cell poses, not a larger pose atlas. The graph should preserve `walk_phase` across
all eight directions, hold planted feet in stage-cell coordinates, keep staff and
face overlays attached to named per-view anchors, and evaluate locomotion,
gesture, staff, face, blink, and speech as independent layers. This directly
addresses `ANIM-GLITCH-006` through `010`, `013`, `014`, and `015` without
flattening the character or hiding discontinuities.

## Scope and Source Quality

This report distinguishes three levels of applicability:

- **Direct**: the algorithm can operate on WizardJoeAvatar's semantic state,
  anchors, region masks, and integer cells.
- **Adapted**: the engine technique assumes continuous skeletal animation, but
  its timing, matching, constraint, or ownership rule transfers to a cell grid.
- **Mesh-only**: the technique depends on bone rotations, skinning, continuous
  deformation, or inverse kinematics and should not be implemented literally.

The principal sources are current official Unity, Unreal Engine, and Godot
documentation, original SIGGRAPH/SCA papers, and GDC presentations. Harel's
original statecharts paper is included because hierarchy and orthogonal
concurrency are the formal basis for separating animation channels: statecharts
extend ordinary state machines with hierarchy, concurrency, and communication
([Harel, 1987](https://doi.org/10.1016/0167-6423(87)90035-9)).

The exact ASCILINE checkout was also inspected. Its production client keeps a
bounded frame buffer and presents frames on `requestAnimationFrame` in
[`external/ASCILINE/app.js`](../../../external/ASCILINE/app.js), but it does not
define character pose or transition semantics. Consequently, ASCILINE transport
recommendations belong primarily to Research Agent 3; this report treats the
decoded cell frame as the presentation boundary.

## 1. What Causes Visible Snapping and Transition Popping?

Visible snapping occurs whenever a displayed quantity is discontinuous in
position, velocity, topology, attachment, or ownership. A conventional
transition explicitly defines its duration, target offset, and interruption
rules; Unity's current transition model exposes all of these and even visualizes
left/right foot contact so a blend can be aligned to avoid slips and jumps
([Unity animation transitions](https://docs.unity3d.com/Manual/class-Transition.html)).
WizardJoeAvatar currently has no equivalent transition object.

The concrete causes are:

| Cause | Current source | Visible result | Defects |
| --- | --- | --- | --- |
| `floor(walk_phase * 4)` swaps complete unrelated masks | `renderer.rs::walking_pose_id` | hat, beard, robe, arms, and staff teleport at quarter-cycle boundaries | `ANIM-GLITCH-006` |
| Direction is an immediate enum replacement with no adjacent-view transition | `controller.rs::resolve_direction_from_velocity`, `renderer.rs::reference_pose_id_for_state` | front/diagonal/side/back silhouette snap | `006`, `008`, `014` |
| Cell regions are inferred from color and normalized position | `renderer.rs::reference_walk_cell_offset` | unrelated brown or saturated cells move together; limbs and staff tear | `007`, `008` |
| Every moved source cell draws a `ceil(scale) + 1` square | `cell.rs::blit_scaled_with_offsets` | order-dependent overlap, thick bands, and disappearing detail | `007` |
| Actions overwrite action, upper-body, staff, and one timeout as a bundle | `controller.rs::set_action`, `update_timers` | interruption teleports arms/staff and restores the wrong state | `009` |
| Face, mouth, and effects use hard-coded local coordinates rather than per-pose anchors | `renderer.rs::reference_stage_point`, `draw_reference_expression`, `draw_reference_mouth`, `draw_reference_action_effects` | overlays pop, drift, or disappear after view changes | `010` |
| Whole-root bob is independently driven by gait and wall-clock speech | `renderer.rs::render_reference_stage` | start/stop/speech pops and beat interference | `013`, `015` |

The SIGGRAPH Motion Graphs work found that human observers are especially
sensitive to walking transitions and created graph edges only at suitable pose
connections ([Kovar, Gleicher, and Pighin, 2002](https://graphics.cs.wisc.edu/Papers/2002/KGP02/mograph.pdf)).
WizardJoeAvatar currently permits a transition between any two view masks at any
instant, without a similarity or contact test. That is why adding more masks
alone cannot solve the problem.

## 2. How Professional Systems Preserve Motion Phase

Professional systems preserve a shared cycle coordinate and align semantically
equivalent events. Unreal Sync Groups keep related motions on one timeline;
marker-based synchronization explicitly aligns events such as left-foot and
right-foot contacts, including clips with different step counts or stride
lengths ([Unreal Animation Sync Groups](https://dev.epicgames.com/documentation/unreal-engine/animation-sync-groups-in-unreal-engine?lang=en-US)).
Godot likewise offers a `Sync` transition that seeks the target state to the
source playback position instead of restarting it
([Godot AnimationTree](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html)).

### Direct cell-grid algorithm: one gait clock and contact markers

Keep the existing distance-driven phase rule from
[`docs/15-procedural-walking.md`](../../15-procedural-walking.md), but make it the
sole locomotion timeline:

```text
phase_next = fract(phase_prev + distance_travelled / stride_length)

markers:
  0.00 left_contact
  0.25 passing_left
  0.50 right_contact
  0.75 passing_right
```

Each directional gait definition must map the same four markers to a pose sample
and contact set. A direction change changes only the *view sampler*; it never
resets `walk_phase`. A walk-to-idle request should either:

- enter a short phase-matched stop transition at the next contact marker, with a
  bounded wait of at most 4 simulation ticks; or
- for an urgent stop, snapshot the current presented pose and inertialize the
  non-contact regions while immediately locking the currently planted foot.

This is distance matching in a small procedural form. Unreal's Distance Matching
advances animation from distance traveled rather than time and specifically
supports starts, stops, and pivots
([Unreal Distance Matching](https://dev.epicgames.com/documentation/en-us/unreal-engine/distance-matching-in-unreal-engine)).

### Eight-direction policy

Velocity should remain continuous. Direction is a view-selection label with
hysteresis, not a new animation clock. Unity's 2D directional blend-tree model
uses velocity X/Z as the two controlling parameters for directional motion
([Unity 2D Blending](https://docs.unity3d.com/Manual/BlendTree-2DBlending.html)).
For this discrete renderer, use that concept but not continuous image blending:

1. retain a continuous heading internally;
2. select one of eight authored views with the existing angular hysteresis;
3. transition only between adjacent directions unless an explicit face command
   requests a larger turn;
4. preserve the same gait marker and planted-foot identity in both views; and
5. align both poses by root and planted-foot anchors before any region changes.

**Code mapping:** extend state beside `WizardState::walk_phase`; update phase only
in `WizardAvatarController::step_locomotion`; replace hard slots in
`walking_pose_id` with a phase sampler; give
`resolve_direction_from_velocity` a pending target/turn transition rather than
immediately replacing the presented view. This addresses `ANIM-GLITCH-006`,
`008`, and `014`.

## 3. How Root Motion and Foot Locking Should Work

The server's world-space controller, not an animation mask, must own the root.
Unity describes root transform as the runtime projection of body displacement,
with hands and feet represented relative to that body transform; its foot-based
Y option keeps the blend point near the lowest foot to prevent floating
([Unity root motion](https://docs.unity3d.com/Manual/RootMotion.html)). Unreal
similarly defines a root bone as the foundational reference for the complete
skeleton and provides explicit root-lock modes
([Unreal root motion](https://dev.epicgames.com/documentation/unreal-engine/root-motion-in-unreal-engine)).

For WizardJoeAvatar, root motion should mean:

```text
world controller position
    -> one perspective projection
    -> one quantized stage root
    -> all body regions and contact shadow relative to that root
```

Body bob, speech, face, and gesture channels must never write the stage root.
They may write named local anchors below `root` in the hierarchy.

### Direct cell-grid foot lock

Maintain a contact record per foot:

```text
FootContact {
    planted: bool,
    planted_stage_cell: (i32, i32),
    local_ankle_anchor: (f32, f32),
    entered_at_tick: u64
}
```

At a contact-marker crossing, store the foot's current stage cell. While planted:

```text
predicted = quantize(projected_root + transformed_local_ankle)
correction = planted_stage_cell - predicted
```

Apply `correction` to the character's local presentation offset, not to
`world_position`. With one planted foot, use the exact integer correction. In a
brief double-support interval, choose the correction minimizing the weighted L1
error to both planted feet, breaking ties by the previous correction. Release
the old foot before the new swing lift begins. Derive the contact shadow only
from projected root plus the two contact flags.

This is an integer-grid specialization of footplant constraint enforcement. The
SCA footskate paper identifies planted-foot drift as especially distracting and
enforces explicit footplant constraints
([Kovar, Schreiner, and Gleicher, 2002](https://graphics.cs.wisc.edu/Papers/2002/KSG02/cleanup.pdf)).

### What not to copy

Do not implement a skeletal IK solver, variable bone lengths, or per-frame
terrain raycasts. Those are **mesh-only** details of conventional foot cleanup.
The applicable principle is the end-effector constraint. Here the end effector
is a named ankle/boot cell anchor and the floor is already a known projected
plane.

**Code mapping:** root ownership belongs in `frame_source.rs::render_state_to_cells`
and `renderer.rs::render_reference_stage`; foot contacts belong in controller or
animation runtime state; `draw_contact_shadow` consumes contact state. Remove
speech from root `bob`. This addresses `ANIM-GLITCH-005`, `008`, `012`, `013`,
and `015`.

## 4. How to Blend Procedural Poses Without Corrupting Anchors

Standard skeletal crossfades interpolate corresponding bone transforms. A raw
cell mask has no such correspondence, so alpha-blending complete masks produces
ghost silhouettes and does not preserve staff, face, or foot attachment. Motion
Warping's original formulation aligns critical correspondence points in time and
then blends parameter curves
([Witkin and Popovic, SIGGRAPH 1995](https://www.cs.cmu.edu/~aw/pdf/motion_warping.pdf)).
The useful part here is correspondence and parameter blending, not mesh
deformation.

### Required pose schema

Every reference pose should expose:

```text
PoseDefinition {
    view: Direction,
    gait_marker: ContactMarker,
    root_anchor,
    anchors: root, pelvis, chest, head,
             left/right shoulder, elbow, wrist,
             left/right hip, knee, ankle,
             staff_hand, staff_top,
             left_eye, right_eye, mouth,
    regions: hat, head, beard, torso, robe,
             left/right arm, left/right leg,
             left/right boot, staff, effects,
    cells: cells tagged with region ID
}
```

This replaces color tests in `reference_walk_cell_offset`. The existing
`reference_avatar_pose_cells.json` is suitable as source data only after it gains
explicit region and anchor metadata loaded by `reference_avatar.rs`.

### Anchor-preserving transition sampler

For a transition from presented pose `A` to target pose `B`:

1. Snapshot the currently *presented* anchor parameters, including any active
   transition. Never restart from the nominal state A.
2. Align B's root and planted-foot anchors to the snapshot.
3. Interpolate semantic anchor parameters in floating-point local space with a
   short monotone curve.
4. Rebuild limbs and staff from interpolated anchors using integer line/polygon
   rasterization.
5. Quantize each final anchor exactly once, using previous-cell tie breaking.
6. Select or morph region masks only inside their semantic ownership masks.

The repository already has Bresenham-style line construction in
`cell.rs::line`; the original integer plotting algorithm is specifically designed
to choose discrete grid points without continuous antialiasing
([Bresenham, IBM Systems Journal 1965](https://doi.org/10.1147/sj.41.0025)).

For regions that cannot be regenerated from anchors, precompute deterministic
correspondence within the *same region* using a minimum-cost assignment:

```text
cost(a, b) = 4 * L1(position_a, position_b)
           + 2 * color_class_mismatch
           + 1 * glyph_mismatch
```

Reject matches beyond a bounded distance and explicitly mark appearing or
disappearing cells. Move matched cells with a monotone integer schedule; reveal
new target cells from the anchor outward and retire source cells toward the
anchor. Resolve collisions by stable `(z_index, region_id, source_index)` order.
This is a deliberately small pose-matching problem, not runtime full-body motion
matching. Modern motion matching scores current pose and desired trajectory
against a database ([Unreal Motion Matching](https://dev.epicgames.com/documentation/unreal-engine/motion-matching-in-unreal-engine?lang=en-US);
[Clavet, GDC 2016](https://media.gdcvault.com/gdc2016/Presentations/Clavet_Simon_MotionMatching.pdf)),
but WizardJoeAvatar has few authored poses and benefits more from offline
region-local correspondences.

### Crossfade policy by content

| Content | Cell-grid transition |
| --- | --- |
| Root and planted feet | constrained; never crossfaded |
| Joint-driven limbs/staff | interpolate anchors, then rerasterize |
| Hat/beard/robe silhouette | matched region morph or reviewed 2-4 frame correction masks |
| Face and mouth | replace cells only inside per-view face/mouth masks |
| Magic effects | additive cells with RGB fade or deterministic occupancy ramp |
| Whole character | never alpha-crossfade two complete silhouettes |

**Code mapping:** replace `reference_walk_cell_offset` and the oversized source
cell footprint in `blit_scaled_with_offsets`; attach overlays in
`draw_reference_animation_overlays` to pose anchors. This addresses
`ANIM-GLITCH-006`, `007`, `008`, `010`, and `013`.

## 5. How to Interrupt One Action and Enter Another Cleanly

An interrupt must be defined per channel and must start from the displayed
result of all prior blending. Unity permits one active transition but defines a
specific ordered queue of current-state, next-state, and Any-State transitions
for interruption
([Unity transition interruption](https://docs.unity3d.com/Manual/class-Transition.html)).
Unreal inertialization records the offset between outgoing and incoming motion
and fades that residual to prevent popping; it also supports interruption by a
new inertial blend
([Unreal blend nodes](https://dev.epicgames.com/documentation/unreal-engine/animation-blueprint-blend-nodes-in-unreal-engine?lang=en-US)).
The original GDC presentation emphasizes that inertialization is a post-process
and does not require continued evaluation of the outgoing graph
([Bollo, GDC 2018](https://gdcvault.com/browse/gdc-18/play/1025165/Inertialization-High-Performance-Animation-Transitions)).

### Direct channel-interruption model

Each channel should have its own generation token and transition:

```text
ChannelState<T> {
    stable: T,
    target: T,
    generation: u64,
    transition: Option<TransitionSnapshot>,
    restore_to: Option<T>,
    expires_at_tick: Option<u64>
}
```

Timers must carry the generation they were created for. An expiry can only
complete the same generation, preventing a stale timer from cancelling a newer
action. Reaction stores `restore_to` and returns to the previous stable
upper-body state, while locomotion and speech continue independently.

On interruption, sample the currently presented anchor value `q`, its finite
difference velocity `v`, and the new target trajectory `q_t`. A practical
cell-grid inertialization-inspired residual is cubic Hermite decay over duration
`T`:

```text
s = clamp(elapsed / T, 0, 1)
h00 = 2s^3 - 3s^2 + 1
h10 = s^3 - 2s^2 + s
residual(s) = h00 * (q - q_t) + T * h10 * (v - v_t)
presented(s) = q_t(s) + residual(s)
```

This preserves position and velocity at the interruption and reaches zero
residual with zero residual velocity. Keep the result continuous internally and
quantize only at final rasterization. Use short durations by channel, for
example 100-160 ms for arms/staff, 60-100 ms for face/mouth, and 120-200 ms for
hat/beard follow-through. Do not inertialize planted-foot or root constraints.

### Interruption priority

| Channel | Priority order | Restoration |
| --- | --- | --- |
| Locomotion | stop/turn > path walk > idle | preserve gait phase unless reset command |
| Upper body | cast > react > point > explain > think > none | reaction restores previous stable action |
| Staff | cast > point > held/rest | follows `staff_hand`; never inferred from global action alone |
| Speech | explicit cancel/end > active speech > closed | closes immediately on cancel, then eases only approved beard/mouth neighbors |
| Face | blink eye override > requested expression > neutral | requested expression persists through blink |

**Code mapping:** replace bundled behavior in `controller.rs::set_action` and the
global logic in `update_timers`; make `cmd_speak` affect speech and approved
upper-body channels separately. This addresses `ANIM-GLITCH-002`, `009`, `010`,
and `015`.

## 6. How to Layer Speech, Expression, Gesture, and Locomotion

The correct model is an orthogonal graph, not a Cartesian product enum. Harel's
statecharts formalize concurrent components, and both Unity and Unreal implement
the animation equivalent with masked layers. Unity layers can override or add
motion only on selected body parts
([Unity Animation Layers](https://docs.unity3d.com/Manual/AnimationLayers.html));
Unreal's upper-body slots use a per-bone mask so locomotion remains active below
the upper body
([Unreal layered animation](https://dev.epicgames.com/documentation/unreal-engine/using-layered-animations-in-unreal-engine?lang=en-US)).

For the cell renderer, replace bone masks with semantic region write masks:

```text
1. locomotion base: root-relative body, legs, robe, gait contacts
2. secondary body: hat/beard lag and breathing, no root write
3. upper-body action: permitted arm/torso regions only
4. staff constraint: staff_hand -> staff_top, with explicit z-order per view
5. expression: brows/eyes/approved cheek cells
6. blink: eye cells only, temporary override
7. speech: mouth cells only, optional approved beard-edge cells
8. effects: additive effect region only
```

Each layer should return a sparse set of semantic parameter changes or region
writes. The compositor rejects writes outside the layer's mask in development
and tests. Conflict resolution is explicit: blink owns eyes while active;
speech owns mouth while active; expression retains brows; staff owns its anchor
chain; no upper layer owns root or planted feet.

The current `WizardState` already names most channels, but
`controller.rs::set_action` collapses them and
`renderer.rs::reference_pose_id_for_state` selects one full-body pose from
locomotion/action. Preserve the fields, give each independent transition state,
and make `draw_reference_animation_overlays` consume per-view anchors. This is
the direct fix for `ANIM-GLITCH-009`, `010`, and `015`.

## 7. Which Practices Apply to a Discrete ASCII/Cell-Grid Character?

### Directly applicable

- Hierarchical and orthogonal state organization.
- Explicit transition conditions, priorities, interruption sources, and
  generation-safe cancellation.
- One distance-driven gait phase across speeds and directions.
- Contact markers (`left_contact`, `right_contact`, passing states).
- Pose matching using named anchors, anchor velocities, semantic region
  occupancy, and desired direction.
- Root ownership and planted-foot constraints.
- Per-channel additive/override masks.
- Motion warping of *parameters* toward a target, such as a pointing hand or
  staff top, within a bounded transition window.
- Fixed-step authoritative simulation with rendering sampled separately.
- Continuous internal anchor values followed by a single deterministic
  integer-grid rasterization.
- Nearest-neighbor scale and stable tie-breaking. Browser image smoothing is
  specifically inappropriate for crisp pixel-art enlargement
  ([MDN `imageSmoothingEnabled`](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/imageSmoothingEnabled)).

### Cell-grid-specific adaptations

1. **Blend parameters, not finished framebuffers.** Interpolate named anchor
   positions and rerasterize regions.
2. **Quantize once.** Do not independently round root, limb endpoints, staff,
   overlays, and scale in different coordinate spaces.
3. **Use temporal hysteresis.** If a continuous anchor is exactly near a cell
   boundary, retain the previous cell until a defined threshold is crossed.
4. **Keep topology authored.** Hat, beard, robe, and directional correction
   masks should remain reviewed assets, with transitions constrained to their
   semantic regions.
5. **Use deterministic draw order.** Collision resolution between moving cells
   must not depend on iteration accidents.
6. **Measure cell churn.** A transition can be numerically continuous while
   still flashing too many cells; region-level symmetric difference is a useful
   visual metric.

Godot's fixed-timestep interpolation documentation separates fixed simulation
ticks from variable render frames and stores previous/current transforms for
presentation interpolation
([Godot fixed timestep interpolation](https://docs.godotengine.org/en/stable/tutorials/physics/interpolation/physics_interpolation_introduction.html)).
For WizardJoeAvatar, interpolate world root and continuous anchor parameters for
presentation, but choose glyph/cell occupancy deterministically at the final
sample. Do not feed interpolated presentation state back into simulation.

## 8. Which Practices Should Not Be Used?

| Technique | Classification | Reason / safe adaptation |
| --- | --- | --- |
| Quaternion bone crossfade over a skinned mesh | **Mesh-only** | No bones, skin weights, or continuous surface. Blend named 2D anchors instead. |
| Full-body IK, FABRIK, CCD, or foot raycast solvers | **Mesh-only** | The floor and target cells are known. Use integer end-effector constraints and Bresenham limb redraw. |
| Unreal Pose/Stride Warping nodes | **Mesh-only implementation** | They require root-motion animation, an IK rig, and foot bones ([Unreal Pose Warping](https://dev.epicgames.com/documentation/unreal-engine/pose-warping-in-unreal-engine?lang=en-US)). Adapt only stride/contact parameter rules. |
| Whole-character alpha crossfade | **Reject** | Creates two simultaneous silhouettes, ghost staff/eyes, and no stable contacts. |
| Subpixel transform, antialiasing, motion blur | **Reject** | Violates the cell-grid contract and hides rather than fixes discontinuities. |
| Full motion-matching database and nearest-neighbor search every frame | **Overkill** | Too little authored motion data; use a tiny deterministic candidate cost only at transition requests. |
| Animation-authored root motion driving world position | **Reject for this architecture** | The server's semantic controller is authoritative. Adapt motion warping only for local pose parameters. |
| Per-cell color heuristics as body-part classification | **Reject** | Color is appearance, not ownership; it caused `ANIM-GLITCH-007`. |
| Independent wall-clock oscillators per layer | **Reject** | Produces beat interference and breaks replay determinism. Use simulation tick and channel phase. |
| Extrapolated presentation as authoritative state | **Reject** | Prediction corrections can visibly snap; Godot documents this failure mode. Interpolation may be used only in presentation. |

## 9. Concrete Algorithms Suitable for This Codebase

The following sequence is intentionally incremental and maps to existing
boundaries. It is a recommendation, not an implementation in this report.

### A. Orthogonal animation runtime

Add per-channel state, transition snapshot, generation token, priority, and
restore target beside `WizardState`. Keep semantic command state serializable;
derived transition caches can live in `WizardAvatarController`.

**Files/functions:** `state.rs::WizardState`, `controller.rs::set_action`,
`update_timers`, `cmd_speak`.  
**Defects:** `ANIM-GLITCH-002`, `009`, `015`.

### B. Gait clock and marker sampler

Keep distance-driven `walk_phase`; derive contact marker and foot lift from the
phase; never reset phase on direction/speed/action changes. Add phase-matched
start/stop/turn transitions.

**Files/functions:** `controller.rs::step_locomotion`,
`resolve_direction_from_velocity`; `renderer.rs::walking_pose_id`.  
**Defects:** `006`, `008`, `014`.

### C. Semantic pose metadata

Add per-view anchors, region IDs, contact metadata, and reviewed adjacency
transitions to reference pose definitions. Eliminate color-based classification.

**Files/functions:** `reference_avatar.rs::ReferencePosePayload`,
`render_reference_avatar_pose_local`; generated
`reference_avatar_pose_cells.json`.  
**Defects:** `006`, `007`, `008`, `010`.

### D. Anchor-preserving pose sampler

Snapshot presented anchors, align target root/contact, interpolate anchors,
rerasterize limbs/staff, and use region-local correspondence for authored masks.

**Files/functions:** `renderer.rs::render_reference_stage`,
`reference_pose_id_for_state`, `reference_walk_cell_offset`,
`draw_reference_animation_overlays`; `cell.rs::line`.  
**Defects:** `006`, `007`, `008`, `010`, `013`.

### E. Integer foot/root constraint pass

After pose sampling but before rasterization, solve planted-foot correction in
stage-cell space and derive shadow from root/contact state. Root correction is a
presentation offset only.

**Files/functions:** `frame_source.rs::render_state_to_cells`,
`renderer.rs::render_reference_stage`, `draw_contact_shadow`.  
**Defects:** `005`, `008`, `012`, `013`.

### F. Inertialized interruption per channel

At interruption, sample the presented anchor value and velocity; decay residual
to the new target with a bounded Hermite transition. Never inertialize root or a
planted foot.

**Files/functions:** new controller transition records consumed by renderer;
replace shared timer semantics in `update_timers`.  
**Defects:** `009`, `010`, `015`.

### G. Deterministic cell rasterization

Use destination-driven nearest-neighbor scaling as `blit_scaled` already does,
or render semantic regions directly at target scale. Remove the
`ceil(scale) + 1` per-source-cell footprint. Quantize after all channel and
contact constraints, with stable z-order and tie breaking.

**Files/functions:** `cell.rs::blit_scaled_with_offsets`,
`renderer.rs::reference_stage_point`.  
**Defects:** `007`, `010`, `013`.

### H. Fixed simulation and render sampling

Advance the controller from one 60 Hz server simulation loop. Store previous and
current simulation snapshots; render at 15/24/30 FPS using a presentation alpha.
Interpolate continuous world/anchor values only; derive contact and event state
from authoritative ticks. `frame_source.rs::next_frame` must sample rather than
advance simulation.

**Files/functions:** `controller.rs::advance`, `frame_source.rs::next_frame`,
server fanout.  
**Defects:** `ANIM-GLITCH-001`, `011`, `016`.

### Suggested transition cost

For the small set of candidate directional/contact poses, select a target entry
sample using a deterministic cost:

```text
C = 8 * planted_foot_L1
  + 5 * root_L1
  + 3 * staff_hand_L1
  + 2 * head_L1
  + 2 * gait_marker_distance
  + 1 * normalized_region_xor
  + turn_distance_penalty
```

Reject candidates with the wrong planted-foot identity unless the transition is
an urgent stop. Prefer the current sample on equal cost. This borrows the
pose/trajectory-cost idea of motion matching while remaining small, explainable,
and deterministic.

## 10. Recommended Test Strategies

The current suite proves state availability and static frame differences, not
continuity. Add tests at four levels.

### Unit and property tests

1. **Phase invariance:** speed and direction changes never reset `walk_phase`;
   equal traveled distance yields equal phase at 15, 24, 30, and 60 render FPS.
2. **Contact schedule:** exactly one expected foot is planted in swing phases;
   double support occurs only in declared windows.
3. **Foot lock:** while planted, the boot anchor remains at the exact same stage
   cell; tolerance `0` for a flat floor.
4. **Root lock:** turning and view changes do not alter projected root cell.
5. **Staff attachment:** `staff_hand` and the hand region differ by at most one
   cell throughout every transition; target should be zero after rasterization
   metadata is complete.
6. **Channel masks:** speech changes only mouth/approved beard cells; blink only
   eyes; expression only face; upper-body action cannot write root, legs, or
   contact state.
7. **Generation-safe timers:** stale expiries cannot cancel a newer action or
   speech generation.
8. **Interruption fuzzing:** generate deterministic command sequences and assert
   no invalid state combinations, anchor jumps, or non-replayable hashes.
9. **Quantization stability:** a stationary continuous anchor produces one cell
   forever; crossing a threshold produces one change, not oscillation.
10. **Raster footprint:** scaling one source cell produces the exact
    destination-driven nearest-neighbor footprint with no extra row/column.

### Transition-sequence tests

Record every transition listed in the baseline, at least 12 frames before and
after the boundary. Assert:

```text
root_jump              == 0 cells
planted_foot_jump      == 0 cells
staff_hand_jump        <= 1 cell during blend, 0 at completion
face_anchor_jump       <= 1 cell during adjacent view change
unexpected_region_write == 0
```

Compute per-frame region metrics:

```text
anchor_motion = weighted sum of L1 anchor deltas
silhouette_churn = XOR(occupancy_t, occupancy_t-1) / union
component_delta = abs(components_t - components_t-1)
```

Flag spikes relative to neighboring gait frames, with separate reviewed limits
for locomotion, turn, gesture, and magic effects. This catches one-frame flashes
that still-image goldens miss.

### Golden temporal tests

- Golden contact-marker frames for all eight directions at phases 0.00, 0.25,
  0.50, and 0.75.
- Golden short sequences for front-to-diagonal, diagonal-to-side, side-to-back,
  walk-to-idle, idle-to-walk, turn-to-walk, and staff gesture transitions.
- Golden interruption sequences: explain-to-walk, think-to-speak,
  cast-to-idle, reaction-to-previous, and point interrupted by cast.
- Expression, blink, and mouth sequences while walking in each canonical view.

Visual approval must inspect the animation or contact sheet in sequence; a
single end frame is insufficient.

### Determinism and clock tests

- Feed the same tick-stamped commands and seed into two runs; require identical
  state snapshots and framebuffer hashes for every authoritative tick.
- Render the same simulation at 15, 24, and 30 FPS; sampled frames may differ,
  but states at common simulation ticks and final world/phase values must match.
- Connect one, two, and eight viewers; simulation tick, gait phase, and action
  expiry must remain identical.
- Reconnect and replay from a state snapshot; the first reconstructed pose and
  every later authoritative hash must match the uninterrupted run.

### Source-versus-transport isolation

For every visual regression, save the authoritative raw cell frame before codec
encoding and the browser-decoded frame after transport. If raw frames differ,
the defect is controller/pose/rasterization. If raw frames match and decoded
frames differ, it is ASCILINE transport/presentation. Run this alongside the
exact checked-out ASCILINE decoder revision stated at the top of this report.
This separation is required to keep `ANIM-GLITCH-003` and `004` from being
misdiagnosed as pose transitions.

### Proposed test IDs

| Test ID | Assertion | Defects guarded |
| --- | --- | --- |
| `WIZ-ANIM-001` | gait phase survives all eight direction changes | `006`, `008`, `014` |
| `WIZ-ANIM-002` | idle/walk transitions preserve root and active contact | `006`, `013` |
| `WIZ-ANIM-003` | planted foot remains fixed through adjacent turn | `008`, `014` |
| `WIZ-ANIM-004` | staff remains attached during turn, point, explain, cast | `006`, `009`, `010` |
| `WIZ-ANIM-005` | speech/expression/blink writes stay inside masks | `009`, `010`, `015` |
| `WIZ-ANIM-006` | interruption starts from currently presented pose | `009`, `015` |
| `WIZ-ANIM-007` | reaction restores previous stable channel states | `009` |
| `WIZ-ANIM-008` | no transition frame exceeds reviewed silhouette-churn limit | `006`, `007`, `008` |
| `WIZ-ANIM-009` | fixed-step replay hashes are identical across render FPS | `001`, `011`, `016` |
| `WIZ-ANIM-010` | raw/decoded frame comparison identifies source vs transport | `003`, `004`, `016` |

## Recommended Implementation Order

1. Separate the fixed simulation clock and multi-client fanout first; otherwise
   all transition timing measurements are contaminated (`001`, `011`).
2. Add semantic pose anchors/regions and correct raster footprints (`007`,
   `010`).
3. Add the persistent gait/contact sampler and integer root/foot lock (`006`,
   `008`, `013`, `014`).
4. Replace bundled actions with orthogonal channel transitions and
   generation-safe interruption (`009`, `015`).
5. Add anchor-preserving directional and action transitions.
6. Gate completion on temporal, multi-client, and deterministic tests (`016`).

This order prevents polished transition code from being evaluated against a
simulation that changes speed with viewer count or a rasterizer that tears cells
independently of animation semantics.

## Sources

- David Harel, “Statecharts: A Visual Formalism for Complex Systems,” 1987:
  <https://doi.org/10.1016/0167-6423(87)90035-9>
- Unity 6.5, Animation transitions:
  <https://docs.unity3d.com/Manual/class-Transition.html>
- Unity 6.5, Animation Layers:
  <https://docs.unity3d.com/Manual/AnimationLayers.html>
- Unity 6.5, 2D Blending:
  <https://docs.unity3d.com/Manual/BlendTree-2DBlending.html>
- Unity 6.5, How Root Motion works:
  <https://docs.unity3d.com/Manual/RootMotion.html>
- Unreal Engine, Animation Sync Groups:
  <https://dev.epicgames.com/documentation/unreal-engine/animation-sync-groups-in-unreal-engine?lang=en-US>
- Unreal Engine, Animation Blueprint Blend Nodes / Inertialization:
  <https://dev.epicgames.com/documentation/unreal-engine/animation-blueprint-blend-nodes-in-unreal-engine?lang=en-US>
- David Bollo, GDC 2018, “Inertialization: High-Performance Animation
  Transitions in Gears of War”:
  <https://gdcvault.com/browse/gdc-18/play/1025165/Inertialization-High-Performance-Animation-Transitions>
- Unreal Engine, Distance Matching:
  <https://dev.epicgames.com/documentation/en-us/unreal-engine/distance-matching-in-unreal-engine>
- Unreal Engine, Motion Matching:
  <https://dev.epicgames.com/documentation/unreal-engine/motion-matching-in-unreal-engine?lang=en-US>
- Simon Clavet, GDC 2016, “Motion Matching and The Road to Next-Gen
  Animation”:
  <https://media.gdcvault.com/gdc2016/Presentations/Clavet_Simon_MotionMatching.pdf>
- Unreal Engine, Root Motion:
  <https://dev.epicgames.com/documentation/unreal-engine/root-motion-in-unreal-engine>
- Andrew Witkin and Zoran Popovic, SIGGRAPH 1995, “Motion Warping”:
  <https://www.cs.cmu.edu/~aw/pdf/motion_warping.pdf>
- Lucas Kovar, Michael Gleicher, and Frederic Pighin, SIGGRAPH 2002,
  “Motion Graphs”:
  <https://graphics.cs.wisc.edu/Papers/2002/KGP02/mograph.pdf>
- Lucas Kovar, John Schreiner, and Michael Gleicher, SCA 2002, “Footskate
  Cleanup for Motion Capture Editing”:
  <https://graphics.cs.wisc.edu/Papers/2002/KSG02/cleanup.pdf>
- Godot Engine, Using AnimationTree:
  <https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html>
- Godot Engine, Fixed timestep interpolation:
  <https://docs.godotengine.org/en/stable/tutorials/physics/interpolation/physics_interpolation_introduction.html>
- J. E. Bresenham, IBM Systems Journal 1965, “Algorithm for Computer Control
  of a Digital Plotter”: <https://doi.org/10.1147/sj.41.0025>
- MDN, `CanvasRenderingContext2D.imageSmoothingEnabled`:
  <https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/imageSmoothingEnabled>
