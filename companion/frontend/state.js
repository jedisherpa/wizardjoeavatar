const HEALTH_PRESENTATION = Object.freeze({
  starting: { label: "Engine starting", source: "Local engine", tone: "pending", message: "Starting Joe..." },
  ready: { label: "Waiting for Prism", source: "No active source", tone: "good", message: "Waiting for Prism GT" },
  connecting: { label: "Connecting to Prism", source: "Connector handshake", tone: "pending", message: "Connecting..." },
  connected_idle: { label: "Ready", source: "Prism connected", tone: "good", message: "" },
  main_media: { label: "Reacting to media", source: "Prism media", tone: "active", message: "" },
  speech: { label: "Reacting to speech", source: "Prism speech", tone: "active", message: "" },
  paused: { label: "Media paused", source: "Prism connected", tone: "warning", message: "" },
  reconnecting: { label: "Reconnecting", source: "Connection interrupted", tone: "warning", message: "Reconnecting..." },
  degraded: { label: "Needs attention", source: "Connection problem", tone: "danger", message: "Joe needs help connecting" },
  controller_conflict: { label: "Controlled elsewhere", source: "Another controller", tone: "warning", message: "Local movement is unavailable" },
  reduced_motion: { label: "Reduced motion", source: "Motion preference", tone: "good", message: "" },
  stopped: { label: "Reactions paused", source: "Paused by you", tone: "warning", message: "Joe's reactions are paused" },
});

const SOURCE_LABELS = Object.freeze({
  main: "Prism media",
  main_media: "Prism media",
  speech: "Prism speech",
  persona: "Prism speech",
  demo: "Local demo",
  keyboard: "Local movement",
  browser: "Browser preview",
});

const STATUS_ALIASES = Object.freeze({
  disabled: "ready",
  waiting: "ready",
  animating: "main_media",
  stale: "reconnecting",
  idle: "connected_idle",
  healthy: "connected_idle",
  error: "degraded",
});

function safeText(value, fallback = "") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

export function derivePresentation(input = {}) {
  const health = input.health && typeof input.health === "object" ? input.health : {};
  const media = input.media && typeof input.media === "object" ? input.media : {};
  const avatar = input.avatar && typeof input.avatar === "object" ? input.avatar : {};
  let status = safeText(health.status, "starting");

  if (input.reactionsPaused) status = "stopped";
  else if (input.error) status = "degraded";
  else if (input.connection === "reconnecting" || input.connection === "closed") status = "reconnecting";
  else if (media.status === "animating") status = media.source === "speech" ? "speech" : "main_media";
  else if (media.status === "paused") status = "paused";
  else if (media.status === "stale") status = "reconnecting";
  else if (input.localDemo) status = "connected_idle";
  else if (STATUS_ALIASES[status]) status = STATUS_ALIASES[status];

  if (!HEALTH_PRESENTATION[status]) status = "degraded";
  const definition = HEALTH_PRESENTATION[status];
  const sourceKey = safeText(media.source || avatar.control_source || (input.localDemo ? "demo" : ""));
  const source = SOURCE_LABELS[sourceKey] || definition.source;
  const facing = safeText(avatar.facing, "forward").replaceAll("_", " ");
  const action = safeText(avatar.action || media.action, status === "connected_idle" ? "idle" : "waiting")
    .replaceAll("_", " ");

  return {
    status,
    label: input.localDemo && status === "connected_idle" ? "Playing local demo" : definition.label,
    source,
    tone: input.localDemo && status === "connected_idle" ? "active" : definition.tone,
    stageMessage: definition.message,
    facing,
    action,
    airborne: Boolean(avatar.airborne),
    showRecovery: ["degraded", "reconnecting"].includes(status),
  };
}

export function activityDescription(presentation) {
  const source = presentation.source === "No active source"
    ? "No media source is active"
    : `${presentation.source} is active`;
  const flight = presentation.airborne ? " Joe is airborne." : "";
  return `Wizard Joe is ${presentation.action}. ${source}. Joe is facing ${presentation.facing}.${flight}`;
}

export function movementCommandForKey(key) {
  const normalized = String(key || "").toLowerCase();
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
  };
  return commands[normalized] || null;
}

export function createRandomPoseCycle(poseIds, random = Math.random) {
  const unique = [...new Set((poseIds || []).filter((pose) => typeof pose === "string" && pose))];
  for (let index = unique.length - 1; index > 0; index -= 1) {
    const sample = Number(random());
    const bounded = Number.isFinite(sample) ? Math.min(0.999999, Math.max(0, sample)) : 0;
    const swapIndex = Math.floor(bounded * (index + 1));
    [unique[index], unique[swapIndex]] = [unique[swapIndex], unique[index]];
  }
  return unique;
}

function finiteNumber(value) {
  return Number.isFinite(value) ? value : null;
}

export function createSafeDiagnostics(input = {}) {
  const health = input.health && typeof input.health === "object" ? input.health : {};
  const media = input.media && typeof input.media === "object" ? input.media : {};
  const stream = input.stream && typeof input.stream === "object" ? input.stream : {};
  const preferences = input.preferences && typeof input.preferences === "object" ? input.preferences : {};

  return {
    app_version: safeText(input.appVersion, "unknown"),
    engine_version: safeText(health.engine_version || health.version, "unknown"),
    protocol_version: finiteNumber(health.protocol_version),
    build_commit: safeText(health.build_commit, "unknown"),
    process_state: safeText(health.status, "unknown"),
    runtime_epoch: safeText(health.runtime_epoch, "unknown"),
    character_id: safeText(health.character_id, "unknown"),
    frame_hub_running: Boolean(health.frame_hub_running),
    connector_enabled: Boolean(health.connector_enabled),
    active_source: safeText(media.source, "none"),
    scheduler_state: safeText(media.scheduler_state, "unknown"),
    accepted_sequence: finiteNumber(media.accepted_sequence),
    acknowledgement_fresh: Boolean(media.acknowledgement_fresh),
    error_code: safeText(input.errorCode, "none"),
    frame_rate: finiteNumber(stream.fps),
    queue_depth: finiteNumber(stream.queueDepth),
    websocket_state: safeText(stream.state, "unknown"),
    motion_mode: safeText(preferences.motionMode, "unknown"),
    reactions_paused: Boolean(preferences.reactionsPaused),
    launch_at_login: Boolean(preferences.launchAtLogin),
    logs: "Companion Logs",
  };
}

export { HEALTH_PRESENTATION };
