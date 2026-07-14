# Wizard Joe Companion

Wizard Joe Companion is a separate Tauri 2 application. It supervises only its
packaged Wizard Joe Python child and never loads, unloads, edits, or signals the
legacy `com.jedisherpa.wizardjoeavatar` LaunchAgent.

## Requirements

- macOS 12 or later
- Rust 1.77.2 or later
- Node.js/npm for the pinned Tauri CLI
- `uv` 0.11.7 to provision the pinned CPython 3.12.10 build runtime

The sidecar builder rejects a different `uv` or Python patch version. An
explicit `PYTHON_BIN` may point to another CPython 3.12.10 executable, but every
Mach-O file in the result is still checked for a macOS 12-or-earlier deployment
target before the payload can be staged.

## Build

From `companion/`:

```sh
npm ci
npm run sidecar:build
npm test
npm run tauri:build
```

`sidecar:build` creates an isolated temporary tool environment, installs the
exact versions in `scripts/sidecar-requirements.lock`, and builds a
PyInstaller onedir payload. It then copies that complete payload to
`src-tauri/resources/sidecar/<target-triple>/wizard-joe-engine/`, where Tauri
bundles it without separating the executable from `_internal`.

The script writes `build-provenance.json` beside the sidecar with the Python and
PyInstaller versions, source commit/dirty state, lock hash, payload hash,
executable hash, target, and sidecar signing state. Tauri's resulting local app
is under `src-tauri/target/release/bundle/macos/`. `tauri:build` applies and
strictly verifies a local ad-hoc signature so the bundle has the resource
envelope macOS requires in Applications. It does not use Developer ID
credentials, notarize, staple, publish, copy to Applications, or alter an
installed app. The verified app is written outside File Provider workspaces at
`~/Library/Caches/Wizard Joe Companion/build-target/release/bundle/macos/` by
default; set `WIZARD_COMPANION_TARGET_DIR` to choose another stable local build
directory.

`WIZARD_SIDECAR_BUILD_DIR` can relocate the temporary sidecar build root.
Generated target-specific resource trees are intentionally ignored; rerun
`npm run sidecar:build` immediately before `npm run tauri:build`.

## Runtime Contract

- A temporary literal-loopback bind selects a dynamic internal port; port 8765
  is never targeted or controlled.
- Each app launch generates separate 32-byte app-control and media-relay
  credentials using the operating system CSPRNG. They reach the Python child
  only through inherited environment.
- Readiness requires a valid versioned `/api/companion/health` response with the
  expected schema, protocol, runtime identity, and child PID.
- After readiness, the supervisor atomically publishes and renews a private
  `0600` `connector-v1.json` rendezvous document. Prism receives only the media
  credential; the app-control credential never leaves the supervisor boundary.
- Unexpected exits receive at most four automatic restarts in 60 seconds with
  250/500/1000/2000 ms delays. A stable 30-second run or manual restart resets
  the policy.
- Quit and restart first request authenticated `/api/companion/shutdown`, wait
  up to three seconds, and kill only the app-owned `Child` if it has not exited.

Typed Tauri commands expose the runtime descriptor/status, engine restart, Prism
GT launch, log-folder opening, and privacy-safe diagnostic copying. No generic
shell command is exposed to the frontend. Logs are stored under the companion's
application-support `logs` directory.

## Checks

```sh
cargo fmt --manifest-path src-tauri/Cargo.toml --all -- --check
cargo test --manifest-path src-tauri/Cargo.toml
npm --prefix frontend test
```

The Rust tests cover port selection, token properties, health/status validation,
restart limits, and resource resolution. A full sidecar build additionally
requires the pinned CPython and downloads the locked build/runtime packages into
the isolated environment.
