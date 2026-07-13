# Rust Chatbot Multi-Agent Implementation Workflow

Plan ID: `RCHAT-FLOW`

Owner: `FLOW`

Status: coordinator synthesis input

This workflow operationalizes the RUNTIME and MOTION plans. It does not
authorize production implementation until the coordinator has committed and
pushed the final pose checkpoint and synthesized the central implementation
plan and registry.

## 1. Binding rules

1. Rust is the sole production runtime, animation, rendering, transport,
   evidence, and release authority for this program.
2. The final pose baseline is immutable during chatbot work: 89 runtime
   geometries, 50 unique WJFL geometries, 621 authored directed transitions, 16
   clips, 89 static frames, two identical 20,065-frame passes, zero failures.
3. Reference PNGs remain offline compiler inputs. Runtime PNG/video/sprite
   loading is prohibited.
4. One Rust runtime owns semantic state at 60 Hz. The browser presents frames
   and sends semantic intent; it does not choose poses or advance world state.
5. Every event is versioned, ordered, bounded, idempotent, acknowledged, and
   replayable.
6. Every animation path uses the graph, region ownership, contact/attachment
   constraints, and deterministic policy. Chat integrations cannot select raw
   production pose IDs.
7. Shared hotspots have one coordinator writer. Agents prepare new modules,
   focused tests, assets, and explicit wiring handoffs.
8. No work is accepted from a dirty or stale base without coordinator review.
9. Structural gates require 100%. The final independent product score must be
   at least 90%, but averages cannot waive any blocker.
10. The exact pushed SHA, tested release binary, deployed binary, public state
    endpoint, and rollback target must agree.

## 2. Roles and ownership

| Role | Primary ownership | Review obligation |
|---|---|---|
| `RUNTIME` | event/command contracts, clock, inbox, state regions, speech timing, reducer, replay, telemetry, transport contract modules | Review MOTION interfaces and FLOW determinism evidence |
| `MOTION` | pose taxonomy, graph, clips, transitions, performance policy, visemes/gaze, secondary motion, visual thresholds | Review runtime event meanings and every visual gate |
| `FLOW` | registry/schema/validator, CI, evidence manifests, browser automation, soak/performance orchestration, release/deploy receipts | Independently verify both implementation lanes |
| `INT` | coordinator-only hotspot wiring, gate promotion, central tracker/registry, branch push, deploy trigger, rollback | Resolve contract conflicts and accept/reject handoffs |

### 2.1 Path allowlists

RUNTIME may own new files under:

```text
rust/wizard_avatar_engine/src/chat_*.rs
rust/wizard_avatar_engine/src/command*.rs
rust/wizard_avatar_engine/src/replay*.rs
rust/wizard_avatar_engine/src/speech*.rs
rust/wizard_avatar_engine/src/state_regions*.rs
rust/wizard_avatar_engine/src/telemetry*.rs
rust/wizard_avatar_engine/tests/chat_*.rs
rust/wizard_avatar_engine/tests/replay_*.rs
rust/wizard_avatar_engine/tests/speech_*.rs
```

MOTION may own new files under:

```text
rust/wizard_avatar_engine/src/motion_*.rs
rust/wizard_avatar_engine/src/facial_*.rs
rust/wizard_avatar_engine/src/secondary_*.rs
rust/wizard_avatar_engine/assets/chatbot_motion_graph*.json.gz
rust/wizard_avatar_engine/tests/motion_*.rs
rust/wizard_avatar_engine/tests/chatbot_animation_*.rs
```

FLOW may own:

```text
docs/cartoon-animation-program/rust-chatbot/**
tools/rchat/**
schemas/rchat/**
.github/workflows/rust-chatbot-*.yml
rust/wizard_avatar_engine/web/tests/**
rust/wizard_avatar_engine/tests/release_*.rs
evidence/cartoon-animation-program/rust-chatbot/**/*.json
evidence/cartoon-animation-program/rust-chatbot/**/*.md
```

Central `IMPLEMENTATION_PLAN.md`, tracker, and registry are coordinator-owned.
An agent does not gain ownership of a hotspot merely because its plan mentions
the path.

## 3. One-writer lock table

| Lock | Paths/surface | Writer | Release condition |
|---|---|---|---|
| `LOCK-RCHAT-REGISTRY` | central tracker and registry | `INT` | schema validation and status commit |
| `LOCK-RCHAT-CARGO` | both Cargo manifests/locks | `INT` | locked build and full tests pass |
| `LOCK-RCHAT-LIB` | engine `src/lib.rs` | `INT` | module compiles and focused tests pass |
| `LOCK-RCHAT-RUNTIME` | `runtime.rs` | `INT` | clock/inbox/replay matrix passes |
| `LOCK-RCHAT-STATE` | `state.rs` | `INT` | old/new JSON compatibility passes |
| `LOCK-RCHAT-CONTROLLER` | `controller.rs` | `INT` | reducer/director integration passes |
| `LOCK-RCHAT-CHANNELS` | `animation.rs` | `INT` | ownership/interruption matrix passes |
| `LOCK-RCHAT-POSE` | `pose.rs`, promoted v4 asset | `INT`; pose asset frozen | full 89/50/621 gate passes |
| `LOCK-RCHAT-CLIPS` | `pose_clip.rs` | `INT` from MOTION handoff | clip hash and legacy equivalence recorded |
| `LOCK-RCHAT-PLAYBACK` | `pose_playback.rs` | `INT` | replacement/restore matrix passes |
| `LOCK-RCHAT-RENDERER` | `renderer.rs`, `frame_source.rs` | `INT` | owned-region screenshot delta passes |
| `LOCK-RCHAT-HUB` | `hub.rs` | `INT` | cadence/fanout/resync tests pass |
| `LOCK-RCHAT-SERVER` | `server.rs` | `INT` | HTTP/WS contract and legacy parity pass |
| `LOCK-RCHAT-WEB` | served browser HTML/JS | `INT` | module and Chromium matrices pass |
| `LOCK-RCHAT-EVIDENCE` | evidence binary integration | `INT` | schema, count, and integrity checks pass |
| `LOCK-RCHAT-DEPLOY` | bridge workflow and remote service | `INT` | F0 approval and rollback target recorded |

A lock record contains `lock_id`, `holder`, `work_id`, `paths`, `acquired_at`,
`expires_at`, `base_sha`, and `reason`. A stale lock is a blocker, not permission
for another writer to proceed.

## 4. Machine-readable registry recommendation

Registry schema ID: `wizardjoe-rchat-registry/v1`.

Required top-level fields:

```json
{
  "schema_version": 1,
  "program_id": "RCHAT",
  "branch": "codex/build-repeatable-avatar-animation",
  "integration_head": "<40-hex-sha>",
  "planning_checkpoint": {
    "local_sha": "<40-hex-sha>",
    "remote_sha": "<40-hex-sha>",
    "pushed": true
  },
  "pose_baseline": {
    "status": "PASS",
    "runtime_geometries": 89,
    "wjfl_geometries": 50,
    "authored_transitions": 621,
    "clips": 16,
    "static_frames": 89,
    "frames_per_pass": 20065,
    "passes": 2,
    "quality_failures": 0,
    "asset_sha256": "028e2d3ff9e0ff58d72c7bb39a792f1d76f7ecc8cf5d37da91677f486eab3bb8",
    "stream_sha256": "a2daab4ce0ffee0f37683c9a0f4b2ef3dea96477f7252cff9877d426953833d5",
    "evidence_manifest": "evidence/pose-library-expansion/rust-v4/animation-verification/manifest.json"
  },
  "agents": [],
  "locks": [],
  "work_items": [],
  "gates": [],
  "artifacts": [],
  "deployments": [],
  "progress": {}
}
```

Each work item requires:

```json
{
  "id": "RCHAT-FLOW-000",
  "title": "string",
  "owner": "RUNTIME|MOTION|FLOW|INT",
  "reviewers": ["role"],
  "status": "PLANNED|READY|IN_PROGRESS|HANDOFF_READY|IN_REVIEW|ACCEPTED|FAILED|BLOCKED|REOPENED",
  "weight": 1,
  "dependencies": ["work-id"],
  "gate_id": "P0",
  "path_allowlist": ["glob"],
  "required_locks": ["lock-id"],
  "base_sha": "40-hex-or-null",
  "result_sha": "40-hex-or-null",
  "started_at": "RFC3339-or-null",
  "finished_at": "RFC3339-or-null",
  "commands": [{"command": "string", "exit_code": 0, "duration_ms": 0}],
  "evidence": [{"path": "string", "sha256": "64-hex", "artifact_url": null}],
  "metrics": {},
  "rollback": {"sha": null, "profile": "legacy", "verified": false},
  "blocker": null,
  "handoff_id": null
}
```

Validator rules:

- IDs are unique and immutable.
- Dependencies exist and form an acyclic graph.
- Only one item is `IN_PROGRESS` per hotspot lock.
- `READY` requires all dependencies `ACCEPTED`.
- `ACCEPTED` requires result SHA, commands, evidence hashes, reviewer, gate, and
  rollback fields.
- Evidence Git SHA equals result SHA.
- No path falls outside the owner allowlist or coordinator handoff.
- No required test is skipped or ignored.
- Gate `PASS` requires every mandatory item `ACCEPTED`.
- Deployment SHA equals the F0-approved SHA.

## 5. Progress accounting

Progress is weighted accepted work, never subjective percent-complete:

```text
accepted_weight / total_weight * 100
```

Report four numbers:

- `program_percent`: all work items;
- `critical_path_percent`: items on the longest remaining dependency path;
- `gate_percent`: passed blocking gates / total blocking gates;
- `pose_coverage_percent`: fixed at 100 only while P0 remains valid.

Weights: contract/implementation item `3`, serial integration `5`, exhaustive QA
`5`, checkpoint/release `2`, documentation/validator `1`. An `IN_REVIEW` item
earns zero until accepted. Reopened items immediately remove their weight.

## 6. Gate and evidence schemas

Gate schema ID: `wizardjoe-rchat-gate/v1`.

```json
{
  "schema_version": 1,
  "program_id": "RCHAT",
  "gate_id": "Q2",
  "status": "PASS|FAIL|BLOCKED",
  "git": {"branch": "string", "sha": "40-hex", "dirty": false},
  "environment": {
    "os": "string",
    "arch": "string",
    "rustc": "string",
    "cargo": "string",
    "node": "string",
    "browser": "string-or-null"
  },
  "inputs": {
    "pose_asset_sha256": "64-hex",
    "motion_graph_sha256": "64-hex-or-null",
    "policy_sha256": "64-hex-or-null",
    "browser_bundle_sha256": "64-hex-or-null"
  },
  "required_work_items": ["work-id"],
  "commands": [{
    "command": "string",
    "exit_code": 0,
    "duration_ms": 0,
    "stdout_artifact": "string-or-null",
    "stderr_artifact": "string-or-null"
  }],
  "metrics": [{
    "name": "string",
    "actual": 0,
    "operator": "eq|lte|gte",
    "threshold": 0,
    "unit": "string",
    "status": "PASS|FAIL"
  }],
  "artifacts": [{
    "kind": "string",
    "path_or_url": "string",
    "sha256": "64-hex",
    "bytes": 0,
    "retention": "pr|candidate|release|permanent"
  }],
  "failures": [],
  "skips": [],
  "review": {
    "primary": "role",
    "independent": "role",
    "reviewed_at": "RFC3339"
  },
  "rollback": {
    "sha": "40-hex",
    "profile": "legacy|shadow|chatbot-v1",
    "drill_passed": true
  }
}
```

Every-frame ledger rows additionally require:

```text
scenario_id, transition_id, clip_id, frame_index, simulation_tick,
source_event_id, command_id, state_revision, pose_id, previous_pose_id,
transition_progress, contacts, root, anchors, channel_generations,
source_frame_sha256, encoded_frame_sha256, decoded_frame_sha256,
presented_frame_sha256, png_path, quality_failures
```

The ledger has contiguous frame indexes, one PNG per row, no extra PNGs, and a
manifest hash over the canonical ordered rows.

## 7. Complete implementation DAG

```text
RCHAT-FLOW-001 pose checkpoint P0
  -> RCHAT-FLOW-010 planning checkpoint D0
      -> RCHAT-FLOW-020 registry/lock validator
      -> RCHAT-FLOW-030 shared contract freeze C0
          -> RCHAT-FLOW-040 RUNTIME contract/runtime wave --------+
          -> RCHAT-FLOW-050 MOTION graph/performance wave ---------+-> RCHAT-FLOW-070 serial core integration
          -> RCHAT-FLOW-060 CI/evidence infrastructure ------------+        -> RCHAT-FLOW-080 serial motion integration
                                                                              -> RCHAT-FLOW-090 transport/browser integration
                                                                                  -> RCHAT-FLOW-100 deterministic QA Q1
                                                                                      -> RCHAT-FLOW-110 every-frame visual QA Q2
                                                                                          -> RCHAT-FLOW-120 Chromium QA Q3
                                                                                              -> RCHAT-FLOW-130 soak/performance S1
                                                                                                  -> RCHAT-FLOW-140 clean-clone R0
                                                                                                      -> RCHAT-FLOW-150 final evidence F0-A
                                                                                                          -> RCHAT-FLOW-160 push checkpoint F0-B
                                                                                                              -> RCHAT-FLOW-170 deploy
                                                                                                                  -> RCHAT-FLOW-180 endpoint/rollback drill
                                                                                                                      -> RCHAT-FLOW-190 independent acceptance F0
```

### 7.1 Accountable ledger

| ID | Owner | Dependencies | Deliverable | Gate |
|---|---|---|---|---|
| `RCHAT-FLOW-001` | `INT/FLOW` | none | Commit/push immutable 89/50/621/20,065 pose baseline and hashes | `P0` |
| `RCHAT-FLOW-010` | `INT` | `001` | Push three-agent research/plans and coordinator synthesis | `D0` |
| `RCHAT-FLOW-020` | `FLOW` | `010` | Registry, gate, handoff, lock, and evidence validators | `C0` |
| `RCHAT-FLOW-030` | all/`INT` | `010` | Freeze shared event, state, graph, speech, replay, telemetry, browser contracts | `C0` |
| `RCHAT-FLOW-040` | `RUNTIME` | `020`,`030` | Execute accepted `RCHAT-RUN-010..100` modules and focused tests | `R1` |
| `RCHAT-FLOW-050` | `MOTION` | `020`,`030` | Execute accepted `RCHAT-ANIM-010..135` modules/assets and focused tests | `A1` |
| `RCHAT-FLOW-060` | `FLOW` | `020`,`030` | CI jobs, scope checker, evidence writers, browser harness skeleton | `Q0` |
| `RCHAT-FLOW-070` | `INT` | `040`,`060` | Serial clock/inbox/state/replay/telemetry/server-core wiring | `I1` |
| `RCHAT-FLOW-080` | `INT` | `050`,`070` | Serial director/channel/clip/playback/renderer wiring behind shadow profile | `I2` |
| `RCHAT-FLOW-090` | `INT/FLOW` | `070`,`080` | HTTP/WS acks, capabilities, held controls, reconnect, diagnostics | `T1` |
| `RCHAT-FLOW-100` | `FLOW/RUNTIME` | `090` | Full tests, replay twice, cadence, idempotency, coverage, legacy parity | `Q1` |
| `RCHAT-FLOW-110` | `FLOW/MOTION` | `100` | Screenshot every authored graph/interrupt/chatbot frame twice | `Q2` |
| `RCHAT-FLOW-120` | `FLOW` | `110` | Real Chromium scenario, console, parity, responsive, reduced-motion evidence | `Q3` |
| `RCHAT-FLOW-130` | `FLOW` | `120` | 10-minute required soak plus CI/nightly profiles and performance budget | `S1` |
| `RCHAT-FLOW-140` | `FLOW` | `130` | Clean-clone locked build and complete release matrix | `R0` |
| `RCHAT-FLOW-150` | `FLOW/INT` | `140` | Compact final manifest, artifact checksums, rollback receipt | `F0-A` |
| `RCHAT-FLOW-160` | `INT` | `150` | Commit/push exact release SHA and verify remote ref | `F0-B` |
| `RCHAT-FLOW-170` | `INT` | `160` | Trigger pinned-SHA Hetzner bridge and activate release | `F0-C` |
| `RCHAT-FLOW-180` | `INT/FLOW` | `170` | Verify public HTTPS/WS/build identity; execute rollback and re-promote drill | `F0-D` |
| `RCHAT-FLOW-190` | all | `180` | Independent scorecard, >=90% product score, all blockers 100% pass | `F0` |

## 8. Wave procedure

### Wave 0: immutable checkpoints

`RCHAT-FLOW-001` records the exact asset, manifests, stream hash, commands,
counts, branch, local SHA, remote SHA, and clean status. `RCHAT-FLOW-010` pushes
the synthesized plan before implementation. No production worktree is merged
before local and remote planning SHAs match.

### Wave 1: contracts and validators

RUNTIME and MOTION exchange Rust type definitions and fixtures. FLOW validates
field agreement, schema versions, dependency acyclicity, path ownership, and
lock state. Contract `C0` needs explicit acknowledgements from all three agents.
After `C0`, a contract change requires a decision record, version bump, affected
test update, and three new acknowledgements.

### Wave 2: parallel new modules

RUNTIME and MOTION write only new owned modules/tests/assets. FLOW builds
validators and CI. Each lane runs focused tests and returns a complete handoff.
No lane directly wires shared hotspots.

### Wave 3: serial integration

The coordinator wires in this order:

1. module exports and dependency metadata;
2. integer clock and ordered inbox;
3. orthogonal regions and legacy state projection;
4. replay and bounded telemetry;
5. chat reducer in shadow mode;
6. motion graph loader/evaluator in shadow mode;
7. clips, transition recipes, interruptions, and channel generations;
8. facial, gaze, speech, secondary, staff, wing, and effect channels;
9. controller, hub, frame source, and renderer;
10. HTTP/WebSocket adapters and browser controls.

After every step run focused tests, the full engine suite, `git diff --check`,
registry validation, and a state/API smoke. A failed step blocks all later
integration and rolls back only that step.

### Wave 4: deterministic and visual promotion

Promote in profiles:

```text
legacy -> shadow -> chatbot-v1-candidate -> chatbot-v1
```

Shadow evaluates and records decisions without changing visible frames. The
candidate profile becomes visible only after decision parity and focused visual
gates pass. `legacy` remains an emergency runtime profile until F0 and the
rollback drill pass.

### Wave 5: release

Clean clone, complete CI, final evidence manifest, push, pinned-SHA deploy,
public endpoint proof, rollback drill, re-promotion, and three-agent acceptance
occur in that order.

## 9. CI required checks

Recommended required check names:

```text
rchat-registry-and-scope
rchat-pose-tool
rchat-engine-fmt-clippy
rchat-engine-tests
rchat-browser-modules
rchat-pose-v4-integrity
rchat-chat-contracts
rchat-replay-determinism
rchat-transition-and-interrupt-quality
rchat-browser-chromium
rchat-soak-short
rchat-evidence-manifest
rchat-release-build
```

Commands:

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
WIZARD_SOAK_MODE=short cargo run --manifest-path rust/wizard_avatar_engine/Cargo.toml --locked --release --bin wizard-avatar-soak
cargo build --manifest-path rust/wizard_avatar_engine/Cargo.toml --locked --release --bin wizard-avatar-server
```

CI fails on warnings, skips in required suites, dirty generated outputs, runtime
PNG/video access, missing evidence, stale hashes, overlapping ownership,
unreleased locks, or a gate from another SHA.

## 10. Quality gates

| Gate | Required result |
|---|---|
| `P0` | 89/50/621/16/89/20,065 x2; zero failures; asset and stream hashes fixed |
| `D0` | planning committed/pushed; central registry validates |
| `C0` | all contracts and bad fixtures accepted by all three agents |
| `R1` | clock, inbox, idempotency, state, replay, speech, telemetry tests 100% |
| `A1` | 89/89 taxonomy, 50/50 WJFL, graph/clip/transition/interrupt tests 100% |
| `Q0` | CI, scope, registry, evidence validators reject deliberate bad fixtures |
| `I1/I2` | full Rust regression after each serial integration step |
| `T1` | HTTP/WS semantic parity, terminal acks, legacy binary compatibility |
| `Q1` | two full replays identical; cadence invariant; no unacked mutation |
| `Q2` | one screenshot per frame; zero breakup/topology/contact/attachment failures |
| `Q3` | Chromium scenario matrix, zero console/decode errors, 100% presented parity |
| `S1` | 10-minute mixed-state soak, bounded queues/memory, target cadence/performance |
| `R0` | clean clone and locked release build reproduce all required checks |
| `F0` | exact pushed/deployed SHA, public HTTPS/WS proof, rollback drill, >=90% score |

Hard visual thresholds:

```text
unknown/missing poses                         0
authored transition failures                 0 / 621
static quality failures                      0 / 89
runtime PNG/video/sprite reads                0
horizontal seams / vertical cracks           0
unexpected region fragments                  0
detached staff/wing/hand anchors              0
airborne planted-foot claims                 0
illegal channel writers                      0
source/decode/present hash mismatch           0
missing/extra screenshot frames               0
unhandled browser console/decode errors       0
```

Chat/runtime thresholds:

```text
simulation cadence                            exactly 60 Hz semantic time
default presentation                          24 FPS
event accepted-to-applied p95                 <= 2 simulation ticks loopback
source-frame-to-presented p95                 <= 2 presentation frames loopback
event/command without terminal ack            0
duplicate event state mutations               0
speech cancel to rest                         <= 6 simulation ticks
held-input release after keyup/blur/TTL        <= 2 ticks plus transport
queue growth                                  bounded at configured capacities
required test skips                           0
```

## 11. Real-browser protocol

Automated Chromium runs against the exact release binary on an isolated port
and covers:

1. connect, `INIT`, keyframe, adaptive delta, resync, reconnect;
2. idle, listen, think, speak, clarify, tool wait, error, celebrate,
   interrupted, and recovery states;
3. all ten feelings in full-body and close-accent use;
4. speech start/cues/cancel/end, emotion co-articulation, gaze, blink;
5. locomotion and flight while listening/speaking/interrupting;
6. action replacement, stale event, duplicate event, out-of-order event;
7. held keyboard/gamepad control, keyup, blur, visibility loss, disconnect, TTL;
8. repeat-until-Stop and Stop at a safe marker;
9. reduced-motion profile;
10. two simultaneous viewers plus one reconnecting viewer;
11. 1280x800 and 390x844 layouts with no overflow or occlusion;
12. zero console errors, decode errors, missing cells, blurred squares, or local
    pose simulation.

For sampled and gate-critical frames, browser code reports the presented frame
hash and sequence back to the harness. Evidence correlates event ID -> applied
tick -> state revision -> source frame -> encoded sequence -> decoded hash ->
presented hash -> screenshot.

## 12. Soak and performance

Profiles:

| Profile | Duration | Viewers | Use |
|---|---:|---:|---|
| `short` | 30 seconds | 4 | every PR |
| `release` | 10 minutes | 4 plus one slow/reconnecting | F0 blocker |
| `ci` | 30 minutes | 8 | scheduled candidate |
| `nightly` | 2 hours | 8 plus fault injection | non-blocking until promoted |

The release soak mixes chatbot states, speech cues, all emotion families,
actions, locomotion, flight, interruptions, duplicate/reordered/stale events,
slow clients, reconnects, and resync. It records simulation/render cadence,
queue high-water marks, memory/CPU, encoding ratios, dropped-time events,
deadline misses, resync counts, ack latency, frame latency, and hash mismatches.

## 13. Branch, push, deploy, and rollback

1. Work remains on a `codex/` branch; no push to `main` is required.
2. Coordinator integrates one accepted handoff at a time.
3. Before push, inspect workflow triggers and exact staged paths.
4. Push the release candidate and verify remote SHA with `git ls-remote`.
5. The Hetzner bridge accepts `WIZARD_SHA`, not a mutable branch head.
6. The bridge downloads/checks out that SHA, verifies the release manifest,
   builds or verifies the binary checksum, and refuses a dirty/mismatched tree.
7. Remote activation creates `/opt/wizardjoe-avatar/releases/<sha>`, records
   `previous`, starts candidate, verifies internal state/WS, then switches
   `current` atomically.
8. Public verification checks HTTPS page, state, capabilities/build identity,
   WebSocket frame decode, semantic command/ack, and a screenshot hash.
9. Rollback switches `current` to `previous`, restarts, verifies endpoint and
   build identity, then re-promotes the candidate and verifies again.
10. Commit a compact deployment receipt containing release SHA, binary SHA,
    asset/graph/policy hashes, workflow run URL, endpoint, timestamps, previous
    SHA, and rollback/re-promotion results.

Deployment must not proceed if the bridge only ran `cargo test --lib`, if the
pose tool or integration tests were skipped, or if release evidence came from a
different SHA.

## 14. Failure and rollback rules

On item failure:

1. stop dependent work;
2. set item `FAILED` with exact command, first failing test/frame/tick, and
   artifact hash;
3. preserve evidence before changing code;
4. release held locks through the coordinator;
5. restore only the item rollback SHA/profile;
6. rerun the smallest focused gate, then every previously passed downstream
   gate affected by the change;
7. mark `READY` only after a new base SHA is recorded.

Automatic rollback triggers:

- any P0 count/hash/quality regression;
- nondeterministic replay;
- unacknowledged or duplicate mutation;
- illegal pose edge or channel writer;
- breakup, seam, crack, fragment, contact, attachment, or frame parity failure;
- browser console/decode error in a required scenario;
- unbounded queue/memory growth;
- runtime reference-image access;
- evidence/pushed/deployed SHA mismatch;
- public endpoint fails state, WebSocket, command, or build identity checks.

Rollback never edits the pose v4 asset to hide a chatbot defect and never
substitutes Python, PNGs, videos, or browser-side animation.

## 15. Per-item handoff

```text
handoff_schema: wizardjoe-rchat-handoff/v1
handoff_id:
work_item:
owner:
status: HANDOFF_READY
base_sha:
result_sha:
owned_files_changed:
shared_files_requested:
locks_required:
interfaces_added_or_changed:
contract_hashes:
tests_run:
test_results:
metrics:
evidence_paths_and_sha256:
browser_or_visual_rows:
known_risks:
rollback_sha:
rollback_profile:
rollback_verified:
coordinator_wiring_requested:
next_dependencies_unblocked:
reviewer_required:
```

The coordinator rejects handoffs with unowned files, missing hashes, stale base
SHA, omitted failures/skips, ambiguous rollback, or evidence generated from a
different commit.

## 16. Definition of done

The Rust chatbot visualizer is complete only when:

- all `RCHAT-FLOW-001..190` work items are `ACCEPTED`;
- peer `RCHAT-RUN` and `RCHAT-ANIM` required items are accepted and linked;
- P0 remains exactly 89/50/621/16/89/20,065 x2 with zero failures;
- event, command, state, speech, graph, replay, telemetry, and browser contracts
  are frozen and versioned;
- every runtime geometry is classified and reachable through an approved
  chatbot, locomotion, flight, action, or showcase path;
- all authored transitions and interruption paths pass screenshot-per-frame
  quality checks twice deterministically;
- Chromium proves every required chatbot state, control lifecycle, reconnect,
  reduced-motion, and frame-parity scenario;
- the release soak and performance budgets pass without unbounded growth;
- clean clone reproduces all required checks with locked dependencies;
- compact evidence and heavy artifact receipts identify the exact release SHA;
- that exact pushed SHA is live at the public endpoint;
- rollback and re-promotion are exercised successfully;
- three-agent independent review gives at least 90% overall and no structural,
  safety, determinism, visual, browser, scope, or deployment blocker remains.
