# Rust Chatbot Delivery and Accountability Audit

Audit role: `FLOW`

Audit date: 2026-07-13

Repository: `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar`

Baseline branch: `codex/build-repeatable-avatar-animation`

Purpose: determine what delivery controls are required to turn the completed
Rust pose and animation system into a first-class chatbot visualizer without
losing determinism, visual integrity, branch safety, or deployment
accountability.

## 1. Authority and supersession

This audit is Rust-only. The production authority for the new program is:

- `rust/wizard_avatar_pose_tool` for deterministic offline pose compilation;
- `rust/wizard_avatar_engine` for state, animation, rendering, ASCILINE
  encoding, HTTP/WebSocket delivery, evidence generation, and soak testing;
- `rust/wizard_avatar_engine/web` for the browser client served by the Rust
  server;
- port `8787` locally and the isolated Rust service behind the approved public
  endpoint in production.

The following copied documents remain useful research history but their
Python-only architecture, port-8765 acceptance target, Rust-exclusion rules,
commands, allowlists, work IDs, and release gates are superseded for the Rust
chatbot program:

- `docs/cartoon-animation-program/README.md`;
- `docs/cartoon-animation-program/WORKFLOW.md`;
- `docs/cartoon-animation-program/IMPLEMENTATION_PLAN.md`;
- `docs/cartoon-animation-program/planning/01-first-principles-plan.md`;
- `docs/cartoon-animation-program/planning/02-animation-plan.md`;
- `docs/cartoon-animation-program/planning/03-rust-plan.md`;
- `docs/cartoon-animation-program/planning/04-workflow-plan.md`.

The transferable controls are retained: explicit contracts, fixed-tick state,
one-writer locks, dependency gates, deterministic replay, compact evidence,
real-browser verification, reversible promotion, and exact pushed/deployed SHA
proof. Python files and the separate `web/avatar` client may be read as design
references, but they are not acceptance authorities for this program.

## 2. Final pose prerequisite

The pose prerequisite is closed. The coordinator supplied and the generated
manifests record this final baseline:

| Fact | Required value | Final result |
|---|---:|---:|
| Runtime geometries | 89 | 89 |
| Newly integrated unique WJFL geometries | 50 | 50 |
| Compiled catalog records | 80 | 80 |
| Imported unique geometries | 79 | 79 |
| Imported aliases | 1 | 1 |
| Rust clips | 16 | 16 |
| Authored directed transitions | 621 | 621 |
| Static evidence frames | 89 | 89 |
| Animation frames per pass | 20,065 | 20,065 |
| Deterministic passes | 2 | 2 identical streams |
| Quality failures | 0 | 0 |
| Adaptive decode parity | 100% | pass |
| Presentation parity | 100% | pass |

The two animation streams share SHA-256
`a2daab4ce0ffee0f37683c9a0f4b2ef3dea96477f7252cff9877d426953833d5`.
The promoted gzip asset SHA-256 is
`028e2d3ff9e0ff58d72c7bb39a792f1d76f7ecc8cf5d37da91677f486eab3bb8`.

Authoritative prerequisite surfaces:

- `rust/wizard_avatar_engine/assets/wizard_pose_library.v4.json.gz`;
- `evidence/pose-library-expansion/rust-v4/admission-ledger.json`;
- `evidence/pose-library-expansion/rust-v4/static-census/manifest.json`;
- `evidence/pose-library-expansion/rust-v4/animation-verification/manifest.json`;
- `docs/pose-library-expansion/feelings-queue.json`.

The chatbot implementation must freeze these facts in a dedicated pushed
checkpoint. A dirty working tree or locally generated evidence is not a durable
start gate even when its results pass.

## 3. Current Rust delivery surface

### 3.1 Strengths already present

The engine already provides the hard foundation the copied plan was trying to
create elsewhere:

- deterministic 60 Hz simulation stepping and bounded catch-up;
- a 24 FPS procedural cell-frame source at 480 by 270 cells;
- typed state for locomotion, facing, action, expression, speech, staff,
  contact, pose playback, and channel generations;
- coherent pose handoff, replacement, expiration, and restoration;
- direct ASCILINE cell generation with RAW, ZLIB, DELTA, and RLE_FULL codecs;
- a shared Axum HTTP/WebSocket service and adaptive browser decoder;
- exact static pose, transition, contact, topology, attachment, decode, and
  presentation evidence;
- deterministic replay and quality inspection code;
- focused performance and short/CI/nightly soak binaries;
- a dedicated release binary, `wizard-avatar-server`;
- an isolated Hetzner service, port, Nginx host, certificate, and release
  directory.

The pose compiler is offline. Runtime behavior does not load reference PNGs,
videos, sprite sheets, or flattened animation frames. This remains a release
invariant.

### 3.2 Delivery gaps for a first-class chatbot visualizer

| Gap | Current condition | Required delivery control |
|---|---|---|
| Chat lifecycle | Generic semantic commands exist; no frozen chatbot event contract | Versioned, bounded event envelope and invalid-fixture tests |
| Idempotency | Runtime scheduling is deterministic but network event identity is incomplete | Source epoch/sequence, event ID, dedupe, terminal ack |
| Conversational policy | Clips exist but chatbot state-to-performance selection is not a frozen product contract | Complete 89-pose taxonomy and deterministic policy table |
| Speech timing | Timed speech and fallback mouth motion exist | Quantized viseme/phrase cues, cancellation, reconnect rules |
| Interruption | Pose/channel restoration exists | Full conversation-state interruption matrix and recovery bounds |
| Browser input | Served client uses click/keydown commands | Held input lifecycle, keyup/blur/reconnect release, JSON ack diagnostics |
| Browser proof | Module tests and prior manual browser evidence exist | Automated Chromium scenario matrix with presented-frame hashes |
| CI | The Wizard Joe repository has no authoritative workflow | Required checks in this repository or a pinned reusable workflow |
| Deployment | Bridge workflow builds a mutable branch from another repository | Exact SHA input, full gates, build-info proof, atomic rollback |
| Release identity | State API does not prove source commit, asset, graph, and policy together | Capabilities/build endpoint and evidence lineage |
| Progress accounting | Existing copied tracker is Python-specific | Machine-readable Rust registry with dependencies and weighted progress |

### 3.3 Browser audit

The Rust-served browser correctly decodes ordered adaptive frames, requests
resync, uses atomic Canvas presentation, preserves crisp cells, reconnects, and
offers semantic movement, expression, action, speech, Stop, and repeat-tour
controls. The following are not yet sufficient for chatbot acceptance:

- no versioned chatbot event/ack protocol is visible in the UI;
- no event-to-tick-to-frame-to-presented causal lineage is shown;
- keyboard movement is command-on-keydown rather than leased held input;
- keyup, blur, gamepad disconnect, and event TTL are not one unified release
  path in the Rust-served client;
- no reduced-motion control or chatbot-state diagnostic exists;
- no automated real-browser suite proves all conversation states,
  interruptions, reconnects, and frame parity.

The richer TypeScript controls under `web/avatar` demonstrate useful held-input,
lease, speech, and release ideas, but are not served by the Rust endpoint and
cannot satisfy Rust gates until deliberately ported or replaced.

## 4. Deployment audit

The public Rust endpoint is isolated at
`https://wizardjoe.5.78.137.112.sslip.io/`, backed by
`wizardjoe-avatar.service`, `/opt/wizardjoe-avatar`, and internal listener
`127.0.0.1:18787` on `root@5.78.137.112`. The latest observed bridge run was
successful and the state API was live.

The deployment bridge is held on
`jedisherpa/prism-geometry-talk@codex/wizardjoe-avatar-deploy-bridge-v2` and
reads `CRX41_HETZNER_SSH` from the `hetzner` environment. It checks out
`jedisherpa/wizardjoeavatar` from a branch, builds the Rust server, uploads only
the binary, switches `/opt/wizardjoe-avatar/current`, installs/restarts systemd,
configures Nginx and TLS, and verifies the page and state API.

Release weaknesses to close before final promotion:

1. The workflow resolves a mutable branch rather than accepting a coordinator-
   approved immutable Wizard Joe SHA.
2. It runs engine library tests, not the complete engine integration suite,
   pose-tool suite, v4 admission check, 20,065-frame evidence integrity check,
   browser automation, or soak gate.
3. It does not verify that the remote API reports the same commit, asset hash,
   graph hash, and policy hash that passed CI.
4. It switches `current` before recording and testing an explicit `previous`
   rollback link.
5. It does not perform a rollback drill or retain a machine-readable deployment
   receipt in the Wizard Joe evidence package.
6. Required checks are controlled from another repository, so branch protection
   and change review are indirect.

The bridge may remain the secret-bearing deploy mechanism, but it must consume a
pinned SHA and a signed/hashed release manifest produced by the Wizard Joe CI
gate.

## 5. Accountability model required

### 5.1 Three-agent model

| Agent | Accountable scope | Must not own |
|---|---|---|
| `RUNTIME` | Rust event contracts, command ordering, runtime regions, speech timing, policy reducer, replay, telemetry, transport contracts | Motion tuning, registry, final deployment |
| `MOTION` | 89-geometry taxonomy, graph, clips, transitions, emotion/gaze/viseme performance, secondary motion, visual review | Network authority, registry, deployment |
| `FLOW` | Registry, dependency enforcement, locks, CI, evidence schemas, browser harness, soak/release/deploy verification | Production animation policy or runtime reducer |

The coordinator is the only integration writer for shared hotspots and the only
actor allowed to mark a cross-lane gate `PASS`, push a promotion checkpoint, or
trigger deployment.

### 5.2 Required registry facts

Every work item needs a stable ID, title, owner, reviewer, exact dependencies,
status, weight, path allowlist, held locks, gate, base SHA, result SHA, commands,
evidence paths and hashes, rollback point, blocker, timestamps, and handoff.

Allowed states are:

```text
PLANNED -> READY -> IN_PROGRESS -> HANDOFF_READY -> IN_REVIEW -> ACCEPTED
                                  \-> FAILED -> READY
                                  \-> BLOCKED -> READY
ACCEPTED -> REOPENED -> READY
```

Only `ACCEPTED` earns progress. `BLOCKED`, `FAILED`, and `REOPENED` earn zero.
An item is `READY` only when every dependency is `ACCEPTED`, required locks are
free, and its base SHA equals the integration head recorded by the coordinator.

### 5.3 Gate discipline

Every gate must be represented by one compact JSON record with:

- gate and schema version;
- exact Git SHA, dirty-tree status, branch, Rust version, OS, browser version;
- pose asset, animation graph, policy, replay, and browser bundle hashes;
- required work IDs and their accepted evidence hashes;
- commands, exit codes, durations, totals, failures, skips, and thresholds;
- artifact paths/URLs and SHA-256 values;
- primary reviewer and independent reviewer;
- rollback SHA/profile and drill result;
- final `PASS` or `FAIL` with machine-readable reasons.

No percentage average can hide a structural failure. Pose breakup, unknown
geometry, missing ack, nondeterminism, decode/presentation mismatch, browser
console error, runtime PNG access, privacy violation, or stale deployed SHA is
an automatic gate failure. The final product score may be at least 90%, but all
structural and safety gates remain 100% pass.

## 6. Evidence and retention audit

Commit compact evidence only:

- gate JSON and summary Markdown;
- registry and schema files;
- hashes and aggregate metrics;
- one curated contact sheet per major gate when under 5 MiB.

Store heavy outputs as CI/release artifacts:

- every-frame PNGs and RGB streams;
- full NDJSON replay and transition ledgers;
- Playwright traces and browser videos;
- long soak logs, flamegraphs, and profiles.

Recommended retention:

| Artifact | PR | release candidate | final release |
|---|---:|---:|---:|
| Unit/contract logs | 14 days | 90 days | manifest only |
| Every-frame evidence | 14 days | 90 days | 180 days |
| Browser traces/video | 14 days | 90 days | 180 days |
| Soak/performance logs | 14 days | 90 days | 180 days |
| Gate manifests/checksums | committed | committed | permanent |
| Release binary/receipt | n/a | 90 days | permanent release asset |

Artifacts must be named `wizardjoe-rchat-<gate>-<git-sha>-<kind>` and every
manifest must record the artifact URL, SHA-256, size, producer command, and
retention class.

## 7. Required validation command classes

The implementation workflow must make these command classes authoritative:

```bash
cargo fmt --manifest-path rust/wizard_avatar_pose_tool/Cargo.toml --all -- --check
cargo clippy --manifest-path rust/wizard_avatar_pose_tool/Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path rust/wizard_avatar_pose_tool/Cargo.toml --locked

cargo fmt --manifest-path rust/wizard_avatar_engine/Cargo.toml --all -- --check
cargo clippy --manifest-path rust/wizard_avatar_engine/Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path rust/wizard_avatar_engine/Cargo.toml --locked
node --test rust/wizard_avatar_engine/web/tests/*.test.mjs

cargo run --manifest-path rust/wizard_avatar_engine/Cargo.toml --locked --release --bin wizard-avatar-pose-evidence
cargo run --manifest-path rust/wizard_avatar_engine/Cargo.toml --locked --release --bin wizard-avatar-evidence -- --check-integrity
cargo run --manifest-path rust/wizard_avatar_engine/Cargo.toml --locked --release --bin wizard-avatar-performance
cargo run --manifest-path rust/wizard_avatar_engine/Cargo.toml --locked --release --bin wizard-avatar-soak
```

New chatbot contract, replay, interruption, coverage, browser, and scope tests
must be additive to this floor. The pose prerequisite is never replaced by a
smaller chatbot-only suite.

## 8. Audit conclusion

The Rust system is ready for the chatbot implementation program. Its pose and
transition foundation is complete at 89/50/621 with two identical 20,065-frame
passes and zero quality failures. The remaining risk is not lack of visual
material; it is uncontrolled integration. The next pass must freeze contracts,
keep three-agent ownership disjoint, serialize hotspot wiring, make every gate
machine-verifiable, prove every presented browser frame, and deploy only the
exact pushed SHA that passed the complete Rust release matrix.
