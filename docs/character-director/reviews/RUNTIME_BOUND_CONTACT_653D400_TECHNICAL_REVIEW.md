# Runtime-Bound Contact `653d400` Technical Review

Date: 2026-07-18
Reviewer: independent animation systems / production verification review
Runtime candidate: `653d4002c9bc5764c6ebc20c0b5f56dcfef9dfb8`
Evidence: `evidence/character-director/runtime-bound-contact-653d400-2026-07-18`

## Decision

**ACCEPT as transport, provenance, marker, and visible-contact engineering
evidence. Do not interpret this decision as visual-performance release approval.**

The supplied package independently replays all 341 contiguous adaptive wire
messages. Every decoded raster matches the manifest SHA-256 and atomic trace
SHA-256/FNV-1a values. Frame indexes, codec tags, encoded sizes, scenario labels,
and receive timestamps cross-bind across the manifest, wire index, and trace. A
fresh strict decoded-raster contact pass reproduces the archived report exactly.

## Verified Results

- Runtime identity remains stable from capture start through final trace retrieval.
- Runtime Git commit and tree match the clean captured checkout.
- Queue high-water mark is 1/16 with zero overruns, gaps, drops, or decoder errors.
- All 341 frame indexes are contiguous; all wire byte ranges are contiguous.
- Eight global keyframes are present, with no subscriber-private transport truth.
- Cast commit, effect, recoverable, and settled markers are each presented once in
  authored order.
- All 298 contact frames pass; 12 locked stances have maximum continuous drift of
  approximately `1.42e-14` cells and maximum visible raster-span drift of one cell.
- The verifier compares planted spans against the generated floor raster, so floor
  shading cannot satisfy the foreground-foot requirement.

## Validator Hardening

The review identified that artifact hashes and summary fields alone did not prove
semantic replay. `tools/run_character_director_visual_review.py` now decodes the
archived `wire/frames.bin`, verifies every indexed byte range and frame hash,
reconstructs the atomic trace binding, and recomputes the contact report. A
hash-consistent but semantically incomplete package fails the test gate.

## Remaining Technical Hardening

These are production trust-chain improvements, not reasons to invalidate the
captured runtime behavior:

1. Bind the dependency lock digest and installed distribution versions/hashes into
   runtime provenance.
2. Publish a detached manifest digest or signature from trusted CI so the evidence
   root is independently anchored.

## Scope Boundary

This decision proves the captured bytes, runtime, transport, marker delivery, and
contact behavior. It does not approve acting, interpolation, AV synchronization,
reduced motion, responsive framing, or the complete V1-V10 acceptance matrix.
