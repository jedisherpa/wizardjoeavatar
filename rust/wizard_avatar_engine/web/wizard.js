import { AscilineStreamClient, parseInit } from "./asciline_client.js";
import { CellStageRenderer } from "./canvas_renderer.js";
import { createMotionTourLoop } from "./motion_tour.js";

const canvas = document.getElementById("avatar-canvas");
const diagnostics = {
  ws: document.getElementById("diag-ws"),
  fps: document.getElementById("diag-fps"),
  tag: document.getElementById("diag-tag"),
  seq: document.getElementById("diag-seq"),
  wire: document.getElementById("diag-wire"),
};
const stateLabel = document.getElementById("state-label");
const renderer = new CellStageRenderer(canvas, 480, 270);
let socket = null;
let reconnectTimer = null;
let frameCount = 0;
let lastFpsAt = performance.now();
const tourButton = document.getElementById("tour");

const stream = new AscilineStreamClient({
  sendControl(control) {
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(control));
  },
  onDecoded({ sequence, tag, wireBytes }) {
    diagnostics.tag.textContent = String(tag);
    diagnostics.seq.textContent = String(sequence);
    diagnostics.wire.textContent = String(wireBytes);
  },
  onResync() {
    diagnostics.ws.textContent = "resync";
  },
});
renderer.queue = stream.presentationQueue;

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  renderer.resize(Math.max(1, Math.round(rect.width * dpr)), Math.max(1, Math.round(rect.height * dpr)));
}

function animationFrame(now) {
  if (renderer.present(now)) {
    frameCount += 1;
    const elapsed = now - lastFpsAt;
    if (elapsed >= 1000) {
      diagnostics.fps.textContent = String(Math.round((frameCount * 1000) / elapsed));
      frameCount = 0;
      lastFpsAt = now;
    }
  }
  requestAnimationFrame(animationFrame);
}

function connect() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(`${protocol}//${location.host}/ws/avatar/wizard?codec=adaptive`);
  socket.binaryType = "arraybuffer";
  diagnostics.ws.textContent = "opening";

  socket.onopen = () => {
    diagnostics.ws.textContent = "live";
  };
  socket.onmessage = (event) => {
    if (typeof event.data === "string") {
      if (event.data.startsWith("INIT:")) {
        const metadata = parseInit(event.data);
        stream.beginGeneration(metadata);
        renderer.configure(metadata.cols, metadata.rows);
        renderer.queue = stream.presentationQueue;
        resizeCanvas();
      }
      return;
    }
    if (stream.enqueue(event.data)) {
      stream.drain().catch(() => stream.requestResync("decode_error"));
    }
  };
  socket.onclose = () => {
    diagnostics.ws.textContent = "closed";
    stream.invalidate();
    clearMotionTour();
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connect, 800);
  };
  socket.onerror = () => {
    diagnostics.ws.textContent = "error";
  };
}

async function post(path, payload = {}) {
  const response = await fetch(`/api/avatar/wizard/${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json().catch(() => null);
  if (result?.state) {
    stateLabel.textContent = [
      `locomotion ${result.state.locomotion}`,
      `facing ${result.state.facing}`,
      `expression ${result.state.expression}`,
      `action ${result.state.action}`,
    ].join(" | ");
  }
  return result;
}

const motionTour = createMotionTourLoop({
  post(path, payload) {
    post(path, payload).catch(() => { diagnostics.ws.textContent = "command"; });
  },
  onActiveChange(active) {
    tourButton.setAttribute("aria-pressed", String(active));
  },
});

function clearMotionTour() {
  motionTour.cancel();
}

document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", () => {
    clearMotionTour();
    const command = button.dataset.command;
    post(command.replaceAll("_", "-"), command.startsWith("walk_") ? { distance: 1.5 } : {});
  });
});
document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => {
    clearMotionTour();
    post("action", { action: button.dataset.action, duration_ms: 1800 });
  });
});
document.getElementById("expression").addEventListener("change", (event) => {
  clearMotionTour();
  post("expression", { expression: event.target.value });
});
tourButton.addEventListener("click", () => motionTour.start());
document.getElementById("speak").addEventListener("click", () => {
  clearMotionTour();
  post("speak", { text: "A well tuned spell is mostly timing.", duration_ms: 2600 });
});
window.addEventListener("keydown", (event) => {
  const commands = {
    a: ["walk-left", { distance: 1.2 }],
    arrowleft: ["walk-left", { distance: 1.2 }],
    d: ["walk-right", { distance: 1.2 }],
    arrowright: ["walk-right", { distance: 1.2 }],
    w: ["walk-backward", { distance: 1.2 }],
    arrowup: ["walk-backward", { distance: 1.2 }],
    s: ["walk-forward", { distance: 1.2 }],
    arrowdown: ["walk-forward", { distance: 1.2 }],
    " ": ["stop", {}],
    c: ["action", { action: "magic_cast", duration_ms: 1800 }],
  };
  const command = commands[event.key.toLowerCase()];
  if (command) {
    clearMotionTour();
    post(command[0], command[1]);
  }
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stream.suspend();
  else stream.resume("visibility_resume");
});
canvas.addEventListener("contextlost", (event) => {
  event.preventDefault();
  stream.suspend();
});
canvas.addEventListener("contextrestored", () => {
  renderer.restoreContext();
  renderer.queue = stream.presentationQueue;
  stream.resume("context_restore");
  resizeCanvas();
});
window.addEventListener("resize", resizeCanvas);

resizeCanvas();
requestAnimationFrame(animationFrame);
connect();
