# Multi-Agent Implementation Workflow

This workflow executes [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) after the planning checkpoint is pushed.

## Agents and ownership

| Role | Agent | Production ownership |
|---|---|---|
| FPSE | Linnaeus | runtime clock, command queue, arbitration, typed state, replay |
| ANIM | Bernoulli | pose metadata, graph v2, clips, markers, transition recipes, visual tests |
| SYS | Sagan | Python transport, hub cadence, metrics, resync, Rust-exclusion checks |
| PLAN | Darwin | workflow validator, evidence schemas, CI/release gates, tracker |
| PRSM | Singer | Prism signal envelope/parser/diagnostics; no Prism repo edits |
| PERS | Feynman | sanitized persona/memory/governance intent mapping and privacy tests |
| INT | coordinator | conflict hotspots, serial integration, browser controls, final verification/push |

## Write boundaries

Agents must not revert other work. New modules are preferred during parallel waves. These files are coordinator-locked conflict hotspots:

- `wizard_avatar/models.py`
- `wizard_avatar/controller.py`
- `wizard_avatar/frame_source.py`
- `wizard_avatar/server.py`
- `wizard_avatar/stream.py`
- `web/avatar/wizardClient.ts`
- `web/avatar/wizardControls.ts`
- `docs/cartoon-animation-program/PROGRAM_TRACKER.md`
- `docs/cartoon-animation-program/registry.json`

Workers prepare new modules, schemas, definitions, focused tests, and handoff notes. The coordinator applies the minimal hotspot wiring after reviewing all parallel work.

## Execution DAG

```text
planning push
  -> contracts
      -> FPSE runtime -----------+
      -> ANIM graph/clips -------+-> serial integration -> ground -> flight -> actions -> controls -> Prism
      -> SYS transport ----------+
      -> PRSM signal parser -----+
      -> PERS signal mapping ----+
      -> PLAN gates/evidence ----+
  -> deterministic QA -> browser QA -> soak -> clean-clone -> final push
```

## Wave 0: planning checkpoint

1. Validate all reports and JSON ledgers.
2. Confirm Python tests pass and the generated pose library has 39 entries.
3. Use an explicit staging allowlist. Exclude `rust/`, Rust evidence, raw RGB captures, temporary files, and build outputs.
4. Record staged file count/size and inspect `git diff --cached`.
5. Commit and push research, plan, current Python baseline, pose assets, tests, and compact evidence.

Gate: remote branch contains the planning checkpoint and no Rust runtime files.

## Wave 1: contracts

Parallel assignments:

- FPSE: Python dataclasses/enums/protocols and JSON schemas for commands, acks, runtime snapshot, control intent, replay record.
- ANIM: metadata-complete pose loader, graph-v2 schema/definition, 39-pose taxonomy, strict graph validator.
- SYS: Python-only scope validator and transport compatibility contract.
- PRSM: signal-envelope schema and parser contract.
- PERS: animation-intent mapping table and forbidden-field policy.
- PLAN: machine-readable gate and evidence schemas.

Gate: all schemas validate good fixtures, reject bad fixtures, and make no production behavior change.

## Wave 2: parallel engines

- FPSE implements fixed clock, command inbox, dedupe/ack, leases, arbitration, semantic ground/flight state, replay.
- ANIM implements clip evaluator, markers, clips, transition recipes, face/prop/effect channel contracts.
- SYS implements hub pacing helpers, metrics, epoch/resync state, and transport adapters in new modules.
- PRSM implements an optional Python signal parser with sequence, epoch, TTL, schema, and privacy validation.
- PERS implements content-free signal-to-intent mapping with governance clamps and user-control priority.
- PLAN implements validators, evidence writers, and focused CI commands.

Each agent runs only focused tests for owned modules and returns changed paths, commands, results, risks, and coordinator wiring requests.

## Wave 3: serial integration

The coordinator owns one integration lock and applies changes in this order:

1. Runtime clock and snapshots.
2. Command queue and compatibility adapters.
3. Graph loader/evaluator with behavior still on legacy selection.
4. Hub cadence and immutable rendering.
5. Ground locomotion family.
6. Flight family.
7. Action and independent visual channels.
8. Continuous browser controls.
9. Optional Prism signal adapter.

After each item: run focused tests, full Python tests, strict transition checks, `git diff --check`, and a live state smoke. A failure releases no later promotion.

## Wave 4: browser and visual QA

Real Chromium on `http://127.0.0.1:8765/` must cover:

- press/hold/release in eight directions;
- rapid reversal, stop, reconnect, blur, and visibility loss;
- walk/run start, loop, turn, stop;
- takeoff, hover, flap, glide, bank, descend, land;
- speech and expression while moving and flying;
- action interruption and recovery;
- gamepad dead zone and disconnect;
- Prism listen, think, recall, clarify, approval-wait, persona change, degraded, stale, and disconnect fixtures;
- all 39 poses reachable through clips or declared fallback/showcase path;
- zero console errors, clipped text, missing cells, detached staff/wings, face drift, or blurred squares.

Evidence includes command/replay logs, state/frame hashes, contact/root traces, signal acceptance/rejection logs, screenshots, and a concise video or timed capture manifest.

## Wave 5: release

1. Run all Python and browser tests.
2. Run deterministic replay twice and compare hashes.
3. Run 10-minute mixed-control/multiclient soak.
4. Verify staged scope and repository size.
5. Commit compact implementation/evidence only.
6. Push the branch.
7. Restart the Python server on 8765 and repeat the live smoke against the pushed tree.

## Handoff format

Every agent reports:

```text
work_item:
status:
owned_files_changed:
interfaces_implemented:
tests_run:
test_results:
evidence_paths:
risks:
hotspot_wiring_requested:
next_dependency_unblocked:
```

## Stop conditions

- A worker touches an unowned hotspot.
- A Rust production dependency appears.
- A pose or signal bypasses semantic arbitration.
- Private Prism content enters WizardJoe state, logs, frames, or evidence.
- Determinism, contact, attachment, frame-hash, resync, or browser gates regress.
- The planning checkpoint has not been pushed.
