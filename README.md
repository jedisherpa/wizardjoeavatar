# WizardJoeAvatar

Procedural ASCILINE-compatible wizard-avatar implementation specification.

The project is designed around a server-authoritative, editable character assembled from cell masks, color palettes, semantic layers, skeletal anchors, directional views, procedural locomotion, independent expression/speech channels, a fixed white studio background, and a faint perspective checkerboard floor. The visible avatar renders as colored square tiles, not typography.

## Start here

- [Codex goal entry point](CODEX_GOAL.md)
- [Section index](docs/INDEX.md)
- [Visual reference specification](assets/reference/README.md)
- [Locomotion transition graphs](docs/character-director/LOCOMOTION_TRANSITION_GRAPHS.md)
- [Authored turn continuity](docs/character-director/AUTHORED_TURN_CONTINUITY.md)
- [Authored cast continuity](docs/character-director/AUTHORED_CAST_CONTINUITY.md)

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

## Current implementation

The production target is the ASCILINE Python service on port `8765`. It provides
a fixed-tick animation runtime, adaptive square-cell streaming, keyboard and
gamepad movement, ground and flight control, a complete pose picker, a random
Repeat mode, speech mouth animation with captions, and a content-free Prism
visual-advisory input. Rust experiments in this checkout are historical and are
not production dependencies.

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

Run locally in the foreground:

```bash
python3 -m pip install -r requirements.txt
python3 tools/run_wizard_avatar_server.py --port 8765
```

Then open `http://127.0.0.1:8765/`.

## Animate from Prism GT audio

With the persistent Wizard service and the configured Prism GT app running:

1. Open `/Applications/Prism GT.app`.
2. Confirm the visible **Wizard Joe** status reads **Connected**.
3. Select **Player**, choose a bundled track or **Link Audio**, and press **Play**.
4. Keep `http://127.0.0.1:8765/` open as the visualization output.
5. Use **Open Wizard** in Prism whenever the visualization is not already open.

Prism music, podcasts, audiobooks, and video audio use the main-media channel.
TTS and speaker output temporarily use the speech channel, then return control to
the current main track when speech pauses or ends. The square Stop button on the
visualization releases demo movement; active Prism playback also releases any
scripted demo path automatically while preserving keyboard and gamepad leases.

The visualization's media banner is the quickest health check:

- **Animating main audio** or **Animating speech**: playback owns the performance.
- **Wizard media paused**: the connector is healthy and Prism is paused.
- **Wizard media needs reconnect**: reload Prism GT and press Play again.

On macOS, install the local persistent service once:

```bash
tools/install_local_wizard_service.sh
```

The installer generates a private shared connector credential, configures both
the Wizard LaunchAgent and normal Prism GT desktop launches, starts at login,
restarts after a crash, and remains on port `8765` until:

```bash
tools/stop_local_wizard_service.sh
```

Run verification:

```bash
python3 -m unittest discover -s tests
python3 tools/validate_cartoon_animation_program.py --root .
python3 tools/run_python_avatar_soak.py --duration-seconds 30 --viewers 4 --slow-viewer --strict
python3 tools/generate_wizard_evidence.py
python3 tools/demo_wizard_avatar.py
```

## Add another NFT character

The reusable unit is a versioned character package. A package names the
character’s generated square-cell pose library, animation graph, default pose,
renderer, and capabilities. The shared runtime, projection, control, transport,
browser, API, diagnostics, and evidence flow do not change.

1. Generate a canonical square-cell pose library from the character’s source images.
2. Author or reuse a compatible animation graph whose samples name those poses.
3. Add a package matching `wizard_avatar/definitions/character_package.schema.json`.
4. Construct `ProceduralWizardFrameSource(character_package_path=...)`.
5. Run the package, continuity, browser, and soak gates.

Wizard Joe’s production package is
`wizard_avatar/definitions/wizard_joe_character_package.json`. The test suite
also renders a second fixture character through this same path to prevent the
package boundary from becoming metadata-only.
