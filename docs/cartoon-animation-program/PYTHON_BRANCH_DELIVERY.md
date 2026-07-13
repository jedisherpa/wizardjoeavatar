# Python ASCILINE Branch Delivery

Branch: `codex/python-asciline-avatar`

Live acceptance target: `http://127.0.0.1:8765/`

Production runtime: Python controller, ASCILINE square-cell renderer, FastAPI
server, WebSocket stream, and browser client.

## Pose library

The production library contains 89 unique pose IDs:

- 39 previously integrated movement, action, and flight poses;
- 50 unique feelings/action poses migrated from the tracked source intake;
- ten exact duplicate feelings sources remain documented in the intake ledger
  and are not duplicated in the runtime catalog.

Play and Repeat fetch `/api/avatar/wizard/poses`, so all 89 poses participate
without a hard-coded browser list. Pose overrides remain active while the path
controller moves the character around the stage.

## Repeatable rebuild

From the repository root:

```bash
python3 tools/integrate_feelings_into_python.py --check
python3 tools/generate_reference_avatar_pose_cells.py --check-deterministic
python3 -m unittest discover tests
```

The migration tool is idempotent. It verifies the 50 unique `WJFL` records,
their tracked PNG sources, the 89-entry Python manifest, graph classification,
and generated cell-library parity.

## Rust boundary

The live server has no Rust runtime dependency. It does not import, compile,
launch, or call Rust code.

The candidate-to-semantic mapping and authored anchors were translated once
into `assets/reference/motion_sources/feelings_python_metadata.json`. Current
rebuilds read that Python-owned metadata and the tracked PNG intake, not the
Rust tree. Generated production frames come from
`wizard_avatar/definitions/reference_avatar_pose_cells.json` through the
Python `ProceduralWizardFrameSource`.

Rust chatbot and animation experiments belong on their own branches and are
not staged into this branch's Python implementation commits.
