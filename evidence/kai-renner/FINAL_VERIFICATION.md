# Kai Renner Runtime Verification

Verification date: 2026-07-15

Branch: `codex/persona-kai-renner`

## 124-graph extraction gate

- Exact audited graph count: 124.
- Identity/reference graphs from accepted identity sheet revision 2: 16.
- Runtime/feature graphs from sheets 02–09: 108.
- Exact category counts: 8 turnaround, 8 neutral, 24 expression, 16 viseme/blink, 16 hand/prop, 16 motion, 16 signature, and 4 interaction.
- Runtime representation: JSON colored pixel nodes; unoccupied cells are transparent.
- Runtime image assets: none. PNG worksheets remain preserved, hashed extraction sources only.
- Every audit item records its worksheet cell, worksheet SHA-256, isolation method, bounds, node count, runtime target, and colored-node graph SHA-256.
- Package loading recomputes all 124 graph hashes before animation mapping.
- Human-readable direct-node review: `evidence/kai-renner/kai-renner-124-pixel-graphs-contact-sheet.png` (SHA-256 `fe74afb984811136fd0ec3f26e65448e903b8506a1ca09b9cfc229def9c5038d`). This evidence-only PNG renders the JSON nodes after extraction; it is not referenced by the runtime package.
- The first distance-mask pass was rejected during contact-sheet review because it retained cyan studio islands. The accepted pass uses the warm-subject mask plus vertically bounded dark-cobalt preservation for the trousers, and a shadow-rejecting cool-object mask for the three gray-blue prop studies. It retains the costume and props while removing studio and floor-shadow pixels. All 124 accepted graphs were then reviewed together for complete silhouette, cap/limb clearance, `BAKE` retention where front-facing, and absence of cyan background islands before animation was reconnected.

## Identity and semantic gate

- The original source and canonical voxel image retain their documented SHA-256 hashes.
- The accepted revision-2 identity grid and all eight accepted revision-1 production sheets are explicitly selected by `generation-profile.json`; rejected identity revision 1 is not hashed as a production input.
- The cap, white uppercase `BAKE` construction, square glasses, beard, yellow shirt, blue trousers, near-black shoes, and controlled gray-blue prototype derive directly from the accepted reviewed worksheets.
- Pose-local anchors are occupied graph nodes. `prototype` exists only on the eleven accepted cells that contain the prototype/evidence construction or action.
- Kai-specific runtime actions include smallest pilot, build, test, build/test handoff, privacy check, safety slowdown, metrics, evidence comparison, prototype present/inspect/celebrate, thumbs-up, self-correction, kill-the-hype, settle/listen, and energetic recovery.

## Determinism

Command:

```bash
uv run python tools/generate_voxel_persona_character.py \
  assets/reference/personas/kai-renner/generation-profile.json --check
```

Result: `Kai Renner generated assets are deterministic`.

## Tests

Focused command:

```bash
uv run python -m unittest \
  tests.wizard.test_direct_cell_character \
  tests.wizard.test_kai_renner_character -v
```

Result: 21 tests passed, 0 failed, 0 skipped. This includes both generic direct-cell behavior and Kai-specific 124-graph, source-preservation, bounds/detail, occupied-anchor, body-preserving face-channel, semantic-reachability, tamper-rejection, static-route, live-cell-change, and no-image-decode tests.

Full command:

```bash
uv run python -m unittest discover -s tests -v
```

Result: 182 tests passed in 110.638 seconds, 0 failed, 0 skipped. The run includes Wizard Joe, CrystAIl, codec, controller, projection, locomotion, semantic signals, runtime determinism, transport, stream, browser contract, and Kai regression coverage.

## Live REST and WebSocket smoke

The final regenerated assets ran locally on port 8894. Verified with live requests:

- `GET /api/avatar/characters`: HTTP 200 and `kai-renner-v1` advertised with all package assets.
- `GET /api/avatar/kai-renner-v1/state`: HTTP 200 with character-scoped state.
- `GET /api/avatar/kai-renner-v1/poses`: HTTP 200 with the 108 pose-capable graphs.
- `POST /api/avatar/kai-renner-v1/action` using `privacy_check`: HTTP 200 and action accepted.
- `GET /avatar/characters/kai-renner-v1/extraction-audit`: HTTP 200 with `item_count: 124` and an empty runtime image asset list.
- `WS /ws/avatar/kai-renner-v1`: accepted, returned `INIT:24.0:5:240:135:0:0:0.000`, then a 12,040-byte binary frame.
- A WebSocket `prototype_present` action produced the next 9,850-byte binary frame.

No commit or push was performed by this implementation pass.
