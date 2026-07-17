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

function record(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function firstText(...values) {
  for (const value of values) {
    const text = safeText(value);
    if (text) return text;
  }
  return "";
}

function firstFinite(...values) {
  for (const value of values) {
    if (Number.isFinite(value)) return value;
  }
  return null;
}

function readableValue(value, fallback = "Unavailable") {
  const text = safeText(value);
  if (!text) return fallback;
  return text.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatMediaTime(milliseconds) {
  if (!Number.isFinite(milliseconds) || milliseconds < 0) return "Unavailable";
  const total = Math.floor(milliseconds);
  const hours = Math.floor(total / 3_600_000);
  const minutes = Math.floor((total % 3_600_000) / 60_000);
  const seconds = Math.floor((total % 60_000) / 1000);
  const millis = total % 1000;
  const clock = hours > 0
    ? `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`
    : `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  return `${clock}.${String(millis).padStart(3, "0")}`;
}

export function deriveDirectorState(input = {}) {
  const health = record(input.health);
  const media = record(input.media);
  const avatar = record(input.avatar);
  const diagnostics = record(input.diagnostics);
  const performanceState = record(input.performance);
  const runtime = record(input.runtime);
  const stream = record(input.stream);
  const healthStatus = firstText(health.status, runtime.status);
  const connectionState = firstText(input.connection, stream.state, "connecting");

  let connection = readableValue(connectionState, "Connecting");
  let tone = "pending";
  if (input.error || healthStatus === "degraded" || connectionState === "error") {
    connection = "Degraded";
    tone = "danger";
  } else if (["reconnecting", "closed"].includes(connectionState)) {
    connection = "Reconnecting";
    tone = "warning";
  } else if (connectionState === "live") {
    connection = "Live";
    tone = "good";
  }

  const playbackStatus = firstText(media.playback_state, media.status);
  const playbackLabels = {
    animating: "Playing",
    playing: "Playing",
    ready: "Ready",
    waiting: "Waiting",
    paused: "Paused",
    stopped: "Stopped",
    ended: "Ended",
    stale: "Stale",
    disabled: "Connector disabled",
  };
  const playback = input.reactionsPaused
    ? "Reactions paused"
    : playbackLabels[playbackStatus] || readableValue(playbackStatus);
  if (connectionState === "live" && ["animating", "playing"].includes(playbackStatus)) tone = "active";
  if (connectionState === "live" && ["paused", "stale"].includes(playbackStatus)) tone = "warning";

  const scheduler = firstText(
    media.scheduler_state,
    performanceState.scheduler_state,
    runtime.scheduler_state
  );
  const scoreId = firstText(
    media.score_id,
    performanceState.score_id,
    runtime.score_id,
    diagnostics.score_id
  );
  const mediaTimeMs = firstFinite(
    media.authoritative_media_time_ms,
    media.media_time_ms,
    media.current_time_ms,
    performanceState.authoritative_media_time_ms,
    performanceState.media_time_ms,
    runtime.authoritative_media_time_ms,
    runtime.media_time_ms,
    diagnostics.authoritative_media_time_ms,
    diagnostics.media_time_ms
  );
  const fps = firstFinite(stream.fps, diagnostics.fps);
  const frameState = firstText(stream.state);
  const connectorStatus = firstText(health.connector_status, runtime.connector_status);
  const connectorKnown = Object.prototype.hasOwnProperty.call(health, "connector_enabled");
  let connector = "Unavailable";
  if (connectorStatus) connector = readableValue(connectorStatus);
  else if (connectorKnown) connector = health.connector_enabled ? "Enabled" : "Disabled";

  return {
    connection,
    connector,
    playback,
    source: readableValue(firstText(media.source, media.source_slot), "None"),
    mode: readableValue(firstText(
      media.performance_mode,
      media.mode,
      performanceState.mode,
      performanceState.performance_mode,
      runtime.performance_mode
    )),
    mediaTime: formatMediaTime(mediaTimeMs),
    mouth: readableValue(firstText(
      avatar.mouth,
      media.mouth,
      performanceState.mouth,
      diagnostics.mouth_state
    )),
    action: readableValue(firstText(
      avatar.action,
      media.action,
      performanceState.action,
      diagnostics.current_action
    )),
    pose: firstText(diagnostics.pose_id, avatar.pose_id) || "Unavailable",
    clip: firstText(diagnostics.animation_clip_id, avatar.animation_clip_id) || "Unavailable",
    score: scoreId || (scheduler === "scoreless" ? "Scoreless" : "Unavailable"),
    scheduler: readableValue(scheduler),
    engine: readableValue(healthStatus, "Unknown"),
    frames: frameState === "live" && fps !== null
      ? `Live - ${Math.round(fps)} fps`
      : readableValue(frameState, input.hasFrame ? "Live" : "Waiting"),
    control: readableValue(firstText(avatar.control_source), "None"),
    summary: connectionState === "live" ? playback : connection,
    tone,
  };
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

const GAZE_TARGETS = new Set(["viewer", "left", "right", "up", "down"]);
const EXPRESSIONS = new Set([
  "neutral",
  "happy",
  "thinking",
  "surprised",
  "worried",
  "amused",
  "confident",
  "focused",
  "skeptical",
  "explaining",
]);
const ACTIONS = new Set([
  "idle",
  "explaining",
  "thinking",
  "pointing",
  "magic_cast",
  "reaction",
  "flourish",
  "staff_spin",
  "victory_cast",
  "shush",
  "celebrate",
]);
const PATH_PRESETS = Object.freeze({
  "cross-stage": Object.freeze([
    Object.freeze({ x: -3, z: 5 }),
    Object.freeze({ x: 3, z: 5 }),
    Object.freeze({ x: 0, z: 5 }),
  ]),
  "front-arc": Object.freeze([
    Object.freeze({ x: -2.5, z: 5.8 }),
    Object.freeze({ x: -1.25, z: 4.2 }),
    Object.freeze({ x: 0, z: 3.7 }),
    Object.freeze({ x: 1.25, z: 4.2 }),
    Object.freeze({ x: 2.5, z: 5.8 }),
  ]),
  "figure-eight": Object.freeze([
    Object.freeze({ x: 0, z: 5 }),
    Object.freeze({ x: -2, z: 3.8 }),
    Object.freeze({ x: -2, z: 6.2 }),
    Object.freeze({ x: 0, z: 5 }),
    Object.freeze({ x: 2, z: 3.8 }),
    Object.freeze({ x: 2, z: 6.2 }),
    Object.freeze({ x: 0, z: 5 }),
  ]),
});

function boundedNumber(value, fallback, minimum, maximum) {
  const number = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(maximum, Math.max(minimum, number));
}

function selectedValue(value, allowed, fallback) {
  const normalized = safeText(value, fallback);
  return allowed.has(normalized) ? normalized : fallback;
}

export function createMovePayload(input = {}) {
  return {
    x: boundedNumber(input.x, 0, -20, 20),
    z: boundedNumber(input.z, 5, 0, 20),
    speed: boundedNumber(input.speed, 1.25, 0.1, 5),
  };
}

export function createPathPayload(input = {}) {
  const preset = Object.prototype.hasOwnProperty.call(PATH_PRESETS, input.preset)
    ? input.preset
    : "cross-stage";
  return {
    points: PATH_PRESETS[preset].map((point) => ({ ...point })),
    speed: boundedNumber(input.speed, 1.25, 0.1, 5),
    loop: Boolean(input.loop),
  };
}

export function createGazePayload(target) {
  return { target: selectedValue(target, GAZE_TARGETS, "viewer") };
}

export function createExpressionPayload(expression) {
  return { expression: selectedValue(expression, EXPRESSIONS, "neutral") };
}

export function createActionPayload(input = {}) {
  return {
    action: selectedValue(input.action, ACTIONS, "idle"),
    duration_ms: Math.round(boundedNumber(input.durationMs, 1600, 0, 30_000)),
  };
}

export function createSpeechPayload(input = {}) {
  const payload = {
    text: safeText(input.text, "The stars prefer a tidy spellbook.").slice(0, 1000),
    duration_ms: Math.round(boundedNumber(input.durationMs, 2400, 250, 60_000)),
  };
  if (input.progressiveSupported) payload.progressive_text = Boolean(input.progressiveText);
  return payload;
}

export function supportsProgressiveText(character = {}) {
  const capabilities = Array.isArray(character.capabilities) ? character.capabilities : [];
  return capabilities.some((capability) => [
    "progressive_text",
    "progressive_text_preview",
    "progressive_reveal",
    "text_reveal",
  ].includes(capability));
}

export function normalizeViewportProfile(value) {
  return value === "mobile" ? "mobile" : "desktop";
}

export function createSafeCueInspection(input = {}) {
  const avatar = record(input.avatar);
  const diagnostics = record(input.diagnostics);
  const media = record(input.media);
  return {
    semantic_cue: safeText(avatar.semantic_cue, "none"),
    semantic_gesture: safeText(avatar.semantic_gesture, "none"),
    semantic_transition: safeText(avatar.semantic_transition, "inactive"),
    semantic_active: Boolean(avatar.semantic_advisory_active),
    simulation_tick: finiteNumber(avatar.simulation_tick),
    state_revision: finiteNumber(avatar.state_revision),
    animation_node_id: safeText(diagnostics.animation_node_id || avatar.animation_node_id, "unknown"),
    animation_clip_id: safeText(diagnostics.animation_clip_id || avatar.animation_clip_id, "unknown"),
    scheduler_state: safeText(media.scheduler_state, "unknown"),
    accepted_sequence: finiteNumber(media.accepted_sequence),
  };
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => (
      `${JSON.stringify(key)}:${canonicalJson(value[key])}`
    )).join(",")}}`;
  }
  return JSON.stringify(value);
}

async function sha256Hex(value) {
  const bytes = new TextEncoder().encode(value);
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export async function createPermissionSimulationPayload(input = {}, nowMs = Date.now()) {
  const observedAtMs = Math.max(0, Math.floor(boundedNumber(nowMs, 0, 0, Number.MAX_SAFE_INTEGER)));
  const posture = selectedValue(
    input.posture,
    new Set(["granted", "denied", "promptable", "unavailable", "unknown"]),
    "promptable"
  );
  const scope = safeText(input.scope, "current_surface").replace(/[^A-Za-z0-9._:-]/g, "_").slice(0, 128);
  const purpose = safeText(input.purpose, "director_preview").replace(/[^A-Za-z0-9._:-]/g, "_").slice(0, 128);
  const surface = safeText(input.surface, "companion.stage").replace(/[^A-Za-z0-9._:-]/g, "_").slice(0, 128);
  const expiryOffsets = { "15m": 900_000, "1h": 3_600_000, expired: -1 };
  const expiry = Object.prototype.hasOwnProperty.call(expiryOffsets, input.expiry)
    ? input.expiry
    : "unbounded";
  const granted = posture === "granted";
  const grantedAtMs = granted
    ? (expiry === "expired" ? Math.max(0, observedAtMs - 1000) : observedAtMs)
    : null;
  const expiresAtMs = expiry === "unbounded"
    ? null
    : expiry === "expired"
      ? Math.max(grantedAtMs || 0, observedAtMs - 1)
      : observedAtMs + expiryOffsets[expiry];
  const permission = {
    capability_kind: "director.simulation",
    posture,
    required_scope_class: scope,
    granted_scope_class: granted ? scope : null,
    purpose_code: purpose,
    granted_at_ms: grantedAtMs,
    affected_surfaces: [surface].sort(),
    app_link_state: "not_required",
    expires_at_ms: expiresAtMs,
    revoked: false,
  };
  const identity = {
    schema_version: 1,
    source_epoch: "director-simulation:v1",
    observed_at_ms: observedAtMs,
    permissions: [permission],
  };
  return {
    ...identity,
    state_sha256: `sha256:${await sha256Hex(canonicalJson(identity))}`,
  };
}

export async function summarizeReplayExport(text) {
  const source = typeof text === "string" ? text : "";
  const records = source.split(/\r?\n/).filter(Boolean).flatMap((line) => {
    try {
      const parsed = JSON.parse(line);
      return parsed && typeof parsed === "object" ? [parsed] : [];
    } catch {
      return [];
    }
  });
  const sequences = records.map((item) => item.record_sequence).filter(Number.isFinite);
  const ticks = records.map((item) => item.simulation_tick).filter(Number.isFinite);
  return {
    retained_records: records.length,
    first_sequence: sequences.length ? Math.min(...sequences) : null,
    last_sequence: sequences.length ? Math.max(...sequences) : null,
    last_tick: ticks.length ? Math.max(...ticks) : null,
    retained_sha256: await sha256Hex(source),
  };
}

function finiteNumber(value) {
  return Number.isFinite(value) ? value : null;
}

export function createSafeDiagnostics(input = {}) {
  const health = input.health && typeof input.health === "object" ? input.health : {};
  const media = input.media && typeof input.media === "object" ? input.media : {};
  const avatar = input.avatar && typeof input.avatar === "object" ? input.avatar : {};
  const diagnostics = input.diagnostics && typeof input.diagnostics === "object" ? input.diagnostics : {};
  const performanceState = input.performance && typeof input.performance === "object" ? input.performance : {};
  const runtime = input.runtime && typeof input.runtime === "object" ? input.runtime : {};
  const stream = input.stream && typeof input.stream === "object" ? input.stream : {};
  const preferences = input.preferences && typeof input.preferences === "object" ? input.preferences : {};
  const schedulerState = firstText(media.scheduler_state, performanceState.scheduler_state, runtime.scheduler_state);

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
    playback_state: safeText(media.playback_state || media.status, "unknown"),
    performance_mode: safeText(
      media.performance_mode || media.mode || performanceState.mode || runtime.performance_mode,
      "unknown"
    ),
    authoritative_media_time_ms: firstFinite(
      media.authoritative_media_time_ms,
      media.media_time_ms,
      performanceState.authoritative_media_time_ms,
      performanceState.media_time_ms,
      runtime.authoritative_media_time_ms,
      runtime.media_time_ms,
      diagnostics.authoritative_media_time_ms,
      diagnostics.media_time_ms
    ),
    current_action: safeText(avatar.action || media.action || diagnostics.current_action, "unknown"),
    mouth_state: safeText(avatar.mouth || media.mouth || diagnostics.mouth_state, "unknown"),
    pose_id: safeText(diagnostics.pose_id || avatar.pose_id, "unknown"),
    animation_clip_id: safeText(
      diagnostics.animation_clip_id || avatar.animation_clip_id,
      "unknown"
    ),
    score_id: safeText(media.score_id || performanceState.score_id || runtime.score_id, "none"),
    scheduler_state: safeText(schedulerState, "unknown"),
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
