import { AscilineStreamClient, parseInit } from "./asciline_client.js";
import { CellStageRenderer } from "./canvas_renderer.js";
import { createMotionTourLoop } from "./motion_tour.js";
import {
  buildNewsroomCue,
  NEWSROOM_COMMANDS,
  newsroomCommandLabel,
} from "./newsroom_controls.js";

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
const connection = document.getElementById("connection");
const connectionLabel = connection.querySelector(".connection-label");
const modeButtons = [...document.querySelectorAll("[data-mode-target]")];
const studioControls = document.getElementById("studio-controls");
const newsroomControls = document.getElementById("newsroom-controls");
const newsroomBug = document.getElementById("newsroom-bug");
const cueStrip = document.getElementById("cue-strip");
const cueStatus = document.getElementById("cue-status");
const cueResultTitle = document.getElementById("cue-result-title");
const cueResultDetail = document.getElementById("cue-result-detail");
const newsProgram = document.getElementById("news-program");
const newsSensitivity = document.getElementById("news-sensitivity");
const newsIntensity = document.getElementById("news-intensity");
const newsIntensityValue = document.getElementById("news-intensity-value");
const newsReducedMotion = document.getElementById("news-reduced-motion");
let socket = null;
let reconnectTimer = null;
let frameCount = 0;
let lastFpsAt = performance.now();
const tourButton = document.getElementById("tour");
let newsroomSequence = 1;
let newsroomGeneration = 1;
let newsroomBusy = false;
let newsroomCursorSynced = false;
let countValue = 0;

function setConnectionState(state, label = state) {
  diagnostics.ws.textContent = label;
  connection.dataset.state = state;
  connectionLabel.textContent = label;
}

const stream = new AscilineStreamClient({
  sendControl(control) {
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(control));
  },
  onDecoded({ sequence, tag, wireBytes }) {
    diagnostics.tag.textContent = String(tag);
    diagnostics.seq.textContent = String(sequence);
    diagnostics.wire.textContent = String(wireBytes);
  },
  onResync(control) {
    setConnectionState("opening", control.payload.reason);
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
  setConnectionState("opening");

  socket.onopen = () => {
    setConnectionState("live");
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
    setConnectionState("closed");
    stream.invalidate();
    clearMotionTour();
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connect, 800);
  };
  socket.onerror = () => {
    setConnectionState("error");
  };
}

async function requestJson(path, options = {}) {
  const response = await fetch(path, options);
  const result = await response.json().catch(() => null);
  if (!response.ok) {
    const message = result?.message ?? result?.error ?? `${response.status} ${response.statusText}`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return result;
}

async function post(path, payload = {}) {
  const result = await requestJson(`/api/avatar/wizard/${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
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

function setMode(mode) {
  const newsroom = mode === "newsroom";
  document.body.dataset.mode = newsroom ? "newsroom" : "studio";
  studioControls.hidden = newsroom;
  newsroomControls.hidden = !newsroom;
  for (const button of modeButtons) {
    const selected = button.dataset.modeTarget === mode;
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
  }
  if (newsroom) {
    clearMotionTour();
    syncNewsroomCursor();
  }
  requestAnimationFrame(resizeCanvas);
}

function renderNewsroomCommands() {
  const fragment = document.createDocumentFragment();
  NEWSROOM_COMMANDS.forEach((command, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "cue-button";
    button.dataset.newsCommand = command;
    button.dataset.index = String(index + 1).padStart(2, "0");
    button.textContent = newsroomCommandLabel(command);
    button.title = `Run ${newsroomCommandLabel(command)} cue`;
    button.addEventListener("click", () => sendNewsroomCue(command, button));
    fragment.append(button);
  });
  cueStrip.replaceChildren(fragment);
}

function updateCueReceipt(state, title, detail) {
  cueStatus.dataset.state = state;
  cueStatus.textContent = state === "sending" ? "Sending" : state === "error" ? "Error" : "Applied";
  cueResultTitle.textContent = title;
  cueResultDetail.textContent = detail;
}

async function syncNewsroomCursor() {
  try {
    const receipt = await requestJson("/api/avatar/wizard/v2/newsroom/receipt");
    newsroomSequence = receipt.sequence + 1;
    newsroomGeneration = receipt.generation;
    newsroomCursorSynced = true;
    if (cueStatus.dataset.state === "ready") {
      cueResultDetail.textContent = `Sequence ${newsroomSequence} ready`;
    }
  } catch (error) {
    if (error.status === 404) {
      newsroomCursorSynced = true;
    } else {
      updateCueReceipt("error", "Cue sync failed", error.message);
    }
  }
}

async function sendNewsroomCue(command, button) {
  if (newsroomBusy) return;
  newsroomBusy = true;
  document.querySelectorAll("[data-news-command]").forEach((item) => { item.disabled = true; });

  try {
    if (!newsroomCursorSynced) await syncNewsroomCursor();
    countValue = command === "count" ? (countValue % 3) + 1 : countValue;
    let receipt;
    for (let attempt = 0; attempt < 2; attempt += 1) {
      updateCueReceipt("sending", newsroomCommandLabel(command), `Sequence ${newsroomSequence}`);
      const cue = buildNewsroomCue({
        command,
        sequence: newsroomSequence,
        generation: newsroomGeneration,
        program: newsProgram.value,
        sensitivity: newsSensitivity.value,
        intensity: Number(newsIntensity.value) / 100,
        reducedMotion: newsReducedMotion.checked,
        count: countValue || 1,
      });
      try {
        receipt = await requestJson("/api/avatar/wizard/v2/newsroom/cue", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(cue),
        });
        break;
      } catch (error) {
        if (attempt === 0 && error.status === 409) {
          newsroomCursorSynced = false;
          await syncNewsroomCursor();
          continue;
        }
        throw error;
      }
    }
    newsroomSequence = receipt.sequence + 1;
    newsroomGeneration = receipt.generation;
    document.querySelectorAll("[data-news-command]").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    const performance = receipt.performance;
    const clamp = performance.policy_clamps.length > 0 ? ` / ${performance.policy_clamps.join(", ")}` : "";
    updateCueReceipt(
      "applied",
      newsroomCommandLabel(performance.semantic_pose_id),
      `Seq ${receipt.sequence} / ${performance.binding_fidelity}${clamp}`,
    );
  } catch (error) {
    updateCueReceipt("error", newsroomCommandLabel(command), error.message);
  } finally {
    newsroomBusy = false;
    document.querySelectorAll("[data-news-command]").forEach((item) => { item.disabled = false; });
  }
}

const motionTour = createMotionTourLoop({
  post(path, payload) {
    post(path, payload).catch(() => { setConnectionState("error", "command"); });
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
modeButtons.forEach((button) => {
  button.addEventListener("click", () => setMode(button.dataset.modeTarget));
  button.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    const mode = button.dataset.modeTarget === "studio" ? "newsroom" : "studio";
    setMode(mode);
    document.querySelector(`[data-mode-target="${mode}"]`).focus();
  });
});
newsIntensity.addEventListener("input", () => { newsIntensityValue.textContent = newsIntensity.value; });
newsProgram.addEventListener("change", () => {
  newsroomBug.textContent = newsProgram.selectedOptions[0].textContent;
});
window.addEventListener("keydown", (event) => {
  if (document.body.dataset.mode !== "studio") return;
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

renderNewsroomCommands();
resizeCanvas();
requestAnimationFrame(animationFrame);
connect();
