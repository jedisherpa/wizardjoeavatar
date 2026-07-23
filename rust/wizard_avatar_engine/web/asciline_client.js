import { makeDecoder, TAG_DELTA } from "./asciline_codec.js";
import { CompleteFrameQueue } from "./canvas_renderer.js";

const DEFAULT_MAX_MESSAGES = 16;
const DEFAULT_MAX_BYTES = 8 * 1024 * 1024;
const DEFAULT_MAX_AGE_MS = 1000;

export function inspectEnvelope(message) {
  const bytes = message instanceof Uint8Array ? message : new Uint8Array(message);
  if (bytes.byteLength < 5) throw new Error("ASCILINE frame header is truncated");
  return {
    sequence: new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength).getUint32(0, false),
    tag: bytes[4],
    bytes,
  };
}

export function parseInit(text) {
  const parts = text.split(":");
  if (parts[0] !== "INIT" || parts.length < 5) throw new Error("Invalid ASCILINE INIT message");
  const metadata = {
    fps: Number(parts[1]),
    cols: Number(parts[3]),
    rows: Number(parts[4]),
    epoch: 0,
    cellBytes: 4,
    codec: 1,
  };
  for (let index = 8; index + 1 < parts.length; index += 2) {
    if (parts[index] === "EPOCH") metadata.epoch = Number(parts[index + 1]);
    else if (parts[index] === "CELL_BYTES") metadata.cellBytes = Number(parts[index + 1]);
    else if (parts[index] === "CODEC") metadata.codec = Number(parts[index + 1]);
  }
  if (![metadata.fps, metadata.cols, metadata.rows, metadata.epoch, metadata.cellBytes, metadata.codec]
    .every(Number.isFinite)) {
    throw new Error("ASCILINE INIT metadata is not numeric");
  }
  return metadata;
}

export class BoundedByteQueue {
  constructor(
    maxMessages = DEFAULT_MAX_MESSAGES,
    maxBytes = DEFAULT_MAX_BYTES,
    maxAgeMs = DEFAULT_MAX_AGE_MS,
    now = () => performance.now(),
  ) {
    this.maxMessages = maxMessages;
    this.maxBytes = maxBytes;
    this.maxAgeMs = maxAgeMs;
    this.now = now;
    this.items = [];
    this.bytes = 0;
  }

  get length() {
    return this.items.length;
  }

  clear() {
    this.items.length = 0;
    this.bytes = 0;
  }

  push(message) {
    const bytes = message instanceof Uint8Array ? message : new Uint8Array(message);
    const now = this.now();
    const oldestAge = this.items.length ? now - this.items[0].enqueuedAt : 0;
    if (
      this.items.length + 1 > this.maxMessages
      || this.bytes + bytes.byteLength > this.maxBytes
      || oldestAge > this.maxAgeMs
    ) {
      this.clear();
      return false;
    }
    this.items.push({ message, enqueuedAt: now, byteLength: bytes.byteLength });
    this.bytes += bytes.byteLength;
    return true;
  }

  shift() {
    const item = this.items.shift();
    if (!item) return null;
    this.bytes -= item.byteLength;
    return item.message;
  }
}

export class AscilineStreamClient {
  constructor(options = {}) {
    this.decoderFactory = options.decoderFactory ?? ((cellBytes) => makeDecoder(cellBytes));
    this.sendControl = options.sendControl ?? (() => {});
    this.now = options.now ?? (() => performance.now());
    this.onDecoded = options.onDecoded ?? (() => {});
    this.onResync = options.onResync ?? (() => {});
    this.generation = 0;
    this.presentationQueue = new CompleteFrameQueue(2);
    this.encodedQueue = new BoundedByteQueue(
      DEFAULT_MAX_MESSAGES,
      DEFAULT_MAX_BYTES,
      DEFAULT_MAX_AGE_MS,
      this.now,
    );
    this.decodeActive = false;
    this.activeDrain = null;
    this.awaitingKeyframe = true;
    this.expectedSequence = null;
    this.lastValidSequence = null;
    this.resyncRequested = false;
    this.suspended = false;
  }

  beginGeneration(metadata) {
    this.generation += 1;
    this.metadata = metadata;
    this.decoder = this.decoderFactory(metadata.cellBytes);
    this.encodedQueue.clear();
    this.presentationQueue.clear();
    this.decodeActive = false;
    this.activeDrain = null;
    this.awaitingKeyframe = true;
    this.expectedSequence = null;
    this.lastValidSequence = null;
    this.resyncRequested = false;
    return this.generation;
  }

  invalidate() {
    this.generation += 1;
    this.encodedQueue.clear();
    this.presentationQueue.clear();
    this.decoder = this.metadata ? this.decoderFactory(this.metadata.cellBytes) : null;
    this.decodeActive = false;
    this.activeDrain = null;
    this.awaitingKeyframe = true;
    this.expectedSequence = null;
    this.lastValidSequence = null;
    this.resyncRequested = false;
  }

  enqueue(message) {
    if (this.suspended) return false;
    try {
      inspectEnvelope(message);
    } catch (error) {
      this.requestResync("malformed_header");
      return false;
    }
    if (!this.encodedQueue.push(message)) {
      this.requestResync("queue_overflow");
      return false;
    }
    return true;
  }

  drain() {
    if (this.decodeActive) return this.activeDrain;
    const generation = this.generation;
    const queue = this.encodedQueue;
    const decoder = this.decoder;
    this.decodeActive = true;
    this.activeDrain = this.drainGeneration(generation, queue, decoder).finally(() => {
      if (this.generation === generation) {
        this.decodeActive = false;
        this.activeDrain = null;
      }
    });
    return this.activeDrain;
  }

  async drainGeneration(generation, queue, decoder) {
    while (queue.length) {
      const message = queue.shift();
      if (generation !== this.generation) return;
      const { sequence, tag } = inspectEnvelope(message);
      const fullFrame = tag !== TAG_DELTA;
      if (this.awaitingKeyframe && !fullFrame) {
        this.requestResync("missing_delta");
        continue;
      }
      if (!fullFrame && sequence !== this.expectedSequence) {
        this.requestResync("missing_delta");
        continue;
      }
      if (this.lastValidSequence !== null && sequence <= this.lastValidSequence) continue;

      try {
        const decoded = await decoder.decode(message);
        if (generation !== this.generation) return;
        const expectedBytes = this.metadata.cols * this.metadata.rows * this.metadata.cellBytes;
        if (decoded.frame.length !== expectedBytes) throw new Error("Decoded ASCILINE frame size mismatch");
        this.presentationQueue.push({
          sequence,
          frame: decoded.frame,
          tag,
          wireBytes: inspectEnvelope(message).bytes.byteLength,
          presentationTime: this.now(),
        });
        this.expectedSequence = (sequence + 1) >>> 0;
        this.lastValidSequence = sequence;
        this.awaitingKeyframe = false;
        this.resyncRequested = false;
        this.onDecoded({ sequence, tag, wireBytes: inspectEnvelope(message).bytes.byteLength });
      } catch (error) {
        this.requestResync("decode_error");
      }
    }
  }

  requestResync(reason) {
    const shouldNotify = !this.resyncRequested;
    this.encodedQueue.clear();
    this.presentationQueue.clear();
    // An inflate from the previous generation may still complete. Give the new
    // generation a fresh decoder so stale completion cannot restore old delta history.
    this.decoder = this.metadata ? this.decoderFactory(this.metadata.cellBytes) : null;
    this.awaitingKeyframe = true;
    this.expectedSequence = null;
    this.generation += 1;
    this.decodeActive = false;
    this.activeDrain = null;
    this.resyncRequested = true;
    if (!shouldNotify) return;
    const control = {
      type: "resync",
      payload: {
        epoch: this.metadata?.epoch ?? null,
        last_valid_sequence: this.lastValidSequence,
        reason,
      },
    };
    this.sendControl(control);
    this.onResync(control);
  }

  suspend() {
    if (this.suspended) return;
    this.suspended = true;
    this.invalidate();
  }

  resume(reason = "visibility_resume") {
    if (!this.suspended) return;
    this.suspended = false;
    this.requestResync(reason);
  }

  contextRestored() {
    this.requestResync("context_restore");
  }
}
