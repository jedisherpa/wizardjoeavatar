# Python Runtime Architect Report

## Runtime Trace

- `tools.run_wizard_avatar_server.main` constructs the procedural frame source,
  FastAPI application, and one Uvicorn server.
- Uvicorn owns the asyncio loop; `WizardFrameHub.start()` creates the single
  long-lived fixed-tick task.
- Input flows through `OrderedCommandInbox` to `AvatarRuntime`, the controller,
  `ProceduralWizardFrameSource`, adaptive encoding, bounded server subscribers,
  and Canvas rendering.
- The Companion adds a Rust supervisor thread, one PyInstaller sidecar process,
  and a second Rust bridge thread for authenticated frames.

## Findings

### P0: Snapshot closure is false

`AvatarRuntime.step_tick()` freezes and hashes state in `runtime.py`, but
`frame_source.py` subsequently mutates screen position, scale, pose IDs, and
transition progress. `WizardState.as_public_dict()` may also mutate state.
Snapshot hashes, replay checkpoints, diagnostics, and rendered output can
therefore disagree.

Rendering must become side-effect-free. One aggregate authoritative state must
include locomotion, leases, media/signal state, and presentation inputs.

### P1: Unbounded memory

`ReplayLog._records` grows forever and the replay route materializes complete
NDJSON in memory. `OrderedCommandInbox._source_watermarks` also has no eviction.
Use bounded segments or a ring, stream replay responses, and cap watermarks.

### P1: Event-loop starvation

`WizardFrameHub._run()` holds its asyncio lock while building, compositing,
compressing, and hashing a full frame. HTTP, media, health, and WebSockets share
that loop. Tests observed slow tasks around 0.28-0.50 seconds. Make rendering
pure, benchmark one ordered worker, and drop stale presentation jobs while
preserving one semantic writer.

### P1: Compatibility network boundary

Companion mode enforces literal loopback and separate bearer credentials.
Compatibility mode allows unauthenticated mutation and can bind `0.0.0.0`.
Reject non-loopback by default and apply strict body limits/models everywhere.

### P2: Shutdown and observability

WebSocket receiver tasks are cancelled but not awaited; pending waiters lack a
shutdown result. Browser raw-message buffering is unbounded. Broad receiver
errors are swallowed, and service logs have no rotation.

## Tooling

- Python `>=3.9`; observed Python `3.9.6`.
- `uv.lock` exists; standalone requirements are ranged.
- Tests use `unittest`; no checked-in Ruff, Black, mypy, or coverage policy.
- Companion sidecar uses pinned CPython 3.12.10, uv 0.11.7, PyInstaller, and a
  locked requirements file.

## Rejected Alternatives

- Replacing Python with the historical Rust engine.
- Adding locks around the current mutable graph as the main fix.
- One renderer or process per viewer.
- Browser access to the Companion app bearer.
- Synchronous per-frame persistence.

## Verification

- Assert rendering and read APIs do not change state/hash.
- Replay media, leases, paths, and Prism signals from a fresh process and compare
  state plus frame hashes.
- Run 8-24 hour RSS/queue/latency soak tests.
- Shutdown with active viewers and pending commands with no orphan or stale
  discovery file.
- Test non-loopback rejection, payload limits, codec negotiation, and malformed
  commands.

Independent verification observed 337 passing Python tests and 61 Python-scope
files with zero scope violations.
