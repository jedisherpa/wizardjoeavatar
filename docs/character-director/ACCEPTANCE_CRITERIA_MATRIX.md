# Character Director Acceptance Criteria Matrix

Audit snapshot: 2026-07-15. This matrix covers both current implementation
worktrees:

- Python/Companion: `/Users/paul/Documents/WizardJoeAsci/worktrees/wizardjoe-character-director`
  on `codex/character-director` at implementation commit `84b95fb8aaa4040b9c967c0ef64367ec9139cd26`.
- PrismGT: `/Users/paul/Documents/WizardJoeAsci/worktrees/prism-character-director`
  on `codex/character-director-prism` at implementation commit `0ead02c630fd3e9d9a69d008b19829e82846a7c5`.

This is an acceptance audit, not a declaration of production readiness. The
source changes and automated coverage are substantial, but the goal is not
fully achieved because real connected recordings, browser-driven visual
review, multi-hour evidence, clean-environment reproduction, and a real
upstream permission producer are absent.

## Status definitions

- **Implemented+verified**: present in the current worktrees and exercised by a
  fresh automated command or directly inspectable provenance/documentation.
- **Implemented-not-visually-verified**: code and automated checks exist, but the
  required real-runtime visual/performance review is absent.
- **Partial**: a meaningful portion exists, but the criterion is not complete.
- **Blocked**: the local consumer/relay may exist, but a required external or
  upstream authority is absent.
- **Deferred**: required acceptance work or evidence has not been produced.

## Matrix

| # | DONE WHEN criterion | Status | Evidence and conservative finding |
|---:|---|---|---|
| 1 | Commit `556701a` has been inspected and documented. | **Implemented+verified** | `reports/03-commit-and-provenance.md` records full hash, date, subject, parent, change size, capability, successors, and integration decision; `BASELINE_ENVIRONMENT.md` records the worktree boundary. |
| 2 | Commit `189fbab` has been inspected and documented. | **Implemented+verified** | `reports/03-commit-and-provenance.md` records the same provenance fields for Prism and identifies corrective successor `5910601`; `BASELINE_ENVIRONMENT.md` records the healthy Prism worktree. |
| 3 | The complete connector document has been read. | **Implemented+verified** | The complete 131-line `docs/audiobook-performance/LOCAL_PRISMGT_AUDIO_CONNECTOR.md` was read in this audit with `nl -ba`; `reports/04-prism-connector-specialist.md` also explicitly scopes its review to that canonical document. |
| 4 | Documentation and implementation have been compared. | **Implemented+verified** | `reports/04-prism-connector-specialist.md` contains a requirement-by-requirement documentation-to-code matrix, including incomplete, contradicted, obsolete, and requires-verification findings. |
| 5 | The actual Python visualizer architecture has been mapped. | **Implemented+verified** | `reports/02-python-runtime-architect.md`, `PHASE0_SYNTHESIS.md`, and `BASELINE_ENVIRONMENT.md` map the Uvicorn/asyncio loop, `WizardFrameHub`, command inbox, runtime, controller, frame source, subscribers, Companion process, entry point, packaging, and risks. Current changes preserve that path. |
| 6 | The actual PrismGT integration path has been mapped. | **Implemented+verified** | `reports/04-prism-connector-specialist.md` maps browser audio -> same-origin Rust route -> authenticated loopback relay -> Python coordinator/application. Current code is in `../prism-character-director/src/pages/PrismDodecahedron/media/useMediaSessionConnector.js`, `../prism-character-director/crates/prism-cdiss-cli/src/media_connector.rs`, and `../prism-character-director/crates/prism-cdiss-cli/src/web.rs`. |
| 7 | The existing performance engine has been extended rather than replaced. | **Implemented+verified** | The implementation modifies `wizard_avatar/performance_application.py`, `performance_compiler.py`, `performance_scheduler.py` consumers, `media_session.py`, `runtime.py`, and `stream.py`; new contracts terminate in the existing `CompiledScoreLoader` -> `PerformanceScheduler` -> `PerformanceApplication` path. Fresh Python and integration tests exercise that path. |
| 8 | The existing Prism connector has been extended rather than duplicated. | **Implemented+verified** | Governed context/speech, conversation advisories, and permission relay were added to the existing `useMediaSessionConnector.js`, `media_connector.rs`, and `web.rs`. Fresh Prism JavaScript tests (40), the full locked release build, and `cargo test --workspace -j 1` passed. |
| 9 | A typed, versioned performance context exists. | **Implemented+verified** | `wizard_avatar/performance_context.py` defines frozen V1 dataclasses, exact parsing, canonical hashing, body limits, and live binding checks; `definitions/performance_context_v1.schema.json` and `test_performance_context.py` cover versioning, immutability, privacy, and stale authority. |
| 10 | A typed, versioned character capability manifest exists. | **Implemented+verified** | `wizard_avatar/character_capabilities.py` derives and validates V1 capability records against `definitions/character_capability_manifest_v1.schema.json`; `test_character_capabilities.py` verifies deterministic hashes, admission truth, transitions, contacts, accessibility, tamper rejection, and runtime-gap diagnostics. |
| 11 | A typed, versioned performance score exists. | **Implemented+verified** | The baseline `performance_score.py` and V1/compiled V1 schemas remain authoritative; `performance_compiler.py` adds character-bound compilation and runtime API version 2. `test_performance_score.py`, `test_contract_schemas.py`, and `test_character_bound_compiler.py` passed in full discovery. |
| 12 | High-level direction can compile into supported character behavior. | **Partial** | Deterministic semantic score cues compile and bind to admitted capabilities in `compile_character_bound_performance`; `test_character_bound_compiler.py` proves repeatable runtime-compatible output. There is no implemented parser/planner for the goal's free-form high-level direction examples, so semantic inputs must already be structured. |
| 13 | Unsupported behavior is rejected or explicitly mapped to a valid fallback. | **Implemented+verified** | `performance_compiler.py` rejects renderer IDs/diagnostic poses and emits deterministic fallback records; `test_character_bound_compiler.py` covers unsupported declared fallback, diagnostic pose rejection, raw IDs, channel projection, and smaller-character fallback. |
| 14 | Observable PrismGT latency stages have truthful character behaviors. | **Implemented-not-visually-verified** | Prism maps only correlated server stages into V2 content-free advisories in `useMediaSessionConnector.js`; Python validates stage payloads in `prism_signals.py`. `test_prism_signals.py` and `useMediaSessionConnector.test.js` cover stage mapping, expiry, terminal release, ordering, privacy, and bounded pending state. Deterministic evidence frames cover speaking and interruption, but no real wait/error/timeout Prism performance has been recorded and reviewed. |
| 15 | The character does not expose unapproved output. | **Implemented+verified** | `governed_performance.py` and `performance_release.py` require sink-bound, digest-bound, expiring approval before text/mouth/body release. Prism `approved_reply.rs`, `voice.rs`, `web.rs`, and `governedSpeech.js` bind final approved text, TTS bytes/timing, context, and registration. Python release tests, 9 governed-speech browser tests, 10 Prism approval integration tests, and Rust route tests passed. |
| 16 | Final text can appear in synchronization with voice. | **Implemented-not-visually-verified** | `voice_alignment.py` and `performance_release.py` project approved text reveal and mouth state from media time; `test_voice_alignment.py`, `test_performance_release.py`, and `governedSpeech.test.js` verify Unicode offsets, provider timing, pause/seek/replay, and progressive reveal. No recorded real TTS playback demonstrates visible text/voice sync. |
| 17 | Character animation uses the same authoritative playback timeline. | **Implemented+verified** | `PerformanceScheduler.evaluate(media_time_ms)`, `GovernedSpeechRuntime.evaluate`, and Prism's monotonic speech/media connector use authoritative media time. `test_performance_release.py::test_approved_text_mouth_and_body_share_authoritative_media_time` and cold-seek tests passed. |
| 18 | Play, pause, resume, stop, seek, rate changes, and reconnect are synchronized. | **Implemented+verified** | `media_session.py`, `performance_scheduler.py`, `performance_application.py`, and Prism `useMediaSessionConnector.js` implement the lifecycle. `test_performance_scheduler.py::test_pause_rate_seek_and_reconnect_are_state_equivalent`, media-session lifecycle tests, and 38 fresh Prism media tests passed. This is automated verification, not packaged E2E proof. |
| 19 | Interruption cancels stale performance. | **Implemented+verified** | V2 turn/utterance identity, terminal release, approval revocation, and active-release clearing are implemented in `prism_signals.py`, `performance_release.py`, and `performance_application.py`. `test_prism_signals.py` covers matching/stale terminal behavior; `test_performance_release.py` covers revocation, binding changes, and ownership-safe recovery. |
| 20 | Character movement is purposeful rather than continuous. | **Implemented-not-visually-verified** | Scores use sparse explicit cues, scoreless speech is restrained, media cancels scripted demo locomotion, and gaps resolve to hold/neutral/still in `performance_compiler.py`, `performance_scheduler.py`, and `performance_application.py`. Strict generated-frame quality evidence passes, but no real connected performance review proves the visible result avoids continuous or repetitive motion. |
| 21 | Eye movement has been reviewed. | **Implemented-not-visually-verified** | Gaze targets reach authoritative state and pixel bounds are tested in `test_frame_source.py`, `test_game_control.py`, and `test_performance_application.py`; the generated gaze evidence frame was manually inspected. That is not the required real-time, slow-motion, and frame-by-frame eye review. |
| 22 | Blink timing has been reviewed. | **Implemented-not-visually-verified** | Blink behavior renders and stays within the eye aperture (`test_frame_source.py`, `test_production_animation_wiring.py`), and generated-frame quality checks pass, but no current connected recording or scored review evaluates timing, rhythm, or head-eye coordination. |
| 23 | Hand preparation, stroke, hold, and recovery have been reviewed. | **Partial** | Score phases and clip commit/recovery markers exist (`performance_score.py`, `performance_compiler.py`, `character_capabilities.py`) and scheduler phase tests pass. `reports/05-supervising-animation-director.md` states gestures still require prepare/anticipate/stroke/hold/release/settle admission; no current hand-arc visual review exists. |
| 24 | Locomotion starts, stops, turns, and foot contact have been reviewed. | **Partial** | Locomotion and target-stop tests exist and manifests expose support/planted contacts. The animation-director report says the walk lacks a full reciprocal contact/up/down/passing graph and authored transitions; no current connected recordings or scored foot-contact review exist. |
| 25 | Stillness is used intentionally. | **Partial** | Narrative analysis emits `stillness_target`, scheduler gap policies hold/neutralize, and reduced/still projection suppresses motion. The target is not yet a complete independently reviewed acting policy, and no visual review demonstrates intentional holds across the required scenarios. |
| 26 | Screen resizing and supported aspect ratios work. | **Implemented-not-visually-verified** | Companion `canvas-renderer.js` observes resize and letterboxes a fixed viewport; desktop/mobile stage profiles exist, the letterboxing test passed, and deterministic desktop/portrait evidence PNGs were generated. Live desktop and 390x844 mobile layouts were checked interactively, with one valid 1038x720 desktop screenshot retained under `evidence/character-director/browser-qa/`. A complete portrait/landscape/Retina artifact package and human review are still absent. |
| 27 | Permission-world behavior reflects actual authority. | **Blocked** | Python has a strict content-free projection boundary and visual policy (`permission_world.py`, `performance_application.py`, `frame_source.py`). However, Prism `media_connector.rs::send_permission_world_once` currently calls `PermissionWorldStateV1::build_empty(...)`; it does not read a real canonical permission/grant store. The upstream real permission producer required for production truth is absent. |
| 28 | Denied or revoked permissions remove the corresponding capability. | **Partial** | Injected authoritative states fail closed in `test_permission_world.py`, `test_permission_world_visuals.py`, and `test_permission_world_server.py`; deny/revoke/expiry remove props/effects in Python. The real Prism producer never emits those records, so this is not verified from actual authority end to end. |
| 29 | Persona behavior remains subordinate to PrismGT governance. | **Implemented+verified** | Prism issues exact governed reply records and revalidates them at TTS/relay boundaries; renderer persona overlays are non-authoritative. Fresh Rust tests include `persona::tests::renderer_overlay_cannot_claim_approval_or_authority`, governed bridge tests, and exact approved-reply tests. |
| 30 | Connector messages are versioned and validated. | **Implemented+verified** | Media Session V1, animation signal V2, performance context V1, governed speech/approval V1, voice alignment V1, and permission-world V1 have strict validators, bounded bodies, exact fields, and schemas/fixtures. Python, JavaScript, and Rust contract tests passed. |
| 31 | Stale sessions cannot continue controlling the character. | **Implemented+verified** | `MediaSessionCoordinator` enforces connector session, runtime epoch, sequence, media epoch, and lease identity; V2 advisories and permission snapshots retire old epochs. `test_media_session.py` covers stale epochs, reconnect, takeover, and stale TTS terminal rejection. |
| 32 | Expensive work does not block the render or UI loop. | **Implemented+verified** | `WizardFrameHub` prepares scores off-loop and renders outside the runtime lock; exact retained-replay serialization/hashing is excluded from per-frame diagnostics and remains available on explicit diagnostics/export paths. Focused off-loop, slow-render, and replay-digest tests passed. The authenticated four-viewer soak sustained 23.998 FPS and 59.972 Hz simulation with 42.086 ms p95 frame spacing. |
| 33 | Queues are bounded. | **Implemented+verified** | Command queue/watermarks, replay retention, subscriber queues, render queues, governed events, permission epochs, Prism media relay, conversation advisory pending state, and Companion frame queues have explicit capacities/coalescing/fail-closed behavior. Relevant Python, browser, Companion, and Rust tests passed. |
| 34 | Long-duration playback does not accumulate unacceptable drift or memory growth. | **Deferred** | A fresh authenticated 120-second source soak passed with four normal viewers, one slow viewer, 1,033 requests, 922 controls, 40 Prism signals, zero command/decode/sequence/queue-drop errors, 23.998 FPS, 59.972 Hz simulation, and 42.086 ms p95 frame spacing. Evidence is `evidence/character-director/soak-120s.json` (SHA-256 `6c2cf37e012eaa10ae7b54b09ffc35d2df3fc1d2ea1380e6924b3cdacc8df059`). It is a strong release gate but does not replace the required two-hour, eight-hour, and 24-hour runs. |
| 35 | Reduced-motion behavior works. | **Implemented-not-visually-verified** | Compiler/scheduler projections suppress prohibited channels, permission-world overlays become static, and Prism resolves the user/system motion profile. `test_character_bound_compiler.py`, `test_performance_scheduler.py`, and `test_permission_world_visuals.py` passed; required reduced-motion visual/assistive review is absent. |
| 36 | Automated tests pass. | **Implemented+verified** | Fresh green commands: full Python discovery (428/428), Python scope gate (63 files, zero violations), Companion frontend tests (27/27), Companion Rust tests (17/17), strict animation-quality verification (32/32), Prism frontend tests (40/40), Prism `npm run build`, locked release build, and full Rust workspace tests. The Companion Rust gate was rebuilt after macOS offloaded the worktree target cache to iCloud. |
| 37 | End-to-end recordings demonstrate the real Python visualizer connected to PrismGT. | **Deferred** | No recording in either current worktree demonstrates the governed Character Director path through a real Prism process and Python visualizer. Existing MP4s under `evidence/animation-quality/` predate this implementation and do not show approved Prism reply -> TTS -> context/registration -> synchronized character -> main-media restoration. |
| 38 | The application runs from a documented clean environment. | **Partial** | The pinned sidecar and packaged Tauri supervisor were rebuilt from clean commit `84b95fb8` with `sourceDirty=false`; the live app selected dynamic port 63551, published private discovery, reported ready/running/connector-enabled health, and returned an authenticated performance binding while legacy port 8765 remained live. An independent fresh-clone/clean-user run is still required. |
| 39 | Another engineer can reproduce the system. | **Partial** | `REPRODUCIBLE_SETUP_AND_ROLLBACK.md` and `PRODUCTION_VERIFICATION.md` now provide exact setup, startup, verification, rollback, and evidence commands. They are not yet backed by the final immutable commits and an independent clean-machine or clean-user execution. |
| 40 | Remaining limitations are stated directly. | **Implemented+verified** | This matrix states the missing producer, recordings, visual review, soak, clean-environment, reproduction, high-level language compiler, and motion-quality gaps directly; the specialist reports also preserve unresolved risks rather than converting them into claims. |
| 41 | No planned behavior is described as implemented. | **Implemented+verified** | `PHASE0_TRACKER.md` separates the completed design gate from held implementation/production acceptance, `IMPLEMENTATION_WORKFLOW.md` remains framed as planned work, and this matrix credits only current code/tests/evidence while marking missing acceptance work Partial, Blocked, or Deferred. |

## Acceptance blockers and missing evidence

1. **No real upstream permission producer.** Prism's current heartbeat is an
   identity-bound, monotonic relay, but it always builds an empty permission
   state. A canonical grant/deny/revoke store must produce the strict V1 facts
   before permission-world behavior can claim actual authority.
2. **No current connected recording package.** There is no recording of real
   Prism governed output driving the real Python visualizer through approval,
   TTS, accepted media cursor, progressive text/mouth/body synchronization,
   interruption, permission change, connector loss, and reconnect.
3. **No required connected visual review.** Deterministic desktop, portrait,
   gaze, speaking, interruption, and permission evidence exists and strict
   frame-quality checks pass. Eye motion, blink rhythm, hand phases, foot
   contact, starts/stops/turns, stillness, responsive framing, and reduced
   motion have not yet been reviewed in a real connected performance in real
   time, slow motion, and frame by frame.
4. **No multi-hour acceptance.** The fresh 120-second authenticated concurrency
   soak is clean, but required drift, RSS growth, queue stability, reconnect,
   and shutdown measurements have not been produced for two, eight, or 24
   hours.
5. **No independent clean-user reproduction.** The final commit-backed package
   is live and verified, but it was built in the existing development account.
   A fresh clone or clean-user reproduction and rollback exercise remain.

## Fresh verification commands

```text
# Python worktree
git status --short --branch
.venv/bin/python -m unittest discover -s tests
.venv/bin/python tools/validate_python_scope.py .
node --test tests/*.test.mjs                 # from companion/frontend
cargo test --manifest-path src-tauri/Cargo.toml  # from companion

# Prism worktree
git status --short --branch
node --test \
  src/pages/PrismDodecahedron/media/__tests__/mediaSessionProtocol.test.js \
  src/pages/PrismDodecahedron/media/__tests__/useMediaSessionConnector.test.js \
  src/pages/PrismDodecahedron/media/__tests__/governedSpeech.test.js
cargo test -p prism-cdiss-cli
npm run build
```

## Overall verdict

**Partially achieved.** At this snapshot, 24 criteria are
Implemented+verified, 7 are Implemented-not-visually-verified, 7 are Partial,
1 is Blocked, and 2 are Deferred. Automated correctness, contract coverage,
short concurrency performance, and package supervision are strong; production
acceptance is not justified without the real permission producer, current
Prism-connected recordings and visual review, multi-hour measurements, and a
final clean immutable candidate.
