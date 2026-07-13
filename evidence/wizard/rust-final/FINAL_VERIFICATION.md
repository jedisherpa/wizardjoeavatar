# Rust Wizard Avatar Verification

Date: 2026-07-12

Status: Rust procedural engine prototype is implemented and locally verified for
the requested feasibility direction: a Rust ASCILINE-style avatar runtime that
generates moving chatbot frames from semantic wizard state instead of decoding
source video.

## Objective Coverage

- ASCILINE-style cell stream: Rust frames are row-major `[char, R, G, B]`
  framebuffers and are served through `/ws/avatar/wizard?codec=adaptive`.
- State-driven avatar: `WizardState` carries facing, locomotion, expression,
  mouth shape, action, upper-body gesture channel, staff state, speech state,
  screen position, scale, and reconnect count.
- Chatbot controls: semantic commands cover movement, paths, circles,
  figure-eight motion, facing, actions, expressions, speech, mouth shapes,
  stop, reset, and return-to-center.
- Moving-video feel: procedural walk phase, blink phase, world projection,
  action poses, magic effects, and adaptive frame deltas produce continuous
  streamed motion without prerecorded video frames.
- Clean-room stance: ASCILINE was used as architecture/protocol reference;
  the Rust implementation is not a direct source port.

## Evidence Files

- `ASCILINE_RUST_AVATAR_FEASIBILITY.md`
- `WizardJoeAvatar/rust/wizard_avatar_engine/README.md`
- `WizardJoeAvatar/evidence/wizard/rust-demo/README.md`
- `WizardJoeAvatar/evidence/wizard/rust-demo/demo-summary.json`
- `WizardJoeAvatar/evidence/wizard/rust-snapshots/README.md`
- `WizardJoeAvatar/evidence/wizard/rust-snapshots/manifest.json`
- `WizardJoeAvatar/evidence/wizard/rust-performance/README.md`
- `WizardJoeAvatar/evidence/wizard/rust-performance/performance-summary.json`

## Verification Commands

Run from `WizardJoeAvatar/rust/wizard_avatar_engine`:

```bash
cargo fmt
cargo test
cargo clippy --all-targets -- -D warnings
WIZARD_DEMO_FAST=1 cargo run --bin wizard-avatar-demo
cargo run --bin wizard-avatar-snapshots
cargo run --bin wizard-avatar-performance
```

Run from `WizardJoeAvatar`:

```bash
python3 -m unittest discover -s tests -v
```

Live server:

```bash
cargo run --bin wizard-avatar-server
```

Expected local URL: `http://127.0.0.1:8787`
