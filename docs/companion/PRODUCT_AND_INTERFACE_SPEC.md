# Wizard Joe Companion Product And Interface Specification

Status: interface lock
Date: 2026-07-14
Target: macOS 12 or later, Apple Silicon for the first local artifact

## Product Identity

- Product name: Wizard Joe Companion.
- Bundle identifier: `com.jedisherpa.wizardjoecompanion`.
- Companion data: `~/Library/Application Support/com.jedisherpa.wizardjoecompanion`.
- Logs: companion application-support `logs` directory, with a user-facing Open Logs action.
- Prism GT remains a separate application with its existing bundle identity and data.

## Normal User Journey

1. Place Wizard Joe Companion in Applications.
2. Launch it normally from Finder, Spotlight, or the Dock.
3. See Wizard Joe immediately in a native window with an Engine Starting status.
4. The app starts its bundled Python runtime and transitions to Waiting for Prism.
5. Launch Prism before or after Wizard Joe; the apps discover the local connector automatically.
6. Play music, a podcast, or an audiobook in Prism; audio remains audible and Joe reacts.
7. Trigger persona speech; the persona remains audible and Joe's mouth visibly changes while speech is active.
8. When speech ends, Joe resumes the current main-media performance or returns to idle.
9. Pause media and see a truthful paused/idle state.
10. Quit and relaunch either app without terminal repair.

## Runtime Ownership

| State | Sole authority |
| --- | --- |
| Main-media playback | Prism GT |
| Persona generation and speech playback | Prism GT |
| Browser-to-Rust snapshot transport | Prism connector |
| Media source arbitration and performance scheduling | Python Wizard runtime |
| Final character state and ASCILINE rendering | Python Wizard controller/frame source |
| Companion Python child lifecycle and user-facing health | Wizard Joe Companion Tauri shell |
| Consequential actions, approvals, policy, memory, audit, ledger | Prism governance |

## Process Model

- One companion UI process and at most one app-owned Python child.
- The child binds to a dynamically selected literal-loopback port.
- The shell generates a per-launch high-entropy credential.
- The child reports a versioned health document before the stage connects.
- The shell supervises process exit with bounded exponential restart and a crash-loop ceiling.
- Quit requests graceful authenticated shutdown, waits briefly, then terminates only its own child if necessary.
- The existing port-8765 LaunchAgent is a compatibility runtime and is never controlled by the new app.
- A second companion instance focuses the existing window rather than starting a second child.

## Health States

| State | Meaning | User action |
| --- | --- | --- |
| starting | App launched; child not ready | Wait |
| ready | Child healthy; Prism not sending snapshots | Open Prism GT or use Demo |
| connecting | Connector exchange began; no fresh accepted acknowledgement | Wait |
| connected_idle | Fresh accepted session; no active playback | Play media in Prism |
| main_media | Fresh active main-media performance | None |
| speech | Fresh active persona/TTS performance | None |
| paused | Fresh session explicitly paused | Resume in Prism |
| reconnecting | Temporary transport or process interruption | Automatic retry; Repair available |
| degraded | Auth, acknowledgement, scheduler, asset, or protocol failure | Repair Connection / Copy Diagnostics |
| controller_conflict | Another authorized controller owns Joe | Release the other controller |
| reduced_motion | Normal operation with constrained animation | Change preference if desired |
| stopped | Reactions paused by the user | Resume Reactions |

No state may be called healthy solely because a historical acknowledgement exists. Freshness, identity, accepted sequence, scheduler state, and error state all participate.

## Performance Precedence

1. Explicit authorized manual or governed control lease.
2. Active truthful persona speech.
3. Active main media.
4. User-started local demo.
5. Idle animation.

Speech may own mouth/expression while an authorized control lease retains body authority. Demo locomotion is released when media becomes active. Stale, paused, ended, failed, or silent synthetic fallback cannot retain speech ownership.

## Speech Contract

- Transcript text and raw audio never cross the Wizard media connector.
- Real generated speech plays through Prism's actual speech audio element.
- Browser-synthesis and AudioBuffer fallbacks expose only truthful activity, a monotonic performance clock, media kind/source, and optional bounded numeric reactivity.
- A visual-only synthetic response does not claim audible speech.
- Speech activation emits a new speech media identity and epoch.
- While playing, the performance clock advances monotonically and never loops backward.
- Completion emits ended/stopped before restoring the latest main-media state.
- A normal utterance sampled across 1 second must include at least two mouth states and at least one `open_medium` or `open_wide`.
- Completion returns the mouth to `closed`.

## Connector Contract

Media Session V1 remains frozen for the first product wave:

- 16 KiB maximum request body.
- Integer time and playback-rate fields.
- Exact enums, exact keys, strict protocol version.
- Main and speech source slots.
- Opaque media identity; no private title, URL, path, caption, transcript, prompt, token, or provider key.
- Browser sends snapshots only to a same-origin Prism route.
- Prism Rust adds the private Wizard bearer token and relays only to literal loopback.
- Python validates token, Host, Origin, content type, size, schema, source identity, sequence, and epoch.

Companion lifecycle endpoints are separate from media snapshots and require the app credential.

## Python Lifecycle API

### `GET /api/companion/health`

Public only on literal loopback and read-only. Returns:

- `schema_version`
- `status`
- `runtime_epoch`
- `protocol_version`
- `character_id`
- `pid`
- `started_at_monotonic_ms`
- `frame_hub_running`
- `connector_enabled`

It returns no secret, path, URL, persona content, media metadata, or user data.

### `POST /api/companion/shutdown`

Requires the app bearer credential and no browser Origin. Initiates graceful hub shutdown and server exit.

### Existing mutation routes and WebSocket

All command-bearing HTTP routes require the app credential in companion mode. The frame WebSocket requires a one-time or per-launch credential supplied by the shell at runtime, never embedded in static assets. Read-only public state may remain available only on literal loopback in compatibility mode.

## User Interface

### Main window

- Wizard stage is the primary surface.
- Compact top status bar with state icon, plain-language status, active source, and Prism action.
- Bottom command bar: Play Demo, Repeat, Stop Local Movement, Fly, Poses, More.
- Settings: reaction pause, reduced motion, launch behavior, diagnostics.
- Recovery actions: Retry, Restart Engine, Open Prism GT, Copy Diagnostics, Open Logs.
- Advanced diagnostics are hidden by default.

### Accessibility

- Every control is reachable by keyboard with visible focus.
- Space/Enter activate focused controls; global movement shortcuts never intercept form, dialog, or button interaction.
- Movement keys apply only while the focusable stage owns focus.
- Canvas has a throttled text alternative describing Joe, source, activity, and facing.
- Status changes use a dedicated polite live region; controls are not nested inside `role=status`.
- System Reduce Motion is honored on first launch; users may choose full, reduced, or still.
- Status is never color-only.
- Layout remains non-overlapping at the minimum window size.

## Diagnostics Privacy

Allowed:

- app and engine versions,
- protocol version,
- build commit,
- process state,
- active source slot/kind,
- accepted sequence and epoch,
- scheduler state,
- acknowledgement freshness,
- error code,
- frame rate and queue depth,
- non-secret preference values,
- log locations represented by user-facing labels.

Forbidden:

- credentials,
- full private paths in copied diagnostics,
- URLs,
- media titles,
- transcript/persona text,
- prompts,
- raw audio,
- memory,
- approval payloads,
- provider configuration.

## Packaging States

1. Source checks pass.
2. Development shell runs.
3. Self-contained Python sidecar runs outside the repository.
4. Local Tauri `.app` builds.
5. Local `.app` launches from Applications without development services.
6. Nested code is locally/ad-hoc signed and verified.
7. Developer ID signed.
8. Notarized.
9. Stapled.
10. Installer or DMG created.
11. Published.

This implementation may complete states 1-6. States 7-11 require explicit human approval and credentials.

## Acceptance Gates

- Existing Python, browser, Rust, and build checks pass except separately documented baseline failures.
- New lifecycle, auth, crash/restart, speech clock, mouth sequence, status, and privacy tests pass.
- The self-contained sidecar runs with no system Python or repository path.
- The app launches with Prism absent and transitions cleanly when Prism later launches.
- Main media remains audible and animates Joe.
- Persona speech remains audible and yields changing mouth states in the real packaged path.
- Speech completion restores advanced main time without restarting playback.
- Wizard failure does not stop or silence Prism.
- Two app launches do not create two children.
- A clean local app artifact has commit and SHA-256 provenance.
- Rollback leaves the prior Prism app and port-8765 LaunchAgent intact.

## Release References

The build design follows the current official Tauri 2 external-binary model and PyInstaller one-folder guidance. Public distribution additionally requires Apple's Developer ID, hardened runtime, secure timestamp, notarization, and stapling workflow. These references guide implementation but do not imply those release states were completed.
