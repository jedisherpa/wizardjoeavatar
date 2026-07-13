# Wizard Joe Rust Chatbot Animation Program

Status: active implementation program

Production authority: `rust/wizard_avatar_engine`

Offline asset authority: `rust/wizard_avatar_pose_tool`

Local acceptance endpoint: `http://127.0.0.1:8787/`

Public release target: `https://wizardjoe.5.78.137.112.sslip.io/`

## Purpose

This program turns Wizard Joe from a pose-capable avatar into a first-class
chatbot visualizer. A chatbot or TTS system sends typed semantic lifecycle
events. The Rust runtime owns timing, conversational performance, gesture and
emotion selection, speech mouth timing, interruption, pose transitions,
rendering, ASCILINE encoding, transport, replay, and evidence.

The runtime renders procedural colored cells from the embedded Rust pose asset.
It never loads, crops, composites, or displays the reference PNGs.

## Authority

The files in this directory supersede the copied program's Python-only rules,
port-8765 acceptance target, Rust exclusions, and Python work IDs for this
branch. The copied documents remain historical research. Their useful
first-principles requirements are retained here in Rust form: one fixed-tick
authority, typed contracts, orthogonal animation channels, deterministic
replay, one-writer integration, exhaustive frame evidence, browser parity,
rollback, and exact deployed-SHA proof.

## Frozen pose baseline

P0 is accepted at pushed commit
`ca52b8023d5021e3a9bb14753961e8f7007f5aef`:

| Property | Accepted value |
|---|---:|
| Runtime geometries | 89 |
| Newly integrated WJFL geometries | 50 |
| Imported catalog records | 80 |
| Imported geometries / aliases | 79 / 1 |
| Rust clips | 16 |
| Authored directed transitions | 621 |
| Static frames | 89 |
| Animation frames per deterministic pass | 20,065 |
| Deterministic passes | 2 identical |
| Structural failures | 0 |
| Decode and presentation parity | 100% |

The deterministic animation stream SHA-256 is
`a2daab4ce0ffee0f37683c9a0f4b2ef3dea96477f7252cff9877d426953833d5`.

## Program documents

- `IMPLEMENTATION_PLAN.md`: coordinator-owned architecture, DAG, gates, and
  definition of done.
- `WORKFLOW.md`: multi-agent execution, locks, handoffs, testing, and release.
- `PROGRAM_TRACKER.md`: human-readable current state and decision log.
- `registry.json`: machine-readable work-item and gate state.
- `research/01-rust-runtime-chatbot.md`: runtime research.
- `research/02-chat-animation-motion.md`: animation and motion research.
- `research/03-rust-delivery-audit.md`: delivery and accountability audit.
- `planning/01-rust-runtime-plan.md`: detailed runtime contracts and work.
- `planning/02-chat-animation-plan.md`: detailed motion, QA, and promotion work.
- `planning/03-rust-workflow-plan.md`: detailed delivery workflow.

## Non-negotiable completion rules

1. Rust is the sole production animation and delivery authority.
2. Chat ingress expresses semantic intent and cannot select production pose IDs.
3. Simulation is deterministic at 60 Hz; presentation never advances state.
4. Speech, mouth, gaze, blink, emotion, body, staff, wings, and effects have
   explicit ownership and coexist without resetting unrelated channels.
5. Every loop boundary, interruption, recovery, and graph edge is verified.
6. Every acceptance frame is numbered, hashed, and represented in a ledger.
7. Structural, safety, decode, and presentation gates require 100% pass.
8. Independent product acceptance must score at least 90%.
9. The pushed, built, deployed, and endpoint-reported commit identities agree.
10. Stop and reduced-motion behavior are always available.
