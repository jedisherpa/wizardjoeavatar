# Audiobook Performance Engine Program Tracker

Owner: implementation coordinator
Started: 2026-07-13
Status values: `pending`, `in_progress`, `blocked`, `complete`, `verified`

This is the canonical accountability record. A phase is complete only when its artifacts and verification evidence exist in the repository.

| Phase | Workstream | Owner role | Status | Required evidence |
| --- | --- | --- | --- | --- |
| 0 | Baseline and repository safety | Coordinator | verified | Current-state map, branch/HEAD capture, clean PrismGT baseline, live 8765 proof |
| 1 | Twelve independent specialist audits | 12 specialists | complete | Reports `research/01` through `research/12`, cited and code grounded |
| 2 | Cross-discipline synthesis and ADRs | Synthesis team | complete | Three synthesis reports plus approved master implementation plan |
| 3 | Capability manifest and character contract | Character TD | in_progress | Existing Wizard Joe package is bound; multi-character performance fixture remains |
| 4 | Media asset and session schemas | Systems engineer | verified | Strict schemas, golden fixtures, canonical hashing, Python/JS/Rust parity |
| 5 | Transcript ingestion and local alignment | Speech engineer | complete | VTT/SRT/text/SSML-safe ingest, immutable revisions, local-only adapter states |
| 6 | Narrative analysis and score generation | Narrative/LLM | complete | Deterministic content-free narrative artifacts, cache/provenance, compiler tests |
| 7 | Music DSP and score generation | DSP engineer | complete | Deterministic local media normalization and music-score fixtures |
| 8 | Performance cue scheduler | Runtime engineer | verified | Media-time evaluation, seek/pause/rate/reconnect, source-slot handoff tests |
| 9 | Character performance mapping | Animator/TD | complete | Native action/expression/mouth/pose mapping with manual-control body authority |
| 10 | Facial, eye, mouth, and speech polish | Face specialist | in_progress | Native mouth-shape mapping and TTS fallback complete; authored viseme envelopes remain |
| 11 | Stage movement and camera composition | Previs/animator | pending | Screen path/staging cues, safe bounds, reduced-motion path |
| 12 | Music performance mode | DSP/animator | verified | Deterministic media-time groove cycles with reduced/still projection |
| 13 | PrismGT connector transport | Integration engineer | verified | Strict V1 relay, token/origin/body limits, diagnostics, isolated live relay proof |
| 14 | PrismGT player wiring | PrismGT engineer | complete | Main and speech HTML audio lifecycle wiring; TTS preemption and main restore |
| 15 | Whiz governed media action | PrismGT/governance | pending | Canonical URL validation, explicit-click-only open, disabled/error states |
| 16 | Preview, editing, and debug UI | UX/previs | in_progress | Connector diagnostics shipped; score timeline/editor remains |
| 17 | Automated quality gates | QA | verified | 249 Python, 20 Node, 9 Rust contract, 5 Rust route, 3 desktop activation tests; Vite and desktop builds passed |
| 18 | Browser and visual verification | QA/accessibility | verified | Packaged playback animated main media, paused cleanly, and passed desktop/mobile status and overlap checks |
| 19 | Documentation, deployment, and handoff | Coordinator | in_progress | Local operator guide complete; commits, pushes, and final report remain |

## Specialist Accountability

| # | Discipline | Report | Status |
| --- | --- | --- | --- |
| 1 | Supervising Animation Director | `research/01-supervising-animation-director.md` | complete |
| 2 | Character Performance Animator | `research/02-character-performance-animator.md` | complete |
| 3 | Facial/Eye Motion | `research/03-facial-eye-motion.md` | complete |
| 4 | Audiobook/Narrative Direction | `research/04-audiobook-narrative-direction.md` | complete |
| 5 | Audio DSP/Music | `research/05-audio-dsp-music.md` | complete |
| 6 | Speech Recognition/Alignment | `research/06-speech-alignment.md` | complete |
| 7 | Character Technical Direction | `research/07-character-technical-direction.md` | complete |
| 8 | Performance Planning/LLM | `research/08-performance-planning-llm.md` | complete |
| 9 | PrismGT Integration | `research/09-prismgt-integration.md` | complete |
| 10 | Film Editing/Previsualization | `research/10-film-editing-previs.md` | complete |
| 11 | QA/Verification | `research/11-qa-verification.md` | complete |
| 12 | Accessibility/UX | `research/12-accessibility-ux.md` | complete |

## Decision Log

| ID | Decision | Status |
| --- | --- | --- |
| ADR-001 | Keep Python ASCILINE as character-performance runtime | accepted |
| ADR-002 | Keep PrismGT HTML audio element as authoritative clock | accepted |
| ADR-003 | Use deterministic persisted scores; optional models enrich but never own playback timing | accepted |
| ADR-004 | Prefer transcripts/captions, then optional local transcription; no silent cloud upload | accepted |
| ADR-005 | Derive state from score plus media time so seeks and reconnects are exact | accepted |
| ADR-006 | Use capability-aware mappings and visible fallbacks for additional characters | accepted |
| ADR-007 | Whiz permits only stored canonical HTTP(S) URLs and explicit user activation | accepted |

## Known Risks

| Risk | State | Mitigation/exit condition |
| --- | --- | --- |
| Stream deadline test inconsistency | closed | Fake-clock deadline policy test covers 100 schedules; full 243-test suite passes |
| Whisper unavailable | open | Capability reports unavailable; caption/transcript fixtures cover core; document install adapter |
| Cross-origin hosted connector | closed_local | Loopback-only base URL, bearer/session tokens, browser-origin rejection, 16 KiB strict body |
| Pose-to-pose visual discontinuity | open | Transition grammar and holds; never cell-dissolve authored sprites |
| Face anchors differ across poses | open | Manifested capability/anchor support and regression snapshots |
| PrismGT component is very large | open | Add small connector modules/hooks instead of expanding unrelated concerns |
| Scope spans two repositories | open | Separate branches/commits, versioned contract fixtures shared by test, no replacement deployment |

## Change Ledger

| Date | Change | Verification |
| --- | --- | --- |
| 2026-07-13 | Froze current-state architecture and program tracker | Live 8765 process/API, 89 pose count, repo branches/HEADs inspected |
| 2026-07-13 | Started 12-role research pass in two bounded waves | First five reports present; remaining reports assigned |
| 2026-07-13 | Re-ran the complete Python baseline | 171 tests passed; isolated deadline inconsistency remains tracked from QA |
| 2026-07-13 | Verified the PrismGT frontend baseline | Vite production build passed; full Rust workspace gate requires an undeclared Tauri sidecar prerequisite |
| 2026-07-13 | Completed all 12 independent specialist audits | Twelve cited, code-grounded reports are present; three-way synthesis round started |
| 2026-07-13 | Completed the structured synthesis round | Runtime/contracts, PrismGT/UX, and animation/delivery syntheses reconciled into `IMPLEMENTATION_PLAN.md` |
| 2026-07-13 | Expanded the live integration target to all PrismGT audio | Main music/podcast/audiobook player and TTS/speaker element share deterministic priority and handoff |
| 2026-07-14 | Implemented and verified the local media connector | 245 Python tests, 18 Node tests, 14 Rust focused tests, Vite build, isolated live relay |
| 2026-07-14 | Proved source priority against the persistent runtime | Music animated on `main`; TTS preempted on `speech`; main resumed at advanced media time |
| 2026-07-14 | Closed the usability and state-ownership audit | 249 Python tests; packaged app connected from private config; main audio animated; pause released performance; desktop/mobile browser QA passed |
