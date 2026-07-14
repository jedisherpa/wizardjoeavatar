# Wizard Joe Companion Current-State Audit

Audit date: 2026-07-14
Status: discovery baseline, implementation not yet claimed

## Executive Finding

Wizard Joe is a capable Python ASCILINE animation runtime with a functioning local Prism media connector, but it is not a standalone macOS product. The normal path still depends on a repository checkout, a manually prepared virtual environment, a LaunchAgent, a fixed localhost port, a browser page, and separately provisioned credentials. The current Prism connector work preserves media audibility in tests, but persona mouth animation has a deterministic timing defect in fallback speech paths.

## Repository Identity

| Repository | Branch | HEAD | Remote | Starting tree |
| --- | --- | --- | --- | --- |
| Wizard Joe Python | `codex/audiobook-performance-engine` | `408825ae75e395cd0761d0f17b9636a40559263a` | `https://github.com/jedisherpa/wizardjoeavatar.git` | clean |
| Prism GT | `codex/wizardjoe-media-connector` | `59106015fe22b224df350ddd28dc2fd487132681` | `https://github.com/jedisherpa/prism-geometry-talk.git` | dirty: two modified files and one untracked test |

Historical clues `556701a`, `189fbab`, `408825a`, and `5910601` exist and are ancestors of the active tips. The last two are the current committed tips, but the Prism runtime source includes later uncommitted work.

## Live Environment

- Wizard LaunchAgent: `com.jedisherpa.wizardjoeavatar`.
- Discovery process: PID 59002, parent PID 1, listening only on `127.0.0.1:8765`.
- Program: repository `.venv/bin/python tools/run_wizard_avatar_server.py --port 8765`.
- Logs: `~/Library/Logs/WizardJoeAvatar.log` and `WizardJoeAvatar.error.log`.
- Existing Prism app: `/Applications/Prism GT.app`, version `0.1.0`, bundle `com.jedisherpa.prismgeometrytalk`, ad-hoc signed.
- Preserved rollback app: `/Applications/Prism GT.pre-wizard-connector.app`.
- Prism was not running at discovery.
- The Wizard process started before commit `408825a`; because reload is disabled, the process cannot be treated as proof that in-memory code equals HEAD.

No secret values are copied into this report. The existing private connector configuration and LaunchAgent token remain machine-local.

## Current Architecture

```text
Prism GT HTML audio elements
  -> browser MediaSessionSnapshotV1
  -> same-origin Prism Rust route
  -> loopback-only authenticated Rust relay
  -> Python MediaSessionCoordinator
  -> PerformanceScheduler / PerformanceApplication
  -> WizardAvatarController
  -> ProceduralWizardFrameSource
  -> ASCILINE WebSocket frames
  -> browser Canvas square-cell renderer
```

### Authority

- Prism GT owns audible media playback and persona speech.
- Prism Rust owns governed application state, approvals, policy, ledger, memory, and the credential-bearing relay.
- Python owns media-to-performance interpretation, arbitration, final controller state, ASCILINE rendering, and frame streaming.
- The current browser visualizer owns presentation and developer controls.
- The LaunchAgent currently owns Python process persistence; no product shell owns the user journey.

### Verified code paths

- Python startup: `tools/run_wizard_avatar_server.py`.
- HTTP/WebSocket surface: `wizard_avatar/server.py`.
- Authoritative tick and media application: `wizard_avatar/stream.py::WizardFrameHub`.
- Source arbitration and clock: `wizard_avatar/media_session.py::MediaSessionCoordinator`.
- Media-to-animation policy: `wizard_avatar/performance_scheduler.py`.
- Final animation application: `wizard_avatar/performance_application.py::PerformanceApplication`.
- Rendering: `wizard_avatar/frame_source.py::ProceduralWizardFrameSource`.
- Prism media ownership: `src/pages/PrismDodecahedron/index.jsx`.
- Web Audio analysis: `src/pages/PrismDodecahedron/musicMotion.js`.
- Browser snapshot protocol: `media/mediaSessionProtocol.js`.
- Browser connector state: `media/useMediaSessionConnector.js`.
- Prism relay: `crates/prism-cdiss-cli/src/media_connector.rs` and `web.rs`.
- Prism Tauri child lifecycle: `src-tauri/src/main.rs`.

## Confirmed Contradictions

1. Documentation calls the Python service the production target, but the foreground runner defaults to port 8000 while normal operation uses 8765.
2. The active product is Python, while a historical Rust avatar subdirectory still describes itself as production.
3. Prior reports called the media integration complete, but Prism contains uncommitted audibility/speech work and the packaged speech path still fails mouth-motion acceptance.
4. The browser can display connected/animating based on accepted disposition even when Python reports stale or scheduler-error state.
5. The current installer assumes the ignored `.venv` already exists, so it is not a complete installer.
6. Existing release automation builds an app bundle while one verification path requires a DMG.

## Persona Mouth Root Cause

The preserved Prism work correctly prefers the real speech audio element and prevents Web Audio from capturing main media before its `AudioContext` runs. Its fallback carrier, however, loops an 80 ms silent WAV. Python scoreless speech selects mouth phases in 120 ms intervals. The connector therefore repeatedly reports a clock that cannot reach the first open phase, allowing active audible persona speech to remain visually closed-mouthed.

The correction must not send transcript text or raw audio. It must separate:

1. truthful speech activity,
2. an authoritative or monotonic performance clock,
3. optional privacy-safe amplitude features,
4. actual playback ownership in Prism.

Visual-only synthetic fallback must not claim audible speech.

## Security And Privacy Findings

- The media-session ingress is bearer authenticated, loopback constrained, body limited, and browser-origin rejected.
- The media contract excludes URLs, paths, transcript text, persona responses, and raw media.
- Other Python mutation routes and the command-bearing WebSocket are not equivalently authenticated.
- Existing credentials are stored in private local files, but the source-tree LaunchAgent exposes process environment to the same user and is not a packaging boundary.
- Wizard Joe does not need and must not receive governance authority, memory mutation, tool execution, external communication, or persona text.

## UX And Accessibility Findings

- No first-launch, Prism-missing, degraded, reconnecting, or repair journey exists in a native app.
- Global Space/arrow interception in `wizardControls.ts` conflicts with standard button, dialog, scrolling, and assistive interaction.
- Canvas semantics are static and do not announce current activity.
- Reduced-motion behavior exists in Python but is not consistently exposed or applied to demos/manual animation.
- Raw diagnostics dominate the current developer surface; product status and recovery need their own restrained layer.

## Baseline Verification

| Layer | Result |
| --- | --- |
| Python pytest | unavailable in repository venv |
| Python documented unittest | 249 passed |
| Prism browser connector | 22 passed |
| Prism production frontend | passed; existing chunk-size warning |
| Rust format | passed |
| Rust check | passed |
| Rust workspace tests | passed |
| Rust clippy | baseline failure: `clippy::type_complexity` in a media-connector test helper |

## Release Readiness

Current status: **not standalone and not release ready**.

Missing product boundaries:

- Native companion application identity and lifecycle.
- Self-contained Python runtime.
- Single-instance and duplicate-engine protection.
- App-owned health, logs, restart, and shutdown.
- Secure app-owned connector provisioning and rotation.
- Product status, onboarding, repair, and accessibility.
- Truthful mouth timing and real packaged-path acceptance.
- Reproducible app build with provenance and hashes.
- Clean-install, crash-recovery, and rollback evidence.

## Preservation And Rollback

Until isolated verification passes:

- Leave `/Applications/Prism GT.app` unchanged.
- Leave `/Applications/Prism GT.pre-wizard-connector.app` unchanged.
- Leave LaunchAgent `com.jedisherpa.wizardjoeavatar` running and unchanged.
- Do not share a writable application database between a new companion and Prism.
- Do not clean, checkout, reset, or stash the three preserved Prism paths without an explicit checkpoint.
- Build the new companion under a separate bundle identity and application-support directory.

## Post-Implementation Delta (2026-07-14)

The findings above preserve the verified pre-change baseline. The active
branches now implement the previously missing product boundaries:

- `companion/` provides the separate Tauri 2 app, app-owned Python sidecar,
  dynamic port, single-instance behavior, bounded recovery, graceful shutdown,
  typed authenticated bridge, login item, logs, and safe diagnostics.
- Python companion mode now requires separate launch credentials for app
  control and media relay, validates literal-loopback requests, uses FastAPI
  lifespan cleanup, and reports versioned child identity/readiness.
- Companion publishes an atomic private discovery document under its own
  application-support directory. Prism validates and rereads that document,
  allowing either launch order and runtime rotation without an implicit stale
  legacy fallback.
- Prism now uses truthful audible speech activity with a monotonic performance
  clock, so scoreless speech advances beyond Python's mouth-phase threshold.
  Pause, end, and error restore the current main-media state.
- The app frontend replaces the developer localhost journey with a focused
  stage, source/connection status, controls, pose library, recovery,
  accessibility, reduced motion, and safe diagnostics.

The source-level release gates now pass: Python 264, Companion frontend 17,
Companion Rust 12 with strict Clippy, Prism connector 21, Vite production build,
and the complete locked Prism Rust workspace. An unsigned 81 MB draft app also
builds. It is not yet the accepted artifact because it was produced before the
implementation commit. Clean-commit provenance, isolated packaged lifecycle,
real persona-mouth evidence, and independent verification remain tracked in
`VERIFICATION_EVIDENCE.md` and `PRODUCTION_READINESS.md`.
