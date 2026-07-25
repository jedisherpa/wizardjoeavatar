# Serena G1 Score Identity Technical Review

**Date:** 2026-07-24  
**Scope:** Serena governed score-identity foundation  
**Package:** `sha256:30b5540c8d13cf579776961ce1b31839513a4e184355ec7a35cd16b4a98bc4e5`  
**Runtime profile:** `sha256:7d0cd620b907634f8743e9d08992ae1f591017dfae2a662d7e8e051ab91aa230`

## Decision

**ACCEPT.** Independent review found no P0-P2 findings after correction.

The accepted boundary:

- rejects foreign character and package identity before coordinator mutation;
- retains the V1 scoreless migration path when the package field is null;
- requires an exact package digest for every score-bound snapshot;
- admits canonical compiler output through the production schema loader;
- binds runtime admission to character, package, pose-library, and graph
  digests;
- validates cue `clip_id`, `node_id`, and `preload_asset_ids` against the
  active graph inventory;
- keeps capability-manifest identity at compilation/context time because
  compiled-score schema V1 does not carry that field.

## Verification

- Focused independent review: 50 tests passed.
- Broad Python performance and transport regression: 176 tests passed.
- Python bytecode compilation: passed.
- `git diff --check`: passed.

The broad pass covered media-session transport, score loading and publication,
compiler output, scheduler behavior, governed performance, Serena package
controls, Serena runtime boot, migration behavior, and stream-hub integration.

## Explicit Limits

This acceptance does not claim Serena locomotion, flight, arbitrary music
choreography, permission-world visuals, governed-speech generation parity, or
production character-registry admission. Those remain separately gated.

Unrelated untracked pose and historical evidence directories were preserved
and were not included in this review.
