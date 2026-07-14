import test from "node:test";
import assert from "node:assert/strict";

import {
  activityDescription,
  createRandomPoseCycle,
  createSafeDiagnostics,
  derivePresentation,
  movementCommandForKey,
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

test("movement keys map only to explicit stage commands", () => {
  assert.deepEqual(movementCommandForKey("ArrowLeft"), ["walk-left", { distance: 1.2 }]);
  assert.deepEqual(movementCommandForKey(" "), ["stop", {}]);
  assert.equal(movementCommandForKey("Enter"), null);
  assert.equal(movementCommandForKey("Tab"), null);
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
      title: "Private audiobook title",
      url: "https://private.invalid",
    },
    preferences: { motionMode: "reduced" },
    token: "also-secret",
  });
  const copied = JSON.stringify(diagnostics);

  assert.equal(diagnostics.app_version, "1.2.3");
  assert.equal(diagnostics.motion_mode, "reduced");
  assert.doesNotMatch(copied, /secret|private|audiobook|https:/i);
});
