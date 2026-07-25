# Joeville Visualizer Audit

> **Update:** This records the primary-checkout baseline at audit time. CrystAIl is now verified runtime-ready on the dedicated `codex/crystail-character` branch. Read `CRYSTAIL_READINESS_ADDENDUM.md` for the later two-character branch state; she is not yet present in the primary checkout.

## Audit status

This is a read-only audit of the two production surfaces named in the assignment:

- `WizardJoeAvatar` at commit `6f9ff0e9ee176b6022e04f77e5f6b9a53055bfce`
- `ASCILINE` at commit `05cc6ebd2152f5987ab348038d5619d279ecec27`

The checkout was already dirty. No source files were changed. Focused runtime tests for the character package, projection, floor, and visual contract ran successfully: **10 tests, 10 passed, 0 failed**.

## Executive finding

The current production target is a **single-character, server-authoritative, square-cell visualizer** for Wizard Joe. It is not presently a 13-character visualizer and does not contain a verified 13-character library. It supports one generated 89-pose library, a fixed white procedural studio background, one projected ground plane, one contact shadow, and one opaque framebuffer streamed to a single browser canvas.

Joeville cannot be integrated as a drop-in stack of conventional background images or videos without visualizer work. The frame protocol has no alpha, depth, layer, camera, or asset-reference fields. The server bakes environment, shadow, character, and overlays into one 240 x 135 cell framebuffer before streaming. The browser then paints each non-space cell as an opaque square tile.

## What actually exists

### Character inventory

| Item | Verified result |
|---|---|
| Loadable production character packages | **1** |
| Production character | `wizard-joe-v1`, display name `Wizard Joe` |
| Renderer | `asciline_square_cells` |
| Pose library | `reference_avatar_pose_cells.json` |
| Poses | **89** distinct pose IDs |
| Animation graph | `reference_avatar_animation_graph_v2.json` |
| Default pose | `front_idle` |
| Character-local canvas per pose | 72 x 96 cells |
| Root anchor | (36, 95) for all inspected poses |
| Pose-cell total | 277,285 populated source cells across the library |

The claim that 13 fully integrated characters already exist is **not substantiated by either audited repository**. `WizardJoeAvatar/wizard_avatar/definitions` has one production package JSON. The FastAPI surface exposes singular routes (`/api/avatar/wizard/character`, `/api/avatar/wizard/poses`, `/ws/avatar/wizard`) and constructs one `ProceduralWizardFrameSource`. `ASCILINE` is a generic video-to-cell player and has no character registry. Copies and historical snapshots elsewhere in the wider workspace are not additional integrated production characters.

At the original audit point this was a blocking production fact. The later CrystAIl branch reduces the remaining cast build gap to eleven characters, but a 13-character ensemble still cannot be scale-tested, blocked, or composited honestly until those packages and a multi-character scene compositor exist.

### Visual character construction

Wizard Joe is not loaded from a PNG at runtime. Source PNGs are converted offline into a 37 MB JSON pose library. At runtime, each selected pose is a flat set of `(x, y, RGB)` cells painted with the `#` glyph. The visual pose therefore behaves like an authored raster-cell snapshot even though the transport is procedural and editable JSON.

The source reference is 1254 x 1254 PNG; an example motion source (`front_idle.png`) is 1122 x 1402. All generated runtime poses normalize to 72 x 96 cells. The package also has semantic control, ground/flight locomotion, actions, speech overlays, pose showcase, and visual-advice capabilities.

The runtime pose is assigned a single layer ID such as `reference_voxel_png:front_idle`. Mouth, teeth, magic sparks, thinking marks, and contact shadow are separate temporary overlay IDs internally. These IDs are discarded when the canvas becomes bytes; clients receive no layer metadata.

## Camera, projection, and coordinates

### Stage profiles

| Profile | Grid | FPS | Aspect |
|---|---:|---:|---:|
| Low | 180 x 101 | 15 | approximately 16:9 |
| Medium/default | 240 x 135 | 24 | 16:9 |
| High | 320 x 180 | 30 | 16:9 |

The browser preserves the logical grid aspect and chooses the largest integer square-cell size that fits the viewport. It uses a no-alpha canvas, disables smoothing, and paints square cells. Therefore production plates should be designed first in the **logical grid**, not in arbitrary HD pixels. A medium reference export at 6 pixels per cell is 1440 x 810, but this is evidence/output convenience, not the runtime resolution.

### World convention

- `x`: horizontal ground position, allowed from -5.0 to +5.0.
- `z`: depth, with 1.5 nearest and 10.0 farthest.
- No world `y` exists for ground placement; flight uses a separate scalar `altitude`.
- Camera is fixed, centered, and implied. There is no transform object, lens/FOV, yaw, pitch, roll, pan, tilt, dolly, or camera animation API.
- Horizon is `0.56 * stage height` (75.6 on the 135-row stage).
- Near floor line is `0.95 * stage height` (128.25 on the 135-row stage).

Projection is an affine depth mapping, not a perspective camera matrix:

```text
depth = clamp((10 - z) / (10 - 1.5), 0, 1)
scale = 0.70 + depth * 0.85
screen_x = width/2 + x * width * 0.075 * scale
screen_y = 0.56*height + depth * (0.95*height - 0.56*height)
```

Scale is quantized to one-eighth steps before character rendering. The reference character then applies a 0.90 multiplier, an additional 1.18 horizontal stretch, and a flight altitude reduction down to 0.76 of grounded size.

This creates useful depth staging but not true foreshortening. There is no shared view/projection matrix that an external background generator can consume.

## Current environment support

### Implemented

- Cached fixed background per grid size.
- Pure white upper field.
- Very faint procedural floor beginning at 56% stage height.
- Screen-space checker/grid marks that become wider and taller toward the foreground.
- Contact-shadow ellipse following the character root.
- Character size and root row vary with world depth.
- Background hash is stable for delta compression.

### Important rendering detail

Most floor tile cells use the space glyph with pale RGB values. The Wizard browser intentionally skips every space cell, so those pale fills do not render. Only non-space grid/highlight marks are visible against the browser's white clear. In other words, the current visible floor is principally a sparse dot/grid treatment, not a fully painted two-tone checkerboard.

The floor generator is screen-space procedural approximation. It does not project four corners of world-space tiles and does not expose a ground mesh, vanishing-point guide, or scene geometry to artists.

### Not implemented

- Background image ingestion in the Wizard runtime.
- Video background or environment clip playback in the Wizard runtime.
- Multiple environment planes or independent scenic layers.
- Alpha compositing or mattes.
- Depth maps, Z-buffer, or per-cell depth.
- Occluder masks for trees, counters, door frames, furniture, or foreground architecture.
- Character-behind-set-element interactions.
- Prop registry, set anchors, seats, doors, counters, path splines, or navmesh.
- Camera moves, multiplane parallax, or perspective-aware environment motion.
- Lighting passes, color grading, weather, atmosphere, reflections, or cast shadows from scenery.
- Multiple characters, character-to-character depth sorting, collision, or group blocking.
- Set IDs, location loading, plate manifests, or continuity metadata.

## Layers, shadows, and occlusion

The actual render order is:

1. copy cached white/floor background;
2. draw one contact shadow;
3. blit one flattened pose;
4. draw mouth/teeth/magic/thinking overlays;
5. convert the entire stage to `[glyph, R, G, B]` bytes.

This produces correct local occlusion only by last-write-wins painting. The character covers its shadow; overlays cover the character. There is no general scene graph. A Joeville foreground layer could not currently pass in front of the feet while the background remains behind the head, because environment and character are no longer separable at the browser.

The shadow is a fixed pale ellipse (`#E8E8E5`), approximately `11 * scale` cells in half-width and `2.2 * scale` cells in half-height. It narrows when lifted but has no light direction, receiver geometry, blur, alpha, or environment color interaction.

## ASCILINE transport and video capability

The Wizard stream sends `INIT:fps:5:cols:rows:0:0:0.000`, followed by binary frames. Each logical color-ASCII cell is exactly four bytes in this order:

```text
[ASCII glyph byte, red byte, green byte, blue byte]
```

Adaptive messages have a four-byte big-endian frame index, one-byte codec tag, then payload. The Wizard codec supports RAW (0), ZLIB (1), DELTA (2), and full-frame RLE (3). Deltas must decode sequentially against the previous framebuffer. Periodic full frames and resync requests restore state.

The separate `ASCILINE` repository can ingest MP4, MKV, AVI, MOV, and WebM with OpenCV/FFmpeg and stream their cell conversion; it can also compile `.ascf` clips. That capability is **not composited with Wizard Joe**. Running a scenic video through stock ASCILINE would produce a full-frame cell video stream, not a clean environment layer under the Wizard stream. A browser-side second canvas would also lack synchronized world projection, depth occlusion, and the authoritative scene clock unless new integration is implemented.

## Production implications for Joeville

### Safe assets to design now

The art team can proceed with environment design, but should preserve these deliverables independently of the current runtime:

- clean 16:9 master plates;
- no-character plates;
- explicit floor/ground plane and horizon guides;
- separate far background, midground, walkable ground, interactive set, foreground occluder, shadow-receiver, atmosphere, and lighting passes;
- binary/graded occlusion mattes;
- depth maps;
- camera metadata and a logical 240 x 135 alignment preview;
- entrances, exits, walk paths, seats, and ensemble blocking zones;
- still variants before moving clips.

Do **not** bake characters, contact shadows, captions, or UI into scenic plates. Do not reduce masters to 240 x 135 only; retain layered high-resolution sources and generate cell-aligned proxies.

### Required visualizer engineering before production integration

1. Add a scene/environment package schema with set ID, camera ID, logical horizon, ground polygon, anchors, paths, and asset references.
2. Decide whether environments become cell framebuffers on the server or image/video layers in the browser. Server-side cell composition best preserves current authoritative streaming and codec behavior.
3. Add explicit layers: far, mid, ground, rear-interactive, characters, front-interactive, foreground, atmosphere, UI.
4. Add alpha/matte or keyed-cell semantics and occluder masks; current four-byte cells have no alpha.
5. Add per-entity depth and stable painter sorting for multiple characters and props.
6. Add a character registry and multi-character state array; the current API and controller are singular.
7. Add scene-clock synchronization for environment clips, animation, and characters.
8. Define a camera contract. If the fixed camera remains, lock it per set. If camera movement is needed, add world-to-screen matrices and parallax rules before generating clips.
9. Add test fixtures for two, five, and thirteen characters, including crowd clipping, occlusion, entrance/exit, seating, and bandwidth.
10. Rework world bounds or add pose-aware safe bounds. Current legal coordinates can visibly clip Wizard Joe at near depth.

## Runtime constraints and risk register

| Risk | Current evidence | Production consequence |
|---|---|---|
| Cast premise mismatch | 1 package, not 13 | Ensemble requirements are untestable |
| Opaque flattened stream | No alpha/layer/depth fields | Scenic occlusion requires new compositor work |
| Near-edge clipping | At x +/-5, z 1.5, only about 30 columns of the pose remain visible | Nominal world bounds are not camera-safe bounds |
| Near top clipping | Centered z 1.5 pose reaches row 1 and loses off-stage source area | Close blocking needs a reduced scale or reframed camera |
| No set geometry | Only x/z and scalar altitude | Seating, doors, counters, steps, hiking grade, and collision are undefined |
| No camera model | Fixed affine projection only | Generated shots cannot match runtime from lens metadata alone |
| No environment asset loader | Fixed procedural white studio | Joeville plates cannot yet be displayed by the Wizard service |
| Space cells are transparent-to-renderer | Browser ignores pale RGB on glyph 32 | Background art converted to cells must use non-space occupancy or a new renderer contract |
| Fixed 4-byte cell format | Glyph + RGB only | Alpha/depth/normal/material data require sidecar buffers or protocol extension |
| Pose library is flat per pose | Single base layer ID | Limb/set interleaving and costume-level occlusion cannot be reconstructed from current pose cells |
| One full stage per frame | 129,600 raw bytes at 240 x 135 | Rich moving backgrounds may sharply reduce delta-codec savings |

## Acceptance gate for claiming Joeville integration readiness

Joeville is not integration-ready until all of the following are demonstrated in the real Wizard service and browser:

- verified registry count and IDs for all intended characters;
- measured scale sheets for every character;
- multi-character render with stable depth sorting;
- one layered Joeville still set with foreground occlusion;
- one moving environment clip synchronized to the scene clock;
- entry/exit and walk-path anchors mapped to world coordinates;
- contact and cast shadows on the Joeville receiver plane;
- pose-aware safe framing at all permitted world positions;
- medium-profile 24 FPS and bandwidth measurements with the new environment;
- reconnect/keyframe reconstruction of the complete scene;
- clean-plate parity between authored master and runtime cell render.
