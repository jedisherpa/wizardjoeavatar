import test from "node:test";
import assert from "node:assert/strict";

import { normalizeDescriptor, RuntimeClient } from "../runtime.js";
import { websocketUrlFor } from "../frame-stream.js";

test("runtime descriptor accepts Tauri-friendly snake case without exposing static defaults", () => {
  const descriptor = normalizeDescriptor({
    base_url: "http://127.0.0.1:41327/",
    frame_url: "ws://127.0.0.1:41327/ws/avatar/wizard",
    app_version: "0.1.0",
    is_tauri: true,
  });

  assert.equal(descriptor.baseUrl, "http://127.0.0.1:41327");
  assert.equal(descriptor.token, undefined);
  assert.equal(descriptor.websocketToken, undefined);
  assert.equal(descriptor.appVersion, "0.1.0");
  assert.equal(descriptor.httpTransport, "invoke");
  assert.equal(descriptor.frameTransport, "tauri-event");
});

test("Tauri descriptors without a proxy websocket select the event bridge", () => {
  const descriptor = normalizeDescriptor({
    base_url: "http://127.0.0.1:41327",
    is_tauri: true,
  });

  assert.equal(descriptor.httpTransport, "invoke");
  assert.equal(descriptor.frameTransport, "tauri-event");
  assert.equal(descriptor.frameEventName, "companion-frame");
});

test("a shell-owned websocket proxy must be selected explicitly", () => {
  const descriptor = normalizeDescriptor({
    websocket_url: "ws://127.0.0.1:41328/frames",
    frame_transport: "websocket",
    is_tauri: true,
  });

  assert.equal(descriptor.frameTransport, "websocket");
});

test("websocket URL is derived dynamically without credentials", () => {
  const url = new URL(websocketUrlFor(normalizeDescriptor({
    base_url: "http://127.0.0.1:41327",
  })));

  assert.equal(url.protocol, "ws:");
  assert.equal(url.pathname, "/ws/avatar/wizard");
  assert.equal(url.searchParams.get("codec"), "adaptive");
  assert.equal(url.searchParams.size, 1);
});

test("director commands use the dedicated runtime routes", async () => {
  globalThis.window = {};
  const client = new RuntimeClient({ browserDemo: false });
  const requests = [];
  client.request = async (path, options) => {
    requests.push({ path, options });
    return { state: { action: "idle" } };
  };

  await client.command("gaze", { target: "viewer" });
  await client.command("move", { x: 1, z: 5 });
  await client.command("path", { points: [{ x: 0, z: 5 }] });
  await client.command("expression", { expression: "happy" });
  await client.command("speak", { text: "Preview", duration_ms: 1000 });
  await client.command("speech-stop");

  assert.deepEqual(requests.map((request) => request.path), [
    "/api/avatar/wizard/gaze",
    "/api/avatar/wizard/move",
    "/api/avatar/wizard/path",
    "/api/avatar/wizard/expression",
    "/api/avatar/wizard/speak",
    "/api/avatar/wizard/speech-stop",
  ]);
  assert.ok(requests.every((request) => request.options.method === "POST"));
});

test("Tauri invoke propagates the bounded replay text response mode", async () => {
  globalThis.window = {
    __TAURI__: {
      core: {
        invoke: async (command, args) => {
          assert.equal(command, "companion_http_request");
          assert.deepEqual(args.request, {
            path: "/api/avatar/wizard/replay",
            method: "GET",
            body: null,
            responseType: "text",
          });
          return '{"record_type":"header"}\n';
        },
      },
    },
  };
  const client = new RuntimeClient({ browserDemo: false, httpTransport: "invoke" });

  assert.equal(
    await client.request("/api/avatar/wizard/replay", { responseType: "text" }),
    '{"record_type":"header"}\n'
  );
});

test("browser demo mocks progressive speech, permissions, and replay export", async () => {
  globalThis.window = {};
  const client = new RuntimeClient({ browserDemo: true });
  const character = await client.request("/api/avatar/wizard/character");
  assert.ok(character.capabilities.includes("progressive_text_preview"));

  const permission = await client.request("/api/avatar/wizard/director/permission-world", {
    method: "POST",
    body: {
      permissions: [{
        capability_kind: "director.simulation",
        posture: "promptable",
        required_scope_class: "current_surface",
        expires_at_ms: null,
      }],
    },
  });
  assert.equal(permission.status, "ready");
  assert.equal(
    permission.simulation_projection.affordances[0].permission_posture,
    "promptable"
  );

  await client.command("speak", { text: "Preview", progressive_text: true });
  const replay = await client.request("/api/avatar/wizard/replay", { responseType: "text" });
  assert.match(replay, /"route":"speak"/);
  assert.doesNotMatch(replay, /Preview/);
});
