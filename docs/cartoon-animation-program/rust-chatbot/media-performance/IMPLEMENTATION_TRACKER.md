# Media Performance Implementation Tracker

Statuses mirror the FLOW registry: `PLANNED`, `READY`, `IN_PROGRESS`,
`HANDOFF_READY`, `IN_REVIEW`, `ACCEPTED`, `BLOCKED`, `FAILED`, `REOPENED`.

An item is `ACCEPTED` only when its implementation commit, independent reviewer,
exact commands, hashed evidence, rollback point, and acceptance checks are recorded.

The Wizard registry is the cross-repository status authority. Every Prism work item
must publish an immutable receipt back into its `artifacts` array with repository,
branch/ref, base SHA, result SHA, changed-path allowlist, command receipts, and evidence
hashes. A Wizard `integration_head` never stands in for a Prism SHA.

## Program Gates

Gate status is the registry's blocking vocabulary: `PASS` or `BLOCKED`. Work-item
readiness remains visible in the work-package table below.

| Gate | Requirement | Status |
|---|---|---|
| MP0 | Independent code-grounded research and synthesis | BLOCKED |
| MP1 | Typed contracts and capability manifest | BLOCKED |
| MP2 | Media identity, player session, and connector | BLOCKED |
| MP3 | Transcript and alignment pipeline | BLOCKED |
| MP4 | Music analysis and deterministic compiler | BLOCKED |
| MP5 | Runtime scheduler and animation integration | BLOCKED |
| MP6 | Whiz governance and performance editor | BLOCKED |
| MP7 | Packaged end-to-end acceptance | BLOCKED |

## Work Packages

| ID | Owner | Deliverable | Depends | Evidence Gate | Status |
|---|---|---|---|---|---|
| MP-RSCH-000 | Architecture | Code-grounded two-repository research, decisions, tracker, and acceptance contract | none | Two independent reviews plus FLOW receipt | IN_REVIEW |
| MP-WIZ-005 | Wizard Runtime | Promote `RCHAT-RUN-110` typed inbox/reducer/ACK path with legacy compatibility | RCHAT-RUN-110 | Lifecycle, idempotency, retry, replay tests | PLANNED |
| MP-WIZ-010 | Wizard Runtime | Generated capability manifest wire V2, endpoint, exact-set tests | RCHAT-ANIM-050 | Complete canonical fixture, nonzero frozen hash, exact loaded-registry equality, no planned IDs | IN_REVIEW |
| MP-WIZ-020 | Wizard Runtime | `MediaProtocolV1` typed command variants through existing inbox | MP-WIZ-005 | Canonical full-transcript fixture, every-variant roundtrip, invalid/stale/duplicate/property tests | PLANNED |
| MP-WIZ-030 | Wizard Runtime | `PerformanceScoreV1` and strict validator | MP-WIZ-010 | Golden roundtrip/hash and real nonzero capability-manifest binding tests | BLOCKED |
| MP-WIZ-040 | Wizard Runtime | Bounded deterministic cue scheduler and timeline reducer | MP-WIZ-020,030 | Seek/rate/reconnect replay matrix | PLANNED |
| MP-WIZ-050 | Animation | Layered performance execution: locomotion, gesture, gaze, face, speech, stillness | MP-WIZ-040 | Every-frame ownership/topology evidence | PLANNED |
| MP-WIZ-060 | Animation | Authored audiobook performance phrases and transitions | MP-WIZ-050 | Accent/anticipation/recovery visual review | PLANNED |
| MP-WIZ-070 | Animation | Authored dance phrases, contacts, section transitions, reduced motion | MP-WIZ-050 | Beat/bar/phrase sync and foot-slide checks | PLANNED |
| MP-PRISM-010 | Prism Runtime | Durable media identity/provenance/chapter model and migration | MP0 | Roundtrip/migration/privacy tests | PLANNED |
| MP-PRISM-020 | Prism Runtime | File-backed range streaming and supported-format probe | MP-PRISM-010 | Long-file memory/range tests | PLANNED |
| MP-PRISM-030 | Prism Player | Media-session controller and browser adapter | MP-PRISM-010 | Browser event/seek/rate/chapter tests | PLANNED |
| MP-PRISM-032 | Prism Player | Shared audio/video media-element adapter and explicit video player surface | MP-PRISM-030 | Audio/video parity, buffering, seek, ended tests | PLANNED |
| MP-PRISM-034 | Prism Player | Character, mode, intensity, reduced-motion, rate, seek, chapter, and track controls | MP-PRISM-030, MP-WIZ-020 | Keyboard/focus/browser/desktop tests | PLANNED |
| MP-PRISM-040 | Connector | Correlated connector, retry, snapshot, health, compatibility | MP-WIZ-020, MP-PRISM-030 | Loss/duplicate/reorder/reconnect tests | PLANNED |
| MP-PREP-010 | Preprocess | Resumable job/checkpoint/store framework | MP-PRISM-010 | Cancel/resume/atomic-publish tests | PLANNED |
| MP-PREP-012 | Frontend | Media/transcript import, job progress, cancellation, retry, diagnostics, and error UI | MP-PREP-010 | Import and failure-state browser tests | PLANNED |
| MP-PREP-020 | Transcript | Provided transcript parse and validation | MP-PREP-010 | TXT/MD/SRT/VTT/JSON fixtures | PLANNED |
| MP-PREP-030 | Transcript | Inventory and invoke existing server whisper-cli through an opt-in Rust long-form runner | MP-PREP-010 | Inventory/version/hash, TLS/credential/permission negatives, no-runtime-SSH proof, immediate deletion and one-hour janitor ledgers, content-free audit scan, chunk overlap/cancel/resume fixtures | PLANNED |
| MP-PREP-040 | Transcript | Verification and hierarchical alignment | MP-PREP-020,030 | Coverage/drift/confidence reports | PLANNED |
| MP-PREP-050 | Narrative | Deterministic features plus governed structured LLM passes | MP-PREP-040 | Schema/retry/provider/audit tests | PLANNED |
| MP-PREP-060 | Music | PCM decode, DSP features, beat/section candidates | MP-PREP-010 | Synthetic/golden/reference corpus | PLANNED |
| MP-PREP-070 | Compiler | Capability-constrained audiobook and music compilers | MP-PREP-050,060, MP-WIZ-030 | Stable score hash and critique pass | PLANNED |
| MP-WHIZ-010 | Governance | Stored canonical URL and governed `source.open` permit | MP-PRISM-010 | Scheme/payload-hash/audit tests | PLANNED |
| MP-WHIZ-020 | Frontend | Visible Whiz button with unavailable state | MP-WHIZ-010 | Browser and desktop user-gesture tests | PLANNED |
| MP-EDIT-010 | Tools | Performance score timeline/editor with immutable override layer | MP-PREP-070 | Version/undo/export/revalidate tests | PLANNED |
| MP-QA-010 | QA | Exhaustive cue/frame/sync/reconnect evidence runner | MP-WIZ-040 | Deterministic ledger and manifest | PLANNED |
| MP-QA-020 | QA | Long audiobook/music/video soak and packaged-app verification | MP-QA-010, MP-WIZ-060, MP-WIZ-070, MP-PRISM-020, MP-PRISM-032, MP-PRISM-034, MP-PRISM-040, MP-PREP-012, MP-WHIZ-020, MP-EDIT-010 | Measurements and recordings | PLANNED |

This table is a readable view. Matching `RCHAT-MEDIA-*` entries in
`../registry.json` are the status authority and carry SHA/evidence receipts.

### Current Rust Contract Receipt

- Capability candidate: `73f733a03599af786fc92b1e5ec0826e4ab5a23e` with 18 focused tests passing.
- PerformanceScore candidate: `43d80b902dcc51d501ff72c8c2a8b7f9727ebcf4` with 10 focused tests passing.
- Combined RUN-050 integration: `d405eb1695e6d4a66a72806b2484351d836f03e3`; `cargo test --locked` passed, including the 998.70-second all-neighbor transition sweep and 249.53-second WJFL every-frame/loop-boundary sweep.
- Exact-commit independent acceptance is still outstanding. Earlier review findings were repaired, but reviewer capacity was exhausted before two fresh final-SHA approvals could be recorded. MP-WIZ-010 therefore remains `IN_REVIEW`, and dependency-gated MP-WIZ-030 remains `BLOCKED` despite its completed implementation and focused verification.

## Required Review Pairings

- Runtime contracts: Prism flow reviewer plus Wizard animation reviewer.
- Animation implementation: Wizard runtime reviewer plus independent visual reviewer.
- Preprocessing: Rust systems reviewer plus domain-specific transcript or DSP reviewer.
- Whiz: Prism governance reviewer plus security reviewer.
- Final gate: independent operator reproduces from a clean clone and packaged apps.

## Promotion Order

1. Finish accepted chat runtime and locomotion foundations.
2. Publish capability truth before compiling scores.
3. Freeze protocol and score fixtures before connecting UI.
4. Implement Prism media identity/session and Wizard scheduler in parallel.
5. Add preprocessing behind offline CLI contracts.
6. Author performance content only against published capabilities.
7. Add editor and Whiz after storage/governance contracts exist.
8. Run exhaustive evidence and packaged release gates.

## Accountability Receipt Template

```text
ID:
owner:
reviewers:
repository_receipts:
  - repository:
    branch_or_ref:
    base_sha:
    result_sha:
    changed_paths:
commands:
tests_passed:
evidence_sha256:
deterministic_replay_hash:
performance_measurements:
known_limits:
rollback_sha/profile:
review_verdicts:
```
