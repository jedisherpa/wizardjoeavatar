# Finn Calder Runtime Verification

Verification date: 2026-07-15

Branch: `codex/persona-finn-calder`

This verification covers the production changes on
`codex/persona-finn-calder`; publication occurs only after every gate below
passes on the final diff.

## Exact extraction and identity gate

- Accepted worksheet cells: exactly 124.
- Runtime graph split: 32 audit-only identity/feature graphs plus 92 full-body
  pose graphs.
- All 124 graph hashes are unique; graph node counts range from 1,246 to
  3,487.
- Every node is an integer `x`, `y`, and three-channel RGB value. Aggregate
  bounds are left 4, top 4, right 67, bottom 91 on the canonical 72-by-96
  canvas; RGB channels stay in the validated 0-through-255 range.
- The extraction audit records removal of worksheet background, grid, floor,
  and contact shadow for every item. `runtime_image_assets` is empty. Runtime
  packages contain only transparent colored JSON nodes; approved PNGs remain
  provenance inputs and evidence, never runtime render dependencies.
- Source SHA-256:
  `64a602fe7dc96684738a4e7d7728465eefde2d6071b11d555cf05b1e05b12c37`.
- Canonical SHA-256:
  `efac69875fe2b0c38dafe20d3669af2ed97da98b320dc703f41a1c2f9ea9f385`.
- Package load recomputes graph hashes, node counts, bounds, character-package,
  runtime-profile and generated-file hashes, generation-profile and source
  hashes, and all nine accepted worksheet hashes. The exhaustive tampering
  matrix rejects changes to every one of those inputs.

## Visual inspection

- Isolated contact sheet:
  `evidence/finn-calder/finn-calder-124-isolated-silhouettes.png`.
- Projected JSON-node contact sheet:
  `evidence/finn-calder/finn-calder-124-pixel-graph-renders.png`.
- Both sheets have SHA-256
  `ebc201cdcc8294848986ee0ee7d08fe7b227886355ac7288222cb6e0640aa697`,
  proving zero isolated-to-projected node drift.
- Human inspection confirmed complete green stepped heads, huge black eyes,
  orange tailored suits, four-pronged hands, chunky black shoes, and the
  silver/black right-hand microphone. No worksheet background, grid, floor,
  contact shadow, clipped silhouette, added prop, or identity substitution is
  visible.

## Persona behavior and runtime gate

- The signature sheet exposes only Finn's documented sequence: welcome
  anticipation, inclusive opening, microphone welcome, welcome recovery,
  announcement breath, energetic announcement, participation cue, ritual
  hold, scan/listen, accessibility check, transition direction, ready
  confirmation, celebration anticipation, celebration, appreciation, and
  community sign-off.
- Named semantic actions `welcome_crowd`, `announce_event`,
  `accessibility_check`, `lead_ritual`, `celebrate_student_contribution`,
  `supervise_transition`, and `community_sign_off` are accepted by the live
  controller and resolve to Finn graphs. No other persona's signature pose IDs
  remain in the package.
- Registry, static package assets, character-scoped REST, and character-scoped
  WebSocket are wired through `finn-calder-v1`.
- Forced `PIL.Image.open` failure still renders a complete live frame, proving
  the production path does not decode PNG or SVG art.

## Automated verification

- Deterministic generator: passed (`Finn Calder generated assets are
  deterministic`).
- Focused direct-cell and Finn suite: 22 passed, 0 failed, 0 skipped in
  25.128 seconds.
- Full Python suite: 183 passed, 0 failed, 0 skipped in 119.669 seconds.
- Python production-scope validation: 50 files scanned, 0 violations.
- Strict animation-quality validation: 32/32 scenarios passed, 0 issues.
- `python3 -m py_compile` passed for all changed Python modules and tests.
- `git diff --check` passed.

## Live REST/WebSocket smoke

The production app served on `127.0.0.1:8899` during verification.

- HTTP 200: character registry, Finn state, Finn poses, and Finn static pixel
  graph library.
- Static graph response: `graph_count=32`,
  `encoding=transparent_colored_pixel_nodes`.
- Live named action: `community_sign_off` resolved to pose
  `community_sign_off` for character `finn-calder-v1`.
- WebSocket bootstrap: `INIT:24.0:5:240:135:0:0:0.000`.
- First WebSocket payload: binary frame, 9,252 bytes.
