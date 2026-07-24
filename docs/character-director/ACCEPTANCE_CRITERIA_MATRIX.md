# Character Director Acceptance Criteria Matrix

Audit snapshot: 2026-07-18. This matrix covers both current implementation
worktrees:

- Python/Companion: `/Users/paul/Documents/WizardJoeAsci/worktrees/wizardjoe-character-director`
  on `codex/character-director` at code receipt commit `b7b6101c86b6abd04622935331684b76e3ce8591`.
- PrismGT: `/Users/paul/Documents/WizardJoeAsci/worktrees/prism-character-director`
  on `codex/character-director-prism` at code receipt commit `a53b48d6626c5494336406aaa9b48bd52460d55e`.

This is an acceptance audit, not a declaration of production readiness. The
source changes and automated coverage are substantial, but the goal is not
fully achieved because complete audiovisual acting review, multi-hour
evidence, and independent clean-user/package reproduction are absent.

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
| 8 | The existing Prism connector has been extended rather than duplicated. | **Implemented+verified** | Governed context/speech, conversation advisories, permission relay, and a credential-free visualizer redirect derived from the active validated relay were added to the existing `useMediaSessionConnector.js`, `media_connector.rs`, and `web.rs`. Fresh Prism JavaScript tests (40), the full locked release build, and Rust tests passed; live browser and HTTP checks confirmed the redirect targeted isolated Python port 8875 without replacing legacy 8765. |
| 9 | A typed, versioned performance context exists. | **Implemented+verified** | `wizard_avatar/performance_context.py` defines frozen V1 dataclasses, exact parsing, canonical hashing, body limits, and live binding checks; `definitions/performance_context_v1.schema.json` and `test_performance_context.py` cover versioning, immutability, privacy, and stale authority. |
| 10 | A typed, versioned character capability manifest exists. | **Implemented+verified** | `wizard_avatar/character_capabilities.py` derives and validates V1 capability records against `definitions/character_capability_manifest_v1.schema.json`; `test_character_capabilities.py` verifies deterministic hashes, admission truth, transitions, contacts, accessibility, tamper rejection, and runtime-gap diagnostics. |
| 11 | A typed, versioned performance score exists. | **Implemented+verified** | The baseline `performance_score.py` and V1/compiled V1 schemas remain authoritative; `performance_compiler.py` adds character-bound compilation and runtime API version 2. `test_performance_score.py`, `test_contract_schemas.py`, and `test_character_bound_compiler.py` passed in full discovery. |
| 12 | High-level direction can compile into supported character behavior. | **Implemented+verified** | `direction_compiler.py` and the closed `HighLevelDirectionRequestV1` contract compile both required high/mid-level examples into semantic-only portable cues, exact context/media bindings, admitted character capabilities, scheduler stage movement, and an actual `PerformanceApplication`/`WizardAvatarController` position change. Eight tests prove repeatability, ordering, governance, stale-context rejection, reduced motion, and loader/runtime compatibility. V1 is controlled language, not unrestricted natural language. |
| 13 | Unsupported behavior is rejected or explicitly mapped to a valid fallback. | **Implemented+verified** | The direction compiler rejects unsupported clauses and governed-intent mismatches without echoing content, and records circle-to-linear trajectory fallback explicitly. `performance_compiler.py` separately rejects renderer IDs/diagnostic poses and records capability fallback; both layers have focused regression coverage. |
| 14 | Observable PrismGT latency stages have truthful character behaviors. | **Implemented-not-visually-verified** | Prism maps only correlated server stages into V2 content-free advisories in `useMediaSessionConnector.js`; Python validates stage payloads in `prism_signals.py`. `test_prism_signals.py` and `useMediaSessionConnector.test.js` cover stage mapping, expiry, terminal release, ordering, privacy, and bounded pending state. Deterministic evidence frames cover speaking and interruption, but no real wait/error/timeout Prism performance has been recorded and reviewed. |
| 15 | The character does not expose unapproved output. | **Implemented+verified** | `governed_performance.py` and `performance_release.py` require sink-bound, digest-bound, expiring approval before text/mouth/body release. Prism `approved_reply.rs`, `voice.rs`, `web.rs`, and `governedSpeech.js` bind final approved text, TTS bytes/timing, context, and registration. Python release tests, 9 governed-speech browser tests, 10 Prism approval integration tests, and Rust route tests passed. |
| 16 | Final text can appear in synchronization with voice. | **Implemented-not-visually-verified** | `voice_alignment.py` and `performance_release.py` project approved text reveal and mouth state from media time; `test_voice_alignment.py`, `test_performance_release.py`, and `governedSpeech.test.js` verify Unicode offsets, provider timing, pause/seek/replay, and progressive reveal. No recorded real TTS playback demonstrates visible text/voice sync. |
| 17 | Character animation uses the same authoritative playback timeline. | **Implemented+verified** | `PerformanceScheduler.evaluate(media_time_ms)`, `GovernedSpeechRuntime.evaluate`, and Prism's monotonic speech/media connector use authoritative media time. `test_performance_release.py::test_approved_text_mouth_and_body_share_authoritative_media_time` and cold-seek tests passed. |
| 18 | Play, pause, resume, stop, seek, rate changes, and reconnect are synchronized. | **Implemented+verified** | `media_session.py`, `performance_scheduler.py`, `performance_application.py`, and Prism `useMediaSessionConnector.js` implement the lifecycle. `test_performance_scheduler.py::test_pause_rate_seek_and_reconnect_are_state_equivalent`, media-session lifecycle tests, and 38 fresh Prism media tests passed. This is automated verification, not packaged E2E proof. |
| 19 | Interruption cancels stale performance. | **Implemented+verified** | V2 turn/utterance identity, terminal release, approval revocation, and active-release clearing are implemented in `prism_signals.py`, `performance_release.py`, and `performance_application.py`. Ordered `speech_stop` is now a distinct interruption command rather than a reset/stop alias; browser callbacks carry the expected speech ID, so an obsolete callback cannot cancel a replacement utterance. Focused tests prove mouth closure with root/facing/gaze/locomotion continuity and stale callback rejection. |
| 20 | Character movement is purposeful rather than continuous. | **Implemented-not-visually-verified** | Scores use sparse explicit cues, scoreless speech is restrained, media cancels scripted demo locomotion, and gaps resolve to hold/neutral/still in `performance_compiler.py`, `performance_scheduler.py`, and `performance_application.py`. Strict generated-frame quality evidence passes, but no real connected performance review proves the visible result avoids continuous or repetitive motion. |
| 21 | Eye movement has been reviewed. | **Partial** | Transactional presentation and simulation-tick head-eye state are covered by focused race, rerender, retarget, reconnect, and actual-pixel tests. Commit `3054c97` removes the late settle snap by re-centering gaze when the authored head view reaches its target; 42 gaze frames and 36 front/back turn frames from a clean 332-frame runtime run are retained in `gaze-settle-3054c97-2026-07-18`. The prior two-reviewer 2/4 result remains the release finding until the dedicated V1 scene receives normal-speed, quarter-speed, and two-reviewer acceptance. |
| 22 | Blink timing has been reviewed. | **Partial** | `BlinkScheduler` provides replay-stable 2.5-6.5-second open intervals and 100-200 ms closures. One reviewer identified a clean roughly 125 ms blink; the second could not establish a blink series. The required 60-second rhythm, interval variation, and full two-reviewer category score remain open. |
| 23 | Hand preparation, stroke, hold, and recovery have been reviewed. | **Partial** | Candidate `b7b6101` binds effect onset/decay to authored cast frames and the current staff tip, holds `action_settled` before retirement, and passes focused tests. Independent review still rejects release: whole-pose staff/hand changes jump by tens of output cells, recovery is too short, and transient 60 Hz markers are absent from the accepted 24 FPS trace. Three repeated casts and V7 pre/post-commit visual variants remain open. |
| 24 | Locomotion starts, stops, turns, and foot contact have been reviewed. | **Partial** | V6 machine acceptance now passes at `17637c53`: 222 contiguous owned frames, zero drops or clipping, readable three-sector 90-degree turn, readable five-sector 180-degree reversal, complete 16-pose left/right profile gaits, exact target arrival, explicit release phases, and a six-pose stop/settle. The contact verifier reports 115 contact frames across 17 stances, `2.842170943040401e-14` maximum planted drift, 1-cell maximum raster-span drift, zero root residual, and no issues. See `V6_DIRECTIONAL_ACCEPTANCE_2026-07-23.md`. Status remains partial until normal-speed, quarter-speed, frame-by-frame, and independent human animation review accepts the presentation. |
| 25 | Stillness is used intentionally. | **Partial** | Narrative analysis emits `stillness_target`, scheduler gap policies hold/neutralize, and reduced/still projection suppresses motion. The target is not yet a complete independently reviewed acting policy, and no visual review demonstrates intentional holds across the required scenarios. |
| 26 | Screen resizing and supported aspect ratios work. | **Implemented-not-visually-verified** | Companion `canvas-renderer.js` observes resize and letterboxes a fixed viewport; desktop/mobile stage profiles exist, the letterboxing test passed, and deterministic desktop/portrait evidence PNGs were generated. Live desktop and 390x844 mobile layouts were checked interactively, with one valid 1038x720 desktop screenshot retained under `evidence/character-director/browser-qa/`. A complete portrait/landscape/Retina artifact package and human review are still absent. |
| 27 | Permission-world behavior reflects actual authority. | **Implemented+verified** | Prism now derives content-free `PermissionAuthorityRecord` facts from the canonical `AgreementStore`, limited to internal scope `local_character_runtime`, and relays them through the existing exact-ACK connector. Python binds `prop:memory_notebook` to exact scope `current_character`, purpose `conversation_continuity`, and surface `wizard.stage`, then projects a 7x7 square-cell notebook overlay through the existing frame projector. Wrong purpose/scope/surface, malformed facts, expired authority, stale epochs, and obsolete connector generations fail closed. See `PERMISSION_WORLD_AUTHORITY_2026-07-17.md`. |
| 28 | Denied or revoked permissions remove the corresponding capability. | **Implemented+verified** | `/rag on` creates and confirms the typed canonical authority; `/rag off` revokes it. Memory reads and writes and the Python visual capability disappear on revoke/deny/expiry. Protected writes are linearized with revoke/expiry under the authority-store lock; frame publication reprojects authority after rendering and discards stale or expired in-flight frames. End-to-end, contention, projection, and visual tests cover grant, revoke, expiry, unlink, mismatch, and obsolete ACK paths. |
| 29 | Persona behavior remains subordinate to PrismGT governance. | **Implemented+verified** | Prism issues exact governed reply records and revalidates them at TTS/relay boundaries; renderer persona overlays are non-authoritative. Fresh Rust tests include `persona::tests::renderer_overlay_cannot_claim_approval_or_authority`, governed bridge tests, and exact approved-reply tests. |
| 30 | Connector messages are versioned and validated. | **Implemented+verified** | Media Session V1, animation signal V2, performance context V1, governed speech/approval V1, voice alignment V1, and permission-world V1 have strict validators, bounded bodies, exact fields, and schemas/fixtures. Python, JavaScript, and Rust contract tests passed. |
| 31 | Stale sessions cannot continue controlling the character. | **Implemented+verified** | `MediaSessionCoordinator` enforces connector session, runtime epoch, sequence, media epoch, and lease identity; V2 advisories and permission snapshots retire old epochs. `test_media_session.py` covers stale epochs, reconnect, takeover, and stale TTS terminal rejection. |
| 32 | Expensive work does not block the render or UI loop. | **Implemented+verified** | `WizardFrameHub` prepares scores off-loop and renders outside the runtime lock; exact retained-replay serialization/hashing is excluded from per-frame diagnostics and remains available on explicit diagnostics/export paths. Transition lifecycle advances only in authoritative simulation resolution; stale candidates cannot commit contact state or append `animation_truth_trace_v1`. Focused purity/off-loop tests, 340 contiguous external frames, and the prior concurrency soak pass. |
| 33 | Queues are bounded. | **Implemented+verified** | Command queue/watermarks, replay retention, subscriber queues, render queues, governed events, permission epochs, Prism media relay, conversation advisory pending state, and Companion frame queues have explicit capacities/coalescing/fail-closed behavior. Relevant Python, browser, Companion, and Rust tests passed. |
| 34 | Long-duration playback does not accumulate unacceptable drift or memory growth. | **Partial** | Soak harness V2 now uses bounded WebSocket clients, fixed-retention samples, rolling cadence windows, event-loop lag, authenticated server-PID continuity, and warm-up-aware RSS growth/slope gates. Its strict 12-minute staged run passed at 59.995 Hz and 24.007 FPS with zero rolling cadence breaches, 1.871 ms loop-lag p95, 1,916,928 bytes peak RSS growth, and an 8,038,419 bytes/hour slope across 601 seconds. See `SOAK_HARNESS_V2.md` and `soak-v2-12m-2026-07-17.json` (SHA-256 `f4c306bc79525f9374726650f290105f0d11d2f450609b4c36e411bc48e9e0de`). The historical two-hour V1 run remains duration/throughput evidence but had an unbounded client queue and no RSS sampling. Eight-hour and 24-hour V2 gates remain. |
| 35 | Reduced-motion behavior works. | **Implemented-not-visually-verified** | Compiler/scheduler projections suppress prohibited channels, permission-world overlays become static, and Prism resolves the user/system motion profile. `test_character_bound_compiler.py`, `test_performance_scheduler.py`, and `test_permission_world_visuals.py` passed; required reduced-motion visual/assistive review is absent. |
| 36 | Automated tests pass. | **Implemented+verified** | Current Python discovery contains 517 passing tests in 289.669 seconds and the production-scope validator scans 67 files with zero violations. New tests cover atomic animation truth, forced-keyframe pairing, contact locking/drift rejection, authored reversal/stop, cast marker/effect timing, committed recovery, speech continuity, and stale candidate exclusion. The paired permission-authority and prior Companion/Prism gates remain recorded in `PRODUCTION_VERIFICATION.md`. |
| 37 | End-to-end recordings demonstrate the real Python visualizer connected to PrismGT. | **Partial** | `evidence/character-director/connected-e2e-2026-07-17/` retains a 25.49-second 1280x720 H.264 capture, frame timing, contact sheet, sanitized cursor transitions, hashes, prompt, and conservative interpretation from live Prism `8890` to Python `8875`. The cursor advanced and main media was restored, but the silent screen recording and collapsed public status snapshots do not visibly prove the complete short lip-sync interval, interruption, permission change, loss, or reconnect. |
| 38 | The application runs from a documented clean environment. | **Partial** | The pinned packaged candidate remains proven from clean commit `84b95fb8` with `sourceDirty=false`. A fresh GitHub clone of pushed commit `cee9de8` also installed from `uv.lock`, passed 428 tests, started independently on port 8876, emitted a valid ASCILINE bootstrap and binary frame, and reported 24.0049 FPS with zero queue drops while legacy 8765 stayed live. See `CLEAN_CLONE_REPRODUCTION_2026-07-17.md`. An independent operating-system user/package install and rollback remain. |
| 39 | Another engineer can reproduce the system. | **Partial** | `REPRODUCIBLE_SETUP_AND_ROLLBACK.md`, `PRODUCTION_VERIFICATION.md`, and `CLEAN_CLONE_REPRODUCTION_2026-07-17.md` provide and exercise setup, startup, verification, rollback, and evidence commands. Source reproduction from the immutable pushed commit is now proven in a fresh directory, including the declared historical checkpoint fetch. A clean-machine or independent-user package/rollback execution is still absent. |
| 40 | Remaining limitations are stated directly. | **Implemented+verified** | This matrix states the incomplete recordings, visual review, soak, clean-environment, reproduction, unrestricted-language authoring, multi-user authority, and motion-quality gaps directly; the specialist reports also preserve unresolved risks rather than converting them into claims. |
| 41 | No planned behavior is described as implemented. | **Implemented+verified** | `PHASE0_TRACKER.md` separates the completed design gate from held implementation/production acceptance, `IMPLEMENTATION_WORKFLOW.md` remains framed as planned work, and this matrix credits only current code/tests/evidence while marking missing acceptance work Partial, Blocked, or Deferred. |

## Acceptance blockers and missing evidence

1. **The connected recording package is incomplete.** A real Prism-to-Python
   turn, cursor transition, and live rendering are retained, but the recording
   is silent and the short speech lifecycle was not separately visible in the
   sampled public status route. It does not prove scored lip sync,
   interruption, permission change, connector loss, and reconnect.
2. **The atomic-contact director review rejects release.** The clean-commit
   run under
   `evidence/character-director/atomic-contact-lock-b7b6101-2026-07-18/`
   retains 340 contiguous 24 FPS frames with zero loss, exact trace coverage,
   a passing declared-contact report, and manifest SHA-256
   `687cb9319c3b5f595e11b559ded9e10ee18dbba42dc1c1caf32521eddeed7c17`.
   Independent scores are 41/100 and 42/100. Reviewers identify missing
   external-runtime identity, missing decoded-raster contact proof, transient
   marker loss, subscriber-overflow transport ambiguity, idle stride resets,
   weak reversal anticipation, stop/profile pop, staff/hand discontinuity, and
   the incomplete V1-V10/browser/audio/reduced-motion matrix. See
   `ATOMIC_ANIMATION_TRUTH_2026-07-18.md` and the two bound review reports.
3. **Long-duration acceptance remains incomplete.** The strict staged V2 run
   passed bounded-client, rolling-cadence, loop-lag, and RSS gates, while the
   historical two-hour V1 run remains duration/throughput evidence only.
   Explicit connector loss/shutdown plus eight-hour and 24-hour V2 runs remain.
4. **No independent clean-user reproduction.** Fresh-clone source install,
   tests, startup, and ASCILINE streaming are proven under the current account.
   A separate operating-system user or clean machine package installation and
   rollback exercise remain.

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

**Partially achieved.** At this snapshot, 26 criteria are
Implemented+verified, 7 are Implemented-not-visually-verified, 8 are Partial,
0 are Blocked, and 0 are Deferred. Automated correctness, contract coverage,
short concurrency performance, package supervision, fresh-clone source
reproduction, and a limited connected capture are strong; production
acceptance is not justified without complete audiovisual review, the
remaining long-duration/RSS measurements, and
independent package/rollback reproduction.
