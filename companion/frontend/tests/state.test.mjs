import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";

import {
  activityDescription,
  createActionPayload,
  createExpressionPayload,
  createGazePayload,
  createMovePayload,
  createPathPayload,
  createPermissionSimulationPayload,
  createRandomPoseCycle,
  createSafeDiagnostics,
  createSafeCueInspection,
  createSpeechPayload,
  deriveDirectorState,
  derivePresentation,
  formatMediaTime,
  movementCommandForKey,
  normalizeViewportProfile,
  summarizeReplayExport,
  supportsProgressiveText,
} from "../state.js";

test("health presentation maps media activity and source truthfully", () => {
  const presentation = derivePresentation({
    health: { status: "connected_idle" },
    media: { status: "animating", source: "speech", action: "speaking" },
    avatar: { facing: "south_east", airborne: false },
  });

  assert.equal(presentation.status, "speech");
  assert.equal(presentation.label, "Reacting to speech");
  assert.equal(presentation.source, "Prism speech");
  assert.match(activityDescription(presentation), /speaking/);
  assert.match(activityDescription(presentation), /south east/);
});

test("user reaction pause takes precedence over transport state", () => {
  const presentation = derivePresentation({
    health: { status: "main_media" },
    media: { status: "animating", source: "main" },
    reactionsPaused: true,
  });

  assert.equal(presentation.status, "stopped");
  assert.equal(presentation.tone, "warning");
});

test("truthful Prism activity outranks a local demo", () => {
  const presentation = derivePresentation({
    health: { status: "ready" },
    media: { status: "animating", source: "speech", action: "speaking" },
    localDemo: true,
  });

  assert.equal(presentation.status, "speech");
  assert.equal(presentation.label, "Reacting to speech");
  assert.equal(presentation.source, "Prism speech");
});

test("stale media state never presents as a fresh connection", () => {
  const presentation = derivePresentation({
    health: { status: "ready" },
    media: { status: "stale", source: "main" },
  });

  assert.equal(presentation.status, "reconnecting");
  assert.equal(presentation.tone, "warning");
});

test("director state exposes authoritative runtime and rendered character truth", () => {
  const director = deriveDirectorState({
    health: { status: "ready", connector_enabled: true },
    connection: "live",
    media: {
      status: "animating",
      source: "speech",
      scheduler_state: "playing",
      performance_mode: "narrative",
      authoritative_media_time_ms: 3_723_045,
      score_id: "compiled:chapter-12",
    },
    avatar: {
      mouth: "wide",
      action: "speaking",
      pose_id: "controller_pose",
      animation_clip_id: "controller_clip",
      control_source: "prism",
    },
    diagnostics: {
      pose_id: "front_explaining",
      animation_clip_id: "explain_front",
    },
    stream: { state: "live", fps: 24 },
    hasFrame: true,
  });

  assert.equal(director.connection, "Live");
  assert.equal(director.connector, "Enabled");
  assert.equal(director.playback, "Playing");
  assert.equal(director.source, "Speech");
  assert.equal(director.mode, "Narrative");
  assert.equal(director.mediaTime, "01:02:03.045");
  assert.equal(director.mouth, "Wide");
  assert.equal(director.action, "Speaking");
  assert.equal(director.pose, "front_explaining");
  assert.equal(director.clip, "explain_front");
  assert.equal(director.score, "compiled:chapter-12");
  assert.equal(director.scheduler, "Playing");
  assert.equal(director.frames, "Live - 24 fps");
  assert.equal(director.tone, "active");
});

test("director state degrades optional diagnostics without inventing values", () => {
  const director = deriveDirectorState({
    health: { status: "ready" },
    connection: "live",
    media: { status: "waiting", source: null, scheduler_state: "no_session" },
    avatar: { action: "idle", mouth: "closed", pose_id: "front_idle" },
    stream: { state: "live", fps: 0 },
  });

  assert.equal(director.playback, "Waiting");
  assert.equal(director.connector, "Unavailable");
  assert.equal(director.source, "None");
  assert.equal(director.mode, "Unavailable");
  assert.equal(director.mediaTime, "Unavailable");
  assert.equal(director.score, "Unavailable");
  assert.equal(director.clip, "Unavailable");
  assert.equal(director.action, "Idle");
  assert.equal(director.mouth, "Closed");
});

test("scoreless scheduler is explicit when no score identifier exists", () => {
  const director = deriveDirectorState({
    connection: "live",
    media: { status: "animating", scheduler_state: "scoreless", media_time_ms: 905 },
  });

  assert.equal(director.score, "Scoreless");
  assert.equal(director.mediaTime, "00:00.905");
  assert.equal(formatMediaTime(-1), "Unavailable");
});

test("movement keys map only to explicit stage commands", () => {
  assert.deepEqual(movementCommandForKey("ArrowLeft"), ["walk-left", { distance: 1.2 }]);
  assert.deepEqual(movementCommandForKey(" "), ["stop", {}]);
  assert.equal(movementCommandForKey("Enter"), null);
  assert.equal(movementCommandForKey("Tab"), null);
});

test("director command builders clamp numeric input and constrain option sets", () => {
  assert.deepEqual(createMovePayload({ x: "22", z: "-4", speed: "2" }), {
    x: 20,
    z: 0,
    speed: 2,
  });
  assert.deepEqual(createGazePayload("left"), { target: "left" });
  assert.deepEqual(createGazePayload("behind"), { target: "viewer" });
  assert.deepEqual(createExpressionPayload("amused"), { expression: "amused" });
  assert.deepEqual(createExpressionPayload("private-expression"), { expression: "neutral" });
  assert.deepEqual(createActionPayload({ action: "magic_cast", durationMs: "50000" }), {
    action: "magic_cast",
    duration_ms: 30000,
  });
});

test("path and speech builders emit route-ready payloads", () => {
  const path = createPathPayload({ preset: "figure-eight", loop: true });
  assert.equal(path.points.length, 7);
  assert.deepEqual(path.points.at(-1), { x: 0, z: 5 });
  assert.equal(path.loop, true);

  const unsupported = createSpeechPayload({
    text: " Preview line. ",
    durationMs: 1800,
    progressiveText: true,
  });
  assert.deepEqual(unsupported, { text: "Preview line.", duration_ms: 1800 });
  assert.deepEqual(createSpeechPayload({
    text: "Preview line.",
    durationMs: 1800,
    progressiveText: true,
    progressiveSupported: true,
  }), {
    text: "Preview line.",
    duration_ms: 1800,
    progressive_text: true,
  });
  assert.equal(supportsProgressiveText({ capabilities: ["progressive_text_preview"] }), true);
  assert.equal(supportsProgressiveText({ capabilities: ["speech_overlay"] }), false);
});

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

test("permission simulation builder hashes an exact content-free backend payload", async () => {
  const payload = await createPermissionSimulationPayload({
    posture: "granted",
    scope: "current_surface",
    purpose: "director_preview",
    surface: "companion.stage",
    expiry: "15m",
  }, 10_000);
  const identity = {
    schema_version: payload.schema_version,
    source_epoch: payload.source_epoch,
    observed_at_ms: payload.observed_at_ms,
    permissions: payload.permissions,
  };
  const expectedHash = createHash("sha256").update(canonicalJson(identity)).digest("hex");

  assert.equal(payload.source_epoch, "director-simulation:v1");
  assert.equal(payload.permissions[0].posture, "granted");
  assert.equal(payload.permissions[0].granted_scope_class, "current_surface");
  assert.equal(payload.permissions[0].expires_at_ms, 910_000);
  assert.equal(payload.state_sha256, `sha256:${expectedHash}`);
  assert.doesNotMatch(JSON.stringify(payload), /conversation|transcript|speech_text/i);
});

test("cue and replay inspection remain content-free", async () => {
  const cue = createSafeCueInspection({
    avatar: {
      semantic_cue: "review",
      semantic_gesture: "think",
      semantic_transition: "accepted",
      semantic_advisory_active: true,
      simulation_tick: 42,
      state_revision: 45,
      speech_text: "private conversation",
    },
    diagnostics: { animation_node_id: "ground_think", private_text: "hidden" },
    media: { scheduler_state: "playing", accepted_sequence: 8, title: "hidden title" },
  });
  assert.deepEqual(cue, {
    semantic_cue: "review",
    semantic_gesture: "think",
    semantic_transition: "accepted",
    semantic_active: true,
    simulation_tick: 42,
    state_revision: 45,
    animation_node_id: "ground_think",
    animation_clip_id: "unknown",
    scheduler_state: "playing",
    accepted_sequence: 8,
  });
  assert.doesNotMatch(JSON.stringify(cue), /private|hidden|title/i);

  const replay = await summarizeReplayExport([
    JSON.stringify({ record_sequence: 0, simulation_tick: 0, payload: { text: "private" } }),
    JSON.stringify({ record_sequence: 1, simulation_tick: 60, payload: { text: "still private" } }),
    "",
  ].join("\n"));
  assert.equal(replay.retained_records, 2);
  assert.equal(replay.first_sequence, 0);
  assert.equal(replay.last_sequence, 1);
  assert.equal(replay.last_tick, 60);
  assert.match(replay.retained_sha256, /^[0-9a-f]{64}$/);
  assert.doesNotMatch(JSON.stringify(replay), /private/i);
  assert.equal(normalizeViewportProfile("mobile"), "mobile");
  assert.equal(normalizeViewportProfile("tablet"), "desktop");
});

test("random pose cycles contain every unique pose exactly once", () => {
  const samples = [0.9, 0.1, 0.5];
  let index = 0;
  const cycle = createRandomPoseCycle(
    ["front_idle", "magic_cast", "front_idle", "explaining"],
    () => samples[index++ % samples.length]
  );
  assert.equal(cycle.length, 3);
  assert.deepEqual([...cycle].sort(), ["explaining", "front_idle", "magic_cast"]);
});

test("copied diagnostics are allowlisted and omit private transport data", () => {
  const diagnostics = createSafeDiagnostics({
    appVersion: "1.2.3",
    health: {
      status: "ready",
      runtime_epoch: "epoch-2",
      protocol_version: 1,
      private_path: "/Users/example/private",
      token: "secret",
    },
    media: {
      source: "main",
      scheduler_state: "playing",
      media_time_ms: 2400,
      title: "Private audiobook title",
      url: "https://private.invalid",
    },
    avatar: { action: "speaking", mouth: "open", pose_id: "front_idle" },
    diagnostics: { animation_clip_id: "idle_front", private_path: "/private" },
    performance: { score_id: "compiled:public-score", provider_payload: "private" },
    preferences: { motionMode: "reduced" },
    token: "also-secret",
  });
  const copied = JSON.stringify(diagnostics);

  assert.equal(diagnostics.app_version, "1.2.3");
  assert.equal(diagnostics.motion_mode, "reduced");
  assert.equal(diagnostics.authoritative_media_time_ms, 2400);
  assert.equal(diagnostics.animation_clip_id, "idle_front");
  assert.equal(diagnostics.score_id, "compiled:public-score");
  assert.doesNotMatch(copied, /secret|private|audiobook|https:/i);
});
