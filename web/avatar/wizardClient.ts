import { makeDecoder } from "./wizardCodec.ts";

export class WizardClient {
  constructor(canvasRenderer, diagnostics) {
    this.canvasRenderer = canvasRenderer;
    this.diagnostics = diagnostics;
    this.ws = null;
    this.decoder = null;
    this.frameBuffer = [];
    this.targetFps = 24;
    this.frameCount = 0;
    this.lastFpsAt = performance.now();
  }

  connect() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    this.ws = new WebSocket(`${protocol}//${location.host}/ws/avatar/wizard?codec=adaptive`);
    this.ws.binaryType = "arraybuffer";
    this.ws.onmessage = (event) => this.onMessage(event);
    requestAnimationFrame((time) => this.render(time));
  }

  async onMessage(event) {
    if (typeof event.data === "string") {
      if (event.data.startsWith("INIT:")) {
        const parts = event.data.split(":");
        this.targetFps = parseFloat(parts[1]);
        const cols = parseInt(parts[3], 10);
        const rows = parseInt(parts[4], 10);
        this.decoder = makeDecoder(4);
        this.canvasRenderer.configure(cols, rows);
      }
      return;
    }
    if (!this.decoder) return;
    const decoded = await this.decoder.decode(event.data);
    this.frameBuffer.push(decoded.frame);
    while (this.frameBuffer.length > 6) this.frameBuffer.shift();
  }

  render(now) {
    requestAnimationFrame((time) => this.render(time));
    const frame = this.frameBuffer.shift();
    if (!frame) return;
    this.canvasRenderer.draw(frame);
    this.frameCount++;
    if (now - this.lastFpsAt > 1000) {
      if (this.diagnostics) this.diagnostics.setLocalFps(this.frameCount);
      this.frameCount = 0;
      this.lastFpsAt = now;
    }
  }
}

export async function command(type, payload = {}) {
  const routes = {
    move: "/api/avatar/wizard/move",
    path: "/api/avatar/wizard/path",
    circle: "/api/avatar/wizard/circle",
    face: "/api/avatar/wizard/face",
    action: "/api/avatar/wizard/action",
    expression: "/api/avatar/wizard/expression",
    speak: "/api/avatar/wizard/speak",
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
