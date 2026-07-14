# Wizard Joe Companion Program Tracker

Owner: lead coordinator
Started: 2026-07-14
Status values: `pending`, `in_progress`, `blocked`, `complete`, `verified`

This is the canonical accountability record for productizing the Python Wizard Joe runtime as a standalone macOS companion for Prism GT. A phase is not complete until its source, tests, runtime evidence, recovery procedure, and documentation are present.

## Current Objective

Deliver a user-installable macOS application that owns the Wizard runtime lifecycle, presents a polished native-window experience, connects locally to Prism GT in either launch order, preserves audible playback, animates persona speech reliably, and exposes clear status and recovery without requiring a terminal, port, token, browser URL, or manual LaunchAgent operation.

## Preservation Baseline

| Item | Frozen state |
| --- | --- |
| Python repository | `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar-python` |
| Python branch / HEAD | `codex/audiobook-performance-engine` / `408825ae75e395cd0761d0f17b9636a40559263a` |
| Python working tree | Clean before companion documentation |
| Prism repository | `/Users/paul/Documents/Codex/2026-06-28/jedisherpa-prism-geometry-talk-https-github/work/prism-geometry-talk-current` |
| Prism branch / HEAD | `codex/wizardjoe-media-connector` / `59106015fe22b224df350ddd28dc2fd487132681` |
| Preserved Prism work | Modified `index.jsx`, modified `musicMotion.js`, untracked `musicMotion.test.js` |
| Existing Wizard runtime | LaunchAgent `com.jedisherpa.wizardjoeavatar`, PID 59002 at discovery, loopback `127.0.0.1:8765` |
| Existing Prism app | `/Applications/Prism GT.app`, bundle `com.jedisherpa.prismgeometrytalk`, version `0.1.0`, ad-hoc signed |
| Preserved Prism backup | `/Applications/Prism GT.pre-wizard-connector.app` |

Do not delete, replace, move, rename, or reconfigure the preserved applications or LaunchAgent until an isolated companion artifact passes its acceptance gates.

## Phase Ledger

| Phase | Workstream | Owner | Status | Exit evidence |
| --- | --- | --- | --- | --- |
| 0 | Authority, repository, and live-environment discovery | Lead + runtime investigator | verified | Current-state audit, instruction map, preserved dirty work, live process/app inventory, baseline checks |
| 1 | Independent architecture, integration, UX, and release review | Five specialist reviewers | complete | Independent findings recorded in current-state audit and ADR |
| 2 | Product specification and interface lock | Lead | complete | `PRODUCT_AND_INTERFACE_SPEC.md` locks lifecycle, protocol, precedence, status, privacy, accessibility, recovery, and acceptance |
| 3 | Standalone shell and supervised Python runtime | Lifecycle worker | complete | Tauri shell, pinned sidecar, single instance, dynamic port, bounded restart, health, graceful shutdown |
| 4 | Product visualization and accessibility | Frontend worker | complete | App stage, status, controls, diagnostics, scoped keyboard, VoiceOver, reduced motion, resizing |
| 5 | Prism discovery and connector lifecycle | Integration worker | verified in source | Either launch order, reconnect, token recovery, stale-ack handling, no false healthy state |
| 6 | Audio and persona-performance correctness | Media worker | complete | Truthful main/speech clocks and handoff verified in source; packaged persona evidence remains in Phase 9 |
| 7 | Security, privacy, and diagnostics hardening | Security worker | verified in source | Authenticated mutations/WS, origin/host/body checks, private rotating credentials, safe diagnostics |
| 8 | Reproducible macOS packaging | Release worker | in_progress | Draft 81 MB `.app` built; clean-commit provenance rebuild and hashes remain |
| 9 | Independent packaged-runtime verification | Independent verifier | pending | Clean install, real Prism media and persona speech, crash/reconnect tests, screenshots/log/state samples |
| 10 | Documentation, commits, and handoff | Lead | in_progress | User/developer/release/rollback docs added; final evidence and limitations remain |

## Baseline Checks

| Check | Result | Notes |
| --- | --- | --- |
| Python `pytest` | unavailable | Repository venv does not include pytest; this is a baseline packaging/dependency discrepancy |
| Python documented `unittest` suite | passed | 249 tests passed |
| Prism Node connector tests | passed | 22 passed, including the preserved Web Audio capture tests |
| Prism Vite production build | passed | Build completed; existing large-chunk warning remains |
| Rust format | passed | `cargo fmt --all --check` |
| Rust check | passed | `cargo check --locked --workspace --all-targets` |
| Rust workspace tests | passed | Full workspace passed; exact counts retained in verification evidence |
| Rust clippy | baseline failure | `clippy::type_complexity` in `media_connector.rs`; not introduced by companion work |

## Decision Log

| ID | Decision | Status |
| --- | --- | --- |
| C-ADR-001 | Preserve Python as animation, scheduling, rendering, and frame-stream authority | accepted |
| C-ADR-002 | Build a separate Tauri companion shell with thin Rust lifecycle/transport ownership | accepted |
| C-ADR-003 | Package a self-contained Python runtime; do not depend on system Python, a checkout, or a user venv | accepted |
| C-ADR-004 | Prism GT remains authoritative for media playback, persona speech, governance, approvals, memory, and actions | accepted |
| C-ADR-005 | Keep the current LaunchAgent and installed Prism apps untouched through isolated verification | accepted |
| C-ADR-006 | Replace the 80 ms looping speech carrier clock with truthful activity plus monotonic performance timing | accepted |
| C-ADR-007 | Acknowledgement health must include scheduler/error state and freshness, not disposition alone | accepted |

## Defect Ledger

| ID | Severity | Defect | State | Exit condition |
| --- | --- | --- | --- | --- |
| COMP-001 | critical | No standalone Wizard Joe macOS application exists | implemented | Packaged-runtime launch acceptance remains |
| COMP-002 | critical | Source-tree LaunchAgent and venv are required | closed | Self-contained app-owned sidecar built |
| COMP-003 | critical | 80 ms speech carrier never reaches Python's 120 ms mouth phase | implemented | Source tests pass; real packaged persona evidence remains |
| COMP-004 | high | Python non-media mutation routes and command WebSocket are unauthenticated | closed | Per-launch auth and origin/host negative tests pass |
| COMP-005 | high | Stale or scheduler-error acknowledgements can display as connected/animating | closed | Freshness/error-aware regressions pass |
| COMP-006 | high | Existing browser keyboard handler captures Space/arrows globally | closed | Stage-scoped shortcut tests pass |
| COMP-007 | high | Prism dirty connector work is not a reproducible release input | in_progress | Full tests pass; coherent commit remains |
| COMP-008 | high | Current desktop release workflow app/DMG verification paths disagree | closed | Companion has one documented local `.app` pipeline |
| COMP-009 | medium | Python runner defaults to 8000 while production docs require 8765 | closed | Companion selects a dynamic loopback port; compatibility mode remains explicit |
| COMP-010 | medium | FastAPI shutdown hook is deprecated | closed | Lifespan-managed cleanup and runner tests pass |

## Working Whiteboard

- Active phase: Phase 8/9, clean provenance packaging and isolated runtime verification.
- Critical path: coherent commits; clean build; lifecycle/media acceptance; independent verification.
- Open blockers: packaged persona-mouth evidence and independent verification. Distribution signing/notarization remain intentionally out of scope.
- Failed approaches: short looping silent speech element as a media clock; treating accepted disposition as sufficient health; source-tree LaunchAgent as product packaging.
- File ownership: shared schemas remain single-owner until frozen; companion shell will live in a new bounded directory; existing Prism dirty files stay with the media integration workstream.
- Human approval boundary: no installed app replacement, LaunchAgent mutation, distribution signing, notarization, publishing, or governance-policy change.

## Change Ledger

| Date | Change | Evidence |
| --- | --- | --- |
| 2026-07-14 | Froze repositories, dirty work, service, installed apps, and backup identities | Git, process, launchctl, lsof, plist, bundle, signing, and hash inspection |
| 2026-07-14 | Completed five-role independent discovery pass | Runtime, architecture, media, UX/accessibility, and verification findings |
| 2026-07-14 | Began baseline checks without disturbing live installations | Node 22 pass, Vite pass, Rust fmt/check/test pass, clippy baseline failure, Python documented suite started |
| 2026-07-14 | Completed baseline and interface lock | Python 249 pass; product, lifecycle, privacy, accessibility, speech, and packaging contracts frozen |
| 2026-07-14 | Implemented Python companion mode, Tauri shell, private discovery, product frontend, and Prism integration | Python 264, frontend 17, Companion Rust 12, Prism connector 21, complete Prism Rust workspace |
| 2026-07-14 | Produced draft unsigned local app | 81 MB bundle; clean-commit rebuild required before artifact acceptance |
