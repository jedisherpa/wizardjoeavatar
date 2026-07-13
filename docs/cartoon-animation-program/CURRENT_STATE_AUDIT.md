# Cartoon Character Animation Program Current-State Audit

Audit date: 2026-07-13

Audited branch: `codex/python-asciline-avatar`

Starting checkpoint: `988b2315caaafff6a8db66270339123368c1cb76`

Production endpoint: `http://127.0.0.1:8765/`

## Executive verdict

The branch contains a strong and demonstrably working Python ASCILINE avatar
foundation. The persistent local service renders crisp square-cell frames,
moves in world space, supports continuous keyboard/gamepad-shaped control
intents, flies, streams adaptive keyframes and deltas, reconnects, cycles all 89
poses, accepts sanitized Prism cues, and renders speech mouth motion and browser
captions. The current test suite, Python-scope validator, program validator,
strict 32-scenario animation matrix, live browser smoke test, and recorded
ten-minute soak all pass.

The full Cartoon Character Animation Program is not, however, implemented as
described by `IMPLEMENTATION_PLAN.md`. Several of the plan's central components
exist as well-tested modules or validated JSON but are not connected to the live
port-8765 execution path. In particular, the production path does not use
`AvatarRuntime`, `OrderedCommandInbox`, command acknowledgements, replay logs,
the graph-v2 transition topology for ground and action motion, or the character
package's animation graph. Reference-pose expressions and blinking change state
but do not change rendered pixels. The program tracker and registry therefore
overstate completion.

Current rating: **production-capable animated pose demo and control foundation;
partially integrated cartoon animation runtime**.

## Audit boundary

This audit covers:

- the Python branch created from checkpoint `988b231` plus the pose migration
  documented in this report;
- the live ASCILINE Python service running from this checkout on port 8765;
- the program research, planning, tracker, registry, implementation, tests, and
  committed verification evidence;
- behavior exercised through Python, HTTP, WebSocket-backed browser controls,
  and the generated 89-pose library.

This audit excludes concurrent Rust chatbot experiments and unrelated untracked
pose evidence. Those files were preserved in the original worktree and were not
staged or modified by the Python branch integration.

## Python pose integration addendum

The 50 unique feeling/action sources that previously existed only in the Rust
v4 archive are now integrated into the production Python catalog. The Python
manifest and generated square-cell library contain 89 unique pose IDs, and the
browser Play, Repeat, and pose-picker paths discover them from the live API.

`tools/integrate_feelings_into_python.py` makes this migration idempotent and
verifiable from Python-owned metadata and tracked PNG sources. Rust remains
outside both the live architecture and the current rebuild gate; the server
executes only Python and serves only the generated Python cell library.

## Findings

### P1: The deterministic runtime and ordered command system are not in production

The binding architecture says every ingress should flow through ordered command
and signal inboxes into a 60 Hz `AvatarRuntime`, with immutable presentation
snapshots and stable acknowledgements. The implementation contains substantial
and tested versions of those pieces in `runtime.py` and `commanding.py`, but no
production module instantiates `AvatarRuntime`, `OrderedCommandInbox`, or
`ReplayLog`.

The live hub advances `WizardAvatarController` directly once per presentation
deadline, and HTTP/WebSocket commands call controller handlers directly:

- `wizard_avatar/stream.py:86-88` applies commands directly to the frame source.
- `wizard_avatar/stream.py:106-139` drives simulation through the frame loop.
- `wizard_avatar/server.py:107-110` wraps legacy `WizardCommand` and returns a
  state dictionary, not `CommandAckV1`.
- `wizard_avatar/controller.py:41-45` owns a separate float accumulator.

`CommandEnvelopeV1` is used only to validate and arbitrate continuous control
leases. Other commands do not receive source ordering, idempotency, apply ticks,
stable acknowledgement codes, or replay-log coverage.

Impact: the live runtime does not satisfy the plan's central deterministic
replay, command ordering, immutable snapshot, and acknowledgement contract even
though those components pass isolated unit tests.

### P1: Graph v2 is not the authoritative animation state machine

The graph-v2 asset validates all 89 catalog poses. Its clips, nodes, markers,
transitions, recipes, capability tiers, and fallbacks still describe the
original motion set; the 50 additions are classified for direct presentation.
The production selector uses graph v2 only for airborne pose sampling.

- `wizard_avatar/pose_selection.py:65-86` sends grounded behavior to the older
  `reference_avatar_animation_graph.json`.
- `wizard_avatar/pose_selection.py:89-109` implements grounded selection as
  direct idle, walk, and action overrides.
- `wizard_avatar/pose_selection.py:112-144` uses graph v2 only for flight clips.
- `AnimationGraph.select_transition()` has no production caller.

The transition recipes and legal edges are therefore validated data, not live
transition behavior. Ground run, turn, stop, action anticipation, hold,
recovery, interruption windows, contact gates, phase carry, and authored action
clips are not orchestrated by graph v2.

Impact: the code cannot yet claim one data-driven graph for the complete cartoon
character. The live result is better than the original timed gallery, but it is
still a hybrid of legacy ground selection, partial flight clips, pose overrides,
and direct overlays.

### P1: Most authored action poses are unreachable through semantic actions

Graph v2 declares action nodes for guard, block, flourish, staff spin, victory,
shush, celebration, hit reaction, and airborne staff actions. The public action
vocabulary in `wizard_avatar/models.py:31-41` does not accept nine of those graph
actions.

Direct selection evidence from the current code:

| Requested action | Rendered production pose |
|---|---|
| `explaining` | `explaining` |
| `dash` | `run_front_airborne_reach` |
| `thinking` | `front_idle` plus a small bubble overlay |
| `pointing` | `explaining` |
| `magic_cast` | `magic_cast` |
| `reaction` | `magic_cast` on the ground |

The graph-v2 action poses remain visible through the pose picker and repeat demo,
but pose-library reachability is not the same as semantic animation reachability.

Impact: the plan's action vocabulary and action clip inventory are only partly
delivered.

### P1: Reference-pose expressions and blinking do not affect pixels

The live renderer uses the generated reference-pose library. In that path,
`_draw_reference_animation_overlays()` draws speaking mouth motion, magic/reaction
sparks, and thinking bubbles, but it does not render expression or blink changes
(`wizard_avatar/frame_source.py:186-235`). Expression tests exercise
`render_wizard_local()`, which is the procedural fallback rather than the active
reference-pose path.

Fresh audit probes produced identical frame SHA-256 values and zero changed
bytes for:

- `neutral` versus `happy` expression state;
- open-eye versus blink-phase state.

Impact: HTTP/browser/Prism expression state can report success without a visible
face change. This directly misses the plan's independent face and blink channel
acceptance criteria.

### P1: The character package does not control animation behavior

`CharacterPackage` validates and exposes both a pose library and animation
graph. `ProceduralWizardFrameSource` consumes only the package's pose library and
character ID (`wizard_avatar/frame_source.py:52-60`). Pose selection then loads
the global Wizard Joe graph paths declared in `pose_selection.py`, not
`character_package.animation_graph`.

The second-character test proves that an alternate pose library can render. It
does not prove that a second character's graph, action vocabulary, clips,
transitions, anchors, or capabilities drive the runtime.

Impact: reusable character packaging is real at the asset-loader level but is
not yet a complete reusable animation architecture.

### P2: Compatibility state can contradict authoritative motion state

Scripted movement commands set `action = "walking"` with no expiration
(`wizard_avatar/controller.py:143-177`). Locomotion later changes to `idle` when
velocity reaches zero (`wizard_avatar/locomotion.py:29-35`), but nothing clears
the legacy action.

The live audit observed:

```text
locomotion: idle
velocity: {x: 0.0, z: 0.0}
action: walking
animation_node_id: ground_idle
```

Impact: diagnostics and API consumers can receive internally contradictory
state, and action-priority logic can make decisions from a stale compatibility
field.

### Resolved during audit: fixed pose-count assertion

The starting checkpoint rejected any pose catalog whose size was not exactly 39
at `wizard_avatar/animation_graph.py:470`. The Python integration removes that
fixed assertion and retains manifest/library/classification set equality as the
catalog integrity gate.

Result: the current 89-pose library loads without a production code count edit,
and future migrations can expand the data files through the same set-equality
validation.

### P2: The verification suite proves stability more strongly than integration

The 154 tests are valuable and all pass, but some key tests validate components
in isolation or exercise inactive rendering paths:

- runtime and replay tests do not prove use by the live server;
- graph-v2 tests prove loading and clip evaluation, not state-machine execution;
- expression tests use the fallback renderer, not the production reference path;
- the program validator checks documents, ownership, scope, and checkpoint
  presence, not whether every CAP work package is connected;
- the browser pose reel proves all poses can be displayed while moving, not that
  graph-v2 produces believable transitions among them.

Impact: green gates are accurate for the behavior they cover, but the tracker
uses them to justify broader completion claims.

### P3: Hardware gamepad behavior remains implementation-tested only

Keyboard controls, gamepad polling, dead zone, buttons, TTL, release, blur, and
lease logic are implemented. The committed final evidence explicitly states
that no physical gamepad was attached during browser QA.

Impact: low risk to the Python architecture, but the gamepad acceptance claim is
not hardware verified.

## Verified working capabilities

The audit confirmed the following in the actual production path:

| Capability | Current result | Evidence |
|---|---|---|
| Persistent local service | PASS | macOS launch agent is `running`, `RunAtLoad`, and `KeepAlive`; Python PID listens on `127.0.0.1:8765` |
| Python-only production boundary | PASS | `validate_python_scope.py` scanned 47 files with zero violations |
| Program document and ownership structure | PASS | `validate_cartoon_animation_program.py` returned zero errors |
| Full automated suite | PASS | 154 tests in 140.161 seconds after the 89-pose expansion |
| Strict transition matrix | PASS | 32/32 scenarios, zero issues |
| Browser startup and streaming | PASS | live canvas rendered; no browser warnings or errors |
| Repeat mode | PASS | button entered pressed state; world position and pose changed while streaming |
| Flight | PASS | live state reached `airborne: true`, `mobility_mode: hover`, altitude 1.8 |
| Adaptive ASCILINE transport | PASS | live keyframe/delta diagnostics, 24 FPS target, no server queue drops |
| Reconnect/resync infrastructure | PASS | keyframe resync and bounded subscriber queues are active and tested |
| Pose library | PASS | 89 generated square-cell poses are loadable and selectable |
| Speech mouth and captions | PASS | committed browser evidence and focused tests |
| Prism parsing and arbitration | PASS for sanitized state cues | strict parser, ordering/TTL checks, and control-priority tests |
| Ten-minute soak | PASS at implementation checkpoint | 59.986 simulation Hz, 23.994 FPS, 25.914 ms p95, zero command/decode/sequence/queue errors |

## Work-package status correction

| Work package group | Audited status | Notes |
|---|---|---|
| `CAP-000..011` contracts and planning | COMPLETE | Six research reports, four planning reports, integrated plan, workflow, and pushed checkpoint exist |
| `CAP-100` typed command and ack contracts | PARTIAL | Types exist; live routes do not return or schedule through acks |
| `CAP-110` pose census | COMPLETE | 89 Python poses; fixed-count guard removed |
| `CAP-120` graph-v2 schema and validator | COMPLETE AS DATA | Schema, loader, clips, transitions, and validation exist |
| `CAP-130` scope and ownership validation | COMPLETE | Python boundary and program document ownership pass |
| `CAP-200` fixed-tick runtime | IMPLEMENTED, NOT INTEGRATED | Tested `AvatarRuntime` is not instantiated by production |
| `CAP-210` inbox, dedup, replay, hashes | IMPLEMENTED, NOT INTEGRATED | Modules pass tests but are outside the live command path |
| `CAP-220` control lease and priority | COMPLETE FOR CONTINUOUS CONTROL | Active in the live controller |
| `CAP-230` semantic physics | PARTIAL | Ground and flight physics work; state regions and graph coordination are incomplete |
| `CAP-300..320` graph execution and transitions | PARTIAL | Clip evaluation is live for flight; full graph state machine and recipes are not |
| `CAP-330` animation channels | PARTIAL | Speech mouth, sparks, and thinking cue work; reference expressions/blink do not |
| `CAP-400` HTTP/WebSocket adapters | PARTIAL | Backward-compatible routes work; frozen command/ack protocol is not authoritative |
| `CAP-410` hub cadence and fanout | COMPLETE | Live and soak verified |
| `CAP-420` keyboard/gamepad | COMPLETE IN CODE, HARDWARE QA OPEN | Keyboard/browser path verified; physical gamepad not exercised |
| `CAP-440..450` Prism adapter | PARTIAL | Strict and fail-closed inputs work; some mapped expressions have no pixel effect |
| `CAP-500` tests and evidence | COMPLETE WITH COVERAGE GAPS | Good stability suite; integration assertions need strengthening |
| `CAP-600..650` serial promotion | PARTIAL | Foundation is promoted; graph-v2 ground/action and full face channels are not |
| `CAP-700` deterministic replay | UNIT-LEVEL ONLY | No production replay log or live state-hash replay |
| `CAP-710` live browser matrix | COMPLETE FOR CURRENT DEMO | Fresh smoke plus committed evidence pass |
| `CAP-720` mixed-control soak | COMPLETE AT `a5f0cc1` | Ten-minute evidence is committed |
| `CAP-800..810` evidence, push, persistence | COMPLETE | Evidence exists, branch is pushed, service is persistent |

## Documentation assessment

### Strengths

- Research reports are specific, attributed, and grounded in current code and
  primary technical sources.
- The integrated plan has clear architecture, contracts, work packages,
  acceptance gates, and rollback expectations.
- The workflow defines ownership, handoffs, and branch-safety rules.
- Evidence is compact, committed, and includes machine-readable results.
- The Python-only production boundary is unambiguous.

### Corrections needed

- `PROGRAM_TRACKER.md` and `registry.json` should not remain globally
  `COMPLETE` while P1 integration gaps remain.
- Completion should be derived from production-path assertions, not the
  existence and isolated tests of planned modules.
- Future evidence must record the actual active graph version, runtime class,
  command path, and channel-to-pixel deltas.
- Pose expansion should update graph classification and clips without changing
  a fixed count in Python code.

## Recommended recovery order

1. Make `AvatarRuntime` the sole live 60 Hz owner and route every HTTP/WebSocket
   command through `OrderedCommandInbox` with `CommandAckV1`.
2. Introduce one production animation driver that evaluates graph-v2 nodes,
   clips, markers, legal transitions, interrupt windows, and recipes for ground,
   flight, and actions.
3. Remove the legacy graph-v1 ground/action selector after compatibility tests
   prove equivalent baseline behavior.
4. Make the character package's graph path authoritative; retain the new
   manifest/library/classification set-equality catalog gate.
5. Render expression, blink, eye aim, and mouth channels on the reference-pose
   path, then require nonzero pixel deltas for every visible semantic state.
6. Reconcile legacy compatibility fields from authoritative regions so idle
   state cannot report `action: walking`.
7. Add production-path tests that fail when runtime, inbox, graph transitions,
   package graph, or face channels are bypassed.
8. Repeat the browser matrix, deterministic replay, physical gamepad check, and
   ten-minute soak before restoring a global `COMPLETE` status.

## Commands and observations

```text
.venv/bin/python -m unittest discover tests
Result: 154 tests passed in 140.161s

.venv/bin/python tools/integrate_feelings_into_python.py --check
Result: passed; 50 Python metadata records and 89 generated poses verified

.venv/bin/python tools/validate_cartoon_animation_program.py --root .
Result: passed, zero errors, 87 production paths checked

.venv/bin/python tools/validate_python_scope.py .
Result: passed, 47 files scanned, zero violations

.venv/bin/python tools/verify_animation_quality.py --strict
Result: 32/32 scenarios passed, zero issues

Live browser at http://127.0.0.1:8765/
Result: fresh Python worktree build served all 89 pose IDs; every ID rendered
through the live HTTP command path; Repeat moved the avatar; the pose dialog
listed the new feelings poses; no browser warnings or errors

Expression pixel probe
Result: neutral SHA-256 == happy SHA-256; zero changed bytes

Blink pixel probe
Result: open-eye SHA-256 == blink-phase SHA-256; zero changed bytes
```

## Final conclusion

The current branch is a meaningful implementation, not a mock. It has a healthy
live Python service and a valuable set of reusable components. The remaining
work is primarily integration, not invention: the planned runtime, inbox,
graph, transition, package, and channel concepts already exist in useful form.
The next implementation pass should connect those pieces into the one
authoritative production path and add tests that prove the connection.

Until those P1 items are resolved, the honest program status is **PARTIAL:
stable animated avatar foundation with incomplete cartoon-runtime integration**.
