# Commit and Provenance Report

## Python Baseline

- Repository: `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar`
- Commit: `556701a0dfd8c9c553de7159bc2d747b43fa9bd8`
- Date: `2026-07-14T04:41:00-06:00`
- Subject: `feat: add media-driven audiobook performance engine`
- Parent: `7781a67c97bfbfa16a64d5b9fb12bdf74bd4c032`
- Change: 77 files, 18,489 insertions, 32 deletions

The commit introduced strict media-session contracts and acknowledgements,
canonical artifact hashing, transcript ingestion, deterministic narrative/music
analysis and score generation, media-clock scheduling, speech/main priority,
runtime application, loopback APIs, tools, fixtures, and tests.

Direct corrective successor `408825ae75e395cd0761d0f17b9636a40559263a`
fixes stale acknowledgements, ownership, demo interference, stop controls,
private desktop activation, diagnostics, and mobile layout.

Later commits `3927b8c`, `a91f27d`, and `293a2d8` add the standalone Companion,
ad-hoc signing, and File Provider-safe build location. The preserved dirty
worktree contains later uncommitted projection, performance-shadow, Companion,
documentation, and close-up evidence.

## Prism Baseline

- Repository: `jedisherpa/prism-geometry-talk`
- Commit: `189fbabc4f59af5d53e352c6bf9c692ee7382214`
- Date: `2026-07-14T04:41:00-06:00`
- Subject: `feat: connect Prism media playback to Wizard Joe`
- Parent: `0ce9f9bae665b1415cd776e4d6c9ee23565936ac`
- Change: 9 files, 4,808 insertions, 2 deletions

The commit captures authoritative main-player and audible TTS state, prioritizes
speech, emits strict V1 snapshots, relays them through authenticated local Rust
routes, validates typed acknowledgements, and exposes sanitized diagnostics.

Direct successor `59106015fe22b224df350ddd28dc2fd487132681`
adds private packaged configuration, strict acknowledgement identity, explicit
degraded states, correct playback-rate display, visible status, and integration
documentation.

## Integration Decision

Use Python committed HEAD `293a2d8` as the clean implementation start because
it contains `408825a` and the Companion chain. Preserve the original dirty
worktree as evidence and port only independently reviewed changes.

Use a healthy clone at Prism `5910601`, not the damaged dirty worktree and not
raw `189fbab`. Review local `bf229c2` and dirty Prism changes before selectively
porting them.

## Rejected Alternatives

- Branching from either raw pinned commit.
- Assuming Prism `main` already contains the connector.
- Developing inside either dirty worktree.
- Treating installed binaries as source provenance.
- Cherry-picking unrelated RobbinPrism history wholesale.

## Verification

Before integration, rerun Python, Node connector, focused Rust route/contract,
Vite/Tauri, desktop, and live main -> speech -> restored-main behavior. Verify
pause release, acknowledgement mismatch visibility, `0600` private
configuration, and absence of credential leakage.
