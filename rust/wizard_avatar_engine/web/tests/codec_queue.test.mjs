import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import {
  AscilineStreamClient,
  BoundedByteQueue,
  inspectEnvelope,
  parseInit,
} from "../asciline_client.js";

function envelope(sequence, tag, payload = []) {
  const bytes = new Uint8Array(5 + payload.length);
  new DataView(bytes.buffer).setUint32(0, sequence, false);
  bytes[4] = tag;
  bytes.set(payload, 5);
  return bytes.buffer;
}

async function deflate(bytes) {
  const stream = new Blob([bytes]).stream().pipeThrough(new CompressionStream("deflate"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

test("INIT keeps legacy fields and adds epoch metadata", () => {
  const init = parseInit("INIT:24:5:480:270:0:0:0.000:EPOCH:42:CELL_BYTES:4:CODEC:1");
  assert.deepEqual(init, { fps: 24, cols: 480, rows: 270, epoch: 42, cellBytes: 4, codec: 1 });
});

test("encoded dependency queue remains count and byte bounded", () => {
  const queue = new BoundedByteQueue(4, 24, 250, () => 1000);
  assert.equal(queue.push(envelope(1, 0, [1, 2, 3])), true);
  assert.equal(queue.push(envelope(2, 0, new Array(17).fill(0))), false);
  assert.equal(queue.length, 0, "overflow clears dependency history");
  assert.equal(queue.bytes, 0);
});

test("missing delta requests one resync and never decodes the broken chain", async () => {
  const decoded = [];
  const controls = [];
  const client = new AscilineStreamClient({
    decoderFactory: () => ({
      reset() {},
      async decode(message) {
        const { sequence } = inspectEnvelope(message);
        decoded.push(sequence);
        return { frameIndex: sequence, frame: new Uint8Array([32, 255, 255, 255]) };
      },
    }),
    sendControl: (control) => controls.push(control),
    now: () => 0,
  });
  client.beginGeneration({ fps: 24, cols: 1, rows: 1, epoch: 7, cellBytes: 4, codec: 1 });

  client.enqueue(envelope(10, 0, [32, 255, 255, 255]));
  await client.drain();
  client.enqueue(envelope(12, 2));
  client.enqueue(envelope(13, 2));
  await client.drain();

  assert.deepEqual(decoded, [10]);
  assert.equal(controls.length, 1);
  assert.equal(controls[0].type, "resync");
  assert.equal(controls[0].payload.reason, "missing_delta");
  assert.equal(client.awaitingKeyframe, true);
});

test("stale generation decode completion cannot enter presentation queue", async () => {
  let release;
  const pending = new Promise((resolve) => { release = resolve; });
  const client = new AscilineStreamClient({
    decoderFactory: () => ({
      reset() {},
      async decode() {
        await pending;
        return { frameIndex: 1, frame: new Uint8Array([32, 255, 255, 255]) };
      },
    }),
    sendControl() {},
    now: () => 0,
  });
  const init = { fps: 24, cols: 1, rows: 1, epoch: 1, cellBytes: 4, codec: 1 };
  client.beginGeneration(init);
  client.enqueue(envelope(1, 0, [32, 255, 255, 255]));
  const drain = client.drain();
  client.beginGeneration({ ...init, epoch: 2 });
  release();
  await drain;
  assert.equal(client.presentationQueue.length, 0);
});

test("resync and invalidate clear stale complete presentation frames", () => {
  const controls = [];
  const client = new AscilineStreamClient({
    decoderFactory: () => ({ reset() {}, async decode() {} }),
    sendControl: (control) => controls.push(control),
    now: () => 0,
  });
  const init = { fps: 24, cols: 1, rows: 1, epoch: 9, cellBytes: 4, codec: 1 };
  client.beginGeneration(init);
  client.presentationQueue.push({ sequence: 4, presentationTime: 0, frame: new Uint8Array(4) });
  client.requestResync("missing_delta");
  assert.equal(client.presentationQueue.length, 0);
  client.presentationQueue.push({ sequence: 5, presentationTime: 0, frame: new Uint8Array(4) });
  client.invalidate();
  assert.equal(client.presentationQueue.length, 0);
  assert.equal(controls.length, 1);
});

test("resync invalidates an in-flight decode before it can present", async () => {
  let release;
  let decoderCount = 0;
  const pending = new Promise((resolve) => { release = resolve; });
  const client = new AscilineStreamClient({
    decoderFactory: () => ({
      id: decoderCount += 1,
      reset() {},
      async decode() {
        await pending;
        return { frameIndex: 1, frame: new Uint8Array([32, 255, 255, 255]) };
      },
    }),
    sendControl() {},
    now: () => 0,
  });
  client.beginGeneration({ fps: 24, cols: 1, rows: 1, epoch: 11, cellBytes: 4, codec: 1 });
  client.enqueue(envelope(1, 0, [32, 255, 255, 255]));
  const drain = client.drain();
  client.requestResync("generation_reset");
  release();
  await drain;
  assert.equal(decoderCount, 2, "resync replaces rather than resets the in-flight decoder");
  assert.equal(client.presentationQueue.length, 0);
  assert.equal(client.awaitingKeyframe, true);
});

test("stale decoder completion cannot poison the replacement generation", async () => {
  let releaseFirst;
  const firstPending = new Promise((resolve) => { releaseFirst = resolve; });
  let decoderCount = 0;
  const histories = [];
  const client = new AscilineStreamClient({
    decoderFactory: () => {
      const decoderId = decoderCount += 1;
      let previous = null;
      return {
        reset() { previous = null; },
        async decode(message) {
          const { sequence } = inspectEnvelope(message);
          if (decoderId === 1) await firstPending;
          previous = sequence;
          histories.push([decoderId, previous]);
          return { frameIndex: sequence, frame: new Uint8Array([32, 255, 255, 255]) };
        },
      };
    },
    sendControl() {},
    now: () => 0,
  });
  client.beginGeneration({ fps: 24, cols: 1, rows: 1, epoch: 17, cellBytes: 4, codec: 1 });
  client.enqueue(envelope(1, 0, [32, 255, 255, 255]));
  const staleDrain = client.drain();
  client.requestResync("queue_overflow");
  client.enqueue(envelope(2, 0, [32, 255, 255, 255]));
  await client.drain();
  releaseFirst();
  await staleDrain;

  assert.deepEqual(histories, [[2, 2], [1, 1]]);
  assert.deepEqual(client.presentationQueue.items.map((frame) => frame.sequence), [2]);
  assert.equal(client.lastValidSequence, 2);
});

test("hidden resume drops stale work and requests one fresh keyframe", () => {
  const controls = [];
  const client = new AscilineStreamClient({
    decoderFactory: () => ({ reset() {}, async decode() {} }),
    sendControl: (control) => controls.push(control),
    now: () => 0,
  });
  client.beginGeneration({ fps: 24, cols: 1, rows: 1, epoch: 12, cellBytes: 4, codec: 1 });
  client.presentationQueue.push({ sequence: 2, presentationTime: 0, frame: new Uint8Array(4) });
  client.suspend();
  assert.equal(client.presentationQueue.length, 0);
  assert.equal(client.enqueue(envelope(3, 0, [32, 255, 255, 255])), false);
  client.resume();
  client.resume();
  assert.equal(controls.length, 1);
  assert.equal(controls[0].payload.reason, "visibility_resume");
  assert.equal(client.awaitingKeyframe, true);
});

test("context restore invalidates complete frames and requests one resync", () => {
  const controls = [];
  const client = new AscilineStreamClient({
    decoderFactory: () => ({ reset() {}, async decode() {} }),
    sendControl: (control) => controls.push(control),
    now: () => 0,
  });
  client.beginGeneration({ fps: 24, cols: 1, rows: 1, epoch: 13, cellBytes: 4, codec: 1 });
  client.presentationQueue.push({ sequence: 9, presentationTime: 0, frame: new Uint8Array(4) });
  client.contextRestored();
  assert.equal(client.presentationQueue.length, 0);
  assert.equal(controls.length, 1);
  assert.equal(controls[0].payload.reason, "context_restore");
});

test("malformed RLE, delta index, unknown tag, and frame size each fail into one resync", async () => {
  const cases = [];
  cases.push(envelope(0, 3, await deflate(new Uint8Array([1, 0, 32]))));
  cases.push(envelope(0, 99, []));
  cases.push(envelope(0, 0, [32, 255, 255, 255, 32, 255, 255, 255]));

  for (const malformed of cases) {
    const controls = [];
    const client = new AscilineStreamClient({ sendControl: (control) => controls.push(control), now: () => 0 });
    client.beginGeneration({ fps: 24, cols: 1, rows: 1, epoch: 14, cellBytes: 4, codec: 1 });
    client.enqueue(malformed);
    await client.drain();
    assert.equal(controls.length, 1);
    assert.equal(controls[0].payload.reason, "decode_error");
  }

  const controls = [];
  const deltaClient = new AscilineStreamClient({ sendControl: (control) => controls.push(control), now: () => 0 });
  deltaClient.beginGeneration({ fps: 24, cols: 1, rows: 1, epoch: 15, cellBytes: 4, codec: 1 });
  deltaClient.enqueue(envelope(0, 0, [32, 255, 255, 255]));
  await deltaClient.drain();
  deltaClient.presentationQueue.clear();
  const body = new Uint8Array(8);
  new DataView(body.buffer).setUint32(0, 99, true);
  body.set([35, 1, 2, 3], 4);
  deltaClient.enqueue(envelope(1, 2, await deflate(body)));
  await deltaClient.drain();
  assert.equal(controls.length, 1);
  assert.equal(controls[0].payload.reason, "decode_error");
});

test("sequential drain preserves order under adversarial decode completion delays", async () => {
  const order = [];
  const client = new AscilineStreamClient({
    decoderFactory: () => ({
      reset() {},
      async decode(message) {
        const { sequence } = inspectEnvelope(message);
        await new Promise((resolve) => setTimeout(resolve, sequence === 0 ? 8 : 0));
        order.push(sequence);
        return { frameIndex: sequence, frame: new Uint8Array([32, 255, 255, 255]) };
      },
    }),
    sendControl() {},
    now: () => 0,
  });
  client.beginGeneration({ fps: 24, cols: 1, rows: 1, epoch: 16, cellBytes: 4, codec: 1 });
  client.enqueue(envelope(0, 0, [32, 255, 255, 255]));
  client.enqueue(envelope(1, 0, [32, 255, 255, 255]));
  await client.drain();
  assert.deepEqual(order, [0, 1]);
  assert.deepEqual(client.presentationQueue.items.map((frame) => frame.sequence), [0, 1]);
});

test("served web source has no image element or PNG runtime reference", async () => {
  const html = await readFile(new URL("../index.html", import.meta.url), "utf8");
  const scripts = await Promise.all([
    "../wizard.js",
    "../asciline_client.js",
    "../canvas_renderer.js",
  ].map((path) => readFile(new URL(path, import.meta.url), "utf8")));
  assert.doesNotMatch(html, /<img\b/i);
  assert.doesNotMatch([html, ...scripts].join("\n"), /\.png\b|reference-avatar/i);
});

test("connection open changes diagnostics but never starts the semantic tour", async () => {
  const source = await readFile(new URL("../wizard.js", import.meta.url), "utf8");
  const openHandler = source.match(/socket\.onopen\s*=\s*\(\)\s*=>\s*\{([\s\S]*?)\n\s*\};/);
  assert.ok(openHandler, "wizard client has an explicit open handler");
  assert.doesNotMatch(openHandler[1], /startMotionTour|post\(/);
});
