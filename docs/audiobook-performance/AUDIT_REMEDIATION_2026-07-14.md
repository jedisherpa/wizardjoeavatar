# Media Animation Audit Remediation

Date: 2026-07-14
Status: implemented and verified

This record closes the defects found in the local Prism GT to Wizard Joe media
animation audit.

| Audit finding | Remediation | Verification |
| --- | --- | --- |
| Silent or paused TTS could strand animation on speech | Full-state source ownership now follows each authoritative connector snapshot; only playing, buffering, or seeking speech can preempt main | Coordinator and scheduler handoff regressions; full Python suite |
| Prism could display a healthy binding for a stale or mismatched acknowledgement | Accepted acknowledgements must match connector session, sequence, and epoch; invalid, rejected, resync, conflict, and unavailable states remain visible | JavaScript transport and diagnostics tests |
| Scripted demo locomotion could block media actions | Media playback releases demo paths, repeat targets, and unleased walking before applying body actions; human control leases remain authoritative | Performance application regression and live idle-locomotion playback proof |
| No direct Stop control | Added a square Stop button that cancels repeat, clears pose overrides, and sends the runtime stop command | Browser control wiring and live labeled-control check |
| Activation depended on terminal-only environment | The Wizard installer creates a private `0600` connector file and matching LaunchAgent token; packaged Prism reads it on normal launch while preserving explicit development overrides | Three desktop parser tests and installed-app connected status |
| Connector state was hard to find | Added always-visible Wizard Joe status and Player/Open Wizard actions in Prism, plus a public content-free media banner in the visualization | Packaged browser playback and pause proof |
| Diagnostics rendered an undefined playback rate | Diagnostics now derives the rate from integer `rate_milli` and renders `1x` correctly | Connector component verification |
| Instructions were operator-centric | Added a short user workflow, stable URLs, one-time activation, state meanings, and recovery steps | README and local connector guide review |
| Mobile banner overlapped controls | Mobile controls use a stable two-row grid and the media banner is positioned beneath it | 390 x 844 browser check: zero overlap and zero horizontal overflow |

## Acceptance evidence

- Python: 249 tests passed.
- JavaScript connector: 20 tests passed.
- Rust media connector: 9 focused contract tests passed.
- Rust route integration: 5 focused tests passed.
- Desktop activation parser: 3 tests passed.
- Vite production build passed.
- Tauri desktop application build passed.
- Installed Prism GT reported `connected` with an accepted acknowledgement.
- A bundled main track produced `Animating main audio`; Wizard Joe reported
  `active=true`, `source=main`, `scheduler_state=playing`, an authored action,
  and idle locomotion.
- Pausing produced `Connected - media paused`; Wizard Joe reported inactive,
  paused media with no retained performance action.
- Desktop and mobile pages produced no browser console errors. The mobile page
  had no control/status overlap and no horizontal overflow.

Credentials, media paths, titles, transcripts, and provider secrets are not
included in public status payloads or this evidence.
