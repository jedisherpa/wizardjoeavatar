# Film Editing and Previsualization Audit

**Role:** 10 - Film Editor and Previsualization Specialist
**Project:** Wizard Joe Audiobook Performance Engine and PrismGT Media Connector
**Audit date:** 2026-07-13
**Ownership boundary:** Research and direction only. No production code was changed.

## Executive decision

The two repositories contain complementary halves of a viable audiobook performance system, but they do not yet form an editorial system.

- PrismGT owns the real audiobook element and already reads `audio.currentTime`.
- Wizard Joe has a deterministic 60 Hz simulation, bounded command inbox, canonical state hashes, replay logs, authored animation clips, markers, and transition metadata.
- Neither repository contains a performance score, chapter/scene/beat/shot model, media-time connector, seek reconstruction contract, shot/take editor, or deterministic audiovisual review package.

The central architectural decision should be: **the audiobook media timeline is authoritative; the visual performance is a deterministic, seekable interpretation of that timeline.** Do not schedule visuals by elapsed wall time, render-frame count, caption-relative `setTimeout`, or live audio-analysis history. At any media time `t`, the connector must be able to evaluate the same semantic performance state without replaying the book from the beginning.

The editorial unit should not be a randomly selected pose. It should be an authored **performance phrase** inside a named story beat and visual setup:

`chapter -> scene -> beat -> setup -> performance phrase -> phase`

Each phrase should have motivation, media-time bounds, anticipation, stroke, hold, release, settle, staging intent, interruption rules, and a deterministic fallback. A shot is only a shot when framing or camera continuity actually changes. Until Wizard Joe exposes a real camera capability, call changes in screen position/scale/stage zone **setups** or **reframes**, not shots.

The initial production target should be intentionally modest: a stable narrator setup, authored entrances/exits and repositioning, sparse beat-level gestures, readable holds, deterministic transitions, and a small set of motivated framing presets. That will read as directed performance. A larger pose catalogue with automatic variation will read as pose roulette.

## Audit basis

### Current repository snapshots

- Python: `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar-python`
  - Branch: `codex/audiobook-performance-engine`
  - Commit: `7781a67c97bfbfa16a64d5b9fb12bdf74bd4c032`
- PrismGT: `/Users/paul/Documents/Codex/2026-06-28/jedisherpa-prism-geometry-talk-https-github/work/prism-geometry-talk-current`
  - Branch: `desktop/prism-gt-influence-integrated`
  - Commit: `0ce9f9bae665b1415cd776e4d6c9ee23565936ac`

The assignment brief was read in full. Its load-bearing requirements for this role are: audio remains authoritative; the score is precomputed; stillness is valid; randomness and continuous motion are prohibited; movement density varies with story intensity; chapter openings/endings, entrances/exits, repositioning, beats, optional framing, preview, export, and formal visual review must be explicitly designed.

### Verification scope

This was a read-only static audit of both current commits plus current official and professional sources. I inspected player, caption, animation, runtime, replay, pose-selection, scene-controller, media-normalization, audiobook-storage, and stage-control paths. I did not run or modify production code. The only written artifact is this report.

## Professional and technical anchors

1. **The media playhead, not `timeupdate`, is the clock.** The W3C timed-events note says synchronized web content should be tied to points or periods on the media timeline and recommends polling `currentTime` from `requestAnimationFrame` when smoother synchronization is required. The WHATWG media specification allows `timeupdate` cadence to vary from about 4 to 66 Hz and defines explicit `seeking`, `seeked`, `waiting`, playback-rate, and current-position behavior. [W3C, Requirements for Media Timed Events](https://www.w3.org/TR/media-timed-events/) and [WHATWG, HTML media elements](https://html.spec.whatwg.org/multipage/media.html)
2. **Block decisive poses before polishing motion.** SideFX's current Houdini documentation describes pose-to-pose work as keying important poses at their intended timeline positions, reviewing a blocking pass, and then adding transitions and finer controls. This is the right antidote to automatic pose churn. [SideFX, Animation styles](https://www.sidefx.com/docs/houdini/anim/anim_styles.html)
3. **Timing, staging, anticipation, and follow-through are one performance problem.** Disney Animation identifies timing, clear staging, anticipation, follow-through, and secondary action as core character-animation principles. The engine should therefore represent them as related phases of one phrase, not unrelated commands. [Walt Disney Animation Studios, Animation process](https://www.disneyanimation.com/process/animation/)
4. **Previs is decision-making, not decoration.** Autodesk describes previs and animatics as early tools for testing actor blocking, camera placement, timing, voiceover, music, and visual direction before expensive production. The proposed editor should make those decisions cheap to compare. [Autodesk, What is previsualization?](https://www.autodesk.com/solutions/previsualization-software)
5. **Shots and takes should be hierarchical and non-destructive.** Epic's Sequencer documentation models sequences, shots, trim handles, contextual neighboring shots, metadata, and alternate takes without modifying the original. That is a useful workflow precedent even though this project should not adopt Unreal's runtime model. [Epic Games, Sequences, Shots, and Takes](https://dev.epicgames.com/documentation/en-us/unreal-engine/sequences-shots-and-takes-in-unreal-engine) and [Epic Games, Take Recorder](https://dev.epicgames.com/documentation/en-us/unreal-engine/take-recorder-in-unreal-engine)
6. **Picture and sound may lead or trail each other without changing the audio.** Adobe's current J- and L-cut guidance describes transitions in which incoming audio anticipates the image or outgoing audio continues over the next image. For Wizard Joe, the transferable principle is a bounded visual lead or trail around a spoken beat, while the audiobook itself remains untouched. [Adobe Premiere, Perform J cuts and L cuts](https://helpx.adobe.com/premiere/desktop/edit-projects/trim-clips/perform-j-cuts-and-l-cuts.html)
7. **Editorial interchange is useful, but it is not the media.** OpenTimelineIO is a mature ASWF interchange model for editorial order, ranges, transitions, markers, metadata, and references to external media. Its own documentation makes the coordinate spaces explicit. It is appropriate as an optional export, not as the audiobook performance runtime. [ASWF, OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO) and [OTIO 0.18.1, Time Ranges](https://opentimelineio.readthedocs.io/en/v0.18.1/tutorials/time-ranges.html)
8. **Review evidence must address exact timeline locations.** ASWF's Open Review Initiative exposes session, timeline, annotation, and viewport APIs, including feedback on particular clip frames. Wizard Joe review notes should likewise be attached to immutable media time, score version, and render identity. [ASWF, ReviewPluginApi updates](https://www.aswf.io/blog/reviewpluginapi-updates/)

## Findings

### F1. Critical: PrismGT and Wizard Joe run on different clocks

PrismGT's analyzer reads the browser audio element's `currentTime` during its animation-frame loop (`src/pages/PrismDodecahedron/musicMotion.js:240-336`). That is the right clock source. Wizard Joe's controller advances its own simulation time at a fixed 60 Hz (`wizard_avatar/controller.py:42-53`), while the procedural frame source advances that simulation by `1 / fps` whenever a frame is requested (`wizard_avatar/frame_source.py:48-87`). The separate deterministic runtime also advances from a monotonic wall clock with a catch-up limit (`wizard_avatar/runtime.py:303-351`).

There is no connector that translates the authoritative media position into a Wizard Joe state. Consequently, play, pause, buffering, rate changes, tab throttling, rendering stalls, and seeks can put visual state on a different timeline from the narration.

**Direction:** introduce a media-time evaluation mode. PrismGT sends a normalized transport snapshot containing media identity, integer media time, playback state, rate, discontinuity sequence, and score version. Wizard Joe evaluates the score at that media time; its 60 Hz tick remains an internal deterministic sampling grid, not an independent playback clock.

### F2. Critical: no precomputed editorial score exists in either current branch

`WizardState` contains world position, facing, locomotion, one action, expression, mouth, pose/clip/transition identifiers, timers, and a semantic cue (`wizard_avatar/models.py:123-169`). It has no book, chapter, scene, beat, setup, shot, take, media, score, staging, or camera identity. The command envelope can carry an `issued_tick` and duration but no media-time range (`wizard_avatar/commanding.py:118-169`).

PrismGT's normalized audiobook track contains title, audio, captions, and related metadata but no performance score (`src/lib/media-normalize.js:42-68`; `crates/prism-cdiss-cli/src/audiobooks.rs:85-99`). The Dodecahedron page owns one audio ref, track/caption state, and analyzer metrics but no visual score or connector state (`src/pages/PrismDodecahedron/index.jsx:196-335`). Searches of the current PrismGT branch found no Wizard Joe connector or audiobook performance-score implementation.

**Direction:** define a versioned, validated `PerformanceScoreV1` before expanding runtime behavior. Precomputation should yield explicit ranges and decisions. Live RMS/flux may be shown as diagnostic context, but it must not decide production staging or gestures.

### F3. Critical: PrismGT does not expose an editorial transport

Track loading, previous/next, play, and pause are implemented (`src/pages/PrismDodecahedron/index.jsx:1095-1214`). The visible progress display is a `role="meter"`, not an input scrubber, and the transport has no seek, frame/step, loop-range, rate, chapter-marker, or compare controls (`src/pages/PrismDodecahedron/components/StageUtilityCards.jsx:347-457`).

The analyzer listens for play, pause, ended, and loaded metadata, but not `seeking`, `seeked`, `ratechange`, `waiting`, `stalled`, `playing`, or media-source replacement as a discontinuity (`src/pages/PrismDodecahedron/musicMotion.js:351-370`).

**Direction:** make transport state a first-class adapter around the existing `<audio>` element. Normal playback should sample `currentTime` every animation frame. Discontinuities must increment a sequence number, cancel stale work, reconstruct state at the new time, and publish the first correct post-seek state. `timeupdate` can update low-frequency UI, but must not schedule performance.

### F4. High: caption-relative `setTimeout` scheduling is not seek- or rate-safe

PrismGT finds the active WebVTT cue from `currentTime` (`src/pages/PrismDodecahedron/captions-vtt.js:3-44,96-101`). It then tokenizes caption text and schedules word pulses with `setTimeout` from cue duration and current position (`src/pages/PrismDodecahedron/index.jsx:2029-2105`). React cleanup clears timers when the active-cue effect changes (`src/pages/PrismDodecahedron/index.jsx:2972-2985`), but there is no explicit transport-discontinuity contract and no rate-aware rescheduling.

This approach can emit stale pulses after a seek or playback-rate change, compress words incorrectly, and inherit browser timer throttling. It also reconstructs token timing heuristically rather than using aligned word/phoneme data.

**Direction:** replace relative timers for production cues with state-at-time evaluation over aligned cue ranges. On every render sample, determine which word/phoneme and performance phases are active at the current media time. Timers may remain an optimization only if every callback checks media identity, score version, discontinuity sequence, and active range before acting.

### F5. Critical: selected transition metadata is reported but not performed

The Python graph has useful editorial concepts: loop mode, phase policy, root policy, interrupt policy, contact/action/speech markers, minimum holds, legal successors, and transition recipes (`wizard_avatar/animation_graph.py:35-67,103-173`). Pose selection deterministically chooses a transition identifier when the node changes, immediately swaps to the target node/clip, and resets the clip tick (`wizard_avatar/pose_selection.py:86-107`). The frame source explicitly presents the new sprite as an atomic snapshot and forces transition progress to complete (`wizard_avatar/frame_source.py:172-181`).

Atomic sprites are a valid constraint; interpolating individual cells would create false anatomy. But an atomic image does not require an atomic performance change. The missing layer is an authored sequence of complete snapshots: anticipation pose, action stroke, readable hold, release, recovery, and settle.

**Direction:** execute transition recipes as timed semantic phases made of valid whole poses. A transition ID must correspond to observable phase/range evidence. No normal pose change should bypass the phrase evaluator unless the cue explicitly permits a coherent hard cut.

### F6. High: current selection is deterministic but editorially repetitive

For a selected action/facing/mobility combination, pose selection gathers matching nodes and returns the first match (`wizard_avatar/pose_selection.py:110-173`). This avoids random nondeterminism, but it does not provide intentional variation, motif continuity, anti-repeat policy, or a take choice. During active speech, the effective body action is suppressed (`wizard_avatar/pose_selection.py:141-150`), so the current system alternates between under-performance and explicit command-driven pose replacement rather than phrase-level acting.

Introducing random pose choice would make the problem worse. It would vary evidence between runs and assign visual accents without story motivation.

**Direction:** selection should be authored or deterministically planned during score generation. Each cue records a chosen pose family/take and why it is used. Automatic fallback can consider recent history, but the resolved choice is persisted in the score. Add measurable repetition rules such as `same gesture family not reused inside cooldown unless motif_id matches`; never sample a new pose merely because a timer expired.

### F7. High: staging exists as coordinates, not as dramatic blocking

Wizard Joe can move, follow paths, face directions, and occupy a world position (`wizard_avatar/controller.py:144-217`; `wizard_avatar/models.py:123-169`). PrismGT exposes manual stage X/Y/zoom controls through its stage utility and persisted geometry settings (`src/pages/PrismDodecahedron/components/StageUtilityCards.jsx:600+`). Neither side models stage zones, marks, entrances, exits, eyelines, composition objectives, protected caption areas, character occupancy, or a reason for repositioning.

**Direction:** author named stage zones and setups before continuous coordinates. A locomotion cue must identify source mark, destination mark, motive, path policy, facing on arrival, and settle range. Movement without a destination or story purpose is invalid. Repositioning should happen at scene changes, entrances/exits, or deliberate beat transitions, not as ambient activity.

### F8. High: PrismGT camera and scene motion are wall-clock/reactive, not editorial

The Three.js scene creates a perspective camera and exposes mode, shape, expression, configuration, and audio controls (`src/pages/PrismHero/createPrismHeroScene.js:644-674,719-729`). Its render loop advances from `performance.now`; shape transitions, damping, and settle phases advance with local delta time (`src/pages/PrismHero/createPrismHeroScene.js:1251-1261,1427-1467,1596-1622,1683-1711`). Camera/stage behavior is influenced by pointer and configuration values (`src/pages/PrismHero/createPrismHeroScene.js:2695-2750`). The controller has no `evaluateAtMediaTime`, snapshot, seek, or camera-cue API (`src/pages/PrismHero/createPrismHeroScene.js:2875-2910`).

That motion may be appealing as an interactive background, but it cannot serve as deterministic editorial evidence. Pointer drift is not camera direction; audio-reactive damping is not a shot.

**Direction:** add a deterministic review mode that disables pointer influence and evaluates configured visual state from media time. Camera/framing cues should use a small capability-negotiated preset vocabulary. If the Wizard Joe output is a fixed rendered frame rather than a camera-addressable scene, the connector should apply screen-space placement and scale only, and name it accurately as a reframe.

### F9. High: there is no blocking, take, or compare workflow

Neither repository exposes an editorial timeline with waveform, transcript, chapter/scene/beat lanes, staging, performance phrases, setup/framing tracks, transition handles, markers, versions, or take comparison. Existing controls are runtime controls, not an editor. Existing Wizard Joe action/showcase surfaces can prove that a pose is reachable, but cannot answer whether it is the right pose at the right spoken beat.

**Direction:** create a score editor around the media timeline, not inside the Three.js renderer or the avatar compositor. The first pass should be a flipbook-like blocking pass: audio plus decisive setup and key-pose cards. The second pass authors phrase phases and transitions. The third pass handles staging/framing. Polish follows only after a chapter plays convincingly in blocking.

### F10. High: existing deterministic evidence is reusable but not audiovisual editorial evidence

The Python runtime has a strong foundation: exact simulation ticks, deterministic command ordering, canonical state hashes, and NDJSON replay records (`wizard_avatar/runtime.py:90-230,242-300`). The bounded command inbox orders due commands deterministically and can discard pending kinds (`wizard_avatar/commanding.py:306-408,467-480`). Frame diagnostics expose tick, pose, action, expression, clip/node, and related state (`wizard_avatar/frame_source.py:528-570`).

Those mechanisms prove runtime determinism, not synchronization to a particular audio file and score. Current evidence does not bind media hash, score hash, transport events, media timestamps, visual state, rendered frames, and reviewer notes into one reviewable package.

**Direction:** extend the existing evidence conventions rather than creating an unrelated logger. Every replay record needs media time and discontinuity identity. Every review package needs immutable input hashes, code commits, score version, capability profile, event log, sampled state hashes, selected frames/contact sheets, and a playable audiovisual proxy.

### F11. Strength: the repositories already have the right low-level seams

Useful foundations should be preserved:

- PrismGT already has the actual HTML audio element and reads `currentTime`.
- Caption parsing already produces bounded media-time ranges.
- Wizard Joe already separates controller state, animation graph evaluation, pose selection, frame rendering, diagnostics, and deterministic replay.
- Graph clips already expose markers and policies that can become phrase constraints.
- The command inbox already has deterministic ordering and cancellation primitives useful for discontinuities.
- Character-package capabilities provide a natural place to negotiate staging, gesture, expression, and future framing support.

The missing work is primarily orchestration, editorial data, and review tooling. It does not require replacing either renderer.

## Proposed editorial model

### 1. Canonical time

Store score times as integers with an explicit time base. Preferred choices are audio sample index plus sample rate, or integer microseconds plus source sample rate metadata. Do not make binary floating-point seconds the canonical serialized identity. At runtime:

```text
media_time_tick = round(audio.currentTime * score.time_base)
visual_state = evaluate(score, media_time_tick, capability_profile)
```

The transport snapshot should include:

```json
{
  "media_id": "sha256:...",
  "score_id": "sha256:...",
  "media_time_tick": 123456789,
  "time_base": 1000000,
  "playback_rate": 1.0,
  "transport": "playing",
  "discontinuity_seq": 12,
  "presented_at_monotonic_ns": 0
}
```

`presented_at_monotonic_ns` is diagnostic latency data only. It must never change the chosen performance.

### 2. Hierarchy and terminology

| Unit | Editorial purpose | Required identity |
|---|---|---|
| Book/chapter | Continuity, energy arc, open/end behavior | source media range and stable ID |
| Scene | Location, cast, dramatic objective, staging reset policy | scene ID, range, participants |
| Beat | One change in thought, tactic, information, or emotion | beat ID, range, text/audio anchors |
| Setup | Stable composition and stage arrangement | setup ID, marks, scale/framing preset |
| Shot | A setup interval with an actual camera/framing cut | shot ID, setup ID, cut range |
| Performance phrase | One motivated body/face/locomotion action | phrase ID, character, intent, range |
| Phase | Anticipation, stroke, hold, release, settle | phase range and transition policy |
| Take | Non-destructive alternative for a beat/setup/phrase | parent ID, take number, status, note |

Avoid calling every gesture a shot and every pose a beat. Those terms carry useful editorial meaning only when their boundaries are deliberate.

### 3. Track model

`PerformanceScoreV1` should minimally contain:

- immutable audio/media reference and hash;
- chapter, scene, beat, and review-marker tracks;
- per-character presence and stage-zone tracks;
- locomotion/repositioning track;
- body-performance phrase track;
- expression, gaze, blink, and speech-mouth tracks;
- setup/framing track, optional and capability-gated;
- score provenance, generator version, manual overrides, and take lineage.

Every phrase should include `character_id`, `beat_id`, `setup_id`, `intent`, `motivation`, `source_mark`, `destination_mark`, `pose_family`, resolved `take_id`, amplitude band, phase ranges, minimum hold, interruption boundary, transition in/out, `must_hold`, `allow_flourish`, fallback chain, and provenance. Generated suggestions and approved editorial decisions must remain distinguishable.

### 4. State-at-time evaluation

The evaluator must be a pure function of score, media time, character capabilities, and fixed versioned policy. It should:

1. Find the containing chapter, scene, beat, setup, and active phrases.
2. Resolve track priority and channel ownership.
3. Evaluate phrase phase and target semantic state.
4. Apply deterministic fallback if a requested capability is unavailable.
5. Emit a complete target state and reason trace.

Seeking must not fire every cue skipped over. It reconstructs the state valid at the destination. Forward playback may emit edge events for observability, but rendering still derives from current media time. The result at `t` after a seek must equal the result at `t` after linear playback.

## Transition grammar

### Performance phrase phases

| Phase | Function | Editorial rule |
|---|---|---|
| Anticipation | Prepare weight, gaze, or thought | May precede the spoken accent only when it does not reveal information early |
| Stroke | Primary readable action or attitude change | Align to the intended word, syllable, pause, or dramatic event |
| Hold | Let the audience read the pose and hear the thought | Stillness is valid; never shorten solely to add variation |
| Release | Exit the accent without another unrelated idea | Preserve silhouette and contact continuity |
| Settle | Re-establish balance, eyeline, and baseline | Must complete before incompatible locomotion or a new major phrase |

Anticipation, hold, and settle are authored ranges, not global easing sliders. PrismGT's existing `anticipation` and `settle` configuration values (`src/lib/motion-config.js:16-30`) may tune a renderer, but they cannot replace phrase timing.

### Editorial transition types

| Type | Use | Prohibition |
|---|---|---|
| Hold | Preserve a strong read through narration | Do not inject motion because the screen has been still for N seconds |
| Motivated pose transition | Thought, tactic, or emotional state changes | No unrelated pose-family swap |
| Contact/phase match | Locomotion or action continues across clip samples | No foot sliding or root jump |
| Recovery bridge | Return from gesture/action to narrator baseline | No snap directly from peak pose to neutral unless marked as a deliberate cut |
| Reposition | Enter, exit, cross, or establish a new relationship | Requires destination, route, arrival facing, and settle |
| Setup cut | New scene, chapter, point of view, or deliberate emphasis | Not for every sentence; cut must be logged as a setup/shot boundary |
| Motivated reframe | Slow scale/position change supporting an energy shift | No perpetual drift, pointer-driven review motion, or unbounded zoom |
| Coherent hard cut | Shock, comic punctuation, or hidden discontinuity | Explicit opt-in with reason and before/after evidence |

For an audio-authoritative work, adapt the J/L-cut idea carefully: the picture may anticipate a change or hold after it, but the audio edit is locked. A visual anticipation range must be bounded and semantically non-spoiling. A trailing settle may overlap the next sentence only when it does not contradict the new thought.

## Staging and camera direction

### Stable stage grammar

Begin with named normalized zones such as `off_left`, `left`, `center`, `right`, `off_right`, plus foreground/background only if the renderer can preserve scale and collision expectations. Each setup defines:

- active character marks and protected regions;
- caption/UI exclusion zones;
- baseline facing and eyeline;
- entrance and exit edges;
- maximum scale and translation bounds;
- whether movement is allowed during speech;
- setup continuity across the next beat.

For one narrator, center or a modest rule-of-thirds offset should remain the default. For multiple characters, screen direction and eyeline must remain stable within a scene. Do not flip left/right merely to vary composition. A character crossing the axis must either be shown crossing or be introduced by a deliberate setup change.

### Camera/screen movement policy

Use a small preset vocabulary: `wide`, `medium`, `close`, `two_shot`, and perhaps `detail` only where the output can support it. Every change requires a setup/shot ID and editorial reason. The capability profile decides whether the implementation is a real camera, a source crop, or screen-space placement.

Initial restrictions:

- no handheld/noise motion;
- no continuous breathing camera;
- no automatic zoom from RMS or spectral flux;
- no pointer influence in deterministic review/export;
- no simultaneous large character move and large camera move unless specifically authored;
- no camera cut before Wizard Joe has produced the destination state for that media time;
- caption-safe and viewport-safe framing at all supported aspect ratios.

Camera motion should be rarer than body motion, and body motion should be rarer than facial/mouth activity. This creates an intelligible hierarchy of emphasis.

## Avoiding pose roulette

The planner should resolve variation once and persist it. Use these constraints:

1. **Intent before pose.** Select the dramatic purpose, energy, stage objective, and phase envelope before choosing an asset.
2. **Pose families, not flat lists.** One family contains baseline, anticipation, stroke, hold, and recovery candidates that belong together.
3. **Motif-aware repetition.** Repetition is allowed when it establishes a character motif or rhetorical callback; otherwise enforce a family cooldown.
4. **No autonomous expiry.** A held pose changes because the beat or phrase changes, not because a generic timer reached zero.
5. **Persist generated choices.** A seeded planner may help propose a take, but approval writes an explicit `take_id` and pose sequence to the score.
6. **Track recent visual load.** Density is measured over rolling windows and chapter arcs so peaks remain distinguishable.
7. **Prefer omission.** If no asset satisfies staging, continuity, and intent, hold the baseline and record a fallback reason.

Suggested starting QC limits should be fixture-specific, not universal aesthetic laws. For a designated quiet 60-second review fixture, require at least one uninterrupted two-second body hold, no locomotion unless the script marks a move, no more than three major body strokes in any ten-second window, and no unmotivated setup change. For an action fixture, use an explicit expected-cue list rather than simply raising a random movement quota.

## Preview, edit, and export workflow

### Pass 1: ingest and lock

- Hash and lock the exact audio asset.
- Display waveform, aligned transcript/captions, chapters, scenes, and detected beat suggestions.
- Preserve human-edited timing separately from generated suggestions.
- Establish chapter duration, time base, supported character profile, and safe viewport.

### Pass 2: blocking

- Work in audio loops around one beat or scene.
- Place setups, stage marks, entrances/exits, and decisive key poses.
- Preview as stepped whole-pose blocking with mouth/fine motion optionally muted.
- Reject unclear silhouette, eyeline, or movement motivation before adding transitions.

### Pass 3: performance timing

- Expand each approved phrase into anticipation, stroke, hold, release, and settle handles.
- Slip visual phases against the locked audio; never ripple or retime the audiobook.
- Provide frame/tick stepping, loop range, marker notes, and audible normal-speed review.
- Expose reason, source cue, fallback, and channel conflicts for the selected phrase.

### Pass 4: staging and framing

- Add only motivated repositioning and setup changes.
- Show prior/next setup context while editing boundaries.
- Validate safe areas, screen direction, captions, and multi-character occupancy.
- Compare with camera/framing track muted to prove the performance still reads.

### Pass 5: takes and approval

- Duplicate a beat/phrase/setup as a non-destructive take.
- A/B takes at the same audio range and transport state.
- Record editor, date, rationale, source score, and approval state.
- Promote one take without deleting alternatives.

### Pass 6: export

The canonical export is a versioned score bundle, not only a video:

```text
manifest.json
performance-score.json
media.sha256
capability-profile.json
transport-events.ndjson
state-samples.ndjson
frame-hashes.json
review-overlay.mp4 (or webm)
contact-sheet.png
review-notes.json
```

Optionally export `.otio` for editorial interchange. Use OTIO clips/ranges for chapters, scenes, setups, and shots; markers/metadata can carry beat and performance references. The project-specific score remains canonical because OTIO adapters may not preserve custom performance semantics. Round-trip `.otio` itself losslessly in tests, and clearly report any lossy third-party adapter conversion.

The review proxy should include burn-ins for media time, chapter/scene/beat/setup/phrase IDs, score hash prefix, transport state, pose/node/transition IDs, and capability fallback. Burn-ins may be disabled for creative viewing, but the evidence version must retain them.

## Deterministic review evidence

### Required provenance

Every evidence run must bind:

- audio SHA-256 and duration/time base;
- score SHA-256 and schema version;
- Python and PrismGT commit IDs;
- character package, pose library, animation graph, and capability-profile hashes;
- browser/runtime version, viewport, render FPS, and review mode;
- run ID, start/end media ticks, playback rate, and all discontinuity events.

### Required comparisons

1. **Linear versus seek:** state and sampled frame hash at `t` after linear playback must match a cold seek to `t`.
2. **Render-rate independence:** semantic state hashes at fixed media ticks must match at 24, 30, and 60 presentation FPS.
3. **Playback-rate independence:** cue media ranges and order must match at 0.5x, 1x, 1.5x, and 2x.
4. **Pause/wait:** the media playhead and authored phase stop advancing. In deterministic review mode, nonessential idle motion also freezes or is derived from the same media tick.
5. **Repeatability:** two runs with identical inputs produce identical state hashes and sampled frame hashes.
6. **Fallback:** removing a capability produces the documented fallback and a stable reason code, not silence or a random substitute.
7. **Review addressability:** every note resolves to media tick, score hash, run ID, and optional frame hash.

The playable proxy is necessary for editorial judgment but insufficient as proof. Pair it with machine-readable logs and hashes. Conversely, hashes alone cannot prove pacing, staging clarity, or emotional timing; pair them with contact sheets and full-speed audiovisual review.

## Acceptance tests

### Transport and timing

| ID | Test | Pass condition |
|---|---|---|
| T1 | Authoritative clock | While playing, every connector sample records the same media identity and a media tick derived from the current audio position; no visual scheduler advances from wall time alone |
| T2 | Cue onset | On a controlled local fixture, 95% of visible strokes appear within one presentation frame plus 20 ms of their authored media tick; maximum error is under 100 ms |
| T3 | Seek reconstruction | For 1,000 deterministic random seek points, the first settled state after `seeked` equals linear evaluation at the same media tick |
| T4 | Stale work | After each of 100 forward/backward seeks, zero callbacks or commands from an older discontinuity sequence alter state |
| T5 | Rate changes | At 0.5x, 1x, 1.5x, and 2x, active phrase IDs at sampled media ticks are identical and ordered identically |
| T6 | Buffering/pause | During `waiting` or pause, media-derived phase does not advance; resume continues from current media position without burst catch-up |
| T7 | Source replacement | Loading a new track invalidates all prior media/score work before the first state for the new media is displayed |

### Editorial behavior

| ID | Test | Pass condition |
|---|---|---|
| E1 | Phrase completeness | Every major phrase has valid anticipation/stroke/hold/release/settle ranges or an explicit waived phase with reason |
| E2 | No pose snap | Every changed body pose is explained by an active transition/phrase or an approved coherent-cut marker |
| E3 | Hold readability | `must_hold` ranges contain no body pose, stage mark, or setup changes |
| E4 | Movement motivation | Every locomotion cue has source, destination, reason, arrival facing, and settle; zero free-roaming cues pass schema validation |
| E5 | Pose repetition | A non-motif gesture family cannot recur inside its configured cooldown; all exceptions name a `motif_id` |
| E6 | Quiet fixture | The approved quiet-minute fixture contains the expected stillness interval, no locomotion, no unmotivated cut, and no more than three major strokes per ten-second window |
| E7 | Chapter boundaries | Each fixture chapter has an explicit opening setup and ending hold/settle policy, including the zero-motion option |
| E8 | Multi-character continuity | Stage zones never overlap illegally; eyeline and screen direction remain stable unless an axis-crossing event is authored |
| E9 | Framing safety | At every supported viewport, all active characters remain inside safe bounds and do not occlude caption/UI exclusion regions |

### Determinism and evidence

| ID | Test | Pass condition |
|---|---|---|
| D1 | State determinism | Two identical runs produce byte-identical canonical state-sample logs |
| D2 | Frame determinism | Sampled frames at fixed media ticks produce identical hashes in the supported deterministic renderer/environment |
| D3 | FPS independence | State hashes at fixed media ticks match across 24/30/60 FPS presentation runs |
| D4 | Evidence completeness | Missing input hash, commit, time base, score version, transport event log, or review overlay fails the evidence gate |
| D5 | Note identity | Every review note references an existing score hash and valid media range; stale notes are shown as stale rather than silently migrated |
| D6 | OTIO interchange | Native `.otio` write/read preserves chapter, scene, setup/shot ranges, markers, external media reference, and project metadata |

### Workflow usability

| ID | Test | Pass condition |
|---|---|---|
| U1 | Scrub | Dragging or clicking the timeline updates audio and visual preview to the selected media time without playing skipped cues |
| U2 | Step/loop | The editor can step one configured frame/tick and loop a selected beat while preserving audio lock |
| U3 | Take compare | Two takes can be switched at the same media range without altering their source data or the audio |
| U4 | Track mute | Body, face, staging, and framing tracks can be muted independently for diagnostic review |
| U5 | Score diff | A reviewer can see changed ranges, phrase IDs, and take selections between two score versions before approval |

## Risk register

| Risk | Severity | Why it matters | Mitigation |
|---|---|---|---|
| Dual-clock drift | Critical | Performance loses sync over long chapters and after stalls | Media-time evaluation; wall time diagnostic only |
| Seek/rate stale timers | Critical | Old words or gestures fire in the wrong scene | Discontinuity sequence, cancellation, state reconstruction |
| Pose roulette | High | Character intention appears arbitrary and evidence varies | Persist resolved takes; motif/cooldown policy; omission fallback |
| Over-direction | High | Motion competes with narration and destroys peaks | Density budgets, mandatory holds, track-mute review, quiet fixture |
| Transition metadata theater | High | UI/log claims a transition that viewers only see as a snap | Phase-level execution and before/after evidence gate |
| Camera capability mismatch | High | A screen transform is presented as a camera shot | Capability negotiation and precise setup/reframe terminology |
| Interactive motion contaminates review | High | Pointer, frame rate, or analyzer history changes approved result | Deterministic review mode; media-time scene evaluation |
| Floating-point/time-base disagreement | High | Boundary cues differ across runtimes | Canonical integer time base and shared rounding tests |
| Lossy OTIO adapters | Medium | Custom cues disappear in NLE interchange | Canonical score bundle; native OTIO round-trip; adapter warnings |
| Evidence without editorial meaning | Medium | Hashes pass while pacing is poor | Full-speed A/V review plus machine evidence and timed notes |
| Editorial notes become stale | Medium | Approval refers to an older score or frame | Bind notes to score/run/frame identity and surface staleness |
| Scope inflation into a full NLE | Medium | Core playback correctness is delayed | Build a focused score editor: locked audio, tracks, takes, review/export |

## Recommended implementation order and code ownership

### P0: establish the clock and score contract

1. Define `PerformanceScoreV1`, canonical integer time, schema validation, media/score hashing, and state-at-time evaluator in a renderer-neutral module.
2. In PrismGT, add a transport adapter around the existing audio element near `src/pages/PrismDodecahedron/index.jsx` and `musicMotion.js`. Cover play, pause, seeking/seeked, ratechange, waiting/playing, ended, source replacement, and animation-frame sampling.
3. In Wizard Joe, add a media-time driver beside `wizard_avatar/runtime.py`; reuse deterministic ordering, replay, state hashing, and inbox cancellation. Do not replace the existing runtime clock for non-media uses.
4. Add a connector protocol that sends transport snapshots and score identity, and returns complete state plus reason trace and diagnostics.

### P1: execute phrases, not pose commands

1. Extend the state/diagnostic contract with chapter, scene, beat, setup, shot, phrase, phase, take, media tick, and discontinuity IDs.
2. Build phrase transition execution above `pose_selection.py` and `animation_graph.py`; preserve whole-pose rendering in `frame_source.py`.
3. Add stage-zone and motivated locomotion validation around controller movement commands.
4. Persist resolved variation and fallback decisions in the score.

### P2: focused previs/editor workflow

1. Replace the meter-only progress surface with a real scrub/loop transport while retaining accessible semantics.
2. Add waveform/transcript and chapter/scene/beat/setup/performance/review lanes.
3. Support blocking, phase handles, take duplication/comparison, track mute, score diff, and marker notes.
4. Keep the editor separate from `createPrismHeroScene.js`; the scene should evaluate state, not own editorial data.

### P3: framing and interchange

1. Add capability-gated setup/framing presets and deterministic scene evaluation.
2. Disable pointer/audio-reactive influence in review mode.
3. Add canonical evidence-bundle export and optional OTIO export.
4. Add burn-in proxy, contact sheet, state/event logs, and timed-review-note import/export.

## Release gate

Do not call the connector audiobook-performance-ready until all P0 timing tests, seek/rate tests, phrase-transition tests, and evidence-completeness tests pass on at least:

- one quiet reflective chapter segment;
- one dialogue/multi-character segment;
- one action or high-intensity segment;
- one chapter opening and ending;
- one fixture containing pause, seek backward, seek forward, buffer/wait, rate change, and track replacement.

Creative approval should then review each fixture twice: once as an unadorned audiovisual experience, and once with diagnostic burn-ins. The first asks whether the narration remains primary and the performance feels intentional. The second proves exactly which score, media, state, and render produced that judgment.

## Final direction

The most cinematic version of Wizard Joe is not the one that moves most. It is the one whose stillness, anticipation, action, hold, settle, staging, and framing all arrive for a reason on the audiobook's timeline.

Build the connector as a deterministic editorial player. Block chapter-scale intent first, resolve visual takes into a versioned score, reconstruct state on every discontinuity, and make approval evidence addressable to exact media time. With that foundation, Wizard Joe's existing pose library and PrismGT's existing player can become a directed long-form performance instead of a sequence of technically valid but editorially unrelated reactions.
