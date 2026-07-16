# Mira Solen Runtime Verification

Verification date: 2026-07-15
Branch: `codex/persona-mira-solen`

The canonical worksheet checkpoint is commit `598d2e0`. The generic transparent-pixel runtime foundation was cherry-picked as local commit `1498ef1` from `0379a17`; this verification covers the production runtime and evidence layered on that foundation.

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
- Character manifest SHA-256: `ce401805a2bdbe0424444627e246becf84b8f42161701ab9ccca7e067f1531a6`.

## Human-reviewed contact evidence

- `124-isolated-graphs.png`: 2432x1664, 124 labeled cells, SHA-256 `07beb9b0cb1a06a9521c23c2a53297e3c31fd144c37374ffb0322cbc64d6dd94`.
- `124-projected-graphs.png`: 2432x1664, 124 labeled cells, SHA-256 `1d46fd5615a4c849fcd2ad09f2b9736903326bc8320e8338f82569fbb3998c3e`.
- Both sheets were inspected at full resolution. All cells are isolated, uncropped, background-free, floor-free, and shadow-free. Mira retains her face, bob, dress, emblem, pendant, shoes, tray, orange core, and blue flame. Projected cells preserve the isolated silhouettes without added runtime art.

## Runtime and transport gate

- Registry entry, static package/assets, character-scoped REST state/action routes, and character-scoped WebSocket route are live.
- A live local Uvicorn run returned HTTP 200 for the registry, package, state, and Mira `blue_flame_inspiration` action.
- The live state reached `pose_id=blue_flame_inspiration`.
- The WebSocket emitted the 29-byte INIT text followed by binary ASCILINE frames (8779 and 11275 bytes in the observed action stream).
- The focused test forces `PIL.Image.open` to fail while Mira still renders, proving the live runtime path uses JSON nodes only.
- Mira-specific semantic mappings include artwork reveal, critique invitation, dignity protection, creative reframing, student-voice amplification, and blue-flame inspiration. No copied persona vocabulary is present in Mira's generation profile, runtime profile, graph, or matrix.

## Deterministic, focused, full, live, and diff results

- Deterministic generator check: `Mira Solen generated assets are deterministic`.
- Focused suite: 13 tests passed in 13.934 seconds; 0 failed, 0 skipped.
- Full Python suite: 174 tests passed in 107.804 seconds; 0 failed, 0 skipped.
- Live smoke: registry/static/REST/WebSocket succeeded and streamed Mira binary frames.
- Runtime cell diff: neutral, curiosity, locomotion, and blue-flame signature states produced distinct frame buffers.
- Source diff hygiene: `git diff --check` passed.
- Final production work remains uncommitted by request; no push was performed.
