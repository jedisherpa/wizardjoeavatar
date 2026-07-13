import fs from "node:fs/promises";
import { pathToFileURL } from "node:url";

export const BROWSER_REPORT_SCHEMA = "wizardjoe-rchat-browser-report/v1";
export const EXIT_SKIP = 77;

const SHA256 = /^[0-9a-f]{64}$/;

export function analyzeFrameSequence(frames, thresholds = {}) {
  const limits = {
    maxComponentDelta: thresholds.maxComponentDelta ?? 2,
    maxDetachedCells: thresholds.maxDetachedCells ?? 0,
    maxRootJump: thresholds.maxRootJump ?? 8,
  };
  const discontinuities = [];
  let previous = null;

  if (!Array.isArray(frames) || frames.length === 0) {
    discontinuities.push({
      code: "RCHAT-BROWSER-NO-FRAMES",
      frameIndex: null,
      message: "a browser capture cannot pass without captured frames",
    });
  }

  for (const [position, frame] of (frames ?? []).entries()) {
    const frameIndex = frame?.frameIndex;
    if (!Number.isInteger(frameIndex) || frameIndex !== position) {
      discontinuities.push({
        code: "RCHAT-BROWSER-FRAME-GAP",
        frameIndex: Number.isInteger(frameIndex) ? frameIndex : null,
        message: `expected contiguous frame index ${position}`,
      });
    }
    if (!Number.isInteger(frame?.width) || frame.width <= 0 ||
        !Number.isInteger(frame?.height) || frame.height <= 0) {
      discontinuities.push({
        code: "RCHAT-BROWSER-DIMENSIONS",
        frameIndex,
        message: "frame width and height must be positive integers",
      });
    }
    if (!Number.isInteger(frame?.occupiedCells) || frame.occupiedCells <= 0) {
      discontinuities.push({
        code: "RCHAT-BROWSER-BLANK-FRAME",
        frameIndex,
        message: "frame contains no rendered character cells",
      });
    }
    if (!SHA256.test(frame?.screenshotSha256 ?? "")) {
      discontinuities.push({
        code: "RCHAT-BROWSER-SCREENSHOT-HASH",
        frameIndex,
        message: "every frame requires a lowercase SHA-256 screenshot hash",
      });
    }
    if (!Number.isInteger(frame?.componentCount) || frame.componentCount <= 0) {
      discontinuities.push({
        code: "RCHAT-BROWSER-COMPONENTS",
        frameIndex,
        message: "componentCount must be a positive integer",
      });
    }
    if (!Number.isInteger(frame?.detachedCells) || frame.detachedCells < 0 ||
        frame.detachedCells > limits.maxDetachedCells) {
      discontinuities.push({
        code: "RCHAT-BROWSER-DETACHED-CELLS",
        frameIndex,
        message: `detachedCells exceeds ${limits.maxDetachedCells}`,
      });
    }
    if (!Number.isFinite(frame?.root?.x) || !Number.isFinite(frame?.root?.y)) {
      discontinuities.push({
        code: "RCHAT-BROWSER-ROOT",
        frameIndex,
        message: "frame requires a finite root coordinate",
      });
    }

    if (previous) {
      if (frame.width !== previous.width || frame.height !== previous.height) {
        discontinuities.push({
          code: "RCHAT-BROWSER-DIMENSION-JUMP",
          frameIndex,
          message: "capture dimensions changed between adjacent frames",
        });
      }
      if (Number.isInteger(frame.componentCount) &&
          Number.isInteger(previous.componentCount) &&
          Math.abs(frame.componentCount - previous.componentCount) > limits.maxComponentDelta) {
        discontinuities.push({
          code: "RCHAT-BROWSER-COMPONENT-JUMP",
          frameIndex,
          message: `component count changed by more than ${limits.maxComponentDelta}`,
        });
      }
      if (Number.isFinite(frame?.root?.x) && Number.isFinite(frame?.root?.y) &&
          Number.isFinite(previous?.root?.x) && Number.isFinite(previous?.root?.y)) {
        const rootJump = Math.hypot(
          frame.root.x - previous.root.x,
          frame.root.y - previous.root.y,
        );
        if (rootJump > limits.maxRootJump) {
          discontinuities.push({
            code: "RCHAT-BROWSER-ROOT-JUMP",
            frameIndex,
            message: `root moved ${rootJump.toFixed(3)} cells; limit is ${limits.maxRootJump}`,
          });
        }
      }
    }
    previous = frame;
  }

  discontinuities.sort((left, right) =>
    (left.frameIndex ?? -1) - (right.frameIndex ?? -1) ||
    left.code.localeCompare(right.code) ||
    left.message.localeCompare(right.message));
  return {
    schema: BROWSER_REPORT_SCHEMA,
    schema_version: 1,
    status: discontinuities.length === 0 ? "PASS" : "FAIL",
    frame_count: Array.isArray(frames) ? frames.length : 0,
    screenshot_count: Array.isArray(frames)
      ? frames.filter((frame) => SHA256.test(frame?.screenshotSha256 ?? "")).length
      : 0,
    thresholds: limits,
    discontinuities,
  };
}

export async function runBrowserHarness(options) {
  const policy = options.unavailablePolicy ?? "fail";
  if (!["fail", "skip"].includes(policy)) {
    throw new Error("unavailablePolicy must be fail or skip");
  }

  let playwright;
  try {
    playwright = await import(options.playwrightModule ?? "playwright");
  } catch (error) {
    return unavailable(policy, `browser tooling unavailable: ${error.message}`);
  }
  const chromium = playwright.chromium ?? playwright.default?.chromium;
  if (!chromium?.launch) {
    return unavailable(policy, "browser tooling does not export chromium.launch");
  }

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    if (options.mode === "probe") {
      await browser.close();
      return { exitCode: 0, status: "AVAILABLE", report: null };
    }
    if (!options.adapterModule) {
      await browser.close();
      return unavailable(policy, "capture adapter is not configured");
    }
    const adapter = await import(options.adapterModule);
    if (typeof adapter.captureFrames !== "function") {
      await browser.close();
      return unavailable(policy, "capture adapter must export captureFrames({ browser })");
    }
    const frames = await adapter.captureFrames({ browser });
    const report = analyzeFrameSequence(frames, options.thresholds);
    await browser.close();
    if (options.outputPath) {
      await fs.writeFile(options.outputPath, `${JSON.stringify(report, null, 2)}\n`);
    }
    return {
      exitCode: report.status === "PASS" ? 0 : 1,
      status: report.status,
      report,
    };
  } catch (error) {
    if (browser) {
      await browser.close().catch(() => {});
    }
    return { exitCode: 2, status: "FAIL", report: null, message: error.message };
  }
}

function unavailable(policy, message) {
  return {
    exitCode: policy === "skip" ? EXIT_SKIP : 2,
    status: policy === "skip" ? "SKIP" : "FAIL",
    report: null,
    message,
  };
}

function parseCli(argv) {
  const mode = argv.shift();
  if (!["probe", "capture"].includes(mode)) {
    throw new Error("usage: browser_harness.mjs probe|capture [options]");
  }
  const options = { mode, unavailablePolicy: "fail" };
  while (argv.length > 0) {
    const argument = argv.shift();
    if (argument === "--playwright-module") options.playwrightModule = argv.shift();
    else if (argument === "--adapter") options.adapterModule = argv.shift();
    else if (argument === "--output") options.outputPath = argv.shift();
    else if (argument === "--unavailable-policy") options.unavailablePolicy = argv.shift();
    else throw new Error(`unknown browser harness argument ${argument}`);
  }
  return options;
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  try {
    const result = await runBrowserHarness(parseCli(process.argv.slice(2)));
    const message = result.message ? `: ${result.message}` : "";
    const stream = result.exitCode === 0 ? process.stdout : process.stderr;
    stream.write(`${result.status} rchat browser ${process.argv[2]}${message}\n`);
    process.exitCode = result.exitCode;
  } catch (error) {
    process.stderr.write(`FAIL rchat browser harness: ${error.message}\n`);
    process.exitCode = 2;
  }
}
