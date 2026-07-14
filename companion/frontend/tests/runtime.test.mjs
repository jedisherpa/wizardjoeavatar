import test from "node:test";
import assert from "node:assert/strict";

import { normalizeDescriptor } from "../runtime.js";
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
