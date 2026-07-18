# Character Director Production Verification

Date: 2026-07-17

Python candidate: `/Users/paul/Documents/WizardJoeAsci/worktrees/wizardjoe-character-director`

Prism candidate: `/Users/paul/Documents/WizardJoeAsci/worktrees/prism-character-director`

## Verdict

**Strong partial acceptance; not production promotion.** The current Character
Director implementation passes its complete Python suite, Companion contract
and supervisor suites, Prism media tests, Prism build, strict generated-frame
quality gate, and a concurrent authenticated 120-second cadence soak. The
packaged Companion supervisor has also demonstrated dynamic-port discovery,
authenticated health and binding, and graceful child shutdown. A fresh GitHub
clone now installs, passes all 428 tests, starts independently, and emits live
ASCILINE frames. A limited real Prism-to-Python screen recording is retained,
and a strict two-hour source soak now passes.

Production promotion remains blocked by three external acceptance gaps:

1. The retained connected recording is silent and does not visibly demonstrate
   the complete short lip-sync interval, interruption, or reconnect sequence.
2. Browser-driven and human frame-by-frame animation review is incomplete.
3. Eight-hour/24-hour V2 soaks plus an independent-user package
   install/rollback are still required; a staged V2 RSS gate now passes.

This report distinguishes source verification from human/product acceptance.
No green test is presented as proof of acting quality or external authority.

## Candidate Identity

| Repository | Branch | Base HEAD | State at verification |
| --- | --- | --- | --- |
| Python/Companion | `codex/character-director` | `4903699c3f6a9a627fd9b52ee3e5058f5e9c2629` | Permission-bound projection code receipt; documentation follows in a separate commit |
| Prism | `codex/character-director-prism` | `a53b48d6626c5494336406aaa9b48bd52460d55e` | Canonical permission producer and exact-ACK code receipt |

The original dirty source trees and the legacy Python listener on
`127.0.0.1:8765` were not replaced.

## Automated Results

| Surface | Command or gate | Result |
| --- | --- | --- |
| Python runtime | `python3 -m unittest discover -s tests` | **Pass:** 450/450 |
| Capability determinism | focused capability and portability suites | **Pass:** 9/9 |
| Python boundary | `python3 tools/validate_python_scope.py .` | **Pass:** 64 files, zero violations |
| Python tools | `python3 -m py_compile` for evidence and soak tools | **Pass** |
| Companion frontend | `npm test` in `companion/frontend` | **Pass:** 27/27 |
| Companion supervisor | `cargo test --manifest-path companion/src-tauri/Cargo.toml` | **Pass:** 17/17 from a rebuilt target |
| Visual contract | `python3 tools/verify_animation_quality.py --strict` | **Pass:** 32/32 |
| Prism media | three media test files via `node --test` | **Pass:** 40/40 |
| Prism preference regression | active-source preference-change test | **Pass:** playback state and reduced-motion profile preserved |
| Prism frontend | `npm run build` | **Pass:** Vite production build |
| Prism core | `cargo test -q -p prism-cdiss-core` | **Pass:** 674/674 primary crate tests plus integration/doc targets |
| Prism CLI | `cargo test -q -p prism-cdiss-cli` | **Pass:** 297/297 unit tests and 10/10 integration tests |
| Prism release | locked release build for `prism-dodeca-cli` | **Pass** |
| Prism repository | `git fsck --full --no-progress` | **Pass** after restoring an iCloud-offloaded packfile |
| Whitespace/format | `cargo fmt --all --check` and `git diff --check` in Prism | **Pass** |
| Fresh GitHub clone | `uv sync --frozen`, full tests, isolated server and WebSocket frame | **Pass:** 428/428, 24.0049 FPS, zero queue drops |
| Soak harness V2 | bounded clients, rolling cadence, loop lag, RSS growth/slope | **Pass:** strict 12-minute staged receipt |

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

The later strict two-hour run used seven normal viewers and one deliberately
slow viewer. It completed 7,200.178 seconds at 59.986 Hz simulation and a 23.1
FPS final presentation window. Across 60,821 requests, 54,254 controls, and
2,345 Prism signals it recorded no command, viewer, decode, sequence, or queue
drop errors. Request latency was 24.197 ms p50 and 55.538 ms p95. The retained
5,370.707 ms maximum and 4,779 schedule overruns require comparison in the
longer gates. The harness did not sample RSS.

Evidence:
`evidence/character-director/soak-2h-2026-07-17.json`

SHA-256:
`7f57f50ed191a5b182f00b569d3db0909e7a6011b3c615415afe21e1a3e37b82`

See `SOAK_2H_2026-07-17.md` for the exact command and conservative finding.

The replacement V2 harness bounds the client receive queue and message size,
binds RSS samples to the authenticated health PID, keeps a bounded full-run
latency histogram, and evaluates cadence, queue pressure, event-loop lag, and
memory in rolling windows. Its staged 721.110-second strict run passed at
59.995 Hz simulation and 24.007 FPS presentation with zero rolling cadence
breaches, 1.871 ms event-loop-lag p95, 1,916,928 bytes peak RSS growth, and an
8,038,419.286 bytes/hour slope over 601.096 post-warm-up seconds. Normal viewers
had zero connection, decode, or sequence errors. The deliberate slow viewer
reconnected 12 times and exposed 73.220 queue drops per minute within the
declared bounded-backpressure threshold.

Evidence:
`evidence/character-director/soak-v2-12m-2026-07-17.json`

SHA-256:
`f4c306bc79525f9374726650f290105f0d11d2f450609b4c36e411bc48e9e0de`

See `SOAK_HARNESS_V2.md`. This validates the V2 harness and staged RSS gate; it
does not substitute for eight-hour and 24-hour V2 acceptance runs.

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

`sha256:08b22488f8eb8a71e70fe2977afd45ec7f323b7742adccd4ea01218fb46ac104`

## Package And Lifecycle

A pinned sidecar build using uv 0.11.7, CPython 3.12.10, and PyInstaller 6.21.0
completed. A packaged Tauri candidate launched its owned Python child on a
dynamic loopback port, published the private discovery document, passed
authenticated health and binding checks, and shut the child down gracefully.
Deep ad-hoc code-sign verification also passed.

The final package was rebuilt from clean Python commit `84b95fb8`; its embedded
provenance records the full commit and `sourceDirty: false`. It launched on
dynamic port `63551`, published the private discovery document, reported
`ready` health with the frame hub running and connector enabled, and returned a
valid authenticated performance binding for `wizard-joe-v1`. At the same time,
the legacy process continued answering its real state contract on port 8765.

Bundle:
`/Users/paul/Library/Caches/Wizard Joe Companion/build-target/release/bundle/macos/Wizard Joe Companion.app`

This proves the committed package and coexistence path in the current account.
A fresh source clone has now independently reproduced install, tests, startup,
and streaming under the current account. It does not replace a clean-user or
clean-machine package installation and rollback drill. See
`CLEAN_CLONE_REPRODUCTION_2026-07-17.md`.

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

The in-app browser runtime subsequently verified the live canvas and controls
at desktop and mobile sizes. One valid 1038x720 desktop screenshot and a
machine-readable manifest are retained under
`evidence/character-director/browser-qa/`. The 390x844 mobile layout was checked
interactively, but no valid mobile screenshot was retained. This is layout and
control evidence, not a connected audiovisual or professional acting review.
The later `evidence/character-director/connected-e2e-2026-07-17/` package adds a
25.49-second 1280x720 live Prism-to-Python capture, exact frame timing, a
contact sheet, and sanitized cursor transitions. It proves a real connected
turn and live rendering, but it is silent and does not visibly isolate the
short lip-sync lifecycle, so the professional audiovisual gate remains open.
Generated evidence is not a substitute for real-time, slow-motion, and
frame-by-frame human review of gaze, blink rhythm, hand arcs, foot contact,
starts/stops/turns, stillness, and reduced motion.

The same live pass found that Prism's "Open Wizard" link was hardcoded to the
legacy port even when the connector was bound to an isolated runtime. Prism now
opens `/api/connectors/wizard/visualizer`, whose Rust handler derives a
credential-free root URL from the active validated loopback relay and returns a
temporary `no-store`, `no-referrer` redirect. Browser and HTTP checks confirmed
that the isolated connector opened `http://127.0.0.1:8875/` while the legacy
8765 process remained untouched.

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
- Prism derives production character permission facts from its canonical
  `AgreementStore`; the relay remains content-free and exact-ACK-bound.
- Permission-bound memory writes are linearized with revoke and expiry, and
  Python revalidates authority again at frame publication.

## Current Limitations

1. Controlled-language high-level direction V1 now compiles the required
   examples through the existing runtime; unrestricted natural language and
   arbitrary choreography remain unsupported.
2. `ScoreEditsV1` is a validated component but is not a complete published
   production editing workflow.
3. Normal governed speech can use restrained scoreless body behavior when no
   externally published character-bound score is attached.
4. Server-confirmed cancellation of an in-flight model turn is separate from
   the implemented stale-performance revocation and remains incomplete.
5. A limited connected recording exists; complete audiovisual and human
   animation review are absent.
6. The staged bounded-client/RSS V2 soak passes; eight-hour and 24-hour V2
   gates remain outstanding.
7. Fresh-clone source reproduction passes; independent-user package install
   and rollback remain.

## Promotion Decision

Do not replace the live `127.0.0.1:8765` service or promote the packaged
candidate as production yet. The paired commits and clean package lifecycle are
verified; record a real governed Prism performance and complete the remaining
visual, clean-user, rollback, and long-duration gates
first.
