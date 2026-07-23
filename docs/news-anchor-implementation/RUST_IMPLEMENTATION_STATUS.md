# Rust Newsroom Implementation Status

Updated: 2026-07-22

Branch: `codex/rust-pixelgraph-primary`

Visual authority: the 260-pose production-alpha replacement corpus compiled by
`wizard-avatar-production-alpha-v1`. The final Git SHA is recorded by the deployment
receipt and the server state endpoint.

## Implemented

| Packet area | Rust implementation | Evidence |
|---|---|---|
| Shared v1 schemas | Seven packet schemas are copied byte-for-byte under `rust/wizard_avatar_engine/assets/newsroom/schemas/`. Strict Serde models deny unknown fields. | `tests/newsroom_contract.rs` |
| 88-pose catalog | The exact catalog is embedded and validated for count, order, sections, semantic commands, required fields, IDs, and transition references. Every pose has an explicit authored Rust runtime binding and is reachable through deterministic seeded selection inside its governed semantic family. | `every_catalog_pose_is_reachable_through_governed_semantic_variants` |
| 30-transition matrix | The exact matrix is embedded and validated. Every transition resolves to one existing `MotionGraphV1` recipe. | `embedded_catalogs_are_exact_closed_and_command_complete` |
| Semantic ingress | `NewsPerformanceCueV1` accepts only the 19 closed semantic commands. Raw pose, clip, path, effect-program, unknown, oversized, Unicode-confusable, and malformed fields fail closed. | `cue_ingress_rejects_raw_controls_unknown_fields_and_confusables` |
| Motion policy | Story-sensitivity amplitude caps, serious/correction magic suppression, and the dedicated reduced-motion graph recipe are deterministic. | `sensitivity_and_reduced_motion_policy_clamp_performance` |
| Controller lifecycle | Typed application enforces generation/sequence monotonicity, exact replay idempotency, conflict rejection, interruption attribution, timed restoration, completion, and bounded receipt history. | Controller tests in `tests/newsroom_contract.rs` |
| Runtime and hub | Semantic cues use the existing controller, runtime clock, hub, renderer, adaptive codec, and websocket output path. Catalogs are validated once outside the runtime write lock; actor samples release the lock and run on Tokio's blocking pool. | Full Rust suite, mixed-cue soak, and retained frame evidence |
| Versioned adapter | `POST /api/avatar/wizard/v2/newsroom/cue` applies typed cues. `GET /api/avatar/wizard/v2/newsroom/receipt` returns the latest receipt. `GET /api/avatar/wizard/v2/newsroom/actor-sample` returns the on-demand actor layer. | Automated HTTP adapter test |
| Actor samples | Rust projects the exact promoted 1254-square PixelGraph into RGB and binary coverage buffers with bounds, authored root/contact metadata, state/package/content hashes, and a recomputed actor-layer hash. No procedural pose sampler or PNG is used as runtime character data. | `actor_samples_are_cell_aligned_hashed_and_tamper_evident` |
| Speech timeline | Ordered, non-overlapping mouth/caption intervals, generation identity, closed defaults between cues, and strict fields are implemented. | `speech_timeline_is_ordered_non_overlapping_and_closes_between_cues` |
| Frame QA | The existing evidence binary now drives all 88 variants through `NewsPerformanceCueV1` and the real controller, then checks entry, hold, timed restore, adaptive decode, PNG, contact, topology, and two-pass hashes. | `evidence/pose-library-expansion/rust-v4/animation-verification/manifest.json` |
| Categorized scene composition | Rust composes transparent horizontal cell runs in a closed background/set-piece/prop/character/effect/foreground/broadcast-overlay order. The approved live character painter now routes through categorized scene elements with byte-for-byte parity coverage. | `src/scene.rs`, renderer parity test |
| Newsroom v2 native pixel graphs | Six approved `1672x941` source plates are split into 27 transparent palette-and-row-run graphs. All 4,233,630 occupied RGBA pixels are owned exactly once; source recomposition is exact and every graph-over-PNG comparison is visually approved. | `docs/newsroom-visual-development-v2/layer-admission-ledger.json` |
| Evidence-bound runtime promotion | A separate Rust gate rehashes every approval and comparison artifact, then copies only byte-identical graph files into the engine. Runtime projection uses center-sampled block coordinates; no PNG, SVG, crop, palette reduction, or procedural set reconstruction is loaded. | `docs/newsroom-visual-development-v2/runtime-promotion.json`, `src/newsroom_scene.rs` |
| Pose-graph audit gate | The pinned production set supplies 250 independent alpha poses and the flight pack supplies 10 forward-camera cycle frames. All 260 are exact 1254-square RGBA PixelGraphs, independently reviewed one at a time, and runtime-addressable by both source and unique semantic identity. | `docs/pose-admission-v2/`, `assets/pose_graphs/v6/runtime-manifest.json`, `src/pose_graph_runtime.rs` |

## Rust Work-Item Ledger

| Work item | Status | Accountability note |
|---|---|---|
| WJ-020 strict schemas | COMPLETE | Seven immutable packet schemas, strict typed ingress, closed identifiers, and malformed/raw-control rejection are implemented. |
| WJ-021 newsroom geometry | COMPLETE_WITH_APPROVED_COMPOSITION | All 88 variants resolve to authored Rust geometry. The project owner approved the current imagery on 2026-07-14; 25 entries remain honestly labeled `approved_composition` rather than falsely described as unique new meshes. |
| WJ-022 desk/contact/occlusion metadata | COMPLETE | Production graphs emit authored root/contact mode and exact actor coverage. Exact promoted foreground graphs paint after the actor graph, so desk and lectern occlusion remain deterministic and scene-specific. Region-specific staff/wing rectangles are intentionally absent until they are authored into the replacement manifest. |
| WJ-023 MotionGraph mappings | COMPLETE | Every selected pose resolves to a canonical matrix transition and an existing `MotionGraphV1` recipe; reduced motion uses its dedicated recipe. |
| WJ-024 lifecycle | COMPLETE | Monotonic generation/sequence handling, replay idempotency, interruption, restoration, completion, bounded history, and stale rejection are active in the real controller/runtime/hub path. |
| WJ-025 actor samples | COMPLETE | RGB plus required binary coverage, optional depth/shadow fields, contacts/bounds, state/package/layer hashes, base64 transport, tamper checks, and nonblocking generation are implemented. |

## Packet Discrepancy

The immutable 88-pose catalog references 23 semantic transition names absent from the immutable 30-transition matrix. Several mapped matrix transitions also omit the referencing pose from their legal target set. Rust preserves both source files exactly, resolves names through a closed compatibility table, prefers a declared entry when it is legal, and otherwise selects the first canonical matrix transition that explicitly permits the target pose. Receipts always record the actual canonical transition and existing `MotionGraphV1` recipe.

## Fidelity And Approval

The promoted v6 library replaces the earlier pose corpus as the sole runtime visual
authority. Its two pinned ZIPs contain 250 production-alpha poses and 10
forward-camera flight-cycle frames. Each source is decoded at its authored
`1254 x 1254` RGBA size, converted sequentially into colored PixelGraph runs, read
back, projected, and required to match every source RGBA byte. No scaling, padding,
matte removal, resampling, palette reduction, procedural reconstruction, PNG runtime
load, or SVG runtime load is permitted.

The 88-entry newsroom semantic catalog remains the governed command surface, but its
actor imagery resolves only through these admitted v6 graphs. Raw pose and restore
commands reject retired v5-only identities. Rust owns graph projection, motion clips,
locomotion transforms, category composition, and scene foreground occlusion.

## Verification Result

The v2 newsroom visual pass additionally verifies six approved sources, 27 promoted
runtime graphs, 4,233,630 exact occupied pixels, zero overlap or unassigned pixels,
and six runtime snapshots generated through the same `render_state_to_cells` path used
by the server. Camera-composition boards remain excluded; the visible set selector does
not present them as runtime artwork.

The production-alpha runtime evidence pass proves:

- 260 promoted graph identities with exact source and graph hashes;
- 408,854,160 source-canvas pixels independently reprojected with zero mismatches;
- all 1,300 expected source, projection, transparent-overlay, composite, and comparison evidence PNGs present and hash-bound;
- eight literal visual-review batches covering all 260 poses with 260 approvals and zero rejections;
- 19 authored clips plus four directional locomotion scenarios;
- 1,089 deterministic animation frames and 23 sequence contact sheets;
- all 10 forward-camera flight frames presented in authored order;
- complete graph presence, all gait phases, visible stride, monotonic travel, and every locomotion target reached;
- zero breakup, continuity, graph, topology, or incomplete-frame failures.

Compact reports are retained under `evidence/runtime-pixelgraph-qa-v6/` and
`docs/pose-admission-v2/`. Full frame and one-at-a-time transparent-overlay evidence
is published as release evidence rather than committed as ordinary Git image blobs.

### Historical v5 Baseline

The following soak and replay receipts remain useful regression history for the
earlier v5 runtime. They are not the admission receipt for the replacement corpus.

The implementation source gate passed the focused newsroom contracts, clippy with warnings denied, Rust doc tests, all 29 browser presentation tests, and `cargo test --all-targets`. The current all-target run includes the exhaustive authored-neighbor breakup gate and imported-pose loop gate. The canonical 15-second release soak also passed with warmed actor-sample p50/p95/p99 timings of 5.77/9.39/9.39 milliseconds against a 250-millisecond p99 ceiling and a 64 MiB peak-RSS-growth ceiling.

The exact-SHA frame run and named 60-minute newsroom soak both passed against implementation commit `fc63a938f095f08421a57b2a7019ca22acb9ce56`. The retained soak result is `evidence/animation-quality/final/soak/newsroom.json` and records:

- 3,600.09 seconds across 0/1/2/4/8-viewer scenarios.
- 7,200 semantic cues and 7,200 verified receipts.
- all 88 semantic poses, 379 correction receipts, and 1,028 reduced-motion receipts.
- five stale-cue rejections, six validated actor samples, and 15 reconnects.
- zero simulation/render deadline misses, sequence gaps, lag events, frame-hash mismatches, or generation leaks.
- actor-sample p50/p95/p99 of 5.51/8.43/8.43 milliseconds against a 250-millisecond p99 ceiling.
- maximum per-scenario peak-RSS growth of 2,880 KiB against a 65,536-KiB ceiling.

The exact-SHA optimized visual evidence run produced:

- 24,724 frames in each of two complete passes.
- 621 authored transitions.
- 88 newsroom semantic pose scenarios.
- 16 Rust clips.
- 89 static runtime geometries and one alias.
- zero frame-quality failures.
- exact source/adaptive-decode/presentation parity.
- identical replay SHA-256: `d4710b9125817a9efcd3bf2de43409e4b6f1cd724ad14dd7ce785cad7590ec5e`.

Both retained manifests identify the clean source commit. Generated frame PNGs and the raw frame stream remain reproducible build evidence and are ignored because they exceed practical Git storage. The compact manifest and timeline contact sheet are retained in Git.

## Reproduction

Run from `rust/wizard_avatar_engine`:

```bash
cargo fmt --all -- --check
cargo clippy --locked --all-targets --all-features -- -D warnings
cargo test --locked --all-targets
cargo test --locked --doc
cargo run --locked --bin pixelgraph_runtime_evidence -- ../../evidence/runtime-pixelgraph-qa-v6/deterministic-animation-frames
cargo run --locked --manifest-path ../wizard_avatar_pose_tool/Cargo.toml --bin wizard-avatar-production-alpha-finalize -- --project-root ../..
cargo run --locked --manifest-path ../wizard_avatar_pose_tool/Cargo.toml --bin wizard-avatar-newsroom-promote -- ../..
cargo run --locked --bin newsroom_v2_snapshots -- ../..
WIZARD_EVIDENCE_GIT_SHA="$(git rev-parse HEAD)" cargo run --release --locked --bin wizard-avatar-pose-evidence
WIZARD_EVIDENCE_GIT_SHA="$(git rev-parse HEAD)" WIZARD_SOAK_MODE=newsroom cargo run --release --locked --bin wizard-avatar-soak
WIZARD_AVATAR_GIT_SHA="$(git rev-parse HEAD)" cargo build --release --locked --bin wizard-avatar-server
node --test web/tests/*.test.mjs
```

The newsroom soak takes at least 60 minutes by contract. Its pass condition includes all 88 distinct semantic poses, all 19 commands, correction and reduced-motion receipts, stale-cue rejection, actor-sample validation, reconnects, zero generation leaks, bounded queues, stable frame hashes, and runtime/render clock limits.

## Semantic Endpoint

Example accepted cue:

```json
{
  "schema_version": "newsroom_wizard_v1",
  "cue_id": "cue-opening-001",
  "sequence": 1,
  "program": "general_news",
  "command": "welcome",
  "intensity": 0.4,
  "sensitivity": "normal",
  "start_ms": 0,
  "duration_ms": 1200,
  "generation": 1,
  "reduced_motion": false,
  "seed": 42
}
```

The response is a `NewsroomCueReceiptV1` containing the semantic pose, internal authored pose, fidelity, canonical packet transition, real `MotionGraphV1` recipe, applied policy clamps, lifecycle, generation, and accepted simulation tick. When `seed` is present, it deterministically selects a variant only within the requested semantic family; serious, critical, and correction cues cannot select light-only magic variants.

The actor-sample endpoint returns typed metadata plus base64 RGB and binary
coverage-mask buffers projected from the exact production-alpha graph. Coordinates
are explicitly identified as the top-left `production_alpha_1254_pixelgraph` space.
Hashes are recomputed during validation; malformed base64, non-binary masks,
out-of-range rectangles, shape mismatches, and metadata or content tampering fail
closed.

Release builds compile `WIZARD_AVATAR_GIT_SHA` into both the state endpoint (`build.git_sha`) and actor-sample metadata (`engine_commit`). The Hetzner bridge must build from and verify the same immutable commit.
