# Audiobook Narrative Direction and Beat Research

**Role:** Audiobook Director and Narrative Analyst

**Project:** Wizard Joe Audiobook Performance Engine

**Audit date:** 2026-07-13

**Repository:** `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar-python`

**Scope:** Research, narrative direction, and implementation implications only. No production code was changed.

## Executive decision

Wizard Joe should not animate the words of an audiobook. He should perform the
changing relationship among narrator, listener, character, and story.

The repository already supplies a deterministic visual instrument: 89 authored
poses, 10 facial expressions, 7 mouth shapes, bounded semantic intent, a fixed
simulation clock, and locomotion-preserving command ownership. It does not yet
represent the information an audiobook director actually uses: whole-book and
chapter arcs, point of view, narrator distance, dialogue versus narrative mode,
subtext, suspense release, comic setup and payoff, intimacy, exposition load,
reflection, or meaningful silence. Its current semantic path selects one
winning cue, converts that cue to a short action, and suppresses body-action
selection during active speech. Mouth motion remains a fixed fallback cycle.

The recommended addition is a **content-free hierarchical narrative beat
schedule** above the existing animation layer:

1. Book and narrator profiles establish the durable performance stance.
2. Chapter and scene envelopes describe trajectory, not momentary emotion.
3. Passage mode distinguishes narration, dialogue, interior thought,
   exposition, reflection, and quoted material.
4. Sparse beats identify genuine changes of thought, stakes, relationship, or
   information.
5. Explicit silence events protect breath, suspense, reflection, scene breaks,
   and chapter landings.
6. A restraint policy maps only selected beats to speech-safe visual behavior;
   most narration remains in a characterful neutral.

This is a direction system, not an emotion detector. It must preserve authorial
meaning, avoid spoilers and anticipatory reactions, keep narrator and character
stances distinct, and treat stillness as an authored performance choice.

## Research method and confidence

This report combines:

- direct inspection of the Python controller, signal contract, state model,
  animation graph, pose selector, face and mouth layers, and existing research;
- current requirements from the US Library of Congress National Library
  Service (NLS), including its February 2025 narration revision;
- professional guidance from SAG-AFTRA, Audible/ACX, Penguin Random House
  Audio, the Audio Publishers Association, and working audiobook coaches;
- primary research on co-speech gesture timing, semantic congruence, and
  evaluation of embodied-agent motion.

Professional sources agree strongly on the governing principles: convey the
sense and emotional level of the text, preserve point of view, make dialogue
clear without overplaying it, sustain long-form continuity, and use pacing and
silence deliberately. Genre-specific visual mappings in this report are
**design inferences** from those principles, not claimed industry standards.
They require directed listener testing.

## Repository audit

### What exists

- The pose library contains 89 geometries. The animation graph classifies all
  89, but only 39 are clip samples; 50 are `diagnostic_only`. The companion
  [supervising animation audit](01-supervising-animation-director.md) owns the
  detailed reachability and pose-direction analysis.
- `AnimationIntent` already models `expression`, `gesture`, `amplitude`,
  `tempo`, `mouth_activity`, `hold`, flourish permission, priority, persona
  style, and governance clamps
  (`wizard_avatar/semantic_animation.py:18-64`). This is a strong bounded
  presentation contract, but not a narrative contract.
- Semantic arbitration chooses one substantive winner and composes only caps,
  clamps, and style (`wizard_avatar/semantic_animation.py:376-418`). Suspense,
  speaker stance, chapter trajectory, and silence therefore cannot coexist as
  independent layers.
- Prism ingress is deliberately content-free and fail-closed. Its allowlist is
  oriented to assistant lifecycle, governance, continuity, and health rather
  than literary performance (`wizard_avatar/prism_signals.py:19-105`). It also
  rejects prompt, message, content, rationale, movement, position, and other
  authority-bearing fields (`wizard_avatar/prism_signals.py:161-191`). This
  privacy and ownership boundary should be preserved.
- The controller persists semantic cue, gesture, and amplitude, maps broad
  semantic expressions to the 10 supported face expressions, and converts a
  gesture to a timed action only when no speech session is active
  (`wizard_avatar/controller.py:262-310`). `hold` and flourish permission do not
  become runtime scheduling policy.
- During active speech, production pose selection deliberately suppresses the
  speaking action (`wizard_avatar/pose_selection.py:141-150`). This protects
  the body from uncontrolled pose replacement, but it also prevents a directed
  speech-safe performance lane.
- Speech is started with text plus an estimated duration; the controller does
  not receive word, phoneme, stress, phrase, or silence timing
  (`wizard_avatar/controller.py:328-339`). The renderer cycles generic mouth
  shapes at 10 Hz while speech is active (`wizard_avatar/layers.py:242-251`;
  `wizard_avatar/mouth.py:24-26`).
- `WizardState` records the current action, face, mouth, speech timer, pose,
  locomotion, and one semantic cue. It has no book, chapter, scene, passage,
  speaker, narrator stance, tension trajectory, beat history, silence state, or
  continuity checkpoint (`wizard_avatar/models.py:123-169`).
- The current expression and action vocabularies are useful but broad: 10 face
  expressions, 18 actions, and 7 mouth shapes
  (`wizard_avatar/models.py:18-60`). They should be render targets selected by
  direction policy, never substitutes for literary analysis.

### Consequence

The current engine can respond to **what operational state it is in**, but not
**what the passage is doing**. Adding more poses or more emotion labels alone
would amplify this mismatch. Narrative meaning must be represented before
visual selection, and the runtime must be able to sustain multiple timescales
without collapsing them to one cue.

## Professional performance standard

### Authorial sense before display

The NLS requires conversational delivery that conveys the sense and appropriate
emotional level of the text. It specifically calls for emphasis, inflection,
phrasing, stress, and timing to distinguish narrative, dialogue, and characters
without drawing undue attention to the delivery. It rejects overplayed or
distracting characterization and rejects interpretation that changes meaning.
[NLS Narration Specification, sections 3.1.1-3.1.5](https://www.loc.gov/nls/who-we-are/guidelines-and-specifications/contract-specifications/narration/)

**Direction implication:** visual performance is subordinate to meaning. A
visually legible gesture is a defect if it editorializes, stereotypes, reveals
information early, or attracts attention away from the prose.

### Point of view and narrator stance

SAG-AFTRA's professional workshop with director Paul Alan Ruben frames fiction
performance around playing point of view, emotional stakes, the third-person
narrator, realistic dialogue, the immediate moment, and punctuation. For
nonfiction, the narrator acts as the author's surrogate and may occupy an
expert, teacher, or persuader role.
[SAG-AFTRA, "Audiobook Narration Workshop: It's Not About the Voice"](https://www.sagaftra.org/audiobook-narration-workshop-it%E2%80%99s-not-about-voice)

**Direction implication:** `warm`, `playful`, or `reflective` is too shallow as
the only stance model. The system must separately represent point of view,
narrative distance, narrator attitude, role toward the listener, and the
current character's local attitude.

### Long-form arc and continuity

Penguin Random House Audio asks narration candidates to balance narrative and
dialogue and demonstrate an emotional or situational arc in a short sample.
[PRH Audio Narrator Mentorship](https://penguinrandomhouseaudio.com/narrator-mentorship/)
Professional audiobook preparation taught by Patrick Fraley and Scott Brick
includes story, genre, performance style, shifts in tone, critical story-arc
points, themes, and subplot.
[Fraley and Brick, "Prepping the Whole Audiobook"](https://patfraley.com/pf/product/prep/)
An Audible Approved producer restores continuity between sessions by listening
back for emotional tone, pacing, rhythm, and sensibility, not merely voice
pitch.
[ACX, "Andi Arndt's Audiobook Agenda"](https://www.acx.com/mp/blog/andi-arndts-audiobook-agenda)

**Direction implication:** chapter direction cannot be a fresh classification
of each paragraph. It needs inherited book, narrator, character, and unresolved
story state plus explicit re-entry checkpoints.

### Dialogue and narration

NLS requires timing and inflection to distinguish narration from dialogue and
characters while keeping character voices as fluent and listenable as the
normal narrative voice. ACX likewise advises preparation of the whole book,
scene subtext, and character attitude; it warns that pitch alone is not enough
for differentiation.
[NLS Narration Specification](https://www.loc.gov/nls/who-we-are/guidelines-and-specifications/contract-specifications/narration/)
[ACX, "How to Act Like an Audiobook Narrator"](https://www.acx.com/mp/blog/how-to-act-like-an-audiobook-narrator)
ACX's publisher guidance explicitly says understated character work is safer
than broad, cartoon-like changes.
[ACX, "5 Tips for Choosing a Narrator"](https://www.acx.com/mp/blog/5-tips-for-choosing-a-narrator)

**Direction implication:** dialogue mode may change attitude, rhythm, gaze, or
small expression, but it should not assign a new full-body caricature to every
speaker. Narrator and character channels must remain separable.

### Suspense

The 2025 ACX Author Summit emphasizes that generic direction such as "make it
scary" is insufficient; a production should specify whether tension builds
slowly, what is withheld, and where the reveal occurs. It also recommends that
dialogue, pacing, and atmosphere be considered together.
[ACX Author Summit, 2025](https://www.acx.com/mp/blog/how-to-write-and-produce-engaging-audiobooks-insights-from-the-acx-author)

**Design inference:** suspense should generally reduce visual novelty as
uncertainty rises. Stillness, a contained focus, and delayed release preserve
listener projection. A large reaction belongs at or just after the textual and
audio reveal, never in advance of it.

### Comedy

Penguin Random House Audio's 2024 interview with comedian and narrator Siena
East emphasizes reading and annotating the whole book to understand intent
across prose and dialogue, deliberately slowing the read, and treating humor as
part of character perspective rather than as detachable jokes.
[PRH Audio, "Putting the Com in the Rom"](https://penguinrandomhouseaudio.com/posts/putting-the-com-in-the-rom-a-qa-with-narrator-siena-east/)

**Design inference:** do not telegraph a punchline with a pre-emptive grin,
surprise pose, or flourish. Protect setup neutrality, allow the line and its
timing to land, and place any visual acknowledgment in a bounded tag or
reaction window after the semantic payoff.

### Intimacy

Audiobook performance is intrinsically close: Audible Approved producer Andi
Arndt describes the booth relationship as narrator, listener, and author's
words, and ties continuity to emotional tone, pacing, rhythm, and sensibility.
[ACX, "Andi Arndt's Audiobook Agenda"](https://www.acx.com/mp/blog/andi-arndts-audiobook-agenda)

**Design inference:** intimacy is not high emotional amplitude. It is reduced
distance, attention, vulnerability, and trust. Prefer smaller movement, longer
holds, direct but soft orientation, and rare sincere gestures. Decorative love
symbols, shushing, or repeated hand-to-heart motion can cheapen or misread the
passage.

### Exposition and reflection

SAG-AFTRA's nonfiction model distinguishes expert, teacher, and persuader roles.
NLS requires pace and emotional level to follow the needs, energy, mood, sense,
and style of the text rather than applying one generic cadence.
[SAG-AFTRA workshop](https://www.sagaftra.org/audiobook-narration-workshop-it%E2%80%99s-not-about-voice)
[NLS Narration Specification](https://www.loc.gov/nls/who-we-are/guidelines-and-specifications/contract-specifications/narration/)

**Design inference:** exposition should visualize discourse structure, not
every noun. Reflection should protect inward processing, uncertainty, and
reassessment through stillness, slight gaze or head changes, and a measured
return rather than an automatic `thinking` loop.

### Silence and spacing

ACX treats room tone and spacing as part of comprehension and navigation. Its
current file-boundary requirement allows no more than five seconds of room tone
at the head and tail, while professional editing may also use clean room tone
to improve internal pacing and clarity.
[ACX, "Editing and Spacing"](https://www.acx.com/mp/blog/editing-and-spacing-with-alex-the-audio-scientist)
[ACX, "How to Succeed at Audiobook Production: Part 2"](https://www.acx.com/mp/blog/how-to-succeed-at-audiobook-production-part-2)

**Direction implication:** technical room tone, dramatic silence, breath,
sentence spacing, scene breaks, and chapter boundaries are different events.
The visual system must preserve the actual audio duration and receive a
semantic silence class; it must not infer all pauses from punctuation or fill
every gap with animation.

### Meaningful and restrained visual performance

Gesture and speech are processed as an integrated semantic signal; incongruent
gesture-word pairs measurably interfere with comprehension even when the
gesture is irrelevant to the participant's task.
[Kelly et al., 2009, primary study](https://pubmed.ncbi.nlm.nih.gov/19413483/)
Gesture strokes normally align just before or with stressed speech, and
non-referential gestures can mark discourse updates.
[Sekine et al., 2021, primary narrative-gesture study](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.661339/full)

Large-scale GENEA evaluations show why natural-looking motion is not enough:
synthetic systems can approach human-likeness while remaining far behind human
motion in appropriateness for the specific speech.
[GENEA Challenge 2023](https://arxiv.org/abs/2308.12646)
A real-time embodied-agent study found that a model producing too many gestures
without appropriate pauses could distract from the presented content; eye
tracking also showed that gesturing drew attention toward the agent's body.
[He, Pereira, and Kucherenko, IVA 2022](https://media.contentapi.ea.com/content/dam/ea/seed/presentations/seed-evaluating-data-driven-co-speech-gestures-paper.pdf)

**Direction implication:** evaluate visual naturalness and speech
appropriateness separately. For an audiobook companion, attention captured by
the avatar is not automatically success.

## Narrative direction model

### 1. Book profile

The book profile is authored or reviewed once and inherited by every chapter.
It should contain structural direction, not manuscript text:

| Feature | Purpose |
|---|---|
| `genre_family` and optional subgenre | Sets expectations without hard-coding stereotypes. |
| `narration_form` | Fiction, memoir, essay, instruction, argument, poetry, or mixed. |
| `pov_system` | First, second, third limited, third omniscient, objective, or alternating. |
| `narrator_role` | Storyteller, witness, confidant, expert, teacher, advocate, skeptic, or other authored role. |
| `baseline_distance` | Close, middle, or far relationship to the focal consciousness and listener. |
| `baseline_energy` | Durable center of gravity, not average loudness. |
| `character_policy` | Degree and dimensions of differentiation; never raw impersonation instructions. |
| `performance_ceiling` | Maximum ordinary visual amplitude and reserved peak policy. |
| `sensitivity_notes_ref` | Opaque reference to reviewed cultural/pronunciation guidance outside visual state. |

The profile is a continuity constraint. It should bias interpretation but never
override local evidence in the text and audio.

### 2. Chapter envelope

Chapters need trajectory rather than a single mood label. Use a sequence of
authored or inferred phases, allowing chapters to omit or repeat phases:

- **Entry:** reorientation, carryover, new point of view, or immediate action.
- **Development:** relationship, argument, investigation, or exposition grows.
- **Turn:** new information changes objective, understanding, or stakes.
- **Pressure or release:** tension rises, comedy opens space, intimacy deepens,
  or information resolves.
- **Landing:** closure, reflection, propulsion, or cliffhanger.

Recommended chapter fields:

| Feature | Meaning |
|---|---|
| `chapter_function` | Opening, bridge, escalation, reversal, climax, aftermath, interlude, or mixed. |
| `entry_state` / `exit_state` | Content-free continuity summaries carried across boundaries. |
| `phase_spans` | Ordered entry/development/turn/landing segments with confidence. |
| `tension_curve` | Sparse control points, not per-sentence jitter. |
| `intimacy_curve` | Relational distance over time. |
| `information_curve` | Density and novelty of exposition or revelation. |
| `comic_structure` | Setup, escalation, payoff, tag, callback spans when applicable. |
| `unresolved_threads` | Opaque IDs and state only; no plot text. |
| `pov_owner` | Opaque narrator or focal-character identity. |
| `continuity_checkpoint` | Narrator stance, energy, active emotion, last gesture family, and recovery state. |

No universal rise-and-climax curve should be forced onto every chapter. A
meditative essay, comic interlude, action chapter, and grief aftermath require
different envelopes.

### 3. Scene and passage mode

Every timed span should have one primary discourse mode and optional modifiers:

| Mode | Direction question |
|---|---|
| `narration` | Who is telling, from what distance, and with what attitude? |
| `dialogue` | Who wants what from whom in this turn? |
| `interior_thought` | Is this immediate thought, memory, fantasy, or self-correction? |
| `scene_action` | What changes physically or causally? |
| `exposition` | Is the narrator teaching, defining, comparing, sequencing, or arguing? |
| `reflection` | What is being reconsidered, felt, or integrated? |
| `quotation` | Is the quoted voice being lightly distinguished or formally presented? |
| `paratext` | Heading, note, epigraph, list, citation, or navigation. |

Useful modifiers include `memory`, `dream`, `irony`, `unreliable`, `aside`,
`confession`, `ritual`, `list`, and `scene_transition`. Modifiers must be
evidence-backed and may affect direction without creating a new pose family.

### 4. Narrator and character stance

Represent stance as independent dimensions rather than one emotion:

- `narrative_distance`: close, middle, far;
- `listener_relation`: confidant, companion, audience, student, jury, witness;
- `certainty`: uncertain to certain;
- `authority`: observing to expert;
- `warmth`: cool to warm;
- `urgency`: settled to urgent;
- `vulnerability`: protected to exposed;
- `irony`: sincere to strongly ironic;
- `agency`: passive witness to active advocate.

Keep three layers distinct:

1. **Narrator stance** persists across passages.
2. **Focal consciousness** shapes narrative distance and perception.
3. **Character attitude** applies only within a dialogue or interior turn.

This prevents a frightened character from making the narrator and avatar
globally frightened, and it prevents narrator irony from becoming a character's
facial sneer.

## Proposed `NarrativeBeatV1` features

The following is a proposed analysis-to-direction contract, not production code.
It is intentionally content-free and uses bounded enums, numbers, and opaque
IDs so it can coexist with the repository's privacy and authority model.

### Identity and timing

- `schema_version`
- `book_id`, `chapter_id`, `scene_id`, `passage_id`, `beat_id` as opaque IDs
- `start_ms`, `apex_ms`, `end_ms`
- `audio_alignment_source`: authored, word-aligned, energy-derived, or fallback
- `source_sequence`, `revision`, and `supersedes`
- `confidence` and `review_status`

`apex_ms` is the meaning or stress point. A visual preparation may begin before
it, but the readable gesture stroke should not precede the listener's access to
the meaning unless the text explicitly supplies anticipation.

### Narrative hierarchy

- `chapter_phase`: entry, development, turn, pressure, release, landing
- `scene_function`: setup, pursuit, confrontation, discovery, aftermath,
  transition, exposition, reflection, comic sequence, intimate exchange
- `beat_function`: orient, propose, question, contrast, escalate, reveal,
  reverse, decide, confess, connect, withdraw, punchline, tag, callback,
  summarize, conclude, interrupt
- `boundary_before` and `boundary_after`: clause, sentence, paragraph, scene,
  chapter
- `carryover`: none, tension, question, emotion, relationship, argument

### Voice and discourse

- `performer_mode`: narration, dialogue, interior_thought, scene_action,
  exposition, reflection, quotation, paratext
- `pov_mode` and opaque `pov_owner`
- opaque `speaker_id` and `addressee_id` when applicable
- `narrator_role`: storyteller, witness, confidant, expert, teacher, persuader
- `distance`, `certainty`, `authority`, `warmth`, `urgency`, `vulnerability`,
  and `irony`, all bounded
- `turn_relation`: initiate, answer, evade, interrupt, concede, challenge,
  reassure, disclose, or close

### Story dynamics

- `tension_level` and `tension_slope`
- `information_novelty` and `information_density`
- `stakes_change`: down, stable, up, transformed
- `expectation_state`: open, forming, delayed, fulfilled, violated
- `intimacy_level` and `intimacy_change`
- `comic_phase`: none, setup, escalation, payoff, tag, callback, deadpan_hold
- `reflection_depth`: none, recall, reconsideration, realization, integration
- `emotional_valence`, `emotional_activation`, and `emotional_control`

These features describe dramatic function. They should not be direct pose
selectors. For example, high tension plus high emotional control calls for a
different performance from high tension plus low control.

### Silence

- `silence_kind`: breath, syntactic, turn, interruption, suspense_hold,
  reflective_hold, scene_break, chapter_boundary, technical_room_tone
- `duration_ms`: copied from aligned audio, never invented by the renderer
- `visual_policy`: hold, settle, close_mouth, blink_allowed, gaze_shift,
  recover_to_baseline, freeze_accent
- `carries_state`: tension, intimacy, reflection, expectation, none
- `interruptible`

Silence is an event with meaning and ownership. The renderer must not shorten
it, add speech mouth motion within it, or use it as permission for arbitrary
movement.

### Visual direction, still semantic

- `visual_salience`: none, low, medium, high, peak
- `stillness_target`: active, settled, held, absolute
- `gesture_intent`: none, orient, explain, compare, reference, question,
  reassure, sincere, withhold, release, react
- `expression_family`: neutral, attentive, thoughtful, amused, concerned,
  surprised, resolved, or leave_unchanged
- `gesture_phase`: prepare, stroke, hold, recover
- `gesture_budget_cost`
- `minimum_hold_ms`, `recovery_ms`, and `cooldown_class`
- `speech_safe`, `can_interrupt`, and `return_policy`
- `forbid_flourish`, `forbid_literalization`, and `spoiler_sensitive`

The scheduler, not the analyzer, resolves these intents to the available pose,
face, gaze, and mouth vocabulary.

### Minimal example

```json
{
  "schema_version": 1,
  "beat_id": "b-0042",
  "chapter_phase": "turn",
  "performer_mode": "narration",
  "beat_function": "reveal",
  "start_ms": 81240,
  "apex_ms": 82610,
  "end_ms": 83900,
  "tension_level": 0.82,
  "tension_slope": "release",
  "expectation_state": "fulfilled",
  "visual_salience": "medium",
  "stillness_target": "held",
  "gesture_intent": "react",
  "gesture_phase": "stroke",
  "spoiler_sensitive": true,
  "speech_safe": true,
  "confidence": 0.91
}
```

The example contains no manuscript text, character name, rationale, raw pose
ID, world movement, or execution authority.

## Mapping meaning to restrained visual performance

### Governing rules

1. **Change follows thought.** Do not change the main pose because a sentence
   contains an emotion word.
2. **Audio leads meaning.** The avatar may prepare with the spoken thought, but
   it may not reveal the payoff first.
3. **One readable idea at a time.** A body accent, strong face, gaze move, and
   flourish should not all compete for the same beat.
4. **Narrator stance outranks character mimicry.** Character differentiation is
   subtle and local.
5. **Stillness carries pressure and intimacy.** Motion is not the default proof
   of life.
6. **Gesture is sparse punctuation.** Most clauses receive mouth, eye, and
   continuity behavior only.
7. **Hold through comprehension.** Recovery begins after the listener has had
   time to receive the line, not immediately after the pose appears.
8. **Do not literalize abstract language.** Metaphor, idiom, negation, and
   hypothetical action require conservative treatment.
9. **Preserve chapter memory.** New sections inherit unresolved tension,
   intimacy, and narrator stance unless the text resets them.
10. **The avatar never editorializes protected identity or culture.** No accent,
    stereotype, or identity inference becomes a visual caricature.

### Performance matrix

| Narrative condition | Primary direction | Allowed visual consequence | Avoid |
|---|---|---|---|
| Ordinary narration | Maintain narrator stance and continuity. | Characterful neutral, speech-aligned mouth, bounded blink/gaze. | Gesture on every stress or sentence. |
| Dialogue turn | Play objective, relationship, and subtext. | Small attitude/face shift; rare speech-safe gesture at a turn. | New full-body persona for every speaker; pitch-to-pose mapping. |
| Suspense build | Narrow attention and preserve uncertainty. | Reduced motion, focused gaze, contained posture, longer holds. | Repeated worried reactions; early reveal gesture. |
| Reveal or reversal | Let the line arrive, then register change. | One timed reaction or posture change at/after `apex_ms`. | Anticipatory surprise; flourish over key words. |
| Comic setup | Protect information and rhythm. | Neutral or lightly engaged baseline. | Smiling at the joke before the listener hears it. |
| Punchline/tag | Let audio timing land first. | Brief amused microreaction or release after payoff when warranted. | Celebration, bounce, or repeated mugging. |
| Intimate/confessional | Reduce distance and performance pressure. | Small sincere posture, soft direct orientation, long settle. | Decorative love effects, repeated hand-to-heart, shush by default. |
| Exposition/teaching | Clarify structure and causal relations. | Open-hand explain, compare, or side reference at section turns. | Pointing at every item; emotional inflation. |
| Reflection | Protect inward processing. | Thoughtful stillness, slight gaze shift, blink, measured recovery. | Looping chin gesture; constant sadness overlay. |
| High action | Preserve causality and narrator legibility. | Rare scene-level punctuation after event evidence. | Literal pose for every verb; combat motion during unrelated prose. |
| Scene break | Reorient without erasing carryover. | Settle, gaze reset, or baseline transition during real spacing. | Greeting each scene; automatic emotional neutralization. |
| Chapter boundary | Land the prior chapter, then establish the next. | Explicit exit hold and next-entry posture using checkpoint state. | Abrupt reset to default; motion in technical room tone. |

### Suspense direction

- Track `tension_level` separately from `activation`. Quiet threat can be high
  tension and low movement.
- Represent `expectation_state`; suspense often lives in delayed fulfillment,
  not fear.
- Use fewer, more consequential changes as tension rises.
- Keep the mouth and face readable but controlled during withheld information.
- Place reaction after evidence. A blink, gaze return, or small posture release
  may be more effective than a large surprise pose.
- Preserve unresolved tension through paragraph, scene, and chapter boundaries.

### Comedy direction

- Annotate setup, escalation, payoff, tag, callback, and deadpan hold.
- Keep setup performance sincere unless the narrator's established stance is
  overtly comic.
- Never use sentiment alone to find jokes; humor may be dry, painful, ironic,
  character-based, or structurally delayed.
- Use post-payoff visual acknowledgment only when it supports narrator stance.
- Protect callbacks from overemphasis; recognition is often the listener's
  pleasure.
- Measure comic success by timing and non-interference, not number of amused
  expressions.

### Intimacy direction

- Model intimacy as relational distance and vulnerability, not positive
  valence.
- Reduce gesture size and frequency as intimacy deepens unless the scene itself
  breaks containment.
- Favor direct attention, stillness, soft expression, and slow recovery.
- Distinguish romantic, familial, confessional, therapeutic, spiritual, and
  threatening closeness through reviewed context; do not map them all to love.
- Never infer consent, attraction, or safety from vocal warmth alone.

### Exposition direction

- Annotate definition, sequence, contrast, cause, example, exception, and
  summary.
- Gesture only at structural transitions or a genuinely difficult relation.
- Use side reference or open-hand explanation instead of direct pointing at the
  listener.
- Lower visual activity as information density rises; the listener needs
  processing capacity.
- In persuasive nonfiction, preserve the difference among teaching,
  advocating, and claiming certainty.

### Reflection direction

- Mark whether reflection is recall, reconsideration, realization, or
  integration.
- Let silence carry unfinished thought when the audio does.
- Delay a new main pose until the thought changes, not at the first reflective
  keyword.
- Use emotional control and certainty to decide whether feeling is outward or
  contained.
- Return to baseline gradually when the reflection changes the narrator's
  stance; do not erase the result at the next sentence.

## Runtime and architecture implications

### Add a dedicated boundary

Do not overload the current Prism lifecycle signal with literary fields. Add a
separate, versioned `NarrativeBeatV1` ingestion path or offline schedule loader
that preserves the same principles:

- strict schema and unknown-field rejection;
- content-free payload after analysis;
- bounded values and canonical opaque IDs;
- sequence, revision, expiry, cancellation, and replay semantics;
- no raw pose IDs, coordinates, locomotion, or execution authority;
- explicit source and review provenance;
- deterministic fallback to neutral when invalid or late.

The manuscript-aware analyzer may require source text, but that processing
belongs before the visual trust boundary. The saved and transmitted beat
schedule should not contain manuscript excerpts, character names, or model
rationales.

### Replace winner-take-all with layered composition

Maintain independent regions:

1. `book_profile`
2. `chapter_envelope`
3. `scene_mode`
4. `narrator_stance`
5. `character_turn`
6. `story_beat`
7. `silence`
8. `speech_mouth`
9. `governance_and_safety`
10. `recovery_and_continuity`

Governance remains able to cap or suppress all expressive output. Narrative
layers compose restrictions and direction; they do not compete for one global
priority winner.

### Introduce a performance scheduler

The scheduler should:

- quantize timing to the existing deterministic simulation clock;
- enforce minimum holds, cooldown, repeat protection, and recovery;
- allow a beat to prepare, strike, hold, and recover;
- preserve a chapter checkpoint and book-level baseline;
- suppress visual accents when several beats collide;
- reserve large poses for reviewed peaks;
- keep body, face, gaze, mouth, and silence ownership independent;
- resolve unavailable or unsafe visual intents to a smaller compatible choice;
- log why an accent was selected or suppressed using enums, not hidden text.

### Make speech timing authoritative

Accept word or phoneme timing when available and speech-activity intervals at a
minimum. `NarrativeBeatV1` provides meaning timing; the speech plan provides
mouth timing. Neither should estimate the other from character count.

Required behavior:

- mouth closed or at expression rest during aligned silence;
- no mouth movement before speech start or after completion;
- phrase and interruption boundaries remain stable under pause/resume;
- visual accent timing follows the authoritative audio clock;
- late or missing alignment degrades to speech activity plus neutral body, not
  the current regular 10 Hz display as the final audiobook behavior.

### Use the existing pose library editorially

The library is larger than the runtime's directed vocabulary. Follow the
companion animation audit's curated speech-safe promotion plan rather than
making every pose autonomous. Narrative features should select semantic
families such as `sincere`, `explain`, or `withhold`; a reviewed renderer policy
chooses a reachable pose, face-only treatment, or no accent.

## Risks and mitigations

| Risk | Failure mode | Mitigation |
|---|---|---|
| Literalization | Every action word triggers an action pose. | Require beat function and discourse mode; default to no body accent. |
| Overperformance | Motion competes with long-form listening. | Gesture budget, stillness target, cooldown, and long-form review. |
| Spoilers | Avatar reacts before the reveal reaches the listener. | `apex_ms`, `spoiler_sensitive`, audio-led timing, and hard no-early-accent gate. |
| Narrator/character leakage | Character emotion becomes global narrator stance. | Separate narrator, focal, and character regions with scoped expiry. |
| Arc amnesia | Each paragraph or chapter resets emotional state. | Entry/exit checkpoints and opaque unresolved-thread carryover. |
| Winner flattening | Suspense, intimacy, dialogue, and silence collapse to one label. | Layered state and deterministic composition rules. |
| Silence erasure | Idle animation fills pauses and weakens meaning. | First-class silence events with explicit visual ownership. |
| Comic telegraphing | Smile or flourish announces a joke early. | Setup neutrality and post-payoff reaction window. |
| Emotional stereotyping | Identity, dialect, or genre produces caricature. | Reviewed cultural guidance; forbid identity-to-pose inference; human QA. |
| False certainty | Analyzer confidently misreads irony, negation, or unreliable narration. | Confidence, review status, conservative fallback, and contradiction tests. |
| Content leakage | Manuscript or rationale crosses the visual boundary. | Content-free schedule, opaque IDs, schema rejection, retention audit. |
| Timing drift | Beat, mouth, and audio clocks diverge. | One authoritative audio timeline, tick quantization, replay parity tests. |
| Unreachable intent | Analyzer selects a meaning with no safe runtime pose. | Capability negotiation and face/stillness/neutral fallbacks. |
| Visual habituation | Repeated gestures lose meaning. | Family history, repeat penalty, chapter-scale usage ledger. |
| Evaluation illusion | Motion looks human but is wrong for the line. | Score human-likeness and speech appropriateness separately, as GENEA does. |

## Recommendations

### P0: define the editorial contract

1. Approve the hierarchy, stance dimensions, discourse modes, beat functions,
   silence classes, and privacy exclusions in this report.
2. Choose which fields are authored, model-assisted, audio-derived, or
   prohibited from automatic inference.
3. Define a manual correction format and source-of-truth precedence.
4. Establish spoiler, culture, intimacy, and identity review gates.

### P1: build a content-free annotation fixture set

Create reviewed fixtures for:

- chapter entry, turn, landing, and cliffhanger;
- narration-to-dialogue and dialogue-to-interior-thought transitions;
- quiet and action suspense with a delayed reveal;
- comic setup, payoff, tag, callback, and deadpan;
- intimate confession without romance assumptions;
- dense exposition with definition, contrast, and example;
- reflective reconsideration and realization;
- breath, interruption, suspense hold, scene break, and chapter silence.

Each fixture needs aligned audio, text available only to the analysis/evaluation
side, a content-free expected schedule, and director notes.

### P2: implement schedule and replay before rich motion

1. Parse and validate `NarrativeBeatV1`.
2. Replay schedules deterministically against the audio clock.
3. Expose inspection telemetry for active hierarchy, beat phase, suppression,
   silence, and continuity checkpoint.
4. Initially render only neutral, face, mouth, gaze, and stillness behavior.
5. Prove timing, cancellation, resume, chapter seek, and replay parity.

### P3: add sparse speech-safe body accents

Promote only the curated neutral, think, explain, reference, sincere, and
contained reaction families. Enforce budgets and recovery before adding comic,
magic, action, or peak-emotion punctuation.

### P4: conduct directed long-form evaluation

Use both:

- a 2-3 minute balanced narrative/dialogue sample with an emotional or
  situational arc, matching PRH's professional audition lens; and
- at least one complete chapter plus a cross-chapter handoff, because a short
  sample cannot expose drift, habituation, or continuity loss.

Compare baseline neutral, proposed restrained direction, and a deliberately
overactive condition. Evaluate audio-only before audio-plus-avatar so reviewers
can distinguish narration problems from visual problems.

## Quality rubric

Score each dimension from 0 to 4:

- `0` harmful or contradictory;
- `1` materially distracting or often wrong;
- `2` understandable but inconsistent;
- `3` professional and meaning-supportive;
- `4` exceptional, precise, and durable over long listening.

| Dimension | Weight | A score of 3 requires |
|---|---:|---|
| Meaning fidelity | 15 | No contradiction, editorialization, stereotype, or altered implication. |
| Chapter and scene arc | 10 | Entry, turns, landing, and carryover remain legible without pose chatter. |
| Narrator stance continuity | 10 | POV, distance, role, and attitude persist and change only with evidence. |
| Dialogue/narration clarity | 8 | Modes and speakers are clear through subtle, consistent local choices. |
| Genre and beat timing | 12 | Suspense, comedy, intimacy, exposition, and reflection receive appropriate timing without formulaic acting. |
| Silence and spacing | 10 | Mouth and body respect every authored silence class and real audio duration. |
| Visual restraint | 10 | Accents are sparse, motivated, readable, and subordinate to listening. |
| Audio-visual synchronization | 10 | Mouth follows speech activity; beat stroke aligns with meaning; no anticipatory spoiler. |
| Recovery and long-form continuity | 8 | Holds, cooldown, chapter checkpoints, seek, pause, and resume remain coherent. |
| Accessibility and attention | 7 | Motion does not impair comprehension, captions, or sustained listening comfort. |

Weighted score is useful for comparison, but the following are **hard fails**
regardless of total:

- visual contradiction of the text or narrator stance;
- reaction before a spoiler-sensitive reveal;
- speech mouth movement during intentional aligned silence;
- identity, dialect, disability, culture, gender, or intimacy mapped to a
  stereotype;
- manuscript text or rationale retained in the visual schedule;
- nondeterministic replay for the same schedule and audio timing;
- chapter seek or resume restoring the wrong narrator, speaker, or emotional
  state;
- a high-salience gesture selected without a reviewed semantic beat;
- avatar motion that repeatedly draws evaluator attention away from the story.

### Objective evidence

Collect, but do not optimize blindly for:

- beat-to-apex timing error;
- count of pre-apex spoiler-sensitive accents;
- mouth-active frames inside aligned silence;
- gesture duty cycle by passage mode and chapter phase;
- non-neutral pose changes per thought unit;
- repeated gesture-family rate;
- suppressed-beat reasons;
- time spent in characterful neutral;
- continuity mismatches after pause, seek, reconnect, and chapter boundary;
- semantic schedule hash and rendered replay hash;
- human ratings for motion naturalness and speech appropriateness as separate
  measures.

No universal gesture-rate target should be frozen before listener studies. The
correct rate depends on genre, narrator, passage mode, visual scale, and whether
the listener is watching continuously or peripherally.

## Acceptance scenarios

1. **Quiet suspense:** rising threat with low activation, a long hold, reveal,
   contained reaction, and unresolved chapter exit.
2. **Action suspense:** rapid scene events while narration remains clear; only
   causal peaks earn body punctuation.
3. **Dry comedy:** neutral setup, delayed payoff, optional micro-tag, and a later
   callback that is not over-signaled.
4. **Intimate confession:** close narrator distance, vulnerability increase,
   no romance assumption, meaningful silence, and slow recovery.
5. **Dense exposition:** definition, sequence, contrast, exception, and summary
   with fewer gestures as information density rises.
6. **Reflective turn:** memory becomes reconsideration, then realization; the
   resulting stance persists into the next paragraph.
7. **Multi-character dialogue:** clear turn-taking and subtext with understated
   differentiation and no full-body speaker roulette.
8. **Chapter handoff:** prior cliffhanger or emotional result carries into a new
   POV or narrator without stale speaker state.
9. **Interruption and resume:** mouth closes, gesture settles or holds according
   to policy, and authoritative timing resumes without replaying elapsed beats.
10. **Degraded analysis:** missing or low-confidence beats produce a coherent
    neutral performance rather than random expressivity.

## Source ledger

### Primary and professional audiobook sources

1. [Library of Congress NLS, Narration Specification, revision 1.2, 2025](https://www.loc.gov/nls/who-we-are/guidelines-and-specifications/contract-specifications/narration/)
2. [Library of Congress NLS, The Art and Science of Audio Book Production](https://www.loc.gov/nls/who-we-are/guidelines-and-specifications/the-art-and-science-of-audio-book-production/)
3. [Audio Publishers Association, Audies Judging Criteria](https://www.audiopub.org/s/Audies-Judging-Criteria-for-Site.pdf)
4. [SAG-AFTRA, Audiobook Narration Workshop: It's Not About the Voice](https://www.sagaftra.org/audiobook-narration-workshop-it%E2%80%99s-not-about-voice)
5. [SAG-AFTRA, Breaking Into Audiobook Narration, 2025](https://www.sagaftra.org/sag-aftra-podcast-breaking-audiobook-narration)
6. [Penguin Random House Audio, Narrator Mentorship](https://penguinrandomhouseaudio.com/narrator-mentorship/)
7. [Penguin Random House Audio, Putting the Com in the Rom, 2024](https://penguinrandomhouseaudio.com/posts/putting-the-com-in-the-rom-a-qa-with-narrator-siena-east/)
8. [ACX Author Summit, Engaging Audiobooks, 2025](https://www.acx.com/mp/blog/how-to-write-and-produce-engaging-audiobooks-insights-from-the-acx-author)
9. [ACX, How to Act Like an Audiobook Narrator](https://www.acx.com/mp/blog/how-to-act-like-an-audiobook-narrator)
10. [ACX, 5 Tips for Choosing a Narrator](https://www.acx.com/mp/blog/5-tips-for-choosing-a-narrator)
11. [ACX, Andi Arndt's Audiobook Agenda](https://www.acx.com/mp/blog/andi-arndts-audiobook-agenda)
12. [ACX, Editing and Spacing](https://www.acx.com/mp/blog/editing-and-spacing-with-alex-the-audio-scientist)
13. [ACX, How to Succeed at Audiobook Production: Part 2](https://www.acx.com/mp/blog/how-to-succeed-at-audiobook-production-part-2)
14. [Patrick Fraley and Scott Brick, Prepping the Whole Audiobook](https://patfraley.com/pf/product/prep/)

### Primary visual-performance research

15. [Kelly et al., Integrating Speech and Iconic Gestures, 2009](https://pubmed.ncbi.nlm.nih.gov/19413483/)
16. [Sekine et al., Non-referential Gestures in Narrative Speech, 2021](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.661339/full)
17. [Kucherenko et al., GENEA Challenge 2023](https://arxiv.org/abs/2308.12646)
18. [He, Pereira, and Kucherenko, Evaluating Data-Driven Co-Speech Gestures Through Real-Time Interaction, 2022](https://media.contentapi.ea.com/content/dam/ea/seed/presentations/seed-evaluating-data-driven-co-speech-gestures-paper.pdf)

## Final direction

Build the audiobook director around **thought, relationship, trajectory, and
silence**. Let the audio reveal meaning; let Wizard Joe register only what the
listener is entitled to know; and spend the visual budget where a change in
story state genuinely benefits from being seen. The system will feel more alive
when it earns movement than when it constantly proves that movement is
available.
