# WizardJoeAvatar Repository Documentation

**Purpose.** `jedisherpa/wizardjoeavatar` supplies server-authoritative procedural ASCII animation engines for the Wizard Joe broadcast avatar character. The system generates row-major `[char, R, G, B]` cell framebuffers, applies adaptive encoding (RAW, ZLIB, DELTA, RLE_FULL), and streams them over WebSocket for browser Canvas rendering. It supports semantic commands for movement, pose, gesture, speech, and reset while maintaining deterministic 60 Hz simulation on the analyzed branch.

**Current ecosystem role.** On the analyzed `codex/rust-chatbot-animation-engine` branch at commit `e3c5c5d8fa39b16a2da6a48215a28dc84eee38e5`, the repository provides branch-local Rust (`rust/wizard_avatar_engine`) and Python (`wizard_avatar`) engines plus offline pose tooling. It is registered as `active_multi_branch_implementation` under category `procedural broadcast avatar` with rationale "Specification plus branch-local Rust and Python engines for server-authoritative procedural ASCII animation, TTS mouth motion, semantic actions, transport, resync, encoding, and tests." The default `main` branch at `59f17bb2e534e987242b5c7ae2b47f42f95c8792` remains specification-oriented. No verified deployment receipt or release tag exists for the analyzed commit.

**Target ecosystem role.** The target role is a reusable character visualizer supplying the animation frame source contract to `jedisherpa/joe-newsroom` for segment cues while preserving content-free Prism animation signals that grant no movement, execution, or world authority (`wizard_avatar/definitions/prism_animation_signal.schema.json:00003-00006`). Integration occurs only through versioned contracts tested at frozen commits; no shared runtime state or governance bypass is introduced.

**Exact analyzed production baseline.** Production branch `codex/rust-chatbot-animation-engine` at commit `e3c5c5d8fa39b16a2da6a48215a28dc84eee38e5`. The default `main` branch at `59f17bb2e534e987242b5c7ae2b47f42f95c8792` remains specification-oriented and is not the frozen implementation baseline. Registry scope `in_scope`. Central integration repository reference: https://github.com/jedisherpa/prism-gt-broadcast-integration.

**Document index.**
- `CURRENT_STATE.md` — implemented, partial, and planned behavior with concrete file citations.
- `ROLE_IN_ECOSYSTEM.md` — responsibilities, boundaries, and dependencies.
- `TARGET_ARCHITECTURE.md` — justified target components and data flows.
- `INTEGRATION_CONTRACTS.md` — APIs, schemas, and governance rules.
- `IMPLEMENTATION_PLAN.md` — dependency-ordered workstreams.
- `TEST_AND_ACCEPTANCE_PLAN.md` — matrices and evidence requirements.
- `RISKS_AND_OPEN_QUESTIONS.md` — technical, security, and governance gaps.
- `AGENT_HANDOFF.md` — operating rules and done conditions.
- `implementation-manifest.yaml` — machine-readable summary.

**Freshness and update policy.** All claims are anchored to the frozen repository report, `discovery/production-sources.yml`, `discovery/relationship-graph.md`, and `discovery/contradiction-log.md`. Documentation must reference exact commit hashes and file symbols. Any change to a frozen commit or new contract requires re-verification against Rank 1–4 evidence before update. Stale documents receive a "historical" label. This suite is evidence-first and does not override canonical governance sources, CDISS, or security policy.
