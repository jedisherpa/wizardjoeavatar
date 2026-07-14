# Facial Animation and Eye-Motion Audit

**Role:** Facial Animation and Eye-Motion Specialist
**Audit date:** 2026-07-13
**Scope:** Python face, blink, gaze, eye, expression, and mouth behavior in `WizardJoeAvatar-python`
**Change boundary:** Research document only; no production edits

## Executive summary

Wizard Joe has a functional, test-covered face overlay, but not yet an audiobook facial-performance system. The production-preferred reference-pose path can blink, move both pupils one cell left or right, change brows, and cycle a small mouth. Those features are bounded to the face and survive locomotion. However, they are driven by fixed clocks and categorical state, not by narration structure, gaze targets, fixation planning, phonemes, visemes, audio, or performance timing.

The largest perceptual risk is not that individual values are wildly wrong. A 147 ms reference blink and the documented 160 ms fallback blink are plausible stylized durations. The problem is temporal organization: reference blinks recur exactly every 4.2 seconds, eye aim changes instantaneously, fixations do not exist as events, and speech advances a repeating mouth-shape stepper at 10 Hz. Research on virtual agents and auditory attention consistently indicates that *when* gaze shifts and blinks occur carries meaning. Audiobook research specifically finds greater blink probability during pauses in attended speech, while conversational-agent studies find that properly timed gaze aversion supports thinking, turn-taking, and comfort.

The highest-value next step is a deterministic facial-performance planner above rendering. It should accept narration events (utterance, word/viseme timing, pauses, emphasis, role, referent, and thought/turn boundaries), schedule readable gaze fixations and phrase-aware blinks, and expose continuous but quantized face channels. Rendering can remain intentionally stylized: at this face resolution, clarity should win over anatomical completeness.

## Audit boundary and runtime reality

The audit covered:

- `wizard_avatar/blink.py`
- `wizard_avatar/controller.py`
- `wizard_avatar/definitions/expressions.json`
- `wizard_avatar/expressions.py`
- `wizard_avatar/frame_source.py`
- `wizard_avatar/layers.py`
- `wizard_avatar/models.py`
- `wizard_avatar/mouth.py`
- related command, semantic-animation, pose-selection, server, and test code
- face requirements in `docs/20-expressions.md`, `docs/21-blinking.md`, `docs/22-speech-mouth-shapes.md`, `docs/24-design-board-actions.md`, and `docs/34-speech-expression-tests.md`

The bundled reference pose library currently resolves to `wizard_avatar/definitions/reference_avatar_pose_cells.json`, is available, and contains 89 poses. Therefore `ProceduralWizardFrameSource._render_current_frame()` normally selects the **reference-pose face path** (`wizard_avatar/frame_source.py:99-110`). The procedural face in `wizard_avatar/layers.py` is a fallback and must not be used as evidence that the normal runtime has features implemented only there.

Focused verification passed 23 tests:

```text
python3 -m unittest \
  tests.wizard.test_expressions \
  tests.wizard.test_animation_channels \
  tests.wizard.test_frame_source \
  tests.wizard.test_production_animation_wiring

Ran 23 tests in 11.980s - OK
```

These tests prove command acceptance, pixel changes, face-region containment, reference eye-box construction, blink masking, coarse eye aim, and speech/locomotion channel coexistence. They do not prove natural timing, audiovisual synchronization, expression readability, gaze-target accuracy, or long-form audiobook quality.

## Current implementation inventory

### State and control

- `WizardState` stores `expression`, `mouth`, scalar `blink_phase`, `speech_id`, `speech_text`, `speech_until`, and a world-space `target_point` (`wizard_avatar/models.py:124-143`).
- There is no gaze target, fixation, saccade, eye openness, independent lid, eye-head contribution, expression intensity, or viseme timeline state.
- The fixed simulation increments `blink_phase` by `SIMULATION_DT / 4.2`, making a perfectly periodic 4.2-second cycle (`wizard_avatar/controller.py:48-54`).
- Speech control receives text and total duration only; it does not receive audio, phonemes, visemes, word boundaries, pauses, or amplitude (`wizard_avatar/controller.py:328-339`).
- Expression commands switch a categorical name immediately and set the associated static mouth when speech is inactive (`wizard_avatar/controller.py:320-326`).
- No public blink or gaze command exists in the frozen command kinds (`wizard_avatar/commanding.py:30-46`) or HTTP routes (`wizard_avatar/server.py:141-175`).

### Reference-pose face path (normally active)

- Eye visibility is inferred by searching near authored anchors for white/cool pixels (`wizard_avatar/frame_source.py:190-203`, `250-279`). This sensibly prevents overlays on rear/occluded poses, but it is a color heuristic rather than explicit per-pose face metadata.
- Each visible eye is rewritten as a 5 x 2 white box with a one-column blue center (`wizard_avatar/frame_source.py:208-229`).
- Eye aim is only `-1`, `0`, or `+1` horizontal cell and changes immediately. Priority is world `target_point.x`, then `thinking` left, `skeptical` right, then eight-way body facing (`wizard_avatar/frame_source.py:281-297`).
- Blink is binary: closed only when `blink_phase >= 0.965` (`wizard_avatar/frame_source.py:205`). At a 4.2-second cycle this is about 147 ms closed, with no half-close, easing, or asymmetric close/open phases.
- Both eyes always share the same aim and blink. There is no convergence, vergence, independent correction, wink, or partial blink.
- Non-neutral expressions redraw three-cell brows, but the reference path does not consume the expression's `eyes` descriptor (`wide`, `squint`, `bright`, `side`) (`wizard_avatar/frame_source.py:231-248`, `316-349`).
- The speech shape advances through `open_medium -> open_small -> closed -> open_small` at 10 steps per second (`wizard_avatar/frame_source.py:351-362`). The full four-shape pattern repeats at 2.5 Hz. It never selects `rounded` during speech and has no phonetic relationship to the audio.
- The mouth overlay clears an 11 x 5 rectangle around the mouth anchor before drawing a categorical shape (`wizard_avatar/frame_source.py:383-433`). This is robustly bounded but can erase authored moustache/beard nuance in every animated mouth frame.

### Procedural fallback face path

- `blink_state()` uses a fixed default interval of 4.34 seconds and a 160 ms open/half/closed/half/open pattern (`wizard_avatar/blink.py:4-19`). The `seed` changes only the interval formula; it is not a seeded random generator.
- The fallback renderer uses `blink_state(state.time_seconds)`, not `state.blink_phase` (`wizard_avatar/layers.py:197-216`). Thus the two face paths have different blink clocks and state semantics.
- It supports wide and squint eye glyphs, but `bright` and `side` are inert; there is no pupil/gaze motion (`wizard_avatar/layers.py:206-221`).
- Speech uses a five-shape fallback stepper at 10 steps per second based on *remaining* speech time (`wizard_avatar/layers.py:242-251`, `wizard_avatar/mouth.py:24-26`), so its full pattern repeats at 2 Hz and its phase depends on the requested total duration rather than phonetic content or elapsed audio.

### Expressions

Ten named expressions are defined with brow, eyes, and mouth descriptors (`wizard_avatar/definitions/expressions.json:1-63`). They are useful art-direction labels, but they are not complete animation clips:

- no onset, apex, hold, release, or transition timing;
- no intensity or blending;
- no cheek, nose, lid-tightener, or jaw channels;
- no speech/expression arbitration beyond "speech owns the mouth";
- `head_offset` appears only on `thinking`, is `[0, 0]`, and is never read by production code;
- reference rendering ignores every `eyes` descriptor and substitutes two expression-name gaze exceptions;
- fallback rendering ignores `bright` and `side`.

### Mouth

Seven shapes exist: `closed`, `open_small`, `open_medium`, `open_wide`, `rounded`, `smile`, and `frown` (`wizard_avatar/mouth.py:8-16`). That is a reasonable low-resolution display vocabulary, but it is not a viseme vocabulary. There are no visually distinct closures for /p b m/, labiodentals for /f v/, tongue/teeth cues, or coarticulation. The implementation therefore cannot support lip reading or close audiovisual alignment even though the specification correctly prioritizes viseme, phoneme, word, and amplitude timing (`docs/22-speech-mouth-shapes.md:17-30`).

## Findings

### F1 - Critical: there is no facial-performance timeline

Face channels derive directly from the current categorical state and simulation clock. No component schedules fixations, saccades, blinks, brow beats, mouth cues, or releases against the narration. This makes performance insensitive to sentence boundaries, punctuation, emphasis, named characters, quoted dialogue, pauses, thought beats, and turn structure.

**Implementation implication:** Add a deterministic planner that produces timestamped face events from narration metadata. Keep rendering separate; the renderer should sample an already-planned face state.

**Risk if unchanged:** Long-form playback will reveal repetition quickly. Even technically correct pixels will read as mechanical because independent periodic loops collide with semantic moments.

### F2 - High: gaze is a three-position instantaneous switch, not gaze behavior

The active path has center/left/right pupil placement only. It has no vertical gaze even though the thinking design calls for "up and to the side," no fixation duration, no saccade trajectory, no return behavior, no target salience, and no direct-viewer/listener target. The world `target_point` contributes only the sign of horizontal delta and ignores depth, screen projection, target identity, and pointing geometry.

Human and virtual-character literature models gaze as rapid saccades separated by stable fixations, with gaze direction communicated by coordinated eye and head movement. Saccade duration increases with amplitude (the main sequence), while the Andrist et al. virtual-character model varies eye/head onset by up to roughly +/-100 ms and keeps the eyes on target as the head completes its contribution ([Baloh et al., 1975](https://pubmed.ncbi.nlm.nih.gov/1237825/); [Andrist et al., 2012](https://www.microsoft.com/en-us/research/publication/a-head-eye-coordination-model-for-animating-gaze-shifts-of-virtual-characters/)).

**Implementation implication:** Represent a gaze target, fixation start/end, previous/next target, saccade phase, and head contribution. At 24 fps, most small eye saccades should resolve in one frame and large readable shifts in at most two; the stable fixation is more important than visibly tweening every transition.

**Risk if unchanged:** Instantaneous one-cell changes can look like jitter when targets fluctuate and can be too subtle to communicate referential intent at display scale.

### F3 - High: eye-head coordination is absent

Body `facing` is an eight-direction locomotion/control state, not head pose. Eye aim may follow facing, but eyes never lead or settle against later head motion. No head yaw/pitch/tilt channel exists for facial performance, and expression `head_offset` is inert.

Eye-head coordination is not a fixed ratio. Target amplitude, predictability, salience, modality, vigilance, intent, initial eye position, and individual head-movement propensity all affect contribution and latency. The virtual-character model by Andrist et al. found a coordinated parametric model as accurate as human gaze for communicating target direction and more realistic than its baseline ([paper and results](https://graphics.cs.wisc.edu/Papers/2012/APMG12a/APMG12a.pdf)).

**Implementation implication:** Add a small audiobook head-performance layer: eye-led shifts for nearby visual/referential targets; more head contribution for large shifts; a modest head-first bias for off-screen auditory cues or speaker changes; vestibulo-ocular compensation while the head settles. Quantize the final output to authored pose families rather than requiring continuous 3D rotation.

**Risk if unchanged:** Pupils can point sideways while the whole authored head remains front-facing, weakening both naturalness and target readability.

### F4 - High: blink timing is plausible in duration but fully periodic and semantically blind

The reference path closes for about 147 ms every 4.2 seconds. The fallback plays a 160 ms five-state blink every 4.34 seconds. Neither varies interval, supports double blinks, responds to speech pauses, avoids high-information moments, or coordinates with gaze shifts. This does not meet the repository's own seeded-random 3-7 second requirement (`docs/21-blinking.md:13-25`).

Recent evidence is especially relevant to audiobook performance:

- In an attended-versus-ignored two-audiobook study, blink patterns in a subset of participants coupled to pauses in the attended stream, with more blinks during attended pauses ([Holtze et al., 2023](https://publica.fraunhofer.de/entities/publication/d0b74a26-1de7-4426-b2c6-f58e62ff8a7a)).
- Across speech and sequence experiments, ocular/blink activity tracked higher-level attended structure and often peaked after attended moments, although the authors caution against treating the observed lag as universal ([Zheng et al., 2019](https://www.nature.com/articles/s41467-018-07773-y)).
- Speaking changes blink rate; complex facial movement and vocal speech increased blink rate relative to baseline in controlled experiments ([Brych et al., 2021](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0258322)).
- A recent large reading dataset measured mean blink duration at about 129 ms but also showed wide variability, reinforcing that one fixed cadence is not a population model ([Cornelis et al., 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12141466/)).

**Implementation implication:** Schedule blinks with a deterministic pseudo-random baseline hazard, then bias probability toward phrase/sentence pauses, gaze-shift boundaries, and post-emphasis release. Suppress them during the visual apex of a strong expression or a brief referential look. Keep a hard minimum interval and an explicit, rare double-blink rule.

**Risk if unchanged:** The exact 4.2-second recurrence is learnable by the viewer and may place closures repeatedly on stressed words or direct-address beats.

### F5 - High: speech mouth motion is not lip sync

Both paths use clocked shape cycling. Text affects only total speech duration; no audio-derived event enters the face renderer. Closed frames occur because the cycle reaches `closed`, not because the narration contains silence or a bilabial consonant. `rounded` exists but is excluded from the active speech cycle.

Professional speech systems expose timestamped viseme events. Microsoft Speech, for example, provides a silence viseme plus language-dependent phoneme groups and an audio offset for each event; its 2D guidance explicitly applies temporal tags and smoothing ([Microsoft Speech visemes](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis-viseme)). Current MetaHuman tooling likewise treats mouth-region animation as a layer that can be generated or replaced independently from head movement, blinks, and mood ([Epic MetaHuman audio-driven animation](https://dev.epicgames.com/documentation/metahuman/audio-driven-animation)).

**Implementation implication:** Preserve the seven-shape low-resolution vocabulary but map provider visemes into a smaller display set, at minimum: silence/closure, open, wide, rounded, labiodental, and smile-affect overlay. Use timestamps, anticipation/coarticulation, and explicit silence. Fall back in the repository's documented order: viseme, phoneme, word, amplitude, deterministic cycle.

**Risk if unchanged:** The mouth can contradict the audio, close on vowels, miss /p b m/ closures, and chatter during pauses. These errors are conspicuous in a talking-head audiobook presentation.

### F6 - High: declared eye expression is mostly not rendered

`expressions.json` declares `open`, `bright`, `side`, `wide`, and `squint`. The active reference path reads brows and mouth but never reads the `eyes` field. It implements only two name-specific horizontal aims (`thinking`, `skeptical`). The fallback implements `wide` and `squint`, but not `bright` or `side`.

**Implementation implication:** Treat each declaration as a contract. Either implement the descriptor in both renderers or remove/replace it with explicit supported channels. Tests should assert pixel or state differences for every descriptor on every supported view family.

**Risk if unchanged:** Expressions can pass schema/list membership tests while communicating less than their data promises. `surprised` lacks wide eyes in the normal path; `amused` lacks squinting; `happy` and `confident` lack their declared bright-eye treatment.

### F7 - Medium: brows, lids, and gaze are too tightly collapsed

The reference path has a binary blink and a three-cell brow. There is no separate eye-wide, lid-tighten, upper-lid, lower-lid, or gaze-following lid channel. Modern professional rigs keep these controls separate: ARKit exposes left/right blink, look directions, squint, eye-wide, and brow controls as independent normalized coefficients ([Apple ARKit blend-shape locations](https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation)); MetaHuman similarly exposes separate brow, blink, widen, squint, cheek-raise, and look curves ([MetaHuman control curves](https://dev.epicgames.com/documentation/metahuman/mh-standards-docs/mha_index)). FACS also distinguishes brow raiser/lowerer, upper-lid raiser, cheek raiser, and lid tightener ([CMU FACS reference](https://www.cs.cmu.edu/~face/facs.htm)).

**Implementation implication:** Do not copy a 50-control rig into an ASCII face. Add only channels that produce distinct readable states: `eye_open`, `eye_aim_x`, `eye_aim_y`, `squint`, `brow_inner`, `brow_outer`, and optional asymmetry. Compose them before quantization.

**Risk if unchanged:** Brow-only expressions can read as ambiguous, while a binary lid can only say open/closed and cannot reinforce focus, amusement, surprise, fatigue, or gaze direction.

### F8 - Medium: expression changes snap and have no performance grammar

All expressions are static dictionaries switched immediately. There are no transition durations, holds, accents, asymmetry envelopes, or restoration stacks beyond action state. Speech owns the mouth categorically, so affect does not modulate speaking mouth width, corners, or energy.

**Implementation implication:** Give expression cues attack/hold/release envelopes and additive ownership: base affect, transient beat, speech articulation, blink/lids, and gaze. At 24 fps and this resolution, two- or three-step transitions are sufficient; long smooth blends may create muddy intermediate glyph states.

**Risk if unchanged:** Abrupt whole-face switches look like state changes rather than thought or emotion, and facial affect disappears from the mouth whenever speech is active.

### F9 - Medium: face editing is bounded but fragile across authored poses

Eye presence and layout are inferred from local color clusters. The mouth redraw clears a fixed rectangle. Tests correctly ensure edits remain near anchors across all poses, but proximity is not semantic correctness: a face edit can remain inside the allowed box while covering a finger, moustache, beard edge, prop, or intentionally occluded feature.

**Implementation implication:** Extend pose metadata with explicit face visibility, eye boxes, lid masks, pupil slots, mouth mask, occlusion flags, and per-pose supported face channels. Fail closed when metadata is absent.

**Risk if unchanged:** New pose art can accidentally satisfy color heuristics and receive a face overlay in the wrong region, especially on tilted, profile, shush, crouch, or prop-occluded poses.

### F10 - Medium: current tests validate containment, not audience readability

The strongest tests assert exact pixel counts and allowed regions (`tests/wizard/test_frame_source.py:50-188`, `218-271`). Production wiring checks that expression/blink commands alter some pixels (`tests/wizard/test_production_animation_wiring.py:216-247`). There is no test of:

- blink interval distribution or pause alignment;
- saccade/fixation timing;
- gaze-target decoding by a viewer;
- every expression's eye descriptor;
- viseme/audio alignment or silence closure;
- expression onset/hold/release;
- face readability at actual browser scale and motion;
- long-form repetition over minutes;
- cross-pose occlusion correctness.

Referential gaze is not automatically understood merely because it moves. A 2023 four-experiment study found reliable anticipatory use of virtual-agent listener gaze only in one timing condition, and its stimuli were pretested so shifts were clearly identifiable ([Nunnemann et al., 2023](https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2023.1029157/full)).

**Implementation implication:** Add temporal trace tests, browser-scale golden clips, and a small human decoding test ("where did Joe look?", "which emotion/beat?") rather than relying only on pixel deltas.

**Risk if unchanged:** The system can remain fully green while users cannot reliably read the intended performance.

## Research-to-design synthesis

### Gaze, saccades, and fixations

Human gaze is organized as stable fixations separated by fast saccades, not continuous wandering. Real-world scene studies commonly report mean fixations around 200-300 ms, but task and meaning substantially change dwell time; one 12-second natural-scene study measured 298 ms mean fixation duration and 4.58-degree mean saccades ([Cronin et al., 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC6971407/)). These values are references, not avatar presets. Conversational and narrative looks often need longer holds so an audience can decode them.

For Wizard Joe:

- Use fast, quantized eye arrival and conspicuous holds.
- Avoid random jitter during a fixation.
- Let intentional referential looks last long enough to read at final browser scale, likely hundreds of milliseconds to over a second depending on purpose.
- Use corrective micro-movements sparingly or omit them; one cell is already a large visual event.
- Distinguish direct-address fixation, referential fixation, cognitive aversion, listening/holding gaze, and idle scan.

The foundational `Eyes Alive` work showed that statistically derived eye-tracking behavior was preferable to stationary eyes or arbitrary random saccades for conversational characters ([Lee, Badler, and Badler, 2002](https://doi.org/10.1145/566570.566629)). The broader Eurographics survey likewise treats dwell, blink, gaze target, eyelid motion, and eye-head ratio as coupled expressive variables rather than independent noise generators ([Ruhland et al., 2014](https://doi.org/10.2312/EGST.20141036)).

### Conversational/narrative gaze

Gaze aversion has positive functions: signaling thought, managing intimacy, and regulating turn-taking. In a 24-participant virtual-agent study, gaze aversions timed from a human conversation corpus produced better outcomes than absent or mistimed aversions. The corpus found different timing distributions for cognitive, speaking/listening intimacy, and turn-start functions; those measurements should inform distributions, not become rigid constants ([Andrist, Mutlu, and Gleicher, 2013](https://www.microsoft.com/en-us/research/publication/conversational-gaze-aversion-for-virtual-agents/)).

For audiobook narration, map narrative intent rather than pretend Joe is always in a dyadic conversation:

- **Narrator to audience:** mostly direct gaze, with brief aversion around planning/thought beats and returns on key delivery.
- **Quoted character dialogue:** shift to a stable character-specific off-center target; do not ping-pong every word.
- **Scene/reference cue:** look toward the referenced screen/world object before or near mention, then return deliberately.
- **Reflection:** up/side gaze plus small head contribution, held long enough to read.
- **Emphasis/reveal:** establish direct gaze before the stressed phrase; avoid blinking at the visual apex.
- **Paragraph/scene release:** permit blink, gaze reset, and expression release in the pause.

### Blinks and lids

Use a blink scheduler, not a loop. A recommended stylized blink has:

1. fast close;
2. zero- or one-frame closed hold;
3. slightly slower reopen;
4. optional one-frame settle.

At 24 fps, a readable ordinary blink can be 3-5 frames depending on art scale, even if that exaggerates some human measurements. Preserve the current 120-180 ms target as the nominal fast blink, but judge final timing from rendered frames, not floating-point duration alone. Keep brows stable during ordinary blinks as the current specification requires. Emotional squeeze, wince, wink, or fatigue closure should be separate actions, not variants emitted by the ordinary blink scheduler.

### Brows, lids, and expression

At this resolution, use a small orthogonal control set and authored combinations. The eye aperture and inner brow are likely to carry more readable information than adding subtle cheek details. Recommended supported combinations:

| Intent | Eyes/lids | Brows | Gaze | Mouth affect |
|---|---|---|---|---|
| attentive | open, stable | soft/level | direct | neutral-soft |
| happy | slight lower-lid/cheek cue if readable | soft up | direct | corner lift under articulation |
| thinking | mild narrow | asymmetric/inner lower | up-side | closed or low activity |
| surprised | wide | both up | direct or stimulus | jaw/open emphasis |
| worried | normal/slightly wide | inner up/pinched | unstable target only if intentional | corners down |
| amused | squint | asymmetric soft | side then direct | smile under articulation |
| focused | narrow/tight | both down | fixed referent | restrained |
| skeptical | asymmetric aperture if supported | one up/one down | side hold | one-corner/frown cue |

### Mouth and visual speech

Do not attempt 22 one-to-one viseme drawings in a 7-cell mouth. Collapse provider output into perceptually distinct low-resolution groups. A workable target vocabulary is:

- `rest/silence` - closed or relaxed authored mouth;
- `closed_bilabial` - unmistakable /p b m/ closure;
- `open` - central vowel family;
- `wide` - spread vowels and energetic articulation;
- `rounded` - /o u w/ family;
- `labiodental` - /f v/ teeth/lip cue if readable;
- affect overlay - smile/frown corners composed with the articulation shape.

Use provider timestamps when available. Add coarticulation by anticipating closures/rounding slightly and blending shape ownership across neighboring cues. Enforce silence from the audio/timeline, not from an arbitrary cycle index.

### Readability at Wizard Joe's scale

The active eye is only 5 x 2 cells with a one-column iris. Therefore biological fidelity must be filtered through display constraints:

- Reserve the full one-cell pupil displacement for intentional left/right looks.
- Add vertical aim only if a distinct two- or three-state arrangement remains readable in final rendering.
- Hold meaningful poses; do not spend frames on tiny intermediate states.
- Keep eye white, iris, lid, brow, and mouth contrast stable across background, scale, and pose.
- Use asymmetry deliberately and infrequently so it remains legible.
- Validate at actual browser size, not only enlarged cell dumps.
- Prefer a clear target and return over continuous "alive" noise.

## Recommended architecture

### 1. Narration event input

Define a provider-neutral timeline containing:

- audio start/end and current playback time;
- utterance, sentence, phrase, word, and pause boundaries;
- optional phoneme/viseme events with confidence;
- stress/emphasis and punctuation;
- speaker/character identity and turn boundaries;
- referent/screen target and target salience;
- semantic beat (`address`, `think`, `reveal`, `question`, `aside`, `listen`, `release`);
- interrupt/seek/resume events.

### 2. Deterministic facial-performance planner

The planner should own seeded variability and produce events for:

- fixation target and minimum hold;
- saccade start/arrival;
- eye-head contribution and settle;
- blink start/type;
- base expression and transient expression beat;
- brow/lid accents;
- mouth/viseme cue and silence;
- interruption-safe release.

Determinism should derive from stable inputs such as book/chapter/utterance IDs plus an explicit seed, not wall-clock time. Seeking to a timestamp must reconstruct the same face state.

### 3. Composed continuous channels

Internally compose normalized channels even if output is categorical:

```text
gaze_target_id, eye_aim_x, eye_aim_y
head_yaw, head_pitch, head_tilt, head_contribution
eye_open_left, eye_open_right, squint_left, squint_right
brow_inner_left/right, brow_outer_left/right
mouth_group, jaw_open, mouth_width, mouth_round, corner_left/right
expression_id, expression_intensity
```

Do not expose all of these publicly at first. They create a clean ownership boundary and can quantize into the current ASCII/voxel vocabulary.

### 4. Pose-aware quantizer/renderer

For each authored pose/view, define supported states and masks. Quantize continuous channels into readable cell arrangements, preserving occlusions. The renderer should not invent timing or semantics.

### 5. Verification harness

Capture both machine and human-facing evidence:

- deterministic replay at arbitrary seek points;
- temporal event trace against audio timestamps;
- minimum fixation and blink-spacing invariants;
- no blink at protected emphasis intervals;
- mouth closure at silence and bilabial cues;
- expression descriptor coverage in both render paths;
- all-pose mask/occlusion checks;
- browser recordings at final scale, 24 fps, including 5-10 minute samples;
- blinded decoding checks for gaze direction and core expressions.

## Prioritized implementation plan

### P0 - Correct the contract before adding motion

1. Document the reference-pose path as the current production authority.
2. Add tests that every expression descriptor has a visible supported effect or an explicit unsupported declaration.
3. Align blink semantics between reference and fallback paths.
4. Add explicit pose face metadata and stop relying solely on color inference for new poses.

### P1 - Add narration-aware timing

1. Introduce a deterministic face-event timeline and seek-safe planner.
2. Replace fixed blink loops with a bounded stochastic hazard plus pause/beat bias.
3. Add gaze targets, fixations, saccade events, and direct-viewer gaze.
4. Add small eye-head coordination and implement the existing thinking up-side requirement.

### P2 - Replace mouth cycling

1. Accept provider viseme timestamps and explicit silence.
2. Map them to a compact low-resolution mouth vocabulary.
3. Add amplitude/word fallback and retain the cycle only as last resort.
4. Compose expression corners with speech articulation.

### P3 - Performance polish and proof

1. Add expression attack/hold/release and transient brow/lid beats.
2. Tune audiobook narrator, quoted-character, and reflective gaze policies separately.
3. Record long-form browser evidence and run small audience decoding tests.
4. Tune distributions from evidence; do not hard-code research means as universal truths.

## Exact current limitations

As of this audit, the Python avatar **cannot**:

1. schedule or represent a fixation;
2. represent a saccade, saccade amplitude, latency, or arrival;
3. aim eyes vertically;
4. aim at a screen-space or named semantic target;
5. maintain direct viewer eye contact as an explicit state;
6. coordinate eye motion with a facial-performance head yaw/pitch/tilt;
7. vary left and right eye aim independently or model convergence;
8. render partial lids, lid follow, eye-wide, or lid-tighten in the active reference path;
9. render the declared `eyes` expression field in the active reference path;
10. render `bright` or `side` eye descriptors in the procedural fallback;
11. consume the declared expression `head_offset`;
12. vary blink intervals or generate a seeded random sequence;
13. align blinks to pauses, sentence boundaries, thought beats, gaze shifts, or emphasis;
14. generate half-close/reopen phases in the active reference path;
15. generate a wink, asymmetric blink, or explicit double blink;
16. accept audio, word, phoneme, viseme, or amplitude timing for mouth animation;
17. distinguish speech sounds visually beyond generic open/closed sizes;
18. guarantee mouth closure during actual silence inside a speech interval;
19. coarticulate mouth shapes or blend affect with articulation;
20. animate expression intensity or onset/hold/release;
21. prove gaze or expression readability at final browser scale;
22. prove non-repetitive facial performance over long-form audiobook playback.

The Python avatar **can currently**:

1. select ten validated expression names;
2. change brows and mouth near face anchors without redrawing the full character;
3. draw visible reference eye whites and blue centers on detected front/side face poses;
4. move both reference pupils one cell left, center, or right;
5. produce a short periodic blink bounded to two-row eye boxes;
6. animate a categorical mouth while speech is active;
7. stop speech and restore the expression mouth;
8. preserve speech while locomotion or a compatible action continues;
9. suppress face overlays on at least the tested rear pose through eye-visibility detection;
10. pass the focused 23-test face/channel/wiring suite listed above.

## Risks and constraints

- **Over-realism at low resolution:** Adding biologically detailed channels without distinct cell states will create noise, not fidelity.
- **Timing copied too literally:** Human-study means are population/task observations, not universal animation constants. Use distributions, constraints, and art direction.
- **Dual-renderer drift:** Fixing only reference or fallback behavior will preserve inconsistent runtime semantics.
- **Pose metadata debt:** Heuristic face detection becomes more fragile as the pose library grows.
- **Semantic overreach:** A gaze direction can imply attention, thought, social address, or reference. Random motion can communicate the wrong thing.
- **Audio-provider lock-in:** Use a provider-neutral timeline and map provider visemes at the boundary.
- **Seek/interruption bugs:** Wall-clock or mutable random scheduling will make audiobook seeking nondeterministic and can leave stale mouth/expression state.
- **Accessibility/readability:** Continuous eye motion and rapid expression changes may distract viewers. Provide motion-intensity controls and test at actual presentation size.

## Sources

Primary studies, peer-reviewed reviews, and current professional documentation were prioritized.

1. Andrist, S., Pejsa, T., Mutlu, B., & Gleicher, M. (2012). [A Head-Eye Coordination Model for Animating Gaze Shifts of Virtual Characters](https://www.microsoft.com/en-us/research/publication/a-head-eye-coordination-model-for-animating-gaze-shifts-of-virtual-characters/). ICMI/Gaze-In. Primary model and user study.
2. Andrist, S., Mutlu, B., & Gleicher, M. (2013). [Conversational Gaze Aversion for Virtual Agents](https://www.microsoft.com/en-us/research/publication/conversational-gaze-aversion-for-virtual-agents/). IVA. Human corpus plus virtual-agent evaluation.
3. Baloh, R. W., Sills, A. W., Kumley, W. E., & Honrubia, V. (1975). [Quantitative measurement of saccade amplitude, duration, and velocity](https://pubmed.ncbi.nlm.nih.gov/1237825/). *Neurology*. Primary main-sequence measurements.
4. Lee, S. P., Badler, J. B., & Badler, N. I. (2002). [Eyes Alive](https://doi.org/10.1145/566570.566629). *ACM Transactions on Graphics*. Primary conversational eye-animation model.
5. Ruhland, K., et al. (2014). [Look me in the Eyes: A Survey of Eye and Gaze Animation for Virtual Agents and Artificial Systems](https://doi.org/10.2312/EGST.20141036). Eurographics STAR. Peer-reviewed synthesis.
6. Holtze, B., Rosenkranz, M., Bleichner, M., Jaeger, M., & Debener, S. (2023). [Eye-Blink Patterns Reflect Attention to Continuous Speech](https://doi.org/10.5709/acp-0387-6). *Advances in Cognitive Psychology*. Primary two-audiobook attention study.
7. Zheng, Y., et al. (2019). [Eye activity tracks task-relevant structures during speech and auditory sequence perception](https://www.nature.com/articles/s41467-018-07773-y). *Nature Communications*. Primary auditory-attention experiments.
8. Brych, M., et al. (2021). [How the motor aspect of speaking influences the blink rate](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0258322). *PLOS ONE*. Primary speech/blink experiments.
9. Cornelis, X., Dirix, N., & Bogaerts, L. (2025). [The timing of spontaneous eye blinks in text reading suggests cognitive role](https://pmc.ncbi.nlm.nih.gov/articles/PMC12141466/). *Scientific Reports*. Primary long-form reading/blink study.
10. Cronin, D. A., Hall, E. H., Goold, J. E., Hayes, T. R., & Henderson, J. M. (2020). [Eye Movements in Real-World Scene Photographs](https://pmc.ncbi.nlm.nih.gov/articles/PMC6971407/). *Journal of Eye Movement Research*. Primary fixation/saccade baseline study.
11. Nunnemann, E. M., Kreysa, H., & Knoeferle, P. (2023). [The effects of referential gaze in spoken language comprehension](https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2023.1029157/full). *Frontiers in Communication*. Four primary virtual-agent gaze experiments.
12. Apple. [ARFaceAnchor blend shapes](https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapes) and [BlendShapeLocation](https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation). Current professional facial-channel reference, accessed 2026-07-13.
13. Epic Games. [Audio Driven Animation](https://dev.epicgames.com/documentation/metahuman/audio-driven-animation) and [MetaHuman Animator control curves](https://dev.epicgames.com/documentation/metahuman/mh-standards-docs/mha_index). Current professional facial-performance references, accessed 2026-07-13.
14. Microsoft. [Get facial position with viseme](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis-viseme). Current professional viseme/timestamp reference, accessed 2026-07-13.
15. Carnegie Mellon University. [Facial Action Coding System reference](https://www.cs.cmu.edu/~face/facs.htm). Professional action-unit reference.

## Bottom line

The current code establishes a useful bounded renderer and a good testable base. It should not be discarded. The next system should stop asking the renderer to create liveliness from clocks and instead give it a deterministic, narration-aware performance plan. For this character, believable eyes will come less from adding motion everywhere and more from choosing a target, arriving quickly, holding clearly, blinking at meaningful boundaries, and returning with intent.
