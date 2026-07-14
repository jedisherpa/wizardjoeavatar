# Supervising Animation Director Audit

**Project:** Wizard Joe Audiobook Performance Engine
**Scope:** Current Python visualizer in `WizardJoeAvatar-python`
**Audit date:** 2026-07-13
**Ownership boundary:** Research and direction only. No production code was changed.

## Executive decision

The Python visualizer is a sound deterministic avatar renderer with a verified 89-pose asset library, root-anchored staging, a 24 fps authored animation graph evaluated on a 60 Hz simulation, independent face channels, and tested semantic action routing. It is **not yet an audiobook performance engine**. It has the pictures for a nuanced single performer, but its production path currently behaves as a command-driven pose player.

The decisive gap is reachability and direction. The first 39 poses are clip samples; poses 40-89 are classified `diagnostic_only`, including the best audiobook-specific material: a characterful neutral, greeting, thinking, open-hand explanation, side point, two-hand explanation, hand-to-heart sincerity, and twenty emotion variants. While speech is active, body-gesture selection is deliberately suppressed. Semantic `amplitude`, `hold`, and `allow_flourish` values do not become sustained performance behavior. Pose changes are atomic, authored transition records are selected but not played, and mouth motion uses a fixed 10 Hz cycle rather than speech timing.

**Direction:** preserve the renderer and its atomic square-cell snapshots. Add an audiobook-specific performance scheduler above pose selection. It should hold a characterful neutral most of the time, change main pose only when thought or emotional state changes, use small phrase-level gestures sparingly, insert readable thought pauses before emotional transitions, and retain one continuous Wizard Joe physical identity across chapters and characters.

## Audit basis

### Repository evidence

- `wizard_avatar/definitions/reference_avatar_pose_cells.json` contains exactly **89** pose geometries (`version: 81`).
- `assets/reference/motion_sources/manifest.json` contains the same 89 ordered semantic IDs and their facing, locomotion, action, phase, and tag metadata.
- `wizard_avatar/definitions/reference_avatar_animation_graph_v2.json` contains **89 classifications, 28 nodes, 28 clips, 47 directed transitions, and 5 transition recipes**. Its authored rate is 24 fps and its simulation rate is 60 Hz (`reference_avatar_animation_graph_v2.json:1-18`).
- Exactly **39 poses** have `clip_sample` reachability. Exactly **50 poses**, IDs 40-89, are `diagnostic_only` and absent from every graph clip.
- The frame source loads all pose IDs into the controller (`wizard_avatar/frame_source.py:47-74`), selects one graph sample per frame, applies expression/eye/mouth channels, root-anchors the result, and renders it (`wizard_avatar/frame_source.py:89-146`).
- The renderer explicitly treats sprites as atomic snapshots and forces transition progress to 1.0 (`wizard_avatar/frame_source.py:159-181`).
- Node changes set `animation_transition_id`, reset clip tick, and immediately evaluate the target clip (`wizard_avatar/pose_selection.py:86-107`). The production selector does not evaluate a transition recipe.
- Clip metadata such as `minimum_hold_ticks`, `interrupt_policy`, marker gates, and legal successors is parsed (`wizard_avatar/animation_graph.py:569-657`), but those policies are not enforced by the production pose-selection path.
- Semantic intents define bounded `amplitude`, `tempo`, `mouth_activity`, `hold`, and `allow_flourish` (`wizard_avatar/semantic_animation.py:18-64`; `wizard_avatar/definitions/semantic_animation_map.json:4-124`). The controller persists only cue, gesture, and amplitude, uses tempo only to derive a one-shot action duration, and does not apply `hold` or `allow_flourish` as scheduling policy (`wizard_avatar/controller.py:262-310`).
- During a real speech session, body speech gestures are suppressed: `_effective_action` returns no speech action when `speech_id` exists (`wizard_avatar/pose_selection.py:141-150`). The test contract confirms that speech does not replace the body pose (`tests/wizard/test_pose_selection.py:201-224`).
- Reference-face speech cycles `open_medium`, `open_small`, `closed`, `open_small` at 10 Hz (`wizard_avatar/frame_source.py:351-360`). The procedural fallback also cycles five mouth shapes at 10 Hz (`wizard_avatar/mouth.py:24-26`).
- Existing visual evidence was inspected at `evidence/animation-quality/final/screenshots/02-speech-actions-expressions-contact-sheet.png`, `evidence/pose-library-expansion/intake/contact-sheets/wizard-joe-poses-feelings.png`, and `evidence/pose-library-expansion/rust-v4/static-census/contact-sheet.png`.

### Verification performed

- Machine-counted the 89-pose library, graph classifications, nodes, clips, and transitions.
- Enumerated every pose's current classification and every graph clip's samples and duration.
- Verified that all 50 `diagnostic_only` poses are absent from graph clips.
- Ran 31 focused standard-library tests covering pose selection, semantic animation, production graph wiring, action API reachability, expression rendering, blink rendering, and runtime command flow. Result: **31 passed, 0 failed**.
- Ran the full standard-library suite. Result: **170 passed, 1 failed** in 149.197 seconds. The failing deadline test, `StreamHubTests.test_frame_loop_does_not_replay_missed_deadlines`, published 2 frames where the test requires at least 3. Three isolated reruns also failed, each publishing 1 frame. This was not treated as transient.
- `pytest` was not available in the repository virtual environment; the documented `unittest` path was used instead.

## Professional direction standard

The following sources were selected because they are current industry, studio-adjacent, union, publisher, or professional training sources rather than unsourced animation summaries.

1. **Staging must make one idea clear.** Animation Mentor's staging guidance ties staging to acting and timing and defines its purpose as control of audience attention and clarity of the idea. For Wizard Joe, the readable idea is the spoken thought, not the existence of another pose in the library. [Animation Mentor, "Staging: The 12 Basic Principles of Animation"](https://www.animationmentor.com/blog/staging-the-12-basic-principles-of-animation/)
2. **Thought drives a main pose change.** Veteran animation guidance recommends acting within a few emotional poses, using secondary gestures for emphasis, and not changing pose for each dialogue accent. It also calls for a readable micropause before an emotional change and a neutral pose specific to the character. [Animation Mentor, "10 Advanced Acting Performance Tips for Animators"](https://www.animationmentor.com/blog/10-advanced-acting-performance-tips-for-animators/)
3. **Gesture must be motivated.** Professional hand-animation guidance recommends reference, broken symmetry, offset timing, whole-upper-body integration, and gestures motivated by intent rather than literal illustration of dialogue. [Animation Mentor, "How to Animate Hand Gestures for Dialogue Scenes"](https://www.animationmentor.com/blog/tutorial-how-to-animate-hand-gestures/)
4. **Body language carries emotion before facial polish.** The 2026 professional tutorial emphasizes shoulders, spine, hands, feet, silhouette, weight, and rhythm, particularly for simpler rigs. [Animation Mentor, "Animating Emotion Through Body Language"](https://www.animationmentor.com/blog/tutorial-animating-emotion-through-body-language/)
5. **Holds are performance, not dead time.** Animation timing guidance recommends adjusting hold length until the pose can be read and trading transition frames for more readable main-pose time. [Animation Mentor, "Timing: The 12 Basic Principles of Animation"](https://www.animationmentor.com/blog/timing-the-12-basic-principles-of-animation/)
6. **Audiobook acting is intimate and continuous.** ACX guidance describes the narrator as playing all roles, directs performers to prepare the whole book and scene subtext, and recommends attitude and personality over pitch tricks. It quotes a Penguin Random House studio director's principle that a little characterization goes a long way. [ACX, "How to Act Like an Audiobook Narrator"](https://www.acx.com/mp/blog/how-to-act-like-an-audiobook-narrator)
7. **Long-form continuity includes emotional tone, pacing, rhythm, and sensibility.** An Audible Approved producer recommends listening back before a session because voice pitch alone is insufficient to restore performance continuity. [ACX, "Andi Arndt's Audiobook Agenda"](https://www.acx.com/mp/blog/andi-arndts-audiobook-agenda)
8. **Professional audiobook judgment rewards consistency and flow.** The Audio Publishers Association's current Audies criteria require believable performance, clear and consistent character differentiation through tone/inflection/pacing, maintained pace, uninterrupted plot flow, and effects that enhance rather than distract. [Audio Publishers Association, Audies Judging Criteria](https://www.audiopub.org/s/Audies-Judging-Criteria-for-Site.pdf)
9. **Direction should be validated on representative material.** ACX's current production guidance requires a representative 15-minute checkpoint reflecting final character voices, accents, pacing, tone, and pitch. The visual engine needs the equivalent, not only isolated pose tests. [ACX, "Record a 15-minute sample"](https://help.acx.com/s/article/record-a-15-minute-sample)
10. **Audiobook narration is long-form storytelling.** SAG-AFTRA's 2025 discussion with veteran narrator Sean Pratt distinguishes acting skill from the technique and temperament required to sustain a story alone for hours. [SAG-AFTRA, "Breaking Into Audiobook Narration"](https://www.sagaftra.org/sag-aftra-podcast-breaking-audiobook-narration)

## Findings

### F1. Critical: the audiobook vocabulary exists but is unreachable

Poses 60-69 are the most useful sustained-performer set, and poses 70-89 are the explicit emotion set. All are `diagnostic_only`. The normal selector can reach the first 39 through 28 clips, while the later 50 are available only through explicit pose override/showcase surfaces.

**Evidence:** the graph's classification census is 39 `clip_sample` and 50 `diagnostic_only`; graph validation requires every `clip_sample` pose to be used (`wizard_avatar/animation_graph.py:728-736`); the selector chooses nodes and clips, not diagnostic poses (`wizard_avatar/pose_selection.py:86-173`).

**Implementation implication:** promotion cannot mean making all 50 autonomous. Add a small audiobook graph or performance layer with carefully curated access. First promote `front_idle_wings`, `front_greeting_wave_wings`, `front_thinking_hand_chin_wings`, `front_explaining_open_hand_wings`, `front_point_side_wings`, `front_explaining_both_hands_wings`, and `front_sincere_hand_heart_wings`. Treat emotion pairs as state targets, not random gestures.

### F2. Critical: speech and body acting are mutually exclusive on the production path

The engine's current safety rule prevents an `explaining` upper-body pose from replacing the body during active speech. That protects locomotion and avoids uncontrolled gesticulation, but it also means the audiobook performer becomes physically inert at the exact moment performance is needed.

**Evidence:** `_effective_action` returns `None` for speaking with a `speech_id` (`wizard_avatar/pose_selection.py:141-150`), and semantic gesture actions run only when `speech_id is None` (`wizard_avatar/controller.py:291-305`). The test suite explicitly expects speech to retain an idle/profile body (`tests/wizard/test_pose_selection.py:201-224`).

**Implementation implication:** do not remove the safety boundary globally. Add a speech-safe, front-facing gesture overlay or an audiobook-only body-gesture lane with a restricted allowlist. The lane should preserve locomotion ownership and exclude combat, flight, and large root changes.

### F3. High: intent richness collapses to discrete action firing

The semantic map already contains good restraint concepts: amplitude caps, tempo, holds, flourish permission, priority, persona style, seriousness reduction, and approval/safety clamps. The controller stores `semantic_amplitude`, but body selection does not consume it. `hold` and `allow_flourish` do not govern pose duration or eligibility. Tempo only changes a one-shot action timer.

**Evidence:** compare `wizard_avatar/definitions/semantic_animation_map.json:4-124` with `wizard_avatar/controller.py:277-310` and `wizard_avatar/pose_selection.py:110-173`.

**Implementation implication:** make amplitude choose within a pose family, not scale the whole character. Example: low `speak` stays in `front_idle_wings` with eyes/mouth; medium uses `front_explaining_open_hand_wings`; high, if text intent warrants, uses `front_explaining_both_hands_wings`. `allow_flourish=false` must exclude `front_staff_spin_flourish`, magic peaks, airborne reactions, and celebrations.

### F4. High: transition metadata does not produce emotional transitions

The graph has 47 authored directed transitions and recipes named `contact_match`, `marker_gate`, `phase_match`, `snapshot_handoff`, and `coherent_cut`. The selector records a selected transition ID, resets the target clip to tick zero, and immediately renders that target. The frame source then explicitly forces atomic presentation. This is technically coherent but dramatically abrupt.

**Evidence:** `wizard_avatar/pose_selection.py:86-107`, `wizard_avatar/animation_graph.py:305-316`, and `wizard_avatar/frame_source.py:159-181`.

**Implementation implication:** keep atomic sprite presentation. Emotional continuity should be authored as pose sequences and holds: current attitude -> readable micropause or character neutral -> target attitude -> settle. Do not revive per-cell dissolve, which the renderer correctly rejects as a source of false limbs and facial artifacts.

### F5. High: clip policy is descriptive more than operative

Clips declare minimum holds, interruption policy, legal successors, entry/exit markers, channel ownership, and secondary curves. The production selector evaluates clip samples but does not gate node replacement on these policies. Most one-shot clips are 9-21 authored frames, or 0.375-0.875 seconds at 24 fps, then clamp to their final frame until state changes.

**Evidence:** clip evaluation clamps non-loop clips at their last frame (`wizard_avatar/animation_graph.py:230-264`); metadata is parsed at `wizard_avatar/animation_graph.py:569-657`; node changes are immediate at `wizard_avatar/pose_selection.py:86-101`.

**Implementation implication:** the audiobook scheduler must own minimum readable holds, interruption points, gesture cooldown, emotional hysteresis, and recovery. Otherwise upstream semantic events can produce pose chatter even though the JSON appears to describe restraint.

### F6. High: mouth rhythm is mechanical and detached from narration

The reference performer cycles four mouth states at 10 Hz whenever speaking. It does not use phoneme, word, syllable, stress, pause, or audio-energy timing. A regular oscillator is highly visible over long-form audio and fights the natural pacing standard expected in audiobooks.

**Evidence:** `wizard_avatar/frame_source.py:351-360` and `wizard_avatar/mouth.py:24-26`.

**Implementation implication:** at minimum, drive mouth openness from time-aligned speech activity with closed holds during pauses and plosive closures. Prefer word or phoneme timing when available. Add slight phrase-level variation, but keep body gestures independent from every mouth accent.

### F7. Medium: blink and eye behavior do not yet support thought

The reference path uses a threshold on `state.blink_phase`, while the fallback path uses a fixed deterministic interval. Eye aim can respond to target point, thinking, skeptical expression, or facing, which is a useful base. There is no blink suppression during key reads, blink-on-thought-change, gaze return, or phrase-boundary behavior.

**Evidence:** `wizard_avatar/blink.py:4-25`; `wizard_avatar/frame_source.py:183-248` and `281-297`.

**Implementation implication:** keep deterministic replay, but seed a bounded blink schedule from semantic beats. Use a blink or brief gaze shift as a high-frequency accent only when it supports thought processing. Avoid constant eye wandering.

### F8. Medium: there is no persistent single-performer performance state

`WizardState` carries current action, expression, mouth, pose IDs, semantic cue, gesture, and amplitude. It does not carry narrator baseline, current emotional trajectory, previous emotional target, gesture history, recent peak, phrase/paragraph boundary, chapter energy, or a continuity checkpoint.

**Evidence:** `wizard_avatar/models.py:123-169` and the continuity requirements from ACX and the Audio Publishers Association above.

**Implementation implication:** add a compact performance state separate from story content. It should contain only structural direction: narrator attitude, energy band, emotional valence/arousal, last main pose, last gesture family, cooldown, current hold, and continuity checkpoint. Do not put manuscript text or private content into visual state.

### F9. Medium: pose semantics contain near-duplicate choices that need editorial ownership

Poses 40-59 revisit many meanings already present in poses 11-39: run, crouch, guard, jump, kneel, staff windup/block, point, shush, celebration, and magic. Randomly mixing old and new equivalents would create costume/scale/silhouette jitter and weaken the sense of one performer.

**Evidence:** ordered manifest tags and the inspected feelings contact sheet. The runtime grouping documentation also identifies fit, contact, staff, overlay, and looping risks (`docs/pose-library-expansion/RUNTIME_GROUPING_PLAN.md:219-226`).

**Implementation implication:** appoint one canonical pose per performance meaning and use alternates only as intensity variants in a controlled family. Do not expose semantic duplicates as equal random choices.

### F10. High: the current stream misses its bounded deadline test

The full suite consistently fails the frame-loop test intended to prove that delayed rendering drops missed presentation deadlines without starving publication. The test adds a 60 ms delay, waits 340 ms, and expects 3-5 published frames; this audit observed 2 in the full suite and 1 in each of three isolated reruns. The synchronous compositor runs inside the stream loop's lock before publication.

**Evidence:** `tests/wizard/test_stream_hub.py:68-95` and `wizard_avatar/stream.py:151-190`.

**Implementation implication:** profile frame composition and encoding before adding more performance channels. Audiobook rhythm cannot be evaluated reliably if intended holds and micropause frames are skipped unpredictably. Preserve the existing no-catch-up-burst policy, but establish a tested presentation budget or decouple expensive composition from the timing-critical publication loop.

### F11. Strength: the renderer already provides a disciplined stage

The fixed white studio, faint perspective floor, root projection, contact shadow, front/profile/back views, per-pose anchors, and independent expression channels give the performer a stable visual home. The character remains readable at small scale, and the strongest front-facing poses have clear silhouettes.

**Implementation implication:** keep Wizard Joe near the established front-facing mark for narration. Use profile or back views only for motivated scene transitions, not ordinary character differentiation. Staging clarity is more valuable than demonstrating directional coverage.

### F12. Strength: safety and determinism are suitable foundations

Semantic signals are content-free, bounded, priority-governed, and locomotion-preserving. Runtime ticks and pose evaluation are deterministic. Tests verify graph reachability, API acceptance, face changes, and runtime command flow.

**Implementation implication:** build the audiobook director as a deterministic policy layer with replayable decisions. Do not move story interpretation into the renderer or weaken command ownership.

## Performance model for one audiobook performer

### Layer 1: characterful neutral, the bass line

Wizard Joe should spend most listening time in one authored, in-character neutral: `front_idle_wings` after promotion, with `front_idle` as compatibility fallback. This is not inactivity. Eye aim, blink, mouth, a slight posture/energy state, and occasional breathing-scale secondary motion sustain life without competing with the prose.

### Layer 2: thought and attitude, the middle line

At a clause, sentence, or thought boundary, use a restrained change within the current attitude:

- Thinking/recall: `front_thinking_hand_chin_wings`, usually entered after a short still beat.
- Explanation: `front_explaining_open_hand_wings`; reserve `front_explaining_both_hands_wings` for a genuine increase in commitment.
- Reference/deictic emphasis: `front_point_side_wings` for an idea or place; use direct point poses rarely because pointing at the listener reads confrontational.
- Sincerity/intimacy: `front_sincere_hand_heart_wings`.
- Greeting/chapter open: `front_greeting_wave_wings`, once, then settle.

### Layer 3: emotional state, not emotional stickers

Use `feeling_*_full` poses as sustained body attitudes and `feeling_*_close` as stronger facial/upper-body readings of the same state. Despite the `close` source names, the Python runtime geometries are normalized full-body snapshots; they do not imply a camera cut. Transition because the character's thought changes, not because an emotion word appears in text.

Emotions should decay toward the characterful neutral over a sentence or scene boundary. Adjacent emotions should pass through a readable processing beat unless the story calls for a shock cut. Surprise and fear may enter quickly; sadness, shame, guilt, pride, and love generally need longer reads to avoid becoming pictograms.

### Layer 4: story punctuation, the high line

Combat, magic, flight, jump, fall, block, flourish, and celebration poses are punctuation. They should appear only for narrated events or chapter-level peaks, not as conversational emphasis. A high-energy pose should recover through a grounded bridge and should not be followed immediately by another unrelated peak.

## Explicit 89-pose mapping

**Current role legend:** `C` = reachable graph clip sample; `D` = `diagnostic_only`, currently unreachable through ordinary graph action selection.
**Direction legend:** `BASE` = sustained performer; `GESTURE` = speech-safe candidate; `EMOTION` = emotional state; `PUNCT` = rare story punctuation; `MOVE` = locomotion/scene transition; `HOLD` = keep out of autonomous audiobook selection for now.

| # | Real pose ID | Role | Audiobook direction |
|---:|---|:---:|---|
| 1 | `front_idle` | C | `BASE`: compatibility neutral and universal recovery. |
| 2 | `back_idle` | C | `MOVE`: motivated turn-away or scene transition only. |
| 3 | `profile_left` | C | `MOVE`: brief addressed-aside staging; not a character voice switch. |
| 4 | `profile_right` | C | `MOVE`: brief addressed-aside staging; not a character voice switch. |
| 5 | `walk_front_left` | C | `MOVE`: grounded travel cycle only. |
| 6 | `walk_front_right` | C | `MOVE`: grounded travel cycle only. |
| 7 | `back_left` | C | `MOVE`: rear walk/turn only. |
| 8 | `back_right` | C | `MOVE`: rear walk/turn only. |
| 9 | `explaining` | C | `GESTURE`: existing speech-safe fallback; medium explanation. |
| 10 | `magic_cast` | C | `PUNCT`: literal magic or major imaginative peak only. |
| 11 | `run_front_airborne_reach` | C | `MOVE`: dash bridge; never conversational emphasis. |
| 12 | `run_front_airborne_drive` | C | `MOVE`: run beat; avoid autonomous looping as a speech gesture. |
| 13 | `front_crouch_guard` | C | `PUNCT`: defensive anticipation or threat response. |
| 14 | `front_reaction_jump_fist_staff` | C | `PUNCT`: high-energy shock/celebration; very rare. |
| 15 | `front_kneel_staff_brace` | C | `PUNCT`: impact recovery, exhaustion, or solemn beat. |
| 16 | `front_staff_guard_windup` | C | `PUNCT`: anticipation into literal guard/cast action. |
| 17 | `front_staff_guard_low` | C | `PUNCT`: defensive hold and recovery bridge. |
| 18 | `walk_front_right_lift` | C | `MOVE`: passing pose within grounded travel. |
| 19 | `front_crouch_reaction_staff_planted` | C | `PUNCT`: grounded shock or recovery, with a long settle. |
| 20 | `front_victory_cast` | C | `PUNCT`: chapter-scale triumph or cast peak. |
| 21 | `fly_front_hover_neutral` | C | `MOVE`: airborne neutral for literal flight scenes. |
| 22 | `fly_front_knee_up` | C | `MOVE`: hover/flap phase only. |
| 23 | `fly_front_wings_up` | C | `MOVE`: hover/flap phase only. |
| 24 | `fly_front_wings_down` | C | `MOVE`: hover/flap phase only. |
| 25 | `fly_southeast_forward_glide` | C | `MOVE`: forward flight/travel only. |
| 26 | `fly_southwest_banked_staff` | C | `MOVE`: left bank/turn only. |
| 27 | `fly_southeast_banked_staff` | C | `MOVE`: right bank/turn only. |
| 28 | `fly_southeast_cheer` | C | `PUNCT`: airborne celebration only. |
| 29 | `fly_southeast_staff_forward` | C | `PUNCT`: literal aerial staff action. |
| 30 | `front_run_charge_right_plant` | C | `MOVE`: charge acceleration; literal action only. |
| 31 | `front_crouch_landing_staff_plant` | C | `MOVE`: landing/contact bridge. |
| 32 | `front_magic_staff_thrust` | C | `PUNCT`: literal magic attack; exclude from speech flourish. |
| 33 | `front_airborne_fall_back_staff` | C | `PUNCT`: impact/fall reaction only. |
| 34 | `front_celebrate_wings_staff_up` | C | `PUNCT`: strongest grounded celebration; use at true payoff. |
| 35 | `front_staff_block_horizontal` | C | `PUNCT`: literal block/defense. |
| 36 | `front_point_direct_staff_held` | C | `GESTURE`: direct address; rare and intentional. |
| 37 | `front_celebrate_jump_staff_up` | C | `PUNCT`: extreme celebration; chapter peak only. |
| 38 | `front_shush_secret_staff_held` | C | `GESTURE`: secret/shush; only when semantically literal and not over speech. |
| 39 | `front_staff_spin_flourish` | C | `PUNCT`: spectacle flourish; never routine narration. |
| 40 | `run_front_cross_step_wings_staff` | D | `HOLD`: alternate run image; keep diagnostic until canonicalized. |
| 41 | `run_front_stride_wings_staff` | D | `HOLD`: alternate run image; keep diagnostic until canonicalized. |
| 42 | `front_crouch_guard_wings` | D | `HOLD`: semantic duplicate/intensity alternate for pose 13. |
| 43 | `front_reaction_jump_wings_staff` | D | `HOLD`: semantic duplicate/intensity alternate for pose 14. |
| 44 | `front_kneel_staff_brace_wings` | D | `HOLD`: semantic duplicate/intensity alternate for pose 15. |
| 45 | `front_staff_guard_windup_wings` | D | `HOLD`: semantic duplicate/intensity alternate for pose 16. |
| 46 | `front_staff_guard_horizontal_wings` | D | `HOLD`: guard alternate; resolve against poses 17/35 first. |
| 47 | `front_staff_guard_low_wings` | D | `HOLD`: semantic duplicate/intensity alternate for pose 17. |
| 48 | `front_crouch_staff_planted_wings` | D | `HOLD`: semantic duplicate/intensity alternate for pose 19. |
| 49 | `front_victory_cast_wings` | D | `HOLD`: semantic duplicate/intensity alternate for pose 20. |
| 50 | `front_run_charge_wings` | D | `HOLD`: semantic duplicate/intensity alternate for pose 30. |
| 51 | `front_crouch_hand_plant_wings` | D | `HOLD`: landing/recovery alternate; contact review required. |
| 52 | `front_magic_staff_thrust_wings` | D | `HOLD`: semantic duplicate/intensity alternate for pose 32. |
| 53 | `front_airborne_fall_back_wings` | D | `HOLD`: semantic duplicate/intensity alternate for pose 33. |
| 54 | `front_celebrate_staff_up_wings` | D | `HOLD`: semantic duplicate/intensity alternate for pose 34. |
| 55 | `front_staff_block_wings` | D | `HOLD`: semantic duplicate/intensity alternate for pose 35. |
| 56 | `front_point_direct_wings` | D | `GESTURE`: direct point alternate; choose one canonical direct point. |
| 57 | `front_celebrate_jump_wings` | D | `HOLD`: semantic duplicate/intensity alternate for pose 37. |
| 58 | `front_shush_wings` | D | `GESTURE`: shush alternate; choose one canonical shush and protect mouth. |
| 59 | `front_staff_spin_wings` | D | `HOLD`: semantic duplicate/intensity alternate for pose 39. |
| 60 | `front_idle_wings` | D | `BASE`: first promotion; canonical audiobook neutral. |
| 61 | `front_greeting_wave_wings` | D | `GESTURE`: chapter/session greeting, then settle. |
| 62 | `front_thinking_hand_chin_wings` | D | `GESTURE`: thought, recall, uncertainty; hold rather than pulse. |
| 63 | `front_explaining_open_hand_wings` | D | `GESTURE`: first-choice low/medium explanation pose. |
| 64 | `front_point_side_wings` | D | `GESTURE`: referential point that does not confront the listener. |
| 65 | `front_explaining_both_hands_wings` | D | `GESTURE`: high-commitment explanation; use less often than pose 63. |
| 66 | `front_magic_staff_raise_wings` | D | `PUNCT`: wonder, invocation, or literal magic rise. |
| 67 | `front_sincere_hand_heart_wings` | D | `GESTURE`: intimacy, gratitude, confession, or earnest narration. |
| 68 | `front_playful_kick_wings` | D | `PUNCT`: playful release; rare, genre- and scene-dependent. |
| 69 | `front_magic_staff_spark_wings` | D | `PUNCT`: literal magic reveal or imaginative accent. |
| 70 | `feeling_joy_full` | D | `EMOTION`: sustained open joy body attitude. |
| 71 | `feeling_sadness_full` | D | `EMOTION`: sustained lowered sadness body attitude. |
| 72 | `feeling_anger_full` | D | `EMOTION`: contained anger; avoid repetitive pumping. |
| 73 | `feeling_fear_full` | D | `EMOTION`: fear body attitude; quick entry, controlled recovery. |
| 74 | `feeling_shame_full` | D | `EMOTION`: inward shame; longer hold for readability. |
| 75 | `feeling_disgust_full` | D | `EMOTION`: aversion; use for character attitude, not narrator judgment. |
| 76 | `feeling_surprise_full` | D | `EMOTION`: surprise peak; enter quickly and decay quickly. |
| 77 | `feeling_pride_full` | D | `EMOTION`: lifted confidence/pride; distinguish from celebration. |
| 78 | `feeling_guilt_full` | D | `EMOTION`: inward guilt; sustain through thought beat. |
| 79 | `feeling_love_full` | D | `EMOTION`: open affection; reserve decorative hearts for explicit tone. |
| 80 | `feeling_joy_close` | D | `EMOTION`: stronger facial joy variant; no camera cut implied. |
| 81 | `feeling_sadness_close` | D | `EMOTION`: stronger facial sadness variant; hold gently. |
| 82 | `feeling_anger_close` | D | `EMOTION`: stronger facial anger; cap duration and frequency. |
| 83 | `feeling_fear_close` | D | `EMOTION`: stronger facial fear; avoid rapid alternation with surprise. |
| 84 | `feeling_shame_close` | D | `EMOTION`: stronger facial shame; use after a processing beat. |
| 85 | `feeling_disgust_close` | D | `EMOTION`: stronger facial disgust; character-specific only. |
| 86 | `feeling_surprise_close` | D | `EMOTION`: stronger facial surprise; brief accent. |
| 87 | `feeling_pride_close` | D | `EMOTION`: stronger facial pride; controlled, not smug by default. |
| 88 | `feeling_guilt_close` | D | `EMOTION`: stronger facial guilt; long-form continuity required. |
| 89 | `feeling_love_close` | D | `EMOTION`: stronger facial affection; decorative effect policy required. |

## Recommended implementation sequence

### Priority 0: establish the direction contract

Define an audiobook performance intent that is structural and content-free:

- `thought_boundary`: none, clause, sentence, paragraph, scene, chapter.
- `performer_mode`: narration, quoted_dialogue, inner_voice, scene_action.
- `attitude`: neutral, warm, reflective, direct, playful, guarded.
- `emotion_target`: one of the ten existing emotion families plus neutral.
- `emotion_intensity`: bounded low/medium/high or 0-1.
- `gesture_intent`: none, greet, think, explain, reference, sincere, shush.
- `energy_band`: still, quiet, conversational, heightened, peak.
- `pause_window_ms`, `hold_window_ms`, and `can_interrupt`.

The renderer should receive only this direction and timing, never manuscript text.

### Priority 1: create an audiobook-safe graph subset

Promote poses 60-65 and 67 first. Give each an explicit clip with entry neutral, readable key hold, and return neutral. Keep 66, 68, and 69 as rare punctuation. Keep 40-59 diagnostic until each meaning has one canonical winner.

Initial allowlist during speech:

`front_idle_wings`, `front_greeting_wave_wings`, `front_thinking_hand_chin_wings`, `front_explaining_open_hand_wings`, `front_point_side_wings`, `front_explaining_both_hands_wings`, `front_sincere_hand_heart_wings`, plus `explaining` as fallback.

### Priority 2: enforce restraint and emotional continuity

Use these as **calibration starting points**, not immutable constants:

- Main pose changes: no more than one per thought unit.
- Characterful neutral: target roughly 70-85% of ordinary narration time.
- Gesture cooldown: start around 2-4 seconds, reset only at a new thought boundary.
- Repeat protection: do not select the same non-neutral gesture twice consecutively.
- Thought micropause: test 4-6 authored frames at 24 fps before a non-shock emotion change.
- Readable key hold: test 8-18 authored frames based on silhouette complexity and emotional weight.
- Peak recovery: require a grounded neutral or related emotion before another unrelated peak.
- Emotion hysteresis: require either a scene event, a sustained target, or a material intensity delta before switching families.

### Priority 3: build three rhythmic timescales

- **Bass:** sustained body pose and scene attitude over sentences or paragraphs.
- **Middle:** weight shift, hand gesture, or pose intensity change at thought boundaries.
- **High:** blink, gaze, brow, mouth, and small head accent around selected vocal stress.

Do not drive all three from the same word-level event. This is the direct implementation of professional guidance to layer rhythms while preserving moments of stillness.

### Priority 4: align mouth and face to audio

Accept timestamped speech activity first, then phoneme/viseme timing when available. Preserve explicit closed-mouth frames, vary jaw opening by stress, and let expression affect mouth corners without replacing speech closure requirements. Add tests for silent gaps, plosives, long vowels, and emotional speech.

### Priority 5: validate long-form, not only clips

Create a representative 15-minute visual performance checkpoint containing:

- narration, dialogue, inner thought, action, and a quiet reflective passage;
- at least three emotional transitions, including one interrupted transition;
- chapter opening and closing behavior;
- repeated character appearances separated by several minutes;
- a continuity restart from a saved performance checkpoint.

Review it once for acting and once for technical continuity, mirroring professional audiobook QC practice. Then run a chapter-length soak and inspect gesture density, neutral occupancy, repeated-pose rate, emotion churn, mouth/pause alignment, and root/contact stability.

## Acceptance criteria

The audiobook performance layer is ready for production evaluation when all of the following are true:

1. Every ordinary narration state resolves to a characterful front-facing neutral or a speech-safe allowlisted gesture.
2. Active speech can coexist with approved body acting without taking locomotion ownership.
3. `amplitude`, `hold`, `tempo`, and flourish permission produce observable, tested policy differences.
4. A thought or emotional transition can be replayed deterministically with its processing beat, hold, and recovery intact.
5. No `diagnostic_only` pose becomes autonomous without an authored clip, canonical family role, and interruption policy.
6. Emotion family changes are hysteretic and do not respond directly to isolated emotion words.
7. Mouth closures and pauses align to speech timing; no constant oscillator is visible over sustained narration.
8. A representative 15-minute checkpoint reads as one performer and passes director review for pacing, tone, clarity, restraint, and continuity.
9. A chapter-length soak shows no pose chatter, repeated flourish loop, baseline jump, staff pop, face-overlay conflict, or character identity drift.
10. The stream deadline test passes consistently under the target runtime profile, with dropped presentation deadlines recorded and without simulation catch-up bursts.
11. Existing deterministic runtime, content-free semantic signaling, and command ownership tests remain green.

## Risks and controls

| Risk | Why it matters | Control |
|---|---|---|
| Over-gesticulation | Competes with prose and exhausts the performer over hours. | Thought-boundary gating, cooldown, neutral occupancy target, repeat protection. |
| Emotion-as-keyword pantomime | Produces literal, condescending, or false acting. | Scene/subtext intent upstream; emotion hysteresis; director-curated mappings. |
| Pose popping | Atomic snapshots can look like editing errors. | Authored anticipation, micropause, related-pose bridges, key holds, grounded recovery. |
| Identity drift | Near-duplicate pose families read as different models or performers. | One canonical pose per meaning; alternates are explicit intensity variants. |
| Mouth metronome | Fixed-rate mouth cycling becomes mechanical in long form. | Audio/phoneme timing with closures and silence holds. |
| Facial/body contradiction | A face overlay may fight a baked emotional body pose. | Compatibility matrix for body emotion, brow, eyes, and mouth. |
| Decorative effect fatigue | Hearts, sparks, and motion arcs can dominate narration. | Literal-event or peak-only eligibility; flourish permission enforced. |
| Root/contact discontinuity | Low, airborne, and planted-staff poses can jump or slide. | Preserve current root/contact metadata; require bridge and long-form contact tests. |
| Directional staging loss | Profiles/back views reduce facial readability. | Front-facing default; directional views only for motivated scene transitions. |
| Presentation deadline misses | Skipped frames can erase short holds, mouth closures, or emotional micropause beats. | Profile compositor/codec cost; set a frame budget; test timing under representative 15-minute load. |
| Private-content coupling | Story text in renderer state would weaken governance. | Keep direction structural and content-free, matching the current semantic boundary. |

## Final recommendation

Do not expand the pose library again before directing the 89 poses already present. The next unit of value is not another image; it is a deterministic performance scheduler that can choose less, hold longer, transition with thought, and remember who Wizard Joe is across a chapter.

Promote the seven speech-safe poses first, establish `front_idle_wings` as the characterful audiobook neutral, then integrate the ten full emotion poses as sustained attitudes. Keep the ten `close` emotion variants as intensity alternatives and keep combat, flight, magic, fall, and celebration families out of ordinary narration. Validate the result on a representative 15-minute performance before broadening autonomy.
