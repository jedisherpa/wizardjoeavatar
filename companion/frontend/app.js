import { WizardFrameStream } from "./frame-stream.js";
import { resolveRuntimeDescriptor, RuntimeClient } from "./runtime.js";
import {
  activityDescription,
  createRandomPoseCycle,
  createSafeDiagnostics,
  derivePresentation,
  movementCommandForKey,
} from "./state.js";

const elements = {
  shell: document.getElementById("app-shell"),
  stage: document.getElementById("stage"),
  canvas: document.getElementById("wizard-canvas"),
  stageMessage: document.getElementById("stage-message"),
  stageMessageText: document.getElementById("stage-message-text"),
  stateMark: document.getElementById("state-mark"),
  statusLabel: document.getElementById("status-label"),
  sourceLabel: document.getElementById("source-label"),
  activity: document.getElementById("activity-description"),
  liveStatus: document.getElementById("live-status"),
  playDemo: document.getElementById("play-demo"),
  repeatDemo: document.getElementById("repeat-demo"),
  stopMovement: document.getElementById("stop-movement"),
  flyToggle: document.getElementById("fly-toggle"),
  posesDialog: document.getElementById("poses-dialog"),
  moreDialog: document.getElementById("more-dialog"),
  pauseReactions: document.getElementById("pause-reactions"),
  motionMode: document.getElementById("motion-mode"),
  launchAtLogin: document.getElementById("launch-at-login"),
  diagnostics: document.getElementById("diagnostics-output"),
};

const systemReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const storedMotionMode = localStorage.getItem("wizard.motionMode");
const state = {
  descriptor: null,
  runtime: null,
  health: { status: "starting" },
  avatar: {},
  media: {},
  connection: "connecting",
  error: null,
  errorCode: "none",
  hasFrame: false,
  localDemo: false,
  demoPlayed: false,
  repeatActive: false,
  poseIds: [],
  poseCycle: [],
  reactionPreferenceEpoch: null,
  reactionsPaused: localStorage.getItem("wizard.reactionsPaused") === "true",
  motionMode: storedMotionMode || (systemReducedMotion.matches ? "reduced" : "full"),
  launchAtLogin: localStorage.getItem("wizard.launchAtLogin") === "true",
  lastAnnouncedStatus: "",
  lastDescriptionAt: 0,
  demoTimers: [],
};

const stream = new WizardFrameStream(elements.canvas, {
  onReady() {
    state.error = null;
    render();
  },
  onFrame() {
    state.hasFrame = true;
    updateActivityDescription();
  },
  onState(connection) {
    state.connection = connection;
    render();
  },
  onError(error) {
    setError(error, "frame_bridge_unavailable");
  },
});

function presentation() {
  return derivePresentation(state);
}

function render() {
  const view = presentation();
  elements.statusLabel.textContent = view.label;
  elements.sourceLabel.textContent = view.source;
  elements.stateMark.dataset.tone = view.tone;
  elements.canvas.setAttribute("aria-label", activityDescription(view));
  elements.stageMessage.hidden = state.hasFrame && view.status !== "degraded";
  elements.stageMessageText.textContent = view.stageMessage || view.label;
  elements.flyToggle.setAttribute("aria-pressed", String(view.airborne));
  elements.flyToggle.querySelector("span:last-child").textContent = view.airborne ? "Land" : "Fly";
  elements.pauseReactions.checked = state.reactionsPaused;
  elements.motionMode.value = state.motionMode;
  elements.launchAtLogin.checked = state.launchAtLogin;
  elements.repeatDemo.setAttribute("aria-pressed", String(state.repeatActive));
  elements.repeatDemo.querySelector("span:last-child").textContent = state.repeatActive
    ? "Stop Repeat"
    : "Repeat";
  elements.playDemo.setAttribute("aria-pressed", String(state.localDemo));
  elements.shell.setAttribute("aria-busy", String(!state.hasFrame && !state.error));

  if (view.label !== state.lastAnnouncedStatus) {
    elements.liveStatus.textContent = `${view.label}. ${view.source}.`;
    state.lastAnnouncedStatus = view.label;
  }
  updateActivityDescription();
  updateDiagnostics();
}

function updateActivityDescription(force = false) {
  const now = performance.now();
  if (!force && now - state.lastDescriptionAt < 1000) return;
  const description = activityDescription(presentation());
  elements.activity.textContent = description;
  elements.canvas.setAttribute("aria-label", description);
  state.lastDescriptionAt = now;
}

function diagnosticPayload() {
  return createSafeDiagnostics({
    appVersion: state.descriptor?.appVersion,
    health: state.health,
    media: state.media,
    stream: stream.getStats(),
    preferences: {
      motionMode: state.motionMode,
      reactionsPaused: state.reactionsPaused,
      launchAtLogin: state.launchAtLogin,
    },
    errorCode: state.errorCode,
  });
}

function updateDiagnostics() {
  elements.diagnostics.textContent = JSON.stringify(diagnosticPayload(), null, 2);
}

function setError(error, code = "frontend_error") {
  state.error = error instanceof Error ? error.message : String(error);
  state.errorCode = code;
  render();
}

function clearDemoTimers() {
  for (const timer of state.demoTimers) clearTimeout(timer);
  state.demoTimers.length = 0;
}

function humanizePoseId(poseId) {
  return String(poseId)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function renderPoseCatalog() {
  const grid = document.getElementById("pose-grid");
  grid.replaceChildren();
  for (const poseId of state.poseIds) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.pose = poseId;
    button.textContent = humanizePoseId(poseId);
    button.addEventListener("click", async () => {
      stopRepeat(false);
      await sendCommand("pose", { pose_id: poseId, duration_ms: 1800 });
      closeDialog(elements.posesDialog);
    });
    grid.append(button);
  }
  if (!state.poseIds.length) {
    const empty = document.createElement("p");
    empty.className = "pose-loading";
    empty.textContent = "No poses are available.";
    grid.append(empty);
  }
}

async function loadPoseCatalog() {
  try {
    const result = await state.runtime?.request("/api/avatar/wizard/poses");
    state.poseIds = Array.isArray(result?.poses) ? result.poses : [];
  } catch {
    state.poseIds = [];
  }
  renderPoseCatalog();
}

function stopRepeat(clearPose = true) {
  state.repeatActive = false;
  state.poseCycle = [];
  clearDemoTimers();
  state.localDemo = false;
  if (clearPose) void sendCommand("pose", { pose_id: null }, { quiet: true });
  render();
}

function scheduleNextPose() {
  if (!state.repeatActive) return;
  if (!state.poseCycle.length) {
    state.poseCycle = createRandomPoseCycle(state.poseIds);
  }
  const poseId = state.poseCycle.shift();
  if (!poseId) {
    stopRepeat(false);
    return;
  }
  void sendCommand("pose", { pose_id: poseId, duration_ms: 1600 }, { quiet: true });
  state.avatar = { ...state.avatar, action: "posing", control_source: "demo" };
  const timer = window.setTimeout(scheduleNextPose, 1700);
  state.demoTimers.push(timer);
  render();
}

async function toggleRepeat() {
  if (state.repeatActive) {
    stopRepeat();
    return;
  }
  if (!state.poseIds.length) await loadPoseCatalog();
  if (!state.poseIds.length) {
    setError("No poses are available", "pose_catalog_empty");
    return;
  }
  clearDemoTimers();
  state.repeatActive = true;
  state.localDemo = true;
  state.demoPlayed = true;
  state.poseCycle = [];
  scheduleNextPose();
}

async function sendCommand(type, payload = {}, options = {}) {
  if (!state.runtime) return null;
  try {
    const result = await state.runtime.command(type, payload);
    const avatar = result?.state || result;
    if (avatar && typeof avatar === "object") state.avatar = { ...state.avatar, ...avatar };
    state.error = null;
    if (!options.quiet) render();
    return result;
  } catch (error) {
    setError(error, "command_failed");
    return null;
  }
}

function scheduleDemoCommand(delay, type, payload) {
  const timer = window.setTimeout(() => {
    if (!state.localDemo) return;
    sendCommand(type, payload, { quiet: true });
  }, delay);
  state.demoTimers.push(timer);
}

function playDemo() {
  state.repeatActive = false;
  clearDemoTimers();
  state.localDemo = true;
  state.demoPlayed = true;
  state.avatar = { ...state.avatar, action: "explaining", control_source: "demo" };
  sendCommand("action", { action: "explaining", duration_ms: 1500 }, { quiet: true });
  scheduleDemoCommand(1600, "action", { action: "magic_cast", duration_ms: 1800 });
  scheduleDemoCommand(3500, "pose", { pose_id: "front_victory_cast", duration_ms: 1300 });
  state.demoTimers.push(window.setTimeout(() => {
    state.localDemo = false;
    state.avatar = { ...state.avatar, action: "idle", control_source: null };
    sendCommand("pose", { pose_id: null }, { quiet: true });
    render();
  }, 5000));
  render();
}

async function stopLocalMovement() {
  stopRepeat(false);
  await sendCommand("stop");
}

async function toggleFlight() {
  const airborne = Boolean(state.avatar.airborne);
  await sendCommand("control", {
    source_kind: "keyboard",
    source_id: "companion-stage",
    source_sequence: Date.now(),
    source_epoch: "companion-window",
    lease_id: "companion-flight",
    ttl_ms: 400,
    intent: {
      move_x: 0,
      move_z: 0,
      ascend: 0,
      speed_mode: "walk",
      mobility_request: airborne ? "land" : "takeoff",
      held_actions: [],
    },
  });
}

async function pollRuntime() {
  if (!state.runtime) return;
  try {
    const [health, publicState] = await Promise.all([
      state.runtime.request("/api/companion/health"),
      state.runtime.request("/api/avatar/wizard/state"),
    ]);
    state.health = health;
    state.avatar = publicState.state || state.avatar;
    state.media = publicState.media || {};
    if (
      state.localDemo
      && !state.reactionsPaused
      && ["animating", "playing"].includes(state.media.status)
    ) {
      stopRepeat(false);
      await sendCommand("pose", { pose_id: null }, { quiet: true });
    }
    if (
      health.runtime_epoch
      && state.reactionPreferenceEpoch !== health.runtime_epoch
    ) {
      await applyReactionPreference();
      state.reactionPreferenceEpoch = health.runtime_epoch;
    }
    state.error = null;
    state.errorCode = "none";
    render();
  } catch (error) {
    if (state.connection === "live" && state.hasFrame) {
      state.health = { ...state.health, status: "reconnecting" };
      render();
      return;
    }
    setError(error, "health_unavailable");
  }
}

async function applyReactionPreference() {
  return state.runtime?.request("/api/companion/reactions", {
    method: "POST",
    body: { paused: state.reactionsPaused },
  });
}

async function shellAction(name, payload = {}, failureCode = "shell_action_failed") {
  try {
    const handled = await state.runtime?.shellAction(name, payload);
    if (!handled && !state.descriptor?.browserDemo) throw new Error(`${name} is unavailable`);
    return handled;
  } catch (error) {
    setError(error, failureCode);
    return false;
  }
}

async function openPrism() {
  await shellAction("open_prism_gt", {}, "open_prism_failed");
}

async function copyDiagnostics() {
  const text = JSON.stringify(diagnosticPayload(), null, 2);
  try {
    if (await state.runtime?.shellAction("copy_safe_diagnostics")) {
      elements.liveStatus.textContent = "Diagnostics copied.";
      return;
    }
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      const field = document.createElement("textarea");
      field.value = text;
      field.setAttribute("readonly", "");
      field.className = "sr-only";
      document.body.append(field);
      field.select();
      document.execCommand("copy");
      field.remove();
    }
    elements.liveStatus.textContent = "Diagnostics copied.";
  } catch (error) {
    setError(error, "copy_diagnostics_failed");
  }
}

function openDialog(dialog, trigger) {
  dialog.dataset.trigger = trigger.id;
  dialog.showModal();
}

function closeDialog(dialog) {
  dialog.close();
}

elements.playDemo.addEventListener("click", playDemo);
elements.repeatDemo.addEventListener("click", toggleRepeat);
elements.stopMovement.addEventListener("click", stopLocalMovement);
elements.flyToggle.addEventListener("click", toggleFlight);
document.getElementById("open-poses").addEventListener("click", (event) => openDialog(elements.posesDialog, event.currentTarget));
document.getElementById("open-more").addEventListener("click", (event) => openDialog(elements.moreDialog, event.currentTarget));
document.getElementById("open-prism").addEventListener("click", openPrism);
document.getElementById("settings-open-prism").addEventListener("click", openPrism);

document.querySelectorAll("[data-close-dialog]").forEach((button) => {
  button.addEventListener("click", () => closeDialog(button.closest("dialog")));
});

document.querySelectorAll("dialog").forEach((dialog) => {
  dialog.addEventListener("close", () => {
    const trigger = document.getElementById(dialog.dataset.trigger);
    trigger?.focus();
  });
});

document.getElementById("clear-pose").addEventListener("click", async () => {
  stopRepeat(false);
  await sendCommand("pose", { pose_id: null });
  closeDialog(elements.posesDialog);
});

elements.stage.addEventListener("keydown", (event) => {
  if (event.target !== elements.stage || event.metaKey || event.ctrlKey || event.altKey) return;
  const command = movementCommandForKey(event.key);
  if (!command) return;
  event.preventDefault();
  stopRepeat(false);
  sendCommand(command[0], command[1]);
});

elements.pauseReactions.addEventListener("change", async () => {
  state.reactionsPaused = elements.pauseReactions.checked;
  localStorage.setItem("wizard.reactionsPaused", String(state.reactionsPaused));
  if (state.reactionsPaused) await stopLocalMovement();
  try {
    await applyReactionPreference();
    state.reactionPreferenceEpoch = state.health.runtime_epoch || null;
  } catch (error) {
    setError(error, "reaction_preference_failed");
  }
  render();
});

elements.motionMode.addEventListener("change", () => {
  state.motionMode = elements.motionMode.value;
  localStorage.setItem("wizard.motionMode", state.motionMode);
  stream.setMotionMode(state.motionMode);
  render();
});

elements.launchAtLogin.addEventListener("change", async () => {
  state.launchAtLogin = elements.launchAtLogin.checked;
  localStorage.setItem("wizard.launchAtLogin", String(state.launchAtLogin));
  await shellAction("set_launch_at_login", { enabled: state.launchAtLogin });
  render();
});

systemReducedMotion.addEventListener("change", (event) => {
  if (localStorage.getItem("wizard.motionMode")) return;
  state.motionMode = event.matches ? "reduced" : "full";
  stream.setMotionMode(state.motionMode);
  render();
});

document.getElementById("retry-connection").addEventListener("click", () => {
  state.error = null;
  state.health = { ...state.health, status: "connecting" };
  stream.retry();
  pollRuntime();
  render();
});

document.getElementById("restart-engine").addEventListener("click", async () => {
  state.health = { ...state.health, status: "starting" };
  render();
  if (await shellAction("restart_engine", {}, "restart_failed")) {
    window.setTimeout(() => {
      stream.retry();
      pollRuntime();
    }, 500);
  }
});

document.getElementById("copy-diagnostics").addEventListener("click", copyDiagnostics);
document.getElementById("open-logs").addEventListener("click", () => shellAction("open_logs", {}, "open_logs_failed"));

window.addEventListener("beforeunload", () => stream.destroy());

async function start() {
  try {
    state.descriptor = await resolveRuntimeDescriptor();
    state.runtime = new RuntimeClient(state.descriptor);
    if (!state.descriptor.browserDemo) {
      try {
        state.launchAtLogin = Boolean(
          await state.runtime.shellAction("launch_at_login_status")
        );
      } catch {
        state.launchAtLogin = false;
      }
    }
    await loadPoseCatalog();
    stream.setMotionMode(state.motionMode);
    stream.connect(state.descriptor);
    await pollRuntime();
    window.setInterval(pollRuntime, 1500);
  } catch (error) {
    setError(error, "startup_failed");
  }
}

render();
start();
