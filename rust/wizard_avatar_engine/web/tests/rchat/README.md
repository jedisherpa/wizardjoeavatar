# RCHAT Browser Harness

`browser_harness.mjs` is the Q0 adapter boundary for real-browser, every-frame
capture. It does not generate synthetic success. A capture adapter must export:

```js
export async function captureFrames({ browser }) {
  return [/* one metadata record for every captured browser frame */];
}
```

Each record requires a contiguous `frameIndex`, stable positive dimensions,
nonzero occupied cells, structural component counts, detached-cell count, root
coordinate, and SHA-256 screenshot hash. Empty captures and structural
discontinuities fail. Missing Playwright or a missing adapter returns failure by
default; `--unavailable-policy skip` returns exit code 77 and prints `SKIP`.

Availability probe:

```bash
node rust/wizard_avatar_engine/web/tests/rchat/browser_harness.mjs probe \
  --playwright-module /absolute/path/to/playwright/index.mjs \
  --unavailable-policy fail
```

Later Q waves provide the live Wizard Joe adapter and use `capture` with an
output report. A probe result is `AVAILABLE`, never a browser-evidence `PASS`.
