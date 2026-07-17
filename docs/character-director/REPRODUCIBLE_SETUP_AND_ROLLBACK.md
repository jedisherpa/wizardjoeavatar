# Reproducible Setup, Operation, and Rollback

This runbook covers the Python Wizard Joe runtime, the PyInstaller/Tauri
**Wizard Joe Companion**, and the Prism GT connector in these two worktrees:

```text
/Users/paul/Documents/WizardJoeAsci/worktrees/wizardjoe-character-director
/Users/paul/Documents/WizardJoeAsci/worktrees/prism-character-director
```

It deliberately preserves the historical LaunchAgent and Python service on
`127.0.0.1:8765`. The Companion is a separate application: it selects an
ephemeral loopback port, starts only its packaged child, and never loads,
unloads, signals, or rewrites `com.jedisherpa.wizardjoeavatar`.

## Runtime choices

| Mode | Owner | Endpoint | Prism selection |
|---|---|---|---|
| Companion | `Wizard Joe Companion.app` owns its packaged Python child | Dynamic `127.0.0.1` port | Private, expiring discovery file; default for current packaged Prism |
| Source development | A terminal owns `tools/run_wizard_avatar_server.py` | An explicitly chosen unused loopback port | Explicit private compatibility config when Prism relay is needed |
| Legacy compatibility | LaunchAgent `com.jedisherpa.wizardjoeavatar` | `http://127.0.0.1:8765` | Explicit `PRISM_WIZARD_CONNECTOR_CONFIG` only |

Do not run two Wizard processes on the same port. Do not use `killall Python`,
`pkill -f wizard`, or a generic port-8765 kill command; those can stop the
preserved service.

## Security invariants

These are operational requirements, not optional hardening:

- Every Wizard listener uses a literal loopback host. The Python runner rejects
  non-loopback `--host` values, and Prism rejects non-loopback connector URLs.
- Each Companion launch creates separate random app-control and media-relay
  credentials. The app-control credential remains inside the supervisor/child
  boundary. Only the media credential appears in the discovery document.
- Never print, paste into a ticket, commit, or attach a discovery document,
  connector config, process environment, or real credential. Examples below
  generate credentials locally and display only allowlisted, non-secret fields.
- The Companion discovery file must be owned by the current user, be a regular
  non-symlink file, have exact mode `0600`, and remain at or below 16 KiB. Prism
  rejects unknown fields, stale documents, ports below 49152, unsafe file
  metadata, and malformed values.
- Discovery is not a browser contract. Prism's Rust backend reads the media
  credential and relays bounded media/performance contracts. It does not expose
  the credential to the WebView, URLs, diagnostics, or status responses.
- The connector does not carry audio bytes, transcript/persona text, local
  paths, source URLs, private media metadata, memory, prompts, tokens, or
  governed actions. Wizard Joe cannot invoke Prism actions or bypass approval.
- Keep release signing, notarization, installation replacement, publication,
  and auto-update work outside this local-build procedure unless separately
  authorized.

## 1. Clean-environment setup

### 1.1 Prerequisites

Use macOS 12 or later with Xcode Command Line Tools. The strictest requirements
across both worktrees are:

- Git
- Rust `1.77.2` or later (`prism-character-director` itself requires `1.75`)
- Node.js 24 and npm `11.13.0`
- `uv 0.11.7` exactly for Companion sidecar builds
- CPython `3.12.10` for the packaged sidecar; the build script provisions it
  in an isolated build root when `PYTHON_BIN` is not set

Confirm the toolchain without displaying environment secrets:

```sh
rustc --version
cargo --version
node --version
npm --version
uv --version
xcode-select -p
```

The sidecar builder fails closed if `uv` is not exactly `0.11.7` or an explicit
`PYTHON_BIN` is not exactly CPython `3.12.10`.

### 1.2 Define the worktrees and capture provenance

```sh
export WIZARD_REPO=/Users/paul/Documents/WizardJoeAsci/worktrees/wizardjoe-character-director
export PRISM_REPO=/Users/paul/Documents/WizardJoeAsci/worktrees/prism-character-director

git -C "$WIZARD_REPO" rev-parse HEAD
git -C "$WIZARD_REPO" status --short --branch
git -C "$PRISM_REPO" rev-parse HEAD
git -C "$PRISM_REPO" status --short --branch
```

A release-reproducible build requires a reviewed clean checkout. The active
integration worktrees may legitimately be dirty while work is in progress; do
not clean, reset, or discard them to satisfy this check. The sidecar provenance
records `sourceCommit` and `sourceDirty`, so a dirty build remains visibly a
development artifact.

### 1.3 Provision source and JavaScript dependencies

```sh
cd "$WIZARD_REPO"
uv sync --frozen --python 3.12.10

cd "$WIZARD_REPO/companion"
npm ci

cd "$PRISM_REPO"
npm ci
cargo fetch --locked
```

`uv sync --frozen` creates the repository `.venv` used by source development
and by the legacy LaunchAgent template. `npm ci` uses each checked-in lockfile.
The Companion sidecar build still creates its own disposable packaging venv and
installs `companion/scripts/sidecar-requirements.lock`; it does not package the
repository `.venv`.

## 2. Development start

### 2.1 Python source runtime without Prism

Use a dedicated non-8765 port so the preserved service can remain live:

```sh
cd "$WIZARD_REPO"
export WIZARD_DEV_PORT=8876
lsof -nP -iTCP:"$WIZARD_DEV_PORT" -sTCP:LISTEN
./.venv/bin/python tools/run_wizard_avatar_server.py \
  --host 127.0.0.1 \
  --port "$WIZARD_DEV_PORT" \
  --cols 240 \
  --rows 135 \
  --fps 24
```

The `lsof` command should return no listener before startup. Open
`http://127.0.0.1:8876/`. In this source-only mode the app-control boundary is
off, and the Prism media connector is disabled unless its environment is set.
Stop it with `Ctrl-C` in the owning terminal.

### 2.2 Python source runtime connected to Prism

This is an explicit development compatibility override, not Companion
discovery. It creates a private config with a newly generated token and never
prints that token:

```sh
cd "$WIZARD_REPO"
umask 077
export WIZARD_DEV_PORT=8876
export WIZARD_DEV_DIR="$HOME/Library/Application Support/Wizard Joe Development"
export WIZARD_DEV_CONFIG="$WIZARD_DEV_DIR/prism-connector.env"
export WIZARD_DEV_SCORE_ROOT="$WIZARD_DEV_DIR/scores"
mkdir -p "$WIZARD_DEV_DIR" "$WIZARD_DEV_SCORE_ROOT"
WIZARD_DEV_TOKEN="$(openssl rand -hex 32)"
printf '%s\n' \
  'PRISM_WIZARD_CONNECTOR_ENABLED=1' \
  "PRISM_WIZARD_BASE_URL=http://127.0.0.1:$WIZARD_DEV_PORT" \
  "PRISM_WIZARD_CONNECTOR_TOKEN=$WIZARD_DEV_TOKEN" \
  > "$WIZARD_DEV_CONFIG"
chmod 600 "$WIZARD_DEV_CONFIG"
WIZARD_MEDIA_CONNECTOR_ENABLED=1 \
WIZARD_MEDIA_CONNECTOR_TOKEN="$WIZARD_DEV_TOKEN" \
WIZARD_SCORE_ROOT="$WIZARD_DEV_SCORE_ROOT" \
./.venv/bin/python tools/run_wizard_avatar_server.py \
  --host 127.0.0.1 --port "$WIZARD_DEV_PORT"
```

In a second terminal, launch the Prism desktop development shell with that
specific private config:

```sh
export PRISM_REPO=/Users/paul/Documents/WizardJoeAsci/worktrees/prism-character-director
export WIZARD_DEV_CONFIG="$HOME/Library/Application Support/Wizard Joe Development/prism-connector.env"
cd "$PRISM_REPO"
PRISM_WIZARD_CONNECTOR_CONFIG="$WIZARD_DEV_CONFIG" npm run desktop:dev
```

The config parser accepts exactly the three shown keys, a literal-loopback HTTP
URL with an explicit nonzero port, and a 32-1024-byte non-whitespace ASCII
token. The file must be regular, no larger than 4 KiB, and have no group/world
permission bits. An accepted explicit config wins over Companion discovery for
that Prism process. Quit Prism and relaunch it without this environment variable
to return to Companion discovery.

### 2.3 Companion development shell

The Tauri shell requires a complete PyInstaller onedir resource before it can
start its owned child:

```sh
cd "$WIZARD_REPO/companion"
npm ci
npm run sidecar:build
npm --prefix frontend test
npm test
npm run tauri -- dev
```

The sidecar builder uses a disposable root at
`${TMPDIR:-/tmp}/wizard-joe-companion-sidecar-build` unless
`WIZARD_SIDECAR_BUILD_DIR` is set. It packages the Python runner, runtime
modules, definitions, browser assets, and motion manifest into:

```text
companion/src-tauri/resources/sidecar/<host-triple>/wizard-joe-engine/
```

At runtime the Companion selects an ephemeral loopback port, generates both
credentials, starts the sidecar with `--companion`, validates health and PID,
and only then publishes discovery. Do not separately start the Python runner
for this mode.

### 2.4 Prism development choices

To exercise the complete Tauri launch path and discovery injection:

```sh
cd "$PRISM_REPO"
npm run desktop:dev
```

The Tauri shell runs `npm run build:binary`, starts its own
`prism-dodeca-cli --serve` child, prefers `127.0.0.1:42817` when available, and
otherwise selects another loopback port. It injects the default Companion
discovery path only when no explicit connector enablement or discovery path is
already present.

For backend/browser development without the Prism Tauri shell:

```sh
cd "$PRISM_REPO"
npm run serve:binary
```

That command serves the built Prism UI on `http://127.0.0.1:3001/`, with TTS
disabled, and uses Companion discovery when no explicit connector environment
is present. Do not run `desktop:dev` and `serve:binary` as if they were one
Prism instance; each owns a separate backend process.

### 2.5 Legacy LaunchAgent, opt-in only

The legacy installer is not a clean-machine dependency of the Companion. Run
it only when fixed-port compatibility is intentionally required, and only
after Section 1 has created `$WIZARD_REPO/.venv`:

```sh
cd "$WIZARD_REPO"
test -x .venv/bin/python
lsof -nP -iTCP:8765 -sTCP:LISTEN
tools/install_local_wizard_service.sh
launchctl print "gui/$(id -u)/com.jedisherpa.wizardjoeavatar"
lsof -nP -iTCP:8765 -sTCP:LISTEN
curl -fsS http://127.0.0.1:8765/api/avatar/wizard/state | /usr/bin/python3 -m json.tool
```

The installer creates or reuses a private 64-hex connector credential, writes
the legacy config and LaunchAgent with mode `0600`, bootstraps the agent, and
enables `RunAtLoad`/`KeepAlive`. It first boots out an existing copy of that
agent, so it intentionally changes the legacy PID. Do not run it during a
coexistence acceptance pass whose purpose is to prove that the existing 8765
process remains untouched.

## 3. Packaged local builds

### 3.1 Wizard Joe Companion

```sh
cd "$WIZARD_REPO/companion"
npm ci
npm run sidecar:build
npm --prefix frontend test
cargo test --manifest-path src-tauri/Cargo.toml
npm run tauri:build
```

Default outputs:

```text
companion/src-tauri/resources/sidecar/<host-triple>/wizard-joe-engine/build-provenance.json
~/Library/Caches/Wizard Joe Companion/build-target/release/bundle/macos/Wizard Joe Companion.app
```

`npm run tauri:build` places Cargo output outside the File Provider workspace,
applies a local ad-hoc signature, and performs strict bundle verification. It
does not Developer ID sign, notarize, staple, publish, install, or replace an
existing application. Override the build root only with an explicit stable
path:

```sh
WIZARD_COMPANION_TARGET_DIR="$HOME/Library/Caches/Wizard Joe Companion/alternate-target" \
  npm run tauri:build
```

Verify the default artifact and its packaged child:

```sh
APP="$HOME/Library/Caches/Wizard Joe Companion/build-target/release/bundle/macos/Wizard Joe Companion.app"
TRIPLE="$(rustc --print host-tuple)"
PROVENANCE="$WIZARD_REPO/companion/src-tauri/resources/sidecar/$TRIPLE/wizard-joe-engine/build-provenance.json"
test -d "$APP/Contents"
test -f "$PROVENANCE"
/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP/Contents/Info.plist"
codesign --verify --deep --strict --verbose=2 "$APP"
/usr/bin/python3 -m json.tool "$PROVENANCE"
```

For a clean release candidate, `sourceDirty` must be `false`, `sourceCommit`
must equal the reviewed Wizard commit, the host triple must be intended, and
the recorded Python version must be `3.12.10`. Provenance contains no runtime
credential.

Launch this exact build without replacing an installed copy:

```sh
open "$APP"
```

### 3.2 Prism GT local package

```sh
cd "$PRISM_REPO"
npm ci
npm run desktop:build
```

The Tauri `beforeBuildCommand` runs `npm run build:binary`, which builds the
frontend and the release `prism-dodeca-cli`, then bundles that sidecar at:

```text
$PRISM_REPO/target/release/bundle/macos/Prism GT.app
```

Verify and launch the worktree artifact without replacing `/Applications/Prism
GT.app`:

```sh
PRISM_APP="$PRISM_REPO/target/release/bundle/macos/Prism GT.app"
test -x "$PRISM_APP/Contents/Resources/prism-dodeca-cli"
/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$PRISM_APP/Contents/Info.plist"
codesign --verify --deep --strict --verbose=2 "$PRISM_APP"
open "$PRISM_APP"
```

`scripts/build_desktop_release.sh`, notarization, DMG creation, and installed-app
replacement are credentialed release operations and are not implied by the
local package command above.

## 4. Prism connection and launch order

### Companion discovery, the default

1. Launch the Companion build or development shell.
2. Wait until the Companion UI reports **Ready**.
3. Launch current Prism without `PRISM_WIZARD_CONNECTOR_ENABLED`,
   `PRISM_WIZARD_CONNECTOR_CONFIG`, `PRISM_WIZARD_BASE_URL`, or
   `PRISM_WIZARD_CONNECTOR_TOKEN` overrides.
4. Open Prism's **Diagnostics** command card and inspect **Wizard connector**.
5. Start or pause real media. A successful relay changes the connector from
   `connecting` to `connected`; paused media remains a healthy connected state.

Either application may launch first. Prism refreshes discovery before status
and relay operations, and replaces its active transport when the runtime epoch
or endpoint changes. Missing, expired, invalid, or unreadable discovery is
reported as `unavailable`, not `connected`.

The current Prism **Open Wizard** link still points to
`http://127.0.0.1:8765/`. That link opens the legacy visualizer; it does not
identify the dynamic Companion endpoint. Use the Companion window for the
Companion-owned visualization.

### Explicit legacy selection

The legacy installer writes this private config:

```text
~/Library/Application Support/WizardJoeAvatar/prism-connector.env
```

To test a packaged Prism binary against legacy `8765` without changing global
launchd environment, launch that binary from a terminal with the explicit
config:

```sh
LEGACY_CONFIG="$HOME/Library/Application Support/WizardJoeAvatar/prism-connector.env"
PRISM_BINARY="$PRISM_REPO/target/release/bundle/macos/Prism GT.app/Contents/MacOS/Prism GT"
PRISM_WIZARD_CONNECTOR_CONFIG="$LEGACY_CONFIG" "$PRISM_BINARY"
```

Do not combine an explicit legacy config with Companion discovery. Quit that
Prism process and relaunch normally to select the Companion again.

## 5. Writable paths and retention

| Owner | Path | Contents and policy |
|---|---|---|
| Companion runtime | `~/Library/Application Support/com.jedisherpa.wizardjoecompanion/` | App-owned durable runtime root |
| Companion logs | `~/Library/Application Support/com.jedisherpa.wizardjoecompanion/logs/engine.log` | Sidecar stdout/stderr; rotates at 5 MiB with `engine.log.1` through `.5` |
| Compiled scores | `~/Library/Application Support/com.jedisherpa.wizardjoecompanion/scores/` | Immutable score generations and atomic current pointers |
| Discovery writer | `~/Library/Application Support/Wizard Joe Companion/connector-v1.json` | Ephemeral private rendezvous; 120-second TTL, refreshed about every 45 seconds while healthy |
| Companion build cache | `~/Library/Caches/Wizard Joe Companion/build-target/` | Rebuildable local Cargo/Tauri output, not user score data |
| Prism runtime | `~/Library/Application Support/com.jedisherpa.prismgeometrytalk/` | Prism backend data; all desktop sidecar data variables point here |
| Prism log | `~/Library/Application Support/com.jedisherpa.prismgeometrytalk/prism-dodeca-cli.log` | Prism sidecar stdout/stderr |
| Legacy config | `~/Library/Application Support/WizardJoeAvatar/prism-connector.env` | Private fixed-port connector config |
| Legacy service | `~/Library/LaunchAgents/com.jedisherpa.wizardjoeavatar.plist` | LaunchAgent definition; contains the private media credential and must remain `0600` |
| Legacy logs | `~/Library/Logs/WizardJoeAvatar.log` and `WizardJoeAvatar.error.log` | Historical service output |

Compiled score storage is content-bound:

```text
scores/
  .publication.lock
  media/<media-sha256-without-prefix>/
    current.json
    scores/<score-id>/<revision>/
      score.json
      manifest.json
```

Publication writes immutable generations and atomically replaces `current.json`.
Rollback between score revisions repoints `current.json` only after the selected
generation validates. Do not hand-edit score files or pointers while the
runtime is active. Back up the whole `scores/` directory before deleting app
data; logs and scores are the only Companion paths here that may be valuable
after uninstall.

## 6. Health and diagnostics

### 6.1 Companion discovery and engine health

Inspect metadata and allowlisted fields without printing `mediaToken`:

```sh
DISCOVERY="$HOME/Library/Application Support/Wizard Joe Companion/connector-v1.json"
stat -f 'mode=%Sp owner=%Su bytes=%z path=%N' "$DISCOVERY"
/usr/bin/python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print({k:d[k] for k in ("schemaVersion","baseUrl","runtimeEpoch","pid","issuedAtUnixMs","expiresAtUnixMs")})' "$DISCOVERY"
```

Expected: owner is the current user, mode is `-rw-------`, size is at most
16384 bytes, the URL is literal `127.0.0.1` with a dynamic port, and expiry is
fresh. Obtain the non-secret URL and call the unauthenticated, privacy-safe
health route:

```sh
COMPANION_URL="$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["baseUrl"])' "$DISCOVERY")"
curl -fsS "$COMPANION_URL/api/companion/health" | /usr/bin/python3 -m json.tool
```

Healthy output has schema and protocol version `1`, status `ready`, a nonempty
runtime epoch and character ID, `frame_hub_running: true`, and
`connector_enabled: true`. Check that the published PID owns only its dynamic
listener:

```sh
ENGINE_PID="$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["pid"])' "$DISCOVERY")"
ps -p "$ENGINE_PID" -o pid=,ppid=,etime=,command=
lsof -nP -a -p "$ENGINE_PID" -iTCP -sTCP:LISTEN
```

Do not call Companion mutation, state, or WebSocket routes with the discovery
credential. The media credential is accepted only by the bounded connector
routes; app commands use the separate app-control credential through typed
Tauri commands.

The Companion UI also exposes **Restart Engine**, **Open Logs**, and **Copy
Diagnostics**. Copy Diagnostics includes app version and sanitized runtime
status, not credentials, local paths, transcript text, or media URLs.

### 6.2 Prism health and connector status

Packaged Prism prefers port `42817`, but falls back when it is occupied. Find
the exact owned listener rather than assuming the port:

```sh
PRISM_PID="$(pgrep -x prism-dodeca-cli | tail -n 1)"
ps -p "$PRISM_PID" -o pid=,ppid=,etime=,command=
lsof -nP -a -p "$PRISM_PID" -iTCP -sTCP:LISTEN
PRISM_PORT="$(lsof -nP -a -p "$PRISM_PID" -iTCP -sTCP:LISTEN -Fn | sed -n 's/^n127\.0\.0\.1://p' | head -n 1)"
PRISM_URL="http://127.0.0.1:$PRISM_PORT"
curl -fsS "$PRISM_URL/api/health" | /usr/bin/python3 -m json.tool
curl -fsS "$PRISM_URL/api/readiness" | /usr/bin/python3 -m json.tool
curl -fsS "$PRISM_URL/api/connectors/wizard/status" | /usr/bin/python3 -m json.tool
```

The connector status response is sanitized: it exposes state, counters, coarse
latency, HTTP/error codes, short identity suffixes, scheduler disposition, and
permission-world relay state, but no endpoint, token, path, transcript, or
media content. `unavailable` with `wizard_unavailable` means discovery is
missing, stale, unsafe, or unreachable. `connecting` means a valid transport is
selected but no accepted media acknowledgement has established connected
health yet.

### 6.3 Logs and focused checks

```sh
tail -n 200 "$HOME/Library/Application Support/com.jedisherpa.wizardjoecompanion/logs/engine.log"
tail -n 200 "$HOME/Library/Application Support/com.jedisherpa.prismgeometrytalk/prism-dodeca-cli.log"

cd "$WIZARD_REPO"
./.venv/bin/python -m unittest \
  tests.wizard.test_companion_runner \
  tests.wizard.test_companion_server \
  tests.wizard.test_score_runtime
cd "$WIZARD_REPO/companion"
cargo test --manifest-path src-tauri/Cargo.toml
npm --prefix frontend test

cd "$PRISM_REPO"
node --test src/pages/PrismDodecahedron/media/__tests__/useMediaSessionConnector.test.js
cargo test --locked -p prism-cdiss-cli media_connector
npm run build:binary
cargo test --locked -p prism-geometry-talk-desktop
```

The Prism desktop test must follow `npm run build:binary`: its Tauri bundle
configuration requires `target/release/prism-dodeca-cli` to exist as a resource
even when Cargo is compiling the desktop unit tests.

Do not attach whole app-support directories to bug reports. Use the safe
diagnostic surfaces and inspect logs for unexpected private content before
sharing any excerpt.

## 7. Graceful shutdown

### Companion

Quit **Wizard Joe Companion** normally. The supervisor sends authenticated
`POST /api/companion/shutdown`, waits up to three seconds, kills only the child
it spawned if that child does not exit, joins the supervisor, and removes only
the discovery file whose runtime epoch it owns.

For `npm run tauri -- dev`, quit the app window/application and let the command
return. Do not terminate the terminal first unless the app is unresponsive.

If force quit was unavoidable, treat the remaining discovery document as stale
until it expires. Before stopping an apparent orphan, derive its PID from the
private discovery file, verify that its command belongs to the expected
`Wizard Joe Companion.app/.../wizard-joe-engine` bundle and that its listener
matches the document, then send `TERM` to that one PID only:

```sh
ENGINE_PID="$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["pid"])' "$DISCOVERY")"
ps -p "$ENGINE_PID" -o pid=,ppid=,command=
kill -TERM "$ENGINE_PID"
```

Do not run the `kill` command unless the preceding identity check matches.

### Prism

Closing/destroying the Prism Tauri window stops and waits for only the
`prism-dodeca-cli` child that shell spawned. A directly run
`npm run serve:binary` process handles `Ctrl-C` as graceful server shutdown.

### Legacy 8765 service

The only repository-provided stop command is scoped to its LaunchAgent:

```sh
cd "$WIZARD_REPO"
tools/stop_local_wizard_service.sh
```

This does not remove the plist, config, logs, source environment, Companion, or
Prism. Restart it with `tools/install_local_wizard_service.sh` only after the
repository `.venv` exists; that installer atomically regenerates an invalid or
missing 64-hex media token, writes private config/plist files, and bootstraps
the fixed-port service.

## 8. Rollback

### 8.1 Preserve evidence and scores

After normal Companion shutdown, archive valuable state before removal:

```sh
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$HOME/Desktop/Wizard Joe Companion rollback $STAMP"
mkdir -p "$BACKUP"
ditto "$HOME/Library/Application Support/com.jedisherpa.wizardjoecompanion/logs" "$BACKUP/logs" 2>/dev/null || true
ditto "$HOME/Library/Application Support/com.jedisherpa.wizardjoecompanion/scores" "$BACKUP/scores" 2>/dev/null || true
```

The discovery file is a credential-bearing ephemeral file; do not archive it.

### 8.2 Remove only Companion-owned artifacts

First disable **Launch at login** in the Companion. If the app cannot open,
remove its login item in macOS **System Settings > General > Login Items**.
Confirm no Companion or packaged engine process remains, then remove only the
specific build/install path and Companion-owned support roots:

```sh
COMPANION_APP="$HOME/Library/Caches/Wizard Joe Companion/build-target/release/bundle/macos/Wizard Joe Companion.app"
COMPANION_DATA="$HOME/Library/Application Support/com.jedisherpa.wizardjoecompanion"
DISCOVERY_DIR="$HOME/Library/Application Support/Wizard Joe Companion"

test "$COMPANION_DATA" = "$HOME/Library/Application Support/com.jedisherpa.wizardjoecompanion"
test "$DISCOVERY_DIR" = "$HOME/Library/Application Support/Wizard Joe Companion"
rm -rf -- "$COMPANION_APP" "$COMPANION_DATA"
rm -f -- "$DISCOVERY_DIR/connector-v1.json"
rmdir "$DISCOVERY_DIR" 2>/dev/null || true
```

If a copy was installed elsewhere, remove that exact verified Companion path
separately. Never substitute `/Applications/Prism GT.app`, either Prism
worktree, the Prism application-support directory, `WizardJoeAvatar`, or a
parent `Application Support` directory into these commands.

### 8.3 Return Prism to the desired connector

- To return to Companion discovery, quit every Prism process and relaunch Prism
  with no connector override environment.
- To return to legacy `8765`, leave the historical service/config intact and
  launch Prism with `PRISM_WIZARD_CONNECTOR_CONFIG` set to the private legacy
  config as shown above.
- To disable Wizard relay for one development launch, set
  `PRISM_WIZARD_CONNECTOR_ENABLED=0` for that Prism process. Do not delete Prism
  data to change connector selection.

### 8.4 Repository rollback

Use normal, reviewed `git revert <commit>` commits in the affected repository.
Do not use `git reset --hard`, overwrite whole files from another checkout, or
discard unrelated working-tree changes. Companion and Prism are independently
revertible; rolling back the Companion does not require changing Prism's data,
governance state, preserved application, or legacy LaunchAgent.

## 9. Coexistence acceptance checklist

Before declaring a setup reproducible, record these non-secret results:

1. Capture both repository HEADs and dirty/clean state.
2. Confirm the legacy listener PID on `127.0.0.1:8765` before Companion launch.
3. Launch Companion and verify a different dynamic listener, validated health,
   exact private discovery metadata, and a packaged child path.
4. Confirm the legacy PID and listener did not change.
5. Launch Prism before Companion once and Companion before Prism once; both
   orders must reach a valid transport without editing a token.
6. Play and pause real media and confirm a typed acknowledgement, connected
   status, runtime identity suffix, and no audio interruption when Wizard is
   unavailable.
7. Restart the Companion engine and confirm the runtime epoch/credential
   rotation is accepted while legacy `8765` remains unchanged.
8. Quit Companion normally and confirm its discovery file disappears, its
   child exits, and legacy `8765` still answers.
9. Inspect safe diagnostics and both logs for credentials, transcript/persona
   text, source URLs, or local media paths; none may be present.
10. Preserve build provenance and focused test output with the acceptance
    record, never the connector/discovery files themselves.
