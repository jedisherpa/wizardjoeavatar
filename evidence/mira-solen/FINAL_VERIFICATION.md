# Mira Solen Runtime Verification

Verification date: 2026-07-16
Branch: `codex/persona-mira-solen`

The canonical worksheet checkpoint is commit `598d2e0`, the transparent-pixel
runtime foundation is commit `1498ef1`, and the first published production
avatar is commit `c804032`. This verification covers the provenance-hardening
release layered on that published avatar.

## Extraction and identity gate

- Exact graph count: 124.
- Approved identity v3 graphs: 16.
- Pose/feature graphs from sheets 02–09: 108.
- Category census: 16 identity, 8 turnaround, 8 neutral, 24 expression, 16 viseme/blink, 16 hand/prop, 16 motion, 16 signature, and 4 interaction.
- Runtime format: transparent colored pixel nodes in JSON; runtime image asset list is empty.
- Mira-specific isolation retains the white layered dress and attached saturated blue outer flame while removing the blue studio, grid, floor, cast shadow, and contact shadow.
- Source reference SHA-256: `ee88963dc59ab9efb8f4500734aa8a7b66f67b378e075088207df49cf6e08f6a`.
- Canonical voxel SHA-256: `7802522fbc0d26370fdb826ab409ca3b8d063eac75c62af1bdf888848bb6561e`.
- Pose library SHA-256: `94138553cb493b0437c42c77041ff9fdb66ff32e9a59274a68029e8006b77b32`.
- Identity graph library SHA-256: `ac8536cd7a719a809281169431c3d9f2a803e1b89a80aae0f8a99dca1f831692`.
- Extraction audit SHA-256: `4b6716a67cf428904249a27632288dce75e594cef1a39e0b05f5986f92528909`.
- Character manifest SHA-256: `558fd4542bfb497f0365319f202848c40b3121e7cceb05c1589869fafde2bf2e`.
- Character package SHA-256: `26b1f5dc9609c88377bc8891f2cfcafd608996ec27a9da91f79b40a11dbb50b0`.
- Runtime profile SHA-256: `d1c0e25c440c6605f507ad65d431ebc6c1eb5fc8b50ebca9ae143705606a5676`.
- Package load now recomputes the original, canonical, generation-profile,
  package, runtime-profile, pose, animation-graph, animation-matrix,
  extraction-audit, pixel-graph, and all nine accepted worksheet hashes.
- Exhaustive tamper tests alter every provenance class and every worksheet
  category independently. Repository escapes, non-124 inventories, category
  omissions, duplicate coordinates, unsafe bounds, and invalid RGB nodes are
  rejected before a runtime object is returned.

## Human-reviewed contact evidence

- `124-isolated-graphs.png`: 2432x1664, 124 labeled cells, SHA-256 `07beb9b0cb1a06a9521c23c2a53297e3c31fd144c37374ffb0322cbc64d6dd94`.
- `124-projected-graphs.png`: 2432x1664, 124 labeled cells, SHA-256 `1d46fd5615a4c849fcd2ad09f2b9736903326bc8320e8338f82569fbb3998c3e`.
- Both sheets were inspected at full resolution. All cells are isolated, uncropped, background-free, floor-free, and shadow-free. Mira retains her face, bob, dress, emblem, pendant, shoes, tray, orange core, and blue flame. Projected cells preserve the isolated silhouettes without added runtime art.

## Runtime and transport gate

- Registry entry, static package/assets, character-scoped REST state/action routes, and character-scoped WebSocket route are live.
- A live local Uvicorn run on `127.0.0.1:8897` returned HTTP 200 for the
  registry, state, pose inventory, extraction audit, and Mira
  `blue_flame_inspiration` action.
- The live state reached `pose_id=blue_flame_inspiration`.
- The WebSocket emitted `INIT:24.0:5:240:135:0:0:0.000` followed by binary
  ASCILINE frames (8,779 and 11,275 bytes in the observed action stream).
- The focused test forces `PIL.Image.open` to fail while Mira still renders, proving the live runtime path uses JSON nodes only.
- Mira-specific semantic mappings include artwork reveal, critique invitation, dignity protection, creative reframing, student-voice amplification, and blue-flame inspiration. No copied persona vocabulary is present in Mira's generation profile, runtime profile, graph, or matrix.

## Deterministic, focused, full, live, and diff results

- Deterministic generator check: `Mira Solen generated assets are deterministic`.
- Focused suite: 12 tests passed in 34.718 seconds; 0 failed, 0 skipped.
- Full Python suite: 177 tests passed in 191.509 seconds; 0 failed, 0 skipped.
- Forced Pillow failure: 1 test passed in 1.354 seconds, proving node-only
  runtime rendering after provenance validation.
- Production-scope validation: 50 files scanned, 0 violations.
- Live smoke: registry/static/REST/WebSocket succeeded and streamed Mira binary frames.
- Runtime cell diff: neutral, curiosity, locomotion, and blue-flame signature states produced distinct frame buffers.
- Source diff hygiene: `git diff --check` passed.
- Publication gate: final diff hygiene, commit, and remote push are required;
  the resulting remote commit is recorded in the release handoff.
