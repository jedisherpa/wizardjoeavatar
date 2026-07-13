# Cartoon Character Animation Program

This directory is the durable execution record for turning WizardJoe's integrated pose library into a continuously animated, remotely controllable cartoon character.

Program date: 2026-07-12

Baseline branch: `codex/build-repeatable-avatar-animation`

Baseline production library: 39 generated poses on the ASCILINE Python server at `http://127.0.0.1:8765/`.

Production architecture rule: the Python controller, direct-cell renderer, FastAPI delivery system, WebSocket stream, and browser client are authoritative. Rust is a historical side-track and must not become a production dependency or acceptance gate.

## Required sequence

1. Four role-specific agents inspect the current code and research current primary sources.
2. Each agent saves an attributed report under `research/`.
3. The same four agents reconvene and save role-specific planning contributions under `planning/`.
4. The coordinator synthesizes the contributions into `IMPLEMENTATION_PLAN.md` and `WORKFLOW.md`.
5. Research and planning are committed and pushed as a checkpoint before production implementation begins.
6. Implementation work is assigned through the program ledger with disjoint ownership and explicit gates.
7. Completion requires automated tests, browser evidence, remote-control evidence, and deterministic runtime evidence.

## Roles

| Role ID | Perspective | Research output | Planning output |
|---|---|---|---|
| `FPSE` | First-principles software engineer | `research/01-first-principles-software.md` | `planning/01-first-principles-plan.md` |
| `ANIM` | Game animation and motion expert | `research/02-game-animation-motion.md` | `planning/02-animation-plan.md` |
| `RUST` | Rust expert performing containment and Python-translation audit | `research/03-rust-runtime.md` | `planning/03-rust-plan.md` |
| `PLAN` | Project planning and multi-agent workflow expert | `research/04-project-delivery.md` | `planning/04-workflow-plan.md` |
| `PRSM` | Prism GT Influence Integrated runtime/CDISS signal analyst | `research/05-prism-runtime-signals.md` | Signal report feeds the integrated plan |
| `PERS` | Persona, retrieval, memory, thread, and governance signal analyst | `research/06-persona-memory-governance-signals.md` | Signal report feeds the integrated plan |

## Truth surfaces

- `PROGRAM_TRACKER.md`: coordinator-owned status ledger.
- `registry.json`: machine-readable role, phase, ownership, and gate state.
- `research/`: immutable first-wave reports after the planning checkpoint is pushed.
- `planning/`: second-wave contributions from the same four agents.
- `IMPLEMENTATION_PLAN.md`: integrated technical plan and acceptance contract.
- `WORKFLOW.md`: execution DAG, ownership rules, checkpoints, and commands.
- `evidence/cartoon-animation-program/`: runtime captures and machine-readable verification results.

## Delivery boundary

- Production code changes must stay in `wizard_avatar/`, `web/avatar/`, Python tests, schemas, tools, and relevant documentation.
- The live acceptance target is the Python service on port 8765.
- Rust code is not included in the implementation workflow. The Rust role may identify generally useful ideas, but the plan must translate them into idiomatic Python designs and tests.
- Existing untracked Rust work is not part of the planning checkpoint or production delivery.
