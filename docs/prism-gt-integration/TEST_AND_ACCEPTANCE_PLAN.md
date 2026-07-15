# Test and Acceptance Plan

**Unit tests.** `cargo test` (90 tests reported PASS in verification), `cargo clippy --all-targets -- -D warnings`, `cargo fmt --check`. Python: `python3 -m unittest discover -s tests`. Evidence: `docs/animation-quality/08_FINAL_INDEPENDENT_VERIFICATION.md:00118-00143`.

**Contract tests.** rchat registry/gate/scope validation, evidence writer/validator. Schema-2 ledger with 7,173 rows, zero failures. Location: `.github/workflows/rust-chatbot-ci.yml:00050-00075`, `00126-00148`; `schemas/rchat/`.

**Integration tests.** Focused motion/contract tests, Node tests for browser modules. CI jobs: `rchat-motion`, `rchat-browser`.

**End-to-end tests.** Soak runner `wizard-avatar-soak`. Browser harness foundation with Playwright availability probe (explicitly non-PASS until live adapter). Evidence: `rust/wizard_avatar_engine/web/tests/rchat/README.md:00001-00027`.

**Failure tests.** Frame desync triggers resync. Unknown actions, out-of-bounds coordinates, stale commands rejected. Resync and reduced-motion paths.

**Security tests.** Proposed — interface lock required. Route auth, rate limiting, origin policy not inspectable from omitted source.

**Governance tests.** Prism signal schema validation (`wizard_avatar/definitions/prism_animation_signal.schema.json`). Content-free advisory check. CDISS authority invariant test (proposed).

**Accessibility tests.** Stop/reduced-motion controls required (`docs/cartoon-animation-program/rust-chatbot/README.md:00070-00082`). Keyboard navigation and screen-reader labels on active UI.

**Release tests.** Workflow records command floors, CI checks, evidence artifacts, browser acceptance, deployment identity verification, rollback (`docs/cartoon-animation-program/rust-chatbot/WORKFLOW.md:00083-00119`). No F0 receipt for analyzed commit.

**Real-runtime acceptance evidence.** Retained demo (1,023 frames), performance (targets met), snapshots (30 outputs), independent verification (zero quality failures). Live every-frame capture not claimed. Acceptance requires digest received, schedule persists, rollback within 60 seconds.
