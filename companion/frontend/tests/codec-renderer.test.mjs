import test from "node:test";
import assert from "node:assert/strict";

import { makeDecoder, parseInit, TAG_RAW } from "../asciline-codec.js";
import { CellStageRenderer, CompleteFrameQueue, computeFixedViewport } from "../canvas-renderer.js";
import { BoundedByteQueue } from "../frame-stream.js";

test("ASCILINE INIT metadata keeps protocol defaults and optional fields", () => {
  assert.deepEqual(parseInit("INIT:24:5:480:270:0:0:0.000"), {
    fps: 24,
    cols: 480,
    rows: 270,
    epoch: 0,
    cellBytes: 4,
    codec: 1,
  });
  assert.equal(parseInit("INIT:30:5:96:64:0:0:0:EPOCH:7:CELL_BYTES:4:CODEC:1").epoch, 7);
});

test("raw frame packets decode without altering cell bytes", async () => {
  const payload = Uint8Array.of(35, 20, 40, 60, 32, 1, 2, 3);
  const packet = new Uint8Array(payload.length + 5);
  new DataView(packet.buffer).setUint32(0, 42, false);
  packet[4] = TAG_RAW;
  packet.set(payload, 5);

  const decoded = await makeDecoder(4).decode(packet);
  assert.equal(decoded.sequence, 42);
  assert.deepEqual(decoded.frame, payload);
});

test("fixed viewport letterboxes without distorting the frame", () => {
  assert.deepEqual(computeFixedViewport(1600, 900, 480, 270), {
    x: 0,
    y: 0,
    width: 1600,
    height: 900,
  });
  assert.deepEqual(computeFixedViewport(1000, 900, 480, 270), {
    x: 0,
    y: 169,
    width: 1000,
    height: 562,
  });
});

test("complete frame queue bounds backlog and presents only the newest due frame", () => {
  const queue = new CompleteFrameQueue(2);
  queue.push({ sequence: 1, presentationTime: 10 });
  queue.push({ sequence: 3, presentationTime: 30 });
  queue.push({ sequence: 2, presentationTime: 20 });

  assert.deepEqual(queue.items.map(({ sequence }) => sequence), [2, 3]);
  assert.equal(queue.takeNewestDue(25, -1).sequence, 2);
  assert.equal(queue.takeNewestDue(29, 2), null);
  assert.equal(queue.takeNewestDue(30, 2).sequence, 3);
});

test("encoded frame queue clears dependency history when bounds are exceeded", () => {
  const queue = new BoundedByteQueue(2, 16, 250, () => 100);
  assert.equal(queue.push(Uint8Array.of(1, 2, 3, 4)), true);
  assert.equal(queue.push(new Uint8Array(20)), false);
  assert.equal(queue.length, 0);
  assert.equal(queue.bytes, 0);
});

test("enqueue does not write the visible canvas before presentation", () => {
  function fakeCanvas(width = 2, height = 1) {
    const calls = [];
    const context = {
      calls,
      createImageData(w, h) {
        return { data: new Uint8ClampedArray(w * h * 4) };
      },
      putImageData(...args) { calls.push(["putImageData", ...args]); },
      fillRect(...args) { calls.push(["fillRect", ...args]); },
      drawImage(...args) { calls.push(["drawImage", ...args]); },
    };
    return {
      width,
      height,
      calls,
      getBoundingClientRect() { return { width, height }; },
      getContext() { return context; },
    };
  }

  const visible = fakeCanvas(200, 100);
  const logical = fakeCanvas();
  const renderer = new CellStageRenderer(visible, 2, 1, {
    createCanvas: () => logical,
  });
  visible.calls.length = 0;
  logical.calls.length = 0;
  const frame = Uint8Array.of(35, 1, 2, 3, 64, 4, 5, 6);

  renderer.enqueue({ sequence: 1, presentationTime: 0, frame });
  assert.equal(visible.calls.length, 0);
  assert.equal(logical.calls.length, 0);

  assert.equal(renderer.present(0).sequence, 1);
  assert.equal(logical.calls.filter(([name]) => name === "putImageData").length, 1);
  assert.equal(visible.calls.filter(([name]) => name === "drawImage").length, 1);
});
