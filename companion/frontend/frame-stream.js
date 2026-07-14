import { inspectEnvelope, makeDecoder, parseInit, TAG_DELTA, TAG_RAW } from "./asciline-codec.js";
import { CellStageRenderer } from "./canvas-renderer.js";

export class BoundedByteQueue {
  constructor(maxMessages = 4, maxBytes = 2 * 1024 * 1024, maxAgeMs = 250, now = () => performance.now()) {
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

function websocketUrlFor(descriptor) {
  let value = descriptor.websocketUrl;
  if (!value) {
    const base = new URL(descriptor.baseUrl || location.origin);
    base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
    base.pathname = "/ws/avatar/wizard";
    base.search = "";
    value = base.toString();
  }
  const url = new URL(value);
  if (!url.searchParams.has("codec")) url.searchParams.set("codec", "adaptive");
  return url.toString();
}

function tauriInvoke() {
  return window.__TAURI__?.core?.invoke
    || window.__TAURI__?.invoke
    || window.__TAURI_INTERNALS__?.invoke
    || null;
}

function tauriListen() {
  return window.__TAURI__?.event?.listen || null;
}

function bytesFromBase64(value) {
  const decoded = atob(value);
  return Uint8Array.from(decoded, (character) => character.charCodeAt(0));
}

function setCell(frame, cols, rows, x, y, color, character = 35) {
  if (x < 0 || x >= cols || y < 0 || y >= rows) return;
  const offset = (y * cols + x) * 4;
  frame[offset] = character;
  frame[offset + 1] = color[0];
  frame[offset + 2] = color[1];
  frame[offset + 3] = color[2];
}

function fillRect(frame, cols, rows, x, y, width, height, color, character) {
  for (let row = y; row < y + height; row += 1) {
    for (let col = x; col < x + width; col += 1) {
      setCell(frame, cols, rows, col, row, color, character);
    }
  }
}

function makePreviewFrame(cols, rows, tick, motionMode) {
  const background = [21, 25, 25];
  const frame = new Uint8Array(cols * rows * 4);
  for (let cell = 0; cell < cols * rows; cell += 1) {
    const offset = cell * 4;
    frame[offset] = 32;
    frame[offset + 1] = background[0];
    frame[offset + 2] = background[1];
    frame[offset + 3] = background[2];
  }

  const star = [106, 132, 121];
  [[12, 11], [22, 18], [75, 13], [84, 26], [10, 36], [68, 32]].forEach(([x, y], index) => {
    if (motionMode !== "still" && (tick + index) % 8 < 5) setCell(frame, cols, rows, x, y, star, 43);
  });

  const bob = motionMode === "full" ? Math.round(Math.sin(tick / 4)) : 0;
  const cx = Math.floor(cols / 2);
  const baseY = rows - 23 + bob;
  const cloak = [45, 108, 91];
  const cloakDark = [27, 77, 66];
  const hat = [53, 65, 92];
  const hatLight = [78, 92, 127];
  const face = [220, 174, 118];
  const beard = [218, 225, 217];
  const staff = [151, 91, 48];
  const gold = [221, 166, 67];
  const floor = [40, 48, 45];

  fillRect(frame, cols, rows, 0, baseY + 19, cols, rows - baseY - 19, floor, 46);
  for (let width = 7; width <= 27; width += 4) {
    fillRect(frame, cols, rows, cx - Math.floor(width / 2), baseY - 30 + Math.floor(width / 3), width, 3, hat, 94);
  }
  fillRect(frame, cols, rows, cx - 15, baseY - 20, 31, 3, hatLight, 61);
  fillRect(frame, cols, rows, cx - 7, baseY - 17, 15, 9, face, 64);
  fillRect(frame, cols, rows, cx - 5, baseY - 14, 2, 2, [30, 35, 34], 111);
  fillRect(frame, cols, rows, cx + 4, baseY - 14, 2, 2, [30, 35, 34], 111);
  fillRect(frame, cols, rows, cx - 7, baseY - 9, 15, 6, beard, 87);
  for (let row = 0; row < 20; row += 1) {
    const width = 17 + Math.floor(row * 0.85);
    fillRect(frame, cols, rows, cx - Math.floor(width / 2), baseY - 3 + row, width, 1, row % 4 === 0 ? cloakDark : cloak, 35);
  }
  fillRect(frame, cols, rows, cx - 15, baseY + 16, 10, 3, cloakDark, 95);
  fillRect(frame, cols, rows, cx + 6, baseY + 16, 10, 3, cloakDark, 95);
  fillRect(frame, cols, rows, cx + 19, baseY - 12, 2, 30, staff, 124);
  fillRect(frame, cols, rows, cx + 17, baseY - 16, 6, 5, gold, 42);
  return frame;
}

function rawPacket(sequence, frame) {
  const bytes = new Uint8Array(frame.length + 5);
  new DataView(bytes.buffer).setUint32(0, sequence, false);
  bytes[4] = TAG_RAW;
  bytes.set(frame, 5);
  return bytes;
}

export class WizardFrameStream {
  constructor(canvas, callbacks = {}) {
    this.renderer = new CellStageRenderer(canvas);
    this.callbacks = callbacks;
    this.socket = null;
    this.decoder = null;
    this.metadata = null;
    this.generation = 0;
    this.encodedQueue = new BoundedByteQueue();
    this.decodeActive = false;
    this.activeDrain = null;
    this.awaitingKeyframe = true;
    this.expectedSequence = null;
    this.lastValidSequence = null;
    this.resyncRequested = false;
    this.reconnectTimer = null;
    this.reconnectAttempt = 0;
    this.intentionalClose = false;
    this.previewTimer = null;
    this.previewSequence = 0;
    this.unlisten = null;
    this.bridgeStarted = false;
    this.motionMode = "full";
    this.frameCount = 0;
    this.lastFpsAt = performance.now();
    this.stats = { state: "idle", fps: 0, queueDepth: 0, sequence: null };
    this.animationFrame = requestAnimationFrame((now) => this.present(now));
  }

  connect(descriptor) {
    this.descriptor = descriptor;
    this.stopPreview();
    if (descriptor.browserDemo) {
      this.startPreview();
      return;
    }
    if (descriptor.frameTransport === "tauri-event") {
      this.startTauriBridge();
      return;
    }
    this.openSocket();
  }

  async startTauriBridge() {
    this.closeSocket();
    await this.closeTauriBridge();
    const invoke = tauriInvoke();
    const listen = tauriListen();
    if (!invoke || !listen) {
      this.setState("error");
      this.callbacks.onError?.(new Error("Tauri frame bridge is unavailable"));
      return;
    }
    this.setState("connecting");
    try {
      this.unlisten = await listen(this.descriptor.frameEventName, (event) => {
        this.handleBridgePayload(event.payload);
      });
      let started = false;
      let lastError = null;
      for (const command of ["start_companion_frame_stream", "companion_start_frame_stream"]) {
        try {
          await invoke(command, { eventName: this.descriptor.frameEventName });
          started = true;
          this.bridgeStarted = true;
          break;
        } catch (error) {
          lastError = error;
        }
      }
      if (!started) throw lastError;
      this.setState("live");
    } catch (error) {
      await this.closeTauriBridge();
      this.setState("error");
      this.callbacks.onError?.(error);
    }
  }

  handleBridgePayload(payload) {
    if (typeof payload === "string") {
      this.handleMessage(payload);
      return;
    }
    if (Array.isArray(payload)) {
      this.handleMessage(Uint8Array.from(payload));
      return;
    }
    if (!payload || typeof payload !== "object") return;
    if (payload.type === "init" || payload.type === "text") {
      this.handleMessage(String(payload.data || payload.message || ""));
      return;
    }
    if (payload.type === "binary" || payload.data || payload.base64) {
      const bytes = payload.base64
        ? bytesFromBase64(payload.base64)
        : Uint8Array.from(payload.data || []);
      this.handleMessage(bytes);
    }
  }

  openSocket() {
    this.closeSocket();
    this.intentionalClose = false;
    this.setState("connecting");
    const socket = new WebSocket(websocketUrlFor(this.descriptor));
    this.socket = socket;
    socket.binaryType = "arraybuffer";
    socket.onopen = () => {
      this.reconnectAttempt = 0;
      this.setState("live");
    };
    socket.onmessage = (event) => this.handleMessage(event.data);
    socket.onerror = () => this.setState("error");
    socket.onclose = () => {
      this.invalidate();
      if (this.intentionalClose) return;
      this.setState("reconnecting");
      const delay = Math.min(4000, 300 * (2 ** Math.min(this.reconnectAttempt, 4)));
      this.reconnectAttempt += 1;
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = setTimeout(() => this.openSocket(), delay);
    };
  }

  retry() {
    clearTimeout(this.reconnectTimer);
    if (this.descriptor?.browserDemo) {
      this.startPreview();
    } else if (this.descriptor?.frameTransport === "tauri-event") {
      this.startTauriBridge();
    } else if (this.descriptor) {
      this.openSocket();
    }
  }

  handleMessage(message) {
    if (typeof message === "string") {
      if (!message.startsWith("INIT:")) return;
      try {
        this.beginGeneration(parseInit(message));
      } catch (error) {
        this.setState("error");
        this.callbacks.onError?.(error);
      }
      return;
    }
    if (!this.decoder || !this.metadata) return;
    try {
      inspectEnvelope(message);
    } catch {
      this.requestResync("malformed_header");
      return;
    }
    if (!this.encodedQueue.push(message)) {
      this.requestResync("queue_overflow");
      return;
    }
    this.drain().catch(() => this.requestResync("decode_error"));
  }

  beginGeneration(metadata) {
    if (metadata.cellBytes !== 4) throw new Error("Unsupported ASCILINE cell width");
    this.generation += 1;
    this.metadata = metadata;
    this.decoder = makeDecoder(metadata.cellBytes);
    this.encodedQueue.clear();
    this.renderer.configure(metadata.cols, metadata.rows);
    this.decodeActive = false;
    this.activeDrain = null;
    this.awaitingKeyframe = true;
    this.expectedSequence = null;
    this.lastValidSequence = null;
    this.resyncRequested = false;
    this.callbacks.onReady?.(metadata);
  }

  drain() {
    if (this.decodeActive) return this.activeDrain;
    const generation = this.generation;
    const queue = this.encodedQueue;
    const decoder = this.decoder;
    this.decodeActive = true;
    this.activeDrain = this.drainGeneration(generation, queue, decoder).finally(() => {
      if (generation === this.generation) {
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
      const envelope = inspectEnvelope(message);
      const fullFrame = envelope.tag !== TAG_DELTA;
      if (this.awaitingKeyframe && !fullFrame) {
        this.requestResync("missing_delta");
        continue;
      }
      if (!fullFrame && envelope.sequence !== this.expectedSequence) {
        this.requestResync("missing_delta");
        continue;
      }
      if (this.lastValidSequence !== null && envelope.sequence <= this.lastValidSequence) continue;

      try {
        const decoded = await decoder.decode(message);
        if (generation !== this.generation) return;
        const expectedBytes = this.metadata.cols * this.metadata.rows * this.metadata.cellBytes;
        if (decoded.frame.length !== expectedBytes) throw new Error("Decoded ASCILINE frame size mismatch");
        this.renderer.enqueue({ ...decoded, presentationTime: performance.now() });
        this.expectedSequence = (decoded.sequence + 1) >>> 0;
        this.lastValidSequence = decoded.sequence;
        this.awaitingKeyframe = false;
        this.resyncRequested = false;
      } catch {
        this.requestResync("decode_error");
      }
    }
  }

  present(now) {
    const minimumInterval = this.motionMode === "still"
      ? 1000
      : this.motionMode === "reduced" ? 1000 / 12 : 0;
    const presented = this.renderer.present(now, minimumInterval);
    if (presented) {
      this.stats.sequence = presented.sequence;
      this.recordFrame();
      this.callbacks.onFrame?.(presented);
    }
    this.animationFrame = requestAnimationFrame((nextNow) => this.present(nextNow));
  }

  requestResync(reason) {
    const shouldSend = !this.resyncRequested;
    this.generation += 1;
    this.encodedQueue.clear();
    this.renderer.clearQueue();
    this.decoder?.reset();
    this.decodeActive = false;
    this.activeDrain = null;
    this.awaitingKeyframe = true;
    this.expectedSequence = null;
    this.resyncRequested = true;
    if (!shouldSend) return;
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        type: "resync",
        payload: {
          epoch: this.metadata?.epoch ?? null,
          last_valid_sequence: this.lastValidSequence,
          reason,
        },
      }));
    } else if (this.descriptor?.frameTransport === "tauri-event") {
      this.requestTauriResync(reason);
    }
  }

  async requestTauriResync(reason) {
    const invoke = tauriInvoke();
    if (!invoke) return;
    const payload = { epoch: this.metadata?.epoch ?? null, reason };
    for (const command of ["resync_companion_frame_stream", "companion_resync_frame_stream"]) {
      try {
        await invoke(command, payload);
        return;
      } catch {
        // The shell may use the other command alias.
      }
    }
  }

  startPreview() {
    this.stopPreview();
    const cols = 96;
    const rows = 64;
    this.beginGeneration({ fps: 8, cols, rows, epoch: 1, cellBytes: 4, codec: 1 });
    this.setState("preview");
    const render = () => {
      const frame = makePreviewFrame(cols, rows, this.previewSequence, this.motionMode);
      this.handleMessage(rawPacket(this.previewSequence, frame));
      this.previewSequence = (this.previewSequence + 1) >>> 0;
    };
    render();
    const interval = { full: 125, reduced: 333, still: 1000 }[this.motionMode] || 125;
    this.previewTimer = setInterval(render, interval);
  }

  stopPreview() {
    clearInterval(this.previewTimer);
    this.previewTimer = null;
  }

  setMotionMode(mode) {
    this.motionMode = mode;
    if (this.descriptor?.browserDemo) this.startPreview();
  }

  recordFrame() {
    this.frameCount += 1;
    const now = performance.now();
    const elapsed = now - this.lastFpsAt;
    if (elapsed >= 1000) {
      this.stats.fps = Math.round((this.frameCount * 1000) / elapsed);
      this.frameCount = 0;
      this.lastFpsAt = now;
    }
  }

  setState(state) {
    this.stats.state = state;
    this.callbacks.onState?.(state);
  }

  invalidate() {
    this.generation += 1;
    this.encodedQueue.clear();
    this.renderer.clearQueue();
    this.decoder?.reset();
    this.decodeActive = false;
    this.activeDrain = null;
    this.awaitingKeyframe = true;
    this.expectedSequence = null;
    this.lastValidSequence = null;
    this.resyncRequested = false;
  }

  closeSocket() {
    if (!this.socket) return;
    this.intentionalClose = true;
    this.socket.onclose = null;
    this.socket.close();
    this.socket = null;
  }

  async closeTauriBridge() {
    if (this.unlisten) {
      this.unlisten();
      this.unlisten = null;
    }
    const invoke = tauriInvoke();
    if (!invoke || !this.bridgeStarted) return;
    this.bridgeStarted = false;
    for (const command of ["stop_companion_frame_stream", "companion_stop_frame_stream"]) {
      try {
        await invoke(command);
        return;
      } catch {
        // The bridge may not have started, or the shell may use the other command alias.
      }
    }
  }

  destroy() {
    clearTimeout(this.reconnectTimer);
    this.closeSocket();
    this.closeTauriBridge();
    this.stopPreview();
    cancelAnimationFrame(this.animationFrame);
    this.renderer.destroy();
  }

  getStats() {
    return { ...this.stats, queueDepth: this.encodedQueue.length + this.renderer.queue.length };
  }
}

export { makePreviewFrame, rawPacket, websocketUrlFor };
