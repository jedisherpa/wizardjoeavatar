# Wizard Joe Media Performance Program

Status: Phase 0 research is in independent review; implementation is not complete.

This directory is the accountable design and delivery record for extending the
Rust Wizard Joe visualizer into a deterministic media-performance runtime for
PrismGT. It covers audiobook storytelling, music choreography, media-clock
synchronization, a governed Whiz source-link action, and production verification.

The program has two repositories and one control architecture:

- `jedisherpa/wizardjoeavatar` owns character capabilities, deterministic score
  validation, cue scheduling, animation execution, rendering, and frame evidence.
- `jedisherpa/prism-geometry-talk` owns media identity, durable media metadata,
  the browser media element, observed playback time, preprocessing orchestration,
  user controls, and governed external actions.
- The Wizard FLOW registry is the cross-repository status authority and records
  separate immutable repository receipts; its single Wizard `integration_head`
  is never used as evidence for a Prism change.
- PrismGT commands Wizard Joe only through the versioned extension of Wizard's
  existing remote-command transport. Promotion of the typed inbox under
  `RCHAT-RUN-110` is an explicit prerequisite; legacy controls remain supported
  through a bounded compatibility decoder until that gate is accepted. There is
  no second animation authority.

Documents:

- [PHASE_0_RESEARCH.md](PHASE_0_RESEARCH.md): independent research reports and
  code-grounded current-state findings.
- [ARCHITECTURE.md](ARCHITECTURE.md): final component split, contracts, clocks,
  data flow, recovery behavior, and security boundaries.
- [DEPENDENCIES.md](DEPENDENCIES.md): dependency decisions and rejected options.
- [IMPLEMENTATION_TRACKER.md](IMPLEMENTATION_TRACKER.md): sequenced work packages,
  owners, dependencies, evidence, and completion gates.
- [ACCEPTANCE_PROTOCOL.md](ACCEPTANCE_PROTOCOL.md): exhaustive deterministic,
  synchronization, visual, privacy, packaging, and rollback verification.

Frozen fixtures:

- [fixtures/capability-manifest-v2.json](fixtures/capability-manifest-v2.json):
  complete generated Wizard capability document and nonzero runtime hash binding.
- [fixtures/performance-score-v1.minimal.json](fixtures/performance-score-v1.minimal.json):
  minimal complete score bound to that capability document, the embedded Rust pose
  archive, motion graph, and
  `evidence/animation-quality/final/recordings/01-locomotion-directions.mp4`.
- [fixtures/media-protocol-v1.minimal.json](fixtures/media-protocol-v1.minimal.json):
  canonical hello, welcome, command, ACK, and snapshot transcript.

## Non-negotiable Rules

1. Production implementation remains Rust-first and has no Python runtime
   dependency.
2. `HTMLMediaElement.currentTime` is the observed playback-time authority in
   PrismGT. The Wizard server never invents a competing wall clock.
3. Expensive decoding, transcription, alignment, LLM analysis, and DSP run before
   playback or on bounded background workers, never on the render thread.
4. Performance scores are typed, versioned, hash-addressed, deterministic, and
   validated against a runtime-generated character capability manifest.
5. LLM output may select only capability IDs published by that manifest.
6. Seek, rate change, reconnect, and session restart increment timeline generation
   or otherwise invalidate stale cues before any visible mutation.
7. Whiz opens only the canonical URL stored with the active media record, only
   after an explicit user action, and only through PrismGT's governed action path.
8. Documentation may say `planned`, `candidate`, `shadow-validated`, or
   `implemented`; it may not collapse those states into one another.
9. The FLOW registry is the status authority. This directory supplies detail and
   acceptance criteria; it cannot mark its own work accepted.

## Delivery Definition

The program is complete only when the acceptance matrix in
`ACCEPTANCE_PROTOCOL.md` passes against packaged builds of both applications,
with saved score fixtures, command traces, every-frame visual evidence,
synchronization measurements, memory measurements, and explicit residual limits.
