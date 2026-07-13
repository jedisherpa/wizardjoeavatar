# Rust Per-Frame Pose Verification Protocol

This protocol is mandatory for the 30-pose expansion. A green average, smooth-looking video, or a few representative screenshots is insufficient. Every rendered source frame must be saved and checked before the expansion can be called complete.

## Scope

- 10 baseline geometries.
- 29 unique new geometries.
- One duplicate catalog alias (`WJFA-10`) that must resolve to `WJFA-01` without producing another geometry.
- Every authored directed neighbor transition in `rust/wizard_avatar_engine/src/pose_program.rs`.
- Every applicable locomotion, upper-body, staff, expression, blink, speech, and effect overlay.
- Near, medium, and far projection bins.
- Rust source frame, adaptive ASCILINE decoded frame, and presentation-accepted logical frame.

## Required Sequences

For each unique new pose, capture these deterministic sequences at a 60 Hz simulation rate and a 24 Hz render rate:

1. Stable source neighbor for at least 12 rendered frames.
2. Entry transition through every rendered frame.
3. Stable hold for at least 24 rendered frames.
4. Speech plus blink while held when the face is visible.
5. Expression change while held when the face is visible.
6. Locomotion while held when the pose permits independent movement.
7. Higher-priority interruption at every legal interruption window.
8. Replacement by another pose in the same family.
9. Exit to every authored neighbor.
10. Restoration of the prior stable state.

Flight additionally requires takeoff, hover, flap, bank left, bank right, glide, airborne reaction, landing, and recovered idle. Ground locomotion additionally requires idle-to-walk, walk phases, acceleration, run or dash beat, landing, deceleration, and idle restoration.

## Frame Artifacts

The Rust verifier writes:

```text
evidence/pose-library-expansion/rust-final/
  static-census/
    manifest.json
    contact-sheet.png
    frames/<zero-padded-frame>.png
  animation-verification/
    manifest.json
    frame-ledger.ndjson
    animation.mp4
    timeline-contact-sheet.png
    frames/<zero-padded-frame>.png
```

The PNG count must equal the reported rendered frame count. Numbering must begin at zero, remain contiguous through the final frame, and contain no extra files. Every NDJSON row names the scenario, pose, frame index, simulation tick, semantic state, quality metrics, all 25 semantic anchors, contact markers, planted-foot state, local stream sequence, global presented sequence, codec tag, source/decoded/presented SHA-256 values, presentation acceptance, and matching PNG path; every named path must exist. The manifest records both complete stream hashes and rejects unequal passes, adaptive decode parity, or presentation parity.

## Per-Frame Rejection Rules

Reject the run when any frame has:

- one or more horizontal seam rows
- one or more internal robe or core cracks
- a disconnected staff or a gap through its authored shaft span
- an empty or implausibly collapsed silhouette
- a component explosion relative to adjacent frames
- a detached head, face, beard, hand, foot, wing root, or staff grip
- cells outside the canonical canvas or unexpected clipping
- an invalid layer order or duplicated semantic region
- a planted contact that moves relative to the projected floor
- a contact shadow inconsistent with grounded, airborne, hover, or landing state
- a source/decoded/presented logical hash mismatch
- a non-increasing presented sequence

Effects may be disconnected only when authored as effect components. Wings may have separated tips only when their compiler metadata explicitly permits those attachment edges.

## Pairwise Rejection Rules

For every consecutive rendered pair:

```text
contact root step              = 0 cells during local pose transitions
planted support step           = 0 cells
face-anchor step               <= 1.5 cells unless face is occluded
staff-grip step                <= 1.5 cells unless authored as an impact cut
free-foot step                 <= 5 cells
component-count step           <= 2
occupancy ratio                >= 0.88
source hash                    = decoded hash = presented logical hash
presented sequence             strictly increasing
```

Any authored exception must name the pose, frame window, semantic reason, and alternate numeric limit in the Rust motion specification. There are no global exemptions.

## Determinism

Run the complete matrix twice from a clean state. Require byte-identical:

- compiled pose artifact
- semantic event stream
- frame manifest
- source frame stream hashes
- adaptive codec vectors
- decoded frame stream hashes
- per-frame quality results

A difference is a failure even if both videos look acceptable.

## Visual Review

Automated gates run first. Then generate labeled contact sheets from every sequence and inspect the full recordings at normal playback speed. The 7,173-frame Rust ledger proves source-to-adaptive-decode-to-presentation-accepted logical parity. The production JavaScript queue and decoder are separately covered by 18 module tests, and the live Chromium surface is checked for playback, repeat-until-Stop behavior, responsive layout, and console errors. Browser approval is supplemental evidence; it cannot override a failed source-frame or decoded-frame gate.

The implementation remains incomplete until the independent verifier reruns this protocol, inspects the resulting contact sheets and recordings, and records `PASS` with no unexplained frame failures.

## Current verified run

The 2026-07-13 Rust run captured 7,173 animation PNGs per pass, checked 6,991 consecutive pairs, exercised 11 Rust clips and all 170 authored transitions, and reported zero failures. The verifier confirmed exact zero-based PNG numbering, exact ledger path existence, 25 anchors and contact metadata on every row, contiguous global presented sequence `0..7172`, and source/decoded/presented hash equality with presentation acceptance on all 7,173 frames. Both complete passes produced stream SHA-256 `c53e11ae34aca237be2325b44005ecf6698ecc62001d2461b24ca90d4dd65a1b`. The static census contains all 40 runtime catalog frames: 39 unique geometries and one alias.

See [RUST_INTEGRATION_REPORT.md](RUST_INTEGRATION_REPORT.md) and `evidence/pose-library-expansion/rust-final/` for the complete record.
