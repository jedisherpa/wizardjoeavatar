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
| Contract implementation | COMPLETE | C0 PASS at `1775941e76c2bec0f54f44349d9b6f304d2bce1b`; 29 contract, 3 release-registry, and 30 workflow-validator tests pass |
| Runtime and motion engines | IN_PROGRESS | `RCHAT-RUN-020` and `RCHAT-ANIM-020..030` accepted; integer hub wiring verified at `e2b0cd7` |
| Serial integration | PLANNED | Blocked on engine handoffs |
| QA foundation | COMPLETE | Q0 PASS at `ea0f3d7c0ae4202e565feb4b811011473862dfe2`; evidence writer, scope checker, CI, and honest browser harness |
| Exhaustive QA | PLANNED | Per-frame live capture remains blocked on the integrated profile |
| Publish and deployment | PLANNED | Blocked on F0 |

## Agent ledger

| Role | Agent | Research | Planning | Next accountability |
|---|---|---|---|---|
| RUNTIME | Epicurus (`019f5c84-aca4-7953-b8ac-23a395e7268b`) | COMPLETE | COMPLETE | `RCHAT-RUN-020` accepted at `10cef30`; next owner unit is ordered inbox/idempotency |
| MOTION | Singer (`019f5c84-b193-7f70-83ff-e0c7e33edd51`) | COMPLETE | COMPLETE | `RCHAT-ANIM-020..030` accepted at `c43257a`; next owner unit is deterministic clip evaluation |
| FLOW | Lagrange (`019f5c84-b630-7053-b560-cab55fb3ba11`) | COMPLETE | COMPLETE | `RCHAT-FLOW-060` accepted; Q0 passed with 39 validator, 7 release, and 22 browser contract tests |
| INT | Coordinator | COMPLETE | COMPLETE | Integer clock wired into production hub at `e2b0cd7`; 36 focused integration tests pass |

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
| 2026-07-13 | C0 accepted only after clean-candidate and rollback builds | The pushed result and its rollback SHA both compile independently of the dirty coordinator worktree |
| 2026-07-13 | Browser tooling cannot manufacture a pass | Missing Chromium is `SKIP/77` or `FAIL/2`; live capture remains required at the later QA gate |
| 2026-07-13 | Curated pose contact sheets are committed evidence | Fresh Rust checkouts must pass source-presence and hash validation without local-only files |

## Current blockers

None for C0 or Q0. The material registry validator now checks Git objects, evidence
bytes and hashes, exact gate commands, and aggregate changed-path ownership.

The clean candidate at `1775941e76c2bec0f54f44349d9b6f304d2bce1b`
passed formatting, clippy, 62 focused tests, the all-target compile check, and
the live material registry audit. The rollback candidate at
`988b2315caaafff6a8db66270339123368c1cb76` also passed the all-target compile
check from a detached clean worktree.

R1 and A1 remain open until their complete required-child sets are implemented,
reviewed, and verified. Q0 supplies the harness for those later gates but does
not claim that live per-frame browser capture has occurred.

## Next promotion

1. Commit and push the accepted RUN-020 and ANIM-020..030 receipts without
   staging unrelated Python or legacy work.
2. Start `RCHAT-RUN-030` ordered inbox/idempotency and `RCHAT-ANIM-040`
   deterministic clip evaluation in parallel.
3. Connect the Q0 evidence writer to real Rust source/decode/presentation frames
   before any browser capture can be promoted from foundation status.
