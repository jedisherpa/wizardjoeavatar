# Synthesis C: Animation and Delivery

**Program:** Wizard Joe Audiobook Performance Engine and PrismGT Media Connector
**Synthesis scope:** animation direction, editorial timing, facial performance, music performance, QA, evidence, sequencing, ownership, CI, risks, and completion
**Audit date:** 2026-07-13
**Python baseline:** `7781a67c97bfbfa16a64d5b9fb12bdf74bd4c032` on `codex/audiobook-performance-engine`
**PrismGT baseline:** `0ce9f9bae665b1415cd776e4d6c9ee23565936ac` on `desktop/prism-gt-influence-integrated`
**Inputs reconciled:** the full project brief, current-state map, program tracker, and specialist reports 01 through 12

## 1. Executive Decision

The existing Python application is a deterministic square-cell pose player with a useful command kernel, not yet an audiobook or music performance engine. PrismGT owns the actual media element and therefore the only valid playback clock, but it has no Wizard media-session connector, no performance score, no editorial transport, and no cross-process evidence path.

The implementation should preserve both runtimes and add a deterministic editorial layer between them:

```text
accepted semantic score + exact media time + character package + accessibility profile
    -> pure state-at-time evaluation
    -> character capability resolution and explicit fallback
    -> phrase phases and bounded preload
    -> existing ordered Python command/runtime path
    -> atomic square-cell pose plus declared face/mouth overlays
    -> synchronized frames, diagnostics, replay, and review evidence
```

The creative rule is equally binding: Wizard Joe performs changes of thought, relationship, story pressure, and musical structure. He does not illustrate every word, react to every onset, or move merely because time has passed. Characterful neutral and authored stillness are the default. Body accents, stage movement, reframes, and spectacle consume progressively scarcer visual budgets.

Production delivery must proceed in waves. Contract, clock, deterministic replay, capability truth, and accessibility projection precede expressive autonomy. Audiobook body performance precedes production music choreography. A focused editor follows a proven evaluator, not the reverse. Release requires the same candidate revisions to pass synchronization, determinism, privacy, accessibility, performance, long-form, and signed creative-review gates.

## 2. Confirmed Current Code Reality

The following observations were rechecked against the audited files and are implementation constraints, not report-level assumptions.

| Area | Current code path | Confirmed behavior and delivery consequence |
| --- | --- | --- |
| Pose selection | `wizard_avatar/pose_selection.py:50-173` | A graph transition ID is selected, but the target clip starts immediately. Active `speech_id` suppresses the speaking body action. Matching actions choose the first node. |
| Pose presentation | `wizard_avatar/frame_source.py:89-181` | The normal path uses authored reference poses and presents them as atomic snapshots. Per-cell dissolves are deliberately disabled. Keep this policy. |
| Face and mouth | `wizard_avatar/frame_source.py:183-433` | Eye visibility is color-inferred, gaze is horizontal `-1/0/+1`, blink is a periodic threshold, and speech mouth cycles four shapes at 10 Hz. Timing is not narration-aware. |
| Controller clock | `wizard_avatar/controller.py:42-54` | Simulation and blink advance from the Python fixed tick, not media time. Speech ends from a duration timer. |
| Semantic input | `wizard_avatar/controller.py:262-310` | Gesture, amplitude, and tempo partly survive; hold and flourish policy do not become scheduler behavior. Semantic body actions are suppressed during active speech. |
| Character package | `wizard_avatar/character_package.py:18-94` | V1 names two asset files and six broad strings. It has no structured mappings, channel truth, hashes, compatibility range, preload policy, or fallback records. |
| Command kernel | `wizard_avatar/commanding.py:11-169` | Commands are bounded, ordered, deduplicated, and acknowledged. The queue is capped at 1,024 and 120 future ticks. It has no media, score, cue, or character session identity. |
| Frame loop | `wizard_avatar/stream.py:151-190` | Runtime advances from `perf_counter_ns`; synchronous compose/encode occurs in the loop; missed presentation slots are dropped. The real path currently misses its isolated deadline test. |
| Server boundary | `wizard_avatar/server.py:120-240` | Strict ordered HTTP commands exist, but no media-session endpoint exists. The legacy frame WebSocket accepts before origin/auth validation and is not a safe connector path. |
| Character vocabulary | `wizard_avatar/models.py:18-75` and the 89-pose JSON | There are 10 expressions, 19 action IDs, and no production `dance` action or dance-named clip. Dance cannot be represented as already implemented. |
| Snapshot topology | `reference_avatar_pose_cells.json` | The 89 snapshots contain no populated cell `region` values. Generic upper-body, staff, or wing compositing is not currently truthful. |
| Prism clock | `src/pages/PrismDodecahedron/index.jsx:1141-1214,2858-2896` and `musicMotion.js:163-392` | One HTML audio element owns playback. `currentTime` is sampled in the analyzer. React metrics are throttled and are display state, not scheduler authority. |
| Prism lifecycle | `musicMotion.js:351-384` | Only `play`, `pause`, `ended`, and `loadedmetadata` are handled by the analyzer. Seek, rate, waiting, stalled, and post-buffer playing are absent from a connector contract. |
| Timed speech overlay | `index.jsx:2049-2104,2972-2985` | Caption tokens are distributed heuristically and scheduled with future `setTimeout` calls. This is not word alignment and is unsafe across seek/rate/background changes. |
| Prism player UX | `studio/StageUtilityCards.jsx:347-457` | Progress is a read-only meter. There is no seek, rate, stop, transcript, connector, motion-profile, or Whiz control. |
| Media metadata | `musicLibrary.js:33-77` and `src/lib/media-normalize.js:7-68` | Transcript URL can survive library normalization but is not consumed. Uploaded identity is random/session-local. Canonical external URL and performance identity are absent. |
| Reduced motion | `useReducedMotionPreference.js` and `usePrismScene.js:27-77` | Browser preference is observed by Prism, but no shared runtime profile reaches Python and continuous scene behavior is not comprehensively projected. |
| CI | PrismGT `.github/workflows/ci.yml` and `package.json` | Prism CI already builds the release sidecar before workspace tests, then runs frontend build and Rust checks. There is no JS unit, browser, accessibility, visual, cross-process, or evidence-bundle gate. Python has no repository CI workflow. |

The 89-pose asset library is stronger than its current runtime reachability. The first implementation value comes from executing a curated subset and the graph's declared policy, not from broad autonomous access to all poses.

## 3. Binding Conflict Resolutions

Where specialist recommendations differ, the following decisions govern implementation.

| Conflict | Decision | Reason and rejected alternative |
| --- | --- | --- |
| Milliseconds versus microseconds or audio samples as canonical time | Shared score, connector, editor, and review contracts use non-negative integer milliseconds with one documented nearest-millisecond conversion. DSP artifacts retain canonical sample indices and sample rate; derived events project to milliseconds. | Milliseconds already fit Prism captions, Rust/JS/Python interchange, and the required error budget. A top-level sample or microsecond time base adds cross-language complexity without improving visible 24 fps precision. Binary floating-point seconds are rejected as identity-bearing data. |
| Event stream versus full snapshots | Prism emits event-triggered full snapshots plus a coalesced 4 Hz heartbeat while actually playing. Every snapshot is independently sufficient. | Events are useful as `cause`, but replaying a missed event backlog is unsafe. Heartbeat-only delivery is too slow for pause/seek; event-only delivery lacks drift correction and restart recovery. |
| Connector latency thresholds | Loopback event-to-ack is p95 <= 25 ms and p99 <= 50 ms. Controlled steady-play cue-to-audio visible error is p95 <= 50 ms and max <= 100 ms. A seek must resolve the correct semantic target within 100 ms and may use up to 250 ms to complete a declared visible settle. | This reconciles the 25/50 ms transport gate, 50/100 ms synchronization gate, and 250 ms seek-settle recommendation by measuring different stages. |
| Speech-safe upper-body overlay versus atomic snapshots | Existing Wizard Joe art remains whole-body atomic. Speech-safe body acting uses curated full snapshots only when locomotion is settled and the phrase declares compatibility. Face and mouth may overlay declared anchors. Generic upper-body/staff/wing blending is forbidden until regioned assets exist and pass topology tests. | Zero authored cells have regions. Cutting snapshots by geometry would produce false limbs, prop discontinuity, and misleading capability claims. |
| Per-cell blend versus hard pose replacement | Use authored whole-pose phrase sequences: anticipation, stroke, hold, release, settle. A coherent hard cut is an explicit editorial transition with reason evidence. Never dissolve arbitrary cells. | Atomic presentation is correct for the art, but atomic presentation does not justify unperformed emotional or contact transitions. |
| Runtime random variation versus persisted takes | The compiler may use deterministic seeded selection to propose variants, but the accepted compiled score persists the selected family, variant/take, timing, and fallback. Playback makes no fresh creative choice. | Runtime random choice undermines review evidence. Always choosing the first node is deterministic but repetitive. Persisted takes provide both variation and reproducibility. |
| One score versus analysis, semantic score, and compiled score | Preserve three immutable levels plus an edit layer: analysis bundle, semantic performance score, character-compiled score, and append-only human edits. Playback accepts only a validated compiled revision. | Treating model output as executable collapses evidence, capability validation, and human authorship. Treating one compiled file as the only editable source makes character portability impossible. |
| LLM-required planning versus offline baseline | A deterministic no-model planner is required. Optional LLM passes may enrich narrative analysis and suggest semantic patches but never choose runtime commands directly. | Playback must work offline, generation is not reliably token-deterministic, and private manuscripts require an explicit provider boundary. |
| Music baseline dependency | Baseline uses pinned FFmpeg canonical decode, fixed-hop deterministic features, FFmpeg EBU R128, and pinned `librosa` analysis in an isolated authoring environment. Beat This! is an optional accuracy tier after corpus, packaging, model-hash, determinism, and license gates. All-In-One remains R&D only. | This minimizes the initial dependency and licensing surface while preserving an upgrade path. Essentia Meter, madmom, and aubio are not production defaults. |
| Existing assets as a complete dance library | Music mode initially supports section-aware, beat-locked performance phrases from truthful available capabilities. It is not called production dance until a package declares and validates dedicated dance clips and transitions. | The current action and pose inventory has no production dance action or dance clip. Staff spin, playful kick, runs, flight, and celebration are punctuation, not a complete dance vocabulary. |
| Fixed blink/gaze constants versus biological research values | Implement versioned art-directed distributions and protected windows, then tune from rendered evidence. Do not freeze study means as universal constants. | Stylized 5x2-cell eyes need readable intent, not anatomical simulation. Deterministic fixations and meaningful holds matter more than continuous micro-motion. |
| Ten-minute versus 15-minute review sample | The protected creative checkpoint is at least 15 minutes and includes the required 10-minute acting cases. It is followed by one complete chapter and a cross-chapter handoff. | Ten minutes can prove phrasing but not the full requested checkpoint; 15 minutes still cannot prove chapter continuity or habituation. |
| Editor before runtime versus runtime before editor | Build a read-only timeline/debug inspector with the evaluator, then a focused blocking/take editor after linear/seek parity is proven. Do not build a general NLE. | An editor over an unstable score or clock contract creates expensive rework. Human review still needs inspectable state before full editing lands. |
| Camera shot terminology | Use `setup` and `reframe` for screen-space position/scale. Use `shot` only when an actual camera/framing discontinuity exists and is capability-declared. | The current Wizard output has stage projection, not a camera API. Precise names prevent false capability claims. |
| Flaky frame deadline test | Replace scheduling logic proof with a fake-clock/cheap-frame unit test and keep a separate real-render benchmark. Do not lower the existing frame-count assertion or retry it green. | The existing path plus injected sleep cannot reliably fit the asserted frame count. The failure also exposes a real render budget problem. |

## 4. Performance Direction Contract

### 4.1 Editorial hierarchy

The accepted semantic score uses this hierarchy:

```text
book -> chapter -> scene -> beat -> setup -> phrase -> phase -> channel state
```

- A **beat** is a change in thought, tactic, information, relationship, or emotion.
- A **setup** is a stable stage arrangement and framing policy.
- A **phrase** is one motivated performance action.
- A **phase** is `anticipation`, `stroke`, `hold`, `release`, or `settle`.
- A **take** is a persisted alternative for a beat, setup, or phrase.

Each phrase records the media range, beat/setup IDs, intent, motivation enum, visual salience, source and destination stage marks when moving, selected family and take, amplitude band, complete or explicitly waived phases, minimum hold, interruption policy, cooldown class, channel ownership, required capabilities, fallback chain, reduced-motion projection, and provenance.

The pure evaluator receives an accepted score, integer media time, exact character capability digest, accessibility profile, and versioned resolution policy. It emits a complete desired state and reason trace. Linear playback at `t` and cold seek to `t` must resolve identically. Edge events are diagnostics only; they are not required to reconstruct state.

### 4.2 Visual budget and priority

The scheduler composes channels in this order:

1. safety, reset, reconnect, and accessibility projection;
2. manual director override;
3. full-body transition or action;
4. locomotion and support contact;
5. speech-safe body phrase when the package declares compatibility;
6. prop, wing, and effect state;
7. gaze, head, face, and brow/lid state;
8. mouth/viseme state;
9. optional cosmetic micro-reactivity that cannot alter authored state.

Default visual density descends in the opposite direction: mouth/face activity may be frequent, body gestures are sparse, locomotion is scene-level, setup/reframe changes are rarer, and magic/flight/celebration are peak punctuation.

For ordinary narration, calibration begins at 70-85 percent characterful neutral occupancy, at most one main pose change per thought unit, no immediate non-neutral gesture repeat, and no body phrase solely because a timeout expired. These are review starting points, not universal release constants. Fixture-specific approved limits take precedence.

### 4.3 Body, locomotion, and staging

The first autonomous audiobook allowlist is:

- `front_idle_wings`, with `front_idle` compatibility fallback;
- `front_greeting_wave_wings`;
- `front_thinking_hand_chin_wings`;
- `front_explaining_open_hand_wings`;
- `front_point_side_wings`;
- `front_explaining_both_hands_wings`;
- `front_sincere_hand_heart_wings`;
- existing `explaining` as a validated fallback.

Promotion requires an authored clip/phrase, minimum hold, legal exit, interruption policy, face compatibility, and final-resolution silhouette approval. Emotion `*_full` poses are sustained attitudes. `*_close` poses are intensity variants and do not imply a camera cut. Combat, magic, flight, fall, direct point, shush, flourish, and celebration remain reviewed punctuation.

Starts, stops, and turns become explicit mobility phases. A locomotion phrase must have a source mark, destination mark, reason, path policy, arrival facing, support/contact policy, and settle. The current `grounded_start`, `grounded_stop`, and `turn` metadata is not considered implemented until runtime selection reaches and performs it. New pivot/start/stop art follows a working phase evaluator and contact trace, not vice versa.

Named normalized stage zones begin with `off_left`, `left`, `center`, `right`, and `off_right`. Foreground/background zones are added only after scale, contact, caption exclusion, and viewport tests. Center or a modest rule-of-thirds mark is the narrator default. Profiles and rear views are motivated transitions, not routine speaker differentiation.

### 4.4 Facial, eye, blink, and speech performance

Add a deterministic face-event timeline whose timing derives from the accepted score and alignment, not renderer clocks. It owns:

- semantic gaze target and fixation range;
- saccade arrival and small head contribution;
- direct-viewer, referential, thought/recall, quoted-character, and release policies;
- blink event/type with minimum spacing and protected intervals;
- base expression plus transient attack/hold/release;
- brow/lid accents supported by the pose;
- mouth group, explicit silence, and optional viseme timing.

At Wizard Joe's resolution, intentional eye shifts arrive in one or two authored frames and then hold. No random eye darting occurs during a fixation. Blinks use a deterministic baseline hazard biased toward phrase/sentence pauses, gaze changes, and post-emphasis release. Strong expression apices and brief referential looks can suppress blinks. Rare double blinks are explicit scheduled events, not a random renderer behavior.

Replace the 10 Hz mouth oscillator in production audiobook mode. Timing-source precedence is:

1. provider-native alignment bound to exact audio bytes;
2. forced alignment of the approved transcript;
3. local ASR plus word alignment;
4. word/speech-activity and amplitude fallback;
5. duration-only cycle, visibly diagnosed as degraded mode.

Use a compact display vocabulary: rest/silence, closed bilabial, open, wide, rounded, optional labiodental when readable, and an affect overlay. Mouth closes in aligned silence and on interruption. Speech articulation does not erase affect, and expression transitions do not override mandatory closure.

Every pose that claims face support eventually declares face visibility, eye boxes/pupil slots, lid mask, mouth mask, occlusion state, and supported channels. Existing color inference remains compatibility behavior only. Absent metadata fails closed to the unchanged authored face.

### 4.5 Narrative timing rules

- A main pose changes because thought or story state changes, not because an emotion word appears.
- A readable stroke does not precede a spoiler-sensitive reveal. Non-spoiling anticipation may precede the apex.
- Comic setup stays neutral; any acknowledgment follows the payoff.
- Rising suspense usually reduces novelty and movement.
- Intimacy means reduced distance, contained motion, direct soft attention, and longer settle, not higher amplitude.
- Dense exposition receives fewer gestures as information load rises.
- Reflection protects silence and preserves the changed stance after realization.
- Technical room tone, breath, syntactic pause, suspense hold, scene break, and chapter boundary are distinct silence classes.
- The audio duration of silence is never shortened or filled with arbitrary animation.

### 4.6 Music performance direction

Music analysis produces a content-addressed sidecar with canonical PCM identity, fixed-hop energy/onset features, loudness, beat/downbeat candidates, section boundaries, confidence, tool/model/config hashes, and unknown states where evidence is weak. Browser `AnalyserNode` output remains a separately named cosmetic texture layer and never becomes the accepted beat grid.

The music compiler maps structure to phrases at multiple timescales:

- section: setup, stage zone, phrase family, and energy ceiling;
- bar: routine progression and recovery opportunity;
- beat/downbeat: selected accents only;
- onset/transient: cosmetic or small secondary accent under a strict density cap.

Every frame derives beat/bar/section phase from event timestamps and current media time. No beat phase accumulates from render deltas, `performance.now()`, or `setTimeout`. Pause, seek, rate, visibility recovery, and source replacement immediately recompute state.

The initial current-asset mode is called **music performance**, not production dance. It may use validated neutral, step/travel, playful kick, staff flourish, magic, flight, and celebration phrases only where the package marks them music-compatible. Repetition history, section changes, stage bounds, transition recovery, and reduced-motion projection are mandatory. Dedicated dance release requires new declared dance families with preparation, loop/bar fit, exit, contact, tempo range, directional coverage, and low-motion alternatives.

### 4.7 Accessibility projection

The accepted score is immutable across motion preferences. A deterministic runtime projection applies one of:

| Profile | Required behavior |
| --- | --- |
| `full` | Approved performance under global flash and safety gates. |
| `reduced` | No locomotion, dance, flight, camera/depth motion, spin, scale pulse, rapid turn, or audio-reactive whole-body motion. Timing is preserved with stable poses, holds, restrained face/mouth, and captions/transcript. |
| `still` | Stable representative pose. Audio, transport, captions, transcript, processing, Whiz, and editor remain fully operable. |
| `system` | Resolves to platform preference before the first cue and reacts during playback. Explicit full-motion override must be user chosen. |

Per-channel overrides cover locomotion, dance, generated gesture, face, and eye motion. Reduced motion wins cross-application conflicts. Profile changes do not restart audio, regenerate a score, move focus, or lose edits.

## 5. Explicit Wave Plan

Each wave has one accountable lead. File ownership is exclusive within a wave; work may be parallel only across disjoint modules and fixtures. A wave is complete only when its listed evidence exists.

### Wave C0: Freeze Gates and Evidence Foundations

**Lead:** QA/verification owner
**Depends on:** frozen baselines only
**Blocks:** all expressive implementation

**Work:**

- Create redistribution-safe synthetic audio, alignment, narrative, music, seek/rate, reduced-motion, and malformed fixtures with hashes.
- Define the evidence manifest, normalized replay format, stable error taxonomy, waiver format, and cross-repository run identity.
- Replace the stream scheduling proof with a fake-clock/cheap-frame test; add a separately instrumented real-render benchmark.
- Add Python CI and extend Prism CI without removing its existing sidecar-before-workspace-test order.
- Establish the human review rubric and review-note identity (`media hash`, `score hash`, `run ID`, range/frame hash).

**Owned areas:** Python tests/CI/evidence scripts; Prism test configuration and CI; shared fixture directory selected by the schema owners. Do not alter runtime behavior in this wave.

**Acceptance:**

1. Fake-clock scheduling test passes 100 consecutive runs without retry or sleep-based assertions.
2. Real renderer reports compose, encode, hash, and queue phase percentiles; no result is hidden by aggregate timing.
3. Both commits, dirty states, lock hashes, tool versions, commands, fixture hashes, and artifact checksums appear in one evidence manifest.
4. CI uploads JUnit, contract results, replay hashes, privacy scan, and browser traces on failure.
5. Every skip/quarantine has owner, issue, reason, and expiry; the known deadline issue remains release blocking until its benchmark gate passes.

### Wave C1: Capability and Editorial Contracts

**Lead:** Character TD, with animation director approval
**Depends on:** C0 fixtures and evidence format; cross-synthesis media/score schema decision
**Blocks:** scheduler compilation and autonomous acting

**Work:**

- Define structured package/capability/mapping/fallback and named coordinate-space contracts.
- Define phrase phases, channel precedence, stage marks/setups, face support, accessibility projection, compiled take, and fallback record.
- Generate a truthful Wizard Joe capability census from actual graph/assets, marking fields operative or advisory.
- Promote only the curated audiobook vocabulary through authored clips and explicit policy.
- Create one deliberately different valid second-character fixture with no staff/wings and a smaller action set.

**Owned Python areas:** `character_package.py`, package schemas/definitions, graph capability audit tooling, new semantic-rig/capability modules, and dedicated tests. Graph runtime execution remains C2 ownership.

**Acceptance:**

1. Strict startup validation rejects hash mismatch, duplicate ID/version, missing required anchor, invalid fallback termination, and unsupported region claims.
2. Capability query reports exact facings, channels, overlays, quality tier, fallbacks, and package digest.
3. Existing Wizard art declares whole-body snapshot ownership; no generic upper-body layer is advertised.
4. The second character compiles the shared score without Python conditionals and emits expected fallback records.
5. Every autonomous Wizard pose has a family role, phrase/clip, hold, legal exit, interruption policy, face compatibility, and creative approval.

### Wave C2: Media-Time Evaluator and Phrase Runtime

**Lead:** Runtime/synchronization engineer
**Depends on:** C1 contracts; connector snapshots and accepted compiled-score identity from the integration/schema workstreams
**Blocks:** facial polish, music autonomy, editor approval

**Work:**

- Implement pure state-at-time evaluation and interval lookup outside the 1,024-command inbox.
- Add media session/generation/sequence/runtime-epoch reconciliation at Python tick boundaries.
- Execute node, phrase phase, holds, markers, interrupt gates, legal successors, contact/root policy, and explicit fallback in one evaluator.
- Keep snapshots atomic and add contact-preserving whole-pose handoff/root correction where authored metadata supports it.
- Implement bounded lookahead for preload and preparation only; never enqueue a chapter.
- Add read-only diagnostics for active hierarchy, phrase/phase/take, media time, drift, package/score hashes, suppression, fallback, and acknowledgement.

**Owned Python areas:** new score evaluator/scheduler/media-session modules, `animation_graph.py`, `pose_selection.py`, `runtime.py`, `stream.py`, `server.py`, diagnostics, and focused tests. Legacy WebSocket hardening is a separate security fix but must land before any browser can use it.

**Acceptance:**

1. Linear playback and cold seek match at 1,000 deterministic random media times, including frame hashes after declared settle.
2. Pause, buffering, seek, rate, chapter/track change, reconnect, and restart apply no stale old-generation cue.
3. Every changed body pose has an active phrase/transition or approved coherent-cut reason.
4. Every locomotion phrase has source/destination/reason/facing/contact/settle; free roaming fails validation.
5. Identical media, score, package, policy, seed, and transport trace produce byte-identical normalized cue decisions, dispositions, state hashes, and sampled frame hashes in two fresh processes.
6. The command inbox never exceeds its horizon/capacity in a one-hour sparse-score stress run.

### Wave C3: Audiobook Body and Facial Performance

**Lead:** Supervising animation director; implementation leads are character animator and face specialist
**Depends on:** C2 state evaluator; accepted alignment/speech track from the speech workstream
**Blocks:** creative audiobook approval

**Work:**

- Author and tune characterful neutral, thought, explain, reference, sincere, greeting, and emotion phrases.
- Add gesture history, cooldown, no-gesture weighting, emotional hysteresis, and chapter continuity checkpoints to compilation policy.
- Implement start/stop/turn phases and only then identify required new pivot/contact art.
- Implement deterministic gaze/fixation, eye-head contribution, blink scheduling, expression envelopes, pose face metadata, and aligned mouth groups.
- Add quiet suspense, comedy, intimacy, exposition, reflection, dialogue, action, and chapter-handoff fixtures.

**Owned areas:** animation mappings/graph clips/pose metadata, face planner/quantizer, mouth mapping, creative fixtures, and browser-scale review outputs. Do not edit connector or ingestion internals.

**Acceptance:**

1. Active speech reaches approved body phrases only while compatibility permits and never steals locomotion/contact ownership.
2. Mouth is closed in all aligned silence and interruption windows; no production sample exposes the fixed 10 Hz oscillator.
3. No fixed-period blink loop, random eye dart, pre-reveal spoiler reaction, immediate non-motif gesture repeat, or unsupported face overlay occurs.
4. Silhouette-only review distinguishes neutral, explain, point/reference, think, sincere, quiet, guard, and celebrate at final output size.
5. Contact trace stays inside the approved cell threshold through start, walk, stop, turn, gesture, and recovery fixtures.
6. A 15-minute representative checkpoint passes full-speed and diagnostic review; a complete chapter and cross-chapter handoff pass continuity review.

### Wave C4: Music Analysis and Performance

**Lead:** Audio DSP/music engineer; creative approval by animation director
**Depends on:** C2 evaluator, C1 capability truth, deterministic DSP sidecar and media identity from processing workstream
**Blocks:** any music/dance release claim

**Work:**

- Build isolated pinned FFmpeg/librosa baseline analysis with canonical PCM and loudness provenance.
- Consume beat/downbeat/onset/section/envelope state from media time at every evaluation.
- Compile section/bar/beat-scale phrases using only declared music-compatible capabilities.
- Add deterministic anti-repeat, stage bounds, transition recovery, and `reduced`/`still` projections.
- Evaluate Beat This! as an optional tier. Commission/author dedicated dance clips only after current-asset evidence identifies the actual gaps.

**Owned areas:** isolated music-analysis tool, sidecar schema adapter, music compiler/mappings, music fixtures, and music evidence. Browser live analyzer remains cosmetic and separate.

**Acceptance:**

1. Clean-process baseline analysis is byte-identical for canonical inputs; model tiers meet their declared tolerance and record model hashes.
2. 30/60/120/irregular render schedules choose identical beat/bar/section events at the same media times.
3. Pause, seek, rate, and background recovery never replay pulses or preserve history-dependent normalized state.
4. Low-energy, high-energy, breakdown/drop, ending, sparse/rubato, speech-over-music, and ambiguous-meter fixtures use confidence/unknown correctly.
5. Reduced mode dispatches zero dance, flight, spin, depth, scale-pulse, or audio-reactive whole-body cues.
6. The release is labeled `music performance` until dedicated dance families pass clip, contact, tempo, transition, repetition, and creative gates.

### Wave C5: Focused Previs, Player, and Accessibility UX

**Lead:** PrismGT UX/previs owner; accessibility reviewer has release veto
**Depends on:** C2 evaluator and diagnostics; connector/player lifecycle integration; transcript and score revisions available
**Blocks:** editor, accessibility, and operator completion

**Work:**

- Add complete seek/rate/stop/chapter transport against the real audio element.
- Add persistent transcript with search, cue seek, follow toggle, status/revision, and caption controls.
- Add read-only waveform/transcript/score diagnostics first, then blocking, phrase handles, take compare, track mute, score diff, semantic cue table, and immutable edit overlay.
- Add runtime motion profile and per-channel controls, flash analysis, focus contracts, contrast/target tokens, responsive/zoom behavior, and structured processing status.
- Add governed Whiz state and preserve playback state across external opening.

**Owned Prism areas:** `index.jsx` adapters/hooks, new focused editor modules, player components, media normalization display fields, accessibility components/styles, and browser tests. Keep editorial data out of the Three.js scene implementation.

**Acceptance:**

1. Keyboard and VoiceOver can play/pause/stop/seek/change rate/change chapter/use captions/use transcript/change motion profile/use Whiz/edit/save without pointer or canvas dependence.
2. Timeline scrub/step/loop reconstructs state; skipped cues do not fire.
3. Locked cues survive regeneration; compatible edits rebase and conflicts are explicit.
4. Full to reduced to still applies within 250 ms with continuous audio, stable focus, and no regeneration.
5. Chromium/WebKit axe runs have zero serious/critical findings; manual macOS VoiceOver, Reduce Motion, Increase Contrast, and 200 percent zoom checklists are signed.
6. Every shipped/generated visual sample passes the flash gate at the largest supported presentation.

### Wave C6: Release Candidate and Handoff

**Lead:** Program coordinator; joint signoff by animation, audio, accessibility, QA, Python, and PrismGT owners
**Depends on:** C0-C5 complete; all cross-synthesis implementation waves complete
**Blocks:** production-ready claim

**Work:**

- Run the installed/package-integrated applications on reference hardware.
- Execute full synchronization, failure injection, privacy canary, egress-denied, browser, installed-app, performance, and soak suites.
- Produce audiovisual proxies with and without diagnostic burn-ins, contact sheets, state/event traces, review notes, and checksums.
- Verify documentation, reproduction, migration, rollback, another-character workflow, and exact known limitations.

**Acceptance:** all completion criteria in section 10 pass for the same two candidate commits and packaged build. There are zero unresolved P0/P1 defects, expired waivers, known flaky blocking tests, or unsupported production claims.

## 6. Ownership and Integration Boundaries

| Boundary | Accountable owner | May change | Must not absorb |
| --- | --- | --- | --- |
| Media/transcript/music authoring artifacts | Speech/DSP owners | Offline tools, provenance, alignment/music sidecars | Avatar render loop, Prism visual advisory |
| Semantic score and edits | Narrative/planning owners | Analysis bundle, semantic tracks, immutable edits | Character clip IDs or live commands |
| Character compilation | Character TD/runtime owners | Capability resolution, take persistence, fallback, preload | Manuscript interpretation or provider calls |
| Phrase runtime | Python runtime owner | State-at-time, graph phases, media reconciliation, commands | Independent media clock or media bytes |
| Character art direction | Animation/face owners | Graph clips, pose metadata, mapping policy, review fixtures | Connector transport or media storage |
| Media player/connector | Prism integration owner | Audio-element adapter, same-origin relay, player state | Animation selection or transcript text in connector |
| Editor/accessibility | Prism UX owner | Timeline/table, controls, focus, transcript, profiles | Three.js ownership of canonical score |
| CI/evidence | QA owner | Gates, fixtures, manifests, fault tools, review bundles | Weakening behavior to make a test pass |
| Creative release | Animation director | Acting, timing, staging, repetition, appeal approval | Waiving technical/privacy/accessibility hard fails |
| Production release | Program coordinator | Candidate freeze, cross-owner signoff, handoff | Calling partial evidence complete |

Schema changes require the schema owner plus every consuming-language owner. A producer may not modify another subsystem's schema copy independently. Golden fixtures are the compatibility authority.

## 7. QA and Acceptance Gate Stack

### 7.1 Pull request gates

- Python full unit suite, fake-clock scheduler, graph/phrase properties, deterministic replay, face/mouth invariants, capability/fallback, privacy redaction, and shared contracts.
- Rust format/check/clippy/tests, connector route/auth/governance, generation publication, and shared contracts.
- JavaScript lint/type-check when adopted, unit tests for player reducer/URL/motion profile/score view, production build, Chromium/WebKit smoke, axe, and deterministic screenshots.
- Short synthetic cross-process play/pause/seek/rate/buffer/reconnect run with a synchronization summary.
- Manifest, JUnit, normalized replay hashes, privacy scan, checksums, and failure traces uploaded on success and failure.

No deterministic test passes by retry. No screenshot baseline is updated without review. No waiver lacks owner, issue, reason, and expiry.

### 7.2 Nightly gates

- Full failure-injection matrix: drop/delay/duplicate/reorder, process kill/restart, stale score, corrupt cache, disk failure, provider denial, background/foreground, and sleep/wake.
- One hundred scheduler/deadline stress runs.
- Full rate/seek matrix in Chromium and WebKit.
- Two-hour portable-CI soak, visual suite, dependency/license scan, egress-denied privacy run, flash analysis, and cross-language canonical hash vectors.

### 7.3 Release-candidate gates

- Installed Tauri app driving the actual Python service.
- Fifteen-minute acting checkpoint, complete chapter, cross-chapter handoff, and all music fixtures.
- Reference-hardware renderer/connector benchmarks and 8-hour soak.
- Kill/restart, token rotation, offline, sleep/wake, and reconnect recovery.
- Manual full-speed and frame-by-frame animation review, VoiceOver/keyboard/zoom/motion review, caption/transcript review, and privacy/governance review.
- Signed/notarized and attested artifacts where distribution requires them.

### 7.4 Quantitative release thresholds

| Measure | Gate |
| --- | --- |
| Loopback snapshot event to Wizard ack | p95 <= 25 ms; p99 <= 50 ms |
| Steady cue-to-audio visible error, 0.5x/1x/1.25x/1.5x/2x | p95 <= 50 ms; max <= 100 ms over 15 minutes per rate |
| Pause response | No media-derived advance more than one 24 fps frame, 42 ms, after pause observation |
| Resume | Correct score state within 100 ms; no pre-pause one-shot replay |
| Seek | Correct target on first post-seek update and <= 100 ms; declared settle complete <= 250 ms; zero stale actions |
| Reconnect | Loopback reconnect <= 2 s; after accepted snapshot, <= 100 ms sync error within 500 ms |
| Renderer, 24 fps reference profile | p95 <= 33.3 ms; p99 <= 41.7 ms |
| Browser main thread | No connector/scheduler long task > 100 ms in 15-minute matrix |
| Soak | 8 hours; zero unexpected exceptions/reconnects/stale cues; queue bounds respected |
| Memory after 30-minute warm-up | RSS growth <= 64 MiB total and fitted growth <= 1 MiB/hour |
| Determinism | Byte-identical normalized cue, ack/disposition, state, sampled-frame, and final manifest hashes across fresh processes |
| Privacy local mode | Zero non-loopback connections and zero seeded canary leakage outside the approved source artifact |
| Flash safety | Zero WCAG 2.3.1 general/red-flash violations in shipped/generated visual samples |

Thresholds must name machine, OS, power mode, browser, Python, Node, Rust, FFmpeg, package/model versions, viewport, and render profile. Portable CI proves correctness; reference hardware owns performance release.

## 8. Creative Review and Hard Fails

Use the narrative report's 0-4 rubric for meaning fidelity, arc, narrator continuity, dialogue clarity, genre/beat timing, silence, restraint, synchronization, recovery, and accessibility. A production candidate needs a weighted score of at least 3.0 with no category below 2.5, but the following fail regardless of score:

- contradiction, editorialization, stereotype, or altered narrative implication;
- visible reaction before a spoiler-sensitive reveal;
- mouth motion in aligned intentional silence;
- high-salience gesture without an approved semantic beat;
- pose change without phrase/transition/coherent-cut evidence;
- unmotivated locomotion or setup change;
- random eye darting, mechanical blink recurrence, or unresolved gaze target;
- foot/root/staff contact discontinuity above the approved threshold;
- repeated motion that draws reviewer attention away from the story;
- nondeterministic replay, stale seek/reconnect state, or wrong chapter continuity;
- undeclared fallback, unsupported capability, or hidden degraded mode;
- accessibility motion/flash hard fail, privacy leak, or ungoverned external action.

Creative review must compare: neutral baseline, proposed restrained performance, and deliberately overactive control. Review audio-only first, then audiovisual full speed, then diagnostic/frame-by-frame. Human-likeness and appropriateness to the specific speech are scored separately.

## 9. Evidence Package

Every protected run publishes an immutable redacted bundle:

```text
qa-evidence/<run-id>/
  manifest.json
  SHA256SUMS
  contracts/
  junit/
  transport/events.ndjson
  transport/acks.ndjson
  scheduler/decisions.ndjson
  replay/inputs-manifest.json
  replay/hashes.json
  sync/summary.json
  performance/phase-histograms.json
  privacy/egress-summary.json
  privacy/canary-scan.json
  governance/receipts.ndjson
  browser/traces/
  browser/screenshots/
  browser/videos/
  accessibility/
  creative/review-overlay.webm
  creative/contact-sheet.png
  creative/review-notes.json
```

The manifest binds both commits and dirty states, workflow/run identity, UTC range, hardware/software versions, lockfiles, exact commands/exit codes, fixture hashes, media/alignment/score/package/graph/policy hashes, seed, viewport/FPS/rate, discontinuity events, test counts, waivers, and every artifact hash.

Evidence must never contain copyrighted source audio, manuscript/transcript bodies, user paths, secrets, provider payloads, raw unredacted HAR, or URL query text. Synthetic fixtures and content-free hashes/summaries are publishable. Reviewer notes bind to immutable media range, score hash, run ID, and optional frame hash; stale notes remain visibly stale.

## 10. Completion Definition

The program may state **production-ready audiobook performance and PrismGT media companion** only when all of the following are true for the same frozen candidate revisions and packaged build:

1. Strict cross-language media, score, package, connector, fallback, motion-profile, and evidence contracts agree on all golden fixtures and fail unknown versions closed.
2. Imported or generated media has stable content identity; transcript/alignment/music/score generations are complete, hash-valid, atomic, versioned, editable, and provenance-bearing.
3. The HTML media element is the sole playback authority through play, pause, resume, stop, seek, chapter/track change, rate, buffering, background/foreground, sleep/wake, reconnect, and either-app restart.
4. Linear playback and arbitrary seek resolve the same accepted character state, and all timing thresholds pass at every supported rate.
5. Wizard Joe performs purposeful neutral, stillness, speech, thought, gesture, emotion, locomotion, start/stop/turn, entrance/exit, and chapter continuity through executed phrases and explicit fallbacks.
6. Eye focus, gaze return, blink timing, expression envelopes, head-eye coordination, mouth silence/closure, and speech timing pass machine invariants and human readability review.
7. Music uses deterministic offline analysis and media-time phase; section-aware performance passes low/high/drop/ending/ambiguous fixtures. A production dance claim additionally has validated dedicated dance families.
8. Reduced and still projections, per-channel controls, flash safety, complete player/transcript UX, keyboard operation, VoiceOver, contrast, target, responsive, and zoom gates pass.
9. Whiz opens only a stored, revalidated canonical HTTP(S) destination for an applicable song/video after explicit activation, with disabled/error states and a content-free governed receipt.
10. Two fresh-process runs produce identical normalized decisions, acknowledgements, state hashes, sampled frame hashes, and final manifest hash.
11. Full failure injection, privacy canary, egress-denied, browser, packaged-app, performance, and 8-hour soak gates pass.
12. The 15-minute checkpoint, complete chapter, cross-chapter handoff, and required audiobook/music genres have signed animation, audio, accessibility, and QA approvals.
13. Existing Python behavior and PrismGT behavior remain covered; no test was weakened, retried green, or silently removed.
14. A second materially different character runs the shared score through declared mappings/fallbacks without production code changes.
15. Another engineer can reproduce, inspect, edit, migrate, deploy, roll back, and add a character or animation from exact documentation.
16. The final evidence bundle is complete, redacted, checksummed, and bound to the distributed artifacts.
17. There are zero unresolved P0/P1 defects, known flaky release-blocking tests, expired waivers, silent fallbacks, or capabilities described as complete without evidence.

If any item is absent, the direct status is **experimental integration** or **partially achieved**, with the missing gate and owner named. A green build, a model-generated score, an attractive short clip, or a synchronized happy path does not satisfy completion.

## 11. Principal Risks and Exit Conditions

| Risk | Owner | Early indicator | Required control | Exit evidence |
| --- | --- | --- | --- | --- |
| Dual-clock drift | Runtime/integration | State differs after seek/rate/background | Media snapshots, epochs, pure evaluator, no timer authority | Full rate/seek/reconnect matrix passes |
| Transition metadata remains decorative | Runtime/character TD | Transition ID changes with immediate pose snap | One executable phrase/graph evaluator | Phase/marker/contact tests and visual trace pass |
| Speech-safe acting breaks anatomy or motion | Character TD/animation | Detached prop/limb, root jump, locomotion steal | Whole-snapshot policy until region data exists | Final-size contact/silhouette evidence |
| Overperformance and pose roulette | Animation director | Low neutral occupancy, repeat clusters, listener distraction | Persisted takes, budgets, cooldown, no-gesture default | Long-form rubric and density report pass |
| Mechanical face | Face specialist | Periodic blinks, mouth chatter, unreadable gaze | Narration-aware face timeline and pose metadata | Audio trace plus human decoding review |
| Music is mislabeled dance | DSP/animation | Same flourish/kick repeats across sections | Truthful capability label and dedicated art gate | Music fixtures pass; dance family gate if claimed |
| Renderer misses 24 fps budget | Python performance owner | p99 > 41.7 ms, deadline drops | Phase profiling, cache/preload, decouple expensive work as needed | Reference benchmark and 8-hour soak pass |
| Score/model false determinism | Planning/QA | Fresh generation differs while called reproducible | Cache artifact reproducibility versus generation traceability | Canonical cache and fresh-run report distinguish both |
| Private content leaks through evidence/connector | Security/QA | Canary in log/HAR/bundle or non-loopback traffic | Allowlists, redaction, egress denial, content-free connector | Zero-canary/zero-egress gates pass |
| Accessibility is CSS-only | UX/accessibility | Reduced preference still dispatches body/camera motion | Shared runtime motion projection and flash gate | Motion, flash, VoiceOver, zoom evidence passes |
| Editor grows into an NLE | Product/previs | Runtime correctness delayed by UI scope | Read-only inspector, then focused blocking/takes only | Core evaluator gates precede editor milestones |
| Two repositories drift contract copies | Schema/QA | Same fixture accepted differently | Shared golden fixtures and version policy | Python/JS/Rust parity gate passes |
| Incomplete generation publication | Prism storage owner | Mixed audio/caption/score revisions after fault | Generation directory atomic promotion and prior pointer | Fault-at-every-write test passes |
| Weak CI proves only compilation | QA | No browser, replay, privacy, or evidence artifacts | PR/nightly/RC gate stack | Protected checks and bundles exist |
| New character reveals Wizard-specific assumptions | Character TD | Missing staff/wings crashes or silently idles | Structured mappings and terminal stillness fallback | Materially different second-character suite passes |

## 12. Immediate Start Order

The first implementation pull requests should be small and dependency-revealing:

1. C0 synthetic fixture/evidence manifest plus fake-clock deadline test and render benchmark.
2. C1 generated Wizard package capability audit and strict fallback diagnostics, with no behavior change.
3. Shared integer-millisecond time and compiled phrase golden fixtures across Python, Rust, and JavaScript.
4. C2 pure score state-at-time evaluator tested without networking or rendering.
5. Neutral-only media-session reconciliation from the real Prism audio element to Python.
6. Executed characterful-neutral and one explain phrase with full replay/evidence.
7. Aligned silence/word mouth track plus one deterministic gaze/blink fixture.
8. Fifteen-minute blocking score before broad pose autonomy, music choreography, or full editor construction.

This order exposes contract, timing, capability, and performance-cost failures while changes are still cheap. It also creates an inspectable vertical slice early: real audio clock, accepted score, neutral/one phrase, deterministic seek, and complete evidence.
