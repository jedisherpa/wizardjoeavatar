# QA and Verification for the Audiobook Performance Engine

**Role:** QA and Verification Specialist (research pass 11 of 12)

**Date:** 2026-07-13

**Scope:** Read-only audit of `WizardJoeAvatar-python` and the current PrismGT checkout, plus primary-source research. Only this report was authored; no production code or dependency file was changed.

## Executive verdict

The combined Wizard Joe Audiobook Performance Engine and PrismGT Media Connector is **not production-ready**. Both repositories contain useful testable foundations, but the end-to-end product described in the brief does not yet exist as a verifiable contract:

- Wizard Joe has deterministic fixed-step runtime and command-ordering tests, but no audiobook score, media-clock adapter, connector session, reconnect protocol, or real-pipeline replay test.
- PrismGT has an HTML audio player, caption display, local media routes, provider-governed audiobook generation, and Rust tests, but no connector to Wizard Joe and no JavaScript unit, browser, accessibility, or visual-regression test stack.
- The player currently schedules token pulses from one sample of `audio.currentTime` using future `setTimeout` calls. Seek, playback-rate change, buffering, and reconnect can therefore leave already-scheduled actions stale.
- The known stream deadline test is genuinely timing-sensitive. It passes within the full suite on this audit run but failed three consecutive isolated runs. Its wall-clock assertion mixes scheduling policy with a renderer that is already over the 24 fps frame budget.
- Current CI can prove a frontend bundle and Rust quality checks. It cannot prove audiovisual synchronization, reconnect recovery, privacy, governed external opening, accessibility, deterministic replay, long-duration stability, or packaged-app behavior.

Release approval should require the exact gates in section 10. A green build alone is not evidence that the performance stays synchronized to authoritative audio.

## 1. Audited revisions and baseline evidence

| Repository | Audited branch and revision | Baseline result |
|---|---|---|
| Wizard Joe Python | `codex/audiobook-performance-engine` at `7781a67c97bfbfa16a64d5b9fb12bdf74bd4c032` | `python3 -m unittest discover -s tests -p 'test*.py'`: **171 passed in 148.401 s** |
| Wizard Joe Python | same revision, isolated known deadline test | **3/3 isolated runs failed** at `tests/wizard/test_stream_hub.py:68-100`; each published one frame where the test requires 3-5 |
| PrismGT | `desktop/prism-gt-influence-integrated` at `0ce9f9bae665b1415cd776e4d6c9ee23565936ac` | `npm run build`: passed in 511 ms, with a 675.36 kB `sse-cdiss` chunk warning |
| PrismGT | same revision | `cargo test --locked --workspace --all-targets`: stopped during the Tauri build because `target/release/prism-dodeca-cli` did not exist; this is a build-prerequisite failure, not a Rust test assertion |
| PrismGT | same revision, testable non-desktop packages | `cargo test --locked --quiet -p prism-cdiss-core -p prism-cdiss-cli -p x_connector --all-targets`: **passed**; principal suites reported 253 and 662 unit tests plus all listed integration targets |

The repositories were not cleanly comparable as one revision: they are separate checkouts with separate commits. Every future evidence bundle must record both commit hashes and both dirty states.

## 2. Current verification surface

### 2.1 Wizard Joe Python

The strongest existing foundations are:

- `wizard_avatar/runtime.py:27-67,137-173,176-315` provides stable Python-side value encoding, a replay log, exact integer fixed-step accumulation, state hashes, and bounded catch-up.
- `tests/wizard/test_runtime.py:61-97,143-159` verifies 10,000 fixed ticks, matching hashes for matching schedules, bounded stalls, and deterministic replay of a small reducer.
- `wizard_avatar/commanding.py` and `tests/wizard/test_commanding.py` cover versioned commands, source epoch and sequence ordering, TTL, duplicates, stale input, bounded queues, and stable same-time ordering.
- `wizard_avatar/prism_signals.py` and its tests enforce content-free visual advice and reject authority-bearing or private-looking fields such as prompts, replies, paths, and hashes.
- `wizard_avatar/stream.py:128-190,349-360` exposes runtime diagnostics, hashes, dropped deadlines, schedule overruns, and bounded subscriber behavior.

Those tests stop short of the proposed integration:

- `wizard_avatar/server.py:203-240` accepts an unversioned WebSocket `{type, payload}` command shape and catches malformed input broadly. It does not use the stricter connector envelope in `wizard_avatar/transport.py`.
- `wizard_avatar/stream.py:31-41,288-314` creates random runtime epochs and random legacy command IDs. Operational uniqueness is appropriate, but a raw production replay log will not be byte-identical without a normalization rule.
- The replay test exercises a toy reducer, not `WizardFrameHub`, the real controller, performance score, media state, rendered cells, encoded frame, or connector acknowledgements.
- No current module represents audiobook identity, media hash, score version, chapter, playback rate, buffering, seeking, connector session, or resume snapshot.

### 2.2 PrismGT

The current media path has several useful seams:

- `src/pages/PrismDodecahedron/index.jsx:3585-3590` owns one hidden HTML `<audio>` element; it must remain the authoritative playback clock.
- `src/pages/PrismDodecahedron/musicMotion.js:163-336` samples `currentTime` and `duration` in an animation loop for audio-reactive motion.
- `crates/prism-cdiss-cli/src/web.rs:6221-6369` serves audiobook metadata, audio with range support, captions, generation, and deletion through local routes.
- `crates/prism-cdiss-cli/src/web.rs:7848-7955` applies same-origin/host checks and a per-launch token to mutating local requests.
- `crates/prism-cdiss-cli/src/audiobooks.rs:277-350` places outbound ElevenLabs generation behind `ModelProviderDispatchPermit` and persists provider alignment where available.
- `src/features/visualizer/useReducedMotionPreference.js:5-17` and the reduced-motion CSS in `src/pages/PrismDodecahedron/index.css:2919-2943` provide a basis for motion-sensitive testing.

The principal QA gaps are:

- `src/pages/PrismDodecahedron/index.jsx:2049-2104` computes token-pulse delays from one `audio.currentTime` sample and then relies on `setTimeout`. There is no generation/epoch cancellation oracle for seek, rate change, buffering, chapter change, or reconnect.
- The audio integration listens for `ended` around `index.jsx:2987-3005`, but no explicit contract handles `seeking`, `seeked`, `ratechange`, `waiting`, `playing`, or recovery snapshots.
- `src/pages/PrismDodecahedron/studio/StageUtilityCards.jsx:347-463` exposes playback controls and a noninteractive progress meter, but no seek slider, playback-rate control, connector health, or Whiz external-source action.
- `src/pages/PrismDodecahedron/musicLibrary.js:33-77`, `src/lib/media-normalize.js:7-68`, and `crates/prism-cdiss-cli/src/audiobooks.rs:83-101` do not preserve a canonical external source URL, final media hash, score version, or transcript/alignment version in the track contract.
- `crates/prism-cdiss-cli/src/audiobooks.rs:449-470` atomically writes each audio, caption, alignment, metadata, and index file separately, but it does not atomically publish a complete generation directory. A failure between writes can expose an internally incomplete track.
- `src-tauri/capabilities/default.json` grants only `core:default`; there is no scoped Tauri opener capability or governed external-link implementation.
- `package.json` has no JavaScript test, browser test, accessibility test, type-check, or visual-regression command.
- `.github/workflows/ci.yml` builds the frontend and applies Rust checks, but collects no QA evidence artifacts and runs no browser or packaged-app tests.

## 3. Required test architecture

### 3.1 Shared, versioned contract fixtures

Define one versioned connector schema and store golden fixtures in a location consumed by Python, JavaScript, and Rust tests. A playback snapshot/event needs at least:

`schema_version`, `session_id`, `source_epoch`, `sequence`, `event_id`, `event_type`, `media_id`, `media_sha256`, `score_version`, `character_id`, `media_time_ms`, `duration_ms`, `playback_rate`, `paused`, `buffering`, `chapter_id`, and a monotonic issuance time.

Required fixture groups:

1. Valid snapshots and every event type.
2. Minimum/maximum legal values and unknown optional fields.
3. Missing required fields, wrong types, non-finite numbers, oversized payloads, and unsupported versions.
4. Duplicate, stale, reordered, gapped, expired, and post-epoch messages.
5. Media-hash, score-version, chapter, and character mismatches.
6. Unicode titles and transcript metadata without transferring transcript content through the visual connector.

All three implementations must produce identical accept/reject outcomes and stable error codes for every fixture. Unknown schema versions fail closed. A connector message must never carry transcript text, local paths, provider tokens, prompts, replies, or full canonical URLs.

### 3.2 Clock and state-machine seams

Use two complementary clocks:

- A fake monotonic clock and cheap fake frame source for deterministic unit tests. These tests advance time directly and contain no `sleep`-based assertions.
- Real HTML media and real renderer paths for integration/performance tests. These tests measure behavior; they do not establish scheduling logic through machine-dependent frame counts.

Model player states explicitly: `idle`, `loading`, `playing`, `paused`, `seeking`, `buffering`, `ended`, `error`, and `reconnecting`. Every transition must specify whether existing cue timers are invalidated, what neutral pose is held, and which snapshot is authoritative after recovery.

The HTML media element's `currentTime` is the authoritative position. The WHATWG media model defines seeking around that value and rate-limits `timeupdate`; therefore `timeupdate` should wake UI work, not act as the high-resolution performance clock. The scheduler should sample `audio.currentTime` each render/update and derive the desired score state from it ([WHATWG HTML media](https://html.spec.whatwg.org/multipage/media.html)).

### 3.3 Synthetic fixture corpus

Check in redistribution-safe generated fixtures, not copyrighted audiobook extracts:

- 2 s silence, 10 s speech-like tone/click track, and 30 s narrated synthetic chapter.
- Exact word/cue boundaries, chapter markers, silence spans, and a fixed SHA-256 for each file.
- Alternate MP3/WAV forms, a truncated file, corrupt headers, zero-byte input, and mismatched declared duration.
- One 15-minute deterministic fixture generated from a recipe during CI and one multi-hour sparse-score recipe for soak tests.

FFmpeg's `framehash` or `framemd5` muxers can provide portable decoded-frame evidence for fixture validation ([FFmpeg formats documentation](https://ffmpeg.org/ffmpeg-formats.html#framehash)).

## 4. Test matrix and measurable acceptance criteria

### 4.1 Unit and property tests

| Area | Required tests | Pass criterion |
|---|---|---|
| Ingestion/publication | duplicate import, content hash, supported/invalid media, interrupted write at every file boundary, index crash/restart | Identical media is idempotent; published generation is complete and hash-valid or wholly absent; prior generation remains readable |
| Transcription/alignment | monotonic words/cues, bounds, silence, missing words, overlap, transcript revision, media mismatch, fallback provenance | All times lie within decoded duration; invalid/mismatched artifacts are rejected; fallback is explicit and never silently replaces approved timing |
| Analysis/cache | fixed model/tool/config inputs, cache hit/miss, corrupted cache, changed media/transcript/score, unavailable analyzer | Same inputs produce identical artifact hash; any material input change invalidates cache; fallback is bounded, versioned, and visible |
| Score parser | schema versions, bounds, ordering, overlap policy, missing character, unknown cue, invalid easing, non-finite values | 100% golden-fixture agreement; malformed scores fail before playback with stable error codes |
| Cue lookup | boundary at start/end, silence, exact chapter edge, reverse lookup after seek | Correct active cue set at every boundary and at 10,000 generated positions |
| Scheduler | play, pause, resume, rate, seek, buffer, stop, chapter and epoch invalidation under fake clock | No stale one-shot executes after generation changes; identical trace for identical seed/input |
| Connector | parser, TTL, epoch, sequence, dedupe, ack, queue cap, snapshot replacement | No stale apply; queue never exceeds configured cap; every accepted/rejected message has one disposition |
| URL policy | valid `http`/`https`; missing, relative, whitespace/control, `javascript:`, `file:`, `data:`, `blob:`, credentials | Only explicitly allowed absolute schemes and hosts reach the opener seam |
| Privacy redaction | title, transcript, path, token, URL query/fragment canaries | Zero canaries in connector payloads, ordinary logs, exception text, or test artifacts |
| Reduced motion | preference changes before and during playback | Locomotion and nonessential continuous movement stop or reduce without changing audio/caption state |

Property tests should generate event sequences rather than only isolated examples. Invariants include: audio time never comes from the avatar; pause cannot advance score time; a newer epoch dominates every older message; the latest seek wins; and a cue can fire at most once per epoch unless its score explicitly declares repeat behavior.

### 4.2 End-to-end synchronization

Run the real PrismGT browser player, connector, Python server, performance scheduler, and frame output together. Record each media sample, connector send/receive/ack, selected cue, state hash, and rendered frame timestamp in NDJSON.

| Scenario | Exact gate |
|---|---|
| Steady playback | Over 15 minutes at each of `0.5x`, `1x`, `1.25x`, `1.5x`, and `2x`, cue-to-audio absolute error p95 <= 50 ms and maximum <= 100 ms |
| Pause | No cue or locomotion advancement more than one 24 fps frame (42 ms) after pause observation |
| Resume | First correct score state within 100 ms; no replay of pre-pause one-shots |
| Seek | After 100 random forward/backward seeks, correct cue on the first post-seek rendered update and <= 100 ms; zero stale pre-seek actions |
| Rapid scrub | 100 seeks in 10 s; latest seek wins, queue remains bounded, process stays responsive, and final state matches final media time |
| Chapter/track change | Prior epoch is invalid immediately; new media hash and score version agree before non-neutral performance begins |
| Buffer/rebuffer | Avatar holds the specified neutral or last-safe pose; score time does not advance while media time is stationary |
| End/stop | All pending one-shots are canceled; final state is deterministic and idempotent |
| Loopback connector | Event-to-ack latency p95 <= 25 ms and p99 <= 50 ms on the declared reference Mac |

### 4.3 Reconnect and failure injection

Use a programmable proxy around the connector and injectable filesystem/provider seams. Test each failure at every meaningful state transition.

| Injection | Required oracle |
|---|---|
| Drop, delay, duplicate, or reorder messages | Gap is detected; no stale apply; snapshot recovery converges without duplicate one-shots |
| Close either side, half-open socket, missing pong | Failure is detected; bounded exponential retry; reconnect <= 2 s on loopback; sync error <= 100 ms within 500 ms of accepted snapshot |
| Kill/restart Python or PrismGT | New epoch is required; old commands rejected; playback remains user-controlled; no automatic external action |
| Malformed/oversized frame | Connection or message rejected with stable reason; memory remains bounded; no private payload echoed |
| Slow subscriber/full queue | Old frames are dropped according to policy, newest keyframe wins, and queue cap is never exceeded |
| Audio decode error/network stall | Visible, accessible error; avatar enters safe state; retry does not duplicate cues |
| Corrupt score/media-hash mismatch | Performance refuses to start and reports actionable local error |
| Disk full/read-only/truncated index | Existing generation remains readable; no partially published generation is selected |
| Provider denial/offline/timeout | No dispatch without permit; bounded timeout; local playback and cached media remain usable |
| Background/foreground and sleep/wake | Fresh media snapshot replaces elapsed wall-time assumptions; no catch-up burst |
| Logging sink failure/disk full | Product continues safely or fails explicitly; no recursive logging storm |

RFC 6455 ping/pong frames are the protocol-level mechanism for checking a WebSocket peer's responsiveness; exercise missing and delayed pong behavior explicitly ([RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455#section-5.5.2)).

### 4.4 Privacy and governance

Run tests in two network modes: all egress denied and a narrow test-provider allowlist. Seed unique canaries into media title, transcript, local path, URL query, bearer token, provider prompt, and exception text. Scan:

- process stdout/stderr and structured logs;
- browser console, network log/HAR, SSE and WebSocket captures;
- connector traces and replay bundles;
- CI artifacts, screenshots, videos, crash reports, and failure messages;
- provider request receipts.

The gate is **zero canary occurrences outside the one explicitly approved local source artifact**. Local-only playback must make zero non-loopback connections. A provider call requires a recorded permit containing provider, model, purpose, payload SHA-256, and byte count, but not the content itself. Denial must produce no network attempt.

OWASP recommends excluding access tokens, passwords, sensitive personal data, and commercially sensitive information from logs and explicitly testing logging failures such as connectivity loss and exhausted storage ([OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)).

### 4.5 Whiz external-source action

The future Whiz action needs unit, browser, and packaged-Tauri coverage:

1. Missing or invalid canonical URL keeps the action absent or disabled with an accessible name/state.
2. Loading a track, reconnecting, restoring state, or receiving a connector event never opens a URL.
3. One explicit pointer or keyboard activation invokes exactly one governed opener call.
4. Only scoped absolute `http`/`https` URLs are accepted; credentials and disallowed hosts/schemes are rejected according to policy.
5. Playback time, pause state, score epoch, and connector state do not change as a side effect.
6. A content-free audit receipt records user activation, media ID hash, destination origin, disposition, and policy version.

Tauri's opener plugin blocks potentially dangerous commands by default and requires explicit capability permissions/scopes; use that boundary rather than raw browser opening ([Tauri opener plugin](https://v2.tauri.app/plugin/opener/)).

### 4.6 Browser and accessibility

Add Playwright coverage in Chromium and WebKit. Use a real short media fixture for browser media semantics and fake clocks only below that boundary.

Required browser journeys:

- load library, choose track, play, pause, seek, change rate, toggle captions, change chapter, stop;
- buffer/recover, connector disconnect/reconnect, Python restart, corrupt score, unavailable source URL;
- keyboard-only operation through every control with visible focus and logical focus order;
- Whiz activation and rejection paths;
- normal and reduced-motion preference, including preference change during playback;
- narrow mobile and desktop layouts with long title/caption/error text.

Run axe-based checks on each stable state, but do not treat zero automated violations as full accessibility approval. Playwright notes that automated tests cannot detect every WCAG issue ([Playwright accessibility testing](https://playwright.dev/docs/accessibility-testing)). Manual release review must include VoiceOver on macOS for control names, role/state announcements, focus restoration, caption updates, and connector/error status without repetitive live-region chatter.

Specific gates:

- Every command is keyboard operable, satisfying WCAG 2.1.1 ([WCAG 2.2](https://www.w3.org/TR/WCAG22/#keyboard)).
- Controls expose correct name, role, and value/state ([WCAG name, role, value](https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html)).
- A future seek control is a real accessible slider, not only the current `role="meter"` display.
- Decorative canvas may remain `aria-hidden` only while equivalent playback, caption, and status information exists outside it.
- Reduced-motion mode suppresses interaction-triggered nonessential animation and is tested at the actual rendered scene, not only CSS ([WCAG animation from interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html), [Media Queries Level 5](https://www.w3.org/TR/mediaqueries-5/#prefers-reduced-motion)).

### 4.7 Visual regression and human review

Capture stable states at `1280x860`, `960x680`, and `390x844` in normal and reduced-motion modes:

- player ready, playing, paused, seeking, buffering, reconnecting, error, and completed;
- captions off/on, very long cue, long title, unavailable Whiz action, and chapter transition;
- each authored story/performance mode and neutral fallback.

Use fixed assets, score, seed, tick, browser version, OS image, fonts, color profile, and GPU policy. Playwright's `toHaveScreenshot` is suitable, but its documentation warns that rendering varies by host environment, so baseline and comparison must run in the same pinned environment ([Playwright visual comparisons](https://playwright.dev/docs/test-snapshots)).

For canvas evidence, assert both:

- nonblank pixel coverage and expected bounding region so a blank/frozen canvas cannot pass; and
- an exact image/hash only for fully deterministic frames.

Release evidence also needs a short screen recording for each principal performance mode and signed human approval from animation, audio, accessibility, and QA reviewers. Pixel snapshots cannot judge whether movement serves the narration.

### 4.8 Performance and soak

Instrument phase histograms separately for simulation, cell render, image encode, frame hash, queue wait, connector dispatch, connector ack, and browser apply. One aggregate frame time cannot identify the limiting stage.

Reference-hardware gates for the current 24 fps, 240x135 profile:

- renderer pipeline p95 <= 33.3 ms and p99 <= 41.7 ms;
- no deadline-policy failures in 100 deterministic fake-clock repetitions;
- no long browser main-thread task above 100 ms caused by connector/scheduler work during the 15-minute rate matrix;
- 8-hour playback soak with zero uncaught exceptions, reconnects not caused by injection, stale cue applications, or unbounded timer/queue growth;
- after a 30-minute warm-up, RSS increase <= 64 MiB total and fitted growth <= 1 MiB/hour;
- connector and frame queues remain at or below declared caps for the entire soak.

Performance thresholds must name machine model, CPU architecture, power mode, OS, browser, Python, Node, and Rust versions. Portable hosted CI should run correctness smoke tests; reference-hardware performance should be a required protected gate for release candidates.

## 5. Known stream deadline test: root cause and correction

The test at `tests/wizard/test_stream_hub.py:68-100` wraps the real frame source with an injected `asyncio.sleep(0.06)`, runs the hub for 0.34 s at 24 fps, and requires 3-5 published frames. It intends to prove that missed deadlines are dropped rather than replayed in a burst.

Observed during this audit:

- The full 171-test run passed once.
- The isolated test failed three consecutive runs with `published=1`; each run took about 1.47-1.49 s.
- Approximate local microbenchmarks were 48.8 ms for `render_current_frame`, 75.6 ms for `next_encoded_frame(..., advance=False)`, and 10.3 ms for `frame_hash`.
- The real render/encode/hash path is therefore approximately 85.9 ms before the injected 60 ms delay, or about 145.9 ms per attempted frame. Three frames cannot reliably fit in a 340 ms observation window, and the underlying real path already exceeds the 41.7 ms budget for 24 fps.

This is both a flaky test design and a performance signal. The correct response is **not** to lower the assertion until it turns green.

Required replacement:

1. A fake-clock, cheap-frame-source unit test advances through a known overrun schedule and proves: no replay burst, missed slots counted exactly, simulation does not run ahead, and next deadline is future-aligned. It must run without real sleeps.
2. A separate instrumented real-render benchmark reports phase percentiles and applies the reference-hardware gates in section 4.8.
3. Keep the existing test red/quarantined only with a tracked expiry owner while the split lands; deterministic tests must not use retries as a passing mechanism.

Python's asyncio debug mode records slow callbacks and is useful diagnostic evidence, but it does not make wall-clock sleeps deterministic ([Python asyncio development guidance](https://docs.python.org/3/library/asyncio-dev.html#debug-mode)).

## 6. Deterministic replay contract

Operational session IDs and epochs may remain random. The canonical replay artifact must normalize or exclude them and include fixed:

- media bytes and SHA-256;
- score bytes/version and SHA-256;
- transcript/alignment versions without unnecessary transcript content;
- seed, initial state, character identity, runtime configuration, and tick rate;
- complete ordered playback snapshots/events and connector dispositions;
- selected cue decisions, resulting state hashes, and frame hashes.

Run the same corpus twice in fresh processes. The canonical cue-decision trace, ack/disposition trace, state-hash stream, frame-hash stream, and final manifest SHA-256 must be byte-identical. Mutating the score or seed must change the expected hash. Replaying a trace with one dropped, duplicated, reordered, or stale message must converge to the defined oracle.

`wizard_avatar/runtime.py` currently uses a custom canonical form including hexadecimal float wrappers. It can remain if every implementation shares golden cross-language vectors. If cross-language canonical JSON is desired, adopt RFC 8785 deliberately and version the change; do not call the current custom encoding RFC 8785-compatible ([RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html)).

## 7. Evidence bundle

Every protected run should publish one immutable bundle such as:

```text
qa-evidence/<run-id>/
  manifest.json
  commands.ndjson
  junit/
  contracts/
  sync/trace.ndjson
  sync/summary.json
  replay/inputs-manifest.json
  replay/hashes.json
  browser/traces/
  browser/screenshots/
  browser/diffs/
  browser/videos/
  accessibility/
  performance/
  soak/
  privacy/egress-summary.json
  privacy/canary-scan.json
  governance/receipts.ndjson
  SHA256SUMS
```

`manifest.json` must record both repository URLs/commits/dirty states, workflow URL, run ID, UTC times, OS/hardware, tool/browser versions, lockfile hashes, commands and exit codes, fixture hashes, random seeds, test counts, known-waiver IDs, and every artifact hash.

Never upload copyrighted audio, transcript text, user paths, tokens, raw provider payloads, or unredacted HAR files. Publish synthetic fixtures and content-free hashes/summaries. Apply GitHub artifact attestations to distributable release artifacts so consumers can verify provenance ([GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)). Pin third-party actions to full commit SHAs because GitHub identifies that as the only immutable release reference ([GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions)).

## 8. CI gate design

### Pull request gate

- Python: all unit tests, connector contract fixtures, property tests, deterministic scheduler/replay, privacy redaction, and the fake-clock deadline test.
- Rust: formatting, check, clippy with warnings denied, package tests, audiobook atomic-publication tests, route/auth/governance tests, and shared contract fixtures.
- JavaScript: lint/type-check if adopted, unit tests for media reducer/scheduler/URL policy, production build, Chromium and WebKit player/connector journeys, axe checks, and deterministic screenshots.
- Cross-process: short synthetic media end-to-end play/pause/seek/rate/buffer/reconnect test with synchronization summary.
- Evidence: manifest, JUnit, contract/replay hashes, browser traces on failure, privacy scan, and checksums uploaded even when a gate fails.

No deterministic test may pass because of retry. No focused/skipped/quarantined test is allowed without an owner, reason, issue URL, and expiry date.

### Nightly gate

- Full failure-injection matrix.
- 100-run deadline/scheduler stress.
- Full rate/seek matrix in Chromium and WebKit.
- Two-hour soak on portable CI.
- Visual suite, dependency/license/security scan, egress-denied privacy run, and replay cross-language vectors.

### Release-candidate gate

- Packaged and installed Tauri application driving the actual Python service.
- Reference-hardware performance and 8-hour soak.
- Kill/restart, sleep/wake, offline, and token-rotation recovery.
- Signed/notarized artifact verification where applicable and artifact attestation.
- Manual VoiceOver, keyboard, visual-performance, caption, and privacy/governance review.
- Zero unresolved P0/P1 defects and zero expired waivers.

The current Tauri workspace test prerequisite must be made reproducible in CI: build the expected release sidecar first or make test builds consume a declared fixture. A developer's pre-existing `target/release/prism-dodeca-cli` must never be an implicit condition for a green workspace test.

## 9. Principal risks

| Priority | Risk | Consequence | Required control |
|---|---|---|---|
| P0 | Audio events and score are not connected through a versioned protocol | Avatar drifts or performs the wrong cue | Shared schema, audio-authoritative scheduler, end-to-end sync gates |
| P0 | Future token timers survive seek/rate/buffer changes | Stale pulses and duplicated one-shots | Epoch/generation cancellation plus event-sequence tests |
| P0 | Existing renderer exceeds nominal 24 fps budget on the audit machine | Persistent lag and deadline drops | Phase instrumentation and reference-hardware performance gate |
| P0 | No real-pipeline deterministic replay | Regressions cannot be reproduced or certified | Canonical trace across score, connector, runtime, and frames |
| P1 | Reconnect has no snapshot/ack contract | Old state can regain authority after restart | Epoch, sequence, snapshot replacement, ping/pong and fault tests |
| P1 | Frontend has no browser/accessibility/visual test harness | User-facing breakage reaches release unseen | Playwright, axe, screenshots, canvas checks, manual VoiceOver |
| P1 | Whiz source URL/opener is absent | Unsafe implementation could bypass consent or scheme policy | Scoped Tauri opener, pure URL policy, explicit activation tests |
| P1 | Evidence may leak titles/transcripts/paths/tokens | Privacy and governance breach | Canary/egress testing, redaction, synthetic artifacts |
| P1 | Track files are published atomically one by one rather than as one generation | Crash/disk failure can expose mixed or incomplete artifacts | Generation-directory commit marker or atomic directory swap plus interruption tests |
| P1 | Tauri workspace tests depend on an undeclared release sidecar | CI/local results are nonreproducible | Explicit sidecar build/fixture and clean-checkout test |
| P2 | CI actions use mutable major tags | Supply-chain inputs can change without repository diff | Pin full action SHAs and attest release artifacts |

## 10. Exact production done criteria

Production is done only when **every** row is evidenced for the same candidate revisions and packaged build:

| Gate | Exact done criterion | Current status |
|---|---|---|
| Baseline | Python, JS/browser, Rust, cross-process, and packaged smoke suites all pass with zero unexplained skips/retries | **Not met** |
| Contract | Python/JS/Rust agree on every shared golden message; unsupported versions and stale epochs fail closed | **Not implemented** |
| Ingest/alignment/analysis | Complete generations publish atomically; media/transcript/score hashes and provenance agree; cache invalidation and fallback matrix pass | **Not implemented end to end** |
| Audio authority | HTML audio time is the sole playback authority across play/pause/seek/rate/buffer/chapter/stop | **Not implemented** |
| Sync | Meets every p95/max criterion in section 4.2 at five playback rates | **No evidence** |
| Reconnect | Either process can restart; reconnect <= 2 s and converges within 500 ms/100 ms error with zero duplicate one-shots | **No evidence** |
| Determinism | Two fresh-process replays produce identical canonical cue, disposition, state, frame, and final hashes | **Partial toy coverage only** |
| Failure safety | Full matrix in section 4.3 passes with bounded memory/queues and defined safe states | **No evidence** |
| Privacy | Egress-denied local run has zero non-loopback connections and zero canary leakage across all listed surfaces | **No end-to-end evidence** |
| Governance | Every external provider/open action requires explicit permit or user activation and produces a content-free receipt | **Partial provider gate; Whiz absent** |
| Accessibility | Chromium/WebKit axe runs pass; keyboard and macOS VoiceOver checklist signed; reduced motion verified in rendered scene | **No evidence** |
| Performance | Meets frame, connector, main-thread, memory, and 8-hour soak thresholds on declared hardware | **Not met/no evidence** |
| Visual | Pinned screenshot/canvas gates pass and animation/audio/QA reviewers approve recordings for all modes | **No evidence** |
| Artifact | Complete redacted evidence bundle, checksums, workflow provenance, package attestation, and both commit identities published | **No evidence** |
| Defects | Zero open P0/P1 defects, zero known flaky blocking tests, and zero expired waivers | **Not met: known deadline flake** |

Until all rows pass, describe the work as an experimental integration, not a verified audiobook performance release.

## Sources

- [WHATWG HTML: media elements](https://html.spec.whatwg.org/multipage/media.html)
- [Playwright: visual comparisons](https://playwright.dev/docs/test-snapshots)
- [Playwright: accessibility testing](https://playwright.dev/docs/accessibility-testing)
- [Tauri v2 opener plugin](https://v2.tauri.app/plugin/opener/)
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [WCAG: Understanding Name, Role, Value](https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html)
- [WCAG: Understanding Animation from Interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html)
- [Media Queries Level 5: `prefers-reduced-motion`](https://www.w3.org/TR/mediaqueries-5/#prefers-reduced-motion)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html)
- [RFC 6455: WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [FFmpeg formats documentation](https://ffmpeg.org/ffmpeg-formats.html)
- [GitHub: artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
- [GitHub Actions: secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [Python: developing with asyncio](https://docs.python.org/3/library/asyncio-dev.html)
