# Character Performance Animator Audit

**Project:** Wizard Joe Audiobook Performance Engine

**Scope:** `WizardJoeAvatar-python` whole-body acting and motion performance

**Audit date:** 2026-07-13

**Repository revision audited:** `7781a67c97bfbfa16a64d5b9fb12bdf74bd4c032`

**Ownership boundary:** Research and recommendations only. No production code was changed.

## Executive assessment

Wizard Joe has a stronger authored pose foundation than the current performance
suggests. The active graph contains readable anticipation, commitment, effect,
contact, hold, and recovery landmarks; the 89-pose catalog also contains several
excellent speech-safe whole-body poses that are not reachable in normal playback.
The current runtime, however, behaves as a deterministic pose sequencer rather
than a character performer.

The highest-impact problem is not lack of art. It is that the runtime does not
execute much of the performance information already declared in the graph.
Transition policies, interrupt windows, minimum holds, planted anchors, legal
successors, and secondary curves are loaded but not enforced by production pose
selection. Actual speech deliberately suppresses the `speaking`/`explaining`
body clip. Facing changes bypass the authored `turn` node. Starts and stops have
no distinct performed phase. Every semantic action resolves to one fixed clip,
so repeated beats become visibly mechanical.

**Readiness:** strong pose assets, partial motion grammar, low audiobook acting
readiness. Build a deterministic performance scheduler above the current graph,
promote a small speech-safe pose vocabulary, and make contact/phase metadata
operational before commissioning a large new asset set.

## Method

The audit covered:

- public action and state definitions in `wizard_avatar/models.py`;
- command timing and semantic routing in `wizard_avatar/controller.py`;
- locomotion acceleration, deceleration, facing, and stop behavior in
  `wizard_avatar/locomotion.py` and `wizard_avatar/views.py`;
- graph evaluation and production selection in `wizard_avatar/animation_graph.py`
  and `wizard_avatar/pose_selection.py`;
- final pose presentation in `wizard_avatar/frame_source.py`;
- the 89-pose catalog and graph-v2 clips, nodes, markers, transitions, contacts,
  and secondary curves;
- focused visual inspection of the idle, explanation, point, guard, crouch, and
  run source poses;
- current professional and primary sources from Walt Disney Animation Studios,
  Animation Mentor, the McNeill Lab, MIT, Epic Games, Ubisoft production teams,
  and Ubisoft La Forge.

Counts were derived directly from JSON, not documentation: 89 cataloged and
classified poses, 28 clips, 28 nodes, 47 transitions, 5 transition recipes, 39
unique clip-sample poses, and 50 poses absent from all clips.

Focused verification ran
`python3 -m unittest tests.wizard.test_pose_selection tests.wizard.test_production_animation_wiring tests.wizard.test_semantic_animation`:
31 tests passed, 0 failed. These tests confirm current routing and wiring; they
do not prove the performance qualities recommended below.

## Professional performance standard

### Whole-body acting and weight

Walt Disney Animation Studios describes character performance as the combined
use of timing, staging, anticipation, follow-through, secondary action, anatomy,
weight, movement, and appeal. This is a whole-body standard: a facial or mouth
change alone is not the performance. [Walt Disney Animation Studios, Animation](https://www.disneyanimation.com/process/animation/)

Animation Mentor's April 2026 pose tutorial gives a practical review test:
meaning, silhouette, line of action, and contrapposto. It flags symmetry without
weight shift, hidden acting, and screen-parallel body lines as stiff; it recommends
clear negative space, hip/shoulder counter-rotation, support against load, and a
line of action that communicates force. [Animation Mentor, Building Appealing Character Poses](https://www.animationmentor.com/blog/tutorial-building-appealing-character-poses-for-animation/)

**Audit criterion:** every important beat should read first in the torso, root,
support leg, shoulder line, and silhouette, with face, hands, staff, robe, and
wings reinforcing one intention.

### Starts, stops, turns, and continuity

Epic's current Unreal Engine 5.8 guidance treats loops, pivots, and stops as
distinct locomotion material, uses trajectory and foot pose data for selection,
and exposes pose-reselection history to prevent recent poses being chosen again.
Its distance-matching guidance explicitly treats stop, start, and pivot as
locomotion transitions rather than instantaneous state changes.
[Epic Games, Motion Matching](https://dev.epicgames.com/documentation/en-us/unreal-engine/motion-matching-in-unreal-engine)
[Epic Games, Distance Matching](https://dev.epicgames.com/documentation/en-us/unreal-engine/distance-matching-in-unreal-engine)

Ubisoft's Far Cry 6 production account describes a walk-to-jog change as walking,
then acceleration, then jogging, selected at an appropriate moment from current
pose and expected motion. [Ubisoft, How AI Helped Animate Yara's Hero](https://news.ubisoft.com/en-gb/article/27176jslYNMPt7vBfCaRQ1/far-cry-6-how-ai-helped-animate-yaras-hero)

**Audit criterion:** intent changes must be performed through preparation,
support transfer, acceleration/deceleration, pivot, settle, and facing continuity.
Changing a velocity or facing enum is necessary control logic, not a visible turn.

### Gesture phrasing

The McNeill Lab defines a gesture phrase as preparation, optional prestroke hold,
stroke, optional poststroke hold, and retraction, with the stroke carrying the
imagistic content and maintaining speech synchrony. The MIT Speech Communication
Group independently operationalizes preparation, prestroke hold, stroke as peak
effort, poststroke hold, recovery, and relaxed rest.
[McNeill Lab, Introduction to Gesture Annotation](https://mcneilllab.uchicago.edu/analyzing-gesture/intro_to_annotation.html)
[MIT Speech Communication Group, Gesture Coding Manual](https://scg.mit.edu/gesture/coding-manual.html)

**Audit criterion:** a gesture is a timed phrase around a meaning-bearing stroke,
not a pose fired for an arbitrary number of milliseconds. Adjacent gestures may
co-articulate, but they still need a readable effort peak and a motivated route
to or from rest.

### Variation without noise

Ubisoft La Forge's motion-matching work emphasizes current posture, future
trajectory, foot locking, and a sufficiently broad motion set. Its in-betweening
research adds controllable stochasticity early in a transition while converging
on the target, showing a useful principle: vary the route, not the intended beat.
Epic's current pose-reselection history serves the same practical goal by
preventing immediate reuse.
[Ubisoft La Forge, Introducing Learned Motion Matching](https://www.ubisoft.com/en-us/studio/laforge/news/6xXL85Q3bF2vEj76xmnmIu/introducing-learned-motion-matching)
[Ubisoft La Forge, Robust Motion In-betweening](https://www.ubisoft.com/en-us/studio/laforge/news/2NBPwJzPl3DwCAzGTav7Tg/robust-motion-inbetweening)

**Audit criterion:** variation must be state-aware, bounded, reproducible, and
subject to recency/cooldown rules. Unseeded jitter would be no better than exact
repetition.

## Code-grounded findings

### F1. Critical: body acting is disabled during actual speech

`_cmd_speak` sets `action="speaking"` and `upper_body_action="explain"`
(`wizard_avatar/controller.py:328-339`), but `_effective_action` returns no graph
action whenever `speech_id` is present (`wizard_avatar/pose_selection.py:141-150`).
Semantic gestures are likewise fired only when `speech_id is None`
(`wizard_avatar/controller.py:291-305`). The test suite makes this deliberate:
active speech keeps the profile or locomotion pose instead of using
`explain_front` (`tests/wizard/test_pose_selection.py:201-224`). Mouth movement is
then a fixed four-state 10 Hz cycle (`wizard_avatar/frame_source.py:351-360`).

**Implication:** the character becomes least physically expressive while doing
the audiobook's core job. This is safe for locomotion ownership, but it is not
whole-body acting.

**Recommendation:** preserve the safety boundary for arbitrary actions, but add
an audiobook-only speech gesture lane. It should own only `body`, `staff`,
`wings`, and optional `mouth` for a restricted front-facing vocabulary, preserve
root/locomotion ownership, and synchronize strokes to phrase emphasis supplied by
the audiobook performance timeline.

### F2. Critical: declared transition and interruption grammar is descriptive only

The graph model parses `minimum_hold_ticks`, `interrupt_policy`, markers,
`legal_successors`, transition duration/timing/phase/root/contact policies, and
transition recipes (`wizard_avatar/animation_graph.py:119-172`). Production pose
selection only records the matching `transition_id`, swaps node/clip, resets the
clip tick, and immediately evaluates the target (`wizard_avatar/pose_selection.py:86-107`).
A repository-wide use scan finds no production enforcement of minimum holds,
interrupt windows, legal successors, or active markers outside graph evaluation
and validation.

The renderer then explicitly treats each authored sprite as an atomic snapshot
and forces `pose_transition_progress=1.0` (`wizard_avatar/frame_source.py:159-181`).
Atomic sprites are a defensible ASCILINE presentation choice, but without a
performed transition recipe the result is a hard pose replacement.

**Implication:** `action_commit`, `action_effect`, `action_recoverable`, contact
markers, hold markers, and the five recipes do not govern visible performance.
Actions may be cut by a short caller duration or hold their last frame until an
unrelated timer ends.

**Recommendation:** introduce an integer-tick clip player that owns phase,
crossed markers, pending interrupt, and successor selection. For square-cell art,
prefer authored transition poses and contact-locked snapshot handoffs over a
per-cell dissolve.

### F3. Critical: starts, stops, and turns are state changes, not acted events

The graph declares `grounded_start`, `grounded_stop`, and a `turn` node, but
`_graph_mobility` can return only `grounded_walk` or `grounded_idle` on the ground
(`wizard_avatar/pose_selection.py:153-158`). No production branch selects the
`turn` node. `_cmd_face` assigns the new direction directly
(`wizard_avatar/controller.py:189-197`), while moving facing advances one 45-degree
sector per simulation tick (`wizard_avatar/locomotion.py:34-42` and
`wizard_avatar/views.py:74-86`).

`LocomotionController.stop()` zeros velocity immediately
(`wizard_avatar/locomotion.py:69-74`). Direct control does decelerate and point
motion slows near arrival, which is a good physical foundation, but the visible
node still switches directly between idle and the cyclic walk. The selected
`idle_to_walk`/`walk_to_idle` transition metadata is not executed.

The authored `turn_views` clip itself is only `profile_left -> profile_right` for
all eight facings. Even if made reachable, it does not encode source direction,
target direction, turn side, support foot, or turn magnitude.

**Implication:** starts lack a preparatory lean and first support transfer; stops
lack braking, last contact, overshoot, and settle; turns can flip view while the
feet and mass provide no cause.

**Recommendation:** make `grounded_start`, `grounded_stop`, and `turn` real
runtime mobility phases. Select by current/future velocity, signed heading delta,
and planted foot. A minimal first pass can reuse contact poses, but production
quality needs dedicated left/right start, stop, 45/90-degree pivot, and in-place
turn samples.

### F4. High: contact and weight are authored but not presented as constraints

The graph carries `support_contact` and `planted_anchor` per sample. The walk
clips are distance-driven, and locomotion advances `walk_phase` by traveled
distance over `STRIDE_LENGTH` (`wizard_avatar/locomotion.py:120-126,145-151`).
These are sound foundations. However, `PoseSample` returns only a contact label,
not the planted anchor, and the frame source places every target by its root
anchor (`wizard_avatar/pose_selection.py:18-23,102-107`;
`wizard_avatar/frame_source.py:128-146`). No foot or staff-tip correction keeps
the declared support point fixed between samples.

The graph also declares weight-carrying secondary curves such as `walk_bob`,
`walk_staff_lag`, `walk_robe_lag`, `idle_breathe`, `turn_staff_lag`, and
`hit_fall_arc`. Outside graph loading, none is consumed by production Python.

**Implication:** the data says where the weight is, but the rendered body does not
solve to that support. Root, feet, robe, staff, and wings can all change together,
which reads as a swapped picture rather than mass moving through space.

**Recommendation:** carry `planted_anchor` through `PoseSample`; compute a root
correction that keeps the outgoing and incoming support anchor coincident; change
support only at contact/release markers; and implement the existing secondary
curves as small deterministic offsets with strict amplitude caps.

### F5. High: the best speech silhouettes are present but unreachable

The active graph references 39 unique poses. Fifty cataloged poses are absent
from every clip. The unused set includes:

- `front_idle_wings`
- `front_greeting_wave_wings`
- `front_thinking_hand_chin_wings`
- `front_explaining_open_hand_wings`
- `front_point_side_wings`
- `front_explaining_both_hands_wings`
- `front_sincere_hand_heart_wings`
- `front_playful_kick_wings`
- `front_magic_staff_raise_wings`
- `front_magic_staff_spark_wings`
- twenty `feeling_*_full` / `feeling_*_close` emotion poses

Visual inspection confirms that active `explaining` and
`front_point_direct_staff_held` have clear hand-to-torso separation and readable
negative space. The guard/crouch/run poses also show convincing asymmetry and
support changes. The neutral `front_idle`, by contrast, is highly symmetrical and
the large wings dominate its outer contour; without subtle shifts or alternate
holds it will look emblematic rather than alive over long narration.

**Implication:** a new art campaign is not the first dependency. The graph is
currently leaving its most relevant dialogue, thought, sincerity, and emotion
silhouettes on the shelf.

**Recommendation:** promote only a curated speech-safe subset, then validate it
at final ASCILINE resolution with silhouette masks. Do not expose all diagnostic
poses as random gestures.

### F6. High: repeated intent always produces the same visible phrase

Each effective action resolves to the first matching node
(`wizard_avatar/pose_selection.py:161-173`), and each action-bearing node points to
one clip. There is no gesture-family selection, recent-history penalty, cooldown,
seeded variation, or alternative recovery path in production Python. The only
seed-like variation found in the avatar package is blink timing.

The semantic map already distinguishes amplitude, tempo, hold, flourish
permission, priority, and persona style. The controller persists cue, gesture,
and amplitude but uses tempo only to derive a one-shot timer; `hold`,
`allow_flourish`, and amplitude do not select pose variants
(`wizard_avatar/controller.py:262-310`; `wizard_avatar/semantic_animation.py:163-196`).

**Implication:** repeated explanation, point, thought, or reaction beats have the
same preparation, same silhouette, same duration shape, and same recovery. In a
long audiobook, viewers will detect the loop quickly.

**Recommendation:** use deterministic weighted families with a short reselect
history. The same seed plus performance timeline must reproduce the same result.
Vary pose choice, side, hold length, preparation length, and recovery route within
bounded ranges; never vary the meaning-bearing stroke away from its audio beat.

### F7. Medium: action duration is caller-driven instead of clip-driven

The public `action` command defaults to 1600 ms (`wizard_avatar/controller.py:199-202`),
while current action clips last 0.375-0.875 seconds at 24 fps. Semantic gestures
usually receive about 900 ms adjusted by tempo (`wizard_avatar/controller.py:303-305`).
The graph evaluation clamps a non-looping clip to its final sample
(`wizard_avatar/animation_graph.py:232-239`), but it does not auto-transition at
clip completion or `action_recoverable`.

**Implication:** default commands spend substantial time holding a final pose
(often `front_idle`), while arbitrarily short durations can exit before the
authored recovery. Timing is not attached to the content's phrase or the clip's
performance landmarks.

**Recommendation:** let clip markers determine the earliest safe exit and clip
completion determine default exit. Treat requested duration as a scheduling
constraint: stretch or shorten optional preparation/holds, never truncate the
stroke or uninterruptible recovery.

### F8. Medium: performance coverage is front-heavy

The graph labels south action coverage as capability tier A, while north/profile
coverage is reduced and most actions support only south. Side and diagonal idle
fallbacks are coherent but are not action-equivalent. `speaking` on east/west is
specifically expected to remain a profile idle pose.

**Implication:** turning away or moving during narration can cancel visible acting
or snap back to a front action. This undermines stage continuity.

**Recommendation:** define an audiobook stage rule before broad directional art:
major speech gestures occur in a front or three-quarter presentation zone;
locomotion and turns complete before a major stroke; profile/back views receive
small head, shoulder, staff, and weight shifts rather than unsupported front-pose
substitution.

## Current action-to-pose mapping

The public controller action IDs are defined in `wizard_avatar/models.py:31-50`.
This table distinguishes real production reachability from catalog tags.

| Public action ID | Current node / clip | Actual clip pose IDs | Performance note |
|---|---|---|---|
| `idle` | facing idle node | `front_idle`, `back_idle`, `profile_left`, or `profile_right` | One static sample per facing; declared breathing/settle curves are inactive. |
| `walking` | `ground_walk` / `walk_front` or `back_walk` / `walk_back` | Front: `walk_front_left -> front_idle -> walk_front_right -> walk_front_right_lift`; back: `back_left -> back_idle -> back_right -> back_idle` | Distance-driven contacts are a strong base; no acted start/stop. |
| `dash` | `ground_run` / `run_charge_front` | `front_run_charge_right_plant -> run_front_airborne_reach -> run_front_airborne_drive` | Has plant, release, airborne, commit, and recoverable markers; no automatic `run_recovery`. |
| `speaking` | `explain` / `explain_front` only when no `speech_id` | `front_idle -> explaining -> front_idle` | Suppressed during actual speech. |
| `explaining` | `explain` / `explain_front` | `front_idle -> explaining -> front_idle` | Single fixed gesture, no amplitude variant. |
| `thinking` | no action node | facing idle | `front_thinking_hand_chin_wings` exists but is catalog-only. |
| `pointing` | `point` / `point_front` | `front_idle -> front_point_direct_staff_held -> front_idle` | Readable silhouette; one direction and one intensity. |
| `magic_cast` | `cast` / `cast_front` grounded; `air_staff` / `air_staff_forward` airborne | Ground: `front_idle -> front_staff_guard_windup -> front_magic_staff_thrust -> magic_cast -> front_staff_guard_low -> front_idle`; air: `fly_front_hover_neutral -> fly_southeast_staff_forward -> fly_southeast_forward_glide` | Good anticipation/stroke/recovery structure; too large for routine narration. |
| `reaction` | `hit_reaction` / `hit_fall_recover_front` grounded; `air_reaction_node` / `air_reaction` airborne | Ground: `front_crouch_reaction_staff_planted -> front_airborne_fall_back_staff -> front_crouch_landing_staff_plant -> front_kneel_staff_brace -> front_idle`; air: `fly_front_knee_up -> front_reaction_jump_fist_staff -> fly_front_hover_neutral` | Ground reaction is marked uninterruptible but runtime does not enforce that policy. |
| `hit` | `hit_reaction` / `hit_fall_recover_front` | Same as grounded `reaction` | Combat-scale full-body event. |
| `guard` | `guard` / `guard_front` | `front_staff_guard_windup -> front_crouch_guard -> front_staff_guard_low -> front_idle` | Clear weight drop and staff line; no hold-state execution. |
| `block` | `block` / `block_front` | `front_staff_guard_windup -> front_staff_block_horizontal -> front_staff_guard_low -> front_idle` | Available from idle/walk, but contact/interrupt gates are not enforced. |
| `flourish` | `flourish` / `flourish_front` | `front_staff_guard_low -> front_staff_spin_flourish -> front_staff_guard_low -> front_idle` | Same clip as `staff_spin`; should remain rare in audiobook mode. |
| `staff_spin` | `flourish` / `flourish_front` | Same as `flourish` | Alias, not a variation. |
| `victory_cast` | `victory_cast` / `victory_cast_front` | `front_staff_guard_windup -> front_victory_cast -> magic_cast -> front_idle` | Strong silhouette and effect beat; special-event only. |
| `shush` | `shush` / `shush_front` | `front_idle -> front_shush_secret_staff_held -> front_idle` | Explicit `shush_hold_start/end` markers exist; runtime does not schedule the hold. |
| `celebrate` | `celebrate` / `celebrate_front` grounded; `air_celebrate` / `celebrate_air` airborne | Ground: `front_celebrate_wings_staff_up -> front_celebrate_jump_staff_up -> front_reaction_jump_fist_staff -> front_celebrate_wings_staff_up -> front_idle`; air: `fly_front_hover_neutral -> fly_southeast_cheer -> fly_front_hover_neutral` | Full-body and readable, but high-amplitude and repetitive if reused. |
| `staff_forward` | `air_staff` / `air_staff_forward` only when airborne | `fly_front_hover_neutral -> fly_southeast_staff_forward -> fly_southeast_forward_glide` | Falls back when grounded. |

There is no public `turn` action. The graph's `turn` node is not reachable through
the current mobility calculation.

## Recommended audiobook performance vocabulary

Use these as named families, not direct random pose calls.

| Performance family | Existing pose IDs | Intended use | Phase proposal |
|---|---|---|---|
| `neutral_attentive` | `front_idle_wings`, fallback `front_idle` | Default listening/narration base | Moving hold with tiny breath, weight shift, blink, and staff/wing settle. |
| `explain_light` | `front_explaining_open_hand_wings`, fallback `explaining` | Ordinary explanatory phrase | Neutral -> preparation -> open-hand stroke on stressed word -> short hold -> neutral or next gesture. |
| `explain_broad` | `front_explaining_both_hands_wings` | Rare two-part or expansive idea | Longer preparation, bilateral stroke, brief poststroke hold, asymmetric recovery. |
| `point_reference` | `front_point_side_wings`, `front_point_direct_wings`, fallback `front_point_direct_staff_held` | Deictic reference, contrast, location | Choose side from discourse space; direct point only for strong emphasis. |
| `greeting` | `front_greeting_wave_wings` | Opening, return, friendly acknowledgment | Lift/prep -> one or two wave strokes -> settle; cooldown measured in paragraphs. |
| `think` | `front_thinking_hand_chin_wings`, fallback expression `thinking` on neutral | Reflection, uncertainty, recall | Gaze/torso lead -> hand preparation -> chin hold -> recovery after thought resolves. |
| `sincere` | `front_sincere_hand_heart_wings` | Intimacy, reassurance, gratitude | Small inward prep -> hand-to-heart stroke -> sustained hold -> slow recovery. |
| `quiet` | `front_shush_secret_staff_held`, `front_shush_wings` | Secret/whisper, not generic silence | Preparation before vocal reduction -> hold through secret -> release after phrase. |
| `emotion_state` | `feeling_joy_full`, `feeling_sadness_full`, `feeling_anger_full`, `feeling_fear_full`, `feeling_shame_full`, `feeling_disgust_full`, `feeling_surprise_full`, `feeling_pride_full`, `feeling_guilt_full`, `feeling_love_full`; corresponding `_close` IDs | Sustained emotional state or chapter beat | Enter at a thought boundary, hold across clauses, recover on emotional change; never cycle per word. |
| `accent_magic` | `front_magic_staff_raise_wings`, `front_magic_staff_spark_wings`, existing `cast_front` poses | Literal magic or rare signature accent | Full anticipation/stroke/effect/recovery; long cooldown. |

Catalog `actions` tags on these poses are metadata, not current public action
reachability. Promotion requires graph clips and explicit scheduler policy.

## Implementation recommendations

### P0. Add a performance scheduler with explicit phase state

Introduce a deterministic audiobook performance state above node selection:

```text
REST -> PREPARATION -> PRESTROKE_HOLD -> STROKE
     -> POSTSTROKE_HOLD -> RECOVERY -> REST
```

Required state: family, selected variant, start tick, phase, phase deadline,
stroke/audio anchor tick, planted anchor, amplitude band, pending successor,
interrupt request, seed, and recent-family/variant history.

Map current markers as follows:

- preparation ends at `action_commit` or speech-family entry marker;
- stroke peak aligns to `action_effect`, `speech_open`, or a new explicit
  `gesture_stroke` marker;
- poststroke hold uses `shush_hold_start/end` or authored hold bounds;
- recovery can begin after the stroke and may exit only at
  `action_recoverable`;
- contact changes occur only at contact/release markers.

### P0. Make active speech and body gesture composable

Do not route speech-safe acting through the generic combat action channel. Add a
restricted audiobook lane that can schedule `explain_light`, `point_reference`,
`think`, `sincere`, `quiet`, and `emotion_state` while `speech_id` is active.
Keep root locomotion authoritative and reject broad body gestures while walking,
turning, starting, stopping, airborne, or recovering from an uninterruptible clip.

### P0. Execute contact-aware starts, stops, and turns

1. Detect future motion intent, not only current speed.
2. Choose start side from current planted foot and intended heading.
3. Enter cyclic walk only after the first release/contact marker.
4. On stop intent, finish or distance-match to the nearest legal contact, brake
   the root, settle hips/shoulders/staff, then enter idle.
5. For turns, choose signed shortest heading delta and support foot; keep facing
   stable until a pivot marker instead of changing the enum every tick.
6. Author missing start/stop/pivot art after the runtime can play it. Existing
   `walk_front_left/right`, `back_left/right`, and profile/idle poses can prove
   the state machine but should not be mistaken for complete turn animation.

### P1. Activate weight and secondary action

- Pass `planted_anchor` to presentation and solve root correction at each
  coherent-pose handoff.
- Apply existing `walk_bob`, `walk_staff_lag`, `walk_robe_lag`, `idle_breathe`,
  `idle_wing_settle`, `turn_staff_lag`, and action curves as bounded integer-cell
  or subcell presentation offsets.
- Make hip/shoulder counter-shift and staff/wing follow-through lag the primary
  torso action; never let all channels reverse on the same frame.
- Keep the silhouette stable enough for ASCILINE readability: secondary motion
  must not create duplicate limbs, detach the staff, or close hand/torso negative
  space at the stroke.

### P1. Add deterministic anti-repetition policy

- Maintain at least the last 3 gesture families and last 2 variants.
- Block immediate variant repetition unless narrative continuity explicitly asks
  for a held or repeated gesture.
- Use seeded weighted selection conditioned on amplitude, emotional state,
  discourse role, facing, locomotion, current pose, and time since last use.
- Add paragraph-scale cooldowns for `greeting`, `quiet`, `accent_magic`,
  `celebrate`, `flourish`, and broad reactions.
- Allow no-gesture as the highest-probability result. Restraint is variation.
- Record selection reason, seed, candidate costs, and cooldown exclusions for
  replay and review.

### P1. Establish silhouette and weight gates

At final output resolution, test every stroke and hold pose for:

- hand/staff separation from torso where meaning depends on them;
- one readable line of action;
- visible support side and plausible center of mass;
- non-symmetric shoulder/hip relationship unless symmetry is intentional;
- no root or planted-anchor jump across adjacent samples;
- stable hat, face, wing, and staff identity;
- a silhouette-only reviewer being able to distinguish neutral, explain, point,
  think, sincere, quiet, guard, and celebrate.

### P2. Add only the missing art the executed system proves it needs

Priority new pose/clip gaps are left/right starts, left/right stops, 45- and
90-degree pivots, in-place turns, and small profile/back speaking holds. New
gesticulation art should wait until the promoted catalog poses have been tested
in full audiobook sequences.

## Risks

| Risk | Severity | Failure mode | Mitigation |
|---|---|---|---|
| Promoting all 50 unused poses at once | High | Noisy, incoherent performance and combinatorial transitions | Curate six to eight speech-safe families first. |
| Random variation | High | Non-reproducible timing, gesture/audio mismatch, unstable tests | Seeded choice plus replay log and fixed cooldown rules. |
| Generic action lane during speech | High | Combat/magic pose interrupts narration or locomotion | Dedicated restricted audiobook lane and channel masks. |
| Per-cell crossfade | High | False limbs, broken face, staff fragments, muddy silhouette | Atomic snapshots with authored in-between poses and anchor-locked handoffs. |
| Marker metadata remains advisory | Critical | Stroke truncation, stuck holds, foot sliding, interrupted recovery | Runtime phase/interrupt enforcement and marker-crossing tests. |
| Over-gesturing every emphasized word | High | Mechanical, distracting, semantically literal performance | Thought-level scheduling, no-gesture default, paragraph cooldowns. |
| Front-only action vocabulary | Medium | Snap-to-front or inert profile/back narration | Presentation-zone staging plus small directional hold set. |
| Secondary motion too broad for ASCII cells | Medium | Flicker and silhouette churn | Subtle capped curves, cell-stability tests, final-resolution review. |

## Acceptance evidence for a future implementation

1. A 10-minute representative audiobook scene with narration, dialogue, quiet
   reflection, a turn, a short walk, a stop, and two emotional changes.
2. Frame/state trace proving every gesture phase and audio stroke anchor.
3. No immediate gesture-variant repeats; identical seed reproduces identical
   choices and frame hashes.
4. Start/stop/turn traces proving legal contact changes and planted-anchor drift
   within the agreed cell threshold.
5. Active speech visibly reaches the speech-safe body lane without changing
   locomotion ownership.
6. All action exits occur at legal markers; uninterruptible clips cannot be cut.
7. Silhouette contact sheets at final ASCILINE resolution, reviewed without
   color and without facial detail.
8. Long-hold review proving breath/weight/staff/wing motion remains subtle and
   does not become a short obvious loop.
9. Coverage report listing selected family, variant, amplitude band, cooldown,
   and rejection reason for every performance cue.
10. Regression tests preserving current action IDs and existing graph fallback
    behavior outside audiobook mode.

## Bottom line

The active graph already contains the beginnings of professional motion grammar,
and the catalog already contains the strongest dialogue silhouettes. The next
step is to make those facts executable: speech-safe whole-body phrasing, explicit
preparation/stroke/hold/recovery, contact-aware starts/stops/turns, and restrained
deterministic variation. Until then, adding more poses will increase inventory
without making Wizard Joe act.
