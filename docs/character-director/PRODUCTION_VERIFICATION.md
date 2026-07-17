# Character Director Production Verification

Date: 2026-07-15

Python candidate: `/Users/paul/Documents/WizardJoeAsci/worktrees/wizardjoe-character-director`

Prism candidate: `/Users/paul/Documents/WizardJoeAsci/worktrees/prism-character-director`

## Verdict

**Strong partial acceptance; not production promotion.** The current Character
Director implementation passes its complete Python suite, Companion contract
and supervisor suites, Prism media tests, Prism build, strict generated-frame
quality gate, and a concurrent authenticated 120-second cadence soak. The
packaged Companion supervisor has also demonstrated dynamic-port discovery,
authenticated health and binding, and graceful child shutdown.

Production promotion remains blocked by four external acceptance gaps:

1. Prism does not yet produce permission-world facts from a real authoritative
   grant/deny/revoke store.
2. No retained recording demonstrates a real governed Prism reply and TTS
   driving synchronized text, mouth, body, interruption, and main-media restore.
3. Browser-driven and human frame-by-frame animation review is incomplete.
4. Multi-hour soaks and a final clean immutable package reproduction are still
   required.

This report distinguishes source verification from human/product acceptance.
No green test is presented as proof of acting quality or external authority.

## Candidate Identity

| Repository | Branch | Base HEAD | State at verification |
| --- | --- | --- | --- |
| Python/Companion | `codex/character-director` | `293a2d84d3376eca3084eb0db9b0cd04fee42f08` | Implementation and evidence changes pending final commit |
| Prism | `codex/character-director-prism` | `bf229c28aa7e7a700a63bd5282607ffc77a052c2` | Connector and governed-speech changes pending final commit |

The final paired commit identities must replace these base hashes in the release
receipt after staging and commit. The original dirty source trees and the
legacy Python listener on `127.0.0.1:8765` were not replaced.

## Automated Results

| Surface | Command or gate | Result |
| --- | --- | --- |
| Python runtime | `python3 -m unittest discover -v` | **Pass:** 428/428 in 246.650 s |
| Capability determinism | focused capability and portability suites | **Pass:** 9/9 |
| Python boundary | `python3 tools/validate_python_scope.py .` | **Pass:** 63 files, zero violations |
| Python tools | `python3 -m py_compile` for evidence and soak tools | **Pass** |
| Companion frontend | `npm test` in `companion/frontend` | **Pass:** 27/27 |
| Companion supervisor | `cargo test --manifest-path companion/src-tauri/Cargo.toml` | **Pass:** 17/17 from a rebuilt target |
| Visual contract | `python3 tools/verify_animation_quality.py --strict` | **Pass:** 32/32 |
| Prism media | three media test files via `node --test` | **Pass:** 39/39 |
| Prism preference regression | active-source preference-change test | **Pass:** playback state and reduced-motion profile preserved |
| Prism frontend | `npm run build` | **Pass:** Vite production build |
| Prism Rust | `cargo test --workspace -j 1` | **Pass:** complete workspace before final JavaScript-only fix |
| Prism release | locked release build for `prism-dodeca-cli` | **Pass** |
| Prism repository | `git fsck --full --no-progress` | **Pass** after restoring an iCloud-offloaded packfile |
| Whitespace/format | `cargo fmt --all --check` and `git diff --check` in Prism | **Pass** |

The Companion Rust build initially stalled because macOS had offloaded its
rebuildable `target` cache. A clean local rebuild reached the project but ran
out of disk space; after deleting only rebuildable Rust targets, the normal
target rebuilt and all 17 tests passed. This is an environment incident, not a
waived gate.

## Cadence And Concurrency

The current source server was launched on an isolated dynamic test port with
the app and media connector tokens enabled. The soak drove four normal frame
viewers, one deliberately slow viewer, control traffic, and Prism signals.

| Measurement | Result |
| --- | ---: |
| Requested duration | 120 s |
| Presentation cadence | 23.998 FPS |
| Simulation cadence | 59.972 Hz |
| Frame spacing p95 | 42.086 ms |
| Maximum observed spacing | 200.365 ms |
| Requests | 1,033 |
| Control commands | 922 |
| Prism signals | 40 |
| Command errors | 0 |
| Decode errors | 0 |
| Sequence regressions | 0 |
| Hub queue drops | 0 |
| Schedule overruns | 5 |

Evidence:
`evidence/character-director/soak-120s.json`

SHA-256:
`6c2cf37e012eaa10ae7b54b09ffc35d2df3fc1d2ea1380e6924b3cdacc8df059`

The performance correction moved exact retained-replay serialization and
hashing off the per-frame diagnostics path. Explicit diagnostics and replay
export still compute exact evidence hashes. A regression test prevents that
work from returning to the frame loop.

## Portability

Runtime capability derivation no longer opens the original pose PNGs. Runtime
authority comes from portable pixel-graph/package/manifest hashes. Optional
source-image hashes are used only when embedded in the portable record. A test
replaces source path resolution with a hard failure and confirms manifest
derivation remains successful.

Current deterministic capability-manifest hash:

`sha256:31755bf2948213f4c068e9658b287561f5968243b143dae81b2cb3faa0f084f9`

## Package And Lifecycle

A pinned sidecar build using uv 0.11.7, CPython 3.12.10, and PyInstaller 6.21.0
completed. A packaged Tauri candidate launched its owned Python child on a
dynamic loopback port, published the private discovery document, passed
authenticated health and binding checks, and shut the child down gracefully.
Deep ad-hoc code-sign verification also passed.

That candidate predates the final replay-performance and PNG-portability fixes
and was built while the source tree was dirty. It is evidence for lifecycle
design, not the final release artifact. The final package must be rebuilt from
the immutable commit pair and rerun through the same checks.

## Visual Evidence

Deterministic evidence exists for:

- desktop front idle;
- portrait front idle;
- gaze left and right;
- speaking;
- interruption recovery;
- permission granted;
- permission denied.

The permission-denied frame was manually inspected after the compositor fix:
the staff and staff-only visual residue are removed without opening a cavity in
the character silhouette. Automated checks verify pixel bounds and visual
contracts.

The in-app browser-control runtime exposed no browser target, so no automated
responsive browser screenshots or canvas interaction recording are claimed.
Generated evidence is not a substitute for real-time, slow-motion, and
frame-by-frame human review of gaze, blink rhythm, hand arcs, foot contact,
starts/stops/turns, stillness, and reduced motion.

## Security And Governance

- App and media connector tokens are distinct.
- Connector routes require literal loopback, reject browser origins, validate
  strict bounded JSON, and fail closed.
- Approved text, speech, and animation are sink-bound, digest-bound, expiring,
  revocable, and tied to the accepted media cursor.
- Stale connector sessions, epochs, approvals, and utterances cannot continue
  controlling governed release.
- Advisory Prism states are content-free and cannot claim producer authority.
- Permission simulation is isolated from production permission authority.
- Prism's production permission producer currently emits an empty state; this
  is truthful fail-closed behavior, not a complete permission integration.

## Current Limitations

1. Free-form high-level direction is not yet a complete natural-language
   authoring pipeline; the strongest compiler accepts structured semantic cues.
2. `ScoreEditsV1` is a validated component but is not a complete published
   production editing workflow.
3. Normal governed speech can use restrained scoreless body behavior when no
   externally published character-bound score is attached.
4. A real permission authority producer is absent.
5. Server-confirmed cancellation of an in-flight model turn is separate from
   the implemented stale-performance revocation and remains incomplete.
6. Real connected recordings and human animation review are absent.
7. Two-hour, eight-hour, and 24-hour soak gates remain outstanding.
8. The final immutable-commit package and clean-user reproduction remain.

## Promotion Decision

Do not replace the live `127.0.0.1:8765` service or promote the packaged
candidate yet. Commit both repository halves, rebuild the Companion from the
clean Python commit, verify the paired Prism commit, run the package lifecycle
checks, record a real governed Prism performance, and complete the remaining
visual and long-duration gates first.
