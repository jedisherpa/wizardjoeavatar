# Research Wave 1: Project Delivery and Multi-Agent Execution

- Role: `PLAN`, project planning and multi-agent delivery expert
- Audit date: 2026-07-12
- Audited branch: `codex/build-repeatable-avatar-animation`
- Audited commit: `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1` plus the exact dirty working tree
- Production target: ASCILINE Python service at `http://127.0.0.1:8765/`

## 1. Scope correction and non-negotiable boundary

The implementation program must be Python-only. The production system is:

```text
semantic remote command
  -> Python WizardAvatarController
  -> Python fixed-step locomotion and animation state
  -> Python procedural pose/cell compositor
  -> Python ASCILINE encoder and authoritative frame hub
  -> FastAPI HTTP/WebSocket delivery on port 8765
  -> web/avatar browser client and Canvas renderer
```

The Rust directories and Rust evidence are a prior side-track. They may be inspected for general systems lessons, but they must not be staged into the Python baseline, imported by Python, invoked by CI, required by an acceptance gate, or used to substantiate a port-8765 claim. This boundary is now recorded in the program contract at `docs/cartoon-animation-program/README.md:9-11` and `docs/cartoon-animation-program/README.md:42-47`, and in the machine-readable registry at `docs/cartoon-animation-program/registry.json:3-10`.

## 2. Executive finding

The repository has a credible Python runtime baseline, but not yet a deliverable animation program baseline.

The strongest existing foundation is:

- 39 deterministic canonical poses with a fixed `72 x 96` canvas and root `[36, 95]` (`wizard_avatar/definitions/reference_avatar_pose_cells.json:1-15`, `evidence/pose-library-expansion/POSE_EXPANSION_COMPLETION.md:5-15`).
- One server-authoritative frame hub that advances and fans out a shared Python stream (`wizard_avatar/stream.py:28-65`, `wizard_avatar/stream.py:104-145`).
- A 60 Hz fixed-step locomotion controller rendered at 24 FPS (`wizard_avatar/locomotion.py:13-15`, `wizard_avatar/frame_source.py:41-67`).
- Semantic HTTP and WebSocket commands on the live Python service (`wizard_avatar/server.py:65-128`, `wizard_avatar/server.py:136-173`).
- A deterministic generator, 62 passing Python tests, a 32/32 strict transition matrix, and a live browser pose reel that showed all 39 poses while moving (`evidence/pose-library-expansion/POSE_EXPANSION_COMPLETION.md:25-45`).

The largest gap is that the 39 images are mostly catalog entries, not a connected animation vocabulary. The active animation graph only provides eight idle facings, six action mappings, and sparse walk clips (`wizard_avatar/definitions/reference_avatar_animation_graph.json:6-24`, `wizard_avatar/definitions/reference_avatar_animation_graph.json:25-164`). It has no run, takeoff, flight, bank, land, crouch, staff-combat, celebration, or recovery state machine even though the manifest contains those pose families. The browser Play action is a timed library showcase, not character control: it places every pose above an independently running looping path for 900 ms (`web/avatar/wizardControls.ts:48-84`).

The program should therefore proceed as an interface-first migration from `pose override + short whole-pose transition` to a deterministic semantic motion graph, while preserving the current Python ASCILINE transport and the 39-pose asset baseline.

## 3. Exact current-state audit

### 3.1 Product authority is clear, but the written contracts conflict

`AGENTS.md:5-9` says the numbered documents are the product and acceptance contract. `CODEX_GOAL.md:7-9` requires a server-authoritative procedural character rather than prerecorded or flattened playback. The current implementation satisfies the important architectural direction: the browser receives generated cell frames rather than displaying source PNGs.

However, there is an acceptance contradiction that must be resolved before implementation starts:

- The current README says rainbow wings are required (`README.md:13-26`).
- The legacy visual tests and completion gate say there must be no wings (`docs/30-visual-tests.md:36-49`, `docs/37-completion-gate.md:3-8`).
- The generated `front_idle` pose itself is tagged `wings` (`wizard_avatar/definitions/reference_avatar_pose_cells.json:53-64`).

The current user-approved visual direction includes wings and flying. The planning checkpoint must amend or supersede the stale no-wings requirements explicitly. Otherwise separate agents can both be locally correct while producing mutually exclusive work.

### 3.2 The production runtime is already semantic and server-authoritative

The state model separates world position, velocity, facing, locomotion, action, upper body, expression, mouth, gait phase, staff, speech, presentation pose, and pose override (`wizard_avatar/models.py:67-128`). Commands are dispatched through one controller (`wizard_avatar/controller.py:16-41`). Simulation advances in bounded fixed steps (`wizard_avatar/controller.py:24-31`), and locomotion derives walk phase from distance traveled rather than render count (`wizard_avatar/locomotion.py:76-97`).

The frame source projects world state, selects a reference pose, anchors it to the fixed stage, overlays face/mouth effects, and emits ASCILINE cells (`wizard_avatar/frame_source.py:69-131`). The hub owns one frame-production loop and publishes one encoded result to all subscribers (`wizard_avatar/stream.py:104-145`). This is the correct production spine and must not be replaced by a second renderer or a client-authoritative sprite engine.

### 3.3 The integrated pose library is broad but directionally imbalanced

The current manifest has 39 poses:

- 17 idle-tagged poses
- 9 flying poses
- 5 walking poses
- 3 running poses
- 2 jump poses
- 1 airborne pose
- 1 kneel pose
- 1 landing pose

Direction coverage is heavily front-biased: 26 poses face south, 6 southeast, 2 southwest, and only one each east, west, north, northeast, and northwest. The generated library does guarantee every pose shares a canonical canvas and root (`tests/wizard/test_reference_avatar_pose_library.py:23-40`). This makes the assets safe inputs to a graph, but it does not make every pose interchangeable in every direction.

Planning consequence: motion families must declare supported facings and approved fallback behavior. The program must not promise eight-direction flight or eight-direction action cycles until assets exist or the animation expert approves coherent mirrored/procedural variants.

### 3.4 The active graph uses only a small subset of the new range

The graph maps all eight idle facings, but southeast and southwest idle currently resolve to walking poses (`wizard_avatar/definitions/reference_avatar_animation_graph.json:7-16`). Side walking is a one-pose hold (`wizard_avatar/definitions/reference_avatar_animation_graph.json:68-77`, `wizard_avatar/definitions/reference_avatar_animation_graph.json:137-146`). Front and back walking use only two stride poses with idle inserted as contact frames (`wizard_avatar/definitions/reference_avatar_animation_graph.json:25-50`, `wizard_avatar/definitions/reference_avatar_animation_graph.json:95-119`).

The remaining new poses are reachable primarily through the presentation override. That override outranks locomotion and reports `pose_showcase` (`wizard_avatar/pose_selection.py:53-62`). The live demo deliberately uses it while the path keeps locomotion marked walking (`tests/wizard/test_e2e.py:9-34`). This proves every pose can render, not that the poses form believable locomotion or action clips.

### 3.5 Transition behavior is global, short, and topology-oriented

The frame source assigns every pose change the same transition duration of approximately 120 ms (`wizard_avatar/frame_source.py:50-53`). A pose change remembers only the previous whole pose, start frame, and target (`wizard_avatar/frame_source.py:133-169`). This protects crisp cells and root continuity, but it has no per-edge timing, anticipation, contact-aware phase matching, interruption window, recovery state, or clip-specific easing.

The strict verifier measures frame hashes, changed-cell ratios, state, root position, and scale across scripted boundaries (`tools/verify_animation_quality.py:22-45`, `tools/verify_animation_quality.py:78-110`, `tools/verify_animation_quality.py:122-180`). Its current 32/32 result is useful regression evidence, but the gate can pass a visually abrupt coherent handoff. Animation quality still requires real-browser temporal and subjective checks.

### 3.6 Remote controls exist, but continuous control semantics do not

The Python service exposes move, path, circle, figure-eight, facing, action, pose, expression, speech, stop, and reset commands (`wizard_avatar/server.py:84-128`). The browser maps key-down events to absolute destinations and ignores repeated key events (`web/avatar/wizardControls.ts:24-45`). This is command triggering, not a remote-control protocol suitable for held directional input.

Current gaps include:

- no press/release or desired-velocity command
- no command sequence number or stale-command rejection even though `WizardCommand` has an unused `issued_at` field (`wizard_avatar/models.py:134-138`)
- no controller/client identity, lease, authority arbitration, or dead-man timeout
- no acknowledgment containing accepted sequence and authoritative simulation tick
- no distinction between viewer sockets and controller sockets
- every WebSocket may submit semantic commands (`wizard_avatar/server.py:145-160`)
- HTTP payloads are untyped `Dict[str, Any]` rather than explicit validated request models (`wizard_avatar/server.py:79-118`)

The next program needs a remote-input contract before UI work begins. Otherwise browser, controller, state-machine, and transport agents will invent incompatible control semantics.

### 3.7 Existing tests are valuable but do not cover the requested end state

Current strengths:

- all 39 pose IDs must match the manifest and share canonical anchors (`tests/wizard/test_reference_avatar_pose_library.py:23-40`)
- two subscribers receive identical contiguous decodable frames and per-client resync is tested (`tests/wizard/test_stream_hub.py:30-66`)
- speech preserves walking and active casting; temporary reactions restore prior actions (`tests/wizard/test_animation_channels.py:12-82`)
- the core semantic demo sequence and the 39-pose moving showcase run in process (`tests/wizard/test_e2e.py:9-68`)
- the current local suite passed 62 tests in this audit; deterministic generation reproduced SHA-256 `1200e2891902cd1f3147d2c2d298dd2d99313708fbc8e90034376500e1843037`; the strict matrix passed 32/32 with zero issues; the pose workflow validator found 30 candidates and zero errors.

Current omissions:

- no CI workflow exists under `.github/workflows/`
- no required-status-check configuration is documented
- no automated real-browser control session is part of the suite
- no held-input, controller-loss, out-of-order, duplicate, or stale-command tests
- no run/fly/takeoff/landing clip-cycle tests
- no graph reachability/dead-end/interruption-property test across all animation states
- no deterministic replay test from a recorded remote command log
- no long Python soak test with multiple viewers and one controller
- no Python-only release/evidence manifest that proves the live listener on port 8765 matches the pushed SHA

FastAPI officially supports testing WebSockets with the same `TestClient` used for HTTP, so HTTP/WebSocket command parity can be tested without introducing a second runtime ([FastAPI: Testing WebSockets](https://fastapi.tiangolo.com/advanced/testing-websockets/)).

### 3.8 The Git state is the immediate delivery hazard

The branch and upstream both point to `1b63db9`, but the working tree contains the real implementation:

- 23 modified tracked files
- 2,404 untracked files
- 2,183 untracked files under `evidence/`
- 82 untracked documentation files
- 40 untracked pose-source files
- 10 untracked Python tests
- 8 untracked Python runtime/definition files
- 7 untracked tools
- 73 untracked Rust source files, explicitly outside the production boundary

Large local surfaces include about 586 MB under `evidence/animation-quality`, 69 MB under `evidence/pose-library-expansion`, 49 MB under `assets/reference/motion_sources`, a 16 MB generated pose JSON, and 7.6 GB under `rust/` primarily from ignored build targets. At least three raw evidence files exceed GitHub's 100 MiB regular-file limit.

GitHub blocks regular repository files larger than 100 MiB, warns above 50 MiB, and recommends repositories remain ideally below 1 GB ([GitHub: About large files](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)). Therefore `git add .` is not an acceptable checkpoint operation.

The baseline and planning checkpoint must use an explicit allowlist and inspect the staged tree. Git documents both path-scoped staging and `git add --dry-run`, which should be used before the commit ([Git: git-add](https://git-scm.com/docs/git-add)). Heavy screenshots, recordings, logs, raw RGB captures, and test reports should be uploaded as workflow artifacts, not committed wholesale. GitHub explicitly distinguishes job artifacts from dependency caches and lists test output, screenshots, binaries, and logs as artifact use cases ([GitHub: Workflow artifacts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts), [GitHub: Dependency caching](https://docs.github.com/en/actions/concepts/workflows-and-actions/dependency-caching)).

## 4. Gap from pose reel to animated cartoon character

| Capability | Current state | Required program outcome |
|---|---|---|
| Motion vocabulary | 39 renderable complete poses | Named clips and state transitions that use the poses intentionally |
| Ground locomotion | Sparse walk samples; idle/walk only | Start, locomote, turn, stop, run, and recover with phase/contact continuity |
| Flight | Nine flight poses only reachable as showcase overrides | Takeoff, hover, flap, bank, glide, directional flight, descend, and land states |
| Action animation | Six broad action overrides | Windup, active, hold, recover, interrupt, and locomotion-compatible layers |
| Transition timing | One global 120 ms pose transition | Per-edge timing/easing/contact policy with deterministic interruption rules |
| Remote control | One-shot destination commands | Held input or desired velocity, authority lease, ordering, timeout, and acknowledgment |
| Multi-client behavior | Shared viewers; any socket may command | One authoritative controller policy plus passive viewers and safe handoff |
| Browser experience | Keyboard command triggers and scripted pose reel | Responsive remote controls driving the same semantic Python state machine |
| Test proof | 62 unit/integration tests and 32 boundary scenarios | Graph, replay, remote-input, flight, soak, and real-browser evidence |
| Release proof | Dirty local tree; no CI | Pushed reproducible Python baseline and required green status checks |

## 5. Recommended delivery architecture

### 5.1 Freeze contracts before parallel code

The planning wave should produce and freeze these versioned Python contracts before implementation agents diverge:

1. `MotionIntent`: normalized desired planar movement, desired flight altitude/vertical rate, facing preference, run/fly modifiers, and monotonically increasing input sequence.
2. `MotionState`: grounded, takeoff, flying, landing, and action/substate fields with deterministic timers and clip phase.
3. `AnimationClip` and `TransitionEdge`: samples, duration, loop, phase/contact metadata, entry/exit conditions, interruption policy, and fallback.
4. `ControllerLease`: controller identity, lease generation, last accepted sequence, expiry time, and authority status.
5. Public state response: authoritative simulation tick, accepted controller sequence, active clip, clip phase, transition edge/progress, root/contact state, and current pose.
6. Evidence schema: command log, simulation snapshots, source frame hashes, browser-presented hashes, performance samples, and environment/commit metadata.

Only the integration lead may change a frozen shared contract during a wave. A change requires a short decision record, affected-owner acknowledgment, and rerun of all contract tests.

### 5.2 Preserve one production spine

The Python controller, frame source, stream hub, server, and `web/avatar` client remain the only production path. New functionality should extend that path through data-driven clips and semantic state. No agent may create a parallel renderer, prerecorded sequence, alternate WebSocket service, or Rust fallback.

### 5.3 Separate control, simulation, animation, rendering, and delivery

The dependency order should be:

```text
remote input contract
  -> controller lease/order validation
  -> fixed-step movement and flight simulation
  -> semantic animation state machine
  -> pose/overlay evaluation
  -> ASCILINE frame construction
  -> adaptive encoding/fanout
  -> browser presentation and controls
```

This ordering keeps the renderer dependent on semantic state, as required by `docs/03-required-architecture.md:31-54`, and prevents browser controls from becoming a hidden animation engine.

## 6. Multi-agent ownership model

Use the same four role perspectives in Planning Wave 2, but translate every contribution into Python-only implementation ownership.

| Role | Primary implementation ownership | Explicit exclusions |
|---|---|---|
| FPSE | Python command models, controller lease/order semantics, locomotion/flight state transitions, deterministic clock/replay contracts | `pose_compositor.py`, browser renderer, all Rust files |
| ANIM | Animation graph/schema, clip authoring, pose compatibility, contacts, per-edge timing, pose selection, animation visual acceptance | transport/hub, HTTP routing, all Rust files |
| RUST perspective translated to Python systems | Python stream hub, ASCILINE protocol reliability, frame pacing, fanout/backpressure, browser decode/presentation metrics, performance and soak tests | Rust implementation, Cargo gates, animation authorship |
| PLAN | Tracker, workflow validator, CI, artifact manifest, checkpoint allowlists, evidence index, gate audit | production state/rendering code unless reassigned by coordinator |
| Integration lead | Shared schemas, `frame_source.py` wiring, `server.py` route integration, `wizardControls.ts` final wiring, conflict resolution, promotion decisions | unreviewed feature implementation in another owner's surface |

### Conflict-hotspot rule

These files must have one writer at a time because they sit on multiple dependency edges:

- `wizard_avatar/models.py`
- `wizard_avatar/controller.py`
- `wizard_avatar/frame_source.py`
- `wizard_avatar/server.py`
- `wizard_avatar/definitions/reference_avatar_animation_graph*.json`
- `web/avatar/wizardControls.ts`
- program tracker and registry

Parallel work should happen in new narrowly owned modules and focused tests. The integration lead performs short, reviewed wiring commits after upstream contracts pass.

Git worktrees are appropriate for isolating implementation waves because Git supports multiple linked working trees with separate `HEAD` and index state ([Git: git-worktree](https://git-scm.com/docs/git-worktree.html)). Each agent should receive a dedicated `codex/` branch and worktree created from the same pushed planning checkpoint. Agents must never share one index or stage from the coordinator's dirty worktree.

## 7. Recommended phased dependency graph

This is research guidance for Planning Wave 2, not the final implementation schedule.

### Phase 0: Python baseline recovery and quarantine

Gate `B0`:

- Resolve the wings/no-wings contract in the authoritative docs.
- Write an explicit tracked-file allowlist for the baseline commit.
- Include the Python runtime, `web/avatar`, pose manifest/sources, deterministic generator, generated pose library, Python tests, compact pose-expansion records, and compact evidence summaries.
- Exclude `rust/`, Rust evidence, raw RGB captures, temporary evidence, build products, and duplicate source previews.
- Add ignore rules that make accidental Rust/raw-evidence staging difficult.
- Run `git add --dry-run` with the allowlist, stage, then inspect `git diff --cached --stat`, `git diff --cached --name-only`, and the largest staged blobs.
- Commit and push a reproducible `python-39-pose-baseline` checkpoint before committing the research/plan checkpoint.

Why two ordered commits: a planning-only commit that points to unpushed runtime files is not reproducible. The remote branch must first contain the Python baseline that the plan governs.

### Phase 1: Research and plan checkpoint

Gate `P0`:

- All four research reports exist and cite current dirty-tree files plus primary sources.
- The same four roles produce compatible planning contributions.
- The integrated `IMPLEMENTATION_PLAN.md` contains a DAG, ownership map, acceptance matrix, rollback procedure, and exact commands.
- The workflow validator rejects overlapping ownership and Rust production dependencies.
- The planning checkpoint is committed and pushed after `B0`.
- The coordinator records both SHAs in `registry.json`.

### Phase 2: Contract and schema freeze

Gate `C0`:

- Motion intent, animation state, clip graph, transition edge, controller lease, public state, and evidence schemas are versioned.
- JSON schemas validate all 39 poses and every graph reference.
- Graph reachability tests reject missing poses, dead ends, unsupported direction claims, and unbounded transition cycles.
- Remote input tests reject stale, duplicate, out-of-order, unauthorized, and expired commands.
- No visible behavior change is promoted in this phase.

### Phase 3: Parallel engines behind frozen interfaces

Wave `E1` can proceed in disjoint worktrees:

- FPSE implements Python movement intent, ground/run/flight dynamics, controller lease, and deterministic replay.
- ANIM implements clips, transition graph evaluation, contacts, timing, and pose compatibility.
- Python systems owner hardens the hub, protocol metrics, backpressure, and test harness.
- PLAN implements CI, workflow validation, artifact packaging, and gate reports.

Gate `E1` requires each branch's focused tests, a clean rebase onto `P0/C0`, and an ownership audit. No branch is merged directly into the production branch.

### Phase 4: Serial integration

The integration lead merges in dependency order:

1. contracts and validators
2. controller/locomotion/flight
3. animation graph evaluator
4. frame-source/compositor wiring
5. stream/server remote-control delivery
6. browser controls and diagnostics
7. evidence and CI

Gate `I0` after every merge:

- full Python unit suite
- deterministic pose generator
- graph validation
- strict transition matrix
- port-8765 HTTP/WebSocket smoke
- no new Rust dependency or staged Rust path

### Phase 5: Motion-family promotion

Promote one family at a time, with a feature flag or graph-version switch:

1. idle/breath/look and start/stop
2. walk and turn
3. run and decelerate
4. takeoff/hover/flap/glide/bank/land
5. actions and interruption/recovery
6. expression/speech while moving and flying

Each family must pass its own visual/contact/replay gate before the next family begins. This follows the successful one-candidate-at-a-time pose integration principle documented at `docs/pose-library-expansion/WORKFLOW.md:14-24`, but applies it to motion families rather than individual source images.

### Phase 6: Remote-control and browser acceptance

Gate `R0`:

- A controller can acquire authority, hold/release movement, change modes, trigger actions, stop, and relinquish authority.
- Loss of controller input causes a deterministic safe stop/hover after the specified timeout.
- A passive viewer cannot accidentally seize control.
- Reconnect resumes from an authoritative state/keyframe without replaying stale input.
- One controller plus at least four viewers does not multiply simulation speed.
- A real-browser run records commands, authoritative ticks, active clips, source hashes, presented hashes, FPS, queue depth, and console errors.

### Phase 7: Final evidence and publish

Gate `F0`:

- clean clone of the pushed implementation SHA
- locked dependency installation
- server starts on port 8765 from documented command
- all required Python/JavaScript/browser gates pass
- deterministic command replay produces identical state and source-frame hash sequences twice
- compact evidence manifest is committed
- heavy recordings/logs/screenshots are uploaded as workflow artifacts with explicit retention
- final implementation commit is pushed and its SHA is recorded in the program registry

GitHub's official Python Actions guidance recommends an explicit `setup-python` version and supports matrix testing plus test-result artifacts ([GitHub: Building and testing Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)). The CI should test the declared minimum Python version (`>=3.9`) and the chosen production version, while the live macOS/browser acceptance can remain a separate required job.

## 8. Checkpoint and rollback policy

### 8.1 Commit classes

1. `baseline`: existing Python 39-pose product, no program redesign.
2. `planning`: research, integrated plan, workflow, schemas only.
3. `contract`: frozen public data models and validators, no behavior switch.
4. `family`: one motion family behind a graph/version feature flag.
5. `integration`: wiring only, with full gate evidence.
6. `verification`: compact manifests and reports, not new runtime behavior.

Every commit must be independently testable and must identify the gate it satisfies. Do not mix raw evidence, generated temporary files, unrelated Rust work, and production behavior in one commit.

### 8.2 Rollback mechanism

- Preserve the current animation graph as `v1` until the new graph passes final acceptance.
- Make the Python server select a graph version through a validated configuration value, with `v1` as the emergency fallback during development.
- Do not maintain two renderers. Rollback switches data/behavior configuration on the same renderer and ASCILINE path.
- A failed family gate reverts or disables only that family branch/graph entry.
- Schema migrations must be additive until all in-flight agent branches have rebased.
- The coordinator records failed gate, responsible commit, rollback commit, and evidence path in the program tracker.

### 8.3 Branch protection

The delivery branch should require pull requests, at least one review by someone other than the latest pusher, stale-approval dismissal, and required Python/graph/browser checks. GitHub rulesets can require status checks and code-owner review, and strict checks can require the branch to be current with its base ([GitHub: Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)). GitHub also documents that stale reviews can be dismissed after code-modifying pushes ([GitHub: Required reviews](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/approving-a-pull-request-with-required-reviews)).

CI should use a concurrency group per branch and cancel superseded validation runs so old commits cannot publish evidence after newer changes. GitHub Actions supports concurrency groups specifically to prevent conflicting simultaneous runs or cancel outdated checks ([GitHub: Concurrency](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency)).

## 9. Evidence and accountability model

### 9.1 Machine-readable ledger

Every work item needs:

- stable ID
- owner and worktree/branch
- allowed write paths
- prerequisite IDs
- baseline SHA
- status
- changed paths
- commands and exact results
- generated artifact hashes
- reviewer
- rollback point
- residual risks

The registry validator must fail if:

- two active agents own the same conflict hotspot
- an item starts before prerequisites pass
- an implementation item references `rust/`, Cargo, or ports 8787/8788 as a production dependency
- a gate lacks command output or artifact hash
- the recorded branch SHA differs from the tested SHA
- the tracker and registry disagree

### 9.2 Evidence tiers

| Tier | Stored in Git | Stored as workflow artifact |
|---|---|---|
| Contract | schemas, thresholds, scenario definitions | none |
| Summary | Markdown report, JSON manifest, hashes, small contact sheet | none or optional |
| Detailed | no raw frame dumps | test logs, JUnit XML, NDJSON traces |
| Visual | one or two curated review images if small | recordings, full screenshot sets, raw frames |
| Soak/performance | compact aggregate JSON | raw samples and long logs |

GitHub artifacts default to 90-day retention and allow custom retention periods ([GitHub: Artifact retention](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/remove-workflow-artifacts)). The final plan should set a retention period and copy only release-critical compact summaries into Git.

### 9.3 Required independent reviews

- Motion-family visual review by ANIM, not its implementer.
- Determinism/state review by FPSE, not the graph author.
- Stream/reconnect/performance review by the Python systems owner, not the server integrator.
- Evidence completeness and staged-path review by PLAN, not the feature owner.
- Final live port-8765 browser review by the coordinator.

## 10. Measurable acceptance criteria

The final planning wave should refine thresholds, but it should not weaken these minimums.

### Reproducibility and scope

- A clean clone of the pushed SHA builds and runs the Python service on port 8765 with no Rust toolchain installed.
- No production import, subprocess, CI step, acceptance command, or artifact path depends on `rust/` or Cargo.
- The 39-pose manifest and deterministic generated library remain complete; regeneration is byte-identical and reports the approved SHA unless a reviewed asset migration intentionally changes it.
- The pushed tree contains no regular file above GitHub's 100 MiB limit and no raw temporary capture.

### Simulation and control

- Fixed simulation remains 60 Hz and render delivery remains 24 FPS under the standard profile.
- Identical timestamped command logs produce identical semantic-state and source-frame hash sequences across two runs.
- Held directional input starts motion; release decelerates to the defined stop; controller timeout reaches safe stop/hover within the specified deadline.
- Duplicate, stale, out-of-order, unauthorized, and expired inputs are rejected without changing state.
- One controller plus 1, 2, and 4 viewers produces the same simulation-time advance within 1% and no sequence regression.

### Motion graph

- Every graph pose reference resolves to one of the 39 generated poses.
- Every promoted state has a path to a stable idle/hover state and no unapproved dead end.
- Walk, run, flight, and action clips preserve phase through legal transitions and use declared contact/airborne rules.
- Start/stop, turn, takeoff/land, action interruption, and recovery transitions have explicit edge policy rather than falling back to the global showcase transition.
- Unsupported facings use documented, tested fallbacks and are not advertised as authored coverage.

### Visual continuity

- Fixed-world transition boundaries keep root movement at or below the existing 1-cell strict threshold and scale delta at zero unless an edge explicitly authorizes root motion (`tools/verify_animation_quality.py:141-156`).
- Planted-foot, staff-hand, mouth, eye, and root anchors remain within the canonical canvas and satisfy family-specific continuity thresholds.
- No frame contains a duplicated staff, detached face, unexplained floating cells, torn silhouette, or stage-edge clipping.
- Real-browser review covers idle, ground locomotion, flight, action interruption, speech while moving, reconnect, and controller loss.

### Remote browser and ASCILINE delivery

- HTTP and WebSocket control paths produce equivalent accepted semantic commands.
- New subscribers receive a decodable keyframe before deltas; resync affects only the requesting subscriber.
- Browser source/decoded/presented hashes agree for sampled frames.
- Standard demo sustains at least 24 presented FPS with zero decoder errors, zero unbounded queue growth, and zero console errors.
- The browser never substitutes source PNGs, videos, or a separate sprite animation runtime.

### Quality and release

- Full Python suite, graph validator, deterministic generator, strict transition matrix, JavaScript tests, real-browser remote-control test, multi-client soak, and staged-path scope audit all pass on the pushed SHA.
- No required test is skipped or marked expected failure.
- Compact final evidence records the commit SHA, exact commands, dependency lock hash, generated-library hash, test totals, browser/runtime metrics, artifact URLs, and remaining limitations.

## 11. Principal risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Dirty local product is not reproducible from GitHub | Planning and agents start from different systems | Push Python baseline before planning checkpoint; record SHA |
| Accidental `git add .` captures Rust and raw evidence | Push failure, huge history, mixed architecture | Explicit allowlist, dry-run, staged largest-blob audit, ignore rules |
| Wings contract remains contradictory | Agents implement opposing acceptance criteria | Resolve in Phase 0 and update completion gate |
| Shared files edited concurrently | Silent integration regressions | One writer per hotspot; frozen contracts; serial wiring |
| 39 poses are treated as 39 animation states | Incoherent motion and pose roulette | Group into clips and graph states; declare compatibility/fallbacks |
| Front-heavy asset coverage is oversold | Broken side/back flight/action claims | Scope authored direction coverage and add approved fallbacks |
| Remote clients race for global state | Jitter, overwritten commands, unsafe recovery | Lease, sequence, authority, timeout, viewer/controller split |
| Fixed thresholds pass but motion still looks poor | False completion | Animation-expert visual gate plus real-browser recordings |
| Heavy evidence is committed to Git | Repository growth and blocked pushes | Compact manifests in Git; raw evidence as retained artifacts |
| Rust work leaks back into gates | Two production truths and duplicated maintenance | Validator forbids Rust production dependencies and commands |

## 12. Planning Wave 2 handoff

The `PLAN` agent should return in Planning Wave 2 and convert this research into `docs/cartoon-animation-program/planning/04-workflow-plan.md` with:

1. exact work-item IDs and DAG dependencies
2. per-agent allowlisted paths and conflict-hotspot lock ownership
3. baseline and planning checkpoint staged-file allowlists
4. exact gate commands and expected machine-readable outputs
5. branch/worktree names and handoff template
6. graph-family promotion order and rollback switch
7. CI jobs, concurrency, required-check names, and artifact retention
8. final port-8765 acceptance matrix

The integrated plan must reject any implementation wave that begins before the Python baseline and planning checkpoint are both pushed and recorded.

## 13. Primary and official source bibliography

1. [Git: git-worktree](https://git-scm.com/docs/git-worktree.html) - official linked-worktree behavior and isolation model.
2. [Git: git-add](https://git-scm.com/docs/git-add) - official pathspec, dry-run, and index-staging behavior.
3. [GitHub: About large files](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) - official file and repository size guidance.
4. [GitHub: Workflow artifacts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts) - official persistence model for test output and generated evidence.
5. [GitHub: Dependency caching](https://docs.github.com/en/actions/concepts/workflows-and-actions/dependency-caching) - official distinction between caches and job artifacts.
6. [GitHub: Artifact retention](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/remove-workflow-artifacts) - official default and configurable retention behavior.
7. [GitHub: Building and testing Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) - official Python setup, matrix, testing, and artifact guidance.
8. [GitHub: Matrix jobs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations) - official test matrix and parallelism controls.
9. [GitHub: Concurrency](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency) - official workflow/job concurrency groups.
10. [GitHub: Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets) - official required review and status-check controls.
11. [GitHub: Required reviews](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/approving-a-pull-request-with-required-reviews) - official stale-review and approval behavior.
12. [FastAPI: Testing WebSockets](https://fastapi.tiangolo.com/advanced/testing-websockets/) - official in-process WebSocket test support.
13. [Python: Coroutines and tasks](https://docs.python.org/3/library/asyncio-task.html) - official cancellation and structured-concurrency cleanup guidance relevant to the frame hub and socket lifecycle.
