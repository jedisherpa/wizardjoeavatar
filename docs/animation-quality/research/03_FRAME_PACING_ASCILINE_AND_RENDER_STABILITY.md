# Frame Pacing, ASCILINE, and Render Stability

Research date: 2026-07-12

Repository baseline:

- WizardJoeAvatar branch: `codex/build-repeatable-avatar-animation`
- WizardJoeAvatar recorded base commit: `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1`
- ASCILINE checkout: `external/ASCILINE`
- ASCILINE branch: `main`
- ASCILINE commit: `05cc6ebd2152f5987ab348038d5619d279ecec27`
- ASCILINE worktree at inspection: clean

This report is research and diagnosis only. It does not implement runtime
changes. It covers the ten items required by `goal-objective.md` section 5 and
maps them to the checked-out implementation.

## Executive Conclusion

The current visible instability is not one animation problem. It is a compound
failure across source clocking, fanout, adaptive-codec ownership, browser queue
management, and presentation framing.

The most consequential finding is stronger than the baseline ledger states:
with two clients, each connection's ticker advances the one shared source and
encoder. If client A receives frame 0, client B may cause frame 1 to be encoded
against frame 0 and receive it, then client A may receive frame 2 encoded
against frame 1. Client A applies frame 2 to frame 0 and reconstructs the wrong
image. WebSocket has preserved the messages sent to A; the application has
created a delta-base gap by distributing consecutive members of one global
delta chain among different clients. This connects ANIM-GLITCH-001 directly to
the torn or flashing frames attributed to ANIM-GLITCH-003 and 004.

The required architecture is:

```text
one 60 Hz semantic simulation clock
    -> one 24/30 Hz render sampler per output profile
    -> one immutable raw cell frame per channel sequence
    -> one canonical adaptive encoding per channel sequence
    -> bounded fanout to all clients
    -> per-client bootstrap/resync keyframe without mutating channel history
    -> one ordered, bounded decode worker per browser connection
    -> bounded decoded presentation queue
    -> one requestAnimationFrame presentation loop
    -> fixed stage-to-canvas transform and atomic back-buffer swap
```

This preserves server authority, direct ASCILINE frames, deterministic replay,
and the requirement to encode once and fan out. A client that misses any shared
delta must not receive later deltas until it gets a full current-frame resync.

## Evidence Boundaries

### Directly observed in current source and baseline evidence

- Every WizardJoe WebSocket connection owns a ticker and calls the shared
  `next_encoded_frame`.
- `next_frame` advances semantic simulation by `1 / fps`.
- One `prev_encoded_frame` is shared by every connection.
- Every new connection clears that shared encoder history.
- The browser serializes decode through one Promise chain, but the chain is
  unbounded and paints as soon as decode completes.
- The browser has no sequence, base-sequence, epoch, or dimension validation.
- The browser computes a new content bounding box, scale, and center every
  frame.
- A separate 24 Hz HTTP state poll applies CSS translation, rotation, scale,
  mouth, eye, shadow, and effect transforms outside the decoded frame timeline.
- The baseline recorded 13 `Delta frame without previous frame` errors, 30-47
  browser renders per second for a nominal 24 FPS source, and sequence advances
  incompatible with one authoritative stream.

### Inferences that require the tests specified below

- A partially drawn screenshot is not by itself proof that Canvas displayed a
  half-painted `fillRect` loop. Browser rendering normally occurs at event-loop
  rendering opportunities. Delta corruption, stale state overlays, and the
  dynamic crop can produce a similar symptom. Back-buffer hashes are required
  to classify it.
- ASCILINE production `app.js` launches stateful adaptive decodes concurrently.
  The decode completions can race because each `DecompressionStream` is
  asynchronous; the current code does not prove a stable completion order.
- The best queue depths below are initial engineering parameters, not values
  mandated by a Web standard. They must be validated under the project browser
  and device matrix.

## Current Pipeline Trace

### WizardJoe server and codec

1. `AppState` owns one `Arc<Mutex<ProceduralWizardFrameSource>>`
   (`rust/wizard_avatar_engine/src/server.rs:19-30`).
2. Each `handle_socket` resets that source's encoder
   (`server.rs:267-271`).
3. Each connection creates a Tokio interval at source FPS
   (`server.rs:285-290`).
4. Each interval tick locks the same source and calls
   `next_encoded_frame` (`server.rs:303-307`).
5. `next_frame` advances the controller by exactly `1 / fps`
   (`rust/wizard_avatar_engine/src/frame_source.rs:114-117`).
6. `next_encoded_frame` encodes against the one shared
   `prev_encoded_frame`, replaces it with `shown_frame`, and increments the one
   global `frame_index` (`frame_source.rs:135-162`).
7. The adaptive header contains only `frame_index`, tag, and payload
   (`rust/wizard_avatar_engine/src/codec.rs:95-100`). It carries no stream epoch,
   base sequence, dimensions, cell size, presentation timestamp, or checksum.
8. Keyframes occur when history is absent, dimensions differ, or every 48
   frames (`codec.rs:132-146`). A reconnect clears shared history, but the next
   keyframe goes to whichever connection ticks first, not necessarily the new
   connection.

### WizardJoe browser

1. A WebSocket `ArrayBuffer` message is appended to `state.decodeQueue`, a
   Promise chain (`rust/wizard_avatar_engine/web/wizard.js:1096-1132`). This
   preserves decode invocation order for that chain.
2. `makeDecoder` stores one `previous` full frame and mutates it after each
   asynchronous inflate (`wizard.js:57-113`). It does not validate frame length,
   changed-cell bounds, monotonic sequence, expected base sequence, or current
   connection generation.
3. The Promise chain has no queue length, byte budget, age limit, or cancellation
   token. A decode error is logged, but no resync is requested and later deltas
   continue to be attempted.
4. Decode completion calls `renderFrame` immediately, outside
   `requestAnimationFrame` (`wizard.js:1120-1128`).
5. `renderFrameToAvatar` scans the entire 480 by 270 frame for non-white cells,
   adds a six-cell margin, chooses a new integer cell size, and recenters the
   result in a 1000 by 1000 canvas on every frame (`wizard.js:162-214`).
6. `startAvatarStateLoop` independently polls semantic state at 24 Hz
   (`wizard.js:1063-1083`) and `applyAvatarState` applies another world transform
   plus client-clock overlays (`wizard.js:983-1061`). The HTTP response has no
   frame sequence tying it to the visible ASCILINE frame.
7. `ws.onopen` starts a command tour automatically (`wizard.js:1102-1106`), so
   every browser client becomes a competing command producer.

### Exact ASCILINE revision

The checked-out ASCILINE server gives each connection local `prev_frame` state
and implements client-reported backlog shedding. When frames are skipped, it
holds `prev_frame`; the next sent delta is therefore encoded against the last
frame that client actually received
([server lines 756-780](https://github.com/YusufB5/ASCILINE/blob/05cc6ebd2152f5987ab348038d5619d279ecec27/stream_server.py#L756-L780),
[drop loop lines 875-907](https://github.com/YusufB5/ASCILINE/blob/05cc6ebd2152f5987ab348038d5619d279ecec27/stream_server.py#L875-L907)).
Its shipped gap test proves that policy reconstructs the post-gap frame exactly
([test_backpressure_gap.js](https://github.com/YusufB5/ASCILINE/blob/05cc6ebd2152f5987ab348038d5619d279ecec27/test/test_backpressure_gap.js)).

However, ASCILINE's production browser path is not a drop-in quality model:

- The stateful codec explicitly says decoding must stay in arrival order
  ([codec.js lines 14-15](https://github.com/YusufB5/ASCILINE/blob/05cc6ebd2152f5987ab348038d5619d279ecec27/codec.js#L14-L15)).
- `app.js` starts each decode independently and pushes on asynchronous
  completion
  ([app.js lines 277-287](https://github.com/YusufB5/ASCILINE/blob/05cc6ebd2152f5987ab348038d5619d279ecec27/app.js#L277-L287)).
- Its `frameBuffer` trimming runs immediately after decode launch, before the
  asynchronous callback pushes the decoded frame, so it does not strictly
  bound that path
  ([app.js lines 277-300](https://github.com/YusufB5/ASCILINE/blob/05cc6ebd2152f5987ab348038d5619d279ecec27/app.js#L277-L300)).
- Backpressure reports only `framesInFlight`, not decoded presentation depth or
  oldest-frame age
  ([app.js lines 431-443](https://github.com/YusufB5/ASCILINE/blob/05cc6ebd2152f5987ab348038d5619d279ecec27/app.js#L431-L443)).

WizardJoe should reuse the correct last-sent-base and slow-client principles,
not copy the unordered browser decode path or ASCILINE's connection-local video
playback model.

## Defect Causality Matrix

| Defect | Confirmed contribution from this research scope | Classification |
| --- | --- | --- |
| ANIM-GLITCH-001 | Per-client tickers advance one simulation and divide one delta chain among clients. Mutex serialization prevents data races but not semantic over-advancement or missing delta bases. | simulation, fanout, transport |
| ANIM-GLITCH-002 | Each `onopen` starts a repeating tour. Multiple clients issue unrelated semantic commands, making frame captures and interruption timing non-reproducible. | command ownership, asynchronous state |
| ANIM-GLITCH-003 | A new client clears global history. The next keyframe is not targeted to that client, and existing clients can receive a delta based on a frame they never saw. | encoder ownership, resync |
| ANIM-GLITCH-004 | Wizard decode is ordered but unbounded; presentation is decode-driven rather than rAF-driven; there is no stale-frame policy, sequence gate, or atomic back buffer. Delta-base corruption from 001/003 can masquerade as a Canvas tear. | decode queue, presentation, transport |
| ANIM-GLITCH-005 | Per-frame tight crop changes the camera transform when silhouette, staff, shadow, or effects change. A second unsequenced CSS world transform compounds the reframing. | compositor, coordinate space, asynchronous state |
| ANIM-GLITCH-011 | `next_frame` advances simulation once per render request, so simulation rate equals aggregate client demand rather than a fixed clock. | clock ownership, simulation |
| ANIM-GLITCH-016 | Existing tests cover codec round trips and one-client streaming but do not exercise multi-client timing, missing-base recovery, queue bounds, browser rAF presentation, fixed framing, or long-run behavior. | verification gap |

WebSocket itself is ordered. RFC 6455 requires message fragments to be delivered
in sender order, and the protocol presents complete application messages in
sequence ([RFC 6455 sections 5.4 and 6.2](https://www.rfc-editor.org/rfc/rfc6455.html)).
Therefore WizardJoe sequence gaps on one connection should be treated as an
application fanout/drop event, not ordinary network reordering.

## 1. Specific Audit Checklist for the Current ASCILINE Path

Every checkbox is a release gate, not a suggestion.

### Source clock and fanout

- [ ] Exactly one task owns the 60 Hz semantic simulation clock per avatar
  channel.
- [ ] Simulation advances from a monotonic accumulator, never from WebSocket
  connection count or render request count.
- [ ] Exactly one render sample is produced per channel at each 24/30 Hz source
  deadline.
- [ ] Two or more clients observe the same channel sequence and identical
  canonical encoded bytes for the same sequence.
- [ ] Adding or removing clients does not alter `time_seconds`, path duration,
  walk phase, blink timing, speech timing, or action timers.
- [ ] The shared source mutex is not held across socket I/O.
- [ ] One slow client cannot block the simulation, render producer, encoder, or
  healthy clients.

### Encoder and protocol

- [ ] Canonical channel encoder history is mutated only by the channel encoder.
- [ ] A reconnect bootstrap keyframe is generated from a cached full frame and
  does not reset or advance canonical encoder history.
- [ ] Bootstrap subscription is atomic: the receiver gets full sequence N, then
  only messages newer than N.
- [ ] Header identifies stream/channel epoch, sequence, base sequence,
  presentation time or simulation tick, dimensions, cell byte width, and
  keyframe/full-frame status.
- [ ] A delta explicitly names the full-frame sequence it depends on.
- [ ] Any dimension, palette-layout, cell-width, or stream-epoch change forces a
  full frame and clears incompatible client state.
- [ ] Payload length, run length, index count, changed-cell index bounds, and
  decompressed size are validated before mutation.
- [ ] Periodic full frames bound recovery time; the current 48-frame interval is
  about 2 seconds at 24 FPS and must be measured against acceptable recovery
  latency.

### Per-client slow-path behavior

- [ ] Each client has a bounded outbound queue or bounded broadcast receiver.
- [ ] Lag is detected explicitly, not inferred only from socket closure.
- [ ] If a client misses a canonical delta, later deltas are withheld until a
  current full-frame resync is sent.
- [ ] Persistent lag causes profile downgrade or disconnect, never unbounded
  memory growth.
- [ ] Slow-client policy cannot modify global simulation time or canonical
  encoder history.

Tokio's bounded broadcast channel is directly suitable for one-producer,
multi-consumer fanout. Its documented `RecvError::Lagged` tells a receiver that
old messages were evicted, allowing the receiver to enter resync instead of
silently applying a broken delta chain
([Tokio broadcast documentation](https://docs.rs/tokio/latest/tokio/sync/broadcast/)).

### Browser decode

- [ ] One connection owns one decoder instance and one generation token.
- [ ] WebSocket handlers only validate/enqueue; they never paint.
- [ ] Exactly one decode operation is active per decoder.
- [ ] Wire queue is bounded by message count, bytes, and oldest-frame age.
- [ ] Sequence is strictly increasing within a stream epoch.
- [ ] Duplicate or stale sequences are discarded and counted.
- [ ] A missing base, unexpected dimension, invalid payload, or decode failure
  enters `awaiting_keyframe` and emits one resync request.
- [ ] Old Promise completions cannot write into a new connection generation.
- [ ] `INIT` or reconnect clears wire queue, decoded queue, decoder history, and
  presentation state before accepting deltas.
- [ ] `DecompressionStream` support is feature-detected; fallback decoding is
  tested with the same vectors.

The Compression Standard defines `deflate` as RFC 1950 zlib data and makes
invalid checksums an error
([WHATWG Compression Standard](https://compression.spec.whatwg.org/)). Error
handling must therefore be an expected state transition, not only a console
log.

### Browser presentation and framing

- [ ] One continuous `requestAnimationFrame` loop owns visible Canvas commits.
- [ ] The loop presents at most one source frame per callback.
- [ ] A decoded frame is selected by source timestamp/sequence, not Promise
  completion time.
- [ ] The complete logical frame is drawn into a back buffer before one visible
  commit.
- [ ] Stage-to-canvas crop, scale, and root are stable across poses and effects.
- [ ] No HTTP-polled CSS transform independently moves or scales the same avatar
  represented by the ASCILINE frame.
- [ ] Cell coordinates and destination rectangles are integer-aligned.
- [ ] Canvas backing dimensions account for device pixel ratio without changing
  the logical cell transform frame to frame.
- [ ] `imageSmoothingEnabled` is false for bitmap scaling and CSS uses a tested
  cell-preserving image-rendering mode.
- [ ] Visibility changes and Canvas context loss trigger queue clear plus
  keyframe resync before rendering resumes.

## 2. Recommended Frame Queue Behavior

Use two bounded queues with different legal drop rules.

### Queue A: encoded dependency queue

- Initial capacity: 4 encoded frames or 2 MiB, whichever is reached first.
- Age limit: 250 ms at the time of audit; target steady-state age is at most two
  source intervals.
- Consumer: one sequential decoder loop.
- Legal drop rule: do not remove an arbitrary delta and continue decoding later
  deltas. On overflow, clear the encoded queue, set `awaiting_keyframe`, request
  a current full-frame resync, and ignore deltas until it arrives.
- A full frame may replace all queued older data because it resets decode state.
- Track queue depth, queued bytes, oldest age, peak depth, overflow count,
  resync count, and decode service time.

The classic WebSocket API exposes outbound `bufferedAmount`, but no equivalent
receiver-side desired-size/backpressure control
([WebSockets Standard](https://websockets.spec.whatwg.org/)). The application's
own bounded queue and explicit backlog/resync message are therefore required.
The Streams Standard defines the relevant high-water-mark model: queue size is
compared with a fixed limit and `desiredSize` communicates pressure
([WHATWG Streams Standard, internal queues](https://streams.spec.whatwg.org/#internal-queues)).

### Queue B: decoded presentation queue

- Capacity: 2 full logical frames: current candidate and newest future frame.
- Dropping decoded frames is safe because each entry is already a complete
  framebuffer.
- Keep entries sorted by source sequence/timestamp.
- On each rAF callback, discard all decoded frames older than the newest frame
  whose presentation time is not in the future, then present that newest due
  frame.
- Never render a frame with a sequence less than or equal to the last presented
  sequence.
- Do not let decoded queue depth feed back into semantic simulation time.

Initial jitter target: 2 source frames, about 83 ms at 24 FPS or 67 ms at 30
FPS. This is a tuning starting point for stable local playback, not a fixed
product requirement. Interactive chatbot mode should reduce toward one frame
when decode p95 stays below half a source interval.

## 3. Recommended Render-Loop Behavior

The browser needs one presentation owner:

```javascript
function onAnimationFrame(rafNow) {
  requestAnimationFrame(onAnimationFrame);

  const mediaNow = presentationClock(rafNow);
  const due = presentationQueue.takeNewestDue(mediaNow);
  if (!due || due.sequence <= lastPresentedSequence) return;

  drawLogicalCellsIntoBackBuffer(due.frame, fixedViewport);
  commitBackBufferToVisibleCanvas();
  lastPresentedSequence = due.sequence;
}
```

`requestAnimationFrame` callbacks are collected in an ordered callback map and
invoked with the rendering timestamp
([HTML animation frames](https://html.spec.whatwg.org/multipage/imagebitmap-and-animations.html#animation-frames)).
The source frame rate remains 24/30 FPS; a 60/120 Hz rAF loop holds the current
source frame when no newer frame is due.

Recommended Canvas path:

1. Build a cell-resolution back buffer or `ImageData`, one logical pixel/block
   per cell.
2. Draw the entire back buffer from the immutable decoded frame.
3. Scale to the visible Canvas in one `drawImage`, with an integer-aligned fixed
   destination rectangle.
4. Set `imageSmoothingEnabled = false`. The HTML Canvas specification requires
   nearest-neighbor interpolation for scaled-up images when smoothing is false
   ([Canvas image smoothing](https://html.spec.whatwg.org/multipage/canvas.html#dom-context-2d-imagesmoothingenabled)).
5. Use `OffscreenCanvas` when available, or a detached regular Canvas fallback.
   `OffscreenCanvas` can run in a worker and can transfer a completed
   `ImageBitmap`
   ([HTML OffscreenCanvas](https://html.spec.whatwg.org/multipage/canvas.html#the-offscreen-canvas-interface)).
6. Preserve the fixed white stage and floor. Do not find visible bounds every
   frame. If an avatar-only viewport is required, define one constant crop from
   the maximum authored stage envelope and world projection.

CSS `image-rendering: pixelated` preserves the cell-grid intent, but non-integer
scales can still create uneven source-cell sizes. Prefer integer destination
multiples where layout permits
([CSS Images `image-rendering`](https://drafts.csswg.org/css-images-3/#the-image-rendering)).

## 4. Recommended Interpolation Policy

Do not crossfade or bilinearly interpolate full ASCILINE cell framebuffers.
That would invent colors, soften cells, and make glyph/cell occupancy
nondeterministic.

Use this split:

- Semantic simulation: fixed 60 Hz on the server.
- Render sampling: at each 24/30 Hz deadline, sample or interpolate continuous
  semantic values between fixed simulation states before cell quantization.
- Discrete channels: facing, pose ID, expression, mouth shape, staff mode, and
  layer order change only under the animation graph's deterministic transition
  rules.
- Browser: no semantic interpolation. Select and hold complete server frames by
  presentation timestamp.
- Root and depth: interpolation occurs in server world/projection space, then
  coordinates and scale are quantized once by the canonical renderer.

If frame N is late but frame N+1 is ready, present N+1 when due. Do not fabricate
an intermediate cell image. This keeps source authority and allows the source
animation reports to own pose blending while this transport layer owns pacing.

## 5. Recommended Frame-Dropping Policy

There are three distinct drop points:

1. Before canonical render: the shared producer may skip an overdue render
   deadline while the 60 Hz simulation continues. It must render the latest
   current semantic state and increment a documented source sequence/timestamp.
2. Before decode: arbitrary delta dropping is forbidden. A dropped encoded
   dependency requires a full-frame resync before decoding resumes.
3. After decode: obsolete complete frames may be dropped freely from the
   presentation queue.

For a shared encoded channel, a lagging broadcast receiver that reports
`Lagged` must:

```text
stop forwarding canonical deltas
clear its pending socket queue
send a full cached current frame at sequence N
resume canonical broadcast at the first sequence greater than N
```

Do not reset the channel encoder. Do not let a slow viewer slow the channel.
After repeated resyncs in a bounded window, downgrade that viewer to a lower
profile or close it with a retryable overload reason.

ASCILINE's connection-local video server can safely skip source frames while
holding that client's `prev_frame`. WizardJoe's encode-once fanout cannot skip a
different arbitrary delta for each viewer without either a resync keyframe or a
per-client encoder. The resync approach preserves the documented one-encode
fanout contract.

## 6. Recommended Resynchronization Behavior

Define these client states:

```text
DISCONNECTED
AWAITING_INIT
AWAITING_KEYFRAME
DECODING
PRESENTING
RESYNC_REQUESTED
```

Resync triggers:

- new connection or reconnect
- connection generation/stream epoch change
- sequence regression or duplicate storm
- delta whose `base_sequence` is not the decoder's current full sequence
- missing delta or outbound broadcast lag notification
- decode exception, invalid payload, decompressed-size mismatch, or out-of-range
  cell index
- columns, rows, cell byte width, palette layout, or codec version change
- queue overflow or oldest encoded frame older than 250 ms
- tab resume after hidden suspension
- Canvas context loss/restoration

Resync protocol:

1. Client increments local generation, clears queues/history, and sends one
   `resync` command carrying stream epoch and last valid sequence.
2. Server atomically snapshots current full frame N and subscribes that client
   to messages after N.
3. Server sends a full-frame message marked with epoch and sequence N.
4. Client validates dimensions and payload, installs it as decoder base, draws
   it into the back buffer, and changes to `DECODING`/`PRESENTING`.
5. Deltas with sequence greater than N and matching base chain are accepted.
6. Any Promise completion from an older generation is discarded before it can
   mutate decoder or Canvas state.

A decoder refresh point is, by definition, data that completely resets the
decoder to a known state
([RFC 8082 section 3](https://www.rfc-editor.org/rfc/rfc8082.html#section-3)).
WizardJoe full frames serve that role. Periodic full frames remain useful, but
explicit resync is required; waiting up to two seconds after a known mismatch
needlessly freezes a chatbot avatar.

## 7. Distinguishing Source-Animation Defects from Transport Defects

Capture three synchronized artifacts for every test sequence:

```text
A. source frame: raw Rust cell bytes before adaptive encoding
B. decoded frame: browser decoder full bytes before presentation
C. presented frame: logical back-buffer bytes plus fixed viewport metadata
```

For every sequence, record:

- stream epoch
- source sequence
- simulation tick/time
- presentation timestamp
- semantic state snapshot hash
- dimensions and cell byte width
- CRC32 or BLAKE3 of A, B, and C logical cells
- root cell, feet cells, crop rectangle, scale, and last presented sequence

Classification algorithm:

```text
if A already contains the pop/tear/anchor jump:
    source animation, simulation, state machine, pose, or projection defect
else if hash(A) != hash(B):
    codec, missing-base, ordering, corruption, or resync defect
else if hash(B) == hash(A) and logical hash(C) differs:
    browser renderer, crop, overlay, scaling, or presentation defect
else if A == B == C but display timing is irregular:
    pacing, queue age, rAF scheduling, or audio-clock defect
else if multiple clients produce different A for the same channel tick:
    source clock or fanout ownership defect
```

Run the same deterministic semantic command log in two modes:

- Offline: direct Rust frames with no WebSocket or browser.
- Live: real adaptive WebSocket, shipped decoder, and real Canvas back buffer.

The offline and live A hashes must match by simulation tick. This prevents a
transport fix from concealing a genuine gait or pose defect and prevents source
animation work from being blamed for a corrupted delta chain.

RTP's separation of sequence number, media timestamp, and arrival jitter is the
right diagnostic model even though WizardJoe uses reliable WebSocket transport.
RFC 3550 defines sequence for loss/order detection and a timestamp from a
monotonic media clock, and provides the interarrival-jitter estimator
`J = J + (|D| - J) / 16`
([RFC 3550](https://www.rfc-editor.org/rfc/rfc3550.html)). Record both source
timestamp variance and arrival variance; do not collapse them into one FPS
counter.

## 8. Performance Instrumentation Requirements

### Server per channel

- simulation tick count and catch-up steps
- simulation deadline miss count and maximum lag
- rendered source sequence and render duration p50/p95/p99
- encode duration p50/p95/p99 by tag
- raw bytes, encoded bytes, changed cells, and keyframe count
- current stream epoch and latest cached full-frame sequence
- subscriber count and canonical fanout sequence

### Server per client

- outbound queue messages/bytes/oldest age/peak
- last enqueued and last sent sequence
- lag events, dropped canonical messages, bootstrap keyframes, resyncs, and
  profile downgrades
- socket send duration and close reason
- client-reported encoded depth, decoded depth, presentation depth, and oldest
  age

### Browser

- WebSocket arrivals per second and interarrival jitter
- last received, decoded, enqueued, and presented sequence
- sequence gaps, stale/duplicate messages, missing-base events, decode errors,
  invalid payloads, and resync latency
- encoded queue count/bytes/age and decoded queue count/age
- inflate/decode duration p50/p95/p99
- back-buffer draw duration, visible commit duration, and rAF interval histogram
- source-to-present latency and dropped-after-decode count
- fixed viewport/crop ID, logical cell scale, device pixel ratio, context loss,
  visibility transitions, and reconnect count
- long-task count and duration

Use `performance.now()` for local durations; High Resolution Time requires it to
use a monotonic clock not subject to system clock adjustment
([High Resolution Time](https://www.w3.org/TR/hr-time-3/#sec-monotonic-clock)).
Use `PerformanceObserver` and User Timing marks instead of permanent polling
for browser profiling
([Performance Timeline](https://w3c.github.io/performance-timeline/)). The Long
Tasks API reports main-thread tasks over 50 ms, including rendering work, which
is directly relevant to a 24/30 FPS Canvas budget
([Long Tasks API](https://www.w3.org/TR/longtasks-1/)).

Long-run acceptance:

- 30-minute browser test in normal CI; 2-hour nightly soak.
- Queue depths remain within configured capacities for the entire run.
- No sequence regression, missing-base decode, unhandled rejection, or Canvas
  context error.
- No client changes channel simulation rate.
- After a five-minute warm-up, retained JS heap and process RSS have no sustained
  positive linear trend attributable to frames; record slope and final delta
  rather than relying on one absolute memory threshold.
- Healthy-client p99 source-to-present latency remains bounded when another
  client is deliberately slowed.

## 9. Browser Compatibility Considerations

Required matrix:

- Current stable Chrome/Chromium, Firefox, and Safari on desktop.
- At least one mobile WebKit or Chromium browser if the avatar is product-facing
  there.
- 1x and 2x device pixel ratio.
- 60 Hz and 120 Hz displays where available.
- foreground, hidden for at least 30 seconds, then resumed.
- normal CPU and at least 4x CPU throttling.

Compatibility rules:

- Feature-detect `DecompressionStream`, `OffscreenCanvas`, worker rAF,
  `transferToImageBitmap`, and `PerformanceObserver` entry types.
- Keep a regular detached Canvas fallback when OffscreenCanvas is unavailable.
- Run the same codec vectors against native `DecompressionStream` and fallback
  inflate implementation.
- Do not assume rAF equals source FPS or display FPS. Hidden documents are
  excluded from normal rendering updates by the HTML event-loop rendering
  model
  ([HTML rendering update filtering](https://html.spec.whatwg.org/multipage/webappapis.html#update-the-rendering)).
  On visibility resume, discard stale queues and resync.
- Handle `contextlost` and `contextrestored`; Canvas defines loss state and
  OffscreenCanvas exposes restoration events
  ([HTML Canvas](https://html.spec.whatwg.org/multipage/canvas.html)).
- Keep logical frame hashes independent of device pixel ratio and browser color
  management. Compare cell RGB bytes before display conversion.
- Avoid per-frame CSS layout changes. The current crop and CSS transform path
  should be replaced by one fixed logical transform owned by the renderer.

## Audio and Lip-Sync Clock Policy

This is part of sections 3, 4, and 8 but is explicit because speech timing is a
goal requirement.

- The server remains authoritative for speech ID, phoneme/mouth intervals, and
  semantic animation state.
- The client maps the server speech timeline once to the actual audio playback
  clock, then chooses the due server frame/mouth interval during rAF.
- For Web Audio, schedule against `AudioContext.currentTime`; use
  `getOutputTimestamp()` to estimate the corresponding performance timeline.
  The Web Audio specification defines both time domains and their mapping
  ([Web Audio API 1.1](https://www.w3.org/TR/webaudio-1.1/#dom-audiocontext-getoutputtimestamp)).
- For an `HTMLMediaElement`, use `currentTime` as master playback position and
  sample it in rAF. Do not use `timeupdate` as a lip-sync clock; W3C media-timed
  event requirements document its coarse and variable update behavior
  ([Media Timed Events section 5.3](https://www.w3.org/TR/media-timed-events/#polling-the-current-position-on-the-media-timeline)).
- Detect seeks, pauses, underruns, and clock discontinuities. Clear future mouth
  presentation state and remap the timeline rather than allowing a jump to
  replay stale shapes.
- Never add a separate client wall-clock sine wave to mouth or whole-avatar root
  motion. That would be neither audio-synchronized nor deterministic.

## 10. Automated Tests Required to Prove Stability

Tests must use the production Rust encoder, production browser decoder, and
production Canvas renderer. A test-only decoder or renderer does not satisfy
these requirements.

### Server clock and fanout

`WIZ-PACE-001 single simulation owner`
: Run the same command log for five wall-clock seconds with zero, one, two, and
four clients. Simulation ticks, semantic time, path distance, walk phase, and
action expiry must match within one fixed simulation tick.

`WIZ-PACE-002 byte-identical fanout`
: Two healthy clients subscribed to one channel must receive identical epoch,
sequence, tag, and canonical encoded bytes for at least 500 consecutive frames.

`WIZ-PACE-003 healthy client isolated from slow client`
: Add a client that sleeps on reads. Healthy-client sequence cadence and
source-to-present p99 must remain within the declared budget; channel simulation
must not slow or accelerate.

`WIZ-PACE-004 bounded server queues`
: Saturate a client for 60 seconds. Its outbound queue never exceeds configured
messages or bytes; lag yields a resync/downgrade/close, not growth.

### Keyframe, delta, and reconnect

`WIZ-RESYNC-001 reconnect isolation`
: Reconnect B while A decodes continuously. B's first binary frame is a full
current frame. A remains bit-exact with the source and sees no history reset.

`WIZ-RESYNC-002 missing-delta recovery`
: Remove one delta before browser decode. The client must not present any later
delta-derived image, must send one resync request, and must recover bit-exactly
on the returned full frame.

`WIZ-RESYNC-003 atomic bootstrap race`
: Connect repeatedly at every possible point around channel publish. Each new
client gets full N followed only by sequences greater than N, with no missing
base.

`WIZ-RESYNC-004 dimension/epoch change`
: Change dimensions or stream epoch while an old inflate Promise is delayed.
The old completion is ignored; the new decoder accepts only a full matching
frame and allocates exactly the declared size.

`WIZ-RESYNC-005 corrupt payload validation`
: Fuzz truncated headers, invalid zlib, malformed RLE, non-integral delta body,
out-of-range indices, oversized output, duplicate and regressing sequences.
Each fails closed into bounded resync without an unhandled rejection or partial
Canvas write.

### Browser decode queue and ordering

`WIZ-DECODE-001 adversarial async completion`
: Stub inflate to resolve frame work in reverse and randomized delays. The
single decoder must invoke and commit frames in sequence, or reject and resync;
it must never mutate `previous` out of order.

`WIZ-DECODE-002 queue capacity`
: Deliver at 5x source rate with 4x decode slowdown. Encoded queue count, bytes,
and age stay bounded; overflow follows the declared full-frame resync policy.

`WIZ-DECODE-003 stale connection generation`
: Close/reconnect with old decodes pending. No old generation may change decoder
history, diagnostics, presentation queue, or Canvas.

`WIZ-DECODE-004 shipped ASCILINE vectors`
: Decode raw, zlib, delta, RLE, periodic keyframe, and post-gap vectors using the
exact browser module shipped by WizardJoe and compare every cell byte.

### Presentation and fixed composition

`WIZ-PRESENT-001 rAF-only commit`
: Instrument Canvas methods. WebSocket and decode callbacks perform zero visible
Canvas writes. Each rAF callback performs at most one completed back-buffer
commit.

`WIZ-PRESENT-002 no stale presentation`
: Deliver delayed frames around a newer frame. Presented sequence is strictly
increasing and always the newest due complete frame.

`WIZ-PRESENT-003 fixed viewport`
: For one fixed root/depth, vary hat, beard, staff, shadow, mouth, cast sparks,
and all eight views. Viewport, root screen cell, stage scale, and floor contact
do not change because of content bounds.

`WIZ-PRESENT-004 nearest-neighbor cells`
: At every supported viewport and DPR, each source cell maps to one contiguous
axis-aligned destination block; output contains only source RGB values and white
background, with no blended edge colors.

`WIZ-PRESENT-005 back-buffer atomicity`
: Force yielding/instrumented delays during back-buffer construction and capture
every visible presentation. The visible Canvas is always either complete frame
N or complete frame N+1, never a mixture.

`WIZ-PRESENT-006 no unsequenced overlay motion`
: Given fixed decoded frame bytes, delayed or reordered state HTTP responses
cannot translate, scale, rotate, blink, mouth-animate, or add effects to the
visible avatar.

### Source-versus-transport classification

`WIZ-CLASSIFY-001 A/B/C hash parity`
: For every baseline transition and at least 1,000 walking frames, record raw
source A, decoded B, and logical presented C. Require A == B == C unless C has a
documented non-character UI layer excluded by mask.

`WIZ-CLASSIFY-002 offline/live semantic parity`
: Replay one deterministic command log offline and through real WebSocket. For
each simulation tick/render sequence, semantic snapshot hash and source A hash
match. A failure before encoding is automatically labeled source-animation;
A/B divergence is transport; B/C divergence is presentation.

`WIZ-CLASSIFY-003 multi-client visual parity`
: Four clients with mixed decode speeds must eventually present the same logical
current frame hash after every commanded stable-state checkpoint.

### Audio and lifecycle

`WIZ-SYNC-001 audio-clock mouth schedule`
: Drive a synthetic known audio clock with pause, resume, seek, and underrun.
Presented mouth interval error stays within one source-frame interval and never
alters root or locomotion phase.

`WIZ-LONGRUN-001 foreground soak`
: Thirty-minute CI and two-hour nightly run with motion, speech, reconnect, and
slow-client injections. Assert bounded queues, no decode errors, monotonic
sequence, stable simulation cadence, no unhandled rejection, and no sustained
post-warm-up memory slope.

`WIZ-LONGRUN-002 hidden/resume`
: Hide for 30 seconds while streaming, then show. The client clears stale data,
gets a current full frame, and resumes without fast-forward painting or delta
errors.

`WIZ-LONGRUN-003 Canvas context restore`
: Simulate context loss/restoration. No partially initialized frame is shown;
the renderer rebuilds buffers and presents only after keyframe resync.

Run browser tests in the compatibility matrix from section 9. Existing
`adaptive_websocket_reconstructs_wizard_frame` and
`websocket_accepts_semantic_commands_and_streams_updated_frames` remain useful
single-client smoke tests, but they cannot satisfy ANIM-GLITCH-016.

## Source-File Mapping

| Concern | Current WizardJoe source | Exact ASCILINE comparison | Required ownership after implementation |
| --- | --- | --- | --- |
| Simulation clock | `rust/wizard_avatar_engine/src/frame_source.rs:114-117` | `stream_server.py:646-655, 922-927` paces each connection's video | one fixed channel simulation task |
| Per-client ticker | `rust/wizard_avatar_engine/src/server.rs:267-320` | `stream_server.py:524-943` has connection-local playback | remove simulation/render advancement from socket tasks |
| Encoder history | `frame_source.rs:55-62, 135-162` | `stream_server.py:671-672` uses local `prev_frame` | canonical channel encoder plus non-mutating client bootstrap |
| Keyframe rule | `rust/wizard_avatar_engine/src/codec.rs:132-146` | `codec.py`/`codec.js`, interval 48 | full frame on interval, epoch change, and explicit resync |
| Protocol metadata | `codec.rs:95-100` | `external/ASCILINE/codec.js:7-15` | add epoch/base/timestamp/dimensions contract |
| Fanout/backpressure | no bounded fanout abstraction | `stream_server.py:756-780, 875-907` | bounded broadcast; lag enters resync |
| Browser decoder | `web/wizard.js:57-113` | `external/ASCILINE/codec.js:37-103` | one generation-scoped sequential decoder |
| Browser decode queue | `web/wizard.js:32-40, 1120-1132` | `external/ASCILINE/app.js:277-300` | explicit bounded encoded queue and worker |
| Render scheduling | `web/wizard.js:139-214, 1122-1128` | `external/ASCILINE/app.js:324-365` uses rAF/media time | rAF-only selection and atomic presentation |
| Dynamic crop | `web/wizard.js:162-214` | ASCILINE renders a fixed configured grid | fixed stage or fixed authored viewport |
| Duplicate client transform | `web/wizard.js:983-1083` | ASCILINE frame time drives its visible output | decoded frame is sole visual authority |
| Automatic commands | `web/wizard.js:1102-1106, 1174-1211` | not a codec concern | explicit single tour owner only |
| Current tests | `rust/wizard_avatar_engine/tests/websocket_stream.rs`, `rust_objective_contract.rs:219-249` | ASCILINE gap/live backpressure tests | add section 10 multi-client/browser/soak tests |

## Recommended Priority

1. Separate one fixed simulation/render producer from all socket tasks. This
   addresses ANIM-GLITCH-001 and 011 and prevents further transport diagnosis
   from being contaminated by client count.
2. Replace global reconnect reset with atomic full-frame bootstrap plus bounded
   fanout/resync. This addresses ANIM-GLITCH-003 and the multi-client delta-base
   corruption coupled to 001.
3. Add explicit sequence/base/epoch validation and bounded ordered decode. This
   addresses the transport portion of ANIM-GLITCH-004.
4. Move presentation to rAF with a two-frame complete-frame queue and back
   buffer. This addresses pacing and makes A/B/C classification possible.
5. Remove per-frame crop and unsequenced CSS world transforms. This addresses
   ANIM-GLITCH-005 and restores the server projection as visual authority.
6. Add section 10 tests before animation-pose changes are judged. This closes
   ANIM-GLITCH-016 and prevents transport artifacts from being mistaken for
   source-animation defects.

## Primary Sources

- [WebSockets Standard, living standard](https://websockets.spec.whatwg.org/)
- [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/rfc/rfc6455.html)
- [WHATWG Streams Standard](https://streams.spec.whatwg.org/)
- [WHATWG Compression Standard](https://compression.spec.whatwg.org/)
- [HTML Standard: animation frames](https://html.spec.whatwg.org/multipage/imagebitmap-and-animations.html#animation-frames)
- [HTML Standard: Canvas and OffscreenCanvas](https://html.spec.whatwg.org/multipage/canvas.html)
- [CSS Images Level 3: image-rendering](https://drafts.csswg.org/css-images-3/#the-image-rendering)
- [ECMAScript Promise jobs and ordering](https://tc39.es/ecma262/2024/#sec-jobs-and-host-operations-to-enqueue-jobs)
- [Tokio bounded broadcast channel](https://docs.rs/tokio/latest/tokio/sync/broadcast/)
- [RFC 3550: RTP sequence, timestamp, and jitter model](https://www.rfc-editor.org/rfc/rfc3550.html)
- [RFC 8082: decoder refresh point definition](https://www.rfc-editor.org/rfc/rfc8082.html#section-3)
- [Web Audio API 1.1](https://www.w3.org/TR/webaudio-1.1/)
- [W3C Media Timed Events requirements](https://www.w3.org/TR/media-timed-events/)
- [High Resolution Time](https://www.w3.org/TR/hr-time-3/)
- [Performance Timeline](https://w3c.github.io/performance-timeline/)
- [Long Tasks API](https://www.w3.org/TR/longtasks-1/)
- [ASCILINE exact inspected revision](https://github.com/YusufB5/ASCILINE/tree/05cc6ebd2152f5987ab348038d5619d279ecec27)
