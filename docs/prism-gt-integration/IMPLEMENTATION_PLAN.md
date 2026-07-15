# Implementation Plan

Interface locks

**Dependency-ordered workstreams.**

**Workstream 1: Branch authority stabilization.** Task: Add branch-specific "Current authority" note reconciling Python `8765` vs Rust `8787` citing supersession rule. Likely files: `README.md`, `docs/cartoon-animation-program/rust-chatbot/README.md`. Dependencies: none. Interface lock: authority document. Tests: documentation review. Completion evidence: signed note at analyzed commit. Human approval: owner signature.

**Workstream 2: rchat gate records.** Task: Generate and commit rchat gate records for `e3c5c5d…` using gate schema and validator. Likely files: `schemas/rchat/gate-v1.schema.json`, `tools/rchat/`. Dependencies: Workstream 1. Interface lock: gate schema. Tests: validator run. Completion evidence: committed gate records with SHA match. Human approval: none.

**Workstream 3: Deployment receipt.** Task: Record whether analyzed commit is deployed; label public endpoint as target. Likely files: `docs/HETZNER_DEPLOYMENT.md`. Dependencies: Workstream 2. Interface lock: deployment schema. Tests: SHA verification. Completion evidence: immutable receipt with pushed/built/deployed/endpoint SHA. Human approval: owner decision.

**Workstream 4: Live RCHAT browser capture adapter.** Task: Implement or attach live capture adapter to `rust/wizard_avatar_engine/web/tests/rchat/browser_harness.mjs`; record every-frame evidence. Dependencies: Workstream 3. Interface lock: harness contract. Tests: every-frame capture test. Completion evidence: capture PASS artifact. Human approval: none.

**Workstream 5: Public route auth/gateway.** Task: Document authentication/gateway expectations for `/api/avatar/wizard/*` and WebSocket before public exposure. Dependencies: Workstream 4. Interface lock: auth contract. Tests: security review. Completion evidence: documented policy. Human approval: security sign-off.

**Workstream 6: CDISS/constitutional boundary.** Task: Explicitly document CDISS/constitutional/governed-action boundary. Dependencies: Workstream 5. Interface lock: governance contract. Tests: schema validation. Completion evidence: boundary note. Human approval: governance owner.

**Workstream 7: Media-performance status.** Task: Mark media-performance program status outside implemented features. Dependencies: Workstream 6. Interface lock: program status. Tests: documentation review. Completion evidence: updated README. Human approval: none.

**Migration.** From Python lineage to Rust authority on analyzed branch only. Rollback: disable scheduler flag or revert to prior commit. Completion evidence: all gates passed with rollback drill.

**Human approval points.** Owner decision on C-001 authority conflict; selection of canonical Telegram identity; approval to enable live embedder health output; approval to gate unsigned desktop builds as test-only.
