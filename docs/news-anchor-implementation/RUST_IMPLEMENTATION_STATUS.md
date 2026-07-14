# Rust Newsroom Implementation Status

Updated: 2026-07-14

Branch: `codex/rust-news-anchor-engine`

Baseline used by this implementation: `e3c5c5d8fa39b16a2da6a48215a28dc84eee38e5`.
The packet pinned the earlier Rust commit `e2b0cd74d8f7356d6900138aad34654acf21a187`.

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
| Actor samples | Rust emits cell-aligned RGB and binary coverage buffers with bounds, root, contacts, staff/wing bounds, state/package/content hashes, and a recomputed actor-layer hash. No PNG is used as runtime character data. | `actor_samples_are_cell_aligned_hashed_and_tamper_evident` |
| Speech timeline | Ordered, non-overlapping mouth/caption intervals, generation identity, closed defaults between cues, and strict fields are implemented. | `speech_timeline_is_ordered_non_overlapping_and_closes_between_cues` |
| Frame QA | The existing evidence binary now drives all 88 variants through `NewsPerformanceCueV1` and the real controller, then checks entry, hold, timed restore, adaptive decode, PNG, contact, topology, and two-pass hashes. | `evidence/pose-library-expansion/rust-v4/animation-verification/manifest.json` |

## Rust Work-Item Ledger

| Work item | Status | Accountability note |
|---|---|---|
| WJ-020 strict schemas | COMPLETE | Seven immutable packet schemas, strict typed ingress, closed identifiers, and malformed/raw-control rejection are implemented. |
| WJ-021 newsroom geometry | COMPLETE_WITH_APPROVED_COMPOSITION | All 88 variants resolve to authored Rust geometry. The project owner approved the current imagery on 2026-07-14; 25 entries remain honestly labeled `approved_composition` rather than falsely described as unique new meshes. |
| WJ-022 desk/contact/occlusion metadata | COMPLETE_WITH_APPROVED_COMPOSITION | Desk/seated semantic variants, root/contact sets, actor coverage, and staff/wing bounds are emitted. Final desk/chair foreground compositing remains WJ-032 in Joe. |
| WJ-023 MotionGraph mappings | COMPLETE | Every selected pose resolves to a canonical matrix transition and an existing `MotionGraphV1` recipe; reduced motion uses its dedicated recipe. |
| WJ-024 lifecycle | COMPLETE | Monotonic generation/sequence handling, replay idempotency, interruption, restoration, completion, bounded history, and stale rejection are active in the real controller/runtime/hub path. |
| WJ-025 actor samples | COMPLETE | RGB plus required binary coverage, optional depth/shadow fields, contacts/bounds, state/package/layer hashes, base64 transport, tamper checks, and nonblocking generation are implemented. |

## Packet Discrepancy

The immutable 88-pose catalog references 23 semantic transition names absent from the immutable 30-transition matrix. Several mapped matrix transitions also omit the referencing pose from their legal target set. Rust preserves both source files exactly, resolves names through a closed compatibility table, prefers a declared entry when it is legal, and otherwise selects the first canonical matrix transition that explicitly permits the target pose. Receipts always record the actual canonical transition and existing `MotionGraphV1` recipe.

## Fidelity And Approval

All 88 semantic poses execute today using authored Rust geometry:

- 4 are exact existing matches.
- 59 are composed or approximate uses of existing authored geometry/channels.
- 25 execute as approved compositions of existing authored geometry because the packet classifies them as `NEW_GEOMETRY` or `NEW_GEOMETRY_AND_CLIP` but the current imagery was explicitly approved by the project owner on 2026-07-14.

Those 25 include count/compare/pointing variants, desk/seated work, teleport arrival, and wings-resting imagery. The approval promotes the current composed Rust imagery for this implementation. It does not claim that these are newly drawn unique source geometries; receipts report `approved_composition` so that provenance remains honest.

Joe Newsroom compositor, set occlusion, editorial graphics, TTS authority, and final cross-repository deployment remain Joe-owned boundaries. This Rust branch does not bypass or claim those responsibilities.

## Verification Result

The implementation source gate passed the focused newsroom contracts, clippy with warnings denied, Rust doc tests, all 18 browser presentation tests, and `cargo test --locked --all-targets`. The all-target run includes the 1,015.32-second authored-neighbor breakup gate and the 252.95-second imported-pose loop gate. A release-mode short soak also passed with warmed actor-sample p50/p95/p99 timings of 5.75/8.49/8.49 milliseconds against a 250-millisecond p99 ceiling and a 64 MiB peak-RSS-growth ceiling.

The exact-SHA frame run and named 60-minute newsroom soak remain the evidence-only release gates after the clean implementation commit. The soak exercises all semantic commands and seeded variants, correction and reduced-motion policy, stale rejection, actor-sample generation, runtime clock continuity, reconnects, bounded fanout queues, canonical frame hashes, process RSS, and actor-sample latency percentiles; its retained result is `evidence/animation-quality/final/soak/newsroom.json`.

The optimized visual preflight produced:

- 24,724 frames in each of two complete passes.
- 621 authored transitions.
- 88 newsroom semantic pose scenarios.
- 16 Rust clips.
- 89 static runtime geometries and one alias.
- zero frame-quality failures.
- exact source/adaptive-decode/presentation parity.
- identical replay SHA-256: `d4710b9125817a9efcd3bf2de43409e4b6f1cd724ad14dd7ce785cad7590ec5e`.

The final run embeds its clean source commit in both evidence manifests. Generated frame PNGs and the raw frame stream remain reproducible build evidence and are ignored because they exceed practical Git storage. The compact manifest and timeline contact sheet are retained in Git.

## Reproduction

Run from `rust/wizard_avatar_engine`:

```bash
cargo fmt --all -- --check
cargo clippy --locked --all-targets --all-features -- -D warnings
cargo test --locked --all-targets
cargo test --locked --doc
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

The actor-sample endpoint returns typed metadata plus base64 RGB and binary coverage-mask buffers. Coordinates are explicitly identified as an actor-local, top-left cell grid; Joe remains responsible for placing that layer in its 320x180 studio space. Hashes are recomputed during validation; malformed base64, non-binary masks, out-of-range rectangles, shape mismatches, and metadata or content tampering fail closed.

Release builds compile `WIZARD_AVATAR_GIT_SHA` into both the state endpoint (`build.git_sha`) and actor-sample metadata (`engine_commit`). The Hetzner bridge must build from and verify the same immutable commit.
