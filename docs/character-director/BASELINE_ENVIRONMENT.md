# Baseline Environment

Recorded on 2026-07-15 before Character Director implementation.

## Python Repository

- Repository object store: `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar`
- Preserved dirty worktree: `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar-python`
- Preserved branch: `codex/audiobook-performance-engine`
- Preserved HEAD: `293a2d84d3376eca3084eb0db9b0cd04fee42f08`
- Isolated implementation worktree: `/Users/paul/Documents/WizardJoeAsci/worktrees/wizardjoe-character-director`
- Isolated branch: `codex/character-director`
- Isolated starting HEAD: `293a2d84d3376eca3084eb0db9b0cd04fee42f08`
- Required baseline: `556701a0dfd8c9c553de7159bc2d747b43fa9bd8`
- Verified corrective successor: `408825ae75e395cd0761d0f17b9636a40559263a`
- Python requested by project: `>=3.9`
- Observed system and existing venv Python: `3.9.6`
- Environment tooling: `uv 0.11.7`, checked-in `uv.lock`, ranged standalone `requirements.txt`, pinned Companion sidecar lock
- Entry point: `tools/run_wizard_avatar_server.py`
- Existing test command: `python3 -m unittest discover -s tests`
- Existing scope gate: `python3 tools/validate_python_scope.py --root .`
- Packaging: LaunchAgent compatibility service plus PyInstaller sidecar in the Tauri Companion

The dirty worktree remains untouched as evidence. Uncommitted candidate director,
projection, close-up, and Companion changes require explicit review before they
are moved into this branch.

## Prism Repository

- Preserved dirty worktree: `/Users/paul/Documents/Codex/2026-06-28/jedisherpa-prism-geometry-talk-https-github/work/prism-geometry-talk-current`
- Preserved local HEAD: `bf229c28aa7e7a700a63bd5282607ffc77a052c2`
- Healthy integration clone: `/Users/paul/Documents/WizardJoeAsci/worktrees/prism-character-director`
- Healthy clone branch: `codex/character-director-prism`
- Healthy clone HEAD: `bf229c28aa7e7a700a63bd5282607ffc77a052c2`
- Required baseline: `189fbabc4f59af5d53e352c6bf9c692ee7382214`
- Verified corrective successor: `59106015fe22b224df350ddd28dc2fd487132681`
- Companion commit recovery: exact `bf229c2` history was bundled from the
  preserved repository while supplying missing base objects from the healthy
  clone; bundle SHA-256
  `34d6b0a5e9a6e1986b2435a0e605ab87151ba4f502b03d41a71e5a7705c61e55`
- Bundle verification: complete history, exact `bf229c2` ref, SHA-1 object format

The preserved Prism worktree has dirty connector and UI work and an unreliable
shared object store. Implementation must use the healthy clone, with later work
ported only after review.

## Live Runtime

- Compatibility server: `127.0.0.1:8765`
- Observed PID at this checkpoint: `55990`
- Listener: answering; the guessed `/health` route returns `404`
- Contract status: actual health and diagnostics routes must be derived from the
  Python server route table and verified live before the runtime is described as
  healthy
- Source path: preserved dirty Python worktree

The live service is evidence, not the implementation worktree. Character
Director development must not restart or replace it unless a verification step
explicitly requires a bounded rebuild.
