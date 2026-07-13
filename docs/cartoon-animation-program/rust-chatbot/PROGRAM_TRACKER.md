# Rust Chatbot Animation Program Tracker

Last coordinator update: 2026-07-13

## Program status

| Phase | Status | Gate/result |
|---|---|---|
| 50-pose integration | COMPLETE | 89/50/621/16; 20,065 frames x2; zero failures |
| Three-agent research | COMPLETE | RUNTIME, MOTION, FLOW reports saved |
| Three-agent planning | COMPLETE | Detailed lane plans saved |
| Coordinator synthesis | COMPLETE | Three agents accepted after iterative cross-review |
| Pose checkpoint | COMPLETE | Pushed `ca52b8023d5021e3a9bb14753961e8f7007f5aef` |
| Planning checkpoint | COMPLETE | Pushed `50948b907ad35ec8ca604d6c39a63b4317ac3da7` |
| Rust branch | ACTIVE | `codex/rust-chatbot-animation-engine` in `jedisherpa/wizardjoeavatar` |
| Contract implementation | IN_REVIEW | Shared modules exported; 31 engine contract tests and 19 workflow/release tests pass |
| Runtime and motion engines | PLANNED | Blocked on C0 |
| Serial integration | PLANNED | Blocked on engine handoffs |
| Exhaustive QA | PLANNED | Blocked on integrated profile |
| Publish and deployment | PLANNED | Blocked on F0 |

## Agent ledger

| Role | Agent | Research | Planning | Next accountability |
|---|---|---|---|---|
| RUNTIME | Epicurus (`019f5c84-aca4-7953-b8ac-23a395e7268b`) | COMPLETE | COMPLETE | Contract handoff complete; final C0 review accepted |
| MOTION | Singer (`019f5c84-b193-7f70-83ff-e0c7e33edd51`) | COMPLETE | COMPLETE | Motion graph and speech quantizer in final C0 review |
| FLOW | Lagrange (`019f5c84-b630-7053-b560-cab55fb3ba11`) | COMPLETE | COMPLETE | Validator handoff complete; receipt review pending commit SHA |
| INT | Coordinator | COMPLETE | IN_REVIEW | Exported shared modules; preparing Rust-branch checkpoint |

## Pose prerequisite receipt

- Runtime geometries: 89.
- Unique WJFL geometries: 50.
- Authored directed transitions: 621.
- Rust clips: 16.
- Static evidence: 89 frames, zero failures.
- Animation evidence: 20,065 frames per pass, 19,427 checked pairs,
  zero failures.
- Deterministic stream hash:
  `a2daab4ce0ffee0f37683c9a0f4b2ef3dea96477f7252cff9877d426953833d5`.
- Adaptive decode parity: pass.
- Browser presentation parity: pass.

## Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-07-13 | Complete all 50 pose integrations before chatbot planning implementation | User-required ordering; avoids designing against an incomplete library |
| 2026-07-13 | Rust is the sole production authority | The current Rust system already owns geometry, runtime, renderer, codec, server, and evidence |
| 2026-07-13 | Copied Python documents are historical for this branch | Their language and port restrictions conflict with the requested Rust strategy |
| 2026-07-13 | Chat ingress cannot select raw poses | Semantic intent keeps visual direction coherent, testable, and portable |
| 2026-07-13 | Three lanes with coordinator-only hotspots | Preserves accountability and avoids conflicting runtime authority |
| 2026-07-13 | Structural gates require 100%; product score requires >=90% | Quality averages must never hide breakup, nondeterminism, or transport failure |
| 2026-07-13 | Runtime PNG reuse remains prohibited | The accepted character is procedural colored-cell geometry, not a reused image |

## Current blockers

1. `RCHAT-FLOW-020` must materially verify Git objects, evidence bytes, hashes,
   and scoped diffs instead of validating only field shapes.
2. Gate command validation must match `wizardjoe-rchat-gate/v1` exactly.
3. The corrective implementation commit must contain C0 evidence under the
   explicit registry, library, and evidence ownership recorded in the registry.

The semantic contract itself has passed RUNTIME review; C0 remains open until
these accountability blockers are fixed and rerun from an immutable commit.

## Next promotion

1. Push the current Rust-only C0 checkpoint to
   `codex/rust-chatbot-animation-engine`.
2. Record its immutable result SHA, accept reviewed handoffs, and run the
   registry validator again.
3. Promote `RCHAT-ANIM-019` and aggregate `RCHAT-FLOW-030` only after the
   exact dependency receipts are accepted.
