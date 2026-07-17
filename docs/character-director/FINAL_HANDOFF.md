# Character Director Final Handoff

Date: 2026-07-15

## 1. Executive Summary

The existing ASCILINE Python Wizard Joe runtime now contains a governed,
context-aware Character Director built on the pinned performance engine. The
existing Prism connector now carries approved reply, TTS, timing, observable
stage, media cursor, interruption, and fail-closed permission information into
that runtime. The work does not introduce a second animation engine or a second
Prism connector.

The implementation and short production gates are strong. The overall goal is
**partially achieved**, not production-complete, because real permission facts,
connected Prism recordings, human acting/animation review, multi-hour soaks,
and independent clean-user reproduction remain.

## 2. Repositories, Branches, Commits, And Worktrees

| Surface | Branch | Implementation commit | Worktree |
| --- | --- | --- | --- |
| Python/Companion | `codex/character-director` | `84b95fb8aaa4040b9c967c0ef64367ec9139cd26` | `/Users/paul/Documents/WizardJoeAsci/worktrees/wizardjoe-character-director` |
| Prism | `codex/character-director-prism` | `0ead02c630fd3e9d9a69d008b19829e82846a7c5` | `/Users/paul/Documents/WizardJoeAsci/worktrees/prism-character-director` |

The implementation commits were clean. This handoff is a follow-up
documentation receipt. The original dirty source trees were preserved.

## 3. Commit 556701a

The full baseline commit, parent, date, subject, changed files, successors, and
integration decision are recorded in `reports/03-commit-and-provenance.md`. It
introduced the Python performance-engine foundation that this work extends.

## 4. Commit 189fbab

The full Prism baseline provenance and corrective successor analysis are also
in `reports/03-commit-and-provenance.md`. It introduced the connector path that
this work extends in place.

## 5. Connector-Document Audit

The complete canonical connector document was read and compared with code. The
documentation-to-code matrix is in `reports/04-prism-connector-specialist.md`.
The canonical document itself now includes the Character Director extension and
keeps the browser -> same-origin Prism route -> Rust relay -> Python boundary.

## 6. Current Python Architecture

`WizardFrameHub` remains the single semantic writer. It owns fixed-step runtime
reduction, bounded commands/subscribers/replay, off-loop score preparation, and
off-lock rendering. `MediaSessionCoordinator` owns accepted media identity and
time. `PerformanceScheduler` resolves immutable scores. `PerformanceApplication`
applies only admitted, governed behavior through the existing controller and
renderer.

See `CURRENT_STATE_AND_ARCHITECTURE.md` for the complete authority map.

## 7. Current Prism Architecture

Prism owns approved reply custody, TTS authorization, media playback, and the
authoritative playback cursor. Browser code observes real media and uses only
same-origin routes. The Rust relay holds connector credentials, validates local
discovery, and forwards bounded typed envelopes to Python.

## 8. Specialist Reports

Eleven specialist reports cover coordination, Python runtime, provenance,
connector behavior, animation direction, character technology, context and
compilation, voice timing, permissions/governance, production verification,
and conversational experience. Their index is `reports/README.md`.

## 9. Final Architecture

The binding flow is:

```text
Prism governed result
  -> approved reply registry
  -> digest-bound TTS and alignment
  -> authoritative media cursor
  -> authenticated existing media connector
  -> Python context/release gates
  -> existing scheduler/application/controller
  -> pixel-graph renderer and Companion viewers
```

## 10. Character Capability Manifest

`character_capabilities.py` derives a closed V1 manifest from portable package,
graph, pose-library, runtime-vocabulary, and semantic-map facts. Unsupported and
diagnostic-only behavior is explicit. Current deterministic hash:

`sha256:31755bf2948213f4c068e9658b287561f5968243b143dae81b2cb3faa0f084f9`

Runtime derivation does not read workstation PNGs.

## 11. Performance Context

`PerformanceContextV1` is frozen, versioned, hash-sealed, bounded, content-free
where required, and bound to runtime, character, media, governance, display,
control, and evidence identities. Stale bindings fail closed.

## 12. Buffer-Space Director

Prism produces only observable, correlated stages. Python validates the V2
advisory envelope, sequence, epoch, and expiry. The character can acknowledge,
wait, prepare, verify, recover, or stop without inventing progress or exposing
private reasoning.

## 13. Performance Compiler

The deterministic character-bound compiler maps structured semantic cues to
manifest-admitted behavior, projects motion/accessibility constraints, rejects
raw renderer IDs, and records explicit fallback decisions. A complete
free-form natural-language authoring layer is deferred.

## 14. Performance-Score Model

The existing score/loader/scheduler remains authoritative. New score runtime
binding and validated `ScoreEditsV1` components are additive. Score edits are
not claimed as a complete production publication workflow.

## 15. Text, Voice, And Animation Synchronization

Approved text, audio digest, alignment, utterance identity, and accepted media
cursor are revalidated at release. Progressive text, mouth, and body cues are
pure projections of authoritative media time. Pause, seek, rate, replay, stop,
revoke, reconnect, and stale utterance behavior are covered by tests.

## 16. Prism Connector Changes

The existing connector gained approved-reply custody, exact TTS authorization,
governed speech registration/revocation, content-free stage advisories,
permission-world relay, private discovery refresh, bounded responses, and
main/speech source arbitration. A same-track preference-change bug was fixed to
sample the active source state and is regression-tested.

## 17. Director And Debugging Interface

The Companion exposes a restrained operator surface for runtime health, media
truth, command/gaze/stage previews, pose catalog, content-free cue/replay
inspection, and explicitly simulated permission states. Simulation cannot be
promoted into production authority.

## 18. Files, Modules, Classes, And Functions Changed

The implementation commits are the authoritative file manifests. Principal new
Python modules are:

- `character_capabilities.py`
- `performance_context.py`
- `governed_performance.py`
- `performance_release.py`
- `voice_alignment.py`
- `permission_world.py`
- `score_runtime.py`
- `score_edits.py`

Principal Prism additions are `approved_reply.rs`, `governedSpeech.js`, their
tests, and extensions to `media_connector.rs`, `voice.rs`, `web.rs`,
`useMediaSessionConnector.js`, and `index.jsx`.

## 19. Dependencies Added And Justification

No live frame-by-frame model dependency was added. Companion packaging pins uv
0.11.7, CPython 3.12.10, PyInstaller 6.21.0, and the locked Python web/runtime
dependencies needed for the existing sidecar. Domain state remains standard
Python/Rust/JavaScript contracts rather than a new animation framework.

## 20. Commands Run

Key commands are preserved in `PRODUCTION_VERIFICATION.md`. They include full
Python discovery, scope validation, Companion frontend/Rust tests, strict
animation verification, the authenticated soak, Prism media tests, Prism Vite
build, Prism full Rust workspace tests, locked release build, Git integrity
checks, sidecar build, Tauri build, and live HTTP contract checks.

## 21. Automated Test Results

- Python: 428/428.
- Python scope gate: 63 files, zero violations.
- Companion frontend: 27/27.
- Companion Rust: 17/17.
- Strict animation quality: 32/32.
- Prism media JavaScript: 39/39.
- Prism frontend production build: pass.
- Prism Rust workspace and locked release build: pass.

## 22. Timing And Synchronization Measurements

The 120-second concurrent source soak sustained 23.998 FPS and 59.972 Hz
simulation with 42.086 ms p95 frame spacing. Text/mouth/body share media time;
cursor and lifecycle equivalence are covered by deterministic tests.

## 23. Performance And Memory Measurements

The soak issued 1,033 requests, 922 controls, and 40 Prism signals across four
normal viewers and one slow viewer. It recorded zero command errors, decode
errors, sequence regressions, or hub queue drops, with five schedule overruns.
Two-hour, eight-hour, and 24-hour runs remain.

## 24. Visual-Quality Review

Deterministic desktop, portrait, gaze-left/right, speaking, interruption, and
permission frames are committed. Strict pixel/transition checks pass, and the
permission-denied staff removal was manually inspected. Browser automation had
no available target, and connected real-time/slow-motion/frame-by-frame acting
review remains.

## 25. Governance And Permission Review

Approved sinks are digest-bound, expiring, revocable, and identity-bound.
Stale sessions and utterances fail closed. Persona and advisory layers cannot
claim governance authority. Python permission projection/enforcement is real,
but Prism currently emits an empty fail-closed state because no authoritative
permission producer is connected.

## 26. Packaging And Clean-Environment Results

The final sidecar provenance records Python commit `84b95fb8...` and
`sourceDirty=false`. The ad-hoc signed Tauri app launched on dynamic port 63551,
reported ready health, published private discovery, and returned an
authenticated performance binding while legacy port 8765 stayed live.

Bundle:
`/Users/paul/Library/Caches/Wizard Joe Companion/build-target/release/bundle/macos/Wizard Joe Companion.app`

An independent fresh-clone or clean-user run remains.

## 27. Known Limitations

- No real upstream permission producer.
- No connected governed Prism/TTS recording.
- No complete free-form direction authoring pipeline.
- Score edits are component-only.
- Some speech can use restrained scoreless body behavior.
- No server-confirmed in-flight model-turn cancellation.
- No browser-driven or complete human animation review.
- No multi-hour soak or independent clean-user run.

## 28. Deferred Work

Connect real permission authority, complete live character-bound score
publication, finish in-flight turn cancellation, record governed E2E playback,
conduct professional visual review, run multi-hour package soaks, and execute a
fresh-clone/clean-user install and rollback drill.

## 29. Rollback Instructions

Do not terminate or replace the legacy 8765 process. Quit only the Companion
application it owns, remove its private discovery document if left stale, and
restart the previously verified package or source server. Full commands and
ownership checks are in `REPRODUCIBLE_SETUP_AND_ROLLBACK.md`.

## 30. Exact Reproduction Steps

Use the paired commits above. Follow `REPRODUCIBLE_SETUP_AND_ROLLBACK.md` for
environment setup, pinned sidecar build, signed app build, launch order,
discovery, health/binding checks, Prism connection, tests, evidence generation,
coexistence verification, and shutdown.

## 31. Final Branch And Commit

- Python implementation: `codex/character-director` at
  `84b95fb8aaa4040b9c967c0ef64367ec9139cd26`.
- Prism implementation: `codex/character-director-prism` at
  `0ead02c630fd3e9d9a69d008b19829e82846a7c5`.
- This handoff is committed as a follow-up documentation receipt on the Python
  branch.

## 32. Acceptance-Criteria Matrix

See `ACCEPTANCE_CRITERIA_MATRIX.md` for all 41 criteria, definitions, evidence,
blockers, commands, counts, and conservative status.

## 33. Direct Achievement Statement

**Partially achieved.** The production architecture, governed connector,
deterministic contracts, package supervision, automated correctness, and short
cadence gate are implemented and verified. The goal is not fully achieved until
the real permission producer, connected recordings, professional visual review,
multi-hour runs, and independent clean-user reproduction are complete.
