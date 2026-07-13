# Animation and Motion Plan

**Program:** Cartoon Animation Program
**Role:** ANIM - game animation and character motion
**Planning wave:** 2
**Production target:** ASCILINE Python server and direct-cell compositor on port `8765`
**Status:** Planning contribution; no production implementation is authorized by this document alone

## 1. Purpose and binding decisions

This plan turns the 39 integrated Wizard Joe poses into a controlled limited-animation system. It defines the animation data, authored clips, phase/contact rules, transition topology, secondary motion, visual gates, and ANIM-owned implementation sequence. It is designed to compose with the shared `CAP-*` workflow in `04-workflow-plan.md`.

The following decisions are binding:

1. Production is exclusively the ASCILINE Python architecture served on port `8765`.
2. Rust is excluded from production code, dependencies, CI, runtime fallback, and acceptance. Rust files are historical context only and are not referenced by any ANIM work item.
3. `CAP-000` resolves the stale no-wings contract in favor of the current accepted design: Wizard Joe has rainbow wings in flight and in authored winged action poses. Missing required wings, unexplained extra wing regions, or a transition that destroys wing continuity is a hard visual failure.
4. The 39 assets are animation key poses, not 39 interchangeable whole-frame sprites and not 39 complete loops.
5. The system preserves ASCILINE's discrete cells: integer cell placement, nearest-cell color selection, no antialiasing, no color interpolation, and no per-frame whole-character scaling.
6. Locomotion phase is driven by semantic runtime state, not by demo timers or pose-list order.
7. The current graph v1 remains the rollback behavior until graph v2 passes its family gates and INT promotes it.
8. ANIM owns graph data, graph evaluation, pose classification, motion selection/compositing rules, and visual-channel verification. INT owns final frame-source wiring and live promotion. SYS owns transport and browser input adapters. FPSE owns the deterministic runtime and semantic physics.

## 2. Source synthesis

This plan incorporates all four Wave 1 reports:

- `01-first-principles-software.md`: one deterministic Python runtime, immutable presentation snapshots, explicit contracts, and no renderer split.
- `02-game-animation-motion.md`: locomotion phase, action timing, contact continuity, coherent transitions, limited-animation principles, and review gates.
- `03-rust-runtime.md`: its transferable deterministic-runtime lessons are accepted, but every Rust production recommendation is superseded by the Python-only correction.
- `04-project-delivery.md`: one-writer ownership, checkpoint gates, compact evidence, live port-8765 verification, and reversible promotion.

The integrated identifiers, dependencies, flags, locks, and allowlists in `04-workflow-plan.md` are authoritative where this role plan and the shared workflow overlap.

## 3. Ownership and collaboration boundary

### 3.1 ANIM-owned production paths

ANIM may implement only these production and verification paths unless the coordinator records a new handoff:

```text
wizard_avatar/animation_graph.py
wizard_avatar/motion.py
wizard_avatar/quality.py
wizard_avatar/pose_selection.py
wizard_avatar/pose_compositor.py
wizard_avatar/reference_avatar.py
wizard_avatar/definitions/reference_avatar_animation_graph.v2.json
wizard_avatar/definitions/reference_avatar_animation_graph.v2.schema.json
wizard_avatar/definitions/reference_avatar_pose_cells.schema.json
tools/verify_motion_graph.py
tools/verify_motion_visuals.py
tests/wizard/test_animation_graph_v2.py
tests/wizard/test_clip_playback.py
tests/wizard/test_contact_continuity.py
tests/wizard/test_transition_recipes.py
tests/wizard/test_animation_markers.py
tests/wizard/test_visual_channels_v2.py
```

### 3.2 Read-only collaboration surfaces

ANIM defines requirements and reviews evidence for these paths but does not edit them:

```text
wizard_avatar/models.py
wizard_avatar/animation_state.py
wizard_avatar/frame_source.py
wizard_avatar/shadow.py
wizard_avatar/projection.py
wizard_avatar/server.py
web/avatar/wizardControls.ts
web/avatar/wizardInput.ts
web/avatar/wizardDemo.ts
```

FPSE supplies semantic motion and altitude. INT maps the resulting `PresentationState` into the ANIM evaluator and compositor. SYS supplies ordered control intent. ANIM must not compensate for a runtime defect by adding display-time clocks or browser-only motion.

### 3.3 Locks

- ANIM claims `LOCK-GRAPH` before changing graph v2 JSON, schema, or evaluator.
- ANIM does not claim `LOCK-FRAME`, `LOCK-SERVER`, `LOCK-WEB-CONTROL`, `LOCK-PORT-8765`, `LOCK-GIT-INDEX`, or `LOCK-TRACKER`.
- `LOCK-GRAPH` is released only after strict graph validation passes and the graph SHA-256 is recorded in evidence.
- A post-`CAP-140` field-semantics change requires `LOCK-CONTRACT` and acknowledgment from FPSE, ANIM, SYS, PLAN, and INT.

## 4. Animation data contract

Graph v2 is declarative JSON validated before runtime use. Unknown fields fail validation. Unknown enum values fail validation. The loader does not silently invent defaults for contact, phase, interrupt policy, or capability tier.

### 4.1 Top-level graph fields

```text
schema_version             string, exactly "2.0"
character_id               string, exactly "wizard_joe_reference"
pose_library_version       string
pose_library_sha256        lowercase hex SHA-256
authored_fps               integer, exactly 24 for initial release
simulation_hz              integer, exactly 60
default_clip_id            existing clip ID
capability_tiers           object keyed by Tier A/B/C
pose_taxonomy              array of PoseTaxonomyEntry
clips                      array of ClipDefinition
transition_recipes         array of TransitionRecipe
visual_channels            array of VisualChannelDefinition
fallbacks                  array of explicit FallbackRule
```

### 4.2 Pose taxonomy fields

Each of the 39 poses has exactly one entry:

```text
pose_id                    stable asset ID
library_index              integer 1..39
facing                     north|northeast|east|southeast|south|southwest|west|northwest
altitude_class             grounded|takeoff|airborne|landing
motion_family              idle|walk|run|flight|action|reaction|speech|transition
phase                      null or normalized [0,1)
support_contacts           ordered set of left_foot|right_foot|both_feet|staff_tip|left_hand|none
wing_mode                  hidden|folded|extended|upstroke|downstroke|banked
staff_mode                 absent|carried|planted|guard|attack|spin
silhouette_tags            nonempty array
capability_tier            A|B|C
production_uses            nonempty array of clip IDs
fallback_pose_id           existing pose ID or null
review_status              pending|approved|restricted
```

`wing_mode=hidden` is legal for grounded non-winged poses. It is illegal for flight clips after the `takeoff_commit` marker and before `landing_contact`, except for a single authored occlusion sample that still retains a reviewed wing silhouette region.

### 4.3 Clip fields

```text
clip_id                    stable snake-case ID
family                     idle|locomotion|flight|action|reaction|speech|transition
supported_facings          nonempty set
capability_tier            A|B|C
loop_mode                  loop|once|ping_pong|hold_last
phase_source               none|time|ground_distance|air_distance|flap_phase
root_policy                fixed|ground_distance|air_trajectory|contact_locked
minimum_hold_ticks         nonnegative integer simulation ticks
interrupt_policy           immediate|at_marker|after_commit|uninterruptible
channel_ownership          body/head/eyes/mouth/wings/staff/effect bit set
entry_markers              set
exit_markers               set
samples                    ordered nonempty array of ClipSample
legal_successors           explicit set of clip IDs
fallback_clip_id           existing clip ID
```

### 4.4 Clip sample fields

```text
sample_id                  unique within clip
pose_id                    existing taxonomy pose
sample_kind                authored_pose|approved_breakdown|region_offset_hold
duration_frames            integer >= 1 at authored_fps
phase_start                null or normalized [0,1)
phase_end                  null or normalized (0,1]
normalized_distance        null or nonnegative number
contacts                   ordered set matching taxonomy unless explicitly narrowed
planted_anchor             null or {region, local_x, local_y}
visual_root_offset_cells   {x, y}, integers
altitude_offset_cells      integer
markers                    ordered marker records
secondary_curves           map of channel to curve ID
region_mask_id             required for region_offset_hold, otherwise null
```

An `approved_breakdown` must be generated from named source poses using deterministic integer-cell rules and must have a committed visual-review record. A `region_offset_hold` may move only the named region mask. Neither kind may interpolate cell colors.

### 4.5 Marker and event fields

Marker record:

```text
marker_id                  stable name
frame_offset               integer 0..duration_frames-1
event_type                 enum below
payload                    event-specific object
emit_policy                once_per_traversal|once_per_loop|state_only
```

Initial marker/event enum:

```text
left_contact
left_release
right_contact
right_release
both_contact
staff_contact
staff_release
takeoff_commit
airborne
flap_down_peak
flap_up_peak
bank_apex
landing_contact
landing_settled
action_commit
action_effect
action_recoverable
speech_open
speech_close
shush_hold_start
shush_hold_end
loop_boundary
```

Events emit exactly once according to `emit_policy`, including when a render frame spans multiple 60 Hz ticks. Interrupting a clip does not retroactively emit unvisited events.

### 4.6 Transition recipe fields

```text
recipe_id                  stable ID
from_clip_ids              explicit nonempty set
to_clip_ids                explicit nonempty set
entry_rule                 phase_match|marker_gate|contact_match|snapshot_handoff|hard_cut
duration_frames            integer >= 0
phase_mapping              preserve|nearest_contact|restart|null
contact_requirement        set or null
root_reconciliation        preserve_world_contact|preserve_root|air_trajectory|none
region_masks               explicit set; empty means full coherent pose handoff
interrupt_source           presented_snapshot|authored_sample
hard_failure_fallback      existing clip ID
```

There is no wildcard every-pose-to-every-pose edge. `hard_cut` is allowed only at an authored compatible silhouette/contact marker or for emergency fallback. Production recipes never use coordinate-hash whole-body dissolve.

### 4.7 Presentation input fields consumed by ANIM

ANIM consumes the frozen `PresentationState` defined by `CAP-100`; it does not redefine that contract. At minimum, clip selection and evaluation require:

```text
tick
mobility_state
facing
position_x
position_z
altitude
velocity_x
velocity_z
vertical_velocity
ground_distance
air_distance
locomotion_phase
flap_phase
action_id
action_phase
expression_id
speech_level
controller_epoch
```

If a field is absent from the frozen schema at `CAP-140`, ANIM must raise a contract block rather than infer it from wall time.

## 5. Exhaustive 39-pose taxonomy

All poses are production-reachable through at least one listed clip. Tier C means a deliberate showcase/reaction burst or fallback, not dead data. Final contact and phase values are machine-validated in `CAP-110`; this table establishes intended use.

| # | Pose ID | Facing | Class | Contact / wing / staff intent | Tier | Required production uses |
|---:|---|---|---|---|:---:|---|
| 1 | `front_idle` | south | grounded idle | both feet; wings hidden; staff carried | A | `idle_front`, walk passing hold, action recoveries |
| 2 | `back_idle` | north | grounded idle | both feet; wings hidden; staff carried | B | `idle_back`, `walk_back_limited` passing hold |
| 3 | `profile_left` | west | grounded idle/turn | both feet; wings hidden; staff carried | B | `idle_left`, `turn_views` |
| 4 | `profile_right` | east | grounded idle/turn | both feet; wings hidden; staff carried | B | `idle_right`, `turn_views` |
| 5 | `walk_front_left` | south | walk contact | left support; wings hidden; staff carried | A | `walk_front_limited` |
| 6 | `walk_front_right` | south | walk contact | right support; wings hidden; staff carried | A | `walk_front_limited` |
| 7 | `back_left` | north | walk contact | left support; wings hidden; staff carried | B | `walk_back_limited` |
| 8 | `back_right` | north | walk contact | right support; wings hidden; staff carried | B | `walk_back_limited` |
| 9 | `explaining` | south | speech/action | both feet; wings hidden; staff carried | A | `explain_front` |
| 10 | `magic_cast` | south | cast extreme | both feet; wings may extend; staff attack | A | `cast_front`, `victory_cast_front` effect hold |
| 11 | `run_front_airborne_reach` | south | run burst airborne | no foot contact; wings support silhouette; staff carried | A | `run_charge_front` |
| 12 | `run_front_airborne_drive` | south | run burst airborne | no foot contact; wings support silhouette; staff carried | A | `run_charge_front` |
| 13 | `front_crouch_guard` | south | anticipation/reaction | both feet; wings folded/hidden; staff guard | A | `takeoff_front`, `guard_front`, `hit_fall_recover_front` |
| 14 | `front_reaction_jump_fist_staff` | south | airborne reaction | none; wings extended; staff carried | A | `air_reaction`, `celebrate_front` |
| 15 | `front_kneel_staff_brace` | south | landing/recovery | both feet + staff tip; wings settling; staff planted | A | `land_front`, `hit_fall_recover_front` |
| 16 | `front_staff_guard_windup` | south | action anticipation | both feet; wings hidden/folded; staff guard | A | `cast_front`, `guard_front`, `block_front` |
| 17 | `front_staff_guard_low` | south | guard/recovery | both feet + optional staff; wings hidden; staff guard | A | `guard_front`, `block_front`, cast recovery |
| 18 | `walk_front_right_lift` | south | walk release | left support/right released; wings hidden; staff carried | A | `walk_front_limited` |
| 19 | `front_crouch_reaction_staff_planted` | south | reaction/landing | both feet + staff tip; wings folded; staff planted | A | `hit_fall_recover_front`, landing failure recovery |
| 20 | `front_victory_cast` | south | action extreme | both feet; wings extended; staff attack | A | `victory_cast_front` |
| 21 | `fly_front_hover_neutral` | south | flight neutral | none; wings extended; staff carried | A | `takeoff_front`, `hover_front`, `land_front` |
| 22 | `fly_front_knee_up` | south | flight travel | none; wings extended; staff carried | A | `hover_front`, `air_reaction` |
| 23 | `fly_front_wings_up` | south | flap upstroke | none; wings up; staff carried | A | `hover_front`, `takeoff_front`, `land_front` |
| 24 | `fly_front_wings_down` | south | flap downstroke | none; wings down; staff carried | A | `hover_front`, `takeoff_front` |
| 25 | `fly_southeast_forward_glide` | southeast | air glide | none; wings extended; staff carried | A | `glide_southeast` |
| 26 | `fly_southwest_banked_staff` | southwest | air bank | none; wings banked; staff carried | B | `bank_left` |
| 27 | `fly_southeast_banked_staff` | southeast | air bank | none; wings banked; staff carried | A | `bank_right` |
| 28 | `fly_southeast_cheer` | southeast | air action | none; wings extended; staff carried | A | `celebrate_air` |
| 29 | `fly_southeast_staff_forward` | southeast | air action/travel | none; wings extended; staff attack | A | `air_staff_forward`, air cast transition |
| 30 | `front_run_charge_right_plant` | south | run plant | right support; wings hidden/folded; staff carried | A | `run_charge_front` entry |
| 31 | `front_crouch_landing_staff_plant` | south | landing contact | both feet + staff tip; wings folding; staff planted | A | `land_front` |
| 32 | `front_magic_staff_thrust` | south | cast release | both feet; wings extended/folded per source; staff attack | A | `cast_front` |
| 33 | `front_airborne_fall_back_staff` | south | hit/fall airborne | none; wings reactive; staff carried | A | `hit_fall_recover_front` |
| 34 | `front_celebrate_wings_staff_up` | south | celebration extreme | both feet; wings extended; staff raised | A | `celebrate_front` |
| 35 | `front_staff_block_horizontal` | south | block extreme | both feet; wings folded/hidden; staff guard | A | `block_front` |
| 36 | `front_point_direct_staff_held` | south | direction/speech | both feet; wings hidden; staff held | A | `point_front` |
| 37 | `front_celebrate_jump_staff_up` | south | celebration airborne | none; wings extended; staff raised | A | `celebrate_front` |
| 38 | `front_shush_secret_staff_held` | south | shush/speech | both feet; wings hidden; staff held | A | `shush_front` |
| 39 | `front_staff_spin_flourish` | south | flourish extreme | both feet or authored pivot; wings reactive; staff spin | A | `flourish_front` |

### 5.1 Direction capability policy

- **Tier A:** authored south ground/action/flight and southeast flight. These may be presented as full production behavior after their family gate.
- **Tier B:** north walk/idle, east/west profile idle/turn, southwest flight bank. These are intentionally reduced-motion but coherent.
- **Tier C:** an unsupported direction/action pair may use an explicit nearest-facing fallback only when the graph declares it. The UI and evidence must not describe it as authored omnidirectional motion.
- Full-body mirroring is forbidden by default because staff hand, staff hook, face asymmetry, and wing silhouette may become incorrect. A mirrored derivative requires its own pose ID, staff/hand/wing review, and graph entry.

## 6. Authored clip inventory and exact initial timing

Frame counts are authored at 24 FPS. The deterministic 60 Hz runtime resolves presentation frames from simulation ticks; ANIM never advances clips with browser wall time. Timing may be tuned only within the ranges below without a graph-contract change.

### 6.1 Idle and turn clips

| Clip | Loop | Samples (`pose:frames`) | Phase/contact rule | Exit rule |
|---|---|---|---|---|
| `idle_front` | loop | `front_idle:16` | fixed root; both feet | immediate to start/action; marker-gated to takeoff |
| `idle_back` | loop | `back_idle:16` | fixed root; both feet | immediate to back walk or turn |
| `idle_left` | loop | `profile_left:16` | fixed root; both feet | immediate to turn; Tier B static locomotion fallback |
| `idle_right` | loop | `profile_right:16` | fixed root; both feet | immediate to turn; Tier B static locomotion fallback |
| `turn_views` | once | source hold `2`, coherent target hold `4` | preserve world root and compatible support contact | finish in target idle; no hashed dissolve |

`turn_views` uses an explicit direction edge table. South-to-north routes through the nearer reviewed profile and lasts 8-12 frames. A rapid reversal may snapshot-handoff back through the same reviewed profile; it may not restart from the original source pose.

### 6.2 Ground locomotion clips

| Clip | Loop | Ordered samples | Markers and phase | Root rule |
|---|---|---|---|---|
| `walk_front_limited` | loop | `walk_front_left:4`, `front_idle:4`, `walk_front_right:4`, `walk_front_right_lift:4` | left contact `0.00`; left release/passing `0.25`; right contact `0.50`; right release `0.75`; loop `1.00` | distance-driven, contact locked |
| `walk_back_limited` | loop | `back_left:4`, `back_idle:4`, `back_right:4`, `back_idle:4` | same normalized contact pattern | distance-driven, contact locked |
| `run_charge_front` | once | `front_run_charge_right_plant:4`, `run_front_airborne_reach:2`, `run_front_airborne_drive:3` | right contact at entry; release frame 3; airborne frame 4; action commit frame 5 | ground distance then trajectory |
| `run_land_front` | once | `front_crouch_landing_staff_plant:3`, `front_kneel_staff_brace:5`, `front_idle:4` | landing contact frame 0; settled frame 5; recoverable frame 6 | preserve first contact, then fixed |

The front walk loop is an honest limited loop, not proof of a fully authored walk cycle. Before `M1`, the ANIM reviewer must approve a reciprocal left-lift breakdown or mark the loop asymmetric-but-acceptable in evidence. If no approved breakdown exists, speed is capped so each key pose reads as a deliberate held drawing. East/west movement uses profile holds with root translation only as Tier B; it must not fake stepping contacts.

Ground phase is computed from traveled distance:

```text
phase = (ground_distance / configured_stride_cells) mod 1.0
```

`configured_stride_cells` is frozen with FPSE at `CAP-140`. Changing render FPS does not change phase. Starting from idle selects the nearest first contact based on intended travel direction. Stopping waits for the next compatible contact marker unless an emergency stop is requested.

### 6.3 Flight clips

| Clip | Loop | Ordered samples | Markers | Root/altitude rule |
|---|---|---|---|---|
| `takeoff_front` | once | `front_idle:2`, `front_crouch_guard:4`, `fly_front_wings_down:3`, `fly_front_hover_neutral:4` | commit frame 5; airborne frame 6; down peak frame 7 | contact locked until commit, then air trajectory |
| `hover_front` | loop | `fly_front_hover_neutral:5`, `fly_front_knee_up:3`, `fly_front_wings_up:5`, `fly_front_wings_down:3` | up peak frame 10; down peak frame 14; loop frame 15 | altitude from runtime; bounded visual bob only |
| `glide_southeast` | loop | `fly_southeast_banked_staff:3`, `fly_southeast_forward_glide:10`, `fly_southeast_staff_forward:5` | bank apex frame 2; glide hold frames 3-12; loop frame 17 | air distance/trajectory |
| `bank_left` | once | `fly_front_hover_neutral:4`, `fly_southwest_banked_staff:5`, `fly_front_hover_neutral:3` | bank apex frame 6 | preserve altitude/flap phase |
| `bank_right` | once | `fly_front_hover_neutral:4`, `fly_southeast_banked_staff:5`, `fly_front_hover_neutral:3` | bank apex frame 6 | preserve altitude/flap phase |
| `air_reaction` | once | `fly_front_knee_up:3`, `front_reaction_jump_fist_staff:4`, `fly_front_hover_neutral:4` | action commit frame 2; recoverable frame 6 | air trajectory; no foot contact |
| `land_front` | once | `fly_front_wings_up:4`, `fly_front_wings_down:3`, `front_crouch_landing_staff_plant:3`, `front_kneel_staff_brace:5`, `front_idle:5` | landing contact frame 7; settled frame 12 | air trajectory until contact, then contact locked |

Flight phase continuity is preserved across `hover_front`, `glide_southeast`, `bank_left`, and `bank_right`. Banking chooses the closest wing phase and does not restart the flap. All pre-contact airborne samples declare no foot contact. Shadow position follows the ground-plane root; shadow scale/opacity responds monotonically to altitude and ignores wing/body bob.

### 6.4 Action, reaction, and speech clips

| Clip | Ordered samples (`pose:frames`) | Commit/effect/recovery | Ownership and interruption |
|---|---|---|---|
| `cast_front` | `front_idle:2`, `front_staff_guard_windup:5`, `front_magic_staff_thrust:2`, `magic_cast:5`, `front_staff_guard_low:3`, `front_idle:3` | commit 6; effect 8; recoverable 13 | body+staff+effect; marker-gated before commit, after-commit afterward |
| `guard_front` | `front_staff_guard_windup:4`, `front_crouch_guard:6`, `front_staff_guard_low:4`, `front_idle:3` | commit 3; recoverable 10 | body+staff; hold may extend while input held |
| `block_front` | `front_staff_guard_windup:3`, `front_staff_block_horizontal:5`, `front_staff_guard_low:4`, `front_idle:3` | commit 2; effect 3; recoverable 8 | body+staff; block hold may extend |
| `flourish_front` | `front_staff_guard_low:3`, `front_staff_spin_flourish:8`, `front_staff_guard_low:3`, `front_idle:3` | commit 2; effect 5; recoverable 10 | body+staff; staff channel exclusive |
| `victory_cast_front` | `front_staff_guard_windup:4`, `front_victory_cast:8`, `magic_cast:4`, `front_idle:4` | commit 3; effect 6; recoverable 14 | body+wings+staff+effect |
| `explain_front` | `front_idle:3`, `explaining:10`, `front_idle:3` | speech open 3; close 12 | upper body+mouth; locomotion root may continue only after M3 review |
| `point_front` | `front_idle:3`, `front_point_direct_staff_held:8`, `front_idle:3` | commit 4; recoverable 10 | body+staff; mouth may speak |
| `shush_front` | `front_idle:3`, `front_shush_secret_staff_held:10`, `front_idle:3` | shush start 3; shush end 12 | body+staff+mouth; shush suppresses all mouth writes during hold |
| `celebrate_front` | `front_celebrate_wings_staff_up:5`, `front_celebrate_jump_staff_up:4`, `front_reaction_jump_fist_staff:3`, `front_celebrate_wings_staff_up:5`, `front_idle:4` | commit 4; recoverable 15 | body+wings+staff; airborne middle samples have no contact |
| `celebrate_air` | `fly_front_hover_neutral:3`, `fly_southeast_cheer:8`, `fly_front_hover_neutral:4` | commit 2; recoverable 10 | body+wings+staff; preserves air trajectory |
| `air_staff_forward` | `fly_front_hover_neutral:3`, `fly_southeast_staff_forward:6`, `fly_southeast_forward_glide:5` | commit 2; effect 5; recoverable 8 | body+wings+staff; no foot contact |
| `hit_fall_recover_front` | `front_crouch_reaction_staff_planted:3`, `front_airborne_fall_back_staff:4`, `front_crouch_landing_staff_plant:3`, `front_kneel_staff_brace:5`, `front_idle:5` | commit 2; landing 7; recoverable 14 | body+wings+staff; uninterruptible fall until landing contact |

Every action has anticipation, readable extreme, and recovery. An action marker fires once per traversal even if an extreme hold is lengthened. The action system must never display two staffs, two heads, or detached hands while handing between poses.

## 7. Transition graph and legal topology

### 7.1 Mobility states

```text
grounded_idle
grounded_start
grounded_walk
grounded_run_burst
grounded_stop
grounded_turn
takeoff_anticipation
takeoff_committed
air_hover
air_travel
air_bank
air_reaction
landing_approach
landing_contact
landing_recovery
```

### 7.2 Required legal edges

| From | To | Gate | Phase/contact/root policy |
|---|---|---|---|
| grounded idle | start/walk | intent nonzero | choose nearest first contact; preserve root |
| walk | walk speed/facing change | continuous intent | preserve phase; nearest compatible contact |
| walk | stop/idle | speed below threshold | stop at next contact; lock planted foot |
| walk | run burst | run request | enter at right plant or wait at compatible contact |
| run burst | run land | airborne sequence complete | preserve trajectory to first landing contact |
| any grounded noncommitted action | turn | facing request | snapshot handoff through reviewed profile |
| grounded idle/walk stop | takeoff anticipation | flight request | both-foot contact preferred |
| takeoff anticipation | grounded idle | request released before commit | reverse anticipation coherently |
| takeoff committed | hover | airborne marker | no contact; preserve flap phase |
| hover | travel/bank | directional intent | preserve flap phase and altitude |
| travel/bank | hover | intent released | nearest flap phase; preserve air root |
| any air mobility | air reaction/action | action request | marker gate; preserve air trajectory |
| any stable air mobility | landing approach | descend/land request | preserve flap phase until approach |
| landing approach | landing contact | contact detected | emit once; lock first contact |
| landing contact | recovery/idle | settled marker | fixed root after settle |

### 7.3 Action overlay rules

- Ground actions may begin from idle immediately or from locomotion at a compatible contact/commit marker.
- Air actions preserve altitude and air trajectory unless the action explicitly supplies an impulse through FPSE.
- A body-exclusive action temporarily owns body pose selection; locomotion phase continues in semantic state so recovery can phase-match.
- Eyes, mouth, expression, and bounded secondary channels may continue unless the action owns or suppresses them.
- `shush_front` owns the mouth channel from `shush_hold_start` through `shush_hold_end`.
- Staff spin, block, thrust, and planted contact are staff-exclusive. No other channel may draw a second staff.
- Interruptions after `action_commit` route through that clip's authored recovery unless the target is a hit reaction or emergency landing.

### 7.4 Fallback rules

Fallbacks are explicit and auditable:

1. Unsupported diagonal ground action -> settle to `idle_front`, then play south action.
2. Unsupported east/west walking -> profile hold plus semantic translation, Tier B, no fake contact events.
3. Unsupported north action -> `turn_views` to south, then action, unless remote-control latency budget requires rejection.
4. Unsupported air facing -> nearest authored south/southeast/southwest clip with preserved altitude and a reviewed bank transition.
5. Invalid graph node at runtime -> `idle_front` when grounded or `hover_front` when airborne; emit diagnostics; never substitute an arbitrary pose.

## 8. Contact, phase, root, and altitude rules

### 8.1 Contact authority

`PoseSample.contact` and graph sample contacts must reach the compositor and evidence trace. The renderer may not infer contact from pose-name hashes or hardcoded walk phase.

Supported contact sets:

```text
none
left_foot
right_foot
both_feet
staff_tip
left_foot+staff_tip
right_foot+staff_tip
both_feet+staff_tip
left_hand
```

### 8.2 Root spaces

- `semantic_root`: world position from FPSE.
- `contact_root`: correction required to keep a declared planted anchor fixed.
- `visual_root_offset_cells`: authored integer-cell pose alignment.
- `secondary_offset`: bounded region-only integer offset; never changes semantic/contact roots.
- `altitude`: FPSE world altitude; not encoded by shifting the source pose alone.

Composition order:

```text
world projection -> semantic_root -> contact_root -> visual_root_offset -> region secondary offsets
```

The planted anchor may drift at most one local cell during a stance and zero cells after `landing_settled`. Fixed-world root displacement between adjacent rendered frames is at most one stage cell unless an authored attack/smear explicitly records the exception.

### 8.3 Ground phase rules

- Walk and run phases advance from accumulated ground distance, not elapsed render frames.
- A speed change preserves normalized phase.
- A facing change chooses the closest compatible contact phase.
- Reversal waits for a contact marker when possible, then enters the opposite-facing clip from matching support.
- Stopping completes within 250 ms after speed falls below the frozen threshold.
- A stationary character reaches zero root movement after settle.

### 8.4 Flight phase rules

- Flap phase is independent from body travel phase and persists across hover, glide, and bank.
- Downstroke is 2-3 authored frames; upstroke/settle is 4-7 authored frames.
- Flight body bob is a visual channel and does not modify altitude, collision, or shadow root.
- Bank direction is selected by signed turn intent; release returns to the closest hover sample.
- Landing cannot claim foot contact before FPSE reports contact and the `landing_contact` marker is traversed.

## 9. Limited-animation and transition strategy

### 9.1 Whole-character presentation

Most samples display one complete authored pose for a purposeful hold. Transitions use anticipation, contact matching, silhouette matching, and authored breakdowns. Crisp key-pose changes are preferable to fragmented pseudo-morphs.

Forbidden in production:

- coordinate-hash whole-body cell dissolve
- per-cell random reveal across the character
- color blending between poses
- alpha-blended ghost frames
- sub-cell translation
- whole-frame rescaling to conceal registration differences
- automatic mirroring of staff-bearing poses

### 9.2 Approved breakdowns

Breakdowns may be introduced only when all are true:

1. The source and target share a reviewed semantic region map.
2. Head, torso, staff, hands, feet, and both wings remain coherent connected regions.
3. The generated cell matrix is deterministic and schema-valid.
4. A contact sheet shows source, breakdown, target at native cell scale and at 4x nearest-neighbor scale.
5. An independent ANIM reviewer approves the silhouette and prop continuity.
6. The graph names the breakdown explicitly; it is not generated ad hoc at runtime.

### 9.3 Interruption snapshots

An interruption begins from the actually presented composite snapshot: current authored sample, root corrections, approved region offsets, expression, and mouth state. It must not restart from the full prior asset or from the beginning of the interrupted clip. Snapshot handoff lasts 0-4 frames and may adjust only explicit regions.

## 10. Secondary motion and visual channels

All channels are deterministic functions of 60 Hz state and graph phase. Their output is quantized to integer cells. No channel owns the semantic root.

| Channel | Input | Initial range | Suppression/ownership rule |
|---|---|---:|---|
| body bob | ground phase or flap phase | `y` +/-1 cell | zero during planted landing settle and precise staff plant |
| hat tip lag | angular/facing change | `x` +/-1, `y` +/-1 | suppressed when source mask cannot keep hat connected |
| beard lag | velocity delta/action release | `x` +/-1 | face and mouth anchors remain fixed |
| robe hem lag | ground/air velocity | `x` +/-1 | feet and planted contact masks excluded |
| wing reaction | flap phase/action accent | authored pose plus +/-1 region offset | wing pair remains present and attached; no procedural wing creation |
| staff tip lag | turn/action phase | +/-1 except authored attack | disabled during staff contact, block extreme, and handoff requiring <=1-cell tip drift |
| blink | deterministic blink schedule | eyelid region only | action may suppress; never moves root/head |
| eye aim | facing/attention target | approved eye mask only | stable anchor <=1 cell; no detached whites/irises |
| mouth/speech | speech level/phoneme class | mouth mask only | fully suppressed by shush hold; no brown beard columns inside mouth opening |
| magic effect | action marker + effect phase | bounded effect mask | may cover eyes/mouth for at most 2 frames unless authored and reviewed |

Channels apply in this order:

```text
base pose -> root/contact correction -> body secondary -> wings/robe/hat/beard/staff -> expression/eyes -> mouth -> effects
```

Channel ownership is exclusive per region. A channel that cannot acquire its region is skipped and reports a diagnostic; it never draws a duplicate region.

## 11. ANIM work breakdown

Sub-item IDs are subordinate to the shared `CAP-*` ledger. Their status is reported under the parent item; they do not create an alternate tracker.

### `CAP-110` - Metadata-complete pose loader and census (`C0-B`)

**Dependencies:** `CAP-100`.
**Lock:** `LOCK-GRAPH` for schema-facing metadata decisions.
**Owned paths:** `reference_avatar.py`, `reference_avatar_pose_cells.schema.json`, pose selection/quality modules, focused existing pose-library tests when within allowlist.

| Sub-item | Deliverable | Completion test |
|---|---|---|
| `ANIM-110-A` | load and validate all 39 IDs, facings, phases, contacts, roots, wing/staff modes | 39 unique entries; indexes 1..39; no unknown IDs |
| `ANIM-110-B` | deterministic pose census with counts by facing/family/tier/contact/wing mode | two runs produce byte-identical JSON and same asset hash |
| `ANIM-110-C` | detect metadata/source contradictions, especially airborne contact and required wings | strict tool exits nonzero for injected missing-wing or airborne-contact fixture |

**Commands:**

```bash
python3 -m unittest tests.wizard.test_reference_avatar_pose_library
python3 tools/generate_reference_avatar_pose_cells.py --check-deterministic
```

**Evidence:** `evidence/cartoon-animation-program/animation/CAP-110-pose-census.json` containing commit SHA, asset hash, 39 records, counts, and command results.
**Rollback:** revert metadata loader changes; generated pose-cell artifact remains at the prior verified hash.
**Handoff:** FPSE and INT acknowledge exact contact/root/altitude meanings; PLAN receives census hash; no pose remains unclassified.

### `CAP-120` - Graph v2 schema, validator, and taxonomy (`C0-C`)

**Dependencies:** `CAP-100`, `CAP-110`.
**Owned paths:** graph v2 JSON/schema, `animation_graph.py`, `tools/verify_motion_graph.py`, `test_animation_graph_v2.py`.

| Sub-item | Deliverable | Completion test |
|---|---|---|
| `ANIM-120-A` | strict graph v2 schema implementing Sections 4-5 | invalid enum, unknown field, missing contact, missing fallback all fail |
| `ANIM-120-B` | all 39 taxonomy entries and capability tiers | 39/39 reachable from a production clip; no duplicate index/use |
| `ANIM-120-C` | legal-edge and fallback validator | no wildcard edge, dead end, orphan clip, invalid successor, or cyclic once-only recovery trap |
| `ANIM-120-D` | winged/flying contract validator | flight clips require valid wing modes from takeoff commit through landing contact |

**Commands:**

```bash
python3 tools/verify_motion_graph.py --graph wizard_avatar/definitions/reference_avatar_animation_graph.v2.json --strict
python3 -m unittest tests.wizard.test_animation_graph_v2
```

**Evidence:** graph SHA-256, schema SHA-256, reachability report, 39-row taxonomy report, and wing-contract result in `evidence/cartoon-animation-program/animation/CAP-120-graph-contract.json`.
**Rollback:** graph v2 remains inert; graph v1 stays selected.
**Handoff:** release `LOCK-GRAPH` only after strict validation; all four roles acknowledge schema hash before `CAP-140`.

### `CAP-300` - Evaluator, clips, markers, and events (`A1-A`)

**Dependencies:** `CAP-140`.
**Owned paths:** `animation_graph.py`, `motion.py`, graph v2 JSON, clip/marker tests.

| Sub-item | Deliverable | Completion test |
|---|---|---|
| `ANIM-300-A` | deterministic clip evaluator driven by `PresentationState.tick` and phase fields | repeated traces have byte-identical sample/event hashes |
| `ANIM-300-B` | exact frame-duration and phase-boundary evaluation at 24 FPS over 60 Hz | no fractional simulation step is created by ANIM; boundary tests pass |
| `ANIM-300-C` | exactly-once marker/event traversal, including skipped presentation frames and loop boundaries | each marker count equals expected traversal count |
| `ANIM-300-D` | channel-ownership and fallback result in evaluator output | invalid clip returns declared grounded/air fallback and diagnostic |

**Commands:**

```bash
python3 -m unittest tests.wizard.test_clip_playback
python3 -m unittest tests.wizard.test_animation_markers
```

**Evidence:** `CAP-300-evaluator-trace.json` with input state hashes, selected sample IDs, marker sequence, and result hash.
**Rollback:** select graph v1; evaluator code remains unused by active frame source.
**Handoff:** INT can feed a frozen `PresentationState` and receive sample, contacts, markers, roots, channel ownership, and fallback diagnostics without a wall-clock parameter.

### `CAP-310` - Authored clip inventory and topology (`A1-B`)

**Dependencies:** `CAP-300`.
**Owned paths:** graph v2 JSON, pose selection/motion, graph/clip/contact tests.

| Sub-item | Deliverable | Completion test |
|---|---|---|
| `ANIM-310-A` | idle/turn/front and back limited walk/run/recovery clips | ground matrix `VR-GND-*` ready; contacts alternate or limitation is explicit |
| `ANIM-310-B` | takeoff/hover/glide/bank/reaction/landing clips | flight matrix `VR-FLY-*` ready; no airborne foot contact |
| `ANIM-310-C` | complete action/reaction/speech inventory | every pose 9-10 and 13-20 and 28-39 is production-reachable |
| `ANIM-310-D` | explicit legal successors and capability-tier fallbacks | reachability/topology strict gate passes |

**Commands:**

```bash
python3 -m unittest tests.wizard.test_clip_playback
python3 -m unittest tests.wizard.test_contact_continuity
python3 tools/verify_motion_graph.py --strict
```

**Evidence:** one contact sheet per clip; machine-readable clip inventory; topology DOT/JSON; `CAP-310-clip-review.md`.
**Rollback:** remove failed clip from v2 promotion set, restore its explicit fallback, keep graph v1 active.
**Handoff:** FPSE confirms stride/altitude inputs; INT receives promotion-ready family lists in M1/M2/M3 order; PLAN receives compact evidence links.

### `CAP-320` - Transition recipes and interruption snapshots (`A1-C`)

**Dependencies:** `CAP-300`, `CAP-310`.
**Owned paths:** graph/evaluator, pose compositor/selection, transition/contact tests.

| Sub-item | Deliverable | Completion test |
|---|---|---|
| `ANIM-320-A` | phase/contact-matched locomotion transitions | phase jump <= `1/16`; planted drift <=1 local cell |
| `ANIM-320-B` | takeoff/flight/landing recipes | flap phase preserved; first landing contact emitted once |
| `ANIM-320-C` | action entry/commit/recovery recipes | every action has legal entry, interrupt, recovery, fallback |
| `ANIM-320-D` | interruption from actual presented snapshot | rapid reversal/action tests never restart from stale full source pose |
| `ANIM-320-E` | delete/disable production coordinate-hash body dissolve | strict validator finds zero production uses |

**Commands:**

```bash
python3 -m unittest tests.wizard.test_transition_recipes
python3 -m unittest tests.wizard.test_contact_continuity
python3 tools/verify_motion_visuals.py --headless --family transitions --strict
```

**Evidence:** transition matrix with source/target/marker/root/contact, interruption traces, and nearest-neighbor contact sheets.
**Rollback:** set family transition recipe to coherent marker-gated hard cut; if still failing, omit family from promotion and use graph v1.
**Handoff:** INT receives recipe IDs and interruption-snapshot fields; no frame-source edits are required from ANIM.

### `CAP-330` - Visual channels and secondary motion (`A1-D`)

**Dependencies:** `CAP-320`.
**Owned paths:** pose compositor/reference avatar/quality, graph visual channels, visual-channel tests.

| Sub-item | Deliverable | Completion test |
|---|---|---|
| `ANIM-330-A` | deterministic blink, eye aim, expression, and mouth masks | visible pixel changes with zero root/head movement; anchors <=1 cell |
| `ANIM-330-B` | shush mouth ownership and speech suppression | zero mouth writes during shush hold |
| `ANIM-330-C` | body/hat/beard/robe/wing/staff secondary channels | integer offsets in configured bounds; no detached regions |
| `ANIM-330-D` | magic effect channel and coverage limit | eyes/mouth covered <=2 frames unless an approved exception exists |
| `ANIM-330-E` | channel conflict diagnostics | duplicate writer fixture fails; production trace has zero conflicts |

**Commands:**

```bash
python3 -m unittest tests.wizard.test_visual_channels_v2
python3 tools/verify_motion_visuals.py --headless --family channels --strict
```

**Evidence:** channel-isolation contact sheets, per-channel cell-diff counts, anchor traces, and `CAP-330-channel-review.json`.
**Rollback:** disable individual channel in graph v2; body clip selection remains valid.
**Handoff:** INT receives a compositor result that already owns visual regions; SYS/browser code never implements character-region animation.

### Promotion support: `CAP-610`, `CAP-620`, `CAP-630`, `CAP-710`

ANIM does not own integration edits but provides an independent reviewer and blocks promotion on visual failures.

| Parent | ANIM responsibility | Handoff/pass condition |
|---|---|---|
| `CAP-610` / `M1` | review idle/start/walk/turn/stop/run on integrated Python runtime | all `VR-GND-*` rows pass; contact/root trace attached |
| `CAP-620` / `M2` | review takeoff/hover/flap/glide/bank/land | all `VR-FLY-*` rows pass; altitude/shadow trace attached |
| `CAP-630` / `M3` | review actions/reactions/speech/expression while grounded and airborne | all `VR-ACT-*` rows pass; marker/channel logs attached |
| `CAP-710` / `V2` | independently review real Chromium presentation on live `8765` | zero hard failures, source/decoded/presented hash parity, signed review matrix |

## 12. Automated tests and commands

### 12.1 ANIM focused gate

```bash
python3 tools/verify_motion_graph.py --strict
python3 -m unittest tests.wizard.test_animation_graph_v2
python3 -m unittest tests.wizard.test_clip_playback
python3 -m unittest tests.wizard.test_animation_markers
python3 -m unittest tests.wizard.test_transition_recipes
python3 -m unittest tests.wizard.test_contact_continuity
python3 -m unittest tests.wizard.test_visual_channels_v2
python3 tools/verify_motion_visuals.py --headless --strict
```

### 12.2 Regression gate after each ANIM parent item

```bash
python3 -m unittest discover tests
python3 tools/generate_reference_avatar_pose_cells.py --check-deterministic
python3 tools/verify_motion_graph.py --strict
python3 tools/verify_animation_quality.py --strict
git diff --check
```

### 12.3 Integrated live gate

Only INT/coordinator runs the live server under `LOCK-PORT-8765`:

```bash
python3 tools/run_wizard_avatar_server.py --host 127.0.0.1 --port 8765 --cols 240 --rows 135 --fps 24
python3 tools/verify_remote_control.py --url http://127.0.0.1:8765 --strict
python3 tools/verify_live_cartoon_browser.py --url http://127.0.0.1:8765 --browser chromium --strict
```

ANIM consumes the resulting recording, screenshots, state/marker trace, and browser metrics. ANIM does not bind or restart `8765` from its worktree.

## 13. Concrete visual review matrices

Every row produces: input script ID, graph hash, pose-library hash, start/end ticks, screenshot/contact-sheet paths, state/marker trace, numeric metrics, reviewer, and pass/fail reason.

### 13.1 Ground matrix

| ID | Setup and observation | Pass gate |
|---|---|---|
| `VR-GND-001` | front idle for 5 seconds | fixed root 0 after settle; no detached face/staff; deterministic blink only |
| `VR-GND-002` | idle -> front walk -> 3 complete cycles | contact order L/release/R/release repeats; drift <=1 local cell |
| `VR-GND-003` | walk speed 25% -> 100% -> 50% | phase continuous; world distance/cycle within +/-5% stride |
| `VR-GND-004` | walk -> release -> stop | stop <=250 ms after threshold; stops on compatible contact; root 0 after settle |
| `VR-GND-005` | walk -> run burst -> landing recovery | one plant, airborne section, one landing contact, no foot contact in air |
| `VR-GND-006` | south -> east -> north -> west -> south turns | coherent silhouettes; no hash dissolve; root <=1 cell adjacent frame |
| `VR-GND-007` | rapid left/right reversals every 300 ms | snapshot handoff; no stale-source restart; no duplicated staff/head |
| `VR-GND-008` | north limited walk for 3 cycles | honest Tier B label; alternating back contacts; no fabricated wings |
| `VR-GND-009` | east/west movement fallback | profile hold remains coherent; no contact events claimed as a full walk |
| `VR-GND-010` | interrupt walk with block, then resume | action marker once; locomotion phase resumes within `1/16` |

### 13.2 Flight matrix

| ID | Setup and observation | Pass gate |
|---|---|---|
| `VR-FLY-001` | idle -> takeoff -> hover | takeoff commit once; no foot contact after airborne; wings present |
| `VR-FLY-002` | hover for 5 flap loops | up/down order stable; no phase reset; body bob <=1 visual cell |
| `VR-FLY-003` | hover -> southeast glide -> hover | flap phase continuity <=`1/16`; altitude continuous |
| `VR-FLY-004` | hover -> left bank -> hover | southwest bank readable; wings/staff attached; altitude stable |
| `VR-FLY-005` | hover -> right bank -> hover | southeast bank readable; wings/staff attached; altitude stable |
| `VR-FLY-006` | ascend 20 cells, hold, descend 10 | altitude trace monotonic with command; no contact; shadow response monotonic |
| `VR-FLY-007` | air reaction during forward travel | action preserves air root/trajectory; marker once; no landing event |
| `VR-FLY-008` | air staff forward and celebrate air | each staff/body channel singular; required wings remain visible |
| `VR-FLY-009` | hover -> landing -> idle | first contact once; planted drift <=1; root 0 after settled marker |
| `VR-FLY-010` | landing request canceled before contact | coherent return to closest hover flap phase; no false contact event |

### 13.3 Action and channel matrix

| ID | Setup and observation | Pass gate |
|---|---|---|
| `VR-ACT-001` | cast from idle | anticipation 4-6 frames; commit/effect once; extreme >=2 frames |
| `VR-ACT-002` | guard hold then release | hold extends without marker repeats; authored recovery completes |
| `VR-ACT-003` | block during walk | enters on compatible contact; one staff; resumes phase <=`1/16` |
| `VR-ACT-004` | flourish then reverse direction | staff spin exclusive; snapshot transition; no duplicate tip/hand |
| `VR-ACT-005` | victory cast | wings required; magic covers eyes/mouth <=2 frames |
| `VR-ACT-006` | explain with speech level sweep | mouth anchors <=1 cell; root unchanged; one face |
| `VR-ACT-007` | point while speaking | staff/hand attached; mouth independent; marker once |
| `VR-ACT-008` | shush while speech input remains high | zero mouth writes during hold; resumes only after end marker |
| `VR-ACT-009` | ground celebration | airborne samples claim no contact; landing/recovery coherent |
| `VR-ACT-010` | hit/fall/recover | fall uninterruptible to contact; landing once; no wing loss |
| `VR-ACT-011` | deterministic blink and eye aim over idle/walk/flight | eye/head root unchanged; no detached eye pixels or white seams |
| `VR-ACT-012` | all secondary channels at maximum reviewed input | offsets in bounds; no disconnected hat/beard/robe/wing/staff region |

### 13.4 Control-stress observations

These rows are executed by SYS/INT; ANIM reviews presentation:

| ID | Input sequence | Visual gate |
|---|---|---|
| `VR-CTL-001` | key down/up at 100 ms intervals | no stuck locomotion; transitions use current snapshot |
| `VR-CTL-002` | rapid ground/flight mode toggles around takeoff commit | pre-commit reverses; post-commit finishes legal air transition |
| `VR-CTL-003` | action spam across commit windows | no marker duplication, prop duplication, or illegal dead end |
| `VR-CTL-004` | controller lease expires during walk and flight | controlled stop/hover; no teleport or pose-list reset |
| `VR-CTL-005` | two input sources alternate ownership | animation follows accepted controller epoch only; phase remains coherent |

## 14. Measurable animation gates

### 14.1 Contract and topology

- Exactly 39 unique pose taxonomy entries and 39/39 production-reachable uses.
- Zero unknown pose IDs, orphan clips, dead-end production clips, wildcard transitions, or unresolved fallbacks.
- Every production node has legal entry, interruption policy, recovery, and fallback.
- Every flight sample after `takeoff_commit` and before `landing_contact` satisfies the accepted wing contract.
- Graph, schema, and pose-library SHA-256 values are recorded and match runtime bootstrap evidence.

### 14.2 Timing and events

- Standard authored rate is exactly 24 FPS; simulation input is exactly 60 Hz.
- Phase jump across compatible locomotion/flight changes is <=`1/16`.
- Each marker emits exactly once per declared traversal/loop policy.
- Action extremes remain visible at least 2 rendered frames.
- Standard anticipation is 4-6 frames; tiny anticipation 2-3; recovery 3-8 unless the clip table explicitly states otherwise.
- Ground stop completes within 250 ms after the runtime threshold.

### 14.3 Contact, root, and prop continuity

- Planted foot drift <=1 local cell through stance.
- Fixed-world root jump <=1 stage cell between adjacent frames and 0 after settle.
- Stable staff hand/tip drift <=1 local cell except a declared attack/spin accent.
- Eye and mouth anchor drift <=1 local cell between compatible frames.
- Walk world distance per cycle is within +/-5% of configured stride.
- Exactly one coherent head/face and at most one connected staff in every production frame.
- Zero foot contact claims in airborne samples; exactly one first-contact and one settled marker in landing.

### 14.4 Rendering and silhouette

- Zero coordinate-hash full-body dissolves in production graph v2.
- Zero antialiased cells, color-interpolated cells, sub-cell placements, or whole-character per-frame scaling.
- Zero detached eyes, mouth, hands, feet, staff tip, hat, beard, robe hem, or wing regions.
- Required wings remain present and readable through flight/action transitions; unexplained wing additions/removals are hard failures.
- Magic/effects may cover eyes or mouth for at most 2 consecutive frames unless explicitly authored and approved.

### 14.5 Acceptance authority

Automated success does not override a hard visual failure. `M1`, `M2`, `M3`, and `V2` require an independent ANIM reviewer who did not implement the failing/passing transition. A failed row blocks its parent promotion.

## 15. Rollback points

| Rollback point | Trigger | Action | Preserved evidence |
|---|---|---|---|
| `RB-ANIM-0` | `CAP-110/120` contract failure | revert metadata/graph-v2 data; retain graph v1 | census, schema errors, hashes |
| `RB-ANIM-1` | evaluator/marker nondeterminism | keep evaluator disconnected; graph v1 active | divergent traces and seeds/inputs |
| `RB-ANIM-2` | one clip family fails `A1` | remove family from promotion set; use explicit fallback | contact sheets, failed metrics |
| `RB-ANIM-3` | transition glitch | use authored marker-gated coherent cut; disable recipe | source/target snapshots and trace |
| `RB-ANIM-4` | secondary channel glitch | disable only the channel in v2 | isolated channel diffs |
| `RB-ANIM-5` | integrated `M1/M2/M3` failure | set `WIZARD_ANIMATION_GRAPH=v1`; INT restarts last verified Python SHA | browser recording, graph/runtime hashes |

Rollback never activates Rust, introduces a second renderer, regenerates all source assets, or rewrites shared Git history. Failed visual evidence is preserved before rollback.

## 16. Evidence outputs

Compact committed evidence belongs under:

```text
evidence/cartoon-animation-program/animation/
  CAP-110-pose-census.json
  CAP-120-graph-contract.json
  CAP-300-evaluator-trace.json
  CAP-310-clip-review.md
  CAP-320-transition-review.json
  CAP-330-channel-review.json
  M1-ground-review.json
  M2-flight-review.json
  M3-action-review.json
  V2-live-visual-review.md
```

Large recordings, raw frame dumps, and browser traces remain workflow artifacts. Each committed summary links the artifact identifier and records:

```text
work_item_id
gate_id
commit_sha
graph_sha256
schema_sha256
pose_library_sha256
runtime_epoch
command
exit_code
test_total
metric_values
visual_matrix_rows
reviewer
review_timestamp_utc
artifact_links
known_limitations
rollback_flag_or_sha
```

Screenshots/contact sheets are captured at native cells and 4x nearest-neighbor scale. They include clip/sample IDs and tick numbers outside the character image; overlays must not obscure the sprite.

## 17. Handoff criteria and template

An ANIM parent item is `REVIEW_READY` only when:

1. Every sub-item is complete or explicitly blocked.
2. Focused tests and the full regression gate pass.
3. Changed paths are within the ANIM allowlist.
4. Graph/schema/asset hashes are recorded.
5. Required visual matrix rows are reviewed.
6. Rollback behavior is tested or proven inert behind graph v1.
7. Known Tier B/C limitations are stated without claiming unsupported motion.
8. No Rust file, dependency, command, CI job, or acceptance gate was added.

Every handoff uses this exact payload:

```text
WORK_ITEM:
SUB_ITEMS:
BASE_SHA:
HEAD_SHA:
LOCK_CLAIMED:
LOCK_RELEASED:
CHANGED_PATHS:
COMMANDS_RUN:
RESULTS:
GRAPH_SHA256:
SCHEMA_SHA256:
POSE_LIBRARY_SHA256:
VISUAL_ROWS:
EVIDENCE_PATHS:
KNOWN_LIMITATIONS:
ROLLBACK:
CONTRACT_ACK_REQUIRED_FROM:
READY_FOR:
```

`READY_FOR` is one of `CAP-140`, `CAP-600`, `CAP-610`, `CAP-620`, `CAP-630`, or `CAP-710`. INT rejects a handoff with missing hashes, missing visual rows, out-of-allowlist changes, or ambiguous rollback.

## 18. Definition of ANIM complete

ANIM planning and implementation are complete only when:

- all 39 poses are classified and used intentionally;
- ground, run burst, takeoff, hover, glide, bank, landing, action, reaction, speech, and expression families have legal deterministic clips;
- phase, contact, root, altitude, event, interruption, and channel contracts pass focused tests;
- no production transition fragments the body with a hash dissolve;
- the accepted rainbow-wing flying design survives every applicable gate;
- all `VR-GND-*`, `VR-FLY-*`, `VR-ACT-*`, and `VR-CTL-*` rows required by promotion pass;
- graph v2 can be disabled cleanly in favor of graph v1;
- INT has accepted the ANIM handoffs for `M1`, `M2`, `M3`, and `V2`;
- the live Python service on port `8765`, at the pushed SHA, presents the same source/decoded/presented animation hashes with zero hard visual failures.

This plan does not authorize expanding scope into Rust, replacing ASCILINE, or treating the pose reel as completed character animation.
