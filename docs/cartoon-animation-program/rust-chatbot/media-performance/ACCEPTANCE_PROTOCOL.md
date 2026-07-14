# Media Performance Acceptance Protocol

## Completion Rule

Compilation is necessary and insufficient. Each section below must have saved,
hash-addressed evidence from the actual packaged runtime. A failed or unavailable
test is a visible limitation, not a pass.

## Contract And Determinism

- Deserialize and byte-round-trip the complete capability-manifest V2, protocol V1,
  and score V1 fixtures; reject unknown fields, tags, enum values, and versions.
- Round-trip every `MediaProtocolMessageV1` and every `MediaCommandV1` operation,
  including explicit null option fields, through the strict Rust codec. Prove the
  canonical protocol transcript and all permutation/negative fixtures are stable.
- Canonicalize protocol objects with recursive lexicographic key ordering and prove
  declaration-order, randomized-key-order, and already-canonical inputs converge on
  identical bytes. Exercise snapshot active-cue counts 0, 1, 4,096, and rejected
  4,097 plus duplicate/stale/wrong-generation entries.
- Assert the checked-in raw fixture bytes exactly equal Rust canonical serialization;
  a trailing line feed or any other insignificant whitespace is a contract failure.
- Prove snapshots use `snapshot_revision` plus
  `command_sequence_high_watermark`, receive no ACK, and never enter the terminal
  command replay cache. Test idempotent identical replay, stale revision rejection,
  conflicting same-revision bytes, and atomic high-water reconciliation.
- Recompute the capability manifest from loaded runtime registries, reproduce its
  fixture hash, require the score fixture's nonzero manifest binding, and reject a
  valid score paired with any different manifest bytes or hash.
- Verify the generated safe-idle profile resolves active stop, neutral-expression,
  closed-mouth, and eight-facing idle authorities. Corrupt each reference/boolean and
  prove validation fails; exhaust a cue fallback in every region and prove the exact
  preserve/clear/settle policy with no guessed capability or stale owner revival.
- Reject unknown/diagnostic/incompatible capability IDs before playback.
- Prove canonical serialization and score hashes are stable across repeated runs.
- Replay identical media observations and score bytes at least twice; cue sequence,
  region decisions, animation IDs, and frame hashes must match.
- Property-test bounded identifiers, timestamps, rates, cue counts, queue sizes,
  arithmetic extremes, duplicate IDs, and overlapping tracks.
- Fuzz JSON ingress and media metadata with payload/time/memory bounds.

## Media Session Matrix

For audiobook, music, and supported video, test:

- load, unload, play, pause, resume, stop;
- seek started/completed forward and backward;
- exact-boundary seek at cue start/end and chapter/section edges;
- rate changes while playing and paused;
- track and chapter changes;
- media ended and replay;
- duplicate, delayed, reordered, stale-generation, wrong-session, wrong-media,
  malformed, and oversized events;
- connector loss, server restart, browser reload, and snapshot recovery;
- long buffering gap and discontinuous media-element correction.

Every stale command must be rejected without visible mutation.

## Synchronization Measurements

Record both scheduled media timestamp and observed presentation frame for every cue.

Frozen V1 release thresholds (a change requires a reviewed architecture receipt,
not tuning after a failed run):

- ordinary cue activation: absolute error at most 16,667 microseconds;
- gesture accent: absolute error at most 83,334 microseconds;
- beat/downbeat accent: absolute error at most 33,334 microseconds;
- pause: no score-time advance after accepted pause;
- seek/reconnect: first visible frame comes from the new timeline generation;
- WebSocket Ping/Pong heartbeat is negotiated independently in 1,000..=30,000 ms;
  its traffic never extends the playback observation lease;
- playback observation interval: at most 500 ms while active; lease expires at
  1,000 ms and must freeze before another cue activates;
- projection correction: p99 at most 33,334 microseconds and maximum at most
  100,000 microseconds outside explicit seek/discontinuity windows;
- 60-minute soak: zero stale-generation frames, zero unbounded queue growth, RSS
  growth below 64 MiB after warm-up, and no cumulative drift trend above one
  simulation tick per hour.

Report median, p95, p99, maximum, sample count, dropped observations, correction
count, and clock discontinuities. Do not report only averages.

## Every-Frame Visual Protocol

The evidence runner captures each presented frame and a corresponding ledger row:

- media/session/timeline generation;
- media timestamp and simulation tick;
- score/cue IDs;
- pose/clip/expression/gaze/viseme IDs;
- region owners and generations;
- root/stage position and facing;
- foot/staff/prop contacts;
- topology counters and frame hash.

Automated failures include:

- missing body/staff/required attachment;
- detached or flickering staff line;
- unsupported foot-contact change;
- planted-foot slide above one cell between presented frames or above zero cells
  across a declared hold marker;
- teleport or facing snap outside an explicit transition;
- body-part breakup, isolated cell cluster, seam, or implausible bounding-box jump;
- undesignated hand/body overlap above two cells, undesignated prop/body overlap
  above one cell, or any overlap with a declared stage obstacle;
- mouth/eye/face state incompatible with active performance state;
- stale cue visible after seek, cancel, session end, or safety clamp;
- blank, cropped, occluded, or off-stage character;
- layout shift or overlay collision in desktop/mobile browser evidence.

For contact-bearing authored clips, planted foot/staff anchors may move at most one
cell between presented frames and zero cells across declared hold markers. A
designated contact mask is part of the clip manifest and may contain at most eight
cells; overlap outside that mask uses the global two-cell hand/body and one-cell
prop/body limits above. Required body/attachment loss, detached-cell clusters,
stale-generation frames, blank frames, stage-obstacle overlap, and uncued teleports
have a tolerance of zero. These values are V1 constants, not per-run tuning knobs.

Automated checks are followed by contact sheets, transition strips, and real-time
recording review. Human review records named findings and timestamps.

## Animation Direction Review

Audiobook sequences must demonstrate:

- deliberate staging and use of stillness;
- readable anticipation, gesture stroke, hold, and recovery;
- gaze that serves thought, listener contact, and spatial reference;
- non-periodic blinks with suppression around accents and gaze shifts;
- emotional continuity across sentences/scenes;
- walking with planted contacts, weight shifts, stops, and turns;
- speech/viseme timing that survives pause/seek/rate changes;
- no constant motion, random gesture selection, or mechanical repetition.

Music sequences must demonstrate:

- stable tempo/beat/bar/phrase/section mapping;
- continuous phase and contact through loops and transitions;
- materially different choreography by section and energy;
- restrained quiet passages and authored high-energy peaks;
- a coherent ending rather than abrupt idle reset;
- reduced-motion choreography that remains musical.

## Transcript And Analysis QA

- Verify provided and generated transcript coverage against decoded duration.
- Flag low-confidence, omitted, duplicated, drifted, wrong-language, and
  chapter-mismatch spans.
- Test chunk overlaps with speech crossing both boundaries.
- Cancel and resume without losing or duplicating words.
- Record engine/model/config/hash and uncertain spans.
- Validate LLM JSON strictly; retry or fail visibly on schema errors.
- Run independent critique/correction and preserve both versions.
- Re-run identical inputs/configuration and prove stable deterministic compiler
  output after structured analysis is accepted.

## Music Analysis QA

- Synthetic impulses validate sample/time conversion and onset localization.
- Click tracks cover common meters, tempo ramps, silence, pickup beats, and endings.
- Golden licensed/local fixtures cover dense, quiet, syncopated, and weak-onset music.
- Compare tempo and beat candidates with at least one independent offline oracle;
  record disagreement rather than tuning to one file.
- Section boundaries and energy curves receive human review.

## Privacy, Governance, And Whiz

### Existing Server Whisper Security Gate

Server transcription is accepted only when an automated Rust integration harness
proves all of the following against a disposable server job root:

- validated HTTPS rejects an untrusted certificate, hostname mismatch, downgrade,
  plaintext non-loopback URL, and missing/incorrect transcription credential;
- the packaged client contains no SSH private key material and makes no runtime SSH
  invocation; `CRX41_HETZNER_SSH` is visible only to deployment CI;
- the runtime credential cannot access deployment or unrelated Wizard routes;
- job directories and files are owner-only and every CLI invocation bypasses a shell;
- success and acknowledged cancellation remove media, PCM, CLI output, and transcript
  fragments immediately, with a content-free deletion receipt;
- simulated crash/abandonment followed by janitor time advancement removes every job
  at the exact one-hour boundary and preserves nothing after it;
- audit output contains hashes, tool/model identity, byte counts, timing, disposition,
  and deletion receipt but no media bytes, decoded text, transcript fragments, URL,
  bearer token, or filesystem secret;
- retries, chunk overlap, cancellation, resume, response truncation, disk exhaustion,
  malformed CLI output, and worker restart remain bounded and deterministic.

Required evidence includes the server executable/model inventory and hashes, TLS and
credential negative-test ledger, permission-mode ledger, deletion/janitor ledger,
content-scan report, bounded resource metrics, and the exact Rust test command/output.

- No media/transcript upload without explicit provider disclosure and approval.
- Logs and telemetry contain hashes/IDs, not book text, credentials, or local paths.
- Whiz is disabled for missing/invalid URL.
- Reject `file`, `javascript`, `data`, credentials, malformed host, control
  characters, overlong URL, stale metadata revision, and arbitrary frontend URL.
- Prove each successful open has explicit user correlation, permit, policy result,
  URL hash, media ID, and audit record.
- Prove Wizard cannot invoke the action.
- Prove permits expire at 10 seconds or less, are single-use, fail on replay or
  metadata revision mismatch, and produce one immutable audit outcome.

## Accessibility And Platform Matrix

Conformance target is WCAG 2.2 Level AA. Automated browser checks use axe-core
`4.10.3`; the release limit is zero incomplete critical/serious findings and zero
confirmed WCAG A/AA violations. Text contrast is at least 4.5:1, large text and
meaningful UI graphics at least 3:1, and focus indicators at least 3:1 against
adjacent colors with a minimum two-CSS-pixel perimeter.

The frozen V1 runtime matrix is:

- hosted: Playwright `1.55.0`, Chromium `140.0.7339.16`, 1280x720 and 320x720
  viewports, on Ubuntu 24.04 x86_64;
- desktop: packaged PrismGT on macOS 26.3 build `25D5112c`, arm64, using the
  bundled system WebView, at 100% and 200% zoom;
- dependency-only: Rust `1.75.0` build/contract suites on Ubuntu 24.04 x86_64 and
  Windows 11 24H2 x86_64. These rows do not claim a Linux/Windows desktop package.

Run every player and Whiz flow in hosted Chromium and the packaged desktop app:

- all controls reachable in logical order with keyboard alone;
- visible focus never clipped or hidden by the stage;
- Space/Enter activation is single-fire; Escape cancels dialogs/pending opens;
- buttons expose stable accessible names, pressed/disabled/busy states, and live
  errors without stealing focus;
- seek/rate/chapter/character/mode/intensity/reduced-motion controls work at 200%
  zoom and 320 CSS px width without overlap;
- reduced-motion preference is honored at initial load and live changes;
- hosted Whiz uses the synchronous blank-window permit flow; desktop Whiz uses
  the governed shell opener; popup denial, permit denial, timeout, and opener
  failure are visible and leave playback unchanged.

## Performance And Resource Gates

- Render/simulation frame budget measured with scheduler active.
- Cue lookup bounded by indexed score tracks, not full-score scans each frame.
- No transcription, decode, JSON parse, file IO, network, or LLM work on render path.
- Queue, history, telemetry, checkpoint, and cache bounds tested at limits.
- Negotiated payload limit is 256 KiB, in-flight command limit is 128, snapshot
  active-cue limit is 4,096, and bounded inbox overflow fails without mutation.
- Long audiobook range streaming does not load the complete file into memory.
- Record idle/playing/preprocessing CPU, RSS, peak RSS, binary size, model size,
  score size, startup, score preload, and reconnect latency.

## Build, Package, And Reproduction

- Rust format, Clippy with warnings denied, focused tests, full workspace tests,
  release builds, frontend tests, browser tests, and protocol compatibility pass.
- Clean-clone build works using documented toolchain and asset acquisition.
- Packaged macOS 26.3 arm64 app launches outside source tree and locates managed
  dependencies. Linux and Windows satisfy locked build/contract gates only in V1.
- Installed app version, binary hashes, sidecar hashes, and model hashes recorded.
- Public/deployed endpoint reports expected release SHA and health.
- Rollback to the prior release is exercised, not merely described.

## Final Acceptance Matrix

Each requirement is one of `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`, or
`NOT_APPLICABLE`, with evidence path and SHA-256. There is no aggregate PASS while
any blocking row is `FAIL`, `BLOCKED`, or `NOT_RUN`.
