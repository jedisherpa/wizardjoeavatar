# Wizard Avatar Rust Engine

Rust procedural ASCILINE wizard avatar engine.

This crate is a Rust implementation slice for the WizardJoeAvatar contract. It
does not decode video, render PNG sprites, or generate intermediary animation
frames. It produces direct ASCILINE-style cell framebuffers:

```text
[char, R, G, B] repeated once per cell
```

## What It Contains

- typed semantic wizard state
- expression, mouth, action, staff, and locomotion channels
- fixed white environment with faint perspective floor
- deterministic procedural pose-library renderer seeded from source references
- adaptive ASCILINE frame encoder and decoder
- `/ws/avatar/wizard?codec=adaptive` WebSocket stream
- semantic HTTP control routes under `/api/avatar/wizard/*`
- Rust-owned pose clips with interruption-safe handoffs and restoration
- adaptive browser client served from `/`

## Run

```bash
cargo run --bin wizard-avatar-server
```

Default URL:

```text
http://127.0.0.1:8787
```

The page at `/` connects to the adaptive ASCILINE stream, decodes RAW, ZLIB,
DELTA, and RLE_FULL frame tags in arrival order, renders the wizard on Canvas,
and sends semantic commands back to the Rust server.

Set a custom listener:

```bash
WIZARD_AVATAR_ADDR=127.0.0.1:8790 cargo run --bin wizard-avatar-server
```

Validate the complete 30-pose reference archive before any pose work:

```bash
cargo run --bin wizard-avatar-pose-catalog
```

The validator reads the immutable archive catalog, verifies every source PNG by
SHA-256, and confirms that all entries remain reference-only. New poses are
canonicalized, generated, animated, and verified by Rust tooling only. Python
pose generators are prototype artifacts owned by other workstreams and are not
part of this crate's production or completion path.

The existing `reference_avatar_pose_cells.json` remains a compatibility seed
while the Rust pose builder is introduced. No additional pose may be promoted
into that file until the Rust builder can reproduce its canonical grid,
semantic regions, anchors, contact metadata, and deterministic hash.

## Test

```bash
cargo test
cargo clippy --all-targets -- -D warnings
```

The test suite includes a live in-process WebSocket check that connects to
`/ws/avatar/wizard?codec=adaptive`, receives `INIT`, decodes the first binary
frame, and verifies that it reconstructs the default high-resolution cell
framebuffer.

## Evidence Helpers

Generate fast WebSocket demo evidence:

```bash
WIZARD_DEMO_FAST=1 cargo run --bin wizard-avatar-demo
```

Generate deterministic visual snapshots for all Rust-rendered directions,
expressions, actions, and walk phases:

```bash
cargo run --bin wizard-avatar-snapshots
```

Generate low/medium/high render and adaptive-encode performance evidence:

```bash
cargo run --bin wizard-avatar-performance
```

Generate the complete static pose census and deterministic every-frame motion
verification for all Rust clips and authored transitions:

```bash
cargo run --release --bin wizard-avatar-pose-evidence
```

The motion verifier captures 7,730 frames per pass, runs the suite twice, and
fails on any quality error, stream-hash mismatch, PNG count or numbering error,
or ledger-path mismatch. Its manifest, PNG frame ledger, contact sheets, and MP4 are written under
`evidence/pose-library-expansion/rust-final/` at the repository root.

## Scope Notes

This Rust crate owns the production runtime, pose pipeline, browser stream, and
verification evidence. Python files elsewhere in the repository are not a
fallback runtime and do not satisfy Rust completion gates.
