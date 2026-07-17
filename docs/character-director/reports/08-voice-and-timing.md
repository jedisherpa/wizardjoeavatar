# Voice and Timing Engineer Report

## Scope and evidence boundary

Role: Voice and Timing Engineer.

This report independently audits the actual voice, timing, and media-clock path across:

- Python baseline `556701a` in `WizardJoeAvatar-python`
- Prism connector baseline `189fbab` in `prism-geometry-talk-persona-visuals`
- Canonical connector document `docs/audiobook-performance/LOCAL_PRISMGT_AUDIO_CONNECTOR.md`

The audit covers TTS and speaker integration, alignment metadata, main and speech audio clocks, progressive text, media-session snapshots, pause/seek/rate/reconnect behavior, mouth cues, and fallback paths. Other specialist reports were not read. No runtime code, tests, manifests, existing documentation, or generated artifacts were modified.

Classification terms:

- **Implemented**: the inspected code provides the behavior on the traced path, with relevant focused tests where noted.
- **Partial**: some required mechanics exist, but a material path, binding, or end-to-end guarantee is absent.
- **Missing**: no production path implementing the required behavior was found, or the two sides of the protocol are incompatible.
- **Unverified**: code or documentation suggests behavior, but no current live cross-process or packaged-runtime evidence establishes it.

## Executive finding

The authoritative clock must be the `currentTime` of the HTML media element that is actually audible: Prism's main audio element during audiobook playback and Prism's speech audio element while element-backed speech is audible. Python's monotonic clock is valid only as a short interpolation clock between accepted snapshots. The 60 Hz simulation clock, transcript timers, and synthetic mouth timers must never become media authority.

That architecture is present for main audiobook playback but is not complete for voice output. On ordinary non-touch desktop, Prism attempts Web Audio playback before element playback. Browser speech synthesis and the synthetic speech fallback also bypass the speech media element. Those paths therefore have no speech-element clock to publish, so the connector can continue reporting the main track while another path is audible. The canonical document's statement that TTS and speaker output are represented by a real speech media element is not true for every inspected production path.

A second authority break occurs after scheduling: `PerformanceApplication` can resolve a mouth shape from media time, but `_reference_mouth_shape` can replace it with a simulation-time cycle whenever the action is `speaking`. Consequently, a semantically correct media state does not guarantee a media-synchronous rendered mouth.

## Capability classification

| Capability | Classification | Evidence summary |
| --- | --- | --- |
| Main audiobook element clock | Implemented | Prism snapshots sample the active main element's `currentTime`; Python interpolates accepted playing snapshots. |
| Speech element clock | Partial | Element-backed speech is tracked, but primary desktop Web Audio, browser TTS, synthetic speech, CLI voice, and direct speaker playback bypass it. |
| Strict media-session protocol | Implemented | Source kinds, lifecycle states, sequence, epoch, duration, rate, and sampled time are validated on both sides. |
| Active-source priority | Partial | Speech-over-main policy exists. Exact Python baseline mishandles paused speech handoff; current Python contains a later fix, not yet verified end to end. |
| Pause behavior | Partial | The semantic scheduler stops applying performance for non-playing state, but final mouth rendering can still use an independent simulation clock. |
| Seek behavior | Partial | Seek events and hard reconciliation exist; no live cross-process proof meets the documented 100 ms and 250 ms gates. |
| Playback-rate behavior | Partial | Fixed rates are validated and interpolated correctly in unit tests; no live UI path or cross-process drift evidence was found. |
| Automatic reconnect | Missing | Python's control ACK identifies the prior accepted cursor while Prism requires it to identify the submitted snapshot, preventing the reconnect handler from running. |
| Alignment artifact contract | Implemented | Python defines a strict word/punctuation/silence schema; Prism can retain ElevenLabs character timing and project VTT cues. |
| Runtime alignment consumption | Missing | No production Python adapter consumes `alignment.units`; Prism's character timing is not delivered to the connector or mouth scheduler. |
| Progressive speech text | Partial | Text reveals concurrently with speech using heuristic token delays, not the audible speech clock or provider alignment. |
| Audiobook timed text | Partial | VTT cue selection is main-audio driven, but intra-cue token pulses are weighted estimates over coarse cues. |
| Mouth cues | Partial | Scoreless media-time cycling exists, but it ignores silence/envelope data and can be overridden by simulation-time rendering. |
| Compiled score runtime binding | Missing | Score contracts and loaders exist, but the production `PerformanceApplication` is constructed without a score or score resolver. |
| Fallback behavior | Partial | Several fallbacks preserve output, but they use inconsistent timing sources and are not marked as degraded synchronization. |
| Drift observability | Partial | ACK latency and snapshot age are visible; accepted `clock_error_ms` and rendered cue-to-audio error are not exposed. |
| Packaged desktop behavior | Unverified | No installed Prism application or live Python connector was exercised for this report. |

## Actual clock and audio flow

### Main audiobook path

1. Prism's main `HTMLAudioElement` is held in `audioRef`.
2. `createMediaSessionSnapshot` samples `audio.currentTime`, duration, rate, paused/ended/seeking state, and ready state.
3. `useMediaSessionConnector` emits lifecycle snapshots and a 250 ms heartbeat while the selected source is playing.
4. Rust `MediaConnector::relay` forwards snapshots to Python with one request in flight and one latest pending snapshot.
5. Python's `MediaSessionCoordinator` accepts the snapshot and selects the active source.
6. `MediaClockEstimator.position_at` advances a playing snapshot from its local receipt time, capped by the 1.5 second freshness window.
7. `PerformanceScheduler.resolve` evaluates either a compiled score or scoreless fallback at that estimated media time.
8. `PerformanceApplication.apply` maps the resolved state into avatar state.

This is the intended authority chain. The browser element remains authoritative; Python only estimates between observations.

### Speech path

The tracked path is `speechAudioRef` -> `playCdissAudioElement` -> speech lifecycle snapshots -> speech priority in Python. However, `playCdissAudio` prefers `playCdissAudioBuffer` on clients for which `prefersElementSpeechPlayback()` is false. That function uses an `AudioContext` buffer source, not `speechAudioRef`. The subsequent fallbacks use `speechSynthesis` and `driveSyntheticSpeech`, also without a tracked media element.

Rust-side direct voice output has the same boundary problem. `Voice::speak_with_voice` invokes `say`, Piper followed by `afplay`, or ElevenLabs followed by `afplay`. Those outputs do not pass through the browser speech element. `Voice::synthesize_with_voice` does return bytes for the browser `/api/tts` path, but the browser may still choose Web Audio instead of element playback.

No production publisher of connector snapshots with `source_kind: "speaker"` was found. The enum value is a protocol capability, not evidence of an operational speaker clock.

### Clock precedence

Required precedence is:

1. Audible speech `HTMLMediaElement.currentTime`, when speech is element-backed and audible.
2. Main audiobook `HTMLMediaElement.currentTime` otherwise.
3. Python receipt-monotonic interpolation for no more than 1.5 seconds after the last accepted playing snapshot.
4. Hold the last resolved semantic state when freshness expires, without continued media interpolation.
5. Duration-only or scoreless fallback only when explicitly classified as degraded and never represented as alignment-synchronous.

`sampled_at_monotonic_ms` cannot directly compensate transit time across Prism and Python because the processes do not share a demonstrated monotonic origin. Receipt-time interpolation is conservative. A protocol extension would need an explicit clock-offset/round-trip method before client sample time could safely affect the estimated position.

## Detailed findings

### VT-01: Audible desktop speech can bypass the connector clock

**Classification: Partial. Severity: Critical.**

Evidence:

- `src/pages/PrismDodecahedron/index.jsx@189fbab`
  - `prefersElementSpeechPlayback`
  - `playCdissAudioBuffer`
  - `playCdissAudioElement`
  - `playCdissAudio`
  - `speakCdissReply`
  - `speakWithBrowserTts`
  - `driveSyntheticSpeech`
- `crates/prism-cdiss-cli/src/voice.rs@189fbab`
  - `Voice::speak_with_voice`
  - `Voice::synthesize_with_voice`
- `crates/prism-cdiss-cli/src/web.rs@189fbab`
  - `tts`

`playCdissAudio` attempts Web Audio first unless the touch-oriented element preference returns true. Web Audio has no `HTMLAudioElement.currentTime`, and none of browser TTS, synthetic speech, `say`, or `afplay` is represented by a speech media-session snapshot. Main audio can therefore remain selected while untracked speech is audible. The packaged macOS/Tauri result of `prefersElementSpeechPlayback()` is **Unverified**, but the bypass paths themselves are explicit.

Recommended change:

- When the local connector is enabled, route synthesized reply bytes through `playCdissAudioElement` so the audible object and published clock are the same object.
- Treat Web Audio, browser TTS, synthetic speech, and direct OS speaker output as degraded unsynchronized fallbacks unless they gain an observable clock that satisfies the same contract.
- Do not emit an artificial `speaker` snapshot unless its position is sampled from the object actually producing sound.

### VT-02: Final mouth rendering can discard media-time mouth state

**Classification: Partial. Severity: Critical.**

Evidence:

- `wizard_avatar/media_session.py@556701a`
  - `PerformanceScheduler._scoreless_state`
- `wizard_avatar/performance_application.py@556701a`
  - `PerformanceApplication.apply`
  - `PerformanceApplication._resolve_action`
- `wizard_avatar/frame_source.py@556701a`
  - `_reference_mouth_shape`
- `wizard_avatar/layers.py@556701a`
  - speech fallback mouth selection
- `wizard_avatar/mouth.py@556701a`
  - fallback mouth cycle
- `wizard_avatar/performance_compiler.py@556701a`
  - `_duration_only_mouth_shape`

The scoreless scheduler chooses a mouth from media time in 120 ms phases. `PerformanceApplication` maps that value into avatar state, but `_reference_mouth_shape` returns its own `state.time_seconds * 10` cycle whenever the action is `speaking` or a speech ID is set. This introduces a simulation-clock override after the media scheduler. Other fallback modules use additional fixed cycles, including a separate duration-only profile.

The result can change after a pause, seek, rate change, or cold-state reconstruction even when the scheduler resolves the same media time. Existing semantic tests do not prove rendered-mouth equivalence.

Recommended change:

- When media performance owns the avatar state, render `state.mouth` without replacing it from `state.time_seconds`.
- Use one explicit fallback profile only when no timed mouth track is available.
- Compile silence intervals into closed-mouth cues and provider word/phoneme or audio-envelope timing into mouth cues.

### VT-03: Alignment data does not reach the live scheduler

**Classification: Missing. Severity: High.**

Evidence:

- `schemas/alignment_v1.schema.json@556701a`
  - `AlignmentV1` artifact fields for media binding, PCM binding, transcript binding, timed units, silence, engine, and QA
- `crates/prism-cdiss-cli/src/audiobooks.rs@189fbab`
  - `ElevenLabsAlignment`
  - audiobook generation endpoint using `/with-timestamps`
  - `cues_from_alignment`
- `wizard_avatar/performance_compiler.py@556701a`
  - `compile_narrative_baseline`
  - `NarrativeTimingSpan`
- `tools/performance_authoring/transcript.py@556701a`
  - `optional_speech_capabilities`

Prism preserves ElevenLabs character start/end timing and converts it into VTT cues. That conversion groups characters at punctuation, long spaces, length thresholds, or duration thresholds, which is suitable for coarse captions but loses fine mouth and word timing. Python's schema is richer, but no production parser or adapter consuming `alignment.units` was found. `compile_narrative_baseline` accepts an alignment identity while its timing input remains caption-like `NarrativeTimingSpan` data. The optional speech capability probe reports unavailable because model assets are not configured and provides no adapter.

Recommended change:

- Produce a canonical AlignmentV1 artifact from Prism's normalized provider timing, retaining word/punctuation units and explicit silence.
- Bind it to the exact media and transcript hashes required by the schema.
- Compile progressive text and mouth/silence tracks from the canonical units rather than re-deriving timing from VTT or character count.

### VT-04: Compiled performance scores are not bound into production ingress

**Classification: Missing. Severity: High.**

Evidence:

- `wizard_avatar/performance_application.py@556701a`
  - `PerformanceApplication.__init__`
- `wizard_avatar/media_session.py@556701a`
  - `PerformanceScheduler.accept_snapshot`
  - `PerformanceScheduler.set_score`
- `wizard_avatar/performance_score.py@556701a`
  - score loading and repository contracts
- `wizard_avatar/server.py@556701a`
  - `create_app`

`PerformanceApplication` constructs `PerformanceScheduler` without a score or score resolver. Production code calling `set_score` or supplying a resolver was not found. The loader and repository contracts exist, and tests can inject scores, but normal media-session ingress resolves through scoreless behavior. If a score binding is supplied without a resolver, the scheduler reports `score_not_ready`.

Recommended change:

- Bind the existing score repository/loader at application construction.
- Resolve a score only after its media, transcript, alignment, and score identities match the accepted session context.
- Preserve scoreless behavior as an explicit fallback, not as the silent default when a valid artifact exists.

### VT-05: Reconnect control ACKs are incompatible across the two baselines

**Classification: Missing. Severity: High.**

Evidence:

- `wizard_avatar/media_session.py@556701a`
  - `MediaSessionCoordinator._ack`
  - runtime/session resynchronization handling
- `src/pages/PrismDodecahedron/media/useMediaSessionConnector.js@189fbab`
  - transport ACK identity check
  - `handleAck`
- `crates/prism-cdiss-cli/src/media_connector.rs@189fbab`
  - `MediaConnector::relay`
  - relay response validation

On `resync_required`, Python reports the last accepted sequence and active media epoch. Prism's transport requires every ACK's `accepted_sequence` and `accepted_media_epoch` to equal the just-submitted snapshot before invoking `handleAck`. A legitimate control ACK for a rejected heartbeat therefore becomes `ack_identity_mismatch`. The only automatic path that responds to `resync_required` or a changed runtime instance is never reached, so Prism does not emit the intended reconnect snapshot.

The Rust relay checks connector session identity but otherwise passes the Python ACK through. Prism tests construct ACKs by echoing the submitted sequence and epoch, so they do not cover the Python control-ACK semantics.

Recommended change:

- Define separate submitted-message identity and accepted-cursor identity in the ACK contract, or allow control dispositions to carry the prior accepted cursor into `handleAck`.
- Do not make Python claim that a rejected sequence was accepted merely to satisfy the current client check.
- Add a cross-language test that rotates the Python runtime after an accepted heartbeat and proves a reconnect is emitted and accepted.

### VT-06: Exact-baseline speech handoff can remain stuck on paused speech

**Classification: Partial. Severity: High at `556701a`; repaired after baseline, end-to-end unverified.**

Evidence:

- `wizard_avatar/media_session.py@556701a`
  - `MediaSessionCoordinator._is_terminal_source`
  - `MediaSessionCoordinator._select_active_snapshot`
- `src/pages/PrismDodecahedron/media/useMediaSessionConnector.js@189fbab`
  - speech `finishSpeech`
  - source restore logic
- Current Python source after commit `408825a`
  - `MediaSessionCoordinator._speech_owns_performance`
  - incoming-main reclaim in `_select_active_snapshot`

At the exact Python baseline, a nonterminal speech snapshot retains priority even when paused. Prism ends or pauses speech by publishing the speech lifecycle state and then restoring the main source. Python can continue selecting the paused speech snapshot and ignore the restored main snapshot for performance.

Commit `408825a` changes current Python so only playing/buffering/seeking speech owns performance and an incoming main snapshot can reclaim active state. Focused current-branch tests cover paused TTS restoration and full-state main reclaim. This repair is **Implemented in current Python source** but absent from `556701a` and **Unverified** against Prism `189fbab` in a live process.

### VT-07: Progressive reply text is not synchronized to audible speech

**Classification: Partial. Severity: High.**

Evidence:

- `src/pages/PrismDodecahedron/index.jsx@189fbab`
  - `revealCdissText`
  - concurrent `Promise.all` calls for reveal and speech
  - `scheduleTimedTextSpeech`
- `src/pages/PrismDodecahedron/speech-animation.js@189fbab`
  - `getSpeechTokenDelay`

Reply text reveal and speech playback start concurrently, but reveal timing is a 170-520 ms heuristic derived from token length and punctuation. It does not consume speech element time, provider alignment, actual decoded duration, or browser `SpeechSynthesis` boundary events. There is therefore no measurable bound on text lead or lag.

Audiobook timed text is stronger: cue selection is driven by main audio time. Within a coarse VTT cue, however, token pulses are spread by estimated token weight rather than original alignment timing.

Recommended change:

- Drive progressive reply text from the same canonical alignment units and same active speech element clock used by mouth cues.
- Drive audiobook token-level emphasis from retained alignment units when available; keep VTT cue timing as the coarse fallback.
- Label heuristic reveal as degraded and exclude it from synchronized-performance claims.

### VT-08: Drift correction exists, but transport latency and drift are not demonstrated

**Classification: Partial. Severity: Medium.**

Evidence:

- `wizard_avatar/media_session.py@556701a`
  - `MediaClockEstimator.accept`
  - `MediaClockEstimator.position_at`
  - `MediaSessionCoordinator.accept_snapshot`
  - coordinator diagnostics
- `src/pages/PrismDodecahedron/media/useMediaSessionConnector.js@189fbab`
  - `DEFAULT_HEARTBEAT_MS = 250`
  - one-active/one-latest transport
- `crates/prism-cdiss-cli/src/media_connector.rs@189fbab`
  - one-active/one-latest relay

Python advances playing time from local receipt time and hard-reconciles on source/lifecycle discontinuity or absolute clock error greater than 100 ms. Non-playing states do not advance, and estimates older than 1.5 seconds become uncertain. This is coherent.

However, receipt-time interpolation starts after transport latency, so it systematically trails the sampled browser position by the unmeasured one-way delay. The client sample timestamp is validated but not used, appropriately, because the clock origins are not established as comparable. Two latest-only queues can also erase intermediate lifecycle observations during congestion. Current diagnostics expose snapshot age and estimated position, while `clock_error_ms` is retained in acceptance state but not exposed. Prism exposes round-trip/relay latency, not rendered cue-to-audio drift.

Recommended change:

- Expose accepted `clock_error_ms`, active source, freshness, hard-reconcile reason, and rendered media position in diagnostics.
- Instrument browser sample-to-Python-ACK latency and browser audio-to-rendered-cue error separately.
- Add saturation tests proving terminal speech and main reclaim converge correctly through both latest-only queues.
- Do not increase heartbeat frequency as the sole remedy; that does not repair untracked audio or establish clock offset.

### VT-09: Seek and rate mechanics are present but incompletely exercised

**Classification: Partial. Severity: Medium.**

Evidence:

- `src/pages/PrismDodecahedron/media/mediaSessionProtocol.js@189fbab`
  - `inferPlaybackState`
  - supported-rate validation
- `src/pages/PrismDodecahedron/media/useMediaSessionConnector.js@189fbab`
  - `seeking`, `seeked`, and `ratechange` listeners
- `wizard_avatar/media_session.py@556701a`
  - fixed supported rates
  - seek/discontinuity hard reconciliation
  - rate-aware interpolation

Prism publishes seek lifecycle information and Python hard-reconciles it. `inferPlaybackState` represents a seeking element as `buffering`, with `seeking: true`, so Python's distinct `seeking` lifecycle state is not the normal Prism output. Fixed playback rates are accepted and unit-tested, but no actual Prism rate-control surface was found. A browser rate outside the fixed set would fail protocol validation in the event path.

No live browser-to-Rust-to-Python test demonstrated seek settling or drift at every supported rate. The mechanisms are implemented; the release guarantee remains **Unverified**.

## Risks

1. **False synchronization claim:** UI and documentation can report a connected speech path while Web Audio or OS speech is audible outside the connector.
2. **Rendered desynchronization:** semantic scheduler tests can pass while the displayed mouth uses simulation time.
3. **Silent score degradation:** valid score/alignment artifacts can exist while production continues with fixed scoreless mouth cycles.
4. **Reconnect deadlock:** runtime replacement can leave Prism in an ACK identity error without sending the required reconnect snapshot.
5. **Lifecycle loss under load:** dual latest-only coalescing can omit a speech terminal observation; exact-baseline Python is especially vulnerable.
6. **Unbounded text drift:** heuristic progressive text can visibly lead or trail generated speech, especially after decode latency or provider fallback.
7. **Unsupported-rate failure:** externally changed playback rates outside the protocol set can turn a media event into validation failure.
8. **Insufficient evidence:** current diagnostics cannot prove the project's stated p95/max cue-sync release gates.

## Required measurable verification

The existing project plan already defines the principal release budgets. They should be retained as hard gates:

- Browser snapshot sample to Python ACK: p95 no more than 25 ms and p99 no more than 50 ms.
- Visible cue to audible media position: p95 absolute error no more than 50 ms and maximum no more than 100 ms at every supported rate.
- Seek: no stale pre-seek action after the target is accepted; target error no more than 100 ms; stable new cue no later than 250 ms after seek completion.
- Reconnect: accepted reconnect no later than 2 seconds after interruption; active-source position within 100 ms no later than 500 ms after the accepted reconnect snapshot.

Additional voice-specific requirements needed to close the traced gaps:

- At identical media ID, epoch, position, and score identity, warm playback, cold reconstruction, and post-seek rendering must resolve and render the same mouth state.
- Canonical silence intervals must render a closed mouth for every evaluated frame inside the interval, except explicitly authored transition frames.
- While tracked speech is audible, diagnostics must identify speech as active and its estimated position must meet the same p95/max error budget as main audio.
- Every fallback must report whether it is element-clocked, alignment-clocked, duration-only, or unsynchronized.
- Progressive text claiming synchronization must meet the same 50 ms p95 and 100 ms maximum timing budget against canonical word boundaries. Heuristic reveal must not be counted as passing evidence.
- Runtime rotation, stale sequence, stale epoch, paused speech, ended speech, source replacement, and transport saturation must each converge to the audible source without manual reload.

Required test matrix:

| Dimension | Required cases |
| --- | --- |
| Source | main, element-backed speech, Web Audio fallback, browser TTS fallback, OS/direct speaker path |
| Lifecycle | loading, playing, paused, buffering, seeking, ended, error |
| Control | play, pause, resume, forward seek, backward seek, rate change, source replacement |
| Rate | 0.5x, 0.75x, 1.0x, 1.25x, 1.5x, 2.0x |
| Recovery | Python restart, Rust relay restart, dropped ACK, stale sequence, stale epoch, congested dual queues |
| Timing artifact | exact alignment, coarse VTT, duration-only fallback, no timing artifact |
| Render | semantic resolved state and final rendered mouth/frame output |

Evidence must include timestamped browser media samples, connector submission/ACK records, Python accepted/estimated positions, scheduler cue identities, final rendered mouth values, and calculated error distributions. Unit tests alone are insufficient for the cross-process budgets.

## Recommended implementation order

1. Make the audible speech object and connector clock the same object by using element-backed speech whenever synchronized mode is enabled.
2. Repair ACK control semantics and add an exact Python-Prism reconnect contract test.
3. Remove the simulation-time mouth override when media performance owns state.
4. Bind the existing score repository/resolver into production `PerformanceApplication` construction.
5. Preserve provider alignment as canonical AlignmentV1 and compile word, silence, progressive-text, and mouth tracks from it.
6. Expose clock error and rendered cue timing in diagnostics, then run the full seek/rate/reconnect matrix.
7. Keep duration-only, heuristic, browser-TTS, and direct-speaker paths, but make their degraded timing classification explicit.

## Rejected alternatives

- **Use the Python 60 Hz simulation clock as master.** Rejected because pause, seek, rate change, buffering, and source replacement belong to the media element.
- **Use Prism's `sampled_at_monotonic_ms` directly in Python.** Rejected without a demonstrated shared origin or clock-offset protocol; subtracting unrelated monotonic values creates fabricated latency correction.
- **Increase heartbeat frequency and declare the drift fixed.** Rejected because it cannot track Web Audio/browser TTS and does not remove one-way transport delay or renderer overrides.
- **Treat token-length timers as alignment.** Rejected because decode/start latency and provider prosody are independent of text length.
- **Derive all mouth motion from coarse VTT.** Rejected because VTT projection intentionally collapses character timing and silence detail.
- **Publish synthetic `speaker` positions from elapsed wall time.** Rejected because the snapshot would not measure the audible device or process and could drift independently.
- **Echo a rejected sequence as accepted to satisfy Prism's ACK check.** Rejected because it corrupts the accepted cursor; submitted identity and accepted identity must be represented separately.
- **Put transcript or alignment payloads in heartbeat snapshots.** Rejected because the canonical protocol deliberately carries compact media identity and timing, not transcript content.

## Exact files and symbols inspected

Python baseline `556701a`:

- `docs/audiobook-performance/LOCAL_PRISMGT_AUDIO_CONNECTOR.md`
- `docs/audiobook-performance/IMPLEMENTATION_PLAN.md`
- `docs/audiobook-performance/PROGRAM_TRACKER.md`
- `docs/audiobook-performance/synthesis/01-contracts-runtime-synthesis.md`
- `schemas/alignment_v1.schema.json`
- `wizard_avatar/media_session.py`
  - `MediaClockEstimator`
  - `MediaSessionCoordinator`
  - `PerformanceScheduler`
- `wizard_avatar/performance_application.py`
  - `PerformanceApplication`
- `wizard_avatar/performance_compiler.py`
  - `compile_narrative_baseline`
  - `evaluate_speech_fallback`
  - `_duration_only_mouth_shape`
- `wizard_avatar/performance_score.py`
- `wizard_avatar/frame_source.py`
  - `_reference_mouth_shape`
- `wizard_avatar/layers.py`
- `wizard_avatar/mouth.py`
- `wizard_avatar/server.py`
  - `create_app`
- `tools/performance_authoring/transcript.py`
  - `optional_speech_capabilities`
- Focused media-session, scheduler, application, server, compiler, score, and schema tests located by symbol/reference search

Prism baseline `189fbab`:

- `src/pages/PrismDodecahedron/index.jsx`
- `src/pages/PrismDodecahedron/speech-animation.js`
- `src/pages/PrismDodecahedron/media/mediaSessionProtocol.js`
  - `buildMediaDescriptor`
  - `inferPlaybackState`
  - `createMediaSessionSnapshot`
- `src/pages/PrismDodecahedron/media/useMediaSessionConnector.js`
  - connector transport
  - active-source selection
  - main and speech lifecycle publishing
  - `handleAck`
  - `stopPlayback`
- `src/pages/PrismDodecahedron/media/ConnectorDiagnostics.jsx`
- `crates/prism-cdiss-cli/src/media_connector.rs`
  - `MediaConnector::relay`
  - relay worker and tests
- `crates/prism-cdiss-cli/src/audiobooks.rs`
  - `ElevenLabsAlignment`
  - generation and VTT projection
- `crates/prism-cdiss-cli/src/voice.rs`
  - `Voice::speak_with_voice`
  - `Voice::synthesize_with_voice`
- `crates/prism-cdiss-cli/src/web.rs`
  - `tts`
- Connector protocol, hook, diagnostics, and Rust relay tests located by symbol/reference search

Current Python follow-up inspected only to classify baseline drift:

- Commit `408825a`, especially `MediaSessionCoordinator._speech_owns_performance` and incoming-main reclaim behavior
- Current focused tests for paused speech restore and full-state main reclaim

## Verification performed

- Inspected both exact Git objects with `git show` rather than inferring Prism behavior from its unrelated current checkout.
- Searched production references for alignment consumption, score injection, `set_score`, playback-rate control, connector `speaker` publication, mouth rendering, and reconnect handling.
- Confirmed by direct coordinator exercise that after runtime rotation Python returns `resync_required` with the prior accepted sequence/epoch, which the Prism baseline ACK identity check rejects before `handleAck`.
- Ran the current Python focused suite:

  `env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest tests.wizard.test_media_session tests.wizard.test_performance_scheduler tests.wizard.test_performance_application tests.wizard.test_media_session_server`

  Result: 39 tests passed in 2.061 seconds. Asyncio emitted slow-task notices but no failures.

## Unverified and excluded

- No packaged Prism application, browser, Rust sidecar, Python server, audio device, or installed desktop bundle was started.
- No audible waveform, visual frame capture, latency trace, or drift distribution was collected.
- The focused Python tests exercised the current branch, not an isolated checkout of exact baseline `556701a`.
- Prism baseline tests were inspected but not executed from an isolated worktree.
- Current unrelated and uncommitted work in either shared checkout was not evaluated as completed behavior.
- Other character-director specialist reports were not opened.

Accordingly, the implementation classifications above describe traced source behavior. The stated synchronization budgets remain **Unverified** until the cross-process matrix is executed against the real audible and rendered paths.


