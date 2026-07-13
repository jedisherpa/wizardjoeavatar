import assert from "node:assert/strict";
import test from "node:test";

import {
  analyzeFrameSequence,
  EXIT_SKIP,
  runBrowserHarness,
} from "./browser_harness.mjs";

const HASH = "a".repeat(64);

function frame(frameIndex, overrides = {}) {
  return {
    frameIndex,
    width: 96,
    height: 96,
    occupiedCells: 420,
    componentCount: 2,
    detachedCells: 0,
    root: { x: frameIndex, y: 0 },
    screenshotSha256: HASH,
    ...overrides,
  };
}

test("healthy every-frame sequence passes", () => {
  const report = analyzeFrameSequence([frame(0), frame(1), frame(2)]);
  assert.equal(report.status, "PASS");
  assert.equal(report.frame_count, 3);
  assert.equal(report.screenshot_count, 3);
  assert.deepEqual(report.discontinuities, []);
});

test("frame gaps, blank frames, and topology jumps fail", () => {
  const report = analyzeFrameSequence([
    frame(0),
    frame(2, { occupiedCells: 0, componentCount: 8, detachedCells: 1 }),
  ]);
  const codes = new Set(report.discontinuities.map((failure) => failure.code));
  assert.equal(report.status, "FAIL");
  assert.ok(codes.has("RCHAT-BROWSER-FRAME-GAP"));
  assert.ok(codes.has("RCHAT-BROWSER-BLANK-FRAME"));
  assert.ok(codes.has("RCHAT-BROWSER-COMPONENT-JUMP"));
  assert.ok(codes.has("RCHAT-BROWSER-DETACHED-CELLS"));
});

test("missing browser tooling is an explicit skip or failure", async () => {
  const module = "file:///definitely/missing/rchat-playwright.mjs";
  const skipped = await runBrowserHarness({
    mode: "probe",
    playwrightModule: module,
    unavailablePolicy: "skip",
  });
  const failed = await runBrowserHarness({
    mode: "probe",
    playwrightModule: module,
    unavailablePolicy: "fail",
  });
  assert.equal(skipped.status, "SKIP");
  assert.equal(skipped.exitCode, EXIT_SKIP);
  assert.equal(failed.status, "FAIL");
  assert.equal(failed.exitCode, 2);
});

test("capture adapter must produce real nonempty frame metadata", async () => {
  const playwrightModule = `data:text/javascript,${encodeURIComponent(`
    export const chromium = { launch: async () => ({ close: async () => {} }) };
  `)}`;
  const emptyAdapter = `data:text/javascript,${encodeURIComponent(`
    export async function captureFrames() { return []; }
  `)}`;
  const result = await runBrowserHarness({
    mode: "capture",
    playwrightModule,
    adapterModule: emptyAdapter,
    unavailablePolicy: "fail",
  });
  assert.equal(result.status, "FAIL");
  assert.equal(result.exitCode, 1);
  assert.equal(result.report.discontinuities[0].code, "RCHAT-BROWSER-NO-FRAMES");
});
