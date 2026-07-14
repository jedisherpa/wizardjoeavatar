# ADR-001: Standalone Wizard Joe Companion Architecture

Status: proposed pending interface-lock verification
Date: 2026-07-14

## Decision

Build a separate Tauri macOS application that owns Wizard Joe's user journey and supervises a self-contained packaged Python sidecar.

```text
Wizard Joe Companion.app
  Tauri shell
    - single-instance application lifecycle
    - Python child supervision and bounded restart
    - per-launch credential and dynamic loopback port
    - product status, controls, diagnostics, and recovery
    - bundled visualization assets
  packaged Python sidecar
    - MediaSessionCoordinator
    - PerformanceScheduler / PerformanceApplication
    - WizardAvatarController
    - Procedural ASCILINE rendering
    - authenticated HTTP and WebSocket endpoints
```

Prism GT remains a separate application. Its existing browser-to-Rust connector continues to send privacy-safe media snapshots to Wizard Joe over authenticated loopback communication. Prism remains authoritative for playback, persona speech, governance, approvals, policy, audit, memory, and action execution.

## Why

- It removes terminal, browser URL, port, venv, environment-variable, and LaunchAgent knowledge from the normal user journey.
- It preserves the existing deterministic Python animation engine rather than creating a parallel Rust animation system.
- It reuses the proven Tauri child-process lifecycle pattern already present in Prism while giving Wizard Joe its own identity and release cadence.
- It allows side-by-side isolated verification without replacing the current Prism app or interrupting the known-good Wizard service.
- It keeps orchestration thin: Rust owns lifecycle and transport; Python owns animation.

## Alternatives

### Tauri supervising the installed LaunchAgent

Rejected as the target architecture. It retains a mutable checkout, arbitrary venv, fixed port, version skew, orphan-job, and incomplete uninstall risks. It may remain a temporary compatibility path during migration.

### Embed Wizard Joe as a second Prism GT window

Rejected. It couples product identity, lifecycle, release, rollback, and user data to Prism and prevents a genuinely separate companion.

### Migrate the animation engine to Rust

Rejected. The repository already contains a historical Rust implementation that duplicates the Python runtime, renderer, protocol, and pose ownership. No evidence shows that Python cannot satisfy the goal when packaged as a sidecar.

### Native Swift/AppKit shell

Deferred. It could provide excellent platform integration, but Tauri already exists in the local product stack, provides reusable lifecycle code, and avoids introducing a second native UI toolchain for this phase.

## Interface Locks Before Implementation

1. Python remains the sole owner of performance scheduling and renderable Wizard state.
2. Prism remains the sole owner of audible playback and persona speech generation.
3. The companion shell owns only its Python child lifecycle and user-visible health.
4. Media Session V1 remains privacy-safe and excludes text, URLs, paths, media bytes, and governance state.
5. Every companion mutation endpoint and WebSocket upgrade requires a per-launch credential and loopback-valid Host/Origin.
6. Speech preempts main media only while truthful speech activity is active.
7. Speech fallbacks use monotonic performance timing independent of a short silent media loop.
8. Manual authorized control leases outrank speech body gestures; speech outranks main media; main media outranks demo and idle.
9. Health is versioned and includes process, protocol, readiness, accepted-sequence freshness, scheduler/error state, and recovery guidance.
10. The shell uses a dynamic internal port; port 8765 remains a compatibility mode, not a user-facing requirement.

## Packaging

The Python runtime must include a pinned CPython, dependencies, definitions, and web assets. It must not depend on Xcode Python, a system Python, Homebrew, a repository checkout, or a user-created virtual environment. The build must record lockfile hashes, tool versions, source commits, bundle hash, sidecar hash, and signing/notarization state separately.

Distribution signing, notarization, stapling, and publishing remain separate human-approved milestones. A local ad-hoc or unsigned application may be built and verified without claiming public release readiness.

## Security

- Bind all services to literal loopback.
- Generate a high-entropy per-launch credential; do not place it in frontend assets, logs, docs, or process arguments.
- Pass secrets through inherited environment or a private app-owned file and redact them from diagnostics.
- Authenticate HTTP mutations and WebSocket upgrades.
- Enforce request-size, schema-version, sequence, source, and origin rules.
- Keep Prism action gateways and governance untouched.
- Never send raw audio or persona text to Wizard Joe.

## Migration

1. Freeze cross-language fixtures and lifecycle contracts.
2. Correct speech timing and acknowledgement health in the existing path.
3. Add versioned Python health, authenticated shutdown, and configurable internal port.
4. Produce and test the self-contained Python sidecar.
5. Build the companion shell and bundled product UI.
6. Run it with an isolated app-support directory and dynamic port while the old 8765 service remains untouched.
7. Verify both launch orders, playback, speech, handoff, restart, stale auth, duplicate process, and clean quit.
8. Build a clean local app artifact and capture provenance.
9. Only after approval and acceptance, provide an optional migration from the legacy LaunchAgent.

## Rollback

Quit and remove only the isolated Wizard Joe Companion app and its new app-support directory. The existing LaunchAgent, port-8765 visualizer, Prism app, Prism backup app, connector file, and Prism data directory remain untouched throughout this phase, so rollback does not require source or data restoration.
