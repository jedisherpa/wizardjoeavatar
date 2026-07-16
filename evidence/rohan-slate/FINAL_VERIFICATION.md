# Rohan Slate Runtime Verification

Verification date: 2026-07-16

Branch: `codex/persona-rohan-slate`

## Extraction and identity gate

- Exact graph count: 124: 16 identity/reference graphs and 108 pose/feature
  graphs (8 turnaround, 8 neutral, 24 expression, 16 viseme/blink, 16
  hand/prop, 16 motion, 16 signature, and 4 interaction).
- Original and canonical references remain byte-preserved and hash-locked.
- All nine accepted worksheet files and their exact grid mappings are recorded
  in the manifest; rejected viseme candidates are excluded.
- Every graph is nonempty, unique, inside the 72-by-96 safety canvas, uses
  three-channel integer RGB nodes, and is hash/bounds/count audited before
  animation mapping.
- Cyan studio pixels and floor/contact shadows are absent from every graph.
  Teal eyes, tool-belt geometry, diagnostic meter, and approved wrench remain.
- A visual re-audit exposed nominal-grid clipping in expression cells 13–24.
  Recorded per-cell top expansion was added and all 12 silhouettes were
  regenerated; the final 124-up sheets show complete heads and bodies.
- Meter and wrench anchors occur only on graphs declared by the profile.
- Runtime package validation rejects audit, graph, bounds, count, character
  package, runtime profile, generated asset, source, generation profile,
  canonical reference, and every accepted worksheet tampering attempt.

## Retained visual evidence

- `124-isolated-transparent-graphs.png` — all 124 isolated transparent graphs.
- `124-projected-canvas-graphs.png` — the same 124 colored-node graphs painted
  onto a dark visualizer-style canvas.
- `CONTACT_SHEET_HASHES.json` — exact order and SHA-256 for both sheets.

The contact sheets are evidence only. Runtime assets remain JSON colored nodes;
the visualizer never loads these evidence PNG files.

## Runtime gate

- Rohan is registered as `rohan-slate-v1` and exposed through character-scoped
  static, REST, and WebSocket routes.
- Facilities diagnostics, meter interactions, safety stop, reset/verification,
  watch/wait, walkthrough, wrench presentation, qualified-help signal,
  locomotion, expressions, visemes, and blink channels are reachable.
- Speech and blink composition preserve the active body graph.
- Runtime rendering succeeds with `PIL.Image.open` forced to fail, proving the
  live path does not decode worksheet or evidence images.

## Automated verification

- Deterministic generator `--check`: passed.
- Focused direct-cell and Rohan suite: 20/20 passed in 23.601 seconds.
- Full repository suite: 181/181 passed in 438.272 seconds.
- `git diff --check`: passed.
- Live character list, state, poses, metadata, and pixel-graph routes returned
  HTTP 200; the pixel-graph response was 5,434,114 bytes.
- Character-scoped WebSocket returned
  `INIT:24.0:5:240:135:0:0:0.000`, a 10,073-byte idle binary frame, and a
  12,106-byte action frame; live state confirmed `wrench_present` reached pose
  `wrench_presentation` for `rohan-slate-v1`.
- Forced `PIL.Image.open` failure still produced runtime frames.
- Closure smoke on `127.0.0.1:18767` returned HTTP 200 for the Rohan registry
  and state routes, then returned `INIT:24.0:5:160:100:0:0:0.000` and a
  9,230-byte binary frame over the character-scoped WebSocket.

Final evidence hashes:

- Isolated contact sheet: `72be1d0abb075afdc90a5e6c67bba4d1915eabf106b4f1f6d446467877013ca7`.
- Projected contact sheet: `a2ea50554779ce90e9af5f5a515a1acc217f487cb3d3948146835f6966c317ed`.
- Pose library: `89880a31bf19dc237e102290ff3f7cef62580b709cae3f9d7d0022de399a63c5`.
- Pixel graph library: `78f1592fb443f6a977ad01e118ed6f9f08e2753b63752d5762b022b741579eab`.
- Extraction audit: `8052709541b90154b48981f4d03da03854b62d7c2a93db1703975d6aac524f69`.
