import test from "node:test";
import assert from "node:assert/strict";

import {
  CellStageRenderer,
  CompleteFrameQueue,
  computeFixedViewport,
} from "../canvas_renderer.js";

function fakeCanvas(width = 1600, height = 900) {
  const calls = [];
  const context = {
    calls,
    imageSmoothingEnabled: true,
    createImageData(w, h) { return { width: w, height: h, data: new Uint8ClampedArray(w * h * 4) }; },
    putImageData(image, x, y) { calls.push(["putImageData", image, x, y]); },
    clearRect(...args) { calls.push(["clearRect", ...args]); },
    fillRect(...args) { calls.push(["fillRect", ...args]); },
    drawImage(...args) { calls.push(["drawImage", ...args]); },
  };
  return { width, height, calls, getContext() { return context; } };
}

test("complete presentation queue retains only two newest ordered frames", () => {
  const queue = new CompleteFrameQueue(2);
  queue.push({ sequence: 3, presentationTime: 30 });
  queue.push({ sequence: 1, presentationTime: 10 });
  queue.push({ sequence: 2, presentationTime: 20 });
  assert.deepEqual(queue.items.map((frame) => frame.sequence), [2, 3]);
});

test("responsive resize redraws the last complete frame without waiting for the stream", () => {
  const visible = fakeCanvas();
  const logical = fakeCanvas(2, 1);
  const renderer = new CellStageRenderer(visible, 2, 1, { createCanvas: () => logical });
  renderer.enqueue({
    sequence: 1,
    presentationTime: 0,
    frame: new Uint8Array([35, 1, 2, 3, 64, 4, 5, 6]),
  });
  renderer.present(0);
  visible.calls.length = 0;

  renderer.resize(800, 450);

  assert.equal(visible.calls.filter(([name]) => name === "fillRect").length, 1);
  assert.equal(visible.calls.filter(([name]) => name === "drawImage").length, 1);
});

test("fixed viewport depends on stage dimensions, never frame content", () => {
  const a = computeFixedViewport(1000, 1000, 480, 270);
  const b = computeFixedViewport(1000, 1000, 480, 270);
  assert.deepEqual(a, b);
  assert.deepEqual(a, { x: 0, y: 219, width: 1000, height: 562 });
});

test("enqueue performs zero visible writes and rAF commits one complete frame", () => {
  const visible = fakeCanvas();
  const logical = fakeCanvas(2, 1);
  const renderer = new CellStageRenderer(visible, 2, 1, { createCanvas: () => logical });
  const frame = new Uint8Array([35, 1, 2, 3, 64, 4, 5, 6]);

  renderer.enqueue({ sequence: 1, presentationTime: 0, frame });
  assert.equal(visible.calls.length, 0, "decode/enqueue must not touch visible Canvas");
  assert.equal(logical.calls.length, 0, "frame build is presentation-owned");

  assert.equal(renderer.present(0), true);
  assert.equal(logical.calls.filter(([name]) => name === "putImageData").length, 1);
  assert.equal(visible.calls.filter(([name]) => name === "drawImage").length, 1);
  const image = logical.calls.find(([name]) => name === "putImageData")[1];
  assert.deepEqual([...image.data], [1, 2, 3, 255, 4, 5, 6, 255]);
});

test("context restore clears stale frames and rebuilds the fixed logical stage", () => {
  const visible = fakeCanvas();
  const logical = fakeCanvas(2, 1);
  const renderer = new CellStageRenderer(visible, 2, 1, { createCanvas: () => logical });
  renderer.enqueue({ sequence: 8, presentationTime: 0, frame: new Uint8Array(8) });
  renderer.lastPresentedSequence = 7;
  renderer.restoreContext();
  assert.equal(renderer.queue.length, 0);
  assert.equal(renderer.lastPresentedSequence, -1);
  assert.equal(renderer.logicalCanvas.width, 2);
  assert.equal(renderer.logicalCanvas.height, 1);
});
