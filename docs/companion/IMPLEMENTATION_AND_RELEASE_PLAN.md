# Wizard Joe Companion Implementation and Release Plan

Status: implementation complete; isolated packaged-runtime acceptance in progress

## Objective

Ship Wizard Joe as a standalone macOS companion that owns its Python runtime,
connects to Prism GT without launch-order requirements, preserves Prism-owned
audio, and animates persona speech without receiving transcript text or audio
bytes.

## Delivered Architecture

1. Preserve the Python scheduler, renderer, pose library, media arbitration, and
   ASCILINE frame protocol as the animation authority.
2. Package that runtime as a pinned PyInstaller onedir sidecar.
3. Use a separate Tauri 2 shell for windowing, app-owned child supervision,
   authenticated transport, single-instance behavior, launch at login, and
   recovery controls.
4. Publish a private, expiring discovery document containing only Prism's media
   relay credential. Keep the app-control credential inside the shell and child
   process boundary.
5. Let Prism own playback and speech. Relay only numeric lifecycle, clock,
   level, and feature data into Wizard Joe.
6. Resolve either launch order by rereading discovery before status and relay
   operations and by treating runtime rotation as a reconnect.

## Work Packages

| Package | Implementation | Verification |
| --- | --- | --- |
| Python companion mode | Versioned health, separate credentials, authenticated mutation and frame routes, literal-loopback validation, lifespan cleanup | 264-test Python suite |
| Performance arbitration | Speech preemption, main-media restoration, reaction pause, scoreless speech mouth phases | Unit and connector state tests |
| Companion shell | Dynamic port, child supervision, bounded restart, graceful shutdown, private discovery, typed bridge | 12 Rust tests and strict Clippy |
| Companion experience | Pixel stage, connection/source state, pause/repeat/poses, diagnostics, recovery, keyboard scope, VoiceOver, reduced motion | 17 frontend tests and browser QA |
| Prism media path | Truthful audible speech activity, monotonic clocks, error recovery, stale acknowledgement handling | 21 focused Node tests and Vite build |
| Prism discovery | Strict private-file validation, expiry, rotation, dynamic ports, explicit legacy override | Complete Rust workspace tests |
| Packaging | Pinned CPython/PyInstaller inputs, onedir resource staging, provenance, hashes, unsigned local `.app` | Draft bundle built; clean-commit rebuild and runtime matrix remain |

## Release Sequence

1. Commit Prism connector and speech correctness without discarding protected
   pre-existing edits.
2. Commit Wizard Joe runtime, Companion shell, frontend, tests, and docs.
3. Build the sidecar and `.app` from the clean implementation commit.
4. Record source commit, source-dirty state, hashes, size, architecture, and
   unsigned status.
5. Launch the artifact outside the repository while the legacy service remains
   untouched.
6. Verify startup, single instance, discovery permissions, restart, graceful
   quit, and no orphan child.
7. Verify both Prism-first and Companion-first launch orders with an isolated
   Prism build; do not replace `/Applications/Prism GT.app`.
8. Exercise main media and persona speech. Confirm audible playback, changing
   mouth states, speech-only preemption, restoration, and stale-state recovery.
9. Run an independent verifier over the artifact and evidence.
10. Classify signing, notarization, publishing, and auto-update separately from
    local product readiness.

## Acceptance Rule

No source-level test substitutes for packaged evidence. A gate is `verified`
only when its command or observable runtime evidence is recorded in
`VERIFICATION_EVIDENCE.md`. Signing, notarization, external distribution,
installed Prism replacement, and legacy LaunchAgent migration require separate
human authorization.
