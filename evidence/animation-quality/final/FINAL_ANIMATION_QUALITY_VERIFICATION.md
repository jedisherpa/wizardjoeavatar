# Final Rust Animation-Quality Verification

This directory is the Wave 6 evidence bundle for the Rust
`wizard_avatar_engine` runtime and its shipped ASCILINE browser modules.

## Final Deterministic Result

- exact simulation rate: 60 Hz
- exact evidence sample rate: 24 Hz
- transition recipes: 36
- captured frames: 1,008
- raw-frame hash, both runs: `69d2f9e4e8a39288`
- semantic-state hash, both runs: `1f8db3d09f8d495f`
- A/B/C vectors: 52 across tags 0/1/2/3
- source/decode cell parity: pass
- decode/presentation RGB parity: pass
- transition boundary metrics: 36/36 pass
- short soak: pass at viewer counts 0/1/2/4/8

## Primary Artifacts

- `replay/`: serialized manifest, two summaries, deterministic parity
- `logs/`: source state frames and semantic events
- `hashes/`: Rust source, codec vectors, and browser-module A/B/C results
- `recordings/`: four MP4 aggregate recordings
- `screenshots/`: four aggregate contact sheets
- `frame-sequences/`: all final real Rust cell frames
- `soak/`: short run and CI/nightly configurations
- `transition-metrics.json`: root/contact/staff/face/scale boundary metrics
- `evidence-integrity.json`: final file hashes and byte sizes

## Visual Review

The regenerated contact sheets were inspected after removing unsafe
region-local cell correspondence between directional poses. Every directional
transition now presents a complete coherent pose. The final sheets contain no
shredded silhouette, missing torso/head, duplicated staff, or detached face.

## Browser Evidence Scope

The browser A/B/C path uses the production JavaScript decoder, bounded
generation-scoped presentation queue, and `CellStageRenderer` module. Queue,
malformed, resync, hidden/resume, and context-restore tests are module-level.
The production Chromium surface separately passed controlled desktop/mobile
playback and repeat-until-Stop checks with a clean console. No cross-browser or
long-run compositor claim is made.

The complete requirement mapping and residual limits are in
`docs/animation-quality/06_FINAL_VERIFICATION_EVIDENCE.md`.
