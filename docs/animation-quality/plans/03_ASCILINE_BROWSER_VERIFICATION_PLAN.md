# ASCILINE Fanout, Browser, and Verification Implementation Plan

## Objective

Generate and encode one canonical procedural ASCILINE frame stream, fan it out
without client-driven simulation or global-history resets, recover explicitly
from any delta gap, and present complete fixed-stage block frames atomically on
`requestAnimationFrame`.

Primary defects: `ANIM-GLITCH-001` through `005`, `011`, and `016`.

## Compatibility Decision

Preserve the existing binary envelope and codec tags:

```text
[u32 frame_index big-endian][u8 tag][payload]
0 RAW, 1 ZLIB, 2 DELTA, 3 RLE_FULL
```

Add stream epoch/version/cell-width metadata to the text `INIT` control message.
For codec version 1, DELTA sequence N depends on sequence N-1 in the same epoch.
No binary-header migration is part of this quality pass.

## File Ownership

Create:

- `rust/wizard_avatar_engine/src/hub.rs`
- `rust/wizard_avatar_engine/tests/multiclient_fanout.rs`
- `rust/wizard_avatar_engine/tests/resync_reconnect.rs`
- `rust/wizard_avatar_engine/tests/transition_hashes.rs`
- `rust/wizard_avatar_engine/web/asciline_client.js`
- `rust/wizard_avatar_engine/web/canvas_renderer.js`
- `rust/wizard_avatar_engine/web/tests/codec_queue.test.mjs`
- `rust/wizard_avatar_engine/web/tests/canvas_renderer.test.mjs`
- `tools/capture_animation_quality_evidence.mjs`

Modify:

- `rust/wizard_avatar_engine/src/lib.rs`
- `rust/wizard_avatar_engine/src/server.rs`
- `rust/wizard_avatar_engine/src/frame_source.rs`
- `rust/wizard_avatar_engine/src/codec.rs`
- `rust/wizard_avatar_engine/web/index.html`
- `rust/wizard_avatar_engine/web/wizard.js`
- `rust/wizard_avatar_engine/tests/websocket_stream.rs`
- `rust/wizard_avatar_engine/Cargo.toml`

Serve the exact checked-out `external/ASCILINE/codec.js` logic or a verified
byte-identical local copy as the shared codec module. Remove the second decoder
implementation from `wizard.js`.

## Hub Types

```rust
pub struct FramePacket {
    pub epoch: u64,
    pub sequence: u32,
    pub simulation_tick: u64,
    pub presentation_micros: u64,
    pub encoded: Arc<[u8]>,
    pub full_cells: Arc<[u8]>,
    pub is_keyframe: bool,
    pub diagnostics: FrameDiagnostics,
}

pub struct ChannelSnapshot {
    pub epoch: u64,
    pub latest: Arc<FramePacket>,
}

pub struct AvatarFrameHub {
    pub sender: broadcast::Sender<Arc<FramePacket>>,
    pub latest: Arc<RwLock<Option<Arc<FramePacket>>>>,
    pub runtime: Arc<RwLock<AvatarRuntime>>,
    pub profile: RenderProfile,
}
```

Only the producer task owns `ProceduralWizardFrameSource`, canonical frame
sequence, and `prev_encoded_frame`.

## Canonical Producer

```rust
async fn run_render_producer(hub: Arc<AvatarFrameHub>) {
    let mut deadline = interval(hub.profile.frame_interval());
    deadline.set_missed_tick_behavior(MissedTickBehavior::Skip);

    loop {
        deadline.tick().await;
        let sample = hub.runtime.read().await.sample();
        let packet = source.render_and_encode(sample)?;
        let packet = Arc::new(packet);
        *hub.latest.write().await = Some(packet.clone());
        let _subscriber_count = hub.sender.send(packet);
    }
}
```

The producer skips an overdue render deadline but never changes simulation rate.
One canonical packet is immutable and identical for all healthy clients.

## Non-Mutating Full-Frame Bootstrap

Add a pure codec helper:

```rust
pub fn encode_full_frame(
    frame: &[u8],
    frame_index: u32,
    cell_bytes: usize,
) -> Result<EncodedFrame, CodecError>
```

It chooses RAW/ZLIB/RLE_FULL but never reads or updates canonical history.

Atomic subscription:

```rust
fn subscribe_from_latest(hub: &AvatarFrameHub) -> Subscription {
    let receiver = hub.sender.subscribe();
    let snapshot = hub.latest.read().clone();
    Subscription { receiver, snapshot, last_sent: None }
}
```

The client receives full sequence N from `snapshot`; the socket loop discards
any queued packet `<= N`, then forwards canonical packets `> N`.

## Lag and Resync

Per client:

```rust
enum ClientStreamState {
    Bootstrap,
    Streaming { epoch: u64, last_sent: u32 },
    Resync,
}
```

Triggers: new connection, client `resync` message, broadcast `Lagged`, sequence
gap, epoch change, and explicit profile change.

On trigger:

1. enter `Resync`
2. subscribe to current broadcast position
3. snapshot latest full logical frame N
4. send non-mutating full frame N
5. discard receiver packets `<= N`
6. resume only with contiguous canonical packets `> N`

Never call `source.reset_encoder()` from a socket. Never hold the hub/runtime
lock across socket I/O. Persistent lag after three resyncs in ten seconds closes
the client with a retryable overload reason; later profile downgrade may replace
that policy.

## INIT and Control Messages

```text
INIT:<fps>:5:<cols>:<rows>:0:0:0.000:EPOCH:<epoch>:CELL_BYTES:4:CODEC:1
```

Existing parsers continue to read the original fields. New client validates all
extended fields.

Client resync request:

```json
{
  "type": "resync",
  "payload": {
    "epoch": 42,
    "last_valid_sequence": 913,
    "reason": "missing_delta"
  }
}
```

Server semantic commands and resync control share the socket parser but are
dispatched to separate handlers. Resync is idempotent and rate-limited.

## Browser Client State

```javascript
class AscilineStreamClient {
  generation = 0;
  epoch = null;
  expectedSequence = null;
  awaitingKeyframe = true;
  encodedQueue = new BoundedByteQueue(4, 2 * 1024 * 1024, 250);
  decodedQueue = new CompleteFrameQueue(2);
  decoder = null;
  decodeActive = false;
}
```

`onmessage` only validates envelope metadata and enqueues. It performs no decode
await and no Canvas work.

Sequential decoder loop:

```javascript
async function drainEncodedQueue(client, generation) {
  if (client.decodeActive) return;
  client.decodeActive = true;
  try {
    while (client.encodedQueue.length) {
      const message = client.encodedQueue.shift();
      if (generation !== client.generation) return;

      const { sequence, tag } = inspectEnvelope(message);
      const full = tag !== TAG_DELTA;
      if (client.awaitingKeyframe && !full) continue;
      if (!full && sequence !== client.expectedSequence) {
        requestResync(client, "missing_delta");
        continue;
      }

      const decoded = await client.decoder.decode(message);
      if (generation !== client.generation) return;
      validateDecodedFrame(decoded);
      client.decodedQueue.pushNewest(decoded);
      client.expectedSequence = sequence + 1;
      client.awaitingKeyframe = false;
    }
  } catch (error) {
    requestResync(client, "decode_error");
  } finally {
    client.decodeActive = false;
  }
}
```

Queue overflow clears dependency history and requests one resync. It never drops
one delta and continues with a later delta. Old generation completions are
ignored after reconnect/INIT.

## Atomic Fixed-Stage Renderer

```javascript
class CellStageRenderer {
  logicalCanvas;       // cols x rows
  logicalContext;
  imageData;           // RGBA, one output pixel per cell
  visibleCanvas;
  visibleContext;
  fixedViewport;

  build(frame) {
    for (let cell = 0; cell < cols * rows; cell += 1) {
      const src = cell * 4;
      const dst = cell * 4;
      imageData.data[dst] = frame[src + 1];
      imageData.data[dst + 1] = frame[src + 2];
      imageData.data[dst + 2] = frame[src + 3];
      imageData.data[dst + 3] = 255;
    }
    logicalContext.putImageData(imageData, 0, 0);
  }

  commit() {
    visibleContext.imageSmoothingEnabled = false;
    visibleContext.drawImage(logicalCanvas, ...fixedViewport);
  }
}
```

One continuous rAF loop selects the newest due complete frame, builds it fully
offscreen, then performs one visible `drawImage`. At most one source frame is
committed per rAF callback. Presented sequence is strictly increasing.

Remove:

- per-frame non-white min/max scan
- six-cell dynamic margin
- content-based cell size and centering
- HTTP-polled CSS translate/rotate/scale on the avatar
- separate client mouth/eye/shadow/effect animation
- automatic `startMotionTour()` from `ws.onopen`

The full fixed white 16:9 stage, faint floor, shadow, world travel, and depth
scale remain visible. CSS uses `image-rendering: pixelated`; backing dimensions
respect DPR without changing logical mapping.

The Motion tour button is the only normal UI entry into the tour. A tour token
prevents duplicate schedules; disconnect cancels local timers without sending
new semantic commands.

## Instrumentation

Server channel:

- simulation tick/catch-up/deadline misses
- render sequence/duration and encode tag/duration/bytes
- epoch, latest full sequence, keyframe count, subscriber count

Server client:

- last enqueued/sent sequence
- lag/resync/bootstrap counts and latency
- send duration, close reason, queue age/depth

Browser:

- received/decoded/enqueued/presented sequence
- sequence gaps, stale/duplicate frames, decode errors
- queue count/bytes/oldest age and overflows
- inflate/decode/build/commit p50/p95/p99
- rAF interval, source-to-present latency, dropped complete frames
- generation/epoch/resync/reconnect/visibility/context-loss counts
- fixed viewport ID, DPR, logical scale

Expose diagnostics without applying any visual transform.

## A/B/C Hash Evidence

For every render sequence save or sample:

```text
A = Rust raw full cell bytes before codec
B = browser decoded full cell bytes
C = logical renderer ImageData RGB converted back to cell RGB
```

Record epoch, sequence, simulation tick, semantic hash, dimensions, root/feet,
viewport, and BLAKE3/CRC32. Classification:

- A contains defect: source animation/projection
- A != B: codec/order/resync
- A == B but B != C: browser rendering
- A == B == C with irregular timing: pacing/queue

## Migration Steps

1. Add hub and pure full-frame codec helper; keep old socket path in tests only.
2. Start central runtime/render producer from Plans 1/2.
3. Switch socket handlers to bootstrap plus bounded broadcast.
4. Add multi-client byte-identical fanout and reconnect isolation tests.
5. Serve the shared ASCILINE decoder module; split browser stream client and
   renderer into testable modules.
6. Add generation/epoch/sequence gates and bounded queues.
7. Replace visible renderer with fixed-stage rAF/back buffer.
8. Remove duplicate state-driven visual transforms and auto tour.
9. Add A/B/C hashes and browser capture harness.
10. Remove old per-socket ticker/global reset/dynamic crop paths.

## Automated Tests

Rust integration:

- `WIZ-PACE-001` single simulation owner with 0/1/2/4 clients
- `WIZ-PACE-002` byte-identical canonical fanout for 500 frames
- `WIZ-PACE-003` healthy client unaffected by sleeping client
- `WIZ-PACE-004` bounded lag behavior
- `WIZ-RESYNC-001` reconnect B while A remains bit-exact
- `WIZ-RESYNC-002` remove one delta and require full recovery
- `WIZ-RESYNC-003` repeated bootstrap race around publish
- codec full-frame helper is byte-exact under shipped JS decoder

JavaScript/module:

- adversarial reverse/random inflate completion remains ordered
- encoded queue count/bytes/age stay bounded
- stale generation cannot mutate decoder or renderer
- malformed headers/RLE/delta/index/size fail into one resync
- production vectors cover RAW/ZLIB/DELTA/RLE and post-gap recovery
- renderer maps every logical RGB cell to one exact block with no blended color

Browser E2E:

- WebSocket/decode callbacks perform zero visible Canvas writes
- one atomic visible commit per rAF and no mixed frame hashes
- presented sequence strictly increases and selects newest due frame
- all directions/actions/effects retain one fixed viewport/root/scale
- no runtime image requests for flattened avatar PNGs
- explicit tour runs once; connection alone sends no tour commands
- hidden 30 seconds then resume triggers fresh keyframe and no fast-forward
- 30-minute CI soak and two-hour nightly soak keep queues/memory bounded
- stable Chromium, Firefox, Safari; 1x/2x DPR and 60/120 Hz

## Evidence Output

Write post-fix evidence under `evidence/animation-quality/final/` with the same
recording/log names as baseline plus:

- `hashes/source-decoded-presented.ndjson`
- `multiclient-fanout.json`
- `resync-scenarios.json`
- `queue-and-pacing.json`
- `transition-metrics.json`
- `browser-console.json`
- `FINAL_ANIMATION_QUALITY_VERIFICATION.md`

## Completion Gate

This track is complete only when viewer count cannot alter simulation, every
healthy viewer receives one canonical stream, reconnect/lag cannot corrupt a
delta base, the browser presents only complete fixed-stage frames on rAF, no
dynamic crop or duplicate visual animation remains, and all multi-client,
resync, A/B/C, browser, and soak gates pass.
