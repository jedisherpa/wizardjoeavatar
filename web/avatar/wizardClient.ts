import { frameHash, isKeyframeTag, makeDecoder, parseFrameHeader, TAG_DELTA } from "./wizardCodec.ts";

const DEFAULT_TARGET_FPS = 24;
const JITTER_BUFFER_FRAMES = 2;

export class WizardClient {
  constructor(canvasRenderer, diagnostics) {
    this.canvasRenderer = canvasRenderer;
    this.diagnostics = diagnostics;
    this.ws = null;
    this.decoder = null;
    this.rawMessageQueue = [];
    this.decodePumpActive = false;
    this.frameBuffer = [];
    this.targetFps = DEFAULT_TARGET_FPS;
    this.frameIntervalMs = 1000 / DEFAULT_TARGET_FPS;
    this.nextPresentationAt = 0;
    this.presentationStarted = false;
    this.lastPresentedFrame = null;
    this.hashHistory = [];
    this.ignoreDeltasUntilKeyframe = false;
    this.maxBufferedFrames = 8;
    this.frameCount = 0;
    this.renderLoopStarted = false;
    this.reconnectTimer = null;
    this.reconnectAttempt = 0;
    this.lastFpsAt = performance.now();
    this.metrics = {
      targetFps: DEFAULT_TARGET_FPS,
      presentedFps: 0,
      decodedFrames: 0,
      presentedFrames: 0,
      heldFrames: 0,
      droppedFrames: 0,
      skippedPresentationSlots: 0,
      decodeErrorCount: 0,
      resyncCount: 0,
      resyncSkippedCount: 0,
      ignoredDeltaFrames: 0,
      rawMessagesQueued: 0,
      rawMessagesDropped: 0,
      rawQueueHighWater: 0,
      decodedQueueHighWater: 0,
      lastFrameIndex: null,
      lastPresentedFrameIndex: null,
      lastTag: null,
      lastDecodedHash: null,
      lastPresentedHash: null,
      lastDecodeError: "",
      websocketReadyState: null,
    };
    if (this.diagnostics && typeof this.diagnostics.setClient === "function") {
      this.diagnostics.setClient(this);
    }
  }

  connect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    this.ws = new WebSocket(`${protocol}//${location.host}/ws/avatar/wizard?codec=adaptive`);
    this.ws.binaryType = "arraybuffer";
    this.ws.onmessage = (event) => this.onMessage(event);
    this.ws.onopen = () => {
      this.reconnectAttempt = 0;
      this.metrics.websocketReadyState = this.ws.readyState;
    };
    this.ws.onclose = () => {
      this.metrics.websocketReadyState = this.ws ? this.ws.readyState : null;
      this.scheduleReconnect();
    };
    this.ws.onerror = () => {
      this.metrics.websocketReadyState = this.ws ? this.ws.readyState : null;
    };
    if (!this.renderLoopStarted) {
      this.renderLoopStarted = true;
      requestAnimationFrame((time) => this.render(time));
    }
  }

  scheduleReconnect() {
    if (this.reconnectTimer) return;
    const delay = Math.min(3000, 200 * (2 ** Math.min(this.reconnectAttempt, 4)));
    this.reconnectAttempt += 1;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  onMessage(event) {
    if (typeof event.data === "string") {
      if (event.data.startsWith("INIT:")) {
        this.handleInit(event.data);
      }
      return;
    }
    if (!this.decoder) return;
    this.rawMessageQueue.push(event.data);
    this.metrics.rawMessagesQueued++;
    this.metrics.rawQueueHighWater = Math.max(this.metrics.rawQueueHighWater, this.rawMessageQueue.length);
    this.pumpDecode();
  }

  handleInit(message) {
    const parts = message.split(":");
    const fps = parseFloat(parts[1]);
    const cols = parseInt(parts[3], 10);
    const rows = parseInt(parts[4], 10);
    const renderMode = parts[8] === "rgba" ? "rgba" : "cells";
    this.targetFps = Number.isFinite(fps) && fps > 0 ? fps : DEFAULT_TARGET_FPS;
    this.frameIntervalMs = 1000 / this.targetFps;
    this.maxBufferedFrames = Math.max(6, Math.ceil(this.targetFps / 3));
    this.decoder = makeDecoder(4);
    this.rawMessageQueue = [];
    this.frameBuffer = [];
    this.nextPresentationAt = 0;
    this.presentationStarted = false;
    this.lastPresentedFrame = null;
    this.hashHistory = [];
    this.ignoreDeltasUntilKeyframe = false;
    this.metrics.targetFps = this.targetFps;
    this.canvasRenderer.configure(cols, rows, renderMode);
  }

  async pumpDecode() {
    if (this.decodePumpActive) return;
    this.decodePumpActive = true;
    try {
      while (this.rawMessageQueue.length > 0) {
        const message = this.rawMessageQueue.shift();
        await this.decodeMessage(message);
      }
    } finally {
      this.decodePumpActive = false;
      if (this.rawMessageQueue.length > 0) this.pumpDecode();
    }
  }

  async decodeMessage(message) {
    if (!this.decoder) {
      this.metrics.rawMessagesDropped++;
      return;
    }

    let header;
    try {
      header = parseFrameHeader(message);
    } catch (error) {
      this.metrics.decodeErrorCount++;
      this.metrics.lastDecodeError = error instanceof Error ? error.message : String(error);
      return;
    }

    if (this.ignoreDeltasUntilKeyframe) {
      if (!isKeyframeTag(header.tag)) {
        this.metrics.ignoredDeltaFrames++;
        return;
      }
      this.ignoreDeltasUntilKeyframe = false;
    }

    try {
      const decoded = await this.decoder.decode(message);
      decoded.hash = frameHash(decoded.frame);
      this.enqueueDecodedFrame(decoded);
    } catch (error) {
      this.handleDecodeError(header, error);
    }
  }

  enqueueDecodedFrame(decoded) {
    this.frameBuffer.push(decoded);
    this.metrics.decodedFrames++;
    this.metrics.lastFrameIndex = decoded.frameIndex;
    this.metrics.lastTag = decoded.tag;
    this.metrics.lastDecodedHash = decoded.hash;
    this.recordHash(decoded.frameIndex, { decodedHash: decoded.hash, tag: decoded.tag });
    this.metrics.decodedQueueHighWater = Math.max(this.metrics.decodedQueueHighWater, this.frameBuffer.length);
    while (this.frameBuffer.length > this.maxBufferedFrames) {
      this.frameBuffer.shift();
      this.metrics.droppedFrames++;
    }
  }

  handleDecodeError(header, error) {
    this.metrics.decodeErrorCount++;
    this.metrics.lastDecodeError = error instanceof Error ? error.message : String(error);
    if (this.decoder) this.decoder.reset();
    if (header && header.tag === TAG_DELTA) {
      this.ignoreDeltasUntilKeyframe = true;
      this.requestResync("delta_without_previous");
    }
  }

  requestResync(reason) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "resync", payload: { reason } }));
      this.metrics.resyncCount++;
      return;
    }
    this.metrics.resyncSkippedCount++;
  }

  render(now) {
    requestAnimationFrame((time) => this.render(time));
    this.metrics.websocketReadyState = this.ws ? this.ws.readyState : null;
    this.updateLocalFps(now);

    if (!this.presentationStarted) {
      if (this.frameBuffer.length < JITTER_BUFFER_FRAMES) return;
      this.presentationStarted = true;
      this.nextPresentationAt = now;
    }

    if (now < this.nextPresentationAt) return;

    this.dropBacklog();
    const decoded = this.frameBuffer.shift();
    if (decoded) {
      this.canvasRenderer.draw(decoded.frame);
      this.lastPresentedFrame = decoded;
      this.metrics.presentedFrames++;
      this.metrics.lastPresentedFrameIndex = decoded.frameIndex;
      const presentedHash = this.canvasRenderer.getMetrics().lastPresentedLogicalHash || decoded.hash;
      this.metrics.lastPresentedHash = presentedHash;
      this.recordHash(decoded.frameIndex, { presentedHash });
      this.frameCount++;
    } else if (this.lastPresentedFrame) {
      this.metrics.heldFrames++;
    } else {
      return;
    }

    if (this.nextPresentationAt < now - this.frameIntervalMs * 4) {
      this.nextPresentationAt = now + this.frameIntervalMs;
      return;
    }

    do {
      this.nextPresentationAt += this.frameIntervalMs;
      if (this.nextPresentationAt <= now) this.metrics.skippedPresentationSlots++;
    } while (this.nextPresentationAt <= now);
  }

  dropBacklog() {
    const desiredDepth = JITTER_BUFFER_FRAMES + 1;
    const highWater = Math.max(desiredDepth + 3, Math.ceil(this.targetFps / 4));
    if (this.frameBuffer.length <= highWater) return;
    const dropCount = this.frameBuffer.length - desiredDepth;
    this.frameBuffer.splice(0, dropCount);
    this.metrics.droppedFrames += dropCount;
  }

  updateLocalFps(now) {
    if (now - this.lastFpsAt > 1000) {
      const elapsed = now - this.lastFpsAt;
      this.metrics.presentedFps = this.frameCount * 1000 / elapsed;
      if (this.diagnostics) this.diagnostics.setLocalFps(Math.round(this.metrics.presentedFps));
      this.frameCount = 0;
      this.lastFpsAt = now;
    }
  }

  recordHash(frameIndex, values) {
    let entry = this.hashHistory.find((item) => item.frameIndex === frameIndex);
    if (!entry) {
      entry = { frameIndex };
      this.hashHistory.push(entry);
      if (this.hashHistory.length > 240) this.hashHistory.shift();
    }
    Object.assign(entry, values);
  }

  getMetrics() {
    const canvasMetrics = this.canvasRenderer && typeof this.canvasRenderer.getMetrics === "function"
      ? this.canvasRenderer.getMetrics()
      : null;
    return {
      ...this.metrics,
      targetFps: this.targetFps,
      frameIntervalMs: this.frameIntervalMs,
      rawQueueDepth: this.rawMessageQueue.length,
      decodedQueueDepth: this.frameBuffer.length,
      waitingForKeyframe: this.ignoreDeltasUntilKeyframe,
      presentationStarted: this.presentationStarted,
      canvas: canvasMetrics,
    };
  }

  getHashHistory() {
    return this.hashHistory.slice();
  }
}

export async function command(type, payload = {}) {
  const routes = {
    move: "/api/avatar/wizard/move",
    path: "/api/avatar/wizard/path",
    circle: "/api/avatar/wizard/circle",
    face: "/api/avatar/wizard/face",
    action: "/api/avatar/wizard/action",
    pose: "/api/avatar/wizard/pose",
    control: "/api/avatar/wizard/control",
    prism_signal: "/api/avatar/wizard/prism-signal",
    expression: "/api/avatar/wizard/expression",
    speak: "/api/avatar/wizard/speak",
    speech_stop: "/api/avatar/wizard/speech-stop",
    stop: "/api/avatar/wizard/stop",
    reset: "/api/avatar/wizard/reset",
    figure_eight: "/api/avatar/wizard/figure-eight",
  };
  const route = routes[type];
  if (!route) throw new Error(`Unknown command route ${type}`);
  const response = await fetch(route, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
