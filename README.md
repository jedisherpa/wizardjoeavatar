# WizardJoeAvatar

Procedural ASCILINE-compatible wizard-avatar implementation specification.

The project is designed around a server-authoritative, editable character assembled from cell masks, color palettes, semantic layers, skeletal anchors, directional views, procedural locomotion, independent expression/speech channels, a fixed white studio background, and a faint perspective checkerboard floor. The visible avatar renders as colored square tiles, not typography.

## Start here

- [Codex goal entry point](CODEX_GOAL.md)
- [Section index](docs/INDEX.md)
- [Visual reference specification](assets/reference/README.md)

## Core constraints

- No prerecorded video.
- No runtime flattened character PNG.
- No generated frame dump as the implementation.
- Reference PNG is converted into a repeatable square-cell mask.
- Rainbow wings are required for the current reference avatar.
- Fixed white background.
- Very faint checkerboard floor.
- Eight-direction movement.
- Forward/back depth projection.
- Circular and figure-eight pathing.
- Direct procedural ASCILINE-compatible cell frame generation.
- Full codec, reconnect, visual, locomotion, environment, and speech testing.

## Repository purpose

This repository is intended to be cloned or referenced from any development machine and supplied directly to Codex as the authoritative implementation specification.

## Current implementation status

This is a first procedural implementation pass, not a completed pass of all 38
specification documents. See
[`docs/wizard/COMPLIANCE_GAP_AUDIT.md`](docs/wizard/COMPLIANCE_GAP_AUDIT.md)
for the current gap list.

## First-pass repeatable avatar pipeline

This checkout now contains a deterministic procedural implementation under
`wizard_avatar/`. The character is assembled from palette values, semantic mask
roles, JSON view definitions, layer primitives, expression overlays, skeleton
anchors, world-space locomotion, fixed environment projection, and an
ASCILINE-compatible adaptive frame source. Browser and evidence renderers display
non-empty cells as colored square tiles.

The current front-facing avatar is generated from
`assets/reference/target_voxel_wizard.png` by:

```bash
python3 tools/generate_reference_avatar_cells.py
```

That produces `wizard_avatar/definitions/reference_avatar_cells.json`, which the
live frame source uses instead of reading the PNG at runtime.

The expanded reference motion range is generated from the pose copies in
`assets/reference/motion_sources/`:

```bash
python3 tools/generate_reference_avatar_pose_cells.py
```

That reads `assets/reference/motion_sources/manifest.json` and produces
`wizard_avatar/definitions/reference_avatar_pose_cells.json`, a repeatable
square-cell pose library for front, side, back, walking, explaining, and magic
cast states.

Run locally:

```bash
python3 -m pip install -r requirements.txt
python3 tools/run_wizard_avatar_server.py --port 8000
```

Then open `http://127.0.0.1:8000/`.

Run verification:

```bash
python3 -m unittest discover -s tests
python3 tools/generate_wizard_evidence.py
python3 tools/demo_wizard_avatar.py
```

For future NFT characters, keep the shared runtime and replace or extend:

- `wizard_avatar/palette.py`
- `wizard_avatar/glyphs.py`
- `wizard_avatar/definitions/*.json`
- `assets/reference/target_voxel_wizard.png`
- `wizard_avatar/layers.py`
- `wizard_avatar/expressions.py`

The server/API/browser/demo/tests/evidence flow stays the same.
