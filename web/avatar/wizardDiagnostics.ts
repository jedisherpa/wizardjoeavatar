export class WizardDiagnostics {
  constructor(element) {
    this.element = element;
    this.localFps = 0;
    this.client = null;
  }

  setLocalFps(fps) {
    this.localFps = fps;
  }

  setClient(client) {
    this.client = client;
  }

  start() {
    setInterval(() => this.refresh(), 1000);
    this.refresh();
  }

  async refresh() {
    const characterId = new URLSearchParams(location.search).get("character") || "wizard-joe-v1";
    const response = await fetch(`/api/avatar/${encodeURIComponent(characterId)}/state`);
    if (!response.ok) return;
    const data = await response.json();
    const state = data.state;
    const d = data.diagnostics;
    const browser = this.client && typeof this.client.getMetrics === "function"
      ? this.client.getMetrics()
      : null;
    const lines = [
      `x ${state.world_position.x.toFixed(2)}  z ${state.world_position.z.toFixed(2)}`,
      `screen ${d.screen_x.toFixed(1)}, ${d.screen_y.toFixed(1)}  scale ${d.display_scale.toFixed(3)}`,
      `facing ${state.facing}  phase ${state.walk_phase.toFixed(2)}`,
      `action ${state.action}  face ${state.expression}`,
      `mouth ${state.mouth}  fps ${this.localFps}/${Math.round(d.fps)}`,
      `seq ${d.frame_sequence}  tag ${d.codec_tag}  key ${d.keyframe_count}`,
      `raw ${d.raw_frame_size}  wire ${d.encoded_frame_size}`,
      `delta ${d.delta_cell_count}  reconnect ${d.reconnect_count}`,
    ];
    if (browser) {
      lines.push(
        `browser target ${Math.round(browser.targetFps)}  buf ${browser.decodedQueueDepth}/${browser.rawQueueDepth}`,
        `drop ${browser.droppedFrames}  hold ${browser.heldFrames}  err ${browser.decodeErrorCount}`,
        `resync ${browser.resyncCount}  ignore ${browser.ignoredDeltaFrames}`,
      );
      if (browser.canvas) {
        lines.push(`cell ${browser.canvas.deviceCell}px  dpr ${browser.canvas.dpr.toFixed(2)}`);
      }
    }
    this.element.textContent = lines.join("\n");
  }
}
