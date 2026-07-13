# Wave 6 Final Verification Evidence

## Scope

This report closes the highest-value deterministic Wave 6 evidence path for the
Rust runtime and its shipped browser modules under `rust/wizard_avatar_engine`.
The evidence uses procedural Rust cell frames and the production ASCILINE codec.
No PNG, `<img>`, flattened avatar, palette blend, or full-frame crossfade is in
the runtime path.

- branch: `codex/build-repeatable-avatar-animation`
- recorded pre-pass commit: `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1`
- simulation: exact 60 Hz `AvatarRuntime`
- evidence sampling: exact rational 24 Hz clock, alternating two and three
  simulation ticks per frame
- replay transitions: 36
- replay frames: 1,008
- deterministic raw stream hash: `69d2f9e4e8a39288`
- deterministic semantic stream hash: `1f8db3d09f8d495f`

## Requirement-To-Evidence Mapping

| Requirement | Implementation / evidence | Result |
| --- | --- | --- |
| Exact 60 Hz replay and exact 24 Hz sampling | `wizard-avatar-evidence`, `src/evidence.rs`, `replay/replay-manifest.json` | Pass |
| Every defect-ledger transition category | 36 recipes in `replay/replay-manifest.json`; 1,008 state frames and semantic events | Pass |
| Final frame sequences and state/event logs | `frame-sequences/`, `logs/state-frames.ndjson`, `logs/semantic-events.ndjson` | Pass |
| Root/contact/staff/face/scale jump metrics | `transition-metrics.json`; all 36 boundaries passed | Pass |
| Four aggregate recordings and contact sheets | `recordings/*.mp4`, `screenshots/*-contact-sheet.png` | Pass |
| No pose shredding during direction changes | coherent whole-pose handoff plus exhaustive adjacent-view topology regression | Pass |
| A/B/C source/decode/presentation parity | 52 vectors through Rust source, production adaptive codec, shipped JS decoder/queue/renderer | Pass |
| Existing ASCILINE tags/envelope unchanged | vectors cover tags 0/1/2/3; five-byte envelope unchanged | Pass |
| Replay serialization and repeatability | serialized manifest run twice; semantic and raw hashes identical | Pass |
| Queue, malformed, resync, hidden/resume, context restore | Node module tests plus `resync-scenarios.json` | Pass at module level |
| Viewer counts 0/1/2/4/8 | 15-second wall-clock soak, three seconds per count | Pass |
| CI/nightly soak modes | `wizard-avatar-soak ci` = 1,800 s; `nightly` = 7,200 s | Configured, not run interactively |
| Snapshot/performance/demo regeneration | 30 snapshots, three performance profiles, fast and full demos | Pass |
| Procedural-only browser surface | Node assertion rejects `<img>`, `.png`, and `reference-avatar`; removed PNG remains absent | Pass |

## Directional Topology Fix

The first Wave 6 contact sheet exposed a shredded transition frame. Its cause
was region-local correspondence that moved sorted target cells from unrelated
source-cell positions when adjacent views had different topology.

That correspondence path was removed. A facing transition now presents one
complete pose at a time and switches the whole coherent view once at the blend
midpoint. Cells, anchors, face, staff, and gait stride axis all come from the
same presented pose. Gait/action offsets continue smoothly, while glyphs and
RGB values remain unchanged and discrete.

`wiz_anim_009_adjacent_facing_blends_preserve_coherent_complete_silhouettes`
samples 17 blend values for each of the eight adjacent direction pairs. It
rejects:

- missing required semantic regions
- occupied-cell count below 90% of either coherent endpoint floor
- connected-component explosion
- excessive row/column run fragmentation
- head, staff-hand, staff-tip, or root detachment from their semantic regions

All 136 transition samples pass. All four regenerated contact sheets were also
visually inspected after the fix; none contains scattered fragments, a missing
torso/head, duplicated staff, or detached face.

## Deterministic Replay

`replay/deterministic-parity.json` records:

```text
manifest hash        ba1afe183d3f31b8
run 1 semantic hash  1f8db3d09f8d495f
run 2 semantic hash  1f8db3d09f8d495f
run 1 raw hash       69d2f9e4e8a39288
run 2 raw hash       69d2f9e4e8a39288
frame counts equal   true
```

Category frame counts:

```text
locomotion/directions          308
speech/actions/expressions     476
circles/figure-eight            84
reconnect/replay               140
total                         1008
```

The transition boundary gate reports zero root, planted-foot, staff-hand,
face-anchor, and scale jumps at all command boundaries, zero unexpected mask
writes, and exact source/decode cell equality.

## ASCILINE A/B/C Parity

`hashes/abc-parity-summary.json` records 52 deterministic vectors:

```text
tag 0 raw      1
tag 1 zlib     1
tag 2 delta   39
tag 3 RLE     11
source == decoded cells        true
decoded == presented RGB       true
```

The C path uses the actual bounded `AscilineStreamClient` presentation queue
and `CellStageRenderer` module. It proves accepted frame content and queue
generation behavior, but it is not a claim of compositor timing in a controlled
Chromium, Firefox, or Safari process.

## Soak And Performance

The interactive short soak completed in 15.06 seconds. Across viewer counts
0/1/2/4/8:

- measured simulation rate: 59.90-60.19 Hz
- measured render rate: 23.94-24.25 FPS
- simulation deadline misses: 0
- render deadline misses: 0
- sequence gaps: 0
- lag events: 0
- canonical hash mismatches: 0
- maximum receiver queue depth: 1
- observed RSS range: 15,104-25,664 KB

`soak/configurations.json` defines a 30-minute CI mode and two-hour nightly
mode. Those long modes are configured but were not run during this interactive
pass.

The regenerated performance evidence exceeded each target:

```text
low     138.0 FPS vs 15 FPS target
medium  142.1 FPS vs 24 FPS target
high     72.8 FPS vs 30 FPS target
```

The fast demo completed 123 frames at 23.7 FPS. The full 23-step demo completed
1,023 frames at 24.0 FPS. Both mode-specific summaries are retained under
`evidence/wizard/rust-demo/`.

## Artifact Index

Primary bundle: `evidence/animation-quality/final/`

- `replay/replay-manifest.json`
- `replay/run-1-summary.json`
- `replay/run-2-summary.json`
- `replay/deterministic-parity.json`
- `logs/state-frames.ndjson`
- `logs/semantic-events.ndjson`
- `transition-metrics.json`
- `hashes/source-rust.ndjson`
- `hashes/codec-vectors.json`
- `hashes/source-decoded-presented.ndjson`
- `hashes/abc-parity-summary.json`
- `recordings/01-locomotion-directions.mp4`
- `recordings/02-speech-actions-expressions.mp4`
- `recordings/03-circles-figure-eight.mp4`
- `recordings/04-reconnect-replay.mp4`
- `screenshots/*-contact-sheet.png`
- `soak/short.json`
- `soak/configurations.json`
- `evidence-integrity.json`

Regenerated supporting evidence:

- `evidence/wizard/rust-snapshots/` (30 PPM frames plus manifest)
- `evidence/wizard/rust-performance/performance-summary.json`
- `evidence/wizard/rust-demo/demo-summary-fast.json`
- `evidence/wizard/rust-demo/demo-summary-full.json`

## Verification Commands

```text
cargo fmt --check
cargo test
cargo clippy --all-targets -- -D warnings
node --test web/tests/*.test.mjs
cargo run --bin wizard-avatar-snapshots
cargo run --bin wizard-avatar-performance
WIZARD_DEMO_FAST=1 cargo run --bin wizard-avatar-demo
cargo run --bin wizard-avatar-demo
cargo run --bin wizard-avatar-evidence
cargo run --bin wizard-avatar-soak -- short
cargo run --bin wizard-avatar-evidence -- --integrity-only
cargo run --bin wizard-avatar-evidence -- --check-integrity
```

Final gate outcomes:

```text
cargo fmt --check                         pass
cargo test                               57 passed, 0 failed
cargo clippy --all-targets -- -D warnings pass
node --test web/tests/*.test.mjs          18 passed, 0 failed
python3 -m unittest discover tests        54 passed, 0 failed
```

## Explicit Residual Limits

- The production Chromium surface passed controlled desktop and mobile checks,
  live adaptive WebSocket playback, repeat-until-Stop playback, and a clean
  browser console. Hidden/resume, context restore, malformed frames, resync,
  and per-vector presentation acceptance remain module-level evidence. No
  Firefox, Safari, device-pixel-ratio, or long-run compositor claim is made.
- The 30-minute CI and two-hour nightly soak modes are configured, not executed
  here. The meaningful interactive run was 15 seconds across all five viewer
  counts.
- Direction changes use a topology-safe coherent-pose handoff rather than a
  continuous cell morph. This intentionally favors silhouette integrity over
  synthesized in-between topology.
- The editable semantic pose IDs are enriched and validated in Rust from the
  current cell asset. Baking those IDs into the shared generator JSON remains
  outside the Rust-owned runtime pass.
