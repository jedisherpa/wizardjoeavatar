# Research Wave 1: Game Animation And Character Motion

Role: `ANIM`
Research date: 2026-07-12
Repository inspected: `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar`
Production target: the server-authoritative ASCILINE Python runtime and direct-cell compositor served at `http://127.0.0.1:8765/`, with TypeScript controls and presentation. Rust is explicitly out of production scope for this program.

## Executive Finding

WizardJoe currently has a strong library of **39 readable key poses**, a fixed-step world-motion controller, a canonical cell canvas, semantic commands, and a crisp nearest-neighbor browser presentation path. It does **not** yet have 39 poses organized as animation. Most of the new poses are reachable only through the timed pose override/showcase reel. The production animation graph still defines only eight-direction idle lookup, six action overrides, and walking clips. It has no authored takeoff, flight, landing, run, reaction, celebration, staff-combat, or conversational clip timelines.

The right next step is not a more elaborate universal crossfade. It is a deterministic **cartoon clip and state system** in Python:

1. Group key poses into named clips with non-uniform frame durations.
2. Add anticipation, action, hold, recovery, and interrupt windows.
3. Add contact, apex, release, impact, and effect markers.
4. Preserve distance-driven phase for grounded locomotion and add explicit altitude/flight phase for air motion.
5. Replace arbitrary cell-dissolve transitions with authored breakdowns, coherent pose holds/swaps, and small cell-aligned secondary offsets.
6. Keep the server authoritative; TypeScript sends continuous input intent and presents complete server frames only.

This is deliberately closer to hand-authored limited cartoon animation than skeletal interpolation. The source material is raster-like square-cell art with different topology from pose to pose. A full-body cell morph will often create two staffs, broken wings, shredded faces, or noisy silhouettes. The system should make the **timing and pose choice** fluid while keeping every displayed silhouette intentional and crisp.

## Research Method And Scope

I inspected the current dirty working tree rather than treating the last commit as authoritative. Relevant current surfaces included:

- the 39-pose source manifest and generated cell library;
- the Python state, locomotion, selection, transition, rendering, streaming, and semantic-control code;
- the browser controls and frame-presentation client;
- the numbered movement, skeleton, channel, and browser requirements;
- pose-expansion grouping and browser-verification evidence;
- current Python transition tests and the strict quality harness;
- the live state and diagnostics endpoint at `http://127.0.0.1:8765/api/avatar/wizard/state`.

Technical recommendations were compared against official engine documentation and first-party animation-production material. Unreal, Godot, Unity, and Aseprite concepts are used as **design analogies**, not as dependencies. All proposed production mechanisms remain implementable in Python, JSON, the existing direct-cell compositor, and TypeScript.

## Exact Current State

### 1. The asset library is canonical and broad, but not yet clip-complete

The source manifest fixes every pose to a `72 x 96` canonical space with root `(36, 95)` and baseline `95` (`assets/reference/motion_sources/manifest.json:5-15`). It also defines default mouth, eye, foot, hand, and staff anchors (`assets/reference/motion_sources/manifest.json:17-58`). This is a sound base for stable registration and overlay ownership.

The generated library preserves the canonical root and contains local anchors per pose (`wizard_avatar/definitions/reference_avatar_pose_cells.json:1-20`, `wizard_avatar/definitions/reference_avatar_pose_cells.json:27-106`). However, the palette is still identified as `per_pose_quantized_64`, and the generated aggregate reports 1,974 unique colors (`assets/reference/motion_sources/manifest.json:16`, `wizard_avatar/definitions/reference_avatar_pose_cells.json:17-20`). That makes palette shimmer during pose changes a real risk even when geometry is stable.

Current manifest distribution, calculated from the inspected file:

| Property | Current count |
|---|---:|
| Total poses | 39 |
| South-facing | 26 |
| Southeast-facing | 6 |
| Southwest-facing | 2 |
| North, northeast, northwest, east, west | 1 each |
| Poses with an authored phase | 15 |
| Poses with no phase | 24 |
| Flying poses | 9 |
| Walking poses | 5 |
| Running poses | 3 |
| Jump, airborne, landing, kneel poses | 5 total |

The manifest itself shows the asymmetry. The four base direction poses and four old movement poses occupy `manifest.json:62-197`; most expansion poses are south-facing from `manifest.json:239` onward. The frontal flight cycle has useful quarter phases at `manifest.json:833-1084`, while bank/glide poses are concentrated in southeast/southwest at `manifest.json:1086-1406`. The library therefore supports rich **front-facing performance** now, but not equally rich eight-direction performance.

### 2. The production animation graph exposes only a fraction of the library

The current graph has:

- eight idle-by-facing entries (`wizard_avatar/definitions/reference_avatar_animation_graph.json:7-16`);
- six action pose overrides (`reference_avatar_animation_graph.json:17-24`);
- walking clips only (`reference_avatar_animation_graph.json:25-164`).

There are no graph sections for run, takeoff, hover, flap, glide, bank, fall, land, celebrate, reaction, staff combat, or gesture sequences. The schema requires only `idle_by_facing`, `action_pose_overrides`, and `walking_clips` (`wizard_avatar/definitions/reference_avatar_animation_graph.schema.json:6-14`) and its clip model contains only phase, pose ID, and an optional contact string (`reference_avatar_animation_graph.schema.json:71-107`). It has no per-sample duration, marker/event track, root policy, transition rule, interrupt window, looping segment, playback rate, or channel mask.

Several idle mappings are semantically wrong because they reuse walking poses. Southwest idle maps to `walk_front_left`, southeast idle to `walk_front_right`, northwest idle to `back_left`, and northeast idle to `back_right` (`reference_avatar_animation_graph.json:7-16`). A live inspection reproduced this: the stopped server reported `locomotion: idle`, `facing: southwest`, and `pose_id: walk_front_left`. That mismatch will always read as a frozen step rather than a settled character.

### 3. Locomotion phase is correctly distance-driven, but clip use is rudimentary

The numbered contract requires distance-driven walk phase and cell-aligned motion (`docs/15-procedural-walking.md:1-38`). The Python implementation does this: it advances phase by distance travelled divided by a `0.85` stride (`wizard_avatar/locomotion.py:13-16`, `wizard_avatar/locomotion.py:91-97`). The controller also runs a fixed 60 Hz simulation (`wizard_avatar/locomotion.py:13-15`, `wizard_avatar/controller.py:24-31`). These are important assets and should be retained.

Current limitations:

- Movement is reduced to `walking` whenever planar velocity exceeds a threshold, otherwise `idle` (`wizard_avatar/locomotion.py:29-42`). It cannot authoritatively enter running, flying, falling, or landing from motion.
- World state has only x/z position and x/z velocity (`wizard_avatar/models.py:102-128`). There is no altitude, vertical velocity, flight mode, grounded flag, turn state, desired input vector, or animation clip state.
- Facing advances one octant toward velocity per 60 Hz tick (`wizard_avatar/locomotion.py:34-42`). This is technically ordered but visually too fast and has no turn anticipation or foot-phase gate.
- The selected `PoseSample.contact` is discarded after pose selection; rendering uses only `pose_sample.pose_id` (`wizard_avatar/frame_source.py:79-88`).
- Shadow lift is a single global test for walking phase `0.15 < phase < 0.38` (`wizard_avatar/frame_source.py:97-101`). It does not use left/right/both/none contact markers and is wrong for flight, jumping, landing, kneeling, and staff plants.

The existing front walk clip has four samples but uses `front_idle` for both intermediate beats (`reference_avatar_animation_graph.json:25-50`). West and east walking each hold one static profile pose (`reference_avatar_animation_graph.json:68-77`, `reference_avatar_animation_graph.json:137-146`). This proves state selection but does not produce a convincing side walk. The expansion adds only one explicit right-foot lift (`manifest.json:658-714`), so a reciprocal eight-beat walk cannot be honestly authored from current whole-body poses alone.

### 4. The current transition is a universal spatial dissolve

Every pose change uses one fixed transition length of about 120 ms (`wizard_avatar/frame_source.py:41-53`). The compositor aligns roots, then uses a position hash to choose source or target cells at each intermediate progress (`wizard_avatar/pose_compositor.py:63-101`, `wizard_avatar/pose_compositor.py:124-127`). Smoothstep changes the number of cells switched over time (`wizard_avatar/frame_source.py:155-170`, `wizard_avatar/frame_source.py:320-322`), but it does not preserve semantic regions or coherent silhouettes.

Animation consequences:

- Topologically unrelated poses coexist as scattered source and destination cells during the dissolve.
- A staff, wing, face, hand, or robe edge can appear doubled or fragmented.
- All transitions have the same duration regardless of whether the beat is a quick attack, a heavy landing, a conversational settle, or a slow turn.
- The transition starts from the prior **pose asset**, not a snapshot of the currently presented intermediate image. If a new command interrupts a transition, the next transition can jump to the full previous target (`wizard_avatar/frame_source.py:141-169`).
- Only the target mouth anchor is translated during the transition (`wizard_avatar/frame_source.py:157-170`); no comparable semantic ownership exists for eyes, feet, staff, wings, or effect origins.

The crisp-transition unit test proves deterministic endpoint selection and that intermediate cells come from either endpoint (`tests/wizard/test_crisp_pose_transition.py:20-51`). It does not prove coherent silhouettes, absence of duplicate props, meaningful spacing, contact continuity, or interruption continuity.

### 5. The 39-pose Play demo is a coverage reel, not an animation performance

The Play button fetches all pose IDs, starts a looping path, holds each pose for 900 ms, and issues timed pose overrides (`web/avatar/wizardControls.ts:48-80`). This is a good library coverage check. Evidence confirms 39/39 poses, 258 world positions, intermediate transition progress, and zero browser console errors (`evidence/pose-library-expansion/DEMO_PLAY_VERIFICATION.md:1-30`).

It should not be used as proof of believable animation. A 900 ms sequential gallery ignores clip semantics, compatible neighbors, action timing, contact, direction, and state. The grouping document already warns that Play is a moving library reel and that action/showcase clips are a future layer (`docs/pose-library-expansion/RUNTIME_GROUPING_PLAN.md:7-16`).

### 6. Semantic remote control exists, but input is command-like rather than character-like

The Python server exposes semantic move, path, circle, figure-eight, face, action, pose, expression, speak, stop, and reset routes (`wizard_avatar/server.py:65-128`). This is the right authority boundary. The numbered contract also requires that browser controls send semantic commands and never move the character only on the client (`docs/28-browser-demo-controls.md:32-35`).

The present keyboard layer sends one fixed destination per keydown and ignores key repeats (`web/avatar/wizardControls.ts:24-45`). There is no keyup handling, held-input vector, analog magnitude, dead-man timeout, takeoff/land input, or server-side input sequence number. This feels like clicking destinations, not remotely steering a cartoon character.

Browser presentation is already responsibly decoupled from simulation. It buffers decoded complete frames and presents on `requestAnimationFrame` (`web/avatar/wizardClient.ts:184-223`). That should remain a presentation clock only; animation state and clip progression should remain in Python.

### 7. The original procedural contract anticipated secondary motion, but the pose path does not apply it

The numbered walking specification calls for body bob, hat lag, beard lag, staff lag, arm opposition, and boot lift (`docs/15-procedural-walking.md:16-34`). The joint specification defines a useful semantic hierarchy from root through hips, limbs, staff hand, and staff top (`docs/14-joint-skeleton.md:1-58`). The independent-channel contract requires locomotion, upper body, face, speech, and staff ownership (`docs/23-animation-channels.md:1-45`).

The current reference-pose renderer displays whole generated pose cells plus mouth/effect overlays. It does not yet use stable body-region masks or joint/region transforms to add hat, beard, robe, wing, arm, or staff follow-through. This is why simply adding more full-body poses cannot by itself satisfy the original cartoon-motion intent.

## Gap Between Integrated Poses And Continuous Cartoon Animation

| Needed quality | Current state | Concrete gap |
|---|---|---|
| Readable idle | Front/back/profile images exist | No breathing, blink timing integration, hat/beard settle, or true diagonal idle |
| Responsive walk | Distance phase exists | Missing reciprocal passing/up poses, side-view gait, contact-driven shadow, start/stop clips |
| Run/charge | Three poses exist | No run clip, phase markers, acceleration transition, foot rhythm, or run-to-land recovery |
| Flight | Nine poses exist | No altitude state, takeoff/land graph, flap timing, lift response, bank steering, or airborne shadow policy |
| Turns | Eight view families exist | No authored turn state, angular speed, contact-gated view switch, or direction-compatible clips |
| Actions | Many strong key poses exist | Mostly unreachable from action graph; no anticipation/attack/hold/recovery timelines |
| Interruptibility | Commands can replace state | Interruption restarts from an asset rather than the currently presented pose and velocity |
| Secondary motion | Contract mentions hat/beard/staff lag | No region masks, additive offsets, spring/lag state, or settle logic on reference poses |
| Crisp transitions | Cells stay unblurred | Universal hashed dissolve fragments silhouettes and props |
| Remote-control feel | Semantic endpoints exist | Keydown sends fixed destinations; no held intent, keyup, TTL, analog speed, or flight controls |
| Evidence | 39/39 reel and 32 scenario harness exist | No clip-by-clip motion curves, contact drift, interruption, silhouette, or input-latency gates |

## Animation Principles Applied To This Character

Muriel Cartwright's GDC Animation Bootcamp material summarizes a useful action structure as **anticipation, smear, attack, return to idle**, and emphasizes key poses plus follow-through. That model maps directly onto WizardJoe's limited-animation vocabulary: the supplied images are keys; the system needs timed holds, selective breakdowns, effect/smear frames, and recoveries rather than a noisy interpolation between every pair. [GDC, *Fluid and Powerful Animation*](https://media.gdcvault.com/GDC2014/Presentations/Cartwright_Muriel_Animation_Bootcamp_Fluid.pdf)

Official engine systems consistently separate three concerns:

1. **State topology:** idle/walk/run/jump states with explicit allowed transitions. [Epic State Machines](https://dev.epicgames.com/documentation/unreal-engine/state-machines-in-unreal-engine)
2. **Phase synchronization:** related locomotion clips share markers so feet do not desynchronize during blends. [Epic Sync Groups](https://dev.epicgames.com/documentation/unreal-engine/animation-sync-groups-in-unreal-engine)
3. **Action sequencing:** multi-part actions are divided into controllable sections with explicit entry, looping/hold, and exit behavior. [Epic Animation Montage](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-montage-in-unreal-engine)

The ASCILINE equivalents should be declarative JSON clips, marker-aligned Python phase evaluation, and channel-specific action sequences. This is an inference from those official skeletal-animation systems, adapted to coherent cell poses rather than bones.

## Recommended Python Animation Architecture

### A. Promote the graph from pose lookup to authored clip data

Create animation-graph schema version 2 while retaining generated pose cells as the render source. A clip should contain at minimum:

```json
{
  "clip_id": "cast_staff_front",
  "family": "action",
  "facing": ["south"],
  "loop": false,
  "root_policy": "grounded_in_place",
  "interrupt_policy": "marker_window",
  "samples": [
    {"pose_id": "front_idle", "duration_frames": 2, "markers": []},
    {"pose_id": "front_staff_guard_windup", "duration_frames": 4, "markers": ["anticipation"]},
    {"pose_id": "front_magic_staff_thrust", "duration_frames": 2, "markers": ["release", "effect_on"]},
    {"pose_id": "magic_cast", "duration_frames": 5, "markers": ["hold"]},
    {"pose_id": "front_staff_guard_low", "duration_frames": 4, "markers": ["recover"]},
    {"pose_id": "front_idle", "duration_frames": 3, "markers": ["settled"]}
  ]
}
```

Use integer render-frame durations at the canonical 24 FPS, not one duration for every transition. Aseprite's first-party animation model explicitly supports per-frame duration and named animation tags, which is the right mental model for these sprite-like poses. [Aseprite Frame Duration](https://aseprite.com/docs/frame-duration/) [Aseprite Tags](https://aseprite.com/docs/tags/)

Required clip metadata:

- `clip_id`, family, supported facings, loop mode;
- ordered samples with `duration_frames`;
- named markers: `left_contact`, `right_contact`, `both_contact`, `no_contact`, `anticipation`, `apex`, `release`, `impact`, `staff_plant`, `effect_on`, `effect_off`, `recover`, `settled`;
- root policy: grounded in place, world-distance locomotion, airborne offset, planted staff/hand, or cinematic root motion;
- legal entry/exit states and minimum hold;
- interrupt windows and priority;
- continuation phase or entry marker for synchronized switches;
- channel ownership and incompatibilities;
- optional cell-aligned secondary curves for root bob, hat, beard, robe, wings, staff, and effect origin.

### B. Add a hierarchical state machine, not one flat action enum

Recommended top-level modes:

```text
Grounded
  Idle
  Start
  Walk
  RunOrCharge
  Stop
  Turn
  CrouchOrKneel

Airborne
  Takeoff
  Hover
  Flap
  Glide
  Bank
  Fall
  Land

Action channel
  Conversation
  Staff
  Reaction
  Celebration

Face/speech/effect channels
  Expression
  Blink
  Mouth
  Magic effect
```

Each state produces a coherent full-body base pose/clip. Additive channels may then modify owned regions or overlays. Godot's official AnimationTree distinguishes immediate, synchronized, and at-end transitions, plus crossfade curves and state-machine travel through intermediate states. The Python graph should support equivalent transition semantics without importing Godot. [Godot AnimationTree](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html)

Examples:

- `Idle -> Takeoff -> Hover`, never `Idle -> Bank` directly.
- `Glide -> BankLeft -> Glide`, preserving flight phase.
- `AirborneFall -> Landing -> KneelBrace -> Idle`.
- `Walk -> StopAtContact -> Point`, unless the gesture is explicitly compatible with walking.
- `StaffWindup -> StaffAttack -> StaffRecover`; a stop command may interrupt during windup or recovery, but not on the two-frame attack unless policy says so.

### C. Use distance and markers to synchronize locomotion

Keep `walk_phase += distance / stride_length`. Extend it with clip marker intervals so transitions preserve the support foot. Epic's official Sync Groups documentation calls out unnatural foot placement when walk/run clips blend without synchronized lengths/markers; common `Right Foot Down`/`Left Foot Down` markers are the direct analogue needed here. [Epic Sync Groups](https://dev.epicgames.com/documentation/unreal-engine/animation-sync-groups-in-unreal-engine)

For starts, stops, and landings, use distance-to-target rather than only elapsed time. Epic's official Distance Matching system selects animation poses from a distance variable and advances animation by distance travelled. The Python equivalent can remain simple and deterministic: clip samples include normalized travel distances or stop-distance markers, and the controller selects the appropriate phase from remaining braking distance. [Epic Distance Matching](https://dev.epicgames.com/documentation/en-us/unreal-engine/distance-matching-in-unreal-engine)

Grounded locomotion rules:

- Preserve current phase when switching direction within the same gait family.
- Switch adjacent facing on a shared foot-contact marker whenever possible.
- Lock the planted foot anchor to its prior screen position by applying a bounded visual-root correction while contact is active.
- Advance world x/z from simulation; use visual-root correction only to remove cell-level foot slip.
- Do not call an airborne pose `contact=both` merely to satisfy root tests.
- Derive shadow compression/offset from actual support state.

### D. Separate contact root, visual root, and body altitude

The current single root serves projection, body, and shadow. Flight needs three values:

1. `contact_root`: projected ground point and shadow owner;
2. `visual_root_offset`: bounded cell correction for planted feet or cartoon bob;
3. `flight_height`: server-authoritative vertical body separation above contact root.

Add `flight_height`, `vertical_velocity`, `grounded`, and `support_contact` to Python state. Keep x/z movement in world space. Render the shadow at the contact root, then place the body at `contact_root.y - projected_flight_height + visual_root_offset.y`. The shadow should become smaller/lighter with height but must not chase wing motion.

This follows the useful separation in official root-motion systems: Godot exposes root-motion deltas and accumulators separately so movement code can apply them deliberately. WizardJoe should likewise make root deltas explicit rather than letting source crop or pose anchor changes move the character implicitly. [Godot AnimationTree, Root Motion](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html#root-motion)

### E. Preserve coherent silhouettes; do not dissolve arbitrary topologies

Transition strategy should be selected per edge:

1. **Same clip / compatible topology:** show authored samples with non-uniform holds. Optional region-local one-cell offsets are allowed.
2. **Adjacent view or related state:** keep the current coherent pose while timing/secondary offsets ease, then switch on a contact or smear marker to another coherent pose.
3. **Large action change:** insert authored anticipation/recovery poses.
4. **Fast attack:** use a one- or two-frame authored smear/effect layer, then the attack key.
5. **Interruption:** snapshot the currently presented coherent pose, phase, root correction, and channel velocities; transition from that snapshot rather than from the last asset ID.

Do not use the current hashed cell dissolve for full-body production transitions. It can remain as a diagnostic option, but the production frame must not scatter unrelated source and destination cells.

If region interpolation is later added, first generate stable semantic region IDs/masks for head/hat, beard, torso/robe, each arm, each leg/boot, each wing, staff, and effect. Epic's official layered blending material demonstrates why region ownership matters for combining locomotion with an upper-body action. The ASCILINE analogue is mask-owned cell transforms and overlays, not bone blending. [Epic Blending Animations](https://dev.epicgames.com/documentation/unreal-engine/blending-animations-in-unreal-engine) [Epic Blend Masks and Profiles](https://dev.epicgames.com/documentation/unreal-engine/blend-masks-and-blend-profiles-in-unreal-engine)

### F. Add deterministic secondary motion as cell-aligned offsets

At 24 FPS, subtle stepped offsets will read better than blurred interpolation:

- body/pelvis bob: authored `0, -1, 0, 0` cell patterns tied to gait phase;
- hat tip: one-frame delayed horizontal/vertical offset, bounded to one cell in ordinary walk and two in attacks;
- beard: delayed settle after head/root acceleration;
- robe hem: one-cell opposite-phase sway, suppressed while a foot is planted if it would break contact;
- wings: clip-authored up/down poses plus small body reaction offsets, not continuous raster rotation;
- staff: hand-owned offset with tip lag only when the staff region has valid metadata;
- magic: independent effect marker and effect layer so spark timing does not require body-pose replacement.

Use critically damped or finite impulse-response lag state evaluated at 60 Hz, then quantize to integer cells at render time. Reset or clamp lag on teleports/reset so secondary parts do not whip across the screen.

### G. Make events first-class animation data

Epic's official Animation Notifies documentation uses timeline events for footsteps, particles, sync markers, and duration-based notify states. The direct Python equivalent should emit deterministic clip events as phase crosses markers. [Epic Animation Notifies](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-notifies-in-unreal-engine)

WizardJoe events should include:

- foot contact / footstep;
- staff plant / release;
- magic effect start / peak / end;
- takeoff / apex / landing impact;
- action committed / interruptible / complete;
- speech-mouth suppression for shush;
- wing power stroke.

Events should appear in diagnostics and replay evidence even if no sound system consumes them yet.

### H. Replace destination key commands with held input intent

Keep the existing endpoint commands for automation. Add a remote-control command such as:

```json
{
  "type": "input",
  "payload": {
    "sequence": 1042,
    "move_x": -1.0,
    "move_z": 0.35,
    "speed_mode": "walk",
    "flight": false,
    "ttl_ms": 250
  }
}
```

TypeScript tracks keydown **and keyup**, calculates an input vector, and refreshes it while held. Python accepts only increasing sequence numbers and stops intent after TTL expiration. Actions remain separate commands so locomotion can continue while an allowed upper-body action plays.

The browser should continue presenting complete frames on `requestAnimationFrame`. MDN notes that rAF aligns callbacks with repaint and can pause in background tabs, which further supports keeping simulation and clip progression on the Python server rather than browser timers. [MDN requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)

## Proposed Clip Inventory From The 39 Poses

These are production hypotheses for the planning wave. Timing must be tuned in browser playback and supported facings must remain explicit.

### Grounded locomotion

| Clip | Key-pose order | Motion purpose | Missing requirement |
|---|---|---|---|
| `idle_front` | `front_idle` with procedural settle/breath | Default readable hold | Add secondary motion, varied blink/hold timing |
| `walk_front` | `walk_front_left -> front_idle -> walk_front_right -> walk_front_right_lift` | Limited four-beat walk | Author/derive complementary left passing/up frame; current cycle is asymmetric |
| `run_charge_front` | `front_run_charge_right_plant -> run_front_airborne_reach -> run_front_airborne_drive` | Acceleration/dash phrase | Not a complete reciprocal run loop; treat as burst until matching contacts exist |
| `run_land_front` | `run_front_airborne_drive -> front_crouch_landing_staff_plant -> front_kneel_staff_brace -> front_idle` | Burst recovery | Add impact and planted-staff markers |
| `turn_views` | adjacent coherent idle/view poses | Eight-way orientation | Requires real diagonal idles and richer directional walk poses for equal quality |

Do not mirror whole frames automatically to fill missing locomotion phases. The staff changes side, silhouette, hand ownership, and directional meaning. Mirroring is acceptable only for explicitly staffless or symmetry-reviewed region assets.

### Flight

| Clip | Key-pose order | Timing intent |
|---|---|---|
| `takeoff_front` | `front_idle -> front_crouch_guard -> fly_front_wings_down -> fly_front_hover_neutral` | Crouch anticipation, fast power stroke, settle into hover |
| `hover_front` | `fly_front_hover_neutral -> fly_front_knee_up -> fly_front_wings_up -> fly_front_wings_down` | Uneven flap cycle; longer neutral/up holds, short downstroke |
| `glide_southeast` | `fly_southeast_banked_staff -> fly_southeast_forward_glide -> fly_southeast_staff_forward` | Bank entry, long glide, staff-forward variation |
| `bank_left` | `fly_front_hover_neutral -> fly_southwest_banked_staff -> fly_front_hover_neutral` | Short turn phrase, preserve flap phase |
| `bank_right` | `fly_front_hover_neutral -> fly_southeast_banked_staff -> fly_front_hover_neutral` | Short turn phrase, preserve flap phase |
| `air_reaction` | `fly_southeast_cheer` or `front_airborne_fall_back_staff` | One-shot overlay/state, not normal locomotion |
| `land_front` | `fly_front_wings_up -> fly_front_wings_down -> front_crouch_landing_staff_plant -> front_kneel_staff_brace -> front_idle` | Decelerate, contact impact, recover |

The current art does not provide equivalent north/east/west flight sets. The state machine must use honest capability tiers: rich front/southeast flight where art exists, coherent held/glide fallbacks elsewhere, and a documented asset request for missing directional keys.

### Staff and magic

| Clip | Key-pose order | Cartoon structure |
|---|---|---|
| `cast_front` | `front_idle -> front_staff_guard_windup -> front_magic_staff_thrust -> magic_cast -> front_staff_guard_low -> front_idle` | Anticipation, attack/release, hold, recover |
| `guard_front` | `front_idle -> front_staff_guard_windup -> front_staff_guard_low` | Enter and hold defensive stance |
| `block_front` | `front_staff_guard_low -> front_staff_block_horizontal -> front_staff_guard_low` | Quick impact/read, return to guard |
| `flourish_front` | `front_staff_guard_low -> front_staff_spin_flourish -> front_staff_guard_windup -> front_idle` | Spin pose acts as smear/accent, not a long hold |
| `victory_cast_front` | `magic_cast -> front_victory_cast -> front_celebrate_wings_staff_up -> front_idle` | Magical success punctuation |

### Conversation and reactions

| Clip | Key-pose order | Notes |
|---|---|---|
| `explain_front` | `front_idle -> explaining -> front_idle` | Allow speech mouth and subtle hand hold |
| `point_front` | `front_idle -> explaining -> front_point_direct_staff_held -> explaining -> front_idle` | Explain is anticipation/recovery bridge |
| `shush_front` | `front_idle -> front_shush_secret_staff_held -> front_idle` | Suppress talking mouth while finger overlaps it |
| `celebrate_front` | `front_crouch_guard -> front_reaction_jump_fist_staff -> front_celebrate_jump_staff_up -> front_celebrate_wings_staff_up -> front_crouch_landing_staff_plant -> front_idle` | Clear anticipation, airborne apex, landing, settle |
| `hit_fall_recover_front` | `front_airborne_fall_back_staff -> front_crouch_landing_staff_plant -> front_kneel_staff_brace -> front_crouch_guard -> front_idle` | Reaction, impact, recovery |

## Transition Topology

The graph should encode legal edges and bridge states. Initial topology:

```text
Idle <-> Start <-> Walk <-> RunOrCharge <-> Stop <-> Idle
  |                  |                         |
  +------ Turn ------+                         +-> Crouch/Kneel -> Idle
  |
  +-> Takeoff -> Hover <-> Flap <-> Glide <-> Bank
                    |                         |
                    +-> AirReaction/Fall -----+-> Land -> Crouch/Kneel -> Idle

Grounded locomotion + compatible Conversation action
Grounded idle/guard + Staff action montage
Grounded/Airborne + compatible Reaction or Celebration one-shot
```

No wildcard edge should allow every pose to transition directly to every other pose. State-machine travel through intermediate states is preferable to teleporting when a legal bridge exists.

## Timing And Easing Recommendations

Use 24 FPS frame units because that is the current production stream (`wizard_avatar/frame_source.py:41-46`). Suggested first-pass ranges:

| Beat | Duration | Rationale |
|---|---:|---|
| Tiny anticipation | 2-3 frames | Responsive but readable |
| Standard anticipation | 4-6 frames | Cast, jump, point, bank |
| Attack/release | 1-3 frames | Crisp accent |
| Smear/effect accent | 1-2 frames | Avoid noisy full-pose interpolation |
| Readable action hold | 4-10 frames | Point, shush, block, magic peak |
| Recovery | 3-8 frames | Weight and follow-through |
| Idle micro-motion | 8-24 frame holds | Avoid mechanical constant cycling |
| Walk key | 2-4 frames, distance-driven | Adjust by speed/stride markers |
| Wing downstroke | 2-3 frames | Fast power stroke |
| Wing upstroke/hover settle | 4-7 frames | Slower recovery/upstroke |

Use named easing curves for numeric secondary channels, not for full raster occupancy:

- anticipation: ease-out into the extreme;
- attack: near-linear or ease-in, very short;
- recovery: critically damped/ease-out;
- hover: asymmetric periodic curve;
- landing compression: fast in, slower settle out.

### Silhouette and readability rules

- Each displayed frame must have one head, one torso, at most one staff, and the expected wing count.
- Important action extremes should be held at least two render frames.
- The staff must not cross or cover the face unless the authored key intentionally does so.
- Magic effects should not obscure eyes or mouth for more than two consecutive frames.
- The shush pose owns the mouth region; speech mouth animation is disabled during its hold.
- Wide action poses must stay within the canonical/stage safe bounds without per-frame rescaling.
- Direction changes must preserve whole coherent view families; never mix half of one facing with half of another.

## Risks And Mitigations

### Risk 1: Art coverage is heavily front-biased

**Evidence:** 26 of 39 poses face south; five directions have one pose each.
**Impact:** A promise of equally rich eight-direction walking, flying, and actions is not achievable from current whole-body poses alone.
**Mitigation:** capability-tier the graph; implement excellent front/diagonal clips first; retain simple coherent fallback views; create an explicit missing-art list for true diagonal idles, side walk phases, back walk passing poses, and non-front flight.

### Risk 2: Universal morphing destroys topology

**Evidence:** current transition assigns each cell independently from source or target.
**Impact:** doubled props, broken faces, noisy silhouettes.
**Mitigation:** authored sample timing, coherent swaps, effect smears, and region masks before any local interpolation.

### Risk 3: Contact metadata exists but is not consumed

**Evidence:** selector returns contact, renderer discards it; shadow uses a hardcoded phase window.
**Impact:** foot slide, hovering shadows, false contacts in jumps and flight.
**Mitigation:** make support contact part of authoritative animation state and drive root correction/shadow/events from it.

### Risk 4: Per-pose palette quantization shimmers

**Evidence:** `per_pose_quantized_64` yields 1,974 aggregate colors.
**Impact:** color crawling during clean silhouette changes.
**Mitigation:** generate a shared project or family palette, preserve canonical role colors, and gate stable-region color deltas.

### Risk 5: Interruption re-enters from an asset, not presented motion

**Impact:** rapid remote input causes pops even if ordinary transitions look acceptable.
**Mitigation:** snapshot presented pose/phase/root correction/channel velocities before constructing the next transition.

### Risk 6: Region masks become a second uncontrolled art pipeline

**Impact:** procedural motion may detach staff, face, or wings.
**Mitigation:** generate masks deterministically from reviewed metadata, validate anchor membership/connectivity, and require per-pose visual evidence.

### Risk 7: Flight becomes walking with the body shifted upward

**Impact:** no weight, no takeoff/landing, false foot contacts, shadow follows body.
**Mitigation:** separate ground contact root, altitude, flap phase, vertical velocity, and flight states.

### Risk 8: Browser smoothing hides server defects

**Impact:** remote controls appear smooth on one machine but replays are nondeterministic or clients diverge.
**Mitigation:** Python owns state and frame content; TypeScript owns input collection, decode, buffering, and presentation only.

## Measurable Acceptance Criteria

### Data and graph

1. Every production pose belongs to at least one named clip or is explicitly marked `showcase_only`.
2. Every clip validates supported facing, loop mode, root policy, sample durations, contact markers, entry/exit edges, and interruption policy.
3. Every grounded locomotion clip contains alternating left/right contact markers or is rejected as a loop.
4. Every airborne clip declares `no_contact`; every landing clip declares first contact and settled contact.
5. Graph validation rejects unknown pose IDs, unreachable states, zero-duration samples, illegal direct transitions, and missing marker pairs.

### Visual continuity

6. Fixed-world idle/action transitions have contact-root jump `<= 1` stage cell per adjacent rendered frame and `0` after settle.
7. A planted foot drifts `<= 1` local cell for the duration of its stance window.
8. Stable face, staff-hand, and staff-tip anchors move `<= 1` local cell per frame except during an authored attack/smear window.
9. No production transition frame contains more than one disconnected staff region or two face regions.
10. No full-body production transition uses the hashed cell-dissolve compositor.
11. At least 95% of occupied body cells in a stable hold use the shared reviewed palette role expected for that region.

### Locomotion

12. Three complete front-walk cycles at constant speed show alternating support feet, no reverse phase, and no stationary slide.
13. World distance per walk cycle matches the configured stride within `+-5%`.
14. Walk-to-stop settles on a contact marker and reaches idle within `<= 250 ms` after planar speed reaches the stop threshold.
15. Direction changes never advance more than one 45-degree view edge at a time and preserve locomotion phase across compatible clips.
16. Side and back movement cannot be labeled complete until their clips show visible alternating gait rather than one held image.

### Flight

17. Takeoff traverses anticipation, no-contact, and hover states in order; landing traverses descent, first contact, compression, and settle.
18. During sustained flight, feet never own the shadow/contact root.
19. Shadow center remains tied to ground contact root while body altitude changes; shadow scale changes monotonically with height.
20. Flap phase continues through compatible glide/bank transitions without restarting unless a clip explicitly requests reset.

### Actions and cartoon timing

21. Cast, block, flourish, point, shush, celebrate, and hit-recover clips each contain anticipation/action/recovery semantics or a documented intentional exception.
22. Each attack/release marker is emitted once per clip traversal, including under 60 Hz simulation and 24 FPS sampling.
23. Shush suppresses speech mouth writes for the entire finger-to-mouth hold.
24. Action interruption tests cover before commitment, during commitment, and during recovery; no case jumps back to a stale full pose.

### Remote control and latency

25. Held directional input moves continuously until keyup or TTL expiry; no browser-only world transform is applied.
26. On local loopback, accepted input affects authoritative velocity within one 60 Hz simulation tick and a visible frame within two 24 FPS frames (`<= 84 ms`, excluding OS/browser scheduling outliers recorded separately).
27. Releasing all movement keys decelerates to a valid stop clip; loss of control packets stops intent after `<= 250 ms` TTL.
28. Action, takeoff/land, and speed-mode commands expose accepted sequence IDs and current clip/phase in diagnostics.

### Determinism and evidence

29. Two identical command replays produce identical semantic event logs and identical cell-frame hashes.
30. Clip evidence includes state log, marker log, frame hashes, contact/root metrics, and a browser recording/contact sheet.
31. Browser verification records zero decode errors, zero unhandled console errors, and no source/decoded/presented hash mismatch.
32. A 10-minute mixed remote-control soak completes with no invalid graph state, stuck action, unbounded queue, or off-stage character.

## Recommended Implementation Order From The Animation Perspective

1. **Graph schema and diagnostics:** clips, samples, durations, markers, transitions, current clip/phase/contact in public state.
2. **Transition policy:** remove production use of hashed dissolve; add coherent snapshot, interrupt, and edge rules.
3. **Grounded front locomotion:** idle, start, walk, stop, run burst, landing/recovery; contact-root correction and shared palette.
4. **Held remote input:** keydown/keyup vector, TTL, sequence numbers, server-authoritative acceleration.
5. **Flight state:** altitude, takeoff, hover/flap, glide/bank, landing, ground-owned shadow.
6. **Action montages:** conversation, staff/magic, reaction, celebration with markers and channel priorities.
7. **Secondary motion:** reviewed masks and bounded cell-aligned lag for hat, beard, robe, wings, and staff.
8. **Directional expansion:** add or author missing side/back/diagonal keys before claiming equal eight-direction cartoon quality.
9. **Temporal evidence:** deterministic replays, contact/anchor/silhouette metrics, real browser recordings, and soak.

## Primary-Source Bibliography

1. Epic Games, [State Machines in Unreal Engine](https://dev.epicgames.com/documentation/unreal-engine/state-machines-in-unreal-engine). Used for explicit locomotion-state and transition topology.
2. Epic Games, [Animation Sync Groups in Unreal Engine](https://dev.epicgames.com/documentation/unreal-engine/animation-sync-groups-in-unreal-engine). Used for phase/marker synchronization and foot-placement rationale.
3. Epic Games, [Distance Matching in Unreal Engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/distance-matching-in-unreal-engine). Used for distance-driven starts/stops and phase advancement.
4. Epic Games, [Animation Montage in Unreal Engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-montage-in-unreal-engine). Used for multi-section actions, holds, loops, and runtime-controlled sequencing.
5. Epic Games, [Animation Notifies in Unreal Engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-notifies-in-unreal-engine). Used for contact, effect, impact, and sync-marker events.
6. Epic Games, [Blending Animations in Unreal Engine](https://dev.epicgames.com/documentation/unreal-engine/blending-animations-in-unreal-engine). Used for independent upper/lower-body ownership analogy.
7. Epic Games, [Blend Masks and Blend Profiles](https://dev.epicgames.com/documentation/unreal-engine/blend-masks-and-blend-profiles-in-unreal-engine). Used for semantic region masks and differing regional transition rates.
8. Epic Games, [Blend Spaces in Unreal Engine](https://dev.epicgames.com/documentation/unreal-engine/blend-spaces-in-unreal-engine?application_version=5.7). Used for speed/direction-driven locomotion sampling concepts.
9. Godot Engine, [Using AnimationTree](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html). Used for immediate/sync/at-end transitions, transition curves, graph travel, and explicit root motion.
10. Aseprite, [Frame Duration](https://aseprite.com/docs/frame-duration/). Used for non-uniform sprite-frame timing.
11. Aseprite, [Tags](https://aseprite.com/docs/tags/). Used for named sprite clip organization and loop modes.
12. Muriel Cartwright / GDC, [Fluid and Powerful Animation](https://media.gdcvault.com/GDC2014/Presentations/Cartwright_Muriel_Animation_Bootcamp_Fluid.pdf). Used for anticipation, smear, attack, return-to-idle, keys, and follow-through.
13. MDN Web Docs, [Window.requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame). Used for presentation-clock and hidden-tab behavior.

## Handoff To Planning Wave

The planning wave should treat the following as non-negotiable animation decisions:

- Python on port 8765 is the exclusive production animation authority.
- The 39 poses are keys, not automatically valid neighbors or loops.
- The current 120 ms hashed cell dissolve is not the target transition technique.
- Ground contact, visual root correction, and flight altitude must be separate.
- Front-facing clips can become production quality with current art; equal-quality eight-direction motion needs additional directional keys or reviewed semantic-region construction.
- Remote-control responsiveness and cartoon timing must be solved together: input intent drives state; state drives clips; clips drive markers and crisp cells; TypeScript only presents the authoritative result.
