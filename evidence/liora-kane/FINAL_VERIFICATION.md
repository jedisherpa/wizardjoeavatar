# Liora Kane Runtime Verification

Verification date: 2026-07-15

Branch: `codex/persona-liora-kane`

## Extraction gate

- Exact audited graph count: 124.
- Identity/reference graphs: 16.
- Full-body pose/feature graphs: 108.
- Categories: 8 turnaround, 8 neutral, 24 expression, 16 viseme/blink,
  16 hand/prop, 16 motion, 16 signature, and 4 interaction.
- Runtime format: transparent colored pixel nodes in JSON.
- Runtime PNG/SVG assets: zero.
- Background extraction: distance tolerance 90 plus pale-blue studio-floor
  suppression; backdrop, floor, and contact shadows visually reviewed as absent
  across all 124 direct graphs on both dark and white inspection backgrounds.
- Subject continuity: gray hoodie and teal/cream plaid remain present above
  minimum per-graph color-cell thresholds across all 124 graphs.
- Smallest graph: more than 1,400 nodes; every graph remains inside the
  72-by-96 canonical safe area.
- Review contact sheet: `124-graph-contact-sheet.png`, SHA-256
  `41628557404a82d52df3e113b8a87523ed11c8a8d6755b1af64e692cef03ddfe`.

The contact sheet is review evidence only. Live rendering consumes the JSON
node graphs and succeeds with `PIL.Image.open` forced to fail.

## Identity and semantic gate

- The source and canonical images retain their recorded SHA-256 hashes.
- Runtime package loading independently re-hashes the generation profile,
  original reference, canonical voxel reference, all nine accepted worksheet
  classes, runtime profile, and every generated graph/audit/animation asset.
  Repository-safe path resolution rejects missing or escaping provenance paths.
- No Orion inquiry, question-notebook, coat, beard, glasses, or tie content
  remains in Liora's profile, graph, manifest, runtime profile, or pose IDs.
- All 16 signature cells use the worksheet-authored support/privacy/escalation
  names and notebook anchors.
- Liora is registered through the shared package architecture.
- Static assets, character-scoped commands, direct poses, and WebSocket frames
  were exercised through the running server on `127.0.0.1:8876`.
- Live WebSocket smoke: `INIT:12.0:5:160:100:0:0:0.000` received, an 8,297-byte
  frame received, notebook-write command accepted, and a distinct 8,768-byte
  frame received. HTTP state reported `support_notebook_write`.

## Determinism and tests

- Generator `--check`: passed.
- Provenance-focused Liora and direct-cell suite: 19 passed, 0 failed,
  including independent tamper attempts against 18 immutable/generated assets.
- Live HTTP character registry: HTTP 200 and `liora-kane-v1` present.
- Live WebSocket: connected and streamed before and after a Liora action.
- Full repository suite: 180 passed, 0 failed, 0 skipped in 188.695 seconds.
- Contact-sheet rerender: byte-identical to the reviewed evidence image.

## Human visual review

The 124-up direct-node sheet was inspected at original resolution. The gray
hoodie, cream drawstrings and shoes, teal plaid legs, long brown hair, skin,
and navy notebook remain readable. The formerly retained blue sheet/floor halos
are absent, silhouettes are isolated, and no cell is cropped by the canonical
bounds.
