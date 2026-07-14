import { command } from "./wizardClient.ts";

const CONTROL_INTERVAL_MS = 50;
const CONTROL_TTL_MS = 250;
const heldKeys = new Set();
const sourceEpoch = crypto.randomUUID ? crypto.randomUUID() : `browser-${Date.now()}`;
const sourceId = `browser-${sourceEpoch}`;
const leaseId = `control-${sourceEpoch}`;
let sourceSequence = 0;
let flightRequested = false;
let pendingMobilityRequest = "keep";
let previousGamepadToggle = false;
let repeatRunId = 0;
let lastControlFingerprint = "";
let lastControlSentAt = 0;

const expressionKeys = {
  "1": "neutral",
  "2": "happy",
  "3": "thinking",
  "4": "surprised",
  "5": "skeptical",
};

export function installControls() {
  document.querySelectorAll("[data-demo]").forEach((button) => {
    button.addEventListener("click", () => playDemo(button).catch(console.error));
  });
  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      command("action", { action: button.dataset.action, duration_ms: 1800 }).catch(console.error);
    });
  });
  document.querySelector("[data-repeat]")?.addEventListener("click", (event) => {
    toggleRepeat(event.currentTarget).catch(console.error);
  });
  document.querySelector("[data-stop]")?.addEventListener("click", () => {
    stopScriptedMotion().catch(console.error);
  });

  installPosePicker();
  installKeyboard();
  updateMediaStatus();
  window.setInterval(sendControlIntent, CONTROL_INTERVAL_MS);
  window.setInterval(updateCaption, 125);
  window.addEventListener("blur", releaseHeldInput);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) releaseHeldInput();
  });
  window.addEventListener("beforeunload", () => sendControlIntent(true));
  window.wizardJoeSpeak = speakWithTts;
}

function releaseHeldInput() {
  heldKeys.clear();
  sendControlIntent(true).catch(console.error);
}

function installKeyboard() {
  const controlled = new Set(["w", "a", "s", "d", "arrowup", "arrowdown", "arrowleft", "arrowright", " ", "shift"]);
  window.addEventListener("keydown", (event) => {
    const key = event.key.toLowerCase();
    if (controlled.has(key)) event.preventDefault();
    if (event.repeat && key === "f") return;
    if (expressionKeys[event.key]) {
      command("expression", { expression: expressionKeys[event.key] }).catch(console.error);
      return;
    }
    if (key === "f") {
      flightRequested = !flightRequested;
      pendingMobilityRequest = flightRequested ? "takeoff" : "land";
      updateFlightButton();
      return;
    }
    if (key === "q") command("face", { direction: "left" }).catch(console.error);
    else if (key === "e") command("face", { direction: "right" }).catch(console.error);
    else if (key === "p") command("action", { action: "pointing", duration_ms: 1800 }).catch(console.error);
    else if (key === "x") command("action", { action: "explaining", duration_ms: 2200 }).catch(console.error);
    else if (key === "c") command("action", { action: "magic_cast", duration_ms: 1800 }).catch(console.error);
    else if (key === "r") command("action", { action: "reaction", duration_ms: 1400 }).catch(console.error);
    if (controlled.has(key)) heldKeys.add(key);
  });
  window.addEventListener("keyup", (event) => heldKeys.delete(event.key.toLowerCase()));
  document.querySelector("[data-flight]")?.addEventListener("click", () => {
    flightRequested = !flightRequested;
    pendingMobilityRequest = flightRequested ? "takeoff" : "land";
    updateFlightButton();
  });
}

function keyboardAxes() {
  const left = heldKeys.has("a") || heldKeys.has("arrowleft");
  const right = heldKeys.has("d") || heldKeys.has("arrowright");
  const forward = heldKeys.has("w") || heldKeys.has("arrowup");
  const back = heldKeys.has("s") || heldKeys.has("arrowdown");
  return {
    x: Number(right) - Number(left),
    z: Number(back) - Number(forward),
    ascend: flightRequested ? Number(heldKeys.has(" ")) - Number(heldKeys.has("shift")) : 0,
    run: !flightRequested && heldKeys.has("shift"),
  };
}

function gamepadAxes() {
  const gamepad = Array.from(navigator.getGamepads?.() || []).find((pad) => pad && pad.connected);
  if (!gamepad) return { x: 0, z: 0, ascend: 0, run: false };
  const deadzone = (value) => Math.abs(value || 0) < 0.16 ? 0 : value;
  const toggle = Boolean(gamepad.buttons[3]?.pressed);
  if (toggle && !previousGamepadToggle) {
    flightRequested = !flightRequested;
    pendingMobilityRequest = flightRequested ? "takeoff" : "land";
    updateFlightButton();
  }
  previousGamepadToggle = toggle;
  return {
    x: deadzone(gamepad.axes[0]),
    z: deadzone(gamepad.axes[1]),
    ascend: flightRequested ? Number(gamepad.buttons[0]?.pressed) - Number(gamepad.buttons[1]?.pressed) : 0,
    run: Boolean(gamepad.buttons[7]?.value > 0.4),
  };
}

async function sendControlIntent(release = false) {
  const keyboard = keyboardAxes();
  const gamepad = gamepadAxes();
  let x = release ? 0 : keyboard.x + gamepad.x;
  let z = release ? 0 : keyboard.z + gamepad.z;
  const length = Math.hypot(x, z);
  if (length > 1) {
    x /= length;
    z /= length;
  }
  const mobilityRequest = release ? "keep" : pendingMobilityRequest;
  pendingMobilityRequest = "keep";
  const intent = {
    move_x: x,
    move_z: z,
    ascend: release ? 0 : Math.max(-1, Math.min(1, keyboard.ascend + gamepad.ascend)),
    speed_mode: keyboard.run || gamepad.run ? "run" : "walk",
    mobility_request: mobilityRequest,
    held_actions: [],
  };
  const fingerprint = JSON.stringify(intent);
  const now = Date.now();
  const isActive = Math.abs(intent.move_x) > 0.001
    || Math.abs(intent.move_z) > 0.001
    || Math.abs(intent.ascend) > 0.001
    || intent.mobility_request !== "keep";
  if (fingerprint === lastControlFingerprint) {
    if (!isActive || now - lastControlSentAt < 100) return;
  }
  lastControlFingerprint = fingerprint;
  lastControlSentAt = now;
  try {
    await command("control", {
      command_id: `browser-control-${sourceSequence}`,
      source_id: sourceId,
      source_kind: "keyboard",
      source_sequence: sourceSequence++,
      source_epoch: sourceEpoch,
      lease_id: leaseId,
      ttl_ms: CONTROL_TTL_MS,
      intent,
    });
  } catch (error) {
    console.error(error);
  }
}

async function installPosePicker() {
  const dialog = document.getElementById("pose-picker");
  const grid = document.getElementById("pose-grid");
  document.querySelector("[data-poses]")?.addEventListener("click", () => dialog.showModal());
  document.querySelector("[data-close-poses]")?.addEventListener("click", () => dialog.close());
  dialog?.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  if (!grid) return;
  const response = await fetch("/api/avatar/wizard/poses");
  const { poses } = await response.json();
  const auto = document.createElement("button");
  auto.type = "button";
  auto.className = "pose-button pose-auto";
  auto.textContent = "Auto";
  auto.addEventListener("click", () => command("pose", { pose_id: null }).catch(console.error));
  grid.append(auto);
  poses.forEach((poseId) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "pose-button";
    button.textContent = poseId.replaceAll("_", " ");
    button.title = poseId;
    button.addEventListener("click", () => command("pose", { pose_id: poseId, duration_ms: 0 }).catch(console.error));
    grid.append(button);
  });
}

async function updateCaption() {
  try {
    const response = await fetch("/api/avatar/wizard/state", { cache: "no-store" });
    const { state, media } = await response.json();
    const caption = document.getElementById("captions");
    if (!caption) return;
    caption.textContent = state.speech_text || "";
    caption.hidden = !state.speech_text;
    flightRequested = Boolean(state.airborne) || pendingMobilityRequest === "takeoff";
    updateFlightButton();
    updateMediaStatus(media);
  } catch (_error) {
    // A reconnect should not interrupt local controller input.
  }
}

function updateMediaStatus(media = null) {
  const container = document.getElementById("media-status");
  const title = document.getElementById("media-status-title");
  const detail = document.getElementById("media-status-detail");
  if (!container || !title || !detail || !media) return;
  const labels = {
    disabled: ["Wizard media disabled", "Connector configuration is required"],
    waiting: ["Wizard media ready", "Play audio in the Prism GT app"],
    paused: ["Wizard media paused", "Press Play in Prism GT"],
    stale: ["Wizard media needs reconnect", "Reload Prism GT, then press Play"],
    ready: ["Wizard media connected", "Waiting for active playback"],
    animating: [
      `Animating ${media.source === "speech" ? "speech" : "main audio"}`,
      media.action ? `Action: ${media.action.replaceAll("_", " ")}` : "Following Prism GT",
    ],
  };
  const [heading, description] = labels[media.status] || labels.waiting;
  container.className = `media-status is-${media.status || "waiting"}`;
  title.textContent = heading;
  detail.textContent = description;
}

async function stopScriptedMotion() {
  repeatRunId += 1;
  const repeatButton = document.querySelector("[data-repeat]");
  if (repeatButton) {
    repeatButton.setAttribute("aria-pressed", "false");
    repeatButton.title = "Repeat random poses";
    repeatButton.setAttribute("aria-label", "Repeat random poses");
  }
  await command("pose", { pose_id: null });
  await command("stop", {});
}

function updateFlightButton() {
  const button = document.querySelector("[data-flight]");
  if (!button) return;
  button.setAttribute("aria-pressed", String(flightRequested));
  button.title = flightRequested ? "Land" : "Fly";
}

export async function speakWithTts(text, options = {}) {
  const cleanText = String(text || "").trim();
  if (!cleanText) return;
  const hasBrowserTts = "speechSynthesis" in window && options.audio !== false;
  const durationMs = options.duration_ms || (hasBrowserTts ? 60000 : Math.max(900, cleanText.length * 58));
  await command("speak", { text: cleanText, duration_ms: durationMs, speech_id: options.speech_id });
  if (!hasBrowserTts) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(cleanText);
  if (Number.isFinite(options.rate)) utterance.rate = options.rate;
  if (Number.isFinite(options.pitch)) utterance.pitch = options.pitch;
  utterance.onend = () => command("speech_stop", {}).catch(console.error);
  utterance.onerror = () => command("speech_stop", {}).catch(console.error);
  speechSynthesis.speak(utterance);
}

async function playDemo(button) {
  if (button.dataset.playing === "true") return;
  repeatRunId += 1;
  const repeatButton = document.querySelector("[data-repeat]");
  if (repeatButton) {
    repeatButton.setAttribute("aria-pressed", "false");
    repeatButton.title = "Repeat random poses";
  }
  button.dataset.playing = "true";
  button.disabled = true;
  try {
    await command("reset", {});
    const { poses } = await fetch("/api/avatar/wizard/poses").then((response) => response.json());
    await command("path", {
      points: [{ x: -2.4, z: 4.2 }, { x: 2.4, z: 4.2 }, { x: 2.0, z: 6.4 }, { x: -2.0, z: 6.4 }],
      loop: true,
      speed: 0.85,
    });
    for (const poseId of poses) {
      await command("pose", { pose_id: poseId, duration_ms: 520 });
      await sleep(520);
    }
    await command("pose", { pose_id: null });
    await command("move", { x: 0, z: 5, speed: 1.1 });
  } finally {
    button.disabled = false;
    button.dataset.playing = "false";
  }
}

async function toggleRepeat(button) {
  const isStarting = button.getAttribute("aria-pressed") !== "true";
  repeatRunId += 1;
  const runId = repeatRunId;
  button.setAttribute("aria-pressed", String(isStarting));
  button.title = isStarting ? "Stop repeating" : "Repeat random poses";
  button.setAttribute("aria-label", button.title);
  if (!isStarting) {
    await command("pose", { pose_id: null });
    await command("stop", {});
    return;
  }

  const { poses } = await fetch("/api/avatar/wizard/poses").then((response) => response.json());
  await command("path", {
    points: [
      { x: -2.5, z: 4.0 },
      { x: 2.5, z: 4.0 },
      { x: 2.2, z: 6.5 },
      { x: -2.2, z: 6.5 },
      { x: 0, z: 5.0 },
    ],
    loop: true,
    speed: 0.92,
  });

  while (runId === repeatRunId && button.getAttribute("aria-pressed") === "true") {
    const shuffled = shuffle(poses);
    for (const poseId of shuffled) {
      if (runId !== repeatRunId || button.getAttribute("aria-pressed") !== "true") return;
      await command("pose", { pose_id: poseId, duration_ms: 760 });
      await sleep(760);
    }
  }
}

function shuffle(values) {
  const result = values.slice();
  for (let index = result.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [result[index], result[swapIndex]] = [result[swapIndex], result[index]];
  }
  return result;
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
