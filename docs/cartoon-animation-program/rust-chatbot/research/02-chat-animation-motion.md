# Rust Chatbot Animation Motion Research

Role: `MOTION`
Date: 2026-07-13
Repository: `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar`
Runtime target: `rust/wizard_avatar_engine`, served at `http://127.0.0.1:8787/`
Asset baseline: `wizard_pose_library.v4.json.gz`

## Executive finding

Wizard Joe now has enough authored geometry to become a first-class chatbot
visualizer. The Rust runtime resolves 89 unique geometries: 10 baseline
geometries plus 79 imported geometries from an 80-record v4 catalog containing
one alias. All 50 unique WJFL sources are present in the v4 artifact. The
remaining problem is no longer pose intake. It is performance direction.

The current runtime has several strong foundations:

- exact 60 Hz simulation and 24 FPS evidence sampling;
- deterministic Rust control, pose playback, clip playback, rendering, codec,
  and fanout;
- a canonical 72 by 96 local pose space rooted at `(36, 95)`;
- 18 semantic regions, 25 required anchors, contact sets, attachment edges,
  and authored transition neighbors;
- crisp whole-pose handoffs that avoid dissolving two incompatible silhouettes;
- independent expression, blink, speech, upper-body, staff, and effect state;
- strict topology and anchor quality gates;
- a Rust evidence generator capable of rendering every frame to PNG, hashing
  replay streams, checking adaptive decode parity, and checking presentation
  parity.

The present clips are still closer to coverage reels than directed acting.
`wjfl_social` walks through many unrelated gestures, and `wjfl_feelings` walks
through all emotions and close variants in sequence. A chatbot needs short,
interruptible, repeatable performances selected from conversational state. It
also needs anticipation, action, recovery, co-articulation, gaze, visemes,
blinks, and secondary motion that continue coherently while the base pose or
turn state changes.

The recommended system is a Rust-native deterministic performance director on
top of the v4 pose library. It should preserve crisp authored geometry and use
marker-timed whole-pose handoffs, bounded region transforms, facial overlays,
and secondary channels. It must not use Python as production authority and
must never load or reuse source PNGs at runtime.

## Binding architecture decisions

1. Rust is the only production animation authority for this program. Python is
   not a runtime, build, asset-generation, testing, or acceptance dependency.
2. Source PNGs are offline references only. The runtime may load the embedded
   compiled Rust v4 artifact, but it may not load, crop, display, composite, or
   animate any PNG from intake or evidence directories.
3. The 50 WJFL integrations must be frozen before chatbot implementation. This
   inspection found 50 WJFL admissions and 50 runtime-resolvable WJFL
   geometries. The implementation start gate still requires those checks to be
   rerun and committed by the integration owner.
4. The 89 geometries are keys, not frames to dissolve through. Motion quality
   comes from timing, compatible pose paths, marker alignment, planted-contact
   constraints, and controlled secondary channels.
5. Whole-pose transition intermediates remain coherent authored poses. A
   transition may hold the source and hand off to the target, or travel through
   an explicit breakdown pose. It may not spatially hash, alpha blend, or
   scatter cells from unrelated full-body poses.
6. Chatbot events express semantic performance intent. They do not select raw
   pose IDs, frame indexes, or client transforms.
7. Simulation is deterministic at 60 Hz. Render evidence is sampled at 24 FPS.
   Browser presentation does not advance animation state.
8. The current v4 asset is immutable during the chatbot pass. A future asset
   version requires its own intake, compile, admission, and promotion gate.

## Inspected baseline

### Pose and asset state

`rust/wizard_avatar_engine/src/pose_asset.rs` accepts schema 4 from
`wizard-avatar-pose-tool-rust-v4` and rejects any archive not containing exactly
80 catalog records, 79 geometries, and one alias. The embedded artifact has:

| Property | Count |
|---|---:|
| Baseline Rust geometries | 10 |
| Imported v4 geometries | 79 |
| Runtime unique geometries | 89 |
| Imported catalog records | 80 |
| Imported aliases | 1 |
| Unique WJFL geometries | 50 |
| Required anchors per geometry | 25 |
| Semantic regions | 18 |

The imported v4 geometry distribution is:

| Motion family | Count |
|---|---:|
| Ground action | 53 |
| Flight | 9 |
| Jump | 6 |
| Run | 6 |
| Kneel | 2 |
| Landing | 2 |
| Walk | 1 |

The imported contact distribution is:

| Contact mode | Count |
|---|---:|
| Both feet and staff | 27 |
| Both feet | 23 |
| Airborne | 18 |
| Left foot | 4 |
| Right foot | 3 |
| Hand, foot, and staff | 2 |
| Kneel and staff | 2 |

Direction coverage is deliberately uneven: 73 imported poses face south, five
face southeast, and one faces southwest. Directional travel can still use the
baseline procedural rig, but rich authored acting should be treated as a
front-facing capability. The engine must not pretend that the library contains
equally authored acting for all eight directions.

### WJFL taxonomy

The 50 WJFL geometries form five useful performance sets:

| Candidate range | Count | Performance use |
|---|---:|---|
| `WJFL-01..02` | 2 | Winged run beats |
| `WJFL-03..20` | 18 | Guard, reaction, jump, staff, and celebration keys |
| `WJFL-21..30` | 10 | Idle, greeting, think, explain, point, sincere, playful, and magic social keys |
| `WJFL-31..40` | 10 | Full-body joy, sadness, anger, fear, shame, disgust, surprise, pride, guilt, and love |
| `WJFL-51..60` | 10 | Full-body-safe close-reference variants for the same ten feelings |

`WJFL-41..50` are duplicate archive sources and are correctly excluded from the
unique geometry set. Close-reference poses are compiled geometries derived from
their corresponding full-body feeling bases. They are not runtime PNG crops.

### Runtime and channel state

`rust/wizard_avatar_engine/src/state.rs` currently exposes:

- eight directions;
- three locomotion states: idle, walking, and turn;
- ten expressions;
- seven mouth shapes;
- six upper-body actions;
- four staff states;
- three effect states;
- generation counters for locomotion, facing, upper body, staff, expression,
  blink, speech, and effects.

This is an excellent generation-safe base, but it does not yet express a
chatbot turn state, performance intensity, gaze target, viseme timing,
secondary-motion phase, authored marker stream, or transition recipe.

`rust/wizard_avatar_engine/src/controller.rs` accepts semantic commands and
already prevents stale action generations from replacing newer ones. Speech
currently stores a `speech_id` and uses duration-based fallback mouth movement.
Blink is a deterministic function of elapsed simulation time. This is stable,
but it does not respond to utterance timing, sentence boundaries, turn-taking,
emotion, gaze, or interruption.

### Clip and transition state

`rust/wizard_avatar_engine/src/pose_clip.rs` contains 16 clips:

- `ground_walk`, `ground_run`, `hover_flap`, and `bank_glide`;
- `staff_combo`, `reaction_recover`, `celebrate`, and `conversation`;
- `explain`, `point`, and `think`;
- `wjfl_run`, `wjfl_guard`, `wjfl_reaction`, `wjfl_social`, and
  `wjfl_feelings`.

Each clip step currently has only a pose ID, hold ticks, and transition ticks.
There is no marker track, phase synchronization, contact policy, region mask,
interrupt window, restore policy per marker, deterministic variant weight, or
secondary-motion curve.

`rust/wizard_avatar_engine/src/pose_playback.rs` improves coherence by holding
the whole source until the handoff point. Replacement waits for an in-progress
handoff, and expiry cannot resurrect a stale target. This should remain the
fallback transition recipe. It is not enough for realistic motion because all
handoffs have the same basic topology and do not align anticipation, release,
impact, foot contact, blink, syllable, or prop follow-through.

`rust/wizard_avatar_engine/src/pose.rs` already provides a procedural semantic
gait rig, region-aware transforms, attachment repair, staff-connectivity repair,
and authored transition-duration selection. This is the correct layer for
bounded body mechanics. It should not become a general cell morphing engine.

### Rendering and browser state

`rust/wizard_avatar_engine/src/renderer.rs` renders semantic pose layers,
expression brows, mouth shapes, upper-body effects, magic effects, and a
contact-dependent shadow. It preserves integer-cell presentation.

The current facial overlay is symbolic rather than speech-aware. It can make a
readable expression, but it cannot yet produce timed visemes, asymmetric gaze,
micro-saccades, deliberate blinks, or emotion-specific facial holds. The
secondary-motion state for robe, beard, hat, staff, and wings is implicit in
pose geometry rather than a persistent channel.

The browser client queues complete decoded frames, requests resync on malformed
or missing deltas, and keeps a bounded presentation queue. The browser should
remain a presenter. Chat motion logic belongs in Rust.

### Quality and evidence state

`rust/wizard_avatar_engine/src/quality.rs` already checks:

- zero horizontal seams;
- zero vertical cracks;
- zero unexpected region fragments;
- no split or gapped staff;
- non-empty occupancy;
- visible/source and semantic/source retention;
- occupancy continuity;
- root, face, staff, and foot anchor steps.

Default thresholds include 0.94 semantic source retention, 0.75 visible source
retention, 0.88 same-pose occupancy, a 1.5-cell face step, a 1.5-cell staff step,
and a 5-cell free-foot step. WJFL transition tests allow 4, 6, and 8 cells for
face, staff, and free-foot movement across authored whole-pose changes.

The inspected v4 static census reports 89 frames and zero failures. The current
animation generator is designed to emit:

- one PNG for every rendered animation frame;
- a frame ledger;
- an MP4 review artifact;
- a timeline contact sheet;
- deterministic pass-one/pass-two hashes;
- adaptive decode parity;
- presentation parity;
- quality results grouped by transition.

At inspection time, the v4 animation-verification directory contained only an
in-progress `frames.rgb`. It did not yet contain its final manifest, PNG frame
set, ledger, video, or contact sheet. The chatbot implementation must not claim
animation completion until those final evidence artifacts exist and pass.

## Motion principles for Wizard Joe

### Readability before interpolation

The character is square-cell limited animation. A readable silhouette held for
the correct duration is preferable to a mathematically smooth but fragmented
blend. Motion should use:

1. a clear anticipation;
2. a short action or release;
3. a readable accent hold;
4. secondary overlap;
5. a recovery that returns control cleanly.

The system may use one-cell region offsets and procedural gait deformation
where semantic ownership is stable. It should not invent missing anatomy by
mixing arbitrary endpoint cells.

### Contact is the truth of weight

Grounded motion reads as weight only when the planted contact remains fixed in
screen/local space while the body travels around it. Every grounded clip must
declare a support contact and explicit release/strike markers. Staff plants and
hand plants are additional brace contacts, not decoration.

Rules:

- a planted foot may drift no more than 0.5 cell before release;
- a brace staff tip may drift no more than 0.5 cell during its plant window;
- the contact root remains stable through upper-body, face, speech, and gaze
  changes;
- a heel strike changes support on a named marker, never at an arbitrary pose
  handoff;
- airborne poses carry no planted-foot claim;
- landing follows `airborne -> contact -> compression -> settle`;
- takeoff follows `compression -> release -> airborne`, with the shadow staying
  at the contact root;
- close-reference feelings inherit their full-body base contacts.

### Phase and locomotion

Ground locomotion should remain distance-driven. The current eight-marker
contact cycle is useful and should become the shared phase vocabulary:

```text
left_stance -> left_toe_off -> left_passing -> right_heel_strike ->
right_stance -> right_toe_off -> right_passing -> left_heel_strike
```

Walk/run clip changes preserve normalized phase and switch on a compatible
contact marker. Start and stop clips are not loops:

- start: settle, anticipation lean, first release, locomotion loop;
- stop: final strike, compression, overshoot, settle;
- reverse: stop at contact, turn/weight transfer, restart;
- run-to-action: enter only at an allowed support or airborne marker;
- action-to-run: recover to a compatible stance before restoring distance
  phase.

Flight uses a separate wing phase and altitude state. Flap, glide, bank, fall,
and landing must not borrow grounded contact semantics.

### Transition recipes

The graph needs named recipes, not one universal duration:

| Recipe | Use | Required behavior |
|---|---|---|
| `coherent_handoff` | Compatible static pose changes | Hold source, hand off once, settle target |
| `contact_sync` | Walk/run/start/stop | Preserve phase and planted anchor; hand off on marker |
| `anticipation_action_recover` | Staff, point, cast, reaction | Traverse authored anticipation, action, recovery keys |
| `airborne_arc` | Jump, fall, celebrate jump | Release contact, preserve arc, land through compression |
| `brace_transfer` | Kneel, hand plant, staff plant | Add brace contact before removing prior support |
| `face_coarticulation` | Expression/viseme/gaze changes | Keep body fixed; change only face-owned cells/anchors |
| `secondary_settle` | Hat, beard, robe, staff, wings | Follow body acceleration with bounded delayed offsets |
| `reduced_motion_handoff` | Accessibility mode | No bob, overshoot, or repeated gesture; short coherent hold |

A transition recipe specifies source/target families, markers, duration bounds,
contact policy, owned regions, secondary curves, interrupt windows, and
fallback. Every graph edge must resolve to one recipe.

### Anticipation, action, and recovery

Timing should be authored in integer simulation ticks. At 60 Hz, useful default
ranges are:

| Beat | Default range | Notes |
|---|---:|---|
| Micro anticipation | 3-6 ticks | Blink, glance, small hand prep |
| Standard anticipation | 6-12 ticks | Point, explain, greeting |
| Heavy anticipation | 10-18 ticks | Staff strike, magic cast, jump |
| Action/release | 2-6 ticks | Fast readable accent |
| Accent hold | 4-18 ticks | Longer for surprise, pride, tool wait |
| Recovery | 8-24 ticks | Restore contact and channel ownership |
| Conversational settle | 12-36 ticks | Avoid mechanical snapping to neutral |

Interrupt policy is marker-based:

- before `commit`: replace immediately through a compatible anticipation exit;
- between `commit` and `impact`: queue stop unless safety/error priority wins;
- after `impact`: enter the shortest valid recovery;
- speech and face may usually interrupt independently of grounded locomotion;
- a new turn state invalidates older queued nonessential gestures by generation.

## Chatbot performance model

### Orthogonal channels

Recommended channels are:

| Channel | Owns | May coexist with |
|---|---|---|
| Base body | locomotion, body pose, contact root | all bounded overlays |
| Upper body | gesture and arm/torso emphasis | locomotion when contact-safe |
| Face emotion | brows, lids, cheeks, mouth bias | speech viseme and gaze |
| Speech | viseme and jaw aperture | body, gesture, gaze, blink |
| Gaze | eye offset and head-look bias | all states except closed-eye accent |
| Blink | eyelid closure | face and speech; yields to explicit eye accent |
| Staff/effect | staff action, plant, effect origin | body when attachments remain valid |
| Secondary | hat, beard, robe, wings, staff lag | follows base and upper-body acceleration |

Each channel has an owner generation, priority, entry tick, minimum hold,
interrupt policy, and recovery policy. Replacing one channel must not reset an
unowned channel or locomotion phase.

### Conversational turn states

| Turn state | Performance objective | Default performance |
|---|---|---|
| `idle` | Present and alive, not distracting | neutral contact, sparse blink, low-amplitude settle |
| `listen` | Signal attention and receptivity | gaze to user, tiny nods, closed mouth, restrained hands |
| `think` | Show active processing | gaze offset, thinking hand/chin variant, slower blink |
| `speak` | Deliver content clearly | speech visemes, phrase gestures, gaze returns at emphasis |
| `clarify` | Invite correction | open hand, slight head tilt, questioning brow |
| `tool_wait` | Show progress without fake speech | patient loop, periodic glance/effect, no mouth chatter |
| `error` | Acknowledge failure calmly | short surprise/concern, recovery to composed stance |
| `celebrate` | Mark success without hijacking the UI | one anticipation/action/recovery burst, then settle |
| `interrupted` | Yield immediately and visibly | close mouth, stop gesture at safe marker, return to listen |

State changes should not directly name a pose. They select a performance
family, emotion, intensity, and deterministic variant. Repeated identical
events use a seeded variant cycle so the character feels alive while replay
hashes remain identical.

### Emotion-to-performance mapping

The ten WJFL feeling pairs should be treated as emotion accents, not a carousel.

| Emotion | Posture and timing | Face/gaze | Safe conversational use |
|---|---|---|---|
| Joy | open chest, light upward accent, quick recovery | bright gaze, smile | greeting, success, warm response |
| Sadness | lowered chest, slower settle | down gaze, soft blink | empathy, regret; never loop theatrically |
| Anger | forward weight, short held tension | narrowed gaze | only explicit frustration/error context, low default intensity |
| Fear | recoil, brief airborne/guard accent | wide eyes, quick glance | warning or uncertainty, then composed recovery |
| Shame | contracted posture, delayed eye return | averted gaze | apology; one restrained accent |
| Disgust | small withdrawal and head bias | side gaze, asymmetric brow | explicit rejection, never default error state |
| Surprise | fast open accent, short hold | wide eyes, delayed blink | unexpected result or interruption |
| Pride | lifted chest, stable hold | direct gaze | accomplishment, concise celebration |
| Guilt | contracted stance, hand-to-heart bias | down/return gaze | taking responsibility, subdued timing |
| Love | open sincere posture, gentle hold | warm direct gaze | appreciation and care, no repeated bounce |

The `*_full` and `*_close` geometries are paired beats. The close variant is a
facial emphasis state on a full-body-safe base, not a camera zoom. The pair may
be used as `anticipation -> close accent -> full recovery` only when the face
anchor and contact root pass the recipe thresholds.

### Speech, visemes, and co-articulation

Seven existing mouth shapes are enough for a compact first pass:

```text
rest/closed, small-open, medium-open, wide-open, rounded, smile, frown
```

The speech contract should provide timed viseme cues, not raw audio. A Rust
viseme reducer maps phoneme-class cues to these shapes. Co-articulation rules:

- look ahead 2-4 render frames for the next strong viseme;
- begin jaw opening before the vowel peak;
- preserve emotion mouth bias at phrase boundaries;
- close or nearly close on hard pauses, interruption, and end of turn;
- suppress rapid one-frame toggles by enforcing a two-render-frame minimum
  unless the cue is a plosive closure;
- quantize all cue times to simulation ticks before playback;
- do not infer phonemes from private transcript text inside the renderer;
- allow a duration-only deterministic fallback when no cue track exists.

Phrase gestures use semantic markers such as `phrase_start`, `accent`,
`clause_end`, and `turn_end`. Gesture peaks should lead or coincide with the
spoken accent by no more than two render frames. A gesture must recover before
the next incompatible phrase gesture.

### Gaze and blink

Gaze makes a chatbot feel attentive more effectively than constant body motion.

- Listen: hold user gaze 70-90 percent of the interval with deterministic
  micro-saccades.
- Think/tool wait: avert gaze for 300-900 ms, then periodically return.
- Speak: look at the user at phrase start and important accents; brief aversion
  while formulating is allowed.
- Clarify: direct gaze plus a slight questioning head bias.
- Error: brief down glance, then reestablish contact.
- Interruption: return gaze immediately and close the mouth.

Blink timing is deterministic but nonuniform. Seeded intervals should generally
fall between 2.5 and 6.5 seconds, with a two- or three-frame closure. Schedule
blinks near gaze changes and phrase boundaries. Suppress blinks during a
surprise accent and avoid a blink on the exact action impact frame.

### Secondary motion

Secondary motion should be stateful, bounded, and subordinate:

- Hat: one-cell delayed tilt after body acceleration, settling within 8-14
  ticks.
- Beard: one-cell drag opposite head/chest acceleration, with slower settle.
- Robe: one-cell lateral or vertical follow-through tied to root velocity and
  gait phase.
- Staff: preserve grip attachment; tip may lag by one cell unless planted.
- Wings: use authored flap poses for large motion and a bounded settle offset
  for idle/listen/speak. Never detach a wing region from the torso.
- Effects: attach to `EffectOrigin`; use deterministic phase and lifetime.

Secondary offsets must be integer-cell quantized at render time and included in
frame quality snapshots. A staff or wing attachment gap is an immediate failure.

### Deterministic authored variation

Variation should be finite, weighted, and replayable. Use a small Rust PRNG with
a seed derived from:

```text
session_seed, turn_sequence, performance_family, variant_generation
```

The seed selects among approved variants, timing ranges, gaze offsets, and
secondary settle profiles. The selector must:

- never choose the immediately previous optional variant when another is legal;
- obey cooldowns and turn-state compatibility;
- record the selected variant and seed in evidence;
- produce the same frames for the same command log and seed;
- never use wall-clock randomness.

### Repeatable clips

A repeatable clip has a marked loop segment and explicit entry/exit. Repeating
the Play action should mean repeat until Stop, but chat performance loops must
remain state-specific:

- idle/listen/tool-wait loops may repeat;
- locomotion and hover loops may repeat;
- speech gestures repeat only by phrase selection, never as one endless cycle;
- emotion accents, reaction, error, and celebrate are one-shot;
- Stop exits at the earliest safe marker and settles to idle/listen.

### Accessibility and reduced motion

Reduced motion is a production mode, not a CSS-only preference.

- remove root bob, overshoot, repeated celebration, and continuous wing flap
  where not semantically required;
- prefer one coherent handoff and a stable hold;
- keep speech visemes readable but cap jaw aperture change frequency;
- keep gaze changes but remove micro-saccade jitter;
- reduce effect density and disable rotating effects;
- preserve semantic state, contact correctness, and response timing;
- expose the active motion profile in state and evidence.

The browser may report `prefers-reduced-motion`, but Rust remains authoritative
and applies the profile to all clients for that session or character instance.

## Required quality metrics

Completion should target 100 percent on deterministic and structural gates,
even if program governance permits a minimum score of 90 percent.

| Metric | Required threshold |
|---|---:|
| Runtime geometry coverage | 89/89 |
| WJFL geometry coverage | 50/50 |
| Pose-to-clip/transition/showcase classification | 89/89 |
| Authored graph edge resolution | 100% |
| Screenshot evidence coverage | 1 PNG per rendered frame |
| Deterministic pass-one/pass-two frame hashes | 100% identical |
| Adaptive decode/source hash parity | 100% |
| Presented/decoded hash parity | 100% |
| Horizontal seam rows/cells | 0 |
| Vertical crack cells | 0 |
| Unexpected fragment components | 0 |
| Staff components while present | 1 |
| Staff scanline gaps | 0 |
| Semantic source retention | at least 0.94 |
| Visible source retention | at least 0.75 |
| Same-pose occupancy ratio | at least 0.88 |
| Local root step | 0 cells |
| Planted contact drift | at most 0.5 cell |
| Brace contact drift | at most 0.5 cell |
| Same-channel face step | at most 1.5 cells |
| Same-channel staff-hand step | at most 1.5 cells |
| Authored whole-pose face step | at most 4 cells |
| Authored whole-pose staff step | at most 6 cells |
| Authored whole-pose free-foot step | at most 8 cells |
| Chat turn-state scenario pass rate | 100% |
| Interrupt/replace/restore scenario pass rate | 100% |
| Reduced-motion scenario pass rate | 100% |
| Browser console errors | 0 |

Every exception must name a recipe, pose pair, metric, observed value, owner,
and expiration. There are no silent threshold relaxations.

## Screenshot-per-frame QA protocol

1. Freeze the commit SHA, v4 asset hash, graph hash, seed, and command log.
2. Run the complete scenario suite twice at exact 60 Hz simulation.
3. Sample render frames with the exact 24 FPS clock.
4. For every frame, record state, clip, sample, markers, channel generations,
   contacts, anchors, topology, source hash, encoded tag, decoded hash, and
   presented hash.
5. Render every frame to a numbered PNG with no gaps in numbering.
6. Verify PNG count equals ledger row count equals manifest frame count.
7. Run topology, anchor, contact, attachment, and cadence checks over every row.
8. Generate contact sheets by scenario and transition, plus a complete timeline
   contact sheet.
9. Generate a review video only as convenience. The PNGs and ledger are the
   acceptance evidence.
10. Run the same scenarios through a real browser against port 8787 and compare
    source, decoded, and presented hashes.
11. Fail the gate on any missing screenshot, unmatched hash, fragment, crack,
    detached prop, contact drift, stale channel generation, or console error.

Required scenarios include every graph edge; every loop boundary; entry and exit
for every repeatable clip; all nine conversational states; all ten feelings at
low and high allowed intensity; speech with and without viseme cues; gaze and
blink collisions; locomotion plus speech/gesture; staff, wing, robe, and effect
secondary motion; rapid interruption; Stop during each interrupt window;
reconnect/resync; and reduced motion.

## Risks and mitigations

| Risk | Consequence | Mitigation |
|---|---|---|
| Front-facing art dominates | False promise of eight-direction acting | Publish capability tiers and deterministic facing fallback |
| Coverage clips are mistaken for acting | Mechanical pose carousel | Replace with short state-specific clips and one-shot accents |
| Close-reference feelings read as zooms | Composition jump | Keep full-body root/contact; limit close variant to facial emphasis recipes |
| Region offsets detach staff or wings | Visible breakup | Attachment constraints and zero-gap frame gates |
| Visemes fight emotion mouths | Facial popping | Layer ownership, lookahead, minimum holds, phrase-boundary bias |
| Random variation breaks replay | Unreproducible evidence | Seeded finite authored variants only |
| Interruptions resurrect stale motion | Chat feels unresponsive | Per-channel generations and marker-based replacement |
| Too much idle motion distracts from text | Poor chatbot usability | Sparse idle, bounded intensity, reduced-motion profile |
| Evidence volume becomes unmanageable | QA is skipped or artifacts balloon | Deterministic manifests, scenario partitions, compact hashes, optional video |
| Python plan leaks back into production | Split authority | Rust-only scope validator and Cargo-only gates |
| Runtime PNG reuse returns | Asset provenance and quality regression | Test embedded artifact path and reject image loading in engine/web runtime |

## Research conclusion

The 89-geometry library is broad enough for a convincing chatbot character, but
the correct unit of implementation is not another large pose reel. It is a
deterministic Rust performance graph with short authored clips, contact-aware
transition recipes, orthogonal face/speech/gaze/secondary channels, and explicit
turn-state direction. The existing semantic pose model and evidence machinery
make this practical without abandoning crisp colored cells or introducing a
skeletal/video/PNG runtime.

The implementation should proceed only after the v4 integration checkpoint is
committed and its full animation evidence has passed. From that point, the work
can be delivered incrementally behind a legacy fallback, with each new graph
family promoted only after screenshot-per-frame evidence is complete.
