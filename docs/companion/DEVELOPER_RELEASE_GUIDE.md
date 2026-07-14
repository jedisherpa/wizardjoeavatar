# Wizard Joe Companion Developer and Release Guide

## Repositories

- Wizard Joe and Companion:
  `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar-python`
- Prism integration:
  `/Users/paul/Documents/Codex/2026-06-28/jedisherpa-prism-geometry-talk-https-github/work/prism-geometry-talk-current`

Read each repository's instructions before editing. Preserve unrelated
working-tree changes and the legacy service/install baseline.

## Source Verification

```sh
./.venv/bin/python -m unittest discover -s tests
cd companion && npm --prefix frontend test
cd companion && cargo fmt --manifest-path src-tauri/Cargo.toml --all -- --check
cd companion && cargo test --manifest-path src-tauri/Cargo.toml
cd companion && cargo clippy --manifest-path src-tauri/Cargo.toml --all-targets -- -D warnings
```

In Prism:

```sh
node --test \
  src/pages/PrismDodecahedron/__tests__/musicMotion.test.js \
  src/pages/PrismDodecahedron/media/__tests__/useMediaSessionConnector.test.js \
  src/pages/PrismDodecahedron/media/__tests__/monotonicSpeechClock.test.js
npm run build
cargo fmt --all --check
cargo test --locked --workspace
```

## Reproducible Local Build

From `companion/`:

```sh
npm ci
npm run sidecar:build
npm --prefix frontend test
cargo test --manifest-path src-tauri/Cargo.toml
npm run tauri:build
```

The sidecar builder requires `uv 0.11.7` and CPython `3.12.10`, installs the
locked build dependencies in an isolated directory, verifies Mach-O deployment
targets, and writes `build-provenance.json` beside the onedir payload. The
generated sidecar resource is intentionally ignored and must be rebuilt from
the intended source commit.

Expected local artifact (override the prefix with
`WIZARD_COMPANION_TARGET_DIR`):

```text
~/Library/Caches/Wizard Joe Companion/build-target/release/bundle/macos/Wizard Joe Companion.app
```

This build receives a local ad-hoc signature and strict resource-envelope
verification. It is not Developer ID signed, notarized, stapled, published, or
an authorization to replace an installed application.

## Packaged Verification

1. Confirm both repositories are clean and capture each HEAD.
2. Build the sidecar and app.
3. Verify provenance reports `sourceDirty: false` and the intended source HEAD.
4. Hash the sidecar executable and app bundle manifest.
5. Copy the app to an isolated path outside the repository. Install in
   Applications only if no existing app would be replaced.
6. Launch without a terminal-managed server and inspect the app-owned child.
7. Verify the private discovery file is a regular non-symlink file with mode
   `0600`, a fresh expiry, a literal-loopback URL, and no app-control token.
8. Launch a second instance and confirm it activates the first without creating
   another child.
9. Kill only the app-owned child and confirm bounded automatic recovery and
   runtime identity rotation.
10. Quit and confirm discovery removal and no orphan child.
11. Repeat both application launch orders with an isolated current Prism build.
12. Exercise main media and persona speech and record visible source/mouth
   evidence while independently confirming audible playback.

Never print the discovery credential or inherited app token. Diagnostic output
must use allowlisted fields or hashes.

## Commit and Publication

Commit implementation and evidence separately when a clean-build artifact must
refer to the implementation commit. Push only with explicit authorization.
Signing, notarization, release creation, auto-update feeds, external upload,
installed Prism replacement, and LaunchAgent migration are separate approval
boundaries.
