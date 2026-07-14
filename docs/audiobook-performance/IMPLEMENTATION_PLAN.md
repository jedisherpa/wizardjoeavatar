# Wizard Joe Audiobook Performance Engine Implementation Plan

Status: approved for implementation
Date: 2026-07-13
Inputs: current-state architecture, 12 independent specialist reports, and the three-file structured synthesis round

The detailed normative design lives in:

- `synthesis/01-contracts-runtime-synthesis.md`
- `synthesis/02-prismgt-ux-synthesis.md`
- `synthesis/03-animation-delivery-synthesis.md`

This document is the coordinator's executable integration order. Where a detail is omitted here, the synthesis files remain binding.

## Locked Architecture

1. PrismGT's real HTML audio elements own media time: the main player for music, podcasts, and audiobooks, plus the TTS/speaker element for generated speech.
2. PrismGT sends authenticated, full-state `MediaSessionSnapshotV1` corrections over loopback HTTP.
3. Python validates snapshots and derives complete performance state from accepted compiled score plus `position_ms`.
4. Playback corrections do not enter the 1,024-item ordered user-command inbox and do not use the current frame WebSocket.
5. Linear play, cold seek, reconnect, and restart at the same time resolve to the same cue, pose phrase, expression, mouth, gaze, stage target, and accessibility projection.
6. Persisted contract times are integer milliseconds; offline DSP may preserve canonical integer sample positions.
7. Runtime aesthetic choices are not random. Deterministic compilation may choose a take, which is persisted in `CompiledPerformanceScoreV1`.
8. Authored square-cell poses remain atomic. Continuity comes from phrase phases, holds, marker gates, root/contact correction, and coherent whole-pose cuts, never cell dissolves.
9. Models may propose bounded semantic intent or `no_decision`; deterministic Python compilation owns character mapping and fallback.
10. Local media, transcripts, and manuscript content stay local by default and never cross the connector.
11. Whiz accepts no caller URL. An explicit click requests a single-use server grant for the stored canonical HTTP(S) URL, then performs one top-level navigation.
12. Additional characters use package capabilities, semantic mappings, and explicit fallback records; the scheduler contains no Wizard Joe conditionals.
13. Audible TTS/speaker playback temporarily owns the performance layer; when it ends, the connector resamples and restores the still-playing main-media state without restarting audio or replaying stale cues.

## Wave 0: Contract and Evidence Foundation

Parallel owners may edit only their assigned files.

### 0A - Canonical artifacts

- Add `artifact_hashing.py` and strict schema loading.
- Add Draft 2020-12 schemas and golden fixtures for media asset, transcript, alignment, narrative score, music score, portable performance score, score edits, character package V2, compiled score, media session snapshot, and acknowledgement.
- Reject floats, unknown fields/versions, invalid ranges, unsupported hashes, duplicate IDs, and stale character/package bindings.
- Add cross-language canonical-hash vectors.

Exit: schema/hash unit tests pass and every fixture round-trips without information loss.

### 0B - Deterministic score runtime

- Add immutable score loader/repository, interval index, media session coordinator, clock estimator, state-at-time scheduler, accessibility projection, diagnostics, and fallback records.
- Use half-open cue intervals and deterministic precedence.
- Freeze score-owned channels on pause/buffering.
- On seek or generation change, invalidate old phrase history and compute target state directly.

Exit: fake-clock tests prove linear/cold-seek equivalence, pause, seek, rate, reconnect, deduplication, stale rejection, and reduced/still projection.

### 0C - Local authoring foundation

- Add caption/text transcript ingestion and canonical normalization.
- Prefer provider-native timing bound to exact audio, then supplied captions, then optional local alignment/ASR.
- Add FFprobe/FFmpeg media identity and deterministic baseline PCM/audio feature extraction in an isolated tool boundary.
- Produce content-free narrative and music direction fixtures and cache identities.

Exit: repeat runs produce identical artifact hashes; unavailable optional tools return explicit capability states rather than silent degradation.

### 0D - Timing and evidence repair

- Replace the isolated sleep-sensitive stream deadline assertion with a fake-clock scheduler proof.
- Keep an instrumented real-render benchmark as a separate performance gate.
- Add a run manifest containing commits, dirty state, tool versions, commands, fixture hashes, results, and evidence checksums.

Exit: deterministic test passes 100 iterations and the real benchmark reports phase percentiles without controlling correctness.

### 0E - Prism connector shell

- Add frontend protocol serialization and a media-element connector hook covering both `audioRef` and `speechAudioRef`, with deterministic audible-source priority, one in-flight/one pending coalescing, 4 Hz playing heartbeat, event snapshots, sequence/epoch/session identity, retry, and status.
- Add a Rust/local relay that validates loopback destination, token, body, protocol, and latest-state semantics.
- Keep public hosted routes unable to reach the local Wizard connector.

Exit: protocol parity fixtures pass in Python, JavaScript, and Rust; no media bytes or transcript text appear in captured requests.

## Wave 1: Runtime Integration

1. Add authenticated `POST /api/avatar/wizard/media-session` and sanitized status endpoint.
2. Instantiate one coordinator/scheduler beside `AvatarRuntime` in `WizardFrameHub`.
3. Apply resolved performance state at the existing tick boundary with user/safety authority above score channels.
4. Expose active media, score/package hashes, cue hierarchy, phrase phase, drift/freshness, fallback, suppression, and last acknowledgement.
5. Add feature flags and a neutral fail-closed state; legacy manual/demo controls continue to work when connector mode is off.

Exit: real FastAPI tests cover auth, origin, content type/size, dedupe, stale session, restart, privacy, and sanitized errors; all existing 171 tests remain green.

## Wave 2: Character Performance Compilation

1. Upgrade/adapt CharacterPackage V2 with truthful capabilities, anchors, mappings, transition policy, face support, accessibility projection, and hashes.
2. Compile semantic score cues into persisted character-bound takes with explicit fallback/suppression records.
3. Execute authored phrase preparation, action, hold, recovery, marker, legal-successor, interruption, and contact policy.
4. Make stationary speech compatible with curated body phrases.
5. Add deterministic anti-repetition, emotional hysteresis, chapter continuity, stage bounds, and no-gesture weighting.
6. Validate with a deliberately smaller second-character fixture.

Exit: no unsupported pose or channel is silently selected; every autonomous pose has a role, legal entry/exit, hold, interruption policy, and creative approval.

## Wave 3: Speech, Face, and Narrative Performance

1. Replace fixed mouth cycling with alignment/audio-envelope groups and explicit silence closure.
2. Add deterministic gaze targets/fixations, eye-head contribution, blink scheduling, expression envelopes, and pose visibility support.
3. Implement characterful neutral, explain, reference, think, sincere, quiet, emotion, chapter handoff, and restrained reaction phrases.
4. Preserve spoiler-sensitive timing and editorial holds.
5. Add browser-scale visual goldens and 15-minute representative performance evidence.

Exit: silence never shows speech mouth, no fixed-period blink remains, unsupported rear/occluded face overlays do not render, and acting passes silhouette/contact/continuity review.

## Wave 4: Music Performance

1. Generate canonical PCM, beats/downbeats/onsets, tempo/meter regions, sections, loudness, and envelopes with provenance.
2. Compile bar/section phrases from declared music-compatible character capabilities.
3. Derive every beat/bar/section phase from media timestamps, never render deltas.
4. Enforce accent density, anti-repeat, stage bounds, recovery, confidence/unknown handling, and reduced/still projection.
5. Keep browser Web Audio metrics cosmetic.

Exit: 30/60/120/irregular render schedules choose identical music events; seek/pause/rate never replay pulses; the feature is called music performance until dedicated dance families pass creative gates.

## Wave 5: PrismGT Player, Editor, and Whiz

1. Wire the connector to the existing `audioRef` and `speechAudioRef`; preserve event order, including TTS handoff and ended before main-player auto-next.
2. Add seek, rate, stop, chapter, captions, searchable transcript, follow, character, intensity, and motion-profile controls.
3. Add connector/score diagnostics, cue table, focused timeline, immutable edit overlay, validation, preview, save, regeneration diff, lock/rebase/conflict handling, and take compare.
4. Preserve new media digest, transcript/alignment, performance, external URL, and durability fields in library normalization/storage.
5. Implement governed Whiz grant plus single-use redirect and accessible unavailable/requesting/ready/opening/error states.

Exit: keyboard and VoiceOver can operate the entire player/editor/Whiz path; 200 percent zoom, 320 px width, reduced/still motion, captions, and focus behavior pass.

## Wave 6: Release Candidate

- Run Python, JavaScript, Rust, contract parity, production builds, browser E2E, axe, flash, privacy/egress-denied, sync/fault, performance, and soak gates.
- Verify loopback snapshot-to-ack p95 <= 25 ms and p99 <= 50 ms.
- Verify visible cue-to-audio error p95 <= 50 ms and max <= 100 ms at supported rates.
- Verify seek target within 100 ms with no stale action and settle within 250 ms.
- Verify reconnect <= 2 seconds and <= 100 ms sync within 500 ms of accepted snapshot.
- Produce audiovisual proxies, diagnostic traces, contact sheets, replay hashes, screenshots, checksums, and signed review notes for one candidate pair of commits.
- Deploy Python separately from the existing Rust Wizard service; do not replace any current endpoint.

## Commit and Rollback Policy

- Python and PrismGT stay on separate `codex/` branches with schema parity fixtures.
- Commit by reversible wave: docs/contracts, core runtime, server integration, character mapping, Prism relay, Prism UI, evidence.
- Connector and performance mode are disabled by default until the matching protocol versions and health checks pass.
- Rollback disables the connector/Whiz feature flags and restores legacy player/avatar behavior without deleting generated scores or user edits.
- No push or deployment may overwrite the existing Wizard endpoint or PrismGT production service.

## Completion Rule

Completion means all required code, tests, artifacts, browser evidence, accessibility checks, privacy checks, documentation, commits, pushes, and isolated deployment evidence refer to the same candidate revisions. Skips, retries, placeholders, test-only implementations, unsupported production claims, and documentation-only substitutes do not count.
