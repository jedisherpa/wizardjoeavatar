# Prism Connector Specialist Report

## Scope

The canonical document was compared with current Python, Prism baseline
`189fbab`, corrective successor `5910601`, checked-out Prism `main`, and the
installed app surface. No connector changes were made.

## Documentation-to-Code Matrix

| Requirement | Evidence | Status |
|---|---|---|
| Stable compatibility UI on `127.0.0.1:8765` | LaunchAgent and server runner | Documented and implemented |
| Wizard media POST/status endpoints | `server.py` | Documented and implemented |
| Browser sends only to same-origin Prism route | `mediaSessionProtocol.js`, `useMediaSessionConnector.js` | Implemented on connector branch; missing on Prism `main` |
| Rust bearer-authenticated relay | `media_connector.rs`, `web.rs` | Implemented on connector branch; missing on Prism `main` |
| Strict V1 snapshot and acknowledgement | Python schema/parser plus JS/Rust validators | Documented and implemented |
| Unknown fields, duplicate keys, private content rejected | Python/JS/Rust strict allowlists | Documented and implemented |
| 16 KiB request/ack limits | Python server and Rust relay | Documented and implemented |
| UUID session, sequence, media epoch, stale/dedupe | `MediaSessionCoordinator` | Documented and implemented |
| One controlling session with five-second lease | `media_session.py` | Implemented but undocumented |
| Audible speech preempts main and restores it | connector hook and coordinator | Documented and implemented |
| Real audio elements sampled at 4 Hz while playing | Prism `index.jsx` and connector hook | Implemented on connector branch; missing on `main` |
| Stale interpolation stops after 1.5 seconds | Python coordinator | Implemented but undocumented |
| Pause/terminal/stale releases performance ownership | `PerformanceApplication` | Documented and implemented |
| Compiled score precedence | Scheduler supports it; application has no resolver/repository | Documented but incomplete |
| Runtime-epoch reconnect/resync | connector hook and coordinator | Documented and implemented |
| Manual reload after resync | connector already auto-emits reconnect | Obsolete |
| One in-flight/latest pending and bounded retry | JS hook and Rust relay | Implemented but undocumented |
| High-entropy token and `0600` config | installer and corrective successor | Documented and implemented |
| Constant-time bearer, Origin rejection, literal loopback | Python server and Rust relay | Documented and implemented |
| Typed errors and sanitized status | Rust relay/routes | Documented and implemented |
| Rejected/stale ack preserves accepted cursor | Broken at baseline; fixed in `5910601` | Complete only in successor |
| Packaged Prism private config and visible Wizard status | `5910601` | Missing at baseline and `main`; implemented in successor |
| Passive connector never changes playback | connector `stopPlayback()` pauses and resets audio | Contradicted |
| Dirty shadow diagnostics | `stream.py` behind environment flag | Implemented but undocumented |
| Installed main -> speech -> restored-main proof | Installed code exists; no live Prism run | Requires verification |

## Architecture

Media Session V1 is full-state, content-free, versioned, local-only, bounded,
and acknowledged. Browser code posts to a same-origin local Prism route; Rust
validates and relays to Wizard with the media bearer. Python validates session,
sequence, source priority, and stale state, then the existing scheduler and
application map media time to character state.

## Gaps

- Production `PerformanceApplication` does not receive a compiled score
  repository/resolver.
- The checked-out Prism `main` deletes connector files; connector development
  must use `5910601`.
- Compatibility and Companion discovery lifecycle documentation conflict.
- Installed three-state playback and reconnect remain unproven in this pass.
- The connector's playback-control helper contradicts its passive contract.

## Verification

The specialist observed 21 focused Wizard, 20 JavaScript connector, 9 Rust
connector, and 5 Rust route tests passing. Full builds and live three-state
playback were not run and remain required.
